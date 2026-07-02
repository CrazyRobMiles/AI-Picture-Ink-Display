#!/usr/bin/env python3
"""
Simple web viewer for the AI e-ink picture frame.

Run with:
    python web_viewer.py

Then browse to:
    http://<pi-address>:8080/
"""

from __future__ import annotations

import json
import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, abort, jsonify, render_template_string, request, send_from_directory, url_for
from werkzeug.serving import make_server

import config
from image_catalog import IMAGE_EXTENSIONS
from sd_options import DEFAULT_SD_OPTIONS, OPTION_DEFS, OPTION_FLAGS

WEB_HOST = getattr(config, "WEB_VIEWER_HOST", "0.0.0.0")
WEB_PORT = getattr(config, "WEB_VIEWER_PORT", 8080)
PROMPT_LOG_NAME = "prompt_log.txt"
CONFIG_FILE = Path(__file__).parent / "config.json"

_restart_event: Optional[threading.Event] = None
_command_queue: Optional[queue.Queue] = None


def set_restart_event(event: Optional[threading.Event]) -> None:
    global _restart_event
    _restart_event = event


def set_command_queue(q: Optional[queue.Queue]) -> None:
    global _command_queue
    _command_queue = q


@dataclass(frozen=True)
class ImageEntry:
    index: int
    filename: str
    caption: str
    created: str


