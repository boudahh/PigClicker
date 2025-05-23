
import sys
import threading
import time
import keyboard
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import pyautogui
import cv2
import numpy as np
import os
import json

SAVE_FILE = "targets.json"

class TargetImage:
    def __init__(self, path, offset=(0, 0)):
        self.path = path
        self.template = cv2.imread(path)
        self.offset = offset
        self.name = os.path.basename(path)

    def to_dict(self):
        return {'path': self.path, 'offset': self.offset}

class PigClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("PigClicker v1.6 – Panic + Persistence")
        self.root.geometry("480x430")
        self.running = False
        self.test_mode = False
        self.targets = []
        self.delay = 1.0
        self.panic = False

        self.status_label = tk.Label(root, text="Status: Paused", font=("Arial", 14))
        self.status_label.pack(pady=10)

        self.add_button = tk.Button(root, text="Add Target Image", command=self.load_image)
        self.add_button.pack(pady=5)

        self.test_var = tk.IntVar()
        self.test_checkbox = tk.Checkbutton(root, text="Test Mode (no clicks)", variable=self.test_var, command=self.toggle_test_mode)
        self.test_checkbox.pack(pady=5)

        self.delay_slider = tk.Scale(root, from_=0.1, to=5.0, resolution=0.1, label="Click Delay (sec)", orient=tk.HORIZONTAL, command=self.update_delay)
        self.delay_slider.set(1.0)
        self.delay_slider.pack(pady=10)

        self.target_frame = tk.Frame(root)
        self.target_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.canvas = tk.Canvas(self.target_frame, height=140)
        self.scrollbar = ttk.Scrollbar(self.target_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        keyboard.add_hotkey('F8', self.toggle_clicking)
        keyboard.add_hotkey('esc', self.panic_stop)

        self.load_targets()

        self.thread = threading.Thread(target=self.click_loop)
        self.thread.daemon = True
        self.thread.start()

    def save_targets(self):
        with open(SAVE_FILE, 'w') as f:
            json.dump([t.to_dict() for t in self.targets], f)

    def load_targets(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, 'r') as f:
                    data = json.load(f)
                    for item in data:
                        path, offset = item['path'], tuple(item['offset'])
                        if os.path.exists(path):
                            target = TargetImage(path, offset)
                            self.targets.append(target)
                            self.add_target_row(target)
            except Exception as e:
                print("Failed to load saved targets:", e)

    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if file_path:
            self.open_click_picker(file_path)

    def open_click_picker(self, file_path):
        picker = tk.Toplevel(self.root)
        picker.title("Click to set click point")
        img = Image.open(file_path)
        tk_img = ImageTk.PhotoImage(img)
        picker.image = tk_img
        canvas = tk.Canvas(picker, width=img.width, height=img.height)
        canvas.pack()
        canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)

        def on_click(event):
            offset = (event.x, event.y)
            target = TargetImage(file_path, offset)
            self.targets.append(target)
            self.add_target_row(target)
            self.save_targets()
            picker.destroy()

        canvas.bind("<Button-1>", on_click)
        picker.mainloop()

    def add_target_row(self, target):
        row = tk.Frame(self.scrollable_frame, bg="#f0f0f0")
        label = tk.Label(row, text=f"{target.name} @ {target.offset}", anchor="w", bg="#f0f0f0")
        label.pack(side="left", fill="x", expand=True)
        delete_btn = tk.Button(row, text="❌", fg="red", command=lambda: self.remove_target(row, target))
        delete_btn.pack(side="right", padx=5)

        def on_enter(e): row.configure(bg="#e0e0ff"); label.configure(bg="#e0e0ff")
        def on_leave(e): row.configure(bg="#f0f0f0"); label.configure(bg="#f0f0f0")

        row.bind("<Enter>", on_enter)
        row.bind("<Leave>", on_leave)
        label.bind("<Enter>", on_enter)
        label.bind("<Leave>", on_leave)

        row.pack(fill="x", pady=1)

    def remove_target(self, row, target):
        self.targets.remove(target)
        self.save_targets()
        row.destroy()

    def toggle_test_mode(self):
        self.test_mode = bool(self.test_var.get())

    def update_delay(self, val):
        self.delay = float(val)

    def panic_stop(self):
        self.panic = True
        self.running = False
        self.status_label.config(text="Status: PANIC MODE (ESC pressed)")

    def toggle_clicking(self):
        if self.panic:
            messagebox.showwarning("Panic Mode", "Reset app to resume after Panic.")
            return
        self.running = not self.running
        status = "Running" if self.running else "Paused"
        self.status_label.config(text=f"Status: {status}")

    def click_loop(self):
        while True:
            if self.running and self.targets and not self.panic:
                screenshot = pyautogui.screenshot()
                frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                for target in self.targets:
                    template = target.template
                    result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
                    loc = np.where(result >= 0.9)

                    rectangles = []
                    h, w = template.shape[:2]
                    for pt in zip(*loc[::-1]):
                        rectangles.append([pt[0], pt[1], w, h])
                        rectangles.append([pt[0], pt[1], w, h])

                    boxes, _ = cv2.groupRectangles(rectangles, groupThreshold=1, eps=0.5)

                    for (x, y, _, _) in boxes:
                        click_x = x + target.offset[0]
                        click_y = y + target.offset[1]
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
