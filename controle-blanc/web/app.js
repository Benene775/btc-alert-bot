/* Contrôle blanc — application d'une seule page.
 *
 * L'état vit dans le navigateur (localStorage), pas sur le serveur : pas de compte,
 * pas de mot de passe, aucune donnée personnelle. Le lien de reprise (?s=…) est la
 * seule chose à conserver.
 *
 * Ce qui n'est PAS conservé : les photos. Elles servent à l'analyse puis disparaissent.
 * Ce qu'on garde, c'est la transcription du cours, qui tient dans quelques kilo-octets.
 */

'use strict';

const CLE_ETAT = 'cb.session.';
const CLE_DERNIERE = 'cb.derniere';
const VERSION_ETAT = 1;
const COTE_MAX_PHOTO = 1568;   // au-delà, le modèle redimensionne de toute façon
const QUALITE_PHOTO = 0.82;

let etat = null;
let photosEnAttente = [];      // en mémoire seulement, jamais persistées
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
    message("Ton téléphone n'a plus de place pour sauvegarder. Garde bien ton lien.", 'alerte');
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

/* ------------------------------------------------------------------ api --- */

async function api(chemin, options = {}) {
  const reponse = await fetch(chemin, options);
  if (reponse.ok) return reponse.json();

  let corps = {};
  try { corps = await reponse.json(); } catch (e) { /* réponse non JSON */ }

  if (reponse.status === 404 && corps.detail === 'session inconnue') {
    throw new ErreurApi("Cette session n'existe plus sur le serveur. On en recommence une.", 'session');
  }
  if (reponse.status === 429) {
    throw new ErreurApi(corps.message || 'Limite atteinte pour aujourd\'hui.', 'quota');
  }
  if (reponse.status === 503) {
    throw new ErreurApi(corps.message || 'Le service est indisponible. Réessaie.', 'modele');
  }
  throw new ErreurApi(corps.detail || corps.message || "Ça n'a pas marché. Réessaie.", 'autre');
}

class ErreurApi extends Error {
  constructor(message, genre) {
    super(message);
    this.genre = genre;
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
  window.scrollTo({ top: 0, behavior: 'instant' in window ? 'instant' : 'auto' });
  majBandeau(id);
}

function majBandeau(idEcran) {
  const bandeau = $('bandeau');
  if (!etat || idEcran === 'ecran-accueil') { bandeau.hidden = true; return; }
  bandeau.hidden = false;
  const matiere = (config.matieres.find((m) => m.cle === etat.matiere) || {}).nom;
  $('bandeau-matiere').textContent = matiere || 'Mon contrôle';
  $('bandeau-compte').textContent = texteCompteARebours();
  $('bandeau-compte').hidden = !etat.dateControle;
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
  if (jours === 0) return "C'est aujourd'hui";
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
    message(erreur.message, erreur.genre === 'quota' ? 'neutre' : 'alerte', 7000);
    if (erreur.genre === 'session') demarrerSession(true);
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
  remplirSelecteur($('champ-matiere'), config.matieres, 'histoire-geographie');

  const params = new URLSearchParams(location.search);
  const depuisLien = params.get('s');
  const derniere = localStorage.getItem(CLE_DERNIERE);

  if (depuisLien) {
    const trouve = charger(depuisLien);
    if (trouve) {
      etat = trouve;
      tracer('ouverture', { origine: 'lien' });
      return reprendre();
    }
    // Le lien vient d'un autre appareil : la session serveur existe, l'état local non.
    try {
      const info = await api('/api/session/' + encodeURIComponent(depuisLien));
      etat = etatNeuf(depuisLien, info.lien_de_reprise);
      sauver();
      tracer('ouverture', { origine: 'lien_autre_appareil' });
      message("Session retrouvée, mais ton cours était gardé sur ton autre téléphone. On repart des photos.");
      return montrer('ecran-contexte');
    } catch (e) { /* session inconnue : on tombe sur l'accueil */ }
  }

  if (derniere && charger(derniere)) {
    $('bouton-reprendre').hidden = false;
  }
  montrer('ecran-accueil');
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

async function demarrerSession(silencieux = false) {
  try {
    if (!silencieux) attendre('On prépare ta session…');
    const info = await api('/api/session', { method: 'POST' });
    etat = etatNeuf(info.session_id, info.lien_de_reprise);
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
    message('On garde les ' + restant + ' premières, tu pourras en ajouter d\'autres ensuite.');
  }
  for (const fichier of aTraiter) {
    try {
      const reduite = await reduirePhoto(fichier);
      photosEnAttente.push(reduite);
    } catch (e) {
      message("Une photo n'a pas pu être lue. Réessaie avec celle-là.", 'alerte');
    }
  }
  dessinerPhotos();
}

// Réduire avant l'envoi : moins de données mobiles pour l'élève, moins de tokens
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
        resoudre({ blob, apercu: toile.toDataURL('image/jpeg', 0.5), nom: fichier.name });
      }, 'image/jpeg', QUALITE_PHOTO);
    };
    image.onerror = () => { URL.revokeObjectURL(url); rejeter(new Error('image illisible')); };
    image.src = url;
  });
}

