# Features — Gesture Recognition

Application de reconnaissance gestuelle en temps réel (webcam + MediaPipe + OpenCV).  
Touche de lancement : `.venv/bin/python hand_motion.py`

---

## Démos disponibles

| Touche | Démo | Mains requises |
|--------|------|----------------|
| `a` | Filaments néon entre les deux mains | 2 |
| `b` | Bulles à éclater (score + minuterie) | 1 ou 2 |
| `c` | Bulle physique avec rebonds | 1 |
| `d` | Dessin dans l'air + palette de couleurs | 1 |
| `f` | Reconnaissance de gestes (7 gestes) | 1 ou 2 |
| `g` | Traînées lumineuses sur les doigts | 1 ou 2 |
| `h` | Bulle d'eau 3D modelable | 2 |
| `k` | Galaxie spirale 3D | 2 |
| `l` | Puzzle 3×3 (linux.jpg) | 1 |
| `t` | Globe terrestre 3D texturé | 2 |
| `v` | Jeu Tetris | 1 |

---

## Détail des démos

### Démo A — Filaments (touche `a`)
- Nécessite **deux mains** simultanées.
- Filaments néon colorés reliant les bouts de doigts des deux mains.
- Une couleur par paire de doigts (pouce, index, majeur, annulaire, auriculaire).
- Effet néon par fusion additive d'un calque GaussianBlur.

### Démo B — Bulles à éclater (touche `b`)
- 5 bulles simultanées positionnées sans chevauchement.
- **Pincer** pouce + index (< seuil px) sur une bulle → elle éclate, une nouvelle apparaît.
- Partie de 30 secondes : barre de progression + score en temps réel.
- Écran de fin avec score final ; appuyer à nouveau sur `b` relance une partie.

### Démo C — Bulle physique (touche `c`)
- L'**index** pousse la bulle avec une impulsion proportionnelle à la vitesse du doigt.
- Rebonds sur les 4 bords + amortissement progressif.
- Cercle translucide de contact, flèche de vitesse.

### Démo D — Dessin dans l'air (touche `d`)
- **Index seul étendu** → mode dessin (trait continu).
- **Main ouverte** (4 doigts) → effacement total avec flash blanc animé.
- Palette de 6 couleurs en haut à droite ; pointer l'**auriculaire** dessus change la couleur active.

### Démo F — Reconnaissance de gestes (touche `f`)
- 7 gestes reconnus : **Pouce levé**, **Dr Strange**, **Victoire**, **Poing**, **Main ouverte**, **Index pointé**, **Metal**.
- Lissage sur 10 frames pour éviter le scintillement.
- Geste **Dr Strange** : cercle magique animé (pentagramme + runes + étincelles) adapté à la taille de la main.

### Démo G — Traînées de mouvement (touche `g`)
- Traînée lumineuse sur les 5 bouts de doigts (22 dernières positions).
- Une couleur par doigt ; halo néon additif.
- Compatible avec toutes les autres démos simultanément.

### Démo H — Bulle d'eau 3D (touche `h`)
- **Deux mains** requises : la bulle apparaît entre les paumes.
- **Taille** = distance moyenne centre → bouts des 10 doigts.
- **Modelage** : maillage 48 points, physique ressort-masse + propagation d'onde (effet jelly).
- Rendu 9 couches : halo, corps translucide, illumination, caustiques, Fresnel, contour déformé.

### Démo K — Galaxie spirale 3D (touche `k`)
- **Deux mains** requises ; apparaît au point milieu des paumes.
- **Vue de côté / face** : mains horizontales → tranche (disque fin) ; mains décalées → vue de face.
- **Rotation** : spin automatique continu.
- **Étoile filante** : traverse la scène toutes les 8–16 s avec traînée et halo.
- 1 500 étoiles + 20 nébuleuses colorées ; rendu 3D par tri de profondeur.

### Démo L — Puzzle 3×3 (touche `l`)
- Charge `linux.jpg`, découpe en **9 pièces** disposées à gauche et à droite de la grille.
- **Attraper** : index seul étendu sur une pièce → elle suit le doigt.
- **Déposer** : poing fermé → magnétisme automatique si < 100 px de la case cible.
- Timer **3 minutes** affiché en haut (vert → orange → rouge).
- Compteur de pièces `X / 9` + message de victoire avec temps final.

### Démo Tetris (touche `v`)
- Jeu de Tetris classique : plateau 10×20, 7 tétrominos, rendu en incrustation sur la webcam.
- **Index pointé** : la pièce se déplace vers la colonne ciblée par le doigt (mapping écran → plateau).
- **Poing** : chute rapide (vitesse × 20).
- **Main ouverte** : rotation horaire avec wall-kick (ajustement automatique si bloqué contre un mur).
- **Pièce fantôme** : silhouette de destination pour anticiper le placement.
- Score : 100 × (niveau+1) pour 1 ligne, 300 pour 2, 500 pour 3, 800 pour 4 (Tetris).
- Niveau augmente toutes les 10 lignes (1 à 10), vitesse jusqu'à 0.06 s/cellule.
- Appuyer sur `v` après Game Over relance une nouvelle partie.

### Démo Terre — Globe terrestre 3D (touche `t`)
- **Deux mains** requises ; globe au milieu des paumes, taille proportionnelle à l'écart.
- **Rotation yaw** : déplacer les mains horizontalement → le globe tourne gauche/droite.
- **Rotation pitch** : déplacer les mains verticalement → le globe bascule avant/arrière.
- Inertie courte (~0,2 s) sur les deux axes.
- Texture 2K (`2k_earth_daymap.jpg`), mapping sphérique vectorisé NumPy.
- Éclairage Lambertien + halo atmosphérique bleuté + surbrillance spéculaire.

---

## Contrôles globaux

| Touche | Action |
|--------|--------|
| `i` | Afficher / masquer le squelette de la main |
| `j` | Basculer plein écran / fenêtré |
| `q` | Quitter |

---

## Interface

- **Statut** (barre basse) : aucune main / main immobile / mouvement détecté avec distance en px.
- **Panneau latéral** (haut gauche) : liste des démos avec état ON / OFF.
- **FPS** (bas droite) : vert ≥ 25 fps, orange ≥ 15 fps, rouge < 15 fps.
- Les démos peuvent être **combinées** librement (ex. Traînées + Bulle d'eau, Galaxie + Traînées).
