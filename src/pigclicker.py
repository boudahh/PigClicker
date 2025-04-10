
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
        self.root.title("PigClicker v1.2 – Live Picker")
        self.root.geometry("420x380")
        self.running = False
        self.test_mode = False
        self.targets = []
        self.delay = 1.0

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

        self.img_listbox = tk.Listbox(root, height=6)
        self.img_listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

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
        canvas.pack()
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

if __name__ == "__main__":
    root = tk.Tk()
    app = PigClicker(root)
    root.mainloop()
