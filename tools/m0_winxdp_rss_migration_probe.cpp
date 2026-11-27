// Real Generic XDP carrier with the exact product RX implementation.
// Controlled raw TCP-shaped test packets are NOT a WBD protocol session.
#define WBD_XDP_NATIVE_TRIAL
#define WBD_XDP_PRESSURE_LAB
#include "../crates/wbd-platform/native/winxdp_tx.cpp"
#include <fstream>
#include <filesystem>
#include <map>
#include <vector>
#include <set>
#include <string>
#include <stdexcept>
namespace fs=std::filesystem;
static const UINT16 TestPort=39463;
static fs::path root;
static unsigned command=0;
static void require(bool ok,const char* msg){if(!ok)throw std::runtime_error(msg);}
static UINT32 be32(const unsigned char* p){return (UINT32(p[0])<<24)|(UINT32(p[1])<<16)|(UINT32(p[2])<<8)|p[3];}
static void request(unsigned port,unsigned n){
    ++command;
    auto tmp=root/"request.tmp";
    {std::ofstream f(tmp);f<<command<<" "<<port<<" "<<n<<"\n";require(bool(f),"write request");}
    fs::rename(tmp,root/("request-"+std::to_string(command)));
    const auto end=GetTickCount64()+15000;
    auto done=root/("done-"+std::to_string(command));
    while(!fs::exists(done)){require(GetTickCount64()<end,"guest command timeout");Sleep(1);}
    unsigned count=0;std::ifstream f(done);f>>count;require(count==n,"guest send count");
}
static UINT32 free_count(RxOwner* o){return o->pool_total-o->pool_next+o->free_count;}
static void account(RxOwner* o){
    UINT32 sum=free_count(o);
    for(UINT32 i=0;i<o->count;++i)sum+=o->queues[i].posted;
    require(sum==(o->pooled?o->pool_total:o->count*o->slots),"pool accounting");
}
// Do not infer the actual RSS hash from source ports. Read real RX queue IDs.
static void batch(RxOwner* o,unsigned port,unsigned count,std::map<unsigned,unsigned>& mapping){
    request(port,count);
    std::set<UINT32> seen;
    const auto deadline=GetTickCount64()+3000;
    while(seen.size()<count&&GetTickCount64()<deadline){
        RxFrame f[32];const auto n=wbd_xdp_rx_borrow(o,f,32);
        if(!n){Sleep(1);continue;}
        for(size_t i=0;i<n;++i){
            const auto* p=f[i].data;
            require(f[i].len>=66&&p[12]==8&&p[13]==0&&p[23]==6,"unexpected frame");
            const size_t t=14+(p[14]&15)*4;
            require(f[i].len>=t+20,"tcp header");
            const size_t payload=t+(p[t+12]>>4)*4;
            require(f[i].len>=payload+12&&be32(p+payload)==0x57424450,"probe payload");
            unsigned sport=(unsigned(p[t])<<8)|p[t+1];
            require(be32(p+payload+4)==command,"late foreign command");
            require(seen.insert(be32(p+payload+8)).second,"duplicate packet");
            if(mapping.count(sport))require(mapping[sport]==o->batch_queue,"tuple moved within controlled roster");
            else mapping[sport]=o->batch_queue;
        }
        require(wbd_xdp_rx_release(o)!=0,"release");account(o);
    }
    require(seen.size()==count,"missing packets");
}
static void state(RxOwner* o,const char* stage,unsigned q){
    auto& x=o->queues[q];
    std::printf("MIGRATION stage=%s tick_ms=%llu queue=%u posted=%u peak=%u borrowed=%llu returned=%llu free=%u fresh_cursor=%u\n",
        stage,GetTickCount64(),q,x.posted,x.peak_posted,x.borrowed_chunks,x.returned_chunks,free_count(o),o->pool_next);
    std::fflush(stdout);
}
int main(int argc,char** argv){
    if(argc!=3)return 2;
    root=fs::path(argv[2]);RxOwner* o=nullptr;
    try{
        const bool single=GetEnvironmentVariableA("WBD_XDP_SINGLE_RSS",nullptr,0)>0;
        SetEnvironmentVariableA("WBD_XDP_LAB_POLICY",single?"rx-single":"rx-pool-recycle");
        SetEnvironmentVariableA("WBD_XDP_LAB_RX","16384");
        HRESULT hr; o=open_rx(std::strtoul(argv[1],nullptr,10),&TestPort,1,FALSE,XSK_BIND_FLAG_GENERIC,&hr);
        require(o&&(single?o->single:o->recycle),"product RX open");
        std::printf("READY queues=%u\n",o->count);std::fflush(stdout);
        std::map<unsigned,unsigned> mapping;
        batch(o,0,64,mapping);
        std::map<unsigned,unsigned> by_queue;
        for(auto [port,q]:mapping)by_queue.emplace(q,port);
        if(single){
            require(mapping.size()==64&&by_queue.size()==1&&by_queue.begin()->first==0&&o->count==1,"single RSS roster coverage");
            XSK_STATISTICS x{};UINT32 sz=sizeof(x);
            require(SUCCEEDED(XskGetSockopt(o->queues[0].socket,XSK_SOCKOPT_STATISTICS,&x,&sz))&&!x.RxDropped&&!x.RxTruncated&&!x.RxInvalidDescriptors,"single RSS stats");
            std::puts("SINGLE_RSS_ROSTER_PASS tuples=64 queues=1");
            wbd_xdp_rx_close(o);o=nullptr;request(65535,0);return 0;
        }
        require(by_queue.size()>=3,"need three distinct actual queues");
        std::vector<std::pair<unsigned,unsigned>> roster(by_queue.begin(),by_queue.end());
        for(auto [q,port]:roster)std::printf("MIGRATION_ROSTER queue=%u source=%u\n",q,port);
        // Force real backlog without relying on machine's uncontrolled PPS.
        // Each request stays within already granted credits; no deliberate drop.
        auto heat=[&](unsigned q,unsigned port){
            for(unsigned attempt=0;attempt<4&&o->queues[q].posted<o->slots;++attempt){
                const auto before=o->queues[q].posted;
                batch(o,port,before/2,mapping);
                if(o->queues[q].posted==before)break;
            }
            state(o,"heated",q);
        };
        auto [q0,p0]=roster[0];auto [q1,p1]=roster[1];auto [q2,p2]=roster[2];
        heat(q0,p0);require(o->queues[q0].peak_posted>o->pool_base,"first queue never grew");
        const auto start=GetTickCount64();const auto old=o->queues[q0].posted;
        // Old queue still carries a low-rate tail. Returned buffers should
        // enter the free list and be reusable by the next queue.
        for(unsigned i=0;i<256&&o->queues[q0].posted>o->pool_base;++i)batch(o,p0,128,mapping);
        state(o,"tail_drained",q0);
        std::printf("MIGRATION_TAIL elapsed_ms=%llu released=%u\n",GetTickCount64()-start,old-o->queues[q0].posted);
        require(o->queues[q0].posted==o->pool_base,"tail did not return to floor");
        auto cursor=o->pool_next;heat(q1,p1);
        require(o->queues[q1].peak_posted>o->pool_base,"second queue never grew");
        std::printf("MIGRATION_REUSE new_never_posted=%u returned_list_remaining=%u\n",o->pool_next-cursor,o->free_count);
        // Abrupt stop: no additional packets for q1, never touch its
        // driver-owned entries. Measure stranded credits during next heat.
        const auto stranded=o->queues[q1].posted;
        const auto t=GetTickCount64();Sleep(1000);heat(q2,p2);
        state(o,"abrupt_old",q1);state(o,"abrupt_new",q2);
        std::printf("MIGRATION_ABRUPT elapsed_ms=%llu old_before=%u old_after=%u new_peak=%u free=%u\n",
            GetTickCount64()-t,stranded,o->queues[q1].posted,o->queues[q2].peak_posted,free_count(o));
        require(o->queues[q1].posted==stranded,"unexpected reclaim from silent driver-owned queue");
        // No attempt to call an abrupt-stranding observation a full fix.
        for(UINT32 i=0;i<o->count;++i){XSK_STATISTICS x{};UINT32 sz=sizeof(x);
            require(SUCCEEDED(XskGetSockopt(o->queues[i].socket,XSK_SOCKOPT_STATISTICS,&x,&sz)),"stats");
            require(!x.RxDropped&&!x.RxTruncated&&!x.RxInvalidDescriptors,"driver drop/trunc/invalid");}
        account(o);wbd_xdp_rx_close(o);o=nullptr;
        request(65535,0);std::puts("MIGRATION_PROBE_PASS");return 0;
    }catch(const std::exception& e){std::fprintf(stderr,"MIGRATION_ERROR %s\n",e.what());if(o)wbd_xdp_rx_close(o);return 1;}
}
