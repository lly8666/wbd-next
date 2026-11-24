package org.wbdnext.rootclient;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

/** A named cold UI configuration; no credential or Root/Network ownership. */
final class RootConnectionProfile {
    static final int SLOTS=4;
    static final int MAX_FILE_BYTES=9000;
    private static final int MAGIC=0x57425032; // local profile v1, not a wire format
    final String label;
    final RootConnectionSettings settings;

    RootConnectionProfile(String label,RootConnectionSettings settings) {
        String normalized=label==null?"":label.trim();
        if(normalized.isEmpty()||normalized.length()>32||settings==null)
            throw new IllegalArgumentException("profile name and settings required");
        this.label=normalized;
        this.settings=settings;
    }
    void write(OutputStream output)throws IOException {
        ByteArrayOutputStream settingsBytes=new ByteArrayOutputStream();
        settings.write(settingsBytes); // existing B22/B49 production codec
        byte[] payload=settingsBytes.toByteArray();
        if(payload.length>RootConnectionSettingsTransfer.MAX_BYTES)
            throw new IOException("profile settings exceeded existing preset capacity");
        DataOutputStream out=new DataOutputStream(output);
        out.writeInt(MAGIC);
        out.writeUTF(label);
        out.writeInt(payload.length);
        out.write(payload);
        out.flush();
    }
    static RootConnectionProfile read(InputStream source)throws IOException {
        DataInputStream in=new DataInputStream(source);
        if(in.readInt()!=MAGIC)return null;
        String name=in.readUTF();
        int size=in.readInt();
        if(size<1||size>RootConnectionSettingsTransfer.MAX_BYTES)return null;
        byte[] bytes=new byte[size];
        in.readFully(bytes);
        RootConnectionSettings settings=RootConnectionSettings.read(
            new ByteArrayInputStream(bytes));
        if(settings==null)return null;
        return new RootConnectionProfile(name,settings);
    }
}
