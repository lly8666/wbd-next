import re
PATTERN=re.compile(r"WBD_WINDOWS_RUST_NATIVE_ENTRY_LOCK_SAMPLED sample_every=(\d+) tx_samples=(\d+) tx_wait_ns=(\d+) tx_max_ns=(\d+) rx_samples=(\d+) rx_wait_ns=(\d+) rx_max_ns=(\d+)")
def parse_native_lock_profile(text):
    matches=PATTERN.findall(text)
    if not matches:
        return {"status":"NOT_MEASURED"}
    k,ts,tw,tm,rs,rw,rm=map(int,matches[-1])
    return {"status":"MEASURED","sample_every":k,
        "tx_samples":ts,"tx_wait_ns":tw,"tx_max_ns":tm,
        "rx_samples":rs,"rx_wait_ns":rw,"rx_max_ns":rm,
        "tx_mean_wait_ns":round(tw/ts,2) if ts else None,
        "rx_mean_wait_ns":round(rw/rs,2) if rs else None}
