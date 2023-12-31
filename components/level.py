from __future__ import annotations
from typing import TYPE_CHECKING
from components.base_component import BaseComponent
if TYPE_CHECKING:
    from entities import Actor


class Level(BaseComponent):
    parent: Actor

    def __init__(
        self,
        current_level: int = 1,
        current_xp: int = 0,
        level_up_base: int = 0,
        level_up_factor: int = 150,
        xp_given: int = 0,
    ):
        self.current_level = current_level
        self.current_xp = current_xp
        self.level_up_base = level_up_base
        self.level_up_factor = level_up_factor
        self.xp_given = xp_given

    @property
    def experience_to_next_level(self) -> int:
        return (self.current_level * self.level_up_factor) + self.level_up_base 

    @property
    def requires_level_up(self) -> bool:
        return self.current_xp > self.experience_to_next_level

    def add_xp(self, xp: int) -> None:
        if xp == 0 or self.level_up_base == 0:
            return
        
        real_xp = int(xp * self.parent.fighter.xp_mod)
        self.current_xp += real_xp
        self.generate.message_log.add_message(f"You gain {real_xp} experience points.", fg = (153, 255, 153))

        if self.requires_level_up:
            self.generate.message_log.add_message(f"You advance to level {self.current_level + 1}!", fg = (102, 179, 255))

    def increase_level(self) -> None:
        self.current_xp -= self.experience_to_next_level
        self.current_level += 1

    def increase_max_hp(self, amount: int = 20) -> None:
        self.parent.fighter.max_hp += amount
        self.parent.fighter.hp += amount
        self.generate.message_log.add_message("You feel a warmth swirling inside!", fg = (0, 102, 0))
        self.increase_level()

    def increase_power(self, amount: int = 1) -> None:
        self.parent.fighter.base_power += amount
        self.generate.message_log.add_message("You feel your hands fill with power!", fg = (128, 0, 0))
        self.increase_level()

    def increase_defense(self, amount: int = 1) -> None:
        self.parent.fighter.base_defense += amount
        self.generate.message_log.add_message("You feel your skin hardening!", fg = (204, 153, 102))
        self.increase_level()
    
    def increase_xp(self, amount: float = 0.2) -> None:
        self.parent.fighter.base_xp_mod += amount
        self.generate.message_log.add_message("You feel your mind becoming clearer!", fg = (153, 255, 153))
        self.increase_level()