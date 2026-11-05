"""Tests for Bolo. Run with:  python -m unittest discover -s tests -v"""

from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bolo import BoloError, run_source  # noqa: E402
import bolo  # noqa: E402


def run(src, argv=None):
    return run_source(src, argv)


def output(src, argv=None):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        run(src, argv)
    return buffer.getvalue()


class Numbers(unittest.TestCase):
    def test_integer_arithmetic(self):
        self.assertEqual(run("1 + 2 * 3"), 7)

    def test_parentheses(self):
        self.assertEqual(run("(1 + 2) * 3"), 9)

    def test_division_is_exact_float(self):
        self.assertEqual(run("10 / 4"), 2.5)

    def test_modulo(self):
        self.assertEqual(run("10 % 3"), 1)

    def test_unary_minus(self):
        self.assertEqual(run("-3 + 10"), 7)

    def test_precedence_with_unary(self):
        self.assertEqual(run("-2 * 3"), -6)

    def test_division_by_zero(self):
        with self.assertRaises(BoloError):
            run("1 / 0")


class Text(unittest.TestCase):
    def test_concat(self):
        self.assertEqual(run('"a" + "b"'), "ab")

    def test_escapes(self):
        self.assertEqual(run(r'"a\tb\nc"'), "a\tb\nc")

    def test_single_quotes(self):
        self.assertEqual(run("'hi'"), "hi")

    def test_upper_pipeline(self):
        self.assertEqual(run('"tere" |> upper'), "TERE")

    def test_split_and_count(self):
        self.assertEqual(run('"a,b,c" |> split(",") |> count'), 3)

    def test_split_without_separator_uses_whitespace(self):
        self.assertEqual(run('"  a  b " |> split |> count'), 2)

    def test_replace(self):
        self.assertEqual(run('"a-b" |> replace("-", "_")'), "a_b")

    def test_regex_test(self):
        self.assertEqual(run(r'"IMG_001.jpg" |> test("^IMG_")'), True)

    def test_regex_find(self):
        self.assertEqual(run(r'"a1b22" |> find("[0-9]+")'), ["1", "22"])

    def test_string_is_indexable(self):
        self.assertEqual(run('"abc"[1]'), "b")


class Logic(unittest.TestCase):
    def test_if_expression_value(self):
        self.assertEqual(run("if 3 > 2 { 10 } else { 20 }"), 10)

    def test_if_without_else_is_nil(self):
        self.assertEqual(run("if false { 1 }"), None)

    def test_else_if(self):
        src = """
        x = 2
        if x == 1 { "one" } else if x == 2 { "two" } else { "many" }
        """
        self.assertEqual(run(src), "two")

    def test_and_returns_value(self):
        self.assertEqual(run("1 and 2"), 2)

    def test_or_short_circuits(self):
        self.assertEqual(run("1 or missing"), 1)

    def test_not(self):
        self.assertEqual(run("not false"), True)

    def test_comparisons(self):
        self.assertEqual(run('"a" < "b"'), True)
        self.assertEqual(run("[1, 2] == [1, 2]"), True)
        self.assertEqual(run("1 == true"), False)


class Variables(unittest.TestCase):
    def test_assign_and_read(self):
        self.assertEqual(run("x = 5\nx * 2"), 10)

    def test_reassign(self):
        self.assertEqual(run("x = 1\nx = 9\nx"), 9)

    def test_unknown_name_is_an_error(self):
        with self.assertRaises(BoloError) as caught:
            run("nope + 1")
        self.assertIn("I don't know the name 'nope'", str(caught.exception))

    def test_unknown_name_suggests_a_close_match(self):
        with self.assertRaises(BoloError) as caught:
            run("pritn(1)")
        self.assertIn("did you mean 'print'", str(caught.exception))

    def test_truthiness(self):
        self.assertEqual(run("if 0 { 1 } else { 2 }"), 2)
        self.assertEqual(run('if "" { 1 } else { 2 }'), 2)
        self.assertEqual(run("if [] { 1 } else { 2 }"), 2)


