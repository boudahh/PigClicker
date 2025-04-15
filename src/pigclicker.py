import sys
import threading
import time
import keyboard
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import pyautogui
import cv2
import numpy as np
import os
import json
import traceback

DEBUG_LOG_FILE = "debug.log"

def log_debug(message):
    try:
        with open(DEBUG_LOG_FILE, "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    except Exception as e:
        print(f"Error writing to log file: {e}")

class TargetImage:
    def click_oval(self, x, y):
        if hasattr(self, 'canvas'):
            self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill="red")

    def __init__(self, path, offset=(0, 0), name=""):
        self.path = path
        self.template = cv2.imread(path)
        self.offset = offset
        self.name = name
        self.thumbnail = self._create_thumbnail(path)  # Create thumbnail

    def _create_thumbnail(self, path, size=(50, 50)):  # Adjust size as needed
        try:
            img = Image.open(path)
            img.thumbnail(size)  # Resize in-place
            return ImageTk.PhotoImage(img)
        except Exception as e:
            log_debug(f"Error creating thumbnail for {path}: {e}")
            return None  # Or return a placeholder image

class PigClicker:
    def click_oval(self, x, y):
        if hasattr(self, 'canvas'):
            self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill="red")

    def __init__(self, root):
        self.root = root
        self.root.title("PigClicker v1.4.5 – Target Management")
        self.root.geometry("800x500")
        self.running = False
        self.test_mode = False
        self.targets = []
        self.delay = 1.0
        self.image_cache = {}

        self.left_panel = tk.Frame(root, width=300, bg="#f2f2f2")
        self.left_panel.pack(side="left", fill="y")

        self.right_panel = tk.Frame(root, bg="#ffffff")
        self.right_panel.pack(side="right", expand=True, fill="both")

        self.status_label = tk.Label(self.left_panel, text="Status: Paused", font=("Arial", 14))
        self.status_label.pack(pady=10)

        self.add_button = tk.Button(self.left_panel, text="Add Target Image", command=self.load_image)
        self.add_button.pack(pady=5)

        self.test_var = tk.IntVar()
        self.test_checkbox = tk.Checkbutton(self.left_panel, text="Test Mode (no clicks)", variable=self.test_var, command=self.toggle_test_mode)
        self.test_checkbox.pack(pady=5)

        self.delay_slider = tk.Scale(self.left_panel, from_=0.1, to=5.0, resolution=0.1, label="Click Delay (sec)", orient=tk.HORIZONTAL, command=self.update_delay)
        self.delay_slider.set(1.0)
        self.delay_slider.pack(pady=10)

        keyboard.add_hotkey('F8', self.toggle_clicking)

        self.thumb_canvas = tk.Canvas(self.right_panel, bg="#ffffff", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.right_panel, orient="vertical", command=self.thumb_canvas.yview)
        self.thumb_frame = tk.Frame(self.thumb_canvas, bg="#ffffff")

        self.thumb_frame.bind("<Configure>", lambda e: self.thumb_canvas.configure(scrollregion=self.thumb_canvas.bbox("all")))
        self.thumb_canvas.create_window((0, 0), window=self.thumb_frame, anchor="nw")
        self.thumb_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.thumb_canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        self.scrollbar.pack(side="right", fill="y", pady=10)

        self.edit_button = tk.Button(self.left_panel, text="Edit Target", command=self.edit_selected_target, state=tk.DISABLED)
        self.edit_button.pack(pady=5)

        self.delete_button = tk.Button(self.left_panel, text="Delete Target", command=self.delete_selected_target, state=tk.DISABLED)
        self.delete_button.pack(pady=5)

        self.save_button = tk.Button(self.right_panel, text="Save Targets", command=self.save_targets)
        self.save_button.pack(pady=5)

        self.load_button = tk.Button(self.right_panel, text="Load Targets", command=self.load_targets)
        self.load_button.pack(pady=5)

        self.thread = threading.Thread(target=self.click_loop)
        self.thread.daemon = True
        self.thread.start()

        self.selected_index = None
        self.target_labels = {}

    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if file_path:
            self.open_click_picker(file_path)

    def open_click_picker(self, file_path):
        log_debug("open_click_picker called")
        picker = tk.Toplevel(self.root)
        picker.title("Click to set click point")

        try:
            img = Image.open(file_path)
            original_width = img.width
            original_height = img.height
            max_width = 800
            max_height = 800

            window_width = min(original_width, max_width)
            window_height = min(original_height, max_height)

            picker.geometry(f"{window_width}x{window_height}")
            picker.minsize(window_width, window_height)

            tk_img = ImageTk.PhotoImage(img)
            canvas = tk.Canvas(picker, width=original_width, height=original_height)
            canvas.pack(expand=tk.YES, fill=tk.BOTH)

            canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)

            if original_width > window_width:
                h_scrollbar = tk.Scrollbar(picker, orient="horizontal", command=canvas.xview)
                h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
                canvas.configure(xscrollcommand=h_scrollbar.set)
            if original_height > window_height:
                v_scrollbar = tk.Scrollbar(picker, orient="vertical", command=canvas.yview)
                v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                canvas.configure(yscrollcommand=v_scrollbar.set)

            def on_click(event):
                log_debug("  on_click called")
                offset = (event.x, event.y)
                log_debug(f"  on_click: Click offset = {offset}")
                print(f"  on_click: Event = {event}")
                print(f"  on_click: canvasx = {canvas.canvasx(event.x)}, canvasy = {canvas.canvasy(event.y)}")
                target_name = tk.simpledialog.askstring("Target Name", "Enter a name for this target:")
                if not target_name:
                    target_name = os.path.basename(file_path)
                log_debug(f"  on_click: About to create TargetImage with offset = {offset}")
                target = TargetImage(file_path, tuple(offset), target_name)
                log_debug(f"  on_click: TargetImage created with offset = {target.offset}")
                self.targets.append(target)
                self._add_target_to_listbox(target)
                picker.destroy()
                self._show_click_point(canvas, offset)

            canvas.bind("<Button-1>", on_click)
            picker.mainloop()

        except FileNotFoundError:
            messagebox.showerror("Error", f"File not found: {file_path}")
            log_debug(traceback.format_exc())
        except Exception as e:
            messagebox.showerror("Error", f"Could not open image: {e}")
            log_debug(traceback.format_exc())

    def _show_click_point(self, canvas, offset):
        if self.click_oval:
            canvas.delete(self.click_oval)
        self.click_oval = canvas.create_oval(offset[0] - 5, offset[1] - 5,
                                           offset[0] + 5, offset[1] + 5,
                                           fill="red", outline="red")

    def _add_target_to_listbox(self, target):
        try:
            log_debug(f"_add_target_to_listbox called with: {target.path}, offset = {target.offset}")

            item_frame = tk.Frame(self.thumb_frame, bg="#ffffff", pady=2)
            item_frame.pack(fill="x", anchor="w")
            item_frame.bind("<Button-1>", lambda event, index=len(self.targets) - 1: self._on_thumbnail_click(index))

            if target.thumbnail:  # Check if thumbnail exists
                img_label = tk.Label(item_frame, image=target.thumbnail, bg="#ffffff")
                img_label.image = target.thumbnail  # Keep a reference!
                img_label.pack(side="left", padx=5)
                img_label.bind("<Button-1>", lambda event, index=len(self.targets) - 1: self._on_thumbnail_click(index))

            text_label = tk.Label(item_frame, text=target.name + f" @ {target.offset}", bg="#ffffff", anchor="w")
            text_label.pack(side="left", padx=5)
            text_label.bind("<Button-1>", lambda event, index=len(self.targets) - 1: self._on_thumbnail_click(index))

            self.target_labels[target.path] = text_label

        except Exception as e:
            messagebox.showerror("Error", f"Could not load thumbnail: {e}")
            log_debug(traceback.format_exc())

    def _on_thumbnail_click(self, index):
        log_debug(f"_on_thumbnail_click called with index: {index}")
        self.selected_index = index
        self._update_selection_highlight()
        self.edit_button.config(state=tk.NORMAL)
        self.delete_button.config(state=tk.NORMAL)

    def _update_selection_highlight(self):
        for i, child in enumerate(self.thumb_frame.winfo_children()):
            if i == self.selected_index:
                child.config(bg="#ADD8E6")
                for grandchild in child.winfo_children():
                    grandchild.config(bg="#ADD8E6")
            else:
                child.config(bg="#ffffff")
                for grandchild in child.winfo_children():
                    grandchild.config(bg="#ffffff")

    def edit_selected_target(self):
        if self.selected_index is not None:
            target_to_edit = self.targets[self.selected_index]
            self._open_edit_picker(target_to_edit, self.selected_index)

    def _open_edit_picker(self, target: TargetImage, index_to_edit):
        log_debug(f"_open_edit_picker called with target: {target.path}, index: {index_to_edit}")
        editor = tk.Toplevel(self.root)
        editor.title("Edit Target")

        try:
            img = Image.open(target.path)
            tk_img = ImageTk.PhotoImage(img)
            canvas = tk.Canvas(editor, width=img.width, height=img.height)
            canvas.pack()
            canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)
            self._show_click_point(canvas, target.offset)

            name_label = tk.Label(editor, text="Target Name:")
            name_label.pack()
            name_entry = tk.Entry(editor)
            name_entry.insert(0, target.name)
            name_entry.pack()

            path_label = tk.Label(editor, text="Image Path:")
            path_label.pack()
            path_display = tk.Label(editor, text=target.path)
            path_display.pack()

            def change_image():
                new_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
                if new_path:
                    path_display.config(text=new_path)

            change_image_button = tk.Button(editor, text="Change Image", command=change_image)
            change_image_button.pack()

            def on_edit_click(event=None):
                log_debug("  on_edit_click called")
                new_offset = (event.x, event.y) if event else target.offset
                new_name = name_entry.get()
                new_path = path_display.cget("text")

                self.targets[index_to_edit].offset = new_offset
                self.targets[index_to_edit].name = new_name
                self.targets[index_to_edit].path = new_path
                try:
                    self.targets[index_to_edit].template = cv2.imread(new_path)
                except Exception as e:
                    messagebox.showerror("Error", f"Could not load new image: {e}")
                    log_debug(f"Error loading new image: {e}")
                    log_debug(traceback.format_exc())

                # Update the label and thumbnail
                self.target_labels[target.path].config(text=new_name + f" @ {new_offset}")
                self.targets[index_to_edit].thumbnail = self.targets[index_to_edit]._create_thumbnail(new_path)
                self._rebuild_thumbnail_list() # Rebuild the list to update thumbnails
                editor.destroy()
                self._on_thumbnail_click(index_to_edit)

            done_button = tk.Button(editor, text="Done", command=on_edit_click)
            done_button.pack()

            canvas.bind("<Button-1>", on_edit_click)

            editor.mainloop()

        except FileNotFoundError:
            messagebox.showerror("Error", f"File not found: {target.path}")
            log_debug(f"  FileNotFoundError: {target.path}")
            log_debug(traceback.format_exc())
        except Exception as e:
            messagebox.showerror("Error", f"Could not open image: {e}")
            log_debug(f"  Exception in _open_edit_picker: {e}")
            log_debug(traceback.format_exc())

    def delete_selected_target(self):
        if self.selected_index is not None:
            if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this target?"):
                del self.targets[self.selected_index]
                self._rebuild_thumbnail_list()
                self.selected_index = None
                self.edit_button.config(state=tk.DISABLED)
                self.delete_button.config(state=tk.DISABLED)

    def _rebuild_thumbnail_list(self):
        for child in self.thumb_frame.winfo_children():
            child.destroy()
        for target in self.targets:
            self._add_target_to_listbox(target)
        self._update_selection_highlight()

    def toggle_test_mode(self):
        self.test_mode = bool(self.test_var.get())

    def update_delay(self, val):
        self.delay = float(val)

    def toggle_clicking(self):
        self.running = not self.running
        status = "Running" if self.running else "Paused"
        self.status_label.config