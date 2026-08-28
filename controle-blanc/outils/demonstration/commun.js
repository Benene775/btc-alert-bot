/* Ce que toute démonstration partage, quelle que soit la matière. */

const MATIERES = [
  { cle: "francais", nom: "Français" },
  { cle: "mathematiques", nom: "Mathématiques" },
  { cle: "histoire-geographie", nom: "Histoire-Géographie / EMC" },
  { cle: "svt", nom: "SVT" },
  { cle: "physique-chimie", nom: "Physique-Chimie" },
  { cle: "technologie", nom: "Technologie" },
  { cle: "anglais", nom: "Anglais" },
  { cle: "espagnol", nom: "Espagnol" },
  { cle: "allemand", nom: "Allemand" },
  { cle: "ses", nom: "SES" },
  { cle: "philosophie", nom: "Philosophie" },
  { cle: "autre", nom: "Autre matière" },
];

const NIVEAUX = [
  { cle: "6e", nom: "6e" }, { cle: "5e", nom: "5e" }, { cle: "4e", nom: "4e" },
  { cle: "3e", nom: "3e" }, { cle: "2de", nom: "Seconde" }, { cle: "1re", nom: "Première" },
  { cle: "terminale", nom: "Terminale" },
];

/* --- Un passé pour la démonstration -------------------------------------
 *
 * « Mon année » ne montre rien tant que l'élève n'a rien fait — c'est normal
 * dans le produit, mais une démonstration vide ne démontre rien. On sème donc
 * quelques séances déjà faites, dans le même stockage que le vrai produit :
 * la page les relit sans savoir qu'elles viennent d'ici.
 *
 * Uniquement en démonstration, et une seule fois : si l'élève efface tout, on
 * ne lui réimpose pas un passé qui n'est pas le sien.
 */
const CLE_SEMEE = "cb.demo.semee";

function jourDecale(jours) {
  return new Date(Date.now() + jours * 86400000).toISOString();
}

function jourCourt(jours) {
  return jourDecale(jours).slice(0, 10);
}

function seanceFactice({ id, matiere, niveau, dansJours, titreFiche, chapitres, fiches, controles }) {
  return {
    v: 1,
    sessionId: id,
    lien: location.origin + "/?s=" + id,
    creeLe: jourDecale(-Math.abs(dansJours) - 9),
    niveau,
    matiere,
    dateControle: jourCourt(dansJours),
    chapitres,
    remarquesPhotos: [],
    chemin: "revision",
    ordreCarrefour: [],
    fiches,
    controles,
    notionsFragiles: controles.length
      ? controles[controles.length - 1].correction.notions_fragiles
      : [],
    marques: {},
    etape: "correction",
  };
}

function fragile(notion, pourquoi) {
  return { notion, pourquoi };
}

function ficheFactice(titre, jours, type = "generale") {
  return {
    type,
    le: jourDecale(jours),
    contenu: {
      titre,
      duree_lecture_minutes: 8,
      sections: [{ titre: "Ce qu'il fallait retenir", points: ["Point du cours."],
                   a_retenir: "L'essentiel du chapitre.", pages: [] }],
      definitions: [],
      pieges: [],
    },
  };
}

function controleFactice(titre, jours, nbQuestions, fragiles) {
  return {
    controle_id: "demo-" + Math.random().toString(36).slice(2, 8),
    titre,
    le: jourDecale(jours),
    questions: Array.from({ length: nbQuestions }, (_, i) => ({
      numero: i + 1, enonce: "Question " + (i + 1), notion: "Notion " + (i + 1),
    })),
    reponses: [],
    // Une correction sans réponses corrigées rouvre une page vide : la
    // démonstration doit montrer ce que l'élève retrouvera vraiment.
    correction: {
      mot_de_fin: "Deux notions à reprendre, le reste tient.",
      reponses: fragiles.map((f, i) => ({
        numero: i + 1,
        enonce: "Question " + (i + 1) + " — " + f.notion,
        statut: i === 0 ? "a_revoir" : "partiel",
        ta_reponse: "Ce que tu avais écrit le jour du contrôle.",
        ce_qui_va: "Tu as bien identifié le sujet de la question.",
        erreur_reperee: f.pourquoi,
        ce_qui_manquait: ["L'élément que ton cours donne juste après."],
        ou_dans_ton_cours: "Dans ton chapitre, au paragraphe correspondant.",
        reponse_attendue: "La réponse complète, telle qu'elle était attendue.",
        signalee: false,
      })),
      notions_fragiles: fragiles,
    },
  };
}

function semerLePasse() {
  try {
    if (localStorage.getItem(CLE_SEMEE)) return;
    const seances = [
      seanceFactice({
        id: "demo-svt", matiere: "svt", niveau: "4e", dansJours: 2,
        chapitres: [{ titre: "La respiration et la circulation", notions: [], transcription: "", photos: [] }],
        fiches: [ficheFactice("Fiche de révision — Respiration et circulation", -3)],
        controles: [controleFactice("Contrôle blanc — Respiration et circulation", -3, 7, [
          fragile("Le trajet du sang dans le cœur", "Tu inverses encore oreillettes et ventricules."),
          fragile("Échanges gazeux dans les alvéoles", "Le sens des échanges n'est pas encore automatique."),
        ])],
      }),
      seanceFactice({
        id: "demo-histoire", matiere: "histoire-geographie", niveau: "4e", dansJours: 9,
        chapitres: [{ titre: "La Révolution française", notions: [], transcription: "", photos: [] }],
        fiches: [ficheFactice("Fiche de révision — La Révolution française", -12),
                 ficheFactice("Ce qui ne tenait pas encore", -10, "ciblee")],
        controles: [
          controleFactice("Contrôle blanc — La Révolution française", -12, 8, [
            fragile("La chronologie 1789-1792", "Les dates s'emmêlent dès qu'il y en a plus de trois."),
          ]),
          controleFactice("Contrôle blanc — La Révolution française", -10, 6, [
            fragile("La chronologie 1789-1792", "Encore deux dates inversées, mais c'est plus net."),
          ]),
        ],
      }),
      seanceFactice({
        id: "demo-maths", matiere: "mathematiques", niveau: "4e", dansJours: -6,
        chapitres: [{ titre: "Théorème de Pythagore", notions: [], transcription: "", photos: [] }],
        fiches: [ficheFactice("Fiche de révision — Théorème de Pythagore", -21)],
        controles: [controleFactice("Contrôle blanc — Théorème de Pythagore", -21, 6, [
          fragile("Reconnaître l'hypoténuse", "Tu l'identifies bien, sauf quand la figure est tournée."),
        ])],
      }),
    ];
    seances.forEach((s) => localStorage.setItem("cb.session." + s.sessionId, JSON.stringify(s)));
    localStorage.setItem(CLE_SEMEE, "1");
  } catch (e) { /* stockage refusé : la démonstration s'ouvrira vide */ }
}

semerLePasse();
