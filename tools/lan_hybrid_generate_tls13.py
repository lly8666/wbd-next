#!/usr/bin/env python3
"""Generate REAL locally authenticated TLS1.3 application ciphertext for a
bounded mixed-traffic ideal-oracle CPU lab. Ephemeral cert/key never uploaded.
"""
import argparse
import hashlib
import json
import pathlib
import ssl

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--cert",required=True,type=pathlib.Path)
    ap.add_argument("--key",required=True,type=pathlib.Path)
    ap.add_argument("--out",required=True,type=pathlib.Path)
    ap.add_argument("--summary",required=True,type=pathlib.Path)
    a=ap.parse_args()
    srv=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    srv.minimum_version=srv.maximum_version=ssl.TLSVersion.TLSv1_3
    srv.load_cert_chain(str(a.cert),str(a.key))
    cli=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    cli.minimum_version=cli.maximum_version=ssl.TLSVersion.TLSv1_3
    # Offline ephemeral lab cert; peer proof by recovered plaintext after
    # the genuine TLS1.3 wire transform, NOT production certificate admission.
    cli.check_hostname=False
    cli.verify_mode=ssl.CERT_NONE
    ci,co,si,so=(ssl.MemoryBIO() for _ in range(4))
    c=cli.wrap_bio(ci,co,server_side=False,server_hostname="localhost")
    s=srv.wrap_bio(si,so,server_side=True)
    cd=sd=False
    for _ in range(100):
        if not cd:
            try: c.do_handshake();cd=True
            except ssl.SSLWantReadError: pass
        if not sd:
            try: s.do_handshake();sd=True
            except ssl.SSLWantReadError: pass
        for source,dest in ((co,si),(so,ci)):
            while True:
                chunk=source.read()
                if not chunk:break
                dest.write(chunk)
        if cd and sd:break
    assert cd and sd and c.version()==s.version()=="TLSv1.3"
    # TLS1.3 NewSessionTicket is NOT application data despite outer 0x17.
    # Deliberately discard only this handshake-stage server output.
    while so.read():pass
    original=bytes(((i*37+11)&255) for i in range(16000))
    assert s.write(original)==len(original)
    observed=so.read()
    assert len(observed)>=1305 and observed[:3]==b"\x17\x03\x03"
    n=int.from_bytes(observed[3:5],"big")
    assert n>=1300 and 5+n<=len(observed)
    record=observed[:5+n]
    ci.write(record)
    assert c.read(len(original))==original
    a.out.write_bytes(record)
    d={
        "source":"genuine local OpenSSL TLS1.3 MemoryBIO post-handshake server application record",
        "version":c.version(),
        "outer_type":23,"record_total_len":len(record),
        "body_len":n,"sha256":hashlib.sha256(record).hexdigest(),
        "successful_tls13_decrypt_and_plaintext_match":True,
        "client_certificate_authentication":"NOT_REQUESTED",
        "exported_corpus":False,
        "classification_provenance":"EXTERNAL_PER_PACKET_TRUSTED_BENCH_ORACLE_ONLY",
        "tls13_0x17_means_application":"FALSE_handshake_and_alert_can_also_be_0x17"
    }
    a.summary.write_text(json.dumps(d,indent=2)+"\n")
    print(json.dumps(d))

if __name__=="__main__":main()
