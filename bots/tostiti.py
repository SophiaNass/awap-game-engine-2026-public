import random
import copy
from collections import defaultdict
from enum import Enum
from itertools import product

from game_constants import FoodType, ShopCosts
from robot_controller import RobotController
from item import Pan, Plate, Food


class BotActions(Enum):
    BUY = 1
    PICKUP = 2
    PLACE = 3
    CHOP = 4
    COOK = 5
    TAKE_PAN = 6
    TAKE_PLATE = 7
    FOOD_TO_PLATE = 8
    SUBMIT = 9
    PUT_DIRTY = 10
    WASH = 11


class BotPlayer:
    def __init__(self, _):
        self.mega = {}

    # ---------- MAP PREPROCESS ----------
    def buildMega(self, controller):
        team = controller.get_team()
        m = controller.get_map(team)
        tiles = m.tiles
        W, H = len(tiles), len(tiles[0])
        mega = defaultdict(list)

        dirs = [(0,1),(1,0),(0,-1),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]

        for x in range(W):
            for y in range(H):
                t = tiles[x][y]
                if not t or getattr(t, "tile_name", None) in ("FLOOR", "WALL"):
                    continue
                for dx, dy in dirs:
                    fx, fy = x+dx, y+dy
                    if 0 <= fx < W and 0 <= fy < H:
                        ft = tiles[fx][fy]
                        if ft and getattr(ft, "tile_name", None) == "FLOOR":
                            mega[(fx, fy)].append((x, y))
        self.mega = dict(mega)

    # ---------- ORDERS ----------
    def needed_foods(self, controller):
        team = controller.get_team()
        foods = set()

        orders = controller.get_orders(team)
        if not orders:
            return foods

        for o in orders:
            if o["is_active"] and o["completed_turn"] is None:
                for f in o["required"]:
                    foods.add(f)

        return foods

    # ---------- MOVE GEN ----------
    def per_bot_moves(self, controller, bot_id, tiles, W, H):
        st = controller.get_bot_state(bot_id)
        if not st:
            return []

        x, y = st["x"], st["y"]
        holding = st["holding"]
        moves = [[x, y, None, None]]

        for dx in (-1,0,1):
            for dy in (-1,0,1):
                if dx or dy:
                    if controller.can_move(bot_id, dx, dy):
                        moves.append([x+dx, y+dy, None, None])

        for fx, fy, _, _ in moves[:]:
            for tx, ty in self.mega.get((fx, fy), []):
                t = tiles[tx][ty]
                name = getattr(t, "tile_name", None)

                def add(a):
                    moves.append([fx, fy, a, (tx, ty)])

                if name == "SHOP" and holding is None:
                    for f in self.needed_foods(controller):
                        try:
                            ft = FoodType[f]
                            if controller.can_buy(bot_id, ft, tx, ty):
                                add((BotActions.BUY, ft))
                        except KeyError:
                            pass

                if name == "BOX":
                    if holding is None and t.item:
                        add((BotActions.PICKUP, None))
                    if holding:
                        add((BotActions.PLACE, None))

                if name == "COUNTER":
                    if holding is None and t.item:
                        add((BotActions.PICKUP, None))
                    if holding and t.item is None:
                        add((BotActions.PLACE, None))
                    if holding is None and isinstance(t.item, Food) and not t.item.chopped:
                        add((BotActions.CHOP, None))

                if name == "COOKER":
                    if holding and holding["type"] == "Food":
                        if controller.can_start_cook(bot_id, tx, ty):
                            add((BotActions.COOK, None))
                    if holding is None and isinstance(t.item, Pan) and t.item.food:
                        add((BotActions.TAKE_PAN, None))
                    if holding and holding["type"] == "Pan":
                        add((BotActions.PLACE, None))

                if name == "SINKTABLE" and holding is None:
                    add((BotActions.TAKE_PLATE, None))

                if name == "SINK":
                    if holding and holding["type"] == "Plate" and holding["dirty"]:
                        add((BotActions.PUT_DIRTY, None))
                    if getattr(t, "num_dirty_plates", 0) > 0:
                        add((BotActions.WASH, None))

                if name == "BOX" and holding and holding["type"] == "Plate" and t.item:
                    add((BotActions.FOOD_TO_PLATE, None))

                if name == "SUBMIT" and holding and holding["type"] == "Plate":
                    if controller.can_submit(bot_id, tx, ty):
                        add((BotActions.SUBMIT, None))

        return moves[:40]

    # ---------- EXEC ----------
    def exec_move(self, controller, bot_id, move, start):
        mx, my, act, tgt = move
        sx, sy = start
        dx, dy = mx - sx, my - sy

        if (dx or dy) and controller.can_move(bot_id, dx, dy):
            controller.move(bot_id, dx, dy)

        if not act:
            return

        tx, ty = tgt
        a, p = act

        if a == BotActions.BUY:
            controller.buy(bot_id, p, tx, ty)
        elif a == BotActions.PICKUP:
            controller.pickup(bot_id, tx, ty)
        elif a == BotActions.PLACE:
            controller.place(bot_id, tx, ty)
        elif a == BotActions.CHOP:
            controller.chop(bot_id, tx, ty)
        elif a == BotActions.COOK:
            controller.start_cook(bot_id, tx, ty)
        elif a == BotActions.TAKE_PAN:
            controller.take_from_pan(bot_id, tx, ty)
        elif a == BotActions.TAKE_PLATE:
            controller.take_clean_plate(bot_id, tx, ty)
        elif a == BotActions.FOOD_TO_PLATE:
            controller.add_food_to_plate(bot_id, tx, ty)
        elif a == BotActions.PUT_DIRTY:
            controller.put_dirty_plate_in_sink(bot_id, tx, ty)
        elif a == BotActions.WASH:
            controller.wash_sink(bot_id, tx, ty)
        elif a == BotActions.SUBMIT:
            controller.submit(bot_id, tx, ty)

    # ---------- TURN ----------
    def play_turn(self, controller: RobotController):
        if controller.get_turn() == 1:
            self.buildMega(controller)
            return

        team = controller.get_team()
        bots = controller.get_team_bot_ids(team)
        m = controller.get_map(team)
        tiles = m.tiles
        W, H = len(tiles), len(tiles[0])

        starts = {
            b: (controller.get_bot_state(b)["x"], controller.get_bot_state(b)["y"])
            for b in bots
        }

        per_bot = [self.per_bot_moves(controller, b, tiles, W, H) for b in bots]
        joint = list(product(*per_bot))
        random.shuffle(joint)

        mv = joint[0]
        for i, b in enumerate(bots):
            self.exec_move(controller, b, mv[i], starts[b])
