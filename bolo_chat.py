"""Bolo Chat - a standalone local-AI chatbot with Bolo as its specialty.

It talks to Ollama on this machine, chats about anything, and can also write,
explain, check and run Bolo code. Nothing is sent to the internet.

Double-click `BOLO - Chat With AI.bat`, or run:

    python bolo_chat.py
"""

from __future__ import annotations

import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter.font as tkfont

if getattr(sys, "frozen", False):
    # A packaged BoloChat.exe: keep its scratch folder beside the install.
    APP_DIR = Path(sys.executable).resolve().parent
    DATA_DIR = Path(os.environ.get("LOCALAPPDATA", APP_DIR)) / "Bolo"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
else:
    APP_DIR = Path(__file__).resolve().parent
    DATA_DIR = APP_DIR
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import bolo  # noqa: E402  (import after the path fix above)
import bolo_ai  # noqa: E402

SANDBOX = DATA_DIR / "coder_sandbox"

PAPER = "#f6f5f1"
PANEL = "#ffffff"
INK = "#1d2227"
MUTED = "#6d7178"
ACCENT = "#2f6b4f"
ACCENT_DARK = "#234f3b"
RULE = "#d8d4ca"
FIELD = "#fcfbf8"
CONSOLE_BG = "#1c2126"
CONSOLE_FG = "#e8e6df"
CONSOLE_MUTED = "#9aa3ab"
ERR = "#a33b2a"

KEYWORDS = [
    "to", "if", "else", "for", "in", "return",
    "and", "or", "not", "is", "true", "false", "nothing", "nil",
]
BUILTIN_NAMES = sorted(set(bolo.BUILTINS), key=len, reverse=True)
TOKEN_RE = re.compile(
    r"(?P<comment>#[^\n]*)"
    r'|(?P<string>"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')'
    r"|(?P<number>\b\d+(?:\.\d+)?\b)"
    r"|(?P<keyword>\b(?:" + "|".join(KEYWORDS) + r")\b)"
    r"|(?P<builtin>\b(?:" + "|".join(re.escape(n) for n in BUILTIN_NAMES) + r")\b)"
    r"|(?P<pipe>\|>)"
)
FENCE_RE = re.compile(r"```(?:bolo|bollo)?[ \t]*\n?(.*?)```", re.DOTALL | re.IGNORECASE)


# ---------------------------------------------------------------------------
# Pure helpers (also exercised by the tests)
# ---------------------------------------------------------------------------


def extract_code(text: str) -> str | None:
    """Return the last fenced code block in an answer, or None."""
    blocks = [match.group(1).strip("\n") for match in FENCE_RE.finditer(text)]
    blocks = [block for block in blocks if block.strip()]
    if blocks:
        return blocks[-1].strip()
    return None


def trim_code(code: str, limit: int = 6000) -> str:
    code = code.strip()
    if len(code) <= limit:
        return code
    return code[:limit].rsplit("\n", 1)[0] + "\n# ... the rest was trimmed ..."


def build_messages(
    question: str,
    code: str = "",
    history: list[dict] | None = None,
    include_code: bool = True,
    system: str | None = None,
) -> list[dict]:
    messages = [{"role": "system", "content": system or bolo_ai.CHAT_SYSTEM}]
    code = trim_code(code)
    if include_code and code:
        messages.append(
            {
                "role": "system",
                "content": (
                    "The code currently in the editor is below. Use it only if "
                    "the user's question is about it.\n```bolo\n" + code + "\n```"
                ),
            }
        )
    if history:
        messages.extend(history[-10:])
    messages.append({"role": "user", "content": question})
    return messages


def check_source(source: str) -> tuple[bool, str, int | None]:
    """Parse Bolo code without running it. Returns (ok, message, error line)."""
    if not source.strip():
        return False, "There is no code to check yet.", None
    try:
        bolo.parse(source)
    except bolo.BoloError as err:
        message = bolo.format_error(source, "your code", err)
        return False, message, err.line
    return True, "No syntax errors. The code can run.", None


