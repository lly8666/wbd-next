// M0 WinXDP carrier qualification. Not the WBD wire protocol or product path.
// SDK header-only API; RX->TX reuses the exact same registered chunk.
#define XDP_API_VERSION 3
#include <xdpapi.h>
#include <afxdp_helper.h>
#include <cstdio>
#include <cstdlib>
#include <algorithm>
#include <utility>
#include <memory>
#include <cstdint>

constexpr UINT32 RingSize=256, Chunk=2048, Target=64, Batch=16;
struct Owner {
    HANDLE socket=nullptr, program=nullptr;
    unsigned char* umem=nullptr;
    XSK_RING rx{}, fill{}, tx{}, completion{};
    ~Owner(){
        if(program) CloseHandle(program);
        if(socket) CloseHandle(socket);
        if(umem) VirtualFree(umem,0,MEM_RELEASE);
    }
};
static void check(const char* name, XDP_STATUS status) {
    if(XDP_FAILED(status)){
        std::fprintf(stderr,"%s: 0x%08lx\n",name,(unsigned long)status);
        throw 1;
    }
}
static void swap_bytes(unsigned char* a,unsigned char* b,unsigned n) {
    for(unsigned i=0;i<n;++i) std::swap(a[i],b[i]);
}
// Fixture-only UDP echo, never used for product packets. Recompute IPv4
// checksum; IPv4 UDP checksum zero is legal for this dedicated test traffic.
static bool reflect(unsigned char* p,UINT32 n,UINT16 port) {
    if(n<42||p[12]!=8||p[13]!=0||p[14]!=0x45||p[23]!=17) return false;
    if((unsigned(p[36])<<8|p[37])!=port) return false;
    swap_bytes(p,p+6,6); swap_bytes(p+26,p+30,4); swap_bytes(p+34,p+36,2);
    p[24]=p[25]=p[40]=p[41]=0;
    unsigned sum=0;
    for(unsigned i=14;i<34;i+=2) sum+=(unsigned(p[i])<<8)|p[i+1];
    while(sum>>16) sum=(sum&65535)+(sum>>16);
    unsigned c=(~sum)&65535; p[24]=static_cast<unsigned char>(c>>8); p[25]=static_cast<unsigned char>(c);
    return true;
}
int main(int argc,char** argv) {
    if(argc!=4)return 2;
    UINT32 ifindex=std::strtoul(argv[1],nullptr,10), queue=std::strtoul(argv[2],nullptr,10);
    UINT16 port=static_cast<UINT16>(std::strtoul(argv[3],nullptr,10));
    try {
        Owner o;
        o.umem=static_cast<unsigned char*>(VirtualAlloc(nullptr,RingSize*Chunk,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));
        if(!o.umem)return 3;
        check("XskCreate",XskCreate(&o.socket));
        XSK_UMEM_REG reg{}; reg.TotalSize=RingSize*Chunk;reg.ChunkSize=Chunk;reg.Address=o.umem;
        check("UMEM",XskSetSockopt(o.socket,XSK_SOCKOPT_UMEM_REG,&reg,sizeof(reg)));
        check("generic RX/TX bind",XskBind(o.socket,ifindex,queue,XSK_BIND_FLAG_RX|XSK_BIND_FLAG_TX|XSK_BIND_FLAG_GENERIC));
        for(UINT32 option:{XSK_SOCKOPT_RX_RING_SIZE,XSK_SOCKOPT_RX_FILL_RING_SIZE,XSK_SOCKOPT_TX_RING_SIZE,XSK_SOCKOPT_TX_COMPLETION_RING_SIZE})
            check("ring size",XskSetSockopt(o.socket,option,&RingSize,sizeof(RingSize)));
        check("activate",XskActivate(o.socket,XSK_ACTIVATE_FLAG_NONE));
        XSK_RING_INFO_SET info{};UINT32 size=sizeof(info);
        check("ring info",XskGetSockopt(o.socket,XSK_SOCKOPT_RING_INFO,&info,&size));
        XskRingInitialize(&o.rx,&info.Rx);XskRingInitialize(&o.fill,&info.Fill);
        XskRingInitialize(&o.tx,&info.Tx);XskRingInitialize(&o.completion,&info.Completion);
        UINT32 start=0;
        if(XskRingProducerReserve(&o.fill,RingSize,&start)!=RingSize)return 4;
        for(UINT32 i=0;i<RingSize;++i)*static_cast<UINT64*>(XskRingGetElement(&o.fill,start+i))=UINT64(i)*Chunk;
        XskRingProducerSubmit(&o.fill,RingSize);
        // Only the dedicated disposable fixture port, no general interception.
        XDP_HOOK_ID hook{XDP_HOOK_L2,XDP_HOOK_RX,XDP_HOOK_INSPECT};
        XDP_RULE rule{};rule.Match=XDP_MATCH_UDP_DST;rule.Pattern.Port=static_cast<UINT16>((port<<8)|(port>>8));
        rule.Action=XDP_PROGRAM_ACTION_REDIRECT;rule.Redirect.TargetType=XDP_REDIRECT_TARGET_TYPE_XSK;rule.Redirect.Target=o.socket;
        check("redirect",XdpCreateProgram(ifindex,&hook,queue,XDP_CREATE_PROGRAM_FLAG_GENERIC,&rule,1,&o.program));
        XSK_NOTIFY_RESULT_FLAGS flags{};
        check("initial fill poke",XskNotifySocket(o.socket,XSK_NOTIFY_FLAG_POKE_RX,0,&flags));
        std::printf("READY ifindex=%u queue=%u generic=1 chunk=%u ring=%u\n",ifindex,queue,Chunk,RingSize);std::fflush(stdout);
        UINT32 received=0, completed=0, rx_batches=0, tx_pokes=0;
        ULONGLONG deadline=GetTickCount64()+30000;
        while(completed<Target && GetTickCount64()<deadline){
            UINT32 ci,fi,ri,ti;
            UINT32 cn=XskRingConsumerReserve(&o.completion,Batch,&ci);
            if(cn){
                cn=XskRingProducerReserve(&o.fill,cn,&fi);
                for(UINT32 i=0;i<cn;++i)*static_cast<UINT64*>(XskRingGetElement(&o.fill,fi+i))=*static_cast<UINT64*>(XskRingGetElement(&o.completion,ci+i));
                XskRingConsumerRelease(&o.completion,cn);XskRingProducerSubmit(&o.fill,cn);completed+=cn;
                if(XskRingProducerNeedPoke(&o.fill))check("fill poke",XskNotifySocket(o.socket,XSK_NOTIFY_FLAG_POKE_RX,0,&flags));
            }
            UINT32 rn=XskRingConsumerReserve(&o.rx,(std::min)(Batch,Target-received),&ri);
            rn=XskRingProducerReserve(&o.tx,rn,&ti);
            if(rn){
                for(UINT32 i=0;i<rn;++i){
                    auto* r=static_cast<XSK_BUFFER_DESCRIPTOR*>(XskRingGetElement(&o.rx,ri+i));
                    auto* t=static_cast<XSK_BUFFER_DESCRIPTOR*>(XskRingGetElement(&o.tx,ti+i));
                    if(!reflect(o.umem+r->Address.BaseAddress+r->Address.Offset,r->Length,port))throw 1;
                    *t=*r;
                }
                XskRingConsumerRelease(&o.rx,rn);XskRingProducerSubmit(&o.tx,rn);
                received+=rn;++rx_batches;
                if(XskRingProducerNeedPoke(&o.tx)){check("TX poke",XskNotifySocket(o.socket,XSK_NOTIFY_FLAG_POKE_TX,0,&flags));++tx_pokes;}
            }
            if(!rn&&!cn&&completed<Target){
                XSK_NOTIFY_FLAGS wait=received==Target?XSK_NOTIFY_FLAG_WAIT_TX:XSK_NOTIFY_FLAG_WAIT_RX;
                if(received>completed)wait|=XSK_NOTIFY_FLAG_WAIT_TX;
                auto status=XskNotifySocket(o.socket,wait,1000,&flags);
                if(XDP_FAILED(status)&&status!=HRESULT_FROM_WIN32(ERROR_TIMEOUT)&&status!=HRESULT_FROM_WIN32(WAIT_TIMEOUT))check("wait",status);
            }
        }
        XSK_STATISTICS stats{};size=sizeof(stats);
        check("statistics",XskGetSockopt(o.socket,XSK_SOCKOPT_STATISTICS,&stats,&size));
        std::printf("RX=%u TX_COMPLETION=%u RX_BATCHES=%u TX_POKES=%u RX_DROPPED=%llu RX_TRUNCATED=%llu TX_INVALID=%llu\n",received,completed,rx_batches,tx_pokes,stats.RxDropped,stats.RxTruncated,stats.TxInvalidDescriptors);
        return received==Target&&completed==Target&&!stats.RxTruncated&&!stats.TxInvalidDescriptors?0:5;
    }catch(int){return 6;}
}
