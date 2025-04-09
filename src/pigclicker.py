# PigClicker v1.3.1 – Now with hover effects, panic key, auto-save, and sound-ready UI
# NOTE: GUI framework like Tkinter doesn't support CSS-like hover natively,
# but these behaviors are implemented using event bindings and animation logic.

import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import pyautogui
import cv2
import numpy as np
import os
import json
import keyboard
import threading
import time
import winsound

class TargetImage:
    def __init__(self, path, offset):
        self.path = path
        self.template = cv2.imread(path)
        self.offset = offset

class PigClickerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PigClicker v1.3.1")
        self.root.configure(bg="#1e1e1e")
        self.running = False
        self.test_mode = False
        self.targets = []
        self.delay = 1.0
        self.panic_triggered = False

        self.setup_ui()
        self.load_targets()
        self.bind_hotkeys()

        self.thread = threading.Thread(target=self.click_loop)
        self.thread.daemon = True
        self.thread.start()

    def setup_ui(self):
        icon_frame = tk.Frame(self.root, bg="#1e1e1e")
        icon_frame.pack(pady=10)
        self.icon_label = tk.Label(icon_frame, text="🐽", font=("Arial", 18), bg="#1e1e1e", fg="#ff69b4")
        self.icon_label.pack(side=tk.LEFT)
        self.icon_label.bind("<Enter>", lambda e: self.icon_label.config(font=("Arial", 20)))
        self.icon_label.bind("<Leave>", lambda e: self.icon_label.config(font=("Arial", 18)))

        self.title_label = tk.Label(icon_frame, text="PigClicker", font=("Arial", 18, "bold"), bg="#1e1e1e", fg="#ff69b4")
        self.title_label.pack(side=tk.LEFT, padx=(5, 0))

        self.status_label = tk.Label(self.root, text="Status: Paused", font=("Arial", 12), bg="#1e1e1e", fg="white")
        self.status_label.pack(pady=5)

        self.add_button = tk.Button(self.root, text="Add Target Image", command=self.load_image, bg="#ff69b4", fg="white")
        self.add_button.pack(pady=5)
        self.add_button.bind("<Enter>", lambda e: self.add_button.config(bg="#ff85c1"))
        self.add_button.bind("<Leave>", lambda e: self.add_button.config(bg="#ff69b4"))

        self.test_var = tk.IntVar()
        self.test_checkbox = tk.Checkbutton(self.root, text="Test Mode", variable=self.test_var, command=self.toggle_test_mode, bg="#1e1e1e", fg="white", selectcolor="#ff69b4")
        self.test_checkbox.pack(pady=5)

        self.delay_slider = tk.Scale(self.root, from_=0.1, to=5.0, resolution=0.1, label="Click Delay (sec)", orient=tk.HORIZONTAL, bg="#1e1e1e", fg="white", troughcolor="#ff69b4", command=self.update_delay)
        self.delay_slider.set(1.0)
        self.delay_slider.pack(pady=5)

        self.target_frame = tk.Frame(self.root, bg="#1e1e1e")
        self.target_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.target_labels = []

    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg")])
        if file_path:
            self.pick_click_point(file_path)

    def pick_click_point(self, file_path):
        picker = tk.Toplevel(self.root)
        picker.title("Click to set click point")
        img = Image.open(file_path)
        tk_img = ImageTk.PhotoImage(img)
        canvas = tk.Canvas(picker, width=img.width, height=img.height)
        canvas.pack()
        canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)
        canvas.image = tk_img

        def on_click(event):
            offset = (event.x, event.y)
            self.targets.append(TargetImage(file_path, offset))
            self.display_target(file_path, offset)
            self.save_targets()
            picker.destroy()

        canvas.bind("<Button-1>", on_click)

    def display_target(self, path, offset):
        img_name = os.path.basename(path)
        text = f"{img_name} @ {offset}"
        frame = tk.Frame(self.target_frame, bg="#2e2e2e")
        frame.pack(fill=tk.X, pady=2)
        label = tk.Label(frame, text=text, bg="#2e2e2e", fg="white", padx=10, pady=5)
        label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        del_btn = tk.Label(frame, text="🗑", fg="red", bg="#2e2e2e", cursor="hand2")
        del_btn.pack(side=tk.RIGHT, padx=5)
        del_btn.bind("<Enter>", lambda e: del_btn.config(fg="#ff4444"))
        del_btn.bind("<Leave>", lambda e: del_btn.config(fg="red"))
        del_btn.bind("<Button-1>", lambda e, f=frame, p=path: self.delete_target(f, p))

    def delete_target(self, frame, path):
        frame.destroy()
        self.targets = [t for t in self.targets if t.path != path]
        self.save_targets()

    def toggle_test_mode(self):
        self.test_mode = bool(self.test_var.get())

    def update_delay(self, val):
        self.delay = float(val)

    def toggle_clicking(self):
        if self.panic_triggered:
            self.status_label.config(text="PANIC MODE – CLICKING DISABLED")
            return
        self.running = not self.running
        self.status_label.config(text="Status: Running" if self.running else "Status: Paused")

    def trigger_panic(self):
        self.running = False
        self.panic_triggered = True
        self.status_label.config(text="PANIC MODE – CLICKING DISABLED")
        winsound.MessageBeep(winsound.MB_ICONHAND)

    def click_loop(self):
        while True:
            if self.running and self.targets:
                screenshot = pyautogui.screenshot()
                frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                for target in self.targets:
                    result = cv2.matchTemplate(frame, target.template, cv2.TM_CCOEFF_NORMED)
                    loc = np.where(result >= 0.9)
                    for pt in zip(*loc[::-1]):
                        cx = pt[0] + target.offset[0]
                        cy = pt[1] + target.offset[1]
                        if self.test_mode:
                            pyautogui.moveTo(cx, cy)
                        else:
                            pyautogui.click(cx, cy)
                        time.sleep(self.delay)
            time.sleep(0.1)

    def save_targets(self):
        data = [{"path": t.path, "offset": t.offset} for t in self.targets]
        with open("targets.json", "w") as f:
            json.dump(data, f)

    def load_targets(self):
        if os.path.exists("targets.json"):
            with open("targets.json", "r") as f:
                try:
                    data = json.load(f)
                    for entry in data:
                        self.targets.append(TargetImage(entry["path"], tuple(entry["offset"])))
                        self.display_target(entry["path"], tuple(entry["offset"]))
                except:
                    pass

    def bind_hotkeys(self):
        keyboard.add_hotkey("f8", self.toggle_clicking)
        keyboard.add_hotkey("esc", self.trigger_panic)

if __name__ == "__main__":
    root = tk.Tk()
    app = PigClickerApp(root)
    root.mainloop()
