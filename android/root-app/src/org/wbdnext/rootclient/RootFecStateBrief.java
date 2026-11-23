package org.wbdnext.rootclient;

/**
 * B20: display ONLY the original Go/Rust live FEC revision returned by
 * authenticated native readback. A chosen Auto/Fixed UI setting or native
 * M4 readiness alone is not APPLIED and not app TCP/UDP delivery.
 *
 * Pure Java: the exact production parser is exercised on the Host.
 */
final class RootFecStateBrief {
    private static final String MARKER="V4_PUBLIC_ANDROID_FEC_STATE role=client ";
    private static final String GAME_MARKER="V4_PUBLIC_ANDROID_GAME2_M4_COUNTERS role=client ";
    private static final String GAME4_MARKER="V4_PUBLIC_ANDROID_GAME4_M4_COUNTERS role=client ";
    private static final String[] GAME_FIELDS={
        "rawtx=","rawrx=","tun=","rejected=","dnstx=","dnsrx=",
        "physicaltx=","physicalrx=","physicalerr="
    };
    private static String gameCounters(String line){
        String marker,label;
        if(OriginalGoMilestones.matches(line,
            "V4_PUBLIC_ANDROID_GAME4_M4_COUNTERS role=client")){
            marker=GAME4_MARKER;label="Game4/off";
        }else if(OriginalGoMilestones.matches(line,
            "V4_PUBLIC_ANDROID_GAME2_M4_COUNTERS role=client")){
            marker=GAME_MARKER;label="Game2/off";
        }else{return null;}
        int start=line.indexOf(marker);
        if(start<0)return null;
        String[] values=line.substring(start+marker.length()).split(" ",-1);
        // Keep B43 six-counter receipts readable alongside B44 nine-counter
        // physical/CN DNS receipts from the same original M4 owner.
        if(values.length!=6&&values.length!=GAME_FIELDS.length)return null;
        long[] counts=new long[values.length];
        try{
            for(int i=0;i<counts.length;i++){
                if(!values[i].startsWith(GAME_FIELDS[i]))return null;
                counts[i]=Long.parseLong(values[i].substring(GAME_FIELDS[i].length()));
                if(counts[i]<0)return null;
            }
        }catch(NumberFormatException bad){return null;}
        return label+" 原Rust M4：RAW发送="+counts[0]+
            "，RAW接收="+counts[1]+"，反向TUN="+counts[2]+
            "，拒绝="+counts[3]+"；隧道DNS请求="+counts[4]+
            "，回包="+counts[5]+
            (counts.length==9?"；物理DNS发送="+counts[6]+
                "，回包="+counts[7]+"，错误="+counts[8]:"")+
            "（内核计数，非应用E2E）";
    }
    private RootFecStateBrief(){}

    static String fromGoLine(String line){
        String game=gameCounters(line);
        if(game!=null)return game;
        if(!OriginalGoMilestones.matches(line,
            "V4_PUBLIC_ANDROID_FEC_STATE role=client"))return null;
        // OriginalGoMilestones already checked the exact start or Go
        // timestamp prefix. Never display the rest of stderr verbatim.
        int start=line.indexOf(MARKER);
        if(start<0)return null;
        String[] parts=line.substring(start+MARKER.length()).split(" ",-1);
        if(parts.length!=5||!parts[0].startsWith("mode=")||
           !parts[1].startsWith("requested=")||
           !parts[2].startsWith("applied=")||
           !parts[3].startsWith("profile=")||
           !parts[4].startsWith("pending="))return null;
        String mode=parts[0].substring(5);
        if(!"fixed".equals(mode)&&!"auto".equals(mode))return null;
        boolean pending;
        if("pending=true".equals(parts[4]))pending=true;
        else if("pending=false".equals(parts[4]))pending=false;
        else return null;
        try{
            long requested=Long.parseLong(parts[1].substring(10));
            long applied=Long.parseLong(parts[2].substring(8));
            int profile=Integer.parseInt(parts[3].substring(8));
            if(requested<1||applied<0||applied>requested||
               profile<0||profile>6||pending!=(applied!=requested))return null;
            String label="fixed".equals(mode)?"Fixed":"Auto";
            return "FEC "+label+"：Native 请求版本 "+requested+
                "，已应用版本 "+applied+"，档位 "+profile+
                (pending?"（PENDING，尚未证明新档生效）":
                         "（原 Rust 质量确认 APPLIED）")+
                "；不代表应用端到端交付或性能达标";
        }catch(NumberFormatException invalid){
            return null;
        }
    }
}
