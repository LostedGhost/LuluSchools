"""Fichiers REELS du seed, televerses sur LuluFiles.

L'ancien seed referencait un identifiant fictif (000...0) partout : chaque lien de
fichier (cours PDF, sujet de devoir, copie, acte delivre, photo d'annonce) etait casse.
Ici, chaque document est genere (pymupdf, deja une dependance du backend) puis envoye
une seule fois a LuluFiles ; les enregistrements reutilisent ensuite son identifiant.

Sans LuluFiles joignable (poste de developpement sans cle, option --sans-fichiers), le
seed n'invente JAMAIS d'identifiant : les donnees qui exigent un fichier sont simplement
creees sans (cours au format texte, pas de photo d'annonce, etc.).
"""

from __future__ import annotations

import io
import math
import wave

import pymupdf as fitz

from app.core.files import FileStorageError, LuluFilesClient

VERT = (0.06, 0.39, 0.25)
ENCRE = (0.1, 0.12, 0.16)
GRIS = (0.45, 0.47, 0.5)


def _pdf(titre: str, sous_titre: str, paragraphes: list[str]) -> bytes:
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.draw_rect(fitz.Rect(0, 0, 595, 70), color=None, fill=VERT)
    page.insert_text((40, 45), "LuluSchools", fontsize=20, color=(1, 1, 1), fontname="helv")
    page.insert_textbox(fitz.Rect(40, 95, 555, 150), titre, fontsize=18, color=ENCRE, fontname="hebo")
    page.insert_textbox(fitz.Rect(40, 150, 555, 175), sous_titre, fontsize=11, color=GRIS, fontname="helv")
    y = 190
    for paragraphe in paragraphes:
        hauteur = 16 * (1 + len(paragraphe) // 85)
        page.insert_textbox(fitz.Rect(40, y, 555, y + hauteur + 20), paragraphe, fontsize=11, color=ENCRE, fontname="helv")
        y += hauteur + 18
    contenu = document.tobytes(garbage=3, deflate=True)
    document.close()
    return contenu


def _png(largeur: int, hauteur: int, dessiner) -> bytes:
    document = fitz.open()
    page = document.new_page(width=largeur, height=hauteur)
    dessiner(page)
    png = page.get_pixmap(dpi=96).tobytes("png")
    document.close()
    return png


def _photo_article(libelle: str, teinte: tuple[float, float, float]):
    def dessiner(page):
        page.draw_rect(page.rect, color=None, fill=teinte)
        page.draw_rect(fitz.Rect(90, 70, 390, 290), color=(1, 1, 1), fill=(0.97, 0.97, 0.95), width=2)
        page.insert_textbox(fitz.Rect(100, 150, 380, 230), libelle, fontsize=22, color=ENCRE, fontname="hebo", align=1)
    return dessiner


def _copie_manuscrite(lignes: list[str]):
    def dessiner(page):
        page.draw_rect(page.rect, color=None, fill=(0.99, 0.98, 0.94))
        for i in range(18):
            page.draw_line((30, 60 + i * 28), (570, 60 + i * 28), color=(0.7, 0.8, 0.95), width=0.6)
        page.draw_line((70, 30), (70, 560), color=(0.9, 0.4, 0.4), width=0.8)
        for i, ligne in enumerate(lignes):
            page.insert_text((80, 55 + i * 28), ligne, fontsize=15, color=(0.1, 0.2, 0.55), fontname="tiit")
    return dessiner


def _signature(variante: int):
    def dessiner(page):
        page.draw_rect(page.rect, color=None, fill=(1, 1, 1))
        points = [
            fitz.Point(30 + t * 3.4, 75 + 28 * math.sin(t / (6 + variante)) * math.cos(t / (13 + variante)))
            for t in range(100)
        ]
        page.draw_polyline(points, color=(0.05, 0.1, 0.35), width=2.4)
        page.draw_line((40, 120), (330, 118), color=(0.05, 0.1, 0.35), width=1.2)
    return dessiner


def _wav_carillon() -> bytes:
    """Court carillon (cours audio de demonstration) : 3 notes, 16 kHz mono."""
    frequence = 16000
    echantillons = bytearray()
    for note in (523.25, 659.25, 783.99):
        for i in range(int(frequence * 0.35)):
            enveloppe = 1 - i / (frequence * 0.35)
            valeur = int(9000 * enveloppe * math.sin(2 * math.pi * note * i / frequence))
            echantillons += valeur.to_bytes(2, "little", signed=True)
    tampon = io.BytesIO()
    with wave.open(tampon, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(frequence)
        w.writeframes(bytes(echantillons))
    return tampon.getvalue()


class Fichiers:
    """Televerse a la demande, une seule fois par cle ; renvoie None si indisponible."""

    def __init__(self, actif: bool) -> None:
        self.actif = actif
        self._client = LuluFilesClient() if actif else None
        self._cache: dict[str, str | None] = {}
        self.televerses = 0

    def _envoyer(self, cle: str, fabriquer, nom: str, type_contenu: str) -> str | None:
        if not self.actif:
            return None
        if cle not in self._cache:
            try:
                self._cache[cle] = self._client.upload(fabriquer(), nom, type_contenu)
                self.televerses += 1
            except FileStorageError as exc:
                # Premier echec : LuluFiles est considere indisponible pour tout le seed,
                # plutot que de melanger donnees avec et sans fichiers au hasard des erreurs.
                print(f"  ! LuluFiles indisponible ({exc}) : suite du seed sans fichiers.")
                self.actif = False
                self._cache[cle] = None
        return self._cache[cle]

    def verifier(self) -> None:
        """Televerse un petit fichier de test pour savoir des le depart si LuluFiles repond."""
        self._envoyer("sonde", lambda: _pdf("Test", "Vérification LuluFiles", ["Seed LuluSchools."]), "sonde.pdf", "application/pdf")

    def cours_pdf(self, matiere: str, titre: str, contenu: str, niveau: str) -> str | None:
        return self._envoyer(
            f"cours:{matiere}",  # un support par matiere, partage entre niveaux (moins de televersements)
            lambda: _pdf(titre, f"Support de cours — {matiere}", [contenu, "À retenir : relis les exemples et entraîne-toi sur les exercices du manuel."]),
            f"cours-{matiere}.pdf",
            "application/pdf",
        )

    def cours_audio(self) -> str | None:
        return self._envoyer("cours:audio", _wav_carillon, "cours-audio.wav", "audio/wav")

    def sujet_devoir(self, matiere: str, titre: str, enonces: list[str]) -> str | None:
        return self._envoyer(
            f"sujet:{matiere}",
            lambda: _pdf(titre, f"Sujet — {matiere}", [f"Question {i + 1}. {e}" for i, e in enumerate(enonces)]),
            f"sujet-{matiere}.pdf",
            "application/pdf",
        )

    def copie(self, variante: int) -> str | None:
        lignes = [
            ["Exercice 1 :", "On applique la formule du cours,", "donc le résultat est justifié.", "Exercice 2 :", "Je détaille chaque étape."],
            ["Question 1 :", "D'après la définition vue en classe,", "la réponse est la suivante.", "Question 2 :", "Conclusion : voir ci-dessus."],
            ["Réponse :", "Je commence par poser les données,", "puis je calcule pas à pas.", "Vérification faite.", "Fin de la copie."],
        ][variante % 3]
        return self._envoyer(f"copie:{variante % 3}", lambda: _png(600, 560, _copie_manuscrite(lignes)), "copie.png", "image/png")

    def signature(self, variante: int) -> str | None:
        return self._envoyer(f"signature:{variante % 4}", lambda: _png(360, 150, _signature(variante % 4)), "signature.png", "image/png")

    def piece_candidature(self, type_document: str, variante: int) -> str | None:
        titre = {"cv": "Curriculum vitae", "diplome": "Diplôme"}.get(type_document, type_document)
        return self._envoyer(
            f"candidature:{type_document}:{variante % 3}",
            lambda: _pdf(titre, "Pièce jointe à une candidature (données de démonstration)", [
                "Formation : licence puis certificat d'aptitude pédagogique.",
                "Expérience : plusieurs années d'enseignement dans des établissements publics et privés du Bénin.",
            ]),
            f"{type_document}.pdf",
            "application/pdf",
        )

    def acte(self, nom_acte: str) -> str | None:
        return self._envoyer(
            f"acte:{nom_acte}",
            lambda: _pdf(nom_acte, "Document officiel délivré par l'établissement (démonstration)", [
                f"Le chef d'établissement certifie la délivrance de ce document : {nom_acte}.",
                "Document établi pour servir et valoir ce que de droit.",
            ]),
            "acte.pdf",
            "application/pdf",
        )

    def photo_article(self, categorie: str, libelle: str, teinte: tuple[float, float, float]) -> str | None:
        return self._envoyer(f"article:{categorie}", lambda: _png(480, 360, _photo_article(libelle, teinte)), "article.png", "image/png")

    def capture_tableau(self, cle: str, png: bytes) -> str | None:
        return self._envoyer(f"tableau:{cle}", lambda: png, "tableau.png", "image/png")
