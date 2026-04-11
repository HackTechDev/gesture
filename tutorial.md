# Tutoriel : Détection de mouvement de la main avec MediaPipe et OpenCV

## Prérequis

- Ubuntu
- Python 3.10
- Une webcam fonctionnelle

---

## 1. Créer le dossier du projet

```bash
mkdir -p ~/PYTHON/gesture
cd ~/PYTHON/gesture
```

## 2. Créer l'environnement virtuel

```bash
python3 -m venv .venv
```

## 3. Installer les dépendances

```bash
.venv/bin/pip install mediapipe opencv-python numpy
```

## 4. Lancer l'application

```bash
.venv/bin/python hand_motion.py
```

Au premier lancement, le modèle `hand_landmarker_full.task` est téléchargé automatiquement.

---

## Raccourcis clavier

| Touche | Action |
|--------|--------|
| `a` | Activer / désactiver les filaments lumineux entre les deux mains |
| `b` | Activer / désactiver la démo bulles à éclater |
| `c` | Activer / désactiver la démo bulle physique |
| `d` | Activer / désactiver le dessin dans l'air |
| `f` | Activer / désactiver la reconnaissance de gestes |
| `g` | Activer / désactiver les traînées de mouvement sur les doigts |
| `h` | Activer / désactiver la bulle d'eau modelable |
| `k` | Activer / désactiver la galaxie spirale 3D |
| `l` | Activer / désactiver le puzzle (linux.jpg) |
| `i` | Afficher / masquer le squelette de la main (traits, points, flèche) |
| `j` | Basculer en plein écran / fenêtré |
| `q` | Quitter l'application |

---

## Architecture du projet

Le projet est découpé en plusieurs fichiers, un par démo :

| Fichier | Rôle |
|---|---|
| `hand_motion.py` | Orchestrateur principal : capture webcam, détection MediaPipe, boucle de rendu, touches clavier |
| `demo_a.py` | Démo A — filaments néon entre les extrémités des deux mains |
| `demo_b.py` | Démo B — bulles brillantes à éclater par pincement (jeu avec score et minuterie) |
| `demo_c.py` | Démo C — bulle physique poussée par l'index, avec rebonds |
| `demo_d.py` | Démo D — dessin dans l'air avec l'index, effacement main ouverte, palette de couleurs |
| `demo_f.py` | Démo F — reconnaissance de gestes (Pouce levé, Victoire, Poing, Main ouverte, Index pointé, Metal) |
| `demo_g.py` | Démo G — traînées de mouvement lumineuses sur les 5 bouts de doigts |
| `demo_h.py` | Démo H — bulle d'eau 3D en apesanteur modelable avec les deux mains |
| `demo_k.py` | Démo K — galaxie spirale 3D tournante, déplaçable et inclinable avec les deux mains |
| `demo_l.py` | Démo L — puzzle 3×3 : reconstituer linux.jpg en déplaçant les pièces avec l'index |
| `config.py` | Tous les paramètres ajustables centralisés (caméra, MediaPipe, démos) |

Fonctions utilitaires dans `hand_motion.py` :

| Fonction | Rôle |
|---|---|
| `download_model()` | Téléchargement automatique du modèle `.task` au premier lancement |
| `enhance_frame()` | Prétraitement CLAHE pour compenser l'éclairage inégal |
| `draw_hand()` | Tracé des 21 landmarks et connexions de la main |
| `palm_center()` | Calcule le centre de la paume (landmark 9) |
| `main()` | Boucle principale : capture, détection, rendu, touches |

---

## Notes techniques

**Général**
- MediaPipe 0.10+ n'expose plus `mp.solutions` — la Tasks API (`mediapipe.tasks.python.vision.HandLandmarker`) et un fichier modèle `.task` séparé sont requis.
- Le modèle `.task` est exclu du dépôt git (`.gitignore`) et téléchargé automatiquement.
- Le mode `VIDEO` exploite la continuité temporelle entre frames pour un suivi plus stable qu'`IMAGE`.
- `MOVEMENT_THRESHOLD` (défaut : 15 px) — diminuer pour détecter des mouvements plus subtils.
- Touche `i` : masque / affiche le squelette de la main (traits, points aux articulations, flèche de mouvement). Utile pour les démos visuelles comme la bulle d'eau.
- Le FPS est affiché en bas à droite en temps réel (vert ≥ 25 fps, orange ≥ 15 fps, rouge < 15 fps).
- Tous les paramètres ajustables sont centralisés dans `config.py`.

