from datetime import date, timedelta
import random

from zola import history
from zola.history import INSERT


def _season(st, code, season, teams, start):
    rnd = random.Random(1)
    rows = []
    d = start
    for h in teams:
        for a in teams:
            if h != a:
                d += timedelta(days=1)
                hg = 5 if teams[0] in (h, a) and h == teams[0] else rnd.randint(0, 2)
                rows.append((code, season, d.isoformat(), h, a, hg, (5 if a == teams[0] else rnd.randint(0, 2)), 2.1, 3.3, 3.6, None))
    st.xmany(INSERT, rows)


def test_past_seasons_and_h2h(tmp_store):
    teams = ["Man City", "Arsenal", "Liverpool", "Chelsea", "Spurs", "Everton", "Fulham", "Wolves"]
    _season(tmp_store, "E0", "2026/27", teams, date(2026, 8, 1))
    _season(tmp_store, "E0", "2025/26", teams, date(2025, 8, 1))
    ps = history.past_seasons(39)
    assert ps and ps[0]["season"] == "2025/26" and ps[0]["champion"]["team"] == "Man City"
    hh = history.h2h(39, "Manchester City", "Arsenal")
    assert hh and {hh[0]["home"], hh[0]["away"]} == {"Manchester City", "Arsenal"}


def test_national_lambdas(tmp_store):
    teams = ["Argentina", "Brazil", "Peru", "Chile", "Uruguay", "Colombia", "Ecuador", "Paraguay"]
    rnd = random.Random(2)
    rows, d = [], date(date.today().year - 2, 1, 1)
    for k in range(4):
        for h in teams:
            for a in teams:
                if h != a:
                    d += timedelta(days=1)
                    strong = {"Argentina": 2, "Brazil": 2}.get(h, 0)
                    rows.append(("INT", str(d.year), d.isoformat(), h, a, rnd.randint(0, 2) + strong // 2, rnd.randint(0, 2), None, None, None, "Friendly"))
    tmp_store.xmany(INSERT, rows)
    history._INT_CACHE.clear()
    (lh, la), rho, n = history.national_lambdas("Argentina", "Peru")
    assert lh > la and n >= 200
