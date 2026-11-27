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
// Original NPF sends <=16 ready frames/64KiB. XDP is asynchronous:
// outage 31612-30590=1022 outstanding; one maximal Normal turn
// 32 fresh + 40 parity + 4 controls + 1 ACK = 77. Power-of-two
// ceil(1022+77)=2048, not a substitute for completion credit.
constexpr UINT32 Slots=2048, Chunk=4096, Batch=16;
#ifdef WBD_XDP_PRESSURE_LAB
// Test DLL only. Resolve cold knobs once, no getenv or clock on each frame.
UINT32 lab_value(const char* name,UINT32 fallback,UINT32 a,UINT32 b,UINT32 c){
    char raw[16]{};
    DWORD n=GetEnvironmentVariableA(name,raw,sizeof(raw));
    if(!n||n>=sizeof(raw))return fallback;
    UINT32 v=0;
    for(DWORD i=0;i<n;++i){if(raw[i]<'0'||raw[i]>'9')return fallback;v=v*10+UINT32(raw[i]-'0');}
    return v==a||v==b||v==c?v:fallback;
}
#endif
struct TxOwner {
    HANDLE socket,completion_event;
    XDP_OVERLAPPED completion_ov;
    bool completion_pending;
    unsigned char* umem;
    XSK_RING tx,completion;
    UINT64 free_chunks[Slots];
    UINT32 free_count,reserved_index,reserved_count;
    UINT64 published,completed,pokes,credit_limited,completion_waits;
    bool reported;
#ifdef WBD_XDP_PRESSURE_LAB
    UINT32 slots,peak_pending,peak_unreclaimed;
    UINT64 samples,zero_credit,partial_credit,credit_calls;
#endif
};
bool reclaim(TxOwner* o,bool poke=true) {
    UINT32 index;
    UINT32 n=XskRingConsumerReserve(&o->completion,Slots,&index);
    for(UINT32 i=0;i<n;++i)
        o->free_chunks[o->free_count++]=*static_cast<UINT64*>(XskRingGetElement(&o->completion,index+i));
    if(n){
        XskRingConsumerRelease(&o->completion,n);o->completed+=n;
        // The SDK explicitly requires a poke on completion consumption
        // when NEED_POKE is set, even if no new frame will be published.
        if(poke&&XskRingProducerNeedPoke(&o->tx)){
            XSK_NOTIFY_RESULT_FLAGS result{};++o->pokes;
            HRESULT hr=XskNotifySocket(o->socket,XSK_NOTIFY_FLAG_POKE_TX,0,&result);
            if(FAILED(hr)){std::fprintf(stderr,"WBD_XDP_TX_COMPLETION_POKE_FAILED hr=0x%08lx\n",(unsigned long)hr);return false;}
        }
    }
    return true;
}
void close_owner(TxOwner* o){
    if(o->completion_pending){
        CancelIoEx(o->socket,&o->completion_ov);
        WaitForSingleObject(o->completion_event,INFINITE);
    }
    if(o->socket)CloseHandle(o->socket);
    if(o->completion_event)CloseHandle(o->completion_event);
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
static TxOwner* open_tx(DWORD ifindex,UINT32 slots,XSK_BIND_FLAGS mode,HRESULT* result){
    auto* o=static_cast<TxOwner*>(HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,sizeof(TxOwner)));
    if(!o){*result=E_OUTOFMEMORY;return nullptr;}
    HRESULT status=E_OUTOFMEMORY;
    XSK_UMEM_REG reg{};
    XSK_RING_INFO_SET info{};
    UINT32 size=sizeof(info);
    o->umem=static_cast<unsigned char*>(VirtualAlloc(nullptr,slots*Chunk,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
    if(!o->umem)goto fail;
    status=XskCreate(&o->socket);if(FAILED(status))goto fail;
    reg.TotalSize=slots*Chunk;reg.ChunkSize=Chunk;reg.Address=o->umem;
    status=XskSetSockopt(o->socket,XSK_SOCKOPT_UMEM_REG,&reg,sizeof(reg));if(FAILED(status))goto fail;
    // Generic is the explicit first comparison on WSL vEthernet.
    status=XskBind(o->socket,ifindex,0,XSK_BIND_FLAG_TX|mode);if(FAILED(status))goto fail;
    status=XskSetSockopt(o->socket,XSK_SOCKOPT_TX_RING_SIZE,&slots,sizeof(slots));if(FAILED(status))goto fail;
    status=XskSetSockopt(o->socket,XSK_SOCKOPT_TX_COMPLETION_RING_SIZE,&slots,sizeof(slots));if(FAILED(status))goto fail;
    status=XskActivate(o->socket,XSK_ACTIVATE_FLAG_NONE);if(FAILED(status))goto fail;
    status=XskGetSockopt(o->socket,XSK_SOCKOPT_RING_INFO,&info,&size);if(FAILED(status))goto fail;
    XskRingInitialize(&o->tx,&info.Tx);XskRingInitialize(&o->completion,&info.Completion);
    for(UINT32 i=0;i<slots;++i)o->free_chunks[i]=UINT64(i)*Chunk;
    o->free_count=slots;
#ifdef WBD_XDP_PRESSURE_LAB
    o->slots=slots;
#endif
    *result=S_OK;return o;
fail:
    *result=status;close_owner(o);return nullptr;
}
extern "C" void* wbd_xdp_tx_open_index(DWORD ifindex){
    HRESULT status;
    auto* o=open_tx(ifindex,Slots,XSK_BIND_FLAG_GENERIC,&status);
    if(o)std::fprintf(stderr,"WBD_XDP_TX_READY ifindex=%lu queue=0 slots=%u chunk=%u provider=generic\n",ifindex,Slots,Chunk);
    else std::fprintf(stderr,"WBD_XDP_TX_OPEN_FAILED ifindex=%lu hr=0x%08lx\n",ifindex,(unsigned long)status);
    return o;
}
extern "C" void* wbd_xdp_tx_open(const unsigned char* ip,const unsigned char* mac){
    DWORD ifindex=physical_index(ip,mac);
    if(!ifindex){std::fprintf(stderr,"WBD_XDP_TX no physical IP/MAC match\n");return nullptr;}
    return wbd_xdp_tx_open_index(ifindex);
}
// A single producer owns every free chunk. Completion can only ADD
// credit; publication is the sole operation consuming it. No lock,
// queue, wait or IOCTL in the sufficient-credit case.
extern "C" int wbd_xdp_tx_credit(void* raw,UINT32 wanted){
    auto* o=static_cast<TxOwner*>(raw);
    if(o->free_count<wanted&&!reclaim(o))return -1;
    if(o->free_count<wanted){
        ++o->credit_limited;
        if(XskRingError(&o->tx)||XskRingError(&o->completion))return -1;
    }
#ifdef WBD_XDP_PRESSURE_LAB
    if(!o->free_count)++o->zero_credit;
    else if(o->free_count<wanted)++o->partial_credit;
    if((++o->credit_calls&255)==0){
        ++o->samples;
        UINT32 ready=ReadUInt32Acquire(o->completion.SharedProducer)-*o->completion.SharedConsumer;
        UINT32 outstanding=o->slots-o->free_count;
        UINT32 pending=outstanding>ready?outstanding-ready:0;
        if(pending>o->peak_pending)o->peak_pending=pending;
        if(outstanding>o->peak_unreclaimed)o->peak_unreclaimed=outstanding;
    }
#endif
    return static_cast<int>(o->free_count<wanted?o->free_count:wanted);
}
// WAIT_TX signals available completion descriptors, not remote ACK.
// Only a credit-starved worker arms this event; the original Stop/
// Direct/owner events still share its WAIT_ANY set.
extern "C" uintptr_t wbd_xdp_tx_completion_event(void* raw){
    auto* o=static_cast<TxOwner*>(raw);
    if(!o->completion_event){
        o->completion_event=CreateEventW(nullptr,TRUE,FALSE,nullptr);
        if(!o->completion_event)return 0;
    }
    if(o->completion_pending){
        DWORD state=WaitForSingleObject(o->completion_event,0);
        if(state==WAIT_TIMEOUT)return reinterpret_cast<uintptr_t>(o->completion_event);
        if(state!=WAIT_OBJECT_0)return 0;
        XSK_NOTIFY_RESULT_FLAGS result{};
        HRESULT hr=XskGetNotifyAsyncResult(&o->completion_ov,&result);
        o->completion_pending=false;
        if(FAILED(hr))return 0;
    }
    if(XskRingError(&o->tx)||XskRingError(&o->completion))return 0;
    ResetEvent(o->completion_event);
    o->completion_ov={};o->completion_ov.hEvent=o->completion_event;
    XSK_NOTIFY_FLAGS flags=XSK_NOTIFY_FLAG_WAIT_TX;
    // Official SDK requires a poke after reclaim as well as publish
    // whenever TX is marked NEED_POKE.
    if(XskRingProducerNeedPoke(&o->tx)){
        flags=static_cast<XSK_NOTIFY_FLAGS>(flags|XSK_NOTIFY_FLAG_POKE_TX);
        ++o->pokes;
    }
    ++o->completion_waits;
    HRESULT hr=XskNotifyAsync(o->socket,flags,&o->completion_ov);
    if(hr==HRESULT_FROM_WIN32(ERROR_IO_PENDING)){o->completion_pending=true;}
    else if(FAILED(hr)){std::fprintf(stderr,"WBD_XDP_TX_COMPLETION_NOTIFY_FAILED hr=0x%08lx\n",(unsigned long)hr);return 0;}
    else SetEvent(o->completion_event);
    return reinterpret_cast<uintptr_t>(o->completion_event);
}
extern "C" int wbd_xdp_tx_reserve(void* raw,size_t count,unsigned char** frames){
    auto* o=static_cast<TxOwner*>(raw);
    if(o->free_count<count&&!reclaim(o))return 0;
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
    reclaim(o,false);
#ifdef WBD_XDP_PRESSURE_LAB
    std::fprintf(stderr,"WBD_XDP_TX_LAB slots=%u samples=%llu peak_pending_sampled=%u peak_unreclaimed_sampled=%u credit_calls=%llu zero_credit=%llu partial_credit=%llu\n",o->slots,o->samples,o->peak_pending,o->peak_unreclaimed,o->credit_calls,o->zero_credit,o->partial_credit);
#endif
    XSK_STATISTICS stats{};UINT32 size=sizeof(stats);
    HRESULT hr=XskGetSockopt(o->socket,XSK_SOCKOPT_STATISTICS,&stats,&size);
    std::fprintf(stderr,"WBD_XDP_TX_STOP published=%llu completed_before_close=%llu pokes=%llu invalid=%llu stats_hr=0x%08lx credit_limited=%llu completion_waits=%llu\n",o->published,o->completed,o->pokes,stats.TxInvalidDescriptors,(unsigned long)hr,o->credit_limited,o->completion_waits);
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
// Per RSS queue, NOT divided across queues: one flow can hash to any
// one queue. Old NPF RX capture budget=16MiB per lane. NPF v1.88
// NPF_CAP_SIZE = sizeof(bpf_hdr) + caplen (20+14+1160=1194).
// floor(16MiB/1194)=14051 full-size frames; next power of two 16384.
// 2048-byte chunks retain the existing maximum IPv4+Ethernet coverage.
// This matches bulk/full-size capacity, not NPF's packed ACK-only capacity.
constexpr UINT32 RxSlots=16384,DnsSlots=16,MaxRxQueues=62,MaxPorts=4,RxChunk=2048;
struct RxQueue {
    HANDLE socket,event;
    bool pending;
    XDP_OVERLAPPED ov;
    unsigned char* umem;
    XSK_RING rx,fill;
    UINT64 received,batches,waits,received_bytes;
#ifdef WBD_XDP_PRESSURE_LAB
    UINT64 samples,max_hold_ticks;
    UINT32 peak_ready;
    LARGE_INTEGER held_at;
    bool sampled;
    bool pending_fast;
    UINT64 pending_skips,event_checks;
    UINT32 posted;
    UINT64 expanded_samples;
#endif
};
struct RxOwner {
    HANDLE program,map;
    SOCKET ports[MaxPorts];
    UINT32 port_count;
    bool wsa;
    RxQueue* queues;
    unsigned char* umem;
    UINT32 count,next,batch_queue,batch_index,batch_count;
#ifdef WBD_XDP_PRESSURE_LAB
    UINT32 quantum,slots;
    bool pooled;
    UINT32 pool_next,pool_total;
#endif
};
#ifdef WBD_XDP_PRESSURE_LAB
constexpr UINT32 PoolBase=512,PoolWarm=8192;
#endif
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
    for(UINT32 i=0;i<o->port_count;++i)if(o->ports[i]!=INVALID_SOCKET)closesocket(o->ports[i]);
    if(o->wsa)WSACleanup();
    HeapFree(GetProcessHeap(),0,o);
}
HRESULT rx_poke(RxQueue* q){
    XSK_NOTIFY_RESULT_FLAGS flags{};
    return XskNotifySocket(q->socket,XSK_NOTIFY_FLAG_POKE_RX,0,&flags);
}
HRESULT open_queue(RxQueue* q,DWORD index,UINT32 queue,UINT32 slots,XSK_BIND_FLAGS mode,UINT32 first,UINT32 initial,UINT32 total){
    HRESULT hr;
    XSK_UMEM_REG reg{};
    XSK_RING_INFO_SET info{};
    UINT32 size=sizeof(info),fi;
    q->event=CreateEventW(nullptr,TRUE,FALSE,nullptr);
    if(!q->event)return HRESULT_FROM_WIN32(GetLastError());
    q->ov.hEvent=q->event;
    hr=XskCreate(&q->socket);if(FAILED(hr))return hr;
    reg.TotalSize=UINT64(total)*RxChunk;reg.ChunkSize=RxChunk;reg.Address=q->umem;
    hr=XskSetSockopt(q->socket,XSK_SOCKOPT_UMEM_REG,&reg,sizeof(reg));if(FAILED(hr))return hr;
    hr=XskBind(q->socket,index,queue,XSK_BIND_FLAG_RX|mode);if(FAILED(hr))return hr;
    hr=XskSetSockopt(q->socket,XSK_SOCKOPT_RX_RING_SIZE,&slots,sizeof(slots));if(FAILED(hr))return hr;
    hr=XskSetSockopt(q->socket,XSK_SOCKOPT_RX_FILL_RING_SIZE,&slots,sizeof(slots));if(FAILED(hr))return hr;
    hr=XskActivate(q->socket,XSK_ACTIVATE_FLAG_NONE);if(FAILED(hr))return hr;
    hr=XskGetSockopt(q->socket,XSK_SOCKOPT_RING_INFO,&info,&size);if(FAILED(hr))return hr;
    XskRingInitialize(&q->rx,&info.Rx);XskRingInitialize(&q->fill,&info.Fill);
    if(XskRingProducerReserve(&q->fill,initial,&fi)!=initial)return E_FAIL;
    for(UINT32 i=0;i<initial;++i)*static_cast<UINT64*>(XskRingGetElement(&q->fill,fi+i))=UINT64(first+i)*RxChunk;
    XskRingProducerSubmit(&q->fill,initial);
#ifdef WBD_XDP_PRESSURE_LAB
    q->posted=initial;
#endif
    return rx_poke(q);
}
HRESULT arm_queue(RxQueue* q){
    XSK_NOTIFY_RESULT_FLAGS flags{};
    if(q->pending){
#ifdef WBD_XDP_PRESSURE_LAB
        // Negative fast path only. Actual event still owns result/rearm.
        if(q->pending_fast&&!HasOverlappedIoCompleted(&q->ov)){
            ++q->pending_skips;return S_OK;
        }
        ++q->event_checks;
#endif
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
static RxOwner* open_rx(DWORD index,const UINT16* ports,UINT32 port_count,BOOL udp,XSK_BIND_FLAGS mode,HRESULT* result){
    auto* o=static_cast<RxOwner*>(HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,sizeof(RxOwner)));
    if(!o){*result=E_OUTOFMEMORY;return nullptr;}
    o->port_count=port_count;
    for(UINT32 i=0;i<MaxPorts;++i)o->ports[i]=INVALID_SOCKET;
    UINT32 slots=udp?DnsSlots:RxSlots;
#ifdef WBD_XDP_PRESSURE_LAB
    if(!udp)slots=lab_value("WBD_XDP_LAB_RX",RxSlots,4096,8192,16384);
    o->slots=slots;
    o->quantum=udp?1:lab_value("WBD_XDP_LAB_QUANTUM",32,16,32,32);
    char policy[32]{};
    GetEnvironmentVariableA("WBD_XDP_LAB_POLICY",policy,sizeof(policy));
    const bool pending_fast=!udp&&port_count==1&&!std::strcmp(policy,"rx-pending");
#endif
    HRESULT hr=E_FAIL;
    WSADATA wd{};
    BOOL exclusive=TRUE;
    DWORD dual=0;
    sockaddr_in6 address{};address.sin6_family=AF_INET6;
    HANDLE adapter=nullptr;
    XDP_RSS_CAPABILITIES caps{};UINT32 capSize=sizeof(caps);
    XDP_HOOK_ID hook{XDP_HOOK_L2,XDP_HOOK_RX,XDP_HOOK_INSPECT};
    XDP_RULE rules[MaxPorts]{};
    XDP_CREATE_PROGRAM_FLAGS flags=mode==XSK_BIND_FLAG_NATIVE?XDP_CREATE_PROGRAM_FLAG_NATIVE:XDP_CREATE_PROGRAM_FLAG_GENERIC;
    // TCP_DST matches IPv4 and IPv6. One non-listening reservation owns
    // the port for the original cold generation on both families.
    if(WSAStartup(MAKEWORD(2,2),&wd))goto fail;
    o->wsa=true;
    for(UINT32 i=0;i<port_count;++i){
        address.sin6_port=htons(ports[i]);
        SOCKET p=socket(AF_INET6,udp?SOCK_DGRAM:SOCK_STREAM,udp?IPPROTO_UDP:IPPROTO_TCP);
        o->ports[i]=p;
        if(p==INVALID_SOCKET)goto fail;
        if(setsockopt(p,IPPROTO_IPV6,IPV6_V6ONLY,reinterpret_cast<const char*>(&dual),sizeof(dual))||
           setsockopt(p,SOL_SOCKET,SO_EXCLUSIVEADDRUSE,reinterpret_cast<const char*>(&exclusive),sizeof(exclusive))||
           bind(p,reinterpret_cast<sockaddr*>(&address),sizeof(address))){
            std::fprintf(stderr,"WBD_XDP_PORT_BIND_FAILED port=%u wsa=%d\n",ports[i],WSAGetLastError());goto fail;
        }
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
    {
        UINT32 backing=o->count*slots;
#ifdef WBD_XDP_PRESSURE_LAB
        o->pooled=!udp&&port_count==1&&o->count>1&&slots==RxSlots&&!std::strcmp(policy,"rx-pool");
        if(o->pooled){
            o->pool_next=o->count*PoolBase;
            o->pool_total=o->pool_next+2*(slots-PoolBase);
            backing=o->pool_total;
        }
#endif
        o->umem=static_cast<unsigned char*>(VirtualAlloc(nullptr,size_t(backing)*RxChunk,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
    }
    if(!o->queues||!o->umem){hr=E_OUTOFMEMORY;goto fail;}
    if(o->count>1){
        hr=XdpMapCreate(&o->map,XDP_MAP_TYPE_XSKMAP);if(FAILED(hr))goto fail;
        flags|=XDP_CREATE_PROGRAM_FLAG_ALL_QUEUES;
    }
    for(UINT32 i=0;i<o->count;++i){
        auto* q=&o->queues[i];
        UINT32 first=0,initial=slots,total=slots;
#ifdef WBD_XDP_PRESSURE_LAB
        q->pending_fast=pending_fast;
        if(o->pooled){q->umem=o->umem;first=i*PoolBase;initial=PoolBase;total=o->pool_total;}
        else
#endif
        q->umem=o->umem+size_t(i)*slots*RxChunk;
        hr=open_queue(q,index,i,slots,mode,first,initial,total);if(FAILED(hr))goto fail;
        if(o->map){hr=XdpMapInsert(o->map,&i,&q->socket);if(FAILED(hr))goto fail;}
    }
    for(UINT32 i=0;i<port_count;++i){
        auto& rule=rules[i];
        rule.Match=udp?XDP_MATCH_UDP_DST:XDP_MATCH_TCP_DST;
        rule.Pattern.Port=htons(ports[i]);
        rule.Action=XDP_PROGRAM_ACTION_REDIRECT;
        rule.Redirect.TargetType=o->map?XDP_REDIRECT_TARGET_TYPE_XSKMAP_BY_QUEUEID:XDP_REDIRECT_TARGET_TYPE_XSK;
        rule.Redirect.Target=o->map?o->map:o->queues[0].socket;
    }
    hr=XdpCreateProgram(index,&hook,0,flags,rules,port_count,&o->program);if(FAILED(hr))goto fail;
    *result=S_OK;return o;
fail:
    *result=hr;close_rx(o);return nullptr;
}
static bool provider_unavailable(HRESULT hr){
    // Official driver XskBind returns STATUS_NOT_FOUND when no matching
    // RX/TX hook provider exists, or STATUS_NOT_SUPPORTED for capabilities.
    return hr==HRESULT_FROM_WIN32(ERROR_NOT_FOUND)||
           hr==HRESULT_FROM_WIN32(ERROR_NOT_SUPPORTED)||
           hr==static_cast<HRESULT>(0xD0000225u)||
           hr==static_cast<HRESULT>(0xD00000BBu);
}
extern "C" int wbd_xdp_open_carrier(DWORD index,const UINT16* ports,UINT32 count,BOOL udp,void** handles){
    UINT32 tx_slots=udp?DnsSlots:Slots;
#ifdef WBD_XDP_PRESSURE_LAB
    if(!udp)tx_slots=lab_value("WBD_XDP_LAB_TX",Slots,1024,2048,2048);
#endif
    // Native when the actual interface supports both paths; Generic for
    // ordinary NIC/vEthernet. Never switch one half of an established pair.
    for(UINT32 attempt=0;attempt<2;++attempt){
        const auto mode=attempt==0?XSK_BIND_FLAG_NATIVE:XSK_BIND_FLAG_GENERIC;
        HRESULT status;
        auto* tx=open_tx(index,tx_slots,mode,&status);
        if(tx){
            auto* rx=open_rx(index,ports,count,udp,mode,&status);
            if(rx){
                const char* provider=attempt==0?"native":"generic";
                std::fprintf(stderr,"WBD_XDP_TX_READY ifindex=%lu queue=0 slots=%u chunk=%u provider=%s\n",index,tx_slots,Chunk,provider);
                std::fprintf(stderr,"WBD_XDP_RX_READY ifindex=%lu queues=%u port=%u ports=%u slots_per_queue=%u chunk=%u udp=%u provider=%s\n",index,rx->count,ports[0],count,rx->queues[0].rx.Size,RxChunk,unsigned(udp!=0),provider);
                handles[0]=rx;handles[1]=tx;return 1;
            }
            close_owner(tx);
        }
        if(attempt==0&&provider_unavailable(status)){
            std::fprintf(stderr,"WBD_XDP_NATIVE_UNAVAILABLE ifindex=%lu hr=0x%08lx\n",index,(unsigned long)status);
            continue;
        }
        std::fprintf(stderr,"WBD_XDP_CARRIER_OPEN_FAILED ifindex=%lu port=%u provider=%s hr=0x%08lx\n",index,ports[0],attempt==0?"native":"generic",(unsigned long)status);
        return 0;
    }
    return 0;
}
extern "C" size_t wbd_xdp_rx_borrow(void* raw,RxFrame* frames,size_t max){
    auto* o=static_cast<RxOwner*>(raw);
    UINT32 id=o->next;
#ifdef WBD_XDP_PRESSURE_LAB
    if(max>o->quantum)max=o->quantum;
#endif
    // One ready quantum per queue, no cross-queue copies or queued
    // intermediate packets. Empty queues cost only a ring index read.
    for(UINT32 scan=0;scan<o->count;++scan){
        auto* q=&o->queues[id];
        UINT32 n=XskRingConsumerReserve(&q->rx,static_cast<UINT32>(max),&o->batch_index);
        if(n){
            o->batch_queue=id;o->batch_count=n;
            o->next=id+1==o->count?0:id+1;
            UINT64 bytes=0;
            for(UINT32 i=0;i<n;++i){
                auto* d=static_cast<XSK_BUFFER_DESCRIPTOR*>(XskRingGetElement(&q->rx,o->batch_index+i));
                bytes+=d->Length;
                frames[i]={q->umem+d->Address.BaseAddress+d->Address.Offset,d->Length};
            }
            q->received+=n;q->received_bytes+=bytes;++q->batches;
#ifdef WBD_XDP_PRESSURE_LAB
            q->sampled=(q->batches&255)==0;
            if(q->sampled){
                ++q->samples;
                UINT32 ready=ReadUInt32Acquire(q->rx.SharedProducer)-*q->rx.SharedConsumer;
                if(ready>q->peak_ready)q->peak_ready=ready;
                if(o->pooled){
                    const auto* d=static_cast<XSK_BUFFER_DESCRIPTOR*>(XskRingGetElement(&q->rx,o->batch_index));
                    if(d->Address.BaseAddress>=UINT64(o->count)*PoolBase*RxChunk)++q->expanded_samples;
                }
                QueryPerformanceCounter(&q->held_at);
            }
#endif
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
#ifdef WBD_XDP_PRESSURE_LAB
    // Only the existing RX owner allocates never-posted offsets.
    UINT32 extra=0;
    if(o->pooled&&q->posted<o->slots&&o->pool_next<o->pool_total){
        UINT32 target=q->posted;
        if(q->posted==PoolBase&&q->received==n)target=PoolWarm;
        else if(n>=32&&ReadUInt32Acquire(q->rx.SharedProducer)-*q->rx.SharedConsumer>=q->posted/2)
            target=o->slots;
        extra=target-q->posted;
        const UINT32 unused=o->pool_total-o->pool_next;
        if(extra>unused)extra=unused;
    }
    if(XskRingProducerReserve(&q->fill,n+extra,&fi)!=n+extra)return 0;
#else
    if(XskRingProducerReserve(&q->fill,n,&fi)!=n)return 0;
#endif
    for(UINT32 i=0;i<n;++i){
        auto* d=static_cast<XSK_BUFFER_DESCRIPTOR*>(XskRingGetElement(&q->rx,o->batch_index+i));
        *static_cast<UINT64*>(XskRingGetElement(&q->fill,fi+i))=d->Address.BaseAddress;
    }
    XskRingConsumerRelease(&q->rx,n);
#ifdef WBD_XDP_PRESSURE_LAB
    for(UINT32 i=0;i<extra;++i)*static_cast<UINT64*>(XskRingGetElement(&q->fill,fi+n+i))=UINT64(o->pool_next+i)*RxChunk;
    o->pool_next+=extra;q->posted+=extra;
    XskRingProducerSubmit(&q->fill,n+extra);
    if(q->sampled){
        LARGE_INTEGER now;QueryPerformanceCounter(&now);
        UINT64 ticks=UINT64(now.QuadPart-q->held_at.QuadPart);
        if(ticks>q->max_hold_ticks)q->max_hold_ticks=ticks;
        q->sampled=false;
    }
#else
    XskRingProducerSubmit(&q->fill,n);
#endif
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
    UINT64 received=0,batches=0,waits=0,dropped=0,truncated=0,received_bytes=0;
    HRESULT result=S_OK;
#ifdef WBD_XDP_PRESSURE_LAB
    UINT64 pending_skips=0,event_checks=0,expanded_samples=0;
    UINT32 max_posted=0;
#endif
    for(UINT32 i=0;i<o->count;++i){
        auto* q=&o->queues[i];
        XSK_STATISTICS s{};UINT32 size=sizeof(s);
        HRESULT hr=XskGetSockopt(q->socket,XSK_SOCKOPT_STATISTICS,&s,&size);
        if(FAILED(hr))result=hr;
        received+=q->received;batches+=q->batches;waits+=q->waits;received_bytes+=q->received_bytes;
        dropped+=s.RxDropped;truncated+=s.RxTruncated;
#ifdef WBD_XDP_PRESSURE_LAB
        pending_skips+=q->pending_skips;event_checks+=q->event_checks;
        expanded_samples+=q->expanded_samples;
        if(q->posted>max_posted)max_posted=q->posted;
        if(q->received){
            LARGE_INTEGER frequency;QueryPerformanceFrequency(&frequency);
            UINT64 us=q->max_hold_ticks*1000000/frequency.QuadPart;
            std::fprintf(stderr,"WBD_XDP_RX_LAB queue=%u slots=%u quantum=%u samples=%llu peak_ready_sampled=%u max_batch_hold_sampled_us=%llu\n",i,o->slots,o->quantum,q->samples,q->peak_ready,us);
        }
#endif
        if(q->received||s.RxDropped||s.RxTruncated)
            std::fprintf(stderr,"WBD_XDP_RX_QUEUE_STOP queue=%u received=%llu batches=%llu waits=%llu dropped=%llu truncated=%llu received_bytes=%llu\n",i,q->received,q->batches,q->waits,s.RxDropped,s.RxTruncated,q->received_bytes);
    }
#ifdef WBD_XDP_PRESSURE_LAB
    if(o->port_count==1&&o->slots!=DnsSlots){
        std::fprintf(stderr,"WBD_XDP_RX_PENDING_LAB enabled=%u skipped=%llu event_checks=%llu\n",o->queues[0].pending_fast?1u:0u,pending_skips,event_checks);
        std::fprintf(stderr,"WBD_XDP_RX_POOL_STOP enabled=%u backing_bytes=%llu posted=%u max_queue_posted=%u expanded_samples=%llu reserve_remaining=%u\n",
            o->pooled?1u:0u,UINT64(o->pooled?o->pool_total:o->count*o->slots)*RxChunk,
            o->pooled?o->pool_next:o->count*o->slots,max_posted,expanded_samples,o->pooled?o->pool_total-o->pool_next:0);
    }
#endif
    std::fprintf(stderr,"WBD_XDP_RX_STOP received=%llu batches=%llu waits=%llu dropped=%llu truncated=%llu stats_hr=0x%08lx queues=%u received_bytes=%llu\n",received,batches,waits,dropped,truncated,(unsigned long)result,o->count,received_bytes);
    close_rx(o);
}
extern "C" int wbd_xdp_tx_cold_write(void* raw,const unsigned char* bytes,size_t len){
    unsigned char* dst=nullptr;
    if(len>Chunk||!wbd_xdp_tx_reserve(raw,1,&dst))return 0;
    std::memcpy(dst,bytes,len);
    return wbd_xdp_tx_publish(raw,&len);
}
// Cold-only actual v1.4 driver API readback; no interface bind.
extern "C" int wbd_xdp_driver_status(){
    HANDLE xsk=nullptr,map=nullptr;
    HRESULT hr=XskCreate(&xsk);
    if(FAILED(hr))return hr;
    hr=XdpMapCreate(&map,XDP_MAP_TYPE_XSKMAP);
    if(map)CloseHandle(map);
    CloseHandle(xsk);
    return hr;
}
#endif // WBD_XDP_NATIVE_TRIAL
