/* Contenus de démonstration — espagnol, Première.
 *
 * Ce que l’outil produirait à partir des quatre pages d’un cahier réel : deux
 * séquences, une fiche, un contrôle blanc au format de la matière, et un second
 * contrôle sur les notions ratées.
 *
 * Les consignes sont en français et les réponses attendues en espagnol, comme
 * dans un vrai contrôle de langue vivante.
 */

const SEQUENCE_TURISMO = {
  titre: 'Turismo: luces y sombras',
  notions: [
    'El peso del turismo en la economía española',
    'Ventajas e inconvenientes del turismo de masas',
    'El turismo comunitario como alternativa sostenible',
    'Léxico: sector, potencia, PIB, sostenible, medio ambiente',
  ],
  transcription: `Luces y sombras del turismo

El gráfico y el artículo de prensa evidencian la importancia del turismo en España y el
crecimiento de este sector después de la pandemia de covid 19.

España es la segunda potencia mundial en número de viajeros internacionales, detrás de
Francia y antes de EE. UU.

Los beneficios son económicos: el turismo representa el 13 por ciento del PIB.

Las desventajas son las consecuencias de los numerosos proyectos hoteleros y de
transporte. Además plantea el problema del agua.

España debe apostar por un turismo más sostenible.

Un turismo comunitario, una alternativa ecológica

Es una forma de turismo sostenible donde los habitantes locales organizan actividades,
reciben a los visitantes y comparten su modo de vida.

Los turistas viven experiencias auténticas como la danza, la música, la comida típica,
rituales a la Pachamama.

A diferencia del turismo de masas, este turismo beneficia directamente a todas las
familias de manera equitativa.

Permite proteger el medio ambiente y la identidad cultural.

Este objetivo es sensibilizar sobre otra manera de hacer turismo.`,
  photos: [0],
};

const SEQUENCE_MADRID = {
  titre: 'Madrid, capital cultural e histórica',
  notions: [
    'La campaña turística de Madrid y su objetivo',
    'La frase exclamativa y sus acentos',
    'El futuro hipotético (a lo mejor, quizás + subjuntivo)',
    'Velázquez, Goya y los museos madrileños',
    'El 2 de mayo de 1808 y la guerra de independencia',
    'La estructura tan + adjetivo + que',
  ],
  transcription: `La campaña turística de Madrid

En la campaña turística se mencionan muchas actividades y lugares diferentes. Se pueden
ver varios museos. También se pueden comer platos típicos y comida gastronómica. Además,
en Madrid puedes disfrutar de la vida nocturna.

Madrid es cultura porque hay muchos museos que visitar.
Madrid es atractiva porque se puede disfrutar de muchas actividades chulas.
El objetivo de la campaña es dar a conocer de forma positiva esta capital.

« Una visita por Madrid » — Tu misión: eres guía turístico en Madrid, les anuncias a los
visitantes el programa del día con el mapa de la ciudad. [La suite est masquée par une
feuille posée sur la page.]

La frase exclamativa

Les mots exclamatifs, comme les mots interrogatifs, portent toujours un accent.
  Qué      ¡Qué bonito día!        → Quelle belle journée !
  Quién    ¡Quién sabe!            → Qui sait !
  Dónde    ¡Dónde se metió!        → Dans quoi s’est-il mis !
  Cuándo   ¡Cuándo quiera!         → Quand il veut !
  Cómo     ¡Cómo duermes!          → Qu’est-ce que tu dors !
  Cuánto / Cuánta   ¡Cuánta gente! → Que de monde !

Clara y Óliver están contemplando las obras de Velázquez (pintor del siglo XVII):
Las hilanderas (± 1656), Las meninas (1656-57).
El texto invita a descubrir el arte como una experiencia única, viva.

El futuro hipotético (= a lo mejor, quizás + subjonctif)
  El chico contemplará una obra de Goya. Estará fascinado.
  Imaginará la historia de la obra. Soñará con vivir en la época de Velázquez.

Publica un comentario sobre tu visita al museo:
  « Acabo de visitar el Thyssen en Madrid. ¡Qué bonito museo! »

Madrid, ciudad histórica

Fecha: el 2 de mayo de 1808.
Acontecimiento: tuvo lugar el alzamiento ciudadano contra las tropas francesas,
desatando la guerra de independencia española.
Lugares: en el centro de Madrid, la Puerta del Sol.

Los actores — las tropas de Napoleón y sus caballos:
  soldados con casco dorado = tropa regular ;
  soldados con turbante = los mamelucos = guerreros egipcios.

Los caballos dan superioridad a las tropas francesas ; sienten el horror de la batalla.
Parte de abajo: gente que ya ha muerto → sangre, heridas.

El ejército de Napoleón era tan superior que murieron más de cuatrocientos madrileños.
  [tan + adjectif + que = conséquence]

Goya nació en 1746 en Fuendetodos y murió en 1828 en Burdeos. Fue un pintor de la corte.
Pintó El dos de mayo y El tres de mayo, y Las majas.`,
  photos: [1, 2, 3],
};