class Pipelines(unittest.TestCase):
    def test_map_lambda(self):
        self.assertEqual(run("[1, 2, 3] |> map({ it * 2 })"), [2, 4, 6])

    def test_pipes_feed_first_argument(self):
        self.assertEqual(run("[1, 2, 3] |> filter({ it > 1 })"), [2, 3])

    def test_chain(self):
        self.assertEqual(run("[3, 1, 2] |> sort |> reverse"), [3, 2, 1])

    def test_each_returns_the_list(self):
        self.assertEqual(output("[1, 2] |> each({ print(it) })"), "1\n2\n")

    def test_named_parameters(self):
        self.assertEqual(run("[1, 2, 3] |> reduce(0, { a, b -> a + b })"), 6)

    def test_multiline_pipeline(self):
        src = """
        [1, 2, 3, 4]
          |> filter({ it % 2 == 0 })
          |> map({ it * 10 })
        """
        self.assertEqual(run(src), [20, 40])

    def test_lambda_with_block_body(self):
        src = "[1, 2] |> each({ x = it + 1\n print(x) })"
        self.assertEqual(output(src), "2\n3\n")


class Functions(unittest.TestCase):
    def test_last_value_is_returned(self):
        self.assertEqual(run("to double(n) { n * 2 }\ndouble(21)"), 42)

    def test_explicit_return(self):
        self.assertEqual(run("to f() { return 7\n 9 }\nf()"), 7)

    def test_recursion(self):
        src = """
        to fact(n) {
          if n <= 1 { return 1 }
          n * fact(n - 1)
        }
        fact(5)
        """
        self.assertEqual(run(src), 120)

    def test_closures(self):
        src = """
        to adder(n) {
          { it + n }
        }
        add5 = adder(5)
        add5(10)
        """
        self.assertEqual(run(src), 15)

    def test_arity_mismatch(self):
        with self.assertRaises(BoloError):
            run("to f(a, b) { a }\nf(1)")

    def test_for_loop(self):
        src = """
        total = 0
        for n in [1, 2, 3] {
          total = total + n
        }
        total
        """
        self.assertEqual(run(src), 6)

    def test_indexing(self):
        self.assertEqual(run("[10, 20][1]"), 20)
        self.assertEqual(run("[10, 20][-1]"), 20)

    def test_out_of_range(self):
        with self.assertRaises(BoloError):
            run("[1][5]")


class Builtins(unittest.TestCase):
    def test_total_of_list(self):
        self.assertEqual(run("[1, 2, 3] |> sum"), 6)

    def test_unique_keeps_order(self):
        self.assertEqual(run("[2, 1, 2, 3, 1] |> unique"), [2, 1, 3])

    def test_take_and_skip(self):
        self.assertEqual(run("[1, 2, 3, 4] |> take(2)"), [1, 2])
        self.assertEqual(run("[1, 2, 3, 4] |> skip(2)"), [3, 4])

    def test_join(self):
        self.assertEqual(run('["a", "b"] |> join("-")'), "a-b")

    def test_push(self):
        self.assertEqual(run("[1] |> push(2)"), [1, 2])

    def test_range(self):
        self.assertEqual(run("range(3)"), [0, 1, 2])
        self.assertEqual(run("range(2, 5)"), [2, 3, 4])

    def test_num_and_int(self):
        self.assertEqual(run('num("12")'), 12)
        self.assertEqual(run('num("1.5")'), 1.5)
        self.assertEqual(run('int("3.9")'), 3)
        self.assertEqual(run("int(3.9)"), 3)

    def test_type(self):
        self.assertEqual(run("type(nil)"), "nothing")
        self.assertEqual(run("type(1)"), "number")
        self.assertEqual(run("type([])"), "list")
        self.assertEqual(run('type("a")'), "text")

    def test_str_of_list_is_readable(self):
        self.assertEqual(run('str(["a", 1])'), '["a", 1]')

    def test_count_of_string(self):
        self.assertEqual(run('"hello" |> count'), 5)

    def test_bad_argument_type_mentions_the_builtin(self):
        with self.assertRaises(BoloError) as caught:
            run("upcase = upper\nupcase(1)")
        self.assertIn("upper", str(caught.exception))


