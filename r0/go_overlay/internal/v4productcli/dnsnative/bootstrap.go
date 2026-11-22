package dnsnative

// One original-Go server-name bootstrap before Android FakeTCP SYN / real
// TLS ClientHello. Only the caller's exact physical Android netd-bound
// DialFunc can open UDP53 and same-endpoint TCP53 on truncation.
// The original B1 Resolver checks DNS ID/question and never falls back to
// the system resolver, a tunnel socket, or an alternate DNS upstream.
// B35 permits the existing App physical upstream IPv4 for this cold stage.
import (
    "context"
    "crypto/rand"
    "encoding/binary"
    "fmt"
    "net/netip"
    "strings"
)

func ValidBootstrapHostname(host string) bool {
    if len(host)<3||len(host)>253{return false}
    labels:=strings.Split(host,".")
    if len(labels)<2{return false}
    letters:=false
    for _,label:=range labels {
        if len(label)==0||len(label)>63||label[0]=='-'||
            label[len(label)-1]=='-'{return false}
        for i:=0;i<len(label);i++{
            c:=label[i]
            alpha:=(c>='a'&&c<='z')||(c>='A'&&c<='Z')
            digit:=c>='0'&&c<='9'
            if !alpha&&!digit&&c!='-'{return false}
            if alpha{letters=true}
        }
    }
    return letters
}
func bootstrapQuery(host string)([]byte,error){
    if !ValidBootstrapHostname(host){return nil,ErrInvalid}
    query:=make([]byte,12)
    if _,err:=rand.Read(query[:2]);err!=nil{return nil,err}
    binary.BigEndian.PutUint16(query[2:4],0x0100)
    binary.BigEndian.PutUint16(query[4:6],1)
    for _,label:=range strings.Split(host,"."){
        query=append(query,byte(len(label)))
        query=append(query,label...)
    }
    query=append(query,0,0,1,0,1) // QTYPE=A, QCLASS=IN
    return query,nil
}
// DNS answer owner names may use RFC1035 backward pointers. Cold-only,
// bounded by the normal DNS reply max, 128 dereferences/labels and
// the exact first uncompressed question. No loose suffix matching.
func bootstrapName(packet []byte,start int)(string,int,error){
    if start<12||start>=len(packet){return "",0,ErrInvalid}
    off:=start
    after:=-1
    labels:=make([]string,0,4)
    size:=0
    for steps:=0;steps<128;steps++{
        if off>=len(packet){return "",0,ErrInvalid}
        n:=int(packet[off])
        if n&0xc0==0xc0{
            if off+1>=len(packet){return "",0,ErrInvalid}
            ptr:=(n&0x3f)<<8|int(packet[off+1])
            if ptr<12||ptr>=off{return "",0,ErrInvalid}
            if after<0{after=off+2}
            off=ptr
            continue
        }
        if n&0xc0!=0{return "",0,ErrInvalid}
        off++
        if n==0{
            if after<0{after=off}
            if len(labels)==0{return "",0,ErrInvalid}
            return strings.Join(labels,"."),after,nil
        }
        if n>63||off+n>len(packet)||size+n+1>255{return "",0,ErrInvalid}
        part:=packet[off:off+n]
        for _,c:=range part{
            if !isLabel(c){return "",0,ErrInvalid}
        }
        labels=append(labels,strings.ToLower(string(part)))
        size+=n+1
        off+=n
    }
    return "",0,ErrInvalid
}
func bootstrapReplyIPv4(host string,answer []byte)(netip.Addr,error){
    if len(answer)<17||len(answer)>MaxReply{return netip.Addr{},ErrInvalid}
    flags:=binary.BigEndian.Uint16(answer[2:4])
    if flags&0x8000==0||flags&0x780f!=0||
        binary.BigEndian.Uint16(answer[4:6])!=1{
        return netip.Addr{},ErrInvalid
    }
    name,off,err:=readNameNoCompression(answer,12)
    if err!=nil||name!=strings.ToLower(host)||off+4>len(answer)||
        binary.BigEndian.Uint16(answer[off:off+2])!=1||
        binary.BigEndian.Uint16(answer[off+2:off+4])!=1{
        return netip.Addr{},ErrInvalid
    }
    off+=4
    count:=int(binary.BigEndian.Uint16(answer[6:8]))
    if count==0||count>64{return netip.Addr{},ErrInvalid}
    aliases:=make(map[string]string,4)
    addrs:=make(map[string]netip.Addr,4)
    for i:=0;i<count;i++{
        owner,next,e:=bootstrapName(answer,off)
        if e!=nil||next+10>len(answer){return netip.Addr{},ErrInvalid}
        kind:=binary.BigEndian.Uint16(answer[next:next+2])
        class:=binary.BigEndian.Uint16(answer[next+2:next+4])
        rdlen:=int(binary.BigEndian.Uint16(answer[next+8:next+10]))
        rd:=next+10
        if rdlen>len(answer)-rd{return netip.Addr{},ErrInvalid}
        if class==1{
            switch kind{
            case 1:
                if rdlen!=4{return netip.Addr{},ErrInvalid}
                var raw [4]byte
                copy(raw[:],answer[rd:rd+4])
                ip:=netip.AddrFrom4(raw)
                if !ip.IsGlobalUnicast(){return netip.Addr{},ErrInvalid}
                if _,exists:=addrs[owner];!exists{addrs[owner]=ip}
            case 5:
                alias,end,e:=bootstrapName(answer,rd)
                if e!=nil||end!=rd+rdlen{
                    return netip.Addr{},ErrInvalid
                }
                aliases[owner]=alias
            }
        }
        off=rd+rdlen
    }
    current:=strings.ToLower(host)
    for i:=0;i<8;i++{
        if ip,ok:=addrs[current];ok{return ip,nil}
        alias,ok:=aliases[current]
        if !ok{return netip.Addr{},ErrInvalid}
        current=alias
    }
    return netip.Addr{},ErrInvalid
}
func ResolveBootstrapIPv4(ctx context.Context,host string,dial DialFunc)(netip.Addr,error){
    return ResolveBootstrapIPv4WithUpstream(ctx,host,dial,netip.MustParseAddr("223.5.5.5"))
}

// ResolveBootstrapIPv4WithUpstream uses the selected Android Network's
// already-scoped Go UDP/TCP dialer with one configured DNS IPv4. The same
// endpoint is retained when a valid DNS TC reply requires TCP/53.
func ResolveBootstrapIPv4WithUpstream(
    ctx context.Context,host string,dial DialFunc,upstream netip.Addr,
)(netip.Addr,error){
    if ctx==nil||dial==nil{return netip.Addr{},ErrUnbound}
    if _,err:=ParsePhysicalDNSUpstreamIPv4(upstream.String());err!=nil{
        return netip.Addr{},err
    }
    question,err:=bootstrapQuery(host)
    if err!=nil{return netip.Addr{},err}
    resolver,err:=New(dial,nil,false)
    if err!=nil{return netip.Addr{},err}
    resolver.direct=upstream.String()+":53"
    reply,err:=resolver.Resolve(ctx,question,true) // always exact selected physical upstream
    if err!=nil{return netip.Addr{},fmt.Errorf("physical DNS bootstrap: %w",err)}
    ip,err:=bootstrapReplyIPv4(host,reply)
    if err!=nil{return netip.Addr{},fmt.Errorf("DNS bootstrap A answer: %w",err)}
    return ip,nil
}
