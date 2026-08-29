/* Contenu de démonstration, repris de app/demo.py — un chapitre d’histoire de 3e.
   Assez concret pour juger le format des questions, ce qui est le but. */

const CHAPITRE = {
  titre: "Civils et militaires dans la Première Guerre mondiale",
  notions: [
    "Les trois phases de la guerre",
    "La notion de guerre totale",
    "Verdun et la guerre de tranchées",
    "Le génocide des Arméniens",
    "La mobilisation de l’arrière et le rôle des femmes",
    "1917, année de crise",
  ],
  transcription: "I. Une guerre d’un type nouveau…",
  photos: [0, 1, 2],
};

const FICHE_GENERALE = {
  titre: "Fiche de révision — " + CHAPITRE.titre,
  duree_lecture_minutes: 8,
  sections: [
    {
      titre: "Une guerre d’un type nouveau",
      pages: [0],
      points: [
        "La guerre commence en août 1914 et s’achève le 11 novembre 1918.",
        "Triple-Entente (France, Royaume-Uni, Russie) contre Empires centraux.",
        "Trois phases : mouvement, position, retour au mouvement en 1918.",
        "Guerre totale : le pays entier est mobilisé, pas seulement l’armée.",
      ],
      a_retenir: "Guerre totale : toutes les ressources du pays sont tournées vers la guerre.",
    },
    {
      titre: "La violence de masse",
      pages: [0, 1],
      points: [
        "Verdun, février à décembre 1916, environ 700 000 victimes.",
        "Les poilus vivent dans les tranchées, sous les obus et les gaz.",
        "Génocide des Arméniens en 1915-1916, environ 1,2 million de morts.",
        "Génocide : extermination programmée d’un peuple entier.",
      ],
      a_retenir: "Verdun illustre la guerre de position, le génocide arménien la violence contre les civils.",
    },
    {
      titre: "L’arrière et l’année 1917",
      pages: [1, 2],
      points: [
        "Les femmes remplacent les hommes à l’usine et aux champs.",
        "L’État emprunte, censure et fait de la propagande.",
        "1917 : mutineries françaises, révolutions russes, entrée des États-Unis.",
      ],
      a_retenir: "1917 est l’année où la guerre vacille, à l’avant comme à l’arrière.",
    },
  ],
  definitions: [
    { terme: "Guerre totale", definition: "Mobilisation de toutes les ressources d’un pays pour la guerre." },
    { terme: "Poilu", definition: "Surnom donné aux soldats français du front." },
    { terme: "Génocide", definition: "Extermination programmée d’un peuple entier." },
  ],
  pieges: [
    "Ne pas confondre les trois phases : Verdun appartient à la guerre de position, pas au mouvement.",
    "Le génocide arménien a lieu dans l’Empire ottoman, pas en Allemagne.",
    "1917 n’est pas la fin de la guerre : l’armistice est en novembre 1918.",
  ],
};

const QUESTIONS = [
  {
    numero: 1,
    partie: "Partie 1 — Connaissances",
    enonce: "Donne les dates de début et de fin de la Première Guerre mondiale, puis nomme les trois phases du conflit.",
    document: "",
    notion: "Les trois phases de la guerre",
    chapitre: CHAPITRE.titre,
    points_attendus: [
      "Août 1914 pour le début",
      "11 novembre 1918 pour l’armistice",
      "Guerre de mouvement, guerre de position, retour au mouvement en 1918",
    ],
    ou_dans_le_cours: "Partie I de ton cours, « Une guerre d’un type nouveau », premier paragraphe.",
    duree_minutes: 5,
  },
  {
    numero: 2,
    partie: "Partie 1 — Connaissances",
    enonce: "Qu’appelle-t-on une « guerre totale » ? Donne deux exemples tirés de ton cours.",
    document: "",
    notion: "La notion de guerre totale",
    chapitre: CHAPITRE.titre,
    points_attendus: [
      "Définition : mobilisation de toutes les ressources du pays",
      "Un exemple économique (emprunts, usines d’armement)",
      "Un exemple humain (les femmes dans les usines)",
    ],
    ou_dans_le_cours: "Fin de la partie I, et partie III sur l’arrière.",
    duree_minutes: 7,
  },
  {
    numero: 3,
    partie: "Partie 2 — Étude de document",
    enonce: "Ce témoignage illustre quelle phase de la guerre ? Relève deux éléments du texte qui le montrent, puis explique ce que ton cours ajoute sur les conditions de vie des soldats.",
    document:
      "« Nous tenons le même bout de tranchée depuis onze semaines. La boue monte jusqu’aux genoux, les rats passent sur nos visages la nuit. Ce matin encore, les obus sont tombés pendant quatre heures sans que nous puissions bouger. »\nLettre d’un soldat français, secteur de Verdun, mars 1916.",
    notion: "Verdun et la guerre de tranchées",
    chapitre: CHAPITRE.titre,
    points_attendus: [
      "La guerre de position, reconnue à partir du texte",
      "Deux éléments relevés : immobilité du front, boue, rats, bombardements",
      "Apport du cours : gaz de combat, ampleur des pertes à Verdun",
    ],
    ou_dans_le_cours: "Partie II, « La violence de masse », paragraphe sur Verdun.",
    duree_minutes: 12,
  },
  {
    numero: 4,
    partie: "Partie 2 — Étude de document",
    enonce: "Explique ce qu’est le génocide des Arméniens : où, quand, et pourquoi on emploie le mot « génocide ».",
    document: "",
    notion: "Le génocide des Arméniens",
    chapitre: CHAPITRE.titre,
    points_attendus: [
      "Dans l’Empire ottoman, 1915-1916",
      "Environ 1,2 million de victimes",
      "Le mot génocide : extermination programmée d’un peuple entier",
    ],
    ou_dans_le_cours: "Partie II, dernier paragraphe.",
    duree_minutes: 8,
  },
  {
    numero: 5,
    partie: "Partie 3 — Développement construit",
    enonce: "En un paragraphe d’une quinzaine de lignes, montre que la Première Guerre mondiale a été une guerre totale qui a touché aussi bien les soldats que les civils.",
    document: "",
    notion: "La mobilisation de l’arrière et le rôle des femmes",
    chapitre: CHAPITRE.titre,
    points_attendus: [
      "Une introduction qui reprend la question",
      "Un exemple pour les soldats (tranchées, Verdun)",
      "Un exemple pour les civils (femmes à l’usine, censure, génocide arménien)",
      "Une conclusion qui répond à la question posée",
    ],
    ou_dans_le_cours: "Tout le chapitre, en particulier les parties II et III.",
    duree_minutes: 20,
  },
];

