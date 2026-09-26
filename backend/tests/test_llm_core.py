"""Teste `_texte_ou_erreur` isolement, sans appel reseau reel a FreeLLM (aucun test de
ce projet n'exerce app/core/llm.py::FreeLLMClient directement - toujours substitue par
FakeLLMClient dans tests/conftest.py). Verrouille le garde-fou introduit pour un bug
reel observe en production : `response.choices[0]` levait IndexError quand FreeLLM
renvoyait une liste `choices` vide, non couvert par le `except OpenAIError` qui
n'entoure que l'appel HTTP - l'exception remontait alors jusqu'au handler Starlette par
defaut (sans la forme {"error": {...}} du contrat), que le frontend ne pouvait
qu'afficher comme un message generique de secours."""

from types import SimpleNamespace

import pytest

from app.core.llm import ElProfessorError, _texte_ou_erreur


def _reponse(choices):
    return SimpleNamespace(choices=choices)


def _choix(contenu):
    return SimpleNamespace(message=SimpleNamespace(content=contenu))


def test_texte_ou_erreur_extrait_le_contenu_du_premier_choix():
    reponse = _reponse([_choix("  Voici la reponse.  ")])
    assert _texte_ou_erreur(reponse, ElProfessorError) == "Voici la reponse."


def test_texte_ou_erreur_choices_vide_leve_l_erreur_dediee_plutot_qu_un_indexerror():
    reponse = _reponse([])
    with pytest.raises(ElProfessorError):
        _texte_ou_erreur(reponse, ElProfessorError)


def test_texte_ou_erreur_content_none_renvoie_chaine_vide_sans_lever():
    reponse = _reponse([_choix(None)])
    assert _texte_ou_erreur(reponse, ElProfessorError) == ""
