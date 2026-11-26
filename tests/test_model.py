import numpy as np
import pytest

from zola.api import normalize_fixture, normalize_team_stats, parse_live_odds, parse_prematch_odds
from zola.data import build_state, filter_matches
from zola.db import History, market_won
from zola.model import LiveState, TeamForm, final_score_matrix, predict, score_matrix
from zola import demo

STRONG = TeamForm(2.4, 0.6, 10, 1.9, 0.9, 10, "WWWWW")
WEAK = TeamForm(0.8, 1.9, 10, 0.5, 2.3, 10, "LLDLL")


def test_matrix_sums_to_one():
    assert score_matrix(1.4, 1.1).sum() == pytest.approx(1.0)


def test_probabilities_sum_to_one():
    p = predict("A", "B", STRONG, WEAK)
    assert p.home_win + p.draw + p.away_win == pytest.approx(1.0, abs=1e-6)


def test_strong_home_is_favourite():
    p = predict("A", "B", STRONG, WEAK)
    assert p.winner == "A" and p.home_win > 0.6


def test_teams_differ_with_real_data():
    """El bug original: todos los equipos sin datos daban lo mismo."""
    a = predict("A", "B", STRONG, WEAK)
    b = predict("C", "D", WEAK, STRONG)
    assert a.home_win != pytest.approx(b.home_win, abs=0.05)


def test_no_data_falls_back_and_flags():
    p = predict("A", "B", TeamForm(), TeamForm())
    assert p.confidence == "Baja"
    assert "promedio de liga" in p.data_quality.lower()


def test_live_leader_late_is_big_favourite():
    st = LiveState(minute=85, status="2H", home_goals=2, away_goals=0)
    p = predict("A", "B", TeamForm(), TeamForm(), st)
    assert p.home_win > 0.95
    # el marcador final nunca puede ser menor al actual
    i, j = np.indices((11, 11))
    m = final_score_matrix(0.2, 0.2, st)
    assert m[(i < 2) | (j < 0)].sum() == pytest.approx(0)


def test_finished_match_is_certain():
    st = LiveState(minute=90, status="FT", home_goals=1, away_goals=3)
    p = predict("A", "B", STRONG, WEAK, st)
    assert p.away_win == pytest.approx(1.0) and p.best_score == "1-3" and p.best_bet is None


def test_red_card_lowers_team_chances():
    base = LiveState(minute=30, status="1H")
    red = LiveState(minute=30, status="1H", home_red=1)
    assert predict("A", "B", STRONG, STRONG, red).home_win < predict("A", "B", STRONG, STRONG, base).home_win


def test_value_bet_detected():
    p = predict("A", "B", STRONG, WEAK, odds={"1": 2.5, "X": 3.5, "2": 3.0})
    assert p.best_bet and p.best_bet["kind"] == "valor" and p.best_bet["market"] == "1"


def test_market_won():
    assert market_won("Over 2.5", 2, 1) and not market_won("BTTS Sí", 2, 0) and market_won("X2", 0, 0)


def test_history_dedup_and_settle(tmp_path):
    h = History(tmp_path / "h.db")
    m = dict(demo.MATCHES[1])
    p = predict(m["home"], m["away"], STRONG, WEAK, odds={"1": 2.5})
    assert h.save(m, p, p.best_bet) is True
    assert h.save(m, p, p.best_bet) is False  # sin duplicados en cada recarga
    assert h.settle(m["match_key"], 2, 0) == 1
    s = h.summary()
    assert s["hits"] == 1 and s["units"] == pytest.approx(1.5)


def test_live_label_not_for_finished():
    finished = [m for m in demo.MATCHES if m["status_short"] == "FT"]
    out = filter_matches(demo.MATCHES, "Todas", "", hide_finished=True)
    assert all(m not in out for m in finished)


def test_bucket_filters():
    peru = filter_matches(demo.MATCHES, "Sudamérica", "", False)
    assert any(m["home"] == "Alianza Lima" for m in peru)
    assert not any(m["league"] == "Premier League" for m in peru)
    assert filter_matches(demo.MATCHES, "Todas", "universitario")[0]["away"] == "Universitario"