class Files(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.dir, ignore_errors=True))

    def path(self, *parts):
        return os.path.join(self.dir, *parts)

    def test_write_then_read(self):
        target = self.path("note.txt").replace("\\", "/")
        run(f'write("{target}", "tere")')
        self.assertEqual(run(f'read("{target}")'), "tere")

    def test_files_is_sorted_and_filterable(self):
        for name in ("b.jpg", "a.jpg", "c.txt"):
            open(self.path(name), "w").close()
        folder = self.dir.replace("\\", "/")
        self.assertEqual(run(f'files("{folder}") |> count'), 3)
        found = run(f'files("{folder}", "*.jpg") |> map({{ name(it) }})')
        self.assertEqual(found, ["a.jpg", "b.jpg"])

    def test_move_and_delete(self):
        source = self.path("old.txt").replace("\\", "/")
        target_dir = self.path("archive").replace("\\", "/")
        run(f'write("{source}", "x")')
        run(f'mkdir("{target_dir}")')
        run(f'move("{source}", "{target_dir}/new.txt")')
        self.assertFalse(os.path.exists(source))
        self.assertTrue(os.path.exists(os.path.join(target_dir, "new.txt")))
        run(f'delete("{target_dir}")')
        self.assertFalse(os.path.exists(target_dir))

    def test_path_helpers(self):
        self.assertEqual(run('"photos/2024/a.jpg" |> name'), "a.jpg")
        self.assertEqual(run('"photos/2024/a.jpg" |> stem'), "a")
        self.assertEqual(run('"photos/2024/a.jpg" |> ext'), "jpg")
        self.assertEqual(run('"photos/2024/a.jpg" |> parent'), "photos/2024")

    def test_walk_finds_nested_files(self):
        os.makedirs(self.path("sub"))
        open(self.path("top.txt"), "w").close()
        open(self.path("sub", "deep.txt"), "w").close()
        folder = self.dir.replace("\\", "/")
        self.assertEqual(run(f'walk("{folder}") |> count'), 2)

    def test_tidy_style_pipeline(self):
        os.makedirs(self.path("in"))
        for name in ("a.jpg", "b.jpg", "c.txt"):
            open(self.path("in", name), "w").close()
        folder = self.path("in").replace("\\", "/")
        src = f'''
        folder = "{folder}"
        folder
          |> files("*.jpg")
          |> each({{
              move(it, path(folder, "jpg", name(it)))
          }})
        files(path(folder, "jpg")) |> count
        '''
        self.assertEqual(run(src), 2)
        self.assertEqual(run(f'files("{folder}") |> count'), 1)


class Errors(unittest.TestCase):
    def test_parse_error_has_a_line(self):
        with self.assertRaises(BoloError) as caught:
            run("x = 1\ny = = 2")
        self.assertIsNotNone(caught.exception.line)

    def test_missing_brace(self):
        with self.assertRaises(BoloError) as caught:
            run("if true { 1")
        self.assertIn("never closed", str(caught.exception))

    def test_bad_operator_types(self):
        with self.assertRaises(BoloError):
            run('1 + "a"')

    def test_two_statements_on_one_line_is_rejected(self):
        with self.assertRaises(BoloError):
            run("x = 1 y = 2")

    def test_semicolon_separates_statements(self):
        self.assertEqual(run("x = 1; y = 2; x + y"), 3)

    def test_unterminated_string(self):
        with self.assertRaises(BoloError):
            run('x = "oops')

    def test_calling_a_number(self):
        with self.assertRaises(BoloError):
            run("f = 3\nf()")


