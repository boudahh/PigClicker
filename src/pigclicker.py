import tkinter as tk

class PigClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("PigClicker v1.3.7b FIX")
        self.root.geometry("600x400")
        self.root.configure(bg="#1e1e1e")

        self.main_frame = tk.Frame(self.root, bg="#1e1e1e")
        self.main_frame.pack(fill="both", expand=True)

        self.left_panel = tk.Frame(self.main_frame, bg="#2a2a2a", width=200)
        self.left_panel.pack(side="left", fill="y")

        self.right_panel = tk.Frame(self.main_frame, bg="#333333")
        self.right_panel.pack(side="right", fill="both", expand=True)

        tk.Label(self.left_panel, text="Targets", bg="#2a2a2a", fg="white").pack(pady=10)
        tk.Label(self.right_panel, text="Controls", bg="#333333", fg="white").pack(pady=10)
        tk.Button(self.right_panel, text="Test Button", command=self.test_click).pack(pady=5)

    def test_click(self):
        print("Clicked!")

if __name__ == "__main__":
    root = tk.Tk()
    app = PigClicker(root)
    root.mainloop()
