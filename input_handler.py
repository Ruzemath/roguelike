from __future__ import annotations
import os
import libtcodpy
from typing import Callable, Optional, Tuple, TYPE_CHECKING, Union
import tcod
import action
from action import (
    Action,
    ActionOfChoice,
    PickupAction,
    Wait,
    TakeStairs,
)
import color
import exceptions
if TYPE_CHECKING:
    from generator import Generator
    from entities import Item

MOVE_KEYS = {
    # Arrow keys.
    tcod.event.KeySym.UP: (0, -1),
    tcod.event.KeySym.DOWN: (0, 1),
    tcod.event.KeySym.LEFT: (-1, 0),
    tcod.event.KeySym.RIGHT: (1, 0),
    tcod.event.KeySym.HOME: (-1, -1),
    tcod.event.KeySym.END: (-1, 1),
    tcod.event.KeySym.PAGEUP: (1, -1),
    tcod.event.KeySym.PAGEDOWN: (1, 1),
    # Numpad keys.
    tcod.event.KeySym.KP_1: (-1, 1),
    tcod.event.KeySym.KP_2: (0, 1),
    tcod.event.KeySym.KP_3: (1, 1),
    tcod.event.KeySym.KP_4: (-1, 0),
    tcod.event.KeySym.KP_6: (1, 0),
    tcod.event.KeySym.KP_7: (-1, -1),
    tcod.event.KeySym.KP_8: (0, -1),
    tcod.event.KeySym.KP_9: (1, -1),
    # wasd keys.
    tcod.event.KeySym.a: (-1, 0),
    tcod.event.KeySym.s: (0, 1),
    tcod.event.KeySym.w: (0, -1),
    tcod.event.KeySym.d: (1, 0),
    tcod.event.KeySym.q: (-1, -1),
    tcod.event.KeySym.e: (1, -1),
    tcod.event.KeySym.z: (-1, 1),
    tcod.event.KeySym.c: (1, 1),
}

WAIT_KEYS = {
    tcod.event.KeySym.TAB,
    tcod.event.KeySym.KP_5,
    tcod.event.KeySym.CLEAR,
}

CONFIRM_KEYS = {
    tcod.event.KeySym.RETURN,
    tcod.event.KeySym.KP_ENTER,
}


CURSOR_Y_KEYS = {
    tcod.event.KeySym.UP: -1,
    tcod.event.KeySym.DOWN: 1,
    tcod.event.KeySym.PAGEUP: -10,
    tcod.event.KeySym.PAGEDOWN: 10,
}

ActionOrHandler = Union[Action, "BaseEventHandler"]
"""An event handler return value which can trigger an action or switch active handlers.

If a handler is returned then it will become the active handler for future events.
If an action is returned it will be attempted and if it's valid then
MainGameEventHandler will become the active handler.
"""

class BaseEventHandler(tcod.event.EventDispatch[ActionOrHandler]):
    def handle(self, event: tcod.event.Event) -> BaseEventHandler:
        """Handle an event and return the next active event handler."""
        state = self.dispatch(event)
        if isinstance(state, BaseEventHandler):
            return state
        assert not isinstance(state, Action), f"{self!r} can not handle actions."
        return self

    def on_render(self, console: tcod.console.Console) -> None:
        raise NotImplementedError()

    def ev_quit(self, event: tcod.event.Quit) -> Optional[Action]:
        raise SystemExit()
    
class PopupMessage(BaseEventHandler):
    """Display a popup text window."""

    def __init__(self, parent_handler: BaseEventHandler, text: str):
        self.parent = parent_handler
        self.text = text

    def on_render(self, console: tcod.console.Console) -> None:
        """Render the parent and dim the result, then print the message on top."""
        self.parent.on_render(console)
        console.rgb["fg"] //= 8
        console.rgb["bg"] //= 8

        console.print(
            console.width // 2,
            console.height // 2,
            self.text,
            fg = color.white,
            bg = color.black,
            alignment = libtcodpy.CENTER,
        )

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[BaseEventHandler]:
        """Any key returns to the parent handler."""
        return self.parent    
     
