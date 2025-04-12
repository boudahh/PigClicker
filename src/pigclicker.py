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

class TargetImage:
    def __init__(self, path, offset=(0, 0)):
        self.path = path
        self.template = cv2.imread(path)
        self.offset = offset

class PigClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("PigClicker v1.4.5 – Thumbnail Panel")
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

        # Status and controls
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

        # Thumbnail list setup
        self.thumb_canvas = tk.Canvas(self.left_panel, bg="#f2f2f2", height=250, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.left_panel, orient="vertical", command=self.thumb_canvas.yview)
        self.thumb_frame = tk.Frame(self.thumb_canvas, bg="#f2f2f2")

        self.thumb_frame.bind("<Configure>", lambda e: self.thumb_canvas.configure(scrollregion=self.thumb_canvas.bbox("all")))
        self.thumb_canvas.create_window((0, 0), window=self.thumb_frame, anchor="nw")
        self.thumb_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.thumb_canvas.pack(side="left", fill="both", expand=True, padx=(10,0))
        self.scrollbar.pack(side="right", fill="y")

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
            img = Image.open(target.path)
            thumbnail_size = (50, 50)
            img.thumbnail(thumbnail_size)
            tk_img = ImageTk.PhotoImage(img)
            self.image_cache[target.path] = tk_img

            item_frame = tk.Frame(self.thumb_frame, bg="#f2f2f2", pady=2)
            item_frame.pack(fill="x", anchor="w")

            img_label = tk.Label(item_frame, image=tk_img, bg="#f2f2f2")
            img_label.image = tk_img
            img_label.pack(side="left", padx=5)

            text_label = tk.Label(item_frame, text=os.path.basename(target.path) + f" @ {target.offset}", bg="#f2f2f2", anchor="w")
            text_label.pack(side="left", padx=5)
        except Exception as e:
            messagebox.showerror("Error", f"Could not load thumbnail: {e}")

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

if __name__ == "__main__":
    root = tk.Tk()
    app = PigClicker(root)
    root.mainloop()
