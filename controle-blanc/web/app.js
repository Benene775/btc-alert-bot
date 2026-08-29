/* Repère — application d’une seule page.
 *
 * L’état vit dans le navigateur (localStorage), pas sur le serveur. Le serveur ne
 * connaît de l’élève que son adresse mail : ni son cours, ni ses réponses, ni ses
 * fiches. Pas de mot de passe non plus — on entre avec un code reçu par mail.
 *
 * Ce qui n’est PAS conservé : les photos. Elles servent à l’analyse puis disparaissent.
 * Ce qu’on garde, c’est la transcription du cours, qui tient dans quelques kilo-octets.
 */

'use strict';

/* Les clés du navigateur portent l’identifiant du compte.
 *
 * Sans ça, deux élèves qui se prêtent une tablette voient le classeur l’un de
 * l’autre : leur travail est dans CE navigateur, pas sur le serveur, et rien ne
 * l’y sépare. Le préfixe est posé une fois, après l’entrée et avant la première
 * lecture — d’où des « let » et non des « const ».
 *
 * L’identifiant vient du serveur et ne dit rien de personne : l’adresse mail,
 * elle, n’est jamais écrite dans le navigateur.
 */
let compte = null;             // { id, email } une fois entré
let PREFIXE = 'cb.';
let CLE_ETAT = PREFIXE + 'session.';
let CLE_DERNIERE = PREFIXE + 'derniere';
let CLE_CARTE = PREFIXE + 'carte';
let CLE_AGENDA = PREFIXE + 'agenda';
let BASE_PAGES = 'cb-pages';

function attacherAuCompte(identifiant) {
  PREFIXE = identifiant ? 'cb.' + identifiant + '.' : 'cb.';
  CLE_ETAT = PREFIXE + 'session.';
  CLE_DERNIERE = PREFIXE + 'derniere';
  CLE_CARTE = PREFIXE + 'carte';
  CLE_AGENDA = PREFIXE + 'agenda';
  BASE_PAGES = identifiant ? 'cb-pages-' + identifiant : 'cb-pages';
}

const VERSION_ETAT = 1;
const COTE_MAX_PHOTO = 1568;   // au-delà, le modèle redimensionne de toute façon
const QUALITE_PHOTO = 0.82;

let etat = null;
let photosEnAttente = [];      // le lot en cours de sélection
let photosDuCours = [];        // les pages déjà analysées, gardées pour la fiche
let config = { matieres: [], niveaux: [], mode_demonstration: false, max_photos: 12 };
let controleEnCours = null;
let minuteur = null;

const $ = (id) => document.getElementById(id);
const ecrans = () => document.querySelectorAll('.ecran');

/* ---------------------------------------------------------------- état --- */

function etatNeuf(sessionId, lien) {
  return {
    v: VERSION_ETAT,
    sessionId,
    lien,
    creeLe: new Date().toISOString(),
    niveau: '3e',
    matiere: '',
    dateControle: '',
    chapitres: [],
    remarquesPhotos: [],
    chemin: '',
    ordreCarrefour: [],
    fiches: [],
    controles: [],
    notionsFragiles: [],
    etape: 'contexte',
  };
}

function sauver() {
  if (!etat) return;
  try {
    localStorage.setItem(CLE_ETAT + etat.sessionId, JSON.stringify(etat));
    localStorage.setItem(CLE_DERNIERE, etat.sessionId);
  } catch (e) {
    // Quota du navigateur plein : on prévient sans casser la séance en cours.
    message("Ton téléphone n’a plus de place pour sauvegarder. Garde bien ton lien.", 'alerte');
  }
}

function charger(sessionId) {
  try {
    const brut = localStorage.getItem(CLE_ETAT + sessionId);
    if (!brut) return null;
    const donnees = JSON.parse(brut);
    return donnees && donnees.v === VERSION_ETAT ? donnees : null;
  } catch (e) {
    return null;
  }
}

/* ------------------------------------------------------------- ma page --- */

/*
 * « Ma page » rassemble tout ce que l'élève a fait : son agenda, ses fiches,
 * ses contrôles blancs, et surtout ce qui ne tient pas encore.
 *
 * Ce n'est pas un profil de réseau social : pas de compte, pas de public, rien
 * à montrer à personne. Tout est relu depuis ce téléphone, et rien n'en sort.
 *
 * L'inventaire se reconstruit en parcourant les sessions déjà écrites, sans
 * index séparé : un index se désynchronise, et une séance supprimée y laisserait
 * une ligne fantôme. La source de vérité reste les sessions elles-mêmes.
 */
function toutesLesSessions() {
  const sessions = [];
  let cles;
  try { cles = Object.keys(localStorage); } catch (e) { return sessions; }
  cles.forEach((cle) => {
    if (cle.indexOf(CLE_ETAT) !== 0) return;
    const session = charger(cle.slice(CLE_ETAT.length));
    if (session) sessions.push(session);
  });
  // La plus récemment commencée d'abord.
  return sessions.sort((a, b) => String(b.creeLe).localeCompare(String(a.creeLe)));
}

/* Ce que l'élève a réellement fait.
 *
 * S'inscrire ouvre une séance avant même qu'on ait demandé la matière. Sa page
 * affichait donc, dès la première seconde, une tuile « Matière à préciser » avec
 * zéro fiche, et « 1 cours » à côté de « 0 matière » — deux chiffres qui se
 * contredisent sous les yeux de quelqu'un qui n'a encore rien fait.
 *
 * menageSessions() balaie ces départs, mais seulement au chargement suivant :
 * la page ne peut pas attendre jusque-là pour dire la vérité. Elle lit donc les
 * séances qui portent quelque chose — un chapitre, une fiche ou un contrôle.
 */
function sessionsFaites() {
  return toutesLesSessions().filter((session) => poids(session) > 0);
}

/* --- L'étagère des matières ----------------------------------------------
 *
 * Tout ce que l'élève possède appartient à une matière : ses cours, ses fiches,
 * ses contrôles, ses notions fragiles. La matière n'était pourtant qu'une puce
 * de filtre — jamais la structure.
 *
 * Elle le devient. On voit son année d'un coup, une tuile par matière, et on
 * ouvre celle qui concerne le contrôle de demain. Rien n'est caché derrière un
 * onglet qu'il faut deviner.
 */
function matieres(sessions) {
  const par = new Map();
  const notions = notionsQuiReviennent(sessions);

  sessions.forEach((session) => {
    const cle = session.matiere || '';
    if (!par.has(cle)) {
      par.set(cle, { cle, sessions: [], fiches: 0, controles: 0, aRevoir: 0,
                     insistantes: 0, prochaine: null, dernier: '' });
    }
    const m = par.get(cle);
    m.sessions.push(session);
    m.fiches += (session.fiches || []).length;
    m.controles += (session.controles || []).length;
    if (String(session.creeLe) > String(m.dernier)) m.dernier = session.creeLe;
  });

  notions.forEach((n) => {
    const m = par.get(n.matiere || '');
    if (!m) return;
    m.aRevoir += 1;
    if (n.fois > 1) m.insistantes += 1;
  });

  // La prochaine échéance de chaque matière, dates saisies comprises.
  prochainesEcheances(sessions).forEach((e) => {
    const m = par.get(e.matiere || '');
    if (m && !m.prochaine) m.prochaine = e;
  });
  rendezVous().forEach((r) => {
    const m = par.get(r.matiere || '');
    if (m && !m.prochaine && joursAvant(r.date) >= 0) m.prochaine = { date: r.date, matiere: r.matiere };
  });

  // Ce qui presse d'abord, puis ce qui pèse : une matière sans échéance ni
  // notion fragile n'a pas de raison de passer devant.
  return [...par.values()].sort((a, b) => {
    const ja = a.prochaine ? joursAvant(a.prochaine.date) : 9999;
    const jb = b.prochaine ? joursAvant(b.prochaine.date) : 9999;
    if (ja !== jb) return ja - jb;
    if (b.insistantes !== a.insistantes) return b.insistantes - a.insistantes;
    return String(b.dernier).localeCompare(String(a.dernier));
  });
}

/* --- Le ménage ------------------------------------------------------------
 *
 * Repartir de l'accueil crée une séance neuve. Photographier deux fois le même
 * cours donnait donc deux séances jumelles, et l'archive affichait la même
 * fiche autant de fois qu'on avait recommencé.
 *
 * Deux séances qui portent la même matière et les mêmes chapitres sont le même
 * cours : on les réunit. La survivante est la plus fournie — c'est elle qui
 * porte le plus de travail, et son lien de reprise est celui qui a servi.
 *
 * Les séances vraiment vides (aucun chapitre, aucune fiche, aucun contrôle)
 * sont des départs abandonnés : elles disparaissent.
 */
function signatureCours(session) {
  const chapitres = (session.chapitres || [])
    .map((c) => String(c.titre || '').trim().toLowerCase())
    .sort()
    .join(' | ');
  return (session.matiere || '') + ' :: ' + chapitres;
}

function poids(session) {
  return (session.fiches || []).length + (session.controles || []).length
    + (session.chapitres || []).length;
}

function fusionner(garde, autre) {
  const fiches = garde.fiches || [];
  (autre.fiches || []).forEach((fiche) => {
    const titre = (fiche.contenu && fiche.contenu.titre) || '';
    const jumelle = fiches.find(
      (f) => f.type === fiche.type && ((f.contenu && f.contenu.titre) || '') === titre);
    // La plus récente gagne : c'est celle qui reflète le cours tel qu'il est.
    if (!jumelle) fiches.push(fiche);
    else if (String(fiche.le) > String(jumelle.le)) Object.assign(jumelle, fiche);
  });
  garde.fiches = fiches;

  // Les contrôles, eux, s'additionnent : chacun est un essai distinct.
  const dejaVus = new Set((garde.controles || []).map((c) => c.controle_id));
  (autre.controles || []).forEach((c) => {
    if (!dejaVus.has(c.controle_id)) (garde.controles = garde.controles || []).push(c);
  });
  garde.controles.sort((a, b) => String(a.le).localeCompare(String(b.le)));

  // La date de contrôle la plus proche à venir prime : c'est celle qui compte.
  if (autre.dateControle && (!garde.dateControle || autre.dateControle > garde.dateControle)) {
    garde.dateControle = autre.dateControle;
  }
  garde.marques = { ...(autre.marques || {}), ...(garde.marques || {}) };
  if (!(garde.notionsFragiles || []).length) garde.notionsFragiles = autre.notionsFragiles || [];
  return garde;
}

function oublierSession(sessionId) {
  try {
    localStorage.removeItem(CLE_ETAT + sessionId);
    if (localStorage.getItem(CLE_DERNIERE) === sessionId) localStorage.removeItem(CLE_DERNIERE);
  } catch (e) { /* stockage refusé */ }
  // Les pages du cahier de la séance disparue n'ont plus rien à illustrer.
  oublierPages(sessionId);
}

function menageSessions() {
  const sessions = toutesLesSessions();
  const parCours = new Map();
  let change = false;

  sessions.forEach((session) => {
    if (!poids(session)) {
      // Un départ abandonné : rien à garder.
      oublierSession(session.sessionId);
      change = true;
      return;
    }
    const cle = signatureCours(session);
    const deja = parCours.get(cle);
    if (!deja) return parCours.set(cle, session);

    const [garde, jete] = poids(deja) >= poids(session) ? [deja, session] : [session, deja];
    parCours.set(cle, fusionner(garde, jete));
    oublierSession(jete.sessionId);
    change = true;
  });

  if (!change) return false;
  parCours.forEach((session) => {
    try { localStorage.setItem(CLE_ETAT + session.sessionId, JSON.stringify(session)); }
    catch (e) { /* stockage plein */ }
  });
  // La séance courante a pu être absorbée : on repart de celle qui reste.
  if (etat && !localStorage.getItem(CLE_ETAT + etat.sessionId)) {
    const survivante = [...parCours.values()].find((s) => signatureCours(s) === signatureCours(etat));
    etat = survivante || null;
  }
  return true;
}

function nomMatiere(cle) {
  const trouvee = (config.matieres || []).find((m) => m.cle === cle);
  return trouvee ? trouvee.nom : (cle || 'Matière à préciser');
}

function joursAvant(dateISO) {
  if (!dateISO) return null;
  const jour = 24 * 60 * 60 * 1000;
  const cible = new Date(dateISO + 'T00:00:00');
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((cible - today) / jour);
}

/* L'agenda : les contrôles à venir, le plus proche d'abord. Ceux qui sont
 * passés descendent dans les séances terminées, ils n'ont plus rien à dire. */
function agenda(sessions) {
  return sessions
    .filter((s) => s.dateControle && joursAvant(s.dateControle) >= 0)
    .sort((a, b) => a.dateControle.localeCompare(b.dateControle));
}

/* Ce qui ne tient pas encore.
 *
 * Une notion signalée fragile une fois, c'est un accident. Deux fois, dans deux
 * contrôles, c'est le vrai signal — et c'est la seule chose que ce produit peut
 * dire qu'un cahier ne dit pas. On compte donc les répétitions, sans jamais en
 * faire une note.
 */
function notionsQuiReviennent(sessions) {
  const par = new Map();
  sessions.forEach((session) => {
    (session.controles || []).forEach((controle) => {
      const fragiles = (controle.correction && controle.correction.notions_fragiles) || [];
      fragiles.forEach((n) => {
        const cle = (session.matiere || '') + ' — ' + n.notion;
        const deja = par.get(cle);
        if (deja) {
          deja.fois += 1;
          if (String(controle.le) > String(deja.le)) { deja.le = controle.le; deja.pourquoi = n.pourquoi; }
        } else {
          par.set(cle, { notion: n.notion, pourquoi: n.pourquoi || '', matiere: session.matiere,
                         sessionId: session.sessionId, fois: 1, le: controle.le });
        }
      });
    });
  });
  return Array.from(par.values())
    .sort((a, b) => (b.fois - a.fois) || String(b.le).localeCompare(String(a.le)));
}

function toutesLesFiches(sessions) {
  const fiches = [];
  sessions.forEach((session) => {
    const chapitre = ((session.chapitres || [])[0] || {}).titre || '';
    (session.fiches || []).forEach((fiche, rang) => {
      // Une fiche ciblée s'appelle « Ce qui ne tenait pas encore » — juste dans
      // la fiche, illisible dans une liste où trois se suivent. Dans l'archive
      // elle prend le nom de son chapitre, qui est ce qu'on y cherche.
      const titre = fiche.type === 'ciblee'
        ? (chapitre || (fiche.contenu && fiche.contenu.titre) || 'Fiche ciblée')
        : ((fiche.contenu && fiche.contenu.titre) || chapitre || 'Fiche');
      fiches.push({ session, rang, type: fiche.type, le: fiche.le, titre });
    });
  });
  return fiches.sort((a, b) => String(b.le).localeCompare(String(a.le)));
}

function tousLesControles(sessions) {
  const controles = [];
  sessions.forEach((session) => {
    (session.controles || []).forEach((controle, rang) => {
      controles.push({ session, rang, le: controle.le,
                       titre: controle.titre || 'Contrôle blanc',
                       questions: (controle.questions || []).length,
                       fragiles: ((controle.correction && controle.correction.notions_fragiles) || []).length });
    });
  });
  return controles.sort((a, b) => String(b.le).localeCompare(String(a.le)));
}

/* Les jours travaillés, pour la frise de régularité. Un jour compte dès qu'on y
 * a fait quelque chose : commencé un cours, lu une fiche, passé un contrôle.
 * On ne compte pas de série et on n'en fait pas un score — voir un mois qui se
 * remplit suffit, et rater trois jours ne doit rien casser. */
function joursTravailles(sessions) {
  const jours = new Set();
  sessions.forEach((session) => {
    const marquer = (quand) => { if (quand) jours.add(String(quand).slice(0, 10)); };
    marquer(session.creeLe);
    (session.fiches || []).forEach((f) => marquer(f.le));
    (session.controles || []).forEach((c) => marquer(c.le));
  });
  return jours;
}

/* La carte d'élève : un emblème et un prénom, choisis ici et gardés ici.
 * Aucun compte, aucun envoi — c'est une carte de cantine, pas un profil. */
const EMBLEMES = ['✏️', '📚', '🧭', '🔭', '🧪', '🎒', '🗺️', '🎧', '⚗️', '🪐', '🎨', '🧩'];

function carte() {
  try {
    const brut = localStorage.getItem(CLE_CARTE);
    if (brut) return JSON.parse(brut);
  } catch (e) { /* carte illisible : on repart d'une neuve */ }
  return { prenom: '', embleme: EMBLEMES[0], teinte: 0 };
}

function garderCarte(valeurs) {
  try { localStorage.setItem(CLE_CARTE, JSON.stringify(valeurs)); } catch (e) { /* quota plein */ }
}

/* --- Le rendu de « Ma page » ------------------------------------------
 *
 * Tout empilé, la page faisait plus de trois écrans de haut sur un téléphone —
 * et elle grandissait à chaque contrôle passé. Elle tient maintenant en une
 * carte et un classeur : une seule pile ouverte à la fois, comme des
 * intercalaires. La hauteur ne dépend plus du nombre de séances.
 */

function dateCourte(iso) {
  if (!iso) return '';
  const d = new Date(iso.length > 10 ? iso : iso + 'T00:00:00');
  return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' });
}

function ligneJours(jours) {
  if (jours === null) return '';
  if (jours === 0) return "c'est aujourd'hui";
  if (jours === 1) return "c'est demain";
  return 'dans ' + jours + ' jours';
}

function urgence(jours) {
  return jours <= 1 ? 'haute' : (jours <= 3 ? 'moyenne' : 'basse');
}

/* La matière ouverte, ou null pour la vue « tout ». */
let matiereOuverte = null;
let revoirDeplie = false;

function dessinerEspace() {
  const sessions = sessionsFaites();
  dessinerCarteEleve(sessions);
  dessinerRevientCourt(sessions);
  dessinerEtagere(sessions);
  const echeances = dessinerAgenda(sessions);
  $('compte-agenda').textContent = echeances ? String(echeances) : '';
  soignerTypographie($('ecran-espace'));
}

/* Trois notions au plus, en haut de page : celles qui sont revenues. Le détail
 * par matière attend dans sa tuile — ici on ne montre que ce qui insiste. */
function dessinerRevientCourt(sessions) {
  const notions = notionsQuiReviennent(sessions).filter((n) => n.fois > 1).slice(0, 3);
  $('pan-revient').hidden = notions.length === 0;
  const liste = $('liste-reviennent');
  liste.innerHTML = '';
  notions.forEach((n) => liste.appendChild(ligneNotion(n)));
}

