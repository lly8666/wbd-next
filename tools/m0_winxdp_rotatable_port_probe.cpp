// Exercise the actual WBD native shim, not a second port-set implementation.
#define NOMINMAX
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
extern "C" int wbd_xdp_open_rotatable_carrier(DWORD,const UINT8*,const UINT16*,UINT32,void**);
extern "C" int wbd_xdp_rx_change_port(void*,UINT16,BOOL);
extern "C" int wbd_xdp_rx_cold_read(void*,unsigned char*,size_t);
extern "C" void wbd_xdp_rx_close(void*);
extern "C" void wbd_xdp_tx_close(void*);
struct Pair {
    void* h[2]{};
    ~Pair(){if(h[0])wbd_xdp_rx_close(h[0]);if(h[1])wbd_xdp_tx_close(h[1]);}
};
int main(int argc,char** argv){
    if(argc!=3)return 2;
    WSADATA wd{};if(WSAStartup(MAKEWORD(2,2),&wd))return 2;
    IN_ADDR ip{};
    if(InetPtonA(AF_INET,argv[2],&ip)!=1)return 2;
    Pair pair;
    const UINT16 ports[4]={39461,39462,39464,39465};
    if(!wbd_xdp_open_rotatable_carrier(std::strtoul(argv[1],nullptr,10),
        reinterpret_cast<const UINT8*>(&ip),ports,4,pair.h))return 3;
    // Source-port tags identify the actual independently generated Linux SYN
    // phases and discard any stale packets from the previous test phase.
    unsigned char frame[4096];
    for(unsigned phase=0;phase<3;++phase){
        if(phase==1&&!wbd_xdp_rx_change_port(pair.h[0],39463,TRUE))return 4;
        if(phase==2&&!wbd_xdp_rx_change_port(pair.h[0],39461,FALSE))return 5;
        std::printf("PORTSET_PHASE %u\n",phase);std::fflush(stdout);
        unsigned seen[5]{};
        ULONGLONG end=GetTickCount64()+4500;
        while(GetTickCount64()<end){
            int n=wbd_xdp_rx_cold_read(pair.h[0],frame,sizeof(frame));
            if(n<0)return 6;
            if(n<54||frame[12]!=8||frame[13]!=0||frame[23]!=6)continue;
            unsigned off=14+4*(frame[14]&15);
            if(unsigned(n)<off+20||!(frame[off+13]&2))continue;
            unsigned src=unsigned(frame[off])*256+frame[off+1];
            unsigned dst=unsigned(frame[off+2])*256+frame[off+3];
            unsigned first=46000+phase*100;
            if(src<first||src>=first+30||dst<39461||dst>39465)continue;
            unsigned i=dst-39461,tag=src-first;
            if(tag/6==i)seen[i]|=1u<<(tag%6);
        }
        std::printf("PORTSET_SEEN phase=%u masks=%u,%u,%u,%u,%u\n",phase,seen[0],seen[1],seen[2],seen[3],seen[4]);std::fflush(stdout);
        if(seen[0]!=(phase<2?63u:0u)||seen[1]!=63||seen[2]!=(phase?63u:0u)||seen[3]!=63||seen[4]!=63)return 7;
    }
    std::puts("WBD_XDP_DYNAMIC_PORTSET_REAL_FIVE_TUPLES_PASS same_carrier=1");return 0;
}
