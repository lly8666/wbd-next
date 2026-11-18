package org.wbdnext.android

import android.content.Context
import android.util.AtomicFile
import org.json.JSONObject
import java.io.File
import java.io.FileNotFoundException
import java.security.MessageDigest
import javax.crypto.Mac
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.PBEKeySpec
import javax.crypto.spec.SecretKeySpec

/**
 * One-time enrollment helper for the future original-Go authenticated Android owner.
 * This does NOT install an Android VPN or claim that JNI/admission is implemented.
 * Cached 32-byte key is app-private, no-backup and reused across restarts/lanes.
 * Human-picked 8-digit keys remain vulnerable to offline guessing.
 */
internal object RouteKeyStore {
    private const val iterations = 4096
    private val salt = "WBD-V4-ROUTE-KEY-PBKDF2-SHA256-v2\u0000".toByteArray(Charsets.US_ASCII)
    private val checkDomain = "WBD-V4-ROUTE-KEY-CACHE-v2\u0000".toByteArray(Charsets.US_ASCII)

    private fun validate(value: String) {
        require(value.length in 8..32 && value.all {
            it in '0'..'9' || it in 'A'..'Z' || it in 'a'..'z'
        }) { "route-key needs 8..32 case-sensitive ASCII letters/digits" }
    }
    private fun hex(bytes: ByteArray): String =
        bytes.joinToString("") { "%02x".format(it.toInt() and 0xff) }
    private fun fromHex(s: String): ByteArray {
        require(s.length == 64 && s.all { it in '0'..'9' || it in 'a'..'f' })
        return ByteArray(32) { s.substring(it * 2, it * 2 + 2).toInt(16).toByte() }
    }
    internal fun derive(value: String): ByteArray {
        validate(value)
        val spec = PBEKeySpec(value.toCharArray(), salt, iterations, 256)
        return try {
            SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).encoded
        } finally { spec.clearPassword() }
    }
    private fun check(key: ByteArray, secret: String): ByteArray {
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(key, "HmacSHA256"))
        mac.update(checkDomain)
        return mac.doFinal(secret.toByteArray(Charsets.US_ASCII))
    }
    @Synchronized
    internal fun resolve(context: Context, serverName: String, shortKey: String): ByteArray {
        validate(shortKey)
        require(serverName.isNotEmpty())
        val name = MessageDigest.getInstance("SHA-256")
            .digest(("client\u0000" + serverName).toByteArray(Charsets.UTF_8))
            .copyOf(12).let(::hex)
        val file = AtomicFile(File(context.noBackupFilesDir, "route-key-v2-$name.json"))
        try {
            val raw = file.readFully()
            require(raw.size <= 512) { "oversized route-key cache" }
            val record = JSONObject(String(raw, Charsets.UTF_8))
            require(record.getInt("version") == 2) { "unsupported route-key cache" }
            val key = fromHex(record.getString("key_hex"))
            val tag = fromHex(record.getString("check_hex"))
            if (MessageDigest.isEqual(check(key, shortKey), tag)) return key
        } catch (_: FileNotFoundException) {
            // First enrollment: derive below.
        }
        // A changed short key creates a new key. Invalid/malformed cache must
        // fail closed instead of silently recovering an unrelated route key.
        val key = derive(shortKey)
        val record = JSONObject().put("version", 2).put("key_hex", hex(key))
            .put("check_hex", hex(check(key, shortKey))).toString()
        val stream = file.startWrite()
        try {
            stream.write(record.toByteArray(Charsets.UTF_8))
            file.finishWrite(stream)
        } catch (t: Throwable) {
            file.failWrite(stream)
            throw t
        }
        return key
    }
}
