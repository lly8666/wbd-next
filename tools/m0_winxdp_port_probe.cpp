// Disposable local WSL test: XDP destination IP + owned TCP port.
// No change to the WBD wire or product. No custom eBPF program.
#define XDP_API_VERSION 3
#define XDP_INCLUDE_WINCOMMON
#define NOMINMAX
#include <xdpapi.h>
#include <afxdp_helper.h>
#include <ws2tcpip.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <set>

constexpr UINT32 RingSize=256, Chunk=2048;
UINT16 OwnedPort=39461, OtherPort=39462;
struct Owner{
    HANDLE xsk=nullptr,prog=nullptr;
    SOCKET owned=INVALID_SOCKET,listener=INVALID_SOCKET;
    unsigned char* umem=nullptr;
    UINT8 bitmap[XDP_PORT_SET_BUFFER_SIZE]{};
    XSK_RING rx{},fill{};
    ~Owner(){
        if(prog)CloseHandle(prog);
        if(xsk)CloseHandle(xsk);
        if(umem)VirtualFree(umem,0,MEM_RELEASE);
        if(listener!=INVALID_SOCKET)closesocket(listener);
        if(owned!=INVALID_SOCKET)closesocket(owned);
    }
};
static void check(const char* n,XDP_STATUS hr){
    if(XDP_FAILED(hr)){std::fprintf(stderr,"%s: 0x%08lx\n",n,(unsigned long)hr);throw 1;}
}
static SOCKET bind_tcp(sockaddr_in address){
    SOCKET s=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);
    if(s==INVALID_SOCKET)throw 2;
    BOOL exclusive=TRUE;
    if(setsockopt(s,SOL_SOCKET,SO_EXCLUSIVEADDRUSE,reinterpret_cast<const char*>(&exclusive),sizeof(exclusive))||bind(s,reinterpret_cast<sockaddr*>(&address),sizeof(address))){
        std::fprintf(stderr,"bind port %u: %d\n",ntohs(address.sin_port),WSAGetLastError());closesocket(s);throw 2;
    }
    return s;
}
int main(int argc,char** argv){
    if(argc!=5)return 2;
    const bool dstOnly=std::strcmp(argv[3],"tcp-dst")==0;
    OwnedPort=static_cast<UINT16>(std::strtoul(argv[4],nullptr,10));OtherPort=OwnedPort+1;
    WSADATA w{};if(WSAStartup(MAKEWORD(2,2),&w))return 2;
    try{
        Owner o;
        UINT32 index=std::strtoul(argv[1],nullptr,10);
        sockaddr_in local{};local.sin_family=AF_INET;local.sin_port=htons(OwnedPort);
        if(InetPtonA(AF_INET,argv[2],&local.sin_addr)!=1)return 3;
        sockaddr_in reservation=local;if(dstOnly)reservation.sin_addr.s_addr=INADDR_ANY;
        o.owned=bind_tcp(reservation);
        SOCKET conflict=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);
        if(conflict==INVALID_SOCKET)throw 2;
        int rc=bind(conflict,reinterpret_cast<sockaddr*>(&local),sizeof(local));
        int err=WSAGetLastError();closesocket(conflict);
        std::printf("COMPETING_BIND_RC=%d WSA=%d\n",rc,err);
        if(rc!=SOCKET_ERROR)return 4;
        local.sin_port=htons(OtherPort);o.listener=bind_tcp(local);
        if(listen(o.listener,2))throw 2;
        u_long nonblock=1;if(ioctlsocket(o.listener,FIONBIO,&nonblock))throw 2;
        o.umem=static_cast<unsigned char*>(VirtualAlloc(nullptr,RingSize*Chunk,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));
        if(!o.umem)return 5;
        check("create",XskCreate(&o.xsk));
        XSK_UMEM_REG reg{};reg.TotalSize=RingSize*Chunk;reg.ChunkSize=Chunk;reg.Address=o.umem;
        check("umem",XskSetSockopt(o.xsk,XSK_SOCKOPT_UMEM_REG,&reg,sizeof(reg)));
        check("bind",XskBind(o.xsk,index,0,XSK_BIND_FLAG_RX|XSK_BIND_FLAG_GENERIC));
        check("rx size",XskSetSockopt(o.xsk,XSK_SOCKOPT_RX_RING_SIZE,&RingSize,sizeof(RingSize)));
        check("fill size",XskSetSockopt(o.xsk,XSK_SOCKOPT_RX_FILL_RING_SIZE,&RingSize,sizeof(RingSize)));
        check("activate",XskActivate(o.xsk,XSK_ACTIVATE_FLAG_NONE));
        XSK_RING_INFO_SET info{};UINT32 size=sizeof(info);
        check("info",XskGetSockopt(o.xsk,XSK_SOCKOPT_RING_INFO,&info,&size));
        XskRingInitialize(&o.rx,&info.Rx);XskRingInitialize(&o.fill,&info.Fill);
        UINT32 fi;
        if(XskRingProducerReserve(&o.fill,RingSize,&fi)!=RingSize)return 6;
        for(UINT32 i=0;i<RingSize;++i)*static_cast<UINT64*>(XskRingGetElement(&o.fill,fi+i))=UINT64(i)*Chunk;
        XskRingProducerSubmit(&o.fill,RingSize);
        // Upstream programinspect.c tests the TCP header's network-order
        // 16-bit destination value directly against the port bitmap.
        UINT16 bit=htons(OwnedPort);o.bitmap[bit/8]|=UINT8(1u<<(bit%8));
        XDP_HOOK_ID hook{XDP_HOOK_L2,XDP_HOOK_RX,XDP_HOOK_INSPECT};
        XDP_RULE rule{};
        if(dstOnly){rule.Match=XDP_MATCH_TCP_DST;rule.Pattern.Port=htons(OwnedPort);}
        else{rule.Match=XDP_MATCH_IPV4_TCP_PORT_SET;rule.Pattern.IpPortSet.Address.Ipv4=local.sin_addr;rule.Pattern.IpPortSet.PortSet.PortSet=o.bitmap;}
        rule.Action=XDP_PROGRAM_ACTION_REDIRECT;
        rule.Redirect.TargetType=XDP_REDIRECT_TARGET_TYPE_XSK;rule.Redirect.Target=o.xsk;
        check("redirect",XdpCreateProgram(index,&hook,0,XDP_CREATE_PROGRAM_FLAG_GENERIC,&rule,1,&o.prog));
        XSK_NOTIFY_RESULT_FLAGS flags{};
        check("fill poke",XskNotifySocket(o.xsk,XSK_NOTIFY_FLAG_POKE_RX,0,&flags));
        std::printf("READY owned=%u ordinary=%u ifindex=%u mode=%s\n",OwnedPort,OtherPort,index,argv[3]);std::fflush(stdout);
        std::set<UINT16> sources;
        UINT32 total=0,foreign=0,ordinary=0;
        ULONGLONG deadline=GetTickCount64()+16000;
        while(GetTickCount64()<deadline && (sources.size()<2||ordinary==0)){
            SOCKET peer=accept(o.listener,nullptr,nullptr);
            if(peer!=INVALID_SOCKET){
                const char ok[]="ORDINARY_TCP_OK";
                int n=send(peer,ok,sizeof(ok)-1,0);closesocket(peer);
                if(n==sizeof(ok)-1)++ordinary;
            }
            UINT32 ri;UINT32 n=XskRingConsumerReserve(&o.rx,16,&ri);
            if(n){
                if(XskRingProducerReserve(&o.fill,n,&fi)!=n)throw 3;
                for(UINT32 i=0;i<n;++i){
                    auto* d=static_cast<XSK_BUFFER_DESCRIPTOR*>(XskRingGetElement(&o.rx,ri+i));
                    const auto* p=o.umem+d->Address.BaseAddress+d->Address.Offset;
                    const UINT32 off=14+((p[14]&15)*4);
                    if(d->Length>=off+20 && p[12]==8 && p[13]==0 && p[23]==6 && !std::memcmp(p+30,&local.sin_addr,4) &&
                       (unsigned(p[off+2])<<8|p[off+3])==OwnedPort){
                        UINT16 source=UINT16(unsigned(p[off])<<8|p[off+1]);sources.insert(source);
                        std::printf("OWNED_RX source_port=%u flags=%02x\n",source,p[off+13]);
                    }else{++foreign;}
                    *static_cast<UINT64*>(XskRingGetElement(&o.fill,fi+i))=d->Address.BaseAddress;
                }
                total+=n;XskRingConsumerRelease(&o.rx,n);XskRingProducerSubmit(&o.fill,n);
                if(XskRingProducerNeedPoke(&o.fill))check("fill poke",XskNotifySocket(o.xsk,XSK_NOTIFY_FLAG_POKE_RX,0,&flags));
            }else{
                // Short wait only in this mixed kernel-socket/ring fixture.
                // Product RX will use one existing async wait set.
                XskNotifySocket(o.xsk,XSK_NOTIFY_FLAG_WAIT_RX,100,&flags);
            }
        }
        std::printf("OWNED_RX=%u SOURCE_PORTS=%zu FOREIGN_RX=%u ORDINARY_TCP=%u\n",total,sources.size(),foreign,ordinary);
        return sources.size()>=2 && foreign==0 && ordinary==1?0:7;
    }catch(int e){return 10+e;}
}
