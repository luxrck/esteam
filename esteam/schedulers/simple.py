max_running_time = 20 * 60
check_cards_remains_interval = 5 * 60
# @games = {
#   id: @game,
#   ...
# }
# @game = {
#   cards_remain: int
#   played_time: int
#   name: str
# }
# calls per second. this should implement as a async-generator.
async def scheduler(games, steam):
    for g in games:
        await steam.games_played([g])
        maxt = max_running_time
        interval = check_cards_remains_interval
        while maxt >= 0:
            print("playing:", games[g]['name'], interval, maxt)
            if interval <= 0:
                if not (await steam.cards_remain(g)): break
                await steam.games_played([g])
                interval = check_cards_remains_interval
            maxt -= 1
            interval -=1
            yield True
    yield False
