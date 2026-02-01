import random
from collections import deque
from typing import Tuple, Optional, List
from enum import Enum

from game_constants import Team, TileType, FoodType, ShopCosts
from robot_controller import RobotController
from item import Pan, Plate, Food


# class BotActions(Enum):
#     NONE = 0
#     COOK_EGG = 1
#     COOK_MEAT = 2
#     CHOP_ONION = 3
#     CHOP_MEAT = 4
#     BUY_PLATE = 5
#     BUY_PAN = 6
#     THROW_TRASH = 7
#     BUY_EGG =10
#     BUY_ONION =11
#     BUY_MEAT =12
#     BUY_NOODLES =13
#     BUY_SAUCE =14
#     PICKUP_ITEM = 15
#     PLACE_ITEM = 16

class BotPlayer:
    def __init__(self, map_copy):
        self.map = map_copy
        self.assembly_counter = None 
        self.cooker_loc = None
        self.my_bot_id = None
        self.megaDict = {}
        
        self.state = 0

 
    def play_turn(self, controller: RobotController):

        bot1 = controller.get_team_bot_ids(controller.get_team())[1]
        # print(controller.can_buy(bot1, "PAN"))

        if(controller.get_turn() == 20):
            controller.move(bot1, 0, 1)
        elif(controller.get_turn() == 30):
            controller.move(bot1, 0, 1)
        elif(controller.get_turn() == 40):
            controller.move(bot1, 1, 0)
        elif(controller.get_turn() == 50):
            controller.move(bot1, 1, 0)
        elif(controller.get_turn() == 60):
            controller.move(bot1, 0, 1)
        elif(controller.get_turn() == 80):
            controller.buy(bot1, FoodType.NOODLES)
            print(controller.get_bot_state(bot1))
        # elif(controller.get_turn() == 50):
        #     controller.buy(bot1, "NOODLES")