**Démo A — Filaments (touche `a`)**
- Nécessite les **deux mains simultanément** visibles dans le champ de la webcam.
- Effet néon obtenu par fusion additive d'un calque GaussianBlur sur la frame.
- Une couleur distincte par paire de doigts (pouce, index, majeur, annulaire, auriculaire).

**Démo B — Bulles à éclater (touche `b`)**
- `BUBBLE_COUNT` bulles (défaut : 5) apparaissent simultanément, positionnées sans chevauchement.
- Pincer le **pouce** (landmark 4) et l'**index** (landmark 8) à moins de `PINCH_THRESHOLD` px sur une bulle pour l'éclater — une nouvelle bulle remplace immédiatement celle éclatée.
- La partie dure `GAME_DURATION` secondes (défaut : 30 s) : une barre de progression et un compteur de secondes sont affichés en haut au centre, le score en temps réel à droite.
- À la fin du temps, un écran de fin affiche le score final ; appuyer à nouveau sur `b` relance une partie.
- Paramètres : `PINCH_THRESHOLD`, `BUBBLE_RADIUS`, `BUBBLE_COUNT`, `GAME_DURATION`, `POP_DURATION`.

**Démo C — Bulle physique (touche `c`)**
- L'**index** (landmark 8) pousse la bulle : vitesse du doigt = impulsion appliquée à la bulle.
- La bulle rebondit sur les 4 bords et ralentit progressivement (`DAMPING = 0.97`).
- Un cercle translucide indique la zone de contact ; une flèche montre la vitesse courante.
- Paramètres : `PUSH_FACTOR`, `PUSH_RADIUS`, `DAMPING`, `MAX_VEL`.

**Démo D — Dessin dans l'air (touche `d`)**
- **Index seul étendu** (majeur/annulaire/auriculaire repliés) → mode dessin : une ligne est tracée entre la position courante et la précédente de l'index (landmark 8).
- **Main ouverte** (4 doigts étendus) → effacement complet du canvas avec un flash blanc animé.
- Une **palette de 6 couleurs** est affichée en haut à droite ; pointer l'**auriculaire** (landmark 20) dessus change la couleur active (encadrée en blanc).
- Le dessin persiste sur un calque fusionné additivement sur la frame (zones noires = transparentes).
- Paramètres : `DRAW_COLORS` (liste de couleurs BGR), `DRAW_THICKNESS` (épaisseur du trait).

**Démo H — Bulle d'eau 3D modelable (touche `h`)**
- Nécessite les **deux mains** visibles : la bulle apparaît au centre des deux paumes et disparaît en fondu si une main quitte le champ.
- **Taille** : le rayon cible est la distance moyenne du centre aux 10 bouts de doigts — la surface de la bulle passe naturellement par les extrémités des doigts.
- **Position** : suit le centre des deux paumes avec un ressort amorti pour un mouvement fluide.
- **Modelage 3D** : maillage de 48 points de contrôle avec physique ressort-masse + propagation d'onde (effet jelly). Chaque doigt (5 bouts + paume, par main) déforme la surface indépendamment — depuis l'extérieur : enfonce la surface ; depuis l'intérieur : la gonfle.
- Rendu sphère 3D en 9 couches : halo gaussien additif, corps translucide, face illuminée décalée (volume), cœur lumineux, limb darkening (bords assombris), 5 caustiques animées, rim Fresnel, surbrillances spéculaires, contour final déformé.
- Conseil : combiner avec `i` pour masquer le squelette et profiter pleinement de l'effet.
- Paramètres dans `config.py` : `BUBBLE_H_MIN_R`, `BUBBLE_H_MAX_R`.

