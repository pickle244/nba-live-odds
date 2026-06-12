from app.services.features_service import FeatureIngester
from app.services.utility import get_game_pbp

if __name__ == '__main__':
    fi = FeatureIngester()
    home_players = fi.get_home_players('0022501187')
    print(f'Home roster: {home_players}')
    pbp = get_game_pbp('0022501187')
    for action in pbp[:50]:
        print(f'Seconds left: {action.seconds_remaining} | Description: {action.description}')
    # descriptions = [
    #     'Riley S.FOUL (P1.T1) (I.Hwang)',
    #     'Carrington P.FOUL (P1.T2) (S.Foster)',
    #     'Watkins AWAY.FROM.PLAY.FOUL (P1.T3) (B.Forte)',
    #     'Champagnie Offensive Foul Turnover (P1.T1)',
    #     'Nance Jr. S.FOUL (P1.T1) (I.Hwang)'
    # ]

    # for desc in descriptions:
    #     fouls_dict = fi.parse_fouls(desc, home_players)
    #     print(f'Fouls state: {fouls_dict}')