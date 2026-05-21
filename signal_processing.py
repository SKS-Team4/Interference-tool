"""
Signal Processing Utilities
============================
Core math and I/O functions for the Signal Interference Injection Tool.
"""

import ast
import csv
import numpy as np
from scipy import interpolate


# ---------------------------------------------------------------------------
# Unit conversions
# ---------------------------------------------------------------------------

def dbm_to_mw(dbm):
    """Convert dBm values to milliwatts (linear power)."""
    return np.power(10.0, np.asarray(dbm, dtype=np.float64) / 10.0)


def mw_to_dbm(mw):
    """Convert milliwatt values to dBm. Clips near-zero to avoid log(0)."""
    mw = np.asarray(mw, dtype=np.float64)
    mw = np.maximum(mw, 1e-30)
    return 10.0 * np.log10(mw)


# ---------------------------------------------------------------------------
# Interpolation
# ---------------------------------------------------------------------------

def interpolate_signal(source_psd, source_freqs, target_freqs):
    """
    Linearly interpolate *source_psd* (defined on *source_freqs*) onto
    *target_freqs*.  Frequencies outside the source range are filled with
    -120 dBm (effectively silence).
    """
    source_psd = np.asarray(source_psd, dtype=np.float64)
    source_freqs = np.asarray(source_freqs, dtype=np.float64)
    target_freqs = np.asarray(target_freqs, dtype=np.float64)

    if len(source_psd) == 0:
        return np.full_like(target_freqs, -120.0)
    if len(source_psd) == 1:
        return np.full_like(target_freqs, source_psd[0])

    f = interpolate.interp1d(
        source_freqs, source_psd,
        kind='linear',
        bounds_error=False,
        fill_value=-120.0,
    )
    return f(target_freqs)


# ---------------------------------------------------------------------------
# Injection
# ---------------------------------------------------------------------------

def inject_interference(clean_psd_dbm, interf_psd_dbm):
    """
    Combine clean and interference signals (both in dBm) by converting to
    milliwatts, summing, and converting back.
    """
    clean_mw = dbm_to_mw(clean_psd_dbm)
    interf_mw = dbm_to_mw(interf_psd_dbm)
    return mw_to_dbm(clean_mw + interf_mw)


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def compute_statistics(all_psd):
    """
    Compute per-frequency-bin statistics across all rows.

    Parameters
    ----------
    all_psd : array-like, shape (n_rows, n_bins)
        PSD values in dBm.

    Returns
    -------
    mean, maximum, minimum : ndarray
    """
    data = np.asarray(all_psd, dtype=np.float64)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    return np.mean(data, axis=0), np.max(data, axis=0), np.min(data, axis=0)


# ---------------------------------------------------------------------------
# CSV / DAT I/O helpers
# ---------------------------------------------------------------------------

def _detect_delimiter(sample_text):
    """Heuristically detect the delimiter used in a text sample."""
    for delim in ('\t', ';', ','):
        if delim in sample_text:
            return delim
    return ','


def _is_team4_signal_format(header_line, delimiter):
    """Check whether the first line matches the Team 4 header format."""
    fields = [f.strip().upper() for f in header_line.split(delimiter)]
    return 'PSD_MEAS' in fields


def _parse_team4_signal(fh, delimiter):
    """Parse the Team-4 signal format (header + list-literal PSD column)."""
    header = fh.readline()
    cols = [c.strip().upper() for c in header.split(delimiter)]
    idx_start = cols.index('SEG_START_FREQ')
    idx_stop = cols.index('SEG_STOP_FREQ')
    idx_psd = cols.index('PSD_MEAS')

    rows = []
    for line in fh:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split(delimiter)
        try:
            start_freq = float(parts[idx_start].strip())
            stop_freq = float(parts[idx_stop].strip())
            psd_str = parts[idx_psd].strip()
            psd_list = ast.literal_eval(psd_str)
            psd = np.array(psd_list, dtype=np.float64)
            rows.append((start_freq, stop_freq, psd))
        except (ValueError, IndexError, SyntaxError):
            continue
    return rows


