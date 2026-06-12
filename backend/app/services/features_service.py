from app.db.database import SessionLocal, FeatureSnapshot, Game
from nba_api.stats.endpoints import BoxScoreTraditionalV3
from app.services.utility import get_game_pbp, latest_elo
import re

class FeatureIngester:
    def __init__(self, game_id):
        self.game_id = game_id
        team_info = self.team_info()
        self.home_name = team_info['home_name']
        self.home_tri = team_info['home_tri']
        self.home_roster = team_info['home_roster']
        self.away_tri = team_info['away_tri']

    def team_info(self) -> dict:
        try:
            box = BoxScoreTraditionalV3(game_id=self.game_id).get_dict()
            home_team = box["boxScoreTraditional"]["homeTeam"]
            home_name = home_team['teamName']
            home_tri = home_team['teamTricode']
            players = home_team["players"]
            away_team = box["boxScoreTraditional"]["awayTeam"]
            away_tri = away_team['teamTricode']
            # print(f'home: {home_tri} | away: {away_tri}')
            home_roster = {p["familyName"] for p in players}
            return {
                'home_name': home_name,
                'home_tri': home_tri,
                'home_roster': home_roster,
                'away_tri': away_tri
            }
        except Exception as e:
            print(f"Roster fetch error: {e}")
            return "", set(), ""
        
    def infer_possession(self, desc: str) -> bool | None:
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
            possession_home = tip_player in self.home_roster

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
            possession_home = self.home_name.lower() in team.lower()

        # --- Player rebound ---
        elif "REBOUND" in d:
            player = d.split()[0]
            possession_home = player in self.home_roster

        # --- Made shot: other team gets possession ---
        elif any(x in d for x in ["Jump Shot", "Layup", "Dunk", "Hook Shot", "Finger Roll", "Floating", "Tip Shot"]):
            shooter = d.split()[0]
            possession_home = shooter not in self.home_roster

        # --- Free throw: only flip on final FT ---
        elif "Free Throw" in d and not d.startswith("MISS"):
            shooter = d.split()[0]
            if any(x in d for x in ["1 of 1", "2 of 2", "3 of 3"]):
                # Final FT made — other team inbounds
                possession_home = shooter not in self.home_roster
            else:
                # Intermediate FT (1 of 2) — shooter's team still has possession
                possession_home = shooter in self.home_roster

        # --- Turnover ---
        elif "Turnover" in d:
            player = d.split()[0]
            possession_home = player not in self.home_roster

        # --- Steal ---
        elif "STEAL" in d:
            player = d.split()[0]
            possession_home = player in self.home_roster

        # --- Foul: next events will be free throws for the fouled player ---
        elif "FOUL" in d:
            # The fouling player loses possession — other team shoots FTs
            fouler = d.split()[0]
            possession_home = fouler not in self.home_roster  # fouled team shoots

        return possession_home

    def parse_fouls(self, desc: str, home_fouls: int, away_fouls: int) -> dict:
        """
        Parse foul-related features from play-by-play descriptions.
        Returns a list of dicts with foul state after each event.
        """
        d = desc.strip()

        if "FOUL" in d:
            player = d.split()[0]
            is_home = player in self.home_roster

            # Extract team foul count from (Px.Ty) pattern
            # PN means penalty (bonus) — treat as high number
            # match = re.search(r'\(P\d+\.T(\d+|PN)\)', d)
            match = re.search(r'\(P(\d+)\.(T(\d+)|PN)\)', d)
            if match:
                personal_foul_count = int(match.group(1))
                team_foul_str = match.group(3) if match.group(3) else "PN"
                team_foul_count = 99 if team_foul_str == "PN" else int(team_foul_str)
                # print(f"player: {d.split()[0]}, is_home: {is_home}, team_foul_count: {team_foul_count}")

                if is_home:
                    home_fouls = team_foul_count
                else:
                    away_fouls = team_foul_count

        return {
            "home_fouls": home_fouls,
            "away_fouls": away_fouls,
            "home_in_bonus": home_fouls >= 5,   # bonus at 5, double bonus at 10
            "away_in_bonus": away_fouls >= 5
        }
    
    def parse_timeouts(self, desc: str, home_timeouts: int, away_timeouts: int) -> dict:
        """
        Parse timeout remaining counts from play-by-play descriptions.
        home_team_name: e.g. "WARRIORS" or "Warriors" — matched case-insensitively
        """
        # NBA starts with 7 full timeouts per game (changed to 6 in 2023, verify for your seasons)
        d = desc.strip()

        # Determine which team called the timeout
        is_home = d.upper().startswith(self.home_name.upper())

        # Format 1: "Full X Short X"
        match = re.search(r'Full\s+(\d+)\s+Short\s+(\d+)', d, re.IGNORECASE)
        if match:
            full = int(match.group(1))
            if is_home:
                home_timeouts = 7 - full
            else:
                away_timeouts = 7 - full

        # Format 2: "Reg.X Short X"
        else:
            match = re.search(r'Reg\.(\d+)\s+Short\s+(\d+)', d, re.IGNORECASE)
            if match:
                full = int(match.group(1))
                if is_home:
                    home_timeouts = 7 - full
                else:
                    away_timeouts = 7 - full
        # print(f"match: {match}")
        return {
            "home_timeouts": home_timeouts,
            "away_timeouts": away_timeouts,
        }
    
    def create_snapshots(self, events, game):
        snapshots = []

        home_elo = latest_elo(self.home_tri, game.game_date)
        away_elo = latest_elo(self.away_tri, game.game_date)
        if home_elo is None or away_elo is None:
            return []
        elo_diff = home_elo - away_elo
        home_win = (game.winner == self.home_tri)
        home_fouls = 0
        away_fouls = 0
        home_timeouts = 7
        away_timeouts = 7
        home_possession = None
        for j, event in enumerate(events):
            score_diff = (event.home_score - event.away_score)
            seconds_remaining = event.seconds_remaining
            desc = event.description
            
            new_possession = self.infer_possession(desc)
            if new_possession is not None:
                home_possession = new_possession
            fouls_dict = self.parse_fouls(desc, home_fouls, away_fouls)
            home_fouls = fouls_dict["home_fouls"]
            away_fouls = fouls_dict["away_fouls"]
            home_in_bonus = fouls_dict['home_in_bonus']
            away_in_bonus = fouls_dict['away_in_bonus']
            timeouts_dict = self.parse_timeouts(desc, home_timeouts, away_timeouts)
            home_timeouts = timeouts_dict["home_timeouts"]
            away_timeouts = timeouts_dict["away_timeouts"]
            # print(f'timeouts - home: {home_timeouts} | away: {away_timeouts}')

            window_seconds = event.seconds_remaining + 120
            home_points_last_2min = 0
            away_points_last_2min = 0
            # print(len(list(reversed(events[:j]))))
            for prev in reversed(events[:j]):
                prev_seconds = prev.seconds_remaining
                home_points_last_2min = event.home_score - prev.home_score
                away_points_last_2min = event.away_score - prev.away_score
                if prev_seconds > window_seconds:
                    break
            else:
                # All previous events are within the window — diff against the first event
                if j > 0:
                    home_points_last_2min = event.home_score - events[0].home_score
                    away_points_last_2min = event.away_score - events[0].away_score
                
            # print(f'Seconds left: {seconds_remaining} | Score: {event.home_score} - {event.away_score}')
            # print(f'Points last 2 min: home - {home_points_last_2min} | away - {away_points_last_2min}')
            # print(f'Fouls - home: {home_fouls} | away: {away_fouls}')
            # print(f'in bonus - home: {home_in_bonus} | away: {away_in_bonus}')
            snapshot = FeatureSnapshot(
                game_id=self.game_id,
                seconds_remaining=seconds_remaining,
                score_diff=score_diff,
                elo_diff=elo_diff,
                home_possession=home_possession,
                home_fouls=home_fouls,
                away_fouls=away_fouls,
                home_in_bonus=home_in_bonus,
                away_in_bonus=away_in_bonus,
                home_timeouts=home_timeouts,
                away_timeouts=away_timeouts,
                home_points_last_2min=home_points_last_2min,
                away_points_last_2min=away_points_last_2min,
                home_win=home_win
            )

            snapshots.append(snapshot)
        return snapshots

    def store_features(self):
        session = SessionLocal()
        existing = (
            session.query(FeatureSnapshot)
            .filter(FeatureSnapshot.game_id == self.game_id)
            .first()
        )

        if existing:
            print(f"Skipping already ingested game {self.game_id}")
            return
        
        game = (
            session.query(Game)
            .filter(Game.id == self.game_id)
            .first()
        )
        events = get_game_pbp(game.id)

        snapshots = self.create_snapshots(events, game)
        session.bulk_save_objects(snapshots)

        session.commit()

        # check = session.query(FeatureSnapshot).filter_by(game_id=self.game_id).first()
        # print(f"DB: home_fouls={check.home_fouls} home_timeouts={check.home_timeouts}")
        session.close()
