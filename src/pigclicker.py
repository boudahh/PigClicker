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
        picker = tk.Toplevel(self.root)
        picker.title("Click to set click point")
        img = Image.open(file_path)
        img = img.resize((img.width, img.height))
        tk_img = ImageTk.PhotoImage(img)
        canvas = tk.Canvas(picker, width=img.width, height=img.height)
        canvas.pack(in_=self.left_panel, )
        canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)

        def on_click(event):
            offset = (event.x, event.y)
            self.targets.append(TargetImage(file_path, offset))
            self.img_listbox.insert(tk.END, os.path.basename(file_path) + f" @ {offset}")
            picker.destroy()

        canvas.bind("<Button-1>", on_click)
        picker.mainloop()

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
                        "offset": target.offset
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

        keyboard.add_hotkey('F8', self.toggle_clicking)

        # Thumbnail list in the right panel
        self.thumb_canvas = tk.Canvas(self.right_panel, bg="#ffffff", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.right_panel, orient="vertical", command=self.thumb_canvas.yview)
        self.thumb_frame = tk.Frame(self.thumb_canvas, bg="#ffffff")

        self.thumb_frame.bind("<Configure>",
                             lambda e: self.thumb_canvas.configure(scrollregion=self.thumb_canvas.bbox("all")))
        self.thumb_canvas.create_window((0, 0), window=self.thumb_frame, anchor="nw")
        self.thumb_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.thumb_canvas.pack(side="left", fill=tk.BOTH, expand=True, padx=20, pady=5)

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
            max_width = 500
            max_height = 500
            if img.width > max_width or img.height > max_height:
                img.thumbnail((max_width, max_height))
            tk_img = ImageTk.PhotoImage(img)
            canvas = tk.Canvas(picker, width=img.width, height=img.height)
            canvas.pack()
            canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)

            def on_click(event):
                offset = (event.x, event.y)
                self.targets.append(TargetImage(file_path, offset))
                self.img_listbox.insert(tk.END, os.path.basename(file_path) + f" @ {offset}")
                picker.destroy()

            canvas.bind("<Button-1>", on_click)
            picker.mainloop()
        except FileNotFoundError:
            messagebox.showerror("Error", f"File not found: {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open image: {e}")

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
                        "offset": target.offset
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
import json  # Import the json module
import traceback  # Import traceback module

DEBUG_LOG_FILE = "debug.log"  # Define a constant for the log file name

def log_debug(message):
    """Helper function to write debug messages to the log file."""
    try:
        with open(DEBUG_LOG_FILE, "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    except Exception as e:
        print(f"Error writing to log file: {e}")  # Print to console if log file fails

class TargetImage:
    def __init__(self, path, offset=(0, 0), name=""):  # Added name attribute
        self.path = path
        self.template = cv2.imread(path)
        self.offset = offset
        self.name = name  # Store the custom name

class PigClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("PigClicker v1.4.5 – Target Management")
        self.root.geometry("800x500")
        self.running = False
        self.test_mode = False
        self.targets = []
        self.delay = 1.0
        self.image_cache = {}  # We might not need this anymore

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
        self.test_checkbox = tk.Checkbutton(self.left_panel, text="Test Mode (no clicks)", variable=self.test_var, command=self.toggle_test_mode)
        self.test_checkbox.pack(pady=5)

        self.delay_slider = tk.Scale(self.left_panel, from_=0.1, to=5.0, resolution=0.1, label="Click Delay (sec)", orient=tk.HORIZONTAL, command=self.update_delay)
        self.delay_slider.set(1.0)
        self.delay_slider.pack(pady=10)

        keyboard.add_hotkey('F8', self.toggle_clicking)

        # Thumbnail list in the right panel
        self.thumb_canvas = tk.Canvas(self.right_panel, bg="#ffffff", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.right_panel, orient="vertical", command=self.thumb_canvas.yview)
        self.thumb_frame = tk.Frame(self.thumb_canvas, bg="#ffffff")

        self.thumb_frame.bind("<Configure>", lambda e: self.thumb_canvas.configure(scrollregion=self.thumb_canvas.bbox("all")))
        self.thumb_canvas.create_window((0, 0), window=self.thumb_frame, anchor="nw")
        self.thumb_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.thumb_canvas.pack(side="left", fill=tk.BOTH, expand=True, padx=20, pady=5)

        keyboard.add_hotkey('F8', self.toggle_clicking)

        self.thread = threading.Thread(target=self.click_loop)
        self.thread.daemon = True
        self.thread.start()

    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if file_path:
            self.open_click_picker(file_path)

    def open_click_picker(self, file_path):
        picker = tk.Toplevel(self.root)
        picker.title("Click to set click point")
        img = Image.open(file_path)
        img = img.resize((img.width, img.height))
        tk_img = ImageTk.PhotoImage(img)
        canvas = tk.Canvas(picker, width=img.width, height=img.height)
        canvas.pack(in_=self.left_panel,)
        canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)

        def on_click(event):
            offset = (event.x, event.y)
            self.targets.append(TargetImage(file_path, offset))
            self.img_listbox.insert(tk.END, os.path.basename(file_path) + f" @ {offset}")
            picker.destroy()

        canvas.bind("<Button-1>", on_click)
        picker.mainloop()

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
                        "offset": target.offset
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
                messagebox.showerror