function dessinerEtagere(sessions) {
  const etagere = $('etagere');
  etagere.innerHTML = '';
  const toutes = matieres(sessions);
  $('vide-matieres').hidden = toutes.length > 0;
  $('bouton-tout-voir').hidden = toutes.length < 2;

  toutes.forEach((m) => {
    const tuile = document.createElement('button');
    tuile.type = 'button';
    tuile.className = 'tuile-matiere';
    tuile.dataset.teinte = teinteMatiere(m.cle);

    const code = document.createElement('span');
    code.className = 'tuile-code';
    code.textContent = codeMatiere(m.cle);

    const nom = document.createElement('span');
    nom.className = 'tuile-nom';
    nom.textContent = nomMatiere(m.cle);

    const chiffres = document.createElement('span');
    chiffres.className = 'tuile-chiffres';
    chiffres.textContent = [
      m.fiches + (m.fiches > 1 ? ' fiches' : ' fiche'),
      m.controles + (m.controles > 1 ? ' contrôles' : ' contrôle'),
    ].join(' · ');

    tuile.append(code, nom, chiffres);

    // Une échéance proche passe devant tout : c'est ce qu'on cherche des yeux.
    if (m.prochaine) {
      const jours = joursAvant(m.prochaine.date);
      const compte = document.createElement('span');
      compte.className = 'tuile-echeance';
      compte.dataset.urgence = urgence(jours);
      compte.textContent = jours === 0 ? 'Jour J' : 'J−' + jours;
      tuile.appendChild(compte);
    }

    if (m.aRevoir) {
      const revoir = document.createElement('span');
      revoir.className = 'tuile-revoir';
      revoir.dataset.insistante = m.insistantes ? 'oui' : 'non';
      revoir.textContent = m.aRevoir + ' à revoir';
      if (m.insistantes) {
        const point = document.createElement('i');
        point.setAttribute('aria-hidden', 'true');
        revoir.prepend(point);
        revoir.title = m.insistantes + ' notion(s) déjà revenue(s) plusieurs fois';
      }
      tuile.appendChild(revoir);
    }

    tuile.onclick = () => ouvrirMatiere(m.cle);
    etagere.appendChild(tuile);
  });
}

/* --- La vue d'une matière ------------------------------------------------ */

function ouvrirMatiere(cle) {
  matiereOuverte = cle;
  archives.fiches.matiere = cle || '';
  archives.controles.matiere = cle || '';
  archives.fiches.tout = false;
  archives.controles.tout = false;
  revoirDeplie = false;
  dessinerMatiere();
  montrer('ecran-matiere');
}

function dessinerMatiere() {
  const sessions = sessionsFaites();
  const cle = matiereOuverte;
  const tete = $('matiere-tete');
  tete.innerHTML = '';
  tete.dataset.teinte = cle ? teinteMatiere(cle) : '';
  tete.dataset.tout = cle ? 'non' : 'oui';

  if (cle) {
    const m = matieres(sessions).find((x) => x.cle === cle) || { fiches: 0, controles: 0 };
    const code = document.createElement('span');
    code.className = 'matiere-code';
    code.textContent = codeMatiere(cle);
    const bloc = document.createElement('div');
    const nom = document.createElement('h1');
    nom.className = 'matiere-nom';
    nom.textContent = nomMatiere(cle);
    const dessous = document.createElement('p');
    dessous.className = 'matiere-dessous';
    const morceaux = [m.fiches + (m.fiches > 1 ? ' fiches' : ' fiche'),
                      m.controles + (m.controles > 1 ? ' contrôles blancs' : ' contrôle blanc')];
    if (m.prochaine) {
      const jours = joursAvant(m.prochaine.date);
      morceaux.unshift(jours === 0 ? 'contrôle aujourd’hui' : 'contrôle ' + ligneJours(jours));
    }
    dessous.textContent = morceaux.join(' · ');
    bloc.append(nom, dessous);
    tete.append(code, bloc);
  } else {
    const nom = document.createElement('h1');
    nom.className = 'matiere-nom';
    nom.textContent = 'Tout ton travail';
    tete.appendChild(nom);
  }

  // La recherche et les filtres ne servent que dans la vue « tout » : dans une
  // matière, le filtre par matière n'a plus rien à filtrer.
  const dansTout = !cle;
  ['fiches', 'controles'].forEach((genre) => {
    $('recherche-' + genre).dataset.tout = dansTout ? 'oui' : 'non';
    $('filtres-' + genre).dataset.tout = dansTout ? 'oui' : 'non';
  });
  $('titre-fiches').textContent = dansTout ? 'Toutes tes fiches' : 'Ses fiches';
  $('titre-controles').textContent = dansTout ? 'Tous tes contrôles blancs' : 'Ses contrôles blancs';

  dessinerMatiereRevoir(sessions, cle);
  dessinerMesFiches(sessions);
  dessinerMesControles(sessions);
  soignerTypographie($('ecran-matiere'));
}

function dessinerMatiereRevoir(sessions, cle) {
  /* Pas de notions dans la vue « tout » : le tableau de bord montre déjà les
   * trois qui insistent, et chaque matière montre les siennes. Les treize d'un
   * coup y ajoutaient un écran entier avant même la première fiche, alors
   * qu'on vient ici pour chercher. */
  if (!cle) { $('pan-matiere-revoir').hidden = true; return; }
  const notions = notionsQuiReviennent(sessions).filter((n) => n.matiere === cle);
  $('pan-matiere-revoir').hidden = notions.length === 0;
  const liste = $('liste-matiere-revoir');
  liste.innerHTML = '';

  // Bornées comme le reste : neuf notions d'affilée sur une matière chargée
  // ajoutaient un écran entier. Les cinq premières sont celles qui insistent.
  const visibles = revoirDeplie ? notions : notions.slice(0, PAR_PAGE_TOUT);
  visibles.forEach((n) => liste.appendChild(ligneNotion(n, false)));

  const plus = $('plus-revoir');
  const reste = notions.length - visibles.length;
  plus.hidden = reste <= 0 && !revoirDeplie;
  if (revoirDeplie && notions.length > PAR_PAGE_TOUT) {
    plus.textContent = 'Réduire la liste';
    plus.onclick = () => { revoirDeplie = false; dessinerMatiere(); };
  } else if (reste > 0) {
    plus.textContent = 'Voir les ' + reste + ' autres';
    plus.onclick = () => { revoirDeplie = true; dessinerMatiere(); };
  }
}

/* Le rond d'accès à sa page. Il remplace une bannière large : un rond porte
 * l'emblème que l'élève a choisi, se pose partout, et se remarque sans occuper
 * la largeur d'un écran.
 *
 * Sa pastille dit qu'il y a quelque chose à faire — un contrôle dans trois
 * jours au plus, ou une notion déjà revenue. Pas un compteur d'articles non
 * lus : seulement ce qui mérite qu'on ouvre.
 */
function dessinerRonds() {
  const sessions = sessionsFaites();
  // Connecté, on a une page — même vide. Sans ça, l'élève qui s'inscrit et
  // revient plus tard n'a plus aucun moyen de l'ouvrir depuis l'accueil.
  $('acces-perso').hidden = !compte;

  const mienne = carte();
  const echeances = prochainesEcheances(sessions);
  const presse = echeances.length && joursAvant(echeances[0].date) <= 3;
  const insistantes = notionsQuiReviennent(sessions).filter((n) => n.fois > 1).length;
  const alerte = presse || insistantes > 0;

  [['rond-embleme', 'rond-pastille'], ['bandeau-embleme', 'bandeau-pastille']].forEach(
    ([embleme, pastille]) => {
      $(embleme).textContent = mienne.embleme || EMBLEMES[0];
      $(pastille).hidden = !alerte;
      $(pastille).dataset.urgence = presse ? 'haute' : 'basse';
    });

  // « dans 1 jours » : la pastille se lit à la voix, elle doit se dire.
  const jours = presse ? joursAvant(echeances[0].date) : null;
  const quoi = presse
    ? 'contrôle ' + (jours <= 0 ? 'aujourd’hui' : jours === 1 ? 'demain' : 'dans ' + jours + ' jours')
    : (insistantes ? insistantes + (insistantes > 1 ? ' notions' : ' notion') + ' à revoir' : '');
  const nom = mienne.prenom ? 'la page de ' + mienne.prenom : 'ma page';
  const etiquette = 'Ouvrir ' + nom + (quoi ? ' — ' + quoi : '');
  $('bouton-ma-page').setAttribute('aria-label', etiquette);
  // Depuis sa page, le même rond ramène à la séance : il ne doit pas s'annoncer
  // comme la porte de la page où l'on se trouve déjà.
  $('bouton-espace').setAttribute('aria-label',
    $('bouton-espace').dataset.retour === 'oui' ? 'Revenir à ma séance' : etiquette);
}

/* --- La carte, deux faces ------------------------------------------------ */

function dessinerCarteEleve(sessions) {
  const mienne = carte();
  $('embleme').textContent = mienne.embleme || EMBLEMES[0];
  $('champ-prenom').value = mienne.prenom || '';
  $('carte-annee').dataset.teinte = String(mienne.teinte || 0);
  if (!$('atelier').hidden) dessinerAtelier();

  const niveaux = [...new Set(sessions.map((s) => s.niveau).filter(Boolean))];
  const matieres = [...new Set(sessions.map((s) => s.matiere).filter(Boolean))];
  $('carte-classe').textContent = niveaux.length
    ? niveaux.join(' · ') + ' — ' + matieres.length + (matieres.length > 1 ? ' matières' : ' matière')
    : 'Ta première séance t’attend';

  dessinerProchain(sessions);

  const chiffres = [
    ['Cours', sessions.length],
    ['Fiches', toutesLesFiches(sessions).length],
    ['Contrôles blancs', tousLesControles(sessions).length],
  ];
  const boite = $('carte-chiffres');
  boite.innerHTML = '';
  chiffres.forEach(([libelle, valeur]) => {
    const groupe = document.createElement('div');
    groupe.className = 'carte-eleve-chiffre';
    const dd = document.createElement('dd');
    dd.textContent = String(valeur);
    const dt = document.createElement('dt');
    dt.textContent = libelle;
    groupe.append(dd, dt);
    boite.appendChild(groupe);
  });

  dessinerRegularite(sessions);
}

/* Le prochain contrôle ne se cache derrière aucun onglet : c'est la question
 * qu'un élève se pose en ouvrant la page. Il vit sur la carte. */
function dessinerProchain(sessions) {
  const prochains = prochainesEcheances(sessions);
  const boite = $('prochain');
  boite.innerHTML = '';
  if (!prochains.length) {
    boite.dataset.urgence = 'aucune';
    boite.textContent = 'Pose la date de ton prochain contrôle dans l’agenda.';
    return;
  }
  const session = prochains[0];
  const jours = joursAvant(session.date);
  boite.dataset.urgence = urgence(jours);

  const compte = document.createElement('span');
  compte.className = 'prochain-compte';
  compte.textContent = jours === 0 ? 'Jour J' : 'J−' + jours;

  const texte = document.createElement('div');
  const matiere = document.createElement('p');
  matiere.className = 'prochain-matiere';
  matiere.textContent = nomMatiere(session.matiere);
  const quand = document.createElement('p');
  quand.className = 'prochain-quand';
  quand.textContent = dateCourte(session.date) + ' · ' + ligneJours(jours);
  texte.append(matiere, quand);

  const aller = document.createElement('button');
  aller.type = 'button';
  aller.className = 'prochain-aller';
  // Une date posée sans cours photographié n'a rien à réviser : elle mène à
  // l'appareil photo, pas à une séance qui n'existe pas.
  aller.textContent = session.sessionId ? 'Réviser' : 'Photographier';
  aller.onclick = () => (session.sessionId
    ? ouvrirSession(session.sessionId)
    : demarrerSession({ matiere: session.matiere, date: session.date }));

  boite.append(compte, texte, aller);
}

/* --- L'agenda ------------------------------------------------------------
 *
 * Un agenda où l'élève pose lui-même ses dates. Une date de contrôle se
 * connaît des semaines avant qu'on prenne le cours en photo — l'agenda doit
 * donc exister avant la séance, pas en être un sous-produit.
 *
 * Deux sources se rejoignent dans le calendrier : les dates saisies ici, et
 * celles des séances déjà commencées. Une date saisie devient une séance dès
 * qu'on photographie le cours ; elle n'est alors plus comptée deux fois.
 */

function rendezVous() {
  try {
    const brut = localStorage.getItem(CLE_AGENDA);
    const liste = brut ? JSON.parse(brut) : [];
    return Array.isArray(liste) ? liste : [];
  } catch (e) { return []; }
}

function garderRendezVous(liste) {
  try { localStorage.setItem(CLE_AGENDA, JSON.stringify(liste)); }
  catch (e) { message("Ton téléphone n’a plus de place pour enregistrer.", 'alerte'); }
}

function ajouterRendezVous(date, matiere, note) {
  const liste = rendezVous();
  liste.push({ id: 'rv-' + Date.now().toString(36), date, matiere, note: note || '' });
  garderRendezVous(liste);
}

function retirerRendezVous(id) {
  garderRendezVous(rendezVous().filter((r) => r.id !== id));
}

function cleJour(d) {
  // Pas toISOString : il bascule en UTC et décale d'un jour le soir en France.
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0')
    + '-' + String(d.getDate()).padStart(2, '0');
}

/* Tout ce qui tombe un jour donné : les dates posées à la main et les séances
 * déjà ouvertes. Une séance qui reprend une date saisie la remplace. */
function evenementsDuJour(jour, sessions) {
  const desSessions = sessions
    .filter((s) => s.dateControle === jour)
    .map((s) => ({ source: 'session', date: jour, matiere: s.matiere,
                   sessionId: s.sessionId, chapitres: (s.chapitres || []).length }));
  const matieresPrises = new Set(desSessions.map((e) => e.matiere));
  const saisis = rendezVous()
    .filter((r) => r.date === jour && !matieresPrises.has(r.matiere))
    .map((r) => ({ source: 'saisi', ...r }));
  return [...desSessions, ...saisis];
}

/* Les prochaines échéances, toutes sources confondues : c'est ce que compte
 * l'intercalaire et ce qui alimente la carte d'élève. */
function prochainesEcheances(sessions) {
  const parJour = new Map();
  const ajouter = (date, entree) => {
    if (!date || joursAvant(date) < 0) return;
    if (!parJour.has(date)) parJour.set(date, []);
    parJour.get(date).push(entree);
  };
  sessions.forEach((s) => ajouter(s.dateControle, { source: 'session', matiere: s.matiere, sessionId: s.sessionId }));
  rendezVous().forEach((r) => ajouter(r.date, { source: 'saisi', matiere: r.matiere, id: r.id, note: r.note }));

  return [...parJour.entries()]
    .map(([date, entrees]) => {
      const session = entrees.find((e) => e.source === 'session');
      return { date, ...(session || entrees[0]), total: entrees.length };
    })
    .sort((a, b) => a.date.localeCompare(b.date));
}

let moisAffiche = null;
let jourChoisi = null;

function dessinerAgenda(sessions) {
  if (!moisAffiche) {
    const aujourdhui = new Date();
    moisAffiche = new Date(aujourdhui.getFullYear(), aujourdhui.getMonth(), 1);
  }
  dessinerMois(sessions);
  dessinerJourChoisi(sessions);
  return prochainesEcheances(sessions).length;
}

function dessinerMois(sessions) {
  $('mois-titre').textContent = moisAffiche
    .toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });

  const grille = $('mois-grille');
  grille.innerHTML = '';

  const premier = new Date(moisAffiche.getFullYear(), moisAffiche.getMonth(), 1);
  const dernier = new Date(moisAffiche.getFullYear(), moisAffiche.getMonth() + 1, 0);
  // La semaine française commence le lundi.
  const decalage = (premier.getDay() + 6) % 7;
  const aujourdhui = cleJour(new Date());

  for (let i = 0; i < decalage; i++) {
    const vide = document.createElement('span');
    vide.className = 'jour-vide';
    grille.appendChild(vide);
  }

  for (let n = 1; n <= dernier.getDate(); n++) {
    const date = new Date(moisAffiche.getFullYear(), moisAffiche.getMonth(), n);
    const cle = cleJour(date);
    const evenements = evenementsDuJour(cle, sessions);

    const jour = document.createElement('button');
    jour.type = 'button';
    jour.className = 'jour';
    jour.dataset.jour = cle;
    if (cle === aujourdhui) jour.dataset.aujourdhui = 'oui';
    if (cle === jourChoisi) jour.dataset.choisi = 'oui';
    if (evenements.length) {
      jour.dataset.occupe = 'oui';
      const passe = joursAvant(cle) < 0;
      jour.dataset.passe = passe ? 'oui' : 'non';
    }
    jour.setAttribute('aria-label', date.toLocaleDateString('fr-FR',
      { weekday: 'long', day: 'numeric', month: 'long' })
      + (evenements.length ? ' — ' + evenements.length + ' contrôle(s)' : ''));

    const chiffre = document.createElement('span');
    chiffre.className = 'jour-chiffre';
    chiffre.textContent = String(n);
    jour.appendChild(chiffre);

    if (evenements.length) {
      const points = document.createElement('span');
      points.className = 'jour-points';
      evenements.slice(0, 3).forEach(() => points.appendChild(document.createElement('i')));
      jour.appendChild(points);
    }

    jour.onclick = () => { jourChoisi = cle; dessinerEspace(); };
    grille.appendChild(jour);
  }
}

function dessinerJourChoisi(sessions) {
  const boite = $('jour-detail');
  boite.innerHTML = '';
  if (!jourChoisi) {
    const invite = document.createElement('p');
    invite.className = 'panneau-vide';
    const prochaines = prochainesEcheances(sessions);
    invite.textContent = prochaines.length
      ? 'Touche un jour pour voir ou ajouter un contrôle.'
      : 'Touche le jour de ton prochain contrôle pour l’ajouter.';
    boite.appendChild(invite);
    return;
  }

  const date = new Date(jourChoisi + 'T00:00:00');
  const titre = document.createElement('p');
  titre.className = 'jour-detail-titre';
  titre.textContent = date.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });
  boite.appendChild(titre);

  const evenements = evenementsDuJour(jourChoisi, sessions);
  evenements.forEach((e) => {
    const ligne = document.createElement('div');
    ligne.className = 'rendez-vous';
    ligne.dataset.source = e.source;

    const corps = document.createElement('div');
    const nom = document.createElement('p');
    nom.className = 'rendez-vous-matiere';
    nom.textContent = nomMatiere(e.matiere);
    corps.appendChild(nom);
    const etat = document.createElement('p');
    etat.className = 'rendez-vous-etat';
    etat.textContent = e.source === 'session'
      ? (e.chapitres ? e.chapitres + (e.chapitres > 1 ? ' chapitres prêts' : ' chapitre prêt') : 'Séance commencée')
      : (e.note || 'Cours pas encore photographié');
    corps.appendChild(etat);
    ligne.appendChild(corps);

    const action = document.createElement('button');
    action.type = 'button';
    action.className = 'rendez-vous-action';
    if (e.source === 'session') {
      action.textContent = 'Ouvrir';
      action.onclick = () => ouvrirSession(e.sessionId);
    } else {
      action.textContent = 'Photographier';
      action.onclick = () => demarrerSession({ matiere: e.matiere, date: e.date });
    }
    ligne.appendChild(action);

    if (e.source === 'saisi') {
      const retirer = document.createElement('button');
      retirer.type = 'button';
      retirer.className = 'rendez-vous-retirer';
      retirer.setAttribute('aria-label', 'Retirer ce contrôle');
      retirer.textContent = '×';
      retirer.onclick = () => { retirerRendezVous(e.id); dessinerEspace(); };
      ligne.appendChild(retirer);
    }
    boite.appendChild(ligne);
  });

  boite.appendChild(formulaireRendezVous());
}

