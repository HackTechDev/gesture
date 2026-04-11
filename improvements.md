# Améliorations possibles

## Démo B — Bulles à éclater

- [x] Plusieurs bulles simultanées avec un compteur de score
- [x] Minuterie : éclater le maximum de bulles en X secondes
- [ ] Bulles qui bougent aléatoirement (cibles mouvantes)

## Démo C — Bulle physique

- [ ] Gravité permanente (la bulle tombe si on ne la pousse plus)
- [ ] Plusieurs bulles qui se percutent entre elles (collisions inter-bulles)
- [ ] Obstacles fixes sur l'écran à éviter

## Démo H — Bulle d'eau 3D

- [x] Maillage déformable 3D (48 points, ressort-masse + propagation d'onde)
- [x] Contour calé sur les bouts des doigts (rayon = distance moyenne centre → fingertips)
- [x] Interaction multi-doigts (5 tips + paume par main, poussée intérieure/extérieure)
- [ ] Plusieurs bulles simultanées qui rebondissent entre elles
- [ ] Gravité légère (la bulle tombe doucement si les mains s'éloignent)
- [ ] Éclater la bulle en pinçant les deux mains ensemble

## Nouvelles démos

- [x] Démo D — Dessin dans l'air : tracer avec l'index, effacer en ouvrant la main
- [ ] Démo E — Contrôle de volume : écarter/rapprocher pouce et index pour simuler un curseur
- [x] Démo F — Reconnaissance de gestes : détecter des formes précises (pouce levé, poing, victoire) et afficher leur nom
- [x] Démo F — Geste Dr Strange : cercle magique animé (pentagramme + runes + étincelles) adapté à la taille de la main
- [x] Démo G — Traînées de mouvement (motion trail) sur les 5 bouts de doigts avec halo néon
- [x] Démo K — Galaxie spirale 3D en couleur tournante entre les mains, déplaçable et inclinable

## Qualité visuelle

- [ ] Fond noir ou flou cinématique derrière les landmarks pour mieux les isoler
- [x] Traînées de mouvement (motion trail) sur les doigts — Démo G (touche `g`)
- [ ] Particules qui suivent les extrémités des doigts en permanence

## Interface

- [x] Touche `i` : masquer / afficher le squelette de la main
- [x] Touche `j` : basculer en plein écran / fenêtré

## Architecture

- [x] Séparer chaque démo dans son propre fichier (`demo_a.py`, `demo_b.py`…) et les importer dans `hand_motion.py`
- [x] Fichier `config.py` centralisé pour tous les paramètres ajustables
- [x] Affichage du FPS en temps réel pour mesurer l'impact des démos
