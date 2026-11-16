package org.wbdnext.rootprobe;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Rect;
import android.view.View;
import android.os.SystemClock;
import android.content.pm.PackageManager;
import android.text.InputType;
import android.widget.*;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.WindowManager;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
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
    // View locations are a debug-only black-box input witness. CI reads only
    // screen rectangles and still has to send real Android touch events and
    // verify native Root readback. It does not synthesize a config or call
    // any click handler internally.
    private final LinkedHashMap<String,View> viewWitness=new LinkedHashMap<>();
    private long witnessLastMs=0;
    private String lastUiAction="opened";
    private void noteUiAction(String value){
        lastUiAction=value;
        witnessLastMs=0;
        if(packageInput!=null) packageInput.post(()->emitVisibleBounds());
    }
    private void emitVisibleBounds(){
        long now=SystemClock.elapsedRealtime();
        if(now-witnessLastMs<120 || viewWitness.size()<3)return;
        witnessLastMs=now;
        try{
            JSONObject result=new JSONObject();
            result.put("schema","wbd-split-real-android-view-bounds/v1");
            result.put("activity","SplitSettingsActivity");
            result.put("default_mode",mode(defaultMode));
            result.put("app_mode",mode(appMode));
            result.put("last_action",lastUiAction);
            result.put("override_count",appOverrides.size());
            result.put("package_char_count",packageInput==null?0:packageInput.length());
            result.put("status_preview",status==null?"":status.getText().toString().substring(0,
                Math.min(220,status.getText().length())));
            result.put("save_enabled",saveButton!=null&&saveButton.isEnabled());
            result.put("window_focused",getWindow().getDecorView().hasWindowFocus());
            android.view.WindowInsets insets=getWindow().getDecorView().getRootWindowInsets();
            result.put("ime_visible",android.os.Build.VERSION.SDK_INT>=30&&
                 insets!=null&&insets.isVisible(android.view.WindowInsets.Type.ime()));
            JSONObject views=new JSONObject();
            for(Map.Entry<String,View> entry:viewWitness.entrySet()){
                Rect area=new Rect();
                boolean exists=entry.getValue().isShown() &&
                    entry.getValue().getGlobalVisibleRect(area);
                JSONObject row=new JSONObject();
                row.put("visible",exists && area.top>=80 && area.width()>=30 && area.height()>=24);
                row.put("focused",entry.getValue().hasFocus());
                row.put("left",area.left);row.put("top",area.top);
                row.put("right",area.right);row.put("bottom",area.bottom);
                views.put(entry.getKey(),row);
            }
            result.put("controls",views);
            try(FileOutputStream out=openFileOutput("wbd-split-ui-bounds.json",MODE_PRIVATE)){
                out.write(result.toString().getBytes(StandardCharsets.UTF_8));
            }
        }catch(Exception e){android.util.Log.w("WBD_SPLIT_VIEW","geometry witness unavailable",e);}
    }

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
        String geoSummary="CN geosite规则未验证";
        try{
            JSONObject geo=new JSONObject(asset(this,"cn-geosite-provenance.json"));
            geoSummary="CN geosite完整导入快照: "+geo.optInt("output_distinct_rules",0)+
                " 条；匹配 exact/suffix/keyword/regexp，仅DNS查询时执行";
        }catch(Exception e){geoSummary="CN geosite快照缺失/无法读取；保存将失败";}
        cnStatus.setText("预装 CN IPv4 分配快照："+rules(bundledCn,32768).size()+
            " 条；属于APNIC CN分配地址，不保证精确地理定位。\n"+
            geoSummary+"。\n自定义CN域名规则仍可追加；无FakeIP。");
    }
    private JSONObject build() throws Exception{
        JSONObject v=new JSONObject();v.put("schema","wbd-android-split/v1");
        v.put("default_mode",mode(defaultMode));
        v.put("direct_dns",directDns.getText().toString().trim());
        v.put("tunnel_dns",tunnelDns.getText().toString().trim());
        ArrayList<String> cidrs=rules(bundledCn,32768);
        ArrayList<String> extraCidrs=rules(customCidr.getText().toString(),32768);
        cidrs.addAll(extraCidrs);
        JSONArray extraJson=new JSONArray();
        for(String cidr:extraCidrs)extraJson.put(cidr);
        v.put("custom_cn_ipv4",extraJson);
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
            if(old!=null)continue; // one policy per UID, not per package alias
            apps.put(new JSONObject().put("uid",uid).put("mode",x.getValue()).put("package",name));
        }
        v.put("apps",apps);
        v.put("cn_rule_provenance","APNIC CN allocation snapshot 2026-11-16; not proof of geography");
        v.put("cn_domain_semantics","DNS direct for fixed geolocation-cn + .cn + custom rules only in split; actual A IP final egress");
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
            JSONArray extras=o.optJSONArray("custom_cn_ipv4");
            if(extras!=null){
                StringBuilder extra=new StringBuilder();
                for(int i=0;i<extras.length();i++)extra.append(extras.optString(i)).append('\n');
                customCidr.setText(extra.toString());
            }
            JSONArray cidrs=o.optJSONArray("cn_ipv4");
            if(cidrs!=null && bundledCn.isEmpty() && extras==null){
                StringBuilder ss=new StringBuilder();
                for(int i=0;i<cidrs.length();i++)ss.append(cidrs.optString(i)).append('\n');
                customCidr.setText(ss.toString());
            }
        }catch(Exception e){status.setText("读取旧配置失败："+e.getMessage());}
    }
    private static String hex(byte[] data){
        StringBuilder sb=new StringBuilder(data.length*2);
        for(byte x:data)sb.append(String.format(java.util.Locale.ROOT,"%02x",x&0xff));
        return sb.toString();
    }
    private String extractOwnedGeosite()throws Exception{
        // An APK-asset digest is verified independently against pinned
        // provenance. A replacement file is fully fsynced and renamed before
        // publishing its expected hash in wbd-split-settings.json.
        JSONObject manifest=new JSONObject(asset(this,"cn-geosite-provenance.json"));
        String expected=manifest.optString("text_sha256","");
        if(!expected.matches("[0-9a-f]{64}"))
            throw new IOException("CN geosite provenance digest missing");
        MessageDigest md=MessageDigest.getInstance("SHA-256");
        File dst=new File(getFilesDir(),"wbd-cn-geosite.txt");
        File tmp=new File(getFilesDir(),"wbd-cn-geosite.txt.tmp");
        long length=0;
        try(InputStream in=getAssets().open("wbd-cn-geosite.txt");
            FileOutputStream out=new FileOutputStream(tmp)){
            byte[] buf=new byte[8192];int n;
            while((n=in.read(buf))!=-1){
                length+=n;
                if(length>=6000000)throw new IOException("CN geosite exceeds 6MiB hard limit");
                md.update(buf,0,n);out.write(buf,0,n);
            }
            out.getFD().sync();
        }catch(Exception e){tmp.delete();throw e;}
        String actual=hex(md.digest());
        if(length<10000||!expected.equals(actual)){
            tmp.delete();
            throw new IOException("pinned geosite hash mismatch / incomplete asset");
        }
        if(!tmp.renameTo(dst)){tmp.delete();throw new IOException("geosite atomic rename failed");}
        return actual;
    }
    private void atomicSave(JSONObject data)throws Exception{
        data.put("geosite_sha256",extractOwnedGeosite());
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
                    "，CN geosite "+j.optJSONObject("geosite").optInt("total_rules")+" 条"+
                    "，隔离DNS UDP/53："+(j.optJSONObject("dns_udp_gate")==null?
                         "NOT_RUN":j.optJSONObject("dns_udp_gate").optString("status"))+
                    "，每App覆盖 "+j.optJSONArray("per_app_modes").length()+
                    "。\n**未安装到 Android 主网络，也未接入 WBD VPN。**";
            return st+"："+j.optString("reason","无具体原因");
        }catch(Exception e){return "ENV_BLOCKED：su/配置验证失败 "+e;}
        finally{if(p!=null)p.destroy();}
    }
    @Override public void onCreate(Bundle b){
        super.onCreate(b);
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN | WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        bundledCn=asset(this,SOURCE);
        ScrollView scroll=new ScrollView(this);
        LinearLayout panel=new LinearLayout(this);panel.setOrientation(LinearLayout.VERTICAL);
        panel.setFocusableInTouchMode(true);
        panel.setPadding(24,112,24,36);
        panel.requestFocus();
        TextView headline=new TextView(this);headline.setTextSize(19);
        headline.setText("Android Root 分流配置（无 FakeIP）\n"+
            "当前仅保存/验证策略；正式 WBD 接线后才可启用，不会擅自改手机路由。");
        panel.addView(headline);
        Button quickDns=new Button(this);
        quickDns.setText("一键验证CN域名及双DNS内核收发（不启用VPN）");
        panel.addView(quickDns);
        defaultMode=modes(panel,"默认模式（可按 App 单独覆盖）",true);
        directDns=field(panel,"CN 域名直连 DNS（单地址，无备用）","223.5.5.5",1);
        tunnelDns=field(panel,"其他域名隧道 DNS（单地址，无跨出口回退）","1.1.1.1",1);
        cnStatus=new TextView(this);panel.addView(cnStatus);
        domainInput=field(panel,"额外 CN 域名：每行一个后缀或 =完全匹配（不使用 FakeIP）","",3);
        customCidr=field(panel,"手动额外 CN IPv4 CIDR：每行一条（预装列表外自定义）","",2);
        packageInput=field(panel,"单独设置某 App：填写完整包名（或 uid:10482）","",1);
        packageInput.setInputType(InputType.TYPE_CLASS_TEXT|
            InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
        packageInput.setSelectAllOnFocus(true);
        packageInput.setOnFocusChangeListener((v,focused)->{
            noteUiAction(focused?"package_focused":"package_unfocused");
        });
        packageInput.addTextChangedListener(new TextWatcher(){
            @Override public void beforeTextChanged(CharSequence s,int start,int count,int after){}
            @Override public void onTextChanged(CharSequence s,int start,int before,int count){
                // Expose the field's *length* to test driver after real typing,
                // never its actual package name or user-entered string.
                noteUiAction("package_text_changed");
            }
            @Override public void afterTextChanged(Editable text){}
        });
        // A user-visible, emulator-only diagnostic fallback lets CI prove
        // actual Android touch->Add->Save->Root readback even if the low-memory
        // AVD IME refuses focus. Never available on physical phones.
        Button emulatorSample=null;
        if("ranchu".equalsIgnoreCase(android.os.Build.HARDWARE) &&
           (android.os.Build.FINGERPRINT.contains("generic") || android.os.Build.FINGERPRINT.contains("sdk_gphone"))){
            emulatorSample=new Button(this);
            emulatorSample.setText("模拟器测试：填入演示 UID10502");
            emulatorSample.setOnClickListener(v->{
                packageInput.setText("uid:10502");
                noteUiAction("sample_fill_clicked");
            });
            panel.addView(emulatorSample);
        }
        appMode=modes(panel,"该 App 选用的模式",false);
        Button add=new Button(this);add.setText("添加/覆盖此 App 的模式");
        add.setOnClickListener(v->{
            String p=packageInput.getText().toString().trim();
            if(!p.matches("[A-Za-z][A-Za-z0-9_.]{2,180}")&&!p.matches("uid:[1-9][0-9]{4,6}")){
                status.setText("请填写有效的已安装 App 包名或 uid:数字");
                noteUiAction("add_invalid_package");return;
            }
            appOverrides.put(p,mode(appMode));refresh();
            noteUiAction("add_clicked");
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
            noteUiAction("save_clicked");
            JSONObject config;
            try{config=build();}catch(Exception e){
                status.setText("FAIL：配置错误 "+e.getMessage());
                noteUiAction("save_config_error");return;
            }
            saveButton.setEnabled(false);
            status.setText("正在原子保存并运行 Root 只读策略验证…");
            noteUiAction("save_started");
            new Thread(()->{
                String result;
                try{atomicSave(config);result=verifyNative();}
                catch(Exception e){result="FAIL：保存失败 "+e;}
                String line=result;
                runOnUiThread(()->{status.setText(line);saveButton.setEnabled(true);noteUiAction("save_completed");});
            },"wbd-android-split-validate").start();
        });
        if(emulatorSample!=null)viewWitness.put("sample",emulatorSample);
        // This is an ordinary user-initiated App button, not hidden CI
        // injection. Use EXACTLY the same save/Root validation onClick path.
        // Does not toggle network routing; native reports installed=false.
        quickDns.setOnClickListener(v->{
            noteUiAction("quick_dns_clicked");
            saveButton.performClick();
        });
        viewWitness.put("quick_dns_check",quickDns);
        viewWitness.put("package",packageInput);
        viewWitness.put("app_mode",appMode);
        viewWitness.put("add",add);
        viewWitness.put("save",saveButton);
        viewWitness.put("default_mode",defaultMode);
        scroll.setOnScrollChangeListener((v,sx,sy,ox,oy)->{
            emitVisibleBounds();
        });
        // An App row is added to appsView between Add and Save; its layout
        // pushes the Save button down without necessarily changing scrollY.
        // Record actual post-layout rectangles before the next real tap.
        panel.addOnLayoutChangeListener((v,left,top,right,bottom,oldLeft,oldTop,oldRight,oldBottom)->{
            if(bottom!=oldBottom||right!=oldRight){
                witnessLastMs=0;
                panel.post(()->emitVisibleBounds());
            }
        });
        scroll.addView(panel);setContentView(scroll);
        scroll.post(()->emitVisibleBounds());
        restoreSaved();refresh();
        noteUiAction("opened");
    }
}