class Cli(unittest.TestCase):
    def test_args_variable(self):
        self.assertEqual(run("args", ["a", "b"]), ["a", "b"])
        self.assertEqual(run("args"), [])

    def test_args_are_reachable_with_first(self):
        self.assertEqual(run("args |> first", ["x"]), "x")

    def test_byte_order_mark_is_ignored(self):
        self.assertEqual(run("\ufeff1 + 1"), 2)


class BeginnerWording(unittest.TestCase):
    """The friendly names that the lessons use."""

    def test_say(self):
        self.assertEqual(output('say("hi")'), "hi\n")

    def test_length(self):
        self.assertEqual(run("[1, 2, 3] |> length"), 3)
        self.assertEqual(run('"abcd" |> length'), 4)

    def test_text_and_number(self):
        self.assertEqual(run("text(12)"), "12")
        self.assertEqual(run('number("12") + 1'), 13)

    def test_nothing_is_nil(self):
        self.assertEqual(run("nothing"), None)
        self.assertEqual(run("1 is nothing"), False)
        self.assertEqual(output("say(nothing)"), "nothing\n")

    def test_is(self):
        self.assertEqual(run("2 is 2"), True)
        self.assertEqual(run('"a" is "b"'), False)

    def test_is_not(self):
        self.assertEqual(run("2 is not 3"), True)

    def test_is_reads_like_english_in_if(self):
        src = 'weather = "rain"\nif weather is "rain" { "umbrella" } else { "sunglasses" }'
        self.assertEqual(run(src), "umbrella")

    def test_using_equals_in_an_if_gets_an_explanation(self):
        with self.assertRaises(BoloError) as caught:
            run("x = 1\nif x = 1 { say(1) }")
        self.assertIn("use 'is' to compare", str(caught.exception))

    def test_print_still_works(self):
        self.assertEqual(output('print("hi")'), "hi\n")


class ErrorMessageQuality(unittest.TestCase):
    def test_adding_text_and_number_explains_itself(self):
        with self.assertRaises(BoloError) as caught:
            run('"I am " + 12')
        message = str(caught.exception)
        self.assertIn("can't add text and a number", message)
        self.assertIn("hint", message)

    def test_text_that_looks_like_a_number_gets_a_special_hint(self):
        with self.assertRaises(BoloError) as caught:
            run('"12" - 1')
        self.assertIn("number(", str(caught.exception))

    def test_index_out_of_range_mentions_counting_from_zero(self):
        with self.assertRaises(BoloError) as caught:
            run("[1, 2][5]")
        self.assertIn("counting starts at 0", str(caught.exception))

    def test_calling_a_number_says_so(self):
        with self.assertRaises(BoloError) as caught:
            run("f = 3\nf()")
        self.assertIn("is not a function", str(caught.exception))

    def test_hiding_a_builtin_with_a_box_is_explained(self):
        with self.assertRaises(BoloError) as caught:
            run('text = "hello"\nsay(text(1))')
        message = str(caught.exception)
        self.assertIn("there is a built-in called 'text'", message)

    def test_errors_point_at_the_right_spot(self):
        source = "a = 1\nb = a + 1\nsay(a + \"z\")"
        with self.assertRaises(BoloError) as caught:
            run(source)
        err = caught.exception
        self.assertEqual(err.line, 3)
        self.assertIsNotNone(err.col)

    def test_format_error_draws_a_caret(self):
        from bolo import format_error

        source = "a = 1\nsay(a + \"two\")"
        try:
            run(source)
        except BoloError as err:
            text = format_error(source, "demo.bolo", err)
        else:  # pragma: no cover - the program above must fail
            self.fail("expected an error")

        self.assertIn("demo.bolo: line 2", text)
        self.assertIn("^", text)
        self.assertIn("hint:", text)


