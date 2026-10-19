#!/usr/bin/env python3
"""Fail-closed *real native library* identity/load probe, not product activation.

M0 supplies authenticated owner ABI/export names and original Rust SOURCE.
Checking an ISA-L static archive alone is not this loader qualification.
"""
from __future__ import annotations
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import struct
import sys


def architecture(data: bytes) -> str:
    if data.startswith(b"MZ"):
        if len(data)<0x40: raise ValueError("short PE DOS header")
        off=struct.unpack_from("<I",data,0x3c)[0]
        if off+26>len(data) or data[off:off+4]!=b"PE\0\0":
            raise ValueError("invalid PE header")
        machine=struct.unpack_from("<H",data,off+4)[0]
        return {0x8664:"windows-amd64",0xaa64:"windows-arm64"}.get(machine,"UNSUPPORTED_PE")
    if data.startswith(b"\x7fELF"):
        if len(data)<20 or data[4]!=2: raise ValueError("invalid or non-ELF64")
        machine=struct.unpack_from("<H" if data[5]==1 else ">H",data,18)[0]
        return {62:"linux-amd64",183:"linux-arm64"}.get(machine,"UNSUPPORTED_ELF")
    raise ValueError("not PE/ELF; do not load a Linux archive as Windows DLL")


def inspect(path: Path, expected: str, sha: str, required_symbols: list[str], execute: bool):
    if not path.is_file(): raise FileNotFoundError("required Rust library absent")
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=sha.lower():
        raise ValueError("native library SHA256 mismatch")
    actual=architecture(data)
    if actual!=expected:raise ValueError("wrong native architecture: "+actual)
    loaded=False
    if execute:
        if (expected=="windows-amd64" and sys.platform!="win32") or (
            expected.startswith("linux") and not sys.platform.startswith("linux")):
            raise ValueError("cross-target is not native runtime")
        lib=ctypes.CDLL(str(path.resolve()))
        for symbol in required_symbols:
            if not hasattr(lib,symbol):
                raise ValueError("missing pinned Rust ABI symbol: "+symbol)
        loaded=True
    return {"result":"LOAD_PASS" if loaded else "ARCH_AND_HASH_ONLY",
            "target":expected,"sha256":sha,"required_exports":required_symbols,
            "product_fec2":"OFF","native_execution":loaded,
            "driver":"NOT_RUN","authenticated_go_rust_applied":"NOT_RUN"}


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--library",type=Path,required=True)
    p.add_argument("--target",required=True,choices=["windows-amd64","linux-amd64","linux-arm64"])
    p.add_argument("--sha256",required=True)
    p.add_argument("--symbol",action="append",default=[])
    p.add_argument("--native-load",action="store_true")
    p.add_argument("--receipt",type=Path,required=True)
    a=p.parse_args()
    try:
        info=inspect(a.library,a.target,a.sha256,a.symbol,a.native_load)
        a.receipt.parent.mkdir(parents=True,exist_ok=True)
        a.receipt.write_text(json.dumps(info,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(info))
    except (ValueError,OSError,AttributeError) as ex:
        print("UNSUPPORTED_OR_REJECTED_NATIVE_LOADER: "+str(ex),file=sys.stderr)
        sys.exit(2)
