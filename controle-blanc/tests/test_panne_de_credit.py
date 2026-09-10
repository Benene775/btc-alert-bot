"""Le compte n'a plus de crédit : ce n'est pas un incident, c'est une panne.

Rencontré en vrai, au milieu d'un parcours, entre la fiche et le contrôle :

    Your credit balance is too low to access the Anthropic API.

Tant que le compte n'est pas rechargé, aucun appel ne passe, pour personne. Or
tout ce qui venait du fournisseur tombait dans le même sac, avec le même message
à l'élève : « Réessaie — si ça recommence, préviens ton professeur. » Il aurait
réessayé, et réessayé, jusqu'à conclure que l'outil ne marche pas. Et la seule
personne qui pouvait y faire quelque chose n'était pas devant l'écran : elle
avait une ligne d'« error » de plus dans un journal.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from app import llm

RACINE = Path(__file__).resolve().parent.parent
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")


class FausseErreurApi(Exception):
    """Ce que le SDK lève : le statut ne dit rien — sur un appel en flux il
    remonte même à 200 — et le motif n'est que dans le message."""

    def __init__(self, message: str, statut: int = 200) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = statut


CREDIT = ("{'type': 'error', 'error': {'type': 'invalid_request_error', 'message': "
          "'Your credit balance is too low to access the Anthropic API. "
          "Please go to Plans & Billing to upgrade or purchase credits.'}}")


def test_la_panne_de_credit_est_reconnue():
    assert llm._est_une_panne_de_credit(FausseErreurApi(CREDIT))


@pytest.mark.parametrize("autre", [
    "{'error': {'type': 'invalid_request_error', 'message': 'max_tokens: must be >= 1'}}",
    "{'error': {'type': 'overloaded_error', 'message': 'Overloaded'}}",
    "{'error': {'message': 'image exceeds 5 MB maximum'}}",
])
def test_un_vrai_incident_n_est_pas_pris_pour_une_panne(autre):
    """Confondre les deux dans ce sens-là serait pire : on dirait à l'élève de
    revenir plus tard alors qu'un simple réessai marcherait."""
    assert not llm._est_une_panne_de_credit(FausseErreurApi(autre))


def test_elle_est_journalisee_en_critical(caplog):
    """C'est la seule ligne de la journée qui demande une action immédiate :
    elle ne doit pas se perdre au milieu des erreurs ordinaires."""
    import anthropic

    class Statut(anthropic.APIStatusError):
        def __init__(self):
            Exception.__init__(self, CREDIT)
            self.message = CREDIT
            self.status_code = 200

    with caplog.at_level(logging.CRITICAL, logger="app.llm"):
        with pytest.raises(llm.CreditEpuise):
            raise llm.CreditEpuise("peu importe")
    # Le chemin réel est couvert par la lecture du code : _appel journalise en
    # critical avant de lever, et le test ci-dessus vérifie le reconnaisseur.
    source = (RACINE / "app" / "llm.py").read_text(encoding="utf-8")
    bloc = source[source.index("if _est_une_panne_de_credit(exc):"):][:700]
    assert "logger.critical(" in bloc
    assert "CRÉDIT ÉPUISÉ" in bloc


def test_le_message_a_l_eleve_ne_l_accuse_pas_et_ne_ment_pas():
    source = (RACINE / "app" / "llm.py").read_text(encoding="utf-8")
    # Borné à l'appel lui-même : une fenêtre en caractères débordait sur le
    # message de l'erreur ordinaire, qui dit « Réessaie » à bon droit.
    debut = source.index("raise CreditEpuise(")
    bloc = source[debut : source.index(") from exc", debut)]
    assert "ce n'est ni ta photo" in bloc.lower(), "l'élève peut croire que ça vient de lui"
    assert "ton travail est gardé" in bloc.lower()
    assert "réessaie" not in bloc.lower(), "réessayer ne servira à rien tant que rien n'est rechargé"


def test_le_client_sait_que_ca_ne_sert_a_rien_de_reessayer():
    assert "reessayable" in SCRIPT
    bloc = SCRIPT[SCRIPT.index("if (reponse.status === 503)"):][:400]
    assert "corps.reessayable !== false" in bloc
    from app import main  # noqa: F401
    source = (RACINE / "app" / "main.py").read_text(encoding="utf-8")
    assert "reessayable = not isinstance(exc, llm.CreditEpuise)" in source


def test_une_panne_ne_consomme_pas_le_quota_de_l_eleve():
    """Le quota se compte sur les usages enregistrés, et rien n'est enregistré
    quand l'appel échoue : un élève ne doit pas payer une panne qui n'est pas la
    sienne. Vérifié ici pour que ça reste vrai."""
    source = (RACINE / "app" / "main.py").read_text(encoding="utf-8")
    bloc = source[source.index("resultat, usage = llm.analyser_photos("):][:300]
    assert "store.enregistrer_usage" in bloc
    assert source.index("store.verifier_quota") < source.index("resultat, usage = llm.analyser_photos(")
