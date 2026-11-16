package org.wbdnext.rootprobe;

import android.app.Activity;
import android.os.Bundle;
import android.os.Build;
import android.os.Process;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.net.ConnectivityManager;
import android.net.LinkProperties;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.util.Log;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;

/**
 * Self-contained physical Android Root eligibility probe.
 * Does NOT connect to any WBD server or register VpnService.
 * Safe tests create short-lived owned TUN / raw-localhost sockets and, for
 * IPv6/NAT, an isolated Linux network namespace; no main netd/route mutation.
 * Every result includes status + reason + native errno/evidence, and a report
 * can be shared after the user chooses to do so.
 */
public final class DeviceDiagnosticActivity extends Activity {
    private static final String TAG="WBD_DEVICE_DIAG";
    private static final String PASS="PASS";
    private static final String FAIL="FAIL";
    private static final String BLOCKED="ENV_BLOCKED";
    private TextView summary;
    private Button basic,full,share,copy;
    private JSONObject lastReport;

    private String assetText(String name) {
        try(InputStream in=getAssets().open(name)){
            ByteArrayOutputStream out=new ByteArrayOutputStream();
            byte[] b=new byte[1024];int n;
            while((n=in.read(b))!=-1){if(out.size()+n>4096)break;out.write(b,0,n);}
            return out.toString("UTF-8").trim();
        }catch(Exception e){return "UNAVAILABLE:"+e.getClass().getSimpleName();}
    }
    private String nativePath(){
        String dir=getApplicationInfo().nativeLibraryDir;
        if(dir==null || !dir.startsWith("/data/app/"))return "";
        return dir+"/libwbdprobe.so";
    }
    private JSONObject networkSnapshot(){
        JSONObject j=new JSONObject();
        try{
            ConnectivityManager cm=(ConnectivityManager)getSystemService(Context.CONNECTIVITY_SERVICE);
            if(cm==null)throw new IllegalStateException("ConnectivityManager unavailable");
            Network active=cm.getActiveNetwork();
            j.put("active_network_present",active!=null);
            JSONArray nets=new JSONArray();
            for(Network net:cm.getAllNetworks()){
                JSONObject n=new JSONObject();
                NetworkCapabilities caps=cm.getNetworkCapabilities(net);
                LinkProperties links=cm.getLinkProperties(net);
                n.put("active",active!=null&&active.equals(net));
                if(caps!=null){
                    n.put("wifi",caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI));
                    n.put("cellular",caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR));
                    n.put("ethernet",caps.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET));
                    n.put("system_vpn_transport",caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN));
                    n.put("internet_capability",caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET));
                }
                if(links!=null){
                    n.put("interface",links.getInterfaceName());
                    n.put("mtu",links.getMtu());
                    n.put("dns_count",links.getDnsServers().size());
                    n.put("route_count",links.getRoutes().size());
                    n.put("ipv6_link_address_count",links.getLinkAddresses().stream()
                        .filter(x->x.getAddress() instanceof java.net.Inet6Address).count());
                }
                nets.put(n);
            }
            j.put("status","OBSERVED");
            j.put("networks",nets);
        }catch(Exception e){
            try{j.put("status","UNAVAILABLE");j.put("reason",e.toString());}catch(Exception ignored){}
        }
        return j;
    }
    private static JSONObject failed(String status,String reason){
        JSONObject j=new JSONObject();
        try{j.put("status",status);j.put("reason",reason);}catch(Exception ignored){}
        return j;
    }
    private JSONObject nativeCommand(String mode){
        final String path=nativePath();
        if(path.length()==0)return failed("NATIVE_MISSING","nativeLibraryDir invalid; APK extractNativeLibs not available");
        File binary=new File(path);
        if(!binary.exists())return failed("NATIVE_MISSING","native executable not extracted: "+path+
            " (check ABI, install variant, and extractNativeLibs)");
        JSONObject r=new JSONObject();
        java.lang.Process process=null;
        try{
            r.put("mode",mode);
            r.put("native_path",path);
            long begin=android.os.SystemClock.elapsedRealtime();
            // Known commands only; no user-controlled shell arguments.
            process=new ProcessBuilder("su","-c",path+" "+mode)
                .redirectErrorStream(true).start();
            java.lang.Process child=process;
            StringBuilder text=new StringBuilder();
            Thread reader=new Thread(()->{
                try(InputStream stream=child.getInputStream()){
                    byte[] b=new byte[1024];int n;
                    while((n=stream.read(b))!=-1){
                        synchronized(text){
                            if(text.length()<60000)
                                text.append(new String(b,0,Math.min(n,60000-text.length()),StandardCharsets.UTF_8));
                        }
                    }
                }catch(Exception e){synchronized(text){text.append("\nREAD_ERROR:").append(e);}}
            },"wbd-diagnostic-reader");
            reader.setDaemon(true);reader.start();
            boolean finished=process.waitFor(42,TimeUnit.SECONDS);
            if(!finished){
                process.destroy();
                if(!process.waitFor(2,TimeUnit.SECONDS))process.destroyForcibly();
            }
            reader.join(1800);
            String output;
            synchronized(text){output=text.toString();}
            r.put("elapsed_ms",android.os.SystemClock.elapsedRealtime()-begin);
            r.put("su_exit",finished?process.exitValue():-1);
            if(!finished)return failed("ROOT_TIMEOUT","su/native execution did not finish in 42s; please check Root authorization UI");
            String marker=mode.equals("devicecheck")?"WBD_DIAG_RESULT ":
                mode.equals("ipv6gate")?"WBD_IPV6_RESULT ":
                mode.equals("tethergate")?"WBD_TETHER_RESULT ":
                mode.equals("routegate")?"":""; // routegate / exercise return plain JSON
            int a=marker.isEmpty()?output.indexOf('{'):output.indexOf(marker);
            if(a<0){
                r.put("status","NATIVE_NO_RESULT");
                r.put("reason","native did not produce JSON; Root manager policy, SELinux or executable loader may block it");
                r.put("stdout_stderr_excerpt",output.substring(0,Math.min(3000,output.length())));
                return r;
            }
            int from=marker.isEmpty()?a:a+marker.length();
            String body=output.substring(from).trim();
            if(!marker.isEmpty()){
                int next=body.indexOf('\n');
                if(next>=0)body=body.substring(0,next).trim();
            }
            JSONObject nativeJson=new JSONObject(body);
            r.put("native",nativeJson);
            r.put("status",nativeJson.optString("status","UNVERIFIED"));
            if(process.exitValue()!=0 && "SUPPORTED_IN_SCOPE".equals(r.optString("status")))
                r.put("status","FAIL");
            return r;
        }catch(IOException e){return failed("SU_UNAVAILABLE",
            "Root manager did not provide su, or exec denied by Android SELinux: "+e);}
        catch(Exception e){return failed("NATIVE_EXCEPTION",e.toString());}
        finally{if(process!=null)process.destroy();}
    }
    private static String statusOf(JSONObject run){
        String s=run.optString("status","NOT_RUN");
        if(s.equals("SUPPORTED_IN_SCOPE"))return PASS;
        if(s.equals("PERMISSION_DENIED")||s.equals("SU_UNAVAILABLE"))return "PERMISSION_DENIED";
        if(s.equals("UNAVAILABLE")||s.equals("ENV_BLOCKED")||
           s.equals("NATIVE_MISSING")||s.equals("ROOT_TIMEOUT"))return BLOCKED;
        return FAIL;
    }
    private static String reasonOf(JSONObject n){
        String out=n.optString("reason");
        if(out.length()>0)return out;
        out=n.optString("error");
        if(out.length()>0)return out;
        out=n.optString("evidence");
        if(out.length()>0)return out;
        if(n.has("errno"))return "errno="+n.opt("errno");
        return n.optString("action",n.optString("status","no reason"));
    }
    private JSONObject caseItem(String id,String title,String status,String reason,JSONObject evidence)throws Exception {
        JSONObject x=new JSONObject();
        x.put("id",id);x.put("title",title);x.put("status",status);
        x.put("reason",reason);x.put("evidence",evidence);
        return x;
    }
    private void putRun(JSONArray cases,String id,String title,JSONObject run)throws Exception {
        JSONObject nativeValue=run.optJSONObject("native");
        cases.put(caseItem(id,title,statusOf(run),
            reasonOf(nativeValue!=null?nativeValue:run),run));
    }
    private void run(boolean thorough){
        JSONObject report=new JSONObject();
        JSONArray cases=new JSONArray();
        try{
            report.put("schema","wbd-android-root-ondevice-diagnostic/v1");
            report.put("source",assetText("wbd-diagnostic-source.txt"));
            report.put("timestamp_unix_ms",System.currentTimeMillis());
            report.put("app_uid",Process.myUid());
            report.put("target_sdk",getApplicationInfo().targetSdkVersion);
            report.put("sdk",Build.VERSION.SDK_INT);
            report.put("abi",Build.SUPPORTED_ABIS.length>0?Build.SUPPORTED_ABIS[0]:"UNKNOWN");
            report.put("kernel_page_size","native devicecheck");
            report.put("package",getPackageName());
            report.put("native_lib_present",new File(nativePath()).isFile());
            report.put("network_readonly",networkSnapshot());
            report.put("tests",cases);
            JSONObject root=nativeCommand("devicecheck");
            JSONObject identity=root.optJSONObject("native")==null?null:root.optJSONObject("native").optJSONObject("identity");
            boolean actualRoot="SUPPORTED_IN_SCOPE".equals(root.optString("status")) &&
                identity!=null&&identity.optInt("uid",-1)==0&&identity.optInt("euid",-1)==0;
            cases.put(caseItem("app_su","普通应用→已安装 su→实际 UID0",
                actualRoot?PASS:statusOf(root),
                actualRoot?"真实 UID0 已观察；SELinux 与 caps 仍须分项检查":reasonOf(root),root));
            if(actualRoot){
                JSONObject caps=identity;
                boolean netadmin=caps.optBoolean("cap_net_admin"),netraw=caps.optBoolean("cap_net_raw");
                cases.put(caseItem("cap_net_admin","Root CAP_NET_ADMIN",netadmin?PASS:"PERMISSION_DENIED",
                    "CapEff="+caps.optString("cap_effective_hex")+"; SELinux="+caps.optString("selinux_context"),caps));
                cases.put(caseItem("cap_net_raw","Root CAP_NET_RAW",netraw?PASS:"PERMISSION_DENIED",
                    "CapEff="+caps.optString("cap_effective_hex"),caps));
            }else{
                cases.put(caseItem("cap_net_admin","Root CAP_NET_ADMIN","NOT_RUN","Root 未验证",root));
                cases.put(caseItem("cap_net_raw","Root CAP_NET_RAW","NOT_RUN","Root 未验证",root));
            }
            if(thorough&&actualRoot){
                JSONObject exercised=nativeCommand("exercise");
                JSONObject x=exercised.optJSONObject("native");
                JSONObject check=x==null?null:x.optJSONObject("checks");
                for(String id:new String[]{"tun","raw_tcp"}){
                    JSONObject checkValue=check==null?null:check.optJSONObject(id);
                    String title=id.equals("tun")?"真实内核 TUN IPv4 双向 UDP":"真实 RAW IPv4/TCP socket";
                    String stat=checkValue==null?"NOT_RUN":statusOf(checkValue);
                    String why=checkValue==null?reasonOf(exercised):reasonOf(checkValue);
                    cases.put(caseItem(id,title,stat,why,checkValue==null?exercised:checkValue));
                }
                putRun(cases,"ipv6_tun","隔离网络命名空间 IPv6 TUN 双向 UDP",nativeCommand("ipv6gate"));
                putRun(cases,"policy_route","隔离网络命名空间 SO_MARK/策略路由",nativeCommand("routegate"));
                putRun(cases,"synthetic_tether_nat",
                    "隔离网内 2 Wi-Fi + 1 USB 合成客户端 SNAT/反向 conntrack",
                    nativeCommand("tethergate"));
            }else{
                for(String id:new String[]{"tun","raw_tcp","ipv6_tun","policy_route","synthetic_tether_nat"}){
                    cases.put(caseItem(id,id,"NOT_RUN",
                        thorough?"Root 未验证，拒绝尝试特权操作":"用户选择只读预检",root));
                }
            }
            // Never assert physical hotspot/USB success from a synthetic TUN:
            cases.put(caseItem("physical_wifi_hotspot","真实 Wi-Fi 热点下游 VPN","NOT_RUN",
                "需实际开启系统热点、连接另一台设备，验证其包进入真实 WBD TUN/服务器；本 APK 不建立 VPN",root));
            cases.put(caseItem("physical_usb_tether","真实 USB 共享下游 VPN","NOT_RUN",
                "需 USB 下游设备、真实系统 Tethering 出入口计数及双向回包；本 APK 不建立 VPN",root));
            cases.put(caseItem("offload_bypass","实际 eBPF/硬件转发是否绕过 TUN","NOT_RUN",
                "必须在实际下游业务中对照 BPF/offload 与 TUN 计数",root));
            cases.put(caseItem("cellular_raw_switch","实体 Wi-Fi↔蜂窝 raw 出口和 CLAT","NOT_RUN",
                "需要物理蜂窝网络和切网业务",root));
            cases.put(caseItem("foreground_service","target37 后台存活与系统前台服务","NOT_RUN",
                "本 APK 是短时 Activity，不执行持久 VPN 服务",root));
            cases.put(caseItem("production_wbd","WBD 标准 TLS 加密隧道真实端到端","NOT_RUN",
                "尚未移植产品 Rust+冷控制；本 APK 只诊断内核必要能力",root));
            boolean tun=false,raw=false;
            for(int i=0;i<cases.length();i++){
                JSONObject item=cases.optJSONObject(i);
                if("tun".equals(item.optString("id")))tun=PASS.equals(item.optString("status"));
                if("raw_tcp".equals(item.optString("id")))raw=PASS.equals(item.optString("status"));
            }
            report.put("root_verified",actualRoot);
            report.put("core_ipv4_eligibility",actualRoot&&tun&&raw?"CORE_IPV4_ROOT_PROBE_PASS":
                thorough?"CORE_IPV4_ROOT_PROBE_NOT_READY":"NOT_RUN_READONLY");
            report.put("production_wifi_usb_vpn","NOT_RUN");
            report.put("overall",actualRoot&&tun&&raw?
                "ROOT_KERNEL_PREREQUISITES_PASS_PRODUCTION_UNVERIFIED":
                "NOT_READY_OR_NOT_FULLY_TESTED");
            report.put("important_warning","本 APK 不能获取 Root、不建立 VPN、不关闭 SELinux/offload、不修改系统默认路由；隔离命名空间测试不等于真实热点/USB支持。");
        }catch(Exception e){
            try{report.put("overall","FAIL");report.put("fatal_error",e.toString());}
            catch(Exception ignored){}
        }
        try(FileOutputStream out=openFileOutput("last-device-diagnostic.json",MODE_PRIVATE)){
            out.write(report.toString(2).getBytes(StandardCharsets.UTF_8));
        }catch(Exception e){Log.e(TAG,"cannot save diagnostic report",e);}
        lastReport=report;
        runOnUiThread(()->{
            showReport(report);
            basic.setEnabled(true);full.setEnabled(true);
            share.setEnabled(true);copy.setEnabled(true);
        });
    }
    private void showReport(JSONObject report){
        StringBuilder b=new StringBuilder();
        b.append("结论：").append(report.optString("overall","NOT_RUN")).append("\n")
         .append("核心 Root IPv4：").append(report.optString("core_ipv4_eligibility","NOT_RUN")).append("\n")
         .append("真实 Wi-Fi 热点 / USB VPN：NOT_RUN（该 APK 不能搭建实际隧道）\n\n");
        JSONArray a=report.optJSONArray("tests");
        if(a!=null){
            for(int i=0;i<a.length();i++){
                JSONObject t=a.optJSONObject(i);if(t==null)continue;
                b.append(t.optString("title")).append("：").append(t.optString("status")).append("\n")
                 .append("  ").append(t.optString("reason")).append("\n\n");
            }
        }
        b.append("测试报告保存在 App 私有文件；点“分享报告”可导出。\n")
         .append("安全：本程序不会执行 ip rule flush 或关闭 SELinux。\n")
         .append("如果本次探针结束，非持久 TUN 关闭即消失；无法修复其他 Root 软件的规则。");
        summary.setText(b.toString());
    }
    private void launch(boolean thorough){
        basic.setEnabled(false);full.setEnabled(false);share.setEnabled(false);copy.setEnabled(false);
        summary.setText("正在执行 "+(thorough?"Root 能力实测":"Root 只读预检")+
            "。如出现 su 授权弹窗，请明确允许本诊断 App。\n不会更改主系统默认路由…");
        new Thread(()->run(thorough),"wbd-root-selftest").start();
    }
    private void shareReport(){
        if(lastReport==null)return;
        Intent intent=new Intent(Intent.ACTION_SEND);
        intent.setType("application/json");
        intent.putExtra(Intent.EXTRA_TEXT,lastReport.toString());
        startActivity(Intent.createChooser(intent,"分享 WBD Root 诊断 JSON"));
    }
    private void copyReport(){
        if(lastReport==null)return;
        ClipboardManager cb=(ClipboardManager)getSystemService(Context.CLIPBOARD_SERVICE);
        if(cb!=null)cb.setPrimaryClip(ClipData.newPlainText("WBD Root diagnostic",lastReport.toString()));
    }
    @Override public void onCreate(Bundle state){
        super.onCreate(state);
        ScrollView outer=new ScrollView(this);
        LinearLayout v=new LinearLayout(this);v.setOrientation(LinearLayout.VERTICAL);
        v.setPadding(24,112,24,28);
        TextView title=new TextView(this);title.setTextSize(20);
        title.setText("WBD Android Root 上机诊断\n只测条件，不建立真实 VPN");
        v.addView(title);
        basic=new Button(this);basic.setText("1. Root 授权与系统只读预检");
        basic.setOnClickListener(x->launch(false));v.addView(basic);
        full=new Button(this);full.setText("2. 运行短时 Root / TUN / RAW / NAT 完整检测");
        full.setOnClickListener(x->launch(true));v.addView(full);
        share=new Button(this);share.setText("分享报告 JSON");
        share.setOnClickListener(x->shareReport());v.addView(share);
        copy=new Button(this);copy.setText("复制报告 JSON");
        copy.setOnClickListener(x->copyReport());v.addView(copy);
        summary=new TextView(this);summary.setTextSize(13);
        summary.setText("本 App 不提供 Root 和 WBD VPN。\n\n先安装现有 Root 管理器并明确授权本 App，再按顺序执行 1 和 2。\n"+
            "Root 测试只创建可回收 TUN、raw localhost socket，或新的独立网络命名空间；不修改手机默认路由。\n"+
            "真实 Wi-Fi 热点/USB 需要另一台设备配合，报告中严格标 NOT_RUN。\n\n"+
            "测试完成分享 JSON；如失败会给出 errno/原生原因、SELinux 域和必要内核特性。");
        v.addView(summary);outer.addView(v);setContentView(outer);
        try(FileInputStream in=openFileInput("last-device-diagnostic.json")){
            ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] buf=new byte[1024];int n;
            while((n=in.read(buf))!=-1){if(out.size()+n>80000)break;out.write(buf,0,n);}
            lastReport=new JSONObject(out.toString("UTF-8"));
            showReport(lastReport);
        }catch(Exception ignored){}
    }
}
