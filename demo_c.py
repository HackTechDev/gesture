"""Démo C — Bulle physique poussée par l'index, avec rebonds sur les bords."""
import random
import cv2
from demo_b import BUBBLE_PALETTE

BUBBLE_RADIUS_C = 50
PUSH_RADIUS     = BUBBLE_RADIUS_C + 50  # zone de contact
PUSH_FACTOR     = 0.45                  # intensité de la poussée
DAMPING         = 0.97                  # friction par frame
MAX_VEL         = 28                    # vitesse maximale en px/frame


def new_bubble_c(w, h):
    margin = BUBBLE_RADIUS_C + 20
    return {
        "cx":    float(random.randint(margin, w - margin)),
        "cy":    float(random.randint(margin + 80, h - margin - 60)),
        "r":     BUBBLE_RADIUS_C,
        "vx":    0.0,
        "vy":    0.0,
        "color": random.choice(BUBBLE_PALETTE),
    }


def push_bubble_c(bubble, ix, iy, prev_ix, prev_iy):
    """Applique une impulsion proportionnelle à la vitesse de l'index."""
    dx   = bubble["cx"] - ix
    dy   = bubble["cy"] - iy
    dist = (dx ** 2 + dy ** 2) ** 0.5
    if dist < PUSH_RADIUS:
        bubble["vx"] += (ix - prev_ix) * PUSH_FACTOR
        bubble["vy"] += (iy - prev_iy) * PUSH_FACTOR
        if 0 < dist < bubble["r"] + 10:
            repulse = (bubble["r"] + 10 - dist) * 0.6
            bubble["vx"] += (dx / dist) * repulse
            bubble["vy"] += (dy / dist) * repulse


def update_bubble_c(bubble, w, h):
    """Déplace la bulle et gère les rebonds sur les bords."""
    bubble["cx"] += bubble["vx"]
    bubble["cy"] += bubble["vy"]
    r = bubble["r"]
    ui_top, ui_bot = 80, 42
    if bubble["cx"] - r < 0:
        bubble["cx"] = float(r);  bubble["vx"] = abs(bubble["vx"])
    elif bubble["cx"] + r > w:
        bubble["cx"] = float(w - r);  bubble["vx"] = -abs(bubble["vx"])
    if bubble["cy"] - r < ui_top:
        bubble["cy"] = float(ui_top + r);  bubble["vy"] = abs(bubble["vy"])
    elif bubble["cy"] + r > h - ui_bot:
        bubble["cy"] = float(h - ui_bot - r);  bubble["vy"] = -abs(bubble["vy"])
    bubble["vx"] *= DAMPING
    bubble["vy"] *= DAMPING
    speed = (bubble["vx"] ** 2 + bubble["vy"] ** 2) ** 0.5
    if speed > MAX_VEL:
        bubble["vx"] = bubble["vx"] / speed * MAX_VEL
        bubble["vy"] = bubble["vy"] / speed * MAX_VEL


def draw_bubble_c(frame, bubble):
    cx, cy = int(bubble["cx"]), int(bubble["cy"])
    r, color = bubble["r"], bubble["color"]
    zone_layer = frame.copy()
    cv2.circle(zone_layer, (cx, cy), PUSH_RADIUS, color, 1)
    cv2.addWeighted(zone_layer, 0.15, frame, 0.85, 0, frame)
    overlay = frame.copy()
    cv2.circle(overlay, (cx, cy), r, color, -1)
    cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)
    cv2.circle(frame, (cx, cy), r, color, 2)
    hl_x, hl_y = cx - r // 3, cy - r // 3
    cv2.ellipse(frame, (hl_x, hl_y), (max(r//4, 4), max(r//6, 3)), -35, 0, 360,
                (255, 255, 255), -1)
    cv2.circle(frame, (cx + r//4, cy + r//4), max(r//10, 2), (255, 255, 255), -1)
    speed = (bubble["vx"] ** 2 + bubble["vy"] ** 2) ** 0.5
    if speed > 1.0:
        scale = min(speed * 3, 60)
        ex = int(cx + bubble["vx"] / speed * scale)
        ey = int(cy + bubble["vy"] / speed * scale)
        cv2.arrowedLine(frame, (cx, cy), (ex, ey), color, 1, tipLength=0.3)
