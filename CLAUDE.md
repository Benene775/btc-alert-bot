# Repère — règles de travail

## L'argent du modèle : demander AVANT, toujours

La clé API est celle de Benjamin, et chaque appel au modèle lui est facturé.

**Ne jamais lancer un appel payant sans avoir demandé, et sans avoir donné une
estimation chiffrée du coût.** Pas d'exception : ni pour vérifier une hypothèse,
ni pour reproduire un bogue signalé, ni pour mesurer la qualité d'une sortie.
Proposer, chiffrer, attendre la réponse.

C'est une consigne donnée après coup : une mesure de ~0,15 $ a été lancée sans
demander, pour répondre à une question sur le calibrage par niveau. La réponse
était juste et la dépense minime — la demande manquait.

### Ce qui coûte

Tout appel réel au modèle, c'est-à-dire `app/llm.py` hors mode démonstration :
`analyser_photos`, `fiche_generale`, `fiche_ciblee`, `generer_controle`,
`corriger`. Et tout ce qui les enchaîne : `outils/garde.py`, `outils/essai.py`,
le banc d'essai, un parcours mené contre un serveur lancé avec `CB_DEMO_MODE=0`.

### Ce qui ne coûte rien, et ne se demande donc pas

* `llm.verifier_la_cle()` — `count_tokens` authentifie sans facturer.
* Tout ce qui tourne en `CB_DEMO_MODE=1` : contenus factices, aucun appel.
* La suite de tests, les parcours Playwright contre le serveur de démonstration,
  les captures d'écran, les rendus PDF.

### Estimer — chiffres au 14 septembre 2026

| Appel | Coût | D'où vient le chiffre |
|---|---|---|
| Analyse des photos | ~0,10 $ | **mesuré** sur le tableau de bord (0,0971 $) |
| Fiche générale | ~0,02 $ | **mesuré** (0,019 $) |
| Contrôle blanc | ~0,05 $ | déduit : parcours 0,25 $ moins l'analyse et la fiche |
| Correction | ~0,05 $ | déduit, même calcul |
| Fiche ciblée | ~0,02 $ | déduit |
| **Parcours complet** | **0,25 $** | **mesuré** (README, « Ce que ça coûte ») |
| Passage de `outils/garde.py` | 0,28 à 0,37 $ | **mesuré** (README) |

Les photos font 55 à 79 % d'un parcours : une mesure qui n'en envoie pas est
beaucoup moins chère qu'elle n'en a l'air. Une comparaison « même cours, deux
niveaux » (2 fiches + 2 contrôles, sans photos) coûte ~0,15 $.

Dire d'où vient chaque chiffre : « mesuré » et « déduit » ne valent pas la même
chose, et une estimation présentée comme une mesure est un mensonge poli.

## La clé

Elle vit dans le répertoire de travail temporaire de la session (`$SCRATCHPAD/.cle`,
chmod 600), **jamais dans le dépôt** — qui est public. Ne pas l'écrire dans un
fichier suivi, un commit, un message, ni un test.