def strip_outer_quotes(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ('"', "'"):
        return text[1:-1]
    return text


def load_captions(image_dir: Path) -> Dict[str, Dict[str, str]]:
    """Load prompt_log.txt entries keyed by image filename."""
    captions: Dict[str, Dict[str, str]] = {}
    log_path = image_dir / PROMPT_LOG_NAME

    if not log_path.exists():
        return captions

    try:
        with log_path.open("r", encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split(" | ", 2)
                if len(parts) != 3:
                    continue
                created, filename, prompt = parts
                captions[filename] = {
                    "created": created,
                    "caption": strip_outer_quotes(prompt),
                }
    except OSError:
        return captions

    return captions


def scan_images(image_dir: Path) -> List[Path]:
    if not image_dir.exists():
        return []
    images = [
        path for path in image_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    images.sort()
    return images


def get_entries() -> List[ImageEntry]:
    captions = load_captions(config.IMAGE_DIR)
    images = scan_images(config.IMAGE_DIR)
    entries: List[ImageEntry] = []
    for index, path in enumerate(images):
        meta = captions.get(path.name, {})
        entries.append(ImageEntry(
            index=index,
            filename=path.name,
            caption=meta.get("caption", path.stem),
            created=meta.get("created", ""),
        ))
    return entries


def load_config() -> dict:
    """Load config.json, returning defaults if the file is missing or unreadable."""
    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "DISPLAY_TYPE": config.DISPLAY_TYPE,
        "INPUT_TYPE": config.INPUT_TYPE,
        "PROMPT_BANKS": {},
        "PROMPT_TEMPLATES": [],
        "GLOBAL_QUALITY_HINT": "",
        "SD_OPTIONS": dict(DEFAULT_SD_OPTIONS),
    }


app = Flask(__name__)

PAGE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Picture Frame</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #111;
      --panel: #1b1b1b;
      --text: #f2f2f2;
      --muted: #aaa;
      --button: #333;
      --button-hover: #444;
      --input-bg: #222;
      --border: #333;
      --ok: #4caf50;
      --err: #f44336;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      background: var(--bg);
      color: var(--text);
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    header {
      padding: 0.75rem 1rem;
      background: var(--panel);
      display: flex;
      align-items: center;
      gap: 1rem;
      flex-shrink: 0;
    }

    h1 {
      margin: 0;
      font-size: 1.1rem;
      font-weight: 650;
    }

    .tabs { display: flex; gap: 0.25rem; }

    .tab-btn {
      padding: 0.35rem 0.9rem;
      border: 1px solid var(--border);
      border-radius: 0.4rem;
      background: transparent;
      color: var(--muted);
      cursor: pointer;
      font: inherit;
      font-size: 0.9rem;
    }

    .tab-btn.active {
      background: var(--button);
      color: var(--text);
      border-color: #555;
    }

    .tab-btn:hover:not(.active) {
      background: var(--button);
      color: var(--text);
    }

    #counter {
      margin-left: auto;
      color: var(--muted);
      font-size: 0.9rem;
    }

    /* ---- Gallery view ---- */

    #view-gallery {
      flex: 1;
      display: flex;
      flex-direction: column;
      min-height: 0;
    }

    main {
      flex: 1;
      display: grid;
      grid-template-rows: minmax(0, 1fr) auto;
      gap: 0.75rem;
      padding: 1rem;
    }

    .image-wrap {
      min-height: 0;
      display: flex;
      justify-content: center;
      align-items: center;
    }

    img {
      max-width: 100%;
      max-height: calc(100vh - 13rem);
      object-fit: contain;
      border-radius: 0.5rem;
      background: #000;
      box-shadow: 0 0 2rem rgba(0,0,0,0.45);
    }

    .caption {
      max-width: 72rem;
      margin: 0 auto;
      text-align: center;
      line-height: 1.4;
    }

    .caption p { margin: 0.25rem 0; }

    .meta { color: var(--muted); font-size: 0.9rem; }

    footer {
      padding: 0.75rem 1rem;
      background: var(--panel);
      flex-shrink: 0;
    }

    .controls {
      display: flex;
      justify-content: center;
      align-items: center;
      flex-wrap: wrap;
      gap: 0.75rem;
    }

    button, a.button {
      display: inline-block;
      min-width: 6rem;
      padding: 0.7rem 1rem;
      border: 0;
      border-radius: 0.5rem;
      background: var(--button);
      color: var(--text);
      text-decoration: none;
      text-align: center;
      font: inherit;
      cursor: pointer;
    }

    button:hover, a.button:hover { background: var(--button-hover); }

    #auto-follow.live { background: #2a6; color: #fff; }
    #auto-follow.live:hover { background: #3b7; }

    /* Live / fullscreen mode */
    :fullscreen header,
    :fullscreen footer,
    :fullscreen .caption { display: none; }

    :fullscreen #view-gallery { height: 100vh; }

    :fullscreen main {
      padding: 0;
      grid-template-rows: 1fr;
    }

    :fullscreen img {
      max-height: 100vh;
      max-width: 100vw;
      border-radius: 0;
      box-shadow: none;
    }

    .empty {
      margin: auto;
      color: var(--muted);
      text-align: center;
      font-size: 1.1rem;
    }

    /* ---- Prompts view ---- */

    #view-prompts {
      flex: 1;
      overflow-y: auto;
      padding: 1.25rem 1rem 2rem;
    }

    .prompts-container {
      max-width: 64rem;
      margin: 0 auto;
    }

    .prompts-heading {
      margin: 0 0 0.2rem;
      font-size: 1rem;
      font-weight: 600;
    }

    .hint {
      color: var(--muted);
      font-size: 0.85rem;
      margin: 0 0 1.25rem;
    }

    .bank-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr));
      gap: 1rem;
      margin-bottom: 1rem;
    }

    .bank-section label,
    .full-row label {
      display: block;
      font-size: 0.85rem;
      font-weight: 600;
      text-transform: capitalize;
      color: var(--muted);
      margin-bottom: 0.35rem;
    }

    .bank-section textarea,
    .full-row textarea,
    .full-row input[type="text"] {
      width: 100%;
      background: var(--input-bg);
      border: 1px solid var(--border);
      border-radius: 0.4rem;
      color: var(--text);
      font: 0.88rem/1.5 monospace;
      padding: 0.5rem 0.6rem;
      resize: vertical;
    }

    .full-row {
      margin-bottom: 1rem;
    }

    .full-row input[type="text"] {
      font: inherit;
      padding: 0.5rem 0.6rem;
    }

    #header-save {
      margin-left: auto;
      min-width: 9rem;
      padding: 0.4rem 1rem;
      background: #2a6;
      color: #fff;
      border: 0;
      border-radius: 0.4rem;
      font: inherit;
      font-size: 0.9rem;
      cursor: pointer;
    }

    #header-save:hover { background: #3b7; }

    #save-status {
      font-size: 0.85rem;
      white-space: nowrap;
    }

    .save-ok  { color: var(--ok); }
    .save-err { color: var(--err); }

    /* ---- SD Options view ---- */

    #view-sd {
      flex: 1;
      overflow-y: auto;
      padding: 1.25rem 1rem 2rem;
    }

    .sd-options-container {
      max-width: 64rem;
      margin: 0 auto;
    }

    .sd-option-row {
      display: flex;
      align-items: flex-start;
      gap: 0.75rem;
      padding: 0.6rem 0;
      border-bottom: 1px solid var(--border);
    }

    .sd-option-row input[type="checkbox"] {
      margin-top: 0.3rem;
      flex-shrink: 0;
    }

    .sd-option-main { flex: 1; min-width: 0; }

    .sd-option-label {
      font-weight: 600;
      font-size: 0.92rem;
    }

    .sd-option-flag {
      color: var(--muted);
      font-size: 0.8rem;
      font-family: monospace;
    }

    .sd-option-help {
      color: var(--muted);
      font-size: 0.82rem;
      margin: 0.15rem 0 0.4rem;
    }

    .sd-option-value {
      width: 100%;
      max-width: 24rem;
      background: var(--input-bg);
      border: 1px solid var(--border);
      border-radius: 0.4rem;
      color: var(--text);
      font: inherit;
      padding: 0.4rem 0.6rem;
    }
  </style>
