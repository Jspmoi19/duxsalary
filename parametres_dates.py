# -*- coding: utf-8 -*-
"""
parametres_dates.py — DuxSalary
Tables de parametres legaux VERSIONNEES PAR DATE. Certains parametres (bonus
emploi, reduction structurelle) changent plusieurs fois par an -- ce fichier
donne, pour une date de periode donnee, la version exacte en vigueur.

Chaque entree a une date_debut (inclusive) et est valable jusqu'a la
date_debut de l'entree suivante (ou indefiniment si c'est la plus recente).

Sources: toutes recoupees le 29/09/2026 via Partena Professional (infoflashes
officiels citant l'ONSS) + socialsecurity.be (Instructions administratives).
"""
from datetime import date


# ─────────────────────────────────────────────────────────────────
# BONUS A L'EMPLOI — 4 versions connues pour 2026
# ─────────────────────────────────────────────────────────────────
BONUS_EMPLOI_VERSIONS = [
    {
        'date_debut': date(2026, 1, 1),
        'source': 'Partena infoflash — Au 1er janvier 2026',
        'volet_a': {
            'employe': {'seuil_bas': 2833.36, 'montant_max': 123.00, 'seuil_haut': 3271.48, 'pente': 0.2807},
            'ouvrier': {'seuil_bas': 2833.36, 'montant_max': 132.84, 'seuil_haut': 3271.48, 'pente': 0.3032},
        },
        'volet_b': {
            'employe': {'seuil_bas': 2218.73, 'montant_max': 165.87, 'seuil_haut': 2833.36, 'pente': 0.2699},
            'ouvrier': {'seuil_bas': 2218.73, 'montant_max': 179.14, 'seuil_haut': 2833.36, 'pente': 0.2915},
        },
    },
    {
        'date_debut': date(2026, 3, 1),
        'source': 'Partena infoflash — Au 1er mars 2026',
        'volet_a': {
            'employe': {'seuil_bas': 2833.36, 'montant_max': 123.00, 'seuil_haut': 3336.98, 'pente': 0.2442},
            'ouvrier': {'seuil_bas': 2833.36, 'montant_max': 132.84, 'seuil_haut': 3336.98, 'pente': 0.2638},
        },
        'volet_b': {
            'employe': {'seuil_bas': 2218.73, 'montant_max': 165.87, 'seuil_haut': 2833.36, 'pente': 0.2699},
            'ouvrier': {'seuil_bas': 2218.73, 'montant_max': 179.14, 'seuil_haut': 2833.36, 'pente': 0.2915},
        },
    },
    {
        # Ajoute le 01/10/2026 (version manquante entre mars et juillet). Recoupe
        # sur 3 sources concordantes (flash info Easypay, Securex lex4you, Partena)
        # et verifie au centime sur deux fiches reelles Interconsult de mai et
        # juin 2026 (ouvrier temps partiel). A confirmer sur les Instructions
        # ONSS 2026/2 (source officielle non disponible dans sources/).
        'date_debut': date(2026, 4, 1),
        'source': ('Easypay flash info + Securex lex4you + Partena — Au 1er avril 2026 '
                   '(hausse du RMMMG) ; verifie sur fiches reelles mai/juin 2026'),
        'volet_a': {
            'employe': {'seuil_bas': 2880.32, 'montant_max': 125.04, 'seuil_haut': 3336.98, 'pente': 0.2738},
            'ouvrier': {'seuil_bas': 2880.32, 'montant_max': 135.04, 'seuil_haut': 3336.98, 'pente': 0.2957},
        },
        'volet_b': {
            'employe': {'seuil_bas': 2255.50, 'montant_max': 168.62, 'seuil_haut': 2880.32, 'pente': 0.2699},
            'ouvrier': {'seuil_bas': 2255.50, 'montant_max': 182.11, 'seuil_haut': 2880.32, 'pente': 0.2915},
        },
    },
    {
        'date_debut': date(2026, 7, 1),
        'source': 'Partena infoflash — Au 1er juillet 2026',
        'volet_a': {
            'employe': {'seuil_bas': 2937.93, 'montant_max': 127.54, 'seuil_haut': 3336.98, 'pente': 0.3196},
            'ouvrier': {'seuil_bas': 2937.93, 'montant_max': 137.74, 'seuil_haut': 3336.98, 'pente': 0.3452},
        },
        'volet_b': {
            'employe': {'seuil_bas': 2300.62, 'montant_max': 171.99, 'seuil_haut': 2937.93, 'pente': 0.2699},
            'ouvrier': {'seuil_bas': 2300.62, 'montant_max': 185.75, 'seuil_haut': 2937.93, 'pente': 0.2915},
        },
    },
    {
        'date_debut': date(2026, 9, 1),
        'source': 'Partena infoflash — Au 1er septembre 2026 (verifie contre Group S reel le 29/09/2026)',
        'volet_a': {
            'employe': {'seuil_bas': 2937.93, 'montant_max': 127.54, 'seuil_haut': 3403.62, 'pente': 0.2739},
            'ouvrier': {'seuil_bas': 2937.93, 'montant_max': 137.74, 'seuil_haut': 3403.62, 'pente': 0.2958},
        },
        'volet_b': {
            'employe': {'seuil_bas': 2300.62, 'montant_max': 171.99, 'seuil_haut': 2937.93, 'pente': 0.2699},
            'ouvrier': {'seuil_bas': 2300.62, 'montant_max': 185.75, 'seuil_haut': 2937.93, 'pente': 0.2915},
        },
    },
]


