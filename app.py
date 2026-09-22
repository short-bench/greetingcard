#!/usr/bin/env python3
"""Tiny greeting-card server. Run: python3 app.py [port]"""

import html
import io
import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image as RLImage,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DB_PATH is overridable so the database can live on a mounted volume.
DB_PATH = os.environ.get("CARD_DB", os.path.join(BASE_DIR, "messages.db"))

# ---------------------------------------------------------------------------
# Card configuration. Add/edit cards here.
# The key is the hash used in the URL: https://domain.com/<hash>
# "image" is a path relative to this file.
# ---------------------------------------------------------------------------
CARDS = json.loads(r"""
{
  "farewell-giorgio-aajnfuw": {
    "title": "All the best on your new adventure Giorgio :D",
    "intro": "Collecting some nice words for Giorgio <3",
    "prompt": "Just write something nice (or not nice) for Giorgio",
    "image": "images/giorgio.jpg",
    "accent": "#d94f6a"
  },
  "farewell-mihnea-aajnfuw": {
    "title": "All the best on your new adventure Mihnea :D",
    "intro": "Collecting some nice words for Mihnea <3",
    "prompt": "Just write something nice (or not nice) for Mihnea",
    "image": "images/mihnea.jpg",
    "accent": "#3b7ea1"
  }
}
""")


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS messages (
                   id         INTEGER PRIMARY KEY AUTOINCREMENT,
                   card       TEXT NOT NULL,
                   name       TEXT NOT NULL,
                   message    TEXT NOT NULL,
                   created_at TEXT NOT NULL
               )"""
        )


def add_message(card, name, message):
    with db() as conn:
        conn.execute(
            "INSERT INTO messages (card, name, message, created_at) VALUES (?, ?, ?, ?)",
            (card, name, message, datetime.now().isoformat(timespec="seconds")),
        )


def get_messages(card):
    with db() as conn:
        return conn.execute(
            "SELECT name, message, created_at FROM messages WHERE card = ? ORDER BY id",
            (card,),
        ).fetchall()


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------
def build_pdf(card_hash, card):
    buf = io.BytesIO()
    margin = 18 * mm
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=margin, bottomMargin=margin,
        title=card["title"],
    )
    avail_w = doc.width
    avail_h = doc.height

    accent = colors.HexColor(card.get("accent", "#333333"))
    h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=24,
                        leading=30, textColor=accent, spaceAfter=14)
    body = ParagraphStyle("body", fontName="Helvetica", fontSize=12,
                          leading=17, spaceAfter=4)
    signature = ParagraphStyle("sig", fontName="Helvetica-Oblique", fontSize=11,
                               leading=15, textColor=colors.HexColor("#666666"),
                               spaceAfter=18, alignment=2)

    story = []

    # Page 1: the picture, scaled to fit the page while keeping its ratio.
    img_path = os.path.join(BASE_DIR, card["image"])
    if os.path.exists(img_path):
        img = RLImage(img_path)
        scale = min(avail_w / img.drawWidth, avail_h / img.drawHeight)
        img.drawWidth *= scale
        img.drawHeight *= scale
        story.append(img)
    else:
        story.append(Paragraph(html.escape(card["title"]), h1))
        story.append(Paragraph("(image not found: %s)" % html.escape(card["image"]), body))
    story.append(PageBreak())

    # Page 2+: the wishes.
    story.append(Paragraph(html.escape(card["title"]), h1))
    rows = get_messages(card_hash)
    if not rows:
        story.append(Paragraph("No messages yet.", body))
    for row in rows:
        text = html.escape(row["message"]).replace("\n", "<br/>")
        story.append(Paragraph(text, body))
        story.append(Paragraph("&mdash; %s" % html.escape(row["name"]), signature))

    doc.build(story)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------
PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root { --accent: __ACCENT__; --ink: #22252a; --muted: #6b7280;
          --bg: #f4f1ec; --card: #ffffff; --line: #e6e1d8; }
  * { box-sizing: border-box; }
  body { margin: 0; padding: 32px 16px 64px; background: var(--bg); color: var(--ink);
         font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
         line-height: 1.55; }
  .card { max-width: 640px; margin: 0 auto; background: var(--card); border-radius: 14px;
          overflow: hidden; box-shadow: 0 6px 28px rgba(0,0,0,.09); }
  .photo { display: block; width: 100%; height: auto; background: #ddd; }
  .body { padding: 28px 28px 32px; }
  h1 { margin: 0 0 10px; font-size: 1.7rem; line-height: 1.25; color: var(--accent); }
  p.intro { margin: 0 0 24px; color: var(--muted); }
  label { display: block; font-weight: 600; font-size: .9rem; margin: 0 0 6px; }
  input, textarea { width: 100%; padding: 11px 13px; font: inherit; color: inherit;
                    border: 1px solid var(--line); border-radius: 8px; background: #fcfbf9; }
  input:focus, textarea:focus { outline: 2px solid var(--accent); outline-offset: 1px; border-color: transparent; }
  textarea { min-height: 130px; resize: vertical; }
  .field { margin-bottom: 18px; }
  .row { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
  button, .btn { display: inline-block; padding: 12px 22px; font: inherit; font-weight: 600;
                 border: 0; border-radius: 8px; cursor: pointer; text-decoration: none;
                 background: var(--accent); color: #fff; }
  button:hover, .btn:hover { filter: brightness(1.08); }
  .btn.ghost { background: transparent; color: var(--accent); border: 1px solid var(--line); }
  .note { font-size: .85rem; color: var(--muted); margin: 14px 0 0; }
  .flash { padding: 14px 16px; border-radius: 8px; background: #e8f5ec; color: #1d6b3a;
           border: 1px solid #bfe3cb; margin: 0 0 22px; }
  .wishes { margin: 34px 0 0; border-top: 1px solid var(--line); padding-top: 22px; }
  .wishes h2 { font-size: 1rem; text-transform: uppercase; letter-spacing: .06em;
               color: var(--muted); margin: 0 0 16px; }
  .wish { border-left: 3px solid var(--accent); padding: 2px 0 2px 14px; margin: 0 0 18px; }
  .wish p { margin: 0 0 4px; white-space: pre-wrap; }
  .wish span { font-size: .88rem; color: var(--muted); font-style: italic; }
  .err { color: #b3261e; font-size: .88rem; margin: 6px 0 0; }
</style>
</head>
<body>
  <div class="card">
    __PHOTO__
    <div class="body">
      <h1>__TITLE__</h1>
      <p class="intro">__INTRO__</p>
      __CONTENT__
      __WISHES__
    </div>
  </div>
</body>
</html>
"""