class EventHandler(BaseEventHandler):
    def __init__(self, generator: Generator):
        self.generator = generator
        
    def handle(self, event: tcod.event.Event) -> BaseEventHandler:
        """Handle events for input handlers with an engine."""
        action_or_state = self.dispatch(event)
        if isinstance(action_or_state, BaseEventHandler):
            return action_or_state
        if self.handle_action(action_or_state):  # A valid action was performed.
            if not self.generator.player.is_alive: # The player was killed sometime during or after the action.
                return GameOverEventHandler(self.generator)
            elif self.generator.player.level.requires_level_up:
                return LevelUpEventHandler(self.generator)
            return MainGameEventHandler(self.generator)  # Return to the main handler.
        return self

    def handle_action(self, action: Optional[Action]) -> bool:
        """Handle actions returned from event methods.
        Returns True if the action will advance a turn.
        """
        if action is None:
            return False
        try:
            action.act()
        except exceptions.Impossible as exc:
            self.generator.message_log.add_message(exc.args[0], color.impossible)
            return False  # Skip enemy turn on exceptions.

        self.generator.handle_monster_turns()
        self.generator.update()
        return True
            
    def ev_mousemotion(self, event: tcod.event.MouseMotion) -> None:
        if self.generator.dungeon_map.bounds_check(event.tile.x, event.tile.y):
            self.generator.mouse_location = event.tile.x, event.tile.y
                
    def on_render(self, console: tcod.console.Console) -> None:
        self.generator.make(console)

class AskUserEventHandler(EventHandler):
    """Handles user input for actions which require special input."""

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        """By default any key exits this input handler."""
        if event.sym in {  # Ignore modifier keys.
            tcod.event.KeySym.LSHIFT,
            tcod.event.KeySym.RSHIFT,
            tcod.event.KeySym.LCTRL,
            tcod.event.KeySym.RCTRL,
            tcod.event.KeySym.LALT,
            tcod.event.KeySym.RALT,
        }:
            return None
        return self.on_exit()

    def ev_mousebuttondown(self, event: tcod.event.MouseButtonDown) -> Optional[ActionOrHandler]:
        """By default any mouse click exits this input handler."""
        return self.on_exit()

    def on_exit(self) -> Optional[ActionOrHandler]:
        """Called when the user is trying to exit or cancel an action.
        By default this returns to the main event handler.
        """
        return MainGameEventHandler(self.generator)
    
class CharacterScreenEventHandler(AskUserEventHandler):
    TITLE = "Character Information"

    def on_render(self, console: tcod.console.Console) -> None:
        super().on_render(console)

        if self.generator.player.x <= 30:
            x = 40
        else:
            x = 0

        y = 0
        width = len(self.TITLE) + 4
        console.draw_frame(
            x = x,
            y = y,
            width = width,
            height = 9,
            title = self.TITLE,
            clear = True,
            fg = (255, 255, 255),
            bg = (0, 0, 0),
        )

        console.print(
            x = x + 1, y = y + 2, string = f"Level: {self.generator.player.level.current_level}", fg = (102, 179, 255)
        )
        console.print(
            x = x + 1, y = y + 3,
            string = f"XP For Level {self.generator.player.level.current_level + 1}: {self.generator.player.level.experience_to_next_level}", fg = (153, 255, 153)
        )
        console.print(
            x = x + 1, y = y + 4, string = f"XP Modifier: {int(self.generator.player.fighter.xp_mod * 100)}%", fg = (153, 255, 153)
        )
        console.print(
            x = x + 1, y = y + 5, string = f"Current XP: {self.generator.player.level.current_xp}", fg = (153, 255, 153)
        ) 
        console.print(
            x = x + 1, y = y + 6, string = f"Attack: {self.generator.player.fighter.power}", fg = (128, 0, 0)
        )
        console.print(
            x = x + 1, y = y + 7, string = f"Defense: {self.generator.player.fighter.defense}", fg = (204, 153, 102)
        )
        
        
