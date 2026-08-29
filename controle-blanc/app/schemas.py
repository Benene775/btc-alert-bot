"""Modèles des requêtes envoyées par le navigateur.

Le navigateur est propriétaire de l'état (cours, réponses, fiches) : il le renvoie
à chaque appel. Le serveur ne garde que les compteurs et le corrigé en cours.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DemandeCode(BaseModel):
    """L'adresse, et rien d'autre. On ne demande ni nom, ni classe, ni âge :
    ce qu'on ne collecte pas ne peut ni fuiter ni être réclamé."""

    email: str = Field(max_length=320)


class DemandeEntree(BaseModel):
    email: str = Field(max_length=320)
    code: str = Field(max_length=16)


class Chapitre(BaseModel):
    titre: str = ""
    notions: list[str] = Field(default_factory=list)
    transcription: str = ""
    photos: list[int] = Field(default_factory=list)


class DemandeFiche(BaseModel):
    session_id: str
    niveau: str = "3e"
    chapitres: list[Chapitre]


class NotionFragile(BaseModel):
    notion: str
    chapitre: str = ""
    pourquoi: str = ""


class DemandeFicheCiblee(DemandeFiche):
    notions: list[NotionFragile] = Field(default_factory=list)


class DemandeControle(BaseModel):
    session_id: str
    niveau: str = "3e"
    matiere: str = "autre"
    chapitres: list[Chapitre]
    notions_ciblees: list[str] = Field(default_factory=list)
    enonces_deja_poses: list[str] = Field(default_factory=list)


class ReponseEleve(BaseModel):
    numero: int
    texte: str = ""
    secondes: int = 0


class DemandeCorrection(BaseModel):
    session_id: str
    controle_id: str
    niveau: str = "3e"
    chapitres: list[Chapitre]
    reponses: list[ReponseEleve]
    numeros_signales: list[int] = Field(default_factory=list)


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
