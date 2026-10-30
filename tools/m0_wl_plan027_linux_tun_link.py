"""Real Linux original TUN interface RX/TX deltas, not Linux FQ qdisc."""
def link_delta(before,after,device="wbdwl4"):
    def read(rows):
        if not isinstance(rows,list):return None
        found=[r for r in rows if isinstance(r,dict) and r.get("ifname")==device]
        if len(found)!=1:return None
        stats=found[0].get("stats64") or found[0].get("stats")
        if not isinstance(stats,dict):return None
        out={}
        for side in ("rx","tx"):
            row=stats.get(side)
            if not isinstance(row,dict):return None
            for field in ("packets","dropped","errors"):
                val=row.get(field)
                if type(val) is not int or val<0:return None
                out[side+"_"+field]=val
        return out
    a=read(before);b=read(after)
    if a is None or b is None:
        return {"status":"NOT_MEASURED_LINUX_TUN_INTERFACE_COUNTERS"}
    if any(b[k]<a[k] for k in a):
        return {"status":"INCONCLUSIVE_LINK_COUNTER_RESET"}
    return {"status":"MEASURED_ORIGINAL_LINUX_TUN_IP_LINK",
            "scope":"WSL_WBDWL4_IFACE_RX_TX_NOT_TC_FQ_NOT_ETH0",
            **{k+"_delta":b[k]-a[k] for k in a}}
