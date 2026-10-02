# -*- coding: utf-8 -*-
"""
baremes_experience.py -- DuxSalary
Baremes minimums par CLASSE / CATEGORIE et ANNEES D'EXPERIENCE, versionnes par
date. Une nouvelle indexation = une nouvelle entree dans la liste de la CP (on ne
supprime ni n'ecrase jamais une ancienne version).

Deux structures:
  - BAREMES_EXPERIENCE: grille par classe et annees d'experience (CP 200) ;
  - BAREMES_CATEGORIES (plus bas): baremes par categorie des CP 336, 140.03 et 121.

SOURCE UNIQUE: Banque de donnees Salaires minimums du SPF Emploi
(salairesminimums.be), PDF deposes par Leo dans sources/baremes/. Les montants
sont extraits des PDF par programme, jamais recopies a la main.
CP 200 (01/01/2026, indexation +2,21 %): grille officielle chargee le 02/10/2026.
Elle remplace la grille lue la veille dans deux publications syndicales (CSC,
CGSLB/Synova), qui differait de 1 a 3 centimes sur 149 montants sur 228.
Regles de la CP 200 (PDF officiel): bareme « a partir de la 1ere annee d'entree
en service », bareme « employes actifs depuis 1 an dans la meme entreprise »,
bareme des etudiants de moins de 21 ans selon l'age (16 a 20 ans).
"""
import re
from datetime import date

BAREMES_EXPERIENCE = {
    'CP 200': [{
        'date_debut': date(2026, 1, 1),
        'source': 'salairesminimums.be, CP 2000000 CP auxiliaire pour employés, au 01/01/2026',
        'classes': ('A', 'B', 'C', 'D'),
        'heures_semaine': 38,
        # annees d'experience: (classe A, B, C, D) en EUR par mois, temps plein
        'bareme_I': {
            0: (2242.80, 2336.26, 2369.30, 2555.72),
            1: (2249.57, 2349.65, 2369.30, 2572.63),
            2: (2256.27, 2363.08, 2422.72, 2589.24),
            3: (2263.05, 2376.60, 2469.69, 2606.20),
            4: (2269.88, 2394.82, 2516.65, 2671.94),
            5: (2276.53, 2413.36, 2563.77, 2730.42),
            6: (2283.28, 2427.37, 2610.74, 2788.81),
            7: (2289.95, 2462.42, 2657.88, 2847.07),
            8: (2297.17, 2497.55, 2705.04, 2905.53),
            9: (2315.81, 2532.54, 2752.17, 2963.63),
            10: (2334.52, 2567.80, 2799.16, 3022.34),
            11: (2350.42, 2597.47, 2846.25, 3080.45),
            12: (2366.17, 2626.79, 2893.28, 3139.01),
            13: (2382.16, 2656.47, 2930.46, 3197.29),
            14: (2397.80, 2685.87, 2967.49, 3255.72),
            15: (2413.36, 2715.46, 3004.68, 3304.78),
            16: (2428.83, 2725.04, 3041.72, 3353.78),
            17: (2444.37, 2734.54, 3078.86, 3402.77),
            18: (2459.90, 2744.25, 3089.43, 3451.90),
            19: (2459.90, 2753.78, 3100.06, 3500.99),
            20: (2459.90, 2763.40, 3110.73, 3518.35),
            21: (2459.90, 2773.17, 3121.59, 3535.83),
            22: (2459.90, 2782.63, 3132.27, 3553.29),
            23: (2459.90, 2792.24, 3143.20, 3570.59),
            24: (2459.90, 2801.83, 3153.91, 3587.83),
            25: (2459.90, 2811.38, 3164.85, 3605.11),
            26: (2459.90, 2821.00, 3175.60, 3622.42),
        },
        'bareme_II': {
            1: (2310.29, 2413.08, 2433.27, 2642.08),
            2: (2317.18, 2426.87, 2488.15, 2659.15),
            3: (2324.15, 2440.76, 2536.36, 2676.54),
            4: (2330.81, 2459.31, 2584.73, 2744.49),
            5: (2337.66, 2478.44, 2633.21, 2804.73),
            6: (2344.44, 2492.89, 2681.48, 2864.70),
            7: (2351.34, 2528.89, 2730.02, 2924.78),
            8: (2358.93, 2565.14, 2778.59, 2984.79),
            9: (2378.06, 2601.10, 2827.02, 3044.74),
            10: (2397.32, 2637.36, 2875.48, 3105.00),
            11: (2413.72, 2667.85, 2923.84, 3164.93),
            12: (2429.90, 2698.00, 2972.19, 3225.07),
            13: (2446.31, 2728.53, 3010.43, 3285.12),
            14: (2462.42, 2758.86, 3048.50, 3345.24),
            15: (2478.44, 2789.20, 3086.76, 3395.69),
            16: (2494.34, 2799.06, 3124.96, 3446.06),
            17: (2510.25, 2808.86, 3163.18, 3496.57),
            18: (2526.17, 2818.89, 3174.02, 3547.02),
            19: (2526.17, 2828.75, 3184.93, 3597.56),
            20: (2526.17, 2838.67, 3195.98, 3615.46),
            21: (2526.17, 2848.50, 3207.13, 3633.39),
            22: (2526.17, 2858.33, 3218.09, 3651.34),
            23: (2526.17, 2868.35, 3229.43, 3669.27),
            24: (2526.17, 2878.14, 3240.48, 3686.97),
            25: (2526.17, 2887.97, 3251.74, 3704.66),
            26: (2526.17, 2897.81, 3262.72, 3722.54),
        },
        # age: classes disponibles dans l'ordre A, B, C, D (16 et 17 ans: A et B seulement)
        'etudiants': {
            16: (1447.01, 1504.51),
            17: (1635.97, 1702.00),
            18: (1824.77, 1899.72, 2060.46, 2262.46),
            19: (1975.81, 2057.87, 2234.09, 2406.41),
            20: (2051.39, 2136.83, 2320.65, 2491.56),
        },
    }],
}


