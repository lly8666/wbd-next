"""Reuse H2228 actual routed VXLAN segments; WSL only the Windows access router."""
import os,sys,pathlib,json,platform,subprocess
import m0_h2228_three_runner_relay as h
def load(p):return json.loads(pathlib.Path(p).read_text(encoding="utf-8-sig"))
def main():
    action=sys.argv[1]
    if action=="client-meta":
        d=h.metainfo("client");d["windows_access_ip"]=sys.argv[3]
        h.save(sys.argv[2],d)
    elif action=="relay-route":
        d=load(sys.argv[2]);ip=d["windows_access_ip"]
        import ipaddress
        assert ipaddress.ip_address(ip).is_private
        h.ns(h.ROUTER,"ip","route","replace",ip+"/32","via",h.LAN["client"],"dev",h.RDEV["client"])
    elif action=="server-route":
        ip=load(sys.argv[2])["windows_access_ip"]
        h.ns(h.NODE,"ip","route","replace",ip+"/32","via",h.GW["server"],"dev","wan0")
    elif action=="windows-gateway":
        peer=load(sys.argv[2]);our=h.metainfo("client");h.validate_pair(our,peer,"relay")
        root=h.root
        assert "h228bc" not in h.cmd("ip","-o","link","show").stdout
        root("ip","link","add","h228bc","type","bridge")
        root("ip","link","set","h228bc","up")
        h.vxlan("client",our["tail_ip"],peer["tail_ip"],"h228vc","2281","h228bc")
        root("ip","addr","add","10.248.81.2/24","dev","h228bc")
        root("ip","link","set","h228vc","mtu","1200")
        root("ip","link","set","h228bc","mtu","1200")
        root("ip","route","replace","10.248.82.0/24","via","10.248.81.1","dev","h228bc")
        root("sysctl","-qw","net.ipv4.ip_forward=1")
        for dev in ("all","eth0","h228bc"):root("sysctl","-qw","net.ipv4.conf."+dev+".rp_filter=0")
        for a,b in (("eth0","h228bc"),("h228bc","eth0")):
            root("iptables","-I","FORWARD","1","-i",a,"-o",b,"-j","ACCEPT")
        # Clamp only direct genuine kernel TCP MSS to the previous VXLAN MTU.
        root("iptables","-t","mangle","-A","FORWARD","-p","tcp","--tcp-flags","SYN,RST","SYN","--dport","5202","-j","TCPMSS","--set-mss","1160")
        h.save(sys.argv[3],{"actual_gateway_only":True,"route":h.cmd("ip","route","get","10.248.82.2").stdout,"tail":h.tailscale_ip()})
    else:raise ValueError(action)
if __name__=="__main__":main()