**Démo L — Puzzle (touche `l`)**
- Charge `linux.jpg` et la découpe en **9 pièces** (grille 3×3), disposées aléatoirement à l'écran.
- **Attraper** : pointer l'**index seul** sur une pièce — elle suit le bout du doigt.
- **Déposer** : fermer la main en **poing** — si la pièce est à moins de 55 px de sa case cible, elle se cale automatiquement (magnétisme).
- La grille cible est toujours visible au centre pour guider le placement. Les pièces posées sont encadrées en vert.
- Un compteur `X / 9` indique l'avancement ; un message de victoire apparaît quand le puzzle est complet.
- Conseil : combiner avec `i` pour masquer le squelette et mieux voir les pièces.

**Démo K — Galaxie spirale 3D (touche `k`)**
- Nécessite les **deux mains** simultanément : la galaxie apparaît au point milieu entre les deux paumes.
- **Position** : suit le centre des deux paumes avec un ressort amorti.
- **Taille** : proportionnelle à la distance entre les deux mains (`dist × 0.92`, clampée entre 80 et 340 px de scale).
- **Vue de côté / face** : mains à la même hauteur (horizontales) → galaxie vue en **tranche** (disque fin) ; mains décalées verticalement → vue de **face** (bras spiraux visibles). Transition fluide par ressort amorti.
- **Rotation (yaw)** : spin automatique continu à 0.45 rad/s — la galaxie tourne sur elle-même sans intervention.
- **Étoile filante** : apparaît automatiquement toutes les 8–16 s, traverse la scène avec une traînée lumineuse dégradée et un halo gaussien.
- Structure : 1500 étoiles (55 % bras spiraux, 20 % disque diffus, 20 % bulbe central, 5 % géantes rouges) + 20 nébuleuses colorées le long des bras.
- Rendu 3D par tri de profondeur (`np.argsort`) et facteur de luminosité selon la coordonnée Z.
- Performance : les étoiles de taille 1 (≈ 1 200) sont dessinées en batch NumPy direct sur le buffer de frame ; les étoiles de taille 2+ utilisent `cv2.circle`.
- Conseil : combiner avec `i` pour masquer le squelette et profiter pleinement de l'effet.

**Démo G — Traînées de mouvement (touche `g`)**
- Chaque bout de doigt (pouce, index, majeur, annulaire, auriculaire) laisse une traînée lumineuse sur les `TRAIL_LENGTH` dernières positions (défaut : 22 frames).
- La traînée s'épaissit et s'illumine vers l'extrémité la plus récente ; un halo néon est ajouté par fusion additive d'un calque flou.
- Une couleur distincte est attribuée à chaque doigt ; fonctionne simultanément sur les deux mains.
- Compatible avec toutes les autres démos.

**Démo F — Reconnaissance de gestes (touche `f`)**
- 7 gestes reconnus : **Pouce levé**, **Dr Strange**, **Victoire**, **Poing**, **Main ouverte**, **Index pointé**, **Metal**.
- Détection basée sur la position Y des tips vs PIP joints (tip au-dessus du PIP = doigt étendu) et sur des distances normalisées entre landmarks.
- Lissage sur `GESTURE_SMOOTH` frames (défaut : 10) pour éviter le scintillement — un geste est affiché dès qu'il est majoritaire sur la fenêtre.
- Le nom s'affiche dans un bandeau semi-transparent sous la paume, sauf pour **Dr Strange** qui affiche à la place un cercle magique animé.

  *Détails des gestes :*
  - **Pouce levé** : pouce étendu vers le haut, 4 autres doigts repliés.
  - **Dr Strange** : index + majeur collés et étendus, pouce écarté latéralement, annulaire + auriculaire repliés — affiche un cercle orange/rouge avec pentagramme tournant, 16 marques runiques et 8 étincelles orbitales ; la taille du cercle s'adapte à celle de la main.
  - **Victoire** : index + majeur étendus et écartés, pouce replié, annulaire + auriculaire repliés.
  - **Poing** : tous les doigts et le pouce repliés.
  - **Main ouverte** : les 4 doigts étendus.
  - **Metal** : index + auriculaire étendus, autres repliés.
  - **Index pointé** : index seul étendu.
