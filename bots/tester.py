from game_constants import TileType, FoodType, ShopCosts
from item import Item, Pan, Food, Plate


'''
Each class describes the current STATE of a tile.
Robot controller describes how the state changes through bot actions
'''


class Tile:
    def __init__(self, tile_type: TileType):
        self.tile_name = tile_type.tile_name
        self.tile_id = tile_type.tile_id
        self.is_walkable = tile_type.is_walkable
        self.is_dangerous = tile_type.is_dangerous
        self.is_placeable = tile_type.is_placeable
        self.is_interactable = tile_type.is_interactable

        self.item = None
        self.using = False

    def to_dict(self):
        return {
            "tile_name": self.tile_name,
            "is_walkable": self.is_walkable,
        }


class Placeable(Tile):
    def __init__(self, tile_type: TileType):
        super().__init__(tile_type)
        self.placeable = True


class Interactable(Tile):
    def __init__(self, tile_type: TileType):
        super().__init__(tile_type)
        self.placeable = True
        self.interactable = True


class Floor(Tile):
    def __init__(self):
        super().__init__(TileType.FLOOR)


class Wall(Tile):
    def __init__(self):
        super().__init__(TileType.WALL)


class Counter(Interactable):
    def __init__(self):
        super().__init__(TileType.COUNTER)
        self.item = None

    def to_dict(self):
        d = super().to_dict()
        d["item"] = self.item.to_dict() if self.item else None
        return d


class Box(Interactable):
    '''
    Ingredient-only storage.
    Bots cannot store plates or completed food here.
    '''
    def __init__(self):
        super().__init__(TileType.BOX)
        self.item = None
        self.count = 0

    def can_store(self, item):
        # Only raw food items allowed
        if item is None:
            return False

        # No plates, no pans
        if isinstance(item, Plate) or isinstance(item, Pan):
            return False

        # Must be a Food item
        if not isinstance(item, Food):
            return False

        return True

    def enforce_invar(self):
        if self.count <= 0:
            self.count = 0
            self.item = None

    def to_dict(self):
        d = super().to_dict()
        d["item"] = self.item.to_dict() if self.item else None
        d["count"] = self.count
        return d


class Sink(Interactable):
    def __init__(self):
        super().__init__(TileType.SINK)
        self.num_dirty_plates = 0
        self.curr_dirty_plate_progress = 0

    def to_dict(self):
        d = super().to_dict()
        d["num_dirty_plates"] = self.num_dirty_plates
        d["curr_dirty_plate_progress"] = self.curr_dirty_plate_progress
        d["using"] = self.using
        return d


class SinkTable(Interactable):
    def __init__(self):
        super().__init__(TileType.SINKTABLE)
        self.num_clean_plates = 0

    def to_dict(self):
        d = super().to_dict()
        d["num_clean_plates"] = self.num_clean_plates
        return d


class Cooker(Interactable):
    def __init__(self):
        super().__init__(TileType.COOKER)
        self.item = Pan()
        self.cook_progress = 0

    def to_dict(self):
        d = super().to_dict()
        d["item"] = self.item.to_dict() if self.item else None
        d["cook_progress"] = self.cook_progress
        return d


class Trash(Interactable):
    def __init__(self):
        super().__init__(TileType.TRASH)


class Submit(Interactable):
    '''
    ONLY tile that accepts completed recipes
    '''
    def __init__(self):
        super().__init__(TileType.SUBMIT)

    def can_submit(self, item):
        if item is None:
            return False

        # Must be a plate
        if not isinstance(item, Plate):
            return False

        # Plate must contain food
        if item.food is None:
            return False

        # Food must be cooked if applicable
        if hasattr(item.food, "is_cooked") and not item.food.is_cooked:
            return False

        return True

    def submit(self, item, team):
        '''
        Called by RobotController when a team submits food
        '''
        if not self.can_submit(item):
            return False

        food_name = item.food.food_type.name if hasattr(item.food, "food_type") else str(item.food)

        print(f"[SUBMIT] Team {team} submitted {food_name}")

        return True


class Shop(Interactable):
    def __init__(self):
        super().__init__(TileType.SHOP)
        self.shop_items = set()

        for food in FoodType:
            self.shop_items.add(food)
        for shop_item in ShopCosts:
            self.shop_items.add(shop_item)

    def to_dict(self):
        return super().to_dict()
