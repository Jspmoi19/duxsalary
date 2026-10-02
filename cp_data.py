# cp_data.py — Structure compatible avec contrat_cdi_cdd.html
# Barèmes officiels 2026 — format original attendu par le template

CP_DATABASE = {
    'CP 336': {
        'meta': {
            'nom': 'Commission Paritaire 336 — Professions libérales',
            'type_travailleur': 'employé',
            'secteurs': ['Experts-comptables', 'Avocats', 'Architectes', 'Vétérinaires',
                        'Réviseurs d\'entreprises', 'Conseillers fiscaux', 'Huissiers'],
        },
        'duree_travail': {'heures_semaine': 38, 'heures_jour': 7.6},
        'baremes': {
            'Minimum sectoriel': {'horaire': 13.706, 'mensuel': 2254.30},
            'Professionnel libéral (103%)': {'horaire': 14.117, 'mensuel': 2321.93},
            'Étudiant (95%)': {'horaire': 13.021, 'mensuel': 2141.59},
        },
        'avantages': ['Transport ferroviaire : 80% du prix carte 2e classe',
                      'Indemnité vélo : 0,32 €/km'],
        'mentions_contrat': ['Loi du 3 juillet 1978', 'Accord sectoriel CP 336 2025-2026'],
        'fonds_formation': 'Liberform',
        'cct_applicables': ['Loi du 3 juillet 1978', 'Accord sectoriel CP 336'],
    },

    'CP 200': {
        'meta': {
            'nom': 'Commission Paritaire Auxiliaire pour Employés (CP 200)',
            'type_travailleur': 'employé',
            'secteurs': ['Informatique', 'Conseil', 'Services aux entreprises', 'Intérim'],
        },
        'duree_travail': {'heures_semaine': 38, 'heures_jour': 7.6},
        'baremes': {
            'Classe A — Sans qualification': {'horaire': 13.620, 'mensuel': 2242.81},
            'Classe B — Qualifié': {'horaire': 14.192, 'mensuel': 2336.25},
            'Classe C — Spécialisé': {'horaire': 14.393, 'mensuel': 2369.31},
            'Classe D — Hautement qualifié': {'horaire': 15.519, 'mensuel': 2555.73},
        },
        'avantages': ['Prime annuelle : 330,84 €', 'Intervention train : 100%'],
        'mentions_contrat': ['Loi du 3 juillet 1978', 'CCT CP 200'],
        'fonds_formation': 'Sociare',
        'cct_applicables': ['Loi du 3 juillet 1978', 'CCT CP 200'],
    },

    'CP 302': {
        'meta': {
            'nom': 'Commission Paritaire 302 — Industrie hôtelière (Horeca)',
            'type_travailleur': 'ouvrier',
            'secteurs': ['Restaurants', 'Hôtels', 'Cafés', 'Brasseries', 'Traiteurs',
                        'Fast-food', 'Catering'],
        },
        'duree_travail': {'heures_semaine': 38, 'heures_jour': 7.6},
        'baremes': {
            'Cat I & II — Sans qualification': {'horaire': 15.210, 'mensuel': 2504.53},
            'Cat III — Exécution qualifiée': {'horaire': 15.298, 'mensuel': 2519.02},
            'Cat IV — Fonctions qualifiées': {'horaire': 15.970, 'mensuel': 2629.69},
            'Cat V — Qualifiées confirmées': {'horaire': 16.885, 'mensuel': 2780.38},
            'Cat VI — Techniques/spécialisées': {'horaire': 17.332, 'mensuel': 2853.95},
            'Cat VII — À responsabilité': {'horaire': 19.706, 'mensuel': 3244.94},
            'Cat VIII — Encadrement': {'horaire': 21.230, 'mensuel': 3495.90},
            'Cat IX — Cadres/direction': {'horaire': 22.578, 'mensuel': 3717.86},
        },
        'avantages': ['Flexi-jobs autorisés', 'Extras possibles'],
        'mentions_contrat': ['Loi du 3 juillet 1978', 'CCT sectorielle CP 302'],
        'fonds_formation': 'Horecaforma',
        'cct_applicables': ['Loi du 3 juillet 1978', 'CCT sectorielle CP 302'],
    },

    'CP 124': {
        'meta': {
            'nom': 'Commission Paritaire 124 — Construction (ouvriers)',
            'type_travailleur': 'ouvrier',
            'secteurs': ['Bâtiment', 'Gros oeuvre', 'Parachèvement', 'Génie civil',
                        'Toiture', 'Peinture', 'Carrelage'],
        },
        'duree_travail': {'heures_semaine': 38, 'heures_jour': 7.6},
        'baremes': {
            'Cat I — Manoeuvre': {'horaire': 18.390, 'mensuel': 3028.22},
            'Cat IA — Premier manoeuvre': {'horaire': 19.138, 'mensuel': 3151.38},
            'Cat II — Spécialisé': {'horaire': 19.436, 'mensuel': 3200.44},
            'Cat IIA — Spécialisé élite': {'horaire': 20.406, 'mensuel': 3360.16},
            'Cat III — Qualifié 1er échelon': {'horaire': 20.669, 'mensuel': 3403.47},
            'Cat IV — Qualifié 2e échelon': {'horaire': 21.940, 'mensuel': 3612.57},
            'Chef d\'équipe A': {'horaire': 22.736, 'mensuel': 3743.64},
            'Chef d\'équipe B': {'horaire': 24.134, 'mensuel': 3973.97},
            'Contremaître': {'horaire': 26.328, 'mensuel': 4335.00},
        },
        'avantages': ['Timbres-fidélité Constructiv', 'Indemnité intempéries via Constructiv'],
        'mentions_contrat': ['Loi du 3 juillet 1978', 'CCT sectorielle Constructiv'],
        'fonds_formation': 'Constructiv',
        'cct_applicables': ['Loi du 3 juillet 1978', 'CCT CP 124 — Constructiv'],
    },

    'CP 121': {
        'meta': {
            'nom': 'Commission Paritaire 121 — Nettoyage',
            'type_travailleur': 'ouvrier',
            'secteurs': ['Nettoyage de bâtiments', 'Nettoyage industriel',
                        'Nettoyage de vitres', 'Ramassage immondices', 'Car-wash'],
        },
        # 37 h par semaine: salairesminimums.be, CP 1210000 au 01/07/2026 (« REGIME (sur base
        # hebdomadaire) : 37h ») -- corrige le 02/10/2026 (etait 36,5 h, sans source)
        'duree_travail': {'heures_semaine': 37, 'heures_jour': 7.4},
        'baremes': {
            'Cat 1A — Nettoyage habituel': {'horaire': 17.166, 'mensuel': 2826.29},
            'Cat 1B — Nettoyage avec difficulté': {'horaire': 17.701, 'mensuel': 2914.42},
            'Cat 2A — Nettoyage mi-lourd': {'horaire': 18.278, 'mensuel': 3009.41},
            'Cat 2E — Désinfection': {'horaire': 18.989, 'mensuel': 3126.52},
            'Cat 3A — Ramassage immondices': {'horaire': 19.515, 'mensuel': 3213.19},
            'Cat 3C — Chauffeur camion immondices': {'horaire': 20.533, 'mensuel': 3380.89},
            'Cat 4A — Laveur de vitres (0-7m anc.)': {'horaire': 19.378, 'mensuel': 3190.64},
            'Cat 4D — Laveur de vitres (18m+)': {'horaire': 20.524, 'mensuel': 3379.40},
            'Cat 8C — 1er opérateur': {'horaire': 22.992, 'mensuel': 3786.02},
            'Cat 10F — Hautement qualifié': {'horaire': 23.629, 'mensuel': 3890.89},
        },
        'avantages': ['Prime de fin d\'année : 9%', 'Chèques-repas (voir cheques_regles.py)',
                      'Indemnité RGPT : 1,63 €/jour', 'Travail de nuit : +3,11 €/h'],
        'mentions_contrat': ['Loi du 3 juillet 1978', 'CCT sectorielle CP 121 — 01/07/2026'],
        'fonds_formation': 'Fonds Social du Nettoyage',
        'cct_applicables': ['Loi du 3 juillet 1978', 'CCT CP 121 — barème 01/07/2026'],
    },

    'CP 140.03': {
        'meta': {
            'nom': 'Sous-Commission Paritaire 140.03 — Transport routier et logistique',
            'type_travailleur': 'ouvrier',
            'secteurs': ['Transport routier de marchandises', 'Logistique pour compte de tiers',
                        'Entreposage', 'Distribution', 'Chauffeurs poids lourds'],
        },
        'duree_travail': {'heures_semaine': 38, 'heures_jour': 7.6},
        'baremes': {
            'Personnel roulant — Niveau 1': {'horaire': 14.9255, 'mensuel': 2457.73},
            'Personnel roulant — Niveau 2': {'horaire': 15.4490, 'mensuel': 2543.94},
            'Personnel roulant — Niveau 3': {'horaire': 15.6285, 'mensuel': 2573.49},
            'Personnel roulant — Niveau 4': {'horaire': 15.8075, 'mensuel': 2602.97},
            'Personnel non roulant — Classe 1': {'horaire': 15.6465, 'mensuel': 2576.46},
            'Personnel non roulant — Classe 2': {'horaire': 16.3745, 'mensuel': 2696.33},
            'Personnel non roulant — Classe 3': {'horaire': 16.8015, 'mensuel': 2766.65},
            'Personnel non roulant — Classe 4': {'horaire': 17.2310, 'mensuel': 2837.37},
            'Personnel non roulant — Classe 5': {'horaire': 17.6625, 'mensuel': 2908.43},
            'Personnel non roulant — Classe 6': {'horaire': 18.0260, 'mensuel': 2968.28},
            'Personnel non roulant — Classe 8': {'horaire': 18.3915, 'mensuel': 3028.47},
            'Personnel de garage — Niveau A': {'horaire': 16.2360, 'mensuel': 2673.53},
            'Personnel de garage — Niveau B': {'horaire': 18.6680, 'mensuel': 3074.00},
            'Personnel de garage — Niveau C': {'horaire': 20.7120, 'mensuel': 3410.58},
            'Personnel de garage — Niveau D': {'horaire': 21.7245, 'mensuel': 3577.30},
            'Personnel de garage — Hors catégorie': {'horaire': 23.2605, 'mensuel': 3830.23},
        },
        'avantages': ['Indemnité RGPT sectorielle', 'Indemnité Arab',
                      'Chèques-repas (voir cheques_regles.py)', 'Vêtements de travail fournis'],
        'mentions_contrat': ['Loi du 3 juillet 1978', 'CCT SCP 140.03 2025-2026',
                             'Règlement CE 561/2006 (temps de conduite)'],
        'fonds_formation': 'FSTL — Fonds Social Transport et Logistique',
        'cct_applicables': ['Loi du 3 juillet 1978', 'CCT SCP 140.03', 'AR du 22/01/2010'],
    },
}


