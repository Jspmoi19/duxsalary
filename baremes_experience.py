# -*- coding: utf-8 -*-
"""
baremes_experience.py -- DuxSalary
Baremes minimums par CLASSE / CATEGORIE et ANNEES D'EXPERIENCE, versionnes par
date. Une nouvelle indexation = une nouvelle entree dans la liste de la CP (on ne
supprime ni n'ecrase jamais une ancienne version).

CP chargees: CP 200 uniquement. Les CP 336, 140.03 et 121 n'ont pas de grille
par experience dans le projet: elles restent controlees par categorie
(minimums_cp.py) tant que leurs baremes officiels ne sont pas fournis.

SOURCE CP 200 (01/01/2026, indexation +2,21 %): montants identiques dans deux
publications, lues le 01/10/2026 -- CSC batiment-industrie & energie (« Auxiliaire
pour les employes, CP 200, janvier 2026 ») et CGSLB / Synova (« CP200: indexation
janvier 2026 »). A CONFIRMER sur la source officielle salairesminimums.be (SPF
Emploi), non consultable automatiquement.
Regles (memes sources): salaires mensuels a temps plein, selon les annees
d'experience professionnelle ; bareme I pendant la premiere annee d'emploi dans
l'entreprise, bareme II apres un an dans la meme entreprise ; bareme des
etudiants selon l'age (16 a 20 ans).
"""
import re
from datetime import date

BAREMES_EXPERIENCE = {
    'CP 200': [{
        'date_debut': date(2026, 1, 1),
        'source': ("CSC BIE et CGSLB/Synova, barèmes CP 200 au 01/01/2026 (indexation +2,21 %) — "
                   "à confirmer sur salairesminimums.be"),
        'classes': ('A', 'B', 'C', 'D'),
        'heures_semaine': 38,
        # annees d'experience: (classe A, B, C, D) en EUR par mois, temps plein
        'bareme_I': {
            0: (2242.81, 2336.25, 2369.31, 2555.73),
            1: (2249.57, 2349.64, 2369.31, 2572.63),
            2: (2256.28, 2363.08, 2422.73, 2589.26),
            3: (2263.06, 2376.61, 2469.70, 2606.19),
            4: (2269.90, 2394.83, 2516.65, 2671.93),
            5: (2276.51, 2413.37, 2563.76, 2730.41),
            6: (2283.27, 2427.38, 2610.73, 2788.83),
            7: (2289.96, 2462.42, 2657.89, 2847.10),
            8: (2297.16, 2497.56, 2705.05, 2905.53),
            9: (2315.80, 2532.54, 2752.17, 2963.62),
            10: (2334.52, 2567.80, 2799.16, 3022.34),
            11: (2350.42, 2597.46, 2846.25, 3080.46),
            12: (2366.19, 2626.81, 2893.29, 3139.00),
            13: (2382.16, 2656.48, 2930.44, 3197.28),
            14: (2397.80, 2685.87, 2967.49, 3255.71),
            15: (2413.37, 2715.45, 3004.68, 3304.78),
            16: (2428.84, 2725.03, 3041.73, 3353.79),
            17: (2444.35, 2734.55, 3078.85, 3402.80),
            18: (2459.89, 2744.25, 3089.44, 3451.91),
            19: (2459.89, 2753.78, 3100.07, 3500.99),
            20: (2459.89, 2763.42, 3110.73, 3518.35),
            21: (2459.89, 2773.18, 3121.59, 3535.83),
            22: (2459.89, 2782.63, 3132.28, 3553.29),
            23: (2459.89, 2792.25, 3143.19, 3570.59),
            24: (2459.89, 2801.86, 3153.91, 3587.83),
            25: (2459.89, 2811.39, 3164.86, 3605.11),
            26: (2459.89, 2820.99, 3175.61, 3622.42),
        },
        'bareme_II': {
            1: (2310.30, 2413.09, 2433.25, 2642.08),
            2: (2317.19, 2426.87, 2488.16, 2659.13),
            3: (2324.14, 2440.76, 2536.36, 2676.55),
            4: (2330.81, 2459.32, 2584.73, 2744.52),
            5: (2337.66, 2478.44, 2633.22, 2804.72),
            6: (2344.46, 2492.88, 2681.47, 2864.69),
            7: (2351.35, 2528.90, 2730.03, 2924.79),
            8: (2358.93, 2565.14, 2778.60, 2984.80),
            9: (2378.04, 2601.10, 2827.02, 3044.74),
            10: (2397.33, 2637.36, 2875.48, 3105.00),
            11: (2413.71, 2667.83, 2923.83, 3164.92),
            12: (2429.89, 2698.00, 2972.20, 3225.06),
            13: (2446.31, 2728.54, 3010.43, 3285.11),
            14: (2462.42, 2758.86, 3048.53, 3345.24),
            15: (2478.44, 2789.20, 3086.76, 3395.69),
            16: (2494.33, 2799.07, 3124.96, 3446.06),
            17: (2510.24, 2808.85, 3163.20, 3496.57),
            18: (2526.16, 2818.89, 3174.02, 3547.01),
            19: (2526.16, 2828.76, 3184.94, 3597.56),
            20: (2526.16, 2838.66, 3195.97, 3615.45),
            21: (2526.16, 2848.50, 3207.12, 3633.38),
            22: (2526.16, 2858.33, 3218.09, 3651.35),
            23: (2526.16, 2868.34, 3229.43, 3669.27),
            24: (2526.16, 2878.15, 3240.49, 3686.98),
            25: (2526.16, 2887.96, 3251.76, 3704.65),
            26: (2526.16, 2897.83, 3262.72, 3722.55),
        },
        # age: classes disponibles dans l'ordre A, B, C, D (16 et 17 ans: A et B seulement)
        'etudiants': {
            16: (1447.01, 1504.51),
            17: (1635.95, 1702.00),
            18: (1824.79, 1899.72, 2060.43, 2262.47),
            19: (1975.80, 2057.87, 2234.09, 2406.40),
            20: (2051.38, 2136.84, 2320.65, 2491.55),
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
