"""H2476 hosted-runner fixture import. Only called when Ubuntu was absent."""
import os
import pathlib
from m0_wl_windows_bounded_cmd import run_captured

def command(label, seconds, *args):
    print("H2476_WSL_" + label + "_START", flush=True)
    r = run_captured(["wsl.exe", *args], seconds)
    log = pathlib.Path("result") / ("h1706-ubuntu-" + label.lower() + ".log")
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(r.stdout + "\n" + r.stderr, encoding="utf-8")
    print("H2476_WSL_" + label + "_DONE rc=" + str(r.returncode), flush=True)
    return r

def main():
    root = pathlib.Path(os.environ["RUNNER_TEMP"])
    image = root / "ubuntu-24.04.5-wsl-amd64.tar"
    dest = root / "wbd-real-ubuntu-wsl2"
    dest.mkdir()
    r = command("IMPORT_FIRST", 100, "--import", "Ubuntu", str(dest), str(image), "--version", "2")
    if r.returncode == 0:
        return
    # Hosted fixture only: Ubuntu was absent before this step; clean up
    # only this step's attempted registration, then one fresh directory.
    if command("SHUTDOWN", 20, "--shutdown").returncode:
        raise SystemExit("WSL host did not respond to shutdown")
    inventory = command("RETRY_INVENTORY", 20, "--list", "--quiet")
    if inventory.returncode:
        raise SystemExit("WSL host did not respond to inventory")
    names = [x.strip().lstrip("\ufeff") for x in inventory.stdout.replace("\x00", "").splitlines()]
    if "Ubuntu" in names:
        if command("UNREGISTER_OWNED", 20, "--unregister", "Ubuntu").returncode:
            raise SystemExit("owned Ubuntu partial import could not be removed")
    dest = root / "wbd-real-ubuntu-wsl2-retry"
    dest.mkdir()
    r = command("IMPORT_RETRY", 100, "--import", "Ubuntu", str(dest), str(image), "--version", "2")
    if r.returncode:
        raise SystemExit("real WSL2 import failed after one owned retry")

if __name__ == "__main__":
    main()