def grille_en_vigueur(cp_key, reference_date):
    """Version de la grille applicable a la date, ou None (CP sans grille, ou date anterieure)."""
    versions = [v for v in BAREMES_EXPERIENCE.get(cp_key, []) if v['date_debut'] <= reference_date]
    return max(versions, key=lambda v: v['date_debut']) if versions else None


def classe_de_categorie(categorie, classes=('A', 'B', 'C', 'D')):
    """« Classe B — Qualifié » -> 'B'. None si la categorie ne designe pas une classe."""
    m = re.search(r'\bclasse\s+([A-Z])\b', categorie or '', re.I)
    return m.group(1).upper() if m and m.group(1).upper() in classes else None


def horaire_de_mensuel(mensuel, heures_semaine):
    """Salaire horaire equivalent a un salaire mensuel temps plein (x 12 / 52 / heures par semaine)."""
    return round(mensuel * 12 / 52 / heures_semaine, 4)


def minimum_experience(cp_key, reference_date, categorie=None, annees_experience=None,
                       anciennete_mois=None, is_etudiant=False, age=None):
    """Minimum de la grille par experience. Retourne (minimum, raison) comme
    minimums_cp.minimum_cp ; (None, None) si la CP n'a pas de grille a cette date."""
    g = grille_en_vigueur(cp_key, reference_date)
    if g is None:
        return None, None
    notes = []
    classe = classe_de_categorie(categorie, g['classes'])
    if classe is None:
        classe = g['classes'][0]
        notes.append(f"classe non précisée dans le contrat : classe {classe}")
    i = g['classes'].index(classe)

    if is_etudiant and age is not None and age in g['etudiants']:
        ligne = g['etudiants'][age]
        if i >= len(ligne):
            return None, (f"Barème des étudiants de la {cp_key} : pas de montant pour la classe {classe} à {age} ans, "
                          f"salaire non contrôlé.")
        mensuel, libelle = ligne[i], f"Barème des étudiants, {age} ans, classe {classe}"
    else:
        if is_etudiant:
            notes.append("âge de l'étudiant inconnu : barème ordinaire" if age is None
                         else "étudiant hors barème des étudiants (16 à 20 ans) : barème ordinaire")
        if annees_experience is None:
            annees_experience = 0
            notes.append("années d'expérience non renseignées : 0 an")
        deuxieme_annee = anciennete_mois is not None and anciennete_mois >= 12
        bareme = g['bareme_II'] if deuxieme_annee else g['bareme_I']
        annees = max(min(bareme), min(int(annees_experience), max(bareme)))
        mensuel = bareme[annees][i]
        libelle = (f"Classe {classe}, {annees} an{'s' if annees > 1 else ''} d'expérience, "
                   f"barème {'II (après un an dans l’entreprise)' if deuxieme_annee else 'I (première année dans l’entreprise)'}")
    return {'horaire': horaire_de_mensuel(mensuel, g['heures_semaine']), 'mensuel': mensuel, 'categorie': libelle,
            'depuis': g['date_debut'], 'source': g['source'], 'note': ', '.join(notes) or None}, None


