#!/usr/bin/env python3
"""Snake x jevos — serveur local.

- Sert la page web (dossier web/).
- POST /api/decide : reçoit l'état du jeu, calcule des faits sur chaque direction
  (mode « assisté »), pose 4 questions oui/non à jevos et renvoie sa décision.
- GET /api/health : état du serveur jevos.

Uniquement la bibliothèque standard de Python.
"""
import json
import os
import time
import urllib.error
import urllib.request
from collections import deque
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(ROOT, "web")
JEVOS_URL = os.environ.get("JEVOS_URL", "http://127.0.0.1:8018")
PORT = int(os.environ.get("PORT", "8080"))

DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}

# Deux questions oui/non par direction, posées en une seule requête (8 questions) :
#  - safe : le coup est-il sûr ?    - apple : rapproche-t-il de la pomme ?
# Score = P(safe)² × (0.4 + 0.6 × P(apple)) : la sécurité prime, la pomme départage.
Q_SAFE = "Is the move {d} safe, i.e. not marked DEADLY and not a TRAP?"
Q_APPLE = "Does the move {d} eat the apple or get closer to it?"


def flood(start, blocked, w, h, limit):
    """Nombre de cases libres atteignables depuis start (plafonné à limit)."""
    seen = {start}
    q = deque([start])
    while q and len(seen) < limit:
        x, y = q.popleft()
        for dx, dy in DIRS.values():
            n = (x + dx, y + dy)
            if 0 <= n[0] < w and 0 <= n[1] < h and n not in blocked and n not in seen:
                seen.add(n)
                q.append(n)
    return len(seen)


def analyse(game):
    """Calcule les faits sur chaque direction. Renvoie (faits, texte d'état)."""
    w, h = game["width"], game["height"]
    snake = [tuple(p) for p in game["snake"]]  # snake[0] = tête
    apple = tuple(game["apple"])
    hx, hy = snake[0]
    dist0 = abs(apple[0] - hx) + abs(apple[1] - hy)
    length = len(snake)
    facts = {}
    for d, (dx, dy) in DIRS.items():
        nx, ny = hx + dx, hy + dy
        n = (nx, ny)
        eats = n == apple
        # la queue avance, sauf si on mange : sa case devient libre
        body = snake if eats else snake[:-1]
        f = {"eats": eats}
        if not (0 <= nx < w and 0 <= ny < h):
            f.update(deadly=True, reason="wall")
        elif n in set(body):
            f.update(deadly=True, reason="own body")
        else:
            # après le coup, le serpent = [n] + body ; on compte l'espace atteignable depuis n
            room = flood(n, set(body), w, h, limit=length * 2 + 2)
            dist = abs(apple[0] - nx) + abs(apple[1] - ny)
            f.update(deadly=False, room=room, trap=room < length,
                     closer=dist < dist0)
        facts[d] = f

    lines = []
    for d, f in facts.items():
        if f["deadly"]:
            lines.append(f"- {d}: DEADLY, the snake would hit {'a wall' if f['reason'] == 'wall' else 'its own body'}.")
            continue
        parts = ["safe"]
        if f["eats"]:
            parts.append("EATS THE APPLE")
        else:
            parts.append("gets closer to the apple" if f["closer"] else "gets farther from the apple")
        parts.append("TRAP: not enough free space after this move, the snake would get stuck"
                     if f["trap"] else "plenty of free space after this move")
        lines.append(f"- {d}: " + ", ".join(parts) + ".")

    ax, ay = apple[0] - hx, apple[1] - hy
    where = []
    if ay:
        where.append(f"{abs(ay)} cell{'s' if abs(ay) > 1 else ''} {'down' if ay > 0 else 'up'}")
    if ax:
        where.append(f"{abs(ax)} cell{'s' if abs(ax) > 1 else ''} {'right' if ax > 0 else 'left'}")
    state = (f"Snake game on a {w}x{h} board. The snake is {length} cells long. "
             f"The apple is {' and '.join(where) or 'on the head'} from the head.\n"
             "What happens for each possible move:\n" + "\n".join(lines))
    return facts, state


def ask_jevos(state):
    body = {"model": "jev-latest", "state": state,
            "questions": {}}
    for d in DIRS:
        body["questions"]["safe_" + d] = {"type": "noul", "instructions": Q_SAFE.format(d=d)}
        body["questions"]["apple_" + d] = {"type": "noul", "instructions": Q_APPLE.format(d=d)}
    req = urllib.request.Request(JEVOS_URL + "/v1/systemone", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t = time.perf_counter()
    with urllib.request.urlopen(req, timeout=10) as r:
        out = json.loads(r.read())
    ms = (time.perf_counter() - t) * 1000
    a = out["answers"]
    safe = {d: a["safe_" + d]["noul"] for d in DIRS}
    apple = {d: a["apple_" + d]["noul"] for d in DIRS}
    return safe, apple, ms, out.get("usage", {})


def decide(game):
    facts, state = analyse(game)
    safe, apple, ms, usage = ask_jevos(state)
    score = {d: safe[d] ** 2 * (0.4 + 0.6 * apple[d]) for d in DIRS}
    move = max(score, key=score.get)
    return {"move": move, "probs": score, "safe": safe, "apple": apple, "latency_ms": round(ms, 1),
            "deadly": facts[move]["deadly"], "facts": facts, "state": state, "usage": usage}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=WEB, **kw)

    def log_message(self, fmt, *args):  # silence les logs HTTP
        pass

    def send_json(self, code, data):
        raw = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/api/health":
            try:
                with urllib.request.urlopen(JEVOS_URL + "/health", timeout=2) as r:
                    info = json.loads(r.read())
                return self.send_json(200, {"ok": info.get("status") == "ready", "model": info.get("model"),
                                            "url": JEVOS_URL})
            except Exception as e:
                return self.send_json(200, {"ok": False, "error": str(e), "url": JEVOS_URL})
        return super().do_GET()

    def do_POST(self):
        if self.path != "/api/decide":
            return self.send_json(404, {"error": "not found"})
        try:
            game = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            self.send_json(200, decide(game))
        except urllib.error.URLError as e:
            self.send_json(502, {"error": f"jevos injoignable ({JEVOS_URL}) : {e.reason}"})
        except Exception as e:
            self.send_json(400, {"error": str(e)})


if __name__ == "__main__":
    print(f"Snake x jevos : http://127.0.0.1:{PORT}  (jevos : {JEVOS_URL})")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
