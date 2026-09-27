"""Taxonomie du systeme educatif beninois et textes de demonstration du seed."""

NIVEAUX_MATERNEL_PRIMAIRE = [
    "Maternelle 1", "Maternelle 2",
    "CI", "CP", "CE1", "CE2", "CM1", "CM2",
]

MATIERES_PRIMAIRE = {
    "Maternelle 1": ["Éveil", "Graphisme", "Langage", "Activités Manuelles"],
    "Maternelle 2": ["Éveil", "Graphisme", "Langage", "Activités Manuelles", "Pré-lecture"],
    "CI": ["Français", "Mathématiques", "Activités d'Éveil", "Éducation Civique et Morale"],
    "CP": ["Français", "Mathématiques", "Activités d'Éveil", "Éducation Civique et Morale"],
    "CE1": ["Français", "Mathématiques", "Sciences d'Observation", "Histoire-Géographie", "Éducation Civique et Morale", "EPS"],
    "CE2": ["Français", "Mathématiques", "Sciences d'Observation", "Histoire-Géographie", "Éducation Civique et Morale", "EPS"],
    "CM1": ["Français", "Mathématiques", "Sciences d'Observation", "Histoire-Géographie", "Éducation Civique et Morale", "EPS", "Anglais"],
    "CM2": ["Français", "Mathématiques", "Sciences d'Observation", "Histoire-Géographie", "Éducation Civique et Morale", "EPS", "Anglais"],
}

NIVEAUX_SECONDAIRE_TRONC_COMMUN = ["6ème", "5ème", "4ème", "3ème"]
MATIERES_TRONC_COMMUN = [
    "Français", "Mathématiques", "Anglais", "Histoire-Géographie",
    "Sciences de la Vie et de la Terre (SVT)", "Physique-Chimie",
    "Éducation Civique et Morale", "EPS",
]

# Séries générales (2nde/1ère/Terminale), nomenclature béninoise historique.
SERIES_GENERALES = {
    "A1": "Lettres-Langues",
    "A2": "Lettres-Philosophie",
    "B": "Sciences Économiques et Sociales",
    "C": "Mathématiques et Sciences Physiques",
    "D": "Mathématiques et Sciences de la Vie et de la Terre",
}
MATIERES_GENERAL_COMMUN = ["Français", "Anglais", "Philosophie", "EPS", "Histoire-Géographie"]
MATIERES_PAR_SERIE_GENERALE = {
    "A1": ["Littérature", "Latin/Espagnol", "Philosophie Approfondie"],
    "A2": ["Littérature", "Philosophie Approfondie", "Histoire-Géographie Approfondie"],
    "B": ["Sciences Économiques", "Mathématiques", "Comptabilité"],
    "C": ["Mathématiques", "Physique-Chimie", "Sciences de l'Ingénieur"],
    "D": ["Mathématiques", "SVT", "Physique-Chimie"],
}

# Séries techniques (nomenclature F = industrielle, G = administrative/gestion).
SERIES_TECHNIQUES = {
    "F2": "Électrotechnique",
    "F3": "Génie Civil",
    "F4": "Mécanique Générale",
    "G1": "Secrétariat / Bureautique",
    "G2": "Comptabilité-Gestion",
    "G3": "Techniques Commerciales",
}
NIVEAUX_TECHNIQUE_2ND_CYCLE = [
    "1ère année de lycée technique", "2ème année de lycée technique", "3ème année de lycée technique",
]
MATIERES_TECHNIQUE_COMMUN = ["Français", "Mathématiques", "Anglais", "Technologie Générale"]
MATIERES_PAR_SERIE_TECHNIQUE = {
    "F2": ["Électrotechnique", "Électronique", "Schémas Électriques"],
    "F3": ["Résistance des Matériaux", "Topographie", "Dessin du Bâtiment"],
    "F4": ["Mécanique Générale", "Usinage", "Dessin Industriel"],
    "G1": ["Bureautique", "Techniques de Secrétariat", "Correspondance Administrative"],
    "G2": ["Comptabilité Générale", "Mathématiques Financières", "Droit des Affaires"],
    "G3": ["Techniques Commerciales", "Économie d'Entreprise", "Marketing"],
}

