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
import android.widget.RadioGroup;
import android.widget.RadioButton;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import android.graphics.Typeface;
import android.content.res.ColorStateList;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.ViewGroup;
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
    private final LinearLayout[] pages=new LinearLayout[4];
    private final Button[] tabs=new Button[4];
    private ScrollView pageScroll;
    private LinearLayout pageHost;
    private TextView homeTitle,homeSummary,routeSummary,serviceDetail;
    private Button homeConnect,homeStop,routeFullButton,routeSplitButton,updateCNButton;
    private int currentPage=0;
    private String lastServiceStatus="";
    private boolean cnUpdateRunning=false;
    private static final int BG=0xfff4f6f8, SURFACE=0xffffffff, INK=0xff152b3a,
        MUTED=0xff526675, ACCENT=0xff146e68, LINE=0xffdbe4e8;
    private int dp(int n){return Math.round(n*getResources().getDisplayMetrics().density);}
    private GradientDrawable rounded(int color,int radius){
        GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(radius));return d;
    }
    private TextView text(String value,int sp,int color,boolean bold){
        TextView t=new TextView(this);t.setText(value);t.setTextSize(sp);t.setTextColor(color);
        if(bold)t.setTypeface(Typeface.DEFAULT,Typeface.BOLD);
        return t;
    }
    private LinearLayout vertical(){
        LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);return l;
    }
    private LinearLayout section(LinearLayout page,String title,String hint){
        LinearLayout l=vertical();l.setPadding(dp(16),dp(14),dp(16),dp(14));
        l.setBackground(rounded(SURFACE,16));
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);
        lp.bottomMargin=dp(12);page.addView(l,lp);
        l.addView(text(title,17,INK,true));
        if(!hint.isEmpty()){
            TextView h=text(hint,13,MUTED,false);h.setPadding(0,dp(5),0,dp(9));l.addView(h);
        }
        return l;
    }
    private Button action(String title,boolean primary,Runnable action){
        Button b=new Button(this);b.setText(title);b.setAllCaps(false);
        b.setTextSize(15);b.setTextColor(primary?SURFACE:ACCENT);
        b.setBackground(rounded(primary?ACCENT:0xffe8f1f0,12));
        b.setMinHeight(dp(48));b.setPadding(dp(12),dp(8),dp(12),dp(8));
        b.setOnClickListener(v->action.run());return b;
    }
    private void showPage(int page){
        currentPage=page;
        for(int i=0;i<pages.length;i++){
            pages[i].setVisibility(i==page?View.VISIBLE:View.GONE);
            tabs[i].setTextColor(i==page?SURFACE:MUTED);
            tabs[i].setBackground(rounded(i==page?ACCENT:SURFACE,12));
            tabs[i].setSelected(i==page);
        }
        pageScroll.scrollTo(0,0);
        refreshHome();
    }
    private void polish(View v){
        if(v instanceof Button && !(v instanceof android.widget.CompoundButton)){
            Button b=(Button)v;b.setAllCaps(false);b.setTextSize(14);
            if(b!=homeConnect&&b!=homeStop&&v.getBackground()!=null){
                b.setTextColor(ACCENT);b.setBackground(rounded(0xffe8f1f0,10));
                b.setMinHeight(dp(44));
            }
        }else if(v instanceof android.widget.CompoundButton){
            android.widget.CompoundButton cb=(android.widget.CompoundButton)v;cb.setTextColor(INK);
            cb.setButtonTintList(ColorStateList.valueOf(ACCENT));
            cb.setTextSize(14);cb.setMinHeight(dp(44));
        }else if(v instanceof EditText){
            EditText e=(EditText)v;e.setTextColor(INK);e.setHintTextColor(MUTED);
            e.setTextSize(15);e.setBackgroundTintList(ColorStateList.valueOf(LINE));
        }else if(v instanceof Spinner){
            ((Spinner)v).setMinimumHeight(dp(48));
            v.setBackgroundTintList(ColorStateList.valueOf(MUTED));
        }else if(v instanceof TextView && v!=homeTitle&&v!=homeSummary&&v!=routeSummary&&v!=status){
            TextView t=(TextView)v;t.setTextColor(MUTED);
            t.setPadding(t.getPaddingLeft(),Math.max(t.getPaddingTop(),dp(5)),t.getPaddingRight(),Math.max(t.getPaddingBottom(),dp(5)));
        }
        if(v instanceof ViewGroup){
            ViewGroup g=(ViewGroup)v;for(int i=0;i<g.getChildCount();i++)polish(g.getChildAt(i));
        }
    }
    // Actual current form policy: full tunnel has no optional destination
    // bypass; split uses the existing shared UID FIB and DNS settings.
    private boolean splitSelected(){
        return RootUiRouting.isSplit(cnIPDirect.isChecked(),cnSplitDNS.isChecked(),
            physicalDNS.isChecked(),autoConnectedDirect.isChecked(),
            directCIDRsField.getText().toString(),ipv6DirectCIDRsField.getText().toString());
    }
    private void chooseFullRoute(){
        cnIPDirect.setChecked(false);dnsModes.check(tunnelDNS.getId());autoConnectedDirect.setChecked(false);
        directCIDRsField.setText("");ipv6DirectCIDRsField.setText("");refreshHome();
    }
    private void chooseSplitRoute(){
        cnIPDirect.setChecked(true);dnsModes.check(cnSplitDNS.getId());refreshHome();
    }
    private void setTextIfChanged(TextView t,String value){
        if(t!=null&&!value.contentEquals(t.getText()))t.setText(value);
    }
    private void refreshHome(){
        if(homeTitle==null||allAppsDefault==null||cnIPDirect==null||ipv6DirectCIDRsField==null)return;
        boolean active=RootClientService.sessionOwnerActive;
        boolean pending=RootClientService.startDispatchPending.get()||coldSwitch.pending();
        boolean ready=active&&RootClientService.sessionUiReady;
        setTextIfChanged(homeTitle,pending?"正在切换 / 连接":ready?"已连接":active?"正在连接 / 恢复":"未连接");
        if(homeTitle.getCurrentTextColor()!=(ready&&!pending?ACCENT:INK))
            homeTitle.setTextColor(ready&&!pending?ACCENT:INK);
        setTextIfChanged(homeSummary,(ready?"当前服务器 · "+RootClientService.activeUiServer+"\n":"")+"下次连接 · "+(serverAddress.getText().toString().trim().isEmpty()?"尚未选择服务器":serverAddress.getText().toString().trim())+
            "\n"+(allAppsDefault.isChecked()?"全局普通应用":"仅选定应用")+" · "+(splitSelected()?"分流":"全量隧道")+
            " · "+fecModes.getSelectedItem().toString());
        if(routeSummary!=null)setTextIfChanged(routeSummary,"当前设置："+(allAppsDefault.isChecked()?"全局普通应用":"仅选定应用")+" / "+(splitSelected()?"按目标分流":"全量隧道")+"（下次连接生效）");
        if(routeFullButton!=null&&routeSplitButton!=null){
            boolean split=splitSelected();
            if(routeFullButton.isSelected()!=!split||routeSplitButton.isSelected()!=split){
            routeFullButton.setBackground(rounded(split?0xffe8f1f0:ACCENT,12));
            routeFullButton.setTextColor(split?ACCENT:SURFACE);
            routeFullButton.setSelected(!split);
            routeSplitButton.setBackground(rounded(split?ACCENT:0xffe8f1f0,12));
            routeSplitButton.setTextColor(split?SURFACE:ACCENT);
            routeSplitButton.setSelected(split);
            }
        }
        homeConnect.setEnabled(!exitRequested&&!active&&!pending);
        homeConnect.setAlpha(!active&&!pending?1f:.45f);
        homeStop.setEnabled(active||pending);
        homeStop.setAlpha(active||pending?1f:.45f);
        // The home status is summarized above; full native detail lives in diagnostics.
        if(serviceDetail!=null)setTextIfChanged(serviceDetail,RootClientService.status);
    }
    private void quickChooseServer(){
        refreshNamedProfileChoices();
        String[] names=new String[RootConnectionProfile.SLOTS];
        for(int i=0;i<names.length;i++)names[i]=profileSlots.getItemAtPosition(i).toString();
        new AlertDialog.Builder(this).setTitle("选择服务器")
            .setItems(names,(d,which)->{
                profileSlots.setSelection(which);showPage(1);
                connectSelectedSavedProfile();
            }).setNeutralButton("管理服务器",(d,w)->showPage(1))
            .setNegativeButton("取消",null).show();
    }
    private boolean exitRequested=false;
    private void requestExit(){
        if(cnUpdateRunning){status.setText("请等待域名库更新完成");return;}
        exitRequested=true;
        coldSwitch.cancel();autoHandover.cancel();
        if(RootClientService.sessionOwnerActive||RootClientService.startDispatchPending.get()){
            requestStop();status.setText("正在断开并退出 WBD…");
        }else finishAndRemoveTask();
    }
    private void requestStop(){
        coldSwitch.cancel();autoHandover.cancel();
        Intent i=new Intent(this,RootClientService.class);i.setAction(RootClientService.STOP);
        startService(i);status.setText("已请求断开，等待原生会话退出");
    }

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
    private RadioButton tunnelDNS,physicalDNS,cnSplitDNS;
    private RadioGroup dnsModes;
    private CheckBox allAppsDefault,tlsVerifyServer,cnIPDirect,outerRepair,physicalDNSFollowNetwork,autoConnectedDirect,autoNetworkRecovery,backgroundNetworkRecovery,appTcpDNS,tetherSharing,systemDNS,systemDNS6;
    private Spinner tetherChoices;
    private RootTetherScope tetherWatch;
    private final java.util.List<RootTetherScope> tetherScopes=new java.util.ArrayList<>();
    private void watchTetherChoices(){
        if(tetherWatch!=null)return;
        try{tetherWatch=RootTetherScope.watch(this,scopes->{
            tetherSharing.setEnabled(true);
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
    private TextView selectedAppsSummary,bypassSummary,profileResult;
    private EditText profileLabel;
    private RootConnectionProfileBundle.Entry[] pendingBundleExport;
    private Button saveAllButton;
    private LinearLayout diagnosticsPanel;
    private static final String ACTIVE_SLOT="active-server-slot";
    private TextView status,diagnosticExportResult,dnsStatusBrief,fecStatusText,m4TrafficBrief;
    private static final int SAFE_DIAGNOSTIC_SAVE=2042;
    private static final int LOCAL_TLS_CA_IMPORT=2043;
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
            caPEM.setText(pem);
            status.setText("已导入 "+certs.size()+" 张证书");
        }catch(Exception failure){
            status.setText("CA导入或本机保存失败；请核对PEM并重新导入");
        }
    }
    // B53: one explicit SAF transaction for all ten named slots.
    // No Root permission, credential plaintext, CA or physical Network handle.
    private void exportAllProfiles(){
        try{
            RootConnectionProfileBundle.Entry[] profiles=
                new RootConnectionProfileBundle.Entry[RootConnectionProfile.SLOTS];
            int count=0;
            for(int i=0;i<profiles.length;i++){
                RootConnectionProfile profile=RootConnectionProfileStore.load(this,i+1);
                if(profile==null)continue;
                RootSavedCredentialRecord.Secrets login=RootEncryptedCredentialStore.loadProfile(this,i+1);
                profiles[i]=new RootConnectionProfileBundle.Entry(profile,
                    login==null?"":login.password,login==null?"":login.routeKey,
                    RootConnectionProfileCAStore.loadSlot(this,i+1));
                count++;
            }
            if(count==0){
                profileResult.setText("十个配置槽均为空，请先保存连接配置");
                return;
            }
            pendingBundleExport=profiles;
            Intent select=new Intent(Intent.ACTION_CREATE_DOCUMENT);
            select.addCategory(Intent.CATEGORY_OPENABLE);
            select.setType("application/octet-stream");
            select.putExtra(Intent.EXTRA_TITLE,"wbd-root-ten-profiles.wbpb");
            startActivityForResult(select,PROFILE_BUNDLE_EXPORT);
        }catch(Exception unavailable){
            pendingBundleExport=null;
            profileResult.setText("无法读取当前十个配置槽，导出未开始");
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
            RootConnectionProfileBundle.Entry[] snapshot=pendingBundleExport;
            pendingBundleExport=null;
            if(result!=RESULT_OK||data==null||data.getData()==null||
               snapshot==null){
                profileResult.setText("十槽配置导出已取消");
                return;
            }
            try(OutputStream out=getContentResolver().openOutputStream(
                data.getData(),"wt")){
                if(out==null)throw new java.io.IOException("No profile export output");
                RootConnectionProfileBundle.writeComplete(out,snapshot);
                profileResult.setText("全部服务器已导出（含密码、密钥和证书）");
            }catch(Exception unavailable){
                profileResult.setText("十槽导出失败：未完整写入文件");
            }
            return;
        }
        if(result!=RESULT_OK||data==null||data.getData()==null){
            profileResult.setText("十槽导入已取消");
            return;
        }
        coldSwitch.cancel();
        try(InputStream in=getContentResolver().openInputStream(data.getData())){
            RootConnectionProfileBundle.Entry[] restored=RootConnectionProfileBundle.readComplete(in);
            if(restored==null)throw new IllegalArgumentException("invalid WBD profiles");
            // Import replaces the slots contained in the bundle only. Reusing old slot
            // credentials for another server would select the wrong account.
            // The active Go/Rust process owns separate staged files already.
            for(int i=0;i<restored.length;i++){
                int slot=i+1;
                RootConnectionProfileBundle.Entry entry=restored[i];
                if(entry==null){
                    RootConnectionProfileStore.delete(this,slot);
                    RootEncryptedCredentialStore.clearProfile(this,slot);
                    RootConnectionProfileCAStore.clearSlot(this,slot);
                }else{
                    if(entry.password.isEmpty())RootEncryptedCredentialStore.clearProfile(this,slot);
                    else RootEncryptedCredentialStore.saveProfile(this,slot,entry.password,entry.routeKey);
                    RootConnectionProfileCAStore.saveSlot(this,slot,entry.ca);
                    RootConnectionProfileStore.save(this,slot,entry.profile);
                }
            }
            refreshNamedProfileChoices();
            int slot=chosenProfileSlot();
            if(slot>restored.length||restored[slot-1]==null){
                for(int i=0;i<restored.length;i++)if(restored[i]!=null){slot=i+1;break;}
            }
            if(slot<=restored.length&&restored[slot-1]!=null){
                profileSlots.setSelection(slot-1);
                if(!loadNamedProfile(slot))throw new java.io.IOException("imported profile recall failed");
            }
            boolean missingLogin=false;
            for(RootConnectionProfileBundle.Entry e:restored)if(e!=null&&e.password.isEmpty())missingLogin=true;
            profileResult.setText(missingLogin?"服务器已导入；旧配置需补齐登录信息":"服务器导入完成");
            status.setText(profileResult.getText());
        }catch(Exception failed){
            refreshNamedProfileChoices();
            profileResult.setText("十槽导入未完整成功；若已有部分槽写入请检查后重试。"+
                "未触发Root连接或内核路由");
        }
    }
    private void updateOfficialCN(){
        if(cnUpdateRunning)return;
        new AlertDialog.Builder(this).setTitle("更新中国域名库")
            .setMessage("从 v2fly 官方发布下载规则，校验发布校验值并提取 geolocation-cn。成功后下次连接生效，当前会话不变。")
            .setNegativeButton("取消",null)
            .setPositiveButton("更新",(dialog,which)->{
                if(cnUpdateRunning)return;
                cnUpdateRunning=true;updateCNButton.setEnabled(false);
                status.setText("正在获取官方域名库…");
                File target=NativePayload.customCN(this);
                new Thread(()->{
                    String message;
                    try{
                        RootCnDomainUpdate.Result result=RootCnDomainUpdate.refresh(target);
                        message="已更新 "+result.tag+" · "+result.count+" 条，下次连接生效";
                    }catch(Exception failure){message="域名库更新失败，保留原规则："+failure.getMessage();}
                    final String outcome=message;
                    ui.post(()->{
                        cnUpdateRunning=false;updateCNButton.setEnabled(true);
                        status.setText(outcome);
                    });
                },"wbd-cn-manual-update").start();
            }).show();
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
    private final Runnable refreshStatus=new Runnable(){
        @Override public void run(){
            if(exitRequested){
                if(!RootClientService.sessionOwnerActive&&!RootClientService.startDispatchPending.get()){
                    finishAndRemoveTask();return;
                }
                if(status!=null)setTextIfChanged(status,"正在断开并退出 · "+RootClientService.status);
                ui.postDelayed(this,1000);return;
            }
            completeUserColdSwitchIfReady();
            completeAutomaticColdSwitchIfReady();
            if(status!=null&&!RootClientService.status.equals(lastServiceStatus)){
                lastServiceStatus=RootClientService.status;
                status.setText(RootClientService.sessionUiReady?"已连接":lastServiceStatus);
            }
            refreshHome();
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
        polish(appChoices);polish(bypassChoices);
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
        selectedAppsSummary.setText("已选 "+count+" 个应用 / "+uids.size()+" 个 UID");
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
            bypassSummary.setText("绕过 "+packages+" 个应用");
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
        dnsModes.check(s.cnSplitDNS?cnSplitDNS.getId():s.physicalDNS?physicalDNS.getId():tunnelDNS.getId());
        cnIPDirect.setChecked(s.cnIPDirect);
        outerRepair.setChecked(s.outerRepair);
        appTcpDNS.setChecked(true);
        tetherSharing.setChecked(s.tetherSharing);
        systemDNS.setChecked(true);
        systemDNS6.setChecked(false);
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
    // Only ten cold files, read at an explicit UI lifecycle/user action.
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
    private void rememberSlot(int slot){
        getPreferences(MODE_PRIVATE).edit().putInt(ACTIVE_SLOT,slot).apply();
    }
    private void saveNamedProfile(){
        coldSwitch.cancel();
        try{
            int slot=chosenProfileSlot();
            RootConnectionProfile profile=new RootConnectionProfile(
                profileLabel.getText().toString(),connectionSettingsFromUi());
            String secret=password.getText().toString(),key=routeKey.getText().toString();
            String pem=caPEM.getText().toString();
            // Validate the entire form before changing the stored server.
            new RootConnectionProfileBundle.Entry(profile,secret,key,pem);
            RootSavedCredentialRecord.validate(secret,key);
            RootEncryptedCredentialStore.saveProfile(this,slot,secret,key);
            RootConnectionProfileCAStore.saveSlot(this,slot,pem);
            RootConnectionProfileStore.save(this,slot,profile);
            RootConnectionSettingsStore.save(this,profile.settings);
            RootEncryptedCredentialStore.save(this,secret,key);
            RootConnectionProfileCAStore.saveCurrent(this,pem);
            rememberSlot(slot);
            refreshNamedProfileChoices();
            String message="已保存槽位"+slot+"："+profile.label;
            profileResult.setText(message);status.setText(message);
        }catch(Exception e){
            profileResult.setText("保存失败，请检查服务器、密码、密钥及设置");
            status.setText(profileResult.getText());
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
            rememberSlot(slot);
            profileResult.setText("已载入槽位"+slot+"："+profile.label+(saved==null?"；请填写密码和密钥":""));
            status.setText(profileResult.getText());
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
            profileResult.setText("已删除槽位"+slot);status.setText(profileResult.getText());
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
        if(exitRequested)return;
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
        getWindow().setStatusBarColor(SURFACE);
        getWindow().setNavigationBarColor(SURFACE);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR|View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        LinearLayout shell=vertical();shell.setBackgroundColor(BG);
        shell.setPadding(dp(16),dp(8),dp(16),dp(8));
        if(Build.VERSION.SDK_INT>=30){
            getWindow().setDecorFitsSystemWindows(false);
            shell.setOnApplyWindowInsetsListener((view,insets)->{
                android.graphics.Insets bars=insets.getInsets(android.view.WindowInsets.Type.systemBars());
                android.graphics.Insets ime=insets.getInsets(android.view.WindowInsets.Type.ime());
                shell.setPadding(dp(16)+bars.left,dp(8)+bars.top,dp(16)+bars.right,dp(8)+Math.max(bars.bottom,ime.bottom));
                return insets;
            });
        }
        TextView brand=text("WBD",28,INK,true);
        brand.setPadding(dp(4),dp(6),0,dp(8));shell.addView(brand);
        LinearLayout navigation=new LinearLayout(this);
        String[] nav={"连接","服务器","应用","设置"};
        for(int i=0;i<nav.length;i++){
            final int page=i;tabs[i]=action(nav[i],false,()->showPage(page));
            LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(0,dp(48),1);
            lp.setMargins(dp(2),0,dp(2),dp(8));navigation.addView(tabs[i],lp);
        }
        shell.addView(navigation);
        pageScroll=new ScrollView(this);pageScroll.setFillViewport(true);
        pageHost=vertical();pageScroll.addView(pageHost);
        shell.addView(pageScroll,new LinearLayout.LayoutParams(-1,0,1));
        for(int i=0;i<pages.length;i++){pages[i]=vertical();pageHost.addView(pages[i]);}
        LinearLayout pane=section(pages[0],"连接状态","");
        homeTitle=text("未连接",25,INK,true);pane.addView(homeTitle);
        homeSummary=text("",14,MUTED,false);pane.addView(homeSummary);
        homeConnect=action("连接",true,()->{coldSwitch.cancel();start();refreshHome();});
        pane.addView(homeConnect,new LinearLayout.LayoutParams(-1,dp(56)));
        homeStop=action("断开",false,()->requestStop());pane.addView(homeStop);
        pane.addView(action("关闭程序",false,()->requestExit()));
        pane.addView(action("选择 / 切换服务器",false,()->quickChooseServer()));
        serviceDetail=text("",12,MUTED,false);
        pane=section(pages[0],"网络与传输","");
        networks=new Spinner(this);
        pane.addView(networks);
        Button refresh=new Button(this);
        refresh.setText("刷新网络");
        refresh.setOnClickListener(v->chooseNetworks());
        pane.addView(refresh);
        pane.addView(text("选择当前可用网络。",13,MUTED,false));
        pane=section(pages[1],"服务器设置","");
        serverAddress=input(pane,"服务器地址（IPv4 / 域名）",InputType.TYPE_CLASS_TEXT);
        serverName=input(pane,"TLS 服务器名称（SNI）",InputType.TYPE_CLASS_TEXT);
        serverPort=input(pane,"端口",InputType.TYPE_CLASS_NUMBER);
        serverPort.setText("443");
        pane=section(pages[3],"传输参数","下次连接生效。");
        outerMTUField=input(pane,"外层 MTU（576–1500，默认1460）",
            InputType.TYPE_CLASS_NUMBER);
        outerMTUField.setText("1460");
        pane=section(pages[2],"直连例外","分流模式可以按 CN 地址与自定义网段直接连接。");
        directCIDRsField=input(pane,
            "自定义 IPv4 直连网段（最多16条）",
            InputType.TYPE_CLASS_TEXT);
        TextView directHint=new TextView(this);
        directHint.setText("这些网段直接连接。");
        pane.addView(directHint);
        autoConnectedDirect=new CheckBox(this);
        autoConnectedDirect.setText("当前局域网直连");
        autoConnectedDirect.setChecked(false);
        pane.addView(autoConnectedDirect);
        LinearLayout advancedTransport=section(pages[3],"高级传输","");
        pane=advancedTransport;
        recordCiphers=new Spinner(this);
        recordCiphers.setAdapter(new ArrayAdapter<>(this,
            android.R.layout.simple_spinner_dropdown_item,
            new String[]{"chacha20-poly1305","aes-128-gcm","aes-256-gcm"}));
        pane.addView(text("加密算法",14,MUTED,false));
        pane.addView(recordCiphers);
        pane=section(pages[0],"传输模式","Normal · FEC · Game");
        TextView modeHint=new TextView(this);
        modeHint.setText("选择连接模式；Fixed / Game Fixed 可选 FEC 档位。");
        pane.addView(modeHint);
        fecModes=new Spinner(this);
        fecModes.setAdapter(new ArrayAdapter<>(this,
            android.R.layout.simple_spinner_dropdown_item,
            new String[]{"normal","fec-fixed","fec-auto","game2","game4","game2-fixed","game4-fixed"}));
        pane.addView(fecModes);
        TextView profileHint=new TextView(this);
        profileHint.setText("FEC 修复包比例：0–6\n12.5% · 25% · 37.5% · 50% · 75% · 100% · 125%");
        profileHint.setVisibility(View.GONE);
        pane.addView(profileHint);
        fecProfiles=new Spinner(this);
        fecProfiles.setAdapter(new ArrayAdapter<>(this,
            android.R.layout.simple_spinner_dropdown_item,
            new String[]{"0","1","2","3","4","5","6"}));
        fecProfiles.setSelection(1);
        fecProfiles.setVisibility(View.GONE);
        pane.addView(fecProfiles);
        pane=section(pages[3],"连接维持","低频 Health 与定时冷轮换。");
        TextView healthHint=new TextView(this);
        healthHint.setText("心跳间隔（秒）");
        pane.addView(healthHint);
        nativeHealthIntervals=new Spinner(this);
        nativeHealthIntervals.setAdapter(new ArrayAdapter<>(this,
            android.R.layout.simple_spinner_dropdown_item,new String[]{"15","30"}));
        pane.addView(nativeHealthIntervals);
        TextView rotationHint=new TextView(this);
        rotationHint.setText("定时重连（分钟，0 为关闭）");
        pane.addView(rotationHint);
        coldRotationMinutes=new Spinner(this);
        coldRotationMinutes.setAdapter(new ArrayAdapter<>(this,
            android.R.layout.simple_spinner_dropdown_item,new String[]{"0","5","15","30"}));
        pane.addView(coldRotationMinutes);
        LinearLayout keepaliveCard=pane;
        pane=advancedTransport;
        TextView cipherHint=new TextView(this);
        cipherHint.setText("默认 ChaCha20，可按设备性能选择 AES。");
        pane.addView(cipherHint);
        TextView queueLabel=new TextView(this);
        queueLabel.setText("TUN 队列（包）");
        pane.addView(queueLabel);
        tunQueueSizes=new Spinner(this);
        tunQueueSizes.setAdapter(new ArrayAdapter<>(this,
            android.R.layout.simple_spinner_dropdown_item,
            new String[]{"500","2048"}));
        pane.addView(tunQueueSizes);
        TextView padLabel=new TextView(this);
        padLabel.setText("启动填充");
        pane.addView(padLabel);
        startupPaddingModes=new Spinner(this);
        startupPaddingModes.setAdapter(new ArrayAdapter<>(this,
            android.R.layout.simple_spinner_dropdown_item,
            new String[]{"off","tls","flows"}));
        pane.addView(startupPaddingModes);
        TextView game4ScheduleLabel=new TextView(this);
        game4ScheduleLabel.setText("Game4 副本策略");
        pane.addView(game4ScheduleLabel);
        game4CopySchedules=new Spinner(this);
        game4CopySchedules.setAdapter(new ArrayAdapter<>(this,
            android.R.layout.simple_spinner_dropdown_item,new String[]{"stagger-4-50-140","stagger-4-20-60","immediate"}));
        pane.addView(game4CopySchedules);
        pane=section(pages[1],"账户与密钥","");
        user=input(pane,"用户名",InputType.TYPE_CLASS_TEXT);
        password=input(pane,"密码",
            InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);
        routeKey=input(pane,"Route Key（8–32 位字母数字 / 64 位 Hex）",
            InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);
        pane=section(pages[1],"TLS 证书","");
        tlsVerifyServer=new CheckBox(this);
        tlsVerifyServer.setText("验证服务器证书");
        tlsVerifyServer.setChecked(false);
        pane.addView(tlsVerifyServer);
        caPEM=input(pane,"自定义 CA（PEM）",
            InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        caPEM.setMinLines(3);
        Button importCa=new Button(this);
        importCa.setText("导入 CA 证书");
        importCa.setOnClickListener(v->importTLSCA());
        pane.addView(importCa);
        Button clearCa=new Button(this);
        clearCa.setText("清空证书");
        clearCa.setOnClickListener(v->{
            caPEM.setText("");
            status.setText("证书已清空");
        });
        pane.addView(clearCa);
        pane=section(pages[2],"应用范围","默认全局普通应用。关闭全局后勾选要接管的应用。");
        TextView targetHelp=new TextView(this);
        targetHelp.setText("系统、WBD 与 Root 管理器保持直连。");
        pane.addView(targetHelp);
        allAppsDefault=new CheckBox(this);
        allAppsDefault.setText("全局接管普通应用（默认）");
        allAppsDefault.setChecked(true);
        pane.addView(allAppsDefault);
        LinearLayout policyPanel=section(pages[2],"路由策略","对接管范围统一应用；未选中的应用保持原系统网络。");
        routeSummary=text("",14,INK,true);policyPanel.addView(routeSummary);
        routeFullButton=action("全量隧道",false,()->chooseFullRoute());
        routeSplitButton=action("CN 分流（国内直连）",false,()->chooseSplitRoute());
        LinearLayout policyRow=new LinearLayout(this);
        LinearLayout.LayoutParams fullLp=new LinearLayout.LayoutParams(0,dp(48),1);
        fullLp.rightMargin=dp(4);policyRow.addView(routeFullButton,fullLp);
        LinearLayout.LayoutParams splitLp=new LinearLayout.LayoutParams(0,dp(48),1);
        splitLp.leftMargin=dp(4);policyRow.addView(routeSplitButton,splitLp);
        policyPanel.addView(policyRow);
        pane=section(pages[2],"DNS 解析","应用与共享使用同一 DNS 策略。");
        dnsModes=new RadioGroup(this);
        tunnelDNS=new RadioButton(this);tunnelDNS.setId(View.generateViewId());tunnelDNS.setText("全部隧道 DNS（推荐全量隧道）");
        physicalDNS=new RadioButton(this);physicalDNS.setId(View.generateViewId());physicalDNS.setText("全部直连 DNS");
        cnSplitDNS=new RadioButton(this);cnSplitDNS.setId(View.generateViewId());cnSplitDNS.setText("CN 分流 DNS（国内域名直连，其他走隧道）");
        dnsModes.addView(tunnelDNS);dnsModes.addView(cnSplitDNS);dnsModes.addView(physicalDNS);
        tunnelDNS.setChecked(true);pane.addView(dnsModes);
        physicalDNSUpstreamField=input(pane,"直连 DNS IPv4（默认223.5.5.5）",InputType.TYPE_CLASS_TEXT);
        physicalDNSUpstreamField.setText(RootPhysicalDNSUpstream.DEFAULT);
        physicalDNSFollowNetwork=new CheckBox(this);physicalDNSFollowNetwork.setText("直连 DNS 跟随当前所选网络");
        physicalDNSFollowNetwork.setChecked(false);
        physicalDNSFollowNetwork.setOnCheckedChangeListener((button,checked)->physicalDNSUpstreamField.setEnabled(!checked));
        pane.addView(physicalDNSFollowNetwork);
        tunnelDNSUpstreamField=input(pane,"隧道 DNS IPv4（默认1.1.1.1）",InputType.TYPE_CLASS_TEXT);
        tunnelDNSUpstreamField.setText(RootPhysicalDNSUpstream.TUNNEL_DEFAULT);
        TextView upstreamHint=new TextView(this);
        upstreamHint.setText("A 记录正常解析，AAAA 返回空。");
        pane.addView(upstreamHint);
        updateCNButton=new Button(this);
        updateCNButton.setText("手动更新官方中国域名库");
        updateCNButton.setOnClickListener(v->updateOfficialCN());
        pane.addView(updateCNButton);
        Button importCN=new Button(this);
        importCN.setText("导入CN域名规则（main兼容文本，下次连接生效）");
        importCN.setOnClickListener(v->{if(!cnUpdateRunning)importCNDomainRules();});
        pane.addView(importCN);
        Button resetCN=new Button(this);
        resetCN.setText("恢复APK内置官方CN域名规则");
        resetCN.setOnClickListener(v->{
            if(cnUpdateRunning){status.setText("请先完成当前域名更新");return;}
            File custom=NativePayload.customCN(this);
            if(!custom.exists()||custom.delete())status.setText("已恢复内置CN域名规则，下次连接生效");
            else status.setText("未能移除自定义CN域名规则");
        });
        pane.addView(resetCN);
        cnIPDirect=new CheckBox(this);
        cnIPDirect.setText("中国 IPv4 直连");
        cnIPDirect.setChecked(false);
        pane.addView(cnIPDirect);
        LinearLayout routingPane=pane;
        pane=advancedTransport;
        outerRepair=new CheckBox(this);
        outerRepair.setText("外层机会式重传");
        outerRepair.setChecked(false);
        pane.addView(outerRepair);
        pane=routingPane;
        // Preserve profile codec; managed DNS ingress is now automatic.
        appTcpDNS=new CheckBox(this);appTcpDNS.setChecked(true);
        systemDNS=new CheckBox(this);systemDNS.setChecked(true);
        systemDNS6=new CheckBox(this);systemDNS6.setChecked(false);
        LinearLayout legacyIPv6=section(pages[3],"IPv6 高级兼容","仅用于已有 IPv6 承载服务端。");
        pane=legacyIPv6;
        ipv6GatewayField=input(pane,"高级兼容：IPv6 承载服务端 TUN IPv4（留空＝默认 IPv4-only；仅已有 --inner-ipv6 服务端需要）",InputType.TYPE_CLASS_TEXT);
        ipv6GatewayField.setText("");
        ipv6DirectCIDRsField=input(pane,"高级兼容：IPv6直连CIDR（仅显式IPv6承载生效）",InputType.TYPE_CLASS_TEXT);
        ipv6DirectCIDRsField.setText("");
        pane=section(pages[3],"网络共享","热点 / USB 共享使用 IPv4。");
        tetherSharing=new CheckBox(this);
        tetherSharing.setText("共享 WBD（Android 16）");
        tetherSharing.setChecked(false);
        pane.addView(tetherSharing);
        TextView tetherRequirement=new TextView(this);
        tetherRequirement.setText("先开启系统热点或 USB 共享，再选择接口。");
        pane.addView(tetherRequirement);
        tetherChoices=new Spinner(this);
        pane.addView(tetherChoices);
        pane.addView(action("刷新共享网卡",false,()->{
            if(tetherWatch!=null){tetherWatch.close();tetherWatch=null;}
            watchTetherChoices();
        }));
        dnsModes.setOnCheckedChangeListener((group,checkedId)->refreshHome());
        // B42: select B41 original Go/Rust Game2 owner, not a new protocol.
        fecModes.setOnItemSelectedListener(new android.widget.AdapterView.OnItemSelectedListener(){
            @Override public void onItemSelected(android.widget.AdapterView<?> parent,
                View view,int position,long id){
                String mode=fecModes.getSelectedItem().toString();
                boolean fixed=mode.endsWith("-fixed");
                profileHint.setVisibility(fixed?View.VISIBLE:View.GONE);
                fecProfiles.setVisibility(fixed?View.VISIBLE:View.GONE);
                boolean game4="game4".equals(mode)||"game4-fixed".equals(mode);
                game4CopySchedules.setVisibility(game4?View.VISIBLE:View.GONE);
                game4ScheduleLabel.setVisibility(game4?View.VISIBLE:View.GONE);
            }
            @Override public void onNothingSelected(android.widget.AdapterView<?> parent){}
        });
        pane=section(pages[2],"应用名单","选择接管或绕过的实际已安装应用。");
        selectedAppControls=new LinearLayout(this);
        selectedAppControls.setOrientation(LinearLayout.VERTICAL);
        pane.addView(selectedAppControls);
        TextView searchHint=new TextView(this);
        searchHint.setText("按名称、包名或 UID 搜索。");
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
        bypassHint.setText("选择不经过 WBD 的应用。");
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
        refreshApps.setText("刷新应用名单");
        refreshApps.setOnClickListener(v->chooseInstalledApplications());
        pane.addView(refreshApps);
        // B50: ten named daily connection profiles, all using the
        // existing B22 settings serializer and selected app UID recheck.
        pane=section(pages[1],"已保存服务器","选择、编辑或连接服务器。");
        profileSlots=new Spinner(this);
        String[] initialSlots=new String[RootConnectionProfile.SLOTS];
        for(int i=0;i<initialSlots.length;i++)initialSlots[i]="配置槽"+(i+1);
        profileSlots.setAdapter(new ArrayAdapter<>(this,
            android.R.layout.simple_spinner_dropdown_item,initialSlots));
        pane.addView(profileSlots);
        profileLabel=input(pane,"服务器名称",InputType.TYPE_CLASS_TEXT);
        profileLabel.setText("常用连接");
        Button loadProfile=new Button(this);
        loadProfile.setText("载入并编辑");
        loadProfile.setOnClickListener(v->loadNamedProfile());
        pane.addView(loadProfile);
        Button connectProfile=new Button(this);
        connectProfile.setText("连接此服务器");
        connectProfile.setOnClickListener(v->connectSelectedSavedProfile());
        pane.addView(connectProfile);
        Button deleteProfile=new Button(this);
        deleteProfile.setText("删除服务器配置");
        deleteProfile.setOnClickListener(v->deleteNamedProfile());
        pane.addView(deleteProfile);
        Button exportAllProfiles=new Button(this);
        exportAllProfiles.setText("导出全部服务器");
        exportAllProfiles.setOnClickListener(v->exportAllProfiles());
        pane.addView(exportAllProfiles);
        Button importAllProfiles=new Button(this);
        importAllProfiles.setText("导入服务器备份");
        importAllProfiles.setOnClickListener(v->importAllProfiles());
        pane.addView(importAllProfiles);
        profileResult=new TextView(this);
        profileResult.setText("");
        pane.addView(profileResult);
        pane=keepaliveCard;
        // Explicit two-stage cold physical Network reselection; NO
        // automatic root relaunch after Android onLost/capability changes.
        // The new START reuses the complete existing credential/UID/TLS
        // validation and creates an entirely fresh Go/Rust generation.
        Button oneShotSwitch=new Button(this);
        oneShotSwitch.setText("切换到所选网络");
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
        // Network selection and the explicit switch belong together on Home.
        ((LinearLayout)networks.getParent()).addView(oneShotSwitch);
        autoNetworkRecovery=new CheckBox(this);
        autoNetworkRecovery.setText("前台自动重连");
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
        backgroundNetworkRecovery.setText("后台自动重连");
        backgroundNetworkRecovery.setChecked(false);
        backgroundNetworkRecovery.setOnCheckedChangeListener((button,checked)->{
            if(checked){autoNetworkRecovery.setChecked(false);autoHandover.cancel();}
        });
        pane.addView(backgroundNetworkRecovery);
        Button restore=new Button(this);
        restore.setText("恢复网络");
        restore.setOnClickListener(v->{
            autoHandover.cancel();
            new AlertDialog.Builder(this)
            .setTitle("恢复 WBD 临时Root网络")
            .setMessage("断开连接并恢复 WBD 修改的网络设置。")
            .setNegativeButton("取消",null)
            .setPositiveButton("停止并恢复",(dialog,which)->{
                Intent i=new Intent(this,RootClientService.class);
                i.setAction(RootClientService.RESTORE);
                startForegroundService(i);
                status.setText("已请求恢复；等待原Go精确内核读回");
            }).show();
        });
        pane.addView(restore);
        LinearLayout more=section(pages[3],"更多设置","");
        LinearLayout advancedControls=vertical();advancedControls.setVisibility(View.GONE);
        more.addView(action("高级传输",false,()->advancedControls.setVisibility(advancedControls.getVisibility()==View.VISIBLE?View.GONE:View.VISIBLE)));
        more.addView(advancedControls);
        ((ViewGroup)advancedTransport.getParent()).removeView(advancedTransport);
        advancedControls.addView(advancedTransport);
        LinearLayout diagnostics=more;
        diagnosticsPanel=vertical();diagnosticsPanel.setVisibility(View.GONE);
        diagnostics.addView(action("诊断与恢复",false,()->{
            diagnosticsPanel.setVisibility(diagnosticsPanel.getVisibility()==View.VISIBLE?View.GONE:View.VISIBLE);
        }));
        diagnostics.addView(diagnosticsPanel);
        ((ViewGroup)legacyIPv6.getParent()).removeView(legacyIPv6);
        advancedControls.addView(legacyIPv6);
        ((ViewGroup)restore.getParent()).removeView(restore);
        diagnosticsPanel.addView(serviceDetail);
        diagnosticsPanel.addView(restore);
        pane=diagnosticsPanel;
        Button inspectDNS=new Button(this);
        inspectDNS.setText("DNS 状态");
        inspectDNS.setOnClickListener(v->{
            String report=RootDiagnosticReport.build(
                getFilesDir(),signedSource(),Build.VERSION.SDK_INT);
            dnsStatusBrief.setText(RootDNSStatusBrief.fromReport(report));
        });
        pane.addView(inspectDNS);
        dnsStatusBrief=new TextView(this);
        dnsStatusBrief.setText("");
        dnsStatusBrief.setTextIsSelectable(true);
        pane.addView(dnsStatusBrief);
        // B21: on-demand view of ALREADY collected original Rust M4
        // RAW/TUN receipts; never call Root, netd or native DATA here.
        Button inspectM4=new Button(this);
        inspectM4.setText("流量状态");
        inspectM4.setOnClickListener(v->{
            String report=RootDiagnosticReport.build(
                getFilesDir(),signedSource(),Build.VERSION.SDK_INT);
            m4TrafficBrief.setText(RootM4TrafficBrief.fromReport(report));
        });
        pane.addView(inspectM4);
        m4TrafficBrief=new TextView(this);
        m4TrafficBrief.setText("");
        m4TrafficBrief.setTextIsSelectable(true);
        pane.addView(m4TrafficBrief);
        fecStatusText=new TextView(this);
        fecStatusText.setText(RootClientService.fecStatus);
        fecStatusText.setTextIsSelectable(true);
        // Actual authenticated original Rust revision, not an E2E claim.
        pane.addView(fecStatusText);
        Button exportDiagnostic=new Button(this);
        exportDiagnostic.setText("导出诊断");
        exportDiagnostic.setOnClickListener(v->exportSafeDiagnostic());
        pane.addView(exportDiagnostic);
        diagnosticExportResult=new TextView(this);
        diagnosticExportResult.setText("");
        diagnosticExportResult.setTextIsSelectable(true);
        pane.addView(diagnosticExportResult);
        status=new TextView(this);
        status.setText("未连接");
        status.setTextColor(MUTED);status.setTextSize(12);
        status.setMaxLines(2);status.setTextIsSelectable(true);
        status.setPadding(dp(8),dp(5),dp(8),0);shell.addView(status);
        polish(pageHost);
        // Move the server picker to the top of the server page without
        // duplicating a spinner or changing its original profile slot owner.
        View savedServers=profileSlots;
        ViewGroup savedParent=(ViewGroup)savedServers.getParent();
        if(savedParent instanceof LinearLayout){
            ViewGroup outer=(ViewGroup)savedParent.getParent();
            outer.removeView(savedParent);pages[1].addView(savedParent,0);
        }
        // Scope and routing policy are the first two App cards.
        ViewGroup policyParent=(ViewGroup)policyPanel.getParent();
        policyParent.removeView(policyPanel);pages[2].addView(policyPanel,0);
        ViewGroup scopeCard=(ViewGroup)allAppsDefault.getParent();
        ((ViewGroup)scopeCard.getParent()).removeView(scopeCard);
        pages[2].addView(scopeCard,0);
        View appListCard=(View)selectedAppControls.getParent();
        ((ViewGroup)appListCard.getParent()).removeView(appListCard);
        pages[2].addView(appListCard,2);
        saveAllButton=action("保存全部设置",true,()->saveNamedProfile());
        shell.addView(saveAllButton,new LinearLayout.LayoutParams(-1,dp(48)));
        profileSlots.setOnItemSelectedListener(new android.widget.AdapterView.OnItemSelectedListener(){
            @Override public void onItemSelected(android.widget.AdapterView<?> parent,View view,int pos,long id){
                saveAllButton.setText("保存全部设置 · 槽"+(pos+1));
            }
            @Override public void onNothingSelected(android.widget.AdapterView<?> parent){}
        });
        setContentView(shell);
        shell.requestApplyInsets();
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
        int savedSlot=getPreferences(MODE_PRIVATE).getInt(ACTIVE_SLOT,1);
        profileSlots.setSelection(Math.max(0,Math.min(RootConnectionProfile.SLOTS-1,savedSlot-1)));
        try{
            RootConnectionProfile stored=RootConnectionProfileStore.load(this,savedSlot);
            if(stored!=null)profileLabel.setText(stored.label);
        }catch(Exception ignored){}
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
        showPage(state==null?0:Math.max(0,Math.min(3,state.getInt("wbd_page",0))));
    }
    @Override protected void onSaveInstanceState(Bundle out){
        super.onSaveInstanceState(out);out.putInt("wbd_page",currentPage);
    }
    @Override public void onBackPressed(){
        if(currentPage!=0){showPage(0);return;}
        super.onBackPressed();
    }
    @Override protected void onResume(){
        super.onResume();
        watchTetherChoices();
        // UI-only snapshot refresh; Service's already-owned Network,
        // route and generation are NEVER implicitly switched.
        if(!exitRequested&&autoNetworkRecovery!=null&&autoNetworkRecovery.isChecked()&&
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