function formulaireRendezVous() {
  const forme = document.createElement('form');
  forme.className = 'ajout-rv';

  const etiquette = document.createElement('label');
  etiquette.className = 'masque';
  etiquette.setAttribute('for', 'rv-matiere');
  etiquette.textContent = 'Matière du contrôle';

  const choix = document.createElement('select');
  choix.id = 'rv-matiere';
  (config.matieres || []).forEach((m) => {
    const option = document.createElement('option');
    option.value = m.cle;
    option.textContent = m.nom;
    choix.appendChild(option);
  });
  if (etat && etat.matiere) choix.value = etat.matiere;

  const valider = document.createElement('button');
  valider.type = 'submit';
  valider.className = 'ajout-rv-valider';
  valider.textContent = 'Ajouter';

  forme.onsubmit = (evenement) => {
    evenement.preventDefault();
    ajouterRendezVous(jourChoisi, choix.value, '');
    dessinerEspace();
  };

  forme.append(etiquette, choix, valider);
  return forme;
}

/* --- L'atelier : choisir son emblème et sa couleur -----------------------
 *
 * L'emblème changeait en tournant à chaque appui : personne ne pouvait deviner
 * qu'il y en avait douze, ni revenir à celui d'avant. Un choix se montre.
 *
 * C'est la seule personnalisation du produit, et c'est assez : sans compte ni
 * photo, choisir son emblème et la couleur de sa carte suffit à ce qu'elle
 * devienne la sienne.
 */
const TEINTES_CARTE = ['miel', 'abricot', 'rose', 'sauge', 'ciel', 'lilas'];

function dessinerAtelier() {
  const mienne = carte();

  const emblemes = $('choix-emblemes');
  emblemes.innerHTML = '';
  EMBLEMES.forEach((signe) => {
    const bouton = document.createElement('button');
    bouton.type = 'button';
    bouton.className = 'choix-embleme';
    bouton.textContent = signe;
    bouton.setAttribute('aria-label', 'Emblème ' + signe);
    bouton.setAttribute('aria-pressed', signe === mienne.embleme ? 'true' : 'false');
    bouton.onclick = () => { garderCarte({ ...carte(), embleme: signe }); dessinerEspace(); };
    emblemes.appendChild(bouton);
  });

  const teintes = $('choix-teintes');
  teintes.innerHTML = '';
  TEINTES_CARTE.forEach((nom, rang) => {
    const bouton = document.createElement('button');
    bouton.type = 'button';
    bouton.className = 'choix-teinte';
    bouton.dataset.teinte = String(rang);
    bouton.setAttribute('aria-label', 'Carte ' + nom);
    bouton.setAttribute('aria-pressed', rang === (mienne.teinte || 0) ? 'true' : 'false');
    bouton.onclick = () => { garderCarte({ ...carte(), teinte: rang }); dessinerEspace(); };
    teintes.appendChild(bouton);
  });
}

function basculerAtelier() {
  const atelier = $('atelier');
  const ouvert = atelier.hidden;
  atelier.hidden = !ouvert;
  $('embleme').setAttribute('aria-expanded', ouvert ? 'true' : 'false');
  if (ouvert) dessinerAtelier();
}

/* --- Les panneaux --------------------------------------------------------- */

/* Chaque dessinateur renvoie son nombre d'éléments : c'est ce qui alimente la
 * pastille de l'intercalaire, sans recompter deux fois. */

/* Les notions se replient : le titre et le nombre de fois suffisent à décider,
 * le détail ne s'ouvre que si on le demande. Six notions dépliées, c'était un
 * écran entier pour une information qui tient en une ligne.
 *
 * « details » plutôt qu'un accordéon maison : le navigateur sait déjà le faire,
 * au clavier comme au lecteur d'écran. */
/* Une notion, repliée. Le titre et le nombre de fois suffisent à décider ; le
 * détail ne s'ouvre que si on le demande. */
function ligneNotion(n, montrerMatiere = true) {
  const li = document.createElement('li');
  const pliage = document.createElement('details');
  pliage.className = 'revient';
  pliage.dataset.insistante = n.fois > 1 ? 'oui' : 'non';

  const tete = document.createElement('summary');
  tete.className = 'revient-tete';
  const titre = document.createElement('span');
  titre.className = 'revient-titre';
  titre.textContent = n.notion;
  const badge = document.createElement('span');
  badge.className = 'revient-fois';
  badge.textContent = n.fois > 1 ? '×' + n.fois : (montrerMatiere ? nomMatiere(n.matiere) : '');
  tete.append(titre, badge);

  const corps = document.createElement('div');
  corps.className = 'revient-corps';
  // Dans un tiroir de matière, redire la matière sous chaque notion ne dit rien.
  if (montrerMatiere) {
    const matiere = document.createElement('p');
    matiere.className = 'revient-matiere';
    matiere.textContent = nomMatiere(n.matiere);
    corps.appendChild(matiere);
  }
  if (n.pourquoi) {
    const pourquoi = document.createElement('p');
    pourquoi.className = 'revient-pourquoi';
    pourquoi.textContent = n.pourquoi;
    corps.appendChild(pourquoi);
  }
  const retester = document.createElement('button');
  retester.type = 'button';
  retester.className = 'revient-action';
  retester.textContent = 'Me retester là-dessus';
  retester.onclick = () => ouvrirSession(n.sessionId, () => lancerControle([n.notion]));
  corps.appendChild(retester);

  pliage.append(tete, corps);
  li.appendChild(pliage);
  return li;
}

/* --- L'archive ------------------------------------------------------------
 *
 * Une année d'élève, ce n'est pas quatre fiches : c'est trente, sur six
 * matières. En rangée qui défile, la trentième était à trois mille huit cents
 * pixels du bord — quinze glissements pour l'atteindre, et rien pour la
 * chercher.
 *
 * Fiches et contrôles sont deux listes du même objet : une seule archive les
 * dessine, avec sa recherche, ses filtres par matière et ses lignes groupées
 * par mois. On n'en montre que huit ; le reste se déplie à la demande, pour
 * que la page ne s'allonge pas avec l'année.
 */
/* Huit dans une matière, où la liste EST le contenu. Cinq dans la vue « tout »,
 * qui empile fiches et contrôles : seize lignes d'un coup y faisaient deux
 * écrans et demi, alors qu'on y vient pour chercher, pas pour parcourir. */
const PAR_PAGE = 6;
const PAR_PAGE_TOUT = 5;

function parPage() {
  return matiereOuverte ? PAR_PAGE : PAR_PAGE_TOUT;
}

const archives = {
  fiches: { recherche: '', matiere: '', tout: false },
  controles: { recherche: '', matiere: '', tout: false },
};

/* La couleur d'une matière ne change jamais : c'est son code, d'un écran à
 * l'autre. Prise sur sa position dans la liste des matières, pas au hasard. */
function teinteMatiere(cle) {
  const rang = (config.matieres || []).findIndex((m) => m.cle === cle);
  return String((rang < 0 ? 0 : rang) % 6);
}

/* Le code court d'une matière : « SVT », « ESP », « H-G ». Une pastille de
 * trois lettres se lit d'un coup d'oeil dans une liste de trente lignes, là où
 * « Histoire-Géographie / EMC » écrit en entier noie la ligne. */
const CODES_MATIERE = {
  'francais': 'FR', 'mathematiques': 'MATH', 'histoire-geographie': 'H-G',
  'svt': 'SVT', 'physique-chimie': 'P-C', 'technologie': 'TECH',
  'anglais': 'ANG', 'espagnol': 'ESP', 'allemand': 'ALL',
  'ses': 'SES', 'philosophie': 'PHILO', 'autre': '···',
};

function codeMatiere(cle) {
  if (CODES_MATIERE[cle]) return CODES_MATIERE[cle];
  const nom = nomMatiere(cle);
  return nom.slice(0, 3).toUpperCase();
}

function sansAccent(texte) {
  return String(texte || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

function moisDe(iso) {
  return new Date(iso).toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });
}

function dessinerArchive(genre, elements, sousTitre) {
  const reglages = archives[genre];
  const liste = $('liste-mes-' + genre);
  const plus = $('plus-' + genre);
  liste.innerHTML = '';
  $('vide-' + genre).hidden = elements.length > 0;

  // Chercher et filtrer ne sert que dans la vue « tout », et seulement au-delà
  // d'une poignée d'éléments : dans une matière, le filtre par matière n'a plus
  // rien à filtrer.
  const dansTout = $('recherche-' + genre).dataset.tout === 'oui';
  const outils = dansTout && elements.length > PAR_PAGE_TOUT;
  $('recherche-' + genre).hidden = !outils;
  $('filtres-' + genre).hidden = !outils;
  if (outils) dessinerFiltres(genre, elements);

  const cherche = sansAccent(reglages.recherche);
  const retenus = elements.filter((e) => {
    if (reglages.matiere && e.session.matiere !== reglages.matiere) return false;
    if (!cherche) return true;
    return sansAccent(e.titre + ' ' + nomMatiere(e.session.matiere)).includes(cherche);
  });

  if (!retenus.length && elements.length) {
    const li = document.createElement('li');
    li.className = 'panneau-vide';
    li.textContent = 'Rien ne correspond. Essaie un autre mot, ou enlève le filtre.';
    liste.appendChild(li);
    plus.hidden = true;
    return elements.length;
  }

  const visibles = reglages.tout ? retenus : retenus.slice(0, parPage());
  let moisCourant = null;
  visibles.forEach((e) => {
    const mois = moisDe(e.le);
    if (mois !== moisCourant) {
      moisCourant = mois;
      const entete = document.createElement('li');
      entete.className = 'archive-mois';
      entete.textContent = mois;
      liste.appendChild(entete);
    }
    liste.appendChild(ligneArchive(e, sousTitre));
  });

  const reste = retenus.length - visibles.length;
  plus.hidden = reste <= 0 && !reglages.tout;
  if (reglages.tout && retenus.length > parPage()) {
    plus.hidden = false;
    plus.textContent = 'Réduire la liste';
    plus.onclick = () => { reglages.tout = false; dessinerMatiere(); };
  } else if (reste > 0) {
    plus.textContent = 'Voir les ' + reste + ' autres';
    plus.onclick = () => { reglages.tout = true; dessinerMatiere(); };
  }
  return retenus.length;
}

/* Une puce par matière, avec son compte. La matière courante se retire d'un
 * second appui : un filtre qu'on ne sait pas enlever est un piège. */
function dessinerFiltres(genre, elements) {
  const reglages = archives[genre];
  const boite = $('filtres-' + genre);
  boite.innerHTML = '';

  const comptes = new Map();
  elements.forEach((e) => {
    const cle = e.session.matiere || '';
    comptes.set(cle, (comptes.get(cle) || 0) + 1);
  });

  const puce = (cle, libelle, nombre) => {
    const bouton = document.createElement('button');
    bouton.type = 'button';
    bouton.className = 'puce';
    bouton.dataset.teinte = cle ? teinteMatiere(cle) : '';
    bouton.setAttribute('aria-pressed', reglages.matiere === cle ? 'true' : 'false');
    bouton.textContent = libelle;
    if (nombre !== null) {
      const compte = document.createElement('span');
      compte.className = 'puce-compte';
      compte.textContent = String(nombre);
      bouton.appendChild(compte);
    }
    bouton.onclick = () => {
      reglages.matiere = reglages.matiere === cle ? '' : cle;
      reglages.tout = false;
      dessinerMatiere();
    };
    return bouton;
  };

  boite.appendChild(puce('', 'Tout', elements.length));
  [...comptes.entries()]
    .sort((a, b) => b[1] - a[1])
    .forEach(([cle, nombre]) => boite.appendChild(puce(cle, nomMatiere(cle), nombre)));
}

function ligneArchive(e, sousTitre) {
  const li = document.createElement('li');
  const bouton = document.createElement('button');
  bouton.type = 'button';
  bouton.className = 'ligne-archive';
  bouton.dataset.teinte = teinteMatiere(e.session.matiere);

  // La pastille porte la couleur de la matière — un point d'ancrage plutôt
  // qu'un filet. Elle en dit le code dans la vue « tout » ; dans une matière,
  // elle dit le jour, car répéter « SVT » sous le titre « SVT » n'apprend rien.
  const pastille = document.createElement('span');
  pastille.className = 'ligne-archive-pastille';
  if (matiereOuverte) {
    pastille.textContent = new Date(e.le).getDate();
    pastille.dataset.jour = 'oui';
    pastille.setAttribute('aria-hidden', 'true');
  } else {
    pastille.textContent = codeMatiere(e.session.matiere);
    pastille.setAttribute('aria-label', nomMatiere(e.session.matiere));
  }

  const corps = document.createElement('span');
  corps.className = 'ligne-archive-corps';

  const titre = document.createElement('span');
  titre.className = 'ligne-archive-titre';
  titre.textContent = e.titre;

  const bas = document.createElement('span');
  bas.className = 'ligne-archive-bas';
  bas.textContent = [dateCourte(e.le), sousTitre(e)].filter(Boolean).join(' · ');

  corps.append(titre, bas);
  bouton.append(pastille, corps);
  li.appendChild(bouton);
  return li;
}

/* Dans une liste de fiches, « Fiche de révision — » se répète à chaque ligne
 * sans rien dire : on ne garde que le chapitre, qui est ce qu'on cherche. */
function titreCourt(titre) {
  return String(titre || '').replace(/^(Fiche de révision|Contrôle blanc)\s*[—-]\s*/i, '');
}

function dessinerMesFiches(sessions) {
  const fiches = toutesLesFiches(sessions)
    .map((f) => ({ ...f, titre: titreCourt(f.titre) }));
  const total = dessinerArchive('fiches', fiches,
    (f) => (f.type === 'ciblee' ? 'ciblée' : ''));
  const visiblesFiches = visiblesArchive('fiches', fiches);
  $('liste-mes-fiches').querySelectorAll('.ligne-archive').forEach((bouton, rang) => {
    const visible = visiblesFiches[rang];
    if (visible) bouton.onclick = () => ouvrirFicheGardee(visible.session.sessionId, visible.rang);
  });
  return total;
}

function dessinerMesControles(sessions) {
  const controles = tousLesControles(sessions)
    .map((c) => ({ ...c, titre: titreCourt(c.titre) }));
  const total = dessinerArchive('controles', controles,
    (c) => c.questions + (c.questions > 1 ? ' questions' : ' question'));
  const visiblesControles = visiblesArchive('controles', controles);
  $('liste-mes-controles').querySelectorAll('.ligne-archive').forEach((bouton, rang) => {
    const visible = visiblesControles[rang];
    if (visible) bouton.onclick = () => ouvrirControleGarde(visible.session.sessionId, visible.rang);
  });
  return total;
}

/* Les éléments effectivement dessinés, dans l'ordre : c'est eux que les
 * boutons doivent ouvrir, pas la liste complète. */
function visiblesArchive(genre, elements) {
  const reglages = archives[genre];
  const cherche = sansAccent(reglages.recherche);
  const retenus = elements.filter((e) => {
    if (reglages.matiere && e.session.matiere !== reglages.matiere) return false;
    if (!cherche) return true;
    return sansAccent(e.titre + ' ' + nomMatiere(e.session.matiere)).includes(cherche);
  });
  return reglages.tout ? retenus : retenus.slice(0, parPage());
}

/* La frise : huit semaines, un carré par jour. Pas de compte de jours
 * consécutifs — on regarde un mois se remplir, et rater trois jours ne casse
 * rien. Elle vit au dos de la carte, là où on va la chercher. */
/* Huit semaines sur un téléphone, davantage quand la carte est large : la
 * frise remplit la place qu'on lui donne au lieu de laisser un vide à sa
 * droite. Bornée à un semestre — au-delà, les carrés deviennent illisibles. */
const SEMAINES_MIN = 8;
const SEMAINES_MAX = 26;

function semainesFrise() {
  const large = $('frise-regularite').clientWidth;
  if (!large) return SEMAINES_MIN;
  const colonne = 13;  // 10 px de carré + 3 px de gouttière
  return Math.max(SEMAINES_MIN, Math.min(SEMAINES_MAX, Math.floor(large / colonne)));
}

function dessinerRegularite(sessions) {
  const jours = joursTravailles(sessions);
  const frise = $('frise-regularite');
  frise.innerHTML = '';
  if (!jours.size) {
    $('texte-regularite').textContent = 'Ta frise se remplira à chaque séance.';
    $('frise-legende').textContent = '';
    return;
  }

  const aujourdhui = new Date();
  aujourdhui.setHours(0, 0, 0, 0);

  // Chaque colonne est une semaine : on remonte jusqu'au lundi qui précède,
  // sinon les colonnes coupent les semaines n'importe où et ne veulent rien dire.
  const semaines = semainesFrise();
  const depuisLundi = (aujourdhui.getDay() + 6) % 7;
  const premier = new Date(aujourdhui.getTime() - (depuisLundi + (semaines - 1) * 7) * 86400000);
  const cases = Math.round((aujourdhui - premier) / 86400000) + 1;

  let comptes = 0;
  for (let i = cases - 1; i >= 0; i--) {
    const jour = new Date(aujourdhui.getTime() - i * 86400000);
    const cle = jour.toISOString().slice(0, 10);
    const case_ = document.createElement('i');
    case_.className = 'case-frise';
    if (jours.has(cle)) { case_.dataset.travaille = 'oui'; comptes += 1; }
    if (i === 0) case_.dataset.aujourdhui = 'oui';
    frise.appendChild(case_);
  }
  $('texte-regularite').textContent = comptes > 1
    ? comptes + ' jours travaillés en ' + Math.round(semaines / 4.3) + ' mois.'
    : 'Premier jour travaillé. Le reste se construit comme ça.';
  const mois = (d) => d.toLocaleDateString('fr-FR', { month: 'long' });
  const debut = mois(premier);
  const fin = mois(aujourdhui);
  $('frise-legende').textContent = 'Une colonne = une semaine · '
    + (debut === fin ? debut : debut + ' → ' + fin);
}

