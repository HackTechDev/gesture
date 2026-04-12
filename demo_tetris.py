"""Démo Tetris — Jeu de Tetris contrôlé par les gestes de la main.

Contrôles :
  Index pointé + déplacement horizontal  → déplacer la pièce gauche / droite
  Poing (tous doigts repliés)            → chute rapide
  Main ouverte (4 doigts étendus)        → rotation de la pièce (sens horaire)
"""
import random
import time
import cv2

COLS = 10
ROWS = 20

_FALL_DELAYS = [0.80, 0.65, 0.50, 0.38, 0.28, 0.20, 0.14, 0.10, 0.08, 0.06]
_FAST_DELAY  = 0.04
_MOVE_DELAY  = 0.13   # secondes min entre deux déplacements horizontaux

# Couleurs BGR des tétrominos
_COLORS = [
    (200, 200,   0),   # I — cyan
    (  0, 220, 220),   # O — jaune
    (180,   0, 180),   # T — violet
    (  0, 200,   0),   # S — vert
    (  0,   0, 220),   # Z — rouge
    (200, 100,   0),   # J — bleu
    (  0, 140, 255),   # L — orange
]

_SHAPES = [
    [[1, 1, 1, 1]],                  # I
    [[1, 1], [1, 1]],                # O
    [[0, 1, 0], [1, 1, 1]],         # T
    [[0, 1, 1], [1, 1, 0]],         # S
    [[1, 1, 0], [0, 1, 1]],         # Z
    [[1, 0, 0], [1, 1, 1]],         # J
    [[0, 0, 1], [1, 1, 1]],         # L
]

_SCORE_TABLE = [0, 100, 300, 500, 800]


# ── API publique ───────────────────────────────────────────────────────────────

