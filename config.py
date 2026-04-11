"""config.py — Paramètres centralisés de l'application gesture."""

# ---------------------------------------------------------------------------
# Général
# ---------------------------------------------------------------------------
CAMERA_INDEX     = 0
CAMERA_WIDTH     = 1280
CAMERA_HEIGHT    = 720
CAMERA_FPS       = 30

MOVEMENT_THRESHOLD = 15   # pixels — seuil de détection de mouvement de la paume

FPS_SMOOTHING = 30         # nombre de frames pour la moyenne glissante du FPS

# ---------------------------------------------------------------------------
# MediaPipe
# ---------------------------------------------------------------------------
MIN_DETECTION_CONFIDENCE = 0.5
MIN_PRESENCE_CONFIDENCE  = 0.5
MIN_TRACKING_CONFIDENCE  = 0.5
NUM_HANDS                = 2

# ---------------------------------------------------------------------------
# Landmarks communs
# ---------------------------------------------------------------------------
FINGERTIPS = [4, 8, 12, 16, 20]   # pouce, index, majeur, annulaire, auriculaire

# ---------------------------------------------------------------------------
# Démo A — Filaments
# ---------------------------------------------------------------------------
FILAMENT_COLORS = [
    (255, 180,   0),  # cyan    — pouce
    (  0, 255, 180),  # vert    — index
    (180,   0, 255),  # violet  — majeur
    (  0, 200, 255),  # jaune   — annulaire
    (255,  50, 150),  # rose    — auriculaire
]

# ---------------------------------------------------------------------------
# Démo B — Bulles à éclater
# ---------------------------------------------------------------------------
BUBBLE_RADIUS    = 40   # pixels
POP_DURATION     = 18   # frames d'animation d'éclatement
BUBBLE_COUNT     = 5    # bulles simultanées
GAME_DURATION    = 30   # secondes par partie
PINCH_THRESHOLD  = 50   # distance pouce/index pour pincement (pixels)

BUBBLE_PALETTE = [
    (255,  80, 120),  # rose
    ( 80, 200, 255),  # jaune
    (255, 180,  50),  # cyan
    (120, 255, 100),  # vert
    (200,  80, 255),  # violet
    ( 80, 160, 255),  # orange
]

# ---------------------------------------------------------------------------
# Démo C — Bulle physique
# ---------------------------------------------------------------------------
BUBBLE_RADIUS_C = 50    # pixels
PUSH_RADIUS     = 100   # zone de contact en pixels (BUBBLE_RADIUS_C + marge)
PUSH_FACTOR     = 0.45  # intensité de l'impulsion
DAMPING         = 0.97  # friction par frame
MAX_VEL         = 28    # vitesse maximale en px/frame

# ---------------------------------------------------------------------------
# Démo D — Dessin dans l'air
# ---------------------------------------------------------------------------
DRAW_THICKNESS = 3      # épaisseur du trait en pixels

DRAW_COLORS = [
    (255, 255, 255),  # blanc
    (100, 255, 100),  # vert
    (100, 100, 255),  # rouge
    (  0, 220, 255),  # jaune
    (255, 100, 200),  # violet
    ( 50, 200, 255),  # orange
]

# ---------------------------------------------------------------------------
# Démo F — Reconnaissance de gestes
# ---------------------------------------------------------------------------
GESTURE_SMOOTH       = 10   # frames pour confirmer un geste (anti-scintillement)
DR_STRANGE_CIRCLE_R  = 90   # rayon minimal du cercle magique (pixels)
DR_STRANGE_RUNES     = 16   # nombre de marques runiques
DR_STRANGE_SPARKS    = 8    # nombre d'étincelles orbitales

THUMB_SPREAD_THRESHOLD   = 0.13  # distance normalisée tip→MCP pour pouce écarté
FINGERS_TOGETHER_THRESHOLD = 0.07  # distance normalisée index→majeur "collés"

# ---------------------------------------------------------------------------
# Démo G — Traînées de mouvement
# ---------------------------------------------------------------------------
TRAIL_LENGTH = 22   # positions mémorisées par doigt

TRAIL_COLORS = [
    (255, 180,   0),  # cyan       — pouce
    (  0, 255, 160),  # vert-menthe — index
    (180,  60, 255),  # violet     — majeur
    (  0, 200, 255),  # jaune      — annulaire
    (255,  60, 160),  # rose       — auriculaire
]
