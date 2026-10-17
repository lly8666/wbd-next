"""Reproducible FEC design arithmetic. MODEL_ONLY, never product qualification.

Execute in Actions. No dependencies, network, Monte Carlo or local product tests.
"""
from __future__ import annotations

import itertools
import json
import math


PROFILES = (("light", 1, 8), ("mild", 1, 4), ("medium", 3, 8),
            ("balanced", 1, 2), ("high", 3, 4), ("strong", 1, 1),
            ("maximum", 5, 4))


def parity(k: int, profile: tuple[str, int, int]) -> int:
    return (k * profile[1] + profile[2] - 1) // profile[2]


def residual(k: int, r: int, p: float) -> float:
    """An arbitrary source is erased and at least r other symbols are erased."""
    if k < 1 or r < 0 or not 0 <= p <= 1:
        raise ValueError("invalid model parameters")
    n = k + r - 1
    return p * math.fsum(math.comb(n, j) * p**j * (1-p)**(n-j)
                         for j in range(r, n+1))


def exhaustive_mean_source_loss(k: int, r: int, p: float) -> float:
    """Independent small-block oracle: enumerate complete erasure masks."""
    total = 0.0
    for bits in itertools.product((0, 1), repeat=k+r):
        erased = sum(bits)
        if erased > r:
            total += sum(bits[:k]) / k * p**erased * (1-p)**(k+r-erased)
    return total


def stationary(k: int, p: float) -> dict:
    """Ideal IID minimum, without estimator uncertainty/hysteresis/bursts."""
    for profile in PROFILES:
        r = parity(k, profile)
        q = residual(k, r, p)
        if q <= 0.001:
            return dict(profile=profile[0], r=r, residual_percent=q*100,
                        attainable=True)
    r = parity(k, PROFILES[-1])
    return dict(profile=PROFILES[-1][0], r=r,
                residual_percent=residual(k, r, p)*100, attainable=False)


def poisson_full_probability(k: int, rate_pps: float, deadline_s: float) -> float:
    """After first source, at least k-1 arrivals before deadline; not real traffic."""
    mu = rate_pps * deadline_s
    return max(0., min(1., 1-math.fsum(math.exp(-mu)*mu**i/math.factorial(i)
                                      for i in range(k-1))))


def close_deadline_ms(rate_pps: float | None, rtt_ms: float | None,
                      game: bool = False) -> float:
    """Design arithmetic only; EWMA/timers belong to the production owner."""
    cap = ((8. if game else 16.) if rtt_ms is None else
           min(12. if game else 24.,
               max(4. if game else 8., rtt_ms / (8 if game else 4))))
    minimum = 2. if game else 4.
    if rate_pps is None:
        return 3. if game else 6.
    if rate_pps < 0:
        raise ValueError("negative source rate")
    if rate_pps * cap / 1000 < 1:
        return minimum
    return min(cap, max(minimum, 1.5 * 15 / rate_pps * 1000))


def deadline_example(mbps: float, rtt_ms: float = 150.) -> dict:
    rate = mbps * 1e6 / 8 / 1200
    normal = close_deadline_ms(rate, rtt_ms)
    game = close_deadline_ms(rate, rtt_ms, game=True)
    return dict(class_source_mbps=mbps, rtt_ms=rtt_ms,
                mean_fill_ms=15 / rate * 1000,
                normal_deadline_ms=normal, game_deadline_ms=game,
                poisson_normal_full_probability=poisson_full_probability(16, rate, normal/1000),
                poisson_game_full_probability=poisson_full_probability(16, rate, game/1000))


