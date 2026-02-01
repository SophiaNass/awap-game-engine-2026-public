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
# class BotActions(Enum):
#     NONE = 0
#     COOK = 1
#     CHOP =3
#     BUY_PLATE = 5
#     BUY_PAN = 6
#     THROW_TRASH = 7
#     BUY_PAN = 8
#     BUY_PLATE = 9
#     BUY_EGG =10
#     BUY_ONION =11
#     BUY_MEAT =12
#     BUY_NOODLES =13
#     BUY_SAUCE =14
#     PICKUP_ITEM = 15
#     PLACE_ITEM = 16
#     TAKE_FROM_PAN = 17

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
        print(self.megaDict)
   