def test_normalizers():
    fx = normalize_fixture({"fixture": {"id": 5, "status": {"short": "2H", "elapsed": 70}},
                            "league": {"id": 39, "name": "Premier League", "season": 2026},
                            "teams": {"home": {"id": 1, "name": "X"}, "away": {"id": 2, "name": "Y"}},
                            "goals": {"home": None, "away": 1}})
    assert fx["home_goals"] == 0 and fx["away_goals"] == 1 and fx["league_id"] == 39
    tf = normalize_team_stats([{"fixtures": {"played": {"home": 5, "away": 4}},
                                "goals": {"for": {"average": {"home": "2.0", "away": "1.5"}},
                                          "against": {"average": {"home": "0.8", "away": "1.1"}}},
                                "form": "WDW"}])
    assert tf.gf_home == 2.0 and tf.gp_away == 4 and tf.form == "WDW"
    pre = parse_prematch_odds([{"bookmakers": [{"bets": [
        {"name": "Match Winner", "values": [{"value": "Home", "odd": "1.80"}, {"value": "Draw", "odd": "3.4"}, {"value": "Away", "odd": "4.5"}]},
        {"name": "Goals Over/Under", "values": [{"value": "Over 2.5", "odd": "1.9"}]}]}]}])
    assert pre == {"1": 1.8, "X": 3.4, "2": 4.5, "Over 2.5": 1.9}
    live = parse_live_odds([{"odds": [{"name": "Over/Under", "values": [
        {"value": "Over", "handicap": "2.5", "odd": "2.1", "suspended": False},
        {"value": "Under", "handicap": "2.5", "odd": "1.7", "suspended": True}]}]}])
    assert live == {"Over 2.5": 2.1}


def test_red_cards_from_events():
    m = demo.MATCHES[2]
    st = build_state(m, demo.EVENTS[9003], demo.STATS[9003])
    assert st.away_red == 1 and st.home_red == 0


def test_logo_fallback_crest():
    from zola.logos import crest_svg, logo, _initials
    assert _initials("Sporting Cristal") == "SC" and _initials("Palmeiras") == "PAL"
    assert logo(None, "Alianza Lima").startswith("data:image/svg+xml")
    assert crest_svg("A") == crest_svg("A")


def test_ratings_fit_recovers_strength():
    import numpy as np
    from datetime import date, timedelta
    from zola.ratings import fit
    rng = np.random.default_rng(1)
    teams = ["A", "B", "C", "D", "E", "F"]
    att = {"A": 1.6, "B": 1.2, "C": 1.0, "D": 0.9, "E": 0.8, "F": 0.6}
    ms, d0 = [], date(2026, 1, 1)
    for k in range(6):
        for h in teams:
            for a in teams:
                if h != a:
                    lh, la = 1.2 * 1.25 * att[h] / att[a] ** 0.5, 1.2 * att[a] / att[h] ** 0.5
                    ms.append((d0 + timedelta(days=k * 30), h, a, int(rng.poisson(lh)), int(rng.poisson(la))))
    r = fit(ms)
    order = [x["team"] for x in r.table()]
    assert order[0] == "A" and "F" in order[-2:]
    assert 1.05 < r.home_adv < 1.5
    lh, la = r.lambdas("A", "F")
    assert lh > 2 * la


def test_market_blend_moves_toward_market():
    base = predict("A", "B", STRONG, WEAK, market_weight=0)
    odds = {"1": 3.0, "X": 3.2, "2": 2.4}
    bl = predict("A", "B", STRONG, WEAK, odds=odds)
    assert bl.home_win < base.home_win and bl.blend_weight > 0
    assert abs(bl.home_win + bl.draw + bl.away_win - 1) < 1e-9


def test_second_half_scores_more():
    from zola.model import _remaining_fraction
    assert _remaining_fraction(LiveState(minute=45, status="2H")) > 0.5


def test_real_path_uses_league_ratings(monkeypatch):
    import numpy as np
    from datetime import date, timedelta
    from zola.api import FootballApi
    from zola.data import match_detail
    api = FootballApi("x")
    rng = np.random.default_rng(3)
    teams = ["Alpha", "Beta", "Gamma", "Delta"]
    res = []
    for k in range(4):
        for h in teams:
            for a in teams:
                if h != a:
                    res.append({"date": date(2026, 8, 1) + timedelta(days=7 * k), "home": h, "away": a,
                                "hg": int(rng.poisson(1.5 if h == "Alpha" else 1.1)), "ag": int(rng.poisson(1.0))})
    monkeypatch.setattr(api, "league_results", lambda l, s: res)
    monkeypatch.setattr(api, "odds", lambda f: {"1": 1.8, "X": 3.6, "2": 4.5})
    called = []
    monkeypatch.setattr(api, "team_form", lambda *a: called.append(a))
    m = {"fixture_id": 1, "match_key": "af_1", "league_id": 39, "season": 2026, "home": "Alpha", "away": "Beta",
         "home_id": 1, "away_id": 2, "status_short": "NS", "minute": 0, "home_goals": 0, "away_goals": 0}
    d = match_detail(api, m)
    assert d.lambdas and d.source.startswith("Ratings") and not called
    assert d.ratings_info["teams"] == 4 and len(d.home_form.form) == 5
    p = predict("Alpha", "Beta", d.home_form, d.away_form, d.state, d.odds, lambdas=d.lambdas, rho=d.rho, source=d.source)
    assert p.blend_weight > 0 and p.market_1x2
