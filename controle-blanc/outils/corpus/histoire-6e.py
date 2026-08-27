# -*- coding: utf-8 -*-
"""Corpus d’entraînement : le programme d’histoire de 6e, en vigueur.

À quoi ça sert. Le produit travaille sur le cours photographié par l’élève. Tant
qu’on n’a pas de vraies photos de collège, on ne peut pas juger la qualité des
fiches et des questions produites. Ce corpus tient lieu de photos : chaque
chapitre est écrit tel qu’une transcription de cahier le rendrait — titres,
définitions, dates, exemples, « à retenir ».

Ce n’est pas du contenu produit : rien de tout ceci n’est destiné à être servi à
un élève. C’est un banc d’essai, et rien d’autre. Le jour où l’outil sert des
fiches génériques, il ne vend plus rien que ChatGPT ne fasse gratuitement.

Programme de référence. Arrêté de 2015 modifié en 2018 et 2020, celui qui
s’applique en 6e à la rentrée 2026. Le nouveau programme de cycle 3, publié au
Bulletin officiel n°22 du 28 mai 2026, n’entre en vigueur en 6e qu’à la rentrée
2027 : il faudra reprendre ce corpus à ce moment-là.
"""

from __future__ import annotations

PROGRAMME = "Histoire, classe de 6e — arrêté de 2015 modifié (en vigueur en 6e jusqu’en 2027)"

THEMES = [
    "La longue histoire de l’humanité et des migrations",
    "Récits fondateurs, croyances et citoyenneté dans la Méditerranée antique au Ier millénaire avant J.-C.",
    "L’empire romain dans le monde antique",
]