def verify_arithmetic() -> dict:
    for k in (1, 2, 3, 4):
        for r in (0, 1, 2, 3):
            for p in (0, 0.01, 0.05, 0.2, 0.5, 1):
                assert math.isclose(residual(k, r, p),
                                    exhaustive_mean_source_loss(k, r, p),
                                    rel_tol=1e-11, abs_tol=1e-13)
    for r in range(4):
        assert math.isclose(residual(1, r, .2), .2**(r+1), abs_tol=1e-14)
    assert math.isclose(residual(20, 4, .05), .0012907252927393228,
                        rel_tol=1e-12)
    assert stationary(16, .05)["profile"] == "mild"
    assert stationary(8, .05)["profile"] == "medium"
    assert stationary(1, .2)["attainable"] is False
    assert [parity(16, x) for x in PROFILES] == [2, 4, 6, 8, 12, 16, 20]
    for mbps, normal, game in ((100, 4, 2.16), (50, 4.32, 4.32),
                               (30, 7.2, 7.2), (15, 14.4, 12),
                               (10, 21.6, 12), (6, 24, 12)):
        case = deadline_example(mbps)
        assert math.isclose(case["normal_deadline_ms"], normal, abs_tol=1e-12)
        assert math.isclose(case["game_deadline_ms"], game, abs_tol=1e-12)
    assert close_deadline_ms(0, 600) == 4
    assert close_deadline_ms(20, 600, game=True) == 2
    assert close_deadline_ms(None, None) == 6
    assert close_deadline_ms(None, None, game=True) == 3
    assert close_deadline_ms(100, None) == 16
    assert close_deadline_ms(100, None, game=True) == 2  # 100pps * 8ms < 1
    assert close_deadline_ms(200, None, game=True) == 8
    assert math.isclose(poisson_full_probability(16, 1000, .0225),
                        .9613982417336826, abs_tol=1e-12)
    return dict(result="ARITHMETIC_SELF_CHECK_PASS", product="NOT_RUN")


def main() -> None:
    print(json.dumps({
        "schema_version": 2,
        "scope": "MODEL_ONLY_NOT_PRODUCT_OR_PERFORMANCE_PASS",
        "assumptions": ["systematic MDS erasure code", "IID equal source/parity loss",
                        "all available symbols in deadline", "no outer/app repair",
                        "source-symbol loss, not fragmented datagram failure"],
        "formula": "p * Pr[Binomial(k+r-1,p) >= r]",
        "verification": verify_arithmetic(),
        "profiles": [dict(name=x[0], numerator=x[1], denominator=x[2],
                          r_at_k16=parity(16, x)) for x in PROFILES],
        "ideal_curves": [dict(k=k, loss_percent=p*100, **stationary(k, p))
                         for k in (1, 4, 8, 16)
                         for p in (.01, .03, .05, .10, .15, .20, .25, .30)],
        "deadline_cap_ms": [dict(rtt_ms=rtt, normal=min(24, max(8, rtt/4)),
                                 game=min(12, max(4, rtt/8)))
                            for rtt in (10, 50, 150, 600)],
        "adaptive_deadline_1200B": [deadline_example(mbps, rtt)
                                    for rtt in (50, 150, 600)
                                    for mbps in (6, 10, 15, 30, 50, 100)],
        "fill_ms_1200B_k16": [dict(source_mbps=mbps,
                                  fill_ms=15/(mbps*1e6/8/1200)*1000)
                              for mbps in (6, 10, 15, 30, 50, 100, 200, 500)],
        "rejected_old_deadline_examples": [dict(class_source_mbps=mbps, deadline_ms=ms,
            full_k16_probability=poisson_full_probability(16, mbps*1e6/8/1200, ms/1000))
            for mbps, ms in ((30, 4), (15, 8), (10, 8))],
        "poisson_fill_margin_examples": [dict(mean_multiplier=multiple,
            full_k16_probability=poisson_full_probability(16, 1000, .015*multiple))
            for multiple in (1, 1.5)],
        "equal_100_percent_parity_partial_loss": [dict(k=k, r=k,
            loss_percent=p*100, residual_percent=residual(k, k, p)*100)
            for p in (.2, .3) for k in (8, 16, 20)],
        "header_only_same_k16_r16": [dict(source_bytes=n,
             old_fec_bytes=32*(n+56), new_fec_bytes=16*(n+10)+16*(n+14))
             for n in (64, 1200)],
        "game_iid_examples": [dict(lanes=lanes, lane_loss_percent=30,
            effective_symbol_loss=.3**lanes,
            residual_percent_k8_r8=residual(8, 8, .3**lanes)*100,
            fully_correlated_residual_percent_k8_r8=residual(8, 8, .3)*100)
            for lanes in (1, 2, 4)],
        "table_cache_bytes_all_k1_to16_r20": 32*20*sum(range(1, 17)),
        "limits": "No production estimator/auto controller, burst, host, native ISA or RTT validation."
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