NIVEAUX_UNIVERSITE = [
    "1ère année de Licence", "2ème année de Licence", "3ème année de Licence",
    "1ère année de Master", "2ème année de Master",
]

FILIERES_UNIVERSITE_PUBLIC = {
    "Droit et Sciences Politiques": ["Droit Civil", "Droit Constitutionnel", "Droit Pénal", "Procédure Civile", "Finances Publiques"],
    "Sciences Économiques et de Gestion": ["Microéconomie", "Macroéconomie", "Comptabilité Générale", "Statistiques", "Gestion Financière"],
    "Lettres Modernes": ["Littérature Française", "Linguistique", "Stylistique", "Littérature Africaine"],
    "Histoire et Archéologie": ["Histoire Contemporaine", "Archéologie Préhistorique", "Historiographie"],
    "Sciences Agronomiques": ["Agronomie Générale", "Zootechnie", "Pédologie", "Phytotechnie"],
    "Génie Civil": ["Résistance des Matériaux", "Béton Armé", "Topographie", "Hydraulique"],
    "Génie Électrique": ["Électrotechnique", "Automatisme", "Électronique de Puissance"],
    "Informatique et Télécommunications": ["Algorithmique", "Bases de Données", "Réseaux", "Systèmes d'Exploitation"],
    "Médecine": ["Anatomie", "Physiologie", "Biochimie", "Sémiologie"],
    "Sciences de la Vie et de la Terre": ["Botanique", "Zoologie", "Géologie", "Écologie"],
}
FILIERES_UNIVERSITE_PRIVE = {
    "Gestion des Entreprises": ["Management", "Comptabilité Générale", "Droit des Affaires", "Fiscalité"],
    "Informatique de Gestion": ["Algorithmique", "Bases de Données", "Génie Logiciel", "Réseaux"],
    "Marketing et Communication": ["Marketing Stratégique", "Communication d'Entreprise", "Étude de Marché"],
    "Banque et Finance": ["Analyse Financière", "Techniques Bancaires", "Marchés Financiers"],
    "Logistique et Transport": ["Gestion de la Chaîne Logistique", "Transport International", "Droit des Transports"],
    "Ressources Humaines": ["Gestion des Ressources Humaines", "Droit du Travail", "Psychologie du Travail"],
}

NOMS_ETABLISSEMENTS_EP = [
    "École Primaire Publique d'Akpakpa", "École Primaire Publique de Godomey",
    "École Primaire Publique de Sèmè-Kpodji", "École Primaire Publique de Parakou Centre",
    "École Primaire La Colombe", "Complexe Scolaire Les Flamboyants",
    "École Primaire Sainte-Rita", "Groupe Scolaire Excellence",
    "École Primaire Publique d'Abomey", "École Primaire Les Petits Génies",
]
NOMS_ETABLISSEMENTS_ES_GENERAL = [
    "Collège d'Enseignement Général de Cotonou", "Lycée Béhanzin",
    "Lycée Coulibaly", "Lycée Notre-Dame de Lourdes",
    "Collège Sainte-Jeanne d'Arc", "Lycée Mathieu Bouké",
    "CEG Godomey", "Lycée Toffa 1er",
]
NOMS_ETABLISSEMENTS_ES_TECHNIQUE = [
    "Lycée Technique Coulibaly", "Collège d'Enseignement Technique de Porto-Novo",
    "Lycée Professionnel Adjaha", "Institut Technique Saint-Joseph",
]
NOMS_ETABLISSEMENTS_UP_PUBLIC = [
    "Université Nationale des Sciences, Technologies, Ingénierie et Mathématiques",
    "Université de Parakou",
    "Institut National Supérieur de Technologie Industrielle",
]
NOMS_ETABLISSEMENTS_UP_PRIVE = [
    "Institut Supérieur de Management de Cotonou", "École Supérieure de Gestion et d'Informatique",
    "Institut Africain d'Informatique", "Haute École de Commerce du Bénin",
    "Institut Polytechnique Universitaire de Cotonou", "École Supérieure de Comptabilité et de Finance",
]

