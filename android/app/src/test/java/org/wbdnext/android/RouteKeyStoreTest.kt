package org.wbdnext.android

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class RouteKeyStoreTest {
    @Test fun linuxWindowsAndroidV2Parity() {
        val cases = mapOf(
            "Abc12345" to "b3745a18edd59a1ce6aa2586ae5d90c3ec2eee3fbfafa059783e4492e2bc0539",
            "A1b2C3d4E5f6G7h8" to "68ef025a9224cafa38c55e4fad14eec0fece1642c8679a41368fee0f5702033e",
            "ABCdef0123456789ABCdef0123456789" to "fcb0fd63fb6e807da50afc7d1c39a9df68b7c39ae67ed2cc2db76ebe9127054e"
        )
        for ((input, want) in cases)
            assertEquals(want, RouteKeyStore.derive(input).joinToString("") { "%02x".format(it.toInt() and 255) })
        assertNotEquals(RouteKeyStore.derive("Abc12345").toList(), RouteKeyStore.derive("abc12345").toList())
    }
    @Test fun invalidInputFailsLocally() {
        for (text in listOf("", "1234567", "ABC_12345", "ABC-12345", "abc def12", "中文abcd1234"))
            assertThrows(IllegalArgumentException::class.java) { RouteKeyStore.derive(text) }
    }
}
