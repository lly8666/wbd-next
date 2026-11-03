"""Source-scoped real two-Linux netns V4 cold MSS/record/TUN verifier.

Consumes *actual* original-Go client/server logs and post-authenticated
kernel ip -j link MTU readbacks from arm64_linux_netns_smoke.sh. Both
directions, not a Rust theoretical vector or a green workflow title.
"""
import argparse
import json
import pathlib
import re

def one(pattern,log,label):
    values=re.findall(pattern,log)
    if not values:
        raise ValueError("H981 missing actual "+label)
    return values[-1]

def real_equal_outer_inner_mtu(outer:int,mode:str,game_fec:bool=False)->int:
    # Independent literal native-readback oracle; not the product budget path.
    if mode=="normal" and not game_fec:return outer-71
    if mode in ("fec-fixed","fec-auto") and not game_fec:return outer-85
    if mode in ("game2","game4"):return outer-(102 if game_fec else 87)
    raise ValueError("unsupported real ARM64 mode or FEC shape")

def verify(directory:pathlib.Path,mode:str,client_outer:int,server_outer:int,game_fec:bool=False):
    logs={side:(directory/(side+".log")).read_text(errors="replace")
          for side in ("client","server")}
    kernel=(directory/"mtu-boundary.txt").read_text()
    results={}
    for side,outer,direction in (
        ("client",client_outer,"c2s"),
        ("server",server_outer,"s2c"),
    ):
        log=logs[side]
        local=one(r"V4_PUBLIC_ACTUAL_HANDSHAKE_MSS_V1[^\n]*side="+side+
          r"[^\n]*local_advertised_mss=(\d+)[^\n]*tcp_option_bytes=([a-fA-F0-9]+)",
          log,side+" real encoded original SYN/SYNACK")
        mss=int(local[0]);opt=local[1].lower()
        if opt!="0204"+format(mss,"04x"):
            raise ValueError("H981 encoded TCP MSS mismatch "+side+" "+repr(local))
        peer_type="SYNACK" if side=="client" else "SYN"
        peer=int(one(r"V4_PUBLIC_ACTUAL_PEER_"+peer_type+
           r"_MSS_V1[^\n]*side="+side+r"[^\n]*peer_advertised_mss=(\d+)",
           log,side+" actual peer decoded SYN MSS"))
        pre=one(r"V4_PUBLIC_MTU_PREPARE[^\n]*role="+side+
           r"[^\n]*outer_config=(\d+)[^\n]*interface=(\d+)"+
           r"[^\n]*advertised_mss=(\d+)[^\n]*record_offer=(\d+)[^\n]*tun_planned=(\d+)",
           log,side+" actual original Rust pre-TLS budget")
        pre=[int(x) for x in pre]
        record=one(r"V4_PUBLIC_MTU role="+side+
           r"[^\n]*peer_mss=(\d+)[^\n]*local_record_cap=(\d+)"+
           r"[^\n]*peer_record_cap=(\d+)[^\n]*record_wire=(\d+)[^\n]*tun_mtu=(\d+)",
           log,side+" real authenticated record budget")
        record=[int(x) for x in record]
        applied=int(one(r"ARM64_REAL_MTU_BOUNDARY_PASS mode="+re.escape(mode)+
           r" direction="+direction+r" inner_ipv4=(\d+) df_plus_one=REJECTED",
           kernel,side+" OS post-authenticated TUN readback"))
        if (pre[0]!=outer or pre[2]!=mss or record[0]!=peer or
            record[3]>min(record[1],record[2]) or record[4]!=applied or
            applied>outer):
            raise ValueError("H981 directional peer/record/TUN mismatch "+side+
                             repr((pre,record,applied)))
        results[side]={"outer":outer,"physical":pre[1],
          "local_advertised_mss":mss,"actual_tcp_option_mss":opt,
          "received_peer_mss":peer,"local_record_offer":pre[3],
          "agreed_record_wire_cap":record[3],
          "inner_tun_planned":record[4],"inner_tun_os_applied":applied}
    if (results["client"]["received_peer_mss"]!=results["server"]["local_advertised_mss"] or
        results["server"]["received_peer_mss"]!=results["client"]["local_advertised_mss"]):
        raise ValueError("H981 Linux client/server MSS direction swap")
    if client_outer==server_outer and all(
        row["physical"]>=client_outer for row in results.values()):
        wire=client_outer-40
        inner=real_equal_outer_inner_mtu(client_outer,mode,game_fec)
        for side,row in results.items():
            if (row["local_advertised_mss"],row["received_peer_mss"],
                row["agreed_record_wire_cap"],row["inner_tun_os_applied"])!=(
                  wire,wire,wire,inner):
                raise ValueError("H981 hidden FEC1 56B or wrong record "+side+
                  repr(row))
    else:
        # Asymmetric peer MSS and record min must have a positive, measurable
        # restriction; do not cosmetically force equal independent MTUs.
        if client_outer!=server_outer and results["client"]["local_advertised_mss"]==results["server"]["local_advertised_mss"]:
            raise ValueError("H981 missing actual asymmetric MSS reason")
        for side,row in results.items():
            if row["inner_tun_os_applied"]>min(client_outer,server_outer):
                raise ValueError("H981 asymmetric MTU over maximum "+side)
    return {"mode":mode,"client_outer":client_outer,"server_outer":server_outer,
      "client":results["client"],"server":results["server"],
      "kernel_bidirectional":"REAL_LINUX_TUN_RAW_TLS_RUST_STOP_RETAINED"}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("directory",type=pathlib.Path)
    p.add_argument("mode")
    p.add_argument("client_outer",type=int)
    p.add_argument("server_outer",type=int)
    p.add_argument("--game-fec",action="store_true",help="real authenticated Game4 fixed6")
    x=p.parse_args()
    if x.game_fec and x.mode!="game4":raise SystemExit("only Game4 fixed6 accepted")
    print("H981_LINUX_CLIENT_SERVER_REAL_MTU_PROOF "+json.dumps(
      verify(x.directory,x.mode,x.client_outer,x.server_outer,x.game_fec),
      sort_keys=True),flush=True)
