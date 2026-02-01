import random
from collections import deque
from typing import Dict, List, Tuple, Optional
from game_constants import Team, TileType, ShopCosts, FoodType
from robot_controller import RobotController


class BotPlayer:
    def __init__(self, map_copy):
        self.map = map_copy
        self.megaDict = {}
        self.tile_locations = {}
        self.initialized = False
        self.bot_assignments = {}  # bot_id -> order they're working on
        self.current_orders = []

    def getMegaDict(self, controller: RobotController):
        """Build a dictionary of walkable tiles adjacent to functional tiles"""
        megaDict = self.megaDict
        currmap = controller.get_map(controller.get_team()).tiles
        
        for x in range(len(currmap)):
            for y in range(len(currmap[0])):
                curr_tile = controller.get_tile(controller.get_team(), x, y)
                if curr_tile is not None and curr_tile.tile_name not in ["FLOOR", "WALL"]:
                    if curr_tile.tile_name not in self.tile_locations:
                        self.tile_locations[curr_tile.tile_name] = []
                    self.tile_locations[curr_tile.tile_name].append((x, y))
                    
                    for dx, dy in [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < len(currmap) and 0 <= ny < len(currmap[0]):
                            neighbor_tile = controller.get_tile(controller.get_team(), nx, ny)
                            if neighbor_tile is not None and neighbor_tile.tile_name == "FLOOR":
                                if (nx, ny) not in megaDict:
                                    megaDict[(nx, ny)] = []
                                if not any(t[0].tile_name == curr_tile.tile_name for t in megaDict[(nx, ny)]):
                                    megaDict[(nx, ny)].append((curr_tile, (x, y)))
        
        self.megaDict = megaDict
        self.initialized = True

    def move_bot(self, controller: RobotController, bot_id: int, target_x: int, target_y: int):
        """Move bot one step towards target"""
        bot_state = controller.get_bot_state(bot_id)
        bot_x, bot_y = bot_state['x'], bot_state['y']
        
        dx = 0 if bot_x == target_x else (1 if target_x > bot_x else -1)
        dy = 0 if bot_y == target_y else (1 if target_y > bot_y else -1)
        
        if controller.can_move(bot_id, dx, dy):
            controller.move(bot_id, dx, dy)
            return True
        
        if dx != 0 and controller.can_move(bot_id, dx, 0):
            controller.move(bot_id, dx, 0)
            return True
        
        if dy != 0 and controller.can_move(bot_id, 0, dy):
            controller.move(bot_id, 0, dy)
            return True
        
        return False

    def is_adjacent(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        """Check if two positions are adjacent"""
        return abs(x1 - x2) <= 1 and abs(y1 - y2) <= 1

    def find_closest(self, controller: RobotController, bot_id: int, tile_name: str):
        """Find closest tile of given type"""
        if tile_name not in self.tile_locations:
            return None
        
        bot_state = controller.get_bot_state(bot_id)
        bot_x, bot_y = bot_state['x'], bot_state['y']
        
        closest = None
        min_dist = float('inf')
        
        for tx, ty in self.tile_locations[tile_name]:
            dist = abs(tx - bot_x) + abs(ty - bot_y)
            if dist < min_dist:
                min_dist = dist
                closest = (tx, ty)
        
        return closest

    def get_best_order(self, controller: RobotController):
        """Get best available order"""
        orders = controller.get_orders(controller.get_team())
        active = [o for o in orders if o['is_active'] and not o['completed_turn']]
        if not active:
            return None
        return max(active, key=lambda o: o['reward'])

    def simple_strategy(self, controller: RobotController, bot_id: int):
        """Simple strategy: just get plates and put any food on them"""
        bot_state = controller.get_bot_state(bot_id)
        holding = bot_state['holding']
        bot_x, bot_y = bot_state['x'], bot_state['y']
        
        # Not holding anything
        if holding is None:
            # Get a plate
            sink_table = self.find_closest(controller, bot_id, 'SINKTABLE')
            if sink_table:
                sink_tile = controller.get_tile(controller.get_team(), sink_table[0], sink_table[1])
                if sink_tile and sink_tile.num_clean_plates > 0:
                    if self.is_adjacent(bot_x, bot_y, sink_table[0], sink_table[1]):
                        controller.take_clean_plate(bot_id, sink_table[0], sink_table[1])
                        return
                    else:
                        self.move_bot(controller, bot_id, sink_table[0], sink_table[1])
                        return
            
            # Wash dirty plates
            sink = self.find_closest(controller, bot_id, 'SINK')
            if sink:
                sink_tile = controller.get_tile(controller.get_team(), sink[0], sink[1])
                if sink_tile and sink_tile.num_dirty_plates > 0:
                    if self.is_adjacent(bot_x, bot_y, sink[0], sink[1]):
                        controller.wash_sink(bot_id, sink[0], sink[1])
                        return
                    else:
                        self.move_bot(controller, bot_id, sink[0], sink[1])
                        return
            
            # Wander
            dx, dy = random.choice([(-1,0),(1,0),(0,-1),(0,1)])
            if controller.can_move(bot_id, dx, dy):
                controller.move(bot_id, dx, dy)
            return
        
        # Holding a plate
        if holding.get('type') == 'Plate':
            if holding.get('dirty'):
                sink = self.find_closest(controller, bot_id, 'SINK')
                if sink and self.is_adjacent(bot_x, bot_y, sink[0], sink[1]):
                    controller.put_dirty_plate_in_sink(bot_id, sink[0], sink[1])
                elif sink:
                    self.move_bot(controller, bot_id, sink[0], sink[1])
                return
            
            foods = holding.get('food', [])
            
            # Has food - submit
            if len(foods) > 0:
                submit = self.find_closest(controller, bot_id, 'SUBMIT')
                if submit:
                    if self.is_adjacent(bot_x, bot_y, submit[0], submit[1]):
                        controller.submit(bot_id, submit[0], submit[1])
                    else:
                        self.move_bot(controller, bot_id, submit[0], submit[1])
                return
            
            # Need food - check boxes
            if 'BOX' in self.tile_locations:
                for bx, by in self.tile_locations['BOX']:
                    box_tile = controller.get_tile(controller.get_team(), bx, by)
                    if box_tile and box_tile.item is not None:
                        if self.is_adjacent(bot_x, bot_y, bx, by):
                            controller.add_food_to_plate(bot_id, bx, by)
                            return
                        else:
                            self.move_bot(controller, bot_id, bx, by)
                            return
            
            # Wander
            dx, dy = random.choice([(-1,0),(1,0),(0,-1),(0,1)])
            if controller.can_move(bot_id, dx, dy):
                controller.move(bot_id, dx, dy)
            return
        
        # Holding something else - trash it
        trash = self.find_closest(controller, bot_id, 'TRASH')
        if trash:
            if self.is_adjacent(bot_x, bot_y, trash[0], trash[1]):
                controller.trash(bot_id, trash[0], trash[1])
            else:
                self.move_bot(controller, bot_id, trash[0], trash[1])

    def play_turn(self, controller: RobotController):
        """Main turn logic"""
        if not self.initialized:
            self.getMegaDict(controller)
            print(f"Tiles found: {list(self.tile_locations.keys())}")
        
        team_bot_ids = controller.get_team_bot_ids(controller.get_team())
        
        # Check orders
        order = self.get_best_order(controller)
        if order and controller.get_turn() % 50 == 0:
            print(f"Turn {controller.get_turn()}: Current order requires {order['required']}, reward={order['reward']}")
        
        for bot_id in team_bot_ids:
            try:
                self.simple_strategy(controller, bot_id)
            except Exception as e:
                print(f"Bot {bot_id} error: {e}")
                dx, dy = random.choice([(-1,0),(1,0),(0,-1),(0,1)])
                if controller.can_move(bot_id, dx, dy):
                    controller.move(bot_id, dx, dy)