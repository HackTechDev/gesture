"""Démo L — Puzzle : reconstituer linux.jpg.

Contrôles :
  Index pointé   → attraper / déplacer une pièce
  Poing          → déposer la pièce à l'endroit choisi
  Magnétisme     → si la pièce est proche de sa case cible, elle se cale automatiquement
"""
import math
import random
import time
import cv2
import numpy as np

IMAGE_PATH    = "linux.jpg"
GRID_ROWS     = 3
GRID_COLS     = 3
N_PIECES      = GRID_ROWS * GRID_COLS
SNAP_DIST     = 100    # px — distance de magnétisme vers la case cible
TIMER_SECONDS = 180   # durée du puzzle en secondes (3 min)

# Couleurs
_C_GRID    = (70,  70,  70)    # quadrillage cible
_C_FREE    = (160, 160, 160)   # contour pièce libre
_C_HELD    = (0,   200, 255)   # contour pièce tenue
_C_PLACED  = (0,   220, 80)    # contour pièce posée


# ── API publique ───────────────────────────────────────────────────────────────

def new_puzzle(w, h):
    """Charge l'image, découpe en 9 pièces et les disperse aléatoirement."""
    img = cv2.imread(IMAGE_PATH)
    if img is None:
        return None

    # Redimensionne l'image pour occuper ~40 % de la fenêtre (espace latéral pour les pièces)
    ih, iw = img.shape[:2]
    scale  = min(w * 0.40 / iw, h * 0.40 / ih)
    new_w  = int(iw * scale)
    new_h  = int(ih * scale)
    img    = cv2.resize(img, (new_w, new_h))

    pw = new_w // GRID_COLS
    ph = new_h // GRID_ROWS

    # Centre de la grille cible au milieu de la fenêtre
    gx = (w - pw * GRID_COLS) // 2
    gy = (h - ph * GRID_ROWS) // 2

    # Zones de placement : côtés gauche et droit, pas sous la grille
    margin = 10
    lx0 = 5
    lx1 = max(lx0, gx - pw - margin)
    rx0 = gx + pw * GRID_COLS + margin
    rx1 = w - pw - 5
    py0 = 5
    py1 = max(py0 + 1, gy + ph * (GRID_ROWS - 1))  # haut de la dernière rangée

    half  = N_PIECES // 2
    sides = ["left"] * (N_PIECES - half) + ["right"] * half
    random.shuffle(sides)

    pieces = []
    side_idx = 0
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            piece_img = img[row * ph:(row + 1) * ph,
                            col * pw:(col + 1) * pw].copy()
            if sides[side_idx] == "left":
                px = random.randint(lx0, lx1)
            else:
                px = random.randint(rx0, max(rx0, rx1))
            py = random.randint(py0, py1)
            pieces.append({
                "img":      piece_img,
                "grid_pos": (row, col),
                "pos":      [float(px), float(py)],
                "placed":   False,
            })
            side_idx += 1

    random.shuffle(pieces)

    return {
        "pieces":      pieces,
        "held":        None,
        "piece_w":     pw,
        "piece_h":     ph,
        "grid_origin": (gx, gy),
        "complete":    False,
        "start_time":  time.time(),
        "timeout":     False,
    }