</head>
<body>

<header>
  <h1>AI Picture Frame</h1>
  <nav class="tabs">
    <button class="tab-btn active" id="tab-gallery">Gallery</button>
    <button class="tab-btn" id="tab-prompts">Prompts</button>
    <button class="tab-btn" id="tab-sd">Options</button>
  </nav>
  <button id="header-save" type="button" style="display:none">Save Settings</button>
  <span id="save-status"></span>
  <div id="counter" class="meta"></div>
</header>

<!-- Gallery view -->
<div id="view-gallery">
  <main id="app">
    <div class="empty">Loading images…</div>
  </main>
  <footer>
    <div class="controls">
      <button id="prev" type="button">&#9664; Previous</button>
      <button id="latest" type="button">Latest</button>
      <button id="next" type="button">Next &#9654;</button>
      <button id="auto-follow" type="button">Live</button>
    </div>
  </footer>
</div>

<!-- Prompts view -->
<div id="view-prompts" style="display:none">
  <div class="prompts-container">
    <p class="prompts-heading">Prompt Banks</p>
    <p class="hint">Each line is one option. Blank lines are ignored. Changes take effect on the next generated image.</p>

    <div class="bank-grid" id="bank-grid">
      <div class="empty">Loading&hellip;</div>
    </div>

    <div class="full-row">
      <label>Templates &mdash; <span style="font-weight:normal">use {subject}, {style}, {lighting}, {mood}, {detail}, {environment}</span></label>
      <textarea id="prompt-templates" rows="4" spellcheck="false"></textarea>
    </div>

    <div class="full-row">
      <label>Global Quality Hint &mdash; <span style="font-weight:normal">appended to every prompt</span></label>
      <input type="text" id="quality-hint" spellcheck="false">
    </div>
  </div>
</div>

