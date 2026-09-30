# -*- coding: utf-8 -*-
"""
regles_cp.py — DuxSalary
SOURCE UNIQUE DE VÉRITÉ pour les règles légales par CP.
Toute donnée ici doit avoir une source et une date. Ne jamais coder un taux
en dur ailleurs dans le moteur — tout passe par ce fichier ou par la table
BDD baremes_cp pour les montants qui changent (barèmes salariaux).

Dernière vérification: 29/09/2026
Sources: ONSS instructions DmfA, SPF Emploi (salairesminimums.be),
         SPF Finances (précompte), recoupé avec aureussocial.be
"""

# ─────────────────────────────────────────────────────────────────
# TAUX ONSS DE BASE 2026 (identiques pour tous secteurs marchands)
# ─────────────────────────────────────────────────────────────────
# Exonération fiscale (précompte) de l'indemnité km domicile-travail en VOITURE
# — DISTINCTE du plafond ONSS (qui suit le taux officiel au km, pas de plafond
# annuel en euros). Source: Securex + fin.belgium.be, année de revenus 2026.
# Au-delà de ce montant annuel, le surplus doit être réintégré dans la base
# imposable pour le calcul du précompte (mais PAS dans la base ONSS).
INDEMNITE_KM_VOITURE_EXONERATION_ANNUELLE = 500.0

ONSS = {
    'personnel_taux': 0.1307,          # part travailleur, tous statuts ordinaires
    # Pas de taux patronal global unique: chaque CP a son propre taux facial
    # (validé contre fiches réelles). Voir 'onss_patronal_taux_base' dans REGLES_CP.
    'patronal_taux_defaut': 0.2508,    # fallback si une CP ne précise rien (à éviter)
    'coeff_ouvrier': 1.08,             # base ONSS ouvrier = brut × 1.08 (pécule ONVA)
    'etudiant_personnel': 0.0271,      # cotisation solidarité étudiant — part travailleur
    'etudiant_patronal': 0.0542,       # cotisation solidarité étudiant — part patronale
    'etudiant_fonds_amiante': 0.0001,  # +0,01% fonds amiante, part patronale seulement
    'quota_etudiant_heures_an': 650,   # quota annuel légal
}

# Réduction structurelle — montant plafond trimestriel par profil (2026)
# Formule: réduction dégressive avec le salaire trimestriel, plafonnée à ce montant
# pour les bas salaires, décroît ensuite. On applique le plafond si S_trim <= seuil bas.
REDUCTION_STRUCTURELLE = {
    # Formule DEGRESSIVE officielle (Instructions administratives ONSS 2026/2,
    # categorie 1 -- secteur prive marchand general), remplace l'ancien
    # montant FIXE de 521.47EUR qui ne variait jamais avec le salaire (faux).
    #
    # R_trimestriel = 0.14 x (11687.74 - S) + 0.16 x (9738.14 - S)
    # -- chaque terme a 0 si negatif, S = salaire TRIMESTRIEL de reference.
    #
    # ⚠️ Ecart residuel non resolu: teste contre une simulation Group S reelle
    # (Ciwan, CP336, 2257EUR/mois) -- notre formule donne 387.70EUR/mois,
    # Group S annonce 398.98EUR/mois (ecart 11.28EUR). Les coefficients ONSS
    # sont mis a jour plusieurs fois par an (au moins 4 versions en 2026: T1,
    # avril, T2, instructions intermediaires) -- la version exacte en vigueur
    # au 01/10/2026 n'est pas confirmee a 100%. A revalider avant un dossier
    # a fort volume si cette precision devient critique.
    'categorie_1': {
        'seuil_bas': 11687.74,
        'coeff_bas': 0.14,
        'seuil_tres_bas': 9738.14,
        'coeff_tres_bas': 0.16,
    },
    # Ancien montant fixe conserve en fallback si jamais besoin de comparer
    'ancien_montant_fixe_deprecated': 521.47,
}

# Premier engagement — réduction groupe-cible (loi du 27/06/1969)
PREMIER_ENGAGEMENT = {
    '1er_travailleur_plafond_trim': 2000.0,   # depuis le 01/07/2026 (était 3100€ avant)
    '1er_travailleur_illimite_duree': True,   # pas de limite dans le temps
    'applicable_etudiant': False,             # CONFIRMÉ: ne s'applique jamais aux STU
    'applicable_interim': False,
}

