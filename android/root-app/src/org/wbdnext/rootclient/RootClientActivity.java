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
    // B49: one foreground user-triggered cold reselect, never background Root restart.
    private final RootColdNetworkSwitch coldSwitch=new RootColdNetworkSwitch();
    private final List<InstalledAppTarget> installedApps=new ArrayList<>();
    private final Map<String,CheckBox> checkedApps=new TreeMap<>();
    private final Map<String,CheckBox> checkedBypassApps=new TreeMap<>();
    // A saved selection is only restored if fresh package+UID still match;
    // the OS Network handle and any root route are never restored.
    private final Map<String,Integer> restoredSelection=new TreeMap<>();
    private final Map<String,Integer> restoredBypass=new TreeMap<>();
    private EditText serverAddress,serverName,user,password,routeKey,caPEM,serverPort,outerMTUField,directCIDRsField,physicalDNSUpstreamField;
    private Spinner networks,recordCiphers,tunQueueSizes,startupPaddingModes,fecModes,fecProfiles,nativeHealthIntervals,profileSlots;
    private CheckBox allAppsDefault,tlsVerifyServer,tunnelDNS,physicalDNS,cnSplitDNS,physicalDNSFollowNetwork,autoConnectedDirect;
    private LinearLayout appChoices,selectedAppControls,bypassAppControls,bypassChoices;
    private EditText appSearch,bypassSearch;
    private TextView selectedAppsSummary,bypassSummary,presetResult,profileResult;
    private EditText profileLabel;
    private RootConnectionSettings pendingPresetExport;
    private TextView status,deviceSelfTestResult,diagnosticExportResult,dnsStatusBrief,fecStatusText,m4TrafficBrief;
    private static final int SAFE_DIAGNOSTIC_SAVE=2042;
    private static final int LOCAL_TLS_CA_IMPORT=2043;
    private static final int CONNECTION_PRESET_EXPORT=2044;
    private static final int CONNECTION_PRESET_IMPORT=2045;
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
            status.setText("已导入并保留 "+certs.size()+" 张本地TLS证书；勾选严格校验后原Go才使用");
        }catch(Exception failure){
            status.setText("CA导入或本机保存失败；请核对PEM并重新导入");
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
    @Override protected void onActivityResult(int requestCode,int resultCode,Intent data){
        super.onActivityResult(requestCode,resultCode,data);
        if(requestCode==LOCAL_TLS_CA_IMPORT){
            if(resultCode==RESULT_OK)acceptTLSCA(data);
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
        boolean ready=coldSwitch.complete(
            RootClientService.previousOwnerStopConfirmed,matched>=0);
        if(!ready){
            RootClientService.status="一键冷切网中止：旧原生Stop未完整确认或目标Network已变化；请检查后手动START";
            return;
        }
        networks.setSelection(matched);
        // Original Activity start() owns all UID/secret/Network validation,
        // original FakeTCP/TLS/lease, Rust M4 and kernel journal.
        start();
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
            "当前已勾选 "+count+" 个应用 / "+uids.size()+" 个UID（最多8个不同UID、16个包）。"+
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
            selectedAppsSummary.setText("当前筛选结果超过8个不同UID/16个包，或没有匹配；"+
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
            autoConnectedDirect.isChecked());
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
        physicalDNSFollowNetwork.setChecked(s.physicalDNSFollowNetwork);
        selectSpinner(nativeHealthIntervals,Integer.toString(s.nativeHealthSeconds));
        selectSpinner(recordCiphers,s.cipher);
        selectSpinner(tunQueueSizes,Integer.toString(s.tunQueue));
        selectSpinner(startupPaddingModes,s.padding);
        selectSpinner(fecModes,s.mode);
        selectSpinner(fecProfiles,Integer.toString(s.profile));
        tlsVerifyServer.setChecked(s.verifyTLS);
        tunnelDNS.setChecked(s.tunnelDNS);
        physicalDNS.setChecked(s.physicalDNS);
        cnSplitDNS.setChecked(s.cnSplitDNS);
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
    private int chosenProfileSlot(){
        return profileSlots.getSelectedItemPosition()+1;
    }
    private void saveNamedProfile(){
        try{
            int slot=chosenProfileSlot();
            RootConnectionProfile profile=new RootConnectionProfile(
                profileLabel.getText().toString(),connectionSettingsFromUi());
            RootConnectionProfileStore.save(this,slot,profile);
            profileResult.setText("已保存槽位"+slot+"："+
                profile.label+"（原Normal/Fixed/Auto/Game及UID/DNS/MTU；不含密码/Key/物理Network）");
        }catch(Exception e){
            profileResult.setText("保存失败：填写有效名称及完整连接设置后再保存");
        }
    }
    private void loadNamedProfile(){
        try{
            int slot=chosenProfileSlot();
            RootConnectionProfile profile=RootConnectionProfileStore.load(this,slot);
            if(profile==null){
                profileResult.setText("该槽位尚未保存连接配置");
                return;
            }
            // UI-only. Previous Root generation, kernel routes and selected
            // physical Network are never changed by a preset load.
            restoreConnectionSettings(profile.settings);
            chooseInstalledApplications(); // current Android package/UID only
            RootConnectionSettingsStore.save(this,profile.settings);
            profileLabel.setText(profile.label);
            profileResult.setText("已载入槽位"+slot+"："+profile.label+
                "；可选择真实Network并手动START，运行中的Root不变");
        }catch(Exception e){
            profileResult.setText("读取配置失败；当前已运行的Root会话不受影响");
        }
    }
    private void deleteNamedProfile(){
        try{
            int slot=chosenProfileSlot();
            RootConnectionProfileStore.delete(this,slot);
            profileResult.setText("已删除槽位"+slot+"的本机连接配置；正在运行的Root未改变");
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
            String peer=serverAddress.getText().toString().trim();
            String sni=serverName.getText().toString().trim();
            String account=user.getText().toString().trim();
            String directCIDRs=RootDirectIPv4.canonicalCSV(
                directCIDRsField.getText().toString());
            if(autoConnectedDirect.isChecked()){
                String subnet=PhysicalNetwork.selectedConnectedIPv4Subnet(this,scope);
                directCIDRs=RootDirectIPv4.withConnectedSubnet(directCIDRs,subnet);
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
            if(!"normal".equals(fecMode)&&!"off".equals(paddingMode))
                throw new IllegalArgumentException("Fixed/Auto/Game2/Game4 and fixed Game FEC require startup padding off");
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
            request.putExtra("fec_mode",fecMode);
            request.putExtra("fec_profile",fecProfile);
            request.putExtra("native_health_seconds",nativeHealthSeconds);
            request.putExtra("sni",sni);
            request.putExtra("user",account);
            request.putExtra("all_apps",allApps);
            request.putExtra("tunnel_dns",tunnelDNS.isChecked());
            request.putExtra("physical_dns",physicalDNS.isChecked());
            request.putExtra("cn_dns_split",cnSplitDNS.isChecked());
            request.putExtra("direct_cidrs",directCIDRs);
            request.putExtra("direct_lan_auto",autoConnectedDirect.isChecked());
            request.putExtra("physical_dns_upstream",physicalDnsIPv4);
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
        autoConnectedDirect.setText("可选：所选实体Network的当前IPv4直连子网自动绕过WBD（与手动CIDR合并，最多4条）");
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
        padLabel.setText("原 Normal 隧道启动填充（默认off；tls仅TLS、flows普通TCP/UDP；不等于FEC）");
        pane.addView(padLabel);
        startupPaddingModes=new Spinner(this);
        startupPaddingModes.setAdapter(new ArrayAdapter<>(this,
            android.R.layout.simple_spinner_dropdown_item,
            new String[]{"off","tls","flows"}));
        pane.addView(startupPaddingModes);
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
        Button clearCa=new Button(this);
        clearCa.setText("清除本机已导入的TLS CA（不影响密码/RouteKey）");
        clearCa.setOnClickListener(v->{
            File file=new File(getFilesDir(),RootPrivateCredentialFiles.CA);
            if(!file.exists()||file.delete()){
                caPEM.setText("");
                status.setText("已清除本机TLS CA；严格TLS校验若需私有CA请重新导入");
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
            +"取消全应用模式后，可选择最多 8 个实际 App UID。");
        pane.addView(targetHelp);
        allAppsDefault=new CheckBox(this);
        allAppsDefault.setText("默认：普通 App IPv4 走 WBD（服务器/本App/KernelSU排除，非全系统）");
        allAppsDefault.setChecked(true);
        pane.addView(allAppsDefault);
        tunnelDNS=new CheckBox(this);
        tunnelDNS.setText("隧道DNS：已进入WBD TUN的普通App UDP/53走1.1.1.1并还原原解析器回包（不接管Android系统DNS / CN分流）");
        tunnelDNS.setChecked(true);
        pane.addView(tunnelDNS);
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
        cnSplitDNS.setText("可选CN8503域名DNS分流：普通App UDP/53 CN域名走物理223.5.5.5，其他域名走WBD隧道1.1.1.1（不接管Android系统DNS）");
        cnSplitDNS.setChecked(false);
        pane.addView(cnSplitDNS);
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
                    // Keep whichever of Normal's three DNS modes was
                    // selected; Game2 retains no startup padding.
                    startupPaddingModes.setSelection(0);
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
        selectFiltered.setText("勾选当前过滤的应用（保留其他已选，最多8个UID）");
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
        TextView profileHint=new TextView(this);
        profileHint.setText("本机常用连接：最多4套服务器/模式/UID/分流配置。仅切换表单；密码、RouteKey、CA及实体Network不会存入配置。");
        pane.addView(profileHint);
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
        Button deleteProfile=new Button(this);
        deleteProfile.setText("删除所选配置槽");
        deleteProfile.setOnClickListener(v->deleteNamedProfile());
        pane.addView(deleteProfile);
        profileResult=new TextView(this);
        profileResult.setText("选择槽位，保存或载入；之后正常START/STOP，也可与B49前台冷切网配合。");
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
        connect.setOnClickListener(v->start());
        pane.addView(connect);
        Button stop=new Button(this);stop.setText("STOP — WITHDRAW UID ROUTE / NATIVE JOIN");
        stop.setOnClickListener(v->{
            coldSwitch.cancel();
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
        // UI-only snapshot refresh; Service's already-owned Network,
        // route and generation are NEVER implicitly switched.
        chooseNetworks();
        chooseInstalledApplications();
        ui.post(refreshStatus);
    }
    @Override protected void onPause(){
        coldSwitch.cancel(); // explicit authorization ends with foreground Activity
        ui.removeCallbacks(refreshStatus);super.onPause();
    }
}
