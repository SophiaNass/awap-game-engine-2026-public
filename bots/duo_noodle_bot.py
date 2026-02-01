import random
from collections import deque
from typing import Tuple, Optional, List
from enum import Enum

from game_constants import Team, TileType, FoodType, ShopCosts
from robot_controller import RobotController
from item import Pan, Plate, Food

"""
Actions:


"""
class BotActions(Enum):
    NONE = 0
    COOK_UP = 1
    COOK_DOWN = 2
    COOK_LEFT = 3
    COOK_RIGHT = 4
    CHOP_UP = 5
    CHOP_DOWN = 6
    CHOP_LEFT = 7
    CHOP_RIGHT = 8
    BUY_PLATE_UP = 9
    BUY_PLATE_DOWN = 10
    BUY_PLATE_LEFT = 11
    BUY_PLATE_RIGHT = 12
    BUY_PAN_UP = 13
    BUY_PAN_DOWN = 14
    BUY_PAN_LEFT = 15
    BUY_PAN_RIGHT = 16
    BUY_EGG_UP = 17
    BUY_EGG_DOWN = 18
    BUY_EGG_LEFT = 19
    BUY_EGG_RIGHT = 20
    BUY_ONION_UP = 21
    BUY_ONION_DOWN = 22
    BUY_ONION_LEFT = 23
    BUY_ONION_RIGHT = 24
    BUY_MEAT_UP = 25
    BUY_MEAT_DOWN = 26
    BUY_MEAT_LEFT = 27
    BUY_MEAT_RIGHT = 28
    BUY_NOODLES_UP = 29
    BUY_NOODLES_DOWN = 30
    BUY_NOODLES_LEFT = 31
    BUY_NOODLES_RIGHT = 32
    BUY_SAUCE_UP = 33
    BUY_SAUCE_DOWN = 34
    BUY_SAUCE_LEFT = 35
    BUY_SAUCE_RIGHT = 36
    PICKUP_ITEM_UP = 37
    PICKUP_ITEM_DOWN = 38
    PICKUP_ITEM_LEFT = 39
    PICKUP_ITEM_RIGHT = 40
    PLACE_ITEM_UP = 41
    PLACE_ITEM_DOWN = 42
    PLACE_ITEM_LEFT = 43
    PLACE_ITEM_RIGHT = 44
    TRASH_UP = 45
    TRASH_DOWN = 46
    TRASH_LEFT = 47
    TRASH_RIGHT = 48
    TAKE_FROM_PAN_UP = 49
    TAKE_FROM_PAN_DOWN = 50
    TAKE_FROM_PAN_LEFT = 51
    TAKE_FROM_PAN_RIGHT = 52
    TAKE_CLEAN_PLATE_UP = 53
    TAKE_CLEAN_PLATE_DOWN = 54
    TAKE_CLEAN_PLATE_LEFT = 55
    TAKE_CLEAN_PLATE_RIGHT = 56
    PUT_DIRTY_PLATE_UP = 57
    PUT_DIRTY_PLATE_DOWN = 58
    PUT_DIRTY_PLATE_LEFT = 59
    PUT_DIRTY_PLATE_RIGHT = 60
    WASH_SINK_UP = 61
    WASH_SINK_DOWN = 62
    WASH_SINK_LEFT = 63
    WASH_SINK_RIGHT = 64
    FOOD_TO_PLATE_UP = 65
    FOOD_TO_PLATE_DOWN = 66
    FOOD_TO_PLATE_LEFT = 67
    FOOD_TO_PLATE_RIGHT = 68
    SUBMIT_UP = 69
    SUBMIT_DOWN = 70
    SUBMIT_LEFT = 71
    SUBMIT_RIGHT = 72



