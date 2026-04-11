import urllib.request
import os
import random
import time
from collections import deque, Counter
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

BaseOptions = mp_python.BaseOptions
HandLandmarker = vision.HandLandmarker
HandLandmarkerOptions = vision.HandLandmarkerOptions
VisionRunningMode = vision.RunningMode

# --- Modèle ---
MODEL_PATH = "hand_landmarker_full.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
)

MOVEMENT_THRESHOLD = 15   # pixels
PINCH_THRESHOLD    = 50   # pixels — distance pouce/index pour considérer un pincement
BUBBLE_RADIUS      = 40   # pixels
POP_DURATION       = 18   # frames d'animation d'éclatement
BUBBLE_COUNT       = 5    # nombre de bulles simultanées (démo B)
GAME_DURATION      = 30   # secondes par partie (démo B)

# Démo D — dessin dans l'air
DRAW_COLORS = [
    (255, 255, 255),  # blanc
    (100, 255, 100),  # vert
    (100, 100, 255),  # rouge
    (0,   220, 255),  # jaune
    (255, 100, 200),  # violet
    (50,  200, 255),  # orange
]
DRAW_THICKNESS = 3

# Démo C — bulle physique
BUBBLE_RADIUS_C = 50
PUSH_RADIUS     = BUBBLE_RADIUS_C + 50  # zone de contact autour de la bulle
PUSH_FACTOR     = 0.45                  # intensité de la poussée
DAMPING         = 0.97                  # friction par frame
MAX_VEL         = 28                    # vitesse maximale en px/frame

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]

FINGERTIPS = [4, 8, 12, 16, 20]

FILAMENT_COLORS = [
    (255, 180,   0),
    (0,   255, 180),
    (180,   0, 255),
    (0,   200, 255),
    (255,  50, 150),
]

# Couleurs possibles pour les bulles (BGR)
BUBBLE_PALETTE = [
    (255,  80, 120),  # rose
    (80,  200, 255),  # jaune
    (255, 180,  50),  # cyan
    (120, 255, 100),  # vert
    (200,  80, 255),  # violet
    (80,  160, 255),  # orange
]

clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def download_model():
    if not os.path.exists(MODEL_PATH):
        print(f"Téléchargement du modèle vers {MODEL_PATH} ...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Modèle téléchargé.")


def enhance_frame(frame):
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def draw_hand(frame, hand_landmarks, w, h):
    for start, end in HAND_CONNECTIONS:
        x1, y1 = int(hand_landmarks[start].x * w), int(hand_landmarks[start].y * h)
        x2, y2 = int(hand_landmarks[end].x * w),   int(hand_landmarks[end].y * h)
        cv2.line(frame, (x1, y1), (x2, y2), (0, 200, 0), 2)
    for lm in hand_landmarks:
        cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 4, (255, 255, 255), -1)


def palm_center(hand_landmarks, w, h):
    lm = hand_landmarks[9]
    return int(lm.x * w), int(lm.y * h)


def draw_filaments(frame, left_lm, right_lm, w, h):
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


# ---------------------------------------------------------------------------
# Bulle (démo B — éclatement par pincement)
# ---------------------------------------------------------------------------

def new_bubble(w, h, existing=None):
    """Crée une bulle à une position qui ne chevauche pas les bulles existantes."""
    margin = BUBBLE_RADIUS + 20
    existing = existing or []
    for _ in range(30):  # 30 tentatives max
        cx = random.randint(margin, w - margin)
        cy = random.randint(margin + 80, h - margin - 60)
        if all(((cx - b["cx"]) ** 2 + (cy - b["cy"]) ** 2) ** 0.5 > BUBBLE_RADIUS * 2.5
               for b in existing):
            break
    return {"cx": cx, "cy": cy, "r": BUBBLE_RADIUS, "color": random.choice(BUBBLE_PALETTE)}


