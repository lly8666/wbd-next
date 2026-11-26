// Read-only capability test except for creating and closing an ephemeral BPF map.
#include <errno.h>
#include <fcntl.h>
#include <linux/bpf.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/syscall.h>
#include <unistd.h>
static void report(const char *op,long rc) {
    if (rc<0) printf("BBR_KERNEL %s errno=%d %s\n",op,errno,strerror(errno));
    else printf("BBR_KERNEL %s OK %ld\n",op,rc);
}
int main(void) {
    int s=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);
    if(s>=0) {
        report("TCP_CONGESTION_bbr",setsockopt(s,IPPROTO_TCP,TCP_CONGESTION,"bbr",4));
        close(s);
    }
    int btf=open("/sys/kernel/btf/vmlinux",O_RDONLY);
    report("vmlinux_btf_file",btf);
    if(btf>=0) close(btf);
    union bpf_attr a={0};
    a.map_type=BPF_MAP_TYPE_ARRAY;a.key_size=4;a.value_size=4;a.max_entries=1;
    long fd=syscall(SYS_bpf,BPF_MAP_CREATE,&a,sizeof(a));
    report("BPF_MAP_CREATE",fd);
    if(fd>=0)close((int)fd);
    memset(&a,0,sizeof(a));a.start_id=0;
    long rc=syscall(SYS_bpf,BPF_BTF_GET_NEXT_ID,&a,sizeof(a));
    report("BPF_BTF_GET_NEXT_ID",rc);
    if(rc==0)printf("BBR_KERNEL BTF_FIRST_ID %u\n",a.next_id);
    puts("BBR_KERNEL_PROBE_COMPLETE");
    return 0;
}
