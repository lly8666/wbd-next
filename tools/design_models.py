"""Reference algebra for the architecture, not a Rust/ISA-L implementation or benchmark.

Run only in Actions. The reduced e-by-e decoder is checked against a separate
full 20-by-20 selected-row solve and the original systematic input. This does
not replace future comparison with compiled legacy Go or unsafe SIMD tests.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import random
from functools import lru_cache


def polynomial_mul(a: int, b: int) -> int:
    if not 0 <= a < 256 or not 0 <= b < 256:
        raise ValueError("not a GF256 element")
    result = 0
    while b:
        if b & 1:
            result ^= a
        a <<= 1
        if a & 256:
            a ^= 0x11D
        b >>= 1
    return result


MUL = tuple(tuple(polynomial_mul(a, b) for b in range(256)) for a in range(256))


def inverse_scalar(a: int) -> int:
    if not 0 < a < 256:
        raise ValueError("zero or invalid pivot")
    result, power = 1, a
    exponent = 254
    while exponent:
        if exponent & 1:
            result = MUL[result][power]
        power = MUL[power][power]
        exponent >>= 1
    return result


def identity(n: int) -> list[list[int]]:
    return [[int(i == j) for j in range(n)] for i in range(n)]


def inverse(matrix: list[list[int]]) -> list[list[int]]:
    n = len(matrix)
    if not n or any(len(row) != n for row in matrix):
        raise ValueError("expected nonempty square matrix")
    rows = [list(row) + unit for row, unit in zip(matrix, identity(n))]
    for col in range(n):
        pivot = next((i for i in range(col, n) if rows[i][col]), None)
        if pivot is None:
            raise ValueError("singular matrix")
        rows[col], rows[pivot] = rows[pivot], rows[col]
        scale = MUL[inverse_scalar(rows[col][col])]
        rows[col] = [scale[x] for x in rows[col]]
        for i in range(n):
            if i != col and rows[i][col]:
                factor = MUL[rows[i][col]]
                rows[i] = [x ^ factor[y] for x, y in zip(rows[i], rows[col])]
    return [row[n:] for row in rows]


def multiply(left: list[list[int]], right: list[list[int]]) -> list[list[int]]:
    if not right or not right[0] or any(len(row) != len(right[0]) for row in right):
        raise ValueError("invalid right matrix")
    if any(len(row) != len(right) for row in left):
        raise ValueError("matrix dimension mismatch")
    output = []
    for row in left:
        dest = [0] * len(right[0])
        for factor, source in zip(row, right):
            if factor:
                table = MUL[factor]
                for i, value in enumerate(source):
                    dest[i] ^= table[value]
        output.append(dest)
    return output


@lru_cache(maxsize=1)
def generator() -> tuple[tuple[int, ...], ...]:
    vandermonde = []
    for x in range(1, 41):
        row = [1]
        for _ in range(19):
            row.append(MUL[row[-1]][x])
        vandermonde.append(row)
    return tuple(tuple(row) for row in multiply(vandermonde, inverse(vandermonde[:20])))


def reduced_coefficients(k: int, missing: tuple[int, ...], parity: tuple[int, ...]):
    """Input order: ascending known sources, then explicitly chosen parity rows."""
    if not 1 <= k <= 20 or len(set(missing)) != len(missing):
        raise ValueError("invalid k or repeated source")
    if any(i < 0 or i >= k for i in missing):
        raise ValueError("missing source outside active columns")
    e = len(missing)
    if len(parity) != e or len(set(parity)) != e or any(p < 20 or p >= 40 for p in parity):
        raise ValueError("need e distinct valid parity rows")
    known = tuple(i for i in range(k) if i not in missing)
    if not e:
        return known, []
    g = generator()
    inv = inverse([[g[p][u] for u in missing] for p in parity])
    # With no known columns the left half is empty, not a zero-width multiply.
    left = multiply(inv, [[g[p][i] for i in known] for p in parity]) if known else [[] for _ in missing]
    return known, [a + b for a, b in zip(left, inv)]


def check_case(k: int, configured_r: int, missing: tuple[int, ...], parity: tuple[int, ...], salt: int):
    if configured_r not in (4, 8, 10, 12, 16, 20):
        raise ValueError("unknown profile")
    if any(p >= 20 + min(k, configured_r) for p in parity):
        raise ValueError("parity was not sent in this partial block")
    g = generator()
    # Eight independent byte columns, includes zeros and high bytes. Inactive
    # columns are authoritative zeros, as in the legacy full matrix solve.
    sources = [[(salt + i * 67 + j * 31 + i * j) & 255 for j in range(8)]
               if i < k else [0] * 8 for i in range(20)]
    parity_data = multiply([list(g[p]) for p in parity], sources)
    known, coefficients = reduced_coefficients(k, missing, parity)
    if not missing:
        return
    reduced = multiply(coefficients, [sources[i] for i in known] + parity_data)
    # Independent reference: select 20 full generator rows, including inactive
    # systematic zero rows, invert the entire 20x20 matrix, recover wanted rows.
    available = tuple(i for i in range(20) if i not in missing) + parity
    full_inv = inverse([list(g[i]) for i in available])
    full_data = [sources[i] for i in available if i < 20] + parity_data
    full = multiply([full_inv[i] for i in missing], full_data)
    original = [sources[i] for i in missing]
    if reduced != original or full != original:
        raise AssertionError(f"decode disagreement k={k} r={configured_r} U={missing} P={parity}")


@lru_cache(maxsize=1)
def verification_report():
    cases, exhaustive, rng = 0, 0, random.Random(20261014)
    for k in range(1, 21):
        for r in (4, 8, 10, 12, 16, 20):
            sent_r = min(k, r)
            for e in range(sent_r + 1):
                # Nonadjacent missing sources/parity rows prevent testing only
                # leading square submatrices. Fixed seed is not changed on fail.
                missing = tuple(sorted(rng.sample(range(k), e)))
                parity = tuple(sorted(rng.sample(range(20, 20 + sent_r), e)))
                check_case(k, r, missing, parity, cases)
                cases += 1
    for k in range(1, 5):
        for e in range(k + 1):
            for missing in itertools.combinations(range(k), e):
                for parity in itertools.combinations(range(20, 20 + k), e):
                    check_case(k, 20, missing, parity, cases + exhaustive)
                    exhaustive += 1
    g = generator()
    return {
        "scope": "ALGEBRA_MODEL_ONLY_NOT_PRODUCT_QUALIFICATION",
        "result": "PASS",
        "product_result": "NOT_RUN",
        "compiled_legacy_go_comparison": "NOT_RUN",
        "isa_l_and_rust_memory_safety": "NOT_RUN",
        "gf_polynomial": "0x11d",
        "generator_sha256": hashlib.sha256(bytes(x for row in g for x in row)).hexdigest(),
        "all_active_k": [1, 20], "profiles": [4, 8, 10, 12, 16, 20],
        "each_erasure_count_cases": cases,
        "exhaustive_small_k_cases": exhaustive,
        "total_decode_cases": cases + exhaustive,
        "checks": ["e-by-e versus full 20-by-20 selected-row solve", "both versus original input",
                   "all possible source/parity choices for active k<=4",
                   "no missing source performs no inverse", "inactive source columns are zero"],
    }


if __name__ == "__main__":
    print(json.dumps(verification_report(), indent=2))
