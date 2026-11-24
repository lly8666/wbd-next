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
        // B58: actual Root App selector now supports 16 canonical UIDs
        // and 32 installed packages, not the obsolete B24 8/16 limit.
        List<InstalledAppTarget> many=new ArrayList<>();
        for(int i=0;i<16;i++)many.add(app("org.example.app"+i,"test",10300+i));
        check(RootAppPickerModel.addMatching(many,Collections.emptySet(),"",
            10200,"org.wbdnext.rootclient").size()==16,
            "sixteen original App UIDs must be selectable");
        List<InstalledAppTarget> seventeen=new ArrayList<>(many);
        seventeen.add(app("org.example.app16","test",10316));
        boolean rejected=false;
        try{RootAppPickerModel.addMatching(seventeen,Collections.emptySet(),"",
            10200,"org.wbdnext.rootclient");}
        catch(IllegalArgumentException expected){rejected=true;}
        check(rejected,"seventeen distinct UIDs must exceed the new limit");
        List<InstalledAppTarget> shared=new ArrayList<>();
        for(int i=0;i<32;i++)shared.add(app("org.example.shared"+i,"Shared",10145));
        check(RootAppPickerModel.addMatching(shared,Collections.emptySet(),"Shared",
            10200,"org.wbdnext.rootclient").size()==32,
            "thirty-two installed packages sharing one UID selectable");
        shared.add(app("org.example.shared32","Shared",10145));
        rejected=false;
        try{RootAppPickerModel.addMatching(shared,Collections.emptySet(),"Shared",
            10200,"org.wbdnext.rootclient");}
        catch(IllegalArgumentException expected){rejected=true;}
        check(rejected,"thirty-three packages exceed the B58 selection");
        rejected=false;
        try{RootAppPickerModel.addMatching(items,Collections.emptySet(),"absent",
            10200,"org.wbdnext.rootclient");}
        catch(IllegalArgumentException expected){rejected=true;}
        check(rejected,"empty match cannot silently change selection");
        System.out.println("ANDROID_B24_APP_PICKER_FILTER_BATCH_EXACT_UID_HOST_PASS");
        System.out.println("ANDROID_B58_APP_PICKER_16_UID_32_PACKAGE_HOST_PASS");
    }
}
