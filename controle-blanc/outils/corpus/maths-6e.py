# -*- coding: utf-8 -*-
"""Corpus d’entraînement : le programme de mathématiques de 6e, en vigueur.

Même rôle que le corpus d’histoire : tenir lieu de photos tant qu’on n’a pas de
vrais cahiers d’élèves, pour juger la qualité des fiches et des questions. Ce
n’est pas du contenu destiné à être servi.

Programme de référence. Arrêté du 17 avril 2025, publié au Bulletin officiel
n°16, en vigueur en 6e depuis la rentrée 2025. Attention : contrairement à
l’histoire, dont le nouveau programme n’arrive qu’en 2027, les maths ont déjà
basculé. Le programme est organisé en six domaines, et introduit les
probabilités dès la 6e.

Un cours de maths ne ressemble pas à un cours d’histoire : définitions,
propriétés, méthodes, exemples travaillés, formules. Les transcriptions
ci-dessous en gardent la forme — y compris ses notations, qui sont justement ce
que le produit ne sait pas encore afficher correctement.
"""

from __future__ import annotations

MATIERE = "mathematiques"
NIVEAU = "6e"
CLE_GROUPE = "domaine"
PROGRAMME = "Mathématiques, classe de 6e — arrêté du 17 avril 2025 (en vigueur depuis la rentrée 2025)"

DOMAINES = [
    "Nombres, calculs et résolution de problèmes",
    "Grandeurs et mesures",
    "Espace et géométrie",
    "Organisation et gestion de données, et probabilité",
    "Proportionnalité",
    "Initiation à la pensée informatique",
]

