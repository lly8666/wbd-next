"""Original Linux TUN root fq kernel statistics, separate from netdev TX drops."""
def _root_fq(rows):
    if not isinstance(rows,list):return None
    found=[r for r in rows if isinstance(r,dict) and r.get("kind")=="fq" and
           (r.get("root") is True or r.get("parent") in ("root",None))]
    if len(found)!=1:return None
    stats=found[0].get("stats") or found[0]
    if not isinstance(stats,dict):return None
    counts={}
    for key in ("drops","packets","bytes","overlimits"):
        val=stats.get(key)
        if type(val) is not int or val<0:return None
        counts[key]=val
    return counts

def fq_delta(before,after):
    a=_root_fq(before);b=_root_fq(after)
    if a is None or b is None:
        return {"status":"NOT_MEASURED_LINUX_TUN_FQ_ROOT_COUNTERS"}
    if any(b[k]<a[k] for k in a):
        return {"status":"INCONCLUSIVE_KERNEL_QDISC_COUNTER_RESET_OR_RECREATED"}
    return {"status":"MEASURED_ORIGINAL_LINUX_TUN_FQ_KERNEL",
            "scope":"WSL_LINUX_TUN_WBDWL4_ROOT_FQ_NOT_ETH0_IFB",
            **{k+"_delta":b[k]-a[k] for k in a}}
