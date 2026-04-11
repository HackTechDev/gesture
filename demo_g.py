"""Démo G — Traînées de mouvement (motion trail) sur les bouts de doigts."""
from collections import deque
import cv2
import numpy as np
from config import TRAIL_LENGTH, TRAIL_COLORS, FINGERTIPS


def update_trails(trail_history, idx, hand_landmarks, w, h):
    """Enregistre la position actuelle de chaque bout de doigt."""
    if idx not in trail_history:
        trail_history[idx] = {tip: deque(maxlen=TRAIL_LENGTH) for tip in FINGERTIPS}
    for tip in FINGERTIPS:
        x = int(hand_landmarks[tip].x * w)
        y = int(hand_landmarks[tip].y * h)
        trail_history[idx][tip].append((x, y))


def render(frame, trail_history, active_ids, w, h):
    """Dessine les traînées lumineuses et purge les mains disparues."""
    for idx in list(trail_history.keys()):
        if idx not in active_ids:
            del trail_history[idx]
            continue

        glow = np.zeros_like(frame, dtype=np.uint8)

        for i, tip in enumerate(FINGERTIPS):
            positions = list(trail_history[idx][tip])
            n = len(positions)
            if n < 2:
                continue
            color = TRAIL_COLORS[i]

            for j in range(1, n):
                alpha = j / (n - 1)          # 0 = plus vieux, 1 = plus récent
                thickness_glow = max(1, int(alpha * 10))
                thickness_core = max(1, int(alpha * 3))

                # Intensité de la couleur proportionnelle à l'ancienneté
                c_bright = tuple(int(ch * alpha) for ch in color)
                c_core   = tuple(min(255, int(ch * alpha + 80 * alpha)) for ch in color)

                cv2.line(glow, positions[j - 1], positions[j], c_bright, thickness_glow)
                cv2.line(frame, positions[j - 1], positions[j], c_core,   thickness_core)

            # Point brillant à la pointe du doigt
            tip_pos = positions[-1]
            cv2.circle(glow,  tip_pos, 8, color, -1)
            cv2.circle(frame, tip_pos, 4, color, -1)
            cv2.circle(frame, tip_pos, 2, (255, 255, 255), -1)

        glow_blurred = cv2.GaussianBlur(glow, (19, 19), 0)
        frame[:] = cv2.add(frame, glow_blurred)
