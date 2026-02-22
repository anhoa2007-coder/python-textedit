import os
import sys
import copy
import re

class TextEditor:
    def __init__(self):
        self.content = []  # List of lines
        self.filename = None
        self.modified = False
        self.word_wrap = True
        self.wrap_width = 80
        self.undo_stack = []
        self.redo_stack = []
        self.max_undo = 50
        
    def save_state(self):
        state = copy.deepcopy(self.content)
        self.undo_stack.append(state)
        if len(self.undo_stack) > self.max_undo:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        
    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(copy.deepcopy(self.content))
            self.content = self.undo_stack.pop()
            self.modified = True
            return True
        return False
        
    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(copy.deepcopy(self.content))
            self.content = self.redo_stack.pop()
            self.modified = True
            return True
        return False
    
    def new_file(self):
        if self.modified:
            response = input("Current file has unsaved changes. Discard? (y/n): ").lower()
            if response != 'y':
                return False
        self.content = []
        self.filename = None
        self.modified = False
        self.undo_stack.clear()
        self.redo_stack.clear()
        print("\n✓ New file created.\n")
        return True
    
    def open_file(self, filename=None):
        if self.modified:
            response = input("Current file has unsaved changes. Discard? (y/n): ").lower()
            if response != 'y':
                return False
                
        if filename is None:
            filename = input("Enter filename to open: ").strip()
            
        if not filename:
            print("✗ No filename provided.")
            return False
            
        if not filename.lower().endswith('.txt'):
            filename += '.txt'
            
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.content = f.read().splitlines()
            self.filename = filename
            self.modified = False
            self.undo_stack.clear()
            self.redo_stack.clear()
            print(f"\n✓ Opened: {filename} ({len(self.content)} lines)\n")
            return True
        except FileNotFoundError:
            print(f"✗ File not found: {filename}")
            return False
        except Exception as e:
            print(f"✗ Error opening file: {e}")
            return False
    
    def save_file(self, filename=None):
        if filename is None:
            if self.filename:
                filename = self.filename
            else:
                filename = input("Enter filename to save: ").strip()
                
        if not filename:
            print("✗ No filename provided.")
            return False
            
        if not filename.lower().endswith('.txt'):
            filename += '.txt'
            
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.content))
            self.filename = filename
            self.modified = False
            print(f"\n✓ Saved: {filename}\n")
            return True
        except Exception as e:
            print(f"✗ Error saving file: {e}")
            return False
    
    def save_as(self):
        filename = input("Enter new filename: ").strip()
        return self.save_file(filename)
    
    def find_text(self, search_term=None):
        if search_term is None:
            search_term = input("Enter text to find: ").strip()
            
        if not search_term:
            print("✗ No search term provided.")
            return []
            
        match_case = input("Match case? (y/N): ").strip().lower() == 'y'
            
        results = []
        for i, line in enumerate(self.content):
            if match_case:
                if search_term in line:
                    results.append((i + 1, line))
            else:
                if search_term.lower() in line.lower():
                    results.append((i + 1, line))
                
        if results:
            print(f"\n✓ Found {len(results)} occurrence(s):\n")
            for line_num, line_text in results:
                display_line = line_text[:100] + "..." if len(line_text) > 100 else line_text
                print(f"  Line {line_num}: {display_line}")
            print()
        else:
            print(f"\n✗ '{search_term}' not found.\n")
            
        return results
    
    def replace_text(self, search_term=None, replace_term=None):
        if search_term is None:
            search_term = input("Enter text to find: ").strip()
        if replace_term is None:
            replace_term = input("Enter replacement text: ").strip()
            
        if not search_term:
            print("✗ No search term provided.")
            return 0
            
        match_case = input("Match case? (y/N): ").strip().lower() == 'y'
        replace_all = input("Replace all occurrences? (Y/n): ").strip().lower() != 'n'
            
        self.save_state()
        count = 0
        
        flags = 0 if match_case else re.IGNORECASE
        pattern = re.compile(re.escape(search_term), flags)
        
        for i, line in enumerate(self.content):
            if pattern.search(line):
                if not replace_all:
                    new_line, num_subs = pattern.subn(lambda m: replace_term, line, count=1)
                    self.content[i] = new_line
                    count += num_subs
                    break
                else:
                    new_line, num_subs = pattern.subn(lambda m: replace_term, line)
                    self.content[i] = new_line
                    count += num_subs
                
        if count > 0:
            self.modified = True
            print(f"\n✓ Replaced {count} occurrence(s).\n")
        else:
            print(f"\n✗ '{search_term}' not found.\n")
            
        return count
    
    def toggle_word_wrap(self):
        self.word_wrap = not self.word_wrap
        status = "enabled" if self.word_wrap else "disabled"
        print(f"\n✓ Word wrap {status}.\n")
    
    def set_wrap_width(self):
        try:
            width = int(input(f"Enter wrap width (current: {self.wrap_width}): "))
            if width > 20:
                self.wrap_width = width
                print(f"\n✓ Wrap width set to {width}.\n")
            else:
                print("✗ Width must be greater than 20.")
        except ValueError:
            print("✗ Invalid number.")
    
    def wrap_line(self, line):
        if not self.word_wrap or len(line) <= self.wrap_width:
            return [line]
            
        wrapped = []
        while len(line) > self.wrap_width:
            break_point = line.rfind(' ', 0, self.wrap_width)
            if break_point == -1:
                break_point = self.wrap_width
            wrapped.append(line[:break_point])
            line = line[break_point:].lstrip()
        if line:
            wrapped.append(line)
        return wrapped
    
    def display_content(self):
        print("\n" + "=" * 60)
        if self.filename:
            status = " (modified)" if self.modified else ""
            print(f"File: {self.filename}{status}")
        else:
            print("File: [Untitled]" + (" (modified)" if self.modified else ""))
        print(f"Word Wrap: {'On' if self.word_wrap else 'Off'} | Width: {self.wrap_width}")
        print("=" * 60)
        
        if not self.content:
            print("  (empty file)")
        else:
            for i, line in enumerate(self.content):
                wrapped_lines = self.wrap_line(line)
                for j, wrapped in enumerate(wrapped_lines):
                    if j == 0:
                        print(f"{i + 1:4} | {wrapped}")
                    else:
                        print(f"     | {wrapped}")
        
        print("=" * 60 + "\n")
    
    def edit_line(self):
        if not self.content:
            print("✗ No content to edit. Add lines first.")
            return
            
        self.display_content()
        try:
            line_num = int(input("Enter line number to edit: "))
            if 1 <= line_num <= len(self.content):
                print(f"Current: {self.content[line_num - 1]}")
                new_text = input("New text: ")
                self.save_state()
                self.content[line_num - 1] = new_text
                self.modified = True
                print("✓ Line updated.")
            else:
                print(f"✗ Line number must be between 1 and {len(self.content)}.")
        except ValueError:
            print("✗ Invalid line number.")
    
    def add_line(self):
        self.save_state()
        print("Enter text (empty line to finish):")
        while True:
            line = input(f"{len(self.content) + 1:4} | ")
            if line == "":
                break
            self.content.append(line)
            self.modified = True
    
    def insert_line(self):
        if not self.content:
            return self.add_line()
            
        try:
            line_num = int(input(f"Insert before line (1-{len(self.content) + 1}): "))
            if 1 <= line_num <= len(self.content) + 1:
                text = input("Enter text: ")
                self.save_state()
                self.content.insert(line_num - 1, text)
                self.modified = True
                print("✓ Line inserted.")
            else:
                print(f"✗ Line number must be between 1 and {len(self.content) + 1}.")
        except ValueError:
            print("✗ Invalid line number.")
    
    def delete_line(self):
        if not self.content:
            print("✗ No content to delete.")
            return
            
        try:
            line_num = int(input(f"Delete line (1-{len(self.content)}): "))
            if 1 <= line_num <= len(self.content):
                self.save_state()
                deleted = self.content.pop(line_num - 1)
                self.modified = True
                print(f"✓ Deleted: {deleted[:50]}...")
            else:
                print(f"✗ Line number must be between 1 and {len(self.content)}.")
        except ValueError:
            print("✗ Invalid line number.")
    
    def show_help(self):
        help_text = """
╔══════════════════════════════════════════════════════════════╗
║                    TEXT EDITOR - HELP                        ║
╠══════════════════════════════════════════════════════════════╣
║  FILE OPERATIONS:                                            ║
║    n  - New file      (create a new empty document)          ║
║    o  - Open file     (open an existing .txt file)           ║
║    s  - Save file     (save current document)                ║
║    a  - Save As       (save with a new filename)             ║
║                                                              ║
║  EDITING:                                                    ║
║    v  - View content  (display document with line numbers)   ║
║    e  - Edit line     (modify a specific line)               ║
║    i  - Insert line   (add a line at specific position)      ║
║    d  - Delete line   (remove a specific line)               ║
║    +  - Add lines     (append new lines at the end)          ║
║                                                              ║
║  UNDO/REDO:                                                  ║
║    u  - Undo          (revert last change)                   ║
║    r  - Redo          (restore undone change)                ║
║                                                              ║
║  FIND & REPLACE:                                             ║
║    f  - Find          (search for text in document)          ║
║    p  - Replace       (find and replace text)                ║
║                                                              ║
║  WORD WRAP:                                                  ║
║    w  - Toggle wrap   (enable/disable word wrapping)         ║
║    W  - Set width     (change wrap column width)             ║
║                                                              ║
║  OTHER:                                                      ║
║    h  - Help          (show this help screen)                ║
║    q  - Quit          (exit the editor)                      ║
╚══════════════════════════════════════════════════════════════╝
"""
        print(help_text)
    
    def run(self):
        """Main editor loop."""
        print("\n" + "=" * 60)
        print("       WELCOME TO TEXT-BASED TEXT EDITOR")
        print("       Type 'h' for help, 'q' to quit")
        print("=" * 60 + "\n")
        
        while True:
            try:
                prompt = f"[{self.filename or 'Untitled'}{'*' if self.modified else ''}] > "
                command = input(prompt).strip().lower()
                
                if command == 'q':
                    if self.modified:
                        response = input("Unsaved changes. Quit anyway? (y/n): ").lower()
                        if response != 'y':
                            continue
                    print("\nGoodbye!\n")
                    break
                elif command == 'n':
                    self.new_file()
                elif command == 'o':
                    self.open_file()
                elif command == 's':
                    self.save_file()
                elif command == 'a':
                    self.save_as()
                elif command == 'v':
                    self.display_content()
                elif command == 'e':
                    self.edit_line()
                elif command == 'i':
                    self.insert_line()
                elif command == 'd':
                    self.delete_line()
                elif command == '+':
                    self.add_line()
                elif command == 'u':
                    if self.undo():
                        print("✓ Undo successful.")
                    else:
                        print("✗ Nothing to undo.")
                elif command == 'r':
                    if self.redo():
                        print("✓ Redo successful.")
                    else:
                        print("✗ Nothing to redo.")
                elif command == 'f':
                    self.find_text()
                elif command == 'p':
                    self.replace_text()
                elif command == 'w':
                    self.toggle_word_wrap()
                elif command == 'W' or command == 'ww':
                    self.set_wrap_width()
                elif command == 'h':
                    self.show_help()
                elif command == '':
                    continue
                else:
                    print(f"✗ Unknown command: '{command}'. Type 'h' for help.")
                    
            except KeyboardInterrupt:
                print("\n\nUse 'q' to quit.")
            except EOFError:
                print("\nGoodbye!\n")
                break


def main():
    editor = TextEditor()
    
    if len(sys.argv) > 1:
        editor.open_file(sys.argv[1])
    
    editor.run()


if __name__ == "__main__":
    main()
