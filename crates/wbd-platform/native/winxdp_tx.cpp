// One TX owner, no extra thread, official XDP SDK v3 header-only IOCTLs.
// No protocol/packet encoding here. Rust writes the registered chunks.
#define XDP_API_VERSION 3
#define XDP_INCLUDE_WINCOMMON
#define NOMINMAX
#include <xdpapi.h>
#include <afxdp_helper.h>
#include <iphlpapi.h>
#include <ws2tcpip.h>
#include <cstdio>
#include <cstring>
#include <cstddef>

namespace {
constexpr UINT32 Slots=1024, Chunk=4096, Batch=16;
struct TxOwner {
    HANDLE socket;
    unsigned char* umem;
    XSK_RING tx,completion;
    UINT64 free_chunks[Slots];
    UINT32 free_count,reserved_index,reserved_count;
    UINT64 published,completed,pokes;
    bool reported;
};
void reclaim(TxOwner* o) {
    UINT32 index;
    UINT32 n=XskRingConsumerReserve(&o->completion,Slots,&index);
    for(UINT32 i=0;i<n;++i)
        o->free_chunks[o->free_count++]=*static_cast<UINT64*>(XskRingGetElement(&o->completion,index+i));
    if(n){XskRingConsumerRelease(&o->completion,n);o->completed+=n;}
}
void close_owner(TxOwner* o){
    if(o->socket)CloseHandle(o->socket);
    if(o->umem)VirtualFree(o->umem,0,MEM_RELEASE);
    HeapFree(GetProcessHeap(),0,o);
}
// Resolve the original physical flow identity, not the Wintun ifindex.
DWORD physical_index(const unsigned char* ip,const unsigned char* mac){
    ULONG size=0;
    if(GetIpAddrTable(nullptr,&size,FALSE)!=ERROR_INSUFFICIENT_BUFFER)return 0;
    auto* table=static_cast<MIB_IPADDRTABLE*>(HeapAlloc(GetProcessHeap(),0,size));
    if(!table)return 0;
    DWORD result=0,address;
    std::memcpy(&address,ip,4);
    if(GetIpAddrTable(table,&size,FALSE)==NO_ERROR){
        for(DWORD i=0;i<table->dwNumEntries;++i){
            if(table->table[i].dwAddr!=address)continue;
            MIB_IFROW row{};row.dwIndex=table->table[i].dwIndex;
            if(GetIfEntry(&row)==NO_ERROR&&row.dwPhysAddrLen==6&&!std::memcmp(row.bPhysAddr,mac,6)){
                result=row.dwIndex;break;
            }
        }
    }
    HeapFree(GetProcessHeap(),0,table);
    return result;
}
}
extern "C" void* wbd_xdp_tx_open_index(DWORD ifindex){
    auto* o=static_cast<TxOwner*>(HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,sizeof(TxOwner)));
    if(!o)return nullptr;
    HRESULT status=E_OUTOFMEMORY;
    XSK_UMEM_REG reg{};
    XSK_RING_INFO_SET info{};
    UINT32 size=sizeof(info);
    o->umem=static_cast<unsigned char*>(VirtualAlloc(nullptr,Slots*Chunk,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
    if(!o->umem)goto fail;
    status=XskCreate(&o->socket);if(FAILED(status))goto fail;
    reg.TotalSize=Slots*Chunk;reg.ChunkSize=Chunk;reg.Address=o->umem;
    status=XskSetSockopt(o->socket,XSK_SOCKOPT_UMEM_REG,&reg,sizeof(reg));if(FAILED(status))goto fail;
    // Generic is the explicit first comparison on WSL vEthernet.
    status=XskBind(o->socket,ifindex,0,XSK_BIND_FLAG_TX|XSK_BIND_FLAG_GENERIC);if(FAILED(status))goto fail;
    status=XskSetSockopt(o->socket,XSK_SOCKOPT_TX_RING_SIZE,&Slots,sizeof(Slots));if(FAILED(status))goto fail;
    status=XskSetSockopt(o->socket,XSK_SOCKOPT_TX_COMPLETION_RING_SIZE,&Slots,sizeof(Slots));if(FAILED(status))goto fail;
    status=XskActivate(o->socket,XSK_ACTIVATE_FLAG_NONE);if(FAILED(status))goto fail;
    status=XskGetSockopt(o->socket,XSK_SOCKOPT_RING_INFO,&info,&size);if(FAILED(status))goto fail;
    XskRingInitialize(&o->tx,&info.Tx);XskRingInitialize(&o->completion,&info.Completion);
    for(UINT32 i=0;i<Slots;++i)o->free_chunks[i]=UINT64(i)*Chunk;
    o->free_count=Slots;
    std::fprintf(stderr,"WBD_XDP_TX_READY ifindex=%lu queue=0 slots=%u chunk=%u\n",ifindex,Slots,Chunk);
    return o;
fail:
    std::fprintf(stderr,"WBD_XDP_TX_OPEN_FAILED ifindex=%lu hr=0x%08lx\n",ifindex,(unsigned long)status);
    close_owner(o);return nullptr;
}
extern "C" void* wbd_xdp_tx_open(const unsigned char* ip,const unsigned char* mac){
    DWORD ifindex=physical_index(ip,mac);
    if(!ifindex){std::fprintf(stderr,"WBD_XDP_TX no physical IP/MAC match\n");return nullptr;}
    return wbd_xdp_tx_open_index(ifindex);
}
extern "C" int wbd_xdp_tx_reserve(void* raw,size_t count,unsigned char** frames){
    auto* o=static_cast<TxOwner*>(raw);
    reclaim(o);
    if(count>Batch||count>o->free_count||
       XskRingProducerReserve(&o->tx,static_cast<UINT32>(count),&o->reserved_index)!=count){
        std::fprintf(stderr,"WBD_XDP_TX_RING_FULL requested=%zu free=%u published=%llu completed=%llu\n",count,o->free_count,o->published,o->completed);
        return 0;
    }
    o->reserved_count=static_cast<UINT32>(count);
    for(UINT32 i=0;i<count;++i)frames[i]=o->umem+o->free_chunks[o->free_count-1-i];
    return 1;
}
// Once published, chunks are driver-owned until completion. Poke failure is
// reported separately from the published prefix; never return them as unsent.
extern "C" int wbd_xdp_tx_publish(void* raw,const size_t* lengths){
    auto* o=static_cast<TxOwner*>(raw);
    UINT32 n=o->reserved_count;
    for(UINT32 i=0;i<n;++i){
        auto* d=static_cast<XSK_BUFFER_DESCRIPTOR*>(XskRingGetElement(&o->tx,o->reserved_index+i));
        d->Address.AddressAndOffset=o->free_chunks[--o->free_count];
        d->Length=static_cast<UINT32>(lengths[i]);d->Reserved=0;
    }
    XskRingProducerSubmit(&o->tx,n);o->published+=n;o->reserved_count=0;
    if(XskRingProducerNeedPoke(&o->tx)){
        XSK_NOTIFY_RESULT_FLAGS result{};++o->pokes;
        HRESULT hr=XskNotifySocket(o->socket,XSK_NOTIFY_FLAG_POKE_TX,0,&result);
        if(FAILED(hr)){std::fprintf(stderr,"WBD_XDP_TX_POKE_FAILED hr=0x%08lx\n",(unsigned long)hr);return 0;}
    }
    return 1;
}
extern "C" void wbd_xdp_tx_report(void* raw){
    auto* o=static_cast<TxOwner*>(raw);
    if(o->reported)return;
    o->reported=true;
    reclaim(o);
    XSK_STATISTICS stats{};UINT32 size=sizeof(stats);
    HRESULT hr=XskGetSockopt(o->socket,XSK_SOCKOPT_STATISTICS,&stats,&size);
    std::fprintf(stderr,"WBD_XDP_TX_STOP published=%llu completed_before_close=%llu pokes=%llu invalid=%llu stats_hr=0x%08lx\n",o->published,o->completed,o->pokes,stats.TxInvalidDescriptors,(unsigned long)hr);
}
extern "C" void wbd_xdp_tx_close(void* raw){
    wbd_xdp_tx_report(raw);
    // Socket close relinquishes all kernel references before UMEM is freed.
    close_owner(static_cast<TxOwner*>(raw));
}

// Same cold and steady RX rings. No software queue, no new thread.
// Each descriptor's chunk is returned to Fill only after the Rust batch
// loan is dropped. The cold Go reader copies into its existing decoder.
namespace {
constexpr UINT32 RxSlots=1024,RxBatch=32;
struct RxOwner {
    HANDLE socket,program,event;
    SOCKET port;
    bool wsa,pending;
    XDP_OVERLAPPED ov;
    unsigned char* umem;
    XSK_RING rx,fill;
    UINT32 batch_index,batch_count;
    UINT64 received,batches,waits;
};
struct RxFrame { const unsigned char* data; size_t len; };
void close_rx(RxOwner* o){
    if(o->program)CloseHandle(o->program);
    if(o->pending){
        CancelIoEx(o->socket,&o->ov);
        WaitForSingleObject(o->event,INFINITE);
        o->pending=false;
    }
    if(o->socket)CloseHandle(o->socket);
    if(o->event)CloseHandle(o->event);
    if(o->umem)VirtualFree(o->umem,0,MEM_RELEASE);
    if(o->port!=INVALID_SOCKET)closesocket(o->port);
    if(o->wsa)WSACleanup();
    HeapFree(GetProcessHeap(),0,o);
}
HRESULT rx_poke(RxOwner* o){
    XSK_NOTIFY_RESULT_FLAGS flags{};
    return XskNotifySocket(o->socket,XSK_NOTIFY_FLAG_POKE_RX,0,&flags);
}
}
extern "C" void* wbd_xdp_rx_open(DWORD index,UINT16 port){
    auto* o=static_cast<RxOwner*>(HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,sizeof(RxOwner)));
    if(!o)return nullptr;
    o->port=INVALID_SOCKET;
    HRESULT hr=E_FAIL;
    WSADATA wd{};
    BOOL exclusive=TRUE;
    DWORD dual=0;
    sockaddr_in6 address{};address.sin6_family=AF_INET6;address.sin6_port=htons(port);
    XSK_UMEM_REG reg{};
    XSK_RING_INFO_SET info{};
    UINT32 size=sizeof(info),fi;
    XDP_HOOK_ID hook{XDP_HOOK_L2,XDP_HOOK_RX,XDP_HOOK_INSPECT};
    XDP_RULE rule{};
    // TCP_DST matches IPv4 and IPv6. Reserve this port on both families
    // once, rather than intercept another application on the same port.
    // Never listen/connect; WBD's original cold TCP bytes are unchanged.
    if(WSAStartup(MAKEWORD(2,2),&wd))goto fail;
    o->wsa=true;
    o->port=socket(AF_INET6,SOCK_STREAM,IPPROTO_TCP);
    if(o->port==INVALID_SOCKET)goto fail;
    if(setsockopt(o->port,IPPROTO_IPV6,IPV6_V6ONLY,reinterpret_cast<const char*>(&dual),sizeof(dual))||
       setsockopt(o->port,SOL_SOCKET,SO_EXCLUSIVEADDRUSE,reinterpret_cast<const char*>(&exclusive),sizeof(exclusive))||
       bind(o->port,reinterpret_cast<sockaddr*>(&address),sizeof(address))){
        std::fprintf(stderr,"WBD_XDP_PORT_BIND_FAILED port=%u wsa=%d\n",port,WSAGetLastError());goto fail;
    }
    o->event=CreateEventW(nullptr,TRUE,FALSE,nullptr);
    if(!o->event)goto fail;
    o->ov.hEvent=o->event;
    o->umem=static_cast<unsigned char*>(VirtualAlloc(nullptr,RxSlots*Chunk,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
    if(!o->umem)goto fail;
    hr=XskCreate(&o->socket);if(FAILED(hr))goto fail;
    reg.TotalSize=RxSlots*Chunk;reg.ChunkSize=Chunk;reg.Address=o->umem;
    hr=XskSetSockopt(o->socket,XSK_SOCKOPT_UMEM_REG,&reg,sizeof(reg));if(FAILED(hr))goto fail;
    hr=XskBind(o->socket,index,0,XSK_BIND_FLAG_RX|XSK_BIND_FLAG_GENERIC);if(FAILED(hr))goto fail;
    hr=XskSetSockopt(o->socket,XSK_SOCKOPT_RX_RING_SIZE,&RxSlots,sizeof(RxSlots));if(FAILED(hr))goto fail;
    hr=XskSetSockopt(o->socket,XSK_SOCKOPT_RX_FILL_RING_SIZE,&RxSlots,sizeof(RxSlots));if(FAILED(hr))goto fail;
    hr=XskActivate(o->socket,XSK_ACTIVATE_FLAG_NONE);if(FAILED(hr))goto fail;
    hr=XskGetSockopt(o->socket,XSK_SOCKOPT_RING_INFO,&info,&size);if(FAILED(hr))goto fail;
    XskRingInitialize(&o->rx,&info.Rx);XskRingInitialize(&o->fill,&info.Fill);
    if(XskRingProducerReserve(&o->fill,RxSlots,&fi)!=RxSlots){hr=E_FAIL;goto fail;}
    for(UINT32 i=0;i<RxSlots;++i)*static_cast<UINT64*>(XskRingGetElement(&o->fill,fi+i))=UINT64(i)*Chunk;
    XskRingProducerSubmit(&o->fill,RxSlots);
    rule.Match=XDP_MATCH_TCP_DST;rule.Pattern.Port=htons(port);
    rule.Action=XDP_PROGRAM_ACTION_REDIRECT;rule.Redirect.TargetType=XDP_REDIRECT_TARGET_TYPE_XSK;rule.Redirect.Target=o->socket;
    hr=XdpCreateProgram(index,&hook,0,XDP_CREATE_PROGRAM_FLAG_GENERIC,&rule,1,&o->program);if(FAILED(hr))goto fail;
    hr=rx_poke(o);if(FAILED(hr))goto fail;
    std::fprintf(stderr,"WBD_XDP_RX_READY ifindex=%lu queue=0 port=%u slots=%u chunk=%u\n",index,port,RxSlots,Chunk);
    return o;
fail:
    std::fprintf(stderr,"WBD_XDP_RX_OPEN_FAILED ifindex=%lu port=%u hr=0x%08lx\n",index,port,(unsigned long)hr);
    close_rx(o);return nullptr;
}
extern "C" size_t wbd_xdp_rx_borrow(void* raw,RxFrame* frames,size_t max){
    auto* o=static_cast<RxOwner*>(raw);
    UINT32 n=XskRingConsumerReserve(&o->rx,static_cast<UINT32>(max),&o->batch_index);
    o->batch_count=n;
    for(UINT32 i=0;i<n;++i){
        auto* d=static_cast<XSK_BUFFER_DESCRIPTOR*>(XskRingGetElement(&o->rx,o->batch_index+i));
        frames[i]={o->umem+d->Address.BaseAddress+d->Address.Offset,d->Length};
    }
    if(n){o->received+=n;++o->batches;}
    return n;
}
extern "C" int wbd_xdp_rx_release(void* raw){
    auto* o=static_cast<RxOwner*>(raw);
    UINT32 n=o->batch_count,fi;
    if(!n)return 1;
    if(XskRingProducerReserve(&o->fill,n,&fi)!=n)return 0;
    for(UINT32 i=0;i<n;++i){
        auto* d=static_cast<XSK_BUFFER_DESCRIPTOR*>(XskRingGetElement(&o->rx,o->batch_index+i));
        *static_cast<UINT64*>(XskRingGetElement(&o->fill,fi+i))=d->Address.BaseAddress;
    }
    XskRingConsumerRelease(&o->rx,n);XskRingProducerSubmit(&o->fill,n);
    o->batch_count=0;
    return !XskRingProducerNeedPoke(&o->fill)||SUCCEEDED(rx_poke(o));
}
// Existing Rust wait set consumes this one overlapped event; Direct and
// Stop can wake it without canceling/reissuing an outstanding notify.
extern "C" HANDLE wbd_xdp_rx_arm(void* raw){
    auto* o=static_cast<RxOwner*>(raw);
    XSK_NOTIFY_RESULT_FLAGS flags{};
    if(o->pending){
        if(WaitForSingleObject(o->event,0)!=WAIT_OBJECT_0)return o->event;
        HRESULT hr=XskGetNotifyAsyncResult(&o->ov,&flags);
        o->pending=false;
        if(FAILED(hr))return nullptr;
    }
    ResetEvent(o->event);
    o->ov={};o->ov.hEvent=o->event;
    ++o->waits;
    HRESULT hr=XskNotifyAsync(o->socket,XSK_NOTIFY_FLAG_WAIT_RX,&o->ov);
    if(hr==HRESULT_FROM_WIN32(ERROR_IO_PENDING)){o->pending=true;return o->event;}
    if(FAILED(hr))return nullptr;
    SetEvent(o->event);return o->event;
}
// Bounded cold-only receive. No outstanding async operation on handoff.
extern "C" int wbd_xdp_rx_cold_read(void* raw,unsigned char* dst,size_t cap){
    auto* o=static_cast<RxOwner*>(raw);
    RxFrame f{};
    if(!wbd_xdp_rx_borrow(o,&f,1)){
        XSK_NOTIFY_RESULT_FLAGS flags{};
        HRESULT hr=XskNotifySocket(o->socket,XSK_NOTIFY_FLAG_WAIT_RX,50,&flags);
        if(hr==HRESULT_FROM_WIN32(ERROR_TIMEOUT)||hr==HRESULT_FROM_WIN32(WAIT_TIMEOUT))return 0;
        if(FAILED(hr))return -1;
        if(!wbd_xdp_rx_borrow(o,&f,1))return 0;
    }
    int n=f.len<=cap?static_cast<int>(f.len):-1;
    if(n>0)std::memcpy(dst,f.data,f.len);
    return wbd_xdp_rx_release(o)?n:-1;
}
extern "C" void wbd_xdp_rx_close(void* raw){
    auto* o=static_cast<RxOwner*>(raw);
    XSK_STATISTICS s{};UINT32 size=sizeof(s);
    HRESULT hr=XskGetSockopt(o->socket,XSK_SOCKOPT_STATISTICS,&s,&size);
    std::fprintf(stderr,"WBD_XDP_RX_STOP received=%llu batches=%llu waits=%llu dropped=%llu truncated=%llu stats_hr=0x%08lx\n",o->received,o->batches,o->waits,s.RxDropped,s.RxTruncated,(unsigned long)hr);
    close_rx(o);
}
extern "C" int wbd_xdp_tx_cold_write(void* raw,const unsigned char* bytes,size_t len){
    unsigned char* dst=nullptr;
    if(len>Chunk||!wbd_xdp_tx_reserve(raw,1,&dst))return 0;
    std::memcpy(dst,bytes,len);
    return wbd_xdp_tx_publish(raw,&len);
}

