from zola.api import FootballApi, normalize_lineups
from zola import learn
from zola.model import LiveState, TeamForm, predict


def test_cache_and_fixtures(tmp_store):
    tmp_store.cache_put("k", [{"a": 1}])
    assert tmp_store.cache_get("k", 60) == [{"a": 1}]
    assert tmp_store.cache_get("k", -1) is None
    m = {"fixture_id": 5, "match_key": "af_5", "league_id": 39, "season": 2026, "kickoff": "2026-11-20T15:00:00-05:00",
         "home": "A", "away": "B", "home_goals": 2, "away_goals": 1, "status_short": "FT"}
    tmp_store.upsert_fixtures([m])
    assert tmp_store.league_results(39, 2026)[0]["hg"] == 2
    assert tmp_store.fixture(5)["home"] == "A"


def test_api_uses_persistent_cache_and_stale_fallback(tmp_store, monkeypatch):
    api = FootballApi("x")
    calls = []
    def fake(path, **p):
        calls.append(path)
        return [{"fixture": {"id": 9, "status": {"short": "NS"}}, "league": {"id": 39}, "teams": {"home": {"name": "A"}, "away": {"name": "B"}}, "goals": {}}]
    monkeypatch.setattr(api, "_get", fake)
    api.fixtures("2030-01-01", False)
    api2 = FootballApi("x")            # nueva instancia (como tras reiniciar): usa la base de datos
    monkeypatch.setattr(api2, "_get", fake)
    api2.fixtures("2030-01-01", False)
    assert len(calls) == 1
    from zola.api import ApiError
    def boom(path, **p):
        raise ApiError("caída")
    api3 = FootballApi("x"); monkeypatch.setattr(api3, "_get", boom)
    api3._mem.clear()
    assert api3._fetch("fixtures", 0, date="2030-01-01", timezone="America/Lima")  # dato viejo guardado


def test_learning_records_and_learns(tmp_store):
    strong = TeamForm(2.2, 0.7, 10, 1.6, 1.0, 10, "WWWDW")
    weak = TeamForm(0.9, 1.8, 10, 0.6, 2.1, 10, "LLDLL")
    for i in range(1, 46):
        m = {"fixture_id": i, "match_key": f"af_{i}", "league_id": 39, "season": 2026, "kickoff": "2026-11-01T15:00:00-05:00",
             "home": f"H{i}", "away": f"A{i}", "home_goals": 0, "away_goals": 0, "status_short": "NS"}
        p = predict(m["home"], m["away"], strong, weak, odds={"1": 2.6, "X": 3.3, "2": 2.8})
        learn.record(m, p, LiveState())
        tmp_store.upsert_fixtures([{**m, "home_goals": i % 3, "away_goals": 1, "status_short": "FT"}])
    ev = learn.evaluate()
    assert ev["n"] == 45 and "global" in ev["weights"]
    learn._cache["ts"] = 0
    assert 0.1 <= learn.learned_weight(39) <= 0.85


def test_lineups_normalizer():
    res = [{"team": {"name": "A", "id": 1, "colors": {"player": {"primary": "ff0000", "number": "ffffff"}}},
            "formation": "4-3-3", "coach": {"name": "X"},
            "startXI": [{"player": {"id": 1, "name": "P1", "number": 1, "pos": "G", "grid": "1:1"}}], "substitutes": []}]
    lu = normalize_lineups(res)
    assert lu[0]["color"] == "#ff0000" and lu[0]["start"][0]["grid"] == "1:1"
