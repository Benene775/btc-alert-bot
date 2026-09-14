/* L'agent de service : ce qui fait de Repère une application.
 *
 * Installée sur l'écran d'accueil, la page s'ouvre en plein écran, avec son
 * icône, sans barre d'adresse. Cet agent lui donne le reste : elle démarre même
 * sans réseau, et l'élève retrouve son classeur dans le métro.
 *
 * TROIS RÉGIMES, et le choix compte plus que le code :
 *
 *   /api/*      jamais mis en cache. Servir un vieux classeur ou un vieux
 *               quota depuis le cache ferait réapparaître du travail effacé et
 *               mentir les compteurs. Hors ligne, l'appel échoue — et
 *               l'application sait déjà le dire.
 *
 *   la coque    réseau d'abord, cache en secours. Pendant la phase de test le
 *               code change souvent : un cache d'abord bloquerait les élèves
 *               sur une version périmée, ce qui coûte plus cher qu'un
 *               chargement une seconde plus lent.
 *
 *   les icônes  cache d'abord. Elles ne changent pas, et les redemander à
 *               chaque ouverture pour rien serait du gaspillage.
 */

const VERSION = 'repere-v1';
const COQUE = [
  '/', '/app.js', '/styles.css', '/polices.css', '/manifeste.json',
  '/icones/icone-192.png', '/icones/icone-512.png',
];

self.addEventListener('install', (evenement) => {
  evenement.waitUntil(
    caches.open(VERSION)
      // addAll échoue en bloc si une seule ressource manque : on les prend une
      // par une, pour qu'une icône absente ne prive pas l'élève de la coque.
      .then((cache) => Promise.allSettled(COQUE.map((url) => cache.add(url))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (evenement) => {
  evenement.waitUntil(
    caches.keys()
      .then((noms) => Promise.all(noms.filter((n) => n !== VERSION).map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (evenement) => {
  const requete = evenement.request;
  if (requete.method !== 'GET') return;

  const url = new URL(requete.url);
  if (url.origin !== self.location.origin) return;

  // Ce qui vient du serveur en direct, et rien d'autre.
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/admin/')) return;

  if (url.pathname.startsWith('/icones/')) {
    evenement.respondWith(
      caches.match(requete).then((garde) => garde || fetch(requete))
    );
    return;
  }

  evenement.respondWith(
    fetch(requete)
      .then((reponse) => {
        // On ne garde que ce qui a vraiment été servi : mettre une page
        // d'erreur en cache la rejouerait à chaque démarrage hors ligne.
        if (reponse && reponse.ok) {
          const copie = reponse.clone();
          caches.open(VERSION).then((cache) => cache.put(requete, copie));
        }
        return reponse;
      })
      .catch(() => caches.match(requete).then((garde) => garde || caches.match('/')))
  );
});

/* --- Les rappels de contrôle ----------------------------------------------
 *
 * « Contrôle d'espagnol demain, pense à réviser. » Le serveur envoie, l'agent
 * affiche. Il tourne même quand l'application est fermée : c'est toute la
 * raison d'être de ce mécanisme, et la seule façon de prévenir quelqu'un la
 * veille au soir sans lui demander d'ouvrir quoi que ce soit.
 *
 * Sur iPhone, ça n'existe que pour une application POSÉE SUR L'ÉCRAN D'ACCUEIL
 * (Partager → « Sur l'écran d'accueil »). Dans l'onglet Safari, rien n'arrive,
 * et c'est Apple qui le décide, pas nous. L'application le dit avant de
 * proposer le réglage, plutôt que de laisser croire que c'est cassé.
 */
self.addEventListener('push', (evenement) => {
  let charge = {};
  try { charge = evenement.data ? evenement.data.json() : {}; } catch (e) { charge = {}; }
  const titre = charge.titre || 'Repère';
  evenement.waitUntil(
    self.registration.showNotification(titre, {
      body: charge.corps || '',
      icon: '/icones/icone-192.png',
      badge: '/icones/icone-192.png',
      lang: 'fr',
      // Une étiquette par jour : si deux envois se croisent, le second
      // remplace le premier au lieu d'empiler deux fois la même chose.
      tag: 'rappel-' + (charge.jour || ''),
      data: { url: '/' },
    })
  );
});

self.addEventListener('notificationclick', (evenement) => {
  evenement.notification.close();
  const cible = (evenement.notification.data && evenement.notification.data.url) || '/';
  evenement.waitUntil(
    // Rouvrir l'onglet déjà ouvert plutôt qu'en créer un deuxième : l'élève
    // retrouve sa page où il l'avait laissée.
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((fenetres) => {
      for (const fenetre of fenetres) {
        if (fenetre.url.indexOf(self.location.origin) === 0 && 'focus' in fenetre) {
          fenetre.navigate(cible).catch(() => {});
          return fenetre.focus();
        }
      }
      return self.clients.openWindow(cible);
    })
  );
});
