"""Checks for the Snake game, without opening a window.

The game is a real Bolo program. These tests run it with `show(win)` and the
timer removed, then call the same functions the buttons and clock call.
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

os.environ.setdefault("BOLO_GUI_SILENT", "1")

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import bolo  # noqa: E402

SOURCE = (APP_DIR / "examples" / "snake_app.bolo").read_text(encoding="utf-8")
# Drop the main loop and the starting clock tick, so the window is built but
# never waits for a person.
SKIP = {"show(win)", "later(win, 700, { tick() })"}
SOURCE = "\n".join(
    line for line in SOURCE.splitlines() if line.strip() not in SKIP
)


class SnakeAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import tkinter as tk

            root = tk.Tk()
            root.destroy()
        except Exception as exc:  # noqa: BLE001 - no desktop session
            raise unittest.SkipTest(f"tkinter cannot open a window: {exc}")

    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp(prefix="bolo-snake-test-"))
        self.previous = os.getcwd()
        os.chdir(self.folder)
        self.interp = bolo.Interp()
        self.interp.base_dir = self.folder
        with redirect_stdout(io.StringIO()):
            self.interp.run(bolo.parse(SOURCE))
        self.addCleanup(self.finish)

    def finish(self) -> None:
        self.interp.globals.get("win").close()
        os.chdir(self.previous)

    # -- little helpers -----------------------------------------------------
    def call(self, name: str, *args):
        return self.interp.call_value(self.interp.globals.get(name), list(args))

    def text_of(self, name: str) -> str:
        return self.call("value", self.interp.globals.get(name))

    def state(self, key: str):
        return self.call("get", self.interp.globals.get("state"), key)

    def set_state(self, key: str, value) -> None:
        self.call("put", self.interp.globals.get("state"), key, value)

    def seg(self, index: int):
        return self.call("get", self.interp.globals.get("snake"), index)

    def put_seg(self, index: int, x: int, y: int) -> None:
        self.call("put", self.interp.globals.get("snake"), index, [x, y])

    def head(self):
        return self.seg(0)

    def press(self, key: str) -> None:
        self.interp.globals.get("key_box").var.set(key)
        self.call("steer")

    # -- the checks ---------------------------------------------------------
    def test_the_board_starts_with_a_head_and_food(self) -> None:
        board = self.text_of("board_box")
        lines = board.splitlines()
        self.assertEqual(len(lines), 17)          # 15 rows plus a border
        self.assertEqual({len(line) for line in lines}, {62})
        self.assertIn(" @ ", board)
        self.assertIn(" * ", board)
        self.assertIn("Score 0", self.text_of("status"))

    def test_moving_pushes_the_head_forward(self) -> None:
        self.set_state("food_x", 2)
        self.set_state("food_y", 2)
        before = self.head()
        self.call("step")
        self.assertEqual(self.head(), [before[0] + 1, before[1]])
        self.assertTrue(self.state("alive"))

    def test_eating_food_grows_the_snake_and_speeds_it_up(self) -> None:
        head = self.head()
        self.set_state("food_x", head[0] + 1)
        self.set_state("food_y", head[1])
        self.call("step")
        self.assertEqual(self.state("len"), 4)
        self.assertEqual(self.state("score"), 1)
        self.assertEqual(self.state("speed"), 250)
        food = [self.state("food_x"), self.state("food_y")]
        body = [self.seg(i) for i in range(self.state("len"))]
        self.assertNotIn(food, body)

    def test_the_edges_wrap_around(self) -> None:
        self.put_seg(0, 20, 8)
        self.set_state("dir", "right")
        self.set_state("next", "right")
        self.set_state("food_x", 2)
        self.set_state("food_y", 2)
        self.call("step")
        self.assertEqual(self.head(), [1, 8])
        self.assertTrue(self.state("alive"))

    def test_hitting_yourself_ends_the_game(self) -> None:
        self.put_seg(0, 10, 8)
        self.put_seg(1, 11, 8)
        self.put_seg(2, 9, 8)
        self.set_state("len", 3)
        self.set_state("alive", True)
        self.set_state("paused", False)
        self.set_state("dir", "right")
        self.set_state("next", "right")
        self.set_state("food_x", 2)
        self.set_state("food_y", 2)
        self.set_state("score", 4)
        self.call("step")
        self.assertFalse(self.state("alive"))
        self.assertIn("Game over", self.text_of("status"))
        self.assertEqual(self.state("best"), 4)

    def test_keys_steer_and_ignore_a_reverse(self) -> None:
        self.press("w")
        self.assertEqual(self.state("next"), "up")
        self.assertEqual(self.text_of("key_box"), "")
        # moving right, so "a" would fold the snake onto itself
        self.press("a")
        self.assertEqual(self.state("next"), "up")
        self.press("d")
        self.assertEqual(self.state("next"), "right")

    def test_space_pauses_and_resumes(self) -> None:
        self.press(" ")
        self.assertTrue(self.state("paused"))
        before = self.head()
        self.call("step")
        self.assertEqual(self.head(), before)
        self.assertIn("Paused", self.text_of("status"))
        self.press(" ")
        self.assertFalse(self.state("paused"))

    def test_restart_revives_the_snake_and_clears_the_score(self) -> None:
        self.set_state("score", 7)
        self.set_state("alive", False)
        self.set_state("won", True)
        self.call("restart")
        self.assertTrue(self.state("alive"))
        self.assertFalse(self.state("won"))
        self.assertEqual(self.state("score"), 0)
        self.assertEqual(self.state("len"), 3)
        self.assertEqual(self.head(), [10, 8])
        self.assertIn("Score 0", self.text_of("status"))

    def test_the_speed_label_follows_the_delay(self) -> None:
        for delay, level in ((250, "1"), (210, "2"), (170, "3"), (130, "4"), (100, "5")):
            self.set_state("speed", delay)
            self.call("draw")
            self.assertIn("Speed " + level, self.text_of("status"))

    def test_filling_the_board_wins(self) -> None:
        cols, rows = 20, 15
        self.put_seg(0, 10, 8)
        for i in range(1, cols * rows - 1):
            self.put_seg(i, 1, 1)
        self.set_state("len", cols * rows - 1)
        self.set_state("alive", True)
        self.set_state("dir", "right")
        self.set_state("next", "right")
        self.set_state("food_x", 11)
        self.set_state("food_y", 8)
        self.call("step")
        self.assertFalse(self.state("alive"))
        self.assertTrue(self.state("won"))
        self.assertIn("filled the whole board", self.text_of("status"))


if __name__ == "__main__":
    unittest.main()
