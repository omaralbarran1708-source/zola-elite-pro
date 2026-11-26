import csv
import io
from datetime import date, timedelta

import numpy as np

from zola.backtest import parse_csv, run_backtest
from zola.model import score_matrix


def synthetic_csv(seed=7, new_format=False):
    rng = np.random.default_rng(seed)
    teams = [f"Team{i:02d}" for i in range(20)]
    strength = {t: float(np.exp(rng.normal(0, 0.3))) for t in teams}
    rows = []
    d = date(2025, 8, 9)
    pairs = [(h, a) for h in teams for a in teams if h != a]
    rng.shuffle(pairs)
    for k, (h, a) in enumerate(pairs):
        lh = 1.15 * 1.25 * strength[h] / strength[a] ** 0.8
        la = 1.15 * strength[a] / strength[h] ** 0.8
        m = score_matrix(lh, la, -0.08)
        i, j = np.indices(m.shape)
        p = [m[i > j].sum(), m[i == j].sum(), m[i < j].sum()]
        odds = [round(1 / (x * 1.05), 2) for x in p]
        hg, ag = int(rng.poisson(lh)), int(rng.poisson(la))
        day = d + timedelta(days=(k // 10) * 7)
        rows.append([day.strftime("%d/%m/%Y"), h, a, hg, ag, *odds])
    out = io.StringIO()
    w = csv.writer(out)
    if new_format:
        w.writerow(["Country", "League", "Season", "Date", "Time", "Home", "Away", "HG", "AG", "Res", "PSCH", "PSCD", "PSCA"])
        for r in rows:
            w.writerow(["Brazil", "Serie A", "2025", r[0], "20:00", r[1], r[2], r[3], r[4], "H", *r[5:]])
    else:
        w.writerow(["Div", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "B365H", "B365D", "B365A"])
        for r in rows:
            w.writerow(["E0", *r])
    return out.getvalue()


def test_parse_both_formats():
    a = parse_csv(synthetic_csv())
    b = parse_csv(synthetic_csv(new_format=True), season="2025")
    assert len(a) == len(b) == 380
    assert a[0]["odds"] and a[0]["odds_src"] == "B365"
    assert b[0]["odds_src"] == "PSC"
    assert parse_csv(synthetic_csv(new_format=True), season="2019") == []


def test_backtest_beats_baseline():
    res = run_backtest(parse_csv(synthetic_csv()))
    s = res["systems"]
    assert res["evaluated"] > 200
    assert s["model"]["logloss"] < s["base"]["logloss"]
    assert s["market"]["accuracy"] > 0.4
    assert res["calibration"] and res["sample"]
    assert res["betting"]["blend"]["bets"] >= 0