NOMS_FAMILLE = [
    "Dossou", "Adjovi", "Houngbo", "Kone", "Traore", "Agbo", "Zinsou", "Aissi", "Sossou", "Akakpo",
    "Gbaguidi", "Toko", "Amoussou", "Codjo", "Kpogbe", "Adande", "Hounkpe", "Dahoue", "Sagbo", "Koudjo",
    "Aholou", "Djossou", "Glele", "Assogba", "Tossou", "Hounsou", "Ahoyo", "Sonon", "Bokossa", "Idrissou",
    "Yacoubou", "Alassane", "Hounkonnou", "Chabi", "Gomina", "Sacca", "Baba", "Salifou", "Orou", "Tamou",
]
PRENOMS_MASCULINS = [
    "Kossi", "Moussa", "Kofi", "Eric", "Blaise", "Josue", "Firmin", "Wilfried", "Armel", "Bio",
    "Sena", "Comlan", "Judicael", "Romuald", "Cyrille", "Parfait", "Ulrich", "Landry", "Fabrice", "Ignace",
    "Herve", "Aristide", "Modeste", "Elisee", "Fortune", "Gildas", "Marcellin", "Severin", "Donatien", "Cedric",
]
PRENOMS_FEMININS = [
    "Awa", "Fatou", "Aisha", "Chantal", "Grace", "Clarisse", "Odette", "Prisca", "Nadege", "Bernice",
    "Solange", "Edwige", "Rosine", "Carole", "Huguette", "Estelle", "Divine", "Rafiatou", "Bintou", "Judith",
    "Reine", "Sidonie", "Colette", "Perpetue", "Viviane", "Berthine", "Sandrine", "Beatrice", "Aicha", "Latifa",
]

MOTIFS_CONTESTATION_RECRUTEMENT = [
    "Le document diplome a ete mal note par l'IA, la copie transmise etait pourtant lisible.",
    "Je conteste le score attribue a mon CV, mon experience n'a pas ete prise en compte.",
    "Erreur manifeste dans la notation automatique de mes pieces justificatives.",
]
MOTIFS_CONTESTATION_MICRO_JOB = [
    "Le travail livre ne correspond pas a ce qui avait ete convenu.",
    "La mission n'a pas ete terminee dans les delais annonces.",
    "Qualite du service tres en dessous de la description de l'offre.",
]

TITRES_OFFRES_MICRO_JOB = [
    "Cours particulier de mathematiques niveau college",
    "Soutien scolaire en francais pour eleve de CM2",
    "Preparation au baccalaureat serie D",
    "Cours d'anglais conversationnel",
    "Aide aux devoirs niveau primaire",
    "Initiation a l'informatique pour debutants",
    "Cours de comptabilite pour etudiants en gestion",
    "Repetition en physique-chimie niveau lycee",
    "Accompagnement redaction de memoire",
    "Cours de code et algorithmique pour lyceens",
    "Soutien en philosophie pour terminale",
    "Preparation aux concours d'entree en universite",
]

TITRES_EVENEMENTS = [
    "Kermesse de fin d'annee", "Journee culturelle de l'etablissement",
    "Remise des diplomes", "Spectacle de fin de trimestre",
    "Tournoi sportif inter-classes", "Soiree de gala des anciens eleves",
    "Journee portes ouvertes", "Concert de la chorale scolaire",
]


# ═══════════════════════════════════════════════════════════════════════════
# Université d'Abomey-Calavi (UAC) : toujours presente, quel que soit --scale.
# Premiere universite publique du Benin ; entites et filieres reelles (intitules
# simplifies), campus d'Abomey-Calavi.
# ═══════════════════════════════════════════════════════════════════════════

