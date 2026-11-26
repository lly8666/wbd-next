// One TX owner, no extra thread, official XDP SDK v3 header-only IOCTLs.
// No protocol/packet encoding here. Rust writes the registered chunks.
#define XDP_API_VERSION 3
#define XDP_INCLUDE_WINCOMMON
#define NOMINMAX
#include <xdpapi.h>
#ifdef WBD_XDP_NATIVE_TRIAL
#include <xdpapi_experimental.h>
#endif
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

#ifdef WBD_XDP_NATIVE_TRIAL
// One interface RX owner, original cold/steady handoff, no extra worker.
// Queue-local registered slices of one preallocated region keep each
// producer/consumer ownership independent without copying frames.
namespace {
constexpr UINT32 RxSlots=1024,RxBatch=32,MaxRxQueues=62;
struct RxQueue {
    HANDLE socket,event;
    bool pending;
    XDP_OVERLAPPED ov;
    unsigned char* umem;
    XSK_RING rx,fill;
    UINT64 received,batches,waits;
};
struct RxOwner {
    HANDLE program,map;
    SOCKET port;
    bool wsa;
    RxQueue* queues;
    unsigned char* umem;
    UINT32 count,next,batch_queue,batch_index,batch_count;
};
struct RxFrame { const unsigned char* data; size_t len; };
void close_rx(RxOwner* o){
    if(o->program)CloseHandle(o->program);
    if(o->map)CloseHandle(o->map);
    if(o->queues){
        for(UINT32 i=0;i<o->count;++i){
            auto* q=&o->queues[i];
            if(q->pending){
                CancelIoEx(q->socket,&q->ov);
                WaitForSingleObject(q->event,INFINITE);
            }
            if(q->socket)CloseHandle(q->socket);
            if(q->event)CloseHandle(q->event);
        }
        HeapFree(GetProcessHeap(),0,o->queues);
    }
    if(o->umem)VirtualFree(o->umem,0,MEM_RELEASE);
    if(o->port!=INVALID_SOCKET)closesocket(o->port);
    if(o->wsa)WSACleanup();
    HeapFree(GetProcessHeap(),0,o);
}
HRESULT rx_poke(RxQueue* q){
    XSK_NOTIFY_RESULT_FLAGS flags{};
    return XskNotifySocket(q->socket,XSK_NOTIFY_FLAG_POKE_RX,0,&flags);
}
HRESULT open_queue(RxQueue* q,DWORD index,UINT32 queue){
    HRESULT hr;
    XSK_UMEM_REG reg{};
    XSK_RING_INFO_SET info{};
    UINT32 size=sizeof(info),fi;
    q->event=CreateEventW(nullptr,TRUE,FALSE,nullptr);
    if(!q->event)return HRESULT_FROM_WIN32(GetLastError());
    q->ov.hEvent=q->event;
    hr=XskCreate(&q->socket);if(FAILED(hr))return hr;
    reg.TotalSize=RxSlots*Chunk;reg.ChunkSize=Chunk;reg.Address=q->umem;
    hr=XskSetSockopt(q->socket,XSK_SOCKOPT_UMEM_REG,&reg,sizeof(reg));if(FAILED(hr))return hr;
    hr=XskBind(q->socket,index,queue,XSK_BIND_FLAG_RX|XSK_BIND_FLAG_GENERIC);if(FAILED(hr))return hr;
    hr=XskSetSockopt(q->socket,XSK_SOCKOPT_RX_RING_SIZE,&RxSlots,sizeof(RxSlots));if(FAILED(hr))return hr;
    hr=XskSetSockopt(q->socket,XSK_SOCKOPT_RX_FILL_RING_SIZE,&RxSlots,sizeof(RxSlots));if(FAILED(hr))return hr;
    hr=XskActivate(q->socket,XSK_ACTIVATE_FLAG_NONE);if(FAILED(hr))return hr;
    hr=XskGetSockopt(q->socket,XSK_SOCKOPT_RING_INFO,&info,&size);if(FAILED(hr))return hr;
    XskRingInitialize(&q->rx,&info.Rx);XskRingInitialize(&q->fill,&info.Fill);
    if(XskRingProducerReserve(&q->fill,RxSlots,&fi)!=RxSlots)return E_FAIL;
    for(UINT32 i=0;i<RxSlots;++i)*static_cast<UINT64*>(XskRingGetElement(&q->fill,fi+i))=UINT64(i)*Chunk;
    XskRingProducerSubmit(&q->fill,RxSlots);
    return rx_poke(q);
}
HRESULT arm_queue(RxQueue* q){
    XSK_NOTIFY_RESULT_FLAGS flags{};
    if(q->pending){
        if(WaitForSingleObject(q->event,0)!=WAIT_OBJECT_0)return S_OK;
        HRESULT hr=XskGetNotifyAsyncResult(&q->ov,&flags);
        q->pending=false;
        if(FAILED(hr))return hr;
    }
    ResetEvent(q->event);
    q->ov={};q->ov.hEvent=q->event;
    ++q->waits;
    HRESULT hr=XskNotifyAsync(q->socket,XSK_NOTIFY_FLAG_WAIT_RX,&q->ov);
    if(hr==HRESULT_FROM_WIN32(ERROR_IO_PENDING)){q->pending=true;return S_OK;}
    if(FAILED(hr))return hr;
    SetEvent(q->event);return S_OK;
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
    HANDLE adapter=nullptr;
    XDP_RSS_CAPABILITIES caps{};UINT32 capSize=sizeof(caps);
    XDP_HOOK_ID hook{XDP_HOOK_L2,XDP_HOOK_RX,XDP_HOOK_INSPECT};
    XDP_RULE rule{};
    XDP_CREATE_PROGRAM_FLAGS flags=XDP_CREATE_PROGRAM_FLAG_GENERIC;
    // TCP_DST matches IPv4 and IPv6. One non-listening reservation owns
    // the port for the original cold generation on both families.
    if(WSAStartup(MAKEWORD(2,2),&wd))goto fail;
    o->wsa=true;
    o->port=socket(AF_INET6,SOCK_STREAM,IPPROTO_TCP);
    if(o->port==INVALID_SOCKET)goto fail;
    if(setsockopt(o->port,IPPROTO_IPV6,IPV6_V6ONLY,reinterpret_cast<const char*>(&dual),sizeof(dual))||
       setsockopt(o->port,SOL_SOCKET,SO_EXCLUSIVEADDRUSE,reinterpret_cast<const char*>(&exclusive),sizeof(exclusive))||
       bind(o->port,reinterpret_cast<sockaddr*>(&address),sizeof(address))){
        std::fprintf(stderr,"WBD_XDP_PORT_BIND_FAILED port=%u wsa=%d\n",port,WSAGetLastError());goto fail;
    }
    // This is the same RSS capability source used by ALL_QUEUES in the
    // official driver. Socket bind success alone is NOT queue inventory.
    hr=XdpInterfaceOpen(index,&adapter);if(FAILED(hr))goto fail;
    hr=XdpRssGetCapabilities(adapter,&caps,&capSize);
    CloseHandle(adapter);adapter=nullptr;if(FAILED(hr))goto fail;
    o->count=caps.NumberOfReceiveQueues?caps.NumberOfReceiveQueues:1;
    // Original worker waits on two additional Stop/Direct handles.
    // Explicit scope of this candidate; never silently omit real queues.
    if(o->count>MaxRxQueues){hr=HRESULT_FROM_WIN32(ERROR_NOT_SUPPORTED);goto fail;}
    o->queues=static_cast<RxQueue*>(HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,sizeof(RxQueue)*o->count));
    o->umem=static_cast<unsigned char*>(VirtualAlloc(nullptr,size_t(o->count)*RxSlots*Chunk,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
    if(!o->queues||!o->umem){hr=E_OUTOFMEMORY;goto fail;}
    if(o->count>1){
        hr=XdpMapCreate(&o->map,XDP_MAP_TYPE_XSKMAP);if(FAILED(hr))goto fail;
        flags|=XDP_CREATE_PROGRAM_FLAG_ALL_QUEUES;
    }
    for(UINT32 i=0;i<o->count;++i){
        auto* q=&o->queues[i];
        q->umem=o->umem+size_t(i)*RxSlots*Chunk;
        hr=open_queue(q,index,i);if(FAILED(hr))goto fail;
        if(o->map){hr=XdpMapInsert(o->map,&i,&q->socket);if(FAILED(hr))goto fail;}
    }
    rule.Match=XDP_MATCH_TCP_DST;rule.Pattern.Port=htons(port);
    rule.Action=XDP_PROGRAM_ACTION_REDIRECT;
    rule.Redirect.TargetType=o->map?XDP_REDIRECT_TARGET_TYPE_XSKMAP_BY_QUEUEID:XDP_REDIRECT_TARGET_TYPE_XSK;
    rule.Redirect.Target=o->map?o->map:o->queues[0].socket;
    hr=XdpCreateProgram(index,&hook,0,flags,&rule,1,&o->program);if(FAILED(hr))goto fail;
    std::fprintf(stderr,"WBD_XDP_RX_READY ifindex=%lu queues=%u port=%u slots_per_queue=%u chunk=%u\n",index,o->count,port,RxSlots,Chunk);
    return o;
fail:
    std::fprintf(stderr,"WBD_XDP_RX_OPEN_FAILED ifindex=%lu port=%u queues=%u hr=0x%08lx\n",index,port,o->count,(unsigned long)hr);
    close_rx(o);return nullptr;
}
extern "C" size_t wbd_xdp_rx_borrow(void* raw,RxFrame* frames,size_t max){
    auto* o=static_cast<RxOwner*>(raw);
    UINT32 id=o->next;
    // One ready quantum per queue, no cross-queue copies or queued
    // intermediate packets. Empty queues cost only a ring index read.
    for(UINT32 scan=0;scan<o->count;++scan){
        auto* q=&o->queues[id];
        UINT32 n=XskRingConsumerReserve(&q->rx,static_cast<UINT32>(max),&o->batch_index);
        if(n){
            o->batch_queue=id;o->batch_count=n;
            o->next=id+1==o->count?0:id+1;
            for(UINT32 i=0;i<n;++i){
                auto* d=static_cast<XSK_BUFFER_DESCRIPTOR*>(XskRingGetElement(&q->rx,o->batch_index+i));
                frames[i]={q->umem+d->Address.BaseAddress+d->Address.Offset,d->Length};
            }
            q->received+=n;++q->batches;
            return n;
        }
        if(++id==o->count)id=0;
    }
    o->batch_count=0;return 0;
}
extern "C" int wbd_xdp_rx_release(void* raw){
    auto* o=static_cast<RxOwner*>(raw);
    auto* q=&o->queues[o->batch_queue];
    UINT32 n=o->batch_count,fi;
    if(!n)return 1;
    if(XskRingProducerReserve(&q->fill,n,&fi)!=n)return 0;
    for(UINT32 i=0;i<n;++i){
        auto* d=static_cast<XSK_BUFFER_DESCRIPTOR*>(XskRingGetElement(&q->rx,o->batch_index+i));
        *static_cast<UINT64*>(XskRingGetElement(&q->fill,fi+i))=d->Address.BaseAddress;
    }
    XskRingConsumerRelease(&q->rx,n);XskRingProducerSubmit(&q->fill,n);
    o->batch_count=0;
    return !XskRingProducerNeedPoke(&q->fill)||SUCCEEDED(rx_poke(q));
}
// Only called after the worker finds no ready descriptors. Pending waits
// on other queues survive a wake, including the original Go→Rust handoff.
extern "C" int wbd_xdp_rx_events(void* raw,HANDLE* events){
    auto* o=static_cast<RxOwner*>(raw);
    for(UINT32 i=0;i<o->count;++i){
        auto* q=&o->queues[i];
        HRESULT hr=arm_queue(q);
        if(FAILED(hr)){std::fprintf(stderr,"WBD_XDP_RX_NOTIFY_FAILED queue=%u hr=0x%08lx\n",i,(unsigned long)hr);return -1;}
        events[i]=q->event;
    }
    return static_cast<int>(o->count);
}
// Cold calls borrow the same per-queue descriptors, one at a time for the
// existing Go decoder. The bounded wait owns no Go pointer, and all native
// overlapped events remain valid in the same owner after reader join.
extern "C" int wbd_xdp_rx_cold_read(void* raw,unsigned char* dst,size_t cap){
    RxFrame f{};
    if(!wbd_xdp_rx_borrow(raw,&f,1)){
        HANDLE events[MaxRxQueues];
        int n=wbd_xdp_rx_events(raw,events);
        if(n<=0)return -1;
        DWORD status=WaitForMultipleObjects(static_cast<DWORD>(n),events,FALSE,50);
        if(status==WAIT_TIMEOUT)return 0;
        if(status==WAIT_FAILED)return -1;
        if(!wbd_xdp_rx_borrow(raw,&f,1))return 0;
    }
    int n=f.len<=cap?static_cast<int>(f.len):-1;
    if(n>0)std::memcpy(dst,f.data,f.len);
    return wbd_xdp_rx_release(raw)?n:-1;
}
extern "C" void wbd_xdp_rx_close(void* raw){
    auto* o=static_cast<RxOwner*>(raw);
    UINT64 received=0,batches=0,waits=0,dropped=0,truncated=0;
    HRESULT result=S_OK;
    for(UINT32 i=0;i<o->count;++i){
        auto* q=&o->queues[i];
        XSK_STATISTICS s{};UINT32 size=sizeof(s);
        HRESULT hr=XskGetSockopt(q->socket,XSK_SOCKOPT_STATISTICS,&s,&size);
        if(FAILED(hr))result=hr;
        received+=q->received;batches+=q->batches;waits+=q->waits;
        dropped+=s.RxDropped;truncated+=s.RxTruncated;
        if(q->received||s.RxDropped||s.RxTruncated)
            std::fprintf(stderr,"WBD_XDP_RX_QUEUE_STOP queue=%u received=%llu batches=%llu waits=%llu dropped=%llu truncated=%llu\n",i,q->received,q->batches,q->waits,s.RxDropped,s.RxTruncated);
    }
    std::fprintf(stderr,"WBD_XDP_RX_STOP received=%llu batches=%llu waits=%llu dropped=%llu truncated=%llu stats_hr=0x%08lx queues=%u\n",received,batches,waits,dropped,truncated,(unsigned long)result,o->count);
    close_rx(o);
}
extern "C" int wbd_xdp_tx_cold_write(void* raw,const unsigned char* bytes,size_t len){
    unsigned char* dst=nullptr;
    if(len>Chunk||!wbd_xdp_tx_reserve(raw,1,&dst))return 0;
    std::memcpy(dst,bytes,len);
    return wbd_xdp_tx_publish(raw,&len);
}
#endif // WBD_XDP_NATIVE_TRIAL
