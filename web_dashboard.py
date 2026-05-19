#!/usr/bin/env python3
import os, sys, json, asyncio, threading, collections, subprocess, argparse, math, time
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

sys.path.insert(0, os.path.dirname(__file__))
from schema_eval import Eli, Genesis

MEANINGS = {
    0: ("void",       "before sound, before thought. the ground that holds everything else."),
    1: ("source",     "forming. groove hinting. contains what it's becoming."),
    2: ("speak",      "the melody is present. calm, tonal. nothing unresolved."),
    3: ("divine",     "rhythm locked. harmony in agreement. God-shaped foundation."),
    4: ("door",       "anticipation. the solo is loading. no exit yet."),
    5: ("friction",   "peak chaos. loud and turbulent. the unavoidable decision."),
    6: ("comfort",    "the hook landed. recognition. you are inside it now."),
    7: ("settled",    "I've got this. gate decided. on the other side."),
    8: ("new octave", "chorus opened. full, bright, groove locked. you are in it."),
    9: ("reset",      "beat changed completely. old pattern gone. board cleared."),
}

GAINS_FILE = os.path.join(os.path.dirname(__file__), 'gains.json')
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

SAMPLERATE = 48000
BLOCKSIZE  = 2048
HISTORY_S  = 4.0
HIST_LEN   = int(HISTORY_S * SAMPLERATE / BLOCKSIZE)

rms_history      = collections.deque([0.0] * HIST_LEN, maxlen=HIST_LEN)
centroid_history = collections.deque([0.0] * HIST_LEN, maxlen=HIST_LEN)
onset_history    = collections.deque([0.0] * HIST_LEN, maxlen=HIST_LEN)
period_history   = collections.deque([0.0] * HIST_LEN, maxlen=HIST_LEN)

def spectral_centroid_f(chunk, sr):
    win   = chunk * np.hanning(len(chunk))
    mag   = np.abs(np.fft.rfft(win))
    freqs = np.fft.rfftfreq(len(chunk), 1.0 / sr)
    total = mag.sum()
    if total < 1e-10:
        return 0.0
    return float(np.dot(freqs, mag) / total)

def spectral_flatness_f(chunk):
    win = chunk * np.hanning(len(chunk))
    mag = np.abs(np.fft.rfft(win)) + 1e-10
    gm  = np.exp(np.mean(np.log(mag)))
    am  = np.mean(mag)
    return float(gm / am)