def _appliquer_baremes_officiels():
    """Les baremes des CP qui ont un bareme officiel charge (baremes_experience.py:
    salairesminimums.be) remplacent ceux ecrits ci-dessus -- une seule source pour les
    montants. Les montants ci-dessus ne servent plus que pour les CP sans bareme officiel."""
    from datetime import date
    from baremes_experience import (baremes_pour_formulaires, classe_de_categorie, grille_en_vigueur,
                                    horaire_de_mensuel)
    for cp_key, cp in CP_DATABASE.items():
        officiels = baremes_pour_formulaires(cp_key, date.today())
        if officiels:
            cp['baremes'] = officiels
        # CP avec grille par experience (CP 200): chaque classe prend le montant officiel a 0 an
        grille = grille_en_vigueur(cp_key, date.today())
        if grille:
            for libelle, valeurs in cp['baremes'].items():
                classe = classe_de_categorie(libelle, grille['classes'])
                if classe:
                    mensuel = grille['bareme_I'][0][grille['classes'].index(classe)]
                    valeurs.update(mensuel=mensuel, horaire=horaire_de_mensuel(mensuel, grille['heures_semaine']))


_appliquer_baremes_officiels()


def get_heures_semaine(cp_key):
    cp = CP_DATABASE.get(cp_key)
    return cp['duree_travail']['heures_semaine'] if cp else 38

def get_heures_jour(cp_key):
    cp = CP_DATABASE.get(cp_key)
    return cp['duree_travail'].get('heures_jour', 7.6) if cp else 7.6

def is_ouvrier(cp_key):
    cp = CP_DATABASE.get(cp_key)
    return cp['meta']['type_travailleur'] == 'ouvrier' if cp else False

def get_salaire_min(cp_key, categorie=None):
    cp = CP_DATABASE.get(cp_key)
    if not cp: return None
    baremes = cp.get('baremes', {})
    if categorie and categorie in baremes:
        return baremes[categorie]
    if baremes:
        return list(baremes.values())[0]
    return None

def calcul_preavis_semaines(anciennete_mois, est_employeur=True):
    if int(anciennete_mois or 0) < 3: return 1 if est_employeur else 1
    semaines_emp = min(anciennete_mois // 3 * 1, 62)
    if anciennete_mois > 24:
        semaines_emp = 8 + ((anciennete_mois // 12) - 2) * 6
    return semaines_emp if est_employeur else min(semaines_emp // 2, 13)
