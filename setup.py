"""Handle the loading and initialization of game sessions."""
from __future__ import annotations
import copy
import libtcodpy
from typing import Optional
import tcod
import color
from generator import Generator
import entity_list
import input_handler
from procedure_gen import generate_dungeon


# Load the background image and remove the alpha channel.
background_image = tcod.image.load("menu_background.png")[:, :, :3]


def new_game() -> Generator:
    """Return a brand new game session as an Engine instance."""
    map_width = 80
    map_height = 43

    max_room_size = 10
    min_room_size = 6
    max_rooms = 30

    max_monsters_per_room = 2
    max_items_per_room = 2

    player = copy.deepcopy(entity_list.player)

    generator = Generator(player)

    generator.dungeon_map = generate_dungeon(
        max_rooms = max_rooms,
        min_room_size = min_room_size,
        max_room_size = max_room_size,
        map_width = map_width,
        map_height = map_height,
        max_monsters_per_room = max_monsters_per_room,
        max_items_per_room = max_items_per_room,
        generator = generator,
    )
    generator.update()

    generator.message_log.add_message("Hello and welcome, adventurer, to the Crypts Of Ruze!!!", color.welcome_text)
    return generator

class MainMenu(input_handler.BaseEventHandler):
    """Handle the main menu rendering and input."""

    def on_render(self, console: tcod.console.Console) -> None:
        """Render the main menu on a background image."""
        console.draw_semigraphics(background_image, 0, 0)

        console.print(
            console.width // 2,
            console.height // 2 - 4,
            "CRYPTS OF RUZE",
            fg = color.menu_title,
            alignment = libtcodpy.CENTER,
        )
        console.print(
            console.width // 2,
            console.height - 2,
            "By Ruze",
            fg = color.menu_title,
            alignment = libtcodpy.CENTER,
        )

        menu_width = 24
        for i, text in enumerate(
            ["[N] Play a new game", "[C] Continue last game", "[Q] Quit"]
        ):
            console.print(
                console.width // 2,
                console.height // 2 - 2 + i,
                text.ljust(menu_width),
                fg = color.menu_text,
                bg = color.black,
                alignment = libtcodpy.CENTER,
                bg_blend = libtcodpy.BKGND_ALPHA(64),
            )

    def ev_keydown(
        self, event: tcod.event.KeyDown) -> Optional[input_handler.BaseEventHandler]:
        if event.sym in (tcod.event.KeySym.q, tcod.event.KeySym.ESCAPE):
            raise SystemExit()
        elif event.sym == tcod.event.KeySym.c:
            # TODO: Load the game here
            pass
        elif event.sym == tcod.event.KeySym.n:
            return input_handler.MainGameEventHandler(new_game())
        return None