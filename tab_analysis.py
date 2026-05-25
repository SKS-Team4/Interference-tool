"""
Tab 2 – Analyse & Export
=========================
Load an interfered signal CSV, compute per-frequency-bin statistics
(mean / max / min), and navigate through rows overlaid on the stats graph.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import signal_processing as sp


class AnalyseExportTab(ttk.Frame):
    """Second notebook tab: analyse & export statistics."""

    def __init__(self, parent):
        super().__init__(parent)

        self.signal_data: list = []   # [(start_freq, stop_freq, psd), …]
        self.current_row = 0
        self.stats = None             # (freqs, mean_psd, max_psd, min_psd)

        self._build_toolbar()
        self._build_stats_plot()
        self._build_export_bar()
        self._init_plots()

    # ===================================================================
    # UI construction
    # ===================================================================

    def _build_toolbar(self):
        frm = ttk.Frame(self)
        frm.pack(fill=tk.X, padx=10, pady=(8, 2))

        ttk.Button(frm, text="Import Interfered Signal (CSV/DAT)",
                   command=self._import_signal).pack(side=tk.LEFT, padx=5)

        self.info_label = ttk.Label(frm, text="No signal loaded",
                                    foreground="gray")
        self.info_label.pack(side=tk.LEFT, padx=12)

    def _build_stats_plot(self):
        frame = ttk.LabelFrame(self,
                               text="Statistics (Mean / Max / Min per Frequency Bin)")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        self.fig_stats = Figure(figsize=(12, 5), dpi=100)
        self.ax_stats = self.fig_stats.add_subplot(111)
        self.canvas_stats = FigureCanvasTkAgg(self.fig_stats, master=frame)
        self.canvas_stats.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        nav = ttk.Frame(frame)
        nav.pack(fill=tk.X, pady=2)
        ttk.Button(nav, text="◀ Previous",
                   command=self._prev_row).pack(side=tk.LEFT, padx=5)
        self.row_lbl = ttk.Label(nav, text="Row: — / —")
        self.row_lbl.pack(side=tk.LEFT, expand=True)
        ttk.Button(nav, text="Next ▶",
                   command=self._next_row).pack(side=tk.RIGHT, padx=5)

    def _build_export_bar(self):
        bar = ttk.Frame(self)
        bar.pack(fill=tk.X, padx=10, pady=(2, 8))
        ttk.Button(bar, text="Export Statistics (CSV)",
                   command=self._export_stats).pack(side=tk.LEFT, padx=5)

    # ===================================================================
    # Helpers
    # ===================================================================

    def _freq_label(self):
        """Return frequency axis label matching the data's magnitude."""
        if self.signal_data:
            s, e, _ = self.signal_data[0]
            max_f = max(abs(s), abs(e))
            if max_f > 1e9:
                return "Frequency (GHz)"
            if max_f > 1e6:
                return "Frequency (MHz)"
            if max_f > 1e3:
                return "Frequency (kHz)"
        return "Frequency (Hz)"

    # ===================================================================
    # Plot initialisation
    # ===================================================================

    def _init_plots(self):
        self.ax_stats.set_title("Statistics", fontsize=10)
        self.ax_stats.set_xlabel("Frequency (Hz)", fontsize=9)
        self.ax_stats.set_ylabel("PSD (dBm)", fontsize=9)
        self.ax_stats.grid(True, alpha=0.3)
        self.ax_stats.tick_params(labelsize=8)
        self.fig_stats.tight_layout(pad=2.5)
        self.canvas_stats.draw_idle()

    # ===================================================================
    # Import
    # ===================================================================

    def _import_signal(self):
        path = filedialog.askopenfilename(
            title="Import Interfered Signal",
            filetypes=[("CSV files", "*.csv"), ("DAT files", "*.dat"),
                       ("All files", "*.*")])
        if not path:
            return
        try:
            data = sp.parse_clean_signal_csv(path)
            if not data:
                messagebox.showerror("Error", "No valid data found.")
                return
            self.signal_data = data
            self.current_row = 0
            self.info_label.configure(
                text=f"Signal: {len(data)} rows, {len(data[0][2])} bins",
                foreground="black")
            self._compute_stats()
            self._update_stats_plot()
        except Exception as exc:
            messagebox.showerror("Import Error", str(exc))

    # ===================================================================
    # Navigation
    # ===================================================================

    def _prev_row(self):
        if self.signal_data and self.current_row > 0:
            self.current_row -= 1
            self._update_stats_plot()

    def _next_row(self):
        if self.signal_data and self.current_row < len(self.signal_data) - 1:
            self.current_row += 1
            self._update_stats_plot()

    # ===================================================================
    # Statistics computation
    # ===================================================================

    def _compute_stats(self):
        if not self.signal_data:
            return
        s, e, _ = self.signal_data[0]
        n_bins = len(self.signal_data[0][2])
        freqs = np.linspace(s, e, n_bins)
        all_psd = np.array([row[2] for row in self.signal_data])
        mean_psd, max_psd, min_psd = sp.compute_statistics(all_psd)
        self.stats = (freqs, mean_psd, max_psd, min_psd)

    # ===================================================================
    # Plot update
    # ===================================================================

    def _update_stats_plot(self):
        if not self.signal_data or self.stats is None:
            return

        freqs, mean_psd, max_psd, min_psd = self.stats
        freq_label = self._freq_label()

        ax = self.ax_stats
        ax.clear()
        ax.set_title("Statistics (across all time steps)", fontsize=10)
        ax.set_xlabel(freq_label, fontsize=9)
        ax.set_ylabel("PSD (dBm)", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=8)

        # Statistical envelope
        ax.fill_between(freqs, min_psd, max_psd, alpha=0.12, color='gray',
                        label='Min–Max range')
        ax.plot(freqs, mean_psd, color='#2ecc71', linewidth=1.2, label='Mean')
        ax.plot(freqs, max_psd,  color='#e74c3c', linewidth=0.8, alpha=0.7, label='Max')
        ax.plot(freqs, min_psd,  color='#3498db', linewidth=0.8, alpha=0.7, label='Min')

        # Current row overlay
        s, e, psd = self.signal_data[self.current_row]
        row_freqs = np.linspace(s, e, len(psd))
        ax.plot(row_freqs, psd, color='#8e44ad', linewidth=1.0,
                label=f'Row {self.current_row + 1}')

        ax.legend(fontsize=8, loc='best')
        self.row_lbl.configure(
            text=f"Row: {self.current_row + 1} / {len(self.signal_data)}")
        self.fig_stats.tight_layout(pad=2.5)
        self.canvas_stats.draw_idle()

    # ===================================================================
    # Export
    # ===================================================================

    def _export_stats(self):
        if self.stats is None:
            messagebox.showwarning("Warning",
                                   "No statistics computed. Import a signal first.")
            return

        path = filedialog.asksaveasfilename(
            title="Export Statistics",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        try:
            freqs, mean_psd, max_psd, min_psd = self.stats
            sp.export_statistics_csv(path, freqs, mean_psd, max_psd, min_psd)
            messagebox.showinfo("Success",
                                f"Statistics exported to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export Error", str(exc))