const CHAPITRE = SEQUENCE_MADRID;
const CHAPITRES = [SEQUENCE_TURISMO, SEQUENCE_MADRID];
const MATIERE_DETECTEE = 'Espagnol';
const MATIERE_PAR_DEFAUT = 'espagnol';
const CIBLEE_PAR_DEFAUT = 'Los acentos de la frase exclamativa';
const CIBLEE_DEFINITIONS = [
  { terme: 'Frase exclamativa', definition: 'Phrase d’exclamation. Le mot exclamatif porte toujours un accent écrit : qué, quién, cómo, cuánto.' },
  { terme: 'Futuro hipotético', definition: 'Le futur employé pour exprimer une hypothèse. Équivaut à a lo mejor ou quizás + subjonctif.' },
];
const CIBLEE_PIEGES = [
  'Écrire ¡Que bonito! sans accent. En espagnol, l’accent est ce qui distingue l’exclamatif du relatif.',
  'Traduire le futuro hipotético par un futur français. « Estará fascinado » veut dire « il doit être fasciné », pas « il sera fasciné ».',
];
const MOT_DE_FIN = 'Tes accords en genre et en nombre sont ce qui te coûte le plus. ' +
  'Relis la fiche ciblée, puis retente le contrôle sur ces points-là.';

const FICHE_GENERALE = {
  titre: 'Fiche de révision — Turismo y Madrid',
  duree_lecture_minutes: 9,
  sections: [
    {
      titre: 'El turismo en España: cifras y debate',
      points: [
        'España es la segunda potencia mundial en número de viajeros internacionales, detrás de Francia y antes de EE. UU.',
        'El turismo representa el 13 por ciento del PIB: es un beneficio económico mayor.',
        'Las desventajas: los numerosos proyectos hoteleros y de transporte, y el problema del agua.',
        'Ce que ton cours conclut : España debe apostar por un turismo más sostenible.',
      ],
      a_retenir: 'Deux chiffres suffisent pour toute la première partie : deuxième mondial, 13 % du PIB.',
    },
    {
      titre: 'El turismo comunitario',
      points: [
        'Los habitantes locales organizan las actividades, reciben a los visitantes y comparten su modo de vida.',
        'Los turistas viven experiencias auténticas: la danza, la música, la comida típica, los rituales a la Pachamama.',
        'A diferencia del turismo de masas, beneficia a todas las familias de manera equitativa.',
        'Permite proteger el medio ambiente y la identidad cultural.',
      ],
      a_retenir: 'C’est l’opposition qui compte : turismo de masas contre turismo comunitario. Toute question passera par là.',
    },
    {
      titre: 'La campaña turística de Madrid',
      points: [
        'La campaña menciona muchas actividades y lugares: museos, platos típicos, vida nocturna.',
        'Madrid es cultura porque hay muchos museos que visitar.',
        'Madrid es atractiva porque se puede disfrutar de muchas actividades.',
        'El objetivo es dar a conocer de forma positiva esta capital.',
      ],
      a_retenir: 'Retiens la structure « Madrid es… porque se puede… » : elle sert pour l’expression écrite.',
    },
    {
      titre: 'La frase exclamativa',
      points: [
        'Le mot exclamatif porte toujours un accent écrit, comme l’interrogatif.',
        '¡Qué bonito día! → Quelle belle journée. ¡Quién sabe! → Qui sait !',
        '¡Cómo duermes! → Qu’est-ce que tu dors ! ¡Cuánta gente! → Que de monde !',
        'La phrase s’ouvre par ¡ et se ferme par ! — les deux signes sont obligatoires.',
      ],
      a_retenir: 'Sans accent, ce n’est plus une exclamation. C’est la faute la plus vite sanctionnée.',
    },
    {
      titre: 'El futuro hipotético',
      points: [
        'Le futur espagnol sert aussi à exprimer une hypothèse sur le présent.',
        'Estará fascinado = il doit être fasciné, peut-être qu’il est fasciné.',
        'Équivalents du cours : a lo mejor + indicatif, quizás + subjonctif.',
        'Autres exemples : contemplará una obra, imaginará la historia, soñará con vivir en la época de Velázquez.',
      ],
      a_retenir: 'Un futur espagnol ne se traduit pas toujours par un futur français. C’est le piège du chapitre.',
    },
    {
      titre: 'Madrid histórica: el 2 de mayo y los pintores',
      points: [
        'El 2 de mayo de 1808: alzamiento ciudadano contra las tropas francesas, en la Puerta del Sol.',
        'Desató la guerra de independencia española.',
        'Los mamelucos, soldados con turbante, eran guerreros egipcios al servicio de Napoleón.',
        'Goya (1746 Fuendetodos – 1828 Burdeos), pintor de la corte, pintó El dos de mayo, El tres de mayo y Las majas.',
        'Velázquez, pintor del siglo XVII: Las meninas, Las hilanderas.',
        'La structure tan + adjectif + que exprime la conséquence : era tan superior que murieron más de cuatrocientos madrileños.',
      ],
      a_retenir: 'Ne confonds pas les deux peintres : Velázquez au XVIIe siècle, Goya au tournant du XIXe.',
    },
  ],
  definitions: [
    { terme: 'Sostenible', definition: 'Durable. Un turismo sostenible respeta el medio ambiente y a los habitantes.' },
    { terme: 'El PIB', definition: 'Le PIB, producto interior bruto. El turismo representa el 13 % del PIB español.' },
    { terme: 'El alzamiento', definition: 'Le soulèvement. El alzamiento ciudadano del 2 de mayo de 1808.' },
    { terme: 'Tan + adjetivo + que', definition: 'Structure de conséquence : si… que. Era tan superior que murieron cuatrocientos madrileños.' },
    { terme: 'Acabar de + infinitivo', definition: 'Venir de faire. Acabo de visitar el Thyssen = je viens de visiter le Thyssen.' },
  ],
  pieges: [
    'Tes accords en genre. Ton cahier écrit « Las beneficios » et « Una turismo » : ce sont los beneficios et un turismo. C’est ta faute la plus fréquente.',
    'Tes accords en nombre : « hay mucho museos » et « eres guía turísticos ». Il faut muchos museos, et guía turístico au singulier.',
    'Oublier l’accent sur qué, quién, cómo, cuánto dans une exclamation.',
    'Oublier le ¡ ouvrant. Une exclamation espagnole s’ouvre et se ferme.',
    'Traduire estará par « il sera ». En futuro hipotético, c’est « il doit être ».',
  ],
};

