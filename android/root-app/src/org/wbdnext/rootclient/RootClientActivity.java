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
import android.net.ConnectivityManager;
import android.net.Network;
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
    // B49: one foreground user-triggered cold reselect, never background Root restart.
    private final RootColdNetworkSwitch coldSwitch=new RootColdNetworkSwitch();
    // B60: the existing foreground UI refresh owns this decision only.
    private final RootForegroundAutoReconnect autoHandover=
        new RootForegroundAutoReconnect();
    private final List<InstalledAppTarget> installedApps=new ArrayList<>();
    private final Map<String,CheckBox> checkedApps=new TreeMap<>();
    private final Map<String,CheckBox> checkedBypassApps=new TreeMap<>();
    // A saved selection is only restored if fresh package+UID still match;
    // the OS Network handle and any root route are never restored.
    private final Map<String,Integer> restoredSelection=new TreeMap<>();
    private final Map<String,Integer> restoredBypass=new TreeMap<>();
    private EditText serverAddress,serverName,user,password,routeKey,caPEM,serverPort,outerMTUField,directCIDRsField,physicalDNSUpstreamField,ipv6GatewayField,ipv6DirectCIDRsField,tunnelDNSUpstreamField;
    private Spinner networks,recordCiphers,tunQueueSizes,startupPaddingModes,fecModes,fecProfiles,nativeHealthIntervals,profileSlots,coldRotationMinutes,game4CopySchedules;
    private CheckBox allAppsDefault,tlsVerifyServer,tunnelDNS,physicalDNS,cnSplitDNS,cnIPDirect,outerRepair,physicalDNSFollowNetwork,autoConnectedDirect,autoNetworkRecovery,backgroundNetworkRecovery,appTcpDNS,tetherSharing,systemDNS,systemDNS6;
    private Spinner tetherChoices;
    private RootTetherScope tetherWatch;
    private final java.util.List<RootTetherScope> tetherScopes=new java.util.ArrayList<>();
    private void watchTetherChoices(){
        if(tetherWatch!=null)return;
        try{tetherWatch=RootTetherScope.watch(this,scopes->{
            Object previous=tetherChoices.getSelectedItem();
            tetherScopes.clear();tetherScopes.addAll(scopes);
            java.util.List<String> labels=new java.util.ArrayList<>();
            for(RootTetherScope scope:scopes)labels.add(scope.toString());
            if(labels.isEmpty())labels.add("暂无活动的热点/USB共享");
            tetherChoices.setAdapter(new android.widget.ArrayAdapter<String>(this,android.R.layout.simple_spinner_dropdown_item,labels));
            if(previous!=null&&labels.contains(previous.toString()))tetherChoices.setSelection(labels.indexOf(previous.toString()));
        });}catch(Exception e){
            tetherSharing.setEnabled(false);
            tetherSharing.setText("热点共享不可用（需要 Android 16 公共 tethering API）");
        }
    }
    private RootTetherScope selectedTether(PhysicalNetwork upstream){
        int i=tetherChoices.getSelectedItemPosition();
        if(i<0||i>=tetherScopes.size())throw new IllegalArgumentException("请先打开系统热点/USB共享并选择下游");
        RootTetherScope s=tetherScopes.get(i);
        if(s.iface.equals(upstream.interfaceName)||!s.same(RootTetherScope.read(s.iface)))
            throw new IllegalArgumentException("热点下游已变化，请重新选择");
        return s;
    }
    private LinearLayout appChoices,selectedAppControls,bypassAppControls,bypassChoices;
    private EditText appSearch,bypassSearch;
    private TextView selectedAppsSummary,bypassSummary,presetResult,profileResult;
    private EditText profileLabel;
    private RootConnectionSettings pendingPresetExport;
    private RootConnectionProfile[] pendingBundleExport;
    private TextView status,deviceSelfTestResult,diagnosticExportResult,dnsStatusBrief,fecStatusText,m4TrafficBrief;
    private static final int SAFE_DIAGNOSTIC_SAVE=2042;
    private static final int LOCAL_TLS_CA_IMPORT=2043;
    private static final int CONNECTION_PRESET_EXPORT=2044;
    private static final int CONNECTION_PRESET_IMPORT=2045;
    private static final int PROFILE_BUNDLE_EXPORT=2046;
    private static final int PROFILE_BUNDLE_IMPORT=2047;
    private static final int CN_DOMAIN_IMPORT=2048;
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
    // B23: read the original 0600 app-private CA already staged for
    // Go strict TLS. No Android system trust edits or network discovery.
    private void recallSavedTLSCA(){
        // B54: last selected profile's optional UI CA wins over an older
        // server's root-staged CA. Empty explicitly means no private CA.
        try{
            String selected=RootConnectionProfileCAStore.loadCurrent(this);
            if(selected!=null){
                caPEM.setText(selected);
                return;
            }
        }catch(Exception unavailable){/* old A32 recall still works */}
        File file=new File(getFilesDir(),RootPrivateCredentialFiles.CA);
        if(!file.isFile()||file.length()<1||
           file.length()>RootPrivateCredentialContract.maxBytes(
               RootPrivateCredentialFiles.CA))return;
        try(InputStream in=new java.io.FileInputStream(file);
            ByteArrayOutputStream out=new ByteArrayOutputStream()){
            byte[] chunk=new byte[4096];
            int n;
            int limit=RootPrivateCredentialContract.maxBytes(
                RootPrivateCredentialFiles.CA);
            while((n=in.read(chunk))!=-1){
                if(out.size()+n>limit)return;
                out.write(chunk,0,n);
            }
            String pem=new String(out.toByteArray(),StandardCharsets.UTF_8).trim();
            if(!pem.startsWith("-----BEGIN CERTIFICATE-----")||
               !pem.contains("-----END CERTIFICATE-----"))return;
            java.util.Collection<? extends java.security.cert.Certificate> certs=
                java.security.cert.CertificateFactory.getInstance("X.509")
                    .generateCertificates(new java.io.ByteArrayInputStream(
                        pem.getBytes(StandardCharsets.UTF_8)));
            if(!certs.isEmpty())caPEM.setText(pem);
        }catch(Exception ignored){
            // Optional recall only; user can re-import the local CA.
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
            // Reuse A32 production 0600 writer. A CA is public trust
            // material; unlike the password/RouteKey it needs no new
            // storage or encryption format. Go still reads it only on START.
            privateText(RootPrivateCredentialFiles.CA,pem+"\n");
            caPEM.setText(pem);
            RootConnectionProfileCAStore.saveCurrent(this,pem);
            status.setText("已导入并保留 "+certs.size()+" 张本地TLS证书；勾选严格校验后原Go才使用");
        }catch(Exception failure){
            status.setText("CA导入或本机保存失败；请核对PEM并重新导入");
        }
    }
    // B53: one explicit SAF transaction for all four existing named slots.
    // No Root permission, credential plaintext, CA or physical Network handle.
    private void exportAllProfiles(){
        try{
            RootConnectionProfile[] profiles=
                new RootConnectionProfile[RootConnectionProfile.SLOTS];
            int count=0;
            for(int i=0;i<profiles.length;i++){
                profiles[i]=RootConnectionProfileStore.load(this,i+1);
                if(profiles[i]!=null)count++;
            }
            if(count==0){
                profileResult.setText("四个配置槽均为空，请先保存连接配置");
                return;
            }
            pendingBundleExport=profiles;
            Intent select=new Intent(Intent.ACTION_CREATE_DOCUMENT);
            select.addCategory(Intent.CATEGORY_OPENABLE);
            select.setType("application/octet-stream");
            select.putExtra(Intent.EXTRA_TITLE,"wbd-root-four-profiles.wbpb");
            startActivityForResult(select,PROFILE_BUNDLE_EXPORT);
        }catch(Exception unavailable){
            pendingBundleExport=null;
            profileResult.setText("无法读取当前四个配置槽，导出未开始");
        }
    }
    private void importAllProfiles(){
        Intent select=new Intent(Intent.ACTION_OPEN_DOCUMENT);
        select.addCategory(Intent.CATEGORY_OPENABLE);
        select.setType("*/*");
        try{startActivityForResult(select,PROFILE_BUNDLE_IMPORT);}
        catch(Exception unavailable){profileResult.setText("系统文件选择器不可用");}
    }
    private void onAllProfilesResult(int code,int result,Intent data){
        if(code==PROFILE_BUNDLE_EXPORT){
            RootConnectionProfile[] snapshot=pendingBundleExport;
            pendingBundleExport=null;
            if(result!=RESULT_OK||data==null||data.getData()==null||
               snapshot==null){
                profileResult.setText("四槽配置导出已取消");
                return;
            }
            try(OutputStream out=getContentResolver().openOutputStream(
                data.getData(),"wt")){
                if(out==null)throw new java.io.IOException("No profile export output");
                RootConnectionProfileBundle.write(out,snapshot);
                profileResult.setText("四槽普通连接设置已导出；不含密码、RouteKey、CA及Network");
            }catch(Exception unavailable){
                profileResult.setText("四槽导出失败：未完整写入文件");
            }
            return;
        }
        if(result!=RESULT_OK||data==null||data.getData()==null){
            profileResult.setText("四槽导入已取消");
            return;
        }
        coldSwitch.cancel();
        try(InputStream in=getContentResolver().openInputStream(data.getData())){
            RootConnectionProfile[] restored=RootConnectionProfileBundle.read(in);
            if(restored==null)throw new IllegalArgumentException("not four WBD profiles");
            // Import replaces the four cold slots only. Reusing old slot
            // credentials for another server would select the wrong account.
            // The active Go/Rust process owns separate staged files already.
            for(int i=0;i<restored.length;i++){
                int slot=i+1;
                RootEncryptedCredentialStore.clearProfile(this,slot);
                RootConnectionProfileCAStore.clearSlot(this,slot);
                if(restored[i]==null)RootConnectionProfileStore.delete(this,slot);
                else RootConnectionProfileStore.save(this,slot,restored[i]);
            }
            refreshNamedProfileChoices();
            profileResult.setText("四槽设置已恢复。各槽密码/RouteKey需在本机重新填写保存；"+
                "当前Root会话和选定物理Network不变");
        }catch(Exception failed){
            refreshNamedProfileChoices();
            profileResult.setText("四槽导入未完整成功；若已有部分槽写入请检查后重试。"+
                "未触发Root连接或内核路由");
        }
    }
    private void exportConnectionPreset(){
        try{
            // Freeze the user's NONSECRET cold form before SAF takes focus.
            pendingPresetExport=connectionSettingsFromUi();
            Intent picker=new Intent(Intent.ACTION_CREATE_DOCUMENT);
            picker.addCategory(Intent.CATEGORY_OPENABLE);
            picker.setType("text/plain");
            picker.putExtra(Intent.EXTRA_TITLE,"wbd-root-connection.properties");
            startActivityForResult(picker,CONNECTION_PRESET_EXPORT);
        }catch(Exception invalid){
            pendingPresetExport=null;
            presetResult.setText("导出设置失败：先填完整服务器、SNI、账户及合法模式；不会导出密码或RouteKey");
        }
    }
    private void importConnectionPreset(){
        Intent picker=new Intent(Intent.ACTION_OPEN_DOCUMENT);
        picker.addCategory(Intent.CATEGORY_OPENABLE);
        // Some Android file pickers label .properties as octet-stream.
        picker.setType("*/*");
        try{startActivityForResult(picker,CONNECTION_PRESET_IMPORT);}
        catch(Exception unavailable){presetResult.setText("系统文件选择器不可用，未修改现有设置");}
    }
    private void onConnectionPresetResult(int code,int resultCode,Intent data){
        if(code==CONNECTION_PRESET_EXPORT){
            RootConnectionSettings value=pendingPresetExport;
            pendingPresetExport=null;
            if(resultCode!=RESULT_OK||data==null||data.getData()==null||
               value==null){
                presetResult.setText("连接设置导出已取消");
                return;
            }
            try(OutputStream out=getContentResolver().openOutputStream(
                data.getData(),"wt")){
                if(out==null)throw new java.io.IOException("no output");
                // Exactly B22/B25 production serializer; no secrets or
                // saved root route/Network handle in this exported file.
                value.write(out);
                out.flush();
                presetResult.setText("连接设置已导出：含服务器/账号/模式/已选包名与UID，"+
                    "不含密码、RouteKey、CA或物理网络。可用于重装后手动导入");
            }catch(Exception failed){
                presetResult.setText("导出失败：文件未成功写入；原Root连接不受影响");
            }
            return;
        }
        if(resultCode!=RESULT_OK||data==null||data.getData()==null){
            presetResult.setText("连接设置导入已取消");
            return;
        }
        try(InputStream in=getContentResolver().openInputStream(data.getData())){
            RootConnectionSettings imported=RootConnectionSettingsTransfer.read(in);
            if(imported==null)throw new IllegalArgumentException("bad settings");
            // Replace only the COLD UI form. Re-enumerate installed apps,
            // and restore a checked app only for the SAME package+current
            // Android UID. Do not adopt an old physical Network handle.
            // Persist first, then replace the form. Storage failure
            // must not leave a half-imported selection in the UI.
            RootConnectionSettingsStore.save(this,imported);
            for(CheckBox cb:checkedApps.values())cb.setChecked(false);
            restoreConnectionSettings(imported);
            chooseInstalledApplications();
            presetResult.setText("非密钥连接参数已导入并保存在本机；已选App仅在包名和UID"+
                "仍一致时恢复。请重新填写密码/RouteKey，确认物理Network后手动START");
        }catch(Exception rejected){
            presetResult.setText("导入失败：不是有效的WBD连接预设、超过8KiB或无法保存；"+
                "未触发Root/TLS/内核UID路由");
        }
    }
    private void importCNDomainRules(){
        Intent pick=new Intent(Intent.ACTION_OPEN_DOCUMENT);
        pick.addCategory(Intent.CATEGORY_OPENABLE);
        pick.setType("*/*");
        try{startActivityForResult(pick,CN_DOMAIN_IMPORT);}
        catch(Exception e){status.setText("无法打开域名规则文件选择器");}
    }
    private void acceptCNDomainRules(Intent data){
        if(data==null||data.getData()==null)return;
        File target=NativePayload.customCN(this);
        File tmp=null;
        try(InputStream in=getContentResolver().openInputStream(data.getData())){
            if(in==null)throw new java.io.IOException("no input");
            tmp=File.createTempFile("cn-domains-",".txt",getNoBackupFilesDir());
            try(FileOutputStream out=new FileOutputStream(tmp)){
                byte[] buf=new byte[8192];int n,total=0;
                while((n=in.read(buf))!=-1){
                    total+=n;
                    if(total>=6000000)throw new java.io.IOException("规则文件过大");
                    out.write(buf,0,n);
                }
                if(total==0)throw new java.io.IOException("规则文件为空");
            }
            java.nio.file.Files.move(tmp.toPath(),target.toPath(),java.nio.file.StandardCopyOption.REPLACE_EXISTING);
            status.setText("已保存自定义CN域名规则；下次连接时由原Go/Rust冷加载");
        }catch(Exception e){status.setText("导入CN域名规则失败："+e.getMessage());}
        finally{if(tmp!=null)tmp.delete();}
    }
    @Override protected void onActivityResult(int requestCode,int resultCode,Intent data){
        super.onActivityResult(requestCode,resultCode,data);
        if(requestCode==CN_DOMAIN_IMPORT){
            if(resultCode==RESULT_OK)acceptCNDomainRules(data);
            return;
        }
        if(requestCode==LOCAL_TLS_CA_IMPORT){
            if(resultCode==RESULT_OK)acceptTLSCA(data);
            return;
        }
        if(requestCode==PROFILE_BUNDLE_EXPORT||
           requestCode==PROFILE_BUNDLE_IMPORT){
            onAllProfilesResult(requestCode,resultCode,data);
            return;
        }
        if(requestCode==CONNECTION_PRESET_EXPORT||
           requestCode==CONNECTION_PRESET_IMPORT){
            onConnectionPresetResult(requestCode,resultCode,data);
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
            completeUserColdSwitchIfReady();
            completeAutomaticColdSwitchIfReady();
            if(status!=null)status.setText(RootClientService.status);
            if(fecStatusText!=null)fecStatusText.setText(RootClientService.fecStatus);
            ui.postDelayed(this,1000);
        }
    };
    // Uses the already existing foreground UI refresh: zero new timers or packet workers.
    private void completeUserColdSwitchIfReady(){
        if(!coldSwitch.pending()||RootClientService.sessionOwnerActive||
           RootClientService.startDispatchPending.get())return;
        chooseNetworks();
        int matched=-1;
        for(int i=0;i<physical.size();i++){
            PhysicalNetwork n=physical.get(i);
            if(coldSwitch.matches(n.handle,n.interfaceName,n.ifindex,n.mtu,n.address)&&
               PhysicalNetwork.exact(this,n.handle,n.interfaceName,n.ifindex,
                   n.mtu,n.address)!=null){
                matched=i;break;
            }
        }
        // Snapshot the named profile before the one-shot Stop decision
        // consumes its intent; B49 plain Network switch has slot zero.
        int slot=coldSwitch.profileSlot();
        boolean ready=coldSwitch.complete(
            RootClientService.previousOwnerStopConfirmed,matched>=0);
        if(!ready){
            RootClientService.status="一键冷切网中止：旧原生Stop未完整确认或目标Network已变化；请检查后手动START";
            return;
        }
        networks.setSelection(matched);
        if(slot!=0&&!loadNamedProfile(slot)){
            RootClientService.status="旧Go/Rust已完整停止，但目标配置不可读取；未启动新会话";
            return;
        }
        // Original Activity start() owns all UID/secret/Network validation,
        // original FakeTCP/TLS/lease, Rust M4 and kernel journal.
        start();
    }
    // B60: exact Service Network loss -> existing original joined Stop ->
    // real Android physical selection -> original Activity.start().
    private void completeAutomaticColdSwitchIfReady(){
        if(coldSwitch.pending()||RootClientService.backgroundRecoveryActive||
           autoNetworkRecovery==null||!autoNetworkRecovery.isChecked())return;
        if(autoHandover.armed()&&RootClientService.networkStopRequested)
            autoHandover.onNetworkStop(true);
        if(!autoHandover.pending()||RootClientService.sessionOwnerActive||
           RootClientService.startDispatchPending.get())return;
        chooseNetworks();
        ConnectivityManager cm=getSystemService(ConnectivityManager.class);
        Network active=cm==null?null:cm.getActiveNetwork();
        long activeHandle=active==null?0:active.getNetworkHandle();
        int matched=-1,only=-1,count=0;
        for(int i=0;i<physical.size();i++){
            PhysicalNetwork n=physical.get(i);
            if(PhysicalNetwork.exact(this,n.handle,n.interfaceName,
                n.ifindex,n.mtu,n.address)==null)continue;
            count++;only=i;
            if(activeHandle!=0&&n.handle==activeHandle)matched=i;
        }
        // LAN-only Network may have no system activeNetwork but can be
        // unambiguous when it is the sole real physical underlay.
        if(matched<0&&count==1)matched=only;
        boolean ready=autoHandover.complete(true,
            RootClientService.previousOwnerStopConfirmed,matched>=0);
        if(!ready){
            RootClientService.status="自动冷重连未执行：旧Go/Rust Stop未确认或没有唯一可用的实体Network；请手动选择并START";
            return;
        }
        networks.setSelection(matched);
        start(); // original Go FakeTCP/TLS/lease, Rust M4 and UID route
    }
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
        // B24: retain a genuinely unchanged Android Network while the UI
        // refreshes, never replay a saved handle from a previous session.
        PhysicalNetwork previouslySelected=null;
        if(networks!=null){
            int previous=networks.getSelectedItemPosition();
            if(previous>=0&&previous<physical.size())
                previouslySelected=physical.get(previous);
        }
        physical.clear();
        physical.addAll(PhysicalNetwork.available(this));
        ArrayList<String> labels=new ArrayList<>();
        for(PhysicalNetwork n:physical)labels.add(n.title());
        if(labels.isEmpty())labels.add("NO Wi-Fi/cellular/Ethernet IPv4 Network");
        ArrayAdapter<String> adapter=new ArrayAdapter<>(this,
            android.R.layout.simple_spinner_dropdown_item,labels);
        networks.setAdapter(adapter);
        if(previouslySelected!=null){
            for(int i=0;i<physical.size();i++){
                if(physical.get(i).same(previouslySelected)){
                    networks.setSelection(i);
                    break;
                }
            }
        }
    }
    private void chooseInstalledApplications(){
        // Keep only exact package+UID matches from the previous snapshot.
        // A package reinstalled with a new UID is NEVER auto-reselected.
        Map<String,Integer> previous=new TreeMap<>(restoredSelection);
        restoredSelection.clear();
        for(InstalledAppTarget app:installedApps){
            CheckBox cb=checkedApps.get(app.packageName);
            if(cb!=null&&cb.isChecked())previous.put(app.packageName,app.uid);
        }
        Map<String,Integer> previousBypass=new TreeMap<>(restoredBypass);
        restoredBypass.clear();
        for(InstalledAppTarget app:installedApps){
            CheckBox cb=checkedBypassApps.get(app.packageName);
            if(cb!=null&&cb.isChecked())previousBypass.put(app.packageName,app.uid);
        }
        installedApps.clear();
        checkedApps.clear();
        checkedBypassApps.clear();
        appChoices.removeAllViews();
        bypassChoices.removeAllViews();
        installedApps.addAll(InstalledAppCatalog.discoverable(this));
        if(installedApps.isEmpty()){
            TextView message=new TextView(this);
            message.setText("当前未发现可选的普通已安装应用；请检查本机安装及包可见性");
            appChoices.addView(message);
            TextView bypassMessage=new TextView(this);
            bypassMessage.setText("当前用户没有可排除的普通应用");
            bypassChoices.addView(bypassMessage);
            updateAppSelectionCount();
            return;
        }
        for(InstalledAppTarget app:installedApps){
            CheckBox cb=new CheckBox(this);
            cb.setText(app.title());
            cb.setChecked(previous.containsKey(app.packageName)&&
                previous.get(app.packageName)==app.uid);
            cb.setOnCheckedChangeListener((button,checked)->updateAppSelectionCount());
            appChoices.addView(cb);
            checkedApps.put(app.packageName,cb);
            CheckBox bypass=new CheckBox(this);
            bypass.setText(app.title());
            bypass.setChecked(previousBypass.containsKey(app.packageName)&&
                previousBypass.get(app.packageName)==app.uid);
            bypass.setOnCheckedChangeListener((button,checked)->updateAppSelectionCount());
            bypassChoices.addView(bypass);
            checkedBypassApps.put(app.packageName,bypass);
        }
        applyAppSearch();
        updateAppSelectionCount();
    }
    private void updateAppSelectionCount(){
        if(selectedAppsSummary==null)return;
        int count=0;
        java.util.Set<Integer> uids=new java.util.TreeSet<>();
        for(InstalledAppTarget app:installedApps){
            CheckBox cb=checkedApps.get(app.packageName);
            if(cb!=null&&cb.isChecked()){count++;uids.add(app.uid);}
        }
        selectedAppsSummary.setText(
            "当前已勾选 "+count+" 个应用 / "+uids.size()+" 个UID（最多16个不同UID、32个包）。"+
            "仅在手动START且成功认证后生效");
        if(bypassSummary!=null){
            int packages=0;
            java.util.Set<Integer> appIds=new java.util.TreeSet<>();
            for(InstalledAppTarget app:installedApps){
                CheckBox bypass=checkedBypassApps.get(app.packageName);
                if(bypass!=null&&bypass.isChecked()){
                    packages++;
                    appIds.add(app.uid%AllAppUIDPolicy.PER_USER);
                }
            }
            bypassSummary.setText("全App绕过："+packages+"个已安装包 / "+
                appIds.size()+"个独立AppID；最多6个包（需与WBD/Root Manager的排除配额合计≤8）。"+
                "只有手动START且原Go认证、Kernel UID规则已真实安装后生效");
        }
    }
    private void applyAppSearch(){
        String text=appSearch==null?"":appSearch.getText().toString();
        for(InstalledAppTarget app:installedApps){
            CheckBox cb=checkedApps.get(app.packageName);
            if(cb!=null)cb.setVisibility(RootAppPickerModel.matches(app,text)
                ?View.VISIBLE:View.GONE);
            CheckBox bypass=checkedBypassApps.get(app.packageName);
            if(bypass!=null)bypass.setVisibility(RootAppPickerModel.matches(
                app,bypassSearch==null?"":bypassSearch.getText().toString())
                ?View.VISIBLE:View.GONE);
        }
    }
    private void selectMatchingApps(){
        java.util.Set<String> previous=new java.util.TreeSet<>();
        for(InstalledAppTarget app:installedApps){
            CheckBox cb=checkedApps.get(app.packageName);
            if(cb!=null&&cb.isChecked())previous.add(app.packageName);
        }
        try{
            java.util.Set<String> chosen=RootAppPickerModel.addMatching(
                installedApps,previous,appSearch.getText().toString(),
                android.os.Process.myUid(),getPackageName());
            for(InstalledAppTarget app:installedApps){
                CheckBox cb=checkedApps.get(app.packageName);
                if(cb!=null)cb.setChecked(chosen.contains(app.packageName));
            }
            updateAppSelectionCount();
        }catch(IllegalArgumentException unsupported){
            selectedAppsSummary.setText("当前筛选结果超过16个不同UID/32个包，或没有匹配；"+
                "请缩小过滤条件，不会更改原选中列表");
        }
    }
    // B22 settings are strictly UI cold inputs. Actual Go TLS, /32,
    // app UID routing and native start still happen only on explicit START.
    private static void selectSpinner(Spinner spinner,String value){
        for(int i=0;i<spinner.getCount();i++){
            if(value.equals(spinner.getItemAtPosition(i).toString())){
                spinner.setSelection(i);
                return;
            }
        }
    }
    private RootConnectionSettings connectionSettingsFromUi(){
        Map<String,Integer> selected=new TreeMap<>();
        Map<String,Integer> bypass=new TreeMap<>();
        if(allAppsDefault.isChecked()){
            for(InstalledAppTarget app:installedApps){
                CheckBox check=checkedBypassApps.get(app.packageName);
                if(check!=null&&check.isChecked())
                    bypass.put(app.packageName,app.uid);
            }
        }
        if(!allAppsDefault.isChecked()){
            for(InstalledAppTarget app:installedApps){
                CheckBox check=checkedApps.get(app.packageName);
                if(check!=null&&check.isChecked())
                    selected.put(app.packageName,app.uid);
            }
        }
        return new RootConnectionSettings(
            serverAddress.getText().toString().trim(),
            serverName.getText().toString().trim(),
            user.getText().toString().trim(),
            Integer.parseInt(serverPort.getText().toString().trim()),
            Integer.parseInt(outerMTUField.getText().toString().trim()),
            Integer.parseInt(tunQueueSizes.getSelectedItem().toString()),
            recordCiphers.getSelectedItem().toString(),
            startupPaddingModes.getSelectedItem().toString(),
            fecModes.getSelectedItem().toString(),
            Integer.parseInt(fecProfiles.getSelectedItem().toString()),
            tlsVerifyServer.isChecked(),tunnelDNS.isChecked(),
            physicalDNS.isChecked(),cnSplitDNS.isChecked(),
            allAppsDefault.isChecked(),selected,
            RootDirectIPv4.canonicalCSV(directCIDRsField.getText().toString()),
            bypass,RootPhysicalDNSUpstream.canonical(physicalDNSUpstreamField.getText().toString()),
            physicalDNSFollowNetwork.isChecked(),
            Integer.parseInt(nativeHealthIntervals.getSelectedItem().toString()),
            autoConnectedDirect.isChecked(),
            backgroundNetworkRecovery.isChecked()?2:autoNetworkRecovery.isChecked()?1:0,
            Integer.parseInt(coldRotationMinutes.getSelectedItem().toString()),
            appTcpDNS.isChecked(),tetherSharing.isChecked(),systemDNS.isChecked(),systemDNS6.isChecked(),RootConnectionSettings.ipv6Gateway(ipv6GatewayField.getText().toString()),RootConnectionSettings.ipv6DirectCIDRs(ipv6DirectCIDRsField.getText().toString()),RootPhysicalDNSUpstream.tunnel(tunnelDNSUpstreamField.getText().toString()),game4CopySchedules.getSelectedItem().toString(),cnIPDirect.isChecked(),outerRepair.isChecked());
    }
    private void saveConnectionSettings()throws Exception{
        RootConnectionSettingsStore.save(this,connectionSettingsFromUi());
    }
    private void restoreConnectionSettings(RootConnectionSettings s){
        if(s==null)return;
        serverAddress.setText(s.peer);
        serverName.setText(s.sni);
        user.setText(s.account);
        serverPort.setText(Integer.toString(s.port));
        outerMTUField.setText(Integer.toString(s.outerMTU));
        directCIDRsField.setText(s.directCIDRs);
        autoConnectedDirect.setChecked(s.autoConnectedDirect);
        physicalDNSUpstreamField.setText(s.physicalDNSUpstream);
        tunnelDNSUpstreamField.setText(s.tunnelDNSUpstream);
        physicalDNSFollowNetwork.setChecked(s.physicalDNSFollowNetwork);
        selectSpinner(nativeHealthIntervals,Integer.toString(s.nativeHealthSeconds));
        selectSpinner(coldRotationMinutes,Integer.toString(s.rotationMinutes));
        autoNetworkRecovery.setChecked(s.recoveryMode==1);
        backgroundNetworkRecovery.setChecked(s.recoveryMode==2);
        selectSpinner(recordCiphers,s.cipher);
        selectSpinner(tunQueueSizes,Integer.toString(s.tunQueue));
        selectSpinner(startupPaddingModes,s.padding);
        selectSpinner(game4CopySchedules,s.game4CopySchedule);
        selectSpinner(fecModes,s.mode);
        selectSpinner(fecProfiles,Integer.toString(s.profile));
        tlsVerifyServer.setChecked(s.verifyTLS);
        tunnelDNS.setChecked(s.tunnelDNS);
        physicalDNS.setChecked(s.physicalDNS);
        cnSplitDNS.setChecked(s.cnSplitDNS);
        cnIPDirect.setChecked(s.cnIPDirect);
        outerRepair.setChecked(s.outerRepair);
        appTcpDNS.setChecked(s.appTcpDNS);
        tetherSharing.setChecked(s.tetherSharing);
        systemDNS.setChecked(s.systemDNS);
        systemDNS6.setChecked(s.systemDNS6);
        ipv6GatewayField.setText(s.ipv6Gateway);
        ipv6DirectCIDRsField.setText(s.ipv6DirectCIDRs);
        allAppsDefault.setChecked(s.allApps);
        // B50: replacing a preset must REPLACE checked package/UID pairs,
        // not union with the old UI selection (which changes Root routes).
        restoredSelection.clear();
        restoredBypass.clear();
        for(CheckBox box:checkedApps.values())box.setChecked(false);
        for(CheckBox box:checkedBypassApps.values())box.setChecked(false);
        restoredSelection.putAll(s.selected);
        restoredBypass.putAll(s.bypass);
    }
    // Only four cold files, read at an explicit UI lifecycle/user action.
    // Do not poll profiles or modify the native owner in the 1Hz refresh.
    private void refreshNamedProfileChoices(){
        if(profileSlots==null)return;
        int selected=profileSlots.getSelectedItemPosition();
        String[] labels=new String[RootConnectionProfile.SLOTS];
        for(int i=0;i<labels.length;i++){
            try{
                RootConnectionProfile p=RootConnectionProfileStore.load(this,i+1);
                labels[i]=p==null?"配置槽"+(i+1)+"（空）":
                    "配置槽"+(i+1)+" · "+p.label+" · "+p.settings.mode;
            }catch(Exception unavailable){
                labels[i]="配置槽"+(i+1)+"（读取失败）";
            }
        }
        profileSlots.setAdapter(new ArrayAdapter<>(this,
            android.R.layout.simple_spinner_dropdown_item,labels));
        if(selected>=0&&selected<labels.length)profileSlots.setSelection(selected);
    }
    private void connectSelectedSavedProfile(){
        autoHandover.cancel();
        final int slot=chosenProfileSlot();
        if(RootClientService.startDispatchPending.get()){
            profileResult.setText("当前已有原Root START在派发，请等完成后再切换");
            return;
        }
        final int pos=networks.getSelectedItemPosition();
        if(pos<0||pos>=physical.size()){
            profileResult.setText("请选择当前真实Wi-Fi/移动/有线Network");
            return;
        }
        PhysicalNetwork target=physical.get(pos);
        if(PhysicalNetwork.exact(this,target.handle,target.interfaceName,
            target.ifindex,target.mtu,target.address)==null){
            chooseNetworks();
            profileResult.setText("目标Network已变化，请重新选择");
            return;
        }
        try{
            if(RootConnectionProfileStore.load(this,slot)==null){
                profileResult.setText("该槽位为空，请先保存可用配置");
                return;
            }
            // A quick connect uses THIS stored server's credentials, not
            // whichever password the user last typed for another server.
            if(RootEncryptedCredentialStore.loadProfile(this,slot)==null){
                profileResult.setText("此槽没有已保存的密码/RouteKey；请先载入、填写并保存");
                return;
            }
        }catch(Exception unavailable){
            profileResult.setText("无法读取此槽的连接或本机凭据，请手动载入检查");
            return;
        }
        if(!RootClientService.sessionOwnerActive){
            coldSwitch.cancel();
            if(loadNamedProfile(slot))start(); // existing real Go/Rust START
            return;
        }
        // Active: one real Service STOP; B48 joined Stop + UID return must
        // finish before we consume this frozen slot and target Network.
        coldSwitch.armProfile(slot,target.handle,target.interfaceName,
            target.ifindex,target.mtu,target.address);
        Intent request=new Intent(this,RootClientService.class);
        request.setAction(RootClientService.STOP);
        try{
            startService(request);
            profileResult.setText("已请求原Go/Rust Stop；完整归还后将连接配置槽"+
                slot+"，仅启动一次（离开本页面即取消接续）");
        }catch(Exception unavailable){
            coldSwitch.cancel();
            profileResult.setText("原Stop请求派发失败，未启动新Root会话");
        }
    }
    private int chosenProfileSlot(){
        return profileSlots.getSelectedItemPosition()+1;
    }
    private void saveNamedProfile(){
        coldSwitch.cancel();
        try{
            int slot=chosenProfileSlot();
            RootConnectionProfile profile=new RootConnectionProfile(
                profileLabel.getText().toString(),connectionSettingsFromUi());
            RootConnectionProfileStore.save(this,slot,profile);
            RootConnectionProfileCAStore.saveSlot(this,slot,
                caPEM.getText().toString());
            refreshNamedProfileChoices();
            // The optional per-profile login is just the existing encrypted
            // AndroidKeyStore record, now keyed by one of the four UI slots.
            // An incomplete login must not reuse the previous slot's key.
            boolean credentialsSaved=RootStartCredentialSave.attempt(()->
                RootEncryptedCredentialStore.saveProfile(this,slot,
                    password.getText().toString(),routeKey.getText().toString()));
            if(!credentialsSaved)RootEncryptedCredentialStore.clearProfile(this,slot);
            profileResult.setText("已保存槽位"+slot+"："+profile.label+
                (credentialsSaved?"（密码/RouteKey按槽位设备加密保存）":
                    "（仅普通设置；此槽未存可用密码/RouteKey）")+
                "；物理Network仍需手选");
        }catch(Exception e){
            profileResult.setText("保存失败：填写有效名称及完整连接设置后再保存");
        }
    }
    private boolean loadNamedProfile(int slot){
        try{
            RootConnectionProfile profile=RootConnectionProfileStore.load(this,slot);
            if(profile==null){
                profileResult.setText("该槽位尚未保存连接配置");
                return false;
            }
            // Choose the same saved server's optional CA and its existing
            // per-slot Keystore record. No root-staged CA is touched here.
            String storedCA=RootConnectionProfileCAStore.loadSlot(this,slot);
            RootConnectionProfileCAStore.saveCurrent(this,storedCA);
            RootSavedCredentialRecord.Secrets saved=
                RootEncryptedCredentialStore.activateProfile(this,slot);
            RootConnectionSettingsStore.save(this,profile.settings);
            // UI-only: the running Root generation, UID route and physical
            // Network never change without a separate explicit START.
            restoreConnectionSettings(profile.settings);
            chooseInstalledApplications(); // current Android package/UID only
            password.setText(saved==null?"":saved.password);
            routeKey.setText(saved==null?"":saved.routeKey);
            caPEM.setText(storedCA);
            profileLabel.setText(profile.label);
            profileResult.setText("已载入槽位"+slot+"："+profile.label+
                (saved==null?"；请填写此服务器的密码/RouteKey":
                    "；本槽密码/RouteKey已从原Keystore恢复")+
                "。选择Network后手动START，运行中的Root不变");
            return true;
        }catch(Exception e){
            profileResult.setText("读取配置失败；当前已运行的Root会话不受影响");
            return false;
        }
    }
    private void loadNamedProfile(){
        coldSwitch.cancel();
        loadNamedProfile(chosenProfileSlot());
    }
    private void deleteNamedProfile(){
        coldSwitch.cancel();
        try{
            int slot=chosenProfileSlot();
            RootConnectionProfileStore.delete(this,slot);
            RootEncryptedCredentialStore.clearProfile(this,slot);
            RootConnectionProfileCAStore.clearSlot(this,slot);
            refreshNamedProfileChoices();
            profileResult.setText("已删除槽位"+slot+"的连接与该槽密码/RouteKey；运行中的Root未改变");
        }catch(Exception e){
            profileResult.setText("删除配置失败");
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
        boolean claimedStart=false;
        try{
            // Reserve the asynchronous Activity→Service gap before ANY
            // app-private credentials are written. The Service swaps this
            // reservation for its actual running native owner.
            if(RootClientService.sessionOwnerActive||
               !RootClientService.startDispatchPending.compareAndSet(false,true))
                throw new IllegalStateException(
                    "旧原生会话或START仍在执行。先STOP并等待结束，再手动START");
            claimedStart=true;
            if(physical.isEmpty())throw new IllegalArgumentException("No real physical Android Network");
            int pos=networks.getSelectedItemPosition();
            if(pos<0||pos>=physical.size())throw new IllegalArgumentException("No selected Network");
            PhysicalNetwork scope=physical.get(pos);
            if(PhysicalNetwork.exact(this,scope.handle,scope.interfaceName,
                scope.ifindex,scope.mtu,scope.address)==null){
                throw new IllegalArgumentException("Selected Network changed; refresh before Start");
            }
            RootTetherScope tether=tetherSharing.isChecked()?selectedTether(scope):null;
            String peer=serverAddress.getText().toString().trim();
            String sni=serverName.getText().toString().trim();
            String account=user.getText().toString().trim();
            String directCIDRs=RootDirectIPv4.canonicalCSV(
                directCIDRsField.getText().toString());
            final String manualDirectCIDRs=directCIDRs;
            if(autoConnectedDirect.isChecked()){
                String subnet=PhysicalNetwork.selectedConnectedIPv4Subnet(this,scope);
                if(!subnet.isEmpty())directCIDRs=RootDirectIPv4.withConnectedSubnet(directCIDRs,subnet);
            }
            String physicalDnsIPv4=physicalDNSFollowNetwork.isChecked()
                ?PhysicalNetwork.selectedDNSIPv4(this,scope)
                :RootPhysicalDNSUpstream.canonical(physicalDNSUpstreamField.getText().toString());
            String secret=password.getText().toString();
            String keyInput=routeKey.getText().toString(); // never trim/normalize a secret
            String pem=caPEM.getText().toString().trim();
            String recordCipher=recordCiphers.getSelectedItem().toString();
            String paddingMode=startupPaddingModes.getSelectedItem().toString();
            String fecMode=fecModes.getSelectedItem().toString();
            int fecProfile=Integer.parseInt(fecProfiles.getSelectedItem().toString());
            int nativeHealthSeconds=Integer.parseInt(nativeHealthIntervals.getSelectedItem().toString());
            // B44: Game2/off now uses the existing Normal physical and CN
            // UDP53 owner in the original Rust single-TUN M4.
            int requestedTunQueue=Integer.parseInt(tunQueueSizes.getSelectedItem().toString());
            boolean verifyTLS=tlsVerifyServer.isChecked();
            // Default is full ordinary App UID takeover AFTER true WBD
            // TLS/authenticated /32 and Rust M4. No pre-auth route mutation,
            // no Android system/root UID, VPN, fake-IP or system DNS.
            boolean allApps=allAppsDefault.isChecked();
            SelectedAppGroup chosen=null;
            AllAppRouteScope entire=null;
            String[] bypassPackages=null;
            int[] bypassUIDs=null;
            if(allApps){
                Map<String,Integer> chosenBypass=new TreeMap<>();
                for(InstalledAppTarget app:installedApps){
                    CheckBox cb=checkedBypassApps.get(app.packageName);
                    if(cb!=null&&cb.isChecked())chosenBypass.put(app.packageName,app.uid);
                }
                if(chosenBypass.size()>6)
                    throw new IllegalArgumentException("全App模式最多排除6个用户选定App包");
                bypassPackages=chosenBypass.keySet().toArray(new String[0]);
                bypassUIDs=new int[chosenBypass.size()];
                int at=0;
                for(int uid:chosenBypass.values())bypassUIDs[at++]=uid;
                entire=AllAppRouteScope.snapshot(this,bypassPackages,bypassUIDs);
                if(!AllAppRouteScope.same(this,entire.excludedAppIDs,
                    entire.managerPackages,bypassPackages,bypassUIDs))
                    throw new IllegalArgumentException("Root Manager或绕过App UID发生变化");
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
            int requestedOuterMTU=Integer.parseInt(outerMTUField.getText().toString().trim());
            if(requestedOuterMTU<576||requestedOuterMTU>1500)
                throw new IllegalArgumentException("外层IPv4 IP MTU须为576..1500字节");
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
            // Cold UI recall only. Failure does not block an otherwise valid
            // original Go/TLS connection or add an auth/security gate.
            try{RootConnectionProfileCAStore.saveCurrent(this,pem);}
            catch(Exception unavailable){/* current session uses its in-memory CA */}
            Intent request=new Intent(this,RootClientService.class);
            request.setAction(RootClientService.START);
            request.putExtra("handle",scope.handle);
            request.putExtra("iface",scope.interfaceName);
            request.putExtra("index",scope.ifindex);
            request.putExtra("mtu",scope.mtu);
            request.putExtra("local",scope.address);
            request.putExtra("peer",peer);
            request.putExtra("port",port);
            request.putExtra("outer_mtu",requestedOuterMTU);
            request.putExtra("record_cipher",recordCipher);
            request.putExtra("tun_txqlen",requestedTunQueue);
            request.putExtra("startup_padding",paddingMode);
            request.putExtra("game4_copy_schedule",game4CopySchedules.getSelectedItem().toString());
            request.putExtra("fec_mode",fecMode);
            request.putExtra("fec_profile",fecProfile);
            request.putExtra("native_health_seconds",nativeHealthSeconds);
            request.putExtra("cold_rotation_minutes",
                Integer.parseInt(coldRotationMinutes.getSelectedItem().toString()));
            request.putExtra("sni",sni);
            request.putExtra("user",account);
            request.putExtra("all_apps",allApps);
            request.putExtra("tunnel_dns",tunnelDNS.isChecked());
            request.putExtra("physical_dns",physicalDNS.isChecked());
            request.putExtra("cn_dns_split",cnSplitDNS.isChecked());
            request.putExtra("cn_ip_direct",cnIPDirect.isChecked());
            request.putExtra("outer_repair",outerRepair.isChecked());
            request.putExtra("app_tcp_dns",appTcpDNS.isChecked()&&
                (tunnelDNS.isChecked()||physicalDNS.isChecked()||cnSplitDNS.isChecked()));
            request.putExtra("system_dns",systemDNS.isChecked()&&
                (tunnelDNS.isChecked()||physicalDNS.isChecked()||cnSplitDNS.isChecked()));
            request.putExtra("system_dns6",systemDNS6.isChecked()&&
                (tunnelDNS.isChecked()||physicalDNS.isChecked()||cnSplitDNS.isChecked()));
            request.putExtra("ipv6_gateway",RootConnectionSettings.ipv6Gateway(ipv6GatewayField.getText().toString()));
            request.putExtra("ipv6_direct_cidrs",RootConnectionSettings.ipv6DirectCIDRs(ipv6DirectCIDRsField.getText().toString()));
            if(tether!=null){
                request.putExtra("tether_iface",tether.iface);
                request.putExtra("tether_subnet",tether.subnet);
                request.putExtra("tether_index",tether.index);
            }
            request.putExtra("direct_cidrs",directCIDRs);
            request.putExtra("direct_cidrs_manual",manualDirectCIDRs);
            request.putExtra("background_network_recovery",backgroundNetworkRecovery.isChecked());
            request.putExtra("direct_lan_auto",autoConnectedDirect.isChecked());
            request.putExtra("physical_dns_upstream",physicalDnsIPv4);
            request.putExtra("tunnel_dns_upstream",RootPhysicalDNSUpstream.tunnel(tunnelDNSUpstreamField.getText().toString()));
            request.putExtra("physical_dns_follow_network",physicalDNSFollowNetwork.isChecked());
            if(allApps){
                request.putExtra("exclude_appids",entire.excludedAppIDs);
                request.putExtra("manager_packages",entire.managerPackages);
                request.putExtra("bypass_packages",bypassPackages);
                request.putExtra("bypass_uids",bypassUIDs);
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
            if(autoNetworkRecovery!=null&&autoNetworkRecovery.isChecked())
                autoHandover.arm();
            // Save only validated non-secret UI settings. Physical Network
            // and authorized UID routing remain scoped to THIS Start.
            boolean remembered=true;
            try{saveConnectionSettings();}
            catch(Exception unavailable){remembered=false;}
            String notice=saved?"":"；设备密码自动保存失败（不影响本次连接）";
            if(!remembered)notice+="；普通连接参数未能保存";
            RootClientService.status=(verifyTLS
                ?"Root start — strict TLS server certificate validation ON"
                :"Root start — TLS certificate validation OFF (main default)")+notice;
            status.setText(RootClientService.status);
            // Preserve on-screen values for another Start in this Activity.
            // The keystore-backed snapshot also restores them after restart.
        }catch(Exception e){
            autoHandover.cancel();
            if(claimedStart)RootClientService.startDispatchPending.set(false);
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
            "原 Go FakeTCP/TLS + 原 Rust M4；Normal/off 默认，Fixed/Auto 显式实验选项；非 VPN/FakeIP。\n"+
            "① 选择实体 Wi-Fi/移动/有线IPv4网络  ② 输入 WBD 服务器/账户/Key\n"+
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
        TextView lanHelp=new TextView(this);
        lanHelp.setText("支持没有公网互联网的真实 Wi-Fi/USB Ethernet 局域网，"+
            "但服务器必须在该链路上可达。未获Android互联网验证的局域网"+
            "服务器域名会在START前由已选Network做一次本地DNS解析；无结果时继续原Go物理DNS引导；"+
            "若局域网没有DNS可直接填服务器IPv4，TLS SNI仍单独填写。"+
            "不会自动切换当前Root会话的网卡。");
        pane.addView(lanHelp);
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
        outerMTUField=input(pane,"外层完整 IPv4 IP MTU（576–1500 字节；默认1460，非TUN MTU）",
            InputType.TYPE_CLASS_NUMBER);
        outerMTUField.setText("1460");
        directCIDRsField=input(pane,
            "可选真实IPv4直连网段（逗号分隔，最多4个，如192.168.1.0/24；默认全走WBD）",
            InputType.TYPE_CLASS_TEXT);
        TextView directHint=new TextView(this);
        directHint.setText("仅对本次选定的普通App UID生效：原Root私有路由表将这些IPv4网段交给后续Android路由，"+
            "不经WBD TUN。不是域名分流、系统DNS、或已证明的物理接口出站。");
        pane.addView(directHint);
        autoConnectedDirect=new CheckBox(this);
        autoConnectedDirect.setText("可选：所选实体Network的当前IPv4直连子网自动绕过WBD（与手动CIDR合并，最多16条）");
        autoConnectedDirect.setChecked(false);
        pane.addView(autoConnectedDirect);
        recordCiphers=new Spinner(this);
        recordCiphers.setAdapter(new ArrayAdapter<>(this,
            android.R.layout.simple_spinner_dropdown_item,
            new String[]{"chacha20-poly1305","aes-128-gcm","aes-256-gcm"}));
        pane.addView(recordCiphers);
        TextView modeHint=new TextView(this);
        modeHint.setText("原传输：Normal/off、Fixed/Auto；Game2/4-off 或 game2-fixed/game4-fixed 复用原Go TLS与Rust单TUN/2或4RAW，固定Game FEC档位0–6。三种DNS保持；真机未验。");
        pane.addView(modeHint);
        fecModes=new Spinner(this);
        fecModes.setAdapter(new ArrayAdapter<>(this,
            android.R.layout.simple_spinner_dropdown_item,
            new String[]{"normal","fec-fixed","fec-auto","game2","game4","game2-fixed","game4-fixed"}));
        pane.addView(fecModes);
        TextView profileHint=new TextView(this);
        profileHint.setText("Fixed或Game2/4-fixed选择档位0–6（默认1）；Auto原质量换档；Normal/Game-off不使用档位");
        pane.addView(profileHint);
        fecProfiles=new Spinner(this);
        fecProfiles.setAdapter(new ArrayAdapter<>(this,
            android.R.layout.simple_spinner_dropdown_item,
            new String[]{"0","1","2","3","4","5","6"}));
        fecProfiles.setSelection(1);
        pane.addView(fecProfiles);
        TextView healthHint=new TextView(this);
        healthHint.setText("原Rust M4已认证Health发送间隔（秒）：15默认 / 30低频。"+
            "90秒dead门不变；低频仅减少空闲控制包，不保证所有网络时延或续航更优。");
        pane.addView(healthHint);
        nativeHealthIntervals=new Spinner(this);
        nativeHealthIntervals.setAdapter(new ArrayAdapter<>(this,
            android.R.layout.simple_spinner_dropdown_item,new String[]{"15","30"}));
        pane.addView(nativeHealthIntervals);
        TextView rotationHint=new TextView(this);
        rotationHint.setText("原生定时冷轮换（分钟）：0关闭 / 5 / 15 / 30。下次START生效，可随配置保存，原会话完整STOP后按本次连接参数重新认证同一实体Network；会暂时断流，不是热迁移。");
        pane.addView(rotationHint);
        coldRotationMinutes=new Spinner(this);
        coldRotationMinutes.setAdapter(new ArrayAdapter<>(this,
            android.R.layout.simple_spinner_dropdown_item,new String[]{"0","5","15","30"}));
        pane.addView(coldRotationMinutes);
        TextView cipherHint=new TextView(this);
        cipherHint.setText("原WBD受认证M3记录AEAD（默认ChaCha20）；AES-128/256为原协议已支持选项。" +
            "不同ARM64设备性能取决于CPU硬件与网络，请以实际测速选择。");
        pane.addView(cipherHint);
        TextView queueLabel=new TextView(this);
        queueLabel.setText("原 TUN 内核发送队列 txqueuelen（包；默认500，可选2048）");
        pane.addView(queueLabel);
        tunQueueSizes=new Spinner(this);
        tunQueueSizes.setAdapter(new ArrayAdapter<>(this,
            android.R.layout.simple_spinner_dropdown_item,
            new String[]{"500","2048"}));
        pane.addView(tunQueueSizes);
        TextView padLabel=new TextView(this);
        padLabel.setText("原生七模式隧道启动填充（默认off；tls仅TLS、flows普通TCP/UDP；不等于FEC）");
        pane.addView(padLabel);
        startupPaddingModes=new Spinner(this);
        startupPaddingModes.setAdapter(new ArrayAdapter<>(this,
            android.R.layout.simple_spinner_dropdown_item,
            new String[]{"off","tls","flows"}));
        pane.addView(startupPaddingModes);
        TextView game4ScheduleLabel=new TextView(this);
        game4ScheduleLabel.setText("Game4副本策略（默认宽错峰；仅Game4生效）");
        pane.addView(game4ScheduleLabel);
        game4CopySchedules=new Spinner(this);
        game4CopySchedules.setAdapter(new ArrayAdapter<>(this,
            android.R.layout.simple_spinner_dropdown_item,new String[]{"stagger-4-50-140","stagger-4-20-60","immediate"}));
        pane.addView(game4CopySchedules);
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
        clearSecrets.setText("清除所有已保存密码 / RouteKey（含4套配置）");
        clearSecrets.setOnClickListener(v->new AlertDialog.Builder(this)
            .setTitle("清除保存的登录凭据")
            .setMessage("删除本APK默认及4个配置槽的已保存密码/RouteKey和共用Keystore密钥，不影响当前Root会话或其他客户端。")
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
        Button clearCa=new Button(this);
        clearCa.setText("清除本机已导入的TLS CA（不影响密码/RouteKey）");
        clearCa.setOnClickListener(v->{
            File file=new File(getFilesDir(),RootPrivateCredentialFiles.CA);
            if(!file.exists()||file.delete()){
                caPEM.setText("");
                try{RootConnectionProfileCAStore.saveCurrent(this,"");}
                catch(Exception unavailable){/* original on-device CA already cleared */}
                status.setText("已清除当前TLS CA；配置槽中保存的CA只会在再次载入该槽时恢复");
            }else status.setText("无法清除本机TLS CA，请重试");
        });
        pane.addView(clearCa);
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
            +"取消全应用模式后，可选择最多 16 个实际 App UID。");
        pane.addView(targetHelp);
        allAppsDefault=new CheckBox(this);
        allAppsDefault.setText("默认：普通 App IPv4 走 WBD（服务器/本App/KernelSU排除，非全系统）");
        allAppsDefault.setChecked(true);
        pane.addView(allAppsDefault);
        tunnelDNS=new CheckBox(this);
        tunnelDNS.setText("隧道DNS：普通App UDP/53走配置的隧道上游并还原原解析器回包（系统DNS另选）");
        tunnelDNS.setChecked(true);
        pane.addView(tunnelDNS);
        tunnelDNSUpstreamField=input(pane,"隧道DNS IPv4上游（默认1.1.1.1；Normal/Fixed/Auto/Game、CN非CN域名及可选系统/热点DNS共用）",InputType.TYPE_CLASS_TEXT);
        tunnelDNSUpstreamField.setText(RootPhysicalDNSUpstream.TUNNEL_DEFAULT);
        physicalDNS=new CheckBox(this);
        physicalDNS.setText("可选物理DNS：进入WBD TUN的普通App UDP/53直接通过当前物理Network发送到223.5.5.5（全部域名，不是CN域名分流或Android系统DNS）");
        physicalDNS.setChecked(false);
        pane.addView(physicalDNS);
        physicalDNSUpstreamField=input(pane,
            "物理UDP53上游IPv4（默认223.5.5.5，可填物理LAN路由器DNS如192.168.1.1）",
            InputType.TYPE_CLASS_TEXT);
        physicalDNSUpstreamField.setText(RootPhysicalDNSUpstream.DEFAULT);
        physicalDNSFollowNetwork=new CheckBox(this);
        physicalDNSFollowNetwork.setText("物理DNS跟随所选Wi-Fi/移动/有线Network的IPv4 DNS（只在START时取值）");
        physicalDNSFollowNetwork.setChecked(false);
        physicalDNSFollowNetwork.setOnCheckedChangeListener((button,checked)->
            physicalDNSUpstreamField.setEnabled(!checked));
        pane.addView(physicalDNSFollowNetwork);
        TextView upstreamHint=new TextView(this);
        upstreamHint.setText("可选物理/CN DNS模式下原Rust M4使用此UDP53；"+
            "若WBD服务器填写域名，原Go也通过选定Network的同一DNS IPv4冷引导，"+
            "遇截断走同端点TCP53；可选跟随所选Network IPv4 DNS，IPv6-only需手填IPv4；"+
            "默认223.5.5.5，系统netd DNS不受影响。");
        pane.addView(upstreamHint);
        cnSplitDNS=new CheckBox(this);
        cnSplitDNS.setText("可选CN域名DNS分流：普通App UDP/53 CN域名走物理223.5.5.5，其他域名走配置的WBD隧道DNS（不接管Android系统DNS）");
        cnSplitDNS.setChecked(false);
        pane.addView(cnSplitDNS);
        Button importCN=new Button(this);
        importCN.setText("导入CN域名规则（main兼容文本，下次连接生效）");
        importCN.setOnClickListener(v->importCNDomainRules());
        pane.addView(importCN);
        Button resetCN=new Button(this);
        resetCN.setText("恢复APK内置官方CN域名规则");
        resetCN.setOnClickListener(v->{
            File custom=NativePayload.customCN(this);
            if(!custom.exists()||custom.delete())status.setText("已恢复内置CN域名规则，下次连接生效");
            else status.setText("未能移除自定义CN域名规则");
        });
        pane.addView(resetCN);
        cnIPDirect=new CheckBox(this);
        cnIPDirect.setText("普通CN业务分流：按签名APK内APNIC中国IPv4分配网段直连（普通App及已开启软件热点）；域名仍按上述DNS模式，海外实际IP仍走隧道");
        cnIPDirect.setChecked(false);
        pane.addView(cnIPDirect);
        outerRepair=new CheckBox(this);
        outerRepair.setText("外层机会式重传（原表演式重传；原密文最多一次；真机待验，默认关闭）");
        outerRepair.setChecked(false);
        pane.addView(outerRepair);
        appTcpDNS=new CheckBox(this);
        appTcpDNS.setText("可选App TCP/53 DNS：进入WBD的应用TCP查询也按上面选定的DNS模式处理（内核TCP，不接管系统netd）");
        appTcpDNS.setChecked(false);
        pane.addView(appTcpDNS);
        systemDNS=new CheckBox(this);
        systemDNS.setText("可选系统 DNS IPv4/53：所选应用和实体Network的普通系统UDP/TCP DNS按上述模式处理（不接管Private DNS/DoH）");
        systemDNS.setChecked(false);
        pane.addView(systemDNS);
        systemDNS6=new CheckBox(this);
        systemDNS6.setText("可选系统 DNS IPv6/53：普通IPv6地址DNS也进入上述模式（同时启用系统IPv4 DNS；不等于IPv6业务隧道）");
        systemDNS6.setChecked(false);
        pane.addView(systemDNS6);
        ipv6GatewayField=input(pane,"可选 IPv6 业务兼容承载：服务端 WBD TUN IPv4（如10.219.0.1；服务端须启用 --inner-ipv6；普通App IPv6 DNS跟随上述模式；留空关闭）",InputType.TYPE_CLASS_TEXT);
        ipv6GatewayField.setText("");
        ipv6DirectCIDRsField=input(pane,"IPv6直连CIDR（逗号分隔，最多16条；IPv6承载开启时生效；自动LAN直连同时覆盖所选Network的IPv6子网）",InputType.TYPE_CLASS_TEXT);
        ipv6DirectCIDRsField.setText("");
        tetherSharing=new CheckBox(this);
        tetherSharing.setText("可选：共享 WBD 到现有热点/USB（软件转发，Android 16；共享上述CIDR直连及DNS模式；IPv6承载且有实际下游/64时同时转发IPv6）");
        tetherSharing.setChecked(false);
        pane.addView(tetherSharing);
        tetherChoices=new Spinner(this);
        pane.addView(tetherChoices);
        tunnelDNS.setOnCheckedChangeListener((button,checked)->{
            if(checked){physicalDNS.setChecked(false);cnSplitDNS.setChecked(false);}
        });
        physicalDNS.setOnCheckedChangeListener((button,checked)->{
            if(checked){tunnelDNS.setChecked(false);cnSplitDNS.setChecked(false);}
        });
        cnSplitDNS.setOnCheckedChangeListener((button,checked)->{
            if(checked){tunnelDNS.setChecked(false);physicalDNS.setChecked(false);}
        });
        // B42: select B41 original Go/Rust Game2 owner, not a new protocol.
        fecModes.setOnItemSelectedListener(new android.widget.AdapterView.OnItemSelectedListener(){
            @Override public void onItemSelected(android.widget.AdapterView<?> parent,
                View view,int position,long id){
                if("game2".equals(fecModes.getSelectedItem().toString())||
                   "game4".equals(fecModes.getSelectedItem().toString())||
                   "game2-fixed".equals(fecModes.getSelectedItem().toString())||
                   "game4-fixed".equals(fecModes.getSelectedItem().toString())){
                    // Game uses the same authenticated padding selection as Normal.
                    game4CopySchedules.setEnabled("game4".equals(fecModes.getSelectedItem().toString())||
                        "game4-fixed".equals(fecModes.getSelectedItem().toString()));
                }
            }
            @Override public void onNothingSelected(android.widget.AdapterView<?> parent){}
        });
        selectedAppControls=new LinearLayout(this);
        selectedAppControls.setOrientation(LinearLayout.VERTICAL);
        pane.addView(selectedAppControls);
        TextView searchHint=new TextView(this);
        searchHint.setText("应用选择：按名称、包名或UID过滤；隐藏不代表取消已勾选。"+
            "枚举当前用户已安装普通App（含无桌面入口的游戏/服务App）；仅当前真实UID可选");
        selectedAppControls.addView(searchHint);
        appSearch=input(selectedAppControls,"过滤已安装应用（仅本地）",InputType.TYPE_CLASS_TEXT);
        appSearch.addTextChangedListener(new android.text.TextWatcher(){
            @Override public void beforeTextChanged(CharSequence s,int start,int count,int after){}
            @Override public void onTextChanged(CharSequence s,int start,int before,int count){
                applyAppSearch();
            }
            @Override public void afterTextChanged(android.text.Editable s){}
        });
        Button selectFiltered=new Button(this);
        selectFiltered.setText("勾选当前过滤的应用（保留其他已选，最多16个UID）");
        selectFiltered.setOnClickListener(v->selectMatchingApps());
        selectedAppControls.addView(selectFiltered);
        Button clearSelected=new Button(this);
        clearSelected.setText("清除当前所有应用勾选");
        clearSelected.setOnClickListener(v->{
            for(CheckBox check:checkedApps.values())check.setChecked(false);
            updateAppSelectionCount();
        });
        selectedAppControls.addView(clearSelected);
        selectedAppsSummary=new TextView(this);
        selectedAppControls.addView(selectedAppsSummary);
        appChoices=new LinearLayout(this);
        appChoices.setOrientation(LinearLayout.VERTICAL);
        selectedAppControls.addView(appChoices);

        selectedAppControls.setVisibility(View.GONE);
        // B34: full ordinary-app takeover keeps the original owned kernel
        // 20-profile FIB; selectively exclude up to six verified ordinary
        // package AppIDs across profiles with no new data/payload path.
        bypassAppControls=new LinearLayout(this);
        bypassAppControls.setOrientation(LinearLayout.VERTICAL);
        pane.addView(bypassAppControls);
        TextView bypassHint=new TextView(this);
        bypassHint.setText("全App模式可额外排除实际已安装App，令该App按Android后续系统路由直连。"+
            "仍仅影响IPv4；共享UID/跨用户相同AppID都会一起绕过WBD。"+
            "必须重新手动START；不保证Android netd最终选哪个物理接口。");
        bypassAppControls.addView(bypassHint);
        bypassSummary=new TextView(this);
        bypassAppControls.addView(bypassSummary);
        bypassSearch=input(bypassAppControls,"搜索需要绕过WBD的已安装App（名称/包名/UID）",
            InputType.TYPE_CLASS_TEXT);
        bypassSearch.addTextChangedListener(new android.text.TextWatcher(){
            @Override public void beforeTextChanged(CharSequence x,int a,int c,int after){}
            @Override public void onTextChanged(CharSequence x,int a,int before,int c){applyAppSearch();}
            @Override public void afterTextChanged(android.text.Editable e){}
        });
        Button toggleBypass=new Button(this);
        toggleBypass.setText("展开／折叠全App绕过名单（最多6个已安装应用）");
        toggleBypass.setOnClickListener(v->bypassChoices.setVisibility(
            bypassChoices.getVisibility()==View.VISIBLE?View.GONE:View.VISIBLE));
        bypassAppControls.addView(toggleBypass);
        Button clearBypass=new Button(this);
        clearBypass.setText("清空额外绕过应用");
        clearBypass.setOnClickListener(v->{
            for(CheckBox cb:checkedBypassApps.values())cb.setChecked(false);
            updateAppSelectionCount();
        });
        bypassAppControls.addView(clearBypass);
        bypassChoices=new LinearLayout(this);
        bypassChoices.setOrientation(LinearLayout.VERTICAL);
        bypassAppControls.addView(bypassChoices);
        bypassChoices.setVisibility(View.GONE);
        allAppsDefault.setOnCheckedChangeListener((button,checked)->{
            selectedAppControls.setVisibility(checked?View.GONE:View.VISIBLE);
            bypassAppControls.setVisibility(checked?View.VISIBLE:View.GONE);
        });
        bypassAppControls.setVisibility(View.VISIBLE);
        Button refreshApps=new Button(this);
        refreshApps.setText("Refresh installed applications");
        refreshApps.setOnClickListener(v->chooseInstalledApplications());
        pane.addView(refreshApps);
        // B50: four named daily connection profiles, all using the
        // existing B22 settings serializer and selected app UID recheck.
        TextView namedProfileHint=new TextView(this);
        namedProfileHint.setText("本机最多4套服务器/模式/UID配置；密码/RouteKey用现有Keystore分槽保存，可选本地TLS CA也随槽切换；真实物理Network始终手选。");
        pane.addView(namedProfileHint);
        profileSlots=new Spinner(this);
        profileSlots.setAdapter(new ArrayAdapter<>(this,
            android.R.layout.simple_spinner_dropdown_item,
            new String[]{"配置槽1","配置槽2","配置槽3","配置槽4"}));
        pane.addView(profileSlots);
        profileLabel=input(pane,"配置名称（例：家里Wi-Fi／游戏）",InputType.TYPE_CLASS_TEXT);
        profileLabel.setText("常用连接");
        Button saveProfile=new Button(this);
        saveProfile.setText("保存到所选配置槽");
        saveProfile.setOnClickListener(v->saveNamedProfile());
        pane.addView(saveProfile);
        Button loadProfile=new Button(this);
        loadProfile.setText("载入所选配置（不启动Root）");
        loadProfile.setOnClickListener(v->loadNamedProfile());
        pane.addView(loadProfile);
        Button connectProfile=new Button(this);
        connectProfile.setText("连接此配置／切换到此配置（使用选定实体Network）");
        connectProfile.setOnClickListener(v->connectSelectedSavedProfile());
        pane.addView(connectProfile);
        Button deleteProfile=new Button(this);
        deleteProfile.setText("删除所选配置槽");
        deleteProfile.setOnClickListener(v->deleteNamedProfile());
        pane.addView(deleteProfile);
        Button exportAllProfiles=new Button(this);
        exportAllProfiles.setText("导出全部4套配置（单个文件，不含凭据）");
        exportAllProfiles.setOnClickListener(v->exportAllProfiles());
        pane.addView(exportAllProfiles);
        Button importAllProfiles=new Button(this);
        importAllProfiles.setText("恢复全部4套配置（需重新填写本机凭据）");
        importAllProfiles.setOnClickListener(v->importAllProfiles());
        pane.addView(importAllProfiles);
        profileResult=new TextView(this);
        profileResult.setText("选择槽位保存/载入；每槽独立密码/RouteKey，旧原生会话不变，配合B49前台冷切网。");
        pane.addView(profileResult);
        Button rememberConnection=new Button(this);
        rememberConnection.setText("保存连接设置（本机，下次恢复；不含密码/RouteKey）");
        rememberConnection.setOnClickListener(v->{
            try{
                saveConnectionSettings();
                status.setText("已保存服务器、账号、模式及DNS/MTU等本机设置；密码/RouteKey仍由Keystore单独管理");
            }catch(Exception failure){
                status.setText("保存连接设置失败：请填写合法服务器/SNI/账户和模式参数");
            }
        });
        pane.addView(rememberConnection);
        Button exportPreset=new Button(this);
        exportPreset.setText("导出普通连接设置（换调试版可恢复，不含密码/RouteKey/CA）");
        exportPreset.setOnClickListener(v->exportConnectionPreset());
        pane.addView(exportPreset);
        Button importPreset=new Button(this);
        importPreset.setText("导入普通连接设置（仅恢复表单，仍须手动START）");
        importPreset.setOnClickListener(v->importConnectionPreset());
        pane.addView(importPreset);
        presetResult=new TextView(this);
        presetResult.setText("可通过系统文件选择器保存/恢复普通连接参数；"+
            "调试签名更换后需手动重填密码和RouteKey");
        presetResult.setTextIsSelectable(true);
        pane.addView(presetResult);
        Button connect=new Button(this);connect.setText("START — ROOT / ORIGINAL Go+Rust");
        connect.setOnClickListener(v->{coldSwitch.cancel();start();});
        pane.addView(connect);
        Button stop=new Button(this);stop.setText("STOP — WITHDRAW UID ROUTE / NATIVE JOIN");
        stop.setOnClickListener(v->{
            coldSwitch.cancel();
            autoHandover.cancel();
            Intent i=new Intent(this,RootClientService.class);
            i.setAction(RootClientService.STOP);
            startService(i);
        });
        pane.addView(stop);
        // Explicit two-stage cold physical Network reselection; NO
        // automatic root relaunch after Android onLost/capability changes.
        // The new START reuses the complete existing credential/UID/TLS
        // validation and creates an entirely fresh Go/Rust generation.
        Button reselect=new Button(this);
        reselect.setText("切换实体Network：STOP旧会话，再刷新并手动START");
        reselect.setOnClickListener(v->{
            coldSwitch.cancel();
            autoHandover.cancel();
            if(RootClientService.sessionOwnerActive||
               RootClientService.startDispatchPending.get()){
                new AlertDialog.Builder(this)
                    .setTitle("先退出原会话")
                    .setMessage("将先请求原Go/Rust停止并撤回旧普通App UID路由。"+
                        "不会自动连接另一个Network；请等退出，第二次点此按钮刷新网络列表，"+
                        "亲自选择新的Wi-Fi/蜂窝后手动START。")
                    .setNegativeButton("取消",null)
                    .setPositiveButton("请求STOP",(dialog,which)->{
                        Intent i=new Intent(this,RootClientService.class);
                        i.setAction(RootClientService.STOP);
                        startService(i);
                        status.setText("旧会话STOP已请求；等待实际Go/Rust退出再重选Network");
                    }).show();
            }else{
                chooseNetworks();
                status.setText(RootClientService.previousOwnerStopConfirmed
                    ?"旧会话原生Stop及UID路由撤回已确认；选择新Network后手动START"
                    :"网络列表已刷新；没有完整旧会话Stop收据，"+
                     "如有残留先用WBD恢复网络，再手动START");
            }
        });
        pane.addView(reselect);
        // User explicitly chooses a real new Network before requesting STOP.
        // This is not an onLost-triggered automatic Root relaunch.
        Button oneShotSwitch=new Button(this);
        oneShotSwitch.setText("切换到选中Network：旧会话Stop完成后自动START一次");
        oneShotSwitch.setOnClickListener(v->{
            autoHandover.cancel();
            if(!RootClientService.sessionOwnerActive||
               RootClientService.startDispatchPending.get()){
                status.setText("没有可切换的活跃会话；请选择Network后手动START");
                return;
            }
            int pos=networks.getSelectedItemPosition();
            if(pos<0||pos>=physical.size()){
                status.setText("请先选择目标Network");
                return;
            }
            PhysicalNetwork target=physical.get(pos);
            if(PhysicalNetwork.exact(this,target.handle,target.interfaceName,
                target.ifindex,target.mtu,target.address)==null){
                chooseNetworks();
                status.setText("目标Network发生变化，请重新选择");
                return;
            }
            coldSwitch.arm(target.handle,target.interfaceName,target.ifindex,
                target.mtu,target.address);
            Intent stopOld=new Intent(this,RootClientService.class);
            stopOld.setAction(RootClientService.STOP);
            try{
                startService(stopOld);
                status.setText("已请求原Go/Rust owned Stop；确认全部归还后启动所选Network一次");
            }catch(Exception failure){
                coldSwitch.cancel();
                status.setText("旧会话Stop请求未派发；没有启动新Root会话");
            }
        });
        pane.addView(oneShotSwitch);
        autoNetworkRecovery=new CheckBox(this);
        autoNetworkRecovery.setText("前台自动冷重连（可选）：Network变化后完整STOP，再选当前真实物理网络重新认证；失败不循环，离开本页面即取消");
        autoNetworkRecovery.setChecked(false);
        autoNetworkRecovery.setOnCheckedChangeListener((button,checked)->{
            if(!checked)autoHandover.cancel();
            else{
                if(backgroundNetworkRecovery!=null)backgroundNetworkRecovery.setChecked(false);
                if(RootClientService.sessionOwnerActive&&!RootClientService.backgroundRecoveryActive&&
                   !RootClientService.networkStopRequested)
                    autoHandover.arm();
            }
        });
        pane.addView(autoNetworkRecovery);
        backgroundNetworkRecovery=new CheckBox(this);
        backgroundNetworkRecovery.setText("后台自动冷恢复（下次START生效）：原Go/Rust完整STOP后自动选网，断网等待系统Network事件；锁屏可用，STOP或移除任务即取消");
        backgroundNetworkRecovery.setChecked(false);
        backgroundNetworkRecovery.setOnCheckedChangeListener((button,checked)->{
            if(checked){autoNetworkRecovery.setChecked(false);autoHandover.cancel();}
        });
        pane.addView(backgroundNetworkRecovery);
        Button restore=new Button(this);
        restore.setText("恢复网络（WBD临时Root防火墙/UID路由）");
        restore.setOnClickListener(v->{
            autoHandover.cancel();
            new AlertDialog.Builder(this)
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
            }).show();
        });
        pane.addView(restore);
        Button inspectDNS=new Button(this);
        inspectDNS.setText("查看本会话DNS收发（本机脱敏收据，无Root/联网）");
        inspectDNS.setOnClickListener(v->{
            String report=RootDiagnosticReport.build(
                getFilesDir(),signedSource(),Build.VERSION.SDK_INT);
            dnsStatusBrief.setText(RootDNSStatusBrief.fromReport(report));
        });
        pane.addView(inspectDNS);
        dnsStatusBrief=new TextView(this);
        dnsStatusBrief.setText("点击上方按钮读取当前会话实际DNS路径收据");
        dnsStatusBrief.setTextIsSelectable(true);
        pane.addView(dnsStatusBrief);
        // B21: on-demand view of ALREADY collected original Rust M4
        // RAW/TUN receipts; never call Root, netd or native DATA here.
        Button inspectM4=new Button(this);
        inspectM4.setText("查看最近原生 M4 TCP/UDP 内核收发（本机）");
        inspectM4.setOnClickListener(v->{
            String report=RootDiagnosticReport.build(
                getFilesDir(),signedSource(),Build.VERSION.SDK_INT);
            m4TrafficBrief.setText(RootM4TrafficBrief.fromReport(report));
        });
        pane.addView(inspectM4);
        m4TrafficBrief=new TextView(this);
        m4TrafficBrief.setText("点击查看最近 M4 真实内核收发；不是 App 端到端成功收据");
        m4TrafficBrief.setTextIsSelectable(true);
        pane.addView(m4TrafficBrief);
        fecStatusText=new TextView(this);
        fecStatusText.setText(RootClientService.fecStatus);
        fecStatusText.setTextIsSelectable(true);
        // Actual authenticated original Rust revision, not an E2E claim.
        pane.addView(fecStatusText);
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
        // The exact same public CA is reused across strict-TLS STARTs;
        // Android Keystore credentials and TLS trust policy stay separate.
        recallSavedTLSCA();
        // Restore UI choices only. Re-enumerate physical Networks and
        // installed App UIDs from Android, never reuse an old route handle.
        try{restoreConnectionSettings(RootConnectionSettingsStore.load(this));}
        catch(Exception unavailable){
            status.setText("本机普通连接设置未恢复，请重新填写（不影响手动START）");
        }
        chooseNetworks();
        chooseInstalledApplications();
        refreshNamedProfileChoices();
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
        watchTetherChoices();
        // UI-only snapshot refresh; Service's already-owned Network,
        // route and generation are NEVER implicitly switched.
        if(autoNetworkRecovery!=null&&autoNetworkRecovery.isChecked()&&
           RootClientService.sessionOwnerActive&&
           !RootClientService.networkStopRequested)
            autoHandover.arm();
        chooseNetworks();
        chooseInstalledApplications();
        refreshNamedProfileChoices();
        ui.post(refreshStatus);
    }
    @Override protected void onPause(){
        if(tetherWatch!=null){tetherWatch.close();tetherWatch=null;}
        tetherScopes.clear();
        coldSwitch.cancel(); // explicit authorization ends with foreground Activity
        autoHandover.cancel();
        ui.removeCallbacks(refreshStatus);super.onPause();
    }
}
