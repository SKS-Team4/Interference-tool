"""
Signal Interference Injection Tool
====================================
Desktop GUI for importing clean signals, injecting artificial interference,
visualizing the results, and exporting / analysing interfered signals.

Run:
    python main.py
"""

import tkinter as tk
from tkinter import ttk

import matplotlib
matplotlib.use('TkAgg')                       # ensure Tk backend before imports

from tab_interference import AddInterferenceTab   # noqa: E402
from tab_analysis import AnalyseExportTab          # noqa: E402


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Signal Interference Injection Tool")
        self.geometry("1440x920")
        self.minsize(1100, 750)

        # Notebook styling
        style = ttk.Style(self)
        style.configure('TNotebook.Tab', padding=[18, 6], font=('', 10))

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        tab1 = AddInterferenceTab(notebook)
        tab2 = AnalyseExportTab(notebook)

        notebook.add(tab1, text="  Add Interference  ")
        notebook.add(tab2, text="  Analyse & Export  ")


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