class LevelUpEventHandler(AskUserEventHandler):
    TITLE = "Level Up"

    def on_render(self, console: tcod.console.Console) -> None:
        super().on_render(console)

        if self.generator.player.x <= 30:
            x = 40
        else:
            x = 0

        console.draw_frame(
            x = x,
            y = 0,
            width = 35,
            height = 10,
            title = self.TITLE,
            clear = True,
            fg = (255, 255, 255),
            bg = (0, 0, 0),
        )

        console.print(x = x + 1, y = 1, string = "Congratulations! You level up!")
        console.print(x = x + 1, y = 2, string = "Select an attribute to increase.")
        console.print(
            x = x + 1,
            y = 4,
            string = f"1) Health (+20 HP, from {self.generator.player.fighter.max_hp})",
        )
        console.print(
            x = x + 1,
            y = 5,
            string=f"2) Strength (+1 attack, from {self.generator.player.fighter.power})",
        )
        console.print(
            x = x + 1,
            y = 6,
            string = f"3) Toughness (+1 defense, from {self.generator.player.fighter.defense})",
        )
        console.print(
            x = x + 1,
            y = 7,
            string = f"4) Xp Gain (+20% exp, from {int(self.generator.player.fighter.base_xp_mod * 100)}%)",
        )

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        player = self.generator.player
        key = event.sym
        key_to_index = {
        tcod.event.KeySym.N1: 0,
        tcod.event.KeySym.N2: 1,
        tcod.event.KeySym.N3: 2,
        tcod.event.KeySym.N4: 3,
    }
        if key in key_to_index:
            index = key_to_index[key]
            if index == 0:
                player.level.increase_max_hp()
            elif index == 1:
                player.level.increase_power()
            elif index == 2:
                player.level.increase_defense()
            elif index == 3:
                player.level.increase_xp()
        else:
            self.generator.message_log.add_message("Invalid entry.", color.invalid)
            return None
        return super().ev_keydown(event)

    def ev_mousebuttondown(self, event: tcod.event.MouseButtonDown) -> Optional[ActionOrHandler]:
        """
        Don't allow the player to click to exit the menu, like normal.
        """
        return None
    
class InventoryEventHandler(AskUserEventHandler):
    """This handler lets the user select an item.

    What happens then depends on the subclass.
    """

    TITLE = "<missing title>"

    def on_render(self, console: tcod.console.Console) -> None:
        """Render an inventory menu, which displays the items in the inventory, and the letter to select them.
        Will move to a different position based on where the player is located, so the player can always see where
        they are.
        """
        super().on_render(console)
        number_of_items_in_inventory = len(self.generator.player.inventory.items)

        height = number_of_items_in_inventory + 2

        if height <= 3:
            height = 3

        if self.generator.player.x <= 30:
            x = 40
        else:
            x = 0

        y = 0
        width = len(self.TITLE) + 4
        console.draw_frame(
            x = x,
            y = y,
            width = width,
            height = height,
            title = self.TITLE,
            clear = True,
            fg = (255, 255, 255),
            bg = (0, 0, 0),
        )

        if number_of_items_in_inventory > 0:
            for i, item in enumerate(self.generator.player.inventory.items):
                item_key = chr(ord("a") + i)
                is_equipped = self.generator.player.equipment.item_is_equipped(item)
                item_string = f"({item_key}) {item.name}"
                if is_equipped:
                    item_string = f"{item_string} (E)"
                console.print(x + 1, y + i + 1, item_string)
        else:
            console.print(x + 1, y + 1, "(Empty)")

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        player = self.generator.player
        key = event.sym
        index = key - tcod.event.KeySym.a

        if 0 <= index <= 26:
            try:
                selected_item = player.inventory.items[index]
            except IndexError:
                self.generator.message_log.add_message("Invalid entry.", color.invalid)
                return None
            return self.on_item_selected(selected_item)
        return super().ev_keydown(event)

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        """Called when the user selects a valid item."""
        raise NotImplementedError()
    

