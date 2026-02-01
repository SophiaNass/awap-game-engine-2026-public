import random
import time
import copy
from collections import defaultdict
from enum import Enum
from itertools import product
from typing import List, Optional, Tuple

from game_constants import FoodType, ShopCosts
from robot_controller import RobotController
from item import Pan, Plate, Food


# ----------------------------
# Actions
# ----------------------------

class BotActions(Enum):
    NONE = 0
    COOK = 1
    CHOP = 2
    BUY_PLATE = 3
    BUY_PAN = 4
    BUY_EGG = 5
    BUY_ONION = 6
    BUY_MEAT = 7
    BUY_NOODLES = 8
    BUY_SAUCE = 9
    PICKUP = 10
    PLACE_ITEM = 41
    TRASH = 45
    TAKE_FROM_COUNTER = 46
    TAKE_FROM_PAN = 49
    TAKE_CLEAN_PLATE = 53
    PUT_DIRTY_PLATE = 57
    WASH_SINK = 61
    FOOD_TO_PLATE = 65
    SUBMIT = 69


# A move for one bot:
# [dest_x, dest_y, [BotActions.<...>, [target_x,target_y]], mode]
# mode:
# 0 = stay
# 1 = move only
# 3 = interact without moving
# 4 = move then interact
#
# Joint move: [m1, m2]


# ----------------------------
# BotPlayer
# ----------------------------

