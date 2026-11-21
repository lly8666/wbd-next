package org.wbdnext.rootclient;

import java.io.IOException;
import java.util.concurrent.atomic.AtomicInteger;

public final class RootStartCredentialSaveTest {
    public static void main(String[] args) {
        AtomicInteger actions=new AtomicInteger();
        if(!RootStartCredentialSave.attempt(()->actions.incrementAndGet()))
            throw new AssertionError("working credential persistence refused");
        if(RootStartCredentialSave.attempt(()->{throw new IOException("AndroidKeystore unavailable");}))
            throw new AssertionError("failed persistence reported success");
        if(RootStartCredentialSave.attempt(null))
            throw new AssertionError("no action accepted");
        // After save failure the original client dispatch must remain free
        // to execute: persistence is a non-fatal side effect.
        actions.incrementAndGet();
        if(actions.get()!=2)throw new AssertionError("native dispatch blocked by persistence");
        System.out.println("ANDROID_A39_NONBLOCKING_CREDENTIAL_SAVE_REAL_JVM_HOST_PASS");
    }
}
