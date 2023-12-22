import numpy as np  
from tcod.console import Console
import tile_types


class DungeonMap:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.tiles = np.full((width, height), fill_value = tile_types.wall, order = "F")
        self.visible = np.full((width, height), fill_value = False, order = "F")
        self.encountered = np.full((width, height), fill_value = False, order = "F")

    def bounds_check(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def make(self, console: Console) -> None:
        console.rgb[0:self.width, 0:self.height] = np.select(
            condlist = [self.visible, self.encountered],
            choicelist = [self.tiles["light"], self.tiles["dark"]],
            default = tile_types.VOID
        )