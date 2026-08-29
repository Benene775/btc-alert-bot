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
 * « Ma page » ne montre rien tant que l'élève n'a rien fait — c'est normal
 * dans le produit, mais une démonstration vide ne démontre rien. On sème donc
 * quelques séances déjà faites, dans le même stockage que le vrai produit :
 * la page les relit sans savoir qu'elles viennent d'ici.
 *
 * Uniquement en démonstration, et une seule fois par compte : si l'élève efface
 * tout, on ne lui réimpose pas un passé qui n'est pas le sien.
 *
 * Semé à l'entrée, pas au chargement : avant d'entrer, on ne sait pas encore
 * sous quel préfixe ranger.
 */
/* Le préfixe arrive de l'appelant : depuis les comptes, le classeur d'un
   élève est rangé sous « cb.<compte>. », et semer sous « cb. » remplirait un
   classeur que personne ne lit. */
const SUFFIXE_SEMEE = "demo.semee";

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

/* Une vraie année d'élève : dix cours, six matières, une trentaine de fiches et
 * autant de contrôles. Une démonstration à trois séances ne montre pas ce que
 * devient la page quand elle est pleine — or c'est justement là qu'elle doit
 * tenir. */
const ANNEE_FACTICE = [
  ["svt", "La respiration et la circulation", 2, [
    ["Le trajet du sang dans le cœur", "Tu inverses encore oreillettes et ventricules."],
    ["Échanges gazeux dans les alvéoles", "Le sens des échanges n'est pas encore automatique."]]],
  ["histoire-geographie", "La Révolution française", 9, [
    ["La chronologie 1789-1792", "Encore deux dates inversées, mais c'est plus net."]]],
  ["espagnol", "Turismo: luces y sombras", 16, [
    ["El futuro hipotético", "Le subjonctif après « quizás » n'est pas encore réflexe."],
    ["La frase exclamativa y sus acentos", "Les accents tombent au mauvais endroit."]]],
  ["mathematiques", "Théorème de Pythagore", -6, [
    ["Reconnaître l'hypoténuse", "Tu l'identifies bien, sauf quand la figure est tournée."]]],
  ["francais", "Le récit fantastique", -12, [
    ["Le registre fantastique", "Tu confonds encore fantastique et merveilleux."],
    ["Les indices d'énonciation", "Repérés, mais pas encore interprétés."]]],
  ["physique-chimie", "Les états de la matière", -19, [
    ["Les changements d'état", "Fusion et solidification sont inversées une fois sur deux."]]],
  ["histoire-geographie", "L'Europe des Lumières", -26, [
    ["Les philosophes et leurs idées", "Les noms sont là, les idées se mélangent."]]],
  ["svt", "Nutrition et digestion", -33, [
    ["Le rôle des enzymes", "L'explication reste au niveau du vocabulaire."]]],
  ["mathematiques", "Fractions et proportionnalité", -40, [
    ["Passer d'une écriture à l'autre", "Le passage décimal/fraction coûte encore du temps."]]],
  ["espagnol", "Madrid, capital cultural", -47, [
    ["Los museos madrileños", "Les œuvres sont sues, les auteurs moins."]]],
];

function semerLePasse(prefixe) {
  try {
    if (localStorage.getItem(prefixe + SUFFIXE_SEMEE)) return;
    ANNEE_FACTICE.forEach(([matiere, chapitre, dansJours, fragiles], rang) => {
      const decalage = Math.min(dansJours, 0) - 2;
      const fiches = [ficheFactice("Fiche de révision — " + chapitre, decalage - 1)];
      // Un cours sur deux a donné lieu à une fiche ciblée, comme dans la vraie vie.
      if (rang % 2 === 0) fiches.push(ficheFactice("Ce qui ne tenait pas encore", decalage, "ciblee"));
      const controles = [controleFactice("Contrôle blanc — " + chapitre, decalage - 1,
        5 + (rang % 4), fragiles.map(([n, q]) => fragile(n, q)))];
      // Les chapitres les plus anciens ont été repassés une seconde fois.
      if (rang > 4) controles.push(controleFactice("Contrôle blanc — " + chapitre, decalage + 1,
        5 + (rang % 3), fragiles.slice(0, 1).map(([n, q]) => fragile(n, q))));
      const seance = seanceFactice({
        id: "demo-" + rang + "-" + matiere,
        matiere,
        niveau: "4e",
        dansJours,
        chapitres: [{ titre: chapitre, notions: [], transcription: "", photos: [] }],
        fiches,
        controles,
      });
      localStorage.setItem(prefixe + "session." + seance.sessionId, JSON.stringify(seance));
    });
    localStorage.setItem(prefixe + SUFFIXE_SEMEE, "1");
  } catch (e) { /* stockage refusé : la démonstration s'ouvrira vide */ }
}