def update(puzzle, hands_by_side, w, h):
    """Gère le drag-and-drop des pièces via l'index et le poing."""
    if puzzle is None or puzzle["complete"] or puzzle["timeout"]:
        return

    elapsed = time.time() - puzzle["start_time"]
    if elapsed >= TIMER_SECONDS:
        puzzle["timeout"] = True
        puzzle["held"] = None
        return

    pw = puzzle["piece_w"]
    ph = puzzle["piece_h"]
    gx, gy = puzzle["grid_origin"]

    # Main prioritaire : droite, sinon gauche
    lm = hands_by_side.get("Right") or hands_by_side.get("Left")
    if lm is None:
        return

    ix = int(lm[8].x * w)
    iy = int(lm[8].y * h)
    pointing = _is_pointing(lm)
    fist     = _is_fist(lm)

    held = puzzle["held"]

    if fist and held is not None:
        # ── Dépose ──────────────────────────────────────────────────────────
        piece = puzzle["pieces"][held]
        row, col = piece["grid_pos"]
        tx = gx + col * pw
        ty = gy + row * ph
        if math.hypot(piece["pos"][0] - tx, piece["pos"][1] - ty) < SNAP_DIST:
            piece["pos"]    = [float(tx), float(ty)]
            piece["placed"] = True
        puzzle["held"] = None

    elif pointing and held is None:
        # ── Attrape ─────────────────────────────────────────────────────────
        # Parcours de la fin (pièce du dessus) vers le début
        for i in range(len(puzzle["pieces"]) - 1, -1, -1):
            p = puzzle["pieces"][i]
            if p["placed"]:
                continue
            px, py = p["pos"]
            if px <= ix <= px + pw and py <= iy <= py + ph:
                puzzle["held"] = i
                # Remonte la pièce en fin de liste (rendu au-dessus)
                puzzle["pieces"].append(puzzle["pieces"].pop(i))
                puzzle["held"] = len(puzzle["pieces"]) - 1
                break

    elif pointing and held is not None:
        # ── Déplace ─────────────────────────────────────────────────────────
        p = puzzle["pieces"][held]
        p["pos"] = [float(ix - pw // 2), float(iy - ph // 2)]

    # Vérification complétion
    if all(p["placed"] for p in puzzle["pieces"]):
        puzzle["complete"] = True


def render(frame, puzzle, w, h):
    """Dessine la grille cible, les pièces et le message de victoire."""
    if puzzle is None:
        cv2.putText(frame, f"Image '{IMAGE_PATH}' introuvable",
                    (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 60, 255), 2)
        return

    pw = puzzle["piece_w"]
    ph = puzzle["piece_h"]
    gx, gy = puzzle["grid_origin"]
    held = puzzle["held"]

    # ── 1. Grille cible ───────────────────────────────────────────────────────
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            tx = gx + col * pw
            ty = gy + row * ph
            cv2.rectangle(frame, (tx, ty), (tx + pw, ty + ph), _C_GRID, 1)

    # ── 2. Pièces posées ──────────────────────────────────────────────────────
    for p in puzzle["pieces"]:
        if not p["placed"]:
            continue
        x, y = int(p["pos"][0]), int(p["pos"][1])
        _blit(frame, p["img"], x, y)
        cv2.rectangle(frame, (x, y), (x + pw, y + ph), _C_PLACED, 2)

    # ── 3. Pièces libres (non tenues) ─────────────────────────────────────────
    for i, p in enumerate(puzzle["pieces"]):
        if p["placed"] or i == held:
            continue
        x, y = int(p["pos"][0]), int(p["pos"][1])
        _blit(frame, p["img"], x, y)
        cv2.rectangle(frame, (x, y), (x + pw, y + ph), _C_FREE, 1)

    # ── 4. Pièce tenue (au-dessus + surbrillance) ─────────────────────────────
    if held is not None:
        p = puzzle["pieces"][held]
        x, y = int(p["pos"][0]), int(p["pos"][1])
        # Halo cyan semi-transparent
        ov = frame.copy()
        cv2.rectangle(ov, (x - 3, y - 3),
                      (x + pw + 3, y + ph + 3), _C_HELD, -1)
        cv2.addWeighted(ov, 0.18, frame, 0.82, 0, frame)
        _blit(frame, p["img"], x, y)
        cv2.rectangle(frame, (x, y), (x + pw, y + ph), _C_HELD, 2)

    # ── 5. Compteur de pièces posées ─────────────────────────────────────────
    placed = sum(1 for p in puzzle["pieces"] if p["placed"])
    cv2.putText(frame, f"{placed} / {N_PIECES}",
                (w - 90, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (200, 200, 200), 2)

    # ── 6. Timer ──────────────────────────────────────────────────────────────
    elapsed  = time.time() - puzzle["start_time"]
    remain   = max(0.0, TIMER_SECONDS - elapsed)
    mins     = int(remain) // 60
    secs     = int(remain) % 60
    timer_str = f"{mins}:{secs:02d}"
    # Couleur : vert → orange → rouge selon le temps restant
    if remain > 60:
        t_color = (80, 220, 80)
    elif remain > 30:
        t_color = (0, 165, 255)
    else:
        t_color = (0, 50, 255)
    (tw, _), _ = cv2.getTextSize(timer_str, cv2.FONT_HERSHEY_SIMPLEX, 1.1, 2)
    cv2.putText(frame, timer_str, ((w - tw) // 2, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1.1, t_color, 2)

    # ── 7. Message de victoire ────────────────────────────────────────────────
    if puzzle["complete"]:
        elapsed_total = time.time() - puzzle["start_time"]
        m = int(elapsed_total) // 60
        s = int(elapsed_total) % 60
        msg = f"Puzzle termine !  {m}:{s:02d}"
        (tw, th), _ = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, 1.4, 3)
        tx = (w - tw) // 2
        ty = (h + th) // 2
        cv2.putText(frame, msg, (tx + 2, ty + 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 0), 5)
        cv2.putText(frame, msg, (tx, ty),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 255, 180), 3)

    # ── 8. Message temps écoulé ───────────────────────────────────────────────
    elif puzzle["timeout"]:
        placed = sum(1 for p in puzzle["pieces"] if p["placed"])
        msg = f"Temps ecoule !  {placed}/{N_PIECES} pieces"
        (tw, th), _ = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)
        tx = (w - tw) // 2
        ty = (h + th) // 2
        cv2.putText(frame, msg, (tx + 2, ty + 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 5)
        cv2.putText(frame, msg, (tx, ty),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 80, 255), 3)


# ── Détection de gestes ───────────────────────────────────────────────────────

def _is_pointing(lm):
    """Index seul étendu (majeur, annulaire, auriculaire repliés)."""
    return (lm[8].y  < lm[6].y  and   # index étendu
            lm[12].y > lm[10].y and   # majeur replié
            lm[16].y > lm[14].y and   # annulaire replié
            lm[20].y > lm[18].y)      # auriculaire replié


def _is_fist(lm):
    """Tous les doigts repliés."""
    return (lm[8].y  > lm[6].y  and
            lm[12].y > lm[10].y and
            lm[16].y > lm[14].y and
            lm[20].y > lm[18].y)


# ── Utilitaire ────────────────────────────────────────────────────────────────

def _blit(frame, img, x, y):
    """Copie img sur frame à (x, y) en gérant les bords."""
    fh, fw = frame.shape[:2]
    ih, iw = img.shape[:2]
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(fw, x + iw), min(fh, y + ih)
    if x2 <= x1 or y2 <= y1:
        return
    frame[y1:y2, x1:x2] = img[y1 - y:y2 - y, x1 - x:x2 - x]
