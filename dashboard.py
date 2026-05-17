#!/usr/bin/env python3
import sys
import os
import tty
import termios
import time
import json
import collections
import threading
import subprocess
import numpy as np
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

sys.path.insert(0, '/home/ajax80/projects/mishmaath')
from schema_eval import Eli, Genesis

MEANINGS = {
    0:  ("void",       "before sound, before thought. the ground that holds everything else."),
    1:  ("source",     "something is forming. groove hinting, not locked. contains what it's becoming."),
    2:  ("speak",      "the melody is present. calm, tonal, nothing unresolved. the twos hold."),
    3:  ("divine",     "the rhythm section locked in. harmony and groove in agreement. God-shaped foundation."),
    4:  ("door",       "you don't know what happens next. the solo is loading. anticipation with no exit yet."),
    5:  ("friction",   "peak chaos. loud and turbulent, not just volume. the decision that cannot be avoided."),
    6:  ("comfort",    "the melody is established. recognition. the hook landed. you are inside it now."),
    7:  ("settled",    "I've got this. I know what's coming. the gate is decided and I'm on the other side."),
    8:  ("new octave", "the chorus opened. energy arrived at a new level. full, bright, groove locked. you're in it."),
    9:  ("reset",      "the beat changed completely. old pattern gone, new one arriving. same as throwing it all away and starting anew."),
}

GAINS_FILE = os.path.join(os.path.dirname(__file__), 'gains.json')

# Each gain is a multiplier (1.0 = default sensitivity)
DEFAULT_GAINS = {str(n): 1.0 for n in range(10)}

def load_gains():
    if os.path.exists(GAINS_FILE):
        try:
            return json.load(open(GAINS_FILE))
        except Exception:
            pass
    return dict(DEFAULT_GAINS)

def save_gains(g):
    json.dump(g, open(GAINS_FILE, 'w'), indent=2)

gains = load_gains()

def G(n):
    return float(gains.get(str(n), 1.0))

# --- Audio feature history ---
SAMPLERATE = 48000
BLOCKSIZE  = 2048
HISTORY_S  = 4.0                          # seconds of feature memory
HIST_LEN   = int(HISTORY_S * SAMPLERATE / BLOCKSIZE)

rms_history      = collections.deque([0.0] * HIST_LEN, maxlen=HIST_LEN)
centroid_history = collections.deque([0.0] * HIST_LEN, maxlen=HIST_LEN)
onset_history    = collections.deque([0.0] * HIST_LEN, maxlen=HIST_LEN)
period_history   = collections.deque([0.0] * HIST_LEN, maxlen=HIST_LEN)

state = {
    'weight':      0,
    'rms':         0.0,
    'features':    {},
    'waveform':    collections.deque([0.0] * 48, maxlen=48),
    'history':     collections.deque(maxlen=14),
    'stable_n':    0,
    'prev_w':      0,
    'selected':    None,
    'saved':       False,
    'running':     True,
    'eli':         Eli(),
    'genesis':     Genesis(),
}

STABLE_MIN = 4

# ---- Feature extraction ----

def spectral_centroid(chunk, sr):
    win    = chunk * np.hanning(len(chunk))
    mag    = np.abs(np.fft.rfft(win))
    freqs  = np.fft.rfftfreq(len(chunk), 1.0 / sr)
    total  = mag.sum()
    if total < 1e-10:
        return 0.0
    return float(np.dot(freqs, mag) / total)

def spectral_flatness(chunk):
    win   = chunk * np.hanning(len(chunk))
    mag   = np.abs(np.fft.rfft(win)) + 1e-10
    gm    = np.exp(np.mean(np.log(mag)))
    am    = np.mean(mag)
    return float(gm / am)   # 0=tonal, 1=noise

