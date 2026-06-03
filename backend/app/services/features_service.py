from app.db.database import SessionLocal, FeatureSnapshot, TeamEloRating
from nba_api.stats.endpoints import BoxScoreTraditionalV3
from app.services.utility import get_games, get_game_pbp
import re

class FeatureIngester:
    def __init__(self):
        self.home_rosters: dict[str, set[str]] = {}

    def get_home_players(self, game_id: str) -> set[str]:
        if game_id in self.home_rosters:
            return self.home_rosters[game_id]

        try:
            box = BoxScoreTraditionalV3(game_id=game_id).get_dict()
            players = box["boxScoreTraditional"]["homeTeam"]["players"]
            last_names = {p["familyName"] for p in players}
            self.home_rosters[game_id] = last_names
            return last_names
        except Exception as e:
            print(f"Roster fetch error: {e}")
            return set()
        
    def infer_possession(self, desc: str, home_team_players: set[str], home_team_name: str) -> bool | None:
        """
        Infer home team possession for each play-by-play event.
        home_team_players: set of last names or full names of home team players.
        Returns True = home has possession, False = away, None = unknown.
        """
        possession_home = None  # unknown until tip-off resolved
        d = desc.strip()

        # --- Period boundaries: reset possession ---
        if d.startswith("End of") or d.startswith("Start of"):
            possession_home = None

        # --- Tip-off / jump ball ---
        elif "Tip to" in d:
            tip_player = d.split("Tip to")[-1].strip().split()[0]
            possession_home = tip_player in home_team_players

        # --- Substitution: no possession change ---
        elif d.startswith("SUB:"):
            pass

        # --- Missed shot ---
        elif d.startswith("MISS"):
            pass  # possession unchanged, wait for rebound

        # --- Team rebound (no player name, e.g. "Clippers Rebound") ---
        elif "Rebound" in d and "REBOUND" not in d:
            # Format: "<Team Name> Rebound"
            team = d.replace("Rebound", "").strip()
            possession_home = home_team_name.lower() in team.lower()

        # --- Player rebound ---
        elif "REBOUND" in d:
            player = d.split()[0]
            possession_home = player in home_team_players

        # --- Made shot: other team gets possession ---
        elif any(x in d for x in ["Jump Shot", "Layup", "Dunk", "Hook Shot", "Finger Roll", "Floating", "Tip Shot"]):
            shooter = d.split()[0]
            possession_home = shooter not in home_team_players

        # --- Free throw: only flip on final FT ---
        elif "Free Throw" in d and not d.startswith("MISS"):
            shooter = d.split()[0]
            if any(x in d for x in ["1 of 1", "2 of 2", "3 of 3"]):
                # Final FT made — other team inbounds
                possession_home = shooter not in home_team_players
            else:
                # Intermediate FT (1 of 2) — shooter's team still has possession
                possession_home = shooter in home_team_players

        # --- Turnover ---
        elif "Turnover" in d:
            player = d.split()[0]
            possession_home = player not in home_team_players

        # --- Steal ---
        elif "STEAL" in d:
            player = d.split()[0]
            possession_home = player in home_team_players

        # --- Foul: next events will be free throws for the fouled player ---
        elif "FOUL" in d:
            # The fouling player loses possession — other team shoots FTs
            fouler = d.split()[0]
            possession_home = fouler not in home_team_players  # fouled team shoots

        return possession_home

    def parse_fouls(self, desc: str, home_players: set[str]) -> dict:
        """
        Parse foul-related features from play-by-play descriptions.
        Returns a list of dicts with foul state after each event.
        """
        home_team_fouls = 0
        away_team_fouls = 0
        
        d = desc.strip()

        if "FOUL" in d:
            player = d.split()[0]
            is_home = player in home_players

            # Extract team foul count from (Px.Ty) pattern
            # PN means penalty (bonus) — treat as high number
            match = re.search(r'\(P\d+\.T(\d+|PN)\)', d)
            if match:
                team_foul_str = match.group(1)
                team_foul_count = 99 if team_foul_str == "PN" else int(team_foul_str)

                if is_home:
                    home_team_fouls = team_foul_count
                else:
                    away_team_fouls = team_foul_count

        return {
            "home_team_fouls": home_team_fouls,
            "away_team_fouls": away_team_fouls,
            "home_in_bonus": home_team_fouls >= 5,   # bonus at 5, double bonus at 10
            "away_in_bonus": away_team_fouls >= 5,
            "home_in_double_bonus": home_team_fouls >= 10,
            "away_in_double_bonus": away_team_fouls >= 10,
        }
    
    def parse_timeouts(self, desc: str, home_team_name: str) -> dict:
        """
        Parse timeout remaining counts from play-by-play descriptions.
        home_team_name: e.g. "WARRIORS" or "Warriors" — matched case-insensitively
        """
        # NBA starts with 7 full timeouts per game (changed to 6 in 2023, verify for your seasons)
        home_full = 7
        away_full = 7
        home_short = 2
        away_short = 2
        d = desc.strip()

        # Determine which team called the timeout
        is_home = d.upper().startswith(home_team_name.upper())

        # Format 1: "Full X Short X"
        match = re.search(r'Full\s+(\d+)\s+Short\s+(\d+)', d, re.IGNORECASE)
        if match:
            full = int(match.group(1))
            short = int(match.group(2))
            if is_home:
                home_full = full
                home_short = short
            else:
                away_full = full
                away_short = short

        # Format 2: "Reg.X Short X"
        else:
            match = re.search(r'Reg\.(\d+)\s+Short\s+(\d+)', d, re.IGNORECASE)
            if match:
                full = int(match.group(1))
                short = int(match.group(2))
                if is_home:
                    home_full = full
                    home_short = short
                else:
                    away_full = full
                    away_short = short

        return {
            "home_full_timeouts": home_full,
            "away_full_timeouts": away_full,
            "home_short_timeouts": home_short,
            "away_short_timeouts": away_short,
        }

    def store_features(self):
        games = get_games()
        session = SessionLocal()

        for i, game in enumerate(games):
            game_id = game.id
            
            existing = (
                session.query(FeatureSnapshot)
                .filter(FeatureSnapshot.game_id == game_id)
                .first()
            )

            if existing:
                print(f"Skipping already ingested game {game_id}")
                continue
            
            home_team = game.home_team
            game_date = game.game_date

            home_win = (game.winner == home_team)
            
            home_elo = (
                session.query(TeamEloRating.elo_rating)
                .where(
                    TeamEloRating.team == home_team,
                    TeamEloRating.rating_date <= game_date
                )
                .order_by(
                    TeamEloRating.rating_date.desc()
                )
                .limit(1)
                .scalar()
            )

            away_elo = (
                session.query(TeamEloRating.elo_rating)
                .where(
                    TeamEloRating.team == game.away_team,
                    TeamEloRating.rating_date <= game_date
                )
                .order_by(
                    TeamEloRating.rating_date.desc()
                )
                .limit(1)
                .scalar()
            )

            elo_diff = home_elo - away_elo

            home_roster = self.get_home_players(game_id)

            events = get_game_pbp(game.id)

            snapshots = []

            for j, event in enumerate(events):
                score_diff = (event.home_score - event.away_score)

                seconds_remaining = (
                    (4 - event.period) * 720
                    + event.seconds_remaining
                )

                desc = event.description
                
                home_possession = self.infer_possession(
                    desc, 
                    home_roster, 
                    home_team
                )

                fouls_dict = self.parse_fouls(desc, home_roster)

                timeouts_dict = self.parse_timeouts(desc, home_team)

                window_seconds = seconds_remaining + 120
                home_points_last_2min = 0
                away_points_last_2min = 0
                for prev in reversed(events[:j]):
                    home_points_last_2min = event.home_score - prev.home_score
                    away_points_last_2min = event.away_score - prev.away_score
                    prev_seconds = (4 - prev.period) * 720 + prev.seconds_remaining
                    if prev_seconds > window_seconds:
                        break

                snapshot = FeatureSnapshot(
                    game_id=game_id,
                    seconds_remaining=seconds_remaining,
                    score_diff=score_diff,
                    elo_diff=elo_diff,
                    home_has_possession=home_possession,
                    home_team_fouls=fouls_dict['home_team_fouls'],
                    away_team_fouls=fouls_dict['away_team_fouls'],
                    home_in_bonus=fouls_dict['home_in_bonus'],
                    away_in_bonus=fouls_dict['away_in_bonus'],
                    home_in_double_bonus=fouls_dict['home_in_double_bonus'],
                    away_in_double_bonus=fouls_dict['away_in_double_bonus'],
                    home_full_timeouts=timeouts_dict['home_full_timeouts'],
                    away_full_timeouts=timeouts_dict['away_full_timeouts'],
                    home_short_timeouts=timeouts_dict['home_short_timeouts'],
                    away_short_timeouts=timeouts_dict['away_short_timeouts'],
                    home_points_last_2min=home_points_last_2min,
                    away_points_last_2min=away_points_last_2min,
                    home_win=home_win
                )

                snapshots.append(snapshot)
            session.bulk_save_objects(snapshots)

            session.commit()
            print(f'Features for game {game_id} ingested ({i + 1} / {len(games)})')
        session.close()