def periodicity_f(rms_buf):
    arr = np.array(rms_buf)
    arr = arr - arr.mean()
    if arr.std() < 1e-6:
        return 0.0
    corr = np.correlate(arr, arr, mode='full')
    corr = corr[len(corr)//2:]
    corr /= corr[0] + 1e-10
    lo = int(0.1 * SAMPLERATE / BLOCKSIZE)
    hi = min(int(1.5 * SAMPLERATE / BLOCKSIZE), len(corr) - 1)
    if lo >= hi:
        return 0.0
    return float(corr[lo:hi].max())

def onset_density_f(onset_buf):
    arr    = np.array(onset_buf)
    diffs  = np.diff(arr)
    thresh = arr.mean() * 0.3
    return float((diffs > thresh).sum() / max(len(diffs), 1))

def rms_trend_f(rms_buf):
    arr = np.array(list(rms_buf)[-int(2.0 * SAMPLERATE / BLOCKSIZE):])
    if len(arr) < 4:
        return 0.0
    x = np.arange(len(arr), dtype=float)
    return float(np.polyfit(x, arr, 1)[0])

def stability_f(rms_buf):
    arr = np.array(list(rms_buf)[-int(2.0 * SAMPLERATE / BLOCKSIZE):])
    if len(arr) < 2:
        return 0.0
    cv = arr.std() / (arr.mean() + 1e-10)
    return float(1.0 / (1.0 + cv * 10))

def features_to_weight(f, gains):
    def G(n): return float(gains.get(str(n), 1.0))
    rms = f['rms']; trend = f['trend']; flat = f['flatness']
    centroid = f['centroid']; period = f['periodicity']
    onsets = f['onsets']; stable = f['stability']
    pdelta = f.get('period_delta', 0.0)

    if rms < 0.0003 * G(0): return 0
    if (onsets > 0.39 * G(9) and stable < 0.31 and pdelta > 0.12) or \
       (trend > 0.004 * G(9) and rms > 0.05 and onsets > 0.39 and stable < 0.31):
        return 9
    if rms > 0.12 * G(5) and flat > 0.28: return 5
    if (rms > 0.04 * G(8) and stable > 0.23 and flat < 0.22
            and centroid > 1200 and period > 0.28 and abs(trend) < 0.003):
        return 8
    if trend > 0.001 * G(4) and onsets < 0.28 and flat < 0.25: return 4
    if rms > 0.002 * G(1) and 0.15 < period < 0.40 and stable < 0.25 and flat < 0.28: return 1
    if period > 0.30 * G(3) and centroid < 2800 and rms > 0.005: return 3
    if stable > 0.50 * G(6) and flat < 0.18 and 600 < centroid < 4500: return 6
    if period > 0.31 * G(7) and stable > 0.15 and stable < 0.20 and rms < 0.06: return 7
    if rms > 0.003 * G(2) and flat < 0.25: return 2
    return 1

_eleanor_count = 0
_eleanor_state = ('silent', 'dim')
ELEANOR_HOLD   = 3

def eleanor_report(f):
    global _eleanor_count, _eleanor_state
    period = f.get('periodicity', 0.0)
    stable = f.get('stability',   0.0)
    flat   = f.get('flatness',    1.0)
    rms    = f.get('rms',         0.0)
    if rms < 0.0003:
        _eleanor_state = ('silent', 'dim')
        _eleanor_count = 0
        return _eleanor_state
    too_periodic = period > 0.40
    too_stable   = stable  > 0.32
    too_tonal    = flat    < 0.12
    n = sum([too_periodic, too_stable, too_tonal])
    new = ('warning — too clean', 'red') if n >= 2 else \
          ('mild',                'yellow') if n == 1 else \
          ('clear',               'green')
    if new == _eleanor_state:
        _eleanor_count = 0
    else:
        _eleanor_count += 1
        if _eleanor_count >= ELEANOR_HOLD:
            _eleanor_state = new
            _eleanor_count = 0
    return _eleanor_state

state = {
    'weight':       0,
    'rms':          0.0,
    'features':     {},
    'waveform':     [0.0] * 48,
    'history':      collections.deque(maxlen=14),
    'stable_n':     0,
    'prev_w':       0,
    'gains':        load_gains(),
    'selected':     None,
    'saved':        False,
    'running':      True,
    'eli':          Eli(),
    'genesis':      Genesis(),
    'eleanor_msg':  'silent',
    'eleanor_color':'dim',
}

STABLE_MIN = 4

def audio_reader():
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
        flat = spectral_flatness_f(chunk)
        sc   = spectral_centroid_f(chunk, SAMPLERATE)
        rms_history.append(rms)
        centroid_history.append(sc)
        onset_history.append(rms)
        period_history.append(periodicity_f(rms_history))
        ph    = list(period_history)
        p_now = ph[-1] if ph else 0.0
        p_idx = int(2.0 * SAMPLERATE / BLOCKSIZE)
        p_old = ph[-p_idx] if len(ph) >= p_idx else p_now
        f = {
            'rms':          rms,
            'trend':        rms_trend_f(rms_history),
            'flatness':     flat,
            'centroid':     sc,
            'periodicity':  p_now,
            'period_delta': abs(p_now - p_old),
            'onsets':       onset_density_f(onset_history),
            'stability':    stability_f(rms_history),
        }
        w = features_to_weight(f, state['gains'])
        em, ec = eleanor_report(f)
        state['rms']          = rms
        state['weight']       = w
        state['features']     = f
        state['eleanor_msg']  = em
        state['eleanor_color']= ec
        step = max(1, len(chunk) // 48)
        state['waveform'] = [
            abs(float(chunk[i * step])) if i * step < len(chunk) else 0.0
            for i in range(48)
        ]
        if w == state['prev_w']:
            state['stable_n'] += 1
        else:
            if state['stable_n'] >= STABLE_MIN and state['prev_w'] != 0:
                name = MEANINGS.get(state['prev_w'], ('?',))[0]
                state['history'].append({'w': state['prev_w'], 'name': name, 'rms': rms})
            state['prev_w']  = w
            state['stable_n'] = 0
    proc.terminate()

def test_data_generator():
    t = 0.0
    while state['running']:
        t += 0.083
        w = int((t / 3) % 10)
        rms = 0.05 + 0.03 * math.sin(t * 0.7)
        f = {
            'rms': rms, 'trend': 0.001 * math.sin(t * 0.3),
            'flatness': 0.15 + 0.05 * math.sin(t * 0.5),
            'centroid': 2000 + 500 * math.sin(t * 0.2),
            'periodicity': 0.3 + 0.1 * math.sin(t * 0.4),
            'period_delta': 0.05, 'onsets': 0.2, 'stability': 0.4,
        }
        state['weight'] = w
        state['rms']    = rms
        state['features'] = f
        state['eleanor_msg']   = 'clear'
        state['eleanor_color'] = 'green'
        state['waveform'] = [abs(math.sin(t * 8 + i * 0.4) * rms * 3) for i in range(48)]
        time.sleep(0.083)

def handle_command(msg):
    cmd = msg.get('cmd')
    if cmd == 'select':
        state['selected'] = msg.get('n')
    elif cmd == 'gain_up' and state['selected'] is not None:
        k = str(state['selected'])
        state['gains'][k] = round(state['gains'].get(k, 1.0) * 1.15, 4)
    elif cmd == 'gain_down' and state['selected'] is not None:
        k = str(state['selected'])
        state['gains'][k] = round(state['gains'].get(k, 1.0) * 0.87, 4)
    elif cmd == 'set_gain':
        k = str(msg.get('n', state['selected'] or 0))
        v = float(msg.get('value', 1.0))
        state['gains'][k] = round(max(0.1, min(5.0, v)), 4)
    elif cmd == 'save':
        save_gains(state['gains'])
        state['saved'] = True
        threading.Timer(1.5, lambda: state.update({'saved': False})).start()

def get_snapshot():
    e = state['eli']
    wav  = state['waveform']
    peak = max(max(wav) if wav else 1, 0.001)
    f    = state.get('features', {})
    return {
        'weight':        state['weight'],
        'weight_name':   MEANINGS.get(state['weight'], ('?', ''))[0],
        'weight_desc':   MEANINGS.get(state['weight'], ('?', ''))[1],
        'rms':           round(state['rms'], 6),
        'features':      {k: round(v, 5) for k, v in f.items()},
        'waveform':      [round(v / peak, 4) for v in wav],
        'history':       list(state['history']),
        'gains':         state['gains'],
        'selected':      state['selected'],
        'saved':         state['saved'],
        'eleanor_msg':   state['eleanor_msg'],
        'eleanor_color': state['eleanor_color'],
        'eli': {
            'loop_active':       e.loop_active,
            'playing':           e.playing,
            'override_eleanor':  e.override_eleanor,
            'trust':             e.trust,
        },
    }

app = FastAPI()

@app.get('/', response_class=HTMLResponse)
async def index():
    return HTMLResponse(content=HTML)

@app.websocket('/ws')
async def ws_endpoint(ws: WebSocket):
    await ws.accept()

    async def reader():
        try:
            while True:
                msg = await ws.receive_json()
                handle_command(msg)
        except Exception:
            pass

    reader_task = asyncio.create_task(reader())
    try:
        while True:
            await ws.send_json(get_snapshot())
            await asyncio.sleep(0.083)
    except Exception:
        pass
    finally:
        reader_task.cancel()

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>mishmaath</title>
<style>
:root {
  --bg:      #07090f;
  --panel:   #0c0f1a;
  --border:  #151c2e;
  --cyan:    #00d4ff;
  --magenta: #cc00ff;
  --yellow:  #ffcc00;
  --green:   #00ff88;
  --red:     #ff2244;
  --orange:  #ff8844;
  --white:   #e8eeff;
  --dim:     #1e2540;
  --text:    #b0bcd8;
  --muted:   #4a5470;
  --font:    'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden}
body{background:var(--bg);color:var(--text);font-family:var(--font);font-size:12px;
  display:grid;grid-template-rows:38px 1fr}

header{display:flex;align-items:center;padding:0 14px;gap:10px;
  background:var(--panel);border-bottom:1px solid var(--border)}
.logo{font-size:13px;font-weight:700;color:var(--cyan);letter-spacing:4px}
.dot{width:7px;height:7px;border-radius:50%;background:var(--dim);transition:background .4s}
.dot.live{background:var(--green);box-shadow:0 0 8px var(--green)}
.dot.err{background:var(--red)}
.hstatus{font-size:10px;color:var(--muted)}
.saved{margin-left:auto;font-size:10px;color:var(--green);opacity:0;transition:opacity .3s}
.saved.show{opacity:1}
.hints{margin-left:auto;font-size:10px;color:var(--muted)}

.grid{display:grid;grid-template-columns:190px 1fr 210px;height:100%;overflow:hidden}

.col{display:flex;flex-direction:column;border-right:1px solid var(--border);overflow:hidden}
.col:last-child{border-right:none}

.ptitle{padding:7px 11px 5px;font-size:9px;font-weight:700;color:var(--muted);
  letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid var(--border);flex-shrink:0}

/* === LEFT: schema list === */
.schema-scroll{flex:1;overflow-y:auto;scrollbar-width:none}
.srow{display:flex;align-items:center;gap:7px;padding:5px 10px;cursor:pointer;
  border-bottom:1px solid transparent;transition:background .12s}
.srow:hover{background:rgba(0,212,255,.04)}
.srow.active{background:rgba(0,212,255,.07);border-bottom-color:var(--dim)}
.srow.sel{background:rgba(204,0,255,.07)}
.srow.active.sel{background:rgba(80,80,220,.08)}
.snum{width:16px;text-align:right;font-size:14px;font-weight:700;color:var(--muted);flex-shrink:0}
.srow.active .snum{color:var(--cyan)}
.srow.sel    .snum{color:var(--magenta)}
.sname{flex:1;font-size:11px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.srow.active .sname{color:var(--text)}
.sgain{font-size:10px;color:var(--muted);width:38px;text-align:right;flex-shrink:0}
.srow.sel    .sgain{color:var(--magenta)}
.srow.active .sgain{color:var(--green)}
.smark{width:8px;text-align:center;font-size:10px;color:var(--yellow);flex-shrink:0}

.gain-bar{flex:1;height:3px;background:var(--dim);border-radius:1px;overflow:hidden;max-width:40px}
.gain-fill{height:100%;background:var(--cyan);border-radius:1px;transition:width .15s}

.gcontrols{padding:9px 10px;border-top:1px solid var(--border);
  display:flex;gap:7px;align-items:center;flex-shrink:0}
.gbtn{background:var(--dim);border:1px solid var(--border);color:var(--text);
  padding:3px 11px;cursor:pointer;font-family:var(--font);font-size:15px;
  border-radius:2px;transition:all .12s;line-height:1.2}
.gbtn:hover{background:rgba(0,212,255,.15);border-color:var(--cyan);color:var(--cyan)}
.gbtn:active{transform:scale(.95)}
.greset{font-size:10px;color:var(--muted);cursor:pointer;margin-left:auto}
.greset:hover{color:var(--yellow)}

/* === CENTER === */
.center{border-right:1px solid var(--border)}

.wave-wrap{height:72px;flex-shrink:0;border-bottom:1px solid var(--border);background:var(--bg)}
canvas{display:block;width:100%;height:100%}

.hero{display:flex;flex-direction:column;align-items:center;justify-content:center;
  padding:18px 16px;border-bottom:1px solid var(--border);flex-shrink:0;
  position:relative;min-height:130px}
.hrms{position:absolute;top:9px;right:11px;font-size:10px;color:var(--muted)}
.hnum{font-size:72px;font-weight:700;line-height:1;color:var(--cyan);
  text-shadow:0 0 40px rgba(0,212,255,.35);transition:color .25s,text-shadow .25s}
.hname{font-size:17px;font-weight:600;color:var(--white);margin-top:3px;letter-spacing:1px}
.hdesc{font-size:10px;color:var(--muted);margin-top:5px;text-align:center;
  max-width:380px;line-height:1.55}

/* weight color overrides */
.w0 .hnum{color:#2a3060;text-shadow:none}
.w1 .hnum{color:#8888ee}
.w2 .hnum{color:var(--cyan)}
.w3 .hnum{color:var(--green)}
.w4 .hnum{color:var(--yellow)}
.w5 .hnum{color:var(--red);text-shadow:0 0 24px rgba(255,34,68,.45)}
.w6 .hnum{color:var(--orange)}
.w7 .hnum{color:var(--green)}
.w8 .hnum{color:#ffffff;text-shadow:0 0 50px rgba(255,255,255,.55)}
.w9 .hnum{color:var(--magenta);text-shadow:0 0 24px rgba(204,0,255,.4)}

@keyframes weight-pop{0%{transform:scale(1)}40%{transform:scale(1.06)}100%{transform:scale(1)}}
.hnum.pop{animation:weight-pop .25s ease}

.feats{flex:1;overflow-y:auto;scrollbar-width:none;padding:9px 12px;
  display:flex;flex-direction:column;gap:4px}
.frow{display:flex;align-items:center;gap:8px;height:17px}
.flabel{width:66px;font-size:10px;color:var(--muted);flex-shrink:0}
.ftrack{flex:1;height:3px;background:var(--dim);border-radius:2px;overflow:hidden}
.ffill{height:100%;border-radius:2px;background:var(--cyan);transition:width .1s ease}
.fval{width:68px;text-align:right;font-size:10px;color:var(--muted)}

/* === RIGHT === */
.epanel{padding:8px 11px;border-bottom:1px solid var(--border);flex-shrink:0}
.estatus{font-size:11px;padding:5px 8px;border-radius:3px;margin-top:6px;
  background:rgba(0,255,136,.07);color:var(--green);transition:all .3s}
.estatus.y{background:rgba(255,204,0,.07);color:var(--yellow)}
.estatus.r{background:rgba(255,34,68,.09);color:var(--red)}
.estatus.d{background:transparent;color:var(--muted)}
.edetail{margin-top:4px;display:flex;gap:9px;font-size:10px;color:var(--muted)}

.elipanel{padding:8px 11px;border-bottom:1px solid var(--border);flex-shrink:0}
.erow{display:flex;justify-content:space-between;align-items:center;
  padding:3px 0;font-size:11px;border-bottom:1px solid var(--dim)}
.erow:last-child{border-bottom:none}
.ekey{color:var(--muted)}
.eval{font-weight:600}
.on{color:var(--green)}
.off{color:var(--red)}
.neu{color:var(--text)}

.hpanel{flex:1;overflow-y:auto;scrollbar-width:none}
.hrow{display:flex;align-items:center;gap:7px;padding:4px 11px;
  border-bottom:1px solid var(--dim);font-size:11px}
.hw{width:18px;font-weight:700;color:var(--cyan);text-align:right}
.hn{flex:1;color:var(--muted)}
.hr{font-size:10px;color:var(--muted)}
@keyframes fadein{from{opacity:0;transform:translateX(6px)}to{opacity:1;transform:none}}
.hrow{animation:fadein .25s ease}

/* loading overlay */
#loading{position:fixed;inset:0;background:var(--bg);display:flex;
  flex-direction:column;align-items:center;justify-content:center;gap:14px;z-index:99;
  transition:opacity .4s}
#loading.gone{opacity:0;pointer-events:none}
.llogo{font-size:22px;font-weight:700;color:var(--cyan);letter-spacing:6px}
.lsub{font-size:10px;color:var(--muted)}
.spin{width:22px;height:22px;border:2px solid var(--dim);border-top-color:var(--cyan);
  border-radius:50%;animation:rot .7s linear infinite}
@keyframes rot{to{transform:rotate(360deg)}}

::-webkit-scrollbar{width:3px}
::-webkit-scrollbar-thumb{background:var(--dim)}
</style>
</head>
<body>

<div id="loading">
  <div class="llogo">MISHMAATH</div>
  <div class="spin"></div>
  <div class="lsub">connecting to schema runtime…</div>
</div>

<header>
  <span class="logo">mishmaath</span>
  <div class="dot" id="dot"></div>
  <span class="hstatus" id="hstatus">disconnected</span>
  <span class="saved" id="saved">✓ SAVED</span>
  <span class="hints">0–9 select · +/− gain · S save · R reset</span>
</header>

<div class="grid">

  <!-- LEFT -->
  <div class="col">
    <div class="ptitle">schema weights</div>
    <div class="schema-scroll" id="slist" role="listbox" aria-label="Schema weights"></div>
    <div class="gcontrols">
      <button class="gbtn" id="bminus" aria-label="Decrease gain">−</button>
      <button class="gbtn" id="bplus"  aria-label="Increase gain">+</button>
      <span class="greset" id="breset" role="button" tabindex="0" aria-label="Reset gain to 1.0">reset</span>
    </div>
  </div>

  <!-- CENTER -->
  <div class="col center">
    <div class="wave-wrap"><canvas id="wv" aria-label="Audio waveform"></canvas></div>
    <div class="hero w0" id="hero" role="status" aria-live="polite" aria-atomic="true">
      <span class="hrms" id="hrms">rms 0.00000</span>
      <div class="hnum" id="hnum">0</div>
      <div class="hname" id="hname">void</div>
      <div class="hdesc" id="hdesc">before sound, before thought. the ground that holds everything else.</div>
    </div>
    <div class="feats" id="feats"></div>
  </div>

  <!-- RIGHT -->
  <div class="col">
    <div class="epanel">
      <div class="ptitle" style="padding:0 0 5px;border:none">eleanor</div>
      <div class="estatus" id="estatus" aria-live="polite">silent</div>
      <div class="edetail">
        <span id="ep">p 0.00</span>
        <span id="es">s 0.00</span>
        <span id="ef">f 0.00</span>
      </div>
    </div>
    <div class="elipanel">
      <div class="ptitle" style="padding:0 0 5px;border:none">eli</div>
      <div id="elirows"></div>
    </div>
    <div class="ptitle">history</div>
    <div class="hpanel" id="hist" role="log" aria-live="polite" aria-label="Schema weight history"></div>
  </div>

</div>

<script>
const M = {
  0:["void",      "before sound, before thought. the ground that holds everything else."],
  1:["source",    "forming. groove hinting. contains what it's becoming."],
  2:["speak",     "the melody is present. calm, tonal. nothing unresolved."],
  3:["divine",    "rhythm locked. harmony in agreement. God-shaped foundation."],
  4:["door",      "anticipation. the solo is loading. no exit yet."],
  5:["friction",  "peak chaos. loud and turbulent. the unavoidable decision."],
  6:["comfort",   "the hook landed. recognition. you are inside it now."],
  7:["settled",   "I've got this. gate decided. on the other side."],
  8:["new octave","chorus opened. full, bright, groove locked. you are in it."],
  9:["reset",     "beat changed completely. old pattern gone. board cleared."],
};

const FDEFS = [
  {k:'rms',         lbl:'rms',      lo:0,     hi:0.3,  col:'#00d4ff'},
  {k:'trend',       lbl:'trend',    lo:0,     hi:0.01, col:'#00ff88', signed:true},
  {k:'flatness',    lbl:'noise',    lo:0,     hi:1,    col:'#ff2244'},
  {k:'centroid',    lbl:'centroid', lo:0,     hi:8000, col:'#ffcc00'},
  {k:'periodicity', lbl:'groove',   lo:0,     hi:1,    col:'#ffcc00'},
  {k:'onsets',      lbl:'onsets',   lo:0,     hi:1,    col:'#00d4ff'},
  {k:'stability',   lbl:'stable',   lo:0,     hi:1,    col:'#cc00ff'},
  {k:'period_delta',lbl:'g.shift',  lo:0,     hi:0.3,  col:'#ff2244'},
];

let ws, selected=null, prevWeight=-1, lastHistLen=0;

function buildSchema(){
  const el=document.getElementById('slist');
  for(let n=0;n<=9;n++){
    const r=document.createElement('div');
    r.className='srow'; r.id='sr'+n;
    r.setAttribute('role','option'); r.tabIndex=0;
    r.setAttribute('aria-label','Weight '+n+': '+M[n][0]);
    r.innerHTML=
      '<span class="snum" id="sn'+n+'">'+n+'</span>'+
      '<span class="sname">'+M[n][0]+'</span>'+
      '<span class="sgain" id="sg'+n+'">x1.00</span>'+
      '<span class="smark" id="sm'+n+'">&nbsp;</span>';
    r.onclick=()=>doSelect(n);
    r.onkeydown=e=>{if(e.key==='Enter'||e.key===' ')doSelect(n)};
    el.appendChild(r);
  }
}

function buildFeats(){
  const el=document.getElementById('feats');
  FDEFS.forEach(d=>{
    const r=document.createElement('div');
    r.className='frow';
    r.innerHTML=
      '<span class="flabel">'+d.lbl+'</span>'+
      '<div class="ftrack"><div class="ffill" id="fb'+d.k+'" style="width:0%;background:'+d.col+'"></div></div>'+
      '<span class="fval" id="fv'+d.k+'">0</span>';
    el.appendChild(r);
  });
}

function buildEli(){
  const defs=[
    ['loop',    'loop_active',      v=>v?'ACTIVE':'SUSPENDED', v=>v?'on':'off'],
    ['playing', 'playing',          v=>v?'yes':'no',           v=>v?'on':'off'],
    ['eleanor', 'override_eleanor', v=>v?'overridden':'listening', v=>!v?'on':'off'],
    ['trust',   'trust',            v=>String(v),              ()=>'neu'],
  ];
  const el=document.getElementById('elirows');
  defs.forEach(([lbl,k])=>{
    const r=document.createElement('div');
    r.className='erow';
    r.innerHTML='<span class="ekey">'+lbl+'</span><span class="eval" id="ei'+k+'">—</span>';
    el.appendChild(r);
  });
  window._eliDefs=defs;
}

function update(s){
  const w=s.weight;

  // hero
  if(w!==prevWeight){
    const n=document.getElementById('hnum');
    n.classList.remove('pop');
    void n.offsetWidth;
    n.classList.add('pop');
    prevWeight=w;
  }
  document.getElementById('hero').className='hero w'+w;
  document.getElementById('hnum').textContent=w;
  document.getElementById('hname').textContent=s.weight_name;
  document.getElementById('hdesc').textContent=s.weight_desc;
  document.getElementById('hrms').textContent='rms '+(s.rms).toFixed(5);

  // schema rows
  for(let n=0;n<=9;n++){
    const r=document.getElementById('sr'+n);
    r.classList.toggle('active',n===w);
    r.classList.toggle('sel',n===selected);
    document.getElementById('sm'+n).textContent=n===w?'◄':'\xa0';
    const g=s.gains[String(n)]||1.0;
    document.getElementById('sg'+n).textContent='x'+g.toFixed(2);
  }

  // features
  const f=s.features||{};
  FDEFS.forEach(d=>{
    const v=f[d.k]||0;
    let pct, lbl;
    if(d.signed){
      const av=Math.abs(v);
      pct=Math.min(100,(av/d.hi)*100);
      const fill=document.getElementById('fb'+d.k);
      fill.style.background=v>0.0002?'#00ff88':(v<-0.0002?'#ff2244':'#2a3050');
      lbl=(v>=0?'+':'')+v.toFixed(5);
    } else {
      pct=Math.max(0,Math.min(100,(v/d.hi)*100));
      lbl=d.k==='centroid'?Math.round(v)+'Hz':v.toFixed(3);
    }
    document.getElementById('fb'+d.k).style.width=pct.toFixed(1)+'%';
    document.getElementById('fv'+d.k).textContent=lbl;
  });

  // eleanor
  const es=document.getElementById('estatus');
  es.textContent=s.eleanor_msg;
  es.className='estatus '+({green:'',yellow:'y',red:'r',dim:'d'}[s.eleanor_color]||'d');
  document.getElementById('ep').textContent='p '+(f.periodicity||0).toFixed(2);
  document.getElementById('es').textContent='s '+(f.stability||0).toFixed(2);
  document.getElementById('ef').textContent='f '+(f.flatness||0).toFixed(2);

  // eli
  const e=s.eli;
  window._eliDefs.forEach(([,k,,cls])=>{
    const el=document.getElementById('ei'+k);
    if(!el)return;
    const lbl=window._eliDefs.find(d=>d[1]===k);
    el.textContent=lbl[2](e[k]);
    el.className='eval '+lbl[3](e[k]);
  });

  // history
  if(s.history.length!==lastHistLen){
    lastHistLen=s.history.length;
    const hp=document.getElementById('hist');
    hp.innerHTML='';
    [...s.history].reverse().forEach(h=>{
      const r=document.createElement('div');
      r.className='hrow';
      r.innerHTML='<span class="hw">'+h.w+'</span><span class="hn">'+h.name+'</span><span class="hr">'+((h.rms||0).toFixed(4))+'</span>';
      hp.appendChild(r);
    });
  }

  // saved
  document.getElementById('saved').classList.toggle('show',s.saved);

  // waveform
  drawWave(s.waveform);
}

// canvas
const cv=document.getElementById('wv');
const cx=cv.getContext('2d');

function drawWave(data){
  const W=cv.offsetWidth,H=cv.offsetHeight;
  if(cv.width!==W||cv.height!==H){cv.width=W;cv.height=H}
  cx.clearRect(0,0,W,H);
  if(!data||!data.length)return;
  const step=W/data.length;
  cx.beginPath();
  cx.moveTo(0,H);
  data.forEach((v,i)=>cx.lineTo(i*step,H-v*H*0.88));
  cx.lineTo(W,H);
  cx.closePath();
  const g=cx.createLinearGradient(0,0,0,H);
  g.addColorStop(0,'rgba(0,212,255,.75)');
  g.addColorStop(1,'rgba(0,212,255,.04)');
  cx.fillStyle=g;
  cx.fill();
  cx.beginPath();
  data.forEach((v,i)=>i?cx.lineTo(i*step,H-v*H*0.88):cx.moveTo(0,H-v*H*0.88));
  cx.strokeStyle='rgba(0,212,255,.85)';
  cx.lineWidth=1.5;
  cx.stroke();
}

// websocket
function connect(){
  const proto=location.protocol==='https:'?'wss':'ws';
  ws=new WebSocket(proto+'://'+location.host+'/ws');
  ws.onopen=()=>{
    document.getElementById('dot').className='dot live';
    document.getElementById('hstatus').textContent='connected';
    setTimeout(()=>document.getElementById('loading').classList.add('gone'),300);
  };
  ws.onclose=()=>{
    document.getElementById('dot').className='dot err';
    document.getElementById('hstatus').textContent='disconnected — retrying…';
    setTimeout(connect,2000);
  };
  ws.onerror=()=>document.getElementById('dot').className='dot err';
  ws.onmessage=e=>{try{update(JSON.parse(e.data))}catch(err){console.error(err)}};
}

function send(obj){if(ws&&ws.readyState===1)ws.send(JSON.stringify(obj))}

function doSelect(n){
  selected=selected===n?null:n;
  send({cmd:'select',n:selected});
  for(let i=0;i<=9;i++)document.getElementById('sr'+i).classList.toggle('sel',i===selected);
}

document.getElementById('bminus').onclick=()=>send({cmd:'gain_down'});
document.getElementById('bplus').onclick= ()=>send({cmd:'gain_up'});
document.getElementById('breset').onclick=()=>{
  if(selected!==null)send({cmd:'set_gain',n:selected,value:1.0});
};
document.getElementById('breset').onkeydown=e=>{
  if(e.key==='Enter'||e.key===' ')document.getElementById('breset').onclick();
};

document.addEventListener('keydown',e=>{
  if(e.target.tagName==='INPUT')return;
  if(e.key>='0'&&e.key<='9'){doSelect(parseInt(e.key));return}
  if(e.key==='+'||e.key==='='){send({cmd:'gain_up'});return}
  if(e.key==='-'){send({cmd:'gain_down'});return}
  if(e.key==='s'||e.key==='S'){send({cmd:'save'});return}
  if(e.key==='r'||e.key==='R'){
    if(selected!==null)send({cmd:'set_gain',n:selected,value:1.0});
  }
});

buildSchema();
buildFeats();
buildEli();
connect();
</script>
</body>
</html>"""

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='mishmaath web dashboard')
    ap.add_argument('--host',     default='0.0.0.0')
    ap.add_argument('--port',     type=int, default=8765)
    ap.add_argument('--no-audio', action='store_true', help='use test data instead of parec')
    args = ap.parse_args()

    if args.no_audio:
        threading.Thread(target=test_data_generator, daemon=True).start()
        print(f'[mishmaath] test mode — open http://localhost:{args.port}')
    else:
        threading.Thread(target=audio_reader, daemon=True).start()
        print(f'[mishmaath] live audio — open http://localhost:{args.port}')

    uvicorn.run(app, host=args.host, port=args.port, log_level='warning')