# ---------------------------------------------------------------------------
# The app
# ---------------------------------------------------------------------------


class ChatApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Bolo Chat - local AI")
        self.geometry("1180x760")
        self.minsize(920, 600)
        self.configure(bg=PAPER)

        self.mode = tk.StringVar(value="chat")
        self.chat_model: str | None = None
        self.code_model: str | None = None
        self.ai_checked = False
        self.pending = False
        self.queue: queue.Queue = queue.Queue()
        self.history: list[dict] = []
        self.last_answer = ""
        self.current_path: Path | None = None
        self.proc = None
        self.run_log: Path | None = None
        self.run_seen = False

        self._setup_fonts()
        self._setup_styles()
        self._build()
        self.after(120, self._poll_queue)
        self.after(200, self.check_ai)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # -- setup --------------------------------------------------------------
    def _setup_fonts(self) -> None:
        self.f_h1 = tkfont.Font(family="Segoe UI Semibold", size=19)
        self.f_h2 = tkfont.Font(family="Segoe UI Semibold", size=12)
        self.f_ui = tkfont.Font(family="Segoe UI", size=10)
        self.f_ui_bold = tkfont.Font(family="Segoe UI Semibold", size=10)
        self.f_small = tkfont.Font(family="Segoe UI", size=9)
        self.f_code = tkfont.Font(family="Consolas", size=10)
        self.f_code_small = tkfont.Font(family="Consolas", size=9)

    def _setup_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "TButton", font=self.f_ui, padding=(8, 5), background=PAPER, foreground=INK
        )
        style.map("TButton", background=[("active", "#e9e6de")])
        style.configure(
            "Accent.TButton",
            font=self.f_ui_bold,
            background=ACCENT,
            foreground="#ffffff",
            padding=(12, 6),
        )
        style.map(
            "Accent.TButton",
            background=[("active", ACCENT_DARK), ("disabled", "#9db5a7")],
        )
        style.configure(
            "Ghost.TButton",
            font=self.f_ui,
            background=PANEL,
            foreground=INK,
            padding=(8, 5),
        )
        style.map("Ghost.TButton", background=[("active", "#efede7")])
        style.configure(
            "Mode.TRadiobutton",
            font=self.f_ui_bold,
            padding=(10, 5),
            background="#e9e6de",
            foreground=INK,
        )
        style.map(
            "Mode.TRadiobutton",
            background=[("selected", ACCENT), ("active", "#e0ddd4")],
            foreground=[("selected", "#ffffff")],
        )

    def _build(self) -> None:
        self._build_header()
        self._build_toolbar()

        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=14, pady=(4, 12))
        paned.add(self._build_chat(paned), weight=2)
        paned.add(self._build_code(paned), weight=3)

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=PAPER)
        header.pack(fill="x", padx=20, pady=(14, 2))

        left = tk.Frame(header, bg=PAPER)
        left.pack(side="left")
        tk.Label(
            left, text="Bolo Chat", bg=PAPER, fg=INK, font=self.f_h1
        ).pack(anchor="w")
        tk.Label(
            left,
            text=(
                "Chat about anything. Bolo is its specialty. "
                "Nothing leaves this computer."
            ),
            bg=PAPER,
            fg=MUTED,
            font=self.f_small,
        ).pack(anchor="w", pady=(1, 0))

        right = tk.Frame(header, bg=PAPER)
        right.pack(side="right")

        modes = tk.Frame(right, bg=PAPER)
        modes.pack(side="left", padx=(0, 14))
        for label, value in (("Chat", "chat"), ("Bolo code", "code")):
            ttk.Radiobutton(
                modes,
                text=label,
                value=value,
                variable=self.mode,
                style="Mode.TRadiobutton",
                command=self._mode_changed,
            ).pack(side="left")
        self.ai_status = tk.Label(
            right, text="Checking local AI...", bg=PAPER, fg=MUTED, font=self.f_small
        )
        self.ai_status.pack(side="left", padx=(0, 8))
        ttk.Button(
            right,
            text="Check again",
            style="Ghost.TButton",
            command=self.recheck_ai,
        ).pack(side="left")

    def _build_toolbar(self) -> None:
        bar = tk.Frame(self, bg=PAPER)
        bar.pack(fill="x", padx=18, pady=(6, 2))

        ttk.Button(
            bar, text="Explain my code", command=self.explain_code
        ).pack(side="left")
        ttk.Button(bar, text="Fix my code", command=self.fix_code).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(bar, text="Improve my code", command=self.improve_code).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(
            bar, text="Write a program", command=self.start_writing
        ).pack(side="left", padx=(6, 0))
        ttk.Button(
            bar, text="Use code from answer", command=self.use_answer_code
        ).pack(side="left", padx=(6, 0))

        ttk.Button(
            bar, text="Clear chat", style="Ghost.TButton", command=self.clear_chat
        ).pack(side="right")

        self.include_code = tk.BooleanVar(value=True)
        tk.Checkbutton(
            bar,
            text="Send my code with each question",
            variable=self.include_code,
            bg=PAPER,
            fg=MUTED,
            activebackground=PAPER,
            activeforeground=INK,
            font=self.f_small,
            highlightthickness=0,
            borderwidth=0,
            cursor="hand2",
        ).pack(side="right", padx=(0, 10))

    # -- chat side ----------------------------------------------------------
    def _build_chat(self, parent: tk.Widget) -> tk.Frame:
        card = tk.Frame(
            parent, bg=PANEL, highlightbackground=RULE, highlightthickness=1
        )
        card.pack_propagate(False)

        head = tk.Frame(card, bg=PANEL)
        head.pack(fill="x", padx=14, pady=(10, 4))
        tk.Label(head, text="Chat", bg=PANEL, fg=INK, font=self.f_h2).pack(
            side="left"
        )
        tk.Label(
            head,
            text="Ctrl+Enter sends",
            bg=PANEL,
            fg=MUTED,
            font=self.f_small,
        ).pack(side="right")

        log_frame = tk.Frame(card, bg=PANEL)
        log_frame.pack(fill="both", expand=True, padx=(8, 4), pady=2)
        self.log = tk.Text(
            log_frame,
            wrap="word",
            bg=PANEL,
            fg=INK,
            font=self.f_ui,
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=6,
            spacing1=2,
            spacing3=3,
            cursor="arrow",
        )
        scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log.pack(fill="both", expand=True)
        self.log.tag_configure("you", font=self.f_ui_bold, foreground=ACCENT, spacing1=10)
        self.log.tag_configure("ai", font=self.f_ui_bold, foreground=INK, spacing1=10)
        self.log.tag_configure("body", font=self.f_ui, foreground=INK, spacing3=3)
        self.log.tag_configure(
            "code",
            font=self.f_code_small,
            foreground="#1c3b2c",
            background="#eef2ec",
            lmargin1=10,
            lmargin2=10,
            spacing1=4,
            spacing3=6,
        )
        self.log.tag_configure("muted", font=self.f_small, foreground=MUTED)
        self.log.tag_configure("err", font=self.f_ui, foreground=ERR)
        self.log.configure(state="disabled")
        self._say(
            "Chat about anything, or ask for Bolo code. Paste an error, or "
            "press one of the buttons above.\nThe first answer can take half "
            "a minute while the model wakes up.\n\n",
            "muted",
        )

        composer = tk.Frame(card, bg=PANEL)
        composer.pack(fill="x", padx=10, pady=(4, 10))

        box = tk.Frame(
            composer, bg=FIELD, highlightbackground=RULE, highlightthickness=1
        )
        box.pack(fill="x")
        self.prompt = tk.Text(
            box,
            height=3,
            wrap="word",
            bg=FIELD,
            fg=INK,
            insertbackground=ACCENT,
            font=self.f_ui,
            relief="flat",
            borderwidth=0,
            padx=8,
            pady=6,
        )
        self.prompt.pack(side="left", fill="both", expand=True)
        self.prompt.bind(
            "<Control-Return>", lambda _event: (self.ask(), "break")[1]
        )
        self.ask_button = ttk.Button(
            composer, text="Ask", style="Accent.TButton", command=self.ask
        )
        self.ask_button.pack(side="right", padx=(8, 0), pady=(6, 0))

        self.chat_note = tk.Label(
            composer, text="", bg=PANEL, fg=MUTED, font=self.f_small, anchor="w"
        )
        self.chat_note.pack(fill="x", pady=(4, 0))
        return card

    # -- code side ----------------------------------------------------------
    def _build_code(self, parent: tk.Widget) -> tk.Frame:
        card = tk.Frame(
            parent, bg=PANEL, highlightbackground=RULE, highlightthickness=1
        )
        card.pack_propagate(False)

        head = tk.Frame(card, bg=PANEL)
        head.pack(fill="x", padx=14, pady=(10, 4))
        tk.Label(head, text="Your Bolo code", bg=PANEL, fg=INK, font=self.f_h2).pack(
            side="left"
        )
        self.file_label = tk.Label(
            head, text="untitled.bolo", bg=PANEL, fg=MUTED, font=self.f_small
        )
        self.file_label.pack(side="right")

        bar = tk.Frame(card, bg=PANEL)
        bar.pack(fill="x", padx=12, pady=(2, 4))
        ttk.Button(bar, text="Open", style="Ghost.TButton", command=self.open_file).pack(
            side="left"
        )
        ttk.Button(bar, text="Save", style="Ghost.TButton", command=self.save_file).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(
            bar, text="Check", style="Ghost.TButton", command=self.check_code
        ).pack(side="left", padx=(14, 0))
        self.run_button = ttk.Button(
            bar, text="Run", style="Accent.TButton", command=self.run_code
        )
        self.run_button.pack(side="left", padx=(6, 0))
        self.stop_button = ttk.Button(
            bar, text="Stop", style="Ghost.TButton", command=self.stop_code
        )
        self.stop_button.pack(side="left", padx=(6, 0))
        ttk.Button(
            bar, text="Clear", style="Ghost.TButton", command=self.clear_editor
        ).pack(side="right")

        split = ttk.PanedWindow(card, orient="vertical")
        split.pack(fill="both", expand=True, padx=10, pady=(2, 10))

        editor_card = tk.Frame(split, bg=FIELD)
        self.editor = tk.Text(
            editor_card,
            wrap="none",
            undo=True,
            bg=FIELD,
            fg=INK,
            insertbackground=ACCENT,
            font=self.f_code,
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=8,
            spacing1=1,
            spacing3=1,
        )
        yscroll = ttk.Scrollbar(editor_card, command=self.editor.yview)
        self.editor.configure(yscrollcommand=yscroll.set)
        xscroll = ttk.Scrollbar(
            editor_card, orient="horizontal", command=self.editor.xview
        )
        self.editor.configure(xscrollcommand=xscroll.set)
        yscroll.pack(side="right", fill="y")
        xscroll.pack(side="bottom", fill="x")
        self.editor.pack(fill="both", expand=True)
        self._setup_editor_tags()
        self.editor.bind("<KeyRelease>", self._paint)
        self.editor.bind("<Tab>", self._insert_spaces)
        self.editor.insert(
            "1.0",
            '# Write Bolo here, or ask the AI for a program.\n'
            '# Then press Check, or Run to try it.\n\n'
            'say("hello")\n',
        )
        self.editor.edit_reset()
        self._paint()
        split.add(editor_card, weight=4)

        out_card = tk.Frame(split, bg=CONSOLE_BG)
        out_head = tk.Frame(out_card, bg=CONSOLE_BG)
        out_head.pack(fill="x", padx=12, pady=(6, 2))
        tk.Label(
            out_head, text="OUTPUT", bg=CONSOLE_BG, fg=CONSOLE_MUTED, font=self.f_small
        ).pack(side="left")
        self.run_state = tk.Label(
            out_head, text="", bg=CONSOLE_BG, fg=CONSOLE_MUTED, font=self.f_small
        )
        self.run_state.pack(side="right")
        self.output = tk.Text(
            out_card,
            height=7,
            wrap="word",
            bg=CONSOLE_BG,
            fg=CONSOLE_FG,
            font=self.f_code_small,
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=6,
            state="disabled",
        )
        self.output.pack(fill="both", expand=True, padx=(4, 4), pady=(0, 6))
        self.output.tag_configure("err", foreground="#ffb4a4")
        self.output.tag_configure("muted", foreground=CONSOLE_MUTED)
        self.output.tag_configure("ok", foreground="#9fe0b5")
        split.add(out_card, weight=1)

        self.after(300, lambda: self._set_sash(split, 460))
        return card

    def _setup_editor_tags(self) -> None:
        self.editor.tag_configure("comment", foreground=MUTED)
        self.editor.tag_configure("string", foreground="#a0522d")
        self.editor.tag_configure("number", foreground="#2b5d8a")
        self.editor.tag_configure("keyword", foreground=ACCENT, font=self.f_ui_bold)
        self.editor.tag_configure("builtin", foreground="#5b3f86")
        self.editor.tag_configure("pipe", foreground="#a33b2a")
        self.editor.tag_configure(
            "errline", background="#f7ddd7", foreground=INK
        )

    def _set_sash(self, paned: ttk.PanedWindow, position: int) -> None:
        try:
            paned.sashpos(0, position)
        except tk.TclError:
            pass

    def _insert_spaces(self, _event=None):
        self.editor.insert("insert", "    ")
        return "break"

    def _paint(self, _event=None) -> None:
        text = self.editor.get("1.0", "end-1c")
        for tag in ("comment", "string", "number", "keyword", "builtin", "pipe"):
            self.editor.tag_remove(tag, "1.0", "end")
        for match in TOKEN_RE.finditer(text):
            kind = match.lastgroup
            if not kind:
                continue
            start = f"1.0 + {match.start()}c"
            end = f"1.0 + {match.end()}c"
            self.editor.tag_add(kind, start, end)

    # -- chat plumbing ------------------------------------------------------
    def _say(self, text: str, tag: str = "body") -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text, tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _append_answer(self, answer: str) -> None:
        self.log.configure(state="normal")
        position = 0
        for match in FENCE_RE.finditer(answer):
            before = answer[position:match.start()]
            if before:
                self.log.insert("end", before + "\n", "body")
            code = match.group(1).strip("\n")
            self.log.insert("end", code + "\n", "code")
            position = match.end()
        rest = answer[position:]
        if rest:
            self.log.insert("end", rest.strip("\n") + "\n", "body")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _say_error(self, message: str) -> None:
        self._say(message + "\n\n", "err")

    # -- AI status ----------------------------------------------------------
    def check_ai(self) -> None:
        if self.ai_checked:
            return
        self.ai_checked = True
        self.ai_status.configure(text="Checking local AI...", fg=MUTED)
        threading.Thread(target=self._status_worker, daemon=True).start()

    def recheck_ai(self) -> None:
        self.ai_checked = False
        self.check_ai()

    def _status_worker(self) -> None:
        try:
            names = bolo_ai.models()
        except bolo_ai.OllamaError as exc:
            self.queue.put(("status", None, None, str(exc)))
            return
        chat_model = bolo_ai.pick_model(names, bolo_ai.CHAT_PREFERRED)
        code_model = bolo_ai.pick_model(names, bolo_ai.CODER_PREFERRED)
        if chat_model is None:
            self.queue.put(
                (
                    "status",
                    None,
                    None,
                    "Ollama is running, but it has no models yet. Run:  "
                    "ollama pull llama3.2:3b",
                )
            )
            return
        self.queue.put(("status", chat_model, code_model, None))

    def _apply_status(
        self, chat_model: str | None, code_model: str | None, error: str | None
    ) -> None:
        if error:
            self.chat_model = None
            self.code_model = None
            self.ai_checked = False
            self.ai_status.configure(text=error.split("\n")[0], fg=ERR)
            self._say(
                "The local AI is not ready. " + error + "\n"
                "Start Ollama from the Start menu, then press Check again.\n\n",
                "err",
            )
            return
        self.chat_model = chat_model
        self.code_model = code_model or chat_model
        self.ai_checked = True
        self._refresh_model_label()

    def _active_model(self) -> str | None:
        if self.mode.get() == "code":
            return self.code_model or self.chat_model
        return self.chat_model or self.code_model

    def _refresh_model_label(self) -> None:
        model = self._active_model()
        if model is None:
            self.ai_status.configure(text="Local AI not ready", fg=ERR)
        else:
            self.ai_status.configure(text="Local AI ready - " + model, fg=ACCENT)

    def _mode_changed(self) -> None:
        self._refresh_model_label()
        if self.mode.get() == "code":
            self.chat_note.configure(
                text="Bolo code mode: complete, runnable Bolo."
            )
        else:
            self.chat_note.configure(text="Chat mode: ask me anything.")

    # -- asking -------------------------------------------------------------
    def ask(self, prompt: str | None = None) -> None:
        if self.pending:
            return
        model = self._active_model()
        if model is None:
            self.check_ai()
            self._say(
                "The local AI is not ready yet. Check the status at the top, "
                "then ask again.\n\n",
                "err",
            )
            return

        question = prompt if prompt is not None else self.prompt.get(
            "1.0", "end-1c"
        ).strip()
        if not question:
            if self.mode.get() == "code":
                question = (
                    "Write a small, complete Bolo program that shows what the "
                    "language can do."
                )
            else:
                question = "Tell me something interesting about the world."
        if prompt is None:
            self.prompt.delete("1.0", "end")

        self._say("You\n", "you")
        self._say(question + "\n\n", "body")

        code_mode = self.mode.get() == "code"
        code = self.editor.get("1.0", "end-1c")
        messages = build_messages(
            question,
            code,
            self.history,
            self.include_code.get(),
            system=bolo_ai.CODER_SYSTEM if code_mode else bolo_ai.CHAT_SYSTEM,
        )
        self.history.append({"role": "user", "content": question})

        self.pending = True
        self.ask_button.state(["disabled"])
        self.chat_note.configure(
            text="Thinking... the first answer can take half a minute."
        )
        threading.Thread(
            target=self._worker,
            args=(messages, model, 0.2 if code_mode else 0.7),
            daemon=True,
        ).start()

    def _worker(self, messages: list[dict], model: str, temperature: float) -> None:
        try:
            answer = bolo_ai.chat(messages, model, temperature=temperature)
        except bolo_ai.OllamaError as exc:
            self.queue.put(("error", str(exc)))
        except Exception as exc:  # noqa: BLE001 - shown in the chat
            self.queue.put(("error", f"Unexpected problem: {exc}"))
        else:
            self.queue.put(("answer", answer))

    def _finish_answer(self, answer: str) -> None:
        self.pending = False
        self.ask_button.state(["!disabled"])
        self.last_answer = answer
        code = extract_code(answer)
        note = "Code found - press Use code from answer." if code else ""
        self.chat_note.configure(text=note)
        self._say("Bolo Chat\n", "ai")
        self._append_answer(answer)
        self._say("\n", "body")
        self.history.append({"role": "assistant", "content": answer})
        if len(self.history) > 24:
            self.history = self.history[-24:]

    def _finish_error(self, message: str) -> None:
        self.pending = False
        self.ask_button.state(["!disabled"])
        self.chat_note.configure(text="")
        self._say("Bolo Chat could not answer\n", "ai")
        self._say_error(message)

    def _poll_queue(self) -> None:
        try:
            while True:
                item = self.queue.get_nowait()
                if item[0] == "status":
                    self._apply_status(item[1], item[2])
                elif item[0] == "answer":
                    self._finish_answer(item[1])
                elif item[0] == "error":
                    self._finish_error(item[1])
        except queue.Empty:
            pass
        self.after(120, self._poll_queue)

    # -- quick prompts ------------------------------------------------------
    def explain_code(self) -> None:
        self.ask(
            "Explain what the code in my editor does, step by step, in plain "
            "words. Do not rewrite it unless something is wrong."
        )

    def fix_code(self) -> None:
        self.ask(
            "Find the bug in the code in my editor. Name the line and the exact "
            "change, then give the corrected complete program in one ```bolo block."
        )

    def improve_code(self) -> None:
        self.ask(
            "Make the code in my editor shorter and clearer without changing what "
            "it does. Return the complete program in one ```bolo block."
        )

    def start_writing(self) -> None:
        self.prompt.focus_set()
        current = self.prompt.get("1.0", "end-1c").strip()
        if not current:
            self.prompt.insert("1.0", "Write a Bolo program that ")
            self.prompt.mark_set("insert", "end")
        self.chat_note.configure(
            text="Finish the sentence, then press Ask (or Ctrl+Enter)."
        )

    def use_answer_code(self) -> None:
        code = extract_code(self.last_answer)
        if not code:
            self.chat_note.configure(
                text="The last answer had no code block to take."
            )
            return
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", code + "\n")
        self.editor.edit_reset()
        self._paint()
        self.current_path = None
        self.file_label.configure(text="untitled.bolo")
        self.chat_note.configure(text="Code moved into the editor. Press Check or Run.")
        self.clear_output()
        self._write_output("Code moved from the chat into the editor.\n", "muted")

    def clear_chat(self) -> None:
        self.history.clear()
        self.last_answer = ""
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self._say(
            "Chat cleared. Ask for a program, paste an error, or press one of "
            "the buttons above.\n\n",
            "muted",
        )
        self.chat_note.configure(text="")

    # -- files --------------------------------------------------------------
    def open_file(self) -> None:
        chosen = filedialog.askopenfilename(
            parent=self,
            title="Open a Bolo file",
            filetypes=[("Bolo files", "*.bolo"), ("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not chosen:
            return
        path = Path(chosen)
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Bolo Chat", f"Could not read that file:\n{exc}", parent=self)
            return
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", source)
        self.editor.edit_reset()
        self._paint()
        self.current_path = path
        self.file_label.configure(text=path.name)
        self._write_output(f"Opened {path}\n", "muted")

    def save_file(self) -> None:
        path = self.current_path
        if path is None:
            chosen = filedialog.asksaveasfilename(
                parent=self,
                title="Save your Bolo program",
                defaultextension=".bolo",
                filetypes=[("Bolo files", "*.bolo"), ("Text files", "*.txt")],
            )
            if not chosen:
                return
            path = Path(chosen)
        try:
            path.write_text(self.editor.get("1.0", "end-1c"), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Bolo Chat", f"Could not save:\n{exc}", parent=self)
            return
        self.current_path = path
        self.file_label.configure(text=path.name)
        self._write_output(f"Saved {path}\n", "ok")

    def clear_editor(self) -> None:
        if not messagebox.askyesno(
            "Clear the editor?",
            "This removes the code in the editor. It cannot be undone.",
            parent=self,
        ):
            return
        self.editor.delete("1.0", "end")
        self.current_path = None
        self.file_label.configure(text="untitled.bolo")
        self._paint()

    # -- checking and running ----------------------------------------------
    def check_code(self) -> None:
        source = self.editor.get("1.0", "end-1c")
        ok, message, line = check_source(source)
        self.editor.tag_remove("errline", "1.0", "end")
        self.clear_output()
        if ok:
            self._write_output(message + "\n", "ok")
        else:
            self._write_output(message + "\n", "err")
            if line:
                self.editor.tag_add("errline", f"{line}.0", f"{line}.end")
                self.editor.see(f"{line}.0")

    def run_code(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            self._write_output("A program is already running. Press Stop first.\n", "err")
            return
        source = self.editor.get("1.0", "end-1c")
        if not source.strip():
            self._write_output("There is no code to run.\n", "err")
            return

        ok, message, line = check_source(source)
        if not ok:
            self.clear_output()
            self._write_output(message + "\n", "err")
            if line:
                self.editor.tag_add("errline", f"{line}.0", f"{line}.end")
                self.editor.see(f"{line}.0")
            return
        self.editor.tag_remove("errline", "1.0", "end")

        shutil.rmtree(SANDBOX, ignore_errors=True)
        SANDBOX.mkdir(parents=True, exist_ok=True)
        script = SANDBOX / "program.bolo"
        script.write_text(source, encoding="utf-8")
        log = SANDBOX / "output.txt"

        exe = Path(sys.executable)
        if exe.name.lower() == "pythonw.exe":
            candidate = exe.with_name("python.exe")
            if candidate.exists():
                exe = candidate

        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        try:
            with open(log, "w", encoding="utf-8") as handle:
                proc = subprocess.Popen(
                    self._run_command(script, exe),
                    cwd=str(SANDBOX),
                    stdout=handle,
                    stderr=subprocess.STDOUT,
                    creationflags=flags,
                )
        except OSError as exc:
            self._write_output(f"Could not start Python: {exc}\n", "err")
            return

        self.proc = proc
        self.run_log = log
        self.run_seen = False
        self.run_button.state(["disabled"])
        self.run_state.configure(text="running...")
        self.clear_output()
        self._write_output("Running in coder_sandbox...\n", "muted")
        self._watch_run()

    def _run_command(self, script: Path, exe: Path) -> list[str]:
        """Start Bolo from source, or from the bolo.exe shipped beside a build."""
        if getattr(sys, "frozen", False):
            folder = Path(sys.executable).resolve().parent
            for name in ("bolo.exe", "bolo"):
                candidate = folder / name
                if candidate.exists():
                    return [str(candidate), str(script)]
            return [str(exe), str(script)]
        return [str(exe), str(APP_DIR / "bolo.py"), str(script)]

    def _watch_run(self) -> None:
        proc = self.proc
        if proc is None:
            return
        if proc.poll() is None:
            if not self.run_seen:
                self.run_seen = True
                self.run_state.configure(text="window open - close it to finish")
            self.after(400, self._watch_run)
            return

        self.proc = None
        self.run_button.state(["!disabled"])
        self.run_state.configure(text="finished")
        output = ""
        if self.run_log is not None:
            try:
                output = self.run_log.read_text(
                    encoding="utf-8", errors="replace"
                ).strip()
            except OSError:
                output = ""
        self.clear_output()
        if output:
            self._write_output(output + "\n", "err" if "bolo:" in output else None)
        else:
            self._write_output("Finished with no output.\n", "muted")

    def stop_code(self) -> None:
        if self.proc is None or self.proc.poll() is not None:
            self._write_output("No program is running.\n", "muted")
            return
        try:
            self.proc.terminate()
        except OSError:
            pass
        self.proc = None
        self.run_button.state(["!disabled"])
        self.run_state.configure(text="stopped")
        self._write_output("Program stopped.\n", "muted")

    # -- output -------------------------------------------------------------
    def clear_output(self) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")

    def _write_output(self, text: str, tag: str | None = None) -> None:
        self.output.configure(state="normal")
        if tag:
            self.output.insert("end", text, tag)
        else:
            self.output.insert("end", text)
        self.output.see("end")
        self.output.configure(state="disabled")

    # -- close --------------------------------------------------------------
    def _on_close(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except OSError:
                pass
            self.proc = None
        self.destroy()


def main() -> None:
    app = ChatApp()
    app.mainloop()


if __name__ == "__main__":
    main()
