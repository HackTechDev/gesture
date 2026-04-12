# Améliorations possibles

## Démo B — Bulles à éclater

- [x] Plusieurs bulles simultanées avec un compteur de score
- [x] Minuterie : éclater le maximum de bulles en X secondes
- [ ] Bulles qui bougent aléatoirement (cibles mouvantes)
- [ ] Niveaux de difficulté : bulles plus rapides, plus petites, délai réduit

## Démo C — Bulle physique

- [ ] Gravité permanente (la bulle tombe si on ne la pousse plus)
- [ ] Plusieurs bulles qui se percutent entre elles (collisions inter-bulles)
- [ ] Obstacles fixes sur l'écran à éviter

## Démo D — Dessin dans l'air

- [ ] Outil gomme partielle (effacer uniquement sous le doigt, pas tout le canvas)
- [ ] Exporter le dessin en PNG (touche `s`)

## Démo F — Reconnaissance de gestes

- [ ] Nouveaux gestes : Spider-Man (pouce + auriculaire étendus), Spock (V entre majeur et annulaire)
- [ ] Déclencher une action système au geste (ouvrir une app, screenshot)

## Démo H — Bulle d'eau 3D

- [x] Maillage déformable 3D (48 points, ressort-masse + propagation d'onde)
- [x] Contour calé sur les bouts des doigts (rayon = distance moyenne centre → fingertips)
- [x] Interaction multi-doigts (5 tips + paume par main, poussée intérieure/extérieure)
- [ ] Plusieurs bulles simultanées qui rebondissent entre elles
- [ ] Gravité légère (la bulle tombe doucement si les mains s'éloignent)
- [ ] Éclater la bulle en pinçant les deux mains ensemble

## Démo K — Galaxie spirale 3D

- [x] Étoile filante qui traverse la scène périodiquement (toutes les 8–16 s, traînée dégradée + halo)
- [x] Mode "vue de côté" automatique quand les mains sont horizontales (tranche) / verticales (face)

## Démo L — Puzzle

- [ ] Niveaux : 3×3, 4×4, 5×5 (touche pour changer)
- [ ] Sélection de l'image parmi plusieurs fichiers
- [ ] Meilleur temps sauvegardé dans un fichier `scores.txt`

## Nouvelles démos

- [x] Démo D — Dessin dans l'air : tracer avec l'index, effacer en ouvrant la main
- [ ] Démo E — Contrôle de volume : écarter/rapprocher pouce et index pour simuler un curseur (barre de progression + contrôle volume système via `pactl`)
- [x] Démo F — Reconnaissance de gestes : détecter des formes précises (pouce levé, poing, victoire) et afficher leur nom
- [x] Démo F — Geste Dr Strange : cercle magique animé (pentagramme + runes + étincelles) adapté à la taille de la main
- [x] Démo G — Traînées de mouvement (motion trail) sur les 5 bouts de doigts avec halo néon
- [x] Démo K — Galaxie spirale 3D en couleur tournante entre les mains, déplaçable et inclinable
- [x] Démo L — Puzzle 3×3 : reconstituer linux.jpg en déplaçant les pièces avec l'index, déposer en faisant un poing
- [x] Démo Terre — Globe terrestre 3D texturé (2k_earth_daymap.jpg), rotation yaw/pitch par mouvement des deux mains, éclairage Lambertien + atmosphère
- [ ] Démo M — Piano dans l'air : 5 touches virtuelles (une par doigt), joue une note quand le bout du doigt touche une zone (`sounddevice`)
- [ ] Démo N — Marionnette : personnage dont les membres suivent les angles des doigts et des mains en temps réel
- [ ] Démo O — Peinture de particules : chaque fingertip émet un jet de particules colorées soumises à la gravité
- [ ] Démo P — Miroir magique : zoom, rotation et distorsion de l'image webcam pilotés par les gestes des deux mains

## Qualité visuelle

- [ ] Fond noir ou flou cinématique derrière les landmarks pour mieux les isoler
- [x] Traînées de mouvement (motion trail) sur les doigts — Démo G (touche `g`)
- [ ] Particules qui suivent les extrémités des doigts en permanence
- [ ] Intro animée : logo / titre au lancement avant d'entrer dans la boucle principale

## Interface

- [x] Touche `i` : masquer / afficher le squelette de la main
- [x] Touche `j` : basculer en plein écran / fenêtré
- [ ] Menu principal gestuel : naviguer entre les démos en pointant un menu à l'écran, sans clavier
- [ ] Panneau latéral semi-transparent redessiné (statuts, FPS, touches actives)

## Architecture

- [x] Séparer chaque démo dans son propre fichier (`demo_a.py`, `demo_b.py`…) et les importer dans `hand_motion.py`
- [x] Fichier `config.py` centralisé pour tous les paramètres ajustables
- [x] Affichage du FPS en temps réel pour mesurer l'impact des démos
- [ ] Enregistrement vidéo : touche `r` pour enregistrer la session en `.mp4` via `cv2.VideoWriter`
- [ ] Profils : sauvegarder / charger la combinaison de démos actives dans un fichier JSON
