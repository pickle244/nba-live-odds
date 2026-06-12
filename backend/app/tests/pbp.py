from app.services.pbp_service import PlayByPlayIngester

if __name__ == '__main__':
    game_ids = [
        '0022501187',
        '0022501193'
    ]

    for id in game_ids:
        pbpi = PlayByPlayIngester(id)
        pbp_df = pbpi.find_game_pbp()
        for _, row in pbp_df.iterrows():
            event = pbpi.process_event(row)
            print(f'Seconds left: {event.seconds_remaining} | Score: {event.home_score} : {event.away_score} | Description: {event.description}')

    pbpi = PlayByPlayIngester('0022501187')
    pbpi.store_pbp()