class ReplHelpers(unittest.TestCase):
    def test_braces_open(self):
        from bolo import braces_open

        self.assertFalse(braces_open('say("hi")'))
        self.assertTrue(braces_open("if true {"))
        self.assertFalse(braces_open("if true {\n}"))
        self.assertFalse(braces_open('say("{")'))


class WhileLoops(unittest.TestCase):
    def test_while_counts(self):
        src = """
        n = 0
        total = 0
        while n < 4 {
          n = n + 1
          total = total + n
        }
        total
        """
        self.assertEqual(run(src), 10)

    def test_while_can_never_run(self):
        self.assertEqual(run("while false { 1 }\n42"), 42)

    def test_break_leaves_the_loop(self):
        src = """
        n = 0
        while true {
          n = n + 1
          if n is 3 { break }
        }
        n
        """
        self.assertEqual(run(src), 3)

    def test_continue_skips_the_rest(self):
        src = """
        total = 0
        for n in [1, 2, 3, 4] {
          if n is 2 { continue }
          total = total + n
        }
        total
        """
        self.assertEqual(run(src), 8)

    def test_break_only_leaves_the_inner_loop(self):
        src = """
        found = 0
        for a in [1, 2] {
          for b in [1, 2, 3] {
            if b is 2 { break }
            found = found + 1
          }
        }
        found
        """
        self.assertEqual(run(src), 2)

    def test_break_outside_a_loop_explains_itself(self):
        with self.assertRaises(BoloError) as caught:
            run("break")
        self.assertIn("inside a loop", str(caught.exception))


class ErrorHandling(unittest.TestCase):
    def test_fail_is_caught(self):
        src = """
        try {
          fail("no such file")
        } catch problem {
          "caught: " + problem
        }
        """
        self.assertEqual(run(src), "caught: no such file")

    def test_a_real_error_is_caught(self):
        src = 'try { 1 / 0 } catch problem { "safe" }'
        self.assertEqual(run(src), "safe")

    def test_catch_without_a_name(self):
        src = 'try { fail("x") } catch { "handled" }'
        self.assertEqual(run(src), "handled")

    def test_no_error_means_the_handler_is_skipped(self):
        src = 'try { 7 } catch problem { 9 }'
        self.assertEqual(run(src), 7)

    def test_errors_after_the_catch_still_stop_the_program(self):
        src = 'try { fail("first") } catch problem { 1 }\n1 + "a"'
        with self.assertRaises(BoloError):
            run(src)

    def test_catching_inside_a_function(self):
        src = """
        to safe_divide(a, b) {
          try {
            a / b
          } catch problem {
            "cannot divide"
          }
        }
        safe_divide(1, 0)
        """
        self.assertEqual(run(src), "cannot divide")


class Tables(unittest.TestCase):
    def test_build_and_read(self):
        src = 'p = table("name", "Mari", "age", 12)\np["name"]'
        self.assertEqual(run(src), "Mari")

    def test_write_with_brackets(self):
        src = 't = table()\nt["a"] = 1\nt["a"]'
        self.assertEqual(run(src), 1)

    def test_put_get_has_remove(self):
        src = """
        t = table()
        put(t, "x", 5)
        has(t, "x") is true and get(t, "x") is 5 and get(t, "y", 0) is 0
        """
        self.assertEqual(run(src), True)
        self.assertEqual(run('t = table("x", 1)\nremove(t, "x")\nlength(t)'), 0)

    def test_length_counts_entries(self):
        self.assertEqual(run('table("a", 1, "b", 2) |> length'), 2)

    def test_keys_values_and_pairs(self):
        src = 't = table("a", 1, "b", 2)\n[keys(t), values(t), pairs(t)]'
        self.assertEqual(run(src), [["a", "b"], [1, 2], [["a", 1], ["b", 2]]])

    def test_walk_a_table_pairs(self):
        src = """
        t = table("a", 1, "b", 2)
        total = 0
        for key, value in pairs(t) {
          total = total + value
        }
        total
        """
        self.assertEqual(run(src), 3)

    def test_missing_key_suggests_get_or_has(self):
        with self.assertRaises(BoloError) as caught:
            run('table("a", 1)["b"]')
        message = str(caught.exception)
        self.assertIn("no key", message)
        self.assertIn("has(", message)

    def test_table_prints_readably(self):
        self.assertEqual(run('to_json(table("a", 1))'), '{\n  "a": 1\n}')

    def test_tables_compare_by_content(self):
        self.assertEqual(run('table("a", 1) is table("a", 1)'), True)
        self.assertEqual(run('table("a", 1) is table("a", 2)'), False)


