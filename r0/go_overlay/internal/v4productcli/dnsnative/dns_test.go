package dnsnative

import (
	"bytes"
	"context"
	"encoding/binary"
	"errors"
	"fmt"
	"io"
	"net"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

type localDNS struct {
	tcp net.Listener
	udp net.PacketConn
	addr string
	ip [4]byte
	truncate bool
	badID bool
	delay time.Duration
	ttl uint32
	udpCalls atomic.Int32
	tcpCalls atomic.Int32
}
func serveDNS(t *testing.T,ip [4]byte) *localDNS {
	t.Helper()
	tcp,e:=net.Listen("tcp","127.0.0.1:0")
	if e!=nil{t.Fatal(e)}
	udp,e:=net.ListenPacket("udp",tcp.Addr().String())
	if e!=nil{tcp.Close();t.Fatal(e)}
	s:=&localDNS{tcp:tcp,udp:udp,addr:tcp.Addr().String(),ip:ip,ttl:2}
	t.Cleanup(func(){tcp.Close();udp.Close()})
	go func(){
		var buffer [MaxQuery+1]byte
		for{
			n,peer,err:=udp.ReadFrom(buffer[:])
			if err!=nil{return}
			s.udpCalls.Add(1)
			query:=append([]byte(nil),buffer[:n]...)
			if s.delay>0{time.Sleep(s.delay)}
			response,e:=s.reply(query,s.truncate)
			if e==nil{_,_=udp.WriteTo(response,peer)}
		}
	}()
	go func(){
		for{
			conn,err:=tcp.Accept()
			if err!=nil{return}
			s.tcpCalls.Add(1)
			go func(c net.Conn){
				defer c.Close()
				c.SetDeadline(time.Now().Add(2*time.Second))
				var size [2]byte
				if _,e:=io.ReadFull(c,size[:]);e!=nil{return}
				n:=int(binary.BigEndian.Uint16(size[:]))
				if n<17||n>MaxQuery{return}
				query:=make([]byte,n)
				if _,e:=io.ReadFull(c,query);e!=nil{return}
				response,e:=s.reply(query,false)
				if e!=nil{return}
				binary.BigEndian.PutUint16(size[:],uint16(len(response)))
				_,_=c.Write(append(size[:],response...))
			}(conn)
		}
	}()
	return s
}
func (s *localDNS) reply(query []byte,tc bool)([]byte,error){
	q,e:=parseQuery(query)
	if e!=nil{return nil,e}
	flags:=uint16(0x8180)
	if tc{flags=0x8380}
	out:=append([]byte(nil),query[:q.end]...)
	binary.BigEndian.PutUint16(out[2:4],flags)
	binary.BigEndian.PutUint16(out[6:8],0)
	binary.BigEndian.PutUint16(out[8:10],0)
	binary.BigEndian.PutUint16(out[10:12],0)
	if !tc {
		binary.BigEndian.PutUint16(out[6:8],1)
		var answer [16]byte
		answer[0]=0xc0;answer[1]=0x0c
		binary.BigEndian.PutUint16(answer[2:4],1)
		binary.BigEndian.PutUint16(answer[4:6],1)
		binary.BigEndian.PutUint32(answer[6:10],s.ttl)
		binary.BigEndian.PutUint16(answer[10:12],4)
		copy(answer[12:],s.ip[:])
		out=append(out,answer[:]...)
	}
	if s.badID{out[1]^=0xff}
	return out,nil
}
func makeQuery(name string,id uint16) []byte {
	out:=make([]byte,12)
	binary.BigEndian.PutUint16(out[:2],id)
	binary.BigEndian.PutUint16(out[2:4],0x0100)
	binary.BigEndian.PutUint16(out[4:6],1)
	for _,label:=range strings.Split(name,"."){
		out=append(out,byte(len(label)))
		out=append(out,label...)
	}
	out=append(out,0,0,1,0,1)
	return out
}
func scopedDial(direct,tunnel *localDNS) DialFunc {
	return func(ctx context.Context,path Path,network,endpoint string)(net.Conn,error){
		var destination string
		switch path{
		case Physical:
			if endpoint!=direct.addr{return nil,fmt.Errorf("wrong physical upstream %s",endpoint)}
			destination=direct.addr
		case Tunnel:
			if endpoint!=tunnel.addr{return nil,fmt.Errorf("wrong tunnel upstream %s",endpoint)}
			destination=tunnel.addr
		default:
			return nil,fmt.Errorf("unbound route %d",path)
		}
		return (&net.Dialer{}).DialContext(ctx,network,destination)
	}
}
func resolverForTest(t *testing.T,direct,tunnel *localDNS,
	split bool,cn CNMatch) *Resolver {
	t.Helper()
	r,e:=New(scopedDial(direct,tunnel),cn,split)
	if e!=nil{t.Fatal(e)}
	// Loopback test endpoints are private unexported test fixtures only.
	// New() always defaults to the fixed real CN/Tunnel endpoints.
	r.direct=direct.addr
	r.tunnel=tunnel.addr
	return r
}
func lastIP(t *testing.T,answer []byte)[4]byte{
	t.Helper()
	if len(answer)<4{t.Fatal("missing A record")}
	var got [4]byte
	copy(got[:],answer[len(answer)-4:])
	return got
}
func TestOriginalQNameSelectsCNPhysicalOrTunnelWithoutFakeIP(t *testing.T){
	cn:=serveDNS(t,[4]byte{203,0,113,15})
	tunnel:=serveDNS(t,[4]byte{198,51,100,19})
	r:=resolverForTest(t,cn,tunnel,true,func(n string)bool{
		return n=="cn"||strings.HasSuffix(n,".cn")
	})
	a,e:=r.Resolve(context.Background(),makeQuery("Example.CN",0x1001),false)
	if e!=nil||lastIP(t,a)!=cn.ip{t.Fatal("CN original QNAME not sent physical",e)}
	b,e:=r.Resolve(context.Background(),makeQuery("www.world.net",0x1002),false)
	if e!=nil||lastIP(t,b)!=tunnel.ip{t.Fatal("foreign QNAME not sent tunnel",e)}
	if cn.udpCalls.Load()!=1||tunnel.udpCalls.Load()!=1{
		t.Fatal("unexpected cross-route DNS query")}
}
func TestSplitOffUsesTunnelBootstrapAlwaysPhysical(t *testing.T){
	cn:=serveDNS(t,[4]byte{203,0,113,8})
	tunnel:=serveDNS(t,[4]byte{198,51,100,9})
	r:=resolverForTest(t,cn,tunnel,false,func(string)bool{return true})
	for i,tc:=range []struct{name string;bootstrap bool;expected [4]byte}{
		{"cn.example.cn",false,tunnel.ip},
		{"tls.wbd.example",true,cn.ip},
	}{
		answer,e:=r.Resolve(context.Background(),makeQuery(tc.name,uint16(i+1)),tc.bootstrap)
		if e!=nil||lastIP(t,answer)!=tc.expected{t.Fatal(tc,e)}
	}
	if cn.udpCalls.Load()!=1||tunnel.udpCalls.Load()!=1{t.Fatal("bootstrap path leak")}
}
func TestTruncatedUDPOnlyTCP53SameEndpointAndPath(t *testing.T){
	cn:=serveDNS(t,[4]byte{203,0,113,33})
	cn.truncate=true
	tunnel:=serveDNS(t,[4]byte{198,51,100,44})
	r:=resolverForTest(t,cn,tunnel,true,func(string)bool{return true})
	a,e:=r.Resolve(context.Background(),makeQuery("site.cn",0x2828),false)
	if e!=nil||lastIP(t,a)!=cn.ip{t.Fatal("TCP53 fallback failed",e)}
	if cn.udpCalls.Load()!=1||cn.tcpCalls.Load()!=1||
		tunnel.udpCalls.Load()!=0||tunnel.tcpCalls.Load()!=0{
		t.Fatal("cross-upstream fallback or missing TCP retry")
	}
}
func TestRefuseCrossFallbackIfSelectedPathFails(t *testing.T){
	cn:=serveDNS(t,[4]byte{203,0,113,9})
	tunnel:=serveDNS(t,[4]byte{198,51,100,9})
	dial:=func(ctx context.Context,path Path,network,endpoint string)(net.Conn,error){
		if path==Physical{return nil,errors.New("physical route unavailable")}
		return scopedDial(cn,tunnel)(ctx,path,network,endpoint)
	}
	r,e:=New(dial,func(string)bool{return true},true)
	if e!=nil{t.Fatal(e)}
	r.direct=cn.addr;r.tunnel=tunnel.addr
	if _,e=r.Resolve(context.Background(),makeQuery("china.cn",11),false);e==nil{
		t.Fatal("succeeded despite selected physical DNS failure")
	}
	if tunnel.udpCalls.Load()!=0||tunnel.tcpCalls.Load()!=0{
		t.Fatal("illicit tunnel fallback from physical failure")
	}
	if _,e=New(nil,nil,true);!errors.Is(e,ErrUnbound){t.Fatal("unbound DNS socket accepted")}
}
func TestRejectSpoofedTransactionAndMalformedQuestions(t *testing.T){
	cn:=serveDNS(t,[4]byte{203,0,113,9})
	cn.badID=true
	tunnel:=serveDNS(t,[4]byte{198,51,100,9})
	r:=resolverForTest(t,cn,tunnel,true,func(string)bool{return true})
	q:=makeQuery("valid.cn",0x3300)
	if _,e:=r.Resolve(context.Background(),q,false);e==nil{
		t.Fatal("mismatched DNS transaction ID accepted")
	}
	bad:=[][]byte{
		{0,0}, // truncated header
		append([]byte(nil),q...),
		append([]byte(nil),q...),
		append([]byte(nil),q...),
	}
	bad[1][2]|=0x80 // QR=1 in a query
	bad[2][12]=0xc0 // compressed query name prohibited
	bad[3]=append(bad[3],0xff) // trailing forged data
	for i,packet:=range bad{
		if _,e:=r.Resolve(context.Background(),packet,false);e==nil{
			t.Fatalf("invalid DNS question %d accepted",i)
		}
	}
	if tunnel.udpCalls.Load()!=0{t.Fatal("spoof sent to alternate resolver")}
}
func TestBoundedTTLCacheIDRewriteAndExpiration(t *testing.T){
	cn:=serveDNS(t,[4]byte{203,0,113,61})
	tunnel:=serveDNS(t,[4]byte{198,51,100,62})
	r:=resolverForTest(t,cn,tunnel,true,func(string)bool{return true})
	a,e:=r.Resolve(context.Background(),makeQuery("cache.cn",0x1010),false)
	if e!=nil{t.Fatal(e)}
	b,e:=r.Resolve(context.Background(),makeQuery("cache.cn",0x2020),false)
	if e!=nil{t.Fatal(e)}
	if !bytes.Equal(a[2:],b[2:])||binary.BigEndian.Uint16(b[:2])!=0x2020||
		cn.udpCalls.Load()!=1{
		t.Fatal("cache must not leak first request ID or requery")
	}
	if len(r.cache)!=1||len(r.cache)>maxCache{t.Fatal("not bounded cache")}
	time.Sleep(2200*time.Millisecond)
	if _,e=r.Resolve(context.Background(),makeQuery("cache.cn",0x3030),false);e!=nil{
		t.Fatal(e)
	}
	if cn.udpCalls.Load()!=2{t.Fatal("expired TTL entry served stale")}
}
func TestConcurrentQueriesCoalesceWithoutBackgroundTimers(t *testing.T){
	cn:=serveDNS(t,[4]byte{203,0,113,70})
	cn.delay=80*time.Millisecond
	tunnel:=serveDNS(t,[4]byte{198,51,100,71})
	r:=resolverForTest(t,cn,tunnel,true,func(string)bool{return true})
	const n=12
	var group sync.WaitGroup
	errs:=make(chan error,n)
	start:=make(chan struct{})
	for i:=0;i<n;i++{
		group.Add(1)
		go func(i int){
			defer group.Done()
			<-start
			id:=uint16(0x4000+i)
			out,e:=r.Resolve(context.Background(),makeQuery("merge.cn",id),false)
			if e!=nil{errs<-e;return}
			if binary.BigEndian.Uint16(out[:2])!=id{
				errs<-fmt.Errorf("wrong coalesced transaction ID")
			}
		}(i)
	}
	close(start);group.Wait();close(errs)
	for e:=range errs{t.Fatal(e)}
	if cn.udpCalls.Load()!=1||tunnel.udpCalls.Load()!=0{
		t.Fatalf("inflight not merged or crossed path: physical %d tunnel %d",
			cn.udpCalls.Load(),tunnel.udpCalls.Load())
	}
}
