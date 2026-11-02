"""Exact real M4 owned new-session MTU scenarios, not in-place OS mutation.

The original five-stage MTU CAS/WAL can restore an entire generation. Running
another configured native session is safe only after the previous Stop
confirmed full OS/WAL cleanup. No unsupported 9000-byte JNI/Go ABI claim.
"""
import os
PUBLIC_NATIVE_MTUS=(1280,1400,1460,1500)
NATIVE_OUTER_CHOICES=('legacy1400','default1460','1460','1500')

def native_outer_choice(value):
 if type(value) is not str or value not in NATIVE_OUTER_CHOICES:
  raise ValueError('unsupported original native outer IP MTU selector')
 return value

def exact_native_test_mtu(value:str|int)->int:
 try:
  mtu=int(value)
 except (ValueError,TypeError) as error:
  raise ValueError("unsupported original native Wintun test MTU") from error
 if str(mtu)!=str(value) or mtu not in PUBLIC_NATIVE_MTUS:
  raise ValueError("unsupported original native Wintun test MTU")
 return mtu

def configured_native_test_mtu()->int:
 choice=native_outer_choice(os.environ.get("WBD_WL_NATIVE_OUTER_MTU_REQUEST","legacy1400"))
 requested=exact_native_test_mtu(os.environ.get("WBD_WL_TUN_MTU","1400"))
 if choice!="legacy1400" and requested!=(1460 if choice=="default1460" else int(choice)):
  raise ValueError("outer MTU selector/source scenario mismatch")
 return requested
