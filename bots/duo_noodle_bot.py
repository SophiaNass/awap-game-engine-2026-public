import random
from collections import deque
from typing import Tuple, Optional, List
from enum import Enum
from itertools import product

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
   
    
    def get_legal_moves_per_bot(self, controller: RobotController , bot_id: int):
        
        legal_moves = []
        bot_state = controller.get_bot_state(bot_id)
        x, y = bot_state['x'], bot_state['y']

        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                nx, ny = x + dx, y + dy #these are coordinates
                
                if (nx, ny) in self.megaDict.keys():
                    for j in range(len(self.megaDict[(nx, ny)])): # go over each action
                        currUsefulNeighbor = self.megaDict[(nx, ny)][j]

                        updatedNeighborTile = controller.get_tile(controller.get_team(), currUsefulNeighbor[1][0], currUsefulNeighbor[1][1])
    

                        itemInHand = controller.get_bot_state(bot_id)['holding']
                        print(currUsefulNeighbor[0].tile_name)
                        match currUsefulNeighbor[0].tile_name:
                            case "SINK":
                                if (itemInHand["type"] == "Plate" and itemInHand['dirty'] == True):
                                    if dx == dy == 0:
                                        legal_moves.append([nx, ny, [BotActions.PUT_DIRTY_PLATE,currUsefulNeighbor[1]], 3])

                                        actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                                        for i in range(len(actions)):
                                            adx, ady = actions[i]
                                            tempx, tempy = nx + adx, ny + ady
                                            if 0 <= tempx < len(controller.get_map(controller.get_team()).tiles) and 0 <= tempy < len(controller.get_map(controller.get_team()).tiles[0]):
                                                if controller.get_map(controller.get_team()).is_tile_walkable(tempx, tempy):
                                                    legal_moves.append([tempx, tempy, [BotActions.PUT_DIRTY_PLATE,currUsefulNeighbor[1]], 2])
                                    else:
                                        legal_moves.append([nx, ny, [BotActions.PUT_DIRTY_PLATE,currUsefulNeighbor[1]], 4])
                                    #moves to nx,ny then d
                                if (updatedNeighborTile.num_dirty_plates > 0):
                                    if dx == dy == 0:
                                        legal_moves.append([nx, ny, [BotActions.WASH_SINK,currUsefulNeighbor[1]], 3])

                                        actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                                        for i in range(len(actions)):
                                            adx, ady = actions[i]
                                            tempx, tempy = nx + adx, ny + ady
                                            if 0 <= tempx < len(controller.get_map(controller.get_team()).tiles) and 0 <= tempy < len(controller.get_map(controller.get_team()).tiles[0]):
                                                if controller.get_map(controller.get_team()).is_tile_walkable(tempx, tempy):
                                                    legal_moves.append([tempx, tempy, [BotActions.WASH_SINK,currUsefulNeighbor[1]], 2])
                                    else:
                                        legal_moves.append([nx, ny, [BotActions.WASH_SINK,currUsefulNeighbor[1]], 4])

                            case "COUNTER":
                                if (updatedNeighborTile.item is not None):
                                    if dx == dy == 0:
                                        legal_moves.append([nx, ny, [BotActions.TAKE_FROM_COUNTER,currUsefulNeighbor[1]], 3])

                                        actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                                        for i in range(len(actions)):
                                            adx, ady = actions[i]
                                            tempx, tempy = nx + adx, ny + ady
                                            if 0 <= tempx < len(controller.get_map(controller.get_team()).tiles) and 0 <= tempy < len(controller.get_map(controller.get_team()).tiles[0]):
                                                if controller.get_map(controller.get_team()).is_tile_walkable(tempx, tempy):
                                                    legal_moves.append([tempx, tempy, [BotActions.TAKE_FROM_COUNTER,currUsefulNeighbor[1]], 2])
                                    else:
                                        legal_moves.append([nx, ny, [BotActions.TAKE_FROM_COUNTER,currUsefulNeighbor[1]], 4])
                                    
                                    if (updatedNeighborTile.item is Food and updatedNeighborTile.item.can_chop):
                                        if dx == dy == 0:
                                            legal_moves.append([nx, ny, [BotActions.CHOP,currUsefulNeighbor[1]], 3])

                                            actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                                            for i in range(len(actions)):
                                                adx, ady = actions[i]
                                                tempx, tempy = nx + adx, ny + ady
                                                if 0 <= tempx < len(controller.get_map(controller.get_team()).tiles) and 0 <= tempy < len(controller.get_map(controller.get_team()).tiles[0]):
                                                    if controller.get_map(controller.get_team()).is_tile_walkable(tempx, tempy):
                                                        legal_moves.append([tempx, tempy, [BotActions.CHOP,currUsefulNeighbor[1]], 2])
                                        else:
                                            legal_moves.append([nx, ny, [BotActions.CHOP,currUsefulNeighbor[1]], 4])

                                            
                                if updatedNeighborTile.item is None and itemInHand is not None:
                                    if dx == dy == 0:
                                        legal_moves.append([nx, ny, [BotActions.PLACE_ITEM,currUsefulNeighbor[1]], 3])

                                        actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                                        for i in range(len(actions)):
                                            adx, ady = actions[i]
                                            tempx, tempy = nx + adx, ny + ady
                                            if 0 <= tempx < len(controller.get_map(controller.get_team()).tiles) and 0 <= tempy < len(controller.get_map(controller.get_team()).tiles[0]):
                                                if controller.get_map(controller.get_team()).is_tile_walkable(tempx, tempy):
                                                    legal_moves.append([tempx, tempy, [BotActions.PLACE_ITEM,currUsefulNeighbor[1]], 2])
                                    else:
                                        legal_moves.append([nx, ny, [BotActions.PLACE_ITEM,currUsefulNeighbor[1]], 4])
                            
                            case "SINKTABLE":
                                if (updatedNeighborTile.num_clean_plates > 0 and itemInHand == None):
                                    if dx == dy == 0:
                                        legal_moves.append([nx, ny, [BotActions.TAKE_CLEAN_PLATE,currUsefulNeighbor[1]], 3])
                                        
                                        actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                                        for i in range(len(actions)):
                                            adx, ady = actions[i]
                                            tempx, tempy = nx + adx, ny + ady
                                            if 0 <= tempx < len(controller.get_map(controller.get_team()).tiles) and 0 <= tempy < len(controller.get_map(controller.get_team()).tiles[0]):
                                                if controller.get_map(controller.get_team()).is_tile_walkable(tempx, tempy):
                                                    legal_moves.append([tempx, tempy, [BotActions.TAKE_CLEAN_PLATE,currUsefulNeighbor[1]], 2])
                                    else:
                                        legal_moves.append([nx, ny, [BotActions.TAKE_CLEAN_PLATE,currUsefulNeighbor[1]], 4])
                                        
                                
                            case "COOKER":
                                #might error here with cooking progress
                                if (updatedNeighborTile.item is not None and updatedNeighborTile.item["type"] == "Food" and itemInHand is None):
                                    if dx == dy == 0:
                                        legal_moves.append([nx, ny, [BotActions.TAKE_FROM_PAN,currUsefulNeighbor[1]], 3])
                                        
                                        actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                                        for i in range(len(actions)):
                                            adx, ady = actions[i]
                                            tempx, tempy = nx + adx, ny + ady
                                            if 0 <= tempx < len(controller.get_map(controller.get_team()).tiles) and 0 <= tempy < len(controller.get_map(controller.get_team()).tiles[0]):
                                                if controller.get_map(controller.get_team()).is_tile_walkable(tempx, tempy):
                                                    legal_moves.append([tempx, tempy, [BotActions.TAKE_FROM_PAN,currUsefulNeighbor[1]], 2])
                                    else:
                                        legal_moves.append([nx, ny, [BotActions.TAKE_FROM_PAN,currUsefulNeighbor[1]], 4])
                                if (itemInHand["type"] == "Pan" and updatedNeighborTile.item is None):
                                    if dx == dy == 0:
                                        legal_moves.append([nx, ny, [BotActions.PLACE_ITEM,currUsefulNeighbor[1]], 3])

                                        actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                                        for i in range(len(actions)):
                                            adx, ady = actions[i]
                                            tempx, tempy = nx + adx, ny + ady
                                            if 0 <= tempx < len(controller.get_map(controller.get_team()).tiles) and 0 <= tempy < len(controller.get_map(controller.get_team()).tiles[0]):
                                                if controller.get_map(controller.get_team()).is_tile_walkable(tempx, tempy):
                                                    legal_moves.append((tempx, tempy, [BotActions.PLACE_ITEM,currUsefulNeighbor[1]], 2))
                                    else:
                                        legal_moves.append([nx, ny, [BotActions.PLACE_ITEM,currUsefulNeighbor[1]], 4])
                                
                                if (itemInHand is not None and itemInHand["type"] == "Food" and itemInHand['can_cook'] and updatedNeighborTile.item is not None and updatedNeighborTile.item["type"] == "Pan" and updatedNeighborTile.item["food"] is None):
                                    if dx == dy == 0:
                                        legal_moves.append([nx, ny, [BotActions.COOK,currUsefulNeighbor[1]], 3])

                                        actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                                        for i in range(len(actions)):
                                            adx, ady = actions[i]
                                            tempx, tempy = nx + adx, ny + ady
                                            if 0 <= tempx < len(controller.get_map(controller.get_team()).tiles) and 0 <= tempy < len(controller.get_map(controller.get_team()).tiles[0]):
                                                if controller.get_map(controller.get_team()).is_tile_walkable(tempx, tempy):
                                                    legal_moves.append([tempx, tempy, [BotActions.COOK,currUsefulNeighbor[1]], 2])
                                    else:
                                        legal_moves.append([nx, ny, [BotActions.COOK,currUsefulNeighbor[1]], 4])


                            case "TRASH":
                                if (itemInHand is not None and itemInHand["type"] == "Food"):
                                    if dx == dy == 0:
                                        legal_moves.append([nx, ny, [BotActions.TRASH,currUsefulNeighbor[1]], 3])

                                        actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                                        for i in range(len(actions)):
                                            adx, ady = actions[i]
                                            tempx, tempy = nx + adx, ny + ady
                                            if 0 <= tempx < len(controller.get_map(controller.get_team()).tiles) and 0 <= tempy < len(controller.get_map(controller.get_team()).tiles[0]):
                                                if controller.get_map(controller.get_team()).is_tile_walkable(tempx, tempy):
                                                    legal_moves.append([tempx, tempy, [BotActions.TRASH,currUsefulNeighbor[1]], 2])
                                    else:
                                        legal_moves.append([nx, ny, [BotActions.TRASH,currUsefulNeighbor[1]], 4])
                                if (itemInHand is not None and itemInHand["type"] == "Plate" and itemInHand['food'] != []):
                                    if dx == dy == 0:
                                        legal_moves.append([nx, ny, [BotActions.TRASH,currUsefulNeighbor[1]], 3])

                                        actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                                        for i in range(len(actions)):
                                            adx, ady = actions[i]
                                            tempx, tempy = nx + adx, ny + ady
                                            if 0 <= tempx < len(controller.get_map(controller.get_team()).tiles) and 0 <= tempy < len(controller.get_map(controller.get_team()).tiles[0]):
                                                if controller.get_map(controller.get_team()).is_tile_walkable(tempx, tempy):
                                                    legal_moves.append([tempx, tempy, [BotActions.TRASH,currUsefulNeighbor[1]], 2])
                                    else:
                                        legal_moves.append([nx, ny, [BotActions.TRASH,currUsefulNeighbor[1]], 4])
                                if (itemInHand is not None and itemInHand["type"] == "Pan" and itemInHand['food'] != None):
                                    if dx == dy == 0:
                                        legal_moves.append([nx, ny, [BotActions.TRASH,currUsefulNeighbor[1]], 3])

                                        actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                                        for i in range(len(actions)):
                                            adx, ady = actions[i]
                                            tempx, tempy = nx + adx, ny + ady
                                            if 0 <= tempx < len(controller.get_map(controller.get_team()).tiles) and 0 <= tempy < len(controller.get_map(controller.get_team()).tiles[0]):
                                                if controller.get_map(controller.get_team()).is_tile_walkable(tempx, tempy):
                                                    legal_moves.append([tempx, tempy, [BotActions.TRASH,currUsefulNeighbor[1]], 2])
                                    else:
                                        legal_moves.append([nx, ny, [BotActions.TRASH,currUsefulNeighbor[1]], 4])

                            case "SHOP":
                                if (controller.can_buy(bot_id, ShopCosts.PLATE, currUsefulNeighbor[1][0], currUsefulNeighbor[1][1])):
                                    if dx == dy == 0:
                                        legal_moves.append([nx, ny, [BotActions.BUY_PLATE,currUsefulNeighbor[1]], 3])
                                        
                                        actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                                        for i in range(len(actions)):
                                            adx, ady = actions[i]
                                            tempx, tempy = nx + adx, ny + ady
                                            if 0 <= tempx < len(controller.get_map(controller.get_team()).tiles) and 0 <= tempy < len(controller.get_map(controller.get_team()).tiles[0]):
                                                if controller.get_map(controller.get_team()).is_tile_walkable(tempx, tempy):
                                                    legal_moves.append([tempx, tempy, [BotActions.BUY_PLATE,currUsefulNeighbor[1]], 2])
                                    else:
                                        legal_moves.append([nx, ny, [BotActions.BUY_PLATE,currUsefulNeighbor[1]], 4])

                                if (controller.can_buy(bot_id, ShopCosts.PAN, currUsefulNeighbor[1][0], currUsefulNeighbor[1][1])):
                                
                                    if dx == dy == 0:
                                        legal_moves.append([nx, ny, [BotActions.BUY_PAN,currUsefulNeighbor[1]], 3])
                                        
                                        actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                                        for i in range(len(actions)):
                                            adx, ady = actions[i]
                                            tempx, tempy = nx + adx, ny + ady
                                            if 0 <= tempx < len(controller.get_map(controller.get_team()).tiles) and 0 <= tempy < len(controller.get_map(controller.get_team()).tiles[0]):
                                                if controller.get_map(controller.get_team()).is_tile_walkable(tempx, tempy):
                                                    legal_moves.append([tempx, tempy, [BotActions.BUY_PAN,currUsefulNeighbor[1]], 2])
                                    else:
                                        legal_moves.append([nx, ny, [BotActions.BUY_PAN,currUsefulNeighbor[1]], 4])
                                
                                if (controller.can_buy(bot_id, ShopCosts.EGG, currUsefulNeighbor[1][0], currUsefulNeighbor[1][1])):
                                
                                    if dx == dy == 0:
                                        legal_moves.append([nx, ny, [BotActions.BUY_EGG,currUsefulNeighbor[1]], 3])
                                        
                                        actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                                        for i in range(len(actions)):
                                            adx, ady = actions[i]
                                            tempx, tempy = nx + adx, ny + ady
                                            if 0 <= tempx < len(controller.get_map(controller.get_team()).tiles) and 0 <= tempy < len(controller.get_map(controller.get_team()).tiles[0]):
                                                if controller.get_map(controller.get_team()).is_tile_walkable(tempx, tempy):
                                                    legal_moves.append([tempx, tempy, [BotActions.BUY_EGG,currUsefulNeighbor[1]], 2])
                                    else:
                                        legal_moves.append([nx, ny, [BotActions.BUY_EGG,currUsefulNeighbor[1]], 4])

                                if (controller.can_buy(bot_id, ShopCosts.ONION, currUsefulNeighbor[1][0], currUsefulNeighbor[1][1])):
                                
                                    if dx == dy == 0:
                                        legal_moves.append([nx, ny, [BotActions.BUY_ONION,currUsefulNeighbor[1]], 3])
                                        
                                        actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                                        for i in range(len(actions)):
                                            adx, ady = actions[i]
                                            tempx, tempy = nx + adx, ny + ady
                                            if 0 <= tempx < len(controller.get_map(controller.get_team()).tiles) and 0 <= tempy < len(controller.get_map(controller.get_team()).tiles[0]):
                                                if controller.get_map(controller.get_team()).is_tile_walkable(tempx, tempy):
                                                    legal_moves.append([tempx, tempy, [BotActions.BUY_ONION,currUsefulNeighbor[1]], 2])
                                    else:
                                        legal_moves.append([nx, ny, [BotActions.BUY_ONION,currUsefulNeighbor[1]], 4])
                                
                                if (controller.can_buy(bot_id, ShopCosts.MEAT, currUsefulNeighbor[1][0], currUsefulNeighbor[1][1])):
                                
                                    if dx == dy == 0:
                                        legal_moves.append([nx, ny, [BotActions.BUY_MEAT,currUsefulNeighbor[1]], 3])
                                        #please work
                                        actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                                        for i in range(len(actions)):
                                            adx, ady = actions[i]
                                            tempx, tempy = nx + adx, ny + ady
                                            if 0 <= tempx < len(controller.get_map(controller.get_team()).tiles) and 0 <= tempy < len(controller.get_map(controller.get_team()).tiles[0]):
                                                if controller.get_map(controller.get_team()).is_tile_walkable(tempx, tempy):
                                                    legal_moves.append([tempx, tempy, [BotActions.BUY_MEAT,currUsefulNeighbor[1]], 2])
                                    else:
                                        legal_moves.append([nx, ny, [BotActions.BUY_MEAT,currUsefulNeighbor[1]], 4])
                                
                                if (controller.can_buy(bot_id, ShopCosts.NOODLES, currUsefulNeighbor[1][0], currUsefulNeighbor[1][1])):
                                
                                    if dx == dy == 0:
                                        legal_moves.append([nx, ny, [BotActions.BUY_NOODLES,currUsefulNeighbor[1]], 3])
                                        
                                        actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                                        for i in range(len(actions)):
                                            adx, ady = actions[i]
                                            tempx, tempy = nx + adx, ny + ady
                                            if 0 <= tempx < len(controller.get_map(controller.get_team()).tiles) and 0 <= tempy < len(controller.get_map(controller.get_team()).tiles[0]):
                                                if controller.get_map(controller.get_team()).is_tile_walkable(tempx, tempy):
                                                    legal_moves.append([tempx, tempy, [BotActions.BUY_NOODLES,currUsefulNeighbor[1]], 2])
                                    else:
                                        legal_moves.append([nx, ny, [BotActions.BUY_NOODLES,currUsefulNeighbor[1]], 4])
                                
                                if (controller.can_buy(bot_id, ShopCosts.SAUCE, currUsefulNeighbor[1][0], currUsefulNeighbor[1][1])):
                                
                                    if dx == dy == 0:
                                        legal_moves.append([nx, ny, [BotActions.BUY_SAUCE,currUsefulNeighbor[1]], 3])
                                        
                                        actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                                        for i in range(len(actions)):
                                            adx, ady = actions[i]
                                            tempx, tempy = nx + adx, ny + ady
                                            if 0 <= tempx < len(controller.get_map(controller.get_team()).tiles) and 0 <= tempy < len(controller.get_map(controller.get_team()).tiles[0]):
                                                if controller.get_map(controller.get_team()).is_tile_walkable(tempx, tempy):
                                                    legal_moves.append([tempx, tempy, [BotActions.BUY_SAUCE,currUsefulNeighbor[1]], 2])
                                    else:
                                        legal_moves.append([nx, ny, [BotActions.BUY_SAUCE,currUsefulNeighbor[1]], 4])



                            case "BOX":
                                if itemInHand is None and updatedNeighborTile.item is not None:
                                    if dx == dy == 0:
                                        legal_moves.append([nx, ny, [BotActions.PICKUP,currUsefulNeighbor[1]], 3])
                                        
                                        actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                                        for i in range(len(actions)):
                                            adx, ady = actions[i]
                                            tempx, tempy = nx + adx, ny + ady
                                            if 0 <= tempx < len(controller.get_map(controller.get_team()).tiles) and 0 <= tempy < len(controller.get_map(controller.get_team()).tiles[0]):
                                                if controller.get_map(controller.get_team()).is_tile_walkable(tempx, tempy):
                                                    legal_moves.append([tempx, tempy, [BotActions.PICKUP,currUsefulNeighbor[1]], 2])
                                    else:
                                        legal_moves.append([nx, ny, [BotActions.PICKUP,currUsefulNeighbor[1]], 4])


                                if itemInHand is not None and itemInHand["type"] == "Plate" and updatedNeighborTile.item is not None and (itemInHand['dirty'] == False or itemInHand["food"] != []):
                                    if dx == dy == 0:
                                        legal_moves.append([nx, ny, [BotActions.FOOD_TO_PLATE,currUsefulNeighbor[1]], 3])
                                        
                                        actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                                        for i in range(len(actions)):
                                            adx, ady = actions[i]
                                            tempx, tempy = nx + adx, ny + ady
                                            if 0 <= tempx < len(controller.get_map(controller.get_team()).tiles) and 0 <= tempy < len(controller.get_map(controller.get_team()).tiles[0]):
                                                if controller.get_map(controller.get_team()).is_tile_walkable(tempx, tempy):
                                                    legal_moves.append([tempx, tempy, [BotActions.FOOD_TO_PLATE,currUsefulNeighbor[1]], 2])
                                    else:
                                        legal_moves.append([nx, ny, [BotActions.FOOD_TO_PLATE,currUsefulNeighbor[1]], 4])


                                        
                                if itemInHand is not None and (updatedNeighborTile.item is None or itemInHand["type"] ==  updatedNeighborTile.item['type']):
                                    if dx == dy == 0:
                                        legal_moves.append([nx, ny, [BotActions.PLACE_ITEM,currUsefulNeighbor[1]], 3])
                                        
                                        actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                                        for i in range(len(actions)):
                                            adx, ady = actions[i]
                                            tempx, tempy = nx + adx, ny + ady
                                            if 0 <= tempx < len(controller.get_map(controller.get_team()).tiles) and 0 <= tempy < len(controller.get_map(controller.get_team()).tiles[0]):
                                                if controller.get_map(controller.get_team()).is_tile_walkable(tempx, tempy):
                                                    legal_moves.append([tempx, tempy, [BotActions.PLACE_ITEM,currUsefulNeighbor[1]], 2])
                                    else:
                                        legal_moves.append([nx, ny, [BotActions.PLACE_ITEM,currUsefulNeighbor[1]], 4])

                            case "SUBMIT":
                                if (itemInHand is not None and itemInHand["type"] == "Plate" and itemInHand['dirty'] == False):
                                    if dx == dy == 0:
                                        legal_moves.append([nx, ny, [BotActions.SUBMIT,currUsefulNeighbor[1]], 3])
                                        
                                        actions = [(0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1), (-1,0), (-1,1)]
                                        for i in range(len(actions)):
                                            adx, ady = actions[i]
                                            tempx, tempy = nx + adx, ny + ady
                                            if 0 <= tempx < len(controller.get_map(controller.get_team()).tiles) and 0 <= tempy < len(controller.get_map(controller.get_team()).tiles[0]):
                                                if controller.get_map(controller.get_team()).is_tile_walkable(tempx, tempy):
                                                    legal_moves.append([tempx, tempy, [BotActions.SUBMIT,currUsefulNeighbor[1]], 2])
                                    else:
                                        legal_moves.append([nx, ny, [BotActions.SUBMIT,currUsefulNeighbor[1]], 4])
                            
                            case _:
                                print("UNKNOWN TILE TYPE THATS WEIRDDDDDDD")

                        
                    else:
                        legal_moves.append([nx, ny, [BotActions.NONE, [0,0]], 0])
                        continue
                #nx, ny = x + dx, y + dy
                if controller.get_map(controller.get_team()).is_tile_walkable(nx, ny):
                    legal_moves.append([nx, ny, [BotActions.NONE, [0,0]], 1])
            

                        
        print(legal_moves)
        return legal_moves

    def legal_moves(self, controller: RobotController):
        legal1 = self.get_legal_moves_per_bot(controller, controller.get_team_bot_ids(controller.get_team())[0])
        legal2 = self.get_legal_moves_per_bot(controller, controller.get_team_bot_ids(controller.get_team())[1])

        joint_moves = []

        for m1, m2 in product(legal1, legal2):

            # --- Rule 1: cannot move to same tile ---
            if m1[0] == m2[0] and m1[1] == m2[1]:
                continue

            # --- Rule 2: cannot act on same target tile ---
            # Some actions might not have a meaningful target
            target1 = m1[2][1] if m1[2][0] != BotActions.NONE else None
            target2 = m2[2][1] if m2[2][0] != BotActions.NONE else None

            if target1 is not None and target1 == target2:
                continue

            joint_moves.append([m1, m2])

        return joint_moves
    #retList = [[bot1_action1, bot1_action2, ...], [bot2_action1, bot2_action2, ...], ...]
 


    def make_move(self, controller: RobotController, move):
        for x in range(2):
            curr_move = move[x]
            bot_id = controller.get_team_bot_ids(controller.get_team())[x]

            x,y = controller.get_bot_position(bot_id)

            if (curr_move[3] == 0):
                break

            elif (curr_move[3] == 1):
                if not controller.can_move(bot_id,  curr_move[0] - x, curr_move[1] - y):
                            print(f"WHATTTTT Bot {bot_id} cannot move to ({curr_move[0]}, {curr_move[1]})")
                else:
                    controller.move_bot(bot_id,  curr_move[0] - x, curr_move[1] - y)
            else:
                if(curr_move[3] == 4):
                    if not controller.can_move(bot_id,  curr_move[0] - x, curr_move[1] - y):
                        print(f"WHATTTTT Bot {bot_id} cannot move to ({curr_move[0]}, {curr_move[1]})")
                    else:
                        controller.move_bot(bot_id,  curr_move[0] - x, curr_move[1] - y)
                # create casing


                #action = curr_move[2] = [BotActions.ACTION, [target_x, target_y]], where
                # target x, target y is the tile the action is being performed on (eg sink coord)
                # just need to run actionfunction based on what enum is at the target coords 
                # curr_move[2[1]] = [target_x, target_y]


                match curr_move[2][0]:
                    case BotActions.NONE:
                        pass  # no-op / wait

                    case BotActions.COOK:
                        controller.cook(bot_id, curr_move[2][1][0], curr_move[2][1][1])
                        

                    case BotActions.CHOP:
                        # handle chop
                        ...
                        controller.chop(bot_id, curr_move[2][1][0], curr_move[2][1][1])

                    case BotActions.BUY_PLATE:
                        # handle buy plate
                        controller.buy(bot_id, curr_move[2][1][0], curr_move[2][1][1], FoodType.PLATE)
                        ...

                    case BotActions.BUY_PAN:
                        # handle buy pan
                        controller.buy(bot_id, curr_move[2][1][0], curr_move[2][1][1], FoodType.PAN)
                        ...

                    case BotActions.BUY_EGG:
                        # handle buy egg
                        controller.buy(bot_id, curr_move[2][1][0], curr_move[2][1][1], FoodType.EGG)
                        ...

                    case BotActions.BUY_ONION:
                        # handle buy onion
                        controller.buy(bot_id, curr_move[2][1][0], curr_move[2][1][1], FoodType.ONION)
                        ...

                    case BotActions.BUY_MEAT:
                        # handle buy meat
                        controller.buy(bot_id, curr_move[2][1][0], curr_move[2][1][1], FoodType.MEAT)
                        ...

                    case BotActions.BUY_NOODLES:
                        # handle buy noodles
                        controller.buy(bot_id, curr_move[2][1][0], curr_move[2][1][1], FoodType.NOODLES)
                        ...

                    case BotActions.BUY_SAUCE:
                        # handle buy sauce
                        controller.buy(bot_id, curr_move[2][1][0], curr_move[2][1][1], FoodType.SAUCE)
                        ...

                    case BotActions.PICKUP:
                        controller.pickup(bot_id, curr_move[2][1][0], curr_move[2][1][1])
                        ...

                    case BotActions.PLACE_ITEM:
                        controller.place(bot_id, curr_move[2][1][0], curr_move[2][1][0])
                        ...

                    case BotActions.TRASH:
                        controller.trash(bot_id, curr_move[2][1][0], curr_move[2][1][0])

                        ...

                    case BotActions.TAKE_FROM_COUNTER:
                        controller.pickup(bot_id, curr_move[2][1][0], curr_move[2][1][1])
                        ...

                    case BotActions.TAKE_FROM_PAN:
                        # handle take from pan
                        controller.take_from_pan(bot_id, curr_move[2][1][0], curr_move[2][1][1])

                    case BotActions.TAKE_CLEAN_PLATE:
                        # handle take clean plate
                        controller.take_clean_plate(bot_id, curr_move[2][1][0], curr_move[2][1][1])

                    case BotActions.PUT_DIRTY_PLATE:
                        # handle put dirty plate
                        controller.put_dirty_plate_in_sink(bot_id, curr_move[2][1][0], curr_move[2][1][1])

                    case BotActions.WASH_SINK:
                        # handle wash sink
                        controller.wash_sink(bot_id, curr_move[2][1][0], curr_move[2][1][1])

                    case BotActions.FOOD_TO_PLATE:
                        # handle food to plate
                        controller.add_food_to_plate(bot_id, curr_move[2][1][0], curr_move[2][1][1])

                    case BotActions.SUBMIT:
                        # handle submit
                        controller.submit(bot_id, curr_move[2][1][0], curr_move[2][1][1])

                    case _:
                        raise ValueError(f"Unhandled BotAction: {curr_move[2][0]}")
                    
                if (curr_move[3] == 2):
                    if not controller.can_move(bot_id,  curr_move[0] - x, curr_move[1] - y):
                        print(f"WHATTTTT Bot {bot_id} cannot move to ({curr_move[0]}, {curr_move[1]})")
                    else:
                        controller.move_bot(bot_id,  curr_move[0] - x, curr_move[1] - y)

             
                    #create cases by enum action



        

    def is_game_over(self, controller: RobotController):
        if controller.get_turn() >= 250:
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
        if controller.get_team() == Team.RED:
            print(self.get_legal_moves_per_bot(controller, controller.get_team_bot_ids(controller.get_team())[1]))
        print('-----')
   