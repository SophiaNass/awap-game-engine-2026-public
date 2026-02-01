import random
from collections import deque, defaultdict
from typing import Tuple, Optional, List
from enum import Enum
from itertools import product
import numpy as np
import copy

from game_constants import Team, TileType, FoodType, ShopCosts
from robot_controller import RobotController
from item import Pan, Plate, Food

"""
Actions:


"""

import random
from collections import deque, defaultdict
from typing import Tuple, Optional, List
from enum import Enum
from itertools import product
import numpy as np
from game_constants import Team, TileType, FoodType, ShopCosts
from robot_controller import RobotController
from item import Pan, Plate, Food
import copy



class MonteCarloTreeSearchNode():
    def __init__(self, controller: RobotController, botPlayer: 'BotPlayer', parent=None, parent_action=None):
        self.botPlayer = botPlayer
        self.controller = controller
        self.parent = parent
        self.parent_action = parent_action
        self.children = []
        self._number_of_visits = 0
        self._results = defaultdict(int)
        self._results[1] = 0
        self._results[-1] = 0
        self._untried_actions = None
        self._untried_actions = self.untried_actions()
        return
    def untried_actions(self):
        self._untried_actions = self.botPlayer.legal_moves(self.controller)
        return self._untried_actions
    
    def q(self):
        wins = self._results[1]
        loses = self._results[-1]
        return wins - loses
    def n(self):
        return self._number_of_visits
    def expand(self):
        action = self._untried_actions.pop()
        new_controller = copy.deepcopy(self.controller)
        self.botPlayer.make_move(new_controller, action)
        child_node = MonteCarloTreeSearchNode(
            new_controller, 
            self.botPlayer,
            parent=self, 
            parent_action=action
        )
        self.children.append(child_node)
        return child_node
    

    def is_terminal_node(self):
        return self.botPlayer.is_game_over(self.controller)
    

    def rollout(self):
        rollout_controller = copy.deepcopy(self.controller)
        depth = 0
        max_depth = 4  # Limit rollout depth to prevent infinite loops
        while not self.botPlayer.is_game_over(rollout_controller) and depth < max_depth:
            # Get legal moves
            possible_moves = self.botPlayer.legal_moves(rollout_controller)
            
            if not possible_moves:
                break
            
            # Pick random move
            action = self.rollout_policy(possible_moves)
            
            # Apply it
            self.botPlayer.make_move(rollout_controller, action)
            
            depth += 1
        
        # Return game result (or heuristic if hit max depth)
        if depth >= max_depth:
            # Use heuristic evaluation instead of game_result
            return self.botPlayer.evaluate_state(rollout_controller)
        else:
            return self.botPlayer.game_result(rollout_controller)
            
    

    def backpropagate(self, result):
        self._number_of_visits += 1.
        self._results[result] += 1.
        if self.parent:
            self.parent.backpropagate(result)  

    def is_fully_expanded(self):
        return len(self._untried_actions) == 0 
    
    def best_child(self, c_param=0.1):
        choices_weights = [(c.q() / c.n()) + c_param * np.sqrt((2 * np.log(self.n()) / c.n())) for c in self.children]
        return self.children[np.argmax(choices_weights)]
        

    def rollout_policy(self, possible_moves):
        
        active_moves = [m for m in possible_moves if m[2][0] != BotActions.NONE]
        if len(active_moves)>0:
            return random.choice(active_moves)
        return random.choice(possible_moves)

                                
    def _tree_policy(self):
        current_node = self
        while not current_node.is_terminal_node():
            
            if not current_node.is_fully_expanded():
                return current_node.expand()
            else:
                current_node = current_node.best_child()
        return current_node

    def best_action(self, simulation_no = 100):
        
        
        for i in range(simulation_no):
            
            v = self._tree_policy()
            reward = v.rollout()
            v.backpropagate(reward)
        
        return self.best_child(c_param=0.)







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
        self.mcts_simulations = 8 


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
                        #print(currUsefulNeighbor[0].tile_name)
                        match currUsefulNeighbor[0].tile_name:
                            case "SINK":
                                if (itemInHand is not None and itemInHand["type"] == "Plate" and itemInHand['dirty'] == True):
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
                                    
                                    if (isinstance(updatedNeighborTile.item, Food) and updatedNeighborTile.item.can_chop):
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
                                if (updatedNeighborTile.item is not None and updatedNeighborTile.item.to_dict()["type"] == "Food" and itemInHand is None):
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
                                if (itemInHand is not None and itemInHand["type"] == "Pan" and updatedNeighborTile.item is None):
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
                                
                                if (controller.can_buy(bot_id, FoodType.EGG, currUsefulNeighbor[1][0], currUsefulNeighbor[1][1])):
                                
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

                                if (controller.can_buy(bot_id, FoodType.ONIONS, currUsefulNeighbor[1][0], currUsefulNeighbor[1][1])):
                                
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
                                
                                if (controller.can_buy(bot_id, FoodType.MEAT, currUsefulNeighbor[1][0], currUsefulNeighbor[1][1])):
                                
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
                                
                                if (controller.can_buy(bot_id, FoodType.NOODLES, currUsefulNeighbor[1][0], currUsefulNeighbor[1][1])):
                                
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
                                
                                if (controller.can_buy(bot_id, FoodType.SAUCE, currUsefulNeighbor[1][0], currUsefulNeighbor[1][1])):
                                
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


                                    
                                if itemInHand is not None and (updatedNeighborTile.item is None or itemInHand["type"] ==  updatedNeighborTile.item.to_dict()["type"]):
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
                    if(dx !=0 or dy !=0):
                        legal_moves.append([nx, ny, [BotActions.NONE, [0,0]], 1])
                

                        
        #print(legal_moves)
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
        start_positions = {}
        for bot_id in controller.get_team_bot_ids(controller.get_team()):
            state = controller.get_bot_state(bot_id)
            start_positions[bot_id] = (state['x'], state['y'])

        for n in range(2):
            curr_move = move[n]
            bot_id = controller.get_team_bot_ids(controller.get_team())[n]

            sx, sy = start_positions[bot_id]
            dx = curr_move[0] - sx
            dy = curr_move[1] - sy

            if (curr_move[3] == 0):
                continue

            elif (curr_move[3] == 1):
                if not controller.can_move(bot_id,  dx, dy):
                            print(f"WHATTTTT Bot {bot_id} at ({sx}, {sy})cannot move to ({curr_move[0]}, {curr_move[1]})")
                else:
                    controller.move(bot_id,  dx, dy)
            else:
                if(curr_move[3] == 4):
                    if not controller.can_move(bot_id,  dx, dy):
                        print(f"WHATTTTT Bot {bot_id} at ({sx}, {sy}) cannot move to ({curr_move[0]}, {curr_move[1]})")
                    else:
                        controller.move(bot_id,  dx, dy)
                
                match curr_move[2][0]:
                    case BotActions.NONE:
                        pass  # no-op / wait

                    case BotActions.COOK:
                        controller.start_cook(bot_id, curr_move[2][1][0], curr_move[2][1][1])
                        

                    case BotActions.CHOP:
                        # handle chop
                        
                        controller.chop(bot_id, curr_move[2][1][0], curr_move[2][1][1])

                    case BotActions.BUY_PLATE:
                        # handle buy plate
                        controller.buy(bot_id, FoodType.PLATE, curr_move[2][1][0], curr_move[2][1][1])

                    case BotActions.BUY_PAN:
                        # handle buy pan
                        controller.buy(bot_id, FoodType.PAN, curr_move[2][1][0], curr_move[2][1][1])
                        

                    case BotActions.BUY_EGG:
                        # handle buy egg
                        controller.buy(bot_id, FoodType.EGG, curr_move[2][1][0], curr_move[2][1][1])
                        

                    case BotActions.BUY_ONION:
                        # handle buy onion
                        controller.buy(bot_id, FoodType.ONIONS, curr_move[2][1][0], curr_move[2][1][1])
                        

                    case BotActions.BUY_MEAT:
                        # handle buy meat
                        controller.buy(bot_id, FoodType.MEAT, curr_move[2][1][0], curr_move[2][1][1])
                        

                    case BotActions.BUY_NOODLES:
                        # handle buy noodles
                        controller.buy(bot_id, FoodType.NOODLES, curr_move[2][1][0], curr_move[2][1][1])
                        

                    case BotActions.BUY_SAUCE:
                        # handle buy sauce
                        controller.buy(bot_id, FoodType.SAUCE, curr_move[2][1][0], curr_move[2][1][1])
                        

                    case BotActions.PICKUP:
                        controller.pickup(bot_id, curr_move[2][1][0], curr_move[2][1][1])
                        

                    case BotActions.PLACE_ITEM:
                        controller.place(bot_id, curr_move[2][1][0], curr_move[2][1][1])
                        

                    case BotActions.TRASH:
                        controller.trash(bot_id, curr_move[2][1][0], curr_move[2][1][1])
                        

                    case BotActions.TAKE_FROM_COUNTER:
                        controller.pickup(bot_id, curr_move[2][1][0], curr_move[2][1][1])
                        

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
                    if not controller.can_move(bot_id,  dx, dy):
                        print(f"WHATTTTT Bot {bot_id} at ({sx}, {sy})cannot move to ({dx}, {dy})")
                    else:
                        controller.move(bot_id,  dx, dy)

             
                    #create cases by enum action



        

    def is_game_over(self, controller: RobotController):
        if controller.get_turn() >= 500:
            return True
        return False
    
    def game_result(self, controller: RobotController):
        if self.is_game_over(controller):
            ours = controller.get_team_money(controller.get_team())
            theirs = controller.get_team_money(controller.get_enemy_team())
            if ours > theirs:
                return 1
            elif theirs > ours:
                return -1

            else:
                return 0
   
    def evaluate_state(self, controller: RobotController):
        """
        Heuristic evaluation for non-terminal states.
        Returns value in range [-1, 1] indicating how good the state is.
        """
        ours = controller.get_team_money(controller.get_team())
        theirs = controller.get_team_money(controller.get_enemy_team())
        
        money_diff = ours - theirs
        
        # Normalize to roughly [-1, 1]
        heuristic = max(-1.0, min(1.0, money_diff / 100.0))
        
        return heuristic

    def play_turn(self, controller: RobotController):
        if controller.get_turn() == 1:
           self.getMegaDict(controller)
         #print(f"Turn {controller.get_turn()}: Starting MCTS...")
                
                # Create root node with current controller state
        else: 
            new_controller = copy.deepcopy(controller)
            root_node = MonteCarloTreeSearchNode(controller=new_controller, botPlayer= self)
            
            
            # Run MCTS
            best_child = root_node.best_action(simulation_no=self.mcts_simulations)
            best_move = best_child.parent_action
            
            # Execute the best move on the REAL controller (only once!)
            self.make_move(controller, best_move)
            
        #print(f"MCTS done. Score: {best_child.q()}/{best_child.n()}")n mbjk
   