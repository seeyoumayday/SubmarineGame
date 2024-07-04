import json
import os
import random
import socket
import sys

sys.path.append(os.getcwd())

from lib.player_base import Player, PlayerShip


class state1_player(Player):

    def __init__(self, seed=0):
        self.stage = 0;
        random.seed(seed)

        # フィールドを2x2の配列として持っている．
        self.field = [[i, j] for i in range(Player.FIELD_SIZE)
                      for j in range(Player.FIELD_SIZE)]
        
        # 相手の位置の予想。相手の行動と自分の行動で更新する。
        # 0：未確定　 -1:そのマスには相手の船がいない
        # 1:　そのマスには相手の船がいる可能性が高い 2:そのマスには確実にwがいる
        # 3: そのマスには確実にcがいる 4:そのマスには確実にsがいる
        self.opponent_field = [[i, j, 0] for i in range(Player.FIELD_SIZE)
                      for j in range(Player.FIELD_SIZE) for k in range(Player.FIELD_SIZE)]

        # 初期配置を非復元抽出でランダムに決める．
        #ps = random.sample(self.field, 3)
        positions = {'w': self.field[6], 'c': self.field[21], 's': self.field[4]}
        
        super().__init__(positions)

    #
    # 移動か攻撃かランダムに決める．
    # どれがどこへ移動するか，あるいはどこに攻撃するかもランダム．
    #
    def action(self):
        act = random.choice(["move", "attack"])

        if act == "move":
            ship = random.choice(list(self.ships.values()))
            to = random.choice(self.field)
            while not ship.can_reach(to) or not self.overlap(to) is None:
                to = random.choice(self.field)

            return json.dumps(self.move(ship.type, to))
        elif act == "attack":
            to = random.choice(self.field)
            while not self.can_attack(to):
                to = random.choice(self.field)

            return json.dumps(self.attack(to))


# 仕様に従ってサーバとソケット通信を行う．
def main(host, port, seed=0):
    assert isinstance(host, str) and isinstance(port, int)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        with sock.makefile(mode='rw', buffering=1) as sockfile:
            get_msg = sockfile.readline()
            print(get_msg)
            player = state1_player()
            sockfile.write(player.initial_condition()+'\n')

            while True:
                info = sockfile.readline().rstrip()
                print(info)
                if info == "your turn":
                    sockfile.write(player.action()+'\n')
                    get_msg = sockfile.readline()
                    player.update(get_msg)
                elif info == "waiting":
                    get_msg = sockfile.readline()
                    player.update(get_msg)
                elif info == "you win":
                    break
                elif info == "you lose":
                    break
                elif info == "even":
                    break
                else:
                    raise RuntimeError("unknown information")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Sample Player for Submaline Game")
    parser.add_argument(
        "host",
        metavar="H",
        type=str,
        help="Hostname of the server. E.g., localhost",
    )
    parser.add_argument(
        "port",
        metavar="P",
        type=int,
        help="Port of the server. E.g., 2000",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed of the player",
        required=False,
        default=0,
    )
    args = parser.parse_args()

    main(args.host, args.port, seed=args.seed)