/* --- Rouvrir ce qu'on retrouve ------------------------------------------ */

/* Ouvrir depuis « Ma page » change de séance : l'état courant devient celui
 * qu'on rouvre, pages du cahier comprises — sans quoi les vignettes d'une
 * fiche pointeraient vers les photos d'un autre cours. */
async function ouvrirSession(sessionId, ensuite) {
  const trouve = charger(sessionId);
  if (!trouve) return message("Cette séance n’est plus sur ce téléphone.", 'alerte');
  etat = trouve;
  sauver();
  photosDuCours = await lirePages(sessionId);
  if (ensuite) return ensuite();
  reprendre();
}

async function ouvrirFicheGardee(sessionId, rang) {
  await ouvrirSession(sessionId, () => {});
  const gardee = (etat.fiches || [])[rang];
  if (!gardee) return message("Cette fiche n’est plus disponible.", 'alerte');
  afficherFiche(gardee.contenu, gardee.type);
}

async function ouvrirControleGarde(sessionId, rang) {
  await ouvrirSession(sessionId, () => {});
  const garde = (etat.controles || [])[rang];
  if (!garde || !garde.correction) return message("Cette correction n’est plus disponible.", 'alerte');
  afficherCorrection(garde.correction);
}

function ouvrirEspace() {
  // Sa page, c’est son classeur : sans compte, il n’y a pas de classeur à
  // ouvrir — seulement celui du dernier élève passé sur ce navigateur.
  if (!compte) return exigerEntree('espace');
  // Montrer AVANT de dessiner : un écran caché mesure zéro, et la frise, qui
  // se règle sur la largeur disponible, retombait sur son minimum.
  montrer('ecran-espace');
  dessinerEspace();
  tracer('espace', {});
}

/* ------------------------------------------------------- pages du cahier --- */

/* La photo du cahier est ce que le produit a de plus précieux : c’est elle qui
 * prouve à l’élève que la fiche vient de SON cours et pas d’un manuel. On la
 * garde donc, au lieu de la jeter après l’analyse.
 *
 * Elle ne quitte jamais l’appareil : IndexedDB est un stockage du navigateur,
 * au même titre que localStorage, et rien n’est réenvoyé au serveur.
 */

function ouvrirBase() {
  return new Promise((resoudre, rejeter) => {
    const demande = indexedDB.open(BASE_PAGES, 1);
    demande.onupgradeneeded = () => {
      if (!demande.result.objectStoreNames.contains('pages')) {
        demande.result.createObjectStore('pages');
      }
    };
    demande.onsuccess = () => resoudre(demande.result);
    demande.onerror = () => rejeter(demande.error);
  });
}

async function garderPages(sessionId, pages) {
  try {
    const base = await ouvrirBase();
    await new Promise((resoudre, rejeter) => {
      const transaction = base.transaction('pages', 'readwrite');
      transaction.objectStore('pages').put(pages, sessionId);
      transaction.oncomplete = resoudre;
      transaction.onerror = () => rejeter(transaction.error);
    });
  } catch (e) {
    // Navigation privée, quota, stockage refusé : la fiche se passera des
    // vignettes plutôt que d’échouer.
    console.warn('pages non conservées :', e);
  }
}

/* Les pages d'une séance disparue n'illustrent plus rien : elles occupent le
 * stockage du téléphone pour rien, et ce sont les objets les plus lourds. */
async function oublierPages(sessionId) {
  try {
    const base = await ouvrirBase();
    await new Promise((resoudre) => {
      const transaction = base.transaction('pages', 'readwrite');
      transaction.objectStore('pages').delete(sessionId);
      transaction.oncomplete = resoudre;
      transaction.onerror = resoudre;
    });
  } catch (e) { /* stockage refusé : rien à nettoyer */ }
}

async function lirePages(sessionId) {
  try {
    const base = await ouvrirBase();
    return await new Promise((resoudre, rejeter) => {
      const transaction = base.transaction('pages', 'readonly');
      const demande = transaction.objectStore('pages').get(sessionId);
      demande.onsuccess = () => resoudre(demande.result || []);
      demande.onerror = () => rejeter(demande.error);
    });
  } catch (e) {
    return [];
  }
}

/* ------------------------------------------------------------- entrée --- */

/*
 * Un vrai compte : adresse mail et mot de passe. Deux onglets, parce qu'il y a
 * deux gestes différents — revenir chez soi, ou en ouvrir un.
 *
 * Le jeton de connexion est un cookie HttpOnly : ce script ne peut pas le lire,
 * et n’essaie pas. « Suis-je connecté ? » est une question qu’on pose au
 * serveur. Le mot de passe, lui, ne fait qu’un aller : il part dans la requête
 * et n’est jamais gardé, ni en mémoire au-delà de l’appel, ni en localStorage.
 */

// Ce que l’élève voulait faire quand on lui a demandé d’entrer. On l’y ramène
// après : une porte qui rend à l’accueil fait recommencer le geste.
let apresEntree = null;

async function qui() {
  try { return await api('/api/auth/moi'); } catch (e) { return { connecte: false }; }
}

const VOLETS = ['volet-connexion', 'volet-inscription', 'volet-oubli', 'volet-code'];

function montrerVolet(nom) {
  VOLETS.forEach((v) => { $(v).hidden = v !== nom; });
  cacherErreursEntree();
  // Les onglets ne suivent que leurs deux volets : « oublié » est un détour,
  // pas un troisième onglet.
  const surInscription = nom === 'volet-inscription';
  if (nom === 'volet-connexion' || surInscription) {
    $('onglet-connexion').setAttribute('aria-selected', String(!surInscription));
    $('onglet-inscription').setAttribute('aria-selected', String(surInscription));
    $('onglet-connexion').parentElement.dataset.actif = surInscription ? 'inscription' : 'connexion';
  }
  $('onglet-connexion').parentElement.hidden = !(nom === 'volet-connexion' || surInscription);
  const premier = $(nom).querySelector('input:not([type="hidden"])');
  if (premier) setTimeout(() => premier.focus(), 60);
}

/* Demander l’entrée sans perdre le geste en cours. */
function exigerEntree(suite) {
  apresEntree = suite || null;
  montrer('ecran-connexion');
  montrerVolet('volet-connexion');
}

function cacherErreursEntree() {
  ['erreur-connexion', 'erreur-inscription', 'erreur-oubli', 'erreur-code']
    .forEach((id) => { $(id).hidden = true; });
}

function direErreur(id, texte) {
  const boite = $(id);
  boite.textContent = texte;
  boite.hidden = false;
}

/* Pendant qu’une requête part, le bouton dit ce qui se passe et refuse d’être
   cliqué deux fois — sinon on crée deux comptes avec la même adresse. */
async function pendant(bouton, libelle, action) {
  const avant = bouton.textContent;
  bouton.disabled = true;
  bouton.textContent = libelle;
  try { return await action(); } finally {
    bouton.disabled = false;
    bouton.textContent = avant;
  }
}

const MOTIF_EMAIL = /^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$/;

/* Une validation côté navigateur, pour ne pas faire attendre un aller-retour
   sur une faute de frappe. Le serveur revalide : lui seul décide. */
function adresseValable(email) { return MOTIF_EMAIL.test((email || '').trim()); }

/* --- Se connecter -------------------------------------------------------- */

async function seConnecter() {
  const email = $('champ-email').value.trim();
  const mdp = $('champ-mdp').value;
  if (!adresseValable(email)) {
    return direErreur('erreur-connexion', 'Cette adresse ne ressemble pas à une adresse mail.');
  }
  if (!mdp) return direErreur('erreur-connexion', 'Il manque ton mot de passe.');
  try {
    const reponse = await pendant($('bouton-connexion'), 'On vérifie…',
      () => envoyerJson('/api/auth/connexion', { email, mot_de_passe: mdp }));
    $('champ-mdp').value = '';
    await ouvrirLaPorte(reponse);
  } catch (erreur) {
    direErreur('erreur-connexion', erreur.message);
    $('champ-mdp').select();
  }
}

/* --- S’inscrire ---------------------------------------------------------- */

async function sInscrire() {
  const prenom = $('champ-prenom-inscription').value.trim();
  const niveau = $('champ-classe-inscription').value;
  const email = $('champ-email-inscription').value.trim();
  const mdp = $('champ-mdp-inscription').value;
  const confirmation = $('champ-mdp-confirmation').value;

  if (!prenom) return direErreur('erreur-inscription', 'Dis-nous ton prénom.');
  if (!adresseValable(email)) {
    return direErreur('erreur-inscription', 'Cette adresse ne ressemble pas à une adresse mail.');
  }
  if (mdp.length < 8) {
    return direErreur('erreur-inscription', 'Ton mot de passe doit faire au moins 8 caractères.');
  }
  // Vérifié ici et pas au serveur : la confirmation ne le regarde pas, et un
  // aller-retour pour dire « les deux ne sont pas pareils » est un aller-retour
  // de trop.
  if (mdp !== confirmation) {
    return direErreur('erreur-inscription', 'Les deux mots de passe ne sont pas les mêmes.');
  }
  try {
    const reponse = await pendant($('bouton-inscription'), 'On crée ton compte…',
      () => envoyerJson('/api/auth/inscription',
        { email, mot_de_passe: mdp, prenom, niveau }));
    $('champ-mdp-inscription').value = '';
    $('champ-mdp-confirmation').value = '';
    await ouvrirLaPorte(reponse);
  } catch (erreur) {
    direErreur('erreur-inscription', erreur.message);
    // « Un compte existe déjà » : l’élève est au mauvais endroit, on l’emmène
    // au bon avec son adresse déjà tapée.
    if (erreur.genreAuth === 'existe') {
      $('champ-email').value = email;
      setTimeout(() => { montrerVolet('volet-connexion');
                         direErreur('erreur-connexion', erreur.message); }, 900);
    }
  }
}

/* Trois barres, pas une note sur cent : « ça va » et « solide » suffisent à
   guider, et personne ne sait ce que veut dire 62 %. */
function forceMotDePasse(mdp) {
  if (!mdp || mdp.length < 8) return mdp ? 1 : 0;
  let points = 0;
  if (mdp.length >= 12) points += 1;
  if (mdp.length >= 16) points += 1;
  // La variété compte moins que la longueur, mais elle compte.
  const familles = [/[a-z]/, /[A-Z]/, /[0-9]/, /[^a-zA-Z0-9]/].filter((f) => f.test(mdp)).length;
  if (familles >= 3) points += 1;
  return Math.min(3, 1 + points);
}

function majJauge() {
  const mdp = $('champ-mdp-inscription').value;
  const force = forceMotDePasse(mdp);
  $('jauge-mdp').dataset.force = String(force);
  const dit = ['', 'Trop court pour l’instant.', 'Ça peut aller.', 'Solide.'][force];
  $('note-mdp').textContent = mdp
    ? dit + ' Trois mots collés valent mieux qu’un mot avec un chiffre au bout.'
    : '8 caractères au minimum. Trois mots collés valent mieux qu’un mot avec un chiffre au bout.';
}

/* --- Mot de passe oublié ------------------------------------------------- */

let emailEnCours = '';
let minuteurRenvoi = null;

async function demanderCode(email) {
  const propre = (email || '').trim();
  if (!adresseValable(propre)) {
    return direErreur('erreur-oubli', 'Cette adresse ne ressemble pas à une adresse mail.');
  }
  const bouton = $('volet-oubli').hidden ? $('bouton-renvoyer') : $('bouton-envoyer-code');
  try {
    const reponse = await pendant(bouton, 'On envoie…',
      () => envoyerJson('/api/auth/oubli', { email: propre }));
    emailEnCours = propre;
    $('rappel-email').textContent = propre;
    montrerVolet('volet-code');
    $('champ-code').value = '';
    // En démonstration, le code s’affiche : il n’y a pas de serveur de courrier.
    if (reponse.code_demonstration) {
      $('code-demonstration').textContent =
        'Démonstration : aucun mail n’est envoyé. Ton code est ' + reponse.code_demonstration + '.';
      $('code-demonstration').hidden = false;
    } else {
      $('code-demonstration').hidden = true;
    }
    compteARebours(reponse.renvoi_dans_secondes || 60);
  } catch (erreur) {
    direErreur($('volet-oubli').hidden ? 'erreur-code' : 'erreur-oubli', erreur.message);
    if (erreur.attendre) compteARebours(erreur.attendre);
  }
}

/* « Renvoyer le code » doit dire quand il redeviendra possible : un bouton qui
   refuse sans expliquer donne l’impression que le site est cassé. */
function compteARebours(secondes) {
  const bouton = $('bouton-renvoyer');
  clearInterval(minuteurRenvoi);
  let reste = Math.max(0, Math.round(secondes));
  const afficher = () => {
    if (reste <= 0) {
      clearInterval(minuteurRenvoi);
      bouton.disabled = false;
      bouton.textContent = 'Renvoyer le code';
      return;
    }
    bouton.disabled = true;
    bouton.textContent = 'Renvoyer le code (' + reste + ' s)';
    reste -= 1;
  };
  afficher();
  minuteurRenvoi = setInterval(afficher, 1000);
}

async function reinitialiser() {
  const code = $('champ-code').value.replace(/\D/g, '');
  const mdp = $('champ-mdp-nouveau').value;
  if (code.length !== 6) return direErreur('erreur-code', 'Le code fait six chiffres.');
  if (mdp.length < 8) {
    return direErreur('erreur-code', 'Ton mot de passe doit faire au moins 8 caractères.');
  }
  try {
    const reponse = await pendant($('bouton-reinitialiser'), 'On vérifie…',
      () => envoyerJson('/api/auth/reinitialiser',
        { email: emailEnCours, code, mot_de_passe: mdp }));
    clearInterval(minuteurRenvoi);
    $('champ-mdp-nouveau').value = '';
    message('Mot de passe changé. Tu es connecté.');
    await ouvrirLaPorte(reponse);
  } catch (erreur) {
    direErreur('erreur-code', erreur.message);
  }
}

/* --- Une fois dedans ----------------------------------------------------- */

/* Connecté : on attache le navigateur au compte, on relit son classeur, et on
   ramène l’élève là où il allait. */
async function ouvrirLaPorte(reponse) {
  compte = { id: reponse.compte, email: reponse.email,
             prenom: reponse.prenom || '', niveau: reponse.niveau || '' };
  attacherAuCompte(compte.id);
  adopterProfil();
  majCompte();
  menageSessions();
  const suite = apresEntree;
  apresEntree = null;
  if (suite === 'espace') return ouvrirEspace();
  if (suite && suite.agenda) return demarrerSession(suite.agenda);
  return demarrerSession();
}

/* Le prénom et la classe donnés à l’inscription servent tout de suite : la carte
   de sa page porte son prénom, et le sélecteur de niveau part sur sa classe. On
   ne lui redemande pas ce qu’il vient d’écrire. */
function adopterProfil() {
  if (!compte) return;
  if (compte.prenom) {
    // garderCarte remplace la carte entière : sans le report, l'emblème et la
    // couleur choisis par l'élève partiraient avec.
    const mienne = carte();
    if (!mienne.prenom) garderCarte(Object.assign({}, mienne, { prenom: compte.prenom }));
  }
  if (compte.niveau && $('champ-niveau').querySelector('option[value="' + compte.niveau + '"]')) {
    $('champ-niveau').value = compte.niveau;
  }
}

function majCompte() {
  $('compte-adresse').textContent = compte ? compte.email : '';
}

async function sortir() {
  try { await api('/api/auth/sortir', { method: 'POST' }); } catch (e) { /* déjà dehors */ }
  oublierLeCompte();
  message('À bientôt. Ton travail t’attend ici.');
  montrer('ecran-accueil');
}

/* Sortir ne touche pas au classeur : il est rangé sous le préfixe du compte, et
   l’élève le retrouve entier en revenant. Ce qu’on lâche, c’est la séance
   ouverte en mémoire — pas ce qui est écrit. */
function oublierLeCompte() {
  compte = null;
  etat = null;
  photosDuCours = [];
  attacherAuCompte(null);
  $('bouton-reprendre').hidden = true;
  dessinerRonds();
}

async function effacerLeCompte() {
  if (!compte) return;
  const sur = window.confirm(
    'Effacer ton compte ?\n\n'
    + 'Ton adresse et tes séances sont supprimées du serveur, et tout ce qui est '
    + 'gardé dans ce navigateur — tes cours, tes fiches, tes contrôles — part avec. '
    + 'C’est définitif.');
  if (!sur) return;
  const identifiant = compte.id;
  try {
    attendre('On efface tout…');
    await api('/api/auth/supprimer', { method: 'POST' });
    effacerLeNavigateur(identifiant);
    fermerAttente();
    oublierLeCompte();
    message('Tout est effacé.');
    montrer('ecran-accueil');
  } catch (erreur) { fermerAttente(); gererErreur(erreur); }
}

/* Effacer côté serveur sans effacer ici laisserait tout le travail visible au
   prochain qui se connecte avec la même adresse. */
function effacerLeNavigateur(identifiant) {
  const prefixe = 'cb.' + identifiant + '.';
  try {
    Object.keys(localStorage)
      .filter((cle) => cle.indexOf(prefixe) === 0)
      .forEach((cle) => localStorage.removeItem(cle));
  } catch (e) { /* stockage indisponible */ }
  try { indexedDB.deleteDatabase('cb-pages-' + identifiant); } catch (e) { /* idem */ }
}

/* ------------------------------------------------------------------ api --- */

async function api(chemin, options = {}) {
  const reponse = await fetch(chemin, options);
  if (reponse.ok) return reponse.json();

  let corps = {};
  try { corps = await reponse.json(); } catch (e) { /* réponse non JSON */ }

  if (reponse.status === 401) {
    // Le jeton a expiré, ou n’a jamais existé. On ne dit pas « erreur » : on
    // rouvre la porte, ce que l’élève doit faire de toute façon.
    throw new ErreurApi('Il faut entrer pour continuer.', 'entree');
  }
  if (reponse.status === 400 && corps.erreur === 'auth') {
    const erreur = new ErreurApi(corps.message || 'Ça n’a pas marché.', 'auth');
    erreur.attendre = corps.attendre || 0;
    // Le genre dit ce qui n'allait pas : « existe » emmène au bon volet.
    erreur.genreAuth = corps.genre || '';
    throw erreur;
  }
  if (reponse.status === 404 && corps.detail === 'session inconnue') {
    throw new ErreurApi("Cette session n’existe plus sur le serveur. On en recommence une.", 'session');
  }
  if (reponse.status === 429) {
    throw new ErreurApi(corps.message || 'Limite atteinte pour aujourd’hui.', 'quota');
  }
  if (reponse.status === 503) {
    throw new ErreurApi(corps.message || 'Le service est indisponible. Réessaie.', 'modele');
  }
  throw new ErreurApi(corps.detail || corps.message || "Ça n’a pas marché. Réessaie.", 'autre');
}

