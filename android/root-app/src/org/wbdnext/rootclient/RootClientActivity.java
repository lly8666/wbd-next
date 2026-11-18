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
    private CheckBox allAppsDefault;
    private LinearLayout appChoices;
    private TextView status,deviceSelfTestResult;
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
        try(FileOutputStream out=openFileOutput(file,Context.MODE_PRIVATE)){
            out.write(text.getBytes(StandardCharsets.UTF_8));
            out.getFD().sync();
        }
    }
    private void start(){
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
            String key=routeKey.getText().toString().trim();
            String pem=caPEM.getText().toString().trim();
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
            if(!key.matches("[0-9a-fA-F]{64}"))
                throw new IllegalArgumentException("Invalid offline route key: need exactly 64 hexadecimal characters (32 bytes)");
            if(port<1||port>65535)
                throw new IllegalArgumentException("Invalid real server port: 1..65535");
            if(!pem.isEmpty()&&!pem.startsWith("-----BEGIN CERTIFICATE-----")){
                throw new IllegalArgumentException("TLS CA must be a PEM certificate");
            }
            // Secrets never enter process arguments, Android Intent extras,
            // command logs or system properties. Go opens exact 0600 files
            // with O_NOFOLLOW using the already-authenticated cold source.
            privateText("wbd-pass.secret",secret+"\n");
            privateText("wbd-route.secret",key+"\n");
            if(!pem.isEmpty())privateText("wbd-server-ca.pem",pem+"\n");
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
            request.putExtra("has_ca",!pem.isEmpty());
            startForegroundService(request);
            status.setText("Root start requested; awaiting actual native Go proof");
            password.setText("");
            routeKey.setText("");
        }catch(Exception e){
            status.setText("START REJECTED: "+e.getMessage());
        }
    }
    @Override public void onCreate(Bundle state){
        super.onCreate(state);
        ScrollView scroll=new ScrollView(this);
        LinearLayout pane=new LinearLayout(this);
        pane.setOrientation(LinearLayout.VERTICAL);
        int pad=(int)(getResources().getDisplayMetrics().density*12);
        pane.setPadding(pad,pad,pad,pad);
        scroll.addView(pane);
        TextView intro=new TextView(this);
        intro.setText("WBD original Go + Rust — Android ARM64 Root\n"+
            "No VpnService or FakeIP. Normal/off only. Real traffic NOT YET DEVICE-QUALIFIED.");
        pane.addView(intro);
        TextView diagHint=new TextView(this);
        diagHint.setText("真 ARM64 KernelSU 手机可直接一键测真实 App UID→内核路由→临时 TUN 的固定 UDP 包，" +
            "不需要服务器参数；这并不等于原 Rust M4 或生产目标 App 转发验收。" +
            " 真实 WBD 服务器与密钥只用于下面单独的 START。");
        pane.addView(diagHint);
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
           "arm64-v8a".equals(android.os.Build.SUPPORTED_ABIS[0]))pane.addView(selfTestButton);
        deviceSelfTestResult=new TextView(this);
        deviceSelfTestResult.setText("尚未测试。测试中会请求 KernelSU 授权；结果可长按复制。");
        deviceSelfTestResult.setTextIsSelectable(true);
        pane.addView(deviceSelfTestResult);
        Button copySelfTest=new Button(this);
        copySelfTest.setText("复制一键自检结果");
        copySelfTest.setOnClickListener(v->{
            ClipboardManager cb=(ClipboardManager)getSystemService(CLIPBOARD_SERVICE);
            if(cb!=null)cb.setPrimaryClip(ClipData.newPlainText("WBD ARM64 诊断结果",
                deviceSelfTestResult.getText()));
        });
        pane.addView(copySelfTest);
        serverAddress=input(pane,"Server underlay IPv4 or DNS name (physical DNS bootstrap)",InputType.TYPE_CLASS_TEXT);
        serverName=input(pane,"Standard TLS server name / SNI",InputType.TYPE_CLASS_TEXT);
        serverPort=input(pane,"Original FakeTCP peer port",InputType.TYPE_CLASS_NUMBER);
        serverPort.setText("443");
        user=input(pane,"Authenticated account",InputType.TYPE_CLASS_TEXT);
        password=input(pane,"Password (app-private file, not argv)",
            InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);
        routeKey=input(pane,"Offline original 32-byte route key hex",
            InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);
        caPEM=input(pane,"Optional server TLS CA certificate PEM",
            InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        caPEM.setMinLines(3);
        TextView targetHelp=new TextView(this);
        targetHelp.setText("默认代理所有普通 Android App（20 个 Android 用户空间的应用 UID 段）。"
            +"仅在原 Go TLS/认证 /32、原 Rust M4 就绪后设置 KernelSU UID 路由。"
            +"系统/root/隔离 UID、WBD 自身及已识别 KernelSU Manager 绕过，"
            +"物理网络出口不经隧道。系统 DNS、系统进程全局接管尚未验证，当前不启用。"
            +"取消全应用模式后，可选择最多 8 个实际 App UID。");
        pane.addView(targetHelp);
        allAppsDefault=new CheckBox(this);
        allAppsDefault.setText("默认：代理所有普通应用（排除 WBD/KernelSU/系统 UID）");
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
        status=new TextView(this);
        status.setText("NOT_RUNNING");
        status.setTextIsSelectable(true);
        pane.addView(status);
        setContentView(scroll);
        chooseNetworks();
        chooseInstalledApplications();
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