class InventoryActivateHandler(InventoryEventHandler):
    """Handle using an inventory item."""

    TITLE = "Select an item to use"

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        if item.consumable:
            # Return the action for the selected item.
            return item.consumable.get_action(self.generator.player)
        elif item.equippable:
            return action.EquipAction(self.generator.player, item)
        else:
            return None


class InventoryDropHandler(InventoryEventHandler):
    """Handle dropping an inventory item."""

    TITLE = "Select an item to drop"

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        """Drop this item."""
        return action.DropItem(self.generator.player, item)

class SelectIndexHandler(AskUserEventHandler):
    """Handles asking the user for an index on the map."""

    def __init__(self, generator: Generator):
        """Sets the cursor to the player when this handler is constructed."""
        super().__init__(generator)
        player = self.generator.player
        generator.mouse_location = player.x, player.y

    def on_render(self, console: tcod.console.Console) -> None:
        """Highlight the tile under the cursor."""
        super().on_render(console)
        x, y = self.generator.mouse_location
        console.rgb["bg"][x, y] = color.white
        console.rgb["fg"][x, y] = color.black

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        """Check for key movement or confirmation keys."""
        key = event.sym
        if key in MOVE_KEYS:
            modifier = 1  # Holding modifier keys will speed up key movement.
            if event.mod & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT):
                modifier *= 5
            if event.mod & (tcod.event.KMOD_LCTRL | tcod.event.KMOD_RCTRL):
                modifier *= 10
            if event.mod & (tcod.event.KMOD_LALT | tcod.event.KMOD_RALT):
                modifier *= 20

            x, y = self.generator.mouse_location
            dx, dy = MOVE_KEYS[key]
            x += dx * modifier
            y += dy * modifier
            # Clamp the cursor index to the map size.
            x = max(0, min(x, self.generator.dungeon_map.width - 1))
            y = max(0, min(y, self.generator.dungeon_map.height - 1))
            self.generator.mouse_location = x, y
            return None
        elif key in CONFIRM_KEYS:
            return self.on_index_selected(*self.generator.mouse_location)
        return super().ev_keydown(event)

    def ev_mousebuttondown(self, event: tcod.event.MouseButtonDown) -> Optional[ActionOrHandler]:
        """Left click confirms a selection."""
        if self.generator.dungeon_map.bounds_check(*event.tile):
            if event.button == 1:
                return self.on_index_selected(*event.tile)
        return super().ev_mousebuttondown(event)

    def on_index_selected(self, x: int, y: int) -> Optional[ActionOrHandler]:
        """Called when an index is selected."""
        raise NotImplementedError()


class LookHandler(SelectIndexHandler):
    """Lets the player look around using the keyboard."""

    def on_index_selected(self, x: int, y: int) -> MainGameEventHandler:
        """Return to main handler."""
        return MainGameEventHandler(self.generator)

class SingleRangedAttackHandler(SelectIndexHandler):
    """Handles targeting a single enemy. Only the enemy selected will be affected."""

    def __init__(
        self, generator: Generator, callback: Callable[[Tuple[int, int]], Optional[Action]]
    ):
        super().__init__(generator)

        self.callback = callback

    def on_index_selected(self, x: int, y: int) -> Optional[Action]:
        return self.callback((x, y))

class AreaRangedAttackHandler(SelectIndexHandler):
    """Handles targeting an area within a given radius. Any entity within the area will be affected."""

    def __init__(
        self,
        generator: Generator,
        radius: int,
        callback: Callable[[Tuple[int, int]], Optional[Action]],
    ):
        super().__init__(generator)

        self.radius = radius
        self.callback = callback

    def on_render(self, console: tcod.console.Console) -> None:
        """Highlight the tile under the cursor."""
        super().on_render(console)

        x, y = self.generator.mouse_location

        # Draw a rectangle around the targeted area, so the player can see the affected tiles.
        console.draw_frame(
            x = x - self.radius - 1,
            y = y - self.radius - 1,
            width = self.radius ** 2,
            height = self.radius ** 2,
            fg = color.red,
            clear = False,
        )

    def on_index_selected(self, x: int, y: int) -> Optional[Action]:
        return self.callback((x, y))

