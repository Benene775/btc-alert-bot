"""Modèles des requêtes envoyées par le navigateur.

Le navigateur est propriétaire de l'état (cours, réponses, fiches) : il le renvoie
à chaque appel. Le serveur ne garde que les compteurs et le corrigé en cours.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class Inscription(BaseModel):
    """Ce qu'on demande à l'inscription, et rien de plus.

    Le prénom et la classe ne sont pas de la curiosité : le premier nomme sa
    page, la seconde règle le niveau des contrôles. Ni nom de famille, ni date
    de naissance, ni établissement — ce qu'on ne collecte pas ne peut ni fuiter
    ni être réclamé.
    """

    email: str = Field(max_length=320)
    mot_de_passe: str = Field(max_length=256)
    prenom: str = Field(default="", max_length=80)
    niveau: str = Field(default="", max_length=16)


class Connexion(BaseModel):
    email: str = Field(max_length=320)
    mot_de_passe: str = Field(max_length=256)


class DemandeCode(BaseModel):
    """Mot de passe oublié : on n'a que l'adresse pour reconnaître l'élève."""

    email: str = Field(max_length=320)


class Reinitialisation(BaseModel):
    email: str = Field(max_length=320)
    code: str = Field(max_length=16)
    mot_de_passe: str = Field(max_length=256)


# Bornes du cours renvoyé par le navigateur.
#
# Ce texte part au modèle en entrée, à chaque appel de la séance : sans plafond,
# un appel coûte ce que le navigateur décide, et le quota compte quand même
# « une fiche ». Ce n'est pas une question de mauvaise volonté — un élève qui
# photographie tout son trimestre d'un coup produit le même effet.
#
# Les valeurs sont calées sur l'usage réel : une page de cahier transcrite fait
# environ 500 caractères, dense elle en fait 2 000, et une analyse porte au plus
# douze photos. Le total autorisé représente donc largement plus qu'un trimestre
# de cours, tout en bornant ce qu'un appel peut coûter.
MAX_CAR_TRANSCRIPTION = 60_000      # ≈ 30 pages denses pour un seul chapitre
MAX_CHAPITRES = 40
MAX_CAR_COURS_TOTAL = 200_000       # ≈ 54 000 tokens, soit ~11 c$ l'appel sur Sonnet


class Chapitre(BaseModel):
    titre: str = Field(default="", max_length=300)
    notions: list[str] = Field(default_factory=list, max_length=80)
    transcription: str = Field(default="", max_length=MAX_CAR_TRANSCRIPTION)
    photos: list[int] = Field(default_factory=list, max_length=200)


class AvecCours(BaseModel):
    """Le socle des requêtes qui renvoient le cours de l'élève.

    Les bornes par champ ne suffisent pas : quarante chapitres au plafond
    feraient encore 2,4 millions de caractères. C'est le total qui décide du
    prix d'un appel, donc c'est lui qu'on plafonne.
    """

    chapitres: list[Chapitre] = Field(max_length=MAX_CHAPITRES)

    @model_validator(mode="after")
    def _cours_pas_trop_gros(self):
        total = sum(len(c.transcription) for c in self.chapitres)
        if total > MAX_CAR_COURS_TOTAL:
            raise ValueError(
                f"cours trop volumineux ({total} caractères, "
                f"{MAX_CAR_COURS_TOTAL} au maximum) : choisis moins de chapitres"
            )
        return self


class DemandeFiche(AvecCours):
    session_id: str
    niveau: str = "3e"


class NotionFragile(BaseModel):
    notion: str = Field(max_length=300)
    chapitre: str = Field(default="", max_length=300)
    pourquoi: str = Field(default="", max_length=1_000)


class DemandeFicheCiblee(DemandeFiche):
    notions: list[NotionFragile] = Field(default_factory=list, max_length=80)


class DemandeControle(AvecCours):
    session_id: str
    niveau: str = "3e"
    matiere: str = "autre"
    notions_ciblees: list[str] = Field(default_factory=list, max_length=80)
    enonces_deja_poses: list[str] = Field(default_factory=list, max_length=200)


class ReponseEleve(BaseModel):
    numero: int
    # La copie de l'élève repart au modèle pour la correction : elle est bornée
    # comme le reste. Une réponse de contrôle tient largement là-dedans.
    texte: str = Field(default="", max_length=5_000)
    secondes: int = 0


class DemandeCorrection(AvecCours):
    session_id: str
    controle_id: str
    niveau: str = "3e"
    reponses: list[ReponseEleve] = Field(max_length=100)
    numeros_signales: list[int] = Field(default_factory=list, max_length=100)


class SignalementQuestion(BaseModel):
    session_id: str
    controle_id: str = ""
    numero: int
    enonce: str = ""
    motif: str = ""


class Evenement(BaseModel):
    session_id: str
    type: str
    details: dict = Field(default_factory=dict)


class ContexteSession(BaseModel):
    session_id: str
    niveau: str = ""
    matiere: str = ""
    date_controle: str = ""
