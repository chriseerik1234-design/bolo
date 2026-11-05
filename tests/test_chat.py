"""Checks for Bolo Chat's helpers.

The app itself is a window; these tests stay headless by exercising the
pieces that turn a chat answer into editor code, and that check Bolo source.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import bolo_ai
import bolo_chat


class CodeExtraction(unittest.TestCase):
    def test_takes_a_fenced_bolo_block(self) -> None:
        answer = 'Here you go:\n```bolo\nsay("hi")\n```\nThat is all.'
        self.assertEqual(bolo_chat.extract_code(answer), 'say("hi")')

    def test_takes_the_last_block_when_there_are_several(self) -> None:
        answer = (
            "First try:\n```bolo\nsay(\"one\")\n```\n"
            "Better:\n```bolo\nsay(\"two\")\n```\n"
        )
        self.assertEqual(bolo_chat.extract_code(answer), 'say("two")')

    def test_accepts_a_bare_fence(self) -> None:
        answer = "```\nfor x in [1, 2] { say(x) }\n```"
        self.assertEqual(
            bolo_chat.extract_code(answer), "for x in [1, 2] { say(x) }"
        )

    def test_returns_none_when_there_is_no_code(self) -> None:
        self.assertIsNone(bolo_chat.extract_code("Just a sentence."))

    def test_trim_code_keeps_small_code_whole(self) -> None:
        code = 'say("hi")\n'
        self.assertEqual(bolo_chat.trim_code(code), 'say("hi")')

    def test_trim_code_marks_a_long_file(self) -> None:
        code = "\n".join('say("line")' for _ in range(2000))
        trimmed = bolo_chat.trim_code(code, limit=200)
        self.assertLessEqual(len(trimmed), 260)
        self.assertIn("trimmed", trimmed)


class MessageBuilding(unittest.TestCase):
    def test_the_question_and_code_travel_together(self) -> None:
        messages = bolo_chat.build_messages(
            "What does this do?", 'say("hi")\n'
        )
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("Bolo Chat", messages[0]["content"])
        self.assertIn('say("hi")', messages[1]["content"])
        self.assertEqual(messages[-1], {"role": "user", "content": "What does this do?"})

    def test_code_can_be_left_out(self) -> None:
        messages = bolo_chat.build_messages(
            "Write something", 'say("hi")\n', include_code=False
        )
        joined = "\n".join(message["content"] for message in messages)
        self.assertNotIn('say("hi")', joined)

    def test_history_is_included(self) -> None:
        history = [{"role": "user", "content": "earlier"}]
        messages = bolo_chat.build_messages("now", "", history)
        self.assertIn({"role": "user", "content": "earlier"}, messages)

    def test_chat_mode_uses_the_chat_prompt(self) -> None:
        messages = bolo_chat.build_messages(
            "hello", "", system=bolo_ai.CHAT_SYSTEM
        )
        self.assertIn("chatbot", messages[0]["content"])

    def test_code_mode_uses_the_bolo_prompt(self) -> None:
        messages = bolo_chat.build_messages(
            "write code", "", system=bolo_ai.CODER_SYSTEM
        )
        self.assertIn("```bolo", messages[0]["content"])


class SourceChecks(unittest.TestCase):
    def test_good_code_passes(self) -> None:
        ok, message, line = bolo_chat.check_source('say("hi")\n')
        self.assertTrue(ok)
        self.assertIsNone(line)
        self.assertIn("No syntax errors", message)

    def test_bad_code_points_at_a_line(self) -> None:
        ok, message, line = bolo_chat.check_source('say("hi"\n')
        self.assertFalse(ok)
        self.assertIsNotNone(line)
        self.assertIn("bolo:", message)

    def test_empty_code_is_not_a_program(self) -> None:
        ok, _message, _line = bolo_chat.check_source("   \n")
        self.assertFalse(ok)


class ModelChoice(unittest.TestCase):
    def test_coder_prefers_its_own_model(self) -> None:
        names = ["llama3.2:3b", "bolo-coder:latest", "bolo-tutor:latest"]
        self.assertEqual(
            bolo_ai.pick_model(names, bolo_ai.CODER_PREFERRED), "bolo-coder:latest"
        )

    def test_tutor_still_prefers_the_tutor_model(self) -> None:
        names = ["bolo-coder:latest", "bolo-tutor:latest", "llama3.2:3b"]
        self.assertEqual(bolo_ai.pick_model(names), "bolo-tutor:latest")


if __name__ == "__main__":
    unittest.main()