const QUESTIONS_BIS = [
  {
    numero: 1,
    partie: "Partie 1 — Connaissances",
    enonce: "En quoi 1917 est-elle une « année de crise » ? Cite trois événements.",
    document: "",
    notion: "1917, année de crise",
    chapitre: CHAPITRE.titre,
    points_attendus: [
      "Les mutineries après le Chemin des Dames",
      "Les révolutions russes",
      "L’entrée en guerre des États-Unis en avril 1917",
    ],
    ou_dans_le_cours: "Partie III, dernier paragraphe.",
    duree_minutes: 6,
  },
  {
    numero: 2,
    partie: "Partie 1 — Connaissances",
    enonce: "Un camarade écrit : « La guerre totale, c’est quand toute l’Europe se bat. » Corrige-le et donne la bonne définition.",
    document: "",
    notion: "La notion de guerre totale",
    chapitre: CHAPITRE.titre,
    points_attendus: [
      "Repérer l’erreur : ce n’est pas l’étendue géographique",
      "Définition exacte : mobilisation de toutes les ressources d’un pays",
      "Un exemple concret du cours",
    ],
    ou_dans_le_cours: "Fin de la partie I.",
    duree_minutes: 7,
  },
  {
    numero: 3,
    partie: "Partie 2 — Étude de document",
    enonce: "Que nous apprend cette affiche sur la manière dont l’État mobilise l’arrière ? Relie-la à deux éléments de ton cours.",
    document:
      "Affiche officielle française, 1916. Une femme en blouse d’usine tend un obus vers un soldat au front. En haut : « Pour eux, ne comptez pas vos heures. » En bas : « Souscrivez à l’emprunt de la Défense nationale. »",
    notion: "La mobilisation de l’arrière et le rôle des femmes",
    chapitre: CHAPITRE.titre,
    points_attendus: [
      "La propagande de l’État",
      "Le travail des femmes dans les usines d’armement",
      "L’emprunt auprès des populations",
    ],
    ou_dans_le_cours: "Partie III, « L’arrière et les civils ».",
    duree_minutes: 12,
  },
  {
    numero: 4,
    partie: "Partie 3 — Développement construit",
    enonce: "En une dizaine de lignes, explique pourquoi Verdun est devenue le symbole de la Première Guerre mondiale en France.",
    document: "",
    notion: "Verdun et la guerre de tranchées",
    chapitre: CHAPITRE.titre,
    points_attendus: [
      "Les dates : février à décembre 1916",
      "L’ampleur des pertes, environ 700 000 victimes",
      "Les conditions de vie dans les tranchées",
      "Une conclusion qui répond à la question",
    ],
    ou_dans_le_cours: "Partie II.",
    duree_minutes: 18,
  },
];

// Ce que le faux serveur attend de tout jeu de contenus.
const CHAPITRES = [CHAPITRE];
const MATIERE_DETECTEE = 'Histoire-Géographie / EMC';
const MATIERE_PAR_DEFAUT = 'histoire-geographie';
const CIBLEE_PAR_DEFAUT = 'La notion de guerre totale';
const CIBLEE_DEFINITIONS = [
  { terme: 'Guerre totale', definition: 'Mobilisation de toutes les ressources d’un pays pour la guerre.' },
];
const CIBLEE_PIEGES = ['Citer une date sans dire ce qui s’y passe ne rapporte rien.'];
const MOT_DE_FIN = 'Relis la fiche ciblée, puis retente un contrôle sur ces notions-là. ' +
  'C’est en les reposant qu’elles rentrent.';

