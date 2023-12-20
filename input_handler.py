from typing import Optional
import tcod.event
from action import Action, Escape, Movement


class EventHandler(tcod.event.EventDispatch[Action]):
    def ev_quit(self, event: tcod.event.Quit) -> Optional[Action]:
        raise SystemExit()

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[Action]:
        action: Optional[Action] = None

        key = event.sym

        if key == tcod.event.K_UP or key == tcod.event.KeySym.w:
            action = Movement(dx=0, dy=-1)
        elif key == tcod.event.K_DOWN or key == tcod.event.KeySym.s:
            action = Movement(dx=0, dy=1)
        elif key == tcod.event.K_LEFT or key == tcod.event.KeySym.a:
            action = Movement(dx=-1, dy=0)
        elif key == tcod.event.K_RIGHT or key == tcod.event.KeySym.d:
            action = Movement(dx=1, dy=0)
        elif key == tcod.event.K_ESCAPE:
            action = Escape()

        # No valid key was pressed
        return action