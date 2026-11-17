// NDK/Bionic source-locked layout gate; compile for each Android64 ABI.
// This is NOT a Linux GNU/musl ABI assertion and does not touch device state.
#include <stddef.h>
#include <stdint.h>
#include <net/if.h>
#include <netinet/in.h>
#include <linux/if_tun.h>
#include <linux/if_packet.h>
#include <android/multinetwork.h>

_Static_assert(sizeof(void *) == 8, "Android product requires 64-bit pointers");
_Static_assert(sizeof(struct ifreq) == 40, "Android ifreq must be Linux64 40 bytes");
_Static_assert(offsetof(struct ifreq, ifr_flags) == 16, "Bionic ifr_flags at offset16");
_Static_assert(sizeof(struct sockaddr_in) == 16, "unexpected Bionic sockaddr_in");
_Static_assert(sizeof(struct sockaddr_ll) == 20, "unexpected Bionic sockaddr_ll");
_Static_assert(IFNAMSIZ == 16, "unexpected ifname length");
_Static_assert(TUNGETIFF == 0x800454d2UL, "TUNGETIFF ABI changed");
_Static_assert(TUNSETIFF == 0x400454caUL, "TUNSETIFF ABI changed");
_Static_assert(SO_BINDTODEVICE == 25, "socket binding ABI changed");
int wbd_android_abi_gate_only(void) {
    // Symbol references force header/type checking, not a device operation.
    net_handle_t network = 0;
    return network == 0 ? 0 : 1;
}
