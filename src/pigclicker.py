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
    """Helper function to write debug messages to the log file."""
    try:
        with open(DEBUG_LOG_FILE, "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    except Exception as e:
        print(f"Error writing to log file: {e}")  # Print to console if log file fails


class TargetImage:
    def __init__(self, path, offset=(0, 0), name=""):  # Added name attribute
        self.path = path
        self.template = cv2.imread(path)
        self.offset = offset
        self.name = name  # Store the custom name


class PigClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("PigClicker v1.4.5 – Target Management")
        self.root.geometry("800x500")
        self.running = False
        self.test_mode = False
        self.targets = []
        self.delay = 1.0
        self.image_cache = {}  # We might not need this anymore

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

        self.img_listbox = tk.Listbox(self.left_panel, height=6)
        self.img_listbox.pack(in_=self.left_panel, fill=tk.BOTH, expand=True, padx=20, pady=5)

        keyboard.add_hotkey('F8', self.toggle_clicking)

        self.thread = threading.Thread(target=self.click_loop)
        self.thread.daemon = True
        self.thread.start()

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
            max_width = 500
            max_height = 500
            if img.width > max_width or img.height > max_height:
                img.thumbnail((max_width, max_height))
            tk_img = ImageTk.PhotoImage(img)
            canvas = tk.Canvas(picker, width=img.width, height=img.height)
            canvas.pack(in_=self.left_panel,)
            canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)

            def on_click(event):
                offset = (event.x, event.y)
                target = TargetImage(file_path, offset)
                self.targets.append(target)
                self._add_target_to_listbox(target)
                picker.destroy()

            canvas.bind("<Button-1>", on_click)
            picker.mainloop()
        except FileNotFoundError:
            messagebox.showerror("Error", f"File not found: {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open image: {e}")

    def _add_target_to_listbox(self, target):
        try:
            log_debug(f"_add_target_to_listbox called with: {target.path}")

            img = Image.open(target.path)
            thumbnail_size = (50, 50)
            img.thumbnail(thumbnail_size)
            tk_img = ImageTk.PhotoImage(img)
            self.image_cache[target.path] = tk_img

            item_frame = tk.Frame(self.thumb_frame, bg="#ffffff", pady=2)
            item_frame.pack(fill="x", anchor="w")
            item_frame.bind("<Button-1>", lambda event, index=len(self.targets) - 1: self._on_thumbnail_click(index))

            img_label = tk.Label(item_frame, image=tk_img, bg="#ffffff")
            img_label.image = tk_img
            img_label.pack(side="left", padx=5)
            img_label.bind("<Button-1>", lambda event, index=len(self.targets) - 1: self._on_thumbnail_click(index))

            text_label = tk.Label(item_frame, text=os.path.basename(target.path) + f" @ {target.offset}",
                                bg="#ffffff", anchor="w")
            text_label.pack(side="left", padx=5)
            text_label.bind("<Button-1>", lambda event, index=len(self.targets) - 1: self._on_thumbnail_click(index))

        except Exception as e:
            messagebox.showerror("Error", f"Could not load thumbnail: {e}")

    def _on_thumbnail_click(self, index):
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
                # new_condition_image_path = condition_image_display.cget("text") # Commented out
                # new_click_if_present = present_check.instate(['selected']) # Commented out

                self.targets[index_to_edit].offset = new_offset
                self.targets[index_to_edit].name = new_name
                self.targets[index_to_edit].path = new_path  # Update the path
                # self.targets[index_to_edit].condition_image_path = new_condition_image_path # Commented out
                # self.targets[index_to_edit].click_if_present = new_click_if_present # Commented out
                try:
                    self.targets[index_to_edit].template = cv2.imread(new_path)  # Update template
                except Exception as e:
                    messagebox.showerror("Error", f"Could not load new image: {e}")
                    log_debug(f"Error loading new image: {e}")
                    log_debug(traceback.format_exc())

                # Update the label directly
                self.target_labels[target.path].config(text=new_name + f" @ {new_offset}")
                editor.destroy()
                self._on_thumbnail_click(index_to_edit)

            done_button = tk.Button(editor, text="Done", command=on_edit_click)
            done_button.pack()

            canvas.bind("<Button-1>", on_edit_click)  # Re-enable canvas click for offset editing

            # Condition image editing # Commented out
            # condition_image_label = tk.Label(editor, text="Condition Image:")
            # condition_image_label.pack()
            # condition_image_display = tk.Label(editor, text=target.condition_image_path if target.condition_image_path else "None")
            # condition_image_display.pack()

            # def change_condition_image():
            #     new_condition_image_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
            #     if new_condition_image_path:
            #         condition_image_display.config(text=os.path.basename(new_condition_image_path))

            # change_condition_image_button = tk.Button(editor, text="Change Condition Image",
            #                                         command=change_condition_image)
            # change_condition_image_button.pack()

            # Click if present editing # Commented out
            # present_check = tk.Checkbutton(editor, text="Click if Present",
            #                              variable=tk.BooleanVar(value=target.click_if_present))
            # present_check.pack()

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
                        "name": target.name  # Save the name
                    })
                with open(file_path, "w") as f:
                    json.dump(data_to_save, f)
                messagebox.showinfo("Success", "Targets saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save targets: {e}")

    def load_targets(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            try:
                with open(file_path, "r") as f:
                    loaded_data = json.load(f)
                self.targets = []
                for item in loaded_data:
                    self.targets.append(TargetImage(item["path"], tuple(item["offset"])))
                self._rebuild_thumbnail_list()
                messagebox.showinfo("Success", "Targets loaded successfully!")
            except FileNotFoundError:
                messagebox.showerror("Error", f"File not found: {file_path}")
            except json.JSONDecodeError:
                messagebox.showerror("Error", "Invalid JSON file format")
            except Exception as e:
                messagebox.showerror("Error", f"Could not load targets: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PigClicker(root)
    root.mainloop()