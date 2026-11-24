package rootjournal

import (
    "fmt"
    "net/netip"
    "sort"
    "strconv"
    "strings"
)

const MaxDirectIPv4CIDRs=16
// A signed country allocation snapshot is a separate cold input. Keep the
// user's manual limit at 16; the combined FIB can contain thousands of rows.
const MaxCountryIPv4CIDRs=8192
type DirectBatch func([][]string)error

func MergeCountryDirectCIDRs(manual []string,snapshot,peer string)([]string,error){
    if len(snapshot)>256<<10{return nil,fmt.Errorf("country prefix snapshot too large")}
    lines:=strings.Fields(snapshot)
    if len(lines)==0||len(lines)>MaxCountryIPv4CIDRs{return nil,fmt.Errorf("country prefix count")}
    seen:=map[string]bool{}
    for _,s:=range append(append([]string(nil),manual...),lines...){
        p,e:=ParseDirectCIDRs(s)
        if e!=nil||len(p)!=1{return nil,fmt.Errorf("invalid country/direct prefix: %q",s)}
        if p[0]!=peer+"/32"{seen[p[0]]=true}
    }
    out:=make([]string,0,len(seen))
    for s:=range seen{out=append(out,s)}
    sort.Strings(out)
    return out,nil
}
func changeDirectRoutes(run Runner,batch DirectBatch,action string,cidrs []string,flags []bool)error{
    rows:=make([][]string,0,len(cidrs))
    for i,cidr:=range cidrs{
        if flags!=nil&&!flags[i]{continue}
        rows=append(rows,directArgs(action,cidr))
    }
    if len(rows)==0{return nil}
    if batch!=nil{return batch(rows)}
    for _,row:=range rows{if _,e:=run(row...);e!=nil{return e}}
    return nil
}
func optionalDirectBatch(batch []DirectBatch)DirectBatch{
    if len(batch)>0{return batch[0]};return nil
}

// ParseDirectCIDRs is a cold-only explicit user route selection. The real
// Android kernel policy still belongs to the existing UID table owner.
// Empty preserves the original full-tunnel default.
func ParseDirectCIDRs(raw string)([]string,error){
    if raw==""{return nil,nil}
    fields:=strings.Split(raw,",")
    if len(fields)>MaxDirectIPv4CIDRs{return nil,fmt.Errorf("maximum sixteen direct IPv4 CIDRs")}
    result:=make([]string,0,len(fields))
    for _,field:=range fields{
        field=strings.TrimSpace(field)
        p,e:=netip.ParsePrefix(field)
        if e!=nil||!p.IsValid()||!p.Addr().Is4()||
            p.Bits()<1||p.Bits()>32||p.Masked()!=p||
            p.Addr().IsUnspecified()||p.Addr().IsMulticast()||
            p.Addr().IsLoopback(){
            return nil,fmt.Errorf("direct route requires a canonical nondefault IPv4 CIDR")
        }
        result=append(result,p.String())
    }
    sort.Strings(result)
    for i:=1;i<len(result);i++{
        if result[i]==result[i-1]{return nil,fmt.Errorf("duplicate direct route CIDR")}
    }
    return result,nil
}
func validDirectCIDRs(routes []string,peer string)bool{
    if len(routes)>MaxDirectIPv4CIDRs+MaxCountryIPv4CIDRs{return false}
    previous:=""
    for _,s:=range routes{
        canonical,e:=ParseDirectCIDRs(s)
        if e!=nil||len(canonical)!=1||canonical[0]!=s||
            previous!=""&&previous>=s||peer!=""&&s==peer+"/32"{return false}
        previous=s
    }
    return true
}

// Existing exact root-owned FIB parser stays the single authority for the
// default TUN route and original physical WBD peer exception. New explicit
// user CIDRs are only additional throw routes within that SAME private table.
func routeWithDirect(out,tun,peer string,direct []string)(bool,bool,[]bool,error){
    found:=make([]bool,len(direct))
    stripped:=make([]string,0,2)
    indexes:=make(map[string]int,len(direct))
    for i,cidr:=range direct{indexes[cidr]=i;if strings.HasSuffix(cidr,"/32"){indexes[strings.TrimSuffix(cidr,"/32")]=i}}
    for _,line:=range strings.Split(strings.TrimSpace(out),"\n"){
        fields:=strings.Fields(line)
        if len(fields)==0{continue}
        matched:=-1
        if len(fields)>=2&&fields[0]=="throw"{
            if i,ok:=indexes[fields[1]];ok{matched=i}
        }
        if matched<0{stripped=append(stripped,line);continue}
        if found[matched]{return false,false,nil,fmt.Errorf("duplicate direct route")}
        // These are the only optional attributes accepted by the shared
        // root table parser; never let foreign route flags be silently owned.
        scope,proto:=false,false
        for i:=2;i<len(fields);i+=2{
            if i+1>=len(fields){return false,false,nil,fmt.Errorf("invalid direct route attribute")}
            switch {
            case fields[i]=="scope"&&fields[i+1]=="link"&&!scope:scope=true
            case fields[i]=="proto"&&fields[i+1]=="boot"&&!proto:proto=true
            default:return false,false,nil,fmt.Errorf("foreign direct route attribute")
            }
        }
        found[matched]=true
    }
    route,peerFound,e:=allAppRouteState(strings.Join(stripped,"\n"),tun,peer)
    return route,peerFound,found,e
}
func allDirectPresent(flags []bool)bool{
    for _,yes:=range flags{if !yes{return false}}
    return true
}
func anyDirectPresent(flags []bool)bool{
    for _,yes:=range flags{if yes{return true}}
    return false
}
func directArgs(action,cidr string)[]string{
    return []string{"-4","route",action,"throw",cidr,"table",strconv.Itoa(Table)}
}