function dessinerPhotos() {
  const liste = $('liste-photos');
  liste.innerHTML = '';
  photosEnAttente.forEach((photo, index) => {
    const element = document.createElement('li');
    const image = document.createElement('img');
    image.src = photo.apercu;
    image.alt = 'Page ' + (index + 1);
    const retirer = document.createElement('button');
    retirer.type = 'button';
    retirer.textContent = '×';
    retirer.setAttribute('aria-label', 'Retirer la page ' + (index + 1));
    retirer.onclick = () => { photosEnAttente.splice(index, 1); dessinerPhotos(); };
    element.append(image, retirer);
    liste.appendChild(element);
  });
  $('bouton-analyser').disabled = photosEnAttente.length === 0;
  $('bouton-analyser').textContent = photosEnAttente.length > 1
    ? 'Analyser mes ' + photosEnAttente.length + ' pages'
    : 'Analyser mon cours';
}

async function analyser() {
  if (!photosEnAttente.length) return;
  attendre('On lit ton cours…', 'Une trentaine de secondes, parfois plus si l\'écriture est serrée.');
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
      message("Aucune page n'était lisible. Reprends-les en photo, plus près et bien à plat.", 'alerte', 8000);
      return;
    }
    // Fusion : on peut ajouter des pages plus tard sans perdre ce qui a été lu.
    const titresConnus = new Set(etat.chapitres.map((c) => c.titre));
    nouveaux.forEach((c) => { if (!titresConnus.has(c.titre)) etat.chapitres.push({ ...c, actif: true }); });

    if (!etat.matiere && resultat.matiere_detectee) {
      const trouvee = config.matieres.find((m) => m.nom === resultat.matiere_detectee);
      if (trouvee) etat.matiere = trouvee.cle;
    }
    photosEnAttente = [];
    dessinerPhotos();
    etat.etape = 'perimetre';
    sauver();
    dessinerPerimetre();
    montrer('ecran-perimetre');
  } catch (e) { gererErreur(e); }
}

/* ------------------------------------------- étape 2 : le périmètre ------ */

function dessinerPerimetre() {
  const nombre = etat.chapitres.length;
  $('titre-perimetre').textContent = nombre > 1
    ? "J'ai repéré " + nombre + ' chapitres.'
    : "J'ai repéré 1 chapitre.";

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
    titre: 'Je révise d\'abord',
    detail: 'Une fiche sur tout le chapitre, à relire tranquillement. Ensuite tu te testes.',
  },
  teste: {
    titre: 'Je me teste tout de suite',
    detail: 'Le contrôle blanc maintenant, dans le vrai format. Tu verras vite où tu en es.',
  },
};

