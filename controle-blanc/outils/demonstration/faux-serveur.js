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

/* Les comptes de la démonstration.
   Le vrai produit garde un cookie HttpOnly posé par le serveur, et les mots de
   passe hachés par scrypt en base. Ici il n'y a pas de serveur : les comptes
   vivent dans localStorage, en clair, le temps de la démonstration. Le nom de la
   clé le dit, pour qu'on ne s'y trompe pas en lisant ce fichier. */
const CLE_ENTREE_DEMO = 'cb.demo.entre';
const CLE_COMPTES_DEMO = 'cb.demo.comptes-en-clair';

const sessionDemo = { email: '', code: null, compte: null, oubli: '' };
try {
  const garde = JSON.parse(localStorage.getItem(CLE_ENTREE_DEMO) || 'null');
  if (garde && garde.compte) { sessionDemo.email = garde.email; sessionDemo.compte = garde.compte; }
} catch (e) { /* stockage refusé : on redemandera de se connecter */ }

function comptesDemo() {
  try { return JSON.parse(localStorage.getItem(CLE_COMPTES_DEMO) || '{}') || {}; }
  catch (e) { return {}; }
}

function garderComptesDemo(tous) {
  try { localStorage.setItem(CLE_COMPTES_DEMO, JSON.stringify(tous)); } catch (e) { /* idem */ }
}

function normaliserEmail(brut) {
  const email = (brut || '').trim().toLowerCase();
  return /^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$/.test(email) ? email : '';
}

/* Ouvre la session de démonstration et sème le classeur factice : sans lui la
   page perso s'ouvrirait vide et la démonstration ne démontrerait rien. */
