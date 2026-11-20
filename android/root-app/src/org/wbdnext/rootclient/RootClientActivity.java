package org.wbdnext.rootclient;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.ClipboardManager;
import java.util.concurrent.atomic.AtomicBoolean;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import java.io.InputStream;
import java.io.OutputStream;
import android.text.InputType;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import java.io.FileOutputStream;
import java.io.File;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

// Independent ARM64 Root product front door: NOT VpnService/Vpn.Builder,
// no Java packet pump, no Java Go/TLS/AEAD, no JNI fake-ready symbols.
public final class RootClientActivity extends Activity {
    private final Handler ui=new Handler(Looper.getMainLooper());
    private final List<PhysicalNetwork> physical=new ArrayList<>();
    private final List<InstalledAppTarget> installedApps=new ArrayList<>();
    private final Map<String,CheckBox> checkedApps=new TreeMap<>();
    private EditText serverAddress,serverName,user,password,routeKey,caPEM,serverPort;
    private Spinner networks;
    private CheckBox allAppsDefault,tlsVerifyServer;
    private LinearLayout appChoices;
    private TextView status,deviceSelfTestResult,diagnosticExportResult;
    private static final int SAFE_DIAGNOSTIC_SAVE=2042;
    private static final int LOCAL_TLS_CA_IMPORT=2043;
    // START can fail before any Service exists. Persist fixed app-only
    // stages so a 0-event TXT is no longer the only device-side evidence.
    private void traceUi(RootDiagnosticReceipt.Event event){
        new RootDiagnosticReceipt(new File(getFilesDir(),
            "wbd-root-diagnostic.txt")).record(event);
    }
    private String signedSource(){
        try(InputStream in=getAssets().open("native-arm64/SOURCE")){
            byte[] data=new byte[128];
            int n=in.read(data);
            return n>0?new String(data,0,n,StandardCharsets.US_ASCII).trim():"";
        }catch(Exception unavailable){return "";}
    }
    private void exportSafeDiagnostic(){
        // SAF lets the user choose where to save a bounded, allowlisted TXT.
        // Never open logcat, root journals, network sockets or native stdout.
        try{
            Intent i=new Intent(Intent.ACTION_CREATE_DOCUMENT);
            i.addCategory(Intent.CATEGORY_OPENABLE);
            i.setType("text/plain");
            i.putExtra(Intent.EXTRA_TITLE,"wbd-root-safe-diagnostic.txt");
            startActivityForResult(i,SAFE_DIAGNOSTIC_SAVE);
        }catch(Exception ignored){
            diagnosticExportResult.setText("无法打开系统文件保存器；未请求 Root 或读取原始日志");
        }
    }
    private void importTLSCA(){
        Intent choose=new Intent(Intent.ACTION_OPEN_DOCUMENT);
        choose.addCategory(Intent.CATEGORY_OPENABLE);
        choose.setType("*/*");
        try{startActivityForResult(choose,LOCAL_TLS_CA_IMPORT);}
        catch(Exception unavailable){status.setText("本地CA文件选择器不可用，可直接粘贴PEM");}
    }
    private void acceptTLSCA(Intent data){
        if(data==null||data.getData()==null)return;
        try(InputStream in=getContentResolver().openInputStream(data.getData());
            ByteArrayOutputStream out=new ByteArrayOutputStream()){
            if(in==null)throw new IllegalArgumentException("unreadable CA");
            byte[] chunk=new byte[4096];
            int n;
            while((n=in.read(chunk))!=-1){
                if(out.size()+n>=RootPrivateCredentialContract.maxBytes(RootPrivateCredentialContract.CA))
                    throw new IllegalArgumentException("CA input too large");
                out.write(chunk,0,n);
            }
            String pem=new String(out.toByteArray(),StandardCharsets.UTF_8).trim();
            if(!pem.startsWith("-----BEGIN CERTIFICATE-----")||
               !pem.contains("-----END CERTIFICATE-----"))
                throw new IllegalArgumentException("not PEM");
            java.util.Collection<? extends java.security.cert.Certificate> certs=
                java.security.cert.CertificateFactory.getInstance("X.509")
                .generateCertificates(new java.io.ByteArrayInputStream(
                    pem.getBytes(StandardCharsets.UTF_8)));
            if(certs.isEmpty())throw new IllegalArgumentException("empty trust set");
            caPEM.setText(pem);
            status.setText("已导入 "+certs.size()+" 张本地TLS证书；勾选严格校验后原Go才使用");
        }catch(Exception failure){
            status.setText("CA导入未成功：请选择有效的受限大小PEM文件，原有配置未更改");
        }
    }
    @Override protected void onActivityResult(int requestCode,int resultCode,Intent data){
        super.onActivityResult(requestCode,resultCode,data);
        if(requestCode==LOCAL_TLS_CA_IMPORT){
            if(resultCode==RESULT_OK)acceptTLSCA(data);
            return;
        }
        if(requestCode!=SAFE_DIAGNOSTIC_SAVE||diagnosticExportResult==null)return;
        if(resultCode!=RESULT_OK||data==null||data.getData()==null){
            diagnosticExportResult.setText("未导出诊断（用户取消或位置不可用）");
            return;
        }
        Uri target=data.getData();
        try{
            String report=RootDiagnosticReport.build(getFilesDir(),
                signedSource(),Build.VERSION.SDK_INT);
            try(OutputStream out=getContentResolver().openOutputStream(target,"wt")){
                if(out==null)throw new java.io.IOException("no output stream");
                out.write(report.getBytes(StandardCharsets.UTF_8));
                out.flush();
            }
            diagnosticExportResult.setText("脱敏诊断 TXT 已保存；可直接分享文件排障，不包含 IP/账号/密钥/日志正文");
        }catch(Exception ignored){
            diagnosticExportResult.setText("导出失败：无法写入所选位置；原生会话与路由不受影响");
        }
    }
    private final AtomicBoolean deviceSelfTestActive=new AtomicBoolean(false);
    private void runDeviceSelfTest(){
        if(deviceSelfTestActive.get())return;
        new AlertDialog.Builder(this)
            .setTitle("Android ARM64 / KernelSU 一键自检")
            .setMessage("不需要服务器地址/用户名/密钥。\n\n将请求 KernelSU Root 授权，" +
                "创建并关闭临时真实 TUN，测试 RAW/物理网络绑定；" +
                "还会用本 APK 自己的 UID 向保留测试地址 192.0.2.1:43999 " +
                "发送一个固定 UDP 测试包，观察它是否经独立策略规则进入临时 TUN。" +
                "仅短暂改本 APK UID 的 table19843/pref9699，立即尝试撤销。" +
                "不会修改默认路由、其他 App UID、原 WBD table19842、" +
                "系统 DNS 或任何 TLS/AEAD 数据面。\n\n" +
                "若路由阶段失败，A12 仅输出固定阶段和内核错误类别，不读取或显示隐私日志。\n\n" +
                "异常被强行杀进程时无法绝对保证回滚；若结果显示回滚失败，请停止后检查。")
            .setNegativeButton("取消",null)
            .setPositiveButton("允许本机测试",(dialog,which)->{
                if(!deviceSelfTestActive.compareAndSet(false,true))return;
                final int pos=networks.getSelectedItemPosition();
                final PhysicalNetwork selected=pos>=0&&pos<physical.size()
                    ?physical.get(pos):null;
                deviceSelfTestResult.setText("正在等待 KernelSU 授权并运行隔离自检…");
                new Thread(()->{
                    String outcome=RootDeviceSelfTest.run(this,selected);
                    runOnUiThread(()->{
                        deviceSelfTestActive.set(false);
                        deviceSelfTestResult.setText(outcome);
                    });
                },"wbd-arm64-ksu-selftest").start();
            }).show();
    }
    private final Runnable refreshStatus=new Runnable(){
        @Override public void run(){
            if(status!=null)status.setText(RootClientService.status);
            ui.postDelayed(this,1000);
        }
    };
    private EditText input(LinearLayout view,String label,int kind){
        TextView title=new TextView(this);
        title.setText(label);
        title.setTextSize(15);
        view.addView(title);
        EditText field=new EditText(this);
        field.setSingleLine(kind!=InputType.TYPE_CLASS_TEXT + InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        field.setInputType(kind);
        view.addView(field);
        return field;
    }
    private void chooseNetworks(){
        physical.clear();
        physical.addAll(PhysicalNetwork.available(this));
        ArrayList<String> labels=new ArrayList<>();
        for(PhysicalNetwork n:physical)labels.add(n.title());
        if(labels.isEmpty())labels.add("NO physical Wi-Fi/cellular IPv4 Network (fail closed)");
        ArrayAdapter<String> adapter=new ArrayAdapter<>(this,
            android.R.layout.simple_spinner_dropdown_item,labels);
        networks.setAdapter(adapter);
    }
    private void chooseInstalledApplications(){
        // Keep only exact package+UID matches from the previous snapshot.
        // A package reinstalled with a new UID is NEVER auto-reselected.
        Map<String,Integer> previous=new TreeMap<>();
        for(InstalledAppTarget app:installedApps){
            CheckBox cb=checkedApps.get(app.packageName);
            if(cb!=null&&cb.isChecked())previous.put(app.packageName,app.uid);
        }
        installedApps.clear();
        checkedApps.clear();
        appChoices.removeAllViews();
        installedApps.addAll(InstalledAppCatalog.launchable(this));
        if(installedApps.isEmpty()){
            TextView message=new TextView(this);
            message.setText("No visible installed launchable user app (fail closed)");
            appChoices.addView(message);
            return;
        }
        for(InstalledAppTarget app:installedApps){
            CheckBox cb=new CheckBox(this);
            cb.setText(app.title());
            cb.setChecked(previous.containsKey(app.packageName)&&
                previous.get(app.packageName)==app.uid);
            appChoices.addView(cb);
            checkedApps.put(app.packageName,cb);
        }
    }
    private void privateText(String file,String text)throws Exception{
        // A32: Android's MODE_PRIVATE can produce 0660 (group read/write).
        // Original Go deliberately accepts only exactly 0600 on an opened fd.
        // The same bounded O_NOFOLLOW, owner-only writer is used for
        // password, the 32B route key and optional TLS CA.
        RootPrivateCredentialFiles.write(this,file,text);
    }
    private void start(){
        traceUi(RootDiagnosticReceipt.Event.UI_START_TAPPED);
        boolean dispatchRequested=false;
        try{
            if(physical.isEmpty())throw new IllegalArgumentException("No real physical Android Network");
            int pos=networks.getSelectedItemPosition();
            if(pos<0||pos>=physical.size())throw new IllegalArgumentException("No selected Network");
            PhysicalNetwork scope=physical.get(pos);
            if(PhysicalNetwork.exact(this,scope.handle,scope.interfaceName,
                scope.ifindex,scope.mtu,scope.address)==null){
                throw new IllegalArgumentException("Selected Network changed; refresh before Start");
            }
            String peer=serverAddress.getText().toString().trim();
            String sni=serverName.getText().toString().trim();
            String account=user.getText().toString().trim();
            String secret=password.getText().toString();
            String keyInput=routeKey.getText().toString(); // never trim/normalize a secret
            String pem=caPEM.getText().toString().trim();
            boolean verifyTLS=tlsVerifyServer.isChecked();
            // Default is full ordinary App UID takeover AFTER true WBD
            // TLS/authenticated /32 and Rust M4. No pre-auth route mutation,
            // no Android system/root UID, VPN, fake-IP or system DNS.
            boolean allApps=allAppsDefault.isChecked();
            SelectedAppGroup chosen=null;
            AllAppRouteScope entire=null;
            if(allApps){
                entire=AllAppRouteScope.snapshot(this);
                if(!AllAppRouteScope.same(this,entire.excludedAppIDs,
                    entire.managerPackages))
                    throw new IllegalArgumentException("Root Manager app identity changed");
            }else{
                ArrayList<InstalledAppTarget> chosenApps=new ArrayList<>();
                for(InstalledAppTarget app:installedApps){
                    CheckBox cb=checkedApps.get(app.packageName);
                    if(cb!=null&&cb.isChecked())chosenApps.add(app);
                }
                if(chosenApps.isEmpty())
                    throw new IllegalArgumentException("Select an installed App or restore all-app mode");
                chosen=SelectedAppGroup.from(chosenApps,
                    android.os.Process.myUid(),getPackageName());
                if(!InstalledAppCatalog.stillSameGroup(this,chosen.packages,chosen.uids))
                    throw new IllegalArgumentException("Selected package/UID changed; refresh");
            }
            int port=Integer.parseInt(serverPort.getText().toString().trim());
            if(!ServerAddress.valid(peer))
                throw new IllegalArgumentException("Invalid real WBD server IPv4/DNS name; use One-Tap Self-Test if no server");
            if(sni.isEmpty()||sni.length()>253)
                throw new IllegalArgumentException("Invalid TLS server name / SNI");
            if(account.isEmpty()||account.length()>128)
                throw new IllegalArgumentException("Invalid original WBD username");
            if(secret.isEmpty()||secret.length()>512)
                throw new IllegalArgumentException("Invalid password: real WBD server credentials required");
            if(port<1||port>65535)
                throw new IllegalArgumentException("Invalid real server port: 1..65535");
            if(!pem.isEmpty()&&!pem.startsWith("-----BEGIN CERTIFICATE-----")){
                throw new IllegalArgumentException("TLS CA must be a PEM certificate");
            }
            // Lite v2: EXACT main offline v2 KDF or 64hex legacy. Only a
            // derived 32B key is handed to original Go's private hex file;
            // never the human short key, Intent extra or Go argv.
            String key=RootRouteKeyCache.resolve(this,sni,keyInput);
            // A38: save only original UI input, never the 32-byte derived
            // route key, native argv or unencrypted SharedPreferences.
            boolean saved=RootStartCredentialSave.attempt(
                ()->RootEncryptedCredentialStore.save(this,secret,keyInput));
            if(!saved)
                traceUi(RootDiagnosticReceipt.Event.UI_CREDENTIAL_SAVE_FAILED);
            // Go owns the same standard TLS/auth, Rust M4 and UID Stop.
            privateText("wbd-pass.secret",secret+"\n");
            privateText("wbd-route.secret",key+"\n");
            if(verifyTLS&&!pem.isEmpty())privateText("wbd-server-ca.pem",pem+"\n");
            Intent request=new Intent(this,RootClientService.class);
            request.setAction(RootClientService.START);
            request.putExtra("handle",scope.handle);
            request.putExtra("iface",scope.interfaceName);
            request.putExtra("index",scope.ifindex);
            request.putExtra("mtu",scope.mtu);
            request.putExtra("local",scope.address);
            request.putExtra("peer",peer);
            request.putExtra("port",port);
            request.putExtra("sni",sni);
            request.putExtra("user",account);
            request.putExtra("all_apps",allApps);
            if(allApps){
                request.putExtra("exclude_appids",entire.excludedAppIDs);
                request.putExtra("manager_packages",entire.managerPackages);
            }else{
                request.putExtra("target_uids",chosen.uids);
                request.putExtra("target_packages",chosen.packages);
            }
            request.putExtra("has_ca",verifyTLS&&!pem.isEmpty());
            request.putExtra("tls_verify_server",verifyTLS);
            dispatchRequested=true;
            traceUi(RootDiagnosticReceipt.Event.UI_START_DISPATCH_REQUESTED);
            startForegroundService(request);
            traceUi(RootDiagnosticReceipt.Event.UI_START_DISPATCHED);
            String notice=saved?"":"；设备密码自动保存失败（不影响本次连接）";
            RootClientService.status=(verifyTLS
                ?"Root start — strict TLS server certificate validation ON"
                :"Root start — TLS certificate validation OFF (main default)")+notice;
            status.setText(RootClientService.status);
            // Preserve on-screen values for another Start in this Activity.
            // The keystore-backed snapshot also restores them after restart.
        }catch(Exception e){
            traceUi(dispatchRequested
                ?RootDiagnosticReceipt.Event.UI_START_DISPATCH_FAILED
                :RootDiagnosticReceipt.Event.UI_START_VALIDATION_REJECTED);
            String detail=e.getMessage();
            if(detail==null||detail.length()>200)detail="查看设置后重试";
            RootClientService.status="UI START REJECTED: "+detail+
                "；可导出安全 TXT 查看固定失败阶段";
            status.setText(RootClientService.status);
        }
    }
    @Override public void onCreate(Bundle state){
        super.onCreate(state);
        traceUi(RootDiagnosticReceipt.Event.UI_OPENED);
        ScrollView scroll=new ScrollView(this);
        LinearLayout pane=new LinearLayout(this);
        pane.setOrientation(LinearLayout.VERTICAL);
        int pad=(int)(getResources().getDisplayMetrics().density*12);
        pane.setPadding(pad,pad,pad,pad);
        scroll.addView(pane);
        TextView intro=new TextView(this);
        intro.setText("WBD Root Lite v2 · ARM64 简版测试\n"+
            "原 Go FakeTCP/TLS + 原 Rust M4；仅 Normal/off，非 VPN/FakeIP。\n"+
            "① 选择实体 Wi-Fi/移动网络  ② 输入 WBD 服务器/账户/Key\n"+
            "③ START 后查看固定阶段码，STOP 精确撤销 UID/清理。\n"+
            "首次测试建议取消下面的「默认全部普通App」，只勾选一个测试App。\n"+
            "TLS默认不检验证书（与主线一致），不验证服务器身份；严格模式可手动开启。\n"+
            "注意：真实 Android↔Linux 业务尚未通过实机验收。");
        pane.addView(intro);
        // Keep advanced Root-only selftest but collapse it in Lite.
        CheckBox advanced=new CheckBox(this);
        advanced.setText("显示高级选项：真实 Root/TUN 自检（可选）");
        advanced.setChecked(false);
        pane.addView(advanced);
        LinearLayout advancedPanel=new LinearLayout(this);
        advancedPanel.setOrientation(LinearLayout.VERTICAL);
        advancedPanel.setVisibility(View.GONE);
        advanced.setOnCheckedChangeListener((button,checked)->
            advancedPanel.setVisibility(checked?View.VISIBLE:View.GONE));
        TextView diagHint=new TextView(this);
        diagHint.setText("真 ARM64 KernelSU 手机可直接一键测真实 App UID→内核路由→临时 TUN 的固定 UDP 包，" +
            "不需要服务器参数；这并不等于原 Rust M4 或生产目标 App 转发验收。" +
            " 真实 WBD 服务器与密钥只用于下面单独的 START。");
        advancedPanel.addView(diagHint);
        networks=new Spinner(this);
        pane.addView(networks);
        Button refresh=new Button(this);
        refresh.setText("Refresh physical Networks");
        refresh.setOnClickListener(v->chooseNetworks());
        pane.addView(refresh);
        Button selfTestButton=new Button(this);
        selfTestButton.setText("A12 一键自检 ARM64/KSU/TUN/UID入TUN及分阶段路由诊断（免服务器）");
        selfTestButton.setOnClickListener(v->runDeviceSelfTest());
        if(android.os.Build.SUPPORTED_ABIS.length>0&&
           "arm64-v8a".equals(android.os.Build.SUPPORTED_ABIS[0]))advancedPanel.addView(selfTestButton);
        deviceSelfTestResult=new TextView(this);
        deviceSelfTestResult.setText("尚未测试。测试中会请求 KernelSU 授权；结果可长按复制。");
        deviceSelfTestResult.setTextIsSelectable(true);
        advancedPanel.addView(deviceSelfTestResult);
        Button copySelfTest=new Button(this);
        copySelfTest.setText("复制一键自检结果");
        copySelfTest.setOnClickListener(v->{
            ClipboardManager cb=(ClipboardManager)getSystemService(CLIPBOARD_SERVICE);
            if(cb!=null)cb.setPrimaryClip(ClipData.newPlainText("WBD ARM64 诊断结果",
                deviceSelfTestResult.getText()));
        });
        advancedPanel.addView(copySelfTest);
        pane.addView(advancedPanel);
        serverAddress=input(pane,"Server underlay IPv4 or DNS name (physical DNS bootstrap)",InputType.TYPE_CLASS_TEXT);
        serverName=input(pane,"Standard TLS server name / SNI",InputType.TYPE_CLASS_TEXT);
        serverPort=input(pane,"Original FakeTCP peer port",InputType.TYPE_CLASS_NUMBER);
        serverPort.setText("443");
        user=input(pane,"Authenticated account",InputType.TYPE_CLASS_TEXT);
        password=input(pane,"Password (app-private file, not argv)",
            InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);
        routeKey=input(pane,"Route Key：主线 v2 短 Key（8–32 位英文/数字）或传统 64 位 Hex",
            InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);
        TextView keyHelp=new TextView(this);
        keyHelp.setText("短 Key 使用与 Linux/Windows 一样的离线 PBKDF2-HMAC-SHA256 v2；"+
            "原Go只接收派生后的32字节Hex。派生缓存不存明文口令；若选择保存，"+
            "原始短Key单独由Android Keystore AES-GCM加密后存在不备份目录。"+
            "服务端须使用同一Key；建议随机24–32位。没有线上协商或隐式回退。");
        pane.addView(keyHelp);
        TextView rememberHint=new TextView(this);
        rememberHint.setText("密码与原始简版RouteKey可保存在本机Android Keystore加密记录中，"+
            "下次打开APK自动填入；默认不随Android备份迁移。");
        pane.addView(rememberHint);
        Button saveSecrets=new Button(this);
        saveSecrets.setText("保存密码 / RouteKey（设备加密，重开自动填入）");
        saveSecrets.setOnClickListener(v->{
            try{
                RootEncryptedCredentialStore.save(this,password.getText().toString(),
                    routeKey.getText().toString());
                status.setText("密码和RouteKey已在本机加密保存");
            }catch(Exception failure){
                status.setText("保存失败：请检查密码/RouteKey格式或系统Keystore");
            }
        });
        pane.addView(saveSecrets);
        Button clearSecrets=new Button(this);
        clearSecrets.setText("清除已保存密码 / RouteKey");
        clearSecrets.setOnClickListener(v->new AlertDialog.Builder(this)
            .setTitle("清除保存的登录凭据")
            .setMessage("仅删除本APK加密保存的密码/原始RouteKey和Keystore密钥，不影响当前Root网络会话或其他客户端。")
            .setNegativeButton("取消",null)
            .setPositiveButton("清除",(dialog,which)->{
                try{
                    RootEncryptedCredentialStore.clear(this);
                    password.setText("");
                    routeKey.setText("");
                    status.setText("本机保存的密码和RouteKey已清除");
                }catch(Exception failure){status.setText("清除失败：请检查设备加密存储");}
            }).show());
        pane.addView(clearSecrets);
        tlsVerifyServer=new CheckBox(this);
        tlsVerifyServer.setText("严格验证TLS服务器证书和SNI（默认关闭，主线兼容）");
        tlsVerifyServer.setChecked(false);
        pane.addView(tlsVerifyServer);
        TextView verifyWarning=new TextView(this);
        verifyWarning.setText("默认仍使用原TLS加密/受保护认证，但不验证服务端证书身份，有中间人风险。"+
            "勾选后才验证证书与SNI，并可使用下方本地CA。");
        pane.addView(verifyWarning);
        caPEM=input(pane,"Optional server TLS CA PEM (only for strict verification)",
            InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        caPEM.setMinLines(3);
        Button importCa=new Button(this);
        importCa.setText("从本机文件导入 WBD 服务端 TLS CA PEM");
        importCa.setOnClickListener(v->importTLSCA());
        pane.addView(importCa);
        TextView caHelp=new TextView(this);
        caHelp.setText("只有勾选严格验证时才使用CA；否则默认不做证书身份校验。"+
            "严格模式下UNKNOWN_AUTHORITY请导入CA；HOSTNAME_MISMATCH请核对证书DNS SAN与SNI。");
        pane.addView(caHelp);
        TextView targetHelp=new TextView(this);
        targetHelp.setText("默认仅接管普通 Android 应用的 IPv4 流量（最多20个用户空间），不是系统全流量。"
            +"仅在原 Go TLS/认证 /32、原 Rust M4 就绪后设置 KernelSU UID 路由。"
            +"系统/root/隔离 UID、WBD 自身及已识别 KernelSU Manager 绕过，"
            +"原服务器IPv4在私有路由表设置/32 throw排除，必须内核读回才放行UID路由；" 
            +"其后Android netd是否真实走物理出口尚未真机验。"
            +"IPv6、系统DNS、系统进程不接管。"
            +"取消全应用模式后，可选择最多 8 个实际 App UID。");
        pane.addView(targetHelp);
        allAppsDefault=new CheckBox(this);
        allAppsDefault.setText("默认：普通 App IPv4 走 WBD（服务器/本App/KernelSU排除，非全系统）");
        allAppsDefault.setChecked(true);
        pane.addView(allAppsDefault);
        appChoices=new LinearLayout(this);
        appChoices.setOrientation(LinearLayout.VERTICAL);
        pane.addView(appChoices);
        allAppsDefault.setOnCheckedChangeListener((button,checked)->
            appChoices.setVisibility(checked?View.GONE:View.VISIBLE));
        appChoices.setVisibility(View.GONE);
        Button refreshApps=new Button(this);
        refreshApps.setText("Refresh installed applications");
        refreshApps.setOnClickListener(v->chooseInstalledApplications());
        pane.addView(refreshApps);
        Button connect=new Button(this);connect.setText("START — ROOT / ORIGINAL Go+Rust");
        connect.setOnClickListener(v->start());
        pane.addView(connect);
        Button stop=new Button(this);stop.setText("STOP — WITHDRAW UID ROUTE / NATIVE JOIN");
        stop.setOnClickListener(v->{
            Intent i=new Intent(this,RootClientService.class);
            i.setAction(RootClientService.STOP);
            startService(i);
        });
        pane.addView(stop);
        Button restore=new Button(this);
        restore.setText("恢复网络（WBD临时Root防火墙/UID路由）");
        restore.setOnClickListener(v->new AlertDialog.Builder(this)
            .setTitle("恢复 WBD 临时Root网络")
            .setMessage("将停止当前原 Go/Rust owner，并只按私有root journal"+
                "回滚WBD拥有的精确 OUTPUT RST防火墙规则、UID路由及私有表。"+
                "不会全局flush、清理其他客户端/系统规则或改变DNS。"+
                "若仍有其他owner或外国规则，直接拒绝清理。")
            .setNegativeButton("取消",null)
            .setPositiveButton("停止并恢复",(dialog,which)->{
                Intent i=new Intent(this,RootClientService.class);
                i.setAction(RootClientService.RESTORE);
                startForegroundService(i);
                status.setText("已请求恢复；等待原Go精确内核读回");
            }).show());
        pane.addView(restore);
        Button exportDiagnostic=new Button(this);
        exportDiagnostic.setText("导出脱敏排障 TXT（无 Root／无需联网）");
        exportDiagnostic.setOnClickListener(v->exportSafeDiagnostic());
        pane.addView(exportDiagnostic);
        diagnosticExportResult=new TextView(this);
        diagnosticExportResult.setText("首次使用后或连接失败后点击导出。仅固定阶段码与时间、APK SOURCE/API；不含服务器IP、账号、密钥和原生日志。");
        diagnosticExportResult.setTextIsSelectable(true);
        pane.addView(diagnosticExportResult);
        status=new TextView(this);
        status.setText("NOT_RUNNING");
        status.setTextIsSelectable(true);
        pane.addView(status);
        setContentView(scroll);
        chooseNetworks();
        chooseInstalledApplications();
        try{
            RootSavedCredentialRecord.Secrets saved=
                RootEncryptedCredentialStore.load(this);
            if(saved!=null){
                password.setText(saved.password);
                routeKey.setText(saved.routeKey);
            }
        }catch(Exception failure){
            traceUi(RootDiagnosticReceipt.Event.UI_CREDENTIAL_LOAD_FAILED);
            RootClientService.status="加密凭据不可读取，请手动输入后重新保存；仍可以尝试连接";
            status.setText(RootClientService.status);
        }
    }
    @Override protected void onResume(){
        super.onResume();
        chooseInstalledApplications();
        ui.post(refreshStatus);
    }
    @Override protected void onPause(){
        ui.removeCallbacks(refreshStatus);super.onPause();
    }
}
