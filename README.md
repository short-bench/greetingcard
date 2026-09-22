# Greeting cards

A tiny greeting-card site: people open a link, write one short message, and
anyone can download the finished card as a PDF (image on page 1, wishes on page 2).

## Run

```bash
pip install reportlab pillow
python3 app.py 8000
```

Then open http://localhost:8000/ for the list of cards.

## Cards

Cards are configured as JSON in the `CARDS` block near the top of `app.py`:

```json
"birthday-anna-2026": {
  "title":  "Happy Birthday, Anna!",
  "intro":  "shown under the title",
  "prompt": "label above the message box",
  "image":  "images/birthday-anna.jpg",
  "accent": "#d94f6a"
}
```

The key is the hash in the URL, so this card is shared as:

    https://your-domain.com/birthday-anna-2026

`image` is a path relative to `app.py`. The two files in `images/` are
placeholders — replace them with the real photos (any jpg/png/gif/webp).

## Storage

Messages go into `messages.db` (SQLite, created on first run). To reset a card:

```bash
sqlite3 messages.db "DELETE FROM messages WHERE card = 'birthday-anna-2026';"
```

## Routes

| URL             | What it does                          |
|-----------------|---------------------------------------|
| `/`             | lists the cards and their links        |
| `/<hash>`       | the card: photo, form, messages so far |
| `/<hash>/pdf`   | downloads the PDF                      |
| `/<hash>/image` | serves the configured photo            |

## Deploying

It is a plain `http.server` app, fine for a one-off. Put it behind nginx or a
tunnel (e.g. `cloudflared tunnel --url http://localhost:8000`) so the links work
as `https://your-domain.com/<hash>`. There is no auth: anyone with the link can
read the messages and download the PDF.
