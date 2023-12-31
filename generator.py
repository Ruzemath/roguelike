from __future__ import annotations
from typing import TYPE_CHECKING
from tcod.console import Console
from tcod.map import compute_fov
import render_functions
from message_log import MessageLog
import exceptions
import lzma
import pickle
if TYPE_CHECKING:
    from entities import Actor
    from map import DungeonMap, GameWorld
    
class Generator:
    dungeon_map: DungeonMap
    game_world: GameWorld
    
    def __init__(self, player: Actor):
        self.player = player
        self.message_log = MessageLog()
        self.mouse_location = (0, 0)
        
    def handle_monster_turns(self) -> None:
        for entity in set(self.dungeon_map.actors) - {self.player}:
            if entity.ai:
                try:
                    entity.ai.act()
                except exceptions.Impossible:
                    pass  # Ignore impossible action exceptions from AI.
             
    
    def update(self) -> None: # Updates the fov of the player
        self.dungeon_map.visible[:] = compute_fov(
            self.dungeon_map.tiles["transparent"],
            (self.player.x, self.player.y),
            radius = 8,
        )
        # If a tile is in FOV it should be seen as encountered too.
        self.dungeon_map.encountered |= self.dungeon_map.visible
        
    def make(self, console: Console) -> None:
        self.dungeon_map.make(console)
        self.message_log.render(console, x = 21, y = 45, width = 40, height = 5)
        
        render_functions.render_bar(
            console = console,
            current_value = self.player.fighter.hp,
            maximum_value = self.player.fighter.max_hp,
            total_width = 20,
        )
        
        render_functions.render_dungeon_level(
            console = console,
            dungeon_level = self.game_world.current_floor,
            location = (0, 47),
        )

        render_functions.render_names_at_mouse_location(
            console = console, x = 21, y = 44, generator = self
        )
        
    def save_as(self, filename: str) -> None:
        """Save this Generator instance as a compressed file."""
        save_data = lzma.compress(pickle.dumps(self))
        with open(filename, "wb") as f:
            f.write(save_data)