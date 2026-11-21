package rootjournal

import (
    "fmt"
    "os"
    "reflect"
    "strings"
    "testing"
)

// The kernel may change a rule after WBD writes its durable owner journal.
// A matching pref/table/UID alone MUST NOT authorize deletion of a foreign
// narrowed rule. The exact parser is shared by 1-UID and group Stop.
func TestOwnedUIDReadbackRejectsExtraSelectors(t *testing.T) {
    const uid=11234
    allowed:=[]string{
        "9600: from all uidrange 11234-11234 lookup 19842",
        "9600: from all to all uidrange 11234-11234 table 19842",
    }
    for _,line:=range allowed {
        if !strictOwnedUIDRule(strings.Fields(line),Priority,uid) {
            t.Fatalf("rejected canonical owned rule: %q",line)
        }
    }
    rejected:=[]string{
        "9600: from all fwmark 0x1 uidrange 11234-11234 lookup 19842",
        "9600: from all uidrange 11234-11234 lookup 19842 iif wlan0",
        "9600: not from all uidrange 11234-11234 lookup 19842",
        "9600: from all to 192.0.2.1 uidrange 11234-11234 lookup 19842",
        "9600: from all uidrange 11234-11234 lookup 19842 suppress_prefixlength 0",
        "9600: from all uidrange 11234-11234 lookup 19842 lookup 19842",
        "9601: from all uidrange 11234-11234 lookup 19842",
        "9600: from all uidrange 11234-11234 lookup main",
        "9600: from all uidrange 11235-11235 lookup 19842",
    }
    for _,line:=range rejected {
        if strictOwnedUIDRule(strings.Fields(line),Priority,uid) {
            t.Fatalf("accepted non-owned rule: %q",line)
        }
        if _,err:=ruleState(line,uid);err==nil {
            t.Fatalf("single UID reader accepted non-owned rule: %q",line)
        }
    }
}

func TestOwnedRouteReadbackRejectsForeignAttributes(t *testing.T) {
    for _,line:=range []string{
        "default dev wbdv40",
        "default dev wbdv40 scope link",
        "default dev wbdv40 proto boot scope link",
    } {
        present,err:=routeState(line,"wbdv40")
        if err!=nil||!present {t.Fatalf("rejected owned route %q: %v",line,err)}
    }
    for _,line:=range []string{
        "default dev wbdv40 metric 10",
        "default dev wbdv40 via 192.0.2.1",
        "default dev wbdv40 src 198.18.0.1",
        "default dev wbdv40 proto static scope link",
        "default dev wbdv40 scope link scope link",
        "default dev wbdv40 mtu 1200",
        "default dev wbdv40 scope",
        "default dev other0",
    } {
        if _,err:=routeState(line,"wbdv40");err==nil {
            t.Fatalf("accepted foreign/modified route: %q",line)
        }
    }
}

func TestSingleStopKeepsJournalOnForeignRuleSelector(t *testing.T) {
    f,path,p:=fixture(t)
    s,err:=New(f.run,path,p)
    if err!=nil {t.Fatal(err)}
    original:=s.run
    s.run=func(args ...string)(string,error){
        if reflect.DeepEqual(args,ruleShow()){
            return fmt.Sprintf("%d: from all fwmark 0x1 uidrange %d-%d lookup %d\n",
                Priority,p.UID,p.UID,Table),nil
        }
        return f.run(args...)
    }
    if err:=s.Stop();err==nil {t.Fatal("Stop deleted foreign narrowed UID rule")}
    if !f.route||!f.rule {t.Fatal("Stop mutated kernel after foreign readback")}
    if _,err:=os.Stat(path);err!=nil {t.Fatal("Stop erased durable crash journal",err)}
    s.run=original
    if err:=s.Stop();err!=nil {t.Fatal("exact owner cannot recover",err)}
}

func TestGroupStopKeepsJournalOnForeignRuleSelector(t *testing.T) {
    f,path,p:=groupFixture(t)
    s,err:=NewGroup(f.run,path,p)
    if err!=nil {t.Fatal(err)}
    original:=s.run
    s.run=func(args ...string)(string,error){
        if reflect.DeepEqual(args,ruleShow()){
            return fmt.Sprintf("%d: from all uidrange %d-%d lookup %d iif wlan0\n",
                Priority,p.UIDs[0],p.UIDs[0],Table),nil
        }
        return f.run(args...)
    }
    if err:=s.Stop();err==nil {t.Fatal("group Stop deleted foreign narrowed UID rule")}
    if !f.route||len(f.rules)!=len(p.UIDs){t.Fatal("group Stop changed owned state")}
    if _,err:=os.Stat(path);err!=nil {t.Fatal("group Stop erased durable journal",err)}
    s.run=original
    if err:=s.Stop();err!=nil {t.Fatal("exact group owner cannot recover",err)}
}
