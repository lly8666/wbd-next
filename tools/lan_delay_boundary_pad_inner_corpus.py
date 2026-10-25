#!/usr/bin/env python3
"""Owned genuine TLS 1.3 inner traffic corpus. Uses only ephemeral local TLS keys.
Produces records for a *separate* lab TCP/IP overlay, not outer WBD protocol.
"""
import argparse,hashlib,json,pathlib,ssl
p=argparse.ArgumentParser();p.add_argument("--cert",required=True);p.add_argument("--key",required=True)
p.add_argument("--dir",type=pathlib.Path,required=True);a=p.parse_args()
a.dir.mkdir(parents=True,exist_ok=True)
srv=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
srv.minimum_version=srv.maximum_version=ssl.TLSVersion.TLSv1_3
srv.load_cert_chain(a.cert,a.key)
cli=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
cli.minimum_version=cli.maximum_version=ssl.TLSVersion.TLSv1_3
cli.check_hostname=False;cli.verify_mode=ssl.CERT_NONE
cli.set_alpn_protocols(["h2","http/1.1"])
ci,co,si,so=(ssl.MemoryBIO() for i in range(4))
c=cli.wrap_bio(ci,co,server_hostname="private.inner-wbd.example")
s=srv.wrap_bio(si,so,server_side=True)
done_c=done_s=False
client_records=[];server_records=[]
for i in range(150):
    if not done_c:
        try:c.do_handshake();done_c=True
        except ssl.SSLWantReadError:pass
    if not done_s:
        try:s.do_handshake();done_s=True
        except ssl.SSLWantReadError:pass
    for source,dest,arr in ((co,si,client_records),(so,ci,server_records)):
        while True:
            d=source.read()
            if not d:break
            arr.append(d);dest.write(d)
    if done_c and done_s:break
assert done_c and done_s and c.version()==s.version()=="TLSv1.3"
ch=client_records[0]
assert ch[0]==22 and ch[1:3] in (b"\x03\x01",b"\x03\x03")
assert b"private.inner-wbd.example" in ch
assert b"h2" in ch
sf=b"".join(server_records)
assert sf[0]==22 and sf[1:3]==b"\x03\x03"
assert b"\x17\x03\x03" in sf
assert len(client_records)>=2,"genuine client finished missing"
client_finished=b"".join(client_records[1:])
# In TLS1.3 compatibility mode a plaintext ChangeCipherSpec (0x14) may
# precede the encrypted client Finished (0x17) in one outgoing flight.
assert len(client_finished)>40 and b"\x17\x03\x03" in client_finished
assert client_finished[:3] in (b"\x14\x03\x03",b"\x17\x03\x03")
while so.read():pass
data=bytes(((i*37+11)&255) for i in range(16000))
assert s.write(data)==len(data)
app=so.read()
assert app[:3]==b"\x17\x03\x03"
n=int.from_bytes(app[3:5],"big")
assert n>=1300 and n+5<=len(app)
ci.write(app[:n+5]);assert c.read(16000)==data
for name,b in (("client_hello.bin",ch),("server_flight.bin",sf),("client_finished.bin",client_finished),("encrypted_app.bin",app[:n+5])):
    (a.dir/name).write_bytes(b)
# The public test marker is not a real private website.
summary={"inner_tls":"TLSv1.3",
 "handshake":"GENUINE_OPENSSL_MEMORYBIO",
 "client_hello_contains_test_SNI":True,
 "client_hello_contains_ALPN":True,
 "server_flight_first_outer_record_type":22,
 "client_hello_bytes":len(ch),"server_flight_bytes":len(sf),
 "client_finished_encrypted_bytes":len(client_finished),
 "client_finished_after_real_completed_handshake":True,
 "app_record_bytes":n+5,"app_decrypt_verified":True,
 "public_test_domain":"private.inner-wbd.example",
 "raw_corpus_retained":False,
 "hashes":{name:hashlib.sha256((a.dir/name).read_bytes()).hexdigest() for name in ("client_hello.bin","server_flight.bin","client_finished.bin","encrypted_app.bin")}}
print(json.dumps(summary))
