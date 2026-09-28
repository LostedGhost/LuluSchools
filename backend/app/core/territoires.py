"""Lot 7.6 — decoupage administratif du Benin : 12 departements, 77 communes.

Liste fermee (jamais de saisie libre) : les indicateurs du ministere se regroupent par
departement et par commune, une faute de frappe fausserait les totaux."""

DEPARTEMENTS: dict[str, tuple[str, ...]] = {
    "Alibori": ("Banikoara", "Gogounou", "Kandi", "Karimama", "Malanville", "Ségbana"),
    "Atacora": ("Boukoumbé", "Cobly", "Kérou", "Kouandé", "Matéri", "Natitingou", "Péhunco", "Tanguiéta", "Toucountouna"),
    "Atlantique": ("Abomey-Calavi", "Allada", "Kpomassè", "Ouidah", "Sô-Ava", "Toffo", "Tori-Bossito", "Zè"),
    "Borgou": ("Bembèrèkè", "Kalalé", "N'Dali", "Nikki", "Parakou", "Pèrèrè", "Sinendé", "Tchaourou"),
    "Collines": ("Bantè", "Dassa-Zoumè", "Glazoué", "Ouèssè", "Savalou", "Savè"),
    "Couffo": ("Aplahoué", "Djakotomey", "Dogbo", "Klouékanmè", "Lalo", "Toviklin"),
    "Donga": ("Bassila", "Copargo", "Djougou", "Ouaké"),
    "Littoral": ("Cotonou",),
    "Mono": ("Athiémé", "Bopa", "Comè", "Grand-Popo", "Houéyogbé", "Lokossa"),
    "Ouémé": ("Adjarra", "Adjohoun", "Aguégués", "Akpro-Missérété", "Avrankou", "Bonou", "Dangbo", "Porto-Novo", "Sèmè-Kpodji"),
    "Plateau": ("Adja-Ouèrè", "Ifangni", "Kétou", "Pobè", "Sakété"),
    "Zou": ("Abomey", "Agbangnizoun", "Bohicon", "Covè", "Djidja", "Ouinhi", "Zagnanado", "Za-Kpota", "Zogbodomey"),
}

assert len(DEPARTEMENTS) == 12 and sum(len(c) for c in DEPARTEMENTS.values()) == 77


def verifier_territoire(departement: str | None, commune: str | None) -> tuple[str | None, str | None]:
    """Valide le couple (departement, commune) ; leve ValueError (message utilisateur)."""
    if departement is None and commune is None:
        return None, None
    if departement not in DEPARTEMENTS:
        raise ValueError("Département inconnu : choisissez l'un des 12 départements du Bénin.")
    if commune is not None and commune not in DEPARTEMENTS[departement]:
        raise ValueError(f"La commune « {commune} » n'appartient pas au département {departement}.")
    return departement, commune
