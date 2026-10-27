"""Exact real M4 owned new-session MTU scenarios, not in-place OS mutation.

The original five-stage MTU CAS/WAL can restore an entire generation. Running
another configured native session is safe only after the previous Stop
confirmed full OS/WAL cleanup. No unsupported 9000-byte JNI/Go ABI claim.
"""
import os
PUBLIC_NATIVE_MTUS=(1280,1400,1500)

def exact_native_test_mtu(value:str|int)->int:
 try:
  mtu=int(value)
 except (ValueError,TypeError) as error:
  raise ValueError("unsupported original native Wintun test MTU") from error
 if str(mtu)!=str(value) or mtu not in PUBLIC_NATIVE_MTUS:
  raise ValueError("unsupported original native Wintun test MTU")
 return mtu

def configured_native_test_mtu()->int:
 return exact_native_test_mtu(os.environ.get("WBD_WL_TUN_MTU","1400"))
