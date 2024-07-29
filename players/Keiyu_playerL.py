import json
import os
import random
import socket
import sys

sys.path.append(os.getcwd())

from lib.player_base import Player, PlayerShip
from lib.utility import posToIndex


class KeiyuPlayer(Player):

    def __init__(self):

        self.turn = 0
        self.countShip = 3
        self.isEmergency = [False,False,False]

        # フィールドを2x2の配列として持っている．
        self.field = [[i, j] for i in range(Player.FIELD_SIZE)
                      for j in range(Player.FIELD_SIZE)]
        
        # 自分が予想する相手の船の位置。自分と相手の行動で更新する。
        # 優先度は以下の通り
        # -１：そのマスには確実に相手の船はいない
        # ０：未確定
        # １：何かしらの船がいる可能性がある
        # 2：wが確実にいる
        # ３：cが確実にいる
        # ４：sが確実にいる
        self.opponentsPlacementExpectedByMe = [[i, j, 0] for i in range(Player.FIELD_SIZE)
                      for j in range(Player.FIELD_SIZE)]
        
        # 相手から予想されている自分の船の位置。自分と相手の行動で更新する。
        self.myPlacementExpectedByOpponent = [[i, j, 0] for i in range(Player.FIELD_SIZE) 
                                              for j in range(Player.FIELD_SIZE)]

        # 初期配置を以下の４つ（それぞれ９０度ずつ回転している）からランダムに選ぶ；
        positions1 = {'w': self.field[6], 'c': self.field[21], 's': self.field[4]}
        positions2 = {'w': self.field[8], 'c': self.field[5], 's': self.field[24]}
        positions3 = {'w': self.field[18], 'c': self.field[3], 's': self.field[20]}
        positions4 = {'w': self.field[16], 'c': self.field[23], 's': self.field[0]}
        positions = random.choice([positions1, positions2, positions3, positions4])
        super().__init__(positions)


    def action(self):
        act = self.chooseAction()

        # isEmergencyがTrueの場合はrunを選ぶ
        if act == "run":
            # ship = random.choice(list(self.ships.values()))
            if self.isEmergency[0]:
                ship = self.ships['w']
            elif self.isEmergency[1]:
                ship = self.ships['c']
            elif self.isEmergency[2]:
                ship = self.ships['s']
            self.isEmergency = [False,False,False]
            #行ける場所にランダムに逃げる
            to = random.choice(self.field)
            while not ship.can_reach(to) or not self.overlap(to) is None:
                to = random.choice(self.field)
            return json.dumps(self.move(ship.type, to))
        
        elif act == "move":
            ship = random.choice(list(self.ships.values()))
            to = random.choice(self.field)
            while not ship.can_reach(to) or not self.overlap(to) is None:
                to = random.choice(self.field)
            return json.dumps(self.move(ship.type, to))            

        elif act == "attack":
            to = random.choice(self.field)
            while not self.can_attack(to):
                to = random.choice(self.field)
            to = self.chooseTarget()
            return json.dumps(self.attack(to))
    
    # 自分が攻撃することができるマスの数を返す
    def countAttackable(self):
        count = 0
        for i in range(Player.FIELD_SIZE):
            for j in range(Player.FIELD_SIZE):
                if self.can_attack([i,j]):
                    count += 1
        return count

    # 逃走は、前のターン、残り体力１の船の近傍に攻撃された場合に行う
    # 移動は、残りの自分の船の数に対して自分が攻撃できるマスがあまりに少ない時に移動する
    def chooseAction(self):
        if self.isEmergency[0] or self.isEmergency[1] or self.isEmergency[2]:
            return "run"
        elif (self.countShip == 3 and self.countAttackable() <= 12)\
            or (self.countShip == 2 and self.countAttackable() <= 12):
            return "move"       
        else:
            return "attack"
    
    def chooseTarget(self):
        #まずは攻撃することができるマスをリストアップ
        attackable = []
        for i in range(Player.FIELD_SIZE):
            for j in range(Player.FIELD_SIZE):
                if self.can_attack([i,j]):
                    attackable.append(posToIndex(i,j))    
        #攻撃できるマスの中で一番優先度の高いマスを選ぶ
        # まずは一番優先度の高いマスの優先度を知る
        MaxPriority = -1
        for i in range(len(attackable)):
            if self.opponentsPlacementExpectedByMe[attackable[i]][2] > MaxPriority:
                MaxPriority = self.opponentsPlacementExpectedByMe[attackable[i]][2]

        # 一番優先度の高いマスをリストアップ
        PlacesHaveMaxPriority = []
        for i in range(len(attackable)):
            if self.opponentsPlacementExpectedByMe[attackable[i]][2] == MaxPriority:
                PlacesHaveMaxPriority.append(attackable[i])
        return self.field[random.choice(PlacesHaveMaxPriority)]

    def update_ExpectationOfOpponentsPlacement_afterMyAction(self,json_):
        if "result" in json.loads(json_):
            res = json.loads(json_)['result']
            # 自分が攻撃した時の処理
            if ("attacked" in res):
                attacked = res['attacked']
                pos = attacked['position']
                if("hit" in attacked):
                    hit = attacked['hit']
                    if(hit == "w"):
                        self.opponentsPlacementExpectedByMe[posToIndex(*pos)][2] = 2
                    elif(hit == "c"):
                        self.opponentsPlacementExpectedByMe[posToIndex(*pos)][2] = 3
                    elif(hit == "s"):
                        self.opponentsPlacementExpectedByMe[posToIndex(*pos)][2] = 4
                elif ("near" in attacked):
                    for i in range(len(attacked['near'])):
                        # positionの周りの8近傍を1にする
                        # ただし、すでに2,3,4が入っている場合はスルー
                        #　かつ、フィールド場外になる場合もスルー
                        probable = []
                        dx = [1,1,0,-1,-1,-1,0,1]
                        dy = [0,1,1,1,0,-1,-1,-1]
                        for j in range(8):
                            position = [pos[0]+dx[j],pos[1]+dy[j]]
                            if 0 <= position[0] < Player.FIELD_SIZE \
                                and 0 <= position[1] < Player.FIELD_SIZE:
                                probable.append(posToIndex(position[0],position[1]))
                        for nearPos in probable:
                            if self.opponentsPlacementExpectedByMe[nearPos][2] < 2:
                                self.opponentsPlacementExpectedByMe[nearPos][2] = 1
            # 相手の機体が死んだら、そのマスを-1にする
            if "condition" in json.loads(json_):
                condition = json.loads(json_)['condition']
                enemy_ships = condition["enemy"]
                if not "w" in enemy_ships:
                    for i in range(Player.FIELD_SIZE):
                        for j in range(Player.FIELD_SIZE):
                            if self.opponentsPlacementExpectedByMe[posToIndex(i,j)][2] == 2:
                                self.opponentsPlacementExpectedByMe[posToIndex(i,j)][2] = -1
                if not "c" in enemy_ships:
                    for i in range(Player.FIELD_SIZE):
                        for j in range(Player.FIELD_SIZE):
                            if self.opponentsPlacementExpectedByMe[posToIndex(i,j)][2] == 3:
                                self.opponentsPlacementExpectedByMe[posToIndex(i,j)][2] = -1
                if not "s" in enemy_ships:
                    for i in range(Player.FIELD_SIZE):
                        for j in range(Player.FIELD_SIZE):
                            if self.opponentsPlacementExpectedByMe[posToIndex(i,j)][2] == 4:
                                self.opponentsPlacementExpectedByMe[posToIndex(i,j)][2] = -1
            # 自分が移動した時の処理
            else:
                pass

    def update_ExpectationOfOpponentsPlacement_afterOpponentsAction(self,json_):
        if "result" in json.loads(json_):
            res = json.loads(json_)['result']
            # 相手が攻撃した時の処理
            if ("attacked" in res):
                pass
            # 相手が移動した時の処理
            else:
                moved = res['moved']
                distance = moved['distance']
                if (moved['ship'] == "w"):
                    # まずは優先度２のマスがあるかどうか調べる
                    # あればそのマスを覚える
                    # なければ無視する
                    pos_w = [-1,-1]
                    for i in range(Player.FIELD_SIZE):
                        for j in range(Player.FIELD_SIZE):
                            if self.opponentsPlacementExpectedByMe[posToIndex(i,j)][2] == 2:
                                pos_w = [i,j]
                    if pos_w != [-1,-1]:
                        #まずはopponentsPlacementExpectedByMeを更新
                        self.opponentsPlacementExpectedByMe[posToIndex(*pos_w)][2] = -1
                        self.opponentsPlacementExpectedByMe\
                            [posToIndex(pos_w[0]+distance[0],pos_w[1]+distance[1])][2] = 2
                elif (moved['ship'] == "c"):
                    # まずは優先度3のマスがあるかどうか調べる
                    # あればそのマスを覚える
                    # なければ無視する
                    pos_c = [-1,-1]
                    for i in range(Player.FIELD_SIZE):
                        for j in range(Player.FIELD_SIZE):
                            if self.opponentsPlacementExpectedByMe[posToIndex(i,j)][2] == 3:
                                pos_c = [i,j]
                    if pos_c != [-1,-1]:
                        #まずはopponentsPlacementExpectedByMeを更新
                        self.opponentsPlacementExpectedByMe[posToIndex(*pos_c)][2] = -1
                        self.opponentsPlacementExpectedByMe\
                            [posToIndex(pos_c[0]+distance[0],pos_c[1]+distance[1])][2] = 3
                else:
                    # まずは優先度4のマスがあるかどうか調べる
                    # あればそのマスを覚える
                    # なければ無視する
                    pos_s = [-1,-1]
                    for i in range(Player.FIELD_SIZE):
                        for j in range(Player.FIELD_SIZE):
                            if self.opponentsPlacementExpectedByMe[posToIndex(i,j)][2] == 4:
                                pos_s = [i,j]
                    if pos_s != [-1,-1]:
                        #まずはopponentsPlacementExpectedByMeを更新
                        self.opponentsPlacementExpectedByMe[posToIndex(*pos_s)][2] = -1
                        self.opponentsPlacementExpectedByMe\
                            [posToIndex(pos_s[0]+distance[0],pos_s[1]+distance[1])][2] = 4

    def update_countShip(self, json_):
        me = json.loads(json_)['condition']['me']
        self.countShip = len(me)

    def update_isEmergency(self, json_):
            if "result" in json.loads(json_):
                res = json.loads(json_)['result']
                con = json.loads(json_)['condition']
                # ある船の近傍が攻撃されて、
                # かつ近傍が攻撃された船の残り体力が１の場合、isEmergencyをTrueにする
                # is Emergencyは[w,c,s]の順で格納されている
                if "attacked" in res:
                    attacked = res['attacked']
                    if "near" in attacked:
                        near = attacked['near']
                        for i in range(len(near)):
                            if con['me'][near[i]]['hp'] == 1:
                                if near[i] == "w":
                                    self.isEmergency[0] = True
                                elif near[i] == "c":
                                    self.isEmergency[1] = True
                                elif near[i] == "s":
                                    self.isEmergency[2] = True
            else:
                pass


