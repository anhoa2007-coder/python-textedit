#!/usr/bin/env python3
"""
editor_tui.py  –  A mini TUI text editor (curses, stdlib only)
Compatible with Python 3.8–3.11 / libraries available up to early 2023.

Keybindings
-----------
  Ctrl+S  Save          Ctrl+O  Open          Ctrl+N  New
  Ctrl+Z  Undo          Ctrl+Y  Redo
  Ctrl+F  Find          Ctrl+R  Find & Replace
  Ctrl+G  Go to line    Ctrl+Q  Quit
  Home/End  BOL / EOL   PgUp/PgDn  Page scroll
  Arrows  Move cursor   Enter  New line       Bksp/Del  Delete
"""

import os
import sys
import copy
import re
import curses


# ── colour palette (defined once, resolved in _init_colors) ──────────────────
_C = {}   # filled by _init_colors()

TAB_WIDTH   = 4
LINE_NUM_W  = 5   # "  12 " — 4 digits + space


def _init_colors():
    """Set up colour pairs; fall back gracefully when colours unavailable."""
    global _C
    curses.start_color()
    curses.use_default_colors()

    bg = -1  # transparent background

    # pair numbers → (fg, bg)
    pairs = {
        "header":     (curses.COLOR_BLACK,  curses.COLOR_CYAN),
        "footer":     (curses.COLOR_BLACK,  curses.COLOR_CYAN),
        "linenum":    (curses.COLOR_CYAN,   bg),
        "tilde":      (curses.COLOR_BLUE,   bg),
        "status_ok":  (curses.COLOR_BLACK,  curses.COLOR_GREEN),
        "status_err": (curses.COLOR_WHITE,  curses.COLOR_RED),
        "status_inf": (curses.COLOR_BLACK,  curses.COLOR_YELLOW),
        "normal":     (curses.COLOR_WHITE,  bg),
    }

    for idx, (name, (fg, bg_c)) in enumerate(pairs.items(), start=1):
        try:
            curses.init_pair(idx, fg, bg_c)
            _C[name] = curses.color_pair(idx)
        except curses.error:
            _C[name] = 0

    _C["header"]  |= curses.A_BOLD
    _C["footer"]  |= curses.A_BOLD
    _C["linenum"] |= curses.A_DIM


# ── helpers ───────────────────────────────────────────────────────────────────

def _clamp(v, lo, hi):
    return max(lo, min(hi, v))

def _expand_tabs(s):
    """Expand hard tabs to spaces (TAB_WIDTH)."""
    return s.expandtabs(TAB_WIDTH)


# ── editor ────────────────────────────────────────────────────────────────────

