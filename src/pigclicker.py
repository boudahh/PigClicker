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
import json  # Import the json module
import traceback  # Import traceback module

DEBUG_LOG_FILE = "debug.log"  # Define a constant for the log file name


def log_debug(message):
    """Helper functions to write debug messages to the log file."""
    try:
        with open(DEBUG_LOG_FILE, "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    except Exception as e:
        print(f"Error writing to log file: {e}")  # Print to console if log file fails


class TargetImage:
    def __init__(self, path, offset=(0, 0), name="", condition_image_path=None, click_if_present=True):
        self.path = path
        self.template = cv2.imread(path)
        self.offset = offset
        self.name = name
        self.condition_image_path = condition_image_path  # Path to condition image
        self.click_if_present = click_if_present  # True if click if present, False if click if absent


class PigClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("PigClicker v1.4.5 – Target Management")
        self.root.geometry("800x500")
        self.running = False
        self.test_mode = False
        self.targets = []
        self.delay = 1.0
        self.image_cache = {}

        # Create left and right panels
        self.left_panel = tk.Frame(root, width=300, bg="#f2f2f2")
        self.left_panel.pack(side="left", fill="y")

        self.right_panel = tk.Frame(root, bg="#ffffff")
        self.right_panel.pack(side="right", expand=True, fill="both")

        # Controls in the left panel
        self.status_label = tk.Label(self.left_panel, text="Status: Paused", font=("Arial", 14))
        self.status_label.pack(pady=10)

        self.add_button = tk.Button(self.left_panel, text="Add Target Image", command=self.load_image)
        self.add_button.pack(pady=5)

        self.test_var = tk.IntVar()
        self.test_checkbox = tk.Checkbutton(self.left_panel, text="Test Mode (no clicks)", variable=self.test_var,
                                         command=self.toggle_test_mode)
        self.test_checkbox.pack(pady=5)

        self.delay_slider = tk.Scale(self.left_panel, from_=0.1, to=5.0, resolution=0.1,
                                    label="Click Delay (sec)", orient=tk.HORIZONTAL, command=self.update_delay)
        self.delay_slider.set(1.0)
        self.delay_slider.pack(pady=10)

        keyboard.add_hotkey('F8', self.toggle_clicking)

        # Target list in the right panel (using Frame and Canvas for scrolling)
        self.thumb_canvas = tk.Canvas(self.right_panel, bg="#ffffff", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.right_panel, orient="vertical", command=self.thumb_canvas.yview)
        self.thumb_frame = tk.Frame(self.thumb_canvas, bg="#ffffff")

        self.thumb_frame.bind("<Configure>",
                             lambda e: self.thumb_canvas.configure(scrollregion=self.thumb_canvas.bbox("all")))
        self.thumb_canvas.create_window((0, 0), window=self.thumb_frame, anchor="nw")
        self.thumb_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.thumb_canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        self.scrollbar.pack(side="right", fill="y", pady=10)

        # Buttons for target management in the left panel
        self.edit_button = tk.Button(self.left_panel, text="Edit Target", command=self.edit_selected_target,
                                    state=tk.DISABLED)
        self.edit_button.pack(pady=5)

        self.delete_button = tk.Button(self.left_panel, text="Delete Target",
                                      command=self.delete_selected_target, state=tk.DISABLED)
        self.delete_button.pack(pady=5)

        # Save and Load buttons (in the right panel)
        self.save_button = tk.Button(self.right_panel, text="Save Targets", command=self.save_targets)
        self.save_button.pack(pady=5)

        self.load_button = tk.Button(self.right_panel, text="Load Targets", command=self.load_targets)
        self.load_button.pack(pady=5)

        self.thread = threading.Thread(target=self.click_loop)
        self.thread.daemon = True
        self.thread.start()

        self.selected_index = None  # Initialize selected index
        self.target_labels = {}  # Dictionary to store text_labels

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

            # Determine initial window size
            window_width = min(original_width, max_width)
            window_height = min(original_height + 150, max(min(original_height, max_height), 150))  # Add space for settings

            picker.geometry(f"{window_width}x{window_height}")  # Set initial window size
            picker.minsize(window_width, window_height)  # Prevent making it smaller

            tk_img = ImageTk.PhotoImage(img)
            canvas = tk.Canvas(picker, width=original_width, height=original_height)  # Canvas size = original image
            canvas.pack(expand=tk.YES, fill=tk.BOTH)  # Make canvas expandable

            canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)

            self.click_offset = None  # Initialize click_offset
            self.target_name = None  # Initialize target_name
            self.condition_image_path = None
            self.click_if_present = tk.BooleanVar(value=True)

            # Condition settings UI (integrated into picker)
            condition_frame = tk.Frame(picker)
            condition_frame.pack()

            condition_label = tk.Label(condition_frame, text="Condition Image:")
            condition_label.pack(side=tk.LEFT)

            def select_condition_image():
                self.condition_image_path = filedialog.askopenfilename(
                    filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
                if self.condition_image_path:
                    condition_path_display.config(text=os.path.basename(self.condition_image_path))

            condition_button = tk.Button(condition_frame, text="Select Image", command=select_condition_image)
            condition_button.pack(side=tk.LEFT)

            condition_path_display = tk.Label(condition_frame, text="None")
            condition_path_display.pack(side=tk.LEFT)

            present_check = tk.Checkbutton(condition_frame, text="Click if Present",
                                         variable=self.click_if_present)
            present_check.pack(side=tk.LEFT)

            def on_click(event):
                log_debug("  on_click called")
                offset = (event.x, event.y)  # Use original image coordinates directly
                log_debug(f"  on_click: Click offset = {offset}")
                print(f"  on_click: Event = {event}")
                print(f"  on_click: canvasx = {canvas.canvasx(event.x)}, canvasy = {canvas.canvasy(event.y)}")
                self.target_name = tk.simpledialog.askstring("Target Name", "Enter a name for this target:")
                if not self.target_name:
                    self.target_name = os.path.basename(file_path)
                log_debug(f"  on_click: About to create TargetImage with offset = {offset}")
                target = TargetImage(file_path, tuple(offset), self.target_name, self.condition_image_path,
                                   self.click_if_present.get())
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
        """Helper function to display the click point on the canvas."""
        if self.click_oval:
            canvas.delete(self.click_oval)  # Remove previous oval
        self.click_oval = canvas.create_oval(offset[0] - 5, offset[1] - 5,
                                           offset[0] + 5, offset[1] + 5,
                                           fill="red", outline="red")

    def _add_target_to_listbox(self, target):
        try:
            log_debug(f"_add_target_to_listbox called with: {target.path}, offset = {target.offset}")

            item_frame = tk.Frame(self.thumb_frame, bg="#ffffff", pady=2)
            item_frame.pack(fill="x", anchor="w")
            item_frame.bind("<Button-1>", lambda event, index=len(self.targets) - 1: self._on_thumbnail_click(index))

            text_label = tk.Label(item_frame, text=target.name + f" @ {target.offset}", bg="#ffffff", anchor="w")
            text_label.pack(side="left", padx=5)
            text_label.bind("<Button-1>", lambda event, index=len(self.targets) - 1: self._on_thumbnail_click(index))

            self.target_labels[target.path] = text_label  # Store the label reference

        except Exception as e:
            messagebox.showerror("Error", f"Could not load thumbnail: {e}")
            log_debug(traceback.format_exc())

    def _on_thumbnail_click(self, index):
        log_debug(f"_on_thumbnail_click called with index: {index}")  # Debugging
        self.selected_index = index
        self._update_selection_highlight()
        self.edit_button.config(state=tk.NORMAL)
        self.delete_button.config(state=tk.NORMAL)

    def _update_selection_highlight(self):
        for i, child in enumerate(self.thumb_frame.winfo_children()):
            if i == self.selected_index:
                child.config(bg="#ADD8E6")  # Light blue highlight
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
            #self._show_click_point(canvas, target.offset)  # Removed: click_oval is not used here
            canvas.create_oval(target.offset[0] - 5, target.offset[1] - 5,
                               target.offset[0] + 5, target.offset[1] + 5,
                               fill="red", outline="red")  # Show current click point

            # Name editing
            name_label = tk.Label(editor, text="Target Name:")
            name_label.pack()
            name_entry = tk.Entry(editor)
            name_entry.insert(0, target.name)
            name_entry.pack()

            # Image path editing
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

            def on_edit_click(event=None):  # Make event optional
                log_debug("  on_edit_click called")
                new_offset = (event.x, event.y) if event else target.offset  # Get offset from event or keep old
                new_name = name_entry.get()
                new_path = path_display.cget("text")
                new_condition_image_path = condition_image_display.cget("text")
                new_click_if_present = present_check.instate(['selected'])

                # Update the TargetImage object FIRST
                self.targets[index_to_edit].offset = new_offset
                self.targets[index_to_edit].name = new_name
                self.targets[index_to_edit].path = new_path  # Update the path
                self.targets[index_to_edit].condition_image_path = new_condition_image_path
                self.targets[index_to_edit].click_if_present = new_click_if_present
                try:
                    self.targets[index_to_edit].template = cv2.imread(new_path)  # Update template
                except Exception as e:
                    messagebox.showerror("Error", f"Could not load new image: {e}")
                    log_debug(f"Error loading new image: {e}")
                    log_debug(traceback.format_exc())

                # Update the UI by rebuilding the list
                self._rebuild_thumbnail_list()
                editor.destroy()
                self._on_thumbnail_click(index_to_edit)

            done_button = tk.Button(editor, text="Done", command=on_edit_click)
            done_button.pack()

            canvas.bind("<Button-1>", on_edit_click)  # Re-enable canvas click for offset editing

            # Condition image editing
            condition_image_label = tk.Label(editor, text="Condition Image:")
            condition_image_label.pack()
            condition_image_display = tk.Label(editor, text=target.condition_image_path if target.condition_image_path else "None")
            condition_image_display.pack()

            def change_condition_image():
                new_condition_image_path = filedialog.askopenfilename(
                    filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
                if new_condition_image_path:
                    condition_image_display.config(text=os.path.basename(new_condition_image_path))

            change_condition_image_button = tk.Button(editor, text="Change Condition Image",
                                                     command=change_condition_image)
            change_condition_image_button.pack()

            # Click if present editing
            present_check = tk.Checkbutton(editor, text="Click if Present",
                                         variable=tk.BooleanVar(value=target.click_if_present))
            present_check.pack()

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
        self._update_selection_highlight()  # Keep selection if possible

    def toggle_test_mode(self):
        self.test_mode = bool(self.test_var.get())

    def update_delay(self, val):
        self.delay = float(val)

    def toggle_clicking(self):
        self.running = not self.running
        status = "Running" if self.running else "Paused"
        self.status_label.config(text=f"Status: {status}")

    def click_loop(self):
        while True:
            if self.running and self.targets:
                screenshot = pyautogui.screenshot()
                frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                for target in self.targets:
                    template = target.template
                    result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
                    loc = np.where(result >= 0.9)
                    h, w = template.shape[:2]
                    for pt in zip(*loc[::-1]):
                        click_x = pt[0] + target.offset[0]
                        click_y = pt[1] + target.offset[1]

                        # Conditional Clicking Logic
                        if target.condition_image_path:  # If a condition image is specified
                            condition_location = pyautogui.locateOnScreen(target.condition_image_path)
                            if target.click_if_present:  # Click if the condition image is present
                                if condition_location:
                                    if self.test_mode:
                                        pyautogui.moveTo(click_x, click_y)
                                    else:
                                        pyautogui.click(click_x, click_y)
                            else:  # Click if the condition image is absent
                                if not condition_location:
                                    if self.test_mode:
                                        pyautogui.moveTo(click_x, click_y)
                                    else:
                                        pyautogui.click(click_x, click_y)
                        else:  # No condition image, so click unconditionally
                            if self.test_mode:
                                pyautogui.moveTo(click_x, click_y)
                            else:
                                pyautogui.click(click_x, click_y)

                    time.sleep(self.delay)
            time.sleep(0.1)

    def save_targets(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
            try:
                data_to_save = []
                for target in self.targets:
                    data_to_save.append({
                        "path": target.path,
                        "offset": target.offset,
                        "name": target.name,  # Save the name
                        "condition_image_path": target.condition_image_path,  # Save the condition image path
                        "click_if_present": target.click_if_present  # Save the click if present flag
                    })
                with open(file_path, "w") as f:
                    json.dump(data_to_save, f)
                messagebox.showinfo("Success", "Targets saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save targets: {e}")
                log_debug(traceback.format_exc())  # Log the full traceback

    def load_targets(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            try:
                with open(file_path, "r") as f:
                    loaded_data = json.load(f)
                log_debug(f"load_targets: Loaded data = {loaded_data}")  # Log the entire loaded data
                self.targets = []
                for item in loaded_data:
                    log_debug(f"load_targets: Processing item = {item}")  # Log each item
                    offset = tuple(item.get("offset", (0, 0)))
                    path = item.get("path", "")
                    name = item.get("name", os.path.basename(path))
                    condition_image_path = item.get("condition_image_path")  # Load condition image path
                    click_if_present = item.get("click_if_present", True)  # Load click if present flag (default to True)
                    self.targets.append(TargetImage(path, offset, name, condition_image_path, click_if_present))
                self._rebuild_thumbnail_list()
                messagebox.showinfo("Success", "Targets loaded successfully!")
            except FileNotFoundError:
                messagebox.showerror("Error", f"File not found: {file_path}")
                log_debug(traceback.format_exc())  # Log the full traceback
            except json.JSONDecodeError:
                messagebox.showerror("Error", "Invalid JSON file format")
                log_debug(traceback.format_exc())  # Log the full traceback
            except Exception as e:
                messagebox.showerror("Error", f"Could not load targets: {e}")
                log_debug(traceback.format_exc())  # Log the full traceback

if __name__ == "__main__":
    root = tk.Tk()
    app = PigClicker(root)
    root.mainloop()