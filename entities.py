from __future__ import annotations
import copy
import math
from typing import Optional, Tuple, Type, TypeVar, TYPE_CHECKING, Union
from render_order import RenderOrder
if TYPE_CHECKING:
    from components.consumable import Consumable
    from components.ai import BaseAI
    from components.fighter import Fighter
    from components.inventory import Inventory
    from components.equippable import Equippable
    from components.equipment import Equipment
    from map import DungeonMap
    from components.level import Level

T = TypeVar("T", bound = "Entity")
# Class for all entities including player, items, enemies, and others
class Entity:
    parent: Union[DungeonMap, Inventory]
    def __init__(self, parent: Optional[DungeonMap] = None, x: int = 0, y: int = 0, 
                 char: str = "?", color: Tuple[int, int, int] = (255, 255, 255), 
                 name: str = "<Unnamed>", blocks_movement: bool = False, render_order: RenderOrder = RenderOrder.CORPSE,):
        
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.name = name
        self.blocks_movement = blocks_movement
        self.render_order = render_order
        if parent:
            # If parent isn't provided now then it will be set later.
            self.parent = parent
            parent.entities.add(self)
            
    @property
    def dungeon_map(self) -> DungeonMap:
        return self.parent.dungeon_map
            
    def spawn(self: T, dungeon_map: DungeonMap, x: int, y: int) -> T:
        clone = copy.deepcopy(self)
        clone.x = x
        clone.y = y
        clone.parent = dungeon_map
        dungeon_map.entities.add(clone)
        return clone
    
    def place(self, x: int, y: int, dungeon_map: Optional[DungeonMap] = None) -> None:
        self.x = x
        self.y = y
        if dungeon_map:
            if hasattr(self, "parent"):  # Possibly uninitialized.
                if self.parent is self.dungeon_map:
                    self.dungeon_map.entities.remove(self)
            self.parent = dungeon_map
            dungeon_map.entities.add(self)
    
    def distance(self, x: int, y: int) -> float:
        """
        Return the distance between the current entity and the given (x, y) coordinate.
        """
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)
            
    def move(self, dx: int, dy: int) -> None:
        self.x += dx
        self.y += dy

class Actor(Entity):
    def __init__(
        self,
        *,
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str = "<Unnamed>",
        ai_cls: Type[BaseAI],
        fighter: Fighter,
        inventory: Inventory,
        equipment: Equipment,
        level: Level,
    ):
        super().__init__(
            x = x,
            y = y,
            char = char,
            color = color,
            name = name,
            blocks_movement = True,
            render_order = RenderOrder.ACTOR,
        )

        self.ai: Optional[BaseAI] = ai_cls(self)
        self.fighter = fighter
        self.fighter.parent = self
        self.inventory = inventory
        self.inventory.parent = self
        self.equipment: Equipment = equipment
        self.equipment.parent = self
        self.level = level
        self.level.parent = self

    @property
    def is_alive(self) -> bool:
        """Returns True as long as this actor can perform actions."""
        return bool(self.ai) 

class Item(Entity):
    def __init__(
        self,
        *,
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str = "<Unnamed>",
        consumable: Optional[Consumable] = None,
        equippable: Optional[Equippable] = None,
    ):
        super().__init__(
            x = x,
            y = y,
            char = char,
            color = color,
            name = name,
            blocks_movement = False,
            render_order = RenderOrder.ITEM,
        )

        self.consumable = consumable
        if self.consumable:
            self.consumable.parent = self

        self.equippable = equippable
        if self.equippable:
            self.equippable.parent = self