<!-- SD Options view -->
<div id="view-sd" style="display:none">
  <div class="sd-options-container">

    <p class="prompts-heading">Application Settings</p>
    <p class="hint">These settings take effect after restarting the application.</p>

    <div class="sd-option-row">
      <div class="sd-option-main">
        <div class="sd-option-label">Display Type</div>
        <p class="sd-option-help">Output device. <strong>inky</strong> — Pimoroni e-ink display. <strong>hdmi</strong> — HDMI monitor via Pygame.</p>
        <select id="app-display-type" class="sd-option-value">
          <option value="inky">inky</option>
          <option value="hdmi">hdmi</option>
        </select>
      </div>
    </div>

    <div class="sd-option-row">
      <div class="sd-option-main">
        <div class="sd-option-label">Input Type</div>
        <p class="sd-option-help">Control method. <strong>buttons</strong> — Pimoroni GPIO buttons. <strong>keyboard</strong> — keyboard via Pygame (HDMI mode).</p>
        <select id="app-input-type" class="sd-option-value">
          <option value="buttons">buttons</option>
          <option value="keyboard">keyboard</option>
        </select>
      </div>
    </div>

    <div class="sd-option-row">
      <div class="sd-option-main">
        <div class="sd-option-label">Image Fit Mode</div>
        <p class="sd-option-help"><strong>Stretch</strong> — fill the display, may distort. <strong>Crop</strong> — fill without distortion, edges are cropped. <strong>Border</strong> — show whole image with coloured borders.</p>
        <select id="app-fit-mode" class="sd-option-value">
          <option value="stretch">Stretch</option>
          <option value="crop">Crop</option>
          <option value="contain">Border</option>
        </select>
      </div>
    </div>

    <div class="sd-option-row" id="bg-color-row">
      <div class="sd-option-main">
        <div class="sd-option-label">Border Colour</div>
        <p class="sd-option-help">Background colour used when fit mode is Border.</p>
        <input type="color" id="app-bg-color" value="#ffffff" style="width:4rem;height:2rem;padding:0.1rem;cursor:pointer;background:var(--input-bg);border:1px solid var(--border);border-radius:0.4rem">
      </div>
    </div>

    <hr style="border:0;border-top:1px solid var(--border);margin:1.5rem 0">

    <p class="prompts-heading">Stable Diffusion Options</p>
    <p class="hint">Enable an option and (if it takes one) set its value. Changes take effect on the next generated image.</p>

    <div id="sd-option-rows"><div class="empty">Loading&hellip;</div></div>
  </div>
</div>

