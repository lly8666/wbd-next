// Package dnsnative is the ordinary no-FakeIP DNS wire/transport component
// for the Android Root product. It does NOT intercept Android system DNS,
// own the TUN, or bypass Android ConnectivityManager/netd by itself.
//
// The caller must supply a path-aware DialFunc which binds each socket to
// the exact selected physical Network or to the authenticated WBD TUN.
// Missing binding is always an error; there is NO default net.Dialer.
package dnsnative

import (
	"context"
	"encoding/binary"
	"errors"
	"fmt"
	"io"
	"net"
	"strings"
	"sync"
	"time"
)

type Path uint8

const (
	Physical Path = 1
	Tunnel   Path = 2
)
const (
	ChinaDNS  = "223.5.5.5:53"
	TunnelDNS = "1.1.1.1:53"
	MaxQuery  = 4096
	MaxReply  = 16384
	maxCache  = 256
	maxFlight = 64
)
var (
	ErrInvalid = errors.New("invalid ordinary DNS wire message")
	ErrBusy = errors.New("ordinary DNS in-flight limit")
	ErrUnbound = errors.New("missing authenticated path-aware DNS dialer")
)

type DialFunc func(context.Context, Path, string, string) (net.Conn, error)
type CNMatch func(string) bool

// Resolver is one scoped generation. No DNS socket has a default path,
// global UID exception, alternate endpoint, retry direction, or fallback.
type Resolver struct {
	dial DialFunc
	cn CNMatch
	split bool
	direct string
	tunnel string
	mu sync.Mutex
	cache map[string]entry
	flying map[string]*flight
}
type entry struct {
	wire []byte
	at time.Time
	until time.Time
	ttlFields []int
}
type flight struct {
	done chan struct{}
	wire []byte
	err error
}
func New(dial DialFunc, match CNMatch, cnSplit bool) (*Resolver,error) {
	if dial==nil{return nil,ErrUnbound}
	// A split request without an authenticated, complete CN matcher is
	// a configuration failure, NOT permission to silently send CN names
	// to tunnel DNS. Original server bootstrap still has its own scope.
	if cnSplit&&match==nil{return nil,fmt.Errorf("%w: CN split requires verified domain matcher",ErrUnbound)}
	return &Resolver{dial:dial,cn:match,split:cnSplit,
		direct:ChinaDNS,tunnel:TunnelDNS,
		cache:make(map[string]entry),flying:make(map[string]*flight)},nil
}
func (r *Resolver) decide(name string,bootstrap bool) (Path,string){
	if bootstrap||(r.split&&r.cn!=nil&&r.cn(name)){
		return Physical,r.direct
	}
	return Tunnel,r.tunnel
}
func isLabel(c byte)bool{
	return (c>='a'&&c<='z')||(c>='A'&&c<='Z')||
		(c>='0'&&c<='9')||c=='-'||c=='_'
}
func readNameNoCompression(packet []byte,off int)(string,int,error){
	if off<12||off>=len(packet){return "",0,ErrInvalid}
	var labels []string
	begin:=off
	for steps:=0;steps<128;steps++{
		if off>=len(packet){return "",0,ErrInvalid}
		n:=int(packet[off]);off++
		if n==0{
			if off-begin>255{return "",0,ErrInvalid}
			return strings.Join(labels,"."),off,nil
		}
		if n>63||off+n>len(packet){return "",0,ErrInvalid}
		for _,ch:=range packet[off:off+n]{
			if !isLabel(ch){return "",0,ErrInvalid}
		}
		labels=append(labels,strings.ToLower(string(packet[off:off+n])))
		off+=n
	}
	return "",0,ErrInvalid
}
type question struct{
	name string
	typ uint16
	class uint16
	end int
	cacheable bool
}
func parseQuery(packet []byte)(question,error){
	var q question
	if len(packet)<17||len(packet)>MaxQuery{return q,ErrInvalid}
	flags:=binary.BigEndian.Uint16(packet[2:4])
	if flags&0x8000!=0||flags&0x7800!=0||
		binary.BigEndian.Uint16(packet[4:6])!=1||
		binary.BigEndian.Uint16(packet[6:8])!=0||
		binary.BigEndian.Uint16(packet[8:10])!=0{
		return q,ErrInvalid
	}
	additional:=binary.BigEndian.Uint16(packet[10:12])
	if additional>1{return q,ErrInvalid}
	name,off,err:=readNameNoCompression(packet,12)
	if err!=nil||name==""||len(name)>253||off+4>len(packet){
		return q,ErrInvalid
	}
	q=question{name:name,typ:binary.BigEndian.Uint16(packet[off:off+2]),
		class:binary.BigEndian.Uint16(packet[off+2:off+4]),end:off+4}
	if q.typ==0||q.class!=1{return question{},ErrInvalid}
	if additional==0&&q.end!=len(packet){return question{},ErrInvalid}
	if additional==1{
		// Only one bounded EDNS OPT RR; no concatenated hidden messages,
		// arbitrary additional records or malformed length fields.
		p:=q.end
		if p+11>len(packet)||packet[p]!=0||
			binary.BigEndian.Uint16(packet[p+1:p+3])!=41{
			return question{},ErrInvalid
		}
		rdlen:=int(binary.BigEndian.Uint16(packet[p+9:p+11]))
		if p+11+rdlen!=len(packet){return question{},ErrInvalid}
	}
	q.cacheable=additional==0&&flags&0x0010==0&&flags&0x0020==0
	return q,nil
}
func validateReply(query,reply []byte,q question)(bool,error){
	if len(reply)<12||len(reply)>MaxReply||len(query)<12{
		return false,ErrInvalid
	}
	if reply[0]!=query[0]||reply[1]!=query[1]{
		return false,fmt.Errorf("%w: transaction ID mismatch",ErrInvalid)
	}
	flags:=binary.BigEndian.Uint16(reply[2:4])
	if flags&0x8000==0||flags&0x7800!=0||
		binary.BigEndian.Uint16(reply[4:6])!=1{
		return false,ErrInvalid
	}
	name,off,err:=readNameNoCompression(reply,12)
	if err!=nil||name!=q.name||off+4>len(reply)||
		binary.BigEndian.Uint16(reply[off:off+2])!=q.typ||
		binary.BigEndian.Uint16(reply[off+2:off+4])!=q.class{
		return false,fmt.Errorf("%w: answer question mismatches the original QNAME",ErrInvalid)
	}
	return flags&0x0200!=0,nil
}
func skipName(message []byte,off int)(int,error){
	if off<0||off>=len(message){return 0,ErrInvalid}
	for steps:=0;steps<128;steps++{
		if off>=len(message){return 0,ErrInvalid}
		n:=message[off]
		if n==0{return off+1,nil}
		if n&0xc0==0xc0{
			if off+1>=len(message){return 0,ErrInvalid}
			ptr:=int(n&0x3f)<<8|int(message[off+1])
			if ptr>=off||ptr<12{return 0,ErrInvalid}
			return off+2,nil
		}
		if n&0xc0!=0||n>63||off+1+int(n)>len(message){
			return 0,ErrInvalid
		}
		off+=1+int(n)
	}
	return 0,ErrInvalid
}
func cacheFields(reply []byte,q question)([]int,uint32,bool){
	flags:=binary.BigEndian.Uint16(reply[2:4])
	if flags&0x0200!=0||flags&0x000f!=0||
		binary.BigEndian.Uint16(reply[4:6])!=1||
		binary.BigEndian.Uint16(reply[8:10])!=0||
		binary.BigEndian.Uint16(reply[10:12])!=0{
		return nil,0,false
	}
	count:=int(binary.BigEndian.Uint16(reply[6:8]))
	if count<1||count>64{return nil,0,false}
	_,off,err:=readNameNoCompression(reply,12)
	if err!=nil||off+4>len(reply){return nil,0,false}
	off+=4
	var fields []int
	min:=uint32(300)
	for i:=0;i<count;i++{
		var e error
		off,e=skipName(reply,off)
		if e!=nil||off+10>len(reply){return nil,0,false}
		typ:=binary.BigEndian.Uint16(reply[off:off+2])
		class:=binary.BigEndian.Uint16(reply[off+2:off+4])
		ttl:=binary.BigEndian.Uint32(reply[off+4:off+8])
		rdlen:=int(binary.BigEndian.Uint16(reply[off+8:off+10]))
		if class!=q.class||typ==41||ttl==0||off+10+rdlen>len(reply){
			return nil,0,false
		}
		if ttl<min{min=ttl}
		fields=append(fields,off+4)
		off+=10+rdlen
	}
	if off!=len(reply){return nil,0,false}
	if min==0{return nil,0,false}
	return fields,min,true
}
func withID(wire,query []byte)[]byte{
	out:=append([]byte(nil),wire...)
	copy(out[:2],query[:2])
	return out
}
func (r *Resolver) cached(key string,query []byte)([]byte,bool){
	e,ok:=r.cache[key]
	if !ok{return nil,false}
	now:=time.Now()
	if !now.Before(e.until){delete(r.cache,key);return nil,false}
	out:=withID(e.wire,query)
	elapsed:=uint32(now.Sub(e.at)/time.Second)
	for _,off:=range e.ttlFields{
		ttl:=binary.BigEndian.Uint32(out[off:off+4])
		if elapsed>=ttl{ttl=0}else{ttl-=elapsed}
		binary.BigEndian.PutUint32(out[off:off+4],ttl)
	}
	return out,true
}
func (r *Resolver) store(key string,reply []byte,q question){
	offsets,ttl,ok:=cacheFields(reply,q)
	if !ok{return}
	if len(r.cache)>=maxCache{
		for k,e:=range r.cache{
			if !time.Now().Before(e.until){delete(r.cache,k)}
		}
		if len(r.cache)>=maxCache{
			// Bounded even with 256 distinct live names; eviction does not
			// start a background timer or block DNS packet processing.
			for k:=range r.cache{delete(r.cache,k);break}
		}
	}
	now:=time.Now()
	r.cache[key]=entry{wire:append([]byte(nil),reply...),at:now,
		until:now.Add(time.Duration(ttl)*time.Second),
		ttlFields:offsets}
}
func deadline(ctx context.Context)time.Time{
	t:=time.Now().Add(3*time.Second)
	if end,ok:=ctx.Deadline();ok&&end.Before(t){return end}
	return t
}
func (r *Resolver) udp(ctx context.Context,path Path,server string,query []byte)([]byte,error){
	c,err:=r.dial(ctx,path,"udp",server)
	if err!=nil{return nil,err}
	if c==nil{return nil,ErrUnbound}
	defer c.Close()
	if err=c.SetDeadline(deadline(ctx));err!=nil{return nil,err}
	n,err:=c.Write(query)
	if err!=nil{return nil,err}
	if n!=len(query){return nil,io.ErrShortWrite}
	var buf [MaxQuery+1]byte
	n,err=c.Read(buf[:])
	if err!=nil{return nil,err}
	if n>MaxQuery{return nil,ErrInvalid} // never return an incomplete UDP datagram
	return append([]byte(nil),buf[:n]...),nil
}
func (r *Resolver) tcp(ctx context.Context,path Path,server string,query []byte)([]byte,error){
	c,err:=r.dial(ctx,path,"tcp",server)
	if err!=nil{return nil,err}
	if c==nil{return nil,ErrUnbound}
	defer c.Close()
	if err=c.SetDeadline(deadline(ctx));err!=nil{return nil,err}
	buf:=make([]byte,2+len(query))
	binary.BigEndian.PutUint16(buf[:2],uint16(len(query)))
	copy(buf[2:],query)
	for written:=0;written<len(buf);{
		n,e:=c.Write(buf[written:])
		if e!=nil{return nil,e}
		if n==0{return nil,io.ErrShortWrite}
		written+=n
	}
	var header [2]byte
	if _,err=io.ReadFull(c,header[:]);err!=nil{return nil,err}
	n:=int(binary.BigEndian.Uint16(header[:]))
	if n<17||n>MaxReply{return nil,ErrInvalid}
	reply:=make([]byte,n)
	if _,err=io.ReadFull(c,reply);err!=nil{return nil,err}
	return reply,nil
}
func (r *Resolver) exchange(ctx context.Context,query []byte,q question,
	path Path,address string)([]byte,error){
	reply,err:=r.udp(ctx,path,address,query)
	if err!=nil{return nil,err} // NEVER try another upstream.
	truncated,err:=validateReply(query,reply,q)
	if err!=nil{return nil,err}
	if truncated{
		// RFC 1035 TC only retries TCP against the SAME endpoint and path.
		reply,err=r.tcp(ctx,path,address,query)
		if err!=nil{return nil,err}
		truncated,err=validateReply(query,reply,q)
		if err!=nil{return nil,err}
		if truncated{return nil,ErrInvalid}
	}
	return reply,nil
}
// Resolve is one cold/native ordinary DNS question. A bootstrap query always
// uses physical CN DNS. Ordinary split mode chooses from ORIGINAL QNAME only:
// CN -> physical 223.5.5.5; otherwise tunnel 1.1.1.1. Split off -> tunnel.
// The caller MUST supply a correct explicitly path-bound DialFunc; the
// implementation never calls net.Dialer itself or performs fallback.
func (r *Resolver) Resolve(ctx context.Context,query []byte,bootstrap bool)([]byte,error){
	if r==nil||r.dial==nil{return nil,ErrUnbound}
	q,err:=parseQuery(query)
	if err!=nil{return nil,err}
	if err=ctx.Err();err!=nil{return nil,err}
	path,addr:=r.decide(q.name,bootstrap)
	// Includes original query bytes, flags, QTYPE, EDNS and selected path.
	// Only the transaction ID is excluded, and it is rewritten on reply.
	key:=string([]byte{byte(path)})+string(query[2:])
	r.mu.Lock()
	if q.cacheable{
		if cached,hit:=r.cached(key,query);hit{
			r.mu.Unlock();return cached,nil
		}
		if f,ok:=r.flying[key];ok{
			r.mu.Unlock()
			select {
			case <-f.done:
				if f.err!=nil{return nil,f.err}
				return withID(f.wire,query),nil
			case <-ctx.Done():
				return nil,ctx.Err()
			}
		}
		if len(r.flying)>=maxFlight{
			r.mu.Unlock();return nil,ErrBusy
		}
		f:=&flight{done:make(chan struct{})}
		r.flying[key]=f
		r.mu.Unlock()
		result,e:=r.exchange(ctx,query,q,path,addr)
		r.mu.Lock()
		if e==nil{
			r.store(key,result,q)
			f.wire=append([]byte(nil),result...)
		}
		f.err=e
		close(f.done)
		delete(r.flying,key)
		r.mu.Unlock()
		return result,e
	}
	r.mu.Unlock()
	return r.exchange(ctx,query,q,path,addr)
}
