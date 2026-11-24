package org.wbdnext.rootclient;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.TreeSet;

/** Cold-only UI search/selection; never queries kernel or routes on keystrokes. */
final class RootAppPickerModel {
    private RootAppPickerModel(){}

    static boolean matches(InstalledAppTarget app,String filter){
        if(app==null)return false;
        String needle=filter==null?"":filter.trim().toLowerCase(Locale.ROOT);
        if(needle.isEmpty())return true;
        return app.packageName.toLowerCase(Locale.ROOT).contains(needle)||
            app.label.toLowerCase(Locale.ROOT).contains(needle)||
            Integer.toString(app.uid).contains(needle);
    }

    /** Canonical candidate set. The existing exact package/UID policy owns limits. */
    static Set<String> addMatching(List<InstalledAppTarget> installed,
        Set<String> currentlyChecked,String filter,int selfUID,String selfPackage){
        ArrayList<InstalledAppTarget> selected=new ArrayList<>();
        TreeSet<String> names=new TreeSet<>();
        for(InstalledAppTarget app:installed){
            if(currentlyChecked.contains(app.packageName)||matches(app,filter)){
                selected.add(app);
                names.add(app.packageName);
            }
        }
        // No UI mutation before native selected-app max 16 unique UIDs /
        // max 32 package contract accepts the whole filtered result.
        SelectedAppGroup.from(selected,selfUID,selfPackage);
        return names;
    }
}