class BotPlayer:
    def __init__(self, map_copy):
        self.map = map_copy
        self.megaDict = {}  # floor_pos -> list of [interactable_tile_obj, [tile_x,tile_y]]

        # --- speed / budget knobs ---
        self.time_budget_sec = 0.45     # keep under 0.5s total
        self.max_moves_per_bot = 40     # cap per-bot action list
        self.max_joint_moves = 900      # cap cartesian product size we actually evaluate
        self.rollouts_per_move = 3      # K
        self.max_rollout_depth = 1      # IMPORTANT: controller budgets don't refresh unless turn advances

        # If you want a bit more exploration, raise rollouts_per_move and lower max_joint_moves.

    # --------- map preprocessing ---------

    def buildMegaDict(self, controller: RobotController) -> None:
        """
        Build mapping from FLOOR squares to adjacent interactable tiles.
        Done once (turn 1) using a single map deepcopy.
        """
        team = controller.get_team()
        m = controller.get_map(team)  # deepcopy once here
        tiles = m.tiles
        W, H = len(tiles), len(tiles[0])

        mega = defaultdict(list)

        # For each non-floor/wall tile, add it as interactable for neighboring floor squares
        neighbor_dirs = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]

        for tx in range(W):
            for ty in range(H):
                t = tiles[tx][ty]
                if t is None:
                    continue
                name = getattr(t, "tile_name", None)
                if name is None or name in ("FLOOR", "WALL"):
                    continue

                for dx, dy in neighbor_dirs:
                    fx, fy = tx + dx, ty + dy
                    if 0 <= fx < W and 0 <= fy < H:
                        ft = tiles[fx][fy]
                        if ft is not None and getattr(ft, "tile_name", None) == "FLOOR":
                            # Avoid duplicates by tile_name
                            if not any(getattr(t, "tile_name", None) == getattr(x[0], "tile_name", None) for x in mega[(fx, fy)]):
                                mega[(fx, fy)].append([t, [tx, ty]])

        self.megaDict = dict(mega)

    # --------- move generation ---------

    def _get_legal_moves_per_bot(
        self,
        controller: RobotController,
        bot_id: int,
        tiles, W: int, H: int
    ) -> List[list]:
        """
        Fast per-bot legal move gen:
        - caches bot_state and holding once
        - DOES NOT call controller.get_map() in loops
        - DOES NOT generate mode=2 "act then move" explosion
        - uses controller.can_move() for movement validity (includes occupancy)
        """
        legal_moves: List[list] = []

        bot_state = controller.get_bot_state(bot_id)
        if bot_state is None:
            return legal_moves

        x, y = bot_state["x"], bot_state["y"]
        itemInHand = bot_state["holding"]  # dict or None

        # --- Always allow stay/no-op
        legal_moves.append([x, y, [BotActions.NONE, [0, 0]], 0])

        # --- Move-only options (filter with can_move)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H and controller.can_move(bot_id, dx, dy):
                    legal_moves.append([nx, ny, [BotActions.NONE, [0, 0]], 1])

        # --- Interaction options
        # We consider interactions from either:
        #   - current square (mode 3)
        #   - a neighbor square you can move to (mode 4)
        #
        # We use megaDict: floor_pos -> adjacent interactable tiles
        candidate_floor_positions: List[Tuple[int, int, int, int, int]] = []
        # (fx, fy, mode, mdx, mdy) where mdx/mdy is movement delta from current
        candidate_floor_positions.append((x, y, 3, 0, 0))  # interact without moving

        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H and controller.can_move(bot_id, dx, dy):
                    candidate_floor_positions.append((nx, ny, 4, dx, dy))  # move then interact

        for fx, fy, mode, _, _ in candidate_floor_positions:
            if (fx, fy) not in self.megaDict:
                continue

            for tile_obj, (tx, ty) in self.megaDict[(fx, fy)]:
                # Read the tile state from cached map tiles (fast)
                if not (0 <= tx < W and 0 <= ty < H):
                    continue
                t = tiles[tx][ty]
                if t is None:
                    continue

                tile_name = getattr(tile_obj, "tile_name", None)

                # Helper: append interaction move
                def add(action: BotActions):
                    legal_moves.append([fx, fy, [action, [tx, ty]], mode])

                # ---- Tile-specific rules ----

                if tile_name == "SINK":
                    # put dirty plate
                    if itemInHand is not None and itemInHand.get("type") == "Plate" and itemInHand.get("dirty", False):
                        add(BotActions.PUT_DIRTY_PLATE)
                    # wash sink if dirty plates present
                    if getattr(t, "num_dirty_plates", 0) > 0:
                        add(BotActions.WASH_SINK)

                elif tile_name == "SINKTABLE":
                    # take clean plate if available and empty-handed
                    if itemInHand is None and getattr(t, "num_clean_plates", 0) > 0:
                        add(BotActions.TAKE_CLEAN_PLATE)

                elif tile_name == "COUNTER":
                    # take if item exists and empty-hand required by controller.pickup
                    if itemInHand is None and getattr(t, "item", None) is not None:
                        add(BotActions.TAKE_FROM_COUNTER)

                    # chop: controller requires empty hand and counter has Food that can_chop
                    if itemInHand is None:
                        it = getattr(t, "item", None)
                        if isinstance(it, Food) and getattr(it, "can_chop", False) and getattr(it, "chopped", False) is False:
                            add(BotActions.CHOP)

                    # place: requires holding something and counter empty
                    if itemInHand is not None and getattr(t, "item", None) is None:
                        add(BotActions.PLACE_ITEM)

                elif tile_name == "COOKER":
                    # cooker holds Pan in tile.item (usually), and Pan.food is the food.
                    cooker_item = getattr(t, "item", None)

                    # take_from_pan: requires empty hand and pan has food
                    if itemInHand is None and isinstance(cooker_item, Pan) and cooker_item.food is not None:
                        add(BotActions.TAKE_FROM_PAN)

                    # place pan onto cooker: controller.place handles swapping if holding Pan
                    if itemInHand is not None and itemInHand.get("type") == "Pan":
                        add(BotActions.PLACE_ITEM)

                    # start cook: controller.start_cook requires holding cookable Food and cooker pan empty
                    if itemInHand is not None and itemInHand.get("type") == "Food":
                        # public dict does not include can_cook; use food_name heuristic if needed.
                        # If your public dict DOES include can_cook, this will work:
                        can_cook = itemInHand.get("can_cook", False)
                        if can_cook and isinstance(cooker_item, Pan) and cooker_item.food is None:
                            add(BotActions.COOK)

                elif tile_name == "TRASH":
                    if itemInHand is not None:
                        ttype = itemInHand.get("type")
                        if ttype == "Food":
                            add(BotActions.TRASH)
                        elif ttype == "Plate" and itemInHand.get("food", []) != []:
                            add(BotActions.TRASH)
                        elif ttype == "Pan" and itemInHand.get("food") is not None:
                            add(BotActions.TRASH)

                elif tile_name == "SHOP":
                    # can_buy uses controller internal checks (distance + funds + menu)
                    if controller.can_buy(bot_id, ShopCosts.PLATE, tx, ty):
                        add(BotActions.BUY_PLATE)
                    if controller.can_buy(bot_id, ShopCosts.PAN, tx, ty):
                        add(BotActions.BUY_PAN)
                    if controller.can_buy(bot_id, FoodType.EGG, tx, ty):
                        add(BotActions.BUY_EGG)
                    if controller.can_buy(bot_id, FoodType.ONIONS, tx, ty):
                        add(BotActions.BUY_ONION)
                    if controller.can_buy(bot_id, FoodType.MEAT, tx, ty):
                        add(BotActions.BUY_MEAT)
                    if controller.can_buy(bot_id, FoodType.NOODLES, tx, ty):
                        add(BotActions.BUY_NOODLES)
                    if controller.can_buy(bot_id, FoodType.SAUCE, tx, ty):
                        add(BotActions.BUY_SAUCE)

                elif tile_name == "BOX":
                    box_item = getattr(t, "item", None)

                    # pickup from box: controller.pickup requires empty hand and box has something
                    if itemInHand is None and box_item is not None:
                        add(BotActions.PICKUP)

                    # food_to_plate: controller.add_food_to_plate handles both plate->food and food->plate,
                    # but you were using a custom action. Keep it: if holding plate and box has food, try.
                    if itemInHand is not None and itemInHand.get("type") == "Plate" and box_item is not None:
                        add(BotActions.FOOD_TO_PLATE)

                    # place into box: controller.place supports Box special
                    if itemInHand is not None:
                        add(BotActions.PLACE_ITEM)

                elif tile_name == "SUBMIT":
                    if itemInHand is not None and itemInHand.get("type") == "Plate" and not itemInHand.get("dirty", True):
                        add(BotActions.SUBMIT)

                else:
                    # unknown tile type: ignore
                    pass

        # Cap per-bot list for speed (sample to keep variety)
        if len(legal_moves) > self.max_moves_per_bot:
            # keep the "stay" move and sample the rest
            stay = legal_moves[0]
            rest = legal_moves[1:]
            rest = random.sample(rest, self.max_moves_per_bot - 1)
            legal_moves = [stay] + rest

        return legal_moves

    def legal_moves(self, controller: RobotController) -> List[list]:
        """
        Joint move generation with caching:
        - one map deepcopy for both bots
        - per-bot lists capped
        - joint list capped
        """
        team = controller.get_team()
        m = controller.get_map(team)  # ONE deepcopy per call
        tiles = m.tiles
        W, H = len(tiles), len(tiles[0])

        bot_ids = controller.get_team_bot_ids(team)
        if len(bot_ids) < 2:
            return []

        legal1 = self._get_legal_moves_per_bot(controller, bot_ids[0], tiles, W, H)
        legal2 = self._get_legal_moves_per_bot(controller, bot_ids[1], tiles, W, H)

        joint_moves: List[list] = []

        # Build joint moves with constraints + early cap
        for m1, m2 in product(legal1, legal2):
            # Rule 1: cannot end on same tile
            if m1[0] == m2[0] and m1[1] == m2[1]:
                continue

            # Rule 2: cannot act on same target tile (if both act)
            target1 = m1[2][1] if m1[2][0] != BotActions.NONE else None
            target2 = m2[2][1] if m2[2][0] != BotActions.NONE else None
            if target1 is not None and target1 == target2:
                continue

            joint_moves.append([m1, m2])
            if len(joint_moves) >= self.max_joint_moves:
                break

        return joint_moves

    # --------- applying moves ---------

    def make_move(self, controller: RobotController, move: list) -> None:
        """
        Execute a joint move (for your two bots) on a controller.
        No printing (printing is slow).
        """
        team = controller.get_team()
        bot_ids = controller.get_team_bot_ids(team)

        # snapshot start positions (so dx,dy computed correctly)
        start_pos = {}
        for bid in bot_ids:
            st = controller.get_bot_state(bid)
            if st is not None:
                start_pos[bid] = (st["x"], st["y"])

        for idx in range(min(2, len(bot_ids))):
            bot_id = bot_ids[idx]
            if bot_id not in start_pos:
                continue

            curr_move = move[idx]
            sx, sy = start_pos[bot_id]
            dx = curr_move[0] - sx
            dy = curr_move[1] - sy
            mode = curr_move[3]
            action, target = curr_move[2][0], curr_move[2][1]

            if mode == 0:
                continue

            if mode == 1:
                if dx != 0 or dy != 0:
                    if controller.can_move(bot_id, dx, dy):
                        controller.move(bot_id, dx, dy)
                continue

            # mode 4: move then interact
            if mode == 4:
                if dx != 0 or dy != 0 and controller.can_move(bot_id, dx, dy):
                    controller.move(bot_id, dx, dy)

            # interact (mode 3 or 4)
            tx, ty = target[0], target[1]

            if action == BotActions.NONE:
                pass
            elif action == BotActions.COOK:
                controller.start_cook(bot_id, tx, ty)
            elif action == BotActions.CHOP:
                controller.chop(bot_id, tx, ty)
            elif action == BotActions.BUY_PLATE:
                controller.buy(bot_id, ShopCosts.PLATE, tx, ty)
            elif action == BotActions.BUY_PAN:
                controller.buy(bot_id, ShopCosts.PAN, tx, ty)
            elif action == BotActions.BUY_EGG:
                controller.buy(bot_id, FoodType.EGG, tx, ty)
            elif action == BotActions.BUY_ONION:
                controller.buy(bot_id, FoodType.ONIONS, tx, ty)
            elif action == BotActions.BUY_MEAT:
                controller.buy(bot_id, FoodType.MEAT, tx, ty)
            elif action == BotActions.BUY_NOODLES:
                controller.buy(bot_id, FoodType.NOODLES, tx, ty)
            elif action == BotActions.BUY_SAUCE:
                controller.buy(bot_id, FoodType.SAUCE, tx, ty)
            elif action == BotActions.PICKUP:
                controller.pickup(bot_id, tx, ty)
            elif action == BotActions.PLACE_ITEM:
                controller.place(bot_id, tx, ty)
            elif action == BotActions.TRASH:
                controller.trash(bot_id, tx, ty)
            elif action == BotActions.TAKE_FROM_COUNTER:
                controller.pickup(bot_id, tx, ty)
            elif action == BotActions.TAKE_FROM_PAN:
                controller.take_from_pan(bot_id, tx, ty)
            elif action == BotActions.TAKE_CLEAN_PLATE:
                controller.take_clean_plate(bot_id, tx, ty)
            elif action == BotActions.PUT_DIRTY_PLATE:
                controller.put_dirty_plate_in_sink(bot_id, tx, ty)
            elif action == BotActions.WASH_SINK:
                controller.wash_sink(bot_id, tx, ty)
            elif action == BotActions.FOOD_TO_PLATE:
                controller.add_food_to_plate(bot_id, tx, ty)
            elif action == BotActions.SUBMIT:
                controller.submit(bot_id, tx, ty)
            else:
                # unknown action: ignore
                pass

    # --------- evaluation ---------

    def evaluate_state(self, controller: RobotController) -> float:
        """
        Very cheap heuristic: money diff normalized.
        """
        ours = controller.get_team_money(controller.get_team())
        theirs = controller.get_team_money(controller.get_enemy_team())
        diff = ours - theirs
        return max(-1.0, min(1.0, diff / 100.0))

    # --------- planner (fast, fits 0.5s) ---------

    def _pick_best_move_under_budget(self, controller: RobotController) -> Optional[list]:
        """
        Flat Monte Carlo (NOT tree MCTS) under a hard time budget:
        - generate joint moves once
        - sample/score them with a few rollouts each
        - stop when out of time
        """
        start = time.perf_counter()
        moves = self.legal_moves(controller)
        if not moves:
            return None

        # Randomize order for fairness under early cutoff
        random.shuffle(moves)

        best_move = moves[0]
        best_score = -1e9

        # Evaluate candidates until we run out of time
        for mv in moves:
            if time.perf_counter() - start > self.time_budget_sec:
                break

            total = 0.0
            n = 0

            # K rollouts
            for _ in range(self.rollouts_per_move):
                if time.perf_counter() - start > self.time_budget_sec:
                    break

                sim = copy.deepcopy(controller)  # still costly, but bounded tightly by budget
                self.make_move(sim, mv)

                # depth>1 generally doesn't work because move/action budgets don't refresh without advancing turns,
                # so keep it at 1 (max_rollout_depth kept for future tweaks)
                total += self.evaluate_state(sim)
                n += 1

            if n > 0:
                avg = total / n
                if avg > best_score:
                    best_score = avg
                    best_move = mv

        return best_move

    # --------- main entry ---------

    def play_turn(self, controller: RobotController) -> None:
        """
        Called by the engine each turn.
        """
        if controller.get_turn() == 1:
            self.buildMegaDict(controller)
            return

        best = self._pick_best_move_under_budget(controller)
        if best is None:
            return

        self.make_move(controller, best)
