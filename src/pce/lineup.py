"""Reduced-form lineup value function (stands in for the decision simulator of DESIGN 5.3).

A slot's expected matchup wOBA against relievers is modelled as its hitter-season baseline plus
effects of whether each of the four nearest slots holds a left-only hitter, estimated separately
for left, right and switch hitters, with one interaction (both of the next two are lefties).
"Spillover" of a lineup is the sum of those neighbor effects over nine slots, in runs per 162
games, relative to every neighbor being right-handed. It contains no hitter's own talent.

This is a conditional expectation estimated from observed lineups, not a model of the opposing
manager. It is valid for arrangements like those teams actually use; three or more consecutive
lefties are rare in the data and are extrapolated by the additive form.
"""
from __future__ import annotations

import itertools
from math import comb

import numpy as np
import pandas as pd

from .model import FE, fit

TYPES = ["L", "R", "S"]
NB = ["p2L", "p1L", "n1L", "n2L", "n12"]
TERMS = [f"{t}_{n}" for t in TYPES for n in NB]


def design(d: pd.DataFrame) -> pd.DataFrame:
    x = d[d.slot_stype.isin(TYPES) & d.relief & ~d.has_P & d.pen_lhp_c.notna()
          & d.next1_q.notna() & d.next2_q.notna()].copy()
    base = {"p2L": x.prev2L, "p1L": x.prev1L, "n1L": x.next1L, "n2L": x.next2L, "n12": x.next1L * x.next2L}
    for t in TYPES:
        own = (x.slot_stype == t).astype(np.int8)
        for n, v in base.items():
            x[f"{t}_{n}"] = own * v
    return x


def estimate(x: pd.DataFrame, outcome: str = "e2"):
    m = fit(f"{outcome} ~ {' + '.join(TERMS)} + next1_q + next2_q + pen_lhp_c | {FE}", x)
    names = list(m._coefnames)
    idx = [names.index(t) for t in TERMS]
    beta = pd.Series(np.asarray(m.coef())[idx], index=TERMS)
    vcov = pd.DataFrame(np.asarray(m._vcov)[np.ix_(idx, idx)], index=TERMS, columns=TERMS)
    return beta, vcov, m


def loadings(own: np.ndarray, pL: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Coefficient loadings of lineup spillover. own: (...,9,3) type weights; pL: (...,9) chance
    each slot is a lefty; w: (9,) runs per unit of wOBA for each slot. Returns (...,15)."""
    r = lambda k: np.roll(pL, -k, axis=-1)                 # value at slot i+k
    nb = np.stack([r(-2), r(-1), r(1), r(2), r(1) * r(2)], axis=-1)       # (...,9,5)
    lo = own[..., :, :, None] * nb[..., :, None, :] * w[:, None, None]     # (...,9,3,5)
    return lo.sum(axis=-3).reshape(*lo.shape[:-3], 15)


def onehot(types: str):
    own = np.array([[t == k for k in TYPES] for t in types], dtype=float)
    return own, own[:, 0].copy()


def spillover(types: str, beta: pd.Series, w: np.ndarray) -> float:
    own, pL = onehot(types)
    return float(loadings(own, pL, w) @ beta.to_numpy())


_MASKS = np.array(list(itertools.product([0, 1], repeat=9)), dtype=float)      # 512 coalitions


def shapley(types: str, beta: pd.Series, w: np.ndarray, q: np.ndarray) -> np.ndarray:
    """Exact Shapley split of a lineup's spillover among its nine hitters. A hitter outside the
    coalition is replaced by a draw from the league mix of types q = (L, R, S)."""
    own1, pL1 = onehot(types)
    m = _MASKS
    own = m[:, :, None] * own1[None] + (1 - m[:, :, None]) * q[None, None, :]
    pL = m * pL1[None] + (1 - m) * q[0]
    v = loadings(own, pL, w) @ beta.to_numpy()                                  # (512,)
    size = m.sum(1).astype(int)
    key = (m @ (2 ** np.arange(8, -1, -1))).astype(int)                         # index of each mask
    phi = np.zeros(9)
    for i in range(9):
        without = m[:, i] == 0
        k_with = key[without] + 2 ** (8 - i)
        wt = np.array([1 / (9 * comb(8, s)) for s in size[without]])
        phi[i] = np.sum(wt * (v[k_with] - v[key[without]]))
    return phi