function ouvrirDemo(email) {
  const ouvert = comptesDemo()[email];
  sessionDemo.email = email;
  sessionDemo.compte = ouvert.compte;
  garderEntreeDemo();
  // Le classeur factice : dix cours déjà faits, pour que la page perso montre
  // quelque chose. Sur le site public on veut l'inverse — un compte neuf, comme
  // pour un vrai élève qui arrive. D'où le drapeau posé par artefact.py --vierge.
  if (typeof DEMO_VIERGE === 'undefined' || !DEMO_VIERGE) {
    semerLePasse('cb.' + ouvert.compte + '.');
  }
  return { connecte: true, email, compte: ouvert.compte,
           prenom: ouvert.prenom || '', niveau: ouvert.niveau || '' };
}

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

  /* --- Le compte ----------------------------------------------------------
     La démonstration joue le vrai parcours : on s'inscrit, on se connecte, on
     peut même changer son mot de passe oublié. Le code de réinitialisation
     s'affiche à l'écran, puisqu'il n'y a pas de serveur de courrier — c'est
     exactement ce que fait le vrai serveur quand CB_AUTH_CODE_EN_CLAIR est actif.

     Ce qu'on ne rejoue pas : les blocages (cadence, essais ratés, expiration).
     Ce sont des refus, et une démonstration qui refuse n'apprend rien à qui
     l'essaie. Ils sont tenus par les tests du serveur.

     Ce qu'on ne fait surtout pas : hacher quoi que ce soit. Les comptes vivent
     dans localStorage, en clair, le temps de la démonstration — d'où le nom de
     la clé, qui le dit. */
  const refusAuth = (message, genre) => {
    const erreur = new ErreurApi(message, 'auth');
    erreur.genreAuth = genre || 'refus';
    erreur.attendre = 0;
    return erreur;
  };

  if (chemin === '/api/auth/moi') {
    const ouvert = comptesDemo()[sessionDemo.email];
    return sessionDemo.compte && ouvert
      ? { connecte: true, email: sessionDemo.email, compte: sessionDemo.compte,
          prenom: ouvert.prenom || '', niveau: ouvert.niveau || '' }
      : { connecte: false };
  }

  if (chemin === '/api/auth/inscription') {
    const email = normaliserEmail(corps && corps.email);
    if (!email) throw refusAuth('Cette adresse ne ressemble pas à une adresse mail.', 'email');
    if ((corps.mot_de_passe || '').length < 8) {
      throw refusAuth('Ton mot de passe doit faire au moins 8 caractères.', 'mdp');
    }
    const tous = comptesDemo();
    if (tous[email]) {
      throw refusAuth('Un compte existe déjà avec cette adresse. Connecte-toi, ou '
                      + 'utilise « mot de passe oublié ».', 'existe');
    }
    tous[email] = { compte: 'demo' + empreinteCourte(email), mdp: corps.mot_de_passe,
                    prenom: (corps.prenom || '').trim(), niveau: corps.niveau || '' };
    garderComptesDemo(tous);
    return ouvrirDemo(email);
  }

  if (chemin === '/api/auth/connexion') {
    const email = normaliserEmail(corps && corps.email);
    const ouvert = email && comptesDemo()[email];
    if (!ouvert || ouvert.mdp !== corps.mot_de_passe) {
      throw refusAuth('Adresse ou mot de passe incorrect.', 'refus');
    }
    return ouvrirDemo(email);
  }

  if (chemin === '/api/auth/oubli') {
    const email = normaliserEmail(corps && corps.email);
    if (!email) throw refusAuth('Cette adresse ne ressemble pas à une adresse mail.', 'email');
    const reponse = { envoye: true, expire_dans_minutes: 10, renvoi_dans_secondes: 15 };
    if (!comptesDemo()[email]) return reponse;   // comme le vrai : rien ne part
    sessionDemo.oubli = email;
    sessionDemo.code = String(Math.floor(Math.random() * 1000000)).padStart(6, '0');
    reponse.code_demonstration = sessionDemo.code;
    return reponse;
  }

  if (chemin === '/api/auth/reinitialiser') {
    const email = normaliserEmail(corps && corps.email);
    if (!corps || String(corps.code).replace(/\D/g, '') !== sessionDemo.code
        || email !== sessionDemo.oubli) {
      throw refusAuth('Ce code ne correspond pas.', 'faux');
    }
    if ((corps.mot_de_passe || '').length < 8) {
      throw refusAuth('Ton mot de passe doit faire au moins 8 caractères.', 'mdp');
    }
    const tous = comptesDemo();
    tous[email].mdp = corps.mot_de_passe;
    garderComptesDemo(tous);
    sessionDemo.code = null;
    sessionDemo.oubli = '';
    return ouvrirDemo(email);
  }

  if (chemin === '/api/auth/sortir') {
    sessionDemo.compte = null;
    sessionDemo.email = '';
    garderEntreeDemo();
    return { connecte: false };
  }

  if (chemin === '/api/auth/supprimer') {
    const tous = comptesDemo();
    delete tous[sessionDemo.email];
    garderComptesDemo(tous);
    sessionDemo.compte = null;
    sessionDemo.email = '';
    garderEntreeDemo();
    return { supprime: true };
  }

  if (chemin === '/api/session' && options.method === 'POST') {
    const identifiant = identifiantAleatoire();
    return { session_id: identifiant, lien_de_reprise: lienDeReprise(identifiant) };
  }

  if (chemin === '/api/session/contexte' || chemin === '/api/evenement') return { etat: 'ok' };

  // Le classeur : dans le produit il monte sur le serveur, ce qui fait qu'un
  // élève retrouve ses affaires sur un autre appareil. Une démonstration n'a
  // qu'un navigateur et pas de serveur : elle accepte les montées sans rien
  // ranger, et ne descend jamais rien. Sans ces réponses, la synchronisation
  // réessaierait en boucle.
  if (chemin === '/api/classeur') {
    return { seances: [], agenda: null, maintenant: new Date().toISOString() };
  }
  if (chemin === '/api/agenda') return { range: true };
  if (chemin.startsWith('/api/classeur/')) return { range: true };

  // Les plafonds du mois. Dans le produit ils sont comptés côté serveur, seul
  // endroit où le compte est infalsifiable ; ici on les tient en mémoire, pour
  // que le compteur sous chaque outil de la page perso montre autre chose qu'un
  // blanc — et qu'il baisse vraiment quand on génère.
  if (chemin === '/api/compte/quotas') {
    return { mois: new Date().toISOString().slice(0, 7), quotas: etatDesQuotas() };
  }

  // Le vrai serveur décompte à chaque appel facturé (store.enregistrer_usage).
  // La correction n'y est pas : elle fait partie du contrôle déjà compté.
  // Une analyse consomme autant de pages qu'elle porte de photos.
  if (ACTION_FACTUREE[chemin]) {
    const pages = chemin === '/api/analyse' && options.body
      ? options.body.getAll('photos').length : 1;
    decompter(ACTION_FACTUREE[chemin], Math.max(1, pages));
  }

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

function envoyerJson(chemin, corps, methode = 'POST') {
  return api(chemin, { method: methode, headers: {},
                       body: corps === null || corps === undefined
                         ? undefined : JSON.stringify(corps) });
}

function tracer() { /* les mesures partent au serveur dans le produit ; ici, nulle part. */ }

/* Les plafonds mensuels, en mémoire.
 *
 * Les mêmes chiffres que app/config.py — s'ils divergent, la démonstration
 * ment sur ce que l'abonnement donne. Ils repartent à chaque rechargement :
 * une démonstration n'a pas de mois. */
// L'analyse se compte en PAGES : mêmes chiffres que app/config.py.
const PLAFONDS_MOIS = { analyse: 144, fiche_generale: 12, controle: 12, fiche_ciblee: 12 };
const consommes = { analyse: 0, fiche_generale: 0, controle: 0, fiche_ciblee: 0 };

const ACTION_FACTUREE = {
  '/api/analyse': 'analyse',
  '/api/fiche/generale': 'fiche_generale',
  '/api/fiche/ciblee': 'fiche_ciblee',
  '/api/controle': 'controle',
};

function decompter(action, quantite = 1) {
  if (action in consommes) consommes[action] += quantite;
}

function etatDesQuotas() {
  const etat = {};
  Object.entries(PLAFONDS_MOIS).forEach(([action, plafond]) => {
    etat[action] = { plafond, restant: Math.max(0, plafond - consommes[action]) };
  });
  return etat;
}