const QUESTIONS = [
  {
    numero: 1,
    partie: 'Comprensión — Parte 1',
    enonce: 'Relève dans le texte deux conséquences négatives du tourisme de masse à Madrid. Réponds en espagnol, en citant le texte.',
    document: '« Madrid recibió el año pasado más de diez millones de visitantes. En el centro, los vecinos se quejan: los alquileres han subido, muchos pisos se han convertido en apartamentos turísticos y las tiendas de barrio han cerrado. El ayuntamiento estudia limitar el número de licencias. "No estamos contra el turismo", explica una vecina de Lavapiés, "pero queremos seguir viviendo aquí." »\n\nAdaptado de un artículo de prensa española.',
    notion: 'Ventajas e inconvenientes del turismo de masas',
    chapitre: 'Turismo: luces y sombras',
    points_attendus: [
      'La subida de los alquileres — « los alquileres han subido »',
      'La transformación de los pisos en apartamentos turísticos',
      'El cierre de las tiendas de barrio',
      'Deux éléments cités en espagnol, avec les mots du texte',
    ],
    ou_dans_le_cours: 'Séquence « Turismo », le paragraphe sur les desventajas.',
    duree_minutes: 5,
    poids: 1,
  },
  {
    numero: 2,
    partie: 'Comprensión — Parte 1',
    enonce: 'Que propose la mairie de Madrid ? Réponds par une phrase complète en espagnol.',
    document: '',
    notion: 'Ventajas e inconvenientes del turismo de masas',
    chapitre: 'Turismo: luces y sombras',
    points_attendus: [
      'El ayuntamiento estudia limitar el número de licencias',
      'Une phrase complète, pas une citation brute',
      'Le verbe conjugué correctement au présent',
    ],
    ou_dans_le_cours: 'Le document lui-même : cette question ne demande pas le cours.',
    duree_minutes: 4,
    poids: 1,
  },
  {
    numero: 3,
    partie: 'Comprensión — Parte 1',
    enonce: 'En t’appuyant sur ton cours, explique en espagnol (3 ou 4 phrases) en quoi le turismo comunitario apporte une réponse au problème décrit dans le texte.',
    document: '',
    notion: 'El turismo comunitario como alternativa sostenible',
    chapitre: 'Turismo: luces y sombras',
    points_attendus: [
      'Los habitantes locales organizan las actividades y comparten su modo de vida',
      'Beneficia directamente a todas las familias de manera equitativa',
      'Permite proteger el medio ambiente y la identidad cultural',
      'L’opposition explicite avec el turismo de masas',
    ],
    ou_dans_le_cours: 'Séquence « Turismo », la partie sur le turismo comunitario.',
    duree_minutes: 6,
    poids: 2,
  },
  {
    numero: 4,
    partie: 'Lengua — Parte 2',
    enonce: 'Transforme ces trois phrases en phrases exclamatives, en respectant l’accentuation et la ponctuation espagnoles.\na) El día es bonito.\nb) Hay mucha gente en el museo.\nc) Duermes mucho.',
    document: '',
    notion: 'La frase exclamativa y sus acentos',
    chapitre: 'Madrid, capital cultural e histórica',
    points_attendus: [
      'a) ¡Qué bonito día!',
      'b) ¡Cuánta gente!',
      'c) ¡Cómo duermes!',
      'L’accent écrit sur qué, cuánta, cómo',
      'Le ¡ ouvrant et le ! fermant sur chaque phrase',
    ],
    ou_dans_le_cours: 'Le tableau de la frase exclamativa, séquence Madrid.',
    duree_minutes: 5,
    poids: 2,
  },
  {
    numero: 5,
    partie: 'Lengua — Parte 2',
    enonce: 'Réécris ces phrases au futuro hipotético, puis traduis-les en français pour montrer que tu en as compris le sens.\na) A lo mejor el chico contempla una obra de Goya.\nb) Quizás esté fascinado.',
    document: '',
    notion: 'El futuro hipotético',
    chapitre: 'Madrid, capital cultural e histórica',
    points_attendus: [
      'a) El chico contemplará una obra de Goya',
      'b) Estará fascinado',
      'Traductions : « Le garçon est sans doute en train de contempler… » et « Il doit être fasciné »',
      'La traduction ne doit pas employer un futur français : c’est ce que la question vérifie',
    ],
    ou_dans_le_cours: 'La partie sur le futuro hipotético, avec la marge « = a lo mejor, quizás + subj ».',
    duree_minutes: 6,
    poids: 2,
  },
  {
    numero: 6,
    partie: 'Lengua — Parte 2',
    enonce: 'Relie ces deux phrases avec la structure tan + adjetivo + que étudiée en cours : « El ejército de Napoleón era superior. » / « Murieron más de cuatrocientos madrileños. »',
    document: '',
    notion: 'La estructura tan + adjetivo + que',
    chapitre: 'Madrid, capital cultural e histórica',
    points_attendus: [
      'El ejército de Napoleón era tan superior que murieron más de cuatrocientos madrileños',
      'La structure exprime la conséquence',
      'Le verbe de la subordonnée reste au passé',
    ],
    ou_dans_le_cours: 'Séquence Madrid, l’annotation de marge « tan + adj + que = conséquence ».',
    duree_minutes: 5,
    poids: 1,
  },
  {
    numero: 7,
    partie: 'Civilización — Parte 3',
    enonce: 'Que s’est-il passé le 2 mai 1808 à Madrid ? Réponds en espagnol en précisant le lieu, les acteurs en présence et la conséquence de cet événement.',
    document: '',
    notion: 'El 2 de mayo de 1808 y la guerra de independencia',
    chapitre: 'Madrid, capital cultural e histórica',
    points_attendus: [
      'El alzamiento ciudadano contra las tropas francesas',
      'El lugar: el centro de Madrid, la Puerta del Sol',
      'Los actores: las tropas de Napoleón, con los mamelucos, guerreros egipcios con turbante',
      'La consecuencia: desató la guerra de independencia española',
    ],
    ou_dans_le_cours: 'Séquence Madrid, la fiche « Madrid, ciudad histórica ».',
    duree_minutes: 6,
    poids: 2,
  },
  {
    numero: 8,
    partie: 'Civilización — Parte 3',
    enonce: 'Ton cours cite deux peintres. Pour chacun, donne son siècle et une œuvre. Explique en une phrase ce qui les distingue.',
    document: '',
    notion: 'Velázquez, Goya y los museos madrileños',
    chapitre: 'Madrid, capital cultural e histórica',
    points_attendus: [
      'Velázquez, pintor del siglo XVII: Las meninas o Las hilanderas',
      'Goya, 1746-1828: El dos de mayo, El tres de mayo o Las majas',
      'Los separan casi dos siglos',
      'Los dos fueron pintores de la corte',
    ],
    ou_dans_le_cours: 'Séquence Madrid, le passage sur Velázquez et la fiche sur Goya.',
    duree_minutes: 5,
    poids: 2,
  },
  {
    numero: 9,
    partie: 'Expresión escrita — Parte 4',
    enonce: 'Tu viens de visiter un musée à Madrid. Rédige en espagnol le commentaire que tu publies (10 à 15 lignes). Tu emploieras au moins une phrase exclamative, la structure acabar de + infinitivo, et tu citeras une œuvre étudiée en cours.',
    document: '',
    notion: 'La campaña turística de Madrid',
    chapitre: 'Madrid, capital cultural e histórica',
    points_attendus: [
      'Acabo de visitar… — la structure exigée par la consigne',
      'Au moins une exclamation correctement accentuée et ponctuée, du type ¡Qué bonito museo!',
      'Une œuvre du cours citée : Las meninas, El tres de mayo, Las majas',
      'Le lexique de la séquence : museo, obra, pintor, disfrutar de',
      'Une longueur de 10 à 15 lignes, en phrases construites',
      'Les accords en genre et en nombre — c’est ce qui est le plus surveillé ici',
    ],
    ou_dans_le_cours: 'Toute la séquence Madrid, en particulier le modèle « Acabo de visitar el Thyssen ».',
    duree_minutes: 15,
    poids: 2,
  },
];

