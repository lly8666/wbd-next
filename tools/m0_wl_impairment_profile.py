"""One concrete kernel impairment / offer profile, shared across both OS processes.
This is TEST infrastructure only; a configured tc bandwidth is not measured throughput.
"""
PROFILES = {
    "n0": {"delay_ms":300,"loss_pct":0,"tc_mbit":None,
           "offered_mbps":10.0,"duration_s":240},
    "p200-250m-30p": {"delay_ms":200,"loss_pct":30,"tc_mbit":250,
                       "offered_mbps":250.0,"duration_s":60},
}
def get_profile(name):
    return PROFILES[name]
