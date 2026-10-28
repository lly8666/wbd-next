"""One concrete kernel impairment / offer profile, shared across both OS processes.
This is TEST infrastructure only; a configured tc bandwidth is not measured throughput.
"""
PROFILES = {
    "n0": {"delay_ms":300,"loss_pct":0,"tc_mbit":None,
           "offered_mbps":10.0,"duration_s":240},
    "p200-250m-30p": {"delay_ms":200,"loss_pct":30,"tc_mbit":250,
                       "offered_mbps":250.0,"duration_s":60},
}
def get_profile(name, side=None, configfile=None):
    if name == "v2":
        if side not in ("windows", "linux") or not configfile:
            raise ValueError("V2 requires exact side and scenario file")
        try:
            from .m0_wl_perf_v2_config import read_scenario, profile
        except ImportError:
            from m0_wl_perf_v2_config import read_scenario, profile
        return profile(read_scenario(configfile),side)
    return PROFILES[name]