CHAPITRES = [
    {
        "id": "debuts-humanite",
        "theme": 1,
        "titre": "Les débuts de l’humanité",
        "notions": [
            "L’origine africaine de l’humanité",
            "Les principales étapes de l’évolution humaine",
            "Le mode de vie des chasseurs-cueilleurs",
            "Les premières traces d’art et de sépultures",
            "L’échelle du temps préhistorique",
        ],
        "transcription": """Les débuts de l’humanité

I. Où et quand apparaît l’humanité ?

L’humanité apparaît en Afrique, il y a environ 3 millions d’années. Les plus anciens
fossiles d’hominidés ont été retrouvés en Afrique de l’Est, dans la vallée du Rift.
Lucy, un fossile d’australopithèque découvert en Éthiopie en 1974, a environ 3,2
millions d’années.

Déf. Préhistoire : la très longue période qui va de l’apparition des premiers hommes
à l’invention de l’écriture, vers 3300 av. J.-C.

Attention à l’échelle du temps : la Préhistoire, c’est plus de 99 % de l’histoire de
l’humanité. L’écriture, c’est hier.

II. Comment vivent les premiers hommes ?

Les premiers hommes sont des chasseurs-cueilleurs : ils se nourrissent de ce qu’ils
chassent, pêchent et ramassent. Ils sont nomades, c’est-à-dire qu’ils se déplacent
sans cesse pour suivre le gibier et trouver de la nourriture.

Déf. Nomade : qui n’a pas d’habitation fixe et se déplace régulièrement.

Ils vivent en petits groupes. Ils taillent des outils dans la pierre : c’est le
Paléolithique, l’âge de la pierre taillée. Ils maîtrisent le feu, ce qui leur permet
de se réchauffer, de cuire les aliments et de se protéger des animaux.

III. Les premières traces d’une pensée

Vers 40 000 av. J.-C., les hommes peignent sur les parois des grottes : Lascaux en
Dordogne, Chauvet en Ardèche (découverte en 1994, peintures d’environ 36 000 ans).
Ils enterrent aussi leurs morts, avec des objets : ce sont les premières sépultures.
Ces traces montrent que ces hommes ont des croyances.

À retenir : l’humanité naît en Afrique et se répand sur toute la planète par
migrations successives. Les premiers hommes sont nomades, chasseurs-cueilleurs, et
laissent les premières traces d’art et de croyances.

Dates : ~3 millions d’années, premiers hominidés en Afrique. ~40 000 av. J.-C.,
premières peintures. 3300 av. J.-C., invention de l’écriture, fin de la Préhistoire.""",
    },
    {
        "id": "revolution-neolithique",
        "theme": 1,
        "titre": "La « révolution néolithique »",
        "notions": [
            "Le passage de la prédation à la production",
            "L’agriculture et l’élevage",
            "La sédentarisation et les premiers villages",
            "Le Croissant fertile et la diffusion du Néolithique",
            "Les nouvelles techniques : poterie, tissage, pierre polie",
        ],
        "transcription": """La « révolution néolithique »

I. Qu’est-ce que le Néolithique ?

Vers 10 000 av. J.-C., au Proche-Orient, les hommes cessent peu à peu de seulement
chasser et cueillir : ils commencent à produire leur nourriture. Ils cultivent des
céréales (blé, orge) et domestiquent des animaux (mouton, chèvre, bœuf, porc).

Déf. Néolithique : l’âge de la pierre polie, période où les hommes deviennent
agriculteurs et éleveurs.
Déf. Domestication : action d’apprivoiser une espèce sauvage pour l’élever et
l’utiliser.

Pourquoi parle-t-on de « révolution » ? Parce que le changement est complet : on
passe d’une économie de prédation (on prend ce que la nature donne) à une économie
de production (on fait pousser et on élève).

Attention : ce n’est pas une révolution rapide. Elle s’étend sur plusieurs milliers
d’années. Le mot est entre guillemets dans le programme pour cette raison.

II. Où et comment cela se diffuse-t-il ?

Le Néolithique commence dans le Croissant fertile, une région en forme de croissant
qui va de la Mésopotamie à l’Égypte, en passant par le Levant. De là, l’agriculture
et l’élevage se diffusent par migrations et par échanges : ils atteignent la Grèce
vers 7000 av. J.-C., et la France vers 5500 av. J.-C.

III. Quelles conséquences ?

Les hommes deviennent sédentaires : ils construisent des maisons et se regroupent en
villages. Çatal Höyük, en Anatolie (Turquie actuelle), est l’un des plus anciens
villages connus, vers 7000 av. J.-C.

Déf. Sédentaire : qui vit en un lieu fixe.

Nouvelles techniques : la poterie pour conserver les récoltes, le tissage, la pierre
polie pour de meilleurs outils. Les récoltes permettent de constituer des réserves,
donc des surplus. La population augmente. Des inégalités apparaissent entre ceux qui
possèdent beaucoup et ceux qui possèdent peu.

À retenir : au Néolithique, l’homme cesse de subir la nature pour la transformer.
Agriculture, élevage et sédentarisation changent tout : l’habitat, l’alimentation, la
population et l’organisation de la société.

Dates : ~10 000 av. J.-C., début du Néolithique au Proche-Orient. ~5500 av. J.-C.,
arrivée en France.""",
    },
    {
        "id": "premiers-etats-ecritures",
        "theme": 1,
        "titre": "Premiers États, premières écritures",
        "notions": [
            "La naissance des cités-États en Mésopotamie",
            "L’invention de l’écriture vers 3300 av. J.-C.",
            "Le cunéiforme et les hiéroglyphes",
            "Le rôle de l’écriture : compter, gouverner, croire",
            "Le pouvoir du roi et des scribes",
        ],
        "transcription": """Premiers États, premières écritures

I. Où naissent les premiers États ?

Vers 3500-3000 av. J.-C., en Mésopotamie (« le pays entre les fleuves », entre le
Tigre et l’Euphrate, l’Irak actuel), les villages deviennent des villes. Ces villes
s’organisent en cités-États : Ourouk, Our, Lagash. Chacune a son roi, ses temples,
ses murailles et son territoire.

Déf. Cité-État : une ville et le territoire qu’elle contrôle, formant un État
indépendant.

En Égypte, au même moment, le pays est unifié sous l’autorité d’un seul roi, le
pharaon, considéré comme un dieu vivant.

II. Pourquoi invente-t-on l’écriture ?

L’écriture naît en Mésopotamie vers 3300 av. J.-C. Les premières tablettes d’argile
retrouvées ne racontent pas d’histoires : ce sont des comptes. Nombre de sacs de
grain, têtes de bétail, quantités d’huile. On invente l’écriture pour gérer les
surplus et les impôts.

Déf. Cunéiforme : écriture en forme de coins, tracée avec un roseau taillé (le
calame) sur des tablettes d’argile.
Déf. Hiéroglyphes : l’écriture des Égyptiens, faite de dessins, gravée sur la pierre
ou tracée sur le papyrus.

L’écriture sert ensuite à trois choses : compter (les récoltes, les impôts),
gouverner (les lois, comme le code d’Hammourabi vers 1750 av. J.-C.), et croire (les
prières, les récits sur les dieux, comme l’épopée de Gilgamesh).

III. Qui écrit ?

Très peu de gens savent écrire. Les scribes sont des personnages importants : formés
longuement dans des écoles, ils tiennent les comptes du roi et des temples. Savoir
écrire donne du pouvoir.

À retenir : l’invention de l’écriture marque la fin de la Préhistoire et le début de
l’Histoire, vers 3300 av. J.-C. Elle naît d’un besoin pratique — compter — puis sert
à gouverner et à transmettre les croyances.

Dates : ~3300 av. J.-C., invention de l’écriture en Mésopotamie. ~1750 av. J.-C.,
code d’Hammourabi.""",
    },
    {
        "id": "cites-grecques",
        "theme": 2,
        "titre": "Le monde des cités grecques",
        "notions": [
            "La cité grecque : définition et organisation",
            "Les récits fondateurs : l’Iliade et l’Odyssée",
            "Les sanctuaires panhelléniques et les jeux",
            "La colonisation grecque en Méditerranée",
            "La naissance de la démocratie à Athènes",
        ],
        "transcription": """Le monde des cités grecques

I. Qu’est-ce qu’une cité grecque ?

Au VIIIe siècle av. J.-C., les Grecs s’organisent en cités. Une cité, c’est une ville
et la campagne autour, formant un État indépendant. Athènes, Sparte, Corinthe et
Thèbes sont des cités rivales : elles ont chacune leurs lois, leur armée, leurs dieux
protecteurs.

Déf. Cité : un territoire indépendant composé d’une ville et de sa campagne, avec ses
propres lois.

Les Grecs ne forment pas un pays unique, mais ils se reconnaissent entre eux : même
langue, mêmes dieux, mêmes récits.

II. Qu’est-ce qui les unit ?

1. Les récits fondateurs. L’Iliade et l’Odyssée, poèmes attribués à Homère (VIIIe
siècle av. J.-C.), racontent la guerre de Troie et le retour d’Ulysse. Tous les Grecs
les connaissent. Ces récits mêlent hommes et dieux.

2. La religion. Les Grecs sont polythéistes : ils croient en plusieurs dieux, qui
vivent sur le mont Olympe. Zeus, Athéna, Apollon, Poséidon. Ils leur rendent un culte
dans des sanctuaires.

Déf. Polythéiste : qui croit en plusieurs dieux.
Déf. Sanctuaire panhellénique : lieu sacré où se rendent les Grecs de toutes les
cités. Delphes (oracle d’Apollon) et Olympie (jeux en l’honneur de Zeus, tous les 4
ans à partir de 776 av. J.-C.).

III. La colonisation et la démocratie

Entre le VIIIe et le VIe siècle av. J.-C., les Grecs manquent de terres. Ils partent
fonder des colonies tout autour de la Méditerranée et de la mer Noire : Marseille
(Massalia) vers 600 av. J.-C., Syracuse en Sicile. La Méditerranée devient grecque
sur ses rivages.

À Athènes, au Ve siècle av. J.-C., naît la démocratie. Les citoyens se réunissent sur
la Pnyx, à l’Ecclésia, pour voter les lois.

Déf. Démocratie : régime dans lequel les citoyens votent les lois et prennent les
décisions.
Attention : à Athènes, seuls les hommes libres, nés de père et de mère athéniens, âgés
de plus de 18 ans, sont citoyens. Les femmes, les esclaves et les étrangers (métèques)
ne le sont pas. Cela fait environ 10 % de la population.

À retenir : les Grecs sont divisés en cités rivales, mais unis par une langue, des
récits et des dieux communs. Athènes invente la démocratie, mais réservée à une
minorité.

Dates : VIIIe s. av. J.-C., Homère et premières colonies. 776 av. J.-C., premiers jeux
d’Olympie. Ve s. av. J.-C., démocratie athénienne.""",
    },
    {
        "id": "rome-mythe-histoire",
        "theme": 2,
        "titre": "Rome du mythe à l’histoire",
        "notions": [
            "Le mythe de Romulus et Remus",
            "L’Énéide et le récit des origines troyennes",
            "Ce que dit l’archéologie de la fondation de Rome",
            "La différence entre mythe et fait historique",
            "La République romaine et ses institutions",
        ],
        "transcription": """Rome du mythe à l’histoire

I. Ce que les Romains racontent

Selon la légende, Rome est fondée le 21 avril 753 av. J.-C. par Romulus. Romulus et
Remus sont deux jumeaux, fils du dieu Mars, abandonnés sur le Tibre et allaités par
une louve. Devenus grands, ils décident de fonder une ville. Ils se disputent :
Romulus tue Remus et donne son nom à la ville.

Virgile, poète latin, écrit l’Énéide vers 29-19 av. J.-C. : il raconte qu’Énée, prince
troyen, fuit Troie en flammes et gagne l’Italie. Ses descendants fonderont Rome. Ce
récit rattache Rome au monde grec et lui donne un passé prestigieux.

Déf. Mythe : récit imaginaire qui explique les origines d’un peuple, d’une ville ou du
monde.

II. Ce que disent les archéologues

Les fouilles montrent que des villages de bergers existaient sur les collines du
Palatin dès le Xe siècle av. J.-C., soit bien avant 753. Ces villages se regroupent
peu à peu. Il n’y a pas eu de fondation en un jour par un homme.

Attention à ne pas confondre : le mythe raconte ce que les Romains croyaient et
voulaient croire. L’archéologie établit ce qui s’est réellement passé. Les deux
s’étudient, mais pas de la même façon.

III. De la royauté à la République

Rome est d’abord dirigée par des rois. En 509 av. J.-C., les Romains chassent le
dernier roi, Tarquin le Superbe, et fondent la République.

Déf. République : régime dans lequel le pouvoir est exercé par des magistrats élus
pour un an.

Les institutions : le Sénat (assemblée des anciens magistrats, il conseille et dirige
la politique), les comices (assemblées où les citoyens votent et élisent), les
magistrats (les consuls, deux chaque année, dirigent l’armée et l’État).

À retenir : les Romains se donnent une origine divine et troyenne, alors que
l’archéologie montre une naissance lente à partir de villages. En 509 av. J.-C., la
République remplace la royauté.

Dates : 753 av. J.-C., fondation légendaire. 509 av. J.-C., début de la République.""",
    },
    {
        "id": "monotheisme-juif",
        "theme": 2,
        "titre": "La naissance du monothéisme juif dans un monde polythéiste",
        "notions": [
            "Le monothéisme et le polythéisme",
            "La Bible hébraïque comme récit et comme source",
            "Le royaume d’Israël et le Temple de Jérusalem",
            "L’exil à Babylone et la mise par écrit",
            "La diaspora",
        ],
        "transcription": """La naissance du monothéisme juif dans un monde polythéiste

I. Un dieu unique dans un monde qui en a beaucoup

Dans l’Antiquité, presque tous les peuples sont polythéistes : Grecs, Romains,
Égyptiens, Mésopotamiens. Les Hébreux font exception : ils croient en un dieu unique,
Yahvé.

Déf. Monothéisme : croyance en un seul dieu.
Déf. Polythéisme : croyance en plusieurs dieux.

Les Hébreux sont un petit peuple installé en Canaan, au bord de la Méditerranée. Ils
deviendront les Juifs.

II. La Bible : un récit, et une source à interroger

La Bible hébraïque raconte l’histoire des Hébreux : Abraham quittant Our, Moïse
recevant les Dix Commandements sur le Sinaï, la sortie d’Égypte, l’installation en
Canaan, les rois David et Salomon. Salomon fait construire le Temple de Jérusalem.

Attention : la Bible est d’abord un texte religieux, écrit pour transmettre une foi.
Les historiens la lisent comme une source, en la comparant à l’archéologie. Certains
épisodes ne sont confirmés par aucune fouille.

III. L’exil et la diaspora

En 587 av. J.-C., le roi de Babylone Nabuchodonosor prend Jérusalem, détruit le Temple
et déporte une partie de la population : c’est l’exil à Babylone. Loin de leur terre et
sans temple, les Hébreux mettent par écrit leurs textes pour ne pas oublier. Le
monothéisme s’affirme à ce moment-là.

En 70 apr. J.-C., les Romains détruisent le second Temple. Les Juifs se dispersent dans
tout le bassin méditerranéen.

Déf. Diaspora : la dispersion d’un peuple hors de son pays d’origine.

À retenir : le monothéisme juif naît dans un monde polythéiste. C’est l’épreuve de
l’exil, plus que la puissance, qui pousse les Hébreux à écrire et à affirmer leur foi
en un dieu unique.

Dates : ~1000 av. J.-C., royaume de David et Salomon. 587 av. J.-C., destruction du
Temple et exil à Babylone. 70 apr. J.-C., destruction du second Temple.""",
    },
    {
        "id": "conquetes-paix-romaine",
        "theme": 3,
        "titre": "Conquêtes, paix romaine et romanisation",
        "notions": [
            "L’extension de l’Empire romain et ses limites",
            "Auguste et le passage de la République à l’Empire",
            "La paix romaine",
            "La romanisation : villes, routes, latin, citoyenneté",
            "L’édit de Caracalla en 212",
        ],
        "transcription": """Conquêtes, paix romaine et romanisation

I. Un empire immense

Du IIIe siècle av. J.-C. au IIe siècle apr. J.-C., Rome conquiert tout le pourtour de
la Méditerranée, que les Romains appellent Mare Nostrum, « notre mer ». L’Empire
s’étend au IIe siècle de la Bretagne (Angleterre) à l’Égypte, et de l’Espagne à la
Mésopotamie.

Les frontières s’appellent les limes. Elles sont gardées par les légions. Le mur
d’Hadrien, construit en Bretagne à partir de 122, en est un exemple.

II. D’une République à un Empire

Après la guerre civile, Octave, fils adoptif de César, reçoit du Sénat le titre
d’Auguste en 27 av. J.-C. Il détient tous les pouvoirs, mais conserve les apparences
de la République. Il devient le premier empereur.

Déf. Empereur : celui qui détient tous les pouvoirs — militaire, politique, religieux
— sur l’Empire.

À partir d’Auguste s’ouvre une longue période de calme intérieur : la paix romaine
(pax romana), du Ier au IIe siècle. Le commerce se développe, les villes s’agrandissent.

Déf. Paix romaine : longue période de paix et de prospérité dans l’Empire, garantie
par l’armée romaine.

III. Comment Rome intègre-t-elle les peuples conquis ?

C’est la romanisation. Rome n’impose pas tout par la force : elle diffuse son mode de
vie. Dans les provinces, on construit des villes sur le modèle romain, avec forum,
thermes, théâtre, temples. On construit des routes et des aqueducs — le pont du Gard
alimente Nîmes. On parle latin. Les dieux romains se mêlent aux dieux locaux.

En 212, l’édit de Caracalla accorde la citoyenneté romaine à tous les hommes libres de
l’Empire.

Déf. Romanisation : adoption par les peuples conquis du mode de vie, de la langue et
des institutions de Rome.

À retenir : Rome conquiert par les armes puis intègre par la romanisation. La
citoyenneté, d’abord réservée, finit par être accordée à tous les hommes libres en 212.

Dates : 27 av. J.-C., Auguste premier empereur. Ier-IIe s., paix romaine. 122,
construction du mur d’Hadrien. 212, édit de Caracalla.""",
    },
    {
        "id": "chretiens-dans-empire",
        "theme": 3,
        "titre": "Des chrétiens dans l’empire",
        "notions": [
            "La naissance du christianisme en Judée",
            "Jésus, les Évangiles et les sources historiques",
            "La diffusion du christianisme dans l’Empire",
            "Les persécutions et leurs raisons",
            "L’édit de Milan et la reconnaissance du christianisme",
        ],
        "transcription": """Des chrétiens dans l’empire

I. Où et comment naît le christianisme ?

Le christianisme naît au Ier siècle en Judée, une province romaine. Jésus, un Juif de
Galilée, prêche l’amour de Dieu et du prochain. Il est arrêté et crucifié à Jérusalem
vers 30, sous le gouverneur romain Ponce Pilate. Ses disciples affirment qu’il est
ressuscité et qu’il est le fils de Dieu : ils l’appellent le Christ.

Déf. Chrétien : celui qui croit que Jésus est le fils de Dieu.
Déf. Évangiles : les quatre récits de la vie et de l’enseignement de Jésus, écrits
entre 65 et 100 environ.

Les historiens disposent aussi de sources non chrétiennes : Tacite et Suétone,
auteurs romains, mentionnent les chrétiens au début du IIe siècle.

II. Comment le christianisme se diffuse-t-il ?

Les apôtres, en particulier Paul de Tarse, voyagent dans tout l’Empire et fondent des
communautés. La diffusion est facilitée par les routes romaines, la paix romaine et
l’usage du grec et du latin. Le christianisme touche d’abord les villes et les milieux
modestes.

III. Pourquoi les chrétiens sont-ils persécutés ?

Les chrétiens refusent de rendre un culte à l’empereur et aux dieux romains. Pour les
Romains, c’est un refus d’obéissance qui met l’Empire en danger. Les persécutions sont
irrégulières : en 64 sous Néron après l’incendie de Rome, puis surtout au IIIe siècle.

Déf. Persécution : mauvais traitements infligés à un groupe en raison de sa religion.

Tout change au IVe siècle. En 313, l’édit de Milan de l’empereur Constantin autorise
le christianisme. En 380, l’édit de Thessalonique de Théodose en fait la religion
officielle de l’Empire.

À retenir : né dans une province, minoritaire et persécuté, le christianisme devient en
trois siècles la religion officielle de l’Empire romain.

Dates : vers 30, mort de Jésus. 64, persécution sous Néron. 313, édit de Milan. 380,
le christianisme religion officielle.""",
    },
    {
        "id": "route-soie-chine-han",
        "theme": 3,
        "titre": "L’empire romain et les autres mondes anciens : la route de la soie et la Chine des Han",
        "notions": [
            "L’ancienne route de la soie",
            "L’empire des Han et son organisation",
            "Les produits échangés entre Rome et la Chine",
            "Les intermédiaires du commerce",
            "Ce que les deux empires savent l’un de l’autre",
        ],
        "transcription": """L’empire romain et les autres mondes anciens : la route de la soie et la Chine des Han

I. Deux empires aux deux bouts du monde connu

Au IIe siècle apr. J.-C., deux empires immenses existent en même temps : l’Empire
romain autour de la Méditerranée, et l’empire des Han en Chine (206 av. J.-C. – 220
apr. J.-C.). Chacun compte environ 50 à 60 millions d’habitants.

L’empire des Han est dirigé par un empereur. Il est administré par des fonctionnaires
recrutés sur concours, sur leur connaissance des textes. La Chine des Han produit la
soie, le papier (inventé vers 105), la porcelaine.

II. Qu’est-ce que la route de la soie ?

Ce n’est pas une route unique, mais un ensemble de pistes caravanières qui relient la
Chine à la Méditerranée, sur environ 7 000 km, à travers déserts et montagnes.

Déf. Route de la soie : ensemble des itinéraires commerciaux reliant la Chine au monde
méditerranéen.

De la Chine partent la soie, les épices, le jade. De Rome partent l’or, l’argent, le
verre, la laine. La soie est très recherchée à Rome, où elle coûte extrêmement cher :
certains sénateurs s’en plaignent.

III. Des échanges sans rencontre

Aucun marchand ne fait le trajet entier. Les marchandises passent de caravane en
caravane : Parthes, Sogdiens, Indiens servent d’intermédiaires. Chacun prend sa part.

Résultat : Romains et Chinois se connaissent très mal. Les Romains appellent les
Chinois les Sères, « le peuple de la soie », et croient que la soie pousse sur les
arbres. Les sources chinoises parlent de Da Qin, « le grand Qin », pour désigner Rome.
Une ambassade venue de l’Empire romain serait arrivée en Chine en 166.

Circulent aussi des idées et des techniques — et des maladies.

À retenir : deux empires contemporains, reliés par un commerce indirect. Ils échangent
beaucoup de marchandises, et très peu de connaissances l’un sur l’autre.

Dates : 206 av. J.-C. – 220 apr. J.-C., dynastie Han. ~105, invention du papier. 166,
ambassade venue de l’Empire romain en Chine.""",
    },
]