CHAPITRES = [
    {
        "id": "nombres-decimaux",
        "domaine": 1,
        "titre": "Nombres entiers et nombres décimaux",
        "notions": [
            "La numération décimale de position",
            "Les différentes écritures d’un nombre décimal",
            "Comparer et ranger des nombres décimaux",
            "Encadrer et arrondir",
            "Placer un décimal sur une demi-droite graduée",
        ],
        "transcription": """Nombres entiers et nombres décimaux

I. La numération de position

Dans un nombre, chaque chiffre a une valeur qui dépend de sa position.
Exemple : dans 3 407,25 le chiffre 4 est le chiffre des centaines, le chiffre 2 est
le chiffre des dixièmes.

Tableau à recopier : centaines / dizaines / unités , dixièmes / centièmes / millièmes.

Déf. Un nombre décimal est un nombre qui peut s’écrire avec une partie entière et une
partie décimale, séparées par une virgule.

Attention : chiffre et nombre, ce n’est pas la même chose. Dans 3 407,25 le chiffre des
dizaines est 0, mais le nombre de dizaines est 340.

II. Les écritures d’un même nombre

Un même nombre décimal s’écrit de plusieurs façons.
Exemple avec 12,5 :
  - écriture décimale : 12,5
  - écriture fractionnaire : 125/10
  - décomposition : 12 + 5/10 = 1 × 10 + 2 × 1 + 5 × 0,1

Propriété. On ne change pas un nombre décimal en ajoutant des zéros à la fin de sa
partie décimale : 12,5 = 12,50 = 12,500.
Mais 12,05 n’est pas égal à 12,5 ! Le zéro entre la virgule et le 5 change tout.

III. Comparer, ranger, encadrer

Méthode pour comparer deux décimaux :
  1. On compare d’abord les parties entières.
  2. Si elles sont égales, on compare les dixièmes, puis les centièmes, etc.
Exemple : 7,3 < 7,25 ? Non. 7,3 = 7,30 et 30 > 25 donc 7,3 > 7,25.
C’est l’erreur la plus fréquente : on ne compare pas les parties décimales comme des
nombres entiers.

Déf. Ranger dans l’ordre croissant, c’est du plus petit au plus grand. Décroissant,
c’est l’inverse.

Encadrer 7,26 à l’unité : 7 < 7,26 < 8. À l’unité près.
Arrondir 7,26 au dixième : 7,3 (car le chiffre suivant, 6, est ≥ 5).

À retenir : la virgule ne sépare pas deux nombres entiers. 12,5 est plus grand que
12,45, même si 45 > 5.

Formules et repères : 1 dixième = 0,1 = 1/10. 1 centième = 0,01 = 1/100.""",
    },
    {
        "id": "fractions",
        "domaine": 1,
        "titre": "Les fractions",
        "notions": [
            "La fraction comme partage et comme quotient",
            "Fractions égales et simplification",
            "Comparer une fraction à 1",
            "Placer une fraction sur une demi-droite graduée",
            "Passer d’une fraction décimale à un nombre décimal",
        ],
        "transcription": """Les fractions

I. Qu’est-ce qu’une fraction ?

Déf. Une fraction a/b, c’est le quotient de a par b, avec b non nul.
  - a s’appelle le numérateur (en haut) ;
  - b s’appelle le dénominateur (en bas).

Le dénominateur indique en combien de parts égales on partage l’unité. Le numérateur
indique combien de parts on prend.
Exemple : 3/4 d’une tablette de chocolat, c’est la tablette partagée en 4 parts égales,
dont on prend 3.

Propriété. a/b × b = a. Autrement dit, 3/4 est le nombre qui, multiplié par 4, donne 3.

II. Fractions égales

Propriété. On ne change pas une fraction en multipliant, ou en divisant, son numérateur
et son dénominateur par un même nombre non nul.
Exemple : 3/4 = 6/8 = 30/40. Et 15/20 = 3/4 (on a divisé par 5).

Simplifier une fraction, c’est trouver une fraction égale avec des nombres plus petits.
Méthode : chercher un diviseur commun au numérateur et au dénominateur.
Exemple : 18/24. 6 divise 18 et 24, donc 18/24 = 3/4.

III. Comparer une fraction à 1

Propriété.
  - Si numérateur < dénominateur, alors la fraction est plus petite que 1. Ex : 3/4 < 1.
  - Si numérateur = dénominateur, la fraction vaut 1. Ex : 5/5 = 1.
  - Si numérateur > dénominateur, la fraction est plus grande que 1. Ex : 7/4 > 1.

IV. Fractions décimales et écriture décimale

Déf. Une fraction décimale est une fraction dont le dénominateur est 10, 100, 1000…
Exemple : 25/100 = 0,25. 7/10 = 0,7.

Méthode pour placer 5/4 sur une demi-droite graduée : on partage chaque unité en 4, on
compte 5 parts à partir de 0. 5/4 se place entre 1 et 2.

À retenir : une fraction est un nombre, pas une opération à faire. 3/4 a une place
précise sur la droite graduée, entre 0 et 1.

Erreur à éviter : 3/4 + 1/4 ne fait pas 4/8. On additionne les numérateurs quand les
dénominateurs sont les mêmes : 3/4 + 1/4 = 4/4 = 1.""",
    },
    {
        "id": "calculs-priorites",
        "domaine": 1,
        "titre": "Calculs et priorités opératoires",
        "notions": [
            "Les quatre opérations et leur vocabulaire",
            "Les priorités de calcul",
            "Le rôle des parenthèses",
            "Multiplier et diviser par 10, 100, 1000",
            "Ordre de grandeur et calcul mental",
        ],
        "transcription": """Calculs et priorités opératoires

I. Vocabulaire à connaître

  - Addition : les termes, le résultat est la somme. 5 + 3 = 8.
  - Soustraction : les termes, le résultat est la différence. 8 − 3 = 5.
  - Multiplication : les facteurs, le résultat est le produit. 4 × 6 = 24.
  - Division : le dividende, le diviseur, le résultat est le quotient. 24 : 4 = 6.

Ces mots tombent en contrôle. « Calcule la somme de 12 et 7 » ne veut pas dire la même
chose que « calcule le produit de 12 et 7 ».

II. Les priorités opératoires

Règle. Dans un calcul sans parenthèses :
  1. on effectue d’abord les multiplications et les divisions, de gauche à droite ;
  2. puis les additions et les soustractions, de gauche à droite.

Exemple : 3 + 4 × 5 = 3 + 20 = 23. Et non 35 !
Exemple : 20 − 6 : 2 = 20 − 3 = 17.

Règle. Les parenthèses sont prioritaires sur tout le reste.
Exemple : (3 + 4) × 5 = 7 × 5 = 35.

Attention : quand il n’y a que des additions et des soustractions, on calcule de gauche
à droite. 10 − 4 + 2 = 6 + 2 = 8, et non 10 − 6 = 4.

III. Multiplier et diviser par 10, 100, 1000

Propriété. Multiplier par 10, c’est décaler la virgule d’un rang vers la droite.
Diviser par 10, c’est la décaler d’un rang vers la gauche.
Exemples : 3,45 × 100 = 345. 27,5 : 10 = 2,75.

IV. Ordre de grandeur

Déf. Un ordre de grandeur est une valeur approchée simple qui permet de vérifier un
résultat.
Exemple : 19,8 × 5,1. Ordre de grandeur : 20 × 5 = 100. Si la calculatrice affiche
1 009,8, c’est qu’il y a une erreur.

À retenir : avant de poser un calcul, on estime le résultat. Ça évite les erreurs de
virgule, qui sont les plus fréquentes.

Repères de calcul mental : les tables jusqu’à 12, les doubles et moitiés,
25 × 4 = 100, 50 × 2 = 100.""",
    },
    {
        "id": "longueurs-aires",
        "domaine": 2,
        "titre": "Longueurs, périmètres et aires",
        "notions": [
            "Les unités de longueur et leurs conversions",
            "Le périmètre d’une figure",
            "Les formules d’aire du carré, du rectangle et du triangle",
            "Les unités d’aire et leurs conversions",
            "Distinguer périmètre et aire",
        ],
        "transcription": """Longueurs, périmètres et aires

I. Les unités de longueur

km — hm — dam — m — dm — cm — mm
Chaque unité vaut 10 fois la suivante.
Exemples : 1 km = 1 000 m. 2,5 m = 250 cm. 34 mm = 3,4 cm.

Méthode : on utilise un tableau de conversion, une colonne par unité, un chiffre par
colonne.

II. Le périmètre

Déf. Le périmètre d’une figure est la longueur de son contour.

Formules :
  - Carré de côté c : P = 4 × c
  - Rectangle de longueur L et largeur l : P = 2 × (L + l)
  - Cercle de rayon r : P = 2 × π × r (on prend π ≈ 3,14)

Le périmètre se mesure en unités de longueur : cm, m, km.

III. L’aire

Déf. L’aire d’une figure est la mesure de la surface qu’elle occupe.

Formules :
  - Carré de côté c : A = c × c
  - Rectangle : A = L × l
  - Triangle de base b et de hauteur h : A = (b × h) : 2

L’aire se mesure en unités d’aire : cm², m², km².

Unités d’aire : km² — hm² — dam² — m² — dm² — cm² — mm².
Attention : chaque unité d’aire vaut 100 fois la suivante, pas 10.
Exemple : 1 m² = 100 dm² = 10 000 cm².

Retenir aussi : 1 ha = 1 hm² = 10 000 m² (l’hectare, pour les terrains).

IV. Ne pas confondre

Deux figures peuvent avoir le même périmètre et des aires différentes.
Exemple : un rectangle 1 cm × 5 cm et un carré de 3 cm de côté ont tous deux un
périmètre de 12 cm. Mais leurs aires valent 5 cm² et 9 cm².

À retenir : le périmètre, c’est le tour, en cm. L’aire, c’est la surface, en cm². C’est
la confusion la plus fréquente du chapitre.

Formules à savoir par cœur : P carré = 4 × c ; A rectangle = L × l ;
A triangle = (b × h) : 2 ; 1 m² = 10 000 cm².""",
    },
    {
        "id": "durees",
        "domaine": 2,
        "titre": "Durées et repérage dans le temps",
        "notions": [
            "Les unités de durée et leurs relations",
            "Convertir des durées",
            "Calculer une durée entre deux instants",
            "Additionner et soustraire des durées",
            "Lire un horaire",
        ],
        "transcription": """Durées et repérage dans le temps

I. Les unités de durée

1 jour = 24 heures
1 heure = 60 minutes
1 minute = 60 secondes
1 heure = 3 600 secondes

Attention : les durées ne sont pas décimales. 1 h 30 min n’est pas 1,30 h mais 1,5 h.
C’est l’erreur qui coûte le plus de points dans ce chapitre.

II. Convertir

Méthode pour convertir 2 h 45 min en minutes :
  2 × 60 = 120, puis 120 + 45 = 165 minutes.

Méthode pour convertir 200 minutes en heures et minutes :
  200 : 60 = 3 reste 20, donc 200 min = 3 h 20 min.

III. Calculer une durée

Déf. Un instant, c’est un moment précis (8 h 15). Une durée, c’est un écart entre deux
instants (2 h 30).

Méthode pour calculer la durée entre 8 h 40 et 11 h 15 :
  de 8 h 40 à 9 h 00 → 20 min
  de 9 h 00 à 11 h 00 → 2 h
  de 11 h 00 à 11 h 15 → 15 min
  Total : 2 h 35 min.
On passe par les heures rondes, c’est plus sûr que de poser une soustraction.

IV. Additionner des durées

Exemple : 1 h 45 min + 2 h 30 min = 3 h 75 min = 4 h 15 min.
On convertit toujours quand les minutes dépassent 60.

À retenir : on ne calcule pas les durées comme des nombres décimaux. Il y a 60 minutes
dans une heure, pas 100.

Repères : 1 h = 60 min. 1 j = 24 h. Une année scolaire ≈ 36 semaines.""",
    },
    {
        "id": "droites-angles",
        "domaine": 3,
        "titre": "Droites, segments et angles",
        "notions": [
            "Point, droite, demi-droite, segment et leurs notations",
            "Droites perpendiculaires et droites parallèles",
            "Construire une perpendiculaire et une parallèle",
            "Mesurer et construire un angle",
            "La médiatrice d’un segment",
        ],
        "transcription": """Droites, segments et angles

I. Vocabulaire et notations

  - Un point se note par une lettre majuscule : A.
  - La droite passant par A et B se note (AB). Elle est infinie.
  - Le segment d’extrémités A et B se note [AB]. Sa longueur se note AB.
  - La demi-droite d’origine A passant par B se note [AB).

Attention aux crochets et parenthèses : (AB) la droite, [AB] le segment, AB la longueur.
Écrire « (AB) = 5 cm » est faux : une droite n’a pas de longueur.

II. Perpendiculaires et parallèles

Déf. Deux droites sont perpendiculaires lorsqu’elles se coupent en formant un angle
droit. On note (d1) ⊥ (d2).
Déf. Deux droites sont parallèles lorsqu’elles ne se coupent jamais. On note (d1) // (d2).

Propriétés à connaître :
  - Si deux droites sont perpendiculaires à une même droite, alors elles sont parallèles.
  - Si deux droites sont parallèles et qu’une troisième est perpendiculaire à l’une,
    alors elle est perpendiculaire à l’autre.

Méthode : on construit une perpendiculaire à l’équerre, une parallèle à la règle et
l’équerre.

III. Les angles

Déf. Un angle est la portion de plan délimitée par deux demi-droites de même origine.
L’angle de sommet B et de côtés [BA) et [BC) se note ABC avec un chapeau, ou simplement
l’angle B s’il n’y a pas d’ambiguïté.

On mesure un angle en degrés, avec un rapporteur.
  - angle aigu : entre 0° et 90°
  - angle droit : 90°
  - angle obtus : entre 90° et 180°
  - angle plat : 180°

Méthode pour mesurer : placer le centre du rapporteur sur le sommet, le zéro sur un côté,
lire sur la graduation où passe l’autre côté. Vérifier que la lecture est cohérente avec
la nature de l’angle : un angle qui a l’air aigu ne peut pas mesurer 130°.

IV. La médiatrice

Déf. La médiatrice d’un segment [AB] est la droite perpendiculaire à [AB] passant par
son milieu.
Propriété. Tout point de la médiatrice de [AB] est à égale distance de A et de B.

À retenir : la notation dit ce qu’est l’objet. Se tromper de crochets, c’est se tromper
d’objet, et le correcteur le compte comme une erreur de cours.

Repères : angle droit = 90°, angle plat = 180°."""
    },
    {
        "id": "figures-symetrie",
        "domaine": 3,
        "titre": "Figures usuelles et symétrie axiale",
        "notions": [
            "Les triangles particuliers et leurs propriétés",
            "Les quadrilatères usuels",
            "Le cercle : rayon, diamètre, corde",
            "La symétrie axiale et l’axe de symétrie",
            "Construire le symétrique d’une figure",
        ],
        "transcription": """Figures usuelles et symétrie axiale

I. Les triangles

  - Triangle isocèle : deux côtés de même longueur. Les angles à la base sont égaux.
  - Triangle équilatéral : trois côtés de même longueur. Ses trois angles mesurent 60°.
  - Triangle rectangle : un angle droit. Le côté opposé à l’angle droit est l’hypoténuse.

Un triangle peut être isocèle et rectangle en même temps.

II. Les quadrilatères

  - Rectangle : quatre angles droits. Ses diagonales ont la même longueur et se coupent
    en leur milieu.
  - Losange : quatre côtés de même longueur. Ses diagonales sont perpendiculaires et se
    coupent en leur milieu.
  - Carré : à la fois rectangle et losange. Il a donc toutes leurs propriétés.

À retenir : tout carré est un rectangle, mais tout rectangle n’est pas un carré.

III. Le cercle

Déf. Le cercle de centre O et de rayon r est l’ensemble des points situés à la distance
r du point O.
  - Le rayon relie le centre à un point du cercle.
  - Le diamètre passe par le centre et relie deux points du cercle. Diamètre = 2 × rayon.
  - Une corde relie deux points du cercle sans forcément passer par le centre.

IV. La symétrie axiale

Déf. Deux figures sont symétriques par rapport à une droite (d) si elles se superposent
en pliant le long de (d). La droite (d) est l’axe de symétrie.

Propriétés. La symétrie axiale conserve les longueurs, les angles, les aires et
l’alignement. Elle ne conserve pas le sens : la figure est retournée.

Méthode pour construire le symétrique d’un point A par rapport à (d) : tracer la
perpendiculaire à (d) passant par A, puis reporter la même distance de l’autre côté.

Axes de symétrie à connaître : le rectangle en a 2, le losange 2, le carré 4, le cercle
une infinité, le triangle équilatéral 3, le triangle isocèle 1.

À retenir : une propriété se démontre, elle ne se constate pas à l’œil. « Ça a l’air
d’un carré » n’est jamais une justification."""
    },
    {
        "id": "donnees-probabilites",
        "domaine": 4,
        "titre": "Données et premières probabilités",
        "notions": [
            "Lire et construire un tableau de données",
            "Lire et construire un diagramme en barres",
            "Calculer un effectif total et une fréquence simple",
            "Le vocabulaire du hasard : issue, événement",
            "Comparer des chances : certain, impossible, probable",
        ],
        "transcription": """Données et premières probabilités

I. Organiser des données

Les données se rangent dans un tableau : une ligne pour la catégorie, une ligne pour
l’effectif.
Déf. L’effectif d’une catégorie est le nombre d’individus qu’elle contient. L’effectif
total est la somme de tous les effectifs.

Exemple. Sport préféré des 25 élèves de la classe :
football 8, natation 5, basket 7, danse 5. Effectif total : 8 + 5 + 7 + 5 = 25.

II. Représenter des données

Le diagramme en barres : une barre par catégorie, la hauteur donne l’effectif. Il faut
toujours graduer l’axe, écrire les noms des catégories, et donner un titre.

Méthode de lecture : repérer l’axe des effectifs, lire la hauteur de la barre, vérifier
que la somme des barres donne bien l’effectif total.

III. Le vocabulaire du hasard

Déf. Une expérience aléatoire est une expérience dont on ne peut pas prévoir le résultat.
Exemples : lancer un dé, tirer une carte.
Déf. Une issue est un résultat possible de l’expérience. Pour un dé à six faces, les
issues sont 1, 2, 3, 4, 5, 6.
Déf. Un événement est ce dont on veut mesurer les chances. « Obtenir un nombre pair » est
un événement, réalisé par les issues 2, 4 et 6.

IV. Comparer des chances

Un événement peut être :
  - impossible : il ne se produit jamais. Obtenir 7 avec un dé à six faces.
  - certain : il se produit toujours. Obtenir un nombre entre 1 et 6.
  - possible : il peut se produire ou non.

Quand toutes les issues ont les mêmes chances, on peut les comparer en comptant.
Exemple. Dans un sac de 10 billes, 3 rouges et 7 bleues : il y a plus de chances de
tirer une bleue qu’une rouge, car 7 > 3.

À retenir : le hasard ne se devine pas, il se compte. « J’ai de la chance » n’est pas une
réponse mathématique.

Repères : un dé a 6 issues, une pièce en a 2."""
    },
    {
        "id": "proportionnalite",
        "domaine": 5,
        "titre": "La proportionnalité",
        "notions": [
            "Reconnaître une situation de proportionnalité",
            "Le coefficient de proportionnalité",
            "Compléter un tableau de proportionnalité",
            "Les pourcentages simples",
            "Les échelles",
        ],
        "transcription": """La proportionnalité

I. Reconnaître la proportionnalité

Déf. Deux grandeurs sont proportionnelles si on passe de l’une à l’autre en multipliant
toujours par le même nombre. Ce nombre s’appelle le coefficient de proportionnalité.

Exemple. 1 croissant coûte 1,20 €. 3 croissants coûtent 3,60 €. 5 croissants coûtent
6 €. On multiplie toujours par 1,20 : c’est proportionnel.

Contre-exemple. L’âge d’une personne et sa taille ne sont pas proportionnels : à 2 ans
on ne mesure pas le double de ce qu’on mesurait à 1 an.

Méthode pour vérifier : diviser chaque valeur de la deuxième ligne par celle de la
première. Si on trouve toujours le même quotient, il y a proportionnalité.

II. Le tableau de proportionnalité

Nombre de croissants : 1 | 3 | 5 | 8
Prix en euros :      1,20 | 3,60 | 6 | 9,60
Coefficient : 1,20

Trois méthodes pour compléter :
  1. Le coefficient : on multiplie par 1,20.
  2. Le passage par l’unité : on cherche d’abord le prix de 1, puis on multiplie.
  3. La linéarité : le prix de 8 = prix de 5 + prix de 3.

III. Les pourcentages

Déf. Prendre t % d’un nombre, c’est le multiplier par t/100.
Exemples : 50 % de 60 = 30 (la moitié). 25 % de 60 = 15 (le quart). 10 % de 60 = 6.
Méthode générale : 15 % de 80 = 80 × 15 : 100 = 12.

IV. Les échelles

Déf. L’échelle d’un plan est le coefficient qui fait passer des distances sur le plan
aux distances réelles.
Exemple. Échelle 1/200 : 1 cm sur le plan représente 200 cm, soit 2 m, dans la réalité.

Attention aux unités : il faut convertir avant de comparer.

À retenir : avant d’appliquer une méthode, on vérifie qu’il y a bien proportionnalité.
Beaucoup d’exercices commencent par un tableau qui n’est pas proportionnel, exprès.

Repères : 50 % = la moitié, 25 % = le quart, 10 % = diviser par 10."""
    },
    {
        "id": "pensee-informatique",
        "domaine": 6,
        "titre": "Initiation à la pensée informatique",
        "notions": [
            "Ce qu’est un algorithme",
            "Les instructions de déplacement",
            "La boucle : répéter n fois",
            "L’instruction conditionnelle : si… alors",
            "Exécuter un programme et prévoir son résultat",
        ],
        "transcription": """Initiation à la pensée informatique

I. Qu’est-ce qu’un algorithme ?

Déf. Un algorithme est une suite d’instructions précises, données dans l’ordre, qui
permet d’obtenir un résultat.
Exemples de la vie courante : une recette de cuisine, un itinéraire.

Un ordinateur exécute exactement ce qu’on lui dit, dans l’ordre où on le lui dit. Il ne
devine rien.

II. Les instructions de déplacement

Pour déplacer un objet sur un quadrillage ou un écran :
  avancer de 100 pas
  tourner de 90 degrés à droite
  aller à x = 0 et y = 0
  stylo en position d’écriture / stylo relevé

III. La boucle

Déf. Une boucle permet de répéter plusieurs fois les mêmes instructions.

Exemple. Tracer un carré de côté 100 :
  répéter 4 fois :
      avancer de 100
      tourner de 90 degrés à droite

Sans la boucle, il faudrait écrire 8 lignes. Avec, on en écrit 3.

Pour un triangle équilatéral : répéter 3 fois (avancer de 100 ; tourner de 120 degrés).
Attention : l’angle à programmer n’est pas l’angle de la figure. Pour un triangle
équilatéral dont les angles font 60°, on tourne de 120°.

IV. L’instruction conditionnelle

Déf. Une instruction conditionnelle exécute des instructions seulement si une condition
est vraie.

  si le nombre est pair alors
      afficher « pair »
  sinon
      afficher « impair »

V. Exécuter un programme à la main

Méthode : on suit les instructions une par une, en notant à chaque étape la position et
la direction. On ne saute aucune ligne.

À retenir : un algorithme faux ne « ne marche pas un peu ». Il fait exactement ce qui est
écrit, et c’est en le déroulant à la main qu’on trouve l’erreur.

Repères : carré = répéter 4 fois avec 90°. Triangle équilatéral = répéter 3 fois avec 120°."""
    },
]

NOMS_GROUPES = DOMAINES
