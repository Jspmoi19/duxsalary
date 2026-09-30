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
        'source': 'Instructions ONSS 2026/2 (intermediaires) -- date de bascule estimee, non confirmee',
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