# ─────────────────────────────────────────────────────────────────
# BAREMES OFFICIELS PAR CATEGORIE (sans grille d'annees d'experience)
# ─────────────────────────────────────────────────────────────────
# Source: Banque de donnees Salaires minimums du SPF Emploi (salairesminimums.be),
# PDF deposes par Leo dans sources/baremes/ le 01/10/2026. Montants extraits des
# PDF par programme (aucune recopie a la main) ; seuls les libelles sont ecrits ici.
# Une nouvelle indexation = une nouvelle version dans la liste de la CP.
BAREMES_CATEGORIES = {
    'CP 336': [{
        'date_debut': date(2026, 9, 1),
        'source': 'salairesminimums.be, CP 3360000 Professions libérales, au 01/09/2026',
        'heures_semaine': 38, 'unite': 'mensuel',
        'categories': {
            'Minimum sectoriel': 2254.30,
            "Minimum d'entrée": 2321.93,
        },
        # « Etudiants ou travailleurs qui beneficient d'un regime de formation d'alternance »
        'etudiants': {'mensuel': 2141.59},
        'alias': {'Professionnel libéral (103%)': "Minimum d'entrée"},
    }],
    'CP 140.03': [{
        'date_debut': date(2026, 1, 1),
        'source': 'salairesminimums.be, SCP 1400300 Transport routier et logistique pour compte de tiers, au 01/01/2026',
        'heures_semaine': 38, 'unite': 'horaire',
        # regime « jours de repos compensatoire non payes ou effectivement 38 h/semaine »
        'categories': {
            'Personnel roulant — Niveau 1': 14.9255,
            'Personnel roulant — Niveau 2': 15.4490,
            'Personnel roulant — Niveau 3': 15.6285,
            'Personnel roulant — Niveau 4': 15.8075,
            'Personnel non roulant — Classe 1': 15.6465,
            'Personnel non roulant — Classe 2': 16.3745,
            'Personnel non roulant — Classe 3': 16.8015,
            'Personnel non roulant — Classe 4': 17.2310,
            'Personnel non roulant — Classe 5': 17.6625,
            'Personnel non roulant — Classe 6': 18.0260,
            'Personnel non roulant — Classe 8': 18.3915,
            'Personnel de garage — Niveau A': 16.2360,
            "Personnel de garage — Niveau A.1 (10 ans d'ancienneté)": 16.9745,
            "Personnel de garage — Niveau A.1 (20 ans d'ancienneté)": 17.8285,
            'Personnel de garage — Niveau A.2': 16.9745,
            "Personnel de garage — Niveau A.2 (10 ans d'ancienneté)": 17.8285,
            "Personnel de garage — Niveau A.2 (20 ans d'ancienneté)": 18.6680,
            'Personnel de garage — Niveau B': 18.6680,
            'Personnel de garage — Niveau C': 20.7120,
            'Personnel de garage — Niveau D': 21.7245,
            'Personnel de garage — Hors catégorie': 23.2605,
        },
        # regime « jours de repos compensatoire payes » (salaire horaire plus bas)
        'categories_repos_payes': {
            'Personnel roulant — Niveau 1': 14.5425,
            'Personnel roulant — Niveau 2': 15.0525,
            'Personnel roulant — Niveau 3': 15.2280,
            'Personnel roulant — Niveau 4': 15.4025,
            'Personnel non roulant — Classe 1': 15.2435,
            'Personnel non roulant — Classe 2': 15.9530,
            'Personnel non roulant — Classe 3': 16.3735,
            'Personnel non roulant — Classe 4': 16.7895,
            'Personnel non roulant — Classe 5': 17.2095,
            'Personnel non roulant — Classe 6': 17.5635,
            'Personnel non roulant — Classe 8': 17.9200,
            'Personnel de garage — Niveau A': 15.9460,
            "Personnel de garage — Niveau A.1 (10 ans d'ancienneté)": 16.5545,
            "Personnel de garage — Niveau A.1 (20 ans d'ancienneté)": 17.3790,
            'Personnel de garage — Niveau A.2': 16.5545,
            "Personnel de garage — Niveau A.2 (10 ans d'ancienneté)": 17.3790,
            "Personnel de garage — Niveau A.2 (20 ans d'ancienneté)": 18.2060,
            'Personnel de garage — Niveau B': 18.2060,
            'Personnel de garage — Niveau C': 20.1905,
            'Personnel de garage — Niveau D': 21.1900,
            'Personnel de garage — Hors catégorie': 22.6815,
        },
        # « 90 p.c. du salaire horaire pour la fonction exercee »
        'etudiants': {'pourcentage': 0.90},
        'alias': {},
    }],
    'CP 121': [{
        'date_debut': date(2026, 7, 1),
        'source': 'salairesminimums.be, CP 1210000 Nettoyage, au 01/07/2026',
        'heures_semaine': 37, 'unite': 'horaire',   # « REGIME (sur base hebdomadaire) : 37h »
        'categories': {
            '1.A. Nettoyage habituel': 17.1660,
            '1.B. Nettoyage spécial': 17.7010,
            '1.C. Nettoyage du métro, des ateliers de montage et de carrosserie (hors production)': 17.8690,
            '1.D. Nettoyage des ateliers de montage et de carrosserie (pendant la production)': 18.2305,
            '2.A. Nettoyage mi-lourd': 18.2775,
            "2.B. Nettoyage de wagons, de bus et d'avions": 18.8010,
            "2.C. Nettoyage de wagons, de bus et d'avions (à l'extérieur)": 19.0140,
            '2.D. Dégraissage, nettoyage et désinfection de véhicules neufs': 18.8010,
            '2.E. Désinfection': 18.9890,
            '2.F. Nettoyage de conteneurs-IBC et de fûts': 17.4920,
            "3.A. Collecte de déchets, vidange et nettoyage d'égouts": 19.5145,
            '3.B. Nettoyage mi-lourd (déchets)': 19.3775,
            '3.C. Conduite de véhicules de collecte de déchets': 20.5325,
            '3.D. Chauffeur-mécanicien de véhicules de déchets': 21.0555,
            '3.E. Conduite de compacteur sur décharge': 21.7190,
            '4.A. Laveur de vitres qualifié (0 mois dans la profession)': 19.3775,
            '4.B. Laveur de vitres qualifié (8 mois)': 19.8540,
            '4.C. Laveur de vitres qualifié (12 mois)': 20.1875,
            '4.D. Laveur de vitres qualifié (18 mois)': 20.5235,
            '5. Chauffeur occupé exclusivement au transport du personnel': 17.4160,
            '6. Car-wash': 18.6565,
            '7.A. Ramoneur (0 mois dans la profession)': 19.3775,
            '7.B. Ramoneur (9 mois)': 19.8540,
            '7.C. Ramoneur (17 mois)': 20.1875,
            '7.D. Ramoneur (25 mois)': 20.5235,
            '8. Nettoyage industriel — manœuvre sans formation professionnelle': 18.8680,
            '8.A. Nettoyage industriel — manœuvre': 20.0980,
            '8.B. Nettoyage industriel — 2e opérateur sans permis C': 20.4630,
            '8.B1. Nettoyage industriel — 2e opérateur avec permis C': 20.4630,
            "8.B2. Nettoyage industriel — 6 mois d'ancienneté en 8.B1": 21.0290,
            "8.B3. Nettoyage industriel — 6 mois d'ancienneté en 8.B2": 21.5435,
            "8.B4. Nettoyage industriel — 12 mois d'ancienneté en 8.B3": 22.1215,
            '8.C. Nettoyage industriel — 1er opérateur exécutant': 22.9920,
            '8.F. Nettoyage industriel — contrôleur': 21.0290,
            "10.A. Centre d'enfouissement — manœuvre": 20.1470,
            "10.B. Centre d'enfouissement — manœuvre spécialisé": 20.7250,
            "10.C. Centre d'enfouissement — ouvrier spécialisé": 21.3950,
            "10.D. Centre d'enfouissement — opérateur d'engins": 22.8710,
            "10.E. Centre d'enfouissement — ouvrier qualifié": 22.9625,
            "10.F. Centre d'enfouissement — ouvrier hautement qualifié": 23.6290,
        },
        'etudiants': None,   # pas de bareme des etudiants dans le PDF: bareme ordinaire
        'alias': {},
        'majorations': "Chef d'équipe : +10 % ; brigadier : +5 % en sus du salaire normal des ouvriers exécutants (non calculé par l'outil)",
    }],
}