# ─────────────────────────────────────────────────────────────────
# REDUCTION STRUCTURELLE ONSS — categorie 1 (secteur prive marchand general)
# ─────────────────────────────────────────────────────────────────
REDUCTION_STRUCTURELLE_VERSIONS = [
    {
        'date_debut': date(2026, 1, 1),
        'source': 'Partena infoflash — Au 1er janvier 2026',
        'seuil_bas': 11458.57, 'coeff_bas': 0.14,
        'seuil_tres_bas': 9547.20, 'coeff_tres_bas': 0.15,
    },
    {
        'date_debut': date(2026, 4, 1),
        'source': 'Partena infoflash — Au 1er avril 2026',
        'seuil_bas': 11458.57, 'coeff_bas': 0.14,
        'seuil_tres_bas': 9547.20, 'coeff_tres_bas': 0.16,
    },
    {
        # ⚠️ Version utilisee pour Ciwan (octobre 2026) -- ecart residuel
        # ~11EUR/mois non resolu contre une simulation Group S reelle.
        # Source: Instructions administratives ONSS 2026/2 (intermediaires),
        # date de bascule exacte non confirmee a 100% -- a revalider.
        'date_debut': date(2026, 7, 1),
        'source': ("Instructions administratives ONSS 2026/3 (PDF du 27/08/2026, p.383): "
                   "'A partir du 3eme trimestre 2026' -- CONFIRME, et verifie au centime "
                   "contre Group S (Ciwan, 2257EUR, 22 jours -> 398.98EUR)."),
        'seuil_bas': 11687.74, 'coeff_bas': 0.14,
        'seuil_tres_bas': 9738.14, 'coeff_tres_bas': 0.16,
    },
]


def _get_version(versions_list, reference_date):
    """Retourne la version applicable pour une date donnee (la plus recente
    dont date_debut <= reference_date). Leve une erreur explicite si aucune
    version ne couvre cette date -- mieux vaut planter que donner un chiffre
    silencieusement faux."""
    applicables = [v for v in versions_list if v['date_debut'] <= reference_date]
    if not applicables:
        raise ValueError(
            f"Aucune version de parametre disponible pour la date {reference_date} "
            f"(la plus ancienne connue commence le {versions_list[0]['date_debut']}). "
            f"Ne pas deviner -- ajouter la version manquante dans parametres_dates.py."
        )
    return max(applicables, key=lambda v: v['date_debut'])


def get_bonus_emploi_params(reference_date):
    """reference_date: date de la periode de paie (periode_fin recommande)."""
    return _get_version(BONUS_EMPLOI_VERSIONS, reference_date)


# Plafond ANNUEL du bonus a l'emploi, par travailleur et par annee calendrier.
# Source: Instructions administratives ONSS 2026/3, p.453: "Le montant total
# de la reduction par travailleur ne peut etre superieur a 3.594,36 EUR par
# annee calendrier a partir du 1er juillet 2026."
BONUS_EMPLOI_PLAFOND_ANNUEL_VERSIONS = [
    {'date_debut': date(2026, 7, 1), 'plafond_annuel': 3594.36,
     'source': 'Instructions administratives ONSS 2026/3, p.453'},
]


def get_bonus_emploi_plafond_annuel(reference_date):
    """Plafond annuel en vigueur, ou None si aucune version ne couvre la date
    (avant le 01/07/2026: montant non charge -- le moteur le signale si un
    cumul lui est transmis)."""
    applicables = [v for v in BONUS_EMPLOI_PLAFOND_ANNUEL_VERSIONS if v['date_debut'] <= reference_date]
    return max(applicables, key=lambda v: v['date_debut']) if applicables else None


