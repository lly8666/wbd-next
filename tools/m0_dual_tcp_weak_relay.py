#!/usr/bin/env python3
"""Dedicated H2555 relay impairment entry; reuse actual H2228 topology/control."""
import json
import m0_h2228_three_runner_relay as h

def impair(loss,delay,model):
    loss=float(loss);delay=int(delay)
    h.guard(model=="internet" and ((delay==0 and loss==0) or
        (delay==200 and loss in (1.,3.,5.))),"WEAK_PROFILE")
    ge=h.ge_params(loss) if loss else None
    receipts={};jitter={};commands={}
    for role,dev in h.RDEV.items():
        # Clear between runs so Markov state and queued packets do not carry
        # across legs. Independent directional random streams.
        h.ns(h.ROUTER,"tc","qdisc","del","dev",dev,"root",allow_fail=True)
        j=15 if role=="client" else 10
        terms=["delay","200ms",str(j)+"ms","50%","distribution","paretonormal"] if delay else ["delay","0ms"]
        extras=["loss","gemodel",str(ge["transition_good_bad_pct"])+"%","25%","90%","0.1%"] if ge else ["loss","0%"]
        args=["tc","qdisc","replace","dev",dev,"root","handle","1:","netem",*terms,*extras,"limit","65536"]
        h.ns(h.ROUTER,*args)
        if delay:
            # A single queue-like path; avoid artificial per-packet overtaking
            # from the default time-sorted queue at high PPS.
            h.ns(h.ROUTER,"tc","qdisc","replace","dev",dev,"parent","1:1","handle","10:","pfifo","limit","65536")
        q=json.loads(h.ns(h.ROUTER,"tc","-s","-j","qdisc","show","dev",dev).stdout)
        h.guard(any(x.get("kind")=="netem" for x in q),"WEAK_NETEM_READBACK")
        if delay:h.guard(any(x.get("kind")=="pfifo" for x in q),"WEAK_FIFO_READBACK")
        receipts[dev]=q;jitter[role]=j if delay else 0;commands[role]=args
    return {"loss_target_pct":loss,"one_way_added_delay_ms":delay,
        "jitter_ms_by_egress":jitter,"jitter_correlation_pct":50 if delay else 0,
        "distribution":"paretonormal","loss_model":"internet","gilbert":ge,
        "qdisc_packet_limit":65536,"seed":None,
        "seed_note":"prior native runner tc lacks netem seed option; independent stochastic draws, no seed shopping",
        "bandwidth_rate_cap":"NONE","apply_to":"RELAY_ROUTER_ONLY_EGRESS_BOTH_DIRECTIONS",
        "fifo_no_intentional_reorder":True,"qdiscs":receipts,"commands":commands,
        "no_tailscale_or_endpoint_qdisc_changed":True}

if __name__=="__main__":
    h.impair=impair
    h.main()