class TextWithValues(unittest.TestCase):
    def test_name_inside_text(self):
        self.assertEqual(run('who = "Mari"\n"Hello, {who}!"'), "Hello, Mari!")

    def test_expression_inside_text(self):
        self.assertEqual(run('"2 + 3 is {2 + 3}"'), "2 + 3 is 5")

    def test_two_values(self):
        self.assertEqual(run('a = 1\nb = 2\n"{a} and {b}"'), "1 and 2")

    def test_real_braces(self):
        self.assertEqual(output('say("{{braces}}")'), "{braces}\n")

    def test_json_is_left_alone(self):
        text = 'json("{\\"name\\": \\"Mari\\"}")["name"]'
        self.assertEqual(run(text), "Mari")

    def test_unknown_name_inside_text_is_an_error(self):
        with self.assertRaises(BoloError):
            run('"hello {nobody}"')

    def test_plain_text_is_unchanged(self):
        self.assertEqual(run('"no values here"'), "no values here")


class Membership(unittest.TestCase):
    def test_in_a_list(self):
        self.assertEqual(run("2 in [1, 2, 3]"), True)
        self.assertEqual(run("9 in [1, 2, 3]"), False)

    def test_in_text(self):
        self.assertEqual(run('"cat" in "concatenate"'), True)
        self.assertEqual(run('"dog" in "concatenate"'), False)

    def test_not_in(self):
        self.assertEqual(run("4 not in [1, 2]"), True)

    def test_in_a_table_checks_keys(self):
        self.assertEqual(run('"a" in table("a", 1)'), True)
        self.assertEqual(run('"b" in table("a", 1)'), False)

    def test_in_a_number_explains_itself(self):
        with self.assertRaises(BoloError) as caught:
            run("1 in 2")
        self.assertIn("can't look inside", str(caught.exception))


class UseFiles(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.dir, ignore_errors=True))

    def write(self, name, text):
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def test_use_brings_in_functions_and_names(self):
        self.write("tools.bolo", 'to double(n) { n * 2 }\nanswer = 21\n')
        main = self.write("main.bolo", 'use "tools.bolo"\ndouble(answer)\n')
        self.assertEqual(bolo.run_file(main), 42)

    def test_use_adds_the_extension_for_a_bare_name(self):
        self.write("tools.bolo", 'note = "from tools"\n')
        main = self.write("main.bolo", "use tools\nnote\n")
        self.assertEqual(bolo.run_file(main), "from tools")

    def test_a_file_runs_only_once(self):
        self.write("tools.bolo", 'say("once")\n')
        main = self.write("main.bolo", 'use "tools.bolo"\nuse "tools.bolo"\n7\n')
        file_out = io.StringIO()
        with contextlib.redirect_stdout(file_out):
            self.assertEqual(bolo.run_file(main), 7)
        self.assertEqual(file_out.getvalue(), "once\n")

    def test_missing_file_has_a_clear_message(self):
        main = self.write("main.bolo", 'use "nope.bolo"\n')
        with self.assertRaises(BoloError) as caught:
            bolo.run_file(main)
        self.assertIn("can't open", str(caught.exception))