class ErreurApi extends Error {
  constructor(message, genre) {
    super(message);
    this.genre = genre;
    this.attendre = 0;
  }
}

function envoyerJson(chemin, corps) {
  return api(chemin, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(corps),
  });
}

function tracer(type, details = {}) {
  if (!etat) return;
  // Sans await : une mesure ne doit jamais faire attendre un élève.
  envoyerJson('/api/evenement', { session_id: etat.sessionId, type, details }).catch(() => {});
}

/* --------------------------------------------------------------- écrans --- */

function montrer(id) {
  ecrans().forEach((section) => { section.hidden = section.id !== id; });
  // L'ambiance dépend du moment : on révise au chaud, on se teste au froid.
  document.documentElement.dataset.ecran = id.replace('ecran-', '');
  window.scrollTo({ top: 0, behavior: 'instant' in window ? 'instant' : 'auto' });
  majBandeau(id);
}

function majBandeau(idEcran) {
  const bandeau = $('bandeau');
  // « Ma page » et l'écran d'une matière se consultent même sans séance en
  // cours : ils relisent l'historique. Sans ce cas, le bandeau — donc la
  // marque, donc le rond — disparaissait sur l'écran d'une matière.
  const dansMaPage = idEcran === 'ecran-espace' || idEcran === 'ecran-matiere';
  const dansEspace = idEcran === 'ecran-espace';
  if (idEcran === 'ecran-accueil' || (!etat && !dansMaPage)) { bandeau.hidden = true; return; }
  bandeau.hidden = false;
  // Le bandeau se cale sur la largeur de l'écran qu'il coiffe.
  bandeau.dataset.large = dansMaPage ? 'oui' : 'non';
  const matiere = etat && (config.matieres.find((m) => m.cle === etat.matiere) || {}).nom;
  $('bandeau-matiere').textContent = dansMaPage ? 'Repère' : (matiere || 'Repère');
  $('bandeau-compte').textContent = etat ? texteCompteARebours() : '';
  $('bandeau-compte').hidden = dansMaPage || !etat || !etat.dateControle;
  // Depuis sa page, le rond ramène à la séance en cours.
  $('bouton-espace').dataset.retour = dansEspace ? 'oui' : 'non';
  $('bouton-espace').hidden = dansEspace && !etat;
  dessinerRonds();
}

function joursAvantControle() {
  if (!etat || !etat.dateControle) return null;
  const cible = new Date(etat.dateControle + 'T00:00:00');
  const aujourdhui = new Date();
  aujourdhui.setHours(0, 0, 0, 0);
  return Math.round((cible - aujourdhui) / 86400000);
}

function texteCompteARebours() {
  const jours = joursAvantControle();
  if (jours === null) return '';
  if (jours < 0) return 'Contrôle passé';
  if (jours === 0) return "C’est aujourd’hui";
  if (jours === 1) return 'Demain';
  return 'J−' + jours;
}

function attendre(texte, sousTexte = '') {
  $('attente-texte').textContent = texte;
  $('attente-sous-texte').textContent = sousTexte;
  $('attente').hidden = false;
}

function fermerAttente() { $('attente').hidden = true; }

let minuteurMessage = null;
function message(texte, ton = 'neutre', duree = 4200) {
  const boite = $('message');
  boite.textContent = texte;
  boite.dataset.ton = ton;
  boite.hidden = false;
  clearTimeout(minuteurMessage);
  minuteurMessage = setTimeout(() => { boite.hidden = true; }, duree);
}

function gererErreur(erreur) {
  fermerAttente();
  if (erreur instanceof ErreurApi) {
    // Sortir de session ne mérite pas un message rouge : on ramène à la porte.
    if (erreur.genre === 'entree') {
      oublierLeCompte();
      return exigerEntree(null);
    }
    message(erreur.message, erreur.genre === 'quota' ? 'neutre' : 'alerte', 7000);
    if (erreur.genre === 'session') demarrerSession();
    return;
  }
  console.error(erreur);
  message('Connexion perdue. Vérifie ton réseau et réessaie.', 'alerte');
}

/* ------------------------------------------------------------ démarrage --- */

async function initialiser() {
  try { config = await api('/api/config'); } catch (e) { /* valeurs par défaut */ }
  $('mention-demo').hidden = !config.mode_demonstration;

  remplirSelecteur($('champ-niveau'), config.niveaux, '3e');
  remplirSelecteur($('champ-classe-inscription'), config.niveaux, '3e');
  remplirSelecteur($('champ-matiere'), config.matieres,
                   config.matiere_par_defaut || 'histoire-geographie');

  // Qui est là, avant tout le reste : c'est le compte qui décide sous quel
  // préfixe se trouve le classeur. Lire d'abord et attacher ensuite ferait
  // lire celui de personne.
  const moi = await qui();
  if (moi.connecte) {
    compte = { id: moi.compte, email: moi.email,
               prenom: moi.prenom || '', niveau: moi.niveau || '' };
    attacherAuCompte(compte.id);
    adopterProfil();
    majCompte();
  }

  const params = new URLSearchParams(location.search);
  const depuisLien = params.get('s');

  // Un lien de reprise pour quelqu'un qui n'est pas entré : on le garde sous le
  // coude et on ouvre la porte. Sans ça, le lien reçu par mail se perdait dans
  // l'accueil et il fallait le rouvrir après s'être connecté.
  if (!compte) {
    dessinerRonds();
    montrer(depuisLien ? 'ecran-connexion' : 'ecran-accueil');
    if (depuisLien) exigerEntree(null);
    armerRevelations();
    armerCopie();
    return;
  }

  // Avant de lire l'historique : deux séances jumelles n'ont aucune raison de
  // rester deux, et un départ abandonné n'a rien à montrer.
  menageSessions();

  const derniere = localStorage.getItem(CLE_DERNIERE);

  if (depuisLien) {
    const trouve = charger(depuisLien);
    if (trouve) {
      etat = trouve;
      photosDuCours = await lirePages(etat.sessionId);
      tracer('ouverture', { origine: 'lien' });
      return reprendre();
    }
    // Le lien vient d’un autre appareil : la session serveur existe, l’état local non.
    try {
      const info = await api('/api/session/' + encodeURIComponent(depuisLien));
      etat = etatNeuf(depuisLien, info.lien_de_reprise);
      sauver();
      tracer('ouverture', { origine: 'lien_autre_appareil' });
      message("Session retrouvée, mais ton cours était gardé sur ton autre téléphone. On repart des photos.");
      return montrer('ecran-contexte');
    } catch (e) { /* session inconnue : on tombe sur l’accueil */ }
  }

  if (derniere && charger(derniere)) {
    $('bouton-reprendre').hidden = false;
  }
  dessinerRonds();
  montrer('ecran-accueil');
  armerRevelations();
  armerCopie();
}

function remplirSelecteur(selecteur, valeurs, defaut) {
  selecteur.innerHTML = '';
  valeurs.forEach((v) => {
    const option = document.createElement('option');
    option.value = v.cle;
    option.textContent = v.nom;
    if (v.cle === defaut) option.selected = true;
    selecteur.appendChild(option);
  });
}

async function demarrerSession(depuisAgenda = null) {
  if (!compte) return exigerEntree(depuisAgenda ? { agenda: depuisAgenda } : 'session');
  try {
    attendre('On prépare ta session…');
    const info = await api('/api/session', { method: 'POST' });
    etat = etatNeuf(info.session_id, info.lien_de_reprise);
    // Venir de l'agenda, c'est déjà savoir quoi et quand : on ne le redemande pas.
    if (depuisAgenda) {
      etat.matiere = depuisAgenda.matiere || '';
      etat.dateControle = depuisAgenda.date || '';
      if (etat.matiere) $('champ-matiere').value = etat.matiere;
      if (etat.dateControle) $('champ-date').value = etat.dateControle;
    }
    sauver();
    fermerAttente();
    montrer('ecran-contexte');
  } catch (e) { gererErreur(e); }
}

function reprendre() {
  if (!etat) return montrer('ecran-accueil');
  dessinerReprise();
  montrer('ecran-reprise');
}

/* ----------------------------------------------- étape 1 : le contexte --- */

async function validerContexte() {
  etat.niveau = $('champ-niveau').value;
  etat.matiere = $('champ-matiere').value;
  etat.dateControle = $('champ-date').value;
  etat.etape = 'photos';
  sauver();
  envoyerJson('/api/session/contexte', {
    session_id: etat.sessionId,
    niveau: etat.niveau,
    matiere: etat.matiere,
    date_controle: etat.dateControle,
  }).catch(() => {});
  montrer('ecran-photos');
}

/* ------------------------------------------------- étape 1b : photos ----- */

async function ajouterPhotos(fichiers) {
  const restant = config.max_photos - photosEnAttente.length;
  if (restant <= 0) {
    message(config.max_photos + ' photos au maximum en une fois.');
    return;
  }
  const aTraiter = Array.from(fichiers).slice(0, restant);
  if (fichiers.length > restant) {
    message('On garde les ' + restant + ' premières, tu pourras en ajouter d’autres ensuite.');
  }
  for (const fichier of aTraiter) {
    try {
      const reduite = await reduirePhoto(fichier);
      photosEnAttente.push(reduite);
    } catch (e) {
      message("Une photo n’a pas pu être lue. Réessaie avec celle-là.", 'alerte');
    }
  }
  dessinerPhotos();
}

// Réduire avant l’envoi : moins de données mobiles pour l’élève, moins de tokens
// pour nous. Au-delà de 1568 px le modèle redimensionne de toute façon.
function reduirePhoto(fichier) {
  return new Promise((resoudre, rejeter) => {
    const url = URL.createObjectURL(fichier);
    const image = new Image();
    image.onload = () => {
      const echelle = Math.min(1, COTE_MAX_PHOTO / Math.max(image.width, image.height));
      const largeur = Math.round(image.width * echelle);
      const hauteur = Math.round(image.height * echelle);
      const toile = document.createElement('canvas');
      toile.width = largeur;
      toile.height = hauteur;
      toile.getContext('2d').drawImage(image, 0, 0, largeur, hauteur);
      toile.toBlob((blob) => {
        URL.revokeObjectURL(url);
        if (!blob) return rejeter(new Error('conversion impossible'));
        resoudre({
          blob,
          apercu: toile.toDataURL('image/jpeg', 0.45),
          pleine: toile.toDataURL('image/jpeg', 0.78),
          nom: fichier.name,
        });
      }, 'image/jpeg', QUALITE_PHOTO);
    };
    image.onerror = () => { URL.revokeObjectURL(url); rejeter(new Error('image illisible')); };
    image.src = url;
  });
}

/* L'ordre des pages n'est pas décidé ici : c'est celui dans lequel le téléphone
 * a livré les fichiers, et la spécification HTML ne le garantit pas — selon
 * l'appareil et l'application photos, c'est l'ordre de sélection, celui de la
 * galerie, ou la date de prise de vue.
 *
 * Tant que les photos ne servaient qu'à produire du texte, ça se voyait peu :
 * le modèle recollait le cours au sens. Depuis que chaque partie de la fiche
 * renvoie à une page précise, une page mal placée ouvre la mauvaise feuille,
 * sans rien dire. L'élève doit pouvoir corriger — d'où le numéro visible et la
 * poignée ci-dessous.
 */
function dessinerPhotos() {
  const liste = $('liste-photos');
  const total = photosEnAttente.length;
  liste.innerHTML = '';
  photosEnAttente.forEach((photo, index) => {
    const element = document.createElement('li');
    element.dataset.rang = String(index);
    element.tabIndex = 0;
    element.setAttribute('aria-label', 'Page ' + (index + 1) + ' sur ' + total);

    const image = document.createElement('img');
    image.src = photo.apercu;
    image.alt = '';

    const numero = document.createElement('span');
    numero.className = 'numero-page';
    numero.textContent = String(index + 1);
    numero.setAttribute('aria-hidden', 'true');

    const retirer = document.createElement('button');
    retirer.type = 'button';
    retirer.textContent = '×';
    retirer.setAttribute('aria-label', 'Retirer la page ' + (index + 1));
    retirer.onclick = () => { photosEnAttente.splice(index, 1); dessinerPhotos(); };

    element.append(image, numero, retirer);

    if (total > 1) {
      const poignee = document.createElement('button');
      poignee.type = 'button';
      poignee.className = 'poignee';
      poignee.textContent = '⇅';
      poignee.setAttribute('aria-label', 'Déplacer la page ' + (index + 1));
      element.appendChild(poignee);
      armerGlissement(element, poignee, index);
      // Au clavier, les flèches font le même travail que la poignée.
      element.onkeydown = (evenement) => {
        const pas = { ArrowLeft: -1, ArrowUp: -1, ArrowRight: 1, ArrowDown: 1 }[evenement.key];
        if (!pas) return;
        evenement.preventDefault();
        if (deplacerPage(index, index + pas)) {
          const arrivee = liste.children[index + pas];
          if (arrivee) arrivee.focus();
        }
      };
    }

    liste.appendChild(element);
  });
  $('aide-ordre').hidden = total < 2;
  $('bouton-analyser').disabled = total === 0;
  $('bouton-analyser').textContent = total > 1
    ? 'Analyser mes ' + total + ' pages'
    : 'Analyser mon cours';
}

/* Les blocs de la page publique n'arrivent qu'au moment où on descend les
 * chercher. Un IntersectionObserver plutôt qu'un écouteur de défilement : le
 * navigateur fait le calcul, pas nous, et rien ne rame sur un vieux téléphone.
 */
function armerRevelations() {
  const blocs = document.querySelectorAll('.a-reveler');
  if (!blocs.length) return;
  const bouge = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!bouge || !('IntersectionObserver' in window)) return;

  // On ne cache qu'à partir d'ici : avant, la page était déjà lisible.
  document.documentElement.dataset.revelations = 'oui';
  const guetteur = new IntersectionObserver((entrees) => {
    entrees.forEach((entree) => {
      if (!entree.isIntersecting) return;
      entree.target.dataset.vu = 'oui';
      guetteur.unobserve(entree.target);
    });
  // Une marge en pourcentage rendait le bas de page inatteignable : sur un
  // grand écran, la page ne défile pas d'assez pour faire franchir la ligne de
  // déclenchement au pied, qui restait invisible pour toujours. Une marge fixe
  // et courte ne peut pas dépasser la hauteur de défilement disponible.
  }, { rootMargin: '0px 0px -40px 0px' });
  blocs.forEach((b) => guetteur.observe(b));
}

/* La copie corrigée de l'accueil : l'annotation du prof s'écrit, et la feuille
 * prend la lumière du curseur.
 *
 * Tout part d'ici et pas de la feuille de style, pour la même raison que les
 * révélations : si le script ne tourne pas, l'annotation est simplement là.
 */
function armerCopie() {
  const copie = document.querySelector('.copie');
  if (!copie) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  const ecrire = () => {
    copie.dataset.ecrit = 'non';
    // Deux trames : la première pose l'état caché, la seconde le relâche —
    // sans quoi le navigateur regroupe les deux et ne transitionne pas.
    requestAnimationFrame(() => requestAnimationFrame(() => {
      copie.dataset.ecrit = 'oui';
    }));
  };

  // On cache tout de suite, on écrit après : attendre pour cacher ferait
  // apparaître l'annotation, disparaître, puis se réécrire.
  copie.dataset.ecrit = 'non';
  // La phrase du prof est la chute du héros : elle arrive après lui.
  setTimeout(() => { copie.dataset.ecrit = 'oui'; }, 900);

  if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;
  copie.addEventListener('mouseenter', ecrire);
}

/* Les surfaces qui prennent la lumière du curseur.
 *
 * La liste double celle de la feuille de style (repère « liste-eclairables ») ;
 * un test vérifie qu'elles ne divergent pas, faute de quoi on ajouterait une
 * carte d'un côté sans l'autre et elle resterait mate sans qu'on le voie.
 */
const ECLAIRABLES = '.copie, .case-carrefour, .argument, .chapitres li,'
  + ' .carte-fiche, .tuile, .carte-correction, .fragiles, .document,'
  + ' .rappel, .lien-reprise, .zone-photos';

/* Un seul écouteur pour toute la page, quel que soit le nombre de cartes —
 * et elles se recréent à chaque fiche. En poser un par carte les multiplierait
 * sans que rien ne les retire.
 *
 * Une mise à jour par trame au plus : un pointermove non bridé fait tomber
 * l'animation sur un portable modeste.
 */
function armerLumiere() {
  if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  let attendue = null;
  let dernier = null;
  document.addEventListener('pointermove', (evenement) => {
    dernier = evenement;
    if (attendue) return;
    attendue = requestAnimationFrame(() => {
      attendue = null;
      const surface = dernier.target.closest && dernier.target.closest(ECLAIRABLES);
      if (!surface) return;
      const boite = surface.getBoundingClientRect();
      if (!boite.width || !boite.height) return;
      surface.style.setProperty('--px', ((dernier.clientX - boite.left) / boite.width).toFixed(3));
      surface.style.setProperty('--py', ((dernier.clientY - boite.top) / boite.height).toFixed(3));
    });
  }, { passive: true });
}

function annoncerPhotos(texte) {
  const zone = $('annonce-photos');
  if (zone) zone.textContent = texte;
}

function deplacerPage(depuis, vers) {
  if (vers < 0 || vers >= photosEnAttente.length || vers === depuis) return false;
  const [photo] = photosEnAttente.splice(depuis, 1);
  photosEnAttente.splice(vers, 0, photo);
  dessinerPhotos();
  annoncerPhotos('Page déplacée en position ' + (vers + 1) + ' sur ' + photosEnAttente.length + '.');
  return true;
}

let glisse = null;

function armerGlissement(element, poignee, rang) {
  poignee.onpointerdown = (evenement) => {
    evenement.preventDefault();
    const liste = $('liste-photos');
    glisse = {
      element,
      rang,
      cible: rang,
      x0: evenement.clientX,
      y0: evenement.clientY,
      // Les rectangles sont figés au départ : rien ne bouge dans la grille
      // pendant le déplacement, seule la vignette tirée suit le doigt.
      rects: Array.from(liste.children).map((el) => el.getBoundingClientRect()),
    };
    element.dataset.deplace = 'oui';
    liste.dataset.glisse = 'oui';
    poignee.setPointerCapture(evenement.pointerId);
  };

  poignee.onpointermove = (evenement) => {
    if (!glisse) return;
    const dx = evenement.clientX - glisse.x0;
    const dy = evenement.clientY - glisse.y0;
    glisse.element.style.transform = 'translate(' + dx + 'px,' + dy + 'px) scale(1.06)';
    const cible = glisse.rects.findIndex((r) => evenement.clientX >= r.left
      && evenement.clientX <= r.right && evenement.clientY >= r.top && evenement.clientY <= r.bottom);
    if (cible === -1 || cible === glisse.cible) return;
    glisse.cible = cible;
    Array.from($('liste-photos').children).forEach((el, i) => {
      el.dataset.cible = i === cible && i !== glisse.rang ? 'oui' : 'non';
    });
  };

  const finir = () => {
    if (!glisse) return;
    const { rang: depuis, cible } = glisse;
    glisse.element.style.transform = '';
    glisse.element.dataset.deplace = 'non';
    $('liste-photos').dataset.glisse = 'non';
    glisse = null;
    if (cible !== depuis) deplacerPage(depuis, cible);
    else dessinerPhotos();
  };
  poignee.onpointerup = finir;
  poignee.onpointercancel = finir;
}