function dessinerCarrefour() {
  // Ordre tiré au sort et mémorisé : sans ça, on mesurerait surtout la position
  // du bouton, pas la préférence de l'élève.
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

async function demanderFicheGenerale() {
  attendre('On prépare ta fiche…', 'Elle reprend ton cours, dans ton ordre à toi.');
  try {
    const fiche = await envoyerJson('/api/fiche/generale', {
      session_id: etat.sessionId,
      niveau: etat.niveau,
      chapitres: chapitresRetenus(),
    });
    fermerAttente();
    etat.fiches.push({ type: 'generale', contenu: fiche, le: new Date().toISOString() });
    etat.etape = 'fiche';
    sauver();
    afficherFiche(fiche, 'generale');
  } catch (e) { gererErreur(e); }
}

async function demanderFicheCiblee() {
  if (!etat.notionsFragiles.length) {
    message('Rien à cibler pour l\'instant : passe un contrôle blanc d\'abord.');
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
    etat.fiches.push({ type: 'ciblee', contenu: fiche, le: new Date().toISOString() });
    sauver();
    afficherFiche(fiche, 'ciblee');
  } catch (e) { gererErreur(e); }
}

function afficherFiche(fiche, type) {
  $('etiquette-fiche').textContent = type === 'ciblee' ? 'Fiche ciblée' : 'Fiche générale';
  $('titre-fiche').textContent = fiche.titre || 'Ta fiche';
  $('chapeau-fiche').textContent = type === 'ciblee'
    ? 'Uniquement les notions que tu viens de rater. Relis-la, puis retente le contrôle.'
    : 'Relis-la une fois, sans forcer à retenir. Le contrôle blanc fera le tri ensuite.';

  const corps = $('corps-fiche');
  corps.innerHTML = '';

  (fiche.sections || []).forEach((section) => {
    const bloc = document.createElement('div');
    bloc.className = 'section-fiche';
    const titre = document.createElement('h3');
    titre.textContent = section.titre;
    const points = document.createElement('ul');
    (section.points || []).forEach((point) => {
      const li = document.createElement('li');
      li.textContent = point;
      points.appendChild(li);
    });
    bloc.append(titre, points);
    if (section.a_retenir) {
      const retenir = document.createElement('p');
      retenir.className = 'a-retenir';
      retenir.textContent = section.a_retenir;
      bloc.appendChild(retenir);
    }
    corps.appendChild(bloc);
  });

  if ((fiche.definitions || []).length) {
    const bloc = document.createElement('div');
    bloc.className = 'section-fiche';
    const titre = document.createElement('h3');
    titre.textContent = 'Les mots à connaître';
    const liste = document.createElement('ul');
    liste.className = 'definitions';
    fiche.definitions.forEach((d) => {
      const li = document.createElement('li');
      const terme = document.createElement('b');
      terme.textContent = d.terme;
      li.append(terme, document.createTextNode(d.definition));
      liste.appendChild(li);
    });
    bloc.append(titre, liste);
    corps.appendChild(bloc);
  }

  if ((fiche.pieges || []).length) {
    const bloc = document.createElement('div');
    bloc.className = 'section-fiche';
    const titre = document.createElement('h3');
    titre.textContent = 'Les pièges';
    const liste = document.createElement('ul');
    fiche.pieges.forEach((piege) => {
      const li = document.createElement('li');
      li.textContent = piege;
      liste.appendChild(li);
    });
    bloc.append(titre, liste);
    corps.appendChild(bloc);
  }

  $('bouton-apres-fiche').textContent = type === 'ciblee'
    ? 'Me retester sur ces notions'
    : 'Passer au contrôle blanc';
  $('bouton-apres-fiche').onclick = () => lancerControle(type === 'ciblee');
  montrer('ecran-fiche');
}

/* --------------------------------------------- étape 4 : contrôle blanc -- */

async function lancerControle(cible = false) {
  const notions = cible ? etat.notionsFragiles.map((n) => n.notion) : [];
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
  // La question affichée compte, même si l'élève n'a pas eu le temps de valider.
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

  const corps = $('corps-correction');
  corps.innerHTML = '';
  (correction.reponses || []).forEach((ligne) => {
    const carte = document.createElement('div');
    carte.className = 'carte-correction';
    carte.dataset.statut = ligne.statut;

    const etiquette = document.createElement('span');
    etiquette.className = 'etiquette-statut';
    etiquette.textContent = ligne.signalee ? 'Signalée' : (LIBELLES_STATUT[ligne.statut] || '');

    const enonce = document.createElement('p');
    enonce.className = 'question-correction';
    enonce.textContent = ligne.numero + '. ' + (ligne.enonce || '');

    carte.append(etiquette, enonce);

    if (ligne.ce_qui_va) carte.appendChild(blocTexte('Ce qui va', ligne.ce_qui_va));
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
    tienne.textContent = ligne.ta_reponse ? '« ' + ligne.ta_reponse + ' »' : '(tu n\'as rien écrit)';
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
    message('Signalement noté sur ton téléphone, mais pas envoyé. Ce n\'est pas grave.');
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
      + 'Le meilleur moment pour te retester, c\'est maintenant, pas la veille.';
  } else if (jours === 1) {
    rappel.innerHTML = '<b>' + matiere + '</b>, c\'est demain. Un dernier contrôle blanc sur tes notions fragiles ?';
  } else if (jours === 0) {
    rappel.innerHTML = '<b>' + matiere + '</b>, c\'est aujourd\'hui. Relis ta fiche ciblée, rien de plus.';
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
    bouton.onclick = () => lancerControle(true);
  } else if (etat.chapitres.length) {
    bouton.textContent = 'Passer un contrôle blanc';
    bouton.onclick = () => lancerControle(false);
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
  $('champ-date').value = dateParDefaut();
  $('champ-date').min = new Date().toISOString().slice(0, 10);

  $('bouton-commencer').onclick = () => demarrerSession();
  $('bouton-reprendre').onclick = () => {
    const derniere = localStorage.getItem(CLE_DERNIERE);
    const trouve = derniere && charger(derniere);
    if (!trouve) return demarrerSession();
    etat = trouve;
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

  $('bouton-fiche-accueil').onclick = reprendre;
  $('bouton-correction-accueil').onclick = reprendre;
  $('bouton-accueil').onclick = reprendre;

  $('bouton-question-suivante').onclick = questionSuivante;
  $('bouton-signaler').onclick = () => {
    const question = controleEnCours.questions[controleEnCours.index];
    ouvrirSignalement(question.numero, question.enonce, null);
  };

  $('bouton-fiche-ciblee').onclick = demanderFicheCiblee;
  $('bouton-second-controle').onclick = () => lancerControle(true);

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
