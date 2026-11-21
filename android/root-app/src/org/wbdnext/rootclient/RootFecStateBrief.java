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
    private RootFecStateBrief(){}

    static String fromGoLine(String line){
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
