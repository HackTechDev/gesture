"""Démo Pixel — Zone vidéo pixelisée délimitée par le pouce et l'index des deux mains."""
import cv2
import numpy as np

_PIXEL_SIZE = 16   # taille d'un carré de pixelisation en pixels


def render(frame, hands_by_side, w, h):
    left  = hands_by_side.get("Left")
    right = hands_by_side.get("Right")
    if left is None or right is None:
        return

    # 4 coins : pouce (4) + index (8) de chaque main
    corners = np.array([
        [int(left[4].x  * w), int(left[4].y  * h)],
        [int(left[8].x  * w), int(left[8].y  * h)],
        [int(right[4].x * w), int(right[4].y * h)],
        [int(right[8].x * w), int(right[8].y * h)],
    ], dtype=np.int32)

    # Enveloppe convexe pour un polygone toujours valide
    hull = cv2.convexHull(corners)

    # Masque du polygone
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask, [hull], 255)

    # Bounding box clampée aux bords de la frame
    x, y, bw, bh = cv2.boundingRect(hull)
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(w, x + bw), min(h, y + bh)
    rw, rh = x2 - x1, y2 - y1
    if rw < _PIXEL_SIZE or rh < _PIXEL_SIZE:
        return

    # Pixelisation : réduction puis agrandissement nearest-neighbor
    roi       = frame[y1:y2, x1:x2]
    ps        = _PIXEL_SIZE
    small     = cv2.resize(roi, (max(1, rw // ps), max(1, rh // ps)),
                           interpolation=cv2.INTER_LINEAR)
    pixelated = cv2.resize(small, (rw, rh), interpolation=cv2.INTER_NEAREST)

    # Appliquer uniquement à l'intérieur du polygone
    m = mask[y1:y2, x1:x2, None]   # (rh, rw, 1) pour broadcast sur 3 canaux
    frame[y1:y2, x1:x2] = np.where(m > 0, pixelated, roi)

    # Contour cyan + points aux 4 coins
    cv2.polylines(frame, [hull], True, (0, 220, 255), 2)
    for pt in corners:
        cv2.circle(frame, tuple(pt), 7, (0, 255, 200), -1)