class TextEditor:
    def __init__(self):
        self.content:    list[str]  = [""]
        self.filename:   str | None = None
        self.modified:   bool       = False

        self.undo_stack: list[list[str]] = []
        self.redo_stack: list[list[str]] = []
        self.max_undo = 100

        # cursor (logical, 0-based)
        self.cy: int = 0
        self.cx: int = 0

        # viewport
        self.top_line: int = 0
        self.left_col: int = 0

        # transient status message
        self._status_msg:  str  = ""
        self._status_kind: str  = "inf"   # "ok" | "err" | "inf"

        # search state (for repeat-find)
        self._last_search: str = ""

    # ── undo / redo ──────────────────────────────────────────────────────────

    def _save_state(self):
        self.undo_stack.append(copy.deepcopy(self.content))
        if len(self.undo_stack) > self.max_undo:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def _undo(self):
        if self.undo_stack:
            self.redo_stack.append(copy.deepcopy(self.content))
            self.content  = self.undo_stack.pop()
            self.modified = True
            self._clamp_cursor()
            return True
        return False

    def _redo(self):
        if self.redo_stack:
            self.undo_stack.append(copy.deepcopy(self.content))
            self.content  = self.redo_stack.pop()
            self.modified = True
            self._clamp_cursor()
            return True
        return False

    def _clamp_cursor(self):
        self.cy = _clamp(self.cy, 0, max(0, len(self.content) - 1))
        max_cx  = len(self.content[self.cy]) if self.content else 0
        self.cx = _clamp(self.cx, 0, max_cx)

    # ── status bar messaging ──────────────────────────────────────────────────

    def _set_status(self, msg: str, kind: str = "inf"):
        self._status_msg  = msg
        self._status_kind = kind

    # ── TUI prompt helpers ────────────────────────────────────────────────────

    def _prompt(self, stdscr, message: str, default: str = "") -> str:
        h, w = stdscr.getmaxyx()
        prompt_y = h - 2
        stdscr.addstr(prompt_y, 0, " " * (w - 1))
        stdscr.addstr(prompt_y, 0, message, _C.get("status_inf", 0))
        stdscr.refresh()
        curses.echo()
        curses.curs_set(1)
        try:
            raw = stdscr.getstr(prompt_y, len(message), w - len(message) - 1)
            resp = raw.decode("utf-8", errors="ignore").strip()
        except Exception:
            resp = ""
        finally:
            curses.noecho()
        return resp or default

    def _confirm(self, stdscr, message: str) -> bool:
        h, w = stdscr.getmaxyx()
        prompt_y = h - 2
        stdscr.addstr(prompt_y, 0, " " * (w - 1))
        stdscr.addstr(prompt_y, 0, message + " [y/n] ", _C.get("status_inf", 0))
        stdscr.refresh()
        while True:
            key = stdscr.getch()
            if key in (ord('y'), ord('Y')):
                return True
            if key in (ord('n'), ord('N'), 27):
                return False

    # ── file operations ───────────────────────────────────────────────────────

    def _reset_state(self):
        self.modified = False
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.cy = self.cx = self.top_line = self.left_col = 0

    def _new_file(self, stdscr):
        if self.modified and not self._confirm(stdscr, "Unsaved changes — discard?"):
            return
        self.content  = [""]
        self.filename = None
        self._reset_state()
        self._set_status("New file", "ok")

    def _open_file(self, stdscr, filename: str | None = None):
        if self.modified and not self._confirm(stdscr, "Unsaved changes — discard?"):
            return

        filename = filename or self._prompt(stdscr, "Open: ")
        if not filename:
            return
        if not os.path.splitext(filename)[1]:
            filename += ".txt"

        try:
            with open(filename, "r", encoding="utf-8") as fh:
                lines = fh.read().splitlines()
            self.content  = lines if lines else [""]
            self.filename = filename
            self._reset_state()
            self._set_status(f"Opened  {filename}", "ok")
        except FileNotFoundError:
            self._set_status(f"File not found: {filename}", "err")
        except OSError as exc:
            self._set_status(f"Error opening file: {exc}", "err")

    def _save_file(self, stdscr, save_as: bool = False):
        if not self.filename or save_as:
            name = self._prompt(stdscr, "Save as: ", self.filename or "")
            if not name:
                self._set_status("Save cancelled", "inf")
                return
            if not os.path.splitext(name)[1]:
                name += ".txt"
            self.filename = name
        try:
            with open(self.filename, "w", encoding="utf-8") as fh:
                fh.write("\n".join(self.content))
            self.modified = False
            self._set_status(f"Saved  {self.filename}", "ok")
        except OSError as exc:
            self._set_status(f"Save error: {exc}", "err")

    # ── search / replace ──────────────────────────────────────────────────────

    def _find_next(self, stdscr, term: str | None = None) -> bool:
        """Jump to the next occurrence of `term` (wraps around)."""
        if term is None:
            term = self._prompt(stdscr, "Find: ", self._last_search)
        if not term:
            return False
        self._last_search = term

        total = len(self.content)
        pat   = re.compile(re.escape(term), re.IGNORECASE)

        # search from just after the current position
        for offset in range(1, total + 1):
            idx  = (self.cy + offset) % total
            line = self.content[idx]
            m    = pat.search(line)
            if m:
                self.cy = idx
                self.cx = m.start()
                self._set_status(f"Found '{term}'  (line {idx+1})", "ok")
                return True

        self._set_status(f"'{term}' not found", "err")
        return False

    def _replace_all(self, stdscr):
        term = self._prompt(stdscr, "Find: ", self._last_search)
        if not term:
            return
        self._last_search = term
        repl  = self._prompt(stdscr, "Replace with: ")
        pat   = re.compile(re.escape(term), re.IGNORECASE)
        self._save_state()
        count = 0
        for i, line in enumerate(self.content):
            new_line, n = pat.subn(repl, line)
            self.content[i] = new_line
            count += n
        if count:
            self.modified = True
            self._set_status(f"Replaced {count} occurrence(s)", "ok")
        else:
            self._set_status(f"'{term}' not found", "err")

    def _goto_line(self, stdscr):
        raw = self._prompt(stdscr, f"Go to line (1–{len(self.content)}): ")
        if raw.isdigit():
            target = _clamp(int(raw) - 1, 0, len(self.content) - 1)
            self.cy = target
            self.cx = 0
            self._set_status(f"Jumped to line {target+1}", "ok")
        else:
            self._set_status("Invalid line number", "err")

    # ── viewport ──────────────────────────────────────────────────────────────

    def _adjust_view(self, h: int, w: int):
        text_w   = w - LINE_NUM_W
        max_rows = h - 3   # header + footer + status

        # vertical
        self.top_line = _clamp(self.top_line,
                               self.cy - max_rows + 1,
                               self.cy)
        self.top_line = max(0, self.top_line)

        # horizontal — work on expanded line for screen placement
        line_exp  = _expand_tabs(self.content[self.cy]) if self.content else ""
        screen_cx = len(_expand_tabs(self.content[self.cy][:self.cx])) if self.content else 0
        if screen_cx < self.left_col:
            self.left_col = screen_cx
        if screen_cx >= self.left_col + text_w - 1:
            self.left_col = screen_cx - text_w + 2
        self.left_col = max(0, self.left_col)

    # ── drawing ───────────────────────────────────────────────────────────────

    def _draw(self, stdscr):
        h, w = stdscr.getmaxyx()
        self._adjust_view(h, w)
        stdscr.erase()

        text_w   = w - LINE_NUM_W
        max_rows = h - 3

        # ── header bar ───────────────────────────────────────────────────────
        title    = f" {self.filename or 'Untitled'}"
        if self.modified:
            title += " [+]"
        pos_info = f" Ln {self.cy+1}/{len(self.content)}  Col {self.cx+1} "
        padding  = w - len(title) - len(pos_info)
        header   = title + " " * max(0, padding) + pos_info
        try:
            stdscr.addstr(0, 0, header[:w], _C.get("header", curses.A_REVERSE))
        except curses.error:
            pass

        # ── text area ────────────────────────────────────────────────────────
        for row in range(max_rows):
            line_idx = self.top_line + row
            scr_y    = row + 1

            # line-number gutter
            if line_idx < len(self.content):
                linenum_str = f"{line_idx+1:>{LINE_NUM_W-1}} "
            else:
                linenum_str = " " * LINE_NUM_W

            try:
                if line_idx < len(self.content):
                    stdscr.addstr(scr_y, 0, linenum_str, _C.get("linenum", 0))
                else:
                    stdscr.addstr(scr_y, 0, " " * (LINE_NUM_W - 1), 0)
                    stdscr.addstr(scr_y, LINE_NUM_W - 1, "~", _C.get("tilde", 0))
            except curses.error:
                pass

            if line_idx < len(self.content):
                expanded = _expand_tabs(self.content[line_idx])
                visible  = expanded[self.left_col : self.left_col + text_w - 1]
                try:
                    stdscr.addstr(scr_y, LINE_NUM_W, visible, _C.get("normal", 0))
                except curses.error:
                    pass

        # ── status / message bar ─────────────────────────────────────────────
        if self._status_msg:
            colour_key = f"status_{self._status_kind}"
            colour     = _C.get(colour_key, _C.get("status_inf", 0))
            msg        = f" {self._status_msg} "
            try:
                stdscr.addstr(h - 2, 0, msg[:w], colour)
            except curses.error:
                pass
        
        # ── footer key-hint bar ───────────────────────────────────────────────
        hints = (
            "^S Save  ^O Open  ^N New  ^Z Undo  ^Y Redo  "
            "^F Find  ^R Replace  ^G Goto  ^Q Quit"
        )
        try:
            stdscr.addstr(h - 1, 0, hints[:w], _C.get("footer", curses.A_REVERSE))
        except curses.error:
            pass

        # ── place cursor ─────────────────────────────────────────────────────
        cur_expanded_cx = len(_expand_tabs(self.content[self.cy][:self.cx])) if self.content else 0
        scr_y = 1 + (self.cy - self.top_line)
        scr_x = LINE_NUM_W + (cur_expanded_cx - self.left_col)
        if 1 <= scr_y <= h - 3 and LINE_NUM_W <= scr_x < w:
            try:
                stdscr.move(scr_y, scr_x)
            except curses.error:
                pass

        stdscr.refresh()

    # ── editing primitives ────────────────────────────────────────────────────

    def _insert_char(self, ch: str):
        self._save_state()
        if not self.content:
            self.content = [""]
        if self.cy >= len(self.content):
            self.content.append("")
        line             = self.content[self.cy]
        self.content[self.cy] = line[:self.cx] + ch + line[self.cx:]
        self.cx         += len(ch)
        self.modified    = True

    def _insert_newline(self):
        self._save_state()
        if not self.content:
            self.content = [""]
        line = self.content[self.cy]
        # auto-indent: carry leading whitespace to new line
        indent = len(line) - len(line.lstrip())
        left, right = line[:self.cx], line[self.cx:]
        self.content[self.cy] = left
        self.content.insert(self.cy + 1, " " * indent + right)
        self.cy  += 1
        self.cx   = indent
        self.modified = True

    def _backspace(self):
        self._save_state()
        if not self.content:
            return
        if self.cx > 0:
            line             = self.content[self.cy]
            self.content[self.cy] = line[:self.cx - 1] + line[self.cx:]
            self.cx         -= 1
        elif self.cy > 0:
            prev              = self.content[self.cy - 1]
            cur               = self.content.pop(self.cy)
            self.cy          -= 1
            self.cx           = len(self.content[self.cy])
            self.content[self.cy] = prev + cur
        self.modified = True

    def _delete_char(self):
        self._save_state()
        if not self.content:
            return
        if self.cy < len(self.content):
            line = self.content[self.cy]
            if self.cx < len(line):
                self.content[self.cy] = line[:self.cx] + line[self.cx + 1:]
            elif self.cy < len(self.content) - 1:
                nxt = self.content.pop(self.cy + 1)
                self.content[self.cy] += nxt
        self.modified = True

    # ── cursor movement ───────────────────────────────────────────────────────

    def _move_up(self):
        if self.cy > 0:
            self.cy -= 1
            self.cx  = _clamp(self.cx, 0, len(self.content[self.cy]))

    def _move_down(self):
        if self.cy < len(self.content) - 1:
            self.cy += 1
            self.cx  = _clamp(self.cx, 0, len(self.content[self.cy]))

    def _move_left(self):
        if self.cx > 0:
            self.cx -= 1
        elif self.cy > 0:
            self.cy -= 1
            self.cx  = len(self.content[self.cy])

    def _move_right(self):
        line_len = len(self.content[self.cy]) if self.content else 0
        if self.cx < line_len:
            self.cx += 1
        elif self.cy < len(self.content) - 1:
            self.cy += 1
            self.cx  = 0

    def _page_up(self, h: int):
        page = max(1, h - 4)
        self.cy = max(0, self.cy - page)
        self.cx = _clamp(self.cx, 0, len(self.content[self.cy]))

    def _page_down(self, h: int):
        page = max(1, h - 4)
        last = max(0, len(self.content) - 1)
        self.cy = min(last, self.cy + page)
        self.cx = _clamp(self.cx, 0, len(self.content[self.cy]))

    # ── main loop ────────────────────────────────────────────────────────────

    def _main(self, stdscr):
        _init_colors()
        curses.curs_set(1)
        stdscr.keypad(True)
        stdscr.timeout(80)

        # optional CLI argument
        if len(sys.argv) > 1:
            self._open_file(stdscr, sys.argv[1])

        while True:
            self._draw(stdscr)
            key = stdscr.getch()
            if key == -1:
                continue
            if key == curses.KEY_RESIZE:
                continue

            # clear status on every fresh keystroke
            self._status_msg = ""

            h, _ = stdscr.getmaxyx()

            # ── command keys ─────────────────────────────────────────────────
            if   key == 17:                          # Ctrl+Q
                if self.modified and not self._confirm(stdscr, "Unsaved changes — quit?"):
                    continue
                break

            elif key == 19:   self._save_file(stdscr)           # Ctrl+S
            elif key == 15:   self._open_file(stdscr)           # Ctrl+O
            elif key == 14:   self._new_file(stdscr)            # Ctrl+N
            elif key == 26:                                       # Ctrl+Z
                if not self._undo():
                    self._set_status("Nothing to undo", "inf")
                else:
                    self._set_status("Undo", "ok")
            elif key == 25:                                       # Ctrl+Y
                if not self._redo():
                    self._set_status("Nothing to redo", "inf")
                else:
                    self._set_status("Redo", "ok")
            elif key == 6:    self._find_next(stdscr)           # Ctrl+F
            elif key == 18:   self._replace_all(stdscr)         # Ctrl+R
            elif key == 7:    self._goto_line(stdscr)           # Ctrl+G

            # ── movement ─────────────────────────────────────────────────────
            elif key == curses.KEY_UP:       self._move_up()
            elif key == curses.KEY_DOWN:     self._move_down()
            elif key == curses.KEY_LEFT:     self._move_left()
            elif key == curses.KEY_RIGHT:    self._move_right()
            elif key == curses.KEY_HOME:     self.cx = 0
            elif key == curses.KEY_END:
                self.cx = len(self.content[self.cy]) if self.content else 0
            elif key == curses.KEY_PPAGE:    self._page_up(h)
            elif key == curses.KEY_NPAGE:    self._page_down(h)

            # ── editing ───────────────────────────────────────────────────────
            elif key in (curses.KEY_ENTER, 10, 13):
                self._insert_newline()
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                self._backspace()
            elif key == curses.KEY_DC:
                self._delete_char()
            elif key == 9:   # Tab → spaces
                self._insert_char(" " * TAB_WIDTH)
            elif 32 <= key <= 126:
                self._insert_char(chr(key))

    def run(self):
        curses.wrapper(self._main)


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    editor = TextEditor()
    editor.run()


if __name__ == "__main__":
    main()