/* Le quiz éclair : le même que celui du serveur en mode démonstration, pour
   que les deux racontent la même chose. */
const QUIZ = [
    {
        numero: 1,
        enonce: 'Dans ce cours, que désigne l’expression « guerre totale » ?',
        propositions: [
            'Une guerre qui s’étend au monde entier',
            'Une guerre où toutes les ressources du pays sont mobilisées',
            'Une guerre menée sans respecter aucune règle',
            'Une guerre qui se termine par la disparition d’un État',
        ],
        juste: 1,
        pourquoi_juste: 'Économiques, humaines, scientifiques : tout le pays y passe.',
        pourquoi_faux: [
            'C’est la définition de « mondiale ». « Totale » ne parle pas de l’étendue, mais de tout ce que le pays engage.',
            '',
            'Ça, c’est la violence de masse — un autre point du chapitre.',
            'Rien dans ton cours ne rattache « totale » à la disparition d’un État.',
        ],
        notion: 'La notion de guerre totale',
        chapitre: 'Civils et militaires dans la Première Guerre mondiale',
        ou_dans_le_cours: 'Partie I, dernier paragraphe.',
    },
    {
        numero: 2,
        enonce: 'Quelle bataille ton cours donne-t-il comme emblématique de la guerre de position ?',
        propositions: ['La Marne', 'Verdun', 'La Somme', 'Sedan'],
        juste: 1,
        pourquoi_juste: 'Verdun, février-décembre 1916.',
        pourquoi_faux: [
            'La Marne, c’est 1914 — la guerre de mouvement, pas les tranchées.',
            '',
            'La Somme est bien de 1916, mais ce n’est pas celle que ton cours retient.',
            'Sedan appartient à un autre conflit : elle n’est pas dans ce chapitre.',
        ],
        notion: 'Verdun et la guerre de tranchées',
        chapitre: 'Civils et militaires dans la Première Guerre mondiale',
        ou_dans_le_cours: 'Partie II, première phrase.',
    },
    {
        numero: 3,
        enonce: 'Combien de phases ton cours distingue-t-il dans la guerre ?',
        propositions: ['Deux', 'Trois', 'Quatre', 'Cinq'],
        juste: 1,
        pourquoi_juste: 'Mouvement, position, puis mouvement à nouveau en 1918.',
        pourquoi_faux: [
            'Deux, ce serait oublier le retour du mouvement en 1918.',
            '',
            'Ton cours n’en compte pas quatre : relis la liste, elle en donne trois.',
            'Cinq ne correspond à rien dans ce chapitre.',
        ],
        notion: 'Les trois phases de la guerre',
        chapitre: 'Civils et militaires dans la Première Guerre mondiale',
        ou_dans_le_cours: 'Partie I, deuxième paragraphe.',
    },
    {
        numero: 4,
        enonce: 'Qui remplace les hommes dans les usines pendant le conflit ?',
        propositions: [
            'Les prisonniers de guerre seuls',
            'Les femmes',
            'Les enfants dès dix ans',
            'Personne : les usines ferment',
        ],
        juste: 1,
        pourquoi_juste: 'C’est l’exemple type de la mobilisation de l’arrière.',
        pourquoi_faux: [
            'Ton cours ne parle pas des prisonniers à cet endroit.',
            '',
            'Le travail des enfants n’est pas ce que ton cours retient ici.',
            'Au contraire : les usines se convertissent à l’armement.',
        ],
        notion: 'La mobilisation de l’arrière et le rôle des femmes',
        chapitre: 'Civils et militaires dans la Première Guerre mondiale',
        ou_dans_le_cours: 'Partie III, sur la mobilisation de l’arrière.',
    },
    {
        numero: 5,
        enonce: 'Quelle année ton cours désigne-t-il comme « année de crise » ?',
        propositions: ['1914', '1916', '1917', '1918'],
        juste: 2,
        pourquoi_juste: 'Mutineries, grèves, révolution russe : tout tombe la même année.',
        pourquoi_faux: [
            '1914, c’est l’entrée en guerre, pas la crise.',
            '1916 est l’année de Verdun — dure, mais ce n’est pas le mot de ton cours.',
            '',
            '1918 est l’année de la fin, marquée par le retour du mouvement.',
        ],
        notion: '1917, année de crise',
        chapitre: 'Civils et militaires dans la Première Guerre mondiale',
        ou_dans_le_cours: 'Partie III, sur 1917.',
    },
    {
        numero: 6,
        enonce: 'En quelle année le génocide des Arméniens commence-t-il, d’après ton cours ?',
        propositions: ['1914', '1915', '1917', '1918'],
        juste: 1,
        pourquoi_juste: '1915-1916, pendant la guerre.',
        pourquoi_faux: [
            '1914 est l’année de l’entrée en guerre, pas celle-là.',
            '',
            '1917 est l’année de crise : ne confonds pas les deux repères.',
            '1918 est l’année de l’armistice.',
        ],
        notion: 'Le génocide des Arméniens',
        chapitre: 'Civils et militaires dans la Première Guerre mondiale',
        ou_dans_le_cours: 'Partie II, sur la violence de masse.',
    },
]
