// One TX owner, no extra thread, official XDP SDK v3 header-only IOCTLs.
// No protocol/packet encoding here. Rust writes the registered chunks.
#define XDP_API_VERSION 3
#define XDP_INCLUDE_WINCOMMON
#define NOMINMAX
#include <xdpapi.h>
#include <afxdp_helper.h>
#include <iphlpapi.h>
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
extern "C" void* wbd_xdp_tx_open(const unsigned char* ip,const unsigned char* mac){
    DWORD ifindex=physical_index(ip,mac);
    if(!ifindex){std::fprintf(stderr,"WBD_XDP_TX no physical IP/MAC match\n");return nullptr;}
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
extern "C" void wbd_xdp_tx_close(void* raw){
    auto* o=static_cast<TxOwner*>(raw);
    reclaim(o);
    XSK_STATISTICS stats{};UINT32 size=sizeof(stats);
    HRESULT hr=XskGetSockopt(o->socket,XSK_SOCKOPT_STATISTICS,&stats,&size);
    std::fprintf(stderr,"WBD_XDP_TX_STOP published=%llu completed_before_close=%llu pokes=%llu invalid=%llu stats_hr=0x%08lx\n",o->published,o->completed,o->pokes,stats.TxInvalidDescriptors,(unsigned long)hr);
    // Socket close relinquishes all kernel references before UMEM is freed.
    close_owner(o);
}
