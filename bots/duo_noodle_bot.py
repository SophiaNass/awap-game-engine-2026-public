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
    COOK = 1
    CHOP = 2
    BUY_PLATE =3
    BUY_PAN =4
    BUY_EGG =5
    BUY_ONION = 6
    BUY_MEAT  = 7
    BUY_NOODLES = 8 
    BUY_SAUCE  = 9
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



class BotPlayer:
    def __init__(self, map_copy):
        self.map = map_copy
        self.assembly_counter = None 
        self.cooker_loc = None
        self.my_bot_id = None
        self.megaDict = {}
        
        self.state = 0


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
                                    megaDict[(nx,ny)] = [[curr_tile, [x,y]]]
                            else:
                                if not any(curr_tile.tile_name == item[0].tile_name for item in megaDict[(nx,ny)]):
                                    megaDict[(nx,ny)].append([curr_tile, [x,y]])
        self.megaDict = megaDict
        return megaDict


    # 0 = STAY, 1 = MOVE ONLY, 2 = INTERACT WITH TILE, THEN MOVE, 3 = INTERACT WITHOUT MOVING, 4 = MOVE THEN INTERACT WITH TILE 
   
    
    def get_all_legal_moves(self, controller: RobotController):
        retList = []
        bot_id = controller.get_team_bot_ids(controller.get_team())[0]
        legal_moves = []
        bot_state = controller.get_bot_state(bot_id)
        x, y = bot_state['x'], bot_state['y']

        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                nx, ny = x + dx, y + dy #these are coordinates
                
                if (nx, ny) in self.megaDict.keys():
                    for j in range(len(self.megaDict[(nx, ny)])): # go over each action
                        currUsefulNeighbor = self.megaDict[(nx, ny)][j]

                        itemInHand = controller.get_bot_state(bot_id)['holding']
                        match currUsefulNeighbor[0].title:
                            case "SINK":
                                if (itemInHand["type"] == "Plate" and itemInHand['dirty'] == True):
                                    if dx == dy == 0:
                                        legal_moves.append((nx, ny, [BotActions.PUT_DIRTY_PLATE,currUsefulNeighbor[1]], 3))

                                        actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                                        for i in range(len(actions)):
                                            adx, ady = actions[i]
                                            anx, any = nx + adx, ny + ady
                                            if 0 <= anx < len(controller.get_map(controller.get_team()).tiles) and 0 <= any < len(controller.get_map(controller.get_team()).tiles[0]):
                                                if controller.get_map(controller.get_team()).is_tile_walkable(anx, any):
                                                    legal_moves.append((anx, any, [BotActions.WASH_SINK,currUsefulNeighbor[1]], 2))


                                    else:
                                        legal_moves.append((nx, ny, [BotActions.PUT_DIRTY_PLATE,currUsefulNeighbor[1]], 4))
                                    #moves to nx,ny then d
                                if (currUsefulNeighbor[0].num_dirty_plates > 0):
                                    if dx == dy == 0:
                                        legal_moves.append((nx, ny, [BotActions.WASH_SINK,currUsefulNeighbor[1]], 3))
                                    # Add all moves you can do from here after action 
                                        # legal_moves.append((nx, ny, [BotActions.WASH_SINK,currUsefulNeighbor[1]], 2))
                                   
                                    else:
                                        legal_moves.append((nx, ny, [BotActions.WASH_SINK,currUsefulNeighbor[1]], 4))
                            case "COUNTER":
                                if (currUsefulNeighbor[0].item is not None):
                                    if dx == dy == 0:
                                        legal_moves.append((nx, ny, [BotActions.TAKE_FROM_COUNTER,currUsefulNeighbor[1]], 3))
                                    else:
                                        legal_moves.append((nx, ny, [BotActions.TAKE_FROM_COUNTER,currUsefulNeighbor[1]], 4))
                                    
                                    if (currUsefulNeighbor[0].item is Food and currUsefulNeighbor[0].item.can_chop):
                                        if dx == dy == 0:
                                            legal_moves.append((nx, ny, [BotActions.CHOP,currUsefulNeighbor[1]], 3))
                                        else:
                                            legal_moves.append((nx, ny, [BotActions.CHOP,currUsefulNeighbor[1]], 4))
                                if currUsefulNeighbor[0].item is None and itemInHand is not None:
                                    if dx == dy == 0:
                                        legal_moves.append((nx, ny, [BotActions.PLACE_ITEM,currUsefulNeighbor[1]], 3))
                                    else:
                                        legal_moves.append((nx, ny, [BotActions.PLACE_ITEM,currUsefulNeighbor[1]], 4))
                            
                            case "SINKTABLE":
                                if (currUsefulNeighbor.num_clean_plates > 0 and itemInHand == None):
                                    if dx == dy == 0:
                                        legal_moves.append((nx, ny, [BotActions.TAKE_CLEAN_PLATE,currUsefulNeighbor[1]], 3))
                                        
                                        # Add all moves you can do from here after action 
                                        # legal_moves.append((nx, ny, [BotActions.WASH_SINK,currUsefulNeighbor[1]], 2))
                                    else:
                                        legal_moves.append((nx, ny, [BotActions.TAKE_CLEAN_PLATE,currUsefulNeighbor[1]], 4))
                                       
                                
                            case "COOKER":
                                legal_moves.append((nx, ny, "COOKER", 2))
                            case "TRASH":
                                if (itemInHand is not None and itemInHand["type"] == "Food"):
                                    if dx == dy == 0:
                                        legal_moves.append((nx, ny, [BotActions.TRASH,currUsefulNeighbor[1]], 3))
                                    else:
                                        legal_moves.append((nx, ny, [BotActions.TRASH,currUsefulNeighbor[1]], 4))
                                if (itemInHand is not None and itemInHand["type"] == "Plate" and itemInHand['food'] != []):
                                    if dx == dy == 0:
                                        legal_moves.append((nx, ny, [BotActions.TRASH,currUsefulNeighbor[1]], 3))
                                    else:
                                        legal_moves.append((nx, ny, [BotActions.TRASH,currUsefulNeighbor[1]], 4))
                            case TileType.SHOP:
                                legal_moves.append((nx, ny, "SHOP", 2))
                            case TileType.BOX:
                                legal_moves.append((nx, ny, "BOX", 2))
                            case "SUBMIT":
                                if (itemInHand is not None and itemInHand["type"] == "Plate" and itemInHand['dirty'] == False):
                                    if dx == dy == 0:
                                        legal_moves.append((nx, ny, [BotActions.SUBMIT,currUsefulNeighbor[1]], 3))
                                    else:
                                        
                                        legal_moves.append((nx, ny, [BotActions.SUBMIT,currUsefulNeighbor[1]], 4))
                            
                            case _:
                                print("UNKNOWN TILE TYPE THATS WEIRDDDDDDD")

                        legal_moves.append((nx, ny, self.megaDict[(nx, ny)][j], 3))
                    else:
                        legal_moves.append((nx, ny, 'STAY', 0))
                        continue
                nx, ny = x + dx, y + dy
                fail = False
                for i in range(len(retList)):
                    for j in range(len(retList[i])):
                        if retList[i][j][0] == nx and retList[i][j][1] == ny:
                            fail = True
                if not fail:
                    
                    if controller.get_map(controller.get_team()).is_tile_walkable(nx, ny):
                        legal_moves.append((nx, ny, 'MOVE', 1))
                    if (nx, ny) in self.megaDict.keys():
                        for i in range(len(self.megaDict[(nx, ny)])):
                            if controller.get_map(controller.get_team()).is_tile_walkable(nx, ny):
                                legal_moves.append((nx, ny, self.megaDict[(nx, ny)][i], 4))
                            legal_moves.append((nx, ny, self.megaDict[(nx, ny)][i], 2))
                        
        
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
        print('-----')
        print(self.get_all_legal_moves(controller))
        print('-----')
   