UAC_NOM = "Université d'Abomey-Calavi"
UAC_COORDONNEES = (6.4167, 2.3431)
UAC_DESCRIPTION = (
    "Première université publique du Bénin, l'Université d'Abomey-Calavi accueille ses "
    "étudiants sur le campus d'Abomey-Calavi, au sein de ses facultés, écoles et instituts : "
    "FADESP, FASEG, FLLAC, FAST, FSS, EPAC, IFRI."
)
# filiere affichee -> matieres ; licence pour toutes, master pour FILIERES_UAC_AVEC_MASTER.
FILIERES_UAC = {
    "Droit privé (FADESP)": ["Droit Civil", "Droit Pénal", "Procédure Civile", "Droit des Affaires OHADA"],
    "Sciences Économiques (FASEG)": ["Microéconomie", "Macroéconomie", "Statistiques", "Économie du Développement"],
    "Informatique (IFRI)": ["Algorithmique", "Bases de Données", "Réseaux", "Génie Logiciel"],
    "Génie Civil (EPAC)": ["Résistance des Matériaux", "Béton Armé", "Topographie", "Hydraulique"],
    "Médecine (FSS)": ["Anatomie", "Physiologie", "Biochimie", "Santé Publique"],
    "Lettres Modernes (FLLAC)": ["Littérature Africaine", "Linguistique", "Stylistique", "Littérature Française"],
    "Mathématiques (FAST)": ["Analyse", "Algèbre Linéaire", "Probabilités", "Topologie"],
}
FILIERES_UAC_AVEC_MASTER = ["Droit privé (FADESP)", "Sciences Économiques (FASEG)", "Informatique (IFRI)", "Génie Civil (EPAC)"]


# ═══════════════════════════════════════════════════════════════════════════
# Contenus pedagogiques : un vrai paragraphe de cours pour les matieres frequentes,
# pour qu'El Professor et la generation de quiz travaillent sur un contenu reel
# (repli generique pour les autres matieres).
# ═══════════════════════════════════════════════════════════════════════════

