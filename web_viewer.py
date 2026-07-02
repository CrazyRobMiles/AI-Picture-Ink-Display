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
PROMPTS_FILE = Path(__file__).parent / "prompts.json"
SD_OPTIONS_FILE = Path(__file__).parent / "sd_options.json"
APP_SETTINGS_FILE = Path(__file__).parent / "app_settings.json"

_restart_event: Optional[threading.Event] = None


def set_restart_event(event: Optional[threading.Event]) -> None:
    global _restart_event
    _restart_event = event


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


def load_prompts() -> dict:
    """Load prompts from prompts.json, falling back to config defaults."""
    if PROMPTS_FILE.exists():
        try:
            with PROMPTS_FILE.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "PROMPT_BANKS": {k: list(v) for k, v in config.PROMPT_BANKS.items()},
        "PROMPT_TEMPLATES": list(config.PROMPT_TEMPLATES),
        "GLOBAL_QUALITY_HINT": config.GLOBAL_QUALITY_HINT,
    }


def load_app_settings() -> dict:
    defaults = {"DISPLAY_TYPE": config.DISPLAY_TYPE, "INPUT_TYPE": config.INPUT_TYPE}
    if APP_SETTINGS_FILE.exists():
        try:
            with APP_SETTINGS_FILE.open("r", encoding="utf-8") as f:
                return {**defaults, **json.load(f)}
        except (OSError, json.JSONDecodeError):
            pass
    return defaults


