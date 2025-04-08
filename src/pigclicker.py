
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

class PigClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("PigClicker v1.0")
        self.root.geometry("400x350")
        self.running = False
        self.test_mode = False
        self.targets = []
        self.delay = 1.0

        # Status label
        self.status_label = tk.Label(root, text="Status: Paused", font=("Arial", 14))
        self.status_label.pack(pady=10)

        # Add image button
        self.add_button = tk.Button(root, text="Add Target Image", command=self.load_image)
        self.add_button.pack(pady=5)

        # Test mode toggle
        self.test_var = tk.IntVar()
        self.test_checkbox = tk.Checkbutton(root, text="Test Mode (no clicks)", variable=self.test_var, command=self.toggle_test_mode)
        self.test_checkbox.pack(pady=5)

        # Delay slider
        self.delay_slider = tk.Scale(root, from_=0.1, to=5.0, resolution=0.1, label="Click Delay (sec)", orient=tk.HORIZONTAL, command=self.update_delay)
        self.delay_slider.set(1.0)
        self.delay_slider.pack(pady=10)

        # Loaded image list
        self.img_listbox = tk.Listbox(root, height=6)
        self.img_listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        self.load_default_image()

        keyboard.add_hotkey('F8', self.toggle_clicking)

        self.thread = threading.Thread(target=self.click_loop)
        self.thread.daemon = True
        self.thread.start()

    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if file_path:
            img = cv2.imread(file_path)
            self.targets.append(img)
            self.img_listbox.insert(tk.END, os.path.basename(file_path))

    def load_default_image(self):
        default_path = os.path.join(os.path.dirname(__file__), "confirm_default.png")
        if os.path.exists(default_path):
            img = cv2.imread(default_path)
            self.targets.append(img)
            self.img_listbox.insert(tk.END, "confirm_default.png")

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
                for template in self.targets:
                    result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
                    loc = np.where(result >= 0.9)
                    h, w = template.shape[:2]
                    for pt in zip(*loc[::-1]):
                        center = (pt[0] + w // 2, pt[1] + h // 2)
                        if self.test_mode:
                            pyautogui.moveTo(center)
                        else:
                            pyautogui.click(center)
                        time.sleep(self.delay)
            time.sleep(0.1)

if __name__ == "__main__":
    root = tk.Tk()
    app = PigClicker(root)
    root.mainloop()