def get_reduction_structurelle_params(reference_date):
    return _get_version(REDUCTION_STRUCTURELLE_VERSIONS, reference_date)


# ─────────────────────────────────────────────────────────────────
# PRECOMPTE PROFESSIONNEL — versionne par ANNEE FISCALE
# ─────────────────────────────────────────────────────────────────
# Le SPF Finances publie en decembre la "formule-cle" de l'annee suivante
# (avec un simulateur Excel officiel). Chaque annee = une entree ici.
# Les annees precedentes ne sont JAMAIS modifiees ni supprimees: une fiche
# de 2026 regeneree en 2027 doit toujours utiliser les parametres 2026.
#
# Pour ajouter 2027: copier le bloc 2026, changer 'annee', 'source' et les
# valeurs extraites du simulateur SPF 2027, puis relancer test_profils.py.
PRECOMPTE_VERSIONS = [
    {
        'annee': 2026,
        'source': ("Simulateur Excel verrouille SPF Finances 2026 "
                   "(SimulateurPrP2026verrouilleFR.xlsx), formules extraites "
                   "et executees le 29/09/2026 -- verifie au centime."),
        'frais_forfaitaires_taux': 0.30,
        'frais_forfaitaires_plafond_annuel': 6070.0,
        'tranches_annuelles': [
            # (bas, haut, taux, montant_fixe_cumule_avant_la_tranche)
            (0.0, 16710.0, 0.2675, 0.0),
            (16710.0, 29500.0, 0.4280, 4469.93),
            (29500.0, 51050.0, 0.4815, 9944.05),
            (51050.0, float('inf'), 0.5350, 20320.38),
        ],
        'reduction_base_isole_annuelle': 2987.98,
        'quotient_conjugal_taux': 0.30,
        'quotient_conjugal_plafond_annuel': 13790.0,
        'reduction_base_couple_annuelle': 5975.96,
        'reduction_enfants_charge': {1: 624.0, 2: 1656.0, 3: 4404.0, 4: 7620.0,
                                     5: 11100.0, 6: 14592.0, 7: 18120.0, 8: 21996.0},
        'reduction_enfant_supplementaire_au_dela_8': 3864.0,
        # Reduction du precompte liee au bonus a l'emploi (mecanisme fiscal)
        'reduction_precompte_taux_volet_a': 0.3314,
        'reduction_precompte_taux_volet_b': 0.5254,
        # Exoneration fiscale de l'indemnite km voiture domicile-travail
        # (annee de revenus 2026) -- au-dela, le surplus est imposable
        'exoneration_km_voiture_annuelle': 500.0,
        # Reductions pour autres charges de famille (annexes 4 et 5 de la
        # formule-cle, simulateur SPF 2026) -- montants ANNUELS, cumulables.
        # Enfant handicape a charge: compte pour deux (annexe 3, note 1).
        'reductions_autres_charges': {
            'parent_isole': 624.0,                # annexe 4.1 (isole uniquement)
            'handicape': 624.0,                   # annexe 4.2 / 5.1
            'conjoint_handicape': 624.0,          # annexe 5.2 (conjoint sans revenus)
            'personne_charge_dependance': 1992.0, # annexe 4.3 / 5.3, par personne
            'autre_personne_charge': 624.0,       # annexe 4.4 / 5.4, par personne
        },
        # Allocations exceptionnelles (prime de fin d'annee, 13e mois, bonus,
        # double pecule): taux UNIQUE lu sur la remuneration annuelle brute
        # NORMALE (allocation exclue), applique en une fois a l'allocation.
        # (bas, haut, taux double pecule, taux autres allocations)
        # Source: bareme 2026 publie par calculateur-de-salaire.be (29/09/2026),
        # dont les autres parametres concordent au centime avec le simulateur SPF.
        'allocations_exceptionnelles': [
            (0.00, 10675.00, 0.0000, 0.0000),
            (10675.00, 13660.00, 0.1917, 0.2322),
            (13660.00, 17375.00, 0.2120, 0.2523),
            (17375.00, 20840.00, 0.2625, 0.3028),
            (20840.00, 23580.00, 0.3130, 0.3533),
            (23580.00, 26340.00, 0.3433, 0.3836),
            (26340.00, 31830.00, 0.3634, 0.4038),
            (31830.00, 34640.00, 0.3937, 0.4341),
            (34640.00, 45860.00, 0.4239, 0.4644),
            (45860.00, 59900.00, 0.4744, 0.5148),
            (59900.00, float('inf'), 0.5350, 0.5350),
        ],
    },
]