def load_sd_options() -> dict:
    """Load saved SD option settings from sd_options.json, falling back to defaults."""
    if SD_OPTIONS_FILE.exists():
        try:
            with SD_OPTIONS_FILE.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    return dict(DEFAULT_SD_OPTIONS)


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

    .form-actions {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding-top: 0.25rem;
    }

    #save-prompts {
      min-width: 9rem;
      background: #2a6;
      color: #fff;
      border: 0;
    }

    #save-prompts:hover { background: #3b7; }

    .save-ok  { color: var(--ok);  font-size: 0.9rem; }
    .save-err { color: var(--err); font-size: 0.9rem; }

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

    <div class="form-actions">
      <button id="save-prompts" type="button">Save Changes</button>
      <span id="save-status"></span>
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

    <div class="form-actions">
      <button id="save-app-settings" type="button">Save Settings</button>
      <span id="save-app-status"></span>
    </div>

    <hr style="border:0;border-top:1px solid var(--border);margin:1.5rem 0">

    <p class="prompts-heading">Stable Diffusion Options</p>
    <p class="hint">Enable an option and (if it takes one) set its value. Changes take effect on the next generated image.</p>

    <div id="sd-option-rows"><div class="empty">Loading&hellip;</div></div>

    <div class="form-actions">
      <button id="save-sd-options" type="button">Save Changes</button>
      <span id="save-sd-status"></span>
    </div>
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

  document.getElementById('prev').addEventListener('click', () => {
    if (currentCount > 0) loadImage((currentIndex - 1 + currentCount) % currentCount);
  });
  document.getElementById('next').addEventListener('click', () => {
    if (currentCount > 0) loadImage((currentIndex + 1) % currentCount);
  });
  document.getElementById('latest').addEventListener('click', () => loadImage(null));

  document.addEventListener('keydown', (e) => {
    if (activeTab !== 'gallery') return;
    if (e.key === 'ArrowLeft') document.getElementById('prev').click();
    if (e.key === 'ArrowRight') document.getElementById('next').click();
    if (e.key === 'Home') document.getElementById('latest').click();
  });

  setInterval(() => {
    if (activeTab === 'gallery' && currentIndex !== null) loadImage(currentIndex);
  }, 10000);

  loadImage(null);

  // ---- Tab switching ----

  let activeTab = 'gallery';
  let promptsLoaded = false;
  let sdOptionsLoaded = false;

  function switchTab(tab) {
    activeTab = tab;
    document.getElementById('tab-gallery').classList.toggle('active', tab === 'gallery');
    document.getElementById('tab-prompts').classList.toggle('active', tab === 'prompts');
    document.getElementById('tab-sd').classList.toggle('active', tab === 'sd');
    document.getElementById('view-gallery').style.display = tab === 'gallery' ? '' : 'none';
    document.getElementById('view-prompts').style.display = tab === 'prompts' ? '' : 'none';
    document.getElementById('view-sd').style.display = tab === 'sd' ? '' : 'none';
    document.getElementById('counter').style.display = tab === 'gallery' ? '' : 'none';
    if (tab === 'prompts' && !promptsLoaded) loadPrompts();
    if (tab === 'sd' && !sdOptionsLoaded) { loadAppSettings(); loadSdOptions(); }
  }

  document.getElementById('tab-gallery').addEventListener('click', () => switchTab('gallery'));
  document.getElementById('tab-prompts').addEventListener('click', () => switchTab('prompts'));
  document.getElementById('tab-sd').addEventListener('click', () => switchTab('sd'));

  // ---- Prompts editor ----

  async function loadPrompts() {
    const resp = await fetch('/api/prompts', { cache: 'no-store' });
    const data = await resp.json();

    const grid = document.getElementById('bank-grid');
    grid.innerHTML = '';
    for (const [key, items] of Object.entries(data.PROMPT_BANKS)) {
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

    document.getElementById('prompt-templates').value = data.PROMPT_TEMPLATES.join('\\n');
    document.getElementById('quality-hint').value = data.GLOBAL_QUALITY_HINT || '';
    promptsLoaded = true;
  }

  async function savePrompts() {
    const banks = {};
    document.querySelectorAll('textarea[id^="bank-"]').forEach(ta => {
      const key = ta.id.slice(5);
      banks[key] = ta.value.split('\\n').map(s => s.trim()).filter(s => s.length > 0);
    });

    const templates = document.getElementById('prompt-templates').value
      .split('\\n').map(s => s.trim()).filter(s => s.length > 0);

    const qualityHint = document.getElementById('quality-hint').value.trim();

    const status = document.getElementById('save-status');

    const emptyBanks = Object.entries(banks).filter(([, v]) => v.length === 0).map(([k]) => k);
    if (emptyBanks.length > 0) {
      status.textContent = 'Cannot save: empty bank(s): ' + emptyBanks.join(', ');
      status.className = 'save-err';
      return;
    }
    if (templates.length === 0) {
      status.textContent = 'Cannot save: templates list is empty';
      status.className = 'save-err';
      return;
    }

    status.textContent = 'Saving…';
    status.className = '';

    try {
      const resp = await fetch('/api/prompts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ PROMPT_BANKS: banks, PROMPT_TEMPLATES: templates, GLOBAL_QUALITY_HINT: qualityHint }),
      });
      const result = await resp.json();
      if (result.ok) {
        status.textContent = 'Saved!';
        status.className = 'save-ok';
        setTimeout(() => { status.textContent = ''; }, 3000);
      } else {
        status.textContent = 'Error: ' + (result.error || 'unknown');
        status.className = 'save-err';
      }
    } catch (err) {
      status.textContent = 'Network error';
      status.className = 'save-err';
    }
  }

  document.getElementById('save-prompts').addEventListener('click', savePrompts);

  // ---- Application Settings ----

  async function loadAppSettings() {
    const resp = await fetch('/api/app-settings', { cache: 'no-store' });
    const data = await resp.json();
    document.getElementById('app-display-type').value = data.DISPLAY_TYPE || 'inky';
    document.getElementById('app-input-type').value = data.INPUT_TYPE || 'buttons';
  }

  async function saveAppSettings() {
    const payload = {
      DISPLAY_TYPE: document.getElementById('app-display-type').value,
      INPUT_TYPE: document.getElementById('app-input-type').value,
    };
    const status = document.getElementById('save-app-status');
    status.textContent = 'Saving…';
    status.className = '';
    try {
      const resp = await fetch('/api/app-settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const result = await resp.json();
      if (result.ok) {
        status.textContent = result.restarting
          ? 'Settings changed — restarting application…'
          : 'Saved (no changes).';
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

  document.getElementById('save-app-settings').addEventListener('click', saveAppSettings);

  // ---- SD Options editor ----

  let sdOptionDefs = [];

  async function loadSdOptions() {
    const resp = await fetch('/api/sd-options', { cache: 'no-store' });
    const data = await resp.json();
    sdOptionDefs = data.defs;

    const rows = document.getElementById('sd-option-rows');
    rows.innerHTML = '';

    for (const opt of data.defs) {
      const entry = data.values[opt.flag] || {};

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

    sdOptionsLoaded = true;
  }

  async function saveSdOptions() {
    const values = {};
    for (const opt of sdOptionDefs) {
      const enabled = document.getElementById('sd-enabled-' + opt.flag).checked;
      const entry = { enabled };
      if (opt.kind !== 'bool') {
        const valueEl = document.getElementById('sd-value-' + opt.flag);
        entry.value = valueEl.value.trim();
      }
      values[opt.flag] = entry;
    }

    const status = document.getElementById('save-sd-status');
    status.textContent = 'Saving…';
    status.className = '';

    try {
      const saveResp = await fetch('/api/sd-options', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      const result = await saveResp.json();
      if (result.ok) {
        status.textContent = 'Saved!';
        status.className = 'save-ok';
        setTimeout(() => { status.textContent = ''; }, 3000);
      } else {
        status.textContent = 'Error: ' + (result.error || 'unknown');
        status.className = 'save-err';
      }
    } catch (err) {
      status.textContent = 'Network error';
      status.className = 'save-err';
    }
  }

  document.getElementById('save-sd-options').addEventListener('click', saveSdOptions);
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


@app.route("/api/prompts", methods=["GET"])
def api_get_prompts():
    return jsonify(load_prompts())


@app.route("/api/prompts", methods=["POST"])
def api_save_prompts():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    banks = data.get("PROMPT_BANKS")
    templates = data.get("PROMPT_TEMPLATES")
    quality_hint = data.get("GLOBAL_QUALITY_HINT", "")

    if not isinstance(banks, dict) or not all(isinstance(v, list) for v in banks.values()):
        return jsonify({"error": "Invalid PROMPT_BANKS"}), 400
    if not isinstance(templates, list):
        return jsonify({"error": "Invalid PROMPT_TEMPLATES"}), 400

    payload = {
        "PROMPT_BANKS": {k: [str(i).strip() for i in v if str(i).strip()] for k, v in banks.items()},
        "PROMPT_TEMPLATES": [str(t).strip() for t in templates if str(t).strip()],
        "GLOBAL_QUALITY_HINT": str(quality_hint).strip(),
    }

    empty_banks = [k for k, v in payload["PROMPT_BANKS"].items() if not v]
    if empty_banks:
        return jsonify({"error": f"These banks are empty: {', '.join(empty_banks)}"}), 400
    if not payload["PROMPT_TEMPLATES"]:
        return jsonify({"error": "Templates list cannot be empty"}), 400

    try:
        with PROMPTS_FILE.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    except OSError as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"ok": True})


@app.route("/api/app-settings", methods=["GET"])
def api_get_app_settings():
    return jsonify(load_app_settings())


@app.route("/api/app-settings", methods=["POST"])
def api_save_app_settings():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "No JSON body"}), 400

    allowed = {"inky", "hdmi"}
    display_type = data.get("DISPLAY_TYPE")
    if display_type not in allowed:
        return jsonify({"error": f"DISPLAY_TYPE must be one of {sorted(allowed)}"}), 400

    allowed_input = {"buttons", "keyboard"}
    input_type = data.get("INPUT_TYPE")
    if input_type not in allowed_input:
        return jsonify({"error": f"INPUT_TYPE must be one of {sorted(allowed_input)}"}), 400

    payload = {"DISPLAY_TYPE": display_type, "INPUT_TYPE": input_type}
    current = load_app_settings()
    settings_changed = (display_type != current.get("DISPLAY_TYPE") or
                        input_type != current.get("INPUT_TYPE"))

    try:
        with APP_SETTINGS_FILE.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except OSError as e:
        return jsonify({"error": str(e)}), 500

    if settings_changed and _restart_event is not None:
        _restart_event.set()

    return jsonify({"ok": True, "restarting": settings_changed and _restart_event is not None})


@app.route("/api/sd-options", methods=["GET"])
def api_get_sd_options():
    return jsonify({"defs": OPTION_DEFS, "values": load_sd_options()})


@app.route("/api/sd-options", methods=["POST"])
def api_save_sd_options():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "No JSON body"}), 400

    payload = {}
    for flag, entry in data.items():
        if flag not in OPTION_FLAGS or not isinstance(entry, dict):
            continue
        saved = {"enabled": bool(entry.get("enabled"))}
        if "value" in entry:
            saved["value"] = str(entry["value"]).strip()
        payload[flag] = saved

    try:
        with SD_OPTIONS_FILE.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    except OSError as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"ok": True})


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
