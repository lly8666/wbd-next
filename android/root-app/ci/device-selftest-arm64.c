/*
 * ARM64-only, DEBUG-APK isolated kernel-capability admission binary.
 * Not the WBD client, never used as an alternate TLS/Rust/M4 packet path.
 * Actual TUNSETIFF/AF_PACKET/SO_BINDTODEVICE and bounded A11 TUN read.
 * Never sends external traffic or replaces original Go/Rust data-plane.
 */
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/if_ether.h>
#include <linux/if_packet.h>
#include <linux/if_tun.h>
#include <net/if.h>
#include <netinet/in.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <unistd.h>

#ifndef __aarch64__
#error "This device diagnostic MUST be native Android ARM64"
#endif

static int tun_check(void) {
    int fd = open("/dev/net/tun", O_RDWR | O_CLOEXEC);
    if (fd < 0) return 1;
    struct ifreq ifr;
    memset(&ifr, 0, sizeof(ifr));
    ifr.ifr_flags = IFF_TUN | IFF_NO_PI;
    /* No TUNSETPERSIST; FD lifetime owns a fresh, ephemeral test TUN. */
    snprintf(ifr.ifr_name, IFNAMSIZ, "wbdt%05u",
             (unsigned int)(getpid() % 100000));
    int result = ioctl(fd, TUNSETIFF, &ifr);
    if (result < 0) { close(fd); return 2; }
    int s = socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC, 0);
    if (s < 0) { close(fd); return 3; }
    struct ifreq verify;
    memset(&verify, 0, sizeof(verify));
    strncpy(verify.ifr_name, ifr.ifr_name, IFNAMSIZ - 1);
    int ok = ioctl(s, SIOCGIFINDEX, &verify) == 0 &&
             verify.ifr_ifindex > 0;
    close(fd);                 /* strictly destroys our non-persistent TUN */
    if (ioctl(s, SIOCGIFINDEX, &verify) == 0) ok = 0;
    close(s);
    return ok ? 0 : 4;
}

static int raw_check(const char *interface) {
    if (interface == NULL || strlen(interface) >= IFNAMSIZ ||
        strlen(interface) < 1) return 1;
    for (const char *p = interface; *p; p++) {
        if (!((*p >= 'a' && *p <= 'z') ||
              (*p >= 'A' && *p <= 'Z') ||
              (*p >= '0' && *p <= '9') ||
              *p == '-' || *p == '_' || *p == '.')) return 2;
    }
    unsigned int index = if_nametoindex(interface);
    if (!index) return 3;
    int s = socket(AF_PACKET, SOCK_RAW | SOCK_CLOEXEC, htons(ETH_P_IP));
    if (s < 0) return 4;
    struct sockaddr_ll address;
    memset(&address, 0, sizeof(address));
    address.sll_family = AF_PACKET;
    address.sll_ifindex = (int)index;
    address.sll_protocol = htons(ETH_P_IP);
    if (bind(s, (const struct sockaddr *)&address, sizeof(address)) < 0) {
        close(s);
        return 5;
    }
    close(s);
    return 0;
}

static int underlay_check(const char *interface) {
    if (!interface || strlen(interface) >= IFNAMSIZ ||
        strlen(interface) < 1 || !if_nametoindex(interface)) return 1;
    int s = socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC, 0);
    if (s < 0) return 2;
    int ok = setsockopt(s, SOL_SOCKET, SO_BINDTODEVICE,
                        interface, (socklen_t)strlen(interface)+1);
    close(s);
    return ok == 0 ? 0 : 3;
}


/*
 * A11 ONLY: real unbound app-UID DatagramSocket -> Linux policy route ->
 * ephemeral TUN. Exact constant TEST-NET-1/32, UDP port and payload, never
 * source address, packet bytes, UID or application data are logged.
 *
 * The parent Root shell alone owns policy route mutation/rollback; this
 * bounded helper owns only its nonpersistent TUN FD, never TUNSETPERSIST.
 * Only a trusted 0700 root-owned directory receives the ready marker.
 */
static int uid_tun_capture(const char *ready_file) {
    const char name[] = "wbdst11";
    const char payload[] = "WBD_A11_TUN_UID";
    if (!ready_file || strlen(ready_file) >= 256 ||
        strncmp(ready_file, "/data/local/tmp/wbd-next-selftest/",
                sizeof("/data/local/tmp/wbd-next-selftest/")-1) != 0)
        return 40;
    if (if_nametoindex(name) != 0) return 41;
    int fd = open("/dev/net/tun", O_RDWR | O_CLOEXEC);
    if (fd < 0) return 42;
    struct ifreq ifr;
    memset(&ifr, 0, sizeof(ifr));
    ifr.ifr_flags = IFF_TUN | IFF_NO_PI;
    snprintf(ifr.ifr_name, IFNAMSIZ, "%s", name);
    if (ioctl(fd, TUNSETIFF, &ifr) < 0) {
        close(fd);
        return 43;
    }
    int marker = open(ready_file,
        O_CREAT | O_EXCL | O_WRONLY | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (marker < 0) {
        close(fd);
        return 44;
    }
    close(marker);
    int found = 0;
    struct pollfd pfd;
    pfd.fd = fd;
    pfd.events = POLLIN;
    pfd.revents = 0;
    /* hard bounded: test-only, never a packet-processing service */
    int rv = poll(&pfd, 1, 9500);
    if (rv > 0 && (pfd.revents & POLLIN)) {
        uint8_t packet[2048];
        ssize_t n = read(fd, packet, sizeof(packet));
        if (n >= 20 && (packet[0] >> 4) == 4) {
            size_t ihl = (size_t)(packet[0] & 15) * 4;
            if (ihl >= 20 && (size_t)n >= ihl + 8 + sizeof(payload)-1 &&
                packet[9] == 17 &&
                packet[16] == 192 && packet[17] == 0 &&
                packet[18] == 2 && packet[19] == 1 &&
                ((unsigned int)packet[ihl+2] << 8 | packet[ihl+3]) == 43999 &&
                packet[ihl+4] == 0 &&
                (size_t)packet[ihl+5] >= 8 + sizeof(payload)-1 &&
                memcmp(packet + ihl + 8, payload, sizeof(payload)-1) == 0) {
                found = 1;
            }
        }
    }
    close(fd); /* kernel frees the test TUN; no persistence */
    return found ? 0 : 45;
}

int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1], "--tun") == 0)
        return tun_check();
    if (argc == 3 && strcmp(argv[1], "--raw") == 0)
        return raw_check(argv[2]);
    if (argc == 3 && strcmp(argv[1], "--underlay") == 0)
        return underlay_check(argv[2]);
    if (argc == 3 && strcmp(argv[1], "--uid-tun-capture") == 0)
        return uid_tun_capture(argv[2]);
    return 64;
}