LIBELLE_ETUDIANTS = 'Étudiants et formation en alternance'


def baremes_pour_formulaires(cp_key, reference_date):
    """Categories officielles au format de cp_data ({libelle: {horaire, mensuel}}), pour les
    listes des formulaires de contrat. None si la CP n'a pas de bareme officiel a cette date."""
    v = bareme_categories_en_vigueur(cp_key, reference_date)
    if v is None:
        return None
    res = {}
    for libelle, montant in v['categories'].items():
        if v['unite'] == 'mensuel':
            res[libelle] = {'horaire': horaire_de_mensuel(montant, v['heures_semaine']), 'mensuel': montant}
        else:
            res[libelle] = {'horaire': montant, 'mensuel': round(montant * v['heures_semaine'] * 52 / 12, 2)}
    if v.get('etudiants') and 'mensuel' in v['etudiants']:
        m = v['etudiants']['mensuel']
        res[LIBELLE_ETUDIANTS] = {'horaire': horaire_de_mensuel(m, v['heures_semaine']), 'mensuel': m}
    return res


def bareme_categories_en_vigueur(cp_key, reference_date):
    versions = [v for v in BAREMES_CATEGORIES.get(cp_key, []) if v['date_debut'] <= reference_date]
    return max(versions, key=lambda v: v['date_debut']) if versions else None


