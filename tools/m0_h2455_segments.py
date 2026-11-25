"""H2455 out-of-process boundary snapshots."""
import concurrent.futures,json,pathlib,subprocess,time
def command(args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=12)
    return {"rc":p.returncode,"stdout":p.stdout,"stderr":p.stderr}
def linux_snapshot(namespace=None):
    prefix=["sudo","-n","ip","netns","exec",namespace] if namespace else []
    commands={"links":["ip","-s","-j","link","show"],"qdisc":["tc","-s","-j","qdisc","show"],"nstat":["nstat","-az"],"softnet":["cat","/proc/net/softnet_stat"]}
    return {k:command(prefix+v) for k,v in commands.items()}
def collect(folder,tag,readers):
    def timed(fn):
        d={"start_ns":time.monotonic_ns(),"wall_start_ns":time.time_ns()}
        try:d["value"]=fn()
        except Exception as e:d["error"]=repr(e)
        d["end_ns"]=time.monotonic_ns();return d
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(readers)) as pool:
        futures={k:pool.submit(timed,v) for k,v in readers.items()}
        row={k:f.result() for k,f in futures.items()}
    pathlib.Path(folder,"segments-"+tag+".json").write_text(json.dumps(row,indent=2)+"\n")
    print("H2455_SEGMENTS "+json.dumps({"tag":tag,"errors":{k:v["error"] for k,v in row.items() if "error" in v}}),flush=True)
    return row
def windows_readers(root,wsl,wpath,ps,control):
    return {
        "server":lambda:control("server","/sample"),
        "relay":lambda:control("relay","/snapshot"),
        "wsl":lambda:json.loads(wsl("python3",wpath(root/"tools/m0_h2455_segments.py"),timeout=55)),
        "windows":lambda:json.loads(ps("Get-NetAdapterStatistics | Select-Object Name,ReceivedBytes,SentBytes,ReceivedUnicastPackets,SentUnicastPackets,ReceivedDiscardedPackets,OutboundDiscardedPackets,ReceivedPacketErrors,OutboundPacketErrors | ConvertTo-Json -Compress"))
    }
if __name__=="__main__":
    print(json.dumps(linux_snapshot()))
