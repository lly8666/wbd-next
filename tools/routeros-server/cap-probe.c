/* Cold diagnostic only: no data traffic, no persistent configuration. */
#define _GNU_SOURCE
#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <linux/if_ether.h>
#include <linux/if_packet.h>
static void outcome(const char *name, int rc) {
    if (rc < 0) printf("WBD_ROS_CAP %s FAIL errno=%d %s\n", name, errno, strerror(errno));
    else printf("WBD_ROS_CAP %s PASS\n", name);
}
int main(void) {
    int fd = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_IP));
    outcome("AF_PACKET_RAW", fd);
    if (fd >= 0) close(fd);
    fd = socket(AF_INET, SOCK_RAW, IPPROTO_TCP);
    outcome("AF_INET_RAW_TCP", fd);
    if (fd >= 0) close(fd);
    fd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    outcome("TCP_SOCKET", fd);
    if (fd >= 0) {
        int one = 1;
        outcome("IP_TRANSPARENT", setsockopt(fd, IPPROTO_IP, IP_TRANSPARENT, &one, sizeof(one)));
        outcome("TCP_CONGESTION_cubic", setsockopt(fd, IPPROTO_TCP, TCP_CONGESTION, "cubic", 5));
        outcome("TCP_CONGESTION_bbr", setsockopt(fd, IPPROTO_TCP, TCP_CONGESTION, "bbr", 3));
        close(fd);
    }
    return 0;
}