FORM = """
      <form method="post">
        <div class="field">
          <label for="name">Your name</label>
          <input id="name" name="name" maxlength="80" required value="__NAME__">
        </div>
        <div class="field">
          <label for="message">__PROMPT__</label>
          <textarea id="message" name="message" maxlength="1500" required>__MESSAGE__</textarea>
        </div>
        __ERROR__
        <div class="row">
          <button type="submit">Send my message</button>
          <a class="btn ghost" href="__HASH__/pdf">Download PDF</a>
        </div>
        <p class="note">Your message is added to the card. Everyone can download the finished card as a PDF.</p>
      </form>
"""

DONE = """
      <div class="flash">Thank you &mdash; your message has been added to the card.</div>
      <div class="row">
        <a class="btn" href="__HASH__/pdf">Download the card as PDF</a>
        <a class="btn ghost" href="__HASH__">Write another message</a>
      </div>
"""


def render_card(card_hash, card, state="form", form=None, error=""):
    form = form or {}
    photo = '<img class="photo" src="/%s/image" alt="">' % html.escape(card_hash)

    if state == "done":
        content = DONE.replace("__HASH__", html.escape("/" + card_hash))
    else:
        content = (FORM
                   .replace("__PROMPT__", html.escape(card["prompt"]))
                   .replace("__NAME__", html.escape(form.get("name", "")))
                   .replace("__MESSAGE__", html.escape(form.get("message", "")))
                   .replace("__ERROR__", '<p class="err">%s</p>' % html.escape(error) if error else "")
                   .replace("__HASH__", html.escape("/" + card_hash)))

    rows = get_messages(card_hash)
    if rows:
        items = "".join(
            '<div class="wish"><p>%s</p><span>&mdash; %s</span></div>'
            % (html.escape(r["message"]), html.escape(r["name"]))
            for r in rows
        )
        wishes = '<div class="wishes"><h2>%d message%s so far</h2>%s</div>' % (
            len(rows), "" if len(rows) == 1 else "s", items)
    else:
        wishes = ""

    return (PAGE
            .replace("__TITLE__", html.escape(card["title"]))
            .replace("__ACCENT__", card.get("accent", "#333333"))
            .replace("__INTRO__", html.escape(card["intro"]))
            .replace("__PHOTO__", photo)
            .replace("__CONTENT__", content)
            .replace("__WISHES__", wishes))