# 仕様に従ってサーバとソケット通信を行う．
def main(host, port, seed=0):
    assert isinstance(host, str) and isinstance(port, int)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        completed = False
        with sock.makefile(mode='rw', buffering=1) as sockfile:
            while True:
                get_msg = sockfile.readline()
                print(get_msg)
                player = KeiyuPlayer()
                sockfile.write(player.initial_condition()+'\n')

                while True:
                    info = sockfile.readline().rstrip()
                    print(info)
                    player.turn += 1
                    if info == "your turn":
                        sockfile.write(player.action()+'\n')
                        get_msg = sockfile.readline()
                        player.update(get_msg)
                        player.update_ExpectationOfOpponentsPlacement_afterMyAction(get_msg)
                    elif info == "waiting":
                        get_msg = sockfile.readline()
                        player.update(get_msg)
                        player.update_ExpectationOfOpponentsPlacement_afterOpponentsAction(get_msg)
                        player.update_isEmergency(get_msg)
                        player.update_countShip(get_msg)
                    elif info == "you win":
                        print("It takes ",player.turn, " turns.")
                        break
                    elif info == "you lose":
                        print("It takes ",player.turn, " turns.")
                        break
                    elif info == "even":
                        break
                    elif info == "you win.":
                        completed = True
                        break
                    elif info == "you lose.":
                        completed = True
                        break
                    elif info == "even.":
                        completed = True
                        break
                    else:
                        raise RuntimeError("unknown information")
                if completed:
                    for _ in range(5):
                        info = sockfile.readline()
                        print(info, end="")
                    break


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
