#define _GNU_SOURCE
/* H2237 TEST-ONLY kernel primitive comparison. NO WBD product socket owner.
 * Same immutable IPv4/TCP bytes, identical two-iovec messages and real
 * sendmmsg(2); raw IP_HDRINCL vs AF_PACKET/SOCK_DGRAM L3. Never a proxy
 * for authentic peer delivery, original Go TLS, AEAD/PN or Stop.
 */
#include <arpa/inet.h>
#include <errno.h>
#include <linux/if_packet.h>
#include <linux/if_ether.h>
#include <net/if.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <netinet/tcp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

enum { BATCH=32, HEADER=40, BODY=1024, MAX_SEND=200000 };
static uint8_t headers[BATCH][HEADER], payloads[BATCH][BODY];
static struct iovec iovecs[BATCH][2];
static struct mmsghdr mmsgs[BATCH];
static uint32_t sums(const uint8_t *b,size_t n){
    uint32_t acc=0;
    while(n>=2){acc+=(uint32_t)b[0]*256u+(uint32_t)b[1];b+=2;n-=2;}
    if(n)acc+=(uint32_t)b[0]<<8;
    return acc;
}
static uint16_t fold(uint32_t sum){
    while(sum>>16)sum=(sum&65535u)+(sum>>16);
    return (uint16_t)(~sum);
}
static void put16(uint8_t *p,uint16_t v){p[0]=(uint8_t)(v>>8);p[1]=(uint8_t)v;}
static void put32(uint8_t *p,uint32_t v){
    p[0]=(uint8_t)(v>>24);p[1]=(uint8_t)(v>>16);
    p[2]=(uint8_t)(v>>8);p[3]=(uint8_t)v;
}
static double clock_seconds(clockid_t type){
    struct timespec t;
    if(clock_gettime(type,&t))return -1;
    return (double)t.tv_sec+1e-9*(double)t.tv_nsec;
}
static int parse_mac(const char *arg,uint8_t mac[6]){
    unsigned x[6];
    if(sscanf(arg,"%2x:%2x:%2x:%2x:%2x:%2x",
              &x[0],&x[1],&x[2],&x[3],&x[4],&x[5])!=6)return -1;
    for(int i=0;i<6;i++)if(x[i]>255)return -1;else mac[i]=(uint8_t)x[i];
    return 0;
}
static void make_frames(void){
    for(int i=0;i<BATCH;i++){
        uint8_t *ip=headers[i],*tcp=headers[i]+20,*body=payloads[i];
        memset(headers[i],0,HEADER);
        for(int k=0;k<BODY;k++)body[k]=(uint8_t)((i*19+k*13+41)&255);
        ip[0]=0x45;put16(ip+2,HEADER+BODY);put16(ip+4,43);
        put16(ip+6,0x4000);ip[8]=64;ip[9]=6;
        memcpy(ip+12,(uint8_t[]){10,248,81,2},4);
        memcpy(ip+16,(uint8_t[]){10,248,82,2},4);
        put16(ip+10,fold(sums(ip,20)));
        put16(tcp,44109);put16(tcp+2,44331);
        put32(tcp+4,0x12340000u+(uint32_t)i*1024u);
        put32(tcp+8,1);
        tcp[12]=0x50;tcp[13]=0x18;put16(tcp+14,65535);
        uint32_t sum=sums(ip+12,8)+6u+20u+BODY+
                     sums(tcp,20)+sums(body,BODY);
        put16(tcp+16,fold(sum));
        iovecs[i][0]=(struct iovec){headers[i],HEADER};
        iovecs[i][1]=(struct iovec){payloads[i],BODY};
    }
}
int main(int argc,char **argv){
    if(argc!=4){fprintf(stderr,"H2237_USAGE MODE(raw|packet) GATEWAY_MAC TARGET_PPS(0|100000)\n");return 2;}
    int target_pps=atoi(argv[3]);
    if(target_pps!=0&&target_pps!=100000)return 2;
    int packet=strcmp(argv[1],"packet")==0;
    if(!packet && strcmp(argv[1],"raw"))return 2;
    uint8_t mac[6];
    if(parse_mac(argv[2],mac))return 2;
    unsigned ifindex=if_nametoindex("wan0");
    if(!ifindex){perror("H2237_INTERFACE_NOT_FOUND");return 2;}
    int fd=packet?
      socket(AF_PACKET,SOCK_DGRAM|SOCK_NONBLOCK,htons(ETH_P_IP)):
      socket(AF_INET,SOCK_RAW|SOCK_NONBLOCK,IPPROTO_RAW);
    if(fd<0){perror("H2237_SOCKET_FAILED");return 3;}
    if(setsockopt(fd,SOL_SOCKET,SO_BINDTODEVICE,"wan0",5)){
        perror("H2237_DEVICE_BIND_FAILED");close(fd);return 3;
    }
    if(!packet){
        int enable=1;
        if(setsockopt(fd,IPPROTO_IP,IP_HDRINCL,&enable,sizeof(enable))){
            perror("H2237_IP_HDRINCL_FAILED");close(fd);return 3;
        }
    }
    struct sockaddr_in ipdest={0};
    ipdest.sin_family=AF_INET;
    if(inet_pton(AF_INET,"10.248.82.2",&ipdest.sin_addr)!=1)return 3;
    struct sockaddr_ll pktdest={0};
    pktdest.sll_family=AF_PACKET;
    pktdest.sll_protocol=htons(ETH_P_IP);
    pktdest.sll_ifindex=(int)ifindex;
    pktdest.sll_halen=ETH_ALEN;
    memcpy(pktdest.sll_addr,mac,6);
    make_frames();
    for(int i=0;i<BATCH;i++){
        memset(&mmsgs[i],0,sizeof(mmsgs[i]));
        mmsgs[i].msg_hdr.msg_name=packet?(void*)&pktdest:(void*)&ipdest;
        mmsgs[i].msg_hdr.msg_namelen=packet?sizeof(pktdest):sizeof(ipdest);
        mmsgs[i].msg_hdr.msg_iov=iovecs[i];
        mmsgs[i].msg_hdr.msg_iovlen=2;
    }
    double t0=clock_seconds(CLOCK_MONOTONIC);
    double c0=clock_seconds(CLOCK_PROCESS_CPUTIME_ID);
    if(t0<0||c0<0)return 3;
    int copied=0,calls=0,eagain=0,partial=0;
    while(copied<MAX_SEND && clock_seconds(CLOCK_MONOTONIC)-t0<3.0){
        int budget=MAX_SEND-copied;
        int count=budget<BATCH?budget:BATCH;
        int n=sendmmsg(fd,mmsgs,(unsigned)count,MSG_DONTWAIT);
        calls++;
        if(n<0){
            if(errno==EAGAIN||errno==EWOULDBLOCK){eagain++;continue;}
            if(errno==EINTR)continue;
            fprintf(stderr,"H2237_KERNEL_SEND_FAILED errno=%d\n",errno);
            close(fd);return 4;
        }
        if(n<count)partial++;
        copied+=n;
        if(target_pps>0 && n>0){
            const double due=t0+(double)copied/(double)target_pps;
            double remain=due-clock_seconds(CLOCK_MONOTONIC);
            if(remain>0){
                struct timespec sleep_for={(time_t)remain,
                    (long)((remain-(time_t)remain)*1e9)};
                if(sleep_for.tv_nsec>=0 && sleep_for.tv_nsec<1000000000L)
                    (void)nanosleep(&sleep_for,NULL);
            }
        }
    }
    double elapsed=clock_seconds(CLOCK_MONOTONIC)-t0;
    double cpu=clock_seconds(CLOCK_PROCESS_CPUTIME_ID)-c0;
    close(fd);
    if(copied<=0||elapsed<=0||cpu<0)return 5;
    printf("{\"source\":\"H2237_TEST_ONLY\",\"mode\":\"%s\","
           "\"accepted_kernel_prefix_packets\":%d,\"sendmmsg_calls\":%d,"
           "\"eagain_calls\":%d,\"short_prefix_calls\":%d,"
           "\"one_ipv4_tcp_packet_bytes\":%d,\"wire_payload_bytes_per_packet\":%d,"
           "\"wall_seconds\":%.6f,\"cpu_seconds\":%.6f,"
           "\"target_pps\":%d,"
           "\"accepted_packets_per_second\":%.2f,"
           "\"actual_peer_receipts\":\"NOT_OBSERVED_BY_SENDER\"}\n",
           packet?"packet":"raw",copied,calls,eagain,partial,
           HEADER+BODY,BODY,elapsed,cpu,target_pps,copied/elapsed);
    return 0;
}