def render_index():
    items = "".join(
        '<div class="wish"><p><a href="/%s">%s</a></p><span>/%s</span></div>'
        % (html.escape(h), html.escape(c["title"]), html.escape(h))
        for h, c in CARDS.items()
    )
    return (PAGE
            .replace("__TITLE__", "Greeting cards")
            .replace("__ACCENT__", "#3b7ea1")
            .replace("__INTRO__", "Share one of these links with the people who should sign the card.")
            .replace("__PHOTO__", "")
            .replace("__CONTENT__", "")
            .replace("__WISHES__", '<div class="wishes" style="border:0;padding-top:0">%s</div>' % items))


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
IMAGE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
               ".gif": "image/gif", ".webp": "image/webp"}


class Handler(BaseHTTPRequestHandler):
    server_version = "GreetingCard/1.0"

    # -- helpers ------------------------------------------------------------
    def send(self, body, content_type="text/html; charset=utf-8", status=200, headers=()):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for key, value in headers:
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def not_found(self):
        self.send("<h1>404 &mdash; no such card</h1>", status=404)

    def route(self):
        """-> (card_hash, action) or (None, None)."""
        path = urlparse(self.path).path.strip("/")
        if not path:
            return "", "index"
        parts = path.split("/")
        card_hash = parts[0]
        if card_hash not in CARDS:
            return None, None
        action = parts[1] if len(parts) > 1 else "card"
        return card_hash, action if action in ("card", "image", "pdf") else None

    # -- requests -----------------------------------------------------------
    def do_GET(self):
        card_hash, action = self.route()
        if action == "index":
            return self.send(render_index())
        if action is None:
            return self.not_found()
        card = CARDS[card_hash]

        if action == "card":
            return self.send(render_card(card_hash, card))

        if action == "image":
            path = os.path.join(BASE_DIR, card["image"])
            if not os.path.exists(path):
                return self.not_found()
            with open(path, "rb") as fh:
                data = fh.read()
            ctype = IMAGE_TYPES.get(os.path.splitext(path)[1].lower(), "application/octet-stream")
            return self.send(data, ctype)

        if action == "pdf":
            pdf = build_pdf(card_hash, card)
            name = re.sub(r"[^a-zA-Z0-9]+", "-", card["title"]).strip("-").lower() or "card"
            return self.send(pdf, "application/pdf", headers=[
                ("Content-Disposition", 'attachment; filename="%s.pdf"' % name)])

    do_HEAD = do_GET

    def do_POST(self):
        card_hash, action = self.route()
        if action != "card":
            return self.not_found()
        card = CARDS[card_hash]

        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8", "replace")
        form = parse_qs(raw)
        name = form.get("name", [""])[0].strip()[:80]
        message = form.get("message", [""])[0].strip()[:1500]

        if not name or not message:
            page = render_card(card_hash, card, form={"name": name, "message": message},
                               error="Please fill in both your name and a message.")
            return self.send(page, status=400)

        add_message(card_hash, name, message)
        # Redirect so a refresh does not post twice.
        self.send_response(303)
        self.send_header("Location", "/%s/?done=1" % card_hash)
        self.end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.log_date_time_string(), fmt % args))


class DoneAwareHandler(Handler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        card_hash, action = self.route()
        if action == "card" and query.get("done"):
            return self.send(render_card(card_hash, CARDS[card_hash], state="done"))
        return Handler.do_GET(self)

    do_HEAD = do_GET


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    init_db()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", 8000))
    print("Greeting cards running on port %d (db: %s)" % (port, DB_PATH), flush=True)
    for h in CARDS:
        print("  /%s" % h, flush=True)
    Server(("0.0.0.0", port), DoneAwareHandler).serve_forever()
