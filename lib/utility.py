from lib.player_base import Player, PlayerShip

def posToIndex(x,y):
    return x * Player.FIELD_SIZE + y