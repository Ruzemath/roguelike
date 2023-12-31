from __future__ import annotations
from typing import List, TYPE_CHECKING
from components.base_component import BaseComponent
if TYPE_CHECKING:
    from entities import Actor, Item


class Inventory(BaseComponent):
    parent: Actor

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.items: List[Item] = []

    def drop(self, item: Item) -> None:
        """
        Removes an item from the inventory and restores it to the game map, at the player's current location.
        """
        self.items.remove(item)
        item.place(self.parent.x, self.parent.y, self.dungeon_map)

        self.generate.message_log.add_message(f"You dropped the {item.name}.", fg = item.color)