async function analyser() {
  if (!photosEnAttente.length) return;
  attendre('On lit ton cours…', 'Une trentaine de secondes, parfois plus si l’écriture est serrée.');
  const formulaire = new FormData();
  formulaire.append('session_id', etat.sessionId);
  formulaire.append('niveau', etat.niveau);
  formulaire.append('matiere', etat.matiere);
  photosEnAttente.forEach((photo, i) => formulaire.append('photos', photo.blob, 'page-' + i + '.jpg'));

  try {
    const resultat = await api('/api/analyse', { method: 'POST', body: formulaire });
    fermerAttente();

    const illisibles = (resultat.photos || []).filter((p) => !p.lisible);
    etat.remarquesPhotos = illisibles;

    const nouveaux = resultat.chapitres || [];
    if (!nouveaux.length) {
      message("Aucune page n’était lisible. Reprends-les en photo, plus près et bien à plat.", 'alerte', 8000);
      return;
    }
    // Fusion : on peut ajouter des pages plus tard sans perdre ce qui a été lu.
    const titresConnus = new Set(etat.chapitres.map((c) => c.titre));
    nouveaux.forEach((c) => { if (!titresConnus.has(c.titre)) etat.chapitres.push({ ...c, actif: true }); });

    if (!etat.matiere && resultat.matiere_detectee) {
      const trouvee = config.matieres.find((m) => m.nom === resultat.matiere_detectee);
      if (trouvee) etat.matiere = trouvee.cle;
    }
    // Les pages viennent grossir le cahier gardé sur l’appareil : c’est ce qui
    // permettra à chaque carte de montrer d’où elle vient.
    photosDuCours = photosDuCours.concat(
      photosEnAttente.map((photo, rang) => ({
        page: photosDuCours.length + rang,
        apercu: photo.apercu,
        image: photo.pleine || photo.apercu,
      }))
    );
    garderPages(etat.sessionId, photosDuCours);
    photosEnAttente = [];
    dessinerPhotos();
    etat.etape = 'perimetre';
    sauver();
    // Le cours vient d'être identifié : s'il double une séance existante, on
    // les réunit maintenant plutôt que de laisser deux jumelles s'installer.
    if (menageSessions() && etat) sauver();
    dessinerPerimetre();
    montrer('ecran-perimetre');
  } catch (e) { gererErreur(e); }
}

/* ------------------------------------------- étape 2 : le périmètre ------ */

function dessinerPerimetre() {
  const nombre = etat.chapitres.length;
  $('titre-perimetre').textContent = nombre > 1
    ? "J’ai repéré " + nombre + ' chapitres.'
    : "J’ai repéré 1 chapitre.";

  const alerte = $('alerte-photos');
  if (etat.remarquesPhotos && etat.remarquesPhotos.length) {
    alerte.innerHTML = '<b>Certaines pages sont mal passées :</b><ul>'
      + etat.remarquesPhotos.map((p) => '<li>Page ' + (p.index + 1) + ' — ' + echapper(p.remarque) + '</li>').join('')
      + '</ul>';
    alerte.hidden = false;
  } else {
    alerte.hidden = true;
  }

  const liste = $('liste-chapitres');
  liste.innerHTML = '';
  etat.chapitres.forEach((chapitre, index) => {
    const element = document.createElement('li');
    element.dataset.actif = chapitre.actif === false ? 'non' : 'oui';

    const entete = document.createElement('div');
    entete.className = 'chapitre-entete';

    const case_ = document.createElement('input');
    case_.type = 'checkbox';
    case_.checked = chapitre.actif !== false;
    case_.id = 'chapitre-' + index;
    case_.onchange = () => {
      etat.chapitres[index].actif = case_.checked;
      element.dataset.actif = case_.checked ? 'oui' : 'non';
      sauver();
    };

    const bloc = document.createElement('div');
    const titre = document.createElement('label');
    titre.className = 'chapitre-titre';
    titre.htmlFor = case_.id;
    titre.style.margin = '0';
    titre.style.color = 'inherit';
    titre.style.fontSize = '1rem';
    titre.textContent = chapitre.titre;

    const notions = document.createElement('p');
    notions.className = 'chapitre-notions';
    notions.textContent = (chapitre.notions || []).join(' · ');

    bloc.append(titre, notions);
    entete.append(case_, bloc);
    element.appendChild(entete);
    liste.appendChild(element);
  });
}

function chapitresRetenus() {
  return etat.chapitres
    .filter((c) => c.actif !== false)
    .map(({ titre, notions, transcription, photos }) => ({
      titre, notions: notions || [], transcription: transcription || '', photos: photos || [],
    }));
}

function confirmerPerimetre() {
  if (!chapitresRetenus().length) {
    message('Garde au moins un chapitre.', 'alerte');
    return;
  }
  tracer('perimetre_confirme', { chapitres: chapitresRetenus().length });
  etat.etape = 'carrefour';
  sauver();
  dessinerCarrefour();
  montrer('ecran-carrefour');
}

/* --------------------------------------------- étape 3 : le carrefour ---- */

const CHOIX = {
  revise: {
    titre: 'Je révise d’abord',
    detail: 'Une fiche sur tout le chapitre, à relire tranquillement. Ensuite tu te testes.',
  },
  teste: {
    titre: 'Je me teste tout de suite',
    detail: 'Le contrôle blanc maintenant, dans le vrai format. Tu verras vite où tu en es.',
  },
};

function dessinerCarrefour() {
  // Ordre tiré au sort et mémorisé : sans ça, on mesurerait surtout la position
  // du bouton, pas la préférence de l’élève.
  if (!etat.ordreCarrefour || etat.ordreCarrefour.length !== 2) {
    etat.ordreCarrefour = Math.random() < 0.5 ? ['revise', 'teste'] : ['teste', 'revise'];
    sauver();
  }
  const cases = $('cases-carrefour');
  cases.innerHTML = '';
  etat.ordreCarrefour.forEach((cle, position) => {
    const bouton = document.createElement('button');
    bouton.type = 'button';
    bouton.className = 'case-carrefour';
    bouton.innerHTML = '<strong></strong><span></span>';
    bouton.querySelector('strong').textContent = CHOIX[cle].titre;
    bouton.querySelector('span').textContent = CHOIX[cle].detail;
    bouton.onclick = () => choisirChemin(cle, position);
    cases.appendChild(bouton);
  });
}

function choisirChemin(chemin, position) {
  etat.chemin = chemin;
  sauver();
  tracer('chemin_choisi', { chemin, position });
  if (chemin === 'revise') demanderFicheGenerale();
  else lancerControle();
}

/* ---------------------------------------------------------- les fiches --- */

/* Une fiche remplace celle qu'elle refait, elle ne s'ajoute pas à côté.
 *
 * Repasser par « je révise d'abord » sur le même chapitre empilait une fiche
 * identique à chaque fois : dix lignes « Turismo y Madrid · 28 août » dans
 * l'archive, impossibles à distinguer, et un stockage qui gonflait pour rien.
 *
 * Un contrôle blanc, lui, se garde à chaque fois : le repasser est un nouvel
 * essai, et comparer les deux est justement l'intérêt.
 */
function garderFiche(type, contenu) {
  const titre = (contenu && contenu.titre) || '';
  const rang = etat.fiches.findIndex(
    (f) => f.type === type && ((f.contenu && f.contenu.titre) || '') === titre);
  const entree = { type, contenu, le: new Date().toISOString() };
  if (rang >= 0) etat.fiches[rang] = entree;
  else etat.fiches.push(entree);
}


async function demanderFicheGenerale() {
  attendre('On prépare ta fiche…', 'Elle reprend ton cours, dans ton ordre à toi.');
  try {
    const fiche = await envoyerJson('/api/fiche/generale', {
      session_id: etat.sessionId,
      niveau: etat.niveau,
      chapitres: chapitresRetenus(),
    });
    fermerAttente();
    garderFiche('generale', fiche);
    etat.etape = 'fiche';
    sauver();
    afficherFiche(fiche, 'generale');
  } catch (e) { gererErreur(e); }
}

async function demanderFicheCiblee() {
  if (!etat.notionsFragiles.length) {
    message('Rien à cibler pour l’instant : passe un contrôle blanc d’abord.');
    return;
  }
  attendre('On prépare ta fiche ciblée…', 'Uniquement ce que tu as raté.');
  try {
    const fiche = await envoyerJson('/api/fiche/ciblee', {
      session_id: etat.sessionId,
      niveau: etat.niveau,
      chapitres: chapitresRetenus(),
      notions: etat.notionsFragiles,
    });
    fermerAttente();
    garderFiche('ciblee', fiche);
    sauver();
    afficherFiche(fiche, 'ciblee');
  } catch (e) { gererErreur(e); }
}

/* La typographie française colle une espace insécable avant les doubles
 * ponctuations et à l'intérieur des guillemets. Sans elle, un « » se retrouve
 * seul en début de ligne, et un « ! » se détache de son mot.
 *
 * On ne fait que remplacer une espace existante : un texte espagnol, qui n'en
 * met pas avant sa ponctuation, n'est donc jamais touché.
 */
const INSECABLE = '\u202f';

function soignerTypographie(racine) {
  const parcours = document.createTreeWalker(racine, NodeFilter.SHOW_TEXT);
  let noeud;
  while ((noeud = parcours.nextNode())) {
    const avant = noeud.nodeValue;
    const apres = avant
      .replace(/ ([;:!?»])/g, INSECABLE + '$1')
      .replace(/« /g, '«' + INSECABLE);
    if (apres !== avant) noeud.nodeValue = apres;
  }
}

/* La fiche est un paquet de cartes qu’on fait glisser, pas une page qu’on
 * déroule. Une notion par écran : c’est ainsi que les élèves lisent déjà tout
 * le reste sur leur téléphone, et c’est ce qui empêche la fiche de ressembler
 * à un mur de texte.
 *
 * Chaque carte porte sa teinte et son chiffre. Le bouton « tout afficher »
 * remet le tout en colonne, pour qui préfère lire d’une traite.
 */

const TEINTES = 6;
let observateurCartes = null;

function carteFiche(teinte) {
  const carte = document.createElement('article');
  carte.className = 'carte-fiche';
  carte.dataset.teinte = String(teinte % TEINTES);
  carte.tabIndex = 0;
  // Tête fixe, corps qui défile, pied épinglé : la phrase à retenir reste
  // visible même quand la carte est trop longue pour l’écran.
  carte.innerHTML = '<div class="carte-tete"></div><div class="carte-corps"></div>';
  return carte;
}

function tete(carte) { return carte.querySelector('.carte-tete'); }
function corps(carte) { return carte.querySelector('.carte-corps'); }

function chiffreGeant(texte) {
  const chiffre = document.createElement('span');
  chiffre.className = 'carte-chiffre';
  chiffre.setAttribute('aria-hidden', 'true');
  chiffre.textContent = texte;
  return chiffre;
}

/* Une section entière ne tient pas sur un écran de téléphone : on l’a mesuré,
 * quatre points denses en laissent un ou deux visibles. Elle est donc découpée
 * en cartes d’au plus trois points, et sa phrase à retenir occupe une carte à
 * elle seule — c’est le point d’arrivée de la notion, pas une note de bas de page.
 *
 * Les rubans, eux, comptent les notions et non les cartes : l’élève veut savoir
 * qu’il en est à la troisième idée sur six, pas à la quatorzième carte sur vingt.
 */
const POINTS_PAR_CARTE = 3;

function decouper(points) {
  const groupes = Math.max(1, Math.ceil(points.length / POINTS_PAR_CARTE));
  const taille = Math.ceil(points.length / groupes);
  const morceaux = [];
  for (let i = 0; i < points.length; i += taille) morceaux.push(points.slice(i, i + taille));
  return morceaux;
}

/* Chaque carte porte un bout du cahier dont elle vient. C’est le seul élément
 * que personne d’autre ne peut fabriquer : la preuve, sous les yeux de l’élève,
 * que la fiche sort de SES pages et pas d’un manuel. */
function provenance(pages) {
  const disponibles = (pages || []).filter((n) => photosDuCours[n]);
  if (!disponibles.length) return null;

  const bloc = document.createElement('button');
  bloc.type = 'button';
  bloc.className = 'provenance';

  const vignette = document.createElement('img');
  vignette.className = 'provenance-vignette';
  vignette.src = photosDuCours[disponibles[0]].apercu;
  vignette.alt = '';

  const texte = document.createElement('span');
  texte.className = 'provenance-texte';
  texte.textContent = disponibles.length > 1
    ? 'ton cahier · pages ' + disponibles.map((n) => n + 1).join(' et ')
    : 'ton cahier · page ' + (disponibles[0] + 1);

  bloc.append(vignette, texte);
  bloc.onclick = (evenement) => { evenement.stopPropagation(); ouvrirCahier(disponibles, 0); };
  return bloc;
}

let cahierOuvert = { pages: [], rang: 0 };

function ouvrirCahier(pages, rang) {
  cahierOuvert = { pages, rang };
  dessinerCahier();
  $('visionneuse').hidden = false;
  document.body.style.overflow = 'hidden';
}

function dessinerCahier() {
  const { pages, rang } = cahierOuvert;
  const numero = pages[rang];
  $('page-cahier').src = photosDuCours[numero].image;
  $('legende-page').textContent = 'Ton cahier · page ' + (numero + 1);
  $('page-precedente').hidden = rang === 0;
  $('page-suivante').hidden = rang >= pages.length - 1;
}

function fermerCahier() {
  $('visionneuse').hidden = true;
  document.body.style.overflow = '';
}

/* La carte « à retenir » est la seule de la fiche qui demande quelque chose.
 *
 * Cacher la réponse et essayer de se souvenir avant de vérifier est le geste
 * que tout élève fait avec sa main sur son cahier, et c’est la méthode de
 * révision la plus efficace qu’on connaisse. Un écran sait le faire mieux
 * qu’une feuille : les traits de surligneur sont là, les mots pas encore.
 *
 * Ce n’est pas une note. L’élève juge lui-même, en deux boutons, et ce qu’il
 * met de côté alimente le contrôle blanc — la fiche cesse d’être un cul-de-sac.
 */
function carteRetenir(section, rang, masqueForce = false) {
  const carte = carteFiche(rang);
  carte.classList.add('carte-retenir');

  const etiquette = document.createElement('p');
  etiquette.className = 'carte-etiquette';
  etiquette.textContent = 'Notion ' + (rang + 1) + ' · à retenir';

  const retenir = document.createElement('p');
  retenir.className = 'retenir';
  retenir.dataset.masque = 'oui';
  const trait = document.createElement('mark');
  trait.textContent = section.a_retenir;
  retenir.appendChild(trait);

  const invite = document.createElement('button');
  invite.type = 'button';
  invite.className = 'reveler';
  invite.innerHTML = '<span class="reveler-question">Tu te souviens ?</span>'
    + '<span class="reveler-geste">touche pour voir</span>';

  const marques = document.createElement('div');
  marques.className = 'marques';
  marques.hidden = true;
  [['acquis', 'C’est bon'], ['revoir', 'Pas encore']].forEach(([valeur, libelle]) => {
    const bouton = document.createElement('button');
    bouton.type = 'button';
    bouton.className = 'bouton-marque';
    bouton.dataset.marque = valeur;
    bouton.textContent = libelle;
    bouton.onclick = (evenement) => {
      evenement.stopPropagation();
      marquerNotion(section.titre, valeur);
      Array.from(marques.children).forEach((b) => {
        b.dataset.choisi = b.dataset.marque === valeur ? 'oui' : 'non';
      });
    };
    marques.appendChild(bouton);
  });

  const reveler = () => {
    if (retenir.dataset.masque !== 'oui') return;
    retenir.dataset.masque = 'non';
    invite.hidden = true;
    marques.hidden = false;
    // Un tic très bref : la révélation se sent autant qu’elle se voit.
    if (navigator.vibrate) navigator.vibrate(12);
  };
  invite.onclick = (evenement) => { evenement.stopPropagation(); reveler(); };
  carte.onclick = reveler;

  const groupe = document.createElement('div');
  groupe.className = 'bloc-retenir';
  groupe.append(etiquette, retenir, invite, marques);
  corps(carte).appendChild(groupe);

  const trace = provenance(section.pages);
  if (trace) carte.appendChild(trace);

  // Une notion déjà jugée reste jugée quand on revient sur la fiche — sauf au
  // second tour, dont tout l’intérêt est de la remasquer.
  const deja = masqueForce ? null : (etat.marques || {})[section.titre];
  if (deja) {
    reveler();
    Array.from(marques.children).forEach((b) => {
      b.dataset.choisi = b.dataset.marque === deja ? 'oui' : 'non';
    });
  }

  carteRetenir.derniere = carte;
  return carte;
}

function marquerNotion(titre, valeur) {
  etat.marques = etat.marques || {};
  etat.marques[titre] = valeur;
  sauver();
  majRubansMarques();
  majCarteFin();
  if (!$('vue-ensemble').hidden) dessinerVueEnsemble(groupesCourants);
}

function notionsARevoir() {
  const marques = etat.marques || {};
  return Object.keys(marques).filter((titre) => marques[titre] === 'revoir');
}

function majRubansMarques() {
  const marques = etat.marques || {};
  Array.from($('rubans').children).forEach((ruban) => {
    ruban.dataset.revoir = marques[ruban.dataset.titre] === 'revoir' ? 'oui' : 'non';
  });
}

