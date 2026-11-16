package org.wbdnext.rootprobe;

import android.app.Activity;
import android.os.Bundle;
import android.content.pm.PackageManager;
import android.text.InputType;
import android.widget.*;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.TimeUnit;

/**
 * Android Root CN/global mode editor; configuration only, NOT an OS network
 * installer or a claim that the production WBD tunnel is wired. No FakeIP.
 *
 * The native owner must revalidate package->UID bindings, policy generation,
 * underlay, route journal, DNS endpoints and live WBD admission before Apply.
 * DNS is classified once by QNAME, subsequent real IP data by CN IPv4 CIDRs.
 */
public final class SplitSettingsActivity extends Activity {
    private Spinner defaultMode,appMode;
    private EditText directDns,tunnelDns,domainInput,customCidr,packageInput;
    private TextView status,appsView,cnStatus;
    private Button saveButton;
    private final TreeMap<String,String> appOverrides=new TreeMap<>();
    private String bundledCn="";
    private String previousCustom="";
    private static final String SOURCE="wbd-cn-ipv4.txt";

    private EditText field(LinearLayout panel,String title,String initial,int rows){
        TextView label=new TextView(this);label.setText(title);label.setTextSize(15);
        panel.addView(label);
        EditText edit=new EditText(this);edit.setSingleLine(rows==1);
        if(rows>1){edit.setMinLines(rows);edit.setMaxLines(Math.max(rows,7));}
        edit.setText(initial);panel.addView(edit);return edit;
    }
    private Spinner modes(LinearLayout panel,String title,boolean splitDefault){
        TextView label=new TextView(this);label.setText(title);panel.addView(label);
        Spinner s=new Spinner(this);
        ArrayAdapter<String> a=new ArrayAdapter<>(this,android.R.layout.simple_spinner_item,
            new String[]{"split — 中国 IP/LAN 直连","global — 全部业务走 WBD"});
        a.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        s.setAdapter(a);s.setSelection(splitDefault?0:1);panel.addView(s);return s;
    }
    private static String mode(Spinner s){return s.getSelectedItemPosition()==0?"split":"global";}
    private static String asset(Activity activity,String filename){
        try(InputStream in=activity.getAssets().open(filename)){
            ByteArrayOutputStream out=new ByteArrayOutputStream();
            byte[] b=new byte[8192];int n;
            while((n=in.read(b))!=-1){
                if(out.size()+n>600000)throw new IOException("CN snapshot too large");
                out.write(b,0,n);
            }
            return out.toString("UTF-8");
        }catch(IOException e){return "";}
    }
    private static ArrayList<String> rules(String raw,int hard){
        ArrayList<String> all=new ArrayList<>();
        for(String line:raw.split("\\r?\\n")){
            String trim=line.trim();
            if(trim.isEmpty()||trim.startsWith("#"))continue;
            if(trim.length()>256)throw new IllegalArgumentException("规则过长");
            all.add(trim);
            if(all.size()>hard)throw new IllegalArgumentException("规则数量超过 "+hard);
        }
        return all;
    }
    private void refresh(){
        appsView.setText("每 App 独立路由模式（按包名保存，执行前须重新校验 UID）：\n"+
            (appOverrides.isEmpty()?"无覆盖规则":appOverrides.toString()));
        cnStatus.setText("预装 CN IPv4 分配快照："+rules(bundledCn,32768).size()+
            " 条；属于 APNIC CN 分配地址，不保证完整地理定位。\n"+
            "CN 域名默认包括 .cn；其他中国域名可在下面自定义。");
    }
    private JSONObject build() throws Exception{
        JSONObject v=new JSONObject();v.put("schema","wbd-android-split/v1");
        v.put("default_mode",mode(defaultMode));
        v.put("direct_dns",directDns.getText().toString().trim());
        v.put("tunnel_dns",tunnelDns.getText().toString().trim());
        ArrayList<String> cidrs=rules(bundledCn,32768);
        cidrs.addAll(rules(customCidr.getText().toString(),32768));
        JSONArray ranges=new JSONArray();
        for(String s:cidrs)ranges.put(s);v.put("cn_ipv4",ranges);
        JSONArray customDomains=new JSONArray();
        for(String d:rules(domainInput.getText().toString(),20000))customDomains.put(d);
        v.put("cn_domains",customDomains);
        v.put("direct_ipv4",new JSONArray());
        JSONArray apps=new JSONArray();
        HashMap<Integer,String> uids=new HashMap<>();
        for(Map.Entry<String,String> x:appOverrides.entrySet()){
            String name=x.getKey();
            int uid;
            if(name.startsWith("uid:"))uid=Integer.parseInt(name.substring(4));
            else {
                // This explicit package must be currently installed and visible.
                // Avoid broad dynamic UID guesses. Users may provide uid:NNNN
                // when OEM package-visibility restrictions prevent lookup.
                uid=getPackageManager().getPackageUid(name,0);
            }
            if(uid<10000)throw new IllegalArgumentException("只允许普通应用 UID >=10000: "+name);
            String old=uids.put(uid,x.getValue());
            if(old!=null && !old.equals(x.getValue()))throw new IllegalArgumentException(
                "共享 UID 存在互相冲突的模式，无法按包名隔离: "+name);
            apps.put(new JSONObject().put("uid",uid).put("mode",x.getValue()).put("package",name));
        }
        v.put("apps",apps);
        v.put("cn_rule_provenance","APNIC CN allocation snapshot 2026-11-16; not proof of geography");
        v.put("cn_domain_semantics","DNS direct for .cn+custom only in split; actual A IP final egress");
        v.put("server_bootstrap","always physical direct in split and global; no spare resolver");
        v.put("no_fakeip",true);
        return v;
    }
    private void restoreSaved(){
        File f=new File(getFilesDir(),"wbd-split-settings.json");
        if(!f.isFile())return;
        try{
            byte[] raw=new byte[(int)Math.min(1000000,f.length())];
            try(FileInputStream in=new FileInputStream(f)){
                int p=0,n;while(p<raw.length&&(n=in.read(raw,p,raw.length-p))>0)p+=n;
                raw=Arrays.copyOf(raw,p);
            }
            JSONObject o=new JSONObject(new String(raw,StandardCharsets.UTF_8));
            defaultMode.setSelection("global".equals(o.optString("default_mode"))?1:0);
            directDns.setText(o.optString("direct_dns","223.5.5.5"));
            tunnelDns.setText(o.optString("tunnel_dns","1.1.1.1"));
            JSONArray domains=o.optJSONArray("cn_domains");
            StringBuilder dd=new StringBuilder();
            if(domains!=null)for(int i=0;i<domains.length();i++)
                dd.append(domains.optString(i)).append('\n');
            domainInput.setText(dd.toString());
            // Kept for user edit; app mappings have UID-only persisted form:
            // display as uid:NNNN so invalid/reinstalled old package mappings
            // never silently apply to unrelated UIDs without re-validation.
            JSONArray apps=o.optJSONArray("apps");
            if(apps!=null)for(int i=0;i<apps.length();i++){
                JSONObject x=apps.optJSONObject(i);if(x==null)continue;
                appOverrides.put(x.optString("package","uid:"+x.optInt("uid")),x.optString("mode"));
            }
            JSONArray cidrs=o.optJSONArray("cn_ipv4");
            if(cidrs!=null && bundledCn.isEmpty()){
                StringBuilder ss=new StringBuilder();
                for(int i=0;i<cidrs.length();i++)ss.append(cidrs.optString(i)).append('\n');
                customCidr.setText(ss.toString());
            }
        }catch(Exception e){status.setText("读取旧配置失败："+e.getMessage());}
    }
    private void atomicSave(JSONObject data)throws Exception{
        File dst=new File(getFilesDir(),"wbd-split-settings.json");
        File tmp=new File(getFilesDir(),"wbd-split-settings.json.tmp");
        byte[] bytes=data.toString().getBytes(StandardCharsets.UTF_8);
        if(bytes.length>2*1024*1024)throw new IOException("配置过大");
        try(FileOutputStream o=new FileOutputStream(tmp)){
            o.write(bytes);o.getFD().sync();
        }
        if(!tmp.renameTo(dst)){tmp.delete();throw new IOException("配置原子替换失败");}
    }
    private String verifyNative(){
        File bin=new File(getApplicationInfo().nativeLibraryDir,"libwbdprobe.so");
        if(!bin.isFile())return "FAIL 原生程序缺失 (ABI/安装故障)";
        File cfg=new File(getFilesDir(),"wbd-split-settings.json");
        java.lang.Process p=null;
        try{
            p=new ProcessBuilder("su","-c",bin.getAbsolutePath()+" splitvalidate "+
                cfg.getAbsolutePath()).redirectErrorStream(true).start();
            java.lang.Process child=p;
            ByteArrayOutputStream raw=new ByteArrayOutputStream();
            Thread reader=new Thread(()->{
                try(InputStream i=child.getInputStream()){
                    byte[] b=new byte[512];int n;
                    while((n=i.read(b))!=-1){
                        if(raw.size()+n<10000)raw.write(b,0,n);
                    }
                }catch(Exception ignored){}
            });reader.setDaemon(true);reader.start();
            boolean finished=p.waitFor(15,TimeUnit.SECONDS);
            if(!finished)p.destroyForcibly();
            reader.join(1000);
            String text=raw.toString("UTF-8");
            String marker="WBD_SPLIT_CONFIG_RESULT ";
            int pos=text.indexOf(marker);
            if(!finished)return "ENV_BLOCKED：Root授权／命令超时；配置保存但未应用";
            if(pos<0)return "ENV_BLOCKED：su或原生调用没有产生验证JSON\n"+text.substring(0,Math.min(1500,text.length()));
            JSONObject j=new JSONObject(text.substring(pos+marker.length()).trim().split("\\n")[0]);
            try(FileOutputStream out=openFileOutput("wbd-split-validation.json",MODE_PRIVATE)){
                out.write(j.toString(2).getBytes(StandardCharsets.UTF_8));
            }
            String st=j.optString("status","FAIL");
            if("SUPPORTED_IN_SCOPE".equals(st))
                return "配置语义校验 PASS：CIDR合并区间 "+j.optInt("compiled_cn_ipv4_intervals")+
                    "，每App覆盖 "+j.optJSONArray("per_app_modes").length()+
                    "。\n**未安装到 Android 主网络，也未接入 WBD VPN。**";
            return st+"："+j.optString("reason","无具体原因");
        }catch(Exception e){return "ENV_BLOCKED：su/配置验证失败 "+e;}
        finally{if(p!=null)p.destroy();}
    }
    @Override public void onCreate(Bundle b){
        super.onCreate(b);
        bundledCn=asset(this,SOURCE);
        ScrollView scroll=new ScrollView(this);
        LinearLayout panel=new LinearLayout(this);panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(24,112,24,36);
        TextView headline=new TextView(this);headline.setTextSize(19);
        headline.setText("Android Root 分流配置（无 FakeIP）\n"+
            "当前仅保存/验证策略；正式 WBD 接线后才可启用，不会擅自改手机路由。");
        panel.addView(headline);
        defaultMode=modes(panel,"默认模式（可按 App 单独覆盖）",true);
        directDns=field(panel,"CN 域名直连 DNS（单地址，无备用）","223.5.5.5",1);
        tunnelDns=field(panel,"其他域名隧道 DNS（单地址，无跨出口回退）","1.1.1.1",1);
        cnStatus=new TextView(this);panel.addView(cnStatus);
        domainInput=field(panel,"额外 CN 域名：每行一个后缀或 =完全匹配（不使用 FakeIP）","",3);
        customCidr=field(panel,"手动额外 CN IPv4 CIDR：每行一条（预装列表外自定义）","",2);
        packageInput=field(panel,"单独设置某 App：填写完整包名（或 uid:10482）","",1);
        appMode=modes(panel,"该 App 选用的模式",false);
        Button add=new Button(this);add.setText("添加/覆盖此 App 的模式");
        add.setOnClickListener(v->{
            String p=packageInput.getText().toString().trim();
            if(!p.matches("[A-Za-z][A-Za-z0-9_.]{2,180}")&&!p.matches("uid:[1-9][0-9]{4,6}")){
                status.setText("请填写有效的已安装 App 包名或 uid:数字");return;
            }
            appOverrides.put(p,mode(appMode));refresh();
        });panel.addView(add);
        Button clear=new Button(this);clear.setText("清空单独 App 覆盖");
        clear.setOnClickListener(v->{appOverrides.clear();refresh();});panel.addView(clear);
        appsView=new TextView(this);panel.addView(appsView);
        saveButton=new Button(this);saveButton.setText("保存并经 Root 验证策略（不会修改系统网络）");
        panel.addView(saveButton);
        status=new TextView(this);status.setTextSize(14);
        status.setText("注意：全球模式的普通CN域名DNS也走隧道；"+
            "仅WBD服务器引导DNS和控制连接始终物理直连。\n"+
            "当前没有生产DNS监听器、WBD数据会话、路由持久journal。"+
            "点击保存只确认策略正确，不代表已启用 VPN。");
        panel.addView(status);
        saveButton.setOnClickListener(v->{
            JSONObject config;
            try{config=build();}catch(Exception e){
                status.setText("FAIL：配置错误 "+e.getMessage());return;
            }
            saveButton.setEnabled(false);
            status.setText("正在原子保存并运行 Root 只读策略验证…");
            new Thread(()->{
                String result;
                try{atomicSave(config);result=verifyNative();}
                catch(Exception e){result="FAIL：保存失败 "+e;}
                String line=result;
                runOnUiThread(()->{status.setText(line);saveButton.setEnabled(true);});
            },"wbd-android-split-validate").start();
        });
        scroll.addView(panel);setContentView(scroll);
        restoreSaved();refresh();
    }
}
