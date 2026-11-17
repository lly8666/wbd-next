package org.wbdnext.rootclient;

import android.app.Activity;
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
    private EditText serverIP,serverName,user,password,routeKey,caPEM,serverPort;
    private Spinner networks;
    private LinearLayout appChoices;
    private TextView status;
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
    private static boolean ipv4(String s){
        String[] parts=s.split("\\.",-1);
        if(parts.length!=4)return false;
        for(String p:parts){
            if(p.length()==0||p.length()>3)return false;
            for(int i=0;i<p.length();i++){
                if(p.charAt(i)<'0'||p.charAt(i)>'9')return false;
            }
            try{if(Integer.parseInt(p)>255)return false;}
            catch(NumberFormatException e){return false;}
        }
        return true;
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
            String peer=serverIP.getText().toString().trim();
            String sni=serverName.getText().toString().trim();
            String account=user.getText().toString().trim();
            String secret=password.getText().toString();
            String key=routeKey.getText().toString().trim();
            String pem=caPEM.getText().toString().trim();
            ArrayList<InstalledAppTarget> chosenApps=new ArrayList<>();
            for(InstalledAppTarget app:installedApps){
                CheckBox cb=checkedApps.get(app.packageName);
                if(cb!=null&&cb.isChecked())chosenApps.add(app);
            }
            SelectedAppGroup chosen=SelectedAppGroup.from(
                chosenApps,android.os.Process.myUid(),getPackageName());
            if(!InstalledAppCatalog.stillSameGroup(this,chosen.packages,chosen.uids))
                throw new IllegalArgumentException("Selected package/UID changed; refresh");
            int port=Integer.parseInt(serverPort.getText().toString().trim());
            if(!ipv4(peer)||sni.length()==0||sni.length()>253||
               account.length()==0||account.length()>128||
               secret.length()==0||secret.length()>512||
               !key.matches("[0-9a-fA-F]{64}")||
               port<1||port>65535){
                throw new IllegalArgumentException("Invalid server / TLS / credential / UID settings");
            }
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
            request.putExtra("target_uids",chosen.uids);
            request.putExtra("target_packages",chosen.packages);
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
        networks=new Spinner(this);
        pane.addView(networks);
        Button refresh=new Button(this);
        refresh.setText("Refresh physical Networks");
        refresh.setOnClickListener(v->chooseNetworks());
        pane.addView(refresh);
        serverIP=input(pane,"Server underlay IPv4 (literal)",InputType.TYPE_CLASS_TEXT);
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
        targetHelp.setText("Select up to 16 visible installed packages with at most 8 "
            +"distinct kernel UIDs for this ONE authenticated WBD session. "
            +"Packages sharing one UID are inseparable: selecting one UID routes ALL "
            +"packages using that UID. System/root and this controller are excluded. "
            +"Normal/off only; DNS and split/direct modes are NOT YET implemented.");
        pane.addView(targetHelp);
        appChoices=new LinearLayout(this);
        appChoices.setOrientation(LinearLayout.VERTICAL);
        pane.addView(appChoices);
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