/* La dernière carte reflète ce que l’élève vient de mettre de côté. */
function majCarteFin() {
  const carte = $('paquet').querySelector('.carte-fin');
  if (!carte) return;
  const aRevoir = notionsARevoir();
  const titre = carte.querySelector('h3');
  const mot = carte.querySelector('.mot-fin');
  const bouton = carte.querySelector('#bouton-apres-fiche');

  const second = carte.querySelector('.bouton-second-tour');
  if (aRevoir.length) {
    titre.textContent = aRevoir.length > 1
      ? aRevoir.length + ' notions à revoir.'
      : '1 notion à revoir.';
    mot.textContent = 'Refais-en un tour maintenant : c’est en les reposant qu’elles rentrent.';
    second.hidden = false;
    second.textContent = aRevoir.length > 1
      ? 'Refaire un tour sur ces ' + aRevoir.length + ' notions'
      : 'Refaire un tour sur cette notion';
    second.onclick = () => afficherFiche(ficheCourante.fiche, ficheCourante.type,
                                         { notions: notionsARevoir() });
    bouton.textContent = aRevoir.length > 1
      ? 'Me tester sur ces ' + aRevoir.length + ' notions'
      : 'Me tester sur cette notion';
    bouton.onclick = () => lancerControle(aRevoir);
  } else {
    second.hidden = true;
    titre.textContent = carte.dataset.titreParDefaut;
    mot.textContent = carte.dataset.motParDefaut;
    bouton.textContent = carte.dataset.boutonParDefaut;
    bouton.onclick = () => lancerControle(carte.dataset.cible === 'oui' ? notionsFragiles() : []);
  }
}

function afficherFiche(fiche, type, options = {}) {
  // Le second tour ne rejoue que les notions mises de côté, et rien d’autre :
  // ni les mots, ni les pièges, ni les notions déjà tenues.
  const secondTour = Boolean(options.notions && options.notions.length);
  ficheCourante = { fiche, type };

  $('etiquette-fiche').textContent = secondTour ? 'Second tour'
    : (type === 'ciblee' ? 'Fiche ciblée' : 'Fiche générale');
  $('titre-fiche').textContent = secondTour
    ? 'Ce qui ne tenait pas encore'
    : (fiche.titre || 'Ta fiche');

  const toutes = fiche.sections || [];
  const sections = secondTour
    ? toutes.filter((s) => options.notions.includes(s.titre))
    : toutes;
  const definitions = secondTour ? [] : (fiche.definitions || []);
  const pieges = secondTour ? [] : (fiche.pieges || []);
  const masqueForce = secondTour;

  const souffle = [];
  if (!secondTour && fiche.duree_lecture_minutes) souffle.push(fiche.duree_lecture_minutes + ' min');
  souffle.push(sections.length + (sections.length > 1 ? ' notions' : ' notion'));
  if (pieges.length) souffle.push(pieges.length + (pieges.length > 1 ? ' pièges' : ' piège'));
  $('fiche-souffle').textContent = souffle.join(' · ')
    + (secondTour ? ' · à revoir' : ' · fais glisser');

  const paquet = $('paquet');
  paquet.innerHTML = '';
  const groupes = [];
  let index = 0;

  const ajouter = (carte) => {
    carte.dataset.index = String(index);
    carte.dataset.ruban = String(groupes.length - 1);
    paquet.appendChild(carte);
    index += 1;
  };

  sections.forEach((section, rang) => {
    groupes.push(section.titre);
    const morceaux = decouper(section.points || []);

    morceaux.forEach((points, morceau) => {
      const carte = carteFiche(rang);
      const titre = document.createElement('h3');
      titre.textContent = section.titre;

      const liste = document.createElement('ul');
      liste.className = 'points';
      points.forEach((point) => {
        const li = document.createElement('li');
        li.textContent = point;
        liste.appendChild(li);
      });

      tete(carte).append(chiffreGeant(String(rang + 1)), titre);
      if (morceaux.length > 1) {
        const suite = document.createElement('p');
        suite.className = 'carte-suite';
        suite.textContent = (morceau + 1) + ' sur ' + morceaux.length;
        tete(carte).appendChild(suite);
      }
      corps(carte).appendChild(liste);
      const trace = provenance(section.pages);
      if (trace) carte.appendChild(trace);
      ajouter(carte);
    });

    if (section.a_retenir) {
      ajouter(carteRetenir(section, rang, masqueForce));
    }
  });

  if (definitions.length) {
    groupes.push('Les mots');
    decouper(definitions).forEach((lot, morceau, tous) => {
      const carte = carteFiche(sections.length);
      carte.classList.add('carte-mots');
      const titre = document.createElement('h3');
      titre.textContent = 'Les mots à connaître';
      const liste = document.createElement('dl');
      lot.forEach((d) => {
        const terme = document.createElement('dt');
        terme.textContent = d.terme;
        const definition = document.createElement('dd');
        definition.textContent = d.definition;
        liste.append(terme, definition);
      });
      tete(carte).append(chiffreGeant('Aa'), titre);
      if (tous.length > 1) {
        const suite = document.createElement('p');
        suite.className = 'carte-suite';
        suite.textContent = (morceau + 1) + ' sur ' + tous.length;
        tete(carte).appendChild(suite);
      }
      corps(carte).appendChild(liste);
      ajouter(carte);
    });
  }

  if (pieges.length) {
    groupes.push('Les pièges');
    decouper(pieges).forEach((lot, morceau, tous) => {
      const carte = carteFiche(sections.length + 1);
      carte.classList.add('carte-pieges');
      const titre = document.createElement('h3');
      titre.textContent = pieges.length > 1 ? 'Les pièges' : 'Le piège';
      const liste = document.createElement('ul');
      liste.className = 'liste-pieges';
      lot.forEach((piege) => {
        const li = document.createElement('li');
        li.textContent = piege;
        liste.appendChild(li);
      });
      tete(carte).append(chiffreGeant('!'), titre);
      if (tous.length > 1) {
        const suite = document.createElement('p');
        suite.className = 'carte-suite';
        suite.textContent = (morceau + 1) + ' sur ' + tous.length;
        tete(carte).appendChild(suite);
      }
      corps(carte).appendChild(liste);
      ajouter(carte);
    });
  }

  groupes.push('C’est tout');
  const finale = carteFiche(sections.length + 2);
  finale.classList.add('carte-fin');
  const titreFin = document.createElement('h3');
  titreFin.textContent = type === 'ciblee' ? 'Tu as relu tes points faibles.' : 'Tu as tout lu.';
  const motFin = document.createElement('p');
  motFin.className = 'mot-fin';
  motFin.textContent = type === 'ciblee'
    ? 'Le moment de vérifier que ça tient : refais un contrôle sur ces notions-là.'
    : 'Le seul moyen de savoir ce qui est vraiment acquis, c’est de te tester.';

  const suivant = document.createElement('button');
  suivant.type = 'button';
  suivant.className = 'principal';
  suivant.id = 'bouton-apres-fiche';
  suivant.textContent = type === 'ciblee' ? 'Me retester sur ces notions' : 'Passer au contrôle blanc';
  suivant.onclick = () => lancerControle(type === 'ciblee' ? notionsFragiles() : []);
  finale.dataset.titreParDefaut = titreFin.textContent;
  finale.dataset.motParDefaut = motFin.textContent;
  finale.dataset.boutonParDefaut = suivant.textContent;
  finale.dataset.cible = type === 'ciblee' ? 'oui' : 'non';

  const plusTard = document.createElement('button');
  plusTard.type = 'button';
  plusTard.className = 'discret';
  plusTard.id = 'bouton-fiche-accueil';
  plusTard.textContent = 'Plus tard, garder ma session';
  plusTard.onclick = reprendre;

  // Le second tour passe avant le contrôle : rejouer ce qui n’a pas tenu coûte
  // quelques secondes, là où un contrôle blanc coûte de l’argent et du temps.
  const secondTourBouton = document.createElement('button');
  secondTourBouton.type = 'button';
  secondTourBouton.className = 'principal bouton-second-tour';
  secondTourBouton.hidden = true;

  suivant.classList.remove('principal');
  suivant.classList.add('secondaire');

  tete(finale).appendChild(chiffreGeant('✓'));
  corps(finale).append(titreFin, motFin, secondTourBouton, suivant, plusTard);
  ajouter(finale);

  groupesCourants = groupes;
  dessinerRubans(groupes);
  basculerVue(false);
  soignerTypographie(paquet);
  const titreFiche = fiche.titre || 'fiche';
  // Le second tour est un paquet court et neuf : y proposer une reprise n’a
  // pas de sens, et la position qu’on y prend ne doit pas écraser l’autre.
  if (secondTour) $('reprise-lecture').hidden = true;
  else proposerReprise(titreFiche);
  paquet.dataset.fiche = titreFiche;
  paquet.dataset.tour = secondTour ? 'second' : 'premier';
  paquet.scrollLeft = 0;
  suivreCartes();
  majRubansMarques();
  majCarteFin();
  montrer('ecran-fiche');
}

/* La fiche vue de dessus : les cartes en petit, avec leur couleur, leur numéro
 * et leur état. Avec vingt-trois cartes, retrouver « la frase exclamativa » à
 * la main demande douze glissements ; ici, un regard et une touche.
 */
function dessinerVueEnsemble(groupes) {
  const vue = $('vue-ensemble');
  vue.innerHTML = '';
  const marques = etat.marques || {};

  groupes.forEach((titre, index) => {
    const tuile = document.createElement('button');
    tuile.type = 'button';
    tuile.className = 'tuile';
    tuile.dataset.teinte = String(index % TEINTES);
    tuile.dataset.marque = marques[titre] || 'aucune';

    const numero = document.createElement('span');
    numero.className = 'tuile-numero';
    numero.textContent = index < groupes.length - 1 ? String(index + 1) : '✓';

    const nom = document.createElement('span');
    nom.className = 'tuile-titre';
    nom.textContent = titre;

    const etatNotion = document.createElement('span');
    etatNotion.className = 'tuile-etat';
    etatNotion.textContent = marques[titre] === 'revoir' ? 'à revoir'
      : (marques[titre] === 'acquis' ? 'ça tient' : '');

    tuile.append(numero, nom, etatNotion);
    tuile.onclick = () => {
      const premiere = Array.from($('paquet').children)
        .findIndex((c) => Number(c.dataset.ruban) === index);
      basculerVue(false);
      // Le paquet vient d’être ré-affiché : viser avant que la mise en page
      // soit faite envoie sur la mauvaise carte.
      if (premiere >= 0) requestAnimationFrame(() => allerACarte(premiere));
    };
    vue.appendChild(tuile);
  });
}

function basculerVue(ouvrir) {
  const ouverte = ouvrir === undefined ? $('vue-ensemble').hidden : ouvrir;
  $('vue-ensemble').hidden = !ouverte;
  $('paquet').hidden = ouverte;
  $('bouton-vue').dataset.ouvert = ouverte ? 'oui' : 'non';
  if (ouverte) dessinerVueEnsemble(groupesCourants);
}

let groupesCourants = [];
let ficheCourante = { fiche: null, type: 'generale' };

/* Les rubans disent où on en est et permettent de sauter d’une carte à l’autre. */
function dessinerRubans(titres) {
  const rubans = $('rubans');
  rubans.innerHTML = '';
  titres.forEach((titre, index) => {
    const ruban = document.createElement('button');
    ruban.type = 'button';
    ruban.className = 'ruban';
    ruban.setAttribute('role', 'tab');
    ruban.dataset.titre = titre;
    ruban.setAttribute('aria-label', 'Notion ' + (index + 1) + ' — ' + titre);
    ruban.onclick = () => {
      const premiere = Array.from($('paquet').children)
        .findIndex((c) => Number(c.dataset.ruban) === index);
      if (premiere >= 0) allerACarte(premiere);
    };
    rubans.appendChild(ruban);
  });
}

function allerACarte(index) {
  const carte = $('paquet').children[index];
  if (carte) carte.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
}

/* L’élève revient sur plusieurs jours : on retient où il s’est arrêté et on
 * le lui propose, sans l’y renvoyer d’office — retomber au milieu d’une fiche
 * sans l’avoir demandé est déroutant. */
function proposerReprise(titreFiche) {
  const reprise = $('reprise-lecture');
  const memoire = etat.lectureFiche || {};
  const carte = memoire.titre === titreFiche ? memoire.carte : 0;
  const notion = memoire.titre === titreFiche ? memoire.notion : '';

  if (!carte || carte < 2) { reprise.hidden = true; return; }
  reprise.hidden = false;
  reprise.textContent = 'Reprendre à « ' + notion + ' »';
  reprise.onclick = () => { allerACarte(carte); reprise.hidden = true; };
}

function retenirPosition(titreFiche, carte) {
  // Reprendre à la carte de fin n’aurait aucun intérêt : on ne la retient pas.
  if (carte.classList.contains('carte-fin')) return;
  if ($('paquet').dataset.tour === 'second') return;
  const ruban = $('rubans').children[Number(carte.dataset.ruban)];
  etat.lectureFiche = {
    titre: titreFiche,
    carte: Number(carte.dataset.index),
    notion: ruban ? ruban.dataset.titre : '',
  };
  sauver();
}

function suivreCartes() {
  if (observateurCartes) observateurCartes.disconnect();
  const paquet = $('paquet');
  const rubans = $('rubans');

  observateurCartes = new IntersectionObserver((entrees) => {
    entrees.forEach((entree) => {
      if (!entree.isIntersecting) return;
      const groupe = Number(entree.target.dataset.ruban);
      Array.from(rubans.children).forEach((ruban, i) => {
        ruban.dataset.etat = i < groupe ? 'passe' : (i === groupe ? 'ici' : 'a-venir');
      });
      majRubansMarques();
      retenirPosition(paquet.dataset.fiche, entree.target);
    });
  }, { root: paquet, threshold: 0.6 });

  Array.from(paquet.children).forEach((carte) => observateurCartes.observe(carte));

  // Les flèches du clavier font aussi défiler le paquet.
  paquet.onkeydown = (evenement) => {
    const cartes = Array.from(paquet.children);
    const vue = cartes.findIndex((c) => {
      const boite = c.getBoundingClientRect();
      return boite.left >= -4 && boite.left < paquet.clientWidth / 2;
    });
    if (evenement.key === 'ArrowRight') { allerACarte(vue + 1); evenement.preventDefault(); }
    if (evenement.key === 'ArrowLeft') { allerACarte(Math.max(0, vue - 1)); evenement.preventDefault(); }
  };
}

/* --------------------------------------------- étape 4 : contrôle blanc -- */

async function lancerControle(notionsCiblees = []) {
  const notions = notionsCiblees;
  const dejaPoses = [];
  etat.controles.forEach((c) => (c.questions || []).forEach((q) => dejaPoses.push(q.enonce)));

  attendre('On écrit ton contrôle…', 'Au format de la matière, à partir de ton cours.');
  try {
    const controle = await envoyerJson('/api/controle', {
      session_id: etat.sessionId,
      niveau: etat.niveau,
      matiere: etat.matiere,
      chapitres: chapitresRetenus(),
      notions_ciblees: notions,
      enonces_deja_poses: dejaPoses,
    });
    fermerAttente();
    controleEnCours = {
      ...controle,
      index: 0,
      reponses: {},
      signalees: new Set(),
      debut: Date.now(),
      finPrevue: Date.now() + controle.duree_minutes * 60000,
    };
    etat.etape = 'controle';
    sauver();
    dessinerQuestion();
    montrer('ecran-controle');
    demarrerChrono();
  } catch (e) { gererErreur(e); }
}

function dessinerQuestion() {
  const question = controleEnCours.questions[controleEnCours.index];
  const total = controleEnCours.questions.length;

  $('progression-controle').textContent = 'Question ' + (controleEnCours.index + 1) + ' sur ' + total;
  $('jauge-remplie').style.width = ((controleEnCours.index) / total * 100) + '%';
  $('partie-question').textContent = question.partie || '';

  const doc = $('document-question');
  doc.textContent = question.document || '';
  doc.hidden = !question.document;

  $('enonce-question').textContent = question.enonce;
  $('champ-reponse').value = '';
  $('champ-reponse').focus({ preventScroll: true });

  const signaler = $('bouton-signaler');
  signaler.dataset.signalee = controleEnCours.signalees.has(question.numero) ? 'oui' : 'non';
  signaler.textContent = controleEnCours.signalees.has(question.numero)
    ? 'Signalée — merci'
    : 'Cette question me semble fausse';

  soignerTypographie($('enonce-question'));
  soignerTypographie($('document-question'));

  $('bouton-question-suivante').textContent = controleEnCours.index === total - 1
    ? 'Terminer le contrôle'
    : 'Valider et continuer';
}

function questionSuivante() {
  const question = controleEnCours.questions[controleEnCours.index];
  controleEnCours.reponses[question.numero] = $('champ-reponse').value;
  controleEnCours.index += 1;
  if (controleEnCours.index >= controleEnCours.questions.length) {
    terminerControle();
    return;
  }
  dessinerQuestion();
}

function demarrerChrono() {
  clearInterval(minuteur);
  const afficher = () => {
    const restant = Math.max(0, controleEnCours.finPrevue - Date.now());
    const minutes = Math.floor(restant / 60000);
    const secondes = Math.floor((restant % 60000) / 1000);
    const chrono = $('chrono');
    chrono.textContent = String(minutes).padStart(2, '0') + ':' + String(secondes).padStart(2, '0');
    chrono.dataset.urgent = restant < 120000 ? 'oui' : 'non';
    if (restant <= 0) {
      clearInterval(minuteur);
      message("Le temps est écoulé, comme au contrôle. On corrige ce que tu as écrit.", 'alerte', 6000);
      terminerControle();
    }
  };
  afficher();
  minuteur = setInterval(afficher, 1000);
}

async function terminerControle() {
  clearInterval(minuteur);
  // La question affichée compte, même si l’élève n’a pas eu le temps de valider.
  const courante = controleEnCours.questions[controleEnCours.index];
  if (courante && controleEnCours.reponses[courante.numero] === undefined) {
    controleEnCours.reponses[courante.numero] = $('champ-reponse').value;
  }

  attendre('On corrige ta copie…', 'Question par question, avec le renvoi à ton cours.');
  try {
    const correction = await envoyerJson('/api/correction', {
      session_id: etat.sessionId,
      controle_id: controleEnCours.controle_id,
      niveau: etat.niveau,
      chapitres: chapitresRetenus(),
      reponses: Object.entries(controleEnCours.reponses).map(([numero, texte]) => ({
        numero: Number(numero), texte, secondes: 0,
      })),
      numeros_signales: Array.from(controleEnCours.signalees),
    });
    fermerAttente();

    etat.controles.push({
      controle_id: controleEnCours.controle_id,
      titre: controleEnCours.titre,
      questions: controleEnCours.questions,
      reponses: controleEnCours.reponses,
      correction,
      le: new Date().toISOString(),
    });
    etat.notionsFragiles = correction.notions_fragiles || [];
    etat.etape = 'correction';
    sauver();
    afficherCorrection(correction);
  } catch (e) { gererErreur(e); }
}

/* ------------------------------------------------ étape 5 : correction --- */

const LIBELLES_STATUT = {
  acquis: 'Acquis',
  partiel: 'Presque',
  a_revoir: 'À revoir',
};

function notionsFragiles() {
  return (etat.notionsFragiles || []).map((n) => n.notion);
}

