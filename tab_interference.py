"""
Tab 1 – Add Interference
=========================
Import clean signals & interference data, adjust interference parameters in
real-time, preview / inject, and export the combined result.
"""

import math
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import signal_processing as sp


class AddInterferenceTab(ttk.Frame):
    """First notebook tab: import, configure, preview, inject & export."""

    def __init__(self, parent):
        super().__init__(parent)

        # ---- data stores ----
        self.clean_data: list = []        # [(start_freq, stop_freq, psd_array), …]
        self.interf_raw: np.ndarray | None = None  # flat array of dBm values
        self.injected_data: list | None = None

        # ---- state ----
        self.current_clean_row = 0
        self.current_interf_page = 0
        self.preview_active = False
        self._update_timer = None

        # ---- scrollable container ----
        self._canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self._vsb = ttk.Scrollbar(self, orient=tk.VERTICAL,
                                   command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._vsb.set)
        self._vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._inner = ttk.Frame(self._canvas)
        self._cw = self._canvas.create_window((0, 0), window=self._inner,
                                               anchor='nw')
        self._inner.bind('<Configure>', self._on_inner_configure)
        self._canvas.bind('<Configure>', self._on_canvas_configure)
        self._canvas.bind('<Enter>', lambda e: self._canvas.bind_all(
            '<MouseWheel>', self._on_mousewheel))
        self._canvas.bind('<Leave>', lambda e: self._canvas.unbind_all(
            '<MouseWheel>'))

        # ---- build UI ----
        self._build_toolbar()
        self._build_plots()
        self._build_params()
        self._build_actions()
        self._build_injected_plot()
        self._init_plots()

    # ===================================================================
    # Scroll helpers
    # ===================================================================

    def _on_inner_configure(self, event):
        self._canvas.configure(scrollregion=self._canvas.bbox('all'))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._cw, width=event.width)

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

    # ===================================================================
    # UI construction
    # ===================================================================

    def _build_toolbar(self):
        frm = ttk.Frame(self._inner)
        frm.pack(fill=tk.X, padx=10, pady=(8, 2))

        ttk.Button(frm, text="Import Clean Signal (CSV/DAT)",
                   command=self._import_clean).pack(side=tk.LEFT, padx=5)
        ttk.Button(frm, text="Import Interference (CSV/DAT)",
                   command=self._import_interference).pack(side=tk.LEFT, padx=5)

        self.clean_info = ttk.Label(frm, text="No clean signal loaded",
                                    foreground="gray")
        self.clean_info.pack(side=tk.LEFT, padx=12)

        self.interf_info = ttk.Label(frm, text="No interference loaded",
                                     foreground="gray")
        self.interf_info.pack(side=tk.LEFT, padx=12)

    # ----- plots -----
    def _build_plots(self):
        plots = ttk.Frame(self._inner)
        plots.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        # -- clean signal (left) --
        left = ttk.LabelFrame(plots, text="Clean Signal")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))

        self.fig_clean = Figure(figsize=(6, 3.5), dpi=100)
        self.ax_clean = self.fig_clean.add_subplot(111)
        self.canvas_clean = FigureCanvasTkAgg(self.fig_clean, master=left)
        self.canvas_clean.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        nav = ttk.Frame(left)
        nav.pack(fill=tk.X, pady=2)
        ttk.Button(nav, text="\u25C0 Previous",
                   command=self._prev_clean).pack(side=tk.LEFT, padx=5)
        self.clean_row_lbl = ttk.Label(nav, text="Row: \u2014 / \u2014")
        self.clean_row_lbl.pack(side=tk.LEFT, expand=True)
        ttk.Button(nav, text="Next \u25B6",
                   command=self._next_clean).pack(side=tk.RIGHT, padx=5)

        # -- interference (right) --
        right = ttk.LabelFrame(plots, text="Interference")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))

        self.fig_interf = Figure(figsize=(6, 3.5), dpi=100)
        self.ax_interf = self.fig_interf.add_subplot(111)
        self.canvas_interf = FigureCanvasTkAgg(self.fig_interf, master=right)
        self.canvas_interf.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        nav2 = ttk.Frame(right)
        nav2.pack(fill=tk.X, pady=2)
        ttk.Button(nav2, text="\u25C0 Previous",
                   command=self._prev_interf).pack(side=tk.LEFT, padx=5)
        self.interf_page_lbl = ttk.Label(nav2, text="Page: \u2014 / \u2014")
        self.interf_page_lbl.pack(side=tk.LEFT, expand=True)
        ttk.Button(nav2, text="Next \u25B6",
                   command=self._next_interf).pack(side=tk.RIGHT, padx=5)

    # ----- injected signal (below action bar) -----
    def _build_injected_plot(self):
        bottom = ttk.LabelFrame(self._inner, text="Injected Signal")
        bottom.pack(fill=tk.X, expand=False, padx=10, pady=(2, 8))

        self.fig_injected = Figure(figsize=(12, 3.2), dpi=100)
        self.ax_injected = self.fig_injected.add_subplot(111)
        self.canvas_injected = FigureCanvasTkAgg(self.fig_injected, master=bottom)
        self.canvas_injected.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # ----- interference parameters -----
    def _build_params(self):
        outer = ttk.LabelFrame(self._inner, text="Interference Parameters")
        outer.pack(fill=tk.X, padx=10, pady=4)

        g = ttk.Frame(outer)
        g.pack(fill=tk.X, padx=8, pady=6)

        # Row 0
        ttk.Label(g, text="Spectrum Width (Hz):").grid(
            row=0, column=0, sticky=tk.E, padx=4, pady=3)
        self.var_sw = tk.StringVar(value="0")
        ttk.Entry(g, textvariable=self.var_sw, width=18).grid(
            row=0, column=1, padx=4, pady=3)

        ttk.Label(g, text="Center Frequency (Hz):").grid(
            row=0, column=2, sticky=tk.E, padx=4, pady=3)
        self.var_cf = tk.StringVar(value="0")
        ttk.Entry(g, textvariable=self.var_cf, width=18).grid(
            row=0, column=3, padx=4, pady=3)

        ttk.Label(g, text="Amplitude Offset (dB):").grid(
            row=0, column=4, sticky=tk.E, padx=4, pady=3)
        self.var_ao = tk.StringVar(value="0")
        ttk.Entry(g, textvariable=self.var_ao, width=12).grid(
            row=0, column=5, padx=4, pady=3)

        # Row 1
        ttk.Label(g, text="Vector Length:").grid(
            row=1, column=0, sticky=tk.E, padx=4, pady=3)
        self.var_vl = tk.StringVar(value="100")
        ttk.Entry(g, textvariable=self.var_vl, width=18).grid(
            row=1, column=1, padx=4, pady=3)

        # Bind real-time updates (debounced)
        for var in (self.var_sw, self.var_cf, self.var_ao, self.var_vl):
            var.trace_add('write', self._on_param_change)

    # ----- action bar -----
    def _build_actions(self):
        bar = ttk.Frame(self._inner)
        bar.pack(fill=tk.X, padx=10, pady=(2, 8))

        ttk.Label(bar, text="Injection Strategy:").pack(side=tk.LEFT, padx=5)
        self.var_strategy = tk.StringVar(value="round_robin")
        ttk.Radiobutton(bar, text="Round Robin",
                        variable=self.var_strategy,
                        value="round_robin").pack(side=tk.LEFT, padx=4)
        ttk.Radiobutton(bar, text="One-to-All",
                        variable=self.var_strategy,
                        value="one_to_all").pack(side=tk.LEFT, padx=4)

        ttk.Separator(bar, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=12, pady=2)

        self.preview_btn = ttk.Button(bar, text="Preview",
                                      command=self._toggle_preview)
        self.preview_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(bar, text="Inject && Export",
                   command=self._inject_and_export).pack(side=tk.LEFT, padx=5)

    # ===================================================================
    # Plot initialisation
    # ===================================================================

    def _init_plots(self):
        for ax, title, ylabel in (
            (self.ax_clean,    "Clean Signal",    "PSD (dBm)"),
            (self.ax_interf,   "Interference",    "PSD (dBm)"),
            (self.ax_injected, "Injected Signal", "PSD (dBm)"),
        ):
            ax.set_title(title, fontsize=10)
            ax.set_xlabel("Frequency (Hz)", fontsize=9)
            ax.set_ylabel(ylabel, fontsize=9)
            ax.grid(True, alpha=0.3)
            ax.tick_params(labelsize=8)
        self.fig_clean.tight_layout(pad=2.5)
        self.fig_interf.tight_layout(pad=2.5)
        self.fig_injected.tight_layout(pad=2.5)
        self.canvas_clean.draw_idle()
        self.canvas_interf.draw_idle()
        self.canvas_injected.draw_idle()

    # ===================================================================
    # Parameter helpers (safe getters)
    # ===================================================================

    def _freq_label(self):
        """Return an appropriate frequency axis label based on data range."""
        if self.clean_data:
            s, e, _ = self.clean_data[0]
            max_f = max(abs(s), abs(e))
            if max_f > 1e9:
                return "Frequency (GHz)"
            if max_f > 1e6:
                return "Frequency (MHz)"
            if max_f > 1e3:
                return "Frequency (kHz)"
        return "Frequency (Hz)"

    def _int_var(self, var, default=0, minimum=0):
        try:
            return max(minimum, int(var.get()))
        except (ValueError, TypeError):
            return default

    def _float_var(self, var, default=0.0):
        try:
            return float(var.get())
        except (ValueError, TypeError):
            return default

    @property
    def spectrum_width(self):
        return self._float_var(self.var_sw)

    @property
    def center_freq(self):
        return self._float_var(self.var_cf)

    @property
    def amplitude_offset(self):
        return self._float_var(self.var_ao)

    @property
    def vector_length(self):
        return self._int_var(self.var_vl, default=100, minimum=1)

    # ===================================================================
    # Interference paging
    # ===================================================================

    @property
    def num_interf_pages(self):
        if self.interf_raw is None:
            return 0
        available = len(self.interf_raw)
        return math.ceil(available / self.vector_length) if available > 0 else 0

    def _interf_page_data(self, page=None):
        """Return the dBm values for the given (or current) interference page,
        with amplitude offset already applied."""
        if self.interf_raw is None:
            return None
        if page is None:
            page = self.current_interf_page
        start = page * self.vector_length
        end = start + self.vector_length
        if start >= len(self.interf_raw):
            return None
        data = self.interf_raw[start:end]
        if len(data) == 0:
            return None
        return data + self.amplitude_offset

    def _interf_freqs(self, n_points):
        """Generate an equidistant frequency axis for the interference."""
        c = self.center_freq
        w = self.spectrum_width
        if w <= 0 or n_points <= 0:
            return np.array([c])
        return np.linspace(c - w / 2, c + w / 2, n_points)

    # ===================================================================
    # File import
    # ===================================================================

    def _import_clean(self):
        path = filedialog.askopenfilename(
            title="Import Clean Signal",
            filetypes=[("CSV files", "*.csv"), ("DAT files", "*.dat"),
                       ("All files", "*.*")])
        if not path:
            return
        try:
            data = sp.parse_clean_signal_csv(path)
            if not data:
                messagebox.showerror("Error", "No valid signal rows found.")
                return
            self.clean_data = data
            self.current_clean_row = 0
            self.preview_active = False
            self.preview_btn.configure(text="Preview")

            # Set sensible default params from the first row
            s, e, psd = data[0]
            self.var_sw.set(str(e - s))
            self.var_cf.set(str((s + e) / 2))

            self.clean_info.configure(
                text=f"Clean: {len(data)} rows, {len(psd)} bins",
                foreground="black")
            self._update_clean_plot()
        except Exception as exc:
            messagebox.showerror("Import Error", str(exc))

    def _import_interference(self):
        path = filedialog.askopenfilename(
            title="Import Interference Data",
            filetypes=[("CSV files", "*.csv"), ("DAT files", "*.dat"),
                       ("All files", "*.*")])
        if not path:
            return
        self._load_interference(path)

    def _load_interference(self, path, unit='auto'):
        try:
            raw, detected = sp.parse_interference_file(path, unit=unit)
            if len(raw) == 0:
                messagebox.showerror("Error", "No numeric data found.")
                return
            self.interf_raw = raw
            self.current_interf_page = 0

            # Default vector length = clean signal bins (if available)
            if self.clean_data:
                self.var_vl.set(str(len(self.clean_data[0][2])))

            unit_str = 'linear\u2192dBm' if detected == 'mw' else 'dBm'
            self.interf_info.configure(
                text=f"Interference: {len(raw)} values ({unit_str})",
                foreground="black")
            self._update_interference_plot()
        except Exception as exc:
            messagebox.showerror("Import Error", str(exc))

    def _load_team4(self):
        """Auto-load both signal and interference from the Team_4 folder."""
        team4_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 'Team_4')
        sig_path = os.path.join(team4_dir, 'signal_data_team_4.csv')
        int_path = os.path.join(team4_dir, 'interference_data_team_4.csv')

        loaded = []
        if os.path.isfile(sig_path):
            try:
                data = sp.parse_clean_signal_csv(sig_path)
                if data:
                    self.clean_data = data
                    self.current_clean_row = 0
                    self.preview_active = False
                    self.preview_btn.configure(text="Preview")
                    s, e, psd = data[0]
                    self.var_sw.set(str(e - s))
                    self.var_cf.set(str((s + e) / 2))
                    self.clean_info.configure(
                        text=f"Clean: {len(data)} rows, {len(psd)} bins",
                        foreground="black")
                    self._update_clean_plot()
                    loaded.append('signal')
            except Exception as exc:
                messagebox.showerror("Import Error",
                                     f"Signal: {exc}")

        if os.path.isfile(int_path):
            self._load_interference(int_path, unit='auto')
            loaded.append('interference')

        if loaded:
            messagebox.showinfo("Team 4 Data",
                                f"Loaded: {', '.join(loaded)}")
        else:
            messagebox.showwarning("Team 4 Data",
                                   "No Team 4 files found.")

    # ===================================================================
    # Navigation
    # ===================================================================

    def _prev_clean(self):
        if self.clean_data and self.current_clean_row > 0:
            self.current_clean_row -= 1
            self._update_clean_plot()
            self._update_injected_plot()

    def _next_clean(self):
        if self.clean_data and self.current_clean_row < len(self.clean_data) - 1:
            self.current_clean_row += 1
            self._update_clean_plot()
            self._update_injected_plot()

    def _prev_interf(self):
        if self.current_interf_page > 0:
            self.current_interf_page -= 1
            self._update_interference_plot()

    def _next_interf(self):
        if self.current_interf_page < self.num_interf_pages - 1:
            self.current_interf_page += 1
            self._update_interference_plot()

    # ===================================================================
    # Real-time parameter updates (debounced)
    # ===================================================================

    def _on_param_change(self, *_args):
        if self._update_timer is not None:
            self.after_cancel(self._update_timer)
        self._update_timer = self.after(200, self._debounced_refresh)

    def _debounced_refresh(self):
        self._update_timer = None
        self._update_interference_plot()

    # ===================================================================
    # Plot updates
    # ===================================================================

    def _update_clean_plot(self):
        ax = self.ax_clean
        ax.clear()
        ax.set_title("Clean Signal", fontsize=10)
        ax.set_xlabel(self._freq_label(), fontsize=9)
        ax.set_ylabel("PSD (dBm)", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=8)

        if not self.clean_data:
            self.clean_row_lbl.configure(text="Row: \u2014 / \u2014")
            self.canvas_clean.draw_idle()
            return

        s, e, psd = self.clean_data[self.current_clean_row]
        freqs = np.linspace(s, e, len(psd))
        ax.plot(freqs, psd, color='#4a90d9', linewidth=1.0)

        self.clean_row_lbl.configure(
            text=f"Row: {self.current_clean_row + 1} / {len(self.clean_data)}")
        self.fig_clean.tight_layout(pad=2.5)
        self.canvas_clean.draw_idle()

    def _update_interference_plot(self):
        ax = self.ax_interf
        ax.clear()
        ax.set_title("Interference", fontsize=10)
        ax.set_xlabel(self._freq_label(), fontsize=9)
        ax.set_ylabel("PSD (dBm)", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=8)

        n_pages = self.num_interf_pages
        if n_pages == 0 or self.interf_raw is None:
            self.interf_page_lbl.configure(text="Page: \u2014 / \u2014")
            self.canvas_interf.draw_idle()
            return

        # Clamp page index
        if self.current_interf_page >= n_pages:
            self.current_interf_page = n_pages - 1

        data = self._interf_page_data()
        if data is not None:
            freqs = self._interf_freqs(len(data))
            ax.plot(freqs, data, color='#e74c3c', linewidth=1.0)

        self.interf_page_lbl.configure(
            text=f"Page: {self.current_interf_page + 1} / {n_pages}")
        self.fig_interf.tight_layout(pad=2.5)
        self.canvas_interf.draw_idle()

        if self.preview_active:
            self._update_injected_plot()

    # ===================================================================
    # Interference interpolation for injection / preview
    # ===================================================================

    def _interpolated_interf_for_row(self, row_idx):
        """Return the interference PSD interpolated to match the clean signal
        frequency grid for the given row."""
        if self.interf_raw is None or not self.clean_data:
            return None
        n_pages = self.num_interf_pages
        if n_pages == 0:
            return None

        strategy = self.var_strategy.get()
        page = (self.current_interf_page
                if strategy == "one_to_all"
                else row_idx % n_pages)

        interf = self._interf_page_data(page)
        if interf is None:
            return None

        s, e, psd = self.clean_data[row_idx]
        target_freqs = np.linspace(s, e, len(psd))
        interf_freqs = self._interf_freqs(len(interf))
        return sp.interpolate_signal(interf, interf_freqs, target_freqs)

    # ===================================================================
    # Preview toggle
    # ===================================================================

    def _toggle_preview(self):
        if not self.clean_data:
            messagebox.showwarning("Warning",
                                   "Import a clean signal first.")
            return
        if self.interf_raw is None:
            messagebox.showwarning("Warning",
                                   "Import interference data first.")
            return
        self.preview_active = not self.preview_active
        self.preview_btn.configure(
            text="Reset Preview" if self.preview_active else "Preview")
        self._update_injected_plot()

    # ===================================================================
    # Inject & Export
    # ===================================================================

    def _update_injected_plot(self):
        ax = self.ax_injected
        ax.clear()
        ax.set_title("Injected Signal", fontsize=10)
        ax.set_xlabel(self._freq_label(), fontsize=9)
        ax.set_ylabel("PSD (dBm)", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=8)

        if self.preview_active and self.clean_data and self.interf_raw is not None:
            interf = self._interpolated_interf_for_row(self.current_clean_row)
            if interf is not None:
                s, e, psd = self.clean_data[self.current_clean_row]
                freqs = np.linspace(s, e, len(psd))
                ax.plot(freqs, sp.inject_interference(psd, interf),
                        color='#2ecc71', linewidth=1.0)
        elif self.injected_data:
            s, e, psd = self.injected_data[self.current_clean_row]
            freqs = np.linspace(s, e, len(psd))
            ax.plot(freqs, psd, color='#2ecc71', linewidth=1.0)

        self.fig_injected.tight_layout(pad=2.5)
        self.canvas_injected.draw_idle()

    def _inject_and_export(self):
        if not self.clean_data:
            messagebox.showwarning("Warning",
                                   "Import a clean signal first.")
            return
        if self.interf_raw is None:
            messagebox.showwarning("Warning",
                                   "Import interference data first.")
            return

        # Build the combined dataset and show it immediately
        injected = []
        for i, (s, e, psd) in enumerate(self.clean_data):
            interf = self._interpolated_interf_for_row(i)
            combined = (sp.inject_interference(psd, interf)
                        if interf is not None else psd.copy())
            injected.append((s, e, combined))

        self.injected_data = injected
        self._update_injected_plot()

        # Ask for output path (optional — user can cancel without losing the graph)
        path = filedialog.asksaveasfilename(
            title="Export Interfered Signal",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("DAT files", "*.dat"),
                       ("All files", "*.*")])
        if not path:
            return

        try:
            sp.export_signal_csv(path, injected)
            messagebox.showinfo(
                "Success",
                f"Exported {len(injected)} rows to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export Error", str(exc))
