# Text Editor (Python)
Text editor made with Python, as a basic project in part-time. It allow you to edit files using CLI based UI.

---
## How It Works
- **Core structure:**
  - The TextEditor class manages the document (`self.content` as a list of lines).
  - It tracks whether the file is modified, the filename, undo/redo stacks, and word wrap settings.
  - Each editing action (add, edit, insert, delete, replace) saves the current state for undo/redo.
- **File operations:**
  - `new_file()`, `open_file()`, `save_file()`, and `save_as()` let you manage text files.
  - Files are always saved with .txt extension.
- **Editing features:**
  - Add, insert, edit, and delete lines interactively.
  - Undo/redo stacks allow rolling back changes.
  - Find and replace text across the document.
- **Display:**
  - Shows line numbers and applies word wrapping if enabled.
  - Wrap width can be customized.
- **Interactive loop:**
  - The `run()` method starts a command loop where you type commands (`n`, `o`, `s`, `v`, `e`, `+`, etc.).
  - It prints a help menu (`h`) with all available commands.
  - You quit with `q`.
## How to run it?
  - You download the files, then run the file in the terminal that support Python.