class MoreBuiltins(unittest.TestCase):
    def test_rounding(self):
        self.assertEqual(run("round(2.4)"), 2)
        self.assertEqual(run("round(2.5)"), 3)
        self.assertEqual(run("round(2.456, 2)"), 2.46)
        self.assertEqual(run("floor(2.9)"), 2)
        self.assertEqual(run("ceil(2.1)"), 3)

    def test_abs_and_sqrt(self):
        self.assertEqual(run("abs(-4)"), 4)
        self.assertEqual(run("sqrt(9)"), 3)
        with self.assertRaises(BoloError):
            run("sqrt(-1)")

    def test_min_max_and_average(self):
        self.assertEqual(run("min([3, 1, 2])"), 1)
        self.assertEqual(run("max(3, 9, 2)"), 9)
        self.assertEqual(run("average([2, 4, 6])"), 4)
        self.assertEqual(run("[2, 4, 6] |> mean"), 4)

    def test_min_rejects_a_mix(self):
        with self.assertRaises(BoloError):
            run('min([1, "a"])')

    def test_random_stays_in_range(self):
        for _ in range(20):
            value = run("random()")
            self.assertGreaterEqual(value, 0)
            self.assertLess(value, 1)
            roll = run("random_int(1, 6)")
            self.assertIn(roll, [1, 2, 3, 4, 5, 6])

    def test_choose_returns_one_of_the_items(self):
        self.assertIn(run('choose(["a", "b"])'), ["a", "b"])

    def test_now_and_today_are_text(self):
        self.assertRegex(run("now()"), r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
        self.assertRegex(run("today()"), r"^\d{4}-\d{2}-\d{2}$")

    def test_sleep_zero_is_fine(self):
        self.assertIsNone(run("sleep(0)"))

    def test_pad_and_repeat(self):
        self.assertEqual(run('pad("ab", 4)'), "ab  ")
        self.assertEqual(run('repeat("ab", 3)'), "ababab")
        self.assertEqual(run("repeat([1, 2], 2)"), [1, 2, 1, 2])

    def test_list_helpers(self):
        self.assertEqual(run('index_of(["a", "b"], "b")'), 1)
        self.assertEqual(run('index_of(["a"], "z")'), -1)
        self.assertEqual(run('index_of("hello", "ll")'), 2)
        self.assertEqual(run("insert([1, 3], 1, 2)"), [1, 2, 3])
        self.assertEqual(run("flatten([[1], [2, 3]])"), [1, 2, 3])
        self.assertEqual(run("slice([1, 2, 3, 4], 1, 3)"), [2, 3])
        self.assertEqual(run('slice("hello", 1)'), "ello")

    def test_insert_does_not_change_the_old_list(self):
        self.assertEqual(run("xs = [1]\ninsert(xs, 0, 0)\nxs"), [1])

    def test_json_round_trip(self):
        src = 'data = json("{\\"name\\": \\"Mari\\", \\"tags\\": [1, 2]}")\ndata["name"]'
        self.assertEqual(run(src), "Mari")
        self.assertEqual(run('json("[1, 2]")'), [1, 2])
        self.assertEqual(run('to_json([1, "a"])'), '[\n  1,\n  "a"\n]')

    def test_bad_json_says_so(self):
        with self.assertRaises(BoloError) as caught:
            run('json("[1, 2")')
        self.assertIn("not valid JSON", str(caught.exception))

    def test_quit_sets_the_exit_code(self):
        interp = bolo.Interp()
        result = interp.run(bolo.parse('say("bye")\nquit(3)\nsay("never")'))
        self.assertIsNone(result)
        self.assertEqual(interp.exit_code, 3)

    def test_quit_stops_the_program(self):
        self.assertEqual(output('quit(0)\nsay("never")'), "")


if __name__ == "__main__":
    unittest.main()
