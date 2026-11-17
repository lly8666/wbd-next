package org.wbdnext.rootclient;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

/**
 * App-private, bounded, credential-free native Root acceptance evidence.
 *
 * The only serializable values are fixed enum constants and a millisecond
 * timestamp. In particular: never write root generation tokens, usernames,
 * IPs, app package names, route keys, TLS errors or raw native stdout.
 * Diagnostics are advisory; IO errors must NOT affect original Go/Rust Stop.
 *
 * No Android framework dependency: the exact writer is host-unit-tested
 * and compiled into the official signed ARM64 Root APK.
 */
final class RootDiagnosticReceipt {
    enum Event {
        START_REQUESTED,
        NETWORK_SCOPE_VERIFIED,
        APP_UID_GROUP_VERIFIED,
        ROOT_STAGE_REQUESTED,
        NATIVE_SOURCE_VERIFIED,
        ROOT_GRANT_REQUESTED,
        ROOT_PROCESS_LAUNCHED,
        NATIVE_M4_RECEIPT,
        UID_ROUTE_RECEIPT,
        NATIVE_M4_AND_UID_READY,
        AUTHENTICATED_LEASE_OS_READBACK,
        ORIGINAL_GO_RUST_HANDOFF,
        ORIGINAL_GO_UID_ROUTE_STOP_DRAINED,
        ORIGINAL_GO_RUST_STOP_JOINED,
        ROOT_PROCESS_EXIT_139,
        ROOT_PROCESS_EXIT_132,
        ROOT_PROCESS_EXIT_ZERO,
        ROOT_PROCESS_EXIT_NONZERO,
        ROOT_LAUNCH_FAILED,
        START_REFUSED,
        STOP_REQUESTED,
        STOP_SIGNAL_STARTED,
        STOP_SIGNAL_ACCEPTED,
        STOP_SIGNAL_REFUSED,
        STOP_SIGNAL_ERROR,
        OWNER_CLEANUP_FINISHED
    }

    private static final int MAX_BYTES=16384;
    private final File current;

    RootDiagnosticReceipt(File file) {
        if(file==null)throw new IllegalArgumentException("missing receipt path");
        current=file;
    }

    synchronized boolean record(Event event) {
        if(event==null)throw new IllegalArgumentException("missing event");
        final byte[] line=(Long.toString(System.currentTimeMillis())+
            "|" + event.name() + "\n").getBytes(StandardCharsets.US_ASCII);
        if(line.length>128)return false;
        File parent=current.getParentFile();
        if(parent==null||!parent.isDirectory())return false;
        try{
            if(current.length()+line.length>MAX_BYTES){
                File previous=new File(parent,current.getName()+".previous");
                if(previous.exists()&&!previous.delete())return false;
                if(!current.renameTo(previous))return false;
            }
            try(FileOutputStream out=new FileOutputStream(current,true)){
                if(!current.setReadable(false,false)||
                   !current.setWritable(false,false)||
                   !current.setReadable(true,true)||
                   !current.setWritable(true,true))return false;
                out.write(line);
                out.getFD().sync();
            }
            return true;
        }catch(IOException|SecurityException e){
            // Logging cannot become a source of Root startup/Stop failure.
            return false;
        }
    }

    static boolean safeEventToken(String token) {
        if(token==null)return false;
        for(Event e:Event.values())if(e.name().equals(token))return true;
        return false;
    }
}
