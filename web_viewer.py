#!/usr/bin/env python3
"""
Simple web viewer for the AI e-ink picture frame.

Run with:
    python web_viewer.py

Then browse to:
    http://<pi-address>:8080/
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, abort, jsonify, render_template_string, send_from_directory, url_for

from config import IMAGE_DIR
from image_catalog import IMAGE_EXTENSIONS

WEB_HOST = "0.0.0.0"
WEB_PORT = 8080
PROMPT_LOG_NAME = "prompt_log.txt"


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
    """Load prompt_log.txt entries keyed by image filename.

    Expected current format:
        ISO_TIMESTAMP | filename.png | prompt text
    """
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
        # The generator may be appending while we read. A transient read failure
        # should not take the viewer down.
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
    captions = load_captions(IMAGE_DIR)
    images = scan_images(IMAGE_DIR)

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


def get_entry(index: Optional[int]) -> Optional[ImageEntry]:
    entries = get_entries()
    if not entries:
        return None

    if index is None:
        return entries[-1]

    index = index % len(entries)
    return entries[index]


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

    header, footer {
      padding: 0.75rem 1rem;
      background: var(--panel);
    }

    header {
      display: flex;
      justify-content: space-between;
      gap: 1rem;
      align-items: center;
    }

    h1 {
      margin: 0;
      font-size: 1.1rem;
      font-weight: 650;
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

    .caption p {
      margin: 0.25rem 0;
    }

    .meta {
      color: var(--muted);
      font-size: 0.9rem;
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
  </style>
</head>
<body>
  <header>
    <h1>AI Picture Frame</h1>
    <div id="counter" class="meta"></div>
  </header>

  <main id="app">
    <div class="empty">Loading images…</div>
  </main>

  <footer>
    <div class="controls">
      <button id="prev" type="button">◀ Previous</button>
      <button id="latest" type="button">Latest</button>
      <button id="next" type="button">Next ▶</button>
    </div>
  </footer>

  <script>
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
          <p class="meta">${escapeHtml(data.filename)}${data.created ? ' · ' + escapeHtml(data.created) : ''}</p>
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

    document.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowLeft') document.getElementById('prev').click();
      if (event.key === 'ArrowRight') document.getElementById('next').click();
      if (event.key === 'Home') document.getElementById('latest').click();
    });

    // Refresh metadata occasionally. This picks up new images without forcing
    // someone browsing older images back to latest.
    setInterval(() => {
      if (currentIndex !== null) loadImage(currentIndex);
    }, 10000);

    loadImage(null);
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

    path = IMAGE_DIR / filename
    if not path.exists() or path.suffix.lower() not in IMAGE_EXTENSIONS:
        abort(404)

    return send_from_directory(IMAGE_DIR, filename)


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


if __name__ == "__main__":
    print(f"[WEB] Serving {IMAGE_DIR} on http://{WEB_HOST}:{WEB_PORT}/")
    app.run(host=WEB_HOST, port=WEB_PORT, threaded=True)

