from zola.fdco import match_name, norm

TEAMS = ["Man United", "Man City", "Nott'm Forest", "Wolves", "Brighton", "Tottenham", "Newcastle", "West Ham",
         "Ath Madrid", "Betis", "Sociedad", "Bayern Munich", "M'gladbach", "Paris SG", "Inter", "Milan"]


def test_names():
    assert match_name("Manchester United", TEAMS) == "Man United"
    assert match_name("Nottingham Forest", TEAMS) == "Nott'm Forest"
    assert match_name("Brighton & Hove Albion", TEAMS) == "Brighton"
    assert match_name("Atletico Madrid", TEAMS) == "Ath Madrid"
    assert match_name("Bayern München", TEAMS) == "Bayern Munich"
    assert match_name("Borussia Mönchengladbach", TEAMS) == "M'gladbach"
    assert match_name("Paris Saint Germain", TEAMS) == "Paris SG"
    assert match_name("Tottenham Hotspur", TEAMS) == "Tottenham"
    assert match_name("Real Madrid", TEAMS) is None
