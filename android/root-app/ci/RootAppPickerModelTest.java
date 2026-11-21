package org.wbdnext.rootclient;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;

public final class RootAppPickerModelTest {
    private static void check(boolean ok,String msg){
        if(!ok)throw new AssertionError(msg);
    }
    private static InstalledAppTarget app(String name,String label,int uid){
        return new InstalledAppTarget(name,label,uid);
    }
    public static void main(String[] args){
        List<InstalledAppTarget> items=Arrays.asList(
            app("org.example.browser","Fast Browser",10120),
            app("org.example.voice","Voice Notes",10130),
            app("org.example.search","Search App",10120),
            app("org.example.ping","Ping",10140));
        check(RootAppPickerModel.matches(items.get(0),"BROWSER"),"label match");
        check(RootAppPickerModel.matches(items.get(1),"example.voice"),"package match");
        check(RootAppPickerModel.matches(items.get(2),"10120"),"uid match");
        check(!RootAppPickerModel.matches(items.get(3),"browser"),"different app hidden");
        check(RootAppPickerModel.matches(items.get(3)," "),"blank means all");
        Set<String> old=new TreeSet<>(Collections.singleton("org.example.ping"));
        Set<String> next=RootAppPickerModel.addMatching(items,old,"10120",
            10200,"org.wbdnext.rootclient");
        check(next.contains("org.example.ping")&&next.contains("org.example.browser")&&
            next.contains("org.example.search")&&next.size()==3,
            "visible matching UID + previously checked hidden app retained");
        List<InstalledAppTarget> many=new ArrayList<>();
        for(int i=0;i<9;i++)many.add(app("org.example.app"+i,"test",10300+i));
        boolean rejected=false;
        try{RootAppPickerModel.addMatching(many,Collections.emptySet(),"",
            10200,"org.wbdnext.rootclient");}
        catch(IllegalArgumentException expected){rejected=true;}
        check(rejected,"must not exceed original eight distinct UIDs");
        // 16 packages with one shared UID must be selectable as one route.
        List<InstalledAppTarget> shared=new ArrayList<>();
        for(int i=0;i<16;i++)shared.add(app("org.example.shared"+i,"Shared",10145));
        check(RootAppPickerModel.addMatching(shared,Collections.emptySet(),"Shared",
            10200,"org.wbdnext.rootclient").size()==16,
            "all sixteen packages sharing one UID selectable");
        rejected=false;
        try{RootAppPickerModel.addMatching(items,Collections.emptySet(),"absent",
            10200,"org.wbdnext.rootclient");}
        catch(IllegalArgumentException expected){rejected=true;}
        check(rejected,"empty match cannot silently change selection");
        System.out.println("ANDROID_B24_APP_PICKER_FILTER_BATCH_EXACT_UID_HOST_PASS");
    }
}
