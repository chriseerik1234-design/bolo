"""Checks for the learning app: its lessons, reference and playground.

These run without opening a window. They keep the course honest: every
lesson solution must still pass its own Check, every starter must still
fail it, and no builtin may quietly disappear from the reference.
"""
from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import bolo
import bolo_app


def tearDownModule() -> None:
    shutil.rmtree(bolo_app.SANDBOX, ignore_errors=True)


class LessonChecks(unittest.TestCase):
    def test_every_solution_prints_what_the_lesson_asks_for(self) -> None:
        for index, lesson in enumerate(bolo_app.LESSONS, start=1):
            with self.subTest(lesson=index, title=lesson.title):
                if lesson.gui:
                    # Opening the real window would block the suite.
                    bolo.parse(lesson.solution)
                    for wanted in lesson.code_must:
                        self.assertIn(wanted, lesson.solution)
                    continue
                result = bolo_app.run_source(lesson.solution, reset_first=True)
                self.assertIsNone(result.error, result.error)
                for wanted in lesson.must:
                    self.assertIn(wanted, result.output)

    def test_every_starter_is_not_already_finished(self) -> None:
        for index, lesson in enumerate(bolo_app.LESSONS, start=1):
            with self.subTest(lesson=index, title=lesson.title):
                if lesson.gui:
                    bolo.parse(lesson.starter)
                    missing = [
                        wanted
                        for wanted in lesson.code_must
                        if wanted not in lesson.starter
                    ]
                    self.assertTrue(missing, "starter already passes the lesson")
                    continue
                result = bolo_app.run_source(lesson.starter, reset_first=True)
                done = not result.error and all(
                    wanted in result.output for wanted in lesson.must
                )
                self.assertFalse(done, "starter already passes the lesson")

    def test_lesson_ids_and_order_are_unique(self) -> None:
        ids = [lesson.id for lesson in bolo_app.LESSONS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, [str(n) for n in range(1, len(ids) + 1)])

    def test_every_lesson_has_a_task_and_an_answer(self) -> None:
        for lesson in bolo_app.LESSONS:
            with self.subTest(lesson=lesson.id):
                self.assertTrue(lesson.task.strip())
                self.assertTrue(lesson.solution.strip())
                self.assertTrue(lesson.must or lesson.code_must)


class ReferenceChecks(unittest.TestCase):
    def test_every_builtin_appears_in_the_reference(self) -> None:
        text = "\n".join(
            signature + "\n" + description + "\n" + example
            for _, entries in bolo_app.REFERENCE
            for signature, description, example in entries
        )
        missing = sorted(name for name in bolo.BUILTINS if name not in text)
        self.assertEqual(missing, [])

    def test_reference_examples_parse(self) -> None:
        for group, entries in bolo_app.REFERENCE:
            for signature, _description, example in entries:
                with self.subTest(group=group, signature=signature):
                    bolo.parse(example)

    def test_reference_search_finds_known_words(self) -> None:
        text = "\n".join(
            signature + "\n" + description
            for _, entries in bolo_app.REFERENCE
            for signature, description, _ in entries
        )
        for word in ("sort", "file", "lambda", "if", "for", "map"):
            self.assertIn(word, text.lower())


class PlaygroundChecks(unittest.TestCase):
    def test_every_snippet_runs(self) -> None:
        for name, code in bolo_app.PLAYGROUND_SNIPPETS:
            with self.subTest(snippet=name):
                result = bolo_app.run_source(code, reset_first=True)
                self.assertIsNone(result.error, result.error)

    def test_a_playground_session_remembers_names(self) -> None:
        interp = bolo.Interp()
        first = bolo_app.run_source("answer = 41\n", interp=interp, reset_first=False)
        second = bolo_app.run_source("say(answer + 1)\n", interp=interp, reset_first=False)
        self.assertIsNone(first.error, first.error)
        self.assertIsNone(second.error, second.error)
        self.assertIn("42", second.output)

    def test_file_work_stays_in_the_sandbox(self) -> None:
        result = bolo_app.run_source(
            'write("note.txt", "safe")\nsay(read("note.txt"))\n',
            reset_first=True,
        )
        self.assertIsNone(result.error, result.error)
        self.assertIn("safe", result.output)
        self.assertTrue((bolo_app.SANDBOX / "note.txt").exists())
        self.assertFalse((APP_DIR / "note.txt").exists())


if __name__ == "__main__":
    unittest.main()