def parse_clean_signal_csv(filepath):
    """
    Parse a clean-signal CSV/DAT file.

    Supports two formats:
    1. Simple: start_freq, stop_freq, psd_1, psd_2, …, psd_N
    2. Team 4: tab-delimited with header row containing SEG_START_FREQ,
       SEG_STOP_FREQ, PSD_MEAS (Python list literal).

    Returns
    -------
    list of (start_freq, stop_freq, psd_array) tuples.
    """
    rows = []
    with open(filepath, 'r', newline='', encoding='utf-8-sig') as fh:
        sample = fh.read(8192)
        fh.seek(0)
        delimiter = _detect_delimiter(sample)

        # Check for Team 4 header format
        first_line = sample.split('\n')[0]
        if _is_team4_signal_format(first_line, delimiter):
            return _parse_team4_signal(fh, delimiter)

        reader = csv.reader(fh, delimiter=delimiter)
        for row in reader:
            if not row or row[0].strip().startswith('#'):
                continue
            try:
                values = [float(v.strip()) for v in row if v.strip()]
            except ValueError:
                continue              # skip headers / non-numeric rows
            if len(values) < 3:
                continue
            start_freq = values[0]
            stop_freq = values[1]
            psd = np.array(values[2:], dtype=np.float64)
            rows.append((start_freq, stop_freq, psd))
    return rows


def parse_interference_file(filepath, unit='auto'):
    """
    Parse an interference CSV/DAT file.

    Parameters
    ----------
    filepath : str
    unit : str
        'dbm'   – values are already in dBm.
        'mw'    – values are in milliwatts (convert to dBm).
        'auto'  – detect automatically: if median absolute value > 200,
                  assume linear milliwatts and convert.

    Returns
    -------
    values : ndarray  (1-D, in dBm)
    detected_unit : str  ('dbm' or 'mw')
    """
    raw = []
    with open(filepath, 'r', newline='', encoding='utf-8-sig') as fh:
        sample = fh.read(8192)
        fh.seek(0)
        delimiter = _detect_delimiter(sample)

        reader = csv.reader(fh, delimiter=delimiter)
        for row in reader:
            if not row or row[0].strip().startswith('#'):
                continue
            for cell in row:
                cell = cell.strip()
                if not cell:
                    continue
                try:
                    raw.append(float(cell))
                except ValueError:
                    continue

    arr = np.array(raw, dtype=np.float64)
    if len(arr) == 0:
        return arr, 'dbm'

    if unit == 'auto':
        unit = 'mw' if np.median(np.abs(arr)) > 200 else 'dbm'

    if unit == 'mw':
        arr = mw_to_dbm(arr)

    return arr, unit


def export_signal_csv(filepath, data_rows, delimiter=',', team4_format=False):
    """
    Export signal rows to CSV.

    Parameters
    ----------
    data_rows : list of (start_freq, stop_freq, psd_array)
    team4_format : bool
        If True, export in Team 4 tab-delimited format with header.
    """
    if team4_format:
        with open(filepath, 'w', newline='', encoding='utf-8') as fh:
            fh.write('SEG_START_FREQ\tCENTRE_FREQ\tSEG_STOP_FREQ\tCOUNT\tPSD_MEAS\n')
            for start_freq, stop_freq, psd in data_rows:
                centre = (start_freq + stop_freq) / 2.0
                count = len(psd)
                psd_str = '[' + ', '.join(str(v) for v in psd.tolist()) + ']'
                fh.write(f'{start_freq}\t{centre}\t{stop_freq}\t{count}\t{psd_str}\n')
    else:
        with open(filepath, 'w', newline='', encoding='utf-8') as fh:
            writer = csv.writer(fh, delimiter=delimiter)
            for start_freq, stop_freq, psd in data_rows:
                row = [start_freq, stop_freq] + psd.tolist()
                writer.writerow(row)


def export_statistics_csv(filepath, freqs, mean_psd, max_psd, min_psd):
    """Export per-frequency statistics to CSV with a header row."""
    with open(filepath, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.writer(fh)
        writer.writerow(['Frequency (Hz)', 'Mean PSD (dBm)',
                         'Max PSD (dBm)', 'Min PSD (dBm)'])
        for i in range(len(freqs)):
            writer.writerow([freqs[i], mean_psd[i], max_psd[i], min_psd[i]])
