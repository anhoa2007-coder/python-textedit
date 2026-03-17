# Text Editor (Python)
Text editor made with Python, as a basic project in part-time. It allows you to edit files using a terminal-based TUI powered by `curses`.

> **ANNOUNCEMENT: Final update will be published on December 31st, 2026.**

---

## How It Works

- **Core structure:**
  - The `TextEditor` class manages the document (`self.content` as a list of strings, one per line).
  - It tracks the current filename, whether the file is modified, undo/redo stacks, and the cursor position (`cy`, `cx`).
  - A viewport (`top_line`, `left_col`) handles scrolling both vertically and horizontally.
  - Each editing action saves the current document state to the undo stack before applying changes (up to 100 levels deep).

- **File operations:**
  - `_new_file()`, `_open_file()`, and `_save_file()` let you manage text files.
  - Files without an extension are automatically saved with `.txt`.
  - If there are unsaved changes, you'll be prompted to confirm before opening a new file or quitting.

- **Editing features:**
  - Type normally to insert characters; `Enter` creates a new line with auto-indent carried over from the current line.
  - `Backspace` / `Delete` remove characters or merge lines.
  - `Tab` inserts 4 spaces.
  - Undo and redo (`Ctrl+Z` / `Ctrl+Y`) roll back or reapply changes.
  - Find (`Ctrl+F`) and Find Next (`Ctrl+N`) search forward through the document with wrap-around.
  - Find & Replace (`Ctrl+R`) replaces all occurrences at once.
  - Both search and replace accept either **plain text** or **Python regex** — you choose the mode when prompted.
  - Go to line (`Ctrl+G`) jumps the cursor directly to any line number.

- **Display:**
  - A **header bar** shows the filename (or `Untitled`), a `[+]` indicator when there are unsaved changes, and the current line/column position.
  - A **line-number gutter** (4 digits wide) is shown to the left of every line. Rows past the end of the file display `~`.
  - A **footer bar** at the bottom lists all available key bindings at a glance.
  - A **status bar** sits just above the footer and shows feedback messages (e.g. "Saved", "Not found") colour-coded green/red/yellow.
  - The view scrolls automatically to keep the cursor visible, both vertically (page scrolling) and horizontally (long lines).

- **Keybindings:**

  | Key | Action |
  |-----|--------|
  | `Ctrl+S` | Save |
  | `Ctrl+O` | Open file |
  | `Ctrl+W` | New file |
  | `Ctrl+Z` | Undo |
  | `Ctrl+Y` | Redo |
  | `Ctrl+F` | Find |
  | `Ctrl+N` | Find next match |
  | `Ctrl+R` | Find & Replace |
  | `Ctrl+G` | Go to line |
  | `Ctrl+Q` | Quit |
  | `Home` / `End` | Beginning / end of line |
  | `PgUp` / `PgDn` | Scroll by page |
  | Arrow keys | Move cursor |

- **Entry point:**
  - `run()` launches the editor via `curses.wrapper()`.
  - You can pass a filename as a CLI argument to open it immediately on startup: `python editor.py myfile.txt`.

## How to run it?

Download the file, then run it in any terminal that supports Python and `curses`:

```bash
python editor.py
# or open a file directly
python editor.py myfile.txt
```

> **Note:** `curses` is part of the Python standard library on Linux and macOS. On Windows, you may need to install `windows-curses` via pip.
