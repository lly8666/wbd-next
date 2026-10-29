#!/usr/bin/env python3
"""Run one actual Windows guest/OS prerequisite with a hard child-tree deadline.

Use a regular temp file, not PIPE: killing wsl.exe with inherited Linux pipe
handles can otherwise make subprocess.communicate() block forever after a timeout.
No synthetic guest command or success fallback. A timed-out command is exit 124.
"""
import pathlib
import subprocess
import sys
import tempfile

def main():
    if len(sys.argv)<4:raise SystemExit("usage: bounded_cmd.py <seconds> <binary> [args...]")
    seconds=int(sys.argv[1])
    if seconds<1 or seconds>600:raise SystemExit("bounded OS command seconds must be 1..600")
    command=sys.argv[2:]
    with tempfile.TemporaryFile() as output:
        proc=subprocess.Popen(command,stdout=output,stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0))
        try:
            status=proc.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            print("WL_WSL2_COMMAND_TIMEOUT seconds="+str(seconds)+" binary="+pathlib.Path(command[0]).name,
                  file=sys.stderr,flush=True)
            if sys.platform=="win32":
                try:subprocess.run(["taskkill.exe","/PID",str(proc.pid),"/T","/F"],
                                   stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL,timeout=15,check=False)
                except (OSError,subprocess.TimeoutExpired):
                    pass
            if proc.poll() is None:proc.kill()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:pass
            return 124
        output.seek(0)
        # Limit all OS-command stderr/stdout output; preserve binary WSL list
        # NUL bytes in normal success output.
        data=output.read(128*1024)
        if data:
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
        return status
if __name__=="__main__":
    sys.exit(main())
