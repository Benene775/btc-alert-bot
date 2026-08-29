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

/* Le « compte » de la démonstration.
   Le vrai produit garde un cookie HttpOnly, que le serveur pose et relit. Ici il
   n'y a pas de serveur : on garde donc l'équivalent dans le navigateur, sinon un
   simple rafraîchissement remettrait dehors — ce que le produit ne fait pas. */
const CLE_ENTREE_DEMO = 'cb.demo.entre';

const sessionDemo = { email: '', code: null, compte: null };
try {
  const garde = JSON.parse(localStorage.getItem(CLE_ENTREE_DEMO) || 'null');
  if (garde && garde.compte) { sessionDemo.email = garde.email; sessionDemo.compte = garde.compte; }
} catch (e) { /* stockage refusé : on redemandera d'entrer */ }

function garderEntreeDemo() {
  try {
    if (sessionDemo.compte) {
      localStorage.setItem(CLE_ENTREE_DEMO,
        JSON.stringify({ email: sessionDemo.email, compte: sessionDemo.compte }));
    } else {
      localStorage.removeItem(CLE_ENTREE_DEMO);
    }
  } catch (e) { /* idem */ }
}

/* Un identifiant stable pour une adresse : la même adresse doit rouvrir le même
   classeur, sinon rentrer deux fois donne deux classeurs vides. */
function empreinteCourte(texte) {
  let n = 0;
  for (let i = 0; i < texte.length; i++) n = (n * 31 + texte.charCodeAt(i)) >>> 0;
  return n.toString(36);
}

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
    return { matieres: MATIERES, niveaux: NIVEAUX, mode_demonstration: true,
             max_photos: 12, matiere_par_defaut: MATIERE_PAR_DEFAUT };
  }

  /* --- L'entrée -----------------------------------------------------------
     La démonstration joue le vrai parcours : on donne une adresse, on reçoit un
     code, on entre avec. Le code s'affiche à l'écran, puisqu'il n'y a pas de
     serveur de courrier — c'est exactement ce que fait le vrai serveur quand
     CB_AUTH_CODE_EN_CLAIR est actif.

     Ce qu'on ne rejoue pas : la cadence d'envoi, les cinq essais, l'expiration.
     Ce sont des refus, et une démonstration qui refuse n'apprend rien à qui
     l'essaie. Ils sont tenus par les tests du serveur. */
  if (chemin === '/api/auth/moi') {
    return sessionDemo.compte
      ? { connecte: true, email: sessionDemo.email, compte: sessionDemo.compte }
      : { connecte: false };
  }

  if (chemin === '/api/auth/code') {
    const email = (corps && corps.email || '').trim().toLowerCase();
    if (!/^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$/.test(email)) {
      const refus = new ErreurApi('Cette adresse ne ressemble pas à une adresse mail.', 'auth');
      refus.attendre = 0;
      throw refus;
    }
    sessionDemo.email = email;
    sessionDemo.code = String(Math.floor(Math.random() * 1000000)).padStart(6, '0');
    return { envoye: true, expire_dans_minutes: 10, renvoi_dans_secondes: 15,
             code_demonstration: sessionDemo.code };
  }

  if (chemin === '/api/auth/entrer') {
    if (!corps || String(corps.code).replace(/\D/g, '') !== sessionDemo.code) {
      const refus = new ErreurApi('Ce code ne correspond pas.', 'auth');
      refus.attendre = 0;
      throw refus;
    }
    // Le même compte pour la même adresse : l'élève qui ressort et rerentre
    // doit retrouver son classeur, comme sur le vrai serveur.
    sessionDemo.compte = 'demo' + empreinteCourte(sessionDemo.email);
    sessionDemo.code = null;
    // Le classeur factice est semé sous le préfixe du compte, sans quoi la page
    // perso s'ouvrirait vide et la démonstration ne démontrerait rien.
    semerLePasse('cb.' + sessionDemo.compte + '.');
    garderEntreeDemo();
    return { connecte: true, email: sessionDemo.email, compte: sessionDemo.compte };
  }

  if (chemin === '/api/auth/sortir') {
    sessionDemo.compte = null;
    garderEntreeDemo();
    return { connecte: false };
  }

  if (chemin === '/api/auth/supprimer') {
    sessionDemo.compte = null;
    garderEntreeDemo();
    return { supprime: true };
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
    return { photos, matiere_detectee: MATIERE_DETECTEE, chapitres: CHAPITRES };
  }

  if (chemin === '/api/fiche/generale') return { ...FICHE_GENERALE, type: 'generale' };

  if (chemin === '/api/fiche/ciblee') {
    const cibles = (corps && corps.notions && corps.notions.length)
      ? corps.notions
      : [{ notion: CIBLEE_PAR_DEFAUT, chapitre: CHAPITRES[0].titre, pourquoi: '' }];
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
      definitions: CIBLEE_DEFINITIONS,
      pieges: CIBLEE_PIEGES,
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
      titre: (cible || dejaPose ? 'Contrôle blanc n°2 — ' : 'Contrôle blanc — ') + CHAPITRES[0].titre,
      consigne_generale: "Réponds dans l’ordre, en rédigeant. Tu ne peux pas revenir en arrière, comme le jour du contrôle.",
      matiere: MATIERE_DETECTEE,
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
        erreur_reperee: statut === 'partiel' ? 'Tu t’es arrêté au premier élément attendu.' : '',
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
      mot_de_fin: MOT_DE_FIN,
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