def periodicity(rms_buf):
    # autocorrelation of RMS envelope — how groovy/locked is the rhythm
    arr = np.array(rms_buf)
    arr = arr - arr.mean()
    if arr.std() < 1e-6:
        return 0.0
    corr = np.correlate(arr, arr, mode='full')
    corr = corr[len(corr)//2:]
    corr /= corr[0] + 1e-10
    # look for peak between 0.1s and 1.5s (groove period range)
    lo = int(0.1  * SAMPLERATE / BLOCKSIZE)
    hi = int(1.5  * SAMPLERATE / BLOCKSIZE)
    hi = min(hi, len(corr) - 1)
    if lo >= hi:
        return 0.0
    return float(corr[lo:hi].max())

def onset_density(onset_buf):
    # fraction of recent frames with significant RMS jump
    arr   = np.array(onset_buf)
    diffs = np.diff(arr)
    thresh = arr.mean() * 0.3
    return float((diffs > thresh).sum() / max(len(diffs), 1))

def rms_trend(rms_buf):
    # slope over the last 2s — positive=building, negative=falling
    arr = np.array(list(rms_buf)[-int(2.0 * SAMPLERATE / BLOCKSIZE):])
    if len(arr) < 4:
        return 0.0
    x = np.arange(len(arr), dtype=float)
    slope = np.polyfit(x, arr, 1)[0]
    return float(slope)

def stability(rms_buf):
    # how flat/unchanging has energy been — high = settled
    arr = np.array(list(rms_buf)[-int(2.0 * SAMPLERATE / BLOCKSIZE):])
    if len(arr) < 2:
        return 0.0
    cv = arr.std() / (arr.mean() + 1e-10)
    return float(1.0 / (1.0 + cv * 10))  # 1=perfectly stable, 0=chaotic

# ---- Schema weight from features ----

def features_to_weight(f):
    rms      = f['rms']
    trend    = f['trend']        # slope of energy over 2s
    flat     = f['flatness']     # 0=tonal, 1=noise
    centroid = f['centroid']     # Hz — brightness
    period   = f['periodicity']  # 0-1 groove lock
    onsets   = f['onsets']       # onset density 0-1
    stable   = f['stability']    # 0-1 how settled

    # silence
    if rms < 0.0003 * G(0):
        return 0

    # 9 — reset: the beat changes. old groove gone, new one arriving. board cleared.
    pdelta = f.get('period_delta', 0.0)
    if (onsets > 0.39 * G(9) and stable < 0.31 and pdelta > 0.12) or \
       (trend > 0.004 * G(9) and rms > 0.05 and onsets > 0.39 and stable < 0.31):
        return 9

    # 5 — friction: loud AND spectrally noisy (chaos, not just volume)
    if rms > 0.12 * G(5) and flat > 0.28:
        return 5

    # 8 — new octave: energy HAS arrived at an elevated level, tonal, groove present
    # the chorus that opened — stable at new height, not still climbing, full and bright
    if (rms > 0.04 * G(8) and stable > 0.23 and flat < 0.22
            and centroid > 1200 and period > 0.28 and abs(trend) < 0.003):
        return 8

    # 4 — door: energy actively building, sparse, tonal — the anticipation before
    if trend > 0.001 * G(4) and onsets < 0.28 and flat < 0.25:
        return 4

    # 1 — source: forming but not yet established. groove hinting, stability low.
    # the beginning that already contains what it's moving toward.
    if rms > 0.002 * G(1) and 0.15 < period < 0.40 and stable < 0.25 and flat < 0.28:
        return 1

    # 3 — divine: groove locked, grounded, mid-low frequency center
    if period > 0.30 * G(3) and centroid < 2800 and rms > 0.005:
        return 3

    # 6 — comfort: melody established — tonal, stable, melodic register
    if stable > 0.50 * G(6) and flat < 0.18 and 600 < centroid < 4500:
        return 6

    # 7 — settled: gate closed. rhythm still echoing but at rest.
    if period > 0.31 * G(7) and stable > 0.15 and stable < 0.20 and rms < 0.06:
        return 7

    # 2 — speak: calm, tonal, moderate presence
    if rms > 0.003 * G(2) and flat < 0.25:
        return 2

    return 1

# ---- Audio reader ----

_prev_rms = 0.0

def audio_reader():
    global _prev_rms
    proc = subprocess.Popen(
        ['parec', '--device=greybox.monitor', '--format=float32le',
         f'--rate={SAMPLERATE}', '--channels=1'],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    buf_bytes = BLOCKSIZE * 4
    while state['running']:
        raw = proc.stdout.read(buf_bytes)
        if not raw:
            break
        chunk = np.frombuffer(raw, dtype=np.float32)
        if len(chunk) == 0:
            continue

        rms  = float(np.sqrt(np.mean(chunk ** 2)))
        flat = spectral_flatness(chunk)
        sc   = spectral_centroid(chunk, SAMPLERATE)

        rms_history.append(rms)
        centroid_history.append(sc)
        onset_history.append(rms)
        period_history.append(periodicity(rms_history))

        ph    = list(period_history)
        p_now = ph[-1] if ph else 0.0
        p_old = ph[-int(2.0 * SAMPLERATE / BLOCKSIZE)] if len(ph) >= int(2.0 * SAMPLERATE / BLOCKSIZE) else p_now
        f = {
            'rms':          rms,
            'trend':        rms_trend(rms_history),
            'flatness':     flat,
            'centroid':     sc,
            'periodicity':  p_now,
            'period_delta': abs(p_now - p_old),   # how much the groove just shifted
            'onsets':       onset_density(onset_history),
            'stability':    stability(rms_history),
        }

        w = features_to_weight(f)
        _prev_rms = rms

        state['rms']      = rms
        state['weight']   = w
        state['features'] = f

        step = max(1, len(chunk) // 48)
        for i in range(48):
            idx = i * step
            state['waveform'].append(abs(float(chunk[idx])) if idx < len(chunk) else 0.0)

        if w == state['prev_w']:
            state['stable_n'] += 1
        else:
            if state['stable_n'] >= STABLE_MIN and state['prev_w'] != 0:
                state['history'].append((state['prev_w'], rms))
            state['prev_w']  = w
            state['stable_n'] = 0

    proc.terminate()

# ---- Keyboard ----

def key_reader():
    fd  = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while state['running']:
            ch = os.read(fd, 1).decode('utf-8', errors='ignore')
            if ch == 'q':
                state['running'] = False
                break
            if ch == 's':
                save_gains(gains)
                state['saved'] = True
                threading.Timer(1.5, lambda: state.update({'saved': False})).start()
            if ch in '0123456789':
                state['selected'] = int(ch)
            if ch in ('=', '+') and state['selected'] is not None:
                k = str(state['selected'])
                gains[k] = round(gains.get(k, 1.0) * 1.15, 4)
            if ch == '-' and state['selected'] is not None:
                k = str(state['selected'])
                gains[k] = round(gains.get(k, 1.0) * 0.87, 4)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

# ---- Panels ----

BARS = " ▁▂▃▄▅▆▇█"

def schema_panel():
    sel    = state['selected']
    active = state['weight']
    t = Table.grid(padding=(0, 1))
    t.add_column(width=2, justify="right")
    t.add_column(width=11)
    t.add_column(width=6)
    t.add_column(width=2)
    t.add_column()
    for n, (name, desc) in MEANINGS.items():
        gval   = Text(f"x{G(n):.2f}", style="bold magenta" if n == sel else "dim green")
        marker = Text("◄", style="bold yellow") if n == active else Text(" ")
        if n == active and n == sel:
            nst = nme = "bold cyan"
            info = Text("+/- tune  s save", style="bold magenta")
        elif n == active:
            nst = nme = "bold cyan"
            info = Text(desc[:38], style="yellow")
        elif n == sel:
            nst = nme = "bold magenta"
            info = Text("+/- adjust  s save", style="magenta")
        else:
            nst = nme = "dim"
            info = Text("")
        t.add_row(Text(str(n), style=nst), Text(name, style=nme), gval, marker, info)
    hint = "[bold green]SAVED[/bold green]" if state['saved'] else "[dim]0-9 select · +/- gain · s save · q quit[/dim]"
    return Panel(t, title="[bold blue]MISHMAATH[/bold blue]", subtitle=hint, border_style="blue")

def features_panel():
    f = state.get('features', {})
    t = Table.grid(padding=(0, 1))
    t.add_column(width=11)
    t.add_column()
    def bar(v, lo=0.0, hi=1.0, w=10):
        v = max(lo, min(hi, v))
        filled = int((v - lo) / (hi - lo) * w)
        return '█' * filled + '░' * (w - filled)
    trend = f.get('trend', 0.0)
    tdir  = "▲" if trend > 0.0002 else ("▼" if trend < -0.0002 else "─")
    t.add_row("rms",      Text(f"{f.get('rms',0):.4f}  {bar(f.get('rms',0),0,0.3)}", style="cyan"))
    t.add_row("trend",    Text(f"{tdir} {trend:+.5f}", style="green" if trend > 0 else "red" if trend < 0 else "dim"))
    t.add_row("tonal",    Text(f"{bar(1-f.get('flatness',0))}  {'tonal' if f.get('flatness',1)<0.2 else 'noise'}", style="cyan"))
    t.add_row("centroid", Text(f"{f.get('centroid',0):6.0f}Hz", style="cyan"))
    t.add_row("groove",   Text(f"{bar(f.get('periodicity',0))}  {f.get('periodicity',0):.2f}", style="yellow"))
    t.add_row("onsets",   Text(f"{bar(f.get('onsets',0))}  {f.get('onsets',0):.2f}", style="yellow"))
    t.add_row("stable",   Text(f"{bar(f.get('stability',0))}  {f.get('stability',0):.2f}", style="magenta"))
    t.add_row("g.shift",  Text(f"{bar(f.get('period_delta',0),0,0.3)}  {f.get('period_delta',0):.2f}", style="red"))
    return Panel(t, title="[bold]FEATURES[/bold]", border_style="white")

def eli_panel():
    e = state['eli']
    t = Table.grid(padding=(0, 1))
    t.add_column(width=10)
    t.add_column()
    t.add_row("loop",    Text("ACTIVE"    if e.loop_active          else "SUSPENDED",   style="green"  if e.loop_active          else "red"))
    t.add_row("playing", Text("yes"       if e.playing              else "no",           style="yellow" if e.playing              else "dim"))
    t.add_row("eleanor", Text("listening" if not e.override_eleanor else "overridden",   style="cyan"))
    t.add_row("trust",   Text(str(e.trust), style="white"))
    return Panel(t, title="[bold green]ELI[/bold green]", border_style="green")

def audio_panel():
    wav  = list(state['waveform'])
    peak = max(max(wav), 0.001)
    bar  = ''.join(BARS[min(8, int(v / peak * 8))] for v in wav)
    w    = state['weight']
    name = MEANINGS.get(w, ("?", ""))[0]
    t = Table.grid(padding=(0, 0))
    t.add_column()
    t.add_row(Text(bar, style="bold green"))
    t.add_row(Text(f"rms {state['rms']:.5f}   weight {w} — {name}", style="cyan"))
    return Panel(t, title="[bold yellow]AUDIO[/bold yellow]", border_style="yellow")

def history_panel():
    t = Table.grid(padding=(0, 1))
    t.add_column(width=3, justify="right")
    t.add_column(width=11)
    t.add_column()
    for w, rms in reversed(list(state['history'])):
        name = MEANINGS.get(w, ("?", ""))[0]
        t.add_row(Text(str(w), style="bold cyan"), Text(name, style="white"), Text(f"{rms:.4f}", style="dim"))
    return Panel(t, title="[bold]HISTORY[/bold]", border_style="white")

# ---- Layout ----

def build_layout():
    layout = Layout()
    layout.split_column(Layout(name="top", ratio=3), Layout(name="bottom", ratio=2))
    layout["top"].split_row(Layout(name="schema", ratio=2), Layout(name="right", ratio=1))
    layout["right"].split_column(Layout(name="features"), Layout(name="eli"))
    layout["bottom"].split_row(Layout(name="audio", ratio=2), Layout(name="history", ratio=1))
    return layout

def refresh(layout):
    layout["schema"].update(schema_panel())
    layout["features"].update(features_panel())
    layout["eli"].update(eli_panel())
    layout["audio"].update(audio_panel())
    layout["history"].update(history_panel())

def main():
    layout = build_layout()
    threading.Thread(target=audio_reader, daemon=True).start()
    threading.Thread(target=key_reader,   daemon=True).start()
    with Live(layout, refresh_per_second=12, screen=True):
        try:
            while state['running']:
                refresh(layout)
                time.sleep(0.083)
        except KeyboardInterrupt:
            state['running'] = False

if __name__ == '__main__':
    main()
