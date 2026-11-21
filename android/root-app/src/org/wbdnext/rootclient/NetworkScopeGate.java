package org.wbdnext.rootclient;

import java.util.concurrent.atomic.AtomicBoolean;

// Only the exact physical Network handle of this Root owner generation
// may revoke its route. An unregistered previous generation is inert.
final class NetworkScopeGate {
    private final long handle;
    private final AtomicBoolean active=new AtomicBoolean(true);
    NetworkScopeGate(long handle){
        if(handle==0)throw new IllegalArgumentException("missing Network handle");
        this.handle=handle;
    }
    boolean selected(long candidate){return active.get()&&candidate==handle;}
    boolean lost(long candidate){return selected(candidate);}
    boolean changed(long candidate,boolean valid){return selected(candidate)&&!valid;}
    boolean blocked(long candidate,boolean blocked){return selected(candidate)&&blocked;}
    void close(){active.set(false);}
}
