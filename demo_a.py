"""Démo A — Filaments lumineux entre les extrémités des deux mains."""
import cv2
import numpy as np
from config import FINGERTIPS, FILAMENT_COLORS


def draw_filaments(frame, left_lm, right_lm, w, h):
    """Dessine des filaments néon entre les extrémités des deux mains."""
    glow = np.zeros_like(frame, dtype=np.uint8)
    for tip_idx, color in zip(FINGERTIPS, FILAMENT_COLORS):
        lx, ly = int(left_lm[tip_idx].x * w),  int(left_lm[tip_idx].y * h)
        rx, ry = int(right_lm[tip_idx].x * w), int(right_lm[tip_idx].y * h)
        cv2.line(glow, (lx, ly), (rx, ry), color, 9)
        cv2.line(glow, (lx, ly), (rx, ry), color, 4)
    glow = cv2.GaussianBlur(glow, (21, 21), 0)
    frame[:] = cv2.add(frame, glow)
    for tip_idx, color in zip(FINGERTIPS, FILAMENT_COLORS):
        lx, ly = int(left_lm[tip_idx].x * w),  int(left_lm[tip_idx].y * h)
        rx, ry = int(right_lm[tip_idx].x * w), int(right_lm[tip_idx].y * h)
        cv2.line(frame, (lx, ly), (rx, ry), (255, 255, 255), 1)
        for px, py in [(lx, ly), (rx, ry)]:
            cv2.circle(frame, (px, py), 6, color, -1)
            cv2.circle(frame, (px, py), 3, (255, 255, 255), -1)
