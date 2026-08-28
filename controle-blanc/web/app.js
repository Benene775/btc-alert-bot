/* Contrôle blanc — application d’une seule page.
 *
 * L’état vit dans le navigateur (localStorage), pas sur le serveur : pas de compte,
 * pas de mot de passe, aucune donnée personnelle. Le lien de reprise (?s=…) est la
 * seule chose à conserver.
 *
 * Ce qui n’est PAS conservé : les photos. Elles servent à l’analyse puis disparaissent.
 * Ce qu’on garde, c’est la transcription du cours, qui tient dans quelques kilo-octets.
 */

'use strict';

const CLE_ETAT = 'cb.session.';
const CLE_DERNIERE = 'cb.derniere';
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

/* ------------------------------------------------------- pages du cahier --- */

/* La photo du cahier est ce que le produit a de plus précieux : c’est elle qui
 * prouve à l’élève que la fiche vient de SON cours et pas d’un manuel. On la
 * garde donc, au lieu de la jeter après l’analyse.
 *
 * Elle ne quitte jamais l’appareil : IndexedDB est un stockage du navigateur,
 * au même titre que localStorage, et rien n’est réenvoyé au serveur.
 */
const BASE_PAGES = 'cb-pages';

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

/* ------------------------------------------------------------------ api --- */

async function api(chemin, options = {}) {
  const reponse = await fetch(chemin, options);
  if (reponse.ok) return reponse.json();

  let corps = {};
  try { corps = await reponse.json(); } catch (e) { /* réponse non JSON */ }

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
  remplirSelecteur($('champ-matiere'), config.matieres,
                   config.matiere_par_defaut || 'histoire-geographie');

  const params = new URLSearchParams(location.search);
  const depuisLien = params.get('s');
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
  montrer('ecran-accueil');
  armerRevelations();
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
    etat.fiches.push({ type: 'ciblee', contenu: fiche, le: new Date().toISOString() });
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
  $('champ-date').value = dateParDefaut();
  $('champ-date').min = new Date().toISOString().slice(0, 10);

  $('bouton-commencer').onclick = () => demarrerSession();
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