class MainGameEventHandler(EventHandler):    
    
    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        action: Optional[Action] = None

        key = event.sym
        modifier = event.mod
        player = self.generator.player
        
        if key == tcod.event.KeySym.PERIOD and modifier & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT):
            return TakeStairs(player)
        
        if key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[key]
            action = ActionOfChoice(player, dx, dy)
        elif key in WAIT_KEYS:
            action = Wait(player)
        elif key == tcod.event.KeySym.ESCAPE:
           raise SystemExit()
        elif key == tcod.event.KeySym.v:
            return HistoryViewer(self.generator)
        elif key == tcod.event.KeySym.SPACE:
            action = PickupAction(player)
        elif key == tcod.event.KeySym.i:
            return InventoryActivateHandler(self.generator)
        elif key == tcod.event.KeySym.o:
            return InventoryDropHandler(self.generator)
        elif key == tcod.event.KeySym.m:
            return CharacterScreenEventHandler(self.generator)
        elif key == tcod.event.KeySym.SLASH:
            return LookHandler(self.generator)

        return action

class GameOverEventHandler(EventHandler):
    def on_quit(self) -> None:
        """Handle exiting out of a finished game."""
        if os.path.exists("savegame.sav"):
            os.remove("savegame.sav")  # Deletes the active save file.
        raise exceptions.QuitWithoutSaving()  # Avoid saving a finished game.

    def ev_quit(self, event: tcod.event.Quit) -> None:
        self.on_quit()
        
    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        if event.sym == tcod.event.KeySym.ESCAPE:
            self.on_quit()

class HistoryViewer(EventHandler):
    """Print the history on a larger window which can be navigated."""

    def __init__(self, generator: Generator):
        super().__init__(generator)
        self.log_length = len(generator.message_log.messages)
        self.cursor = self.log_length - 1

    def on_render(self, console: tcod.console.Console) -> None:
        super().on_render(console)  # Draw the main state as the background.

        log_console = tcod.console.Console(console.width - 6, console.height - 6)

        # Draw a frame with a custom banner title.
        log_console.draw_frame(0, 0, log_console.width, log_console.height)
        log_console.print_box(
            0, 0, log_console.width, 1, "┤Message history├", alignment = libtcodpy.CENTER
        )

        # Render the message log using the cursor parameter.
        self.generator.message_log.render_messages(
            log_console,
            1,
            1,
            log_console.width - 2,
            log_console.height - 2,
            self.generator.message_log.messages[: self.cursor + 1],
        )
        log_console.blit(console, 3, 3)

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[MainGameEventHandler]:
        # Fancy conditional movement to make it feel right.
        if event.sym in CURSOR_Y_KEYS:
            adjust = CURSOR_Y_KEYS[event.sym]
            if adjust < 0 and self.cursor == 0:
                # Only move from the top to the bottom when you're on the edge.
                self.cursor = self.log_length - 1
            elif adjust > 0 and self.cursor == self.log_length - 1:
                # Same with bottom to top movement.
                self.cursor = 0
            else:
                # Otherwise move while staying clamped to the bounds of the history log.
                self.cursor = max(0, min(self.cursor + adjust, self.log_length - 1))
        elif event.sym == tcod.event.KeySym.HOME:
            self.cursor = 0  # Move directly to the top message.
        elif event.sym == tcod.event.KeySym.END:
            self.cursor = self.log_length - 1  # Move directly to the last message.
        else:  # Any other key moves back to the main game state.
            return MainGameEventHandler(self.generator)
        return None