def new_tetris(w, h):
    """Initialise une nouvelle partie."""
    cell = max(16, min(30, (h - 60) // ROWS))
    return {
        "cell":         cell,
        "board":        [[None] * COLS for _ in range(ROWS)],
        "current":      _new_piece(),
        "next":         _new_piece(),
        "score":        0,
        "lines":        0,
        "level":        0,
        "game_over":    False,
        "last_fall":    time.time(),
        "last_move":    0.0,
        "fast_drop":    False,
        "prev_open":    False,
        "rot_cooldown": 0.0,
    }


def update(tetris, hands_by_side, w, h):
    """Met à jour la logique du jeu selon les gestes détectés."""
    if tetris is None or tetris["game_over"]:
        return

    lm = hands_by_side.get("Right") or hands_by_side.get("Left")

    if lm is not None:
        ix       = int(lm[8].x * w)
        pointing = _is_pointing(lm)
        fist     = _is_fist(lm)
        open_h   = _is_open(lm)

        # ── Déplacement horizontal ────────────────────────────────────────────
        if pointing:
            now = time.time()
            if now - tetris["last_move"] >= _MOVE_DELAY:
                target = int(ix / w * COLS)
                target = max(0, min(COLS - 1, target))
                p  = tetris["current"]
                pw = len(p["shape"][0])
                mid = p["x"] + pw // 2
                if mid < target:
                    _try_move(tetris, 1)
                    tetris["last_move"] = now
                elif mid > target:
                    _try_move(tetris, -1)
                    tetris["last_move"] = now

        # ── Rotation (front montant du geste main ouverte) ────────────────────
        now = time.time()
        if open_h and not tetris["prev_open"] and now > tetris["rot_cooldown"]:
            _try_rotate(tetris)
            tetris["rot_cooldown"] = now + 0.35
        tetris["prev_open"] = open_h

        # ── Chute rapide ──────────────────────────────────────────────────────
        tetris["fast_drop"] = fist
    else:
        tetris["fast_drop"] = False
        tetris["prev_open"] = False

    _apply_gravity(tetris)


def render(frame, tetris, w, h):
    """Dessine le plateau, la pièce courante et le panneau d'info."""
    if tetris is None:
        return

    cell = tetris["cell"]
    bw   = COLS * cell
    bh   = ROWS * cell
    bx   = (w - bw) // 2
    by   = (h - bh) // 2

    # ── Fond semi-transparent du plateau ──────────────────────────────────────
    ov = frame.copy()
    cv2.rectangle(ov, (bx - 3, by - 3), (bx + bw + 3, by + bh + 3), (12, 12, 12), -1)
    cv2.addWeighted(ov, 0.72, frame, 0.28, 0, frame)

    # ── Grille et cellules posées ─────────────────────────────────────────────
    for r in range(ROWS):
        for c in range(COLS):
            color = tetris["board"][r][c]
            cx = bx + c * cell
            cy = by + r * cell
            cv2.rectangle(frame, (cx, cy), (cx + cell - 1, cy + cell - 1), (40, 40, 40), 1)
            if color is not None:
                cv2.rectangle(frame, (cx + 1, cy + 1),
                              (cx + cell - 2, cy + cell - 2), color, -1)
                lighter = tuple(min(255, v + 70) for v in color)
                cv2.line(frame, (cx + 1, cy + 1), (cx + cell - 2, cy + 1), lighter, 2)
                cv2.line(frame, (cx + 1, cy + 1), (cx + 1, cy + cell - 2), lighter, 2)

    # ── Pièce fantôme (destination de chute) ─────────────────────────────────
    p  = tetris["current"]
    gy = p["y"]
    while not _collides(tetris["board"], p["shape"], p["x"], gy + 1):
        gy += 1
    if gy > p["y"]:
        for r, row in enumerate(p["shape"]):
            for c, val in enumerate(row):
                if val:
                    cx = bx + (p["x"] + c) * cell
                    cy = by + (gy + r) * cell
                    ghost = tuple(max(0, v // 6) for v in p["color"])
                    cv2.rectangle(frame, (cx + 2, cy + 2),
                                  (cx + cell - 3, cy + cell - 3), ghost, 1)

    # ── Pièce courante ────────────────────────────────────────────────────────
    for r, row in enumerate(p["shape"]):
        for c, val in enumerate(row):
            if val:
                cx = bx + (p["x"] + c) * cell
                cy = by + (p["y"] + r) * cell
                if cy + cell > by:
                    cv2.rectangle(frame, (cx + 1, cy + 1),
                                  (cx + cell - 2, cy + cell - 2), p["color"], -1)
                    lighter = tuple(min(255, v + 70) for v in p["color"])
                    cv2.line(frame, (cx + 1, cy + 1), (cx + cell - 2, cy + 1), lighter, 2)
                    cv2.line(frame, (cx + 1, cy + 1), (cx + 1, cy + cell - 2), lighter, 2)

    # ── Bordure du plateau ────────────────────────────────────────────────────
    cv2.rectangle(frame, (bx - 3, by - 3), (bx + bw + 3, by + bh + 3), (160, 160, 160), 2)

    # ── Panneau d'info (à droite du plateau) ─────────────────────────────────
    ix = bx + bw + 14
    _lbl(frame, "Score",   ix, by + 25)
    _val(frame, str(tetris["score"]), ix, by + 52)
    _lbl(frame, "Lignes",  ix, by + 88)
    _val(frame, str(tetris["lines"]), ix, by + 115)
    _lbl(frame, "Niveau",  ix, by + 151)
    _val(frame, str(tetris["level"] + 1), ix, by + 178)

    _lbl(frame, "Suivant", ix, by + 218)
    nxt = tetris["next"]
    cs  = min(cell, 22)
    for r, row in enumerate(nxt["shape"]):
        for c, val in enumerate(row):
            if val:
                cv2.rectangle(frame,
                              (ix + c * cs,        by + 228 + r * cs),
                              (ix + c * cs + cs - 2, by + 228 + r * cs + cs - 2),
                              nxt["color"], -1)

    # ── Game Over ─────────────────────────────────────────────────────────────
    if tetris["game_over"]:
        for msg, scale, dy, color in [
            ("GAME OVER", 1.4, 0,  (0, 50, 255)),
            ("Appuyer sur V pour rejouer", 0.60, 45, (200, 200, 200)),
        ]:
            (tw, th), _ = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, scale, 3)
            tx = (w - tw) // 2
            ty = h // 2 + dy
            cv2.putText(frame, msg, (tx + 2, ty + 2),
                        cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 5)
            cv2.putText(frame, msg, (tx, ty),
                        cv2.FONT_HERSHEY_SIMPLEX, scale, color, 2)


# ── Détection de gestes ───────────────────────────────────────────────────────

def _is_pointing(lm):
    """Index seul étendu."""
    return (lm[8].y  < lm[6].y  and
            lm[12].y > lm[10].y and
            lm[16].y > lm[14].y and
            lm[20].y > lm[18].y)


def _is_fist(lm):
    """Tous les doigts repliés."""
    return (lm[8].y  > lm[6].y  and
            lm[12].y > lm[10].y and
            lm[16].y > lm[14].y and
            lm[20].y > lm[18].y)


def _is_open(lm):
    """Main ouverte : 4 doigts étendus."""
    return (lm[8].y  < lm[6].y  and
            lm[12].y < lm[10].y and
            lm[16].y < lm[14].y and
            lm[20].y < lm[18].y)


# ── Logique du jeu ────────────────────────────────────────────────────────────

def _new_piece():
    i = random.randrange(len(_SHAPES))
    return {
        "shape": [row[:] for row in _SHAPES[i]],
        "color": _COLORS[i],
        "x":     COLS // 2 - len(_SHAPES[i][0]) // 2,
        "y":     0,
    }


def _collides(board, shape, x, y):
    for r, row in enumerate(shape):
        for c, val in enumerate(row):
            if val:
                nx, ny = x + c, y + r
                if nx < 0 or nx >= COLS or ny >= ROWS:
                    return True
                if ny >= 0 and board[ny][nx] is not None:
                    return True
    return False


def _try_move(tetris, dx):
    p = tetris["current"]
    if not _collides(tetris["board"], p["shape"], p["x"] + dx, p["y"]):
        p["x"] += dx


def _try_rotate(tetris):
    """Rotation horaire + wall-kick basique."""
    p       = tetris["current"]
    rotated = [list(row) for row in zip(*p["shape"][::-1])]
    for kick in (0, 1, -1, 2, -2):
        if not _collides(tetris["board"], rotated, p["x"] + kick, p["y"]):
            p["shape"] = rotated
            p["x"]    += kick
            return


def _apply_gravity(tetris):
    now   = time.time()
    delay = _FAST_DELAY if tetris["fast_drop"] else _FALL_DELAYS[tetris["level"]]
    if now - tetris["last_fall"] < delay:
        return
    p = tetris["current"]
    if _collides(tetris["board"], p["shape"], p["x"], p["y"] + 1):
        _lock(tetris)
    else:
        p["y"] += 1
    tetris["last_fall"] = now


def _lock(tetris):
    p = tetris["current"]
    for r, row in enumerate(p["shape"]):
        for c, val in enumerate(row):
            if val:
                ny = p["y"] + r
                if 0 <= ny < ROWS:
                    tetris["board"][ny][p["x"] + c] = p["color"]
    _clear_lines(tetris)
    tetris["current"] = tetris["next"]
    tetris["next"]    = _new_piece()
    if _collides(tetris["board"], tetris["current"]["shape"],
                 tetris["current"]["x"], tetris["current"]["y"]):
        tetris["game_over"] = True


def _clear_lines(tetris):
    new_board = [row for row in tetris["board"] if any(c is None for c in row)]
    cleared   = ROWS - len(new_board)
    if cleared:
        tetris["board"]  = [[None] * COLS for _ in range(cleared)] + new_board
        tetris["lines"] += cleared
        tetris["score"] += _SCORE_TABLE[min(cleared, 4)] * (tetris["level"] + 1)
        tetris["level"]  = min(9, tetris["lines"] // 10)


# ── Helpers UI ────────────────────────────────────────────────────────────────

def _lbl(frame, text, x, y):
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (150, 150, 150), 1)


def _val(frame, text, x, y):
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (240, 240, 240), 2)