# Bonus à l'emploi 2026 — réduction ONSS personnelle pour bas/moyens salaires
BONUS_EMPLOI = {
    # Parametres EN VIGUEUR AU 01/09/2026 (source: ONSS via Partena, infoflash
    # du 07/07/2026, section "Au 1er septembre 2026" -- verifie le 29/09/2026
    # via web_fetch direct de la page officielle, ET recoupe au centime contre
    # une simulation reelle Group S pour Ciwan Ilhan CP336 employe 2257EUR).
    #
    # STRUCTURE 2024+ (reforme du 01/04/2024): volet A ET volet B s'appliquent
    # DESORMAIS aux employes ET aux ouvriers, avec des seuils et montants
    # DIFFERENTS pour chaque combinaison statut x volet (4 tableaux distincts).
    # AVANT cette correction, le code supposait a tort que le volet B etait
    # reserve aux ouvriers -- FAUX depuis le 01/04/2024.
    #
    # Ces seuils sont mis a jour PLUSIEURS FOIS PAR AN (janvier, mars, juillet,
    # septembre releves en 2026) -- a revoir a chaque nouvelle indexation.
    'volet_a': {
        'employe': {'seuil_bas': 2937.93, 'montant_max': 127.54,
                     'seuil_haut': 3403.62, 'pente': 0.2739},
        'ouvrier': {'seuil_bas': 2937.93, 'montant_max': 137.74,
                     'seuil_haut': 3403.62, 'pente': 0.2958},
    },
    'volet_b': {
        'employe': {'seuil_bas': 2300.62, 'montant_max': 171.99,
                     'seuil_haut': 2937.93, 'pente': 0.2699},
        'ouvrier': {'seuil_bas': 2300.62, 'montant_max': 185.75,
                     'seuil_haut': 2937.93, 'pente': 0.2915},
    },
    'applicable_etudiant': False,
    'reduction_precompte_taux_volet_a': 0.3314,
    'reduction_precompte_taux_volet_b': 0.5254,
    'reduction_precompte_plafond_imposable': 3500.0,
}

# Précompte professionnel — "formule-clé" 2026 (Annexe III AR/CIR92, applicable
# depuis le 01/01/2023, publiée au Moniteur belge du 29/12/2025).
# Architecture officielle en 4 étapes — remplace l'ancien système par barèmes
# mensuels arrondis (abandonné depuis 2023):
#   1. Revenu annuel brut imposable = (brut mensuel imposable) × 12
#   2. − frais professionnels forfaitaires: 30% du revenu annuel, plafonnés
#   3. Impôt = tranches progressives appliquées au revenu net obtenu
#   4. − "tranche non imposée" (crédit d'impôt, PAS une exemption sur le revenu)
#      puis ÷ 12 = précompte mensuel
#
# ⚠️ Confiance calibrée: architecture et taux confirmés par 3 sources
# indépendantes citant l'Annexe III (calculateur-de-salaire.be, monsalaire-net.be,
# securex.be). Le cas ISOLÉ SANS ENFANT a été recoupé contre un tableau
# d'exemples chiffrés indépendant (2500/3000/3500/4000€ bruts) avec un écart
# résiduel de quelques euros non totalement expliqué (probablement un effet
# bonus-emploi ou un arrondi de constante officielle qu'on n'a pas pu vérifier
# au caractère près). Le cas MARIÉ/COHABITANT reste moins solide — le
# "quotient conjugal" (30% du revenu attribué au partenaire sans revenus,
# plafonné à 13.790€/an) n'est PAS encore implémenté, seule la tranche non
# imposée est doublée en approximation. À valider avant un premier dossier
# marié réel.
PRECOMPTE = {
    'frais_forfaitaires_taux': 0.30,
    'frais_forfaitaires_plafond_annuel': 6070.0,
    'tranches_annuelles': [
        # (bas, haut, taux, montant_fixe_cumule_avant_la_tranche) — vérifié via
        # le simulateur EXCEL VERROUILLÉ officiel du SPF Finances (formule-clé
        # 2026), recalculé formule par formule le 29/09/2026, pas une source tierce.
        (0.0, 16710.0, 0.2675, 0.0),
        (16710.0, 29500.0, 0.4280, 4469.93),
        (29500.0, 51050.0, 0.4815, 9944.05),
        (51050.0, float('inf'), 0.5350, 20320.38),
    ],
    # Isolé (et marié/cohabitant dont le conjoint a AUSSI des revenus propres):
    # cette réduction est soustraite DIRECTEMENT DE L'IMPÔT calculé sur le
    # revenu net imposable complet — PAS du revenu avant application des tranches.
    'reduction_base_isole_annuelle': 2987.98,
    # Marié/cohabitant dont le conjoint N'A PAS de revenus professionnels propres
    # (ou seulement une pension ≤174€ nets/mois): mécanisme du QUOTIENT CONJUGAL.
    # 30% du revenu net imposable du travailleur est attribué fictivement au
    # conjoint (plafonné), chaque part est imposée séparément selon les mêmes
    # tranches, puis cette réduction (le double de la réduction isolé) est
    # soustraite de la SOMME des deux impôts ainsi obtenus.
    'quotient_conjugal_taux': 0.30,
    'quotient_conjugal_plafond_annuel': 13790.0,
    'reduction_base_couple_annuelle': 5975.96,
    # Réduction pour enfants à charge — montant ANNUEL, soustrait de l'impôt
    # après la réduction de base ci-dessus (Annexe 3, vérifiée sur le fichier officiel)
    'reduction_enfants_charge': {1: 624.0, 2: 1656.0, 3: 4404.0, 4: 7620.0, 5: 11100.0,
                                  6: 14592.0, 7: 18120.0, 8: 21996.0},
    'reduction_enfant_supplementaire_au_dela_8': 3864.0,
    # Autres réductions (Annexe 4/5) — NON implémentées finement (handicap,
    # personne à charge 66+ ans, conjoint à faibles revenus propres). Ces cas
    # ne concernent aucun dossier actif au 29/09/2026. Si un jour un travailleur
    # ou son conjoint correspond à l'une de ces situations (voir Annexe 4/5 du
    # simulateur SPF), il faudra les ajouter avant de facturer ce dossier.
    'applicable_etudiant': False,   # précompte toujours 0 pour étudiant STU
}