class BotPlayer:
    def __init__(self, map_copy):
        self.map = map_copy
        self.assembly_counter = None 
        self.cooker_loc = None
        self.my_bot_id = None
        self.megaDict = {}
        
        self.state = 0

    def get_bfs_path(self, controller: RobotController, start: Tuple[int, int], target_predicate) -> Optional[Tuple[int, int]]:
        queue = deque([(start, [])]) 
        visited = set([start])
        w, h = self.map.width, self.map.height

        while queue:
            (curr_x, curr_y), path = queue.popleft()
            tile = controller.get_tile(controller.get_team(), curr_x, curr_y)
            if target_predicate(curr_x, curr_y, tile):
                if not path: return (0, 0) 
                return path[0] 

            for dx in [0, -1, 1]:
                for dy in [0, -1, 1]:
                    if dx == 0 and dy == 0: continue
                    nx, ny = curr_x + dx, curr_y + dy
                    if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                        if controller.get_map(controller.get_team()).is_tile_walkable(nx, ny):
                            visited.add((nx, ny))
                            queue.append(((nx, ny), path + [(dx, dy)]))
        return None

    def move_towards(self, controller: RobotController, bot_id: int, target_x: int, target_y: int) -> bool:
        bot_state = controller.get_bot_state(bot_id)
        bx, by = bot_state['x'], bot_state['y']
        def is_adjacent_to_target(x, y, tile):
            return max(abs(x - target_x), abs(y - target_y)) <= 1
        if is_adjacent_to_target(bx, by, None): return True
        step = self.get_bfs_path(controller, (bx, by), is_adjacent_to_target)
        if step and (step[0] != 0 or step[1] != 0):
            controller.move(bot_id, step[0], step[1])
            return False 
        return False 

    def find_nearest_tile(self, controller: RobotController, bot_x: int, bot_y: int, tile_name: str) -> Optional[Tuple[int, int]]:
        best_dist = 9999
        best_pos = None
        m = controller.get_map(controller.get_team())
        for x in range(m.width):
            for y in range(m.height):
                tile = m.tiles[x][y]
                if tile.tile_name == tile_name:
                    dist = max(abs(bot_x - x), abs(bot_y - y))
                    if dist < best_dist:
                        best_dist = dist
                        best_pos = (x, y)
        return best_pos

    def getMegaDict(self, controller: RobotController):
        megaDict = self.megaDict
        currmap = controller.get_map(controller.get_team()).tiles
        for x in range(len(currmap)):
            for y in range(len(currmap[0])):
                curr_tile = controller.get_tile(controller.get_team(), x, y)
                if curr_tile is not None and curr_tile.tile_name != "FLOOR" and curr_tile.tile_name != "WALL":
                    actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                    for i in range(len(actions)):
                        dx, dy = actions[i]
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < len(currmap) and 0 <= ny < len(currmap[0]):
                            if (nx,ny) not in megaDict.keys():
                                neighbor_tile = controller.get_tile(controller.get_team(), nx, ny)
                                if neighbor_tile is not None and neighbor_tile.tile_name == "FLOOR":
                                    megaDict[(nx,ny)] = [curr_tile.tile_name]
                            else:
                                if curr_tile.tile_name not in megaDict[(nx,ny)]:
                                    megaDict[(nx,ny)].append(curr_tile.tile_name)
        self.megaDict = megaDict
        return megaDict



    def get_all_legal_moves(self, controller: RobotController):
        retList = []
        for i in range(len(controller.get_team_bot_ids(controller.get_team()))):
            bot_id = controller.get_team_bot_ids(controller.get_team())[i]
            legal_moves = []
            bot_state = controller.get_bot_state(bot_id)
            x, y = bot_state['x'], bot_state['y']
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    nx, ny = x + dx, y + dy
                    if dx == 0 and dy == 0:
                        legal_moves.append((nx, ny, 'STAY'))
                        continue
                    nx, ny = x + dx, y + dy
                    fail = False
                    for i in range(len(retList)):
                        for j in range(len(retList[i])):
                            print('here')
                            print(retList)
                            
                            if retList[i][j][0] == nx and retList[i][j][1] == ny:
                                fail = True
                    if not fail:
                        
                        if controller.get_map(controller.get_team()).is_tile_walkable(nx, ny):
                            legal_moves.append((nx, ny, 'MOVE'))
                        if (nx, ny) in self.megaDict.keys():
                            for i in range(len(self.megaDict[(nx, ny)])):
                                legal_moves.append((nx, ny, self.megaDict[(nx, ny)][i]))
            
            retList.append((legal_moves))
        return retList

    #retList = [[bot1_action1, bot1_action2, ...], [bot2_action1, bot2_action2, ...], ...]
    def get_total_actions(self, controller: RobotController):
        retList = []
        legal_list = self.get_all_legal_moves(controller)
        for i in range(len(legal_list[0])):
            for j in range(len(legal_list[1])):
                retList.append([legal_list[0][i], legal_list[1][j]])
        return retList


    def is_game_over(self, controller: RobotController):
        if controller.get_turn() >= 500:
            return True
        return False
    
    def game_result(self, controller: RobotController):
        if controller.is_game_over(controller):
            ours = controller.get_team_money(controller.get_team())
            theirs = controller.get_team_money(controller.get_enemy_team())
            if ours > theirs:
                return 1
            elif theirs > ours:
                return -1

            else:
                return 0
   
        

    def play_turn(self, controller: RobotController):
        if controller.get_turn() == 1:
           self.getMegaDict(controller)
   