# -*- coding: utf-8 -*-
"""
prime_fin_annee.py — DuxSalary
Calcul de la prime de fin d'annee (13e mois), Belgique.

IMPORTANT: il n'existe AUCUNE obligation legale generale. La prime de fin
d'annee est une obligation CONVENTIONNELLE, definie CCT par CCT. Son mode
de calcul differe radicalement d'une CP a l'autre:
  - CP 200:    100% du salaire brut de decembre, min 6 mois d'anciennete
  - CP 336:    montant FORFAITAIRE (35-105EUR), prorata oct-dec seulement
  - CP 140.03: 5% du salaire brut complet
  - CP 121:    9% du salaire annuel brut

Fiscalite (commune a toutes): la prime est soumise aux cotisations ONSS
personnelles (13.07%) ET a un precompte professionnel SPECIAL dit
"remunerations exceptionnelles" -- un bareme distinct du precompte mensuel
ordinaire, publie chaque annee par le SPF Finances.
⚠️ Ce bareme exceptionnel N'EST PAS encore implemente ici (voir
precompte_prime_exceptionnel plus bas) -- le calcul retourne le BRUT et
signale explicitement que le net n'est pas calculable en l'etat.

Sources recoupees le 29/09/2026: CGSLB (CP 200), Acerta, hellosafe.be,
calculateur-de-salaire.be, macalculatriceenligne.com.
"""

ONSS_PERSONNEL = 0.1307


def calculer_prime_fin_annee(regles_cp_prime: dict,
                              salaire_mensuel_brut: float,
                              mois_prestes_annee: int,
                              anciennete_mois: int,
                              salaire_annuel_brut: float = None) -> dict:
    """Calcule la prime de fin d'annee BRUTE selon les regles de la CP.

    regles_cp_prime: le dict 'prime_fin_annee' issu de regles_cp.py
    salaire_mensuel_brut: salaire brut mensuel actuel (base CP 200)
    mois_prestes_annee: mois prestes durant l'annee civile en cours
    anciennete_mois: anciennete totale au moment du paiement
    salaire_annuel_brut: cumul brut de l'annee (necessaire pour CP 121/140.03)

    Retourne un dict avec le detail, y compris les raisons d'un eventuel
    refus de droit -- pour que l'utilisateur comprenne le resultat.
    """
    if not regles_cp_prime or not regles_cp_prime.get('applicable'):
        return {'droit': False, 'montant_brut': 0.0,
                'raison': "Aucune prime de fin d'annee prevue pour cette CP",
                'a_verifier': False}

    # Condition d'anciennete (si la CP en impose une)
    anciennete_min = regles_cp_prime.get('anciennete_minimale_mois', 0)
    if anciennete_min and anciennete_mois < anciennete_min:
        return {
            'droit': False, 'montant_brut': 0.0,
            'raison': f"Anciennete insuffisante: {anciennete_mois} mois "
                       f"(minimum requis: {anciennete_min} mois). "
                       f"Aucune prime due, meme au prorata.",
            'a_verifier': False,
        }

    mode = regles_cp_prime.get('mode')
    mois = max(0, min(12, mois_prestes_annee))
    brut = 0.0
    methode = ''

    if mode == 'mois_salaire':
        coef = regles_cp_prime.get('coefficient', 1.0)
        base = salaire_mensuel_brut * coef
        brut = round(base * mois / 12, 2) if regles_cp_prime.get('proratise_selon_mois_prestes') else round(base, 2)
        methode = f"{coef*100:.0f}% du salaire mensuel brut x {mois}/12 mois"

    elif mode == 'montant_fixe':
        montant = regles_cp_prime.get('montant_brut_annuel', 0.0)
        brut = round(montant * mois / 12, 2) if regles_cp_prime.get('proratise_selon_mois_prestes') else round(montant, 2)
        methode = f"montant fixe {montant}EUR x {mois}/12 mois"

    elif mode == 'montant_fixe_fourchette':
        # CP 336: fourchette, montant exact dependant de la CCT -> on ne
        # peut PAS calculer un montant unique de facon fiable
        mn = regles_cp_prime.get('montant_min', 0.0)
        mx = regles_cp_prime.get('montant_max', 0.0)
        return {
            'droit': True, 'montant_brut': None,
            'montant_min': mn, 'montant_max': mx,
            'raison': f"Prime forfaitaire entre {mn}EUR et {mx}EUR selon la CCT "
                       f"applicable, prorata calcule sur la periode "
                       f"{regles_cp_prime.get('periode_reference', 'a preciser')}. "
                       f"Le montant exact doit etre confirme avec la CCT du secteur.",
            'methode': 'montant forfaitaire (fourchette) -- non calculable automatiquement',
            'a_verifier': True,
        }

    elif mode == 'pourcentage_brut':
        pct = regles_cp_prime.get('pourcentage', 0.0)
        base = salaire_annuel_brut if salaire_annuel_brut else (salaire_mensuel_brut * mois)
        brut = round(base * pct, 2)
        methode = f"{pct*100:.2f}% du brut ({base:.2f}EUR)"

    elif mode == 'pourcentage_brut_annuel':
        pct = regles_cp_prime.get('pourcentage', 0.0)
        if not salaire_annuel_brut:
            return {
                'droit': True, 'montant_brut': None,
                'raison': "Le cumul brut annuel est necessaire pour cette CP "
                           "et n'a pas ete fourni.",
                'a_verifier': True,
            }
        brut = round(salaire_annuel_brut * pct, 2)
        methode = f"{pct*100:.2f}% du brut annuel ({salaire_annuel_brut:.2f}EUR)"

    else:
        return {'droit': False, 'montant_brut': 0.0,
                'raison': f"Mode de calcul '{mode}' non reconnu", 'a_verifier': True}

    onss = round(brut * ONSS_PERSONNEL, 2)

    return {
        'droit': True,
        'montant_brut': brut,
        'onss_personnel': onss,
        'base_imposable': round(brut - onss, 2),
        'methode': methode,
        'echeance': regles_cp_prime.get('echeance', ''),
        # Le net n'est PAS calculable sans le bareme des remunerations
        # exceptionnelles du SPF Finances (non implemente)
        'precompte_exceptionnel': None,
        'montant_net': None,
        'avertissement_net': (
            "Le NET n'est pas calcule: la prime est soumise au bareme du "
            "precompte professionnel sur REMUNERATIONS EXCEPTIONNELLES "
            "(taux 0% a 53.50% selon la remuneration annuelle brute), "
            "distinct du precompte mensuel ordinaire. Ce bareme n'est pas "
            "encore implemente dans DuxSalary."
        ),
        'a_verifier': regles_cp_prime.get('a_verifier', False),
        'source': regles_cp_prime.get('source', ''),
    }
