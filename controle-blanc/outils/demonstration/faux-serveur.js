/* Le seul écart avec l’application réelle : le transport.
   Les signatures api() et envoyerJson() sont identiques, si bien que toute la
   suite du fichier — écrans, état, minuteur, localStorage — est celle du produit,
   inchangée. Ici, les réponses sont fabriquées sur place au lieu d’être demandées
   au serveur, et rien n’est envoyé nulle part. */

const DELAIS = {
  '/api/analyse': 1600,
  '/api/controle': 1400,
  '/api/correction': 1600,
  '/api/fiche/generale': 1200,
  '/api/fiche/ciblee': 1100,
};

const corrigesEnMemoire = {};

function pause(ms) { return new Promise((resoudre) => setTimeout(resoudre, ms)); }

function identifiantAleatoire() {
  return Math.random().toString(36).slice(2, 10) + Math.random().toString(36).slice(2, 6);
}

function lienDeReprise(identifiant) {
  return location.origin + location.pathname + '?s=' + identifiant;
}

class ErreurApi extends Error {
  constructor(message, genre) { super(message); this.genre = genre; }
}

async function api(chemin, options = {}) {
  await pause(DELAIS[chemin] || 260);
  const corps = typeof options.body === 'string' ? JSON.parse(options.body) : null;

  if (chemin === '/api/config') {
    return { matieres: MATIERES, niveaux: NIVEAUX, mode_demonstration: true, max_photos: 12 };
  }

  if (chemin === '/api/session' && options.method === 'POST') {
    const identifiant = identifiantAleatoire();
    return { session_id: identifiant, lien_de_reprise: lienDeReprise(identifiant) };
  }

  if (chemin === '/api/session/contexte' || chemin === '/api/evenement') return { etat: 'ok' };

  if (chemin.startsWith('/api/session/')) {
    // Pas de session partagée entre appareils dans la démonstration.
    throw new ErreurApi("Cette session n’existe plus. On en recommence une.", 'session');
  }

  if (chemin === '/api/analyse') {
    const nombre = options.body ? options.body.getAll('photos').length : 3;
    const photos = [];
    for (let i = 0; i < Math.max(1, nombre); i++) photos.push({ index: i, lisible: true, remarque: '' });
    if (photos.length >= 3) {
      photos[photos.length - 1] = {
        index: photos.length - 1,
        lisible: false,
        remarque: 'Le bas de cette page est coupé, reprends-la en cadrant plus large.',
      };
    }
    return { photos, matiere_detectee: 'Histoire-Géographie / EMC', chapitres: [CHAPITRE] };
  }

  if (chemin === '/api/fiche/generale') return { ...FICHE_GENERALE, type: 'generale' };

  if (chemin === '/api/fiche/ciblee') {
    const cibles = (corps && corps.notions && corps.notions.length)
      ? corps.notions
      : [{ notion: 'La notion de guerre totale', chapitre: CHAPITRE.titre, pourquoi: '' }];
    return {
      type: 'ciblee',
      titre: 'Fiche ciblée — ce qui a coincé',
      duree_lecture_minutes: 5,
      sections: cibles.slice(0, 3).map((n) => ({
        titre: n.notion,
        points: [
          'Reprends la définition exacte du cours, mot pour mot.',
          "Trouve dans ton cours un exemple précis qui l’illustre.",
          'Explique-la à voix haute en une phrase, sans regarder.',
        ],
        a_retenir: n.pourquoi || 'Relis ce passage de ton cours avant de te retester.',
      })),
      definitions: [
        { terme: 'Guerre totale', definition: "Mobilisation de toutes les ressources d’un pays pour la guerre." },
      ],
      pieges: ['Citer une date sans dire ce qui s’y passe ne rapporte rien.'],
    };
  }

  if (chemin === '/api/controle') {
    const cible = corps && corps.notions_ciblees && corps.notions_ciblees.length;
    const dejaPose = corps && corps.enonces_deja_poses && corps.enonces_deja_poses.length;
    const questions = (cible || dejaPose) ? QUESTIONS_BIS : QUESTIONS;
    const identifiant = identifiantAleatoire();
    corrigesEnMemoire[identifiant] = questions;
    return {
      controle_id: identifiant,
      titre: (cible || dejaPose ? 'Contrôle blanc n°2 — ' : 'Contrôle blanc — ') + CHAPITRE.titre,
      consigne_generale: "Réponds dans l’ordre, en rédigeant. Tu ne peux pas revenir en arrière, comme le jour du contrôle.",
      matiere: 'Histoire-Géographie / EMC',
      duree_minutes: questions.reduce((total, q) => total + q.duree_minutes, 0),
      // Comme sur le serveur, les réponses attendues ne partent pas avec les énoncés.
      questions: questions.map(({ points_attendus, ou_dans_le_cours, ...reste }) => reste),
    };
  }

  if (chemin === '/api/correction') {
    const questions = corrigesEnMemoire[corps.controle_id] || QUESTIONS;
    const parNumero = {};
    (corps.reponses || []).forEach((r) => { parNumero[r.numero] = r.texte || ''; });
    const signales = new Set(corps.numeros_signales || []);

    const lignes = [];
    const fragiles = [];
    questions.forEach((question) => {
      const texte = (parNumero[question.numero] || '').trim();
      const signalee = signales.has(question.numero);
      let statut;
      if (signalee || texte.length > 180) statut = 'acquis';
      else if (texte.length > 40) statut = 'partiel';
      else statut = 'a_revoir';

      lignes.push({
        numero: question.numero,
        statut,
        ce_qui_va: signalee
          ? "Tu as signalé cette question, on ne la retient pas contre toi."
          : (texte ? 'Tu as bien identifié le sujet de la question.' : ''),
        ce_qui_manquait: statut === 'acquis' ? [] : question.points_attendus.slice(1),
        ou_dans_ton_cours: question.ou_dans_le_cours,
        reponse_attendue: question.points_attendus.join(' '),
        enonce: question.enonce,
        notion: question.notion,
        document: question.document,
        ta_reponse: parNumero[question.numero] || '',
        signalee,
      });

      if (statut === 'a_revoir' && fragiles.length < 3) {
        fragiles.push({
          notion: question.notion,
          chapitre: question.chapitre,
          pourquoi: 'Ta réponse ne reprend pas les éléments attendus du cours.',
        });
      }
    });

    return {
      reponses: lignes,
      notions_fragiles: fragiles,
      mot_de_fin: "Relis la fiche ciblée, puis retente un contrôle sur ces notions-là. C’est en les reposant qu’elles rentrent.",
    };
  }

  if (chemin === '/api/signalement') {
    return { etat: 'ok', message: "C’est noté, merci. Cette question ne comptera pas contre toi." };
  }

  throw new ErreurApi("Ça n’a pas marché. Réessaie.", 'autre');
}

function envoyerJson(chemin, corps) {
  return api(chemin, { method: 'POST', headers: {}, body: JSON.stringify(corps) });
}

function tracer() { /* les mesures partent au serveur dans le produit ; ici, nulle part. */ }