NOTIONS_PAR_MATIERE = {
    "Mathématiques": ("Le théorème de Pythagore", "Dans un triangle rectangle, le carré de l'hypoténuse est égal à la somme des carrés des deux autres côtés : si ABC est rectangle en A, alors BC² = AB² + AC². Réciproquement, si BC² = AB² + AC², le triangle est rectangle en A. Exemple : AB = 3 cm et AC = 4 cm donnent BC² = 9 + 16 = 25, donc BC = 5 cm. Méthode : identifier le plus grand côté, calculer séparément son carré et la somme des carrés des deux autres, puis comparer."),
    "Français": ("La proposition subordonnée relative", "Une proposition subordonnée relative complète un nom ou un pronom, appelé antécédent. Elle est introduite par un pronom relatif : qui, que, quoi, dont, où, lequel. Exemple : « Le livre que tu m'as prêté est passionnant » ; « que tu m'as prêté » complète l'antécédent « livre ». Le pronom relatif a une fonction dans la subordonnée : « qui » est sujet, « que » est complément d'objet direct, « dont » remplace un complément introduit par « de »."),
    "Anglais": ("The present perfect", "The present perfect links a past action to the present. Form: have/has + past participle. Use it for experiences (I have visited Porto-Novo), for actions that started in the past and continue (She has lived in Cotonou since 2020) and for recent results (They have finished their homework). With a finished time (yesterday, in 2019), use the simple past instead."),
    "Histoire-Géographie": ("Le royaume du Danxomè", "Fondé au XVIIe siècle sur le plateau d'Abomey, le royaume du Danxomè s'organise autour d'une monarchie puissante. Les rois, de Houégbadja à Béhanzin, développent une administration structurée, une armée comprenant les célèbres guerrières, et un art de cour remarquable (bas-reliefs, tentures appliquées). Béhanzin résiste à la conquête coloniale française de 1890 à 1894. Les palais royaux d'Abomey sont inscrits au patrimoine mondial de l'UNESCO."),
    "Physique-Chimie": ("La loi d'Ohm", "Pour un conducteur ohmique, la tension U à ses bornes est proportionnelle à l'intensité I du courant qui le traverse : U = R × I, avec U en volts (V), I en ampères (A) et R, la résistance, en ohms (Ω). Exemple : une résistance de 100 Ω traversée par un courant de 0,05 A a une tension de 5 V à ses bornes. On vérifie la loi en traçant U en fonction de I : on obtient une droite passant par l'origine."),
    "Sciences de la Vie et de la Terre (SVT)": ("La photosynthèse", "La photosynthèse permet aux plantes chlorophylliennes de fabriquer leur matière organique à partir de dioxyde de carbone et d'eau, en utilisant l'énergie lumineuse. Elle se déroule dans les chloroplastes des cellules des feuilles et rejette du dioxygène. Bilan : 6 CO₂ + 6 H₂O → C₆H₁₂O₆ + 6 O₂. Sans lumière, la photosynthèse s'arrête ; la respiration, elle, continue jour et nuit."),
    "SVT": ("La photosynthèse", "La photosynthèse permet aux plantes chlorophylliennes de fabriquer leur matière organique à partir de dioxyde de carbone et d'eau, grâce à l'énergie lumineuse, dans les chloroplastes. Bilan : 6 CO₂ + 6 H₂O → C₆H₁₂O₆ + 6 O₂. Sans lumière, elle s'arrête ; la respiration continue jour et nuit."),
    "Philosophie": ("La conscience", "La conscience est la connaissance plus ou moins claire que le sujet a de lui-même et du monde. Descartes en fait le fondement de toute certitude : « Je pense, donc je suis ». Mais Freud montre qu'une part de notre vie psychique échappe à la conscience : l'inconscient. La question est alors de savoir si nous sommes vraiment maîtres de nos pensées et de nos actes."),
    "Éducation Civique et Morale": ("Les droits et devoirs du citoyen", "La Constitution du Bénin du 11 décembre 1990 garantit des droits fondamentaux : droit à la vie, liberté d'expression, droit à l'éducation. Le citoyen a aussi des devoirs : respecter les lois, payer l'impôt, respecter le bien public et les droits d'autrui. Être citoyen, c'est aussi participer à la vie de la communauté, notamment par le vote à partir de 18 ans."),
    "Algorithmique": ("La recherche dichotomique", "La recherche dichotomique trouve une valeur dans un tableau TRIÉ en divisant à chaque étape l'intervalle de recherche par deux : on compare la valeur cherchée à l'élément du milieu, puis on poursuit dans la moitié gauche ou droite. Sa complexité est logarithmique, O(log n) : pour un million d'éléments, une vingtaine de comparaisons suffisent, contre un million pour une recherche séquentielle."),
    "Microéconomie": ("L'élasticité-prix de la demande", "L'élasticité-prix de la demande mesure la sensibilité de la quantité demandée à une variation du prix : e = variation relative de la quantité / variation relative du prix. Si |e| > 1, la demande est élastique : une hausse de prix fait baisser la recette. Si |e| < 1, elle est inélastique, comme pour les biens de première nécessité (riz, gari, carburant)."),
    "Droit Civil": ("Les conditions de validité du contrat", "Un contrat est valable si quatre conditions sont réunies : le consentement des parties, exempt de vices (erreur, dol, violence) ; leur capacité à contracter ; un objet certain et licite ; une cause licite. En l'absence de l'une d'elles, le contrat est frappé de nullité, absolue lorsque l'intérêt général est en jeu, relative lorsque seul l'intérêt d'une partie est protégé."),
}


def notion_pour(matiere: str) -> tuple[str, str]:
    """(titre du chapitre, contenu du cours) pour une matiere."""
    if matiere in NOTIONS_PAR_MATIERE:
        return NOTIONS_PAR_MATIERE[matiere]
    return (
        f"Introduction à : {matiere}",
        f"Ce chapitre présente les notions fondamentales de {matiere} : les définitions clés, "
        "des exemples résolus pas à pas, puis une synthèse des points à retenir avant l'évaluation. "
        "Chaque notion est illustrée par une situation tirée de la vie quotidienne au Bénin.",
    )


def telephone_benin(n: int) -> str:
    """Numero mobile beninois a 10 chiffres (format en vigueur depuis 2024), unique par n."""
    return f"+229 01 {90 + n % 10} {(n // 10) % 100:02d} {(n // 1000) % 100:02d} {(n // 100000) % 100:02d}"
