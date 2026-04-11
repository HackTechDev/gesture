"""Démo B — Bulles brillantes à éclater par pincement pouce/index."""
import random
import time
import cv2
import numpy as np
from config import (
    BUBBLE_RADIUS, POP_DURATION, BUBBLE_COUNT,
    GAME_DURATION, PINCH_THRESHOLD, BUBBLE_PALETTE,
)


def new_bubble(w, h, existing=None):
    """Crée une bulle à une position qui ne chevauche pas les existantes."""
    margin = BUBBLE_RADIUS + 20
    existing = existing or []
    for _ in range(30):
        cx = random.randint(margin, w - margin)
        cy = random.randint(margin + 80, h - margin - 60)
        if all(((cx - b["cx"]) ** 2 + (cy - b["cy"]) ** 2) ** 0.5 > BUBBLE_RADIUS * 2.5
               for b in existing):
            break
    return {"cx": cx, "cy": cy, "r": BUBBLE_RADIUS, "color": random.choice(BUBBLE_PALETTE)}


def draw_bubble(frame, bubble):
    cx, cy, r, color = bubble["cx"], bubble["cy"], bubble["r"], bubble["color"]
    overlay = frame.copy()
    cv2.circle(overlay, (cx, cy), r, color, -1)
    cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)
    cv2.circle(frame, (cx, cy), r, color, 2)
    hl_x, hl_y = cx - r // 3, cy - r // 3
    axes = (max(r // 4, 4), max(r // 6, 3))
    cv2.ellipse(frame, (hl_x, hl_y), axes, -35, 0, 360, (255, 255, 255), -1)
    cv2.circle(frame, (cx + r // 4, cy + r // 4), max(r // 10, 2), (255, 255, 255), -1)


def draw_pop(frame, pop):
    """Animation d'éclatement : anneaux expansifs + étincelles."""
    t = 1.0 - pop["frames_left"] / POP_DURATION
    cx, cy = pop["cx"], pop["cy"]
    color  = pop["color"]
    for i in range(5):
        progress  = min(t + i / 5 * 0.3, 1.0)
        ring_r    = int(BUBBLE_RADIUS * (1 + progress * 3))
        alpha     = max(0.0, 1.0 - progress * 1.5)
        thickness = max(1, int(3 * (1 - progress)))
        ring_layer = frame.copy()
        cv2.circle(ring_layer, (cx, cy), ring_r, color, thickness)
        cv2.addWeighted(ring_layer, alpha * 0.7, frame, 1 - alpha * 0.7, 0, frame)
    rng = np.random.default_rng(seed=int(t * 100))
    for _ in range(8):
        angle   = rng.uniform(0, 2 * np.pi)
        dist    = int(BUBBLE_RADIUS * (1 + t * 2.5) * rng.uniform(0.6, 1.0))
        sx, sy  = cx + int(np.cos(angle) * dist), cy + int(np.sin(angle) * dist)
        cv2.circle(frame, (sx, sy), max(1, int(4 * (1 - t))), (255, 255, 255), -1)


def process(frame, hand_landmarks, w, h, bubbles, pops, score):
    """Détecte un pincement et éclate la bulle touchée. Retourne le nouveau score."""
    tx = int(hand_landmarks[4].x * w)
    ty = int(hand_landmarks[4].y * h)
    ix = int(hand_landmarks[8].x * w)
    iy = int(hand_landmarks[8].y * h)
    if ((tx - ix) ** 2 + (ty - iy) ** 2) ** 0.5 < PINCH_THRESHOLD:
        mid_x, mid_y = (tx + ix) // 2, (ty + iy) // 2
        for b in bubbles[:]:
            if ((mid_x - b["cx"]) ** 2 + (mid_y - b["cy"]) ** 2) ** 0.5 < b["r"] + 20:
                pops.append({"cx": b["cx"], "cy": b["cy"],
                             "color": b["color"], "frames_left": POP_DURATION})
                bubbles.remove(b)
                score += 1
                bubbles.append(new_bubble(w, h, bubbles))
                break
    return score


def render(frame, bubbles, pops, score, game_start, w, h):
    """Dessine bulles, animations, HUD. Retourne remaining (secondes restantes)."""
    remaining = max(0, GAME_DURATION - (time.time() - game_start))

    if remaining > 0:
        for b in bubbles:
            draw_bubble(frame, b)
    else:
        overlay = frame.copy()
        cv2.rectangle(overlay, (w//2 - 220, h//2 - 70), (w//2 + 220, h//2 + 70),
                      (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
        cv2.putText(frame, "TEMPS ECOULE !", (w//2 - 160, h//2 - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 80, 255), 3)
        cv2.putText(frame, f"Score final : {score}", (w//2 - 120, h//2 + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        cv2.putText(frame, "Appuyez sur B pour rejouer", (w//2 - 190, h//2 + 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1)

    for pop in pops[:]:
        draw_pop(frame, pop)
        pop["frames_left"] -= 1
        if pop["frames_left"] <= 0:
            pops.remove(pop)

    bar_w     = int((remaining / GAME_DURATION) * 300)
    bar_color = (0, 220, 0) if remaining > 10 else (0, 80, 255)
    cv2.rectangle(frame, (w//2 - 150, 12), (w//2 + 150, 30), (60, 60, 60), -1)
    cv2.rectangle(frame, (w//2 - 150, 12), (w//2 - 150 + bar_w, 30), bar_color, -1)
    cv2.putText(frame, f"{int(remaining)}s", (w//2 - 20, 27),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    cv2.putText(frame, f"Score : {score}", (w//2 + 160, 27),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 255, 180), 2)
    return remaining
