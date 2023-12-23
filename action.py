from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from generator import Generator
    from entities import Entity, Actor

class Action:
    def __init__(self, entity: Actor) -> None:
        super().__init__()
        self.entity = entity
        
    @property
    def generator(self) -> Generator:
        return self.entity.dungeon_map.generator
    
    def act(self) -> None: # Method is going to be overridden by its subclasses
        raise NotImplementedError()


class Leave(Action):
    def act(self) -> None:
        raise SystemExit()

class Wait(Action):
    def act(self) -> None:
        pass
    
class DirectionAction(Action):
    def __init__(self, entity: Actor, dx: int, dy: int):
        super().__init__(entity)
        self.dx = dx
        self.dy = dy
    
    @property
    def dest_xy(self) -> Tuple[int, int]:
        return self.entity.x + self.dx, self.entity.y + self.dy

    @property
    def blocking_entity(self) -> Optional[Entity]:
        return self.generator.dungeon_map.get_blocking_entity_at_location(*self.dest_xy)
    
    @property
    def target_actor(self) -> Optional[Actor]:
        """Return the actor at this actions destination."""
        return self.generator.dungeon_map.get_actor_at_location(*self.dest_xy)


    def act(self) -> None:
        raise NotImplementedError()

class Attack(DirectionAction):
    def act(self) -> None:
        target = self.target_actor
        
        if not target: # No entity to attack.
            return  

        damage = self.entity.fighter.power - target.fighter.defense
        attack_desc = f"{self.entity.name.capitalize()} attacks {target.name}"
        if damage > 0:
            print(f"{attack_desc} for {damage} hit points.")
            target.fighter.hp -= damage
        else:
            print(f"{attack_desc} but does no damage.")

class Movement(DirectionAction):
    
    def act(self) -> None:
        dest_x, dest_y = self.dest_xy
        
        if not self.generator.dungeon_map.bounds_check(dest_x, dest_y): # Can't Move, Out of Bounds
            return
        if not self.generator.dungeon_map.tiles["walkable"][dest_x, dest_y]: # Can't Move, Tile is Not Walkable
            return
        if self.generator.dungeon_map.get_blocking_entity_at_location(dest_x, dest_y): # Can't Move, Entity on Tile
            return
        
        self.entity.move(self.dx, self.dy)

class ActionOfChoice(DirectionAction):
    def act(self) -> None:
        if self.target_actor:
            return Attack(self.entity, self.dx, self.dy).act()
        else:
            return Movement(self.entity, self.dx, self.dy).act()