function afficherCorrection(correction) {
  $('mot-de-fin').textContent = correction.mot_de_fin || '';

  const fragiles = correction.notions_fragiles || [];
  $('bloc-fragiles').hidden = fragiles.length === 0;
  const liste = $('liste-fragiles');
  liste.innerHTML = '';
  fragiles.forEach((n) => {
    const li = document.createElement('li');
    const titre = document.createElement('b');
    titre.textContent = n.notion;
    const pourquoi = document.createElement('span');
    pourquoi.textContent = n.pourquoi || '';
    li.append(titre, pourquoi);
    liste.appendChild(li);
  });

  /* Une correction dépliée, c'était huit écrans et demi de défilement : neuf
   * questions, chacune avec ce qui va, l'erreur, ce qui manquait, où relire et
   * la réponse attendue. Or la première question qu'un élève se pose est
   * « lesquelles j'ai ratées ? », pas « qu'est-ce que j'ai écrit à la 7 ».
   *
   * Chaque question tient donc en une ligne — son numéro, son état, son énoncé —
   * et s'ouvre si on la demande. Aucune ne s'ouvre d'elle-même : en ouvrir une
   * coûtait un demi-écran et choisissait à la place de l'élève, alors que le
   * bloc des notions fragiles, juste au-dessus, lui a déjà dit où regarder. */
  const corps = $('corps-correction');
  corps.innerHTML = '';

  (correction.reponses || []).forEach((ligne) => {
    const carte = document.createElement('details');
    carte.className = 'carte-correction';
    carte.dataset.statut = ligne.statut;

    const tete = document.createElement('summary');
    tete.className = 'tete-correction';

    const numero = document.createElement('span');
    numero.className = 'numero-correction';
    numero.textContent = String(ligne.numero);

    // L'état se glisse en tête de l'énoncé : sur sa propre ligne, il coûtait
    // 22 px par question sans rien dire que la couleur du numéro ne dise déjà.
    const etiquette = document.createElement('span');
    etiquette.className = 'etiquette-statut';
    etiquette.textContent = ligne.signalee ? 'Signalée' : (LIBELLES_STATUT[ligne.statut] || '');

    const enonce = document.createElement('p');
    enonce.className = 'question-correction';
    enonce.append(etiquette, document.createTextNode(ligne.enonce || ''));

    tete.append(numero, enonce);
    carte.appendChild(tete);

    if (ligne.ce_qui_va) carte.appendChild(blocTexte('Ce qui va', ligne.ce_qui_va));
    // En maths et en sciences, l’élève se trompe plus souvent qu’il n’oublie :
    // nommer l’erreur vaut mieux que lister ce qui manquait.
    if (ligne.erreur_reperee) {
      carte.appendChild(blocTexte('L’erreur', ligne.erreur_reperee, 'erreur'));
    }
    if ((ligne.ce_qui_manquait || []).length) {
      carte.appendChild(blocListe('Ce qui manquait', ligne.ce_qui_manquait));
    }
    if (ligne.ou_dans_ton_cours) {
      carte.appendChild(blocTexte('Où le relire dans ton cours', ligne.ou_dans_ton_cours, 'repere'));
    }

    const details = document.createElement('details');
    details.className = 'detail-reponse';
    const resume = document.createElement('summary');
    resume.textContent = 'Voir la réponse attendue et ce que tu as écrit';
    const attendue = document.createElement('p');
    attendue.textContent = ligne.reponse_attendue || '';
    const tienne = document.createElement('p');
    tienne.className = 'ta-reponse';
    tienne.textContent = ligne.ta_reponse ? '« ' + ligne.ta_reponse + ' »' : '(tu n’as rien écrit)';
    details.append(resume, attendue, tienne);
    carte.appendChild(details);

    const signaler = document.createElement('button');
    signaler.type = 'button';
    signaler.className = 'signalement';
    signaler.textContent = ligne.signalee ? 'Signalée — merci' : 'Cette question me semble fausse';
    signaler.dataset.signalee = ligne.signalee ? 'oui' : 'non';
    signaler.onclick = () => ouvrirSignalement(ligne.numero, ligne.enonce, signaler);
    carte.appendChild(signaler);

    corps.appendChild(carte);
  });

  soignerTypographie(corps);
  soignerTypographie($('bloc-fragiles'));
  $('bouton-fiche-ciblee').hidden = fragiles.length === 0;
  $('bouton-second-controle').hidden = fragiles.length === 0;
  montrer('ecran-correction');
}

function blocTexte(titre, texte, classe = '') {
  const bloc = document.createElement('div');
  bloc.className = 'bloc-correction';
  const entete = document.createElement('p');
  entete.className = 'bloc-titre';
  entete.textContent = titre;
  const corps = document.createElement('p');
  if (classe) corps.className = classe;
  corps.textContent = texte;
  bloc.append(entete, corps);
  return bloc;
}

function blocListe(titre, elements) {
  const bloc = document.createElement('div');
  bloc.className = 'bloc-correction';
  const entete = document.createElement('p');
  entete.className = 'bloc-titre';
  entete.textContent = titre;
  const liste = document.createElement('ul');
  elements.forEach((element) => {
    const li = document.createElement('li');
    li.textContent = element;
    liste.appendChild(li);
  });
  bloc.append(entete, liste);
  return bloc;
}

/* --------------------------------- « cette question me semble fausse » --- */

let signalementEnCours = null;

function ouvrirSignalement(numero, enonce, bouton) {
  signalementEnCours = { numero, enonce, bouton };
  $('motif-signalement').value = '';
  const dialogue = $('dialogue-signalement');
  if (typeof dialogue.showModal === 'function') dialogue.showModal();
  else envoyerSignalement('');
}

async function envoyerSignalement(motif) {
  if (!signalementEnCours) return;
  const { numero, enonce, bouton } = signalementEnCours;
  const controleId = controleEnCours ? controleEnCours.controle_id
    : (etat.controles.length ? etat.controles[etat.controles.length - 1].controle_id : '');

  if (controleEnCours) controleEnCours.signalees.add(numero);
  if (bouton) {
    bouton.textContent = 'Signalée — merci';
    bouton.dataset.signalee = 'oui';
  } else {
    const signaler = $('bouton-signaler');
    signaler.textContent = 'Signalée — merci';
    signaler.dataset.signalee = 'oui';
  }

  try {
    const reponse = await envoyerJson('/api/signalement', {
      session_id: etat.sessionId,
      controle_id: controleId,
      numero,
      enonce: enonce || '',
      motif: motif || '',
    });
    message(reponse.message);
  } catch (e) {
    message('Signalement noté sur ton téléphone, mais pas envoyé. Ce n’est pas grave.');
  }
  signalementEnCours = null;
}

/* --------------------------------------------- reprise / tableau de bord - */

function dessinerReprise() {
  const jours = joursAvantControle();
  const rappel = $('rappel-date');
  const matiere = (config.matieres.find((m) => m.cle === etat.matiere) || {}).nom || 'Ton contrôle';
  if (jours === null) {
    rappel.textContent = matiere + ' — pense à indiquer la date du contrôle.';
  } else if (jours > 1) {
    rappel.innerHTML = '<b>' + matiere + '</b> dans ' + jours + ' jours. '
      + 'Le meilleur moment pour te retester, c’est maintenant, pas la veille.';
  } else if (jours === 1) {
    rappel.innerHTML = '<b>' + matiere + '</b>, c’est demain. Un dernier contrôle blanc sur tes notions fragiles ?';
  } else if (jours === 0) {
    rappel.innerHTML = '<b>' + matiere + '</b>, c’est aujourd’hui. Relis ta fiche ciblée, rien de plus.';
  } else {
    rappel.innerHTML = '<b>' + matiere + '</b> est passé. Tu peux commencer un nouveau cours.';
  }

  const fichesCiblees = etat.fiches.filter((f) => f.type === 'ciblee').length;
  const etapes = [
    { fait: etat.chapitres.length > 0, texte: etat.chapitres.length + ' chapitre(s) analysé(s)' },
    { fait: etat.fiches.some((f) => f.type === 'generale'), texte: 'Fiche générale lue' },
    { fait: etat.controles.length > 0, texte: etat.controles.length + ' contrôle(s) blanc(s) passé(s)' },
    { fait: fichesCiblees > 0, texte: fichesCiblees + ' fiche(s) ciblée(s)' },
  ];
  const liste = $('liste-etapes');
  liste.innerHTML = '';
  etapes.forEach((etape) => {
    const li = document.createElement('li');
    li.dataset.fait = etape.fait ? 'oui' : 'non';
    const marqueur = document.createElement('span');
    marqueur.className = 'marqueur';
    marqueur.textContent = etape.fait ? '✓' : '○';
    const texte = document.createElement('span');
    texte.textContent = etape.texte;
    li.append(marqueur, texte);
    liste.appendChild(li);
  });

  $('texte-lien').textContent = etat.lien || (location.origin + '/?s=' + etat.sessionId);

  const bouton = $('bouton-continuer-session');
  if (etat.notionsFragiles.length) {
    bouton.textContent = 'Me retester sur mes notions fragiles';
    bouton.onclick = () => lancerControle(notionsFragiles());
  } else if (etat.chapitres.length) {
    bouton.textContent = 'Passer un contrôle blanc';
    bouton.onclick = () => lancerControle();
  } else {
    bouton.textContent = 'Photographier mon cours';
    bouton.onclick = () => montrer('ecran-photos');
  }
}

async function copierLien() {
  const lien = $('texte-lien').textContent;
  try {
    await navigator.clipboard.writeText(lien);
    message('Lien copié. Envoie-le-toi par message, tu le retrouveras demain.');
  } catch (e) {
    message('Sélectionne le lien et copie-le à la main.');
  }
}

/* ------------------------------------------------------------- divers --- */

function echapper(texte) {
  const noeud = document.createElement('div');
  noeud.textContent = texte == null ? '' : String(texte);
  return noeud.innerHTML;
}

function dateParDefaut() {
  const dans7jours = new Date(Date.now() + 7 * 86400000);
  return dans7jours.toISOString().slice(0, 10);
}

/* ------------------------------------------------------------ câblage --- */

document.addEventListener('DOMContentLoaded', () => {
  // Ici et pas dans initialiser(), qui sort par le haut quand l'élève arrive
  // par un lien de reprise : la lumière vaut pour tous les écrans, pas
  // seulement pour la page d'accueil.
  armerLumiere();

  $('champ-date').value = dateParDefaut();
  $('champ-date').min = new Date().toISOString().slice(0, 10);

  $('bouton-commencer').onclick = () => demarrerSession();
  $('bouton-commencer-bas').onclick = () => demarrerSession();
  $('bouton-ma-page').onclick = () => ouvrirEspace();

  // --- L'entrée -----------------------------------------------------------
  // Des <form> plutôt que des boutons : « Entrée » valide, le clavier des
  // téléphones affiche « envoyer », et un gestionnaire de mots de passe sait
  // quoi remplir et quoi proposer. Rien de tout ça ne s'obtient avec un div.
  $('volet-connexion').onsubmit = (e) => { e.preventDefault(); seConnecter(); };
  $('volet-inscription').onsubmit = (e) => { e.preventDefault(); sInscrire(); };
  $('volet-oubli').onsubmit = (e) => { e.preventDefault(); demanderCode($('champ-email-oubli').value); };
  $('volet-code').onsubmit = (e) => { e.preventDefault(); reinitialiser(); };

  $('onglet-connexion').onclick = () => montrerVolet('volet-connexion');
  $('onglet-inscription').onclick = () => montrerVolet('volet-inscription');
  $('lien-vers-inscription').onclick = () => montrerVolet('volet-inscription');
  $('lien-vers-connexion').onclick = () => montrerVolet('volet-connexion');
  $('lien-retour-connexion').onclick = () => montrerVolet('volet-connexion');
  $('bouton-oubli').onclick = () => {
    // L'adresse déjà tapée suit : la retaper est le genre de détail qui fait
    // abandonner à l'endroit précis où on est déjà énervé.
    $('champ-email-oubli').value = $('champ-email').value.trim();
    montrerVolet('volet-oubli');
  };
  $('bouton-renvoyer').onclick = () => demanderCode(emailEnCours);
  $('bouton-changer-adresse').onclick = () => {
    clearInterval(minuteurRenvoi);
    montrerVolet('volet-oubli');
  };
  $('bouton-quitter-connexion').onclick = () => {
    apresEntree = null;
    clearInterval(minuteurRenvoi);
    montrer('ecran-accueil');
  };

  // « Voir » : sur un clavier de téléphone, un mot de passe qu'on ne peut pas
  // relire est un mot de passe qu'on retape trois fois.
  [['voir-mdp', 'champ-mdp'], ['voir-mdp-inscription', 'champ-mdp-inscription'],
   ['voir-mdp-nouveau', 'champ-mdp-nouveau']].forEach(([bouton, champ]) => {
    $(bouton).onclick = () => {
      const montre = $(champ).type === 'password';
      $(champ).type = montre ? 'text' : 'password';
      $(bouton).textContent = montre ? 'Cacher' : 'Voir';
      $(bouton).setAttribute('aria-pressed', String(montre));
      $(bouton).setAttribute('aria-label',
        montre ? 'Cacher le mot de passe' : 'Afficher le mot de passe');
      $(champ).focus();
    };
  });

  $('champ-mdp-inscription').addEventListener('input', () => {
    majJauge();
    $('erreur-inscription').hidden = true;
  });
  // Le code arrive souvent par copier-coller depuis la boîte mail, avec des
  // espaces. On nettoie à la frappe plutôt que de refuser à la validation.
  $('champ-code').addEventListener('input', (e) => {
    const propre = e.target.value.replace(/\D/g, '').slice(0, 6);
    if (propre !== e.target.value) e.target.value = propre;
    $('erreur-code').hidden = true;
  });
  ['champ-email', 'champ-mdp'].forEach((id) =>
    $(id).addEventListener('input', () => { $('erreur-connexion').hidden = true; }));
  ['champ-email-inscription', 'champ-prenom-inscription', 'champ-mdp-confirmation'].forEach((id) =>
    $(id).addEventListener('input', () => { $('erreur-inscription').hidden = true; }));
  $('champ-email-oubli').addEventListener('input', () => { $('erreur-oubli').hidden = true; });

  $('bouton-sortir').onclick = () => sortir();
  $('bouton-effacer-compte').onclick = () => effacerLeCompte();
  $('bouton-espace').onclick = () => {
    if (document.getElementById('ecran-espace').hidden) return ouvrirEspace();
    if (etat) reprendre();
  };
  $('bouton-quitter-espace').onclick = () => {
    if (etat) return reprendre();
    montrer('ecran-accueil');
  };
  $('bouton-espace-nouveau').onclick = () => demarrerSession();
  $('bouton-tout-voir').onclick = () => ouvrirMatiere(null);
  $('retour-etagere').onclick = () => { montrer('ecran-espace'); dessinerEspace(); };

  const changerMois = (pas) => {
    moisAffiche = new Date(moisAffiche.getFullYear(), moisAffiche.getMonth() + pas, 1);
    // Changer de mois ne garde pas un jour choisi qui n'y est plus.
    jourChoisi = null;
    dessinerEspace();
  };
  ['fiches', 'controles'].forEach((genre) => {
    $('recherche-' + genre).oninput = (evenement) => {
      archives[genre].recherche = evenement.target.value;
      archives[genre].tout = false;
      dessinerMatiere();
      // Redessiner remplace le champ dans le DOM des filtres voisins, pas le
      // champ lui-même : le focus et le curseur ne bougent pas.
      $('recherche-' + genre).focus();
    };
  });

  $('mois-precedent').onclick = () => changerMois(-1);
  $('mois-suivant').onclick = () => changerMois(1);

  // La carte d'élève : deux réglages, gardés ici et nulle part ailleurs.
  $('champ-prenom').oninput = (evenement) => {
    garderCarte({ ...carte(), prenom: evenement.target.value.trim() });
  };
  $('embleme').onclick = basculerAtelier;
  $('bouton-reprendre').onclick = () => {
    const derniere = localStorage.getItem(CLE_DERNIERE);
    const trouve = derniere && charger(derniere);
    if (!trouve) return demarrerSession();
    etat = trouve;
    lirePages(etat.sessionId).then((pages) => { photosDuCours = pages; });
    tracer('ouverture', { origine: 'reprise' });
    reprendre();
  };

  $('bouton-vers-photos').onclick = validerContexte;
  $('champ-photos').onchange = (evenement) => {
    ajouterPhotos(evenement.target.files);
    evenement.target.value = '';
  };
  $('bouton-analyser').onclick = analyser;

  $('bouton-perimetre-ok').onclick = confirmerPerimetre;
  $('bouton-plus-de-photos').onclick = () => montrer('ecran-photos');

  $('bouton-correction-accueil').onclick = reprendre;
  $('bouton-accueil').onclick = reprendre;

  $('bouton-question-suivante').onclick = questionSuivante;
  $('bouton-signaler').onclick = () => {
    const question = controleEnCours.questions[controleEnCours.index];
    ouvrirSignalement(question.numero, question.enonce, null);
  };

  $('bouton-fiche-ciblee').onclick = demanderFicheCiblee;
  $('bouton-second-controle').onclick = () => lancerControle(notionsFragiles());

  $('bouton-vue').onclick = () => basculerVue();

  $('fermer-visionneuse').onclick = fermerCahier;
  $('visionneuse').onclick = (evenement) => {
    if (evenement.target === $('visionneuse') || evenement.target === $('page-cahier')) fermerCahier();
  };
  $('page-precedente').onclick = (e) => { e.stopPropagation(); cahierOuvert.rang -= 1; dessinerCahier(); };
  $('page-suivante').onclick = (e) => { e.stopPropagation(); cahierOuvert.rang += 1; dessinerCahier(); };
  document.addEventListener('keydown', (evenement) => {
    if (evenement.key === 'Escape' && !$('visionneuse').hidden) fermerCahier();
  });

  $('bouton-tout-afficher').onclick = () => {
    const paquet = $('paquet');
    const colonne = paquet.dataset.vue === 'colonne';
    paquet.dataset.vue = colonne ? 'paquet' : 'colonne';
    $('rubans').hidden = !colonne;
    $('bouton-tout-afficher').textContent = colonne
      ? 'Tout afficher d’un coup'
      : 'Revenir aux cartes';
    if (colonne) suivreCartes();
  };

  $('bouton-copier').onclick = copierLien;
  $('bouton-nouveau-cours').onclick = () => demarrerSession();

  $('dialogue-signalement').addEventListener('close', (evenement) => {
    const dialogue = evenement.target;
    if (dialogue.returnValue === 'envoyer') envoyerSignalement($('motif-signalement').value);
    else signalementEnCours = null;
  });

  // Un contrôle en cours ne survit pas à un rechargement : on prévient.
  window.addEventListener('beforeunload', (evenement) => {
    if (controleEnCours && $('ecran-controle').hidden === false) {
      evenement.preventDefault();
      evenement.returnValue = '';
    }
  });

  initialiser();
});