<script>
  // ---- Gallery ----

  let currentIndex = null;
  let currentCount = 0;

  async function loadImage(index) {
    const target = index === null ? '/api/current' : `/api/image/${index}`;
    const response = await fetch(target, { cache: 'no-store' });

    if (response.status === 404) {
      document.getElementById('counter').textContent = '';
      document.getElementById('app').innerHTML = '<div class="empty">No generated images found yet.</div>';
      currentIndex = null;
      currentCount = 0;
      return;
    }

    const data = await response.json();
    currentIndex = data.index;
    currentCount = data.count;

    document.getElementById('counter').textContent = `${data.index + 1} of ${data.count}`;
    document.getElementById('app').innerHTML = `
      <div class="image-wrap">
        <img src="${data.image_url}?v=${encodeURIComponent(data.filename)}" alt="${escapeHtml(data.caption)}">
      </div>
      <div class="caption">
        <p>${escapeHtml(data.caption)}</p>
        <p class="meta">${escapeHtml(data.filename)}${data.created ? ' &middot; ' + escapeHtml(data.created) : ''}</p>
      </div>
    `;
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  let autoFollowTimer = null;

  function setAutoFollow(enabled) {
    if (autoFollowTimer) { clearInterval(autoFollowTimer); autoFollowTimer = null; }
    document.getElementById('auto-follow').classList.toggle('live', enabled);
    if (enabled) {
      loadImage(null);
      autoFollowTimer = setInterval(() => { if (activeTab === 'gallery') loadImage(null); }, 60000);
      document.documentElement.requestFullscreen().catch(() => {});
    } else {
      if (document.fullscreenElement) document.exitFullscreen();
    }
  }

  document.addEventListener('fullscreenchange', () => {
    if (!document.fullscreenElement) setAutoFollow(false);
  });

  document.getElementById('prev').addEventListener('click', () => {
    setAutoFollow(false);
    if (currentCount > 0) loadImage((currentIndex - 1 + currentCount) % currentCount);
  });
  document.getElementById('next').addEventListener('click', () => {
    setAutoFollow(false);
    if (currentCount > 0) loadImage((currentIndex + 1) % currentCount);
  });
  document.getElementById('latest').addEventListener('click', () => loadImage(null));
  document.getElementById('auto-follow').addEventListener('click', () => {
    setAutoFollow(!document.getElementById('auto-follow').classList.contains('live'));
  });

  document.addEventListener('keydown', (e) => {
    if (activeTab !== 'gallery') return;
    if (e.key === 'ArrowLeft') document.getElementById('prev').click();
    if (e.key === 'ArrowRight') document.getElementById('next').click();
    if (e.key === 'Home') document.getElementById('latest').click();
  });

  loadImage(null);

  // ---- Tab switching ----

  let activeTab = 'gallery';

  function switchTab(tab) {
    activeTab = tab;
    document.getElementById('tab-gallery').classList.toggle('active', tab === 'gallery');
    document.getElementById('tab-prompts').classList.toggle('active', tab === 'prompts');
    document.getElementById('tab-sd').classList.toggle('active', tab === 'sd');
    document.getElementById('view-gallery').style.display = tab === 'gallery' ? '' : 'none';
    document.getElementById('view-prompts').style.display = tab === 'prompts' ? '' : 'none';
    document.getElementById('view-sd').style.display = tab === 'sd' ? '' : 'none';
    document.getElementById('counter').style.display = tab === 'gallery' ? '' : 'none';
    document.getElementById('header-save').style.display = tab === 'gallery' ? 'none' : '';
  }

  document.getElementById('tab-gallery').addEventListener('click', () => switchTab('gallery'));
  document.getElementById('tab-prompts').addEventListener('click', () => switchTab('prompts'));
  document.getElementById('tab-sd').addEventListener('click', () => switchTab('sd'));

  // ---- Config (prompts + app settings + SD options) ----

  let sdOptionDefs = [];

  async function loadConfig() {
    const resp = await fetch('/api/config', { cache: 'no-store' });
    const data = await resp.json();
    const cfg = data.config;
    sdOptionDefs = data.sd_defs;

    // Populate prompt banks
    const grid = document.getElementById('bank-grid');
    grid.innerHTML = '';
    for (const [key, items] of Object.entries(cfg.PROMPT_BANKS || {})) {
      const section = document.createElement('div');
      section.className = 'bank-section';
      const lbl = document.createElement('label');
      lbl.textContent = key;
      const ta = document.createElement('textarea');
      ta.id = 'bank-' + key;
      ta.rows = 10;
      ta.spellcheck = false;
      ta.value = items.join('\\n');
      section.appendChild(lbl);
      section.appendChild(ta);
      grid.appendChild(section);
    }

    document.getElementById('prompt-templates').value = (cfg.PROMPT_TEMPLATES || []).join('\\n');
    document.getElementById('quality-hint').value = cfg.GLOBAL_QUALITY_HINT || '';

    // Populate app settings
    document.getElementById('app-display-type').value = cfg.DISPLAY_TYPE || 'inky';
    document.getElementById('app-input-type').value = cfg.INPUT_TYPE || 'buttons';
    document.getElementById('app-fit-mode').value = cfg.DISPLAY_FIT_MODE || 'stretch';
    document.getElementById('app-bg-color').value = cfg.DISPLAY_BACKGROUND || '#ffffff';
    updateBgColorVisibility();

    // Populate SD options
    const sdValues = cfg.SD_OPTIONS || {};
    const rows = document.getElementById('sd-option-rows');
    rows.innerHTML = '';

    for (const opt of sdOptionDefs) {
      const entry = sdValues[opt.flag] || {};

      const row = document.createElement('div');
      row.className = 'sd-option-row';

      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.id = 'sd-enabled-' + opt.flag;
      checkbox.checked = !!entry.enabled;

      const main = document.createElement('div');
      main.className = 'sd-option-main';

      const label = document.createElement('div');
      label.className = 'sd-option-label';
      label.textContent = opt.label + ' ';
      const flagSpan = document.createElement('span');
      flagSpan.className = 'sd-option-flag';
      flagSpan.textContent = opt.flag;
      label.appendChild(flagSpan);

      const help = document.createElement('p');
      help.className = 'sd-option-help';
      help.textContent = opt.help;

      main.appendChild(label);
      main.appendChild(help);

      if (opt.kind === 'select') {
        const select = document.createElement('select');
        select.className = 'sd-option-value';
        select.id = 'sd-value-' + opt.flag;
        for (const choice of opt.choices) {
          const o = document.createElement('option');
          o.value = choice;
          o.textContent = choice;
          if (choice === entry.value) o.selected = true;
          select.appendChild(o);
        }
        main.appendChild(select);
      } else if (opt.kind !== 'bool') {
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'sd-option-value';
        input.id = 'sd-value-' + opt.flag;
        input.value = entry.value || '';
        main.appendChild(input);
      }

      row.appendChild(checkbox);
      row.appendChild(main);
      rows.appendChild(row);
    }
  }

  async function saveConfig() {
    const status = document.getElementById('save-status');
    status.textContent = 'Saving…';
    status.className = '';

    // Collect prompt banks
    const banks = {};
    document.querySelectorAll('textarea[id^="bank-"]').forEach(ta => {
      const key = ta.id.slice(5);
      banks[key] = ta.value.split('\\n').map(s => s.trim()).filter(s => s.length > 0);
    });
    const templates = document.getElementById('prompt-templates').value
      .split('\\n').map(s => s.trim()).filter(s => s.length > 0);

    // Collect SD options
    const sdOptions = {};
    for (const opt of sdOptionDefs) {
      const enabled = document.getElementById('sd-enabled-' + opt.flag).checked;
      const entry = { enabled };
      if (opt.kind !== 'bool') {
        entry.value = document.getElementById('sd-value-' + opt.flag).value.trim();
      }
      sdOptions[opt.flag] = entry;
    }

    const payload = {
      DISPLAY_TYPE: document.getElementById('app-display-type').value,
      INPUT_TYPE: document.getElementById('app-input-type').value,
      DISPLAY_FIT_MODE: document.getElementById('app-fit-mode').value,
      DISPLAY_BACKGROUND: document.getElementById('app-bg-color').value,
      PROMPT_BANKS: banks,
      PROMPT_TEMPLATES: templates,
      GLOBAL_QUALITY_HINT: document.getElementById('quality-hint').value.trim(),
      SD_OPTIONS: sdOptions,
    };

    try {
      const resp = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const result = await resp.json();
      if (result.ok) {
        status.textContent = result.restarting
          ? 'Saved — restarting application…'
          : 'Saved!';
        status.className = 'save-ok';
        setTimeout(() => { status.textContent = ''; }, 5000);
      } else {
        status.textContent = 'Error: ' + (result.error || 'unknown');
        status.className = 'save-err';
      }
    } catch (err) {
      status.textContent = 'Network error';
      status.className = 'save-err';
    }
  }

  function updateBgColorVisibility() {
    const show = document.getElementById('app-fit-mode').value === 'contain';
    document.getElementById('bg-color-row').style.display = show ? '' : 'none';
  }

  document.getElementById('app-fit-mode').addEventListener('change', updateBgColorVisibility);
  document.getElementById('header-save').addEventListener('click', saveConfig);

  loadConfig();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE_TEMPLATE)


