"""L'envoi du code de réinitialisation par courrier.

Un seul message part d'ici : « voici ton code pour changer de mot de passe ».
Il est écrit en texte simple et en HTML — beaucoup de messageries scolaires
coupent le second, et un code qu'on ne peut pas lire est un élève bloqué
dehors.

Sans serveur SMTP configuré, le code va dans les journaux. C'est fait pour le
développement : `config.AUTH_CODE_EN_CLAIR` le renvoie alors aussi dans la
réponse HTTP, ce qui ouvre la porte en grand et n'a donc rien à faire en
production. Les deux réglages sont refusés dès qu'un SMTP existe.
"""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, parseaddr

from . import config

logger = logging.getLogger("controle-blanc.courrier")


class ErreurCourrier(Exception):
    """Le message n'est pas parti. L'élève doit l'apprendre, pas le deviner."""


OBJET = "Ton code Repère pour changer de mot de passe : {code}"

TEXTE = """Tu as demandé à changer ton mot de passe sur Repère.

Ton code :

    {code}

Il est valable {minutes} minutes, et une seule fois.

Si tu n'as rien demandé, ignore ce message : ton mot de passe actuel reste
valable, et sans ce code personne ne peut le changer.

—
Repère · on optimise tes révisions
"""

# Le HTML reste volontairement primitif : pas d'image, pas de feuille de style
# externe, pas de police à télécharger. Un message qui se charge à moitié dans
# une messagerie scolaire vaut moins qu'un message sobre qui arrive entier.
HTML = """<!doctype html>
<html lang="fr"><body style="margin:0;padding:24px;background:#fbf7f2;
 font:16px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#241e17">
  <div style="max-width:440px;margin:0 auto;background:#fffdfa;border-radius:16px;
       padding:28px;border:1px solid rgba(36,30,23,.08)">
    <p style="margin:0 0 4px;font:600 13px/1 ui-monospace,monospace;letter-spacing:.14em;
       text-transform:uppercase;color:#9a6410">Repère</p>
    <p style="margin:20px 0 8px;font-size:15px;color:#7a6a5a">
      Ton code pour changer de mot de passe :</p>
    <p style="margin:0;font:700 34px/1.2 ui-monospace,'SFMono-Regular',Menlo,monospace;
       letter-spacing:.18em;color:#241e17">{code}</p>
    <p style="margin:20px 0 0;font-size:14px;color:#7a6a5a">
      Valable {minutes} minutes, et une seule fois.</p>
    <p style="margin:12px 0 0;font-size:14px;color:#7a6a5a">
      Si tu n'as rien demandé, ignore ce message : ton mot de passe actuel reste
      valable, et sans ce code personne ne peut le changer.</p>
  </div>
</body></html>
"""


def _message(destinataire: str, code: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = OBJET.format(code=code)
    nom, adresse = parseaddr(config.SMTP_EXPEDITEUR)
    msg["From"] = formataddr((nom or "Repère", adresse or "ne-pas-repondre@localhost"))
    msg["To"] = destinataire
    # Un code n'a aucune raison d'être cité dans une réponse automatique ni
    # rangé par un robot d'archivage.
    msg["Auto-Submitted"] = "auto-generated"
    msg.set_content(TEXTE.format(code=code, minutes=config.DUREE_CODE_MINUTES))
    msg.add_alternative(HTML.format(code=code, minutes=config.DUREE_CODE_MINUTES), subtype="html")
    return msg


def envoyer_code(destinataire: str, code: str) -> None:
    """Envoie le code de réinitialisation, ou lève ErreurCourrier."""
    if not config.SMTP_HOTE:
        # Pas de serveur : le code va dans les journaux, et nulle part ailleurs.
        logger.warning("SMTP non configuré — code pour %s : %s", destinataire, code)
        return
    try:
        contexte = ssl.create_default_context()
        with smtplib.SMTP(config.SMTP_HOTE, config.SMTP_PORT, timeout=15) as serveur:
            serveur.ehlo()
            if serveur.has_extn("starttls"):
                serveur.starttls(context=contexte)
                serveur.ehlo()
            if config.SMTP_UTILISATEUR:
                serveur.login(config.SMTP_UTILISATEUR, config.SMTP_MOT_DE_PASSE)
            serveur.send_message(_message(destinataire, code))
    except (smtplib.SMTPException, OSError) as erreur:
        # Le message d'erreur du serveur peut contenir l'adresse : il va dans les
        # journaux, pas dans la réponse HTTP.
        logger.error("envoi du code impossible vers %s : %s", destinataire, erreur)
        raise ErreurCourrier("Le code n'a pas pu être envoyé. Réessaie dans un instant.") from erreur