def draw_bubble(frame, bubble):
    cx, cy, r, color = bubble["cx"], bubble["cy"], bubble["r"], bubble["color"]

    # Corps translucide
    overlay = frame.copy()
    cv2.circle(overlay, (cx, cy), r, color, -1)
    cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)

    # Contour lumineux
    cv2.circle(frame, (cx, cy), r, color, 2)

    # Reflet principal (ellipse blanche, haut-gauche)
    hl_x, hl_y = cx - r // 3, cy - r // 3
    axes = (max(r // 4, 4), max(r // 6, 3))
    cv2.ellipse(frame, (hl_x, hl_y), axes, -35, 0, 360, (255, 255, 255), -1)

    # Petit point brillant secondaire
    cv2.circle(frame, (cx + r // 4, cy + r // 4), max(r // 10, 2), (255, 255, 255), -1)


def draw_pop(frame, pop):
    """Animation d'éclatement : anneaux expansifs qui s'estompent."""
    t = 1.0 - pop["frames_left"] / POP_DURATION   # 0 → 1
    cx, cy = pop["cx"], pop["cy"]
    color  = pop["color"]

    for i in range(5):
        offset = i / 5
        progress = min(t + offset * 0.3, 1.0)
        ring_r   = int(BUBBLE_RADIUS * (1 + progress * 3))
        alpha    = max(0.0, 1.0 - progress * 1.5)
        thickness = max(1, int(3 * (1 - progress)))

        ring_layer = frame.copy()
        cv2.circle(ring_layer, (cx, cy), ring_r, color, thickness)
        cv2.addWeighted(ring_layer, alpha * 0.7, frame, 1 - alpha * 0.7, 0, frame)

    # Étincelles
    rng = np.random.default_rng(seed=int(t * 100))
    for _ in range(8):
        angle = rng.uniform(0, 2 * np.pi)
        dist  = int(BUBBLE_RADIUS * (1 + t * 2.5) * rng.uniform(0.6, 1.0))
        sx    = cx + int(np.cos(angle) * dist)
        sy    = cy + int(np.sin(angle) * dist)
        spark_r = max(1, int(4 * (1 - t)))
        cv2.circle(frame, (sx, sy), spark_r, (255, 255, 255), -1)


# ---------------------------------------------------------------------------
# Dessin dans l'air (démo D)
# ---------------------------------------------------------------------------

def is_index_only(lm):
    """Index étendu, majeur/annulaire/auriculaire repliés."""
    return (lm[8].y  < lm[6].y  and
            lm[12].y > lm[10].y and
            lm[16].y > lm[14].y and
            lm[20].y > lm[18].y)


def is_open_hand(lm):
    """Les 4 doigts étendus = main ouverte → effacer."""
    return (lm[8].y  < lm[6].y  and
            lm[12].y < lm[10].y and
            lm[16].y < lm[14].y and
            lm[20].y < lm[18].y)


def draw_palette(frame, color_idx, w):
    """Barre de couleurs en haut à droite pour la démo D."""
    sw = 28  # largeur d'un carré
    gap = 4
    total = len(DRAW_COLORS) * (sw + gap) - gap
    x0 = w - total - 10
    y0 = 40
    for i, color in enumerate(DRAW_COLORS):
        x = x0 + i * (sw + gap)
        cv2.rectangle(frame, (x, y0), (x + sw, y0 + sw), color, -1)
        if i == color_idx:
            cv2.rectangle(frame, (x - 2, y0 - 2), (x + sw + 2, y0 + sw + 2),
                          (255, 255, 255), 2)
    return x0, y0, sw, gap


# ---------------------------------------------------------------------------
# Bulle physique (démo C — poussée par l'index)
# ---------------------------------------------------------------------------

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
    """Applique une impulsion à la bulle proportionnelle à la vitesse de l'index."""
    dx   = bubble["cx"] - ix
    dy   = bubble["cy"] - iy
    dist = (dx ** 2 + dy ** 2) ** 0.5

    if dist < PUSH_RADIUS:
        # Impulsion = vitesse de l'index
        bubble["vx"] += (ix - prev_ix) * PUSH_FACTOR
        bubble["vy"] += (iy - prev_iy) * PUSH_FACTOR

        # Répulsion directe si l'index est à l'intérieur de la bulle
        if 0 < dist < bubble["r"] + 10:
            repulse = (bubble["r"] + 10 - dist) * 0.6
            bubble["vx"] += (dx / dist) * repulse
            bubble["vy"] += (dy / dist) * repulse


def update_bubble_c(bubble, w, h):
    """Déplace la bulle et gère les rebonds sur les bords."""
    bubble["cx"] += bubble["vx"]
    bubble["cy"] += bubble["vy"]

    r = bubble["r"]
    ui_top, ui_bot = 80, 42   # hauteur des bandeaux UI

    if bubble["cx"] - r < 0:
        bubble["cx"] = float(r)
        bubble["vx"] = abs(bubble["vx"])
    elif bubble["cx"] + r > w:
        bubble["cx"] = float(w - r)
        bubble["vx"] = -abs(bubble["vx"])

    if bubble["cy"] - r < ui_top:
        bubble["cy"] = float(ui_top + r)
        bubble["vy"] = abs(bubble["vy"])
    elif bubble["cy"] + r > h - ui_bot:
        bubble["cy"] = float(h - ui_bot - r)
        bubble["vy"] = -abs(bubble["vy"])

    # Amortissement
    bubble["vx"] *= DAMPING
    bubble["vy"] *= DAMPING

    # Limite de vitesse
    speed = (bubble["vx"] ** 2 + bubble["vy"] ** 2) ** 0.5
    if speed > MAX_VEL:
        bubble["vx"] = bubble["vx"] / speed * MAX_VEL
        bubble["vy"] = bubble["vy"] / speed * MAX_VEL


def draw_bubble_c(frame, bubble):
    """Dessine la bulle physique avec un anneau de contact visible."""
    cx, cy = int(bubble["cx"]), int(bubble["cy"])
    r, color = bubble["r"], bubble["color"]

    # Zone de poussée (cercle fin et translucide)
    zone_layer = frame.copy()
    cv2.circle(zone_layer, (cx, cy), PUSH_RADIUS, color, 1)
    cv2.addWeighted(zone_layer, 0.15, frame, 0.85, 0, frame)

    # Corps translucide
    overlay = frame.copy()
    cv2.circle(overlay, (cx, cy), r, color, -1)
    cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)

    # Contour + reflets
    cv2.circle(frame, (cx, cy), r, color, 2)
    hl_x, hl_y = cx - r // 3, cy - r // 3
    axes = (max(r // 4, 4), max(r // 6, 3))
    cv2.ellipse(frame, (hl_x, hl_y), axes, -35, 0, 360, (255, 255, 255), -1)
    cv2.circle(frame, (cx + r // 4, cy + r // 4), max(r // 10, 2), (255, 255, 255), -1)

    # Vecteur vitesse (flèche indicative)
    speed = (bubble["vx"] ** 2 + bubble["vy"] ** 2) ** 0.5
    if speed > 1.0:
        scale = min(speed * 3, 60)
        ex = int(cx + bubble["vx"] / speed * scale)
        ey = int(cy + bubble["vy"] / speed * scale)
        cv2.arrowedLine(frame, (cx, cy), (ex, ey), color, 1, tipLength=0.3)


# ---------------------------------------------------------------------------
# Reconnaissance de gestes (démo F)
# ---------------------------------------------------------------------------

GESTURE_SMOOTH = 10   # frames pour confirmer un geste (anti-scintillement)


def _bent(lm, tip, pip):
    return lm[tip].y > lm[pip].y

def _extended(lm, tip, pip):
    return lm[tip].y < lm[pip].y


def detect_gesture(lm):
    """Retourne (nom, couleur_BGR) du geste détecté, ou (None, None)."""
    index_ext  = _extended(lm,  8,  6)
    middle_ext = _extended(lm, 12, 10)
    ring_ext   = _extended(lm, 16, 14)
    pinky_ext  = _extended(lm, 20, 18)
    # Pouce vraiment levé : tip au-dessus de ses articulations ET au-dessus
    # du MCP de l'index (landmark 5) — écarte le cas du pouce replié sur le poing
    thumb_up   = lm[4].y < lm[3].y and lm[4].y < lm[2].y and lm[4].y < lm[5].y

    # Pouce levé : pouce vers le haut, 4 doigts repliés
    if thumb_up and not index_ext and not middle_ext and not ring_ext and not pinky_ext:
        return "Pouce leve !", (0, 200, 255)

    # Victoire : index + majeur étendus, annulaire + auriculaire repliés
    if index_ext and middle_ext and not ring_ext and not pinky_ext:
        return "Victoire !", (100, 255, 100)

    # Poing : tous les doigts repliés (pouce non étendu vers le haut)
    if not index_ext and not middle_ext and not ring_ext and not pinky_ext and not thumb_up:
        return "Poing !", (80, 80, 255)

    # Main ouverte : tous les doigts étendus
    if index_ext and middle_ext and ring_ext and pinky_ext:
        return "Main ouverte", (255, 200, 50)

    # Metal : index + auriculaire étendus, majeur + annulaire repliés
    if index_ext and not middle_ext and not ring_ext and pinky_ext:
        return "Metal !", (0, 80, 255)

    # Index pointé : index étendu seul
    if index_ext and not middle_ext and not ring_ext and not pinky_ext:
        return "Index pointe", (200, 100, 255)

    return None, None


def draw_gesture_label(frame, name, color, cx, cy, w, h):
    """Affiche le nom du geste dans un bandeau centré sous la main."""
    font       = cv2.FONT_HERSHEY_SIMPLEX
    scale      = 1.1
    thickness  = 3
    (tw, th), _ = cv2.getTextSize(name, font, scale, thickness)
    pad        = 14
    bx         = max(pad, min(cx - tw // 2, w - tw - pad))
    by         = min(cy + 60, h - 60)

    # Fond arrondi (rectangle + cercles aux coins)
    rx1, ry1 = bx - pad, by - th - pad
    rx2, ry2 = bx + tw + pad, by + pad
    overlay   = frame.copy()
    cv2.rectangle(overlay, (rx1, ry1), (rx2, ry2), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)
    cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), color, 2)
    cv2.putText(frame, name, (bx, by), font, scale, color, thickness)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    download_model()

    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=VisionRunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Erreur : impossible d'ouvrir la webcam.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)

    # Lire la résolution réelle après configuration
    w_cam = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h_cam = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    prev_positions  = {}
    show_filaments  = False
    show_bubble     = False
    bubbles         = []      # liste de bulles actives
    pops            = []      # animations d'éclatement en cours
    score           = 0
    game_start      = None    # timestamp de début de partie
    show_demo_c     = False
    bubble_c        = None
    prev_index_c    = {}      # idx -> (x, y) frame précédente
    show_demo_d     = False
    canvas          = None    # calque de dessin persistant
    prev_draw_pos   = {}      # idx -> (x, y) frame précédente
    draw_color_idx  = 0       # index dans DRAW_COLORS
    erase_flash     = 0       # nb de frames du flash d'effacement
    show_demo_f     = False
    gesture_history = {}      # idx -> deque des N dernières détections

    with HandLandmarker.create_from_options(options) as landmarker:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]

            enhanced = enhance_frame(frame)
            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB),
            )
            results = landmarker.detect_for_video(mp_image, timestamp_ms)

            status_text  = "Aucune main detectee"
            status_color = (200, 200, 200)
            current_positions = {}
            hands_by_side     = {}

            for idx, hand_landmarks in enumerate(results.hand_landmarks or []):
                draw_hand(frame, hand_landmarks, w, h)

                cx, cy = palm_center(hand_landmarks, w, h)
                current_positions[idx] = (cx, cy)
                cv2.circle(frame, (cx, cy), 7, (255, 0, 0), -1)

                if idx in prev_positions:
                    px, py = prev_positions[idx]
                    dist = ((cx - px) ** 2 + (cy - py) ** 2) ** 0.5
                    if dist > MOVEMENT_THRESHOLD:
                        status_text  = f"Mouvement detecte !  ({dist:.0f} px)"
                        status_color = (0, 80, 255)
                        cv2.arrowedLine(frame, (px, py), (cx, cy), (0, 0, 255), 2, tipLength=0.4)
                    else:
                        status_text  = "Main immobile"
                        status_color = (0, 220, 0)
                else:
                    status_text = "Main detectee"

                if results.handedness and idx < len(results.handedness):
                    side = results.handedness[idx][0].display_name
                    hands_by_side[side] = hand_landmarks

                # --- Démo D : dessin dans l'air ---
                if show_demo_d and canvas is not None:
                    ix = int(hand_landmarks[8].x * w)
                    iy = int(hand_landmarks[8].y * h)
                    px_pinky = int(hand_landmarks[20].x * w)
                    py_pinky = int(hand_landmarks[20].y * h)
                    color = DRAW_COLORS[draw_color_idx]

                    if is_open_hand(hand_landmarks):
                        canvas[:] = 0
                        erase_flash = 12
                        prev_draw_pos.pop(idx, None)

                    else:
                        # Sélection couleur : petit doigt (landmark 20) sur la palette
                        x0, y0, sw, gap = draw_palette(frame, draw_color_idx, w)
                        for i in range(len(DRAW_COLORS)):
                            bx = x0 + i * (sw + gap)
                            if bx <= px_pinky <= bx + sw and y0 <= py_pinky <= y0 + sw:
                                draw_color_idx = i
                                color = DRAW_COLORS[i]
                                prev_draw_pos.pop(idx, None)
                                break

                        # Dessin : index seul étendu
                        if is_index_only(hand_landmarks):
                            if idx in prev_draw_pos:
                                cv2.line(canvas, prev_draw_pos[idx], (ix, iy),
                                         color, DRAW_THICKNESS)
                            prev_draw_pos[idx] = (ix, iy)
                            # Curseur à l'extrémité de l'index
                            cv2.circle(frame, (ix, iy), 8, color, -1)
                            cv2.circle(frame, (ix, iy), 8, (255, 255, 255), 1)
                        else:
                            prev_draw_pos.pop(idx, None)

                # --- Démo F : reconnaissance de gestes ---
                if show_demo_f:
                    name, gcolor = detect_gesture(hand_landmarks)
                    if idx not in gesture_history:
                        gesture_history[idx] = deque(maxlen=GESTURE_SMOOTH)
                    gesture_history[idx].append((name, gcolor))

                # --- Démo C : poussée de la bulle par l'index ---
                if show_demo_c and bubble_c is not None:
                    ix = int(hand_landmarks[8].x * w)
                    iy = int(hand_landmarks[8].y * h)
                    if idx in prev_index_c:
                        push_bubble_c(bubble_c, ix, iy, *prev_index_c[idx])
                    prev_index_c[idx] = (ix, iy)

                # --- Détection du pincement pouce/index (démo B) ---
                if show_bubble and bubbles:
                    tx = int(hand_landmarks[4].x * w)
                    ty = int(hand_landmarks[4].y * h)
                    ix = int(hand_landmarks[8].x * w)
                    iy = int(hand_landmarks[8].y * h)
                    pinch_dist = ((tx - ix) ** 2 + (ty - iy) ** 2) ** 0.5
                    mid_x, mid_y = (tx + ix) // 2, (ty + iy) // 2

                    if pinch_dist < PINCH_THRESHOLD:
                        for b in bubbles[:]:
                            if ((mid_x - b["cx"]) ** 2 + (mid_y - b["cy"]) ** 2) ** 0.5 < b["r"] + 20:
                                pops.append({"cx": b["cx"], "cy": b["cy"],
                                             "color": b["color"], "frames_left": POP_DURATION})
                                bubbles.remove(b)
                                score += 1
                                bubbles.append(new_bubble(w, h, bubbles))
                                break

            prev_positions = current_positions
            if not show_demo_c:
                prev_index_c.clear()

            # --- Filaments ---
            if show_filaments and "Left" in hands_by_side and "Right" in hands_by_side:
                draw_filaments(frame, hands_by_side["Left"], hands_by_side["Right"], w, h)

            # --- Démo B : bulles + score + minuterie ---
            if show_bubble:
                now = time.time()
                elapsed = now - game_start
                remaining = max(0, GAME_DURATION - elapsed)

                if remaining > 0:
                    for b in bubbles:
                        draw_bubble(frame, b)
                else:
                    # Temps écoulé — afficher l'écran de fin par-dessus
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

                # HUD score + minuterie
                bar_w = int((remaining / GAME_DURATION) * 300)
                bar_color = (0, 220, 0) if remaining > 10 else (0, 80, 255)
                cv2.rectangle(frame, (w//2 - 150, 12), (w//2 + 150, 30), (60, 60, 60), -1)
                cv2.rectangle(frame, (w//2 - 150, 12), (w//2 - 150 + bar_w, 30), bar_color, -1)
                cv2.putText(frame, f"{int(remaining)}s", (w//2 - 20, 27),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
                cv2.putText(frame, f"Score : {score}", (w//2 + 160, 27),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 255, 180), 2)

            # --- Démo D : rendu du canvas + flash effacement ---
            if show_demo_d and canvas is not None:
                frame[:] = cv2.add(frame, canvas)
                draw_palette(frame, draw_color_idx, w)

                if erase_flash > 0:
                    flash = frame.copy()
                    cv2.rectangle(flash, (0, 0), (w, h), (255, 255, 255), -1)
                    alpha = erase_flash / 12 * 0.35
                    cv2.addWeighted(flash, alpha, frame, 1 - alpha, 0, frame)
                    cv2.putText(frame, "EFFACE !", (w // 2 - 80, h // 2),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 200), 3)
                    erase_flash -= 1

            # --- Démo C ---
            if show_demo_c and bubble_c is not None:
                update_bubble_c(bubble_c, w, h)
                draw_bubble_c(frame, bubble_c)

            # --- Démo F : affichage des gestes lissés ---
            if show_demo_f:
                active_ids = set(range(len(results.hand_landmarks or [])))
                for idx in list(gesture_history.keys()):
                    if idx not in active_ids:
                        del gesture_history[idx]
                        continue
                    history = gesture_history[idx]
                    counts  = Counter(name for name, _ in history if name is not None)
                    if not counts:
                        continue
                    best, freq = counts.most_common(1)[0]
                    if freq >= GESTURE_SMOOTH // 2:
                        # Récupérer la couleur associée au geste majoritaire
                        gcolor = next(
                            (c for n, c in history if n == best and c is not None),
                            (200, 200, 200),
                        )
                        pcx, pcy = current_positions.get(idx, (w // 2, h // 2))
                        draw_gesture_label(frame, best, gcolor, pcx, pcy, w, h)

            # --- UI ---
            cv2.rectangle(frame, (0, h - 42), (w, h), (30, 30, 30), -1)
            cv2.putText(frame, status_text, (10, h - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, status_color, 2)

            fil_label = "Filaments : ON" if show_filaments else "Filaments : OFF"
            fil_color = (0, 220, 255) if show_filaments else (120, 120, 120)
            cv2.putText(frame, fil_label, (10, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, fil_color, 2)

            bub_label = "Bulles : ON" if show_bubble else "Bulles : OFF"
            bub_color = (100, 255, 180) if show_bubble else (120, 120, 120)
            cv2.putText(frame, bub_label, (10, 58),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, bub_color, 2)

            phy_label = "Physique : ON" if show_demo_c else "Physique : OFF"
            phy_color = (50, 200, 255) if show_demo_c else (120, 120, 120)
            cv2.putText(frame, phy_label, (10, 88),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, phy_color, 2)

            des_label = "Dessin : ON" if show_demo_d else "Dessin : OFF"
            des_color = (180, 255, 180) if show_demo_d else (120, 120, 120)
            cv2.putText(frame, des_label, (10, 118),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, des_color, 2)

            ges_label = "Gestes : ON" if show_demo_f else "Gestes : OFF"
            ges_color = (80, 180, 255) if show_demo_f else (120, 120, 120)
            cv2.putText(frame, ges_label, (10, 148),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, ges_color, 2)

            cv2.putText(frame, "a:filaments b:bulles c:physique d:dessin f:gestes q:quitter",
                        (w - 640, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.47, (180, 180, 180), 1)

            cv2.imshow("Detection de mouvement de la main", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("a"):
                show_filaments = not show_filaments
            elif key == ord("b"):
                show_bubble = not show_bubble
                if show_bubble:
                    bubbles    = [new_bubble(w, h, [])]
                    for _ in range(BUBBLE_COUNT - 1):
                        bubbles.append(new_bubble(w, h, bubbles))
                    pops       = []
                    score      = 0
                    game_start = time.time()
                else:
                    bubbles    = []
                    pops       = []
                    score      = 0
                    game_start = None
            elif key == ord("c"):
                show_demo_c = not show_demo_c
                if show_demo_c:
                    bubble_c = new_bubble_c(w, h)
                else:
                    bubble_c = None
                    prev_index_c.clear()
            elif key == ord("d"):
                show_demo_d = not show_demo_d
                if show_demo_d:
                    canvas = np.zeros((h, w, 3), dtype=np.uint8)
                    prev_draw_pos.clear()
                    erase_flash = 0
                else:
                    canvas = None
                    prev_draw_pos.clear()
            elif key == ord("f"):
                show_demo_f = not show_demo_f
                if not show_demo_f:
                    gesture_history.clear()

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