@app.route("/images/<path:filename>")
def image_file(filename: str):
    requested = Path(filename)
    if requested.name != filename:
        abort(404)

    path = config.IMAGE_DIR / filename
    if not path.exists() or path.suffix.lower() not in IMAGE_EXTENSIONS:
        abort(404)

    return send_from_directory(config.IMAGE_DIR, filename)


@app.route("/api/current")
def api_current():
    return api_image(None)


@app.route("/api/image/<int:index>")
def api_image(index: Optional[int]):
    entries = get_entries()
    if not entries:
        abort(404)

    entry = entries[-1] if index is None else entries[index % len(entries)]

    return jsonify({
        "index": entry.index,
        "count": len(entries),
        "filename": entry.filename,
        "caption": entry.caption,
        "created": entry.created,
        "image_url": url_for("image_file", filename=entry.filename),
    })


@app.route("/api/config", methods=["GET"])
def api_get_config():
    return jsonify({"config": load_config(), "sd_defs": OPTION_DEFS})


@app.route("/api/config", methods=["POST"])
def api_save_config():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "No JSON body"}), 400

    display_type = data.get("DISPLAY_TYPE")
    if display_type not in {"inky", "hdmi"}:
        return jsonify({"error": "DISPLAY_TYPE must be 'inky' or 'hdmi'"}), 400

    input_type = data.get("INPUT_TYPE")
    if input_type not in {"buttons", "keyboard"}:
        return jsonify({"error": "INPUT_TYPE must be 'buttons' or 'keyboard'"}), 400

    fit_mode = data.get("DISPLAY_FIT_MODE", "stretch")
    if fit_mode not in {"stretch", "crop", "contain"}:
        return jsonify({"error": "DISPLAY_FIT_MODE must be 'stretch', 'crop', or 'contain'"}), 400

    import re as _re
    bg_color = data.get("DISPLAY_BACKGROUND", "#ffffff")
    if not _re.match(r"^#[0-9a-fA-F]{6}$", str(bg_color)):
        return jsonify({"error": "DISPLAY_BACKGROUND must be a hex colour like #ffffff"}), 400

    banks = data.get("PROMPT_BANKS")
    templates = data.get("PROMPT_TEMPLATES")
    if not isinstance(banks, dict) or not all(isinstance(v, list) for v in banks.values()):
        return jsonify({"error": "Invalid PROMPT_BANKS"}), 400
    if not isinstance(templates, list):
        return jsonify({"error": "Invalid PROMPT_TEMPLATES"}), 400

    clean_banks = {k: [str(i).strip() for i in v if str(i).strip()] for k, v in banks.items()}
    clean_templates = [str(t).strip() for t in templates if str(t).strip()]
    empty_banks = [k for k, v in clean_banks.items() if not v]
    if empty_banks:
        return jsonify({"error": f"Empty bank(s): {', '.join(empty_banks)}"}), 400
    if not clean_templates:
        return jsonify({"error": "Templates list cannot be empty"}), 400

    sd_options_raw = data.get("SD_OPTIONS", {})
    clean_sd = {}
    for flag, entry in sd_options_raw.items():
        if flag not in OPTION_FLAGS or not isinstance(entry, dict):
            continue
        saved = {"enabled": bool(entry.get("enabled"))}
        if "value" in entry:
            saved["value"] = str(entry["value"]).strip()
        clean_sd[flag] = saved

    current = load_config()
    settings_changed = (display_type != current.get("DISPLAY_TYPE") or
                        input_type != current.get("INPUT_TYPE"))
    display_changed = (fit_mode != current.get("DISPLAY_FIT_MODE") or
                       bg_color.lower() != current.get("DISPLAY_BACKGROUND", "").lower())

    payload = {
        "DISPLAY_TYPE": display_type,
        "INPUT_TYPE": input_type,
        "DISPLAY_FIT_MODE": fit_mode,
        "DISPLAY_BACKGROUND": bg_color.lower(),
        "PROMPT_BANKS": clean_banks,
        "PROMPT_TEMPLATES": clean_templates,
        "GLOBAL_QUALITY_HINT": str(data.get("GLOBAL_QUALITY_HINT", "")).strip(),
        "SD_OPTIONS": clean_sd,
    }

    try:
        with CONFIG_FILE.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    except OSError as e:
        return jsonify({"error": str(e)}), 500

    if settings_changed and _restart_event is not None:
        _restart_event.set()
    elif display_changed and _command_queue is not None:
        _command_queue.put("redisplay")

    return jsonify({"ok": True, "restarting": settings_changed and _restart_event is not None})


class WebViewerThread(threading.Thread):
    """Runs the Flask web server on a background thread with a clean shutdown path."""

    def __init__(self):
        super().__init__(daemon=True)
        self._server = make_server(WEB_HOST, WEB_PORT, app)

    def run(self):
        print(f"[WEB] Serving {config.IMAGE_DIR} on http://{WEB_HOST}:{WEB_PORT}/")
        self._server.serve_forever()

    def stop(self):
        self._server.shutdown()
        print("[WEB] Web viewer stopped")


if __name__ == "__main__":
    print(f"[WEB] Serving {config.IMAGE_DIR} on http://{WEB_HOST}:{WEB_PORT}/")
    app.run(host=WEB_HOST, port=WEB_PORT, threaded=True)