def _code_categorie(libelle):
    """Code d'une categorie, pour reconnaitre un ancien libelle de contrat:
    « Cat 1A — Nettoyage habituel » et « 1.A. Nettoyage habituel » -> '1A' ;
    « Personnel roulant — Niveau 2 » -> libelle complet en minuscules."""
    t = (libelle or '').strip()
    m = re.match(r'(?:cat\.?\s*)?(\d{1,2})\.?\s?([A-F])?\.?(\d)?(?![\d,])', t, re.I)
    if m:
        return (m.group(1) + (m.group(2) or '') + (m.group(3) or '')).upper()
    return t.lower()


def trouver_categorie(version, categorie):
    """Libelle officiel correspondant a la categorie d'un contrat (libelle exact,
    alias d'un ancien libelle, ou meme code), sinon None."""
    if not categorie:
        return None
    if categorie in version['categories']:
        return categorie
    if categorie in version.get('alias', {}):
        return version['alias'][categorie]
    code = _code_categorie(categorie)
    for libelle in version['categories']:
        if _code_categorie(libelle) == code:
            return libelle
    return None


def minimum_categorie(cp_key, reference_date, categorie=None, is_etudiant=False):
    """Minimum officiel par categorie. Retourne (minimum, raison) comme
    minimum_experience ; (None, None) si la CP n'a pas de bareme officiel a cette date."""
    v = bareme_categories_en_vigueur(cp_key, reference_date)
    if v is None:
        return None, None
    notes = []
    libelle = trouver_categorie(v, categorie)
    if libelle is None:
        libelle = min(v['categories'], key=lambda k: v['categories'][k])
        notes.append("catégorie du contrat non reconnue dans le barème : catégorie la plus basse")
    montant = v['categories'][libelle]
    if v['unite'] == 'mensuel':
        mensuel, horaire = montant, horaire_de_mensuel(montant, v['heures_semaine'])
    else:
        horaire, mensuel = montant, round(montant * v['heures_semaine'] * 52 / 12, 2)
    etu = v.get('etudiants')
    if is_etudiant:
        if etu and 'mensuel' in etu:
            mensuel, horaire = etu['mensuel'], horaire_de_mensuel(etu['mensuel'], v['heures_semaine'])
            libelle, notes = LIBELLE_ETUDIANTS, []   # montant unique: la categorie du contrat ne joue pas
        elif etu and 'pourcentage' in etu:
            horaire, mensuel = round(horaire * etu['pourcentage'], 4), round(mensuel * etu['pourcentage'], 2)
            libelle = f"Étudiant : {etu['pourcentage'] * 100:.0f} % de « {libelle} »"
        else:
            notes.append("pas de barème étudiant propre à cette CP : minimum ordinaire")
    if 'categories_repos_payes' in v and not is_etudiant:
        bas = v['categories_repos_payes'].get(libelle)
        if bas:
            notes.append("régime 38 h/semaine ; avec jours de repos compensatoire payés : "
                         + f"{bas:.4f}".replace('.', ',') + " €")
    return {'horaire': horaire, 'mensuel': mensuel, 'categorie': libelle, 'depuis': v['date_debut'],
            'source': v['source'], 'note': ' ; '.join(notes) or None}, None
