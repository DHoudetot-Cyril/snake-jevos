#!/usr/bin/env python3
"""Fait jouer jevos sans navigateur : python3 tools/simulate.py [parties] [taille]"""
import os
import random
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from server import DIRS, decide  # noqa: E402

games = int(sys.argv[1]) if len(sys.argv) > 1 else 5
n = int(sys.argv[2]) if len(sys.argv) > 2 else 16
scores, lats, deadly, causes = [], [], 0, {}

for gi in range(games):
    rnd = random.Random(gi)
    m = n // 2
    snake = [(m, m), (m - 1, m), (m - 2, m)]

    def new_apple():
        free = [(x, y) for x in range(n) for y in range(n) if (x, y) not in snake]
        return rnd.choice(free)

    apple, score, steps, since_eat = new_apple(), 0, 0, 0
    while True:
        d = decide({"width": n, "height": n, "snake": snake, "apple": apple})
        lats.append(d["latency_ms"])
        dx, dy = DIRS[d["move"]]
        head = (snake[0][0] + dx, snake[0][1] + dy)
        eats = head == apple
        body = snake if eats else snake[:-1]
        if not (0 <= head[0] < n and 0 <= head[1] < n) or head in body:
            deadly += 1
            print("   MORT:", {k: round(v, 2) for k, v in d["probs"].items()}, "\n  ", d["state"].replace("\n", "\n   "))
            f = d["facts"]
            cause = "piégé (aucun coup sûr)" if all(v["deadly"] for v in f.values()) else "choix mortel"
            causes[cause] = causes.get(cause, 0) + 1
            break
        snake = [head] + body
        steps += 1
        since_eat += 1
        if eats:
            score += 1
            since_eat = 0
            apple = new_apple()
        if since_eat > n * n * 2:
            causes["boucle sans fin"] = causes.get("boucle sans fin", 0) + 1
            break
    scores.append(score)
    print(f"partie {gi + 1}: score {score} en {steps} coups")

print(f"\nscore moyen {statistics.mean(scores):.1f}, max {max(scores)} | "
      f"latence médiane {statistics.median(lats):.0f} ms (min {min(lats):.0f}, max {max(lats):.0f}) | fins : {causes}")
