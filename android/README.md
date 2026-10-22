# Android ARM64 client integration (NOT YET CONNECTABLE)

This is a buildable Android VpnService **OS ownership boundary**, not a working
VPN client yet. No JNI `libwbd_android_client.so` or original-Go authenticated
control owner is present; service fails closed *before* VPN establishment if
the library/verified session is absent. An Activity must request
`VpnService.prepare()` user consent before starting ACTION_CONNECT.

Next native work: fixed-source Go TLS credential owner over Android-protected
socket; authenticatedReady must reflect real admission, not placeholder success.
Implement JNI ownership transaction: only accept a detached fd after protected
underlay and session admission; native consumes bounded TUN IO and release loans,
Stop joins all IO and closes the exact fd. Error/revoke must unwind; application
must not claim an active tunnel based on `establish()` alone.

Current 10.188.0.2/32 and full-route values are development placeholders,
not product-approved addresses or leak protection. Android DNS and IPv6
policies are **NOT_RUN**. Do not publish/deploy this app as a VPN.
