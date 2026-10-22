package org.wbdnext.android

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.net.VpnService
import android.os.Build
import android.os.ParcelFileDescriptor
import android.content.Intent
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Android OS boundary only. No independent TLS/AEAD implementation.
 *
 * Native must first authenticate the original Go session and attest ready.
 * JNI is not yet linked in this branch: fail CLOSED without creating a VPN.
 * The bridge MUST call protect(fd) before any underlay connect to avoid VPN
 * recursion, and MUST own/destroy the detached TUN fd only on StartSuccess.
 */
class WbdVpnService : VpnService() {
    companion object {
        const val ACTION_CONNECT = "org.wbdnext.android.CONNECT"
        const val ACTION_STOP = "org.wbdnext.android.STOP"
        private const val CHANNEL = "wbd-vpn"
        private const val NOTIFICATION_ID = 5401
    }
    private var started = AtomicBoolean(false)

    fun interface SocketProtector {
        fun protect(fd: Int): Boolean
    }

    private object NativeOwner {
        private val available = runCatching { System.loadLibrary("wbd_android_client") }.isSuccess
        fun loaded() = available
        external fun authenticatedReady(): Boolean
        // Return true ONLY after ownership transfer, never for a queued attempt.
        external fun startOwnedTun(tunFd: Int, protector: SocketProtector): Boolean
        // Must join kernel IO, release loans and close owned TUN before true.
        external fun stopOwnedTun(): Boolean
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            closeOwner()
            stopSelf()
            return START_NOT_STICKY
        }
        if (intent?.action != ACTION_CONNECT || VpnService.prepare(this) != null ||
            !NativeOwner.loaded() || !runCatching { NativeOwner.authenticatedReady() }.getOrDefault(false)) {
            // Permission must be obtained by a user-initiated Activity first.
            // Missing bridge or missing authentication MUST NOT install a route.
            stopSelf(startId)
            return START_NOT_STICKY
        }
        if (!started.compareAndSet(false, true)) return START_NOT_STICKY
        val channel = NotificationChannel(CHANNEL, "WBD VPN", NotificationManager.IMPORTANCE_LOW)
        getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        val notification = Notification.Builder(this, CHANNEL)
            .setSmallIcon(android.R.drawable.stat_sys_download_done)
            .setContentTitle("WBD VPN").setContentText("Connecting authenticated tunnel")
            .build()
        startForeground(NOTIFICATION_ID, notification)

        var detachedFd = -1
        try {
            val tun = Builder().setSession("WBD Next")
                .setMtu(1200)
                .addAddress("10.188.0.2", 32)
                .addRoute("0.0.0.0", 0)
                .establish() ?: error("Android refused VPN interface")
            detachedFd = tun.detachFd()
            tun.close()
            val accepted = NativeOwner.startOwnedTun(detachedFd, SocketProtector { fd -> protect(fd) })
            if (!accepted) error("Authenticated native owner refused TUN")
            detachedFd = -1 // Native now owns it and must close on Stop.
        } catch (_: Exception) {
            if (detachedFd >= 0) ParcelFileDescriptor.adoptFd(detachedFd).close()
            closeOwner()
            stopSelf(startId)
        } catch (_: LinkageError) {
            if (detachedFd >= 0) ParcelFileDescriptor.adoptFd(detachedFd).close()
            closeOwner()
            stopSelf(startId)
        }
        return START_NOT_STICKY
    }

    override fun onRevoke() {
        closeOwner()
        super.onRevoke()
        stopSelf()
    }

    override fun onDestroy() {
        closeOwner()
        super.onDestroy()
    }

    private fun closeOwner() {
        if (started.getAndSet(false) && NativeOwner.loaded()) {
            // Native stop is required to be joined; failure cannot be called Applied/clean.
            runCatching { NativeOwner.stopOwnedTun() }
        }
    }
}