def get_precompte_params(reference_date):
    """Retourne les parametres du precompte pour l'ANNEE de reference_date.
    Correspondance STRICTE sur l'annee: pas de repli sur l'annee precedente.
    Si le bareme de l'annee n'est pas charge, leve une erreur explicite --
    mieux vaut bloquer une fiche que la calculer avec le bareme d'une autre
    annee sans que personne ne s'en rende compte."""
    annee = reference_date.year
    for v in PRECOMPTE_VERSIONS:
        if v['annee'] == annee:
            return v
    disponibles = sorted(v['annee'] for v in PRECOMPTE_VERSIONS)
    raise ValueError(
        f"Bareme du precompte professionnel {annee} non charge dans DuxSalary "
        f"(annees disponibles: {disponibles}). Recuperer le simulateur officiel "
        f"SPF Finances {annee} et ajouter la version dans parametres_dates.py "
        f"avant de generer une fiche pour cette annee."
    )


# ─────────────────────────────────────────────────────────────────
# PREMIER ENGAGEMENT — forfait trimestriel 1er travailleur (temps plein)
# ─────────────────────────────────────────────────────────────────
# Source: Instructions administratives ONSS 2026/3, p.404-405:
# G21 = 2.000EUR a partir du 01/07/2026 (G20 = 3.100EUR avant), illimite
# dans le temps. Montant pour des prestations a TEMPS PLEIN: proportionne
# par la fraction de prestation mu et le facteur beta_g (Pg = G x mu x beta_g).
PREMIER_ENGAGEMENT_VERSIONS = [
    {'date_debut': date(2016, 1, 1), 'forfait_1er_trimestriel': 3100.0,
     'source': 'Instructions ONSS (G20), avant le 01/07/2026'},
    {'date_debut': date(2026, 7, 1), 'forfait_1er_trimestriel': 2000.0,
     'source': 'Instructions administratives ONSS 2026/3, p.405 (G21)'},
]


def get_premier_engagement_params(reference_date):
    return _get_version(PREMIER_ENGAGEMENT_VERSIONS, reference_date)


# ─────────────────────────────────────────────────────────────────
# COTISATION SPECIALE DE SECURITE SOCIALE (CSSS) -- retenue travailleur
# ─────────────────────────────────────────────────────────────────
# Source: Instructions administratives ONSS 2026/3, p.336-337 (bareme en
# vigueur depuis le 01/04/2022). Base = remuneration BRUTE declaree (108% pour
# les ouvriers), PAS le brut imposable. Tranche determinee par la remuneration
# TRIMESTRIELLE; montants trimestriels (fixes) et % sur la remuneration mensuelle.
# Corrige le 30/09/2026: l'ancien code appliquait un bareme obsolete (7,6% /
# 18,60 EUR) sur le brut imposable, sans distinction de situation familiale.
CSS_VERSIONS = [
    {'date_debut': date(2022, 4, 1),
     'source': 'Instructions administratives ONSS 2026/3 p.336-337',
     # imposition individuelle: (q_min, q_max, fixe_trimestriel, taux, seuil_mensuel)
     'individuelle': [
        (5836.14, 6570.54, 0.00, 0.0422, 1945.38),
        (6570.54, 11211.00, 30.99, 0.0110, 2190.18),
        (11211.00, 12300.00, 82.05, 0.0338, 3737.00),
        (12300.00, 18116.46, 118.83, 0.0110, 4100.00),
        (18116.46, float('inf'), 182.82, 0.0, 0.0),
     ],
     # imposition commune, conjoint SANS revenus professionnels
     'couple_un_revenu': {'tranche_1': (5836.14, 6570.54, 0.0590, 1945.38),
                          'tranche_2': (6570.54, 43.32, 0.0110, 2190.18, 182.82)},
     # imposition commune, conjoint AVEC revenus professionnels
     'couple_deux_revenus': {'forfait': (3285.29, 5836.14, 15.45),
                             'tranche_1': (5836.14, 6570.54, 0.0590, 1945.38, 15.45),
                             'tranche_2': (6570.54, 43.32, 0.0110, 2190.18, 154.92)},
    },
]


def get_css_params(reference_date):
    return _get_version(CSS_VERSIONS, reference_date)
