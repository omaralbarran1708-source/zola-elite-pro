from zola import strength
from zola.model import score_matrix
import numpy as np


def test_implied_lambdas_roundtrip():
    m = score_matrix(1.8, 0.9)
    i, j = np.indices(m.shape)
    p = [m[i > j].sum(), m[i == j].sum(), m[i < j].sum()]
    po = m[(i + j) > 2].sum()
    odds = {"1": 1 / p[0], "X": 1 / p[1], "2": 1 / p[2], "Over 2.5": 1 / po, "Under 2.5": 1 / (1 - po)}
    lh, la = strength.implied_lambdas(odds)
    assert abs(lh - 1.8) < 0.11 and abs(la - 0.9) < 0.11


def test_elo_lambdas():
    lh, la = strength.elo_lambdas(1900, 1700)
    assert lh > la
    eq = strength.elo_lambdas(1700, 1765)
    assert abs(eq[0] - eq[1]) < 0.15