const QUESTIONS_BIS = [
  {
    numero: 1,
    partie: 'Lengua — Parte 1',
    enonce: 'Corrige les cinq phrases suivantes. Chacune contient une faute, et une seule.\na) Las beneficios son económicos.\nb) Un turismo comunitario es una alternativa.\nc) En Madrid hay mucho museos.\nd) Eres guía turísticos en Madrid.\ne) Los numerosas proyectos hoteleros.',
    document: '',
    notion: 'Los acuerdos de género y de número',
    chapitre: 'Madrid, capital cultural e histórica',
    points_attendus: [
      'a) Los beneficios — beneficio est masculin',
      'b) Phrase correcte, il n’y a pas de faute — c’est le piège',
      'c) muchos museos — accord en nombre',
      'd) guía turístico — le sujet est au singulier',
      'e) los numerosos proyectos — accord en genre et en nombre',
    ],
    ou_dans_le_cours: 'Ce sont les formes relevées dans ton propre cahier lors de l’analyse.',
    duree_minutes: 8,
    poids: 2,
  },
  {
    numero: 2,
    partie: 'Lengua — Parte 1',
    enonce: 'Écris quatre phrases exclamatives à partir de ces éléments, en soignant accents et ponctuation : a) un museo / bonito — b) gente / mucha — c) el día / largo — d) saber / quién.',
    document: '',
    notion: 'La frase exclamativa y sus acentos',
    chapitre: 'Madrid, capital cultural e histórica',
    points_attendus: [
      'a) ¡Qué bonito museo!',
      'b) ¡Cuánta gente!',
      'c) ¡Qué largo día! ou ¡Qué día tan largo!',
      'd) ¡Quién sabe!',
      'Chaque mot exclamatif accentué, chaque phrase encadrée par ¡ et !',
    ],
    ou_dans_le_cours: 'Le tableau de la frase exclamativa.',
    duree_minutes: 7,
    poids: 2,
  },
  {
    numero: 3,
    partie: 'Lengua — Parte 2',
    enonce: 'Voici trois phrases au futuro hipotético. Traduis-les en français, puis réécris chacune avec « a lo mejor » ou « quizás ».\na) Soñará con vivir en la época de Velázquez.\nb) Imaginará la historia de la obra.\nc) El museo estará cerrado.',
    document: '',
    notion: 'El futuro hipotético',
    chapitre: 'Madrid, capital cultural e histórica',
    points_attendus: [
      'a) « Il rêve sans doute de vivre à l’époque de Velázquez » / A lo mejor sueña con…',
      'b) « Il doit imaginer l’histoire de l’œuvre » / Quizás imagine la historia…',
      'c) « Le musée doit être fermé » / A lo mejor está cerrado',
      'Aucune traduction ne doit employer un futur français',
      'Quizás est suivi du subjonctif, a lo mejor de l’indicatif',
    ],
    ou_dans_le_cours: 'La marge « = a lo mejor, quizás + subj », séquence Madrid.',
    duree_minutes: 9,
    poids: 2,
  },
  {
    numero: 4,
    partie: 'Expresión escrita — Parte 3',
    enonce: 'Un ami te dit : « Madrid no me interesa, es una ciudad como otra cualquiera. » Réponds-lui en espagnol (8 à 10 lignes) pour le convaincre. Tu emploieras au moins une exclamation et la structure tan + adjetivo + que.',
    document: '',
    notion: 'La campaña turística de Madrid',
    chapitre: 'Madrid, capital cultural e histórica',
    points_attendus: [
      'Au moins un argument du cours : los museos, la vida nocturna, la gastronomía, la historia',
      'Une exclamation correctement accentuée',
      'La structure tan + adjetivo + que employée à bon escient',
      'Les accords en genre et en nombre, point travaillé depuis le premier contrôle',
      'Une longueur de 8 à 10 lignes',
    ],
    ou_dans_le_cours: 'Séquence Madrid, la partie sur la campagne touristique.',
    duree_minutes: 16,
    poids: 2,
  },
];
