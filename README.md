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

---

## Running on the droplet next to Traefik

The container joins Traefik's existing network and is routed by labels. It
publishes **no ports**, so it is only reachable through Traefik.

### 1. Use a subdomain

Card hashes live at the root of the domain (`/<hash>`), so this app needs a host
of its own — on an apex domain shared with other projects every path would have
to be routed here. Point a DNS A record at the droplet:

    cards.retrobit.me.  A  <droplet-ip>

### 2. Traefik wiring

Already filled in to match the other projects on the droplet: external network
`traefik_web`, certresolver `lets-encrypt`, and no explicit `entrypoints` label
(Traefik's defaults, same as the scrum app). Nothing to change unless you want a
different subdomain, which is the `Host(...)` rule in `docker-compose.yml`.

Unlike the other projects this one does **not** publish a `ports:` mapping, so
it is reachable only through Traefik on 443, never directly on the droplet IP.

### 3. Deploy

```bash
rsync -av --exclude messages.db --exclude .git ./ root@<droplet>:/opt/greetingcard/
ssh root@<droplet> 'cd /opt/greetingcard && docker compose up -d --build'
```

Changing a photo or a card's text means editing `app.py` / `images/` and
re-running `docker compose up -d --build`. Messages live on the named volume
`greetingcard-data`, so they survive rebuilds.

### 4. Getting the results out

```bash
# the finished PDFs
curl -O https://cards.retrobit.me/farewell-giorgio-aajnfuw/pdf

# or the raw database
docker compose cp greetingcard:/data/messages.db ./messages.db
```

### Notes

- There is no auth: anyone with a link can read the messages and download the
  PDF. The hashes are unguessable, but don't send the link to the recipients.
- When the cards are done: `docker compose down -v` also deletes the volume and
  with it the messages, so grab the PDFs first.