# Cotisation spéciale sécurité sociale (CSSS) — barème mensuel 2026
CSSS = {
    'tranches': [
        (0, 1945.38, 0.0),
        (1945.38, 2190.19, 0.076),   # + montant fixe additionné progressivement
        (2190.19, 6038.82, 0.011),   # avec base 18.60€ (voir moteur pour formule complète)
        (6038.82, float('inf'), 0.0),  # forfait 60.94€ max
    ],
}

# ─────────────────────────────────────────────────────────────────
# RÈGLES SPÉCIFIQUES PAR CP — la vraie source de vérité par secteur
# ─────────────────────────────────────────────────────────────────
REGLES_CP = {

    'CP 140.03': {
        'nom': 'Sous-commission paritaire du transport routier et logistique',
        'type_travailleur_defaut': 'ouvrier',
        'heures_semaine_defaut': 38,
        'onss_patronal_taux_base': 0.27,   # validé contre fiche FDLR Liantis 2025 (taux facial CP140.03)
        'avantage_repas': {
            'applicable': True,
            'montant_jour': 1.09,
            'soumis_onss': True,     # OUI — c'est soumis, contrairement à CP 200/336
        },
        'cheques_repas': {
            'obligatoire': True,
            'valeur_totale_jour': 8.00,
            'part_employeur_jour': 6.91,
            'part_travailleur_jour': 1.09,
            'depuis': '01/07/2026',
        },
        'rgpt': {
            'applicable': True,
            'montant_heure': 1.8175,
            'depuis': '01/01/2026',
        },
        'sectoriel_notes': [
            'Personnel roulant soumis au règlement CE n°561/2006 (temps de conduite/repos)',
            'Cotisations sectorielles FSE + formation dues via DmfA trimestrielle, '
            'NON couvertes par la réduction structurelle ni le premier engagement — '
            'facturées séparément par l\'ONSS après DmfA.',
        ],
        'indexation': {'derniere': '01/01/2026 (+2.18%)', 'prochaine_attendue': 'janvier 2027'},
        'source': 'salairesminimums.be PC 1400300, recoupé Liantis (FDLR 2025) + PayrollTool',
        'derniere_verification': '28/09/2026',
    },

    'CP 200': {
        'nom': 'Commission paritaire auxiliaire pour employés (CPAE)',
        'type_travailleur_defaut': 'employe',
        'heures_semaine_defaut': 38,
        'onss_patronal_taux_base': 0.25,   # validé fiches Liantis employés CP200/336
        'avantage_repas': {
            'applicable': False,   # employés: pas d'avantage repas soumis ONSS de ce type
        },
        'cheques_repas': {
            'obligatoire': False,   # PAS OBLIGATOIRE en CP 200 — accord d'entreprise requis
            'valeur_max_legale_jour': 8.00,
            'part_employeur_max_jour': 6.91,
            'part_travailleur_min_jour': 1.09,
        },
        'rgpt': {'applicable': False},
        'prime_fin_annee': {
            'applicable': True,
            'mode': 'mois_salaire',
            'coefficient': 1.0,
            'anciennete_minimale_mois': 6,
            'proratise_selon_mois_prestes': True,
            'echeance': '31 decembre au plus tard',
            'source': 'CCT CP 200 / CGSLB / Acerta, verifie 29/09/2026',
        },
        'prime_annuelle_sectorielle': {
            'applicable': True,
            'mode': 'montant_fixe',
            'montant_brut_annuel': 330.84,
            'proratise_selon_mois_prestes': True,
            'convertible_en_avantage': True,
            'mois_paiement': 6,   # payee en JUIN (pas en decembre)
            'periode_reference': 'du 1er juin N-1 au 31 mai N',
            'proratise_selon_regime': True,
            'source': 'CCT CP 200, montant au 01/01/2026; CGSLB, CSC-CNE, SETCa (paiement en juin)',
        },
        'fonds_formation': 'CEFORA',
        'sectoriel_notes': [
            'Classification par classe de fonction (A à D) — pas d\'ancienneté dans le barème minimum de base.',
        ],
        'indexation': {'derniere': '01/01/2026 (+2.21%)', 'prochaine_attendue': 'janvier 2027'},
        'source': 'salairesminimums.be PC 2000000',
        'derniere_verification': '29/09/2026',
    },

    'CP 336': {
        'nom': 'Commission paritaire des professions libérales',
        'type_travailleur_defaut': 'employe',
        'heures_semaine_defaut': 38,
        'onss_patronal_taux_base': 0.25,   # aligné employés CP200 — à reconfirmer spécifiquement pour 336
        'avantage_repas': {'applicable': False},
        'cheques_repas': {
            'obligatoire': False,   # à vérifier par CCT d'entreprise — pas d'obligation sectorielle générale connue
            'part_employeur_usuelle_jour': 6.91,
            'part_travailleur_usuelle_jour': 1.09,
        },
        'rgpt': {'applicable': False},
        'transport': {
            'train_remboursement_pct': 80,   # 80% du prix carte 2e classe
            'velo_indemnite_km': 0.32,
        },
        'prime_fin_annee': {
            'applicable': True,
            'mode': 'montant_fixe_fourchette',
            'montant_min': 35.0,
            'montant_max': 105.0,
            'periode_reference': '01/10 au 31/12',
            'echeance': 'janvier (annee suivante)',
            'source': 'hellosafe.be / CCT CP336 -- fourchette a preciser '
                       'selon la CCT exacte applicable, montant non unique',
            'a_verifier': True,
        },
        'sectoriel_notes': [
            'Pas de classification de fonctions officielle: un seul minimum sectoriel.',
            'Statut "professionnel libéral entrée (103%)" = critère de STATUT '
            '(activité intellectuelle indépendante + déontologie imposée), '
            'PAS un barème générique — ne l\'appliquer que si le travailleur '
            'correspond réellement à cette définition légale (ex: expert-comptable '
            'stagiaire, pas un aide-comptable).',
            'Salaire plafonné à 3.500€ brut temps plein pour l\'indexation au 01/01/2026 spécifiquement.',
        ],
        'indexation': {'derniere': '01/09/2026 (+2%)', 'prochaine_attendue': 'janvier 2027'},
        'source': 'salairesminimums.be PC 3360000, CGSLB CP336, aureussocial.be',
        'derniere_verification': '29/09/2026',
    },

    'CP 121': {
        'nom': 'Commission paritaire pour le nettoyage',
        'type_travailleur_defaut': 'ouvrier',
        'heures_semaine_defaut': 36.5,   # ATTENTION: différent des autres CP (pas 38h)
        'onss_patronal_taux_base': 0.27,   # ⚠️ NON VALIDÉ — taux ouvrier standard par défaut, à confirmer avant Yassin
        'avantage_repas': {'applicable': False},   # à confirmer — pas d'avantage repas standard connu
        'cheques_repas': {
            'obligatoire': True,
            'valeur_totale_jour': 3.09,
            'depuis': '01/01/2026',
            # part employeur/travailleur non confirmées avec certitude — À VÉRIFIER avant Yassin
        },
        'rgpt': {
            'applicable': True,
            'montant_jour': 1.63,   # PAR JOUR (ACCG, primes CP 121 au 01/07/2026) - corrige le 30/09/2026
        },
        'sectoriel_notes': [
            '⚠️ NON ENCORE VALIDÉ contre une fiche réelle — dossier Yassin est le premier '
            'cas d\'usage. Vérifier: part CR employeur/travailleur exactes, avantages '
            'sectoriels spécifiques (prime vêtements, prime saleté), fonds de sécurité '
            'd\'existence propre au nettoyage.',
        ],
        'indexation': {'derniere': '01/07/2026', 'prochaine_attendue': 'à vérifier'},
        'source': 'salairesminimums.be PC 1210000 — À RECOUPER avant premier client actif',
        'derniere_verification': '29/09/2026',
    },
}


def get_regles_cp(cp_key: str) -> dict:
    """Retourne les règles d'une CP, ou lève une erreur explicite si CP non gérée."""
    if cp_key not in REGLES_CP:
        raise ValueError(
            f"CP '{cp_key}' non définie dans regles_cp.py — "
            f"aucun calcul de paie ne doit être fait pour une CP non documentée. "
            f"CP disponibles: {list(REGLES_CP.keys())}"
        )
    return REGLES_CP[cp_key]
