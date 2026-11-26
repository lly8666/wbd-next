// Same real guest source-port roster in each arm. XDP 1.4 stock TCP_DST
// and XSKMAP, no eBPF, one RX loop across per-queue rings.
#define XDP_API_VERSION 3
#define XDP_INCLUDE_WINCOMMON
#define NOMINMAX
#include <xdpapi.h>
#include <xdpapi_experimental.h>
#include <afxdp_helper.h>
#include <ws2tcpip.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <set>
#include <vector>
#include <memory>

constexpr UINT32 Slots=256,Chunk=2048,ProbeLimit=61;
constexpr UINT16 OwnedPort=39463,OrdinaryPort=39464,FirstSource=39500,Flows=32;
static void check(const char* op,HRESULT hr){
    if(FAILED(hr)){std::fprintf(stderr,"%s hr=0x%08lx\n",op,(unsigned long)hr);throw 1;}
}
struct Queue{
    HANDLE socket=nullptr,event=nullptr;
    XDP_OVERLAPPED ov{};
    bool pending=false;
    unsigned char* umem=nullptr;
    XSK_RING rx{},fill{};
    std::set<UINT16> sources;
    UINT32 frames=0;
    ~Queue(){
        if(pending){CancelIoEx(socket,&ov);WaitForSingleObject(event,INFINITE);}
        if(socket)CloseHandle(socket);
        if(event)CloseHandle(event);
        if(umem)VirtualFree(umem,0,MEM_RELEASE);
    }
    HRESULT open(UINT32 index,UINT32 id){
        HRESULT hr=XskCreate(&socket);if(FAILED(hr))return hr;
        umem=static_cast<unsigned char*>(VirtualAlloc(nullptr,Slots*Chunk,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));
        if(!umem)return E_OUTOFMEMORY;
        XSK_UMEM_REG reg{};reg.TotalSize=Slots*Chunk;reg.ChunkSize=Chunk;reg.Address=umem;
        check("UMEM",XskSetSockopt(socket,XSK_SOCKOPT_UMEM_REG,&reg,sizeof(reg)));
        hr=XskBind(socket,index,id,XSK_BIND_FLAG_RX|XSK_BIND_FLAG_GENERIC);
        if(FAILED(hr))return hr;
        check("RX",XskSetSockopt(socket,XSK_SOCKOPT_RX_RING_SIZE,&Slots,sizeof(Slots)));
        check("Fill",XskSetSockopt(socket,XSK_SOCKOPT_RX_FILL_RING_SIZE,&Slots,sizeof(Slots)));
        // Some providers reject the unavailable queue at activation.
        hr=XskActivate(socket,XSK_ACTIVATE_FLAG_NONE);
        if(FAILED(hr))return hr;
        XSK_RING_INFO_SET info{};UINT32 size=sizeof(info),fi;
        check("ring info",XskGetSockopt(socket,XSK_SOCKOPT_RING_INFO,&info,&size));
        XskRingInitialize(&rx,&info.Rx);XskRingInitialize(&fill,&info.Fill);
        if(XskRingProducerReserve(&fill,Slots,&fi)!=Slots)throw 2;
        for(UINT32 i=0;i<Slots;++i)*static_cast<UINT64*>(XskRingGetElement(&fill,fi+i))=UINT64(i)*Chunk;
        XskRingProducerSubmit(&fill,Slots);
        XSK_NOTIFY_RESULT_FLAGS flags{};check("poke fill",XskNotifySocket(socket,XSK_NOTIFY_FLAG_POKE_RX,0,&flags));
        event=CreateEventW(nullptr,TRUE,FALSE,nullptr);if(!event)throw 2;
        return S_OK;
    }
    void arm(){
        XSK_NOTIFY_RESULT_FLAGS flags{};
        if(pending){
            if(WaitForSingleObject(event,0)!=WAIT_OBJECT_0)return;
            check("notify result",XskGetNotifyAsyncResult(&ov,&flags));
            pending=false;
        }
        ResetEvent(event);ov={};ov.hEvent=event;
        HRESULT hr=XskNotifyAsync(socket,XSK_NOTIFY_FLAG_WAIT_RX,&ov);
        if(hr==HRESULT_FROM_WIN32(ERROR_IO_PENDING)){pending=true;return;}
        check("notify",hr);SetEvent(event);
    }
    UINT32 drain(const IN_ADDR& ip,std::set<UINT16>& seen){
        UINT32 ri,fi,foreign=0;
        UINT32 n=XskRingConsumerReserve(&rx,32,&ri);
        if(!n)return 0;
        if(XskRingProducerReserve(&fill,n,&fi)!=n)throw 2;
        for(UINT32 i=0;i<n;++i){
            auto* d=static_cast<XSK_BUFFER_DESCRIPTOR*>(XskRingGetElement(&rx,ri+i));
            const auto* p=umem+d->Address.BaseAddress+d->Address.Offset;
            if(d->Length>=54&&p[12]==8&&p[13]==0&&p[23]==6){
                UINT32 off=14+((p[14]&15)*4);
                if(d->Length>=off+20&&!std::memcmp(p+30,&ip,4)&&
                   (unsigned(p[off+2])<<8|p[off+3])==OwnedPort&&(p[off+13]&2)){
                    UINT16 source=UINT16(unsigned(p[off])<<8|p[off+1]);
                    if(source>=FirstSource&&source<FirstSource+Flows){sources.insert(source);seen.insert(source);}
                    else ++foreign;
                }else ++foreign;
            }else ++foreign;
            *static_cast<UINT64*>(XskRingGetElement(&fill,fi+i))=d->Address.BaseAddress;
        }
        frames+=n;XskRingConsumerRelease(&rx,n);XskRingProducerSubmit(&fill,n);
        if(XskRingProducerNeedPoke(&fill)){XSK_NOTIFY_RESULT_FLAGS flags{};check("fill",XskNotifySocket(socket,XSK_NOTIFY_FLAG_POKE_RX,0,&flags));}
        return foreign;
    }
};
struct Owner{
    HANDLE prog=nullptr,map=nullptr,accept_event=nullptr;
    SOCKET reservation=INVALID_SOCKET,listener=INVALID_SOCKET;
    std::vector<std::unique_ptr<Queue>> queues;
    ~Owner(){
        if(prog)CloseHandle(prog);if(map)CloseHandle(map);
        queues.clear();
        if(listener!=INVALID_SOCKET)closesocket(listener);
        if(accept_event)WSACloseEvent(accept_event);
        if(reservation!=INVALID_SOCKET)closesocket(reservation);
    }
};
int main(int argc,char**argv){
    if(argc!=5)return 2;
    WSADATA w{};if(WSAStartup(MAKEWORD(2,2),&w))return 2;
    try{
        Owner o;
        UINT32 index=std::strtoul(argv[1],nullptr,10),expected=std::strtoul(argv[4],nullptr,10);
        bool all=!std::strcmp(argv[3],"all");
        sockaddr_in local{};local.sin_family=AF_INET;local.sin_port=htons(OrdinaryPort);
        if(InetPtonA(AF_INET,argv[2],&local.sin_addr)!=1)return 2;
        // Match TCP_DST on both families, own the local port once.
        o.reservation=socket(AF_INET6,SOCK_STREAM,IPPROTO_TCP);
        DWORD dual=0;BOOL exclusive=TRUE;
        sockaddr_in6 bound{};bound.sin6_family=AF_INET6;bound.sin6_port=htons(OwnedPort);
        if(o.reservation==INVALID_SOCKET||setsockopt(o.reservation,IPPROTO_IPV6,IPV6_V6ONLY,(char*)&dual,sizeof(dual))||
           setsockopt(o.reservation,SOL_SOCKET,SO_EXCLUSIVEADDRUSE,(char*)&exclusive,sizeof(exclusive))||
           bind(o.reservation,(sockaddr*)&bound,sizeof(bound)))return 3;
        o.listener=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);
        if(o.listener==INVALID_SOCKET||bind(o.listener,(sockaddr*)&local,sizeof(local))||listen(o.listener,2))return 3;
        o.accept_event=WSACreateEvent();
        if(WSAEventSelect(o.listener,o.accept_event,FD_ACCEPT))return 3;
        if(all)check("map",XdpMapCreate(&o.map,XDP_MAP_TYPE_XSKMAP));
        // Use the same capability query that ALL_QUEUES uses internally.
        // Bind/Activate success does not prove a live RSS queue exists.
        HANDLE adapter=nullptr;
        check("interface open",XdpInterfaceOpen(index,&adapter));
        XDP_RSS_CAPABILITIES caps{};UINT32 capSize=sizeof(caps);
        HRESULT capStatus=XdpRssGetCapabilities(adapter,&caps,&capSize);
        CloseHandle(adapter);check("rss capabilities",capStatus);
        UINT32 count=caps.NumberOfReceiveQueues?caps.NumberOfReceiveQueues:1;
        std::printf("XDP_RSS_CAP_QUEUE_COUNT=%u os=%u hash_types=%u\n",count,expected,caps.HashTypes);
        if(count>=ProbeLimit){std::fprintf(stderr,"wait set probe requires fewer than %u queues\n",ProbeLimit);return 4;}
        const UINT32 limit=all?count:1;
        for(UINT32 q=0;q<limit;++q){
            auto v=std::make_unique<Queue>();
            check("queue open",v->open(index,q));
            if(all)check("map insert",XdpMapInsert(o.map,&q,&v->socket));
            o.queues.push_back(std::move(v));
        }
        XDP_HOOK_ID hook{XDP_HOOK_L2,XDP_HOOK_RX,XDP_HOOK_INSPECT};
        XDP_RULE rule{};rule.Match=XDP_MATCH_TCP_DST;rule.Pattern.Port=htons(OwnedPort);
        rule.Action=XDP_PROGRAM_ACTION_REDIRECT;
        rule.Redirect.TargetType=all?XDP_REDIRECT_TARGET_TYPE_XSKMAP_BY_QUEUEID:XDP_REDIRECT_TARGET_TYPE_XSK;
        rule.Redirect.Target=all?o.map:o.queues[0]->socket;
        auto flags=all?XDP_CREATE_PROGRAM_FLAG_GENERIC|XDP_CREATE_PROGRAM_FLAG_ALL_QUEUES:XDP_CREATE_PROGRAM_FLAG_GENERIC;
        check("program",XdpCreateProgram(index,&hook,0,flags,&rule,1,&o.prog));
        std::vector<HANDLE> events{o.accept_event};
        for(auto& q:o.queues){events.push_back(q->event);q->arm();}
        std::printf("READY mode=%s queues=%zu expected_os=%u\n",argv[3],o.queues.size(),expected);std::fflush(stdout);
        std::set<UINT16> seen;UINT32 ordinary=0,foreign=0;
        ULONGLONG deadline=GetTickCount64()+11000;
        while(GetTickCount64()<deadline&&(seen.size()<Flows||ordinary==0)){
            for(auto& q:o.queues){foreign+=q->drain(local.sin_addr,seen);q->arm();}
            WSANETWORKEVENTS ne{};
            if(WaitForSingleObject(o.accept_event,0)==WAIT_OBJECT_0){
                WSAEnumNetworkEvents(o.listener,o.accept_event,&ne);
                SOCKET peer=accept(o.listener,nullptr,nullptr);
                if(peer!=INVALID_SOCKET){
                    const char ok[]="ORDINARY_TCP_OK";
                    if(send(peer,ok,sizeof(ok)-1,0)==sizeof(ok)-1)++ordinary;
                    closesocket(peer);
                }
            }
            if(seen.size()<Flows||ordinary==0)WaitForMultipleObjects(static_cast<DWORD>(events.size()),events.data(),FALSE,1000);
        }
        for(size_t i=0;i<o.queues.size();++i){
            auto& q=*o.queues[i];
            std::printf("QUEUE=%zu frames=%u distinct=%zu sources=",i,q.frames,q.sources.size());
            for(auto s:q.sources)std::printf("%u,",s);
            std::printf("\n");
        }
        std::printf("RSS_RESULT mode=%s total_distinct=%zu expected=%u foreign=%u ordinary=%u queues=%zu\n",argv[3],seen.size(),Flows,foreign,ordinary,o.queues.size());
        return foreign==0&&ordinary==1&&(!all||seen.size()==Flows)?0:7;
    }catch(int e){return 10+e;}
}
