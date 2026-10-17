"""Fictitious team definitions for synthetic match simulation."""

from typing import List
from omnipitch.generator.models import Player, Team


def create_fictitious_teams() -> List[Team]:
    """Generates 100% synthetic fictitious teams and rosters (compliant with Hackathon rules)."""

    avalon_players = [
        Player(player_id="AVA-01", name="Marcus Vance", number=1, position="GK", team_id="avalon_city"),
        Player(player_id="AVA-02", name="Leo Sterling", number=2, position="DEF", team_id="avalon_city"),
        Player(player_id="AVA-04", name="Tobias Thorne", number=4, position="DEF", team_id="avalon_city"),
        Player(player_id="AVA-05", name="Dorian Cole", number=5, position="DEF", team_id="avalon_city"),
        Player(player_id="AVA-03", name="Nico Lind", number=3, position="DEF", team_id="avalon_city"),
        Player(player_id="AVA-06", name="Mateo Rios", number=6, position="MID", team_id="avalon_city"),
        Player(player_id="AVA-08", name="Julian Drake", number=8, position="MID", team_id="avalon_city"),
        Player(player_id="AVA-10", name="Kaelen Cross", number=10, position="MID", team_id="avalon_city"),
        Player(player_id="AVA-07", name="Finneas Frost", number=7, position="FWD", team_id="avalon_city"),
        Player(player_id="AVA-09", name="Cyrus Kane", number=9, position="FWD", team_id="avalon_city"),
        Player(player_id="AVA-11", name="Bram Walker", number=11, position="FWD", team_id="avalon_city"),
    ]

    solaria_players = [
        Player(player_id="SOL-01", name="Rory Gallagher", number=1, position="GK", team_id="solaria_rovers"),
        Player(player_id="SOL-02", name="Axel Mercer", number=2, position="DEF", team_id="solaria_rovers"),
        Player(player_id="SOL-05", name="Hugo Bennett", number=5, position="DEF", team_id="solaria_rovers"),
        Player(player_id="SOL-06", name="Silas Brandt", number=6, position="DEF", team_id="solaria_rovers"),
        Player(player_id="SOL-03", name="Dante Morales", number=3, position="DEF", team_id="solaria_rovers"),
        Player(player_id="SOL-04", name="Jasper Holt", number=4, position="MID", team_id="solaria_rovers"),
        Player(player_id="SOL-08", name="Ezra Kim", number=8, position="MID", team_id="solaria_rovers"),
        Player(player_id="SOL-10", name="Zane Al-Mansoor", number=10, position="MID", team_id="solaria_rovers"),
        Player(player_id="SOL-07", name="Lucian Vega", number=7, position="FWD", team_id="solaria_rovers"),
        Player(player_id="SOL-09", name="Victor Sterling", number=9, position="FWD", team_id="solaria_rovers"),
        Player(player_id="SOL-11", name="Orion Price", number=11, position="FWD", team_id="solaria_rovers"),
    ]

    avalon = Team(
        team_id="avalon_city",
        name="Avalon City FC",
        short_name="AVA",
        primary_color="#00A3E0",  # Sky Blue
        secondary_color="#0C2340",  # Navy
        formation="4-3-3",
        players=avalon_players,
    )

    solaria = Team(
        team_id="solaria_rovers",
        name="Solaria Rovers",
        short_name="SOL",
        primary_color="#C8102E",  # Crimson
        secondary_color="#FFD100",  # Gold
        formation="4-3-3",
        players=solaria_players,
    )

    return [avalon, solaria]
