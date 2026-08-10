"""
moteur_paie.py — DuxSalary
Calcul complet de la fiche de paie belge 2026
Supporte : CP 140.03 (Transport), CP 302 (Horeca), CP 200, CP 336, CP 121, CP 124
"""

from datetime import date, datetime
import math

# ── BARÈMES LÉGAUX 2026 ──────────────────────────────────────────────

ONSS_PERSONNEL = 0.1307
ONSS_PATRONAL_BASE = 0.2700
ONSS_ETUDIANT_PERSONNEL = 0.0271
ONSS_ETUDIANT_PATRONAL = 0.0542

# Bonus à l'emploi (réduction ONSS bas salaires) 2026
# Champ B = réduction ONSS travailleur pour bas salaires
BONUS_EMPLOI_PLAFOND = 2826.00  # au-delà : pas de bonus
BONUS_EMPLOI_MAX = 175.32       # montant max mensuel

# Réduction structurelle ONSS patronal 2026
REDUCTION_STRUCTURELLE_BASE = 621.17  # forfait annuel
REDUCTION_STRUCTURELLE_BAS_SALAIRE_PLAFOND = 4000.00  # brut/trimestre

# Cotisation spéciale sécurité sociale 2026 (mensuelle, célibataire)
CSS_TRANCHES = [
    (0,      1945.39, 0.0),
    (1945.39, 2190.19, lambda b: (b - 1945.39) * 0.076),
    (2190.19, 6038.82, lambda b: 18.60 + (b - 2190.19) * 0.011),
    (6038.82, float('inf'), lambda b: 60.94),
]

# Barèmes précompte professionnel 2026 (simplifié, isolé sans charge)
# Sur base annualisée, tranches IPP
PRECOMPTE_TRANCHES_ANNUEL = [
    (0,       10160,  0.0),
    (10160,   14850,  0.2675),
    (14850,   24800,  0.3765),
    (24800,   40480,  0.4360),
    (40480,   float('inf'), 0.4930),
]

# Quotités exemptées annuelles 2026
QUOTITE_EXEMPTEE = {
    'celibataire': 10160,
    'marie_1_revenu': 11320,
    'isole_enfant': 10160,
}
REDUCTION_ENFANT_CHARGE = {
    1: 1850, 2: 4760, 3: 10660, 4: 16000, 5: 21000,
}

# ── INDEMNITÉS PAR CP ────────────────────────────────────────────────

CP_INDEMNITES = {
    'CP 302': {
        'avantage_repas_jour': 1.09,       # soumis ONSS, déduit du net
        'indem_vetements_jour': 4.40,      # exonéré ONSS
        'indem_deplacement_jour': 1.98,    # exonéré ONSS (domicile-travail fixe)
        'cheques_repas_jour': 0.0,         # pas obligatoire CP 302
        'onss_patronal': 0.2700,
    },
    'CP 140.03': {
        'rgpt_heure': 1.8175,                # exonéré ONSS, net
        'cheques_repas_jour': 3.09,        # depuis 01/07/2026, exonéré ONSS
        'indem_vetements_jour': 0.0,       # vêtements fournis et entretenus par employeur
        'indem_deplacement_jour': 0.0,     # selon km (calculé séparément)
        'arab_heure': 0.0,                 # ARAB selon CCT entreprise (optionnel)
        'onss_patronal': 0.2700,
    },
    'CP 121': {
        'rgpt_jour': 1.63,
        'cheques_repas_jour': 3.09,
        'indem_vetements_semaine': 2.517,
        'onss_patronal': 0.2700,
    },
    'CP 124': {
        'cheques_repas_jour': 0.0,
        'onss_patronal': 0.2700,
    },
    'CP 200': {
        'onss_patronal': 0.2500,
    },
    'CP 336': {
        'onss_patronal': 0.2500,
    },
}

def calcul_css(brut_imposable_mensuel, etat_civil='celibataire', nb_enfants=0):
    """Cotisation spéciale sécurité sociale 2026."""
    b = brut_imposable_mensuel
    if b <= 1945.39:
        return 0.0
    elif b <= 2190.19:
        return round((b - 1945.39) * 0.076, 2)
    elif b <= 6038.82:
        return round(18.60 + (b - 2190.19) * 0.011, 2)
    else:
        return 60.94

def calcul_bonus_emploi(brut_mensuel, heures_semaine_reel=38.0, heures_semaine_ref=38.0):
    """Bonus à l'emploi = réduction ONSS travailleur pour bas salaires 2026.
    Formule officielle ONSS 2026 — deux volets A et B.
    Pour temps partiel: conversion en équivalent temps plein d'abord."""
    if heures_semaine_reel <= 0:
        return 0.0
    
    # Conversion en salaire équivalent temps plein
    ratio = heures_semaine_reel / heures_semaine_ref
    if ratio < 1.0 and ratio > 0:
        brut_etp = brut_mensuel / ratio
    else:
        brut_etp = brut_mensuel
    
    # Volet A (bas salaires) — plafond 2 792,16 EUR/mois (temps plein)
    SEUIL_A_BAS = 1945.38
    SEUIL_A_HAUT = 2792.16
    MAX_A = 229.01
    
    if brut_etp <= SEUIL_A_BAS:
        bonus_a = MAX_A
    elif brut_etp <= SEUIL_A_HAUT:
        bonus_a = round(MAX_A * (SEUIL_A_HAUT - brut_etp) / (SEUIL_A_HAUT - SEUIL_A_BAS), 2)
    else:
        bonus_a = 0.0
    
    # Volet B (très bas salaires) — plafond 2 777,83 EUR/mois (temps plein)
    SEUIL_B_BAS = 1945.38
    SEUIL_B_HAUT = 2777.83
    MAX_B = 0.0  # Volet B faible pour ouvriers — simplifié
    
    bonus_total_etp = bonus_a + MAX_B
    
    # Proratiser selon le régime temps partiel
    bonus_proratise = round(bonus_total_etp * ratio, 2)
    
    # Le bonus ne peut pas dépasser l'ONSS dû
    onss_du = round(brut_mensuel * ONSS_PERSONNEL, 2)
    return min(bonus_proratise, onss_du)

def calcul_reduction_structurelle(brut_mensuel):
    """Réduction structurelle ONSS patronal 2026.
    Plafonnée à l'ONSS patronal dû."""
    brut_trim = brut_mensuel * 3
    base = 521.47  # forfait mensuel
    if brut_trim < REDUCTION_STRUCTURELLE_BAS_SALAIRE_PLAFOND:
        complement = max(0, (REDUCTION_STRUCTURELLE_BAS_SALAIRE_PLAFOND - brut_trim) * 0.1800)
        reduction = round(base + complement / 3, 2)
    else:
        reduction = round(base, 2)
    # Plafonner à l'ONSS patronal dû
    onss_patron_du = round(brut_mensuel * ONSS_PATRONAL_BASE, 2)
    return min(reduction, onss_patron_du)

def calcul_precompte(brut_imposable_mensuel, etat_civil='celibataire', nb_enfants=0):
    """Calcul précompte professionnel 2026 par mensualisation."""
    # Annualiser
    brut_annuel = brut_imposable_mensuel * 12
    
    # Quotité exemptée de base
    quotite = QUOTITE_EXEMPTEE.get(etat_civil, 10160)
    
    # Réduction pour enfants à charge
    if nb_enfants > 0:
        red_enfants = REDUCTION_ENFANT_CHARGE.get(min(nb_enfants, 5), 21000)
    else:
        red_enfants = 0
    
    # Base imposable annuelle après quotité
    base_imposable = max(0, brut_annuel - quotite)
    
    # Calcul IPP par tranches
    precompte_annuel = 0
    tranches = [
        (10160,  14850,  0.2675),
        (14850,  24800,  0.3765),
        (24800,  40480,  0.4360),
        (40480,  float('inf'), 0.4930),
    ]
    revenu_restant = base_imposable
    for bas, haut, taux in tranches:
        if revenu_restant <= 0:
            break
        tranche = min(revenu_restant, (haut - bas) if haut != float('inf') else revenu_restant)
        precompte_annuel += tranche * taux
        revenu_restant -= tranche
    
    # Réduction pour enfants à charge
    precompte_annuel = max(0, precompte_annuel - red_enfants)
    
    # Ramener au mensuel
    precompte_mensuel = round(precompte_annuel / 12, 2)
    return precompte_mensuel

def calculer_fiche_paie(
    # Données travailleur
    prenom, nom, niss, adresse, iban,
    date_naissance, date_entree,
    # Données employeur
    nom_societe, adresse_societe, bce_societe, rsz_societe,
    # Contrat
    cp_key, categorie, salaire_horaire,
    # Optionnels
    etat_civil='celibataire', nb_enfants=0,
    heures_semaine=38.0, heures_jour=7.6, jours_semaine=5, type_contrat='CDD', is_etudiant=False,
    premier_engagement=False,
    # Prestations du mois
    jours_prestes=0, heures_prestees=0.0,
    jours_feries_payes=0, heures_feries=0.0,
    jours_conge=0, jours_maladie=0, jours_chomage=0,
    # Indemnités
    km_domicile=0, moyen_transport='voiture', vehicule_societe=False,
    rgpt_actif=True, arab_heure=0.0, cheques_repas=True,
    # Période
    periode_debut=None, periode_fin=None,
):
    """Calcule la fiche de paie complète selon la CP et retourne un dict structuré."""
    
    indemnites_cp = CP_INDEMNITES.get(cp_key, {})
    onss_taux = ONSS_ETUDIANT_PERSONNEL if is_etudiant else ONSS_PERSONNEL
    onss_patronal_taux = indemnites_cp.get('onss_patronal', 0.2700)
    
    # Régime de travail réel
    heures_semaine_reel = round(heures_jour * jours_semaine, 2)
    regime_str = f"{heures_semaine_reel:.2f}h/sem ({heures_jour}h/j × {jours_semaine}j)"
    
    # ── ÉLÉMENTS DES SALAIRES ──────────────────────────────────────
    lignes_salaire = []
    
    # 1. Prestations
    montant_prestations = round(salaire_horaire * heures_prestees, 2)
    if jours_prestes > 0:
        lignes_salaire.append({
            'libelle': 'Prestation (jours-heures)',
            'base': salaire_horaire,
            'jours': jours_prestes,
            'heures': heures_prestees,
            'montant': montant_prestations,
            'soumis_onss': True,
        })
    
    # 2. Jours fériés payés
    montant_feries = round(salaire_horaire * heures_feries, 2)
    if jours_feries_payes > 0:
        lignes_salaire.append({
            'libelle': 'Jour férié payé (jours-heures)',
            'base': salaire_horaire,
            'jours': jours_feries_payes,
            'heures': heures_feries,
            'montant': montant_feries,
            'soumis_onss': True,
        })
    
    # 3. Avantage en nature repas (CP 302 — soumis ONSS)
    montant_avantage_repas = 0.0
    avantage_repas_jour = indemnites_cp.get('avantage_repas_jour', 0.0)
    if avantage_repas_jour > 0 and jours_prestes > 0:
        montant_avantage_repas = round(avantage_repas_jour * jours_prestes, 2)
        lignes_salaire.append({
            'libelle': 'Avantages en nature Repas',
            'base': avantage_repas_jour,
            'jours': jours_prestes,
            'heures': 0,
            'montant': montant_avantage_repas,
            'soumis_onss': True,
        })
    
    # ── BRUT SOUMIS À L'ONSS ──────────────────────────────────────
    brut_onss = sum(l['montant'] for l in lignes_salaire if l['soumis_onss'])
    
    # ── ONSS TRAVAILLEUR ──────────────────────────────────────────
    onss_travailleur = round(brut_onss * onss_taux, 2)
    
    # Bonus à l'emploi (réduit l'ONSS travailleur)
    bonus_emploi = 0.0 if is_etudiant else calcul_bonus_emploi(brut_onss, heures_semaine_reel, heures_semaine)
    onss_net = round(max(0, onss_travailleur - bonus_emploi), 2)
    
    # ── IMPOSABLE ─────────────────────────────────────────────────
    brut_imposable = round(brut_onss - onss_net, 2)
    
    # ── PRÉCOMPTE PROFESSIONNEL ───────────────────────────────────
    precompte = 0.0
    if not is_etudiant:
        precompte = calcul_precompte(brut_imposable, etat_civil, nb_enfants)
    else:
        precompte = 0.0  # Étudiants : pas de précompte sous 650h
    
    # ── INDEMNITÉS EXONÉRÉES (hors ONSS, hors IPP) ───────────────
    lignes_indemn = []
    
    # Indemnité vêtements (CP 302 : 4,40€/j)
    indem_vetements = indemnites_cp.get('indem_vetements_jour', 0.0)
    montant_vetements = 0.0
    if indem_vetements > 0 and jours_prestes > 0:
        montant_vetements = round(indem_vetements * jours_prestes, 2)
        lignes_indemn.append({
            'libelle': 'Indemnité vêtements',
            'detail': f'{indem_vetements:.4f} eur/jour',
            'jours': jours_prestes,
            'montant': montant_vetements,
        })
    
    # Déplacement domicile-travail (CP 302 : 1,98€/j fixe)
    indem_deplacement = indemnites_cp.get('indem_deplacement_jour', 0.0)
    montant_deplacement = 0.0
    if indem_deplacement > 0 and jours_prestes > 0 and not vehicule_societe:
        montant_deplacement = round(indem_deplacement * jours_prestes, 2)
        lignes_indemn.append({
            'libelle': 'Déplacement maison/travail',
            'detail': f'{indem_deplacement:.4f} eur/jour',
            'jours': jours_prestes,
            'montant': montant_deplacement,
        })
    
    # Indemnité km (si voiture personnelle et km > 0 et pas véhicule société)
    montant_km = 0.0
    if km_domicile > 0 and moyen_transport == 'voiture' and not vehicule_societe and indem_deplacement == 0:
        taux_km = 0.4444  # taux fiscal 2026
        montant_km = round(taux_km * km_domicile * 2 * jours_prestes, 2)
        lignes_indemn.append({
            'libelle': f'Indemnité kilométrique ({km_domicile} km)',
            'detail': f'{taux_km} €/km',
            'jours': jours_prestes,
            'montant': montant_km,
        })
    
    # RGPT (CP 140.03, CP 121)
    montant_rgpt = 0.0
    rgpt_heure = indemnites_cp.get('rgpt_heure', 0.0)
    if rgpt_heure > 0 and rgpt_actif and heures_prestees > 0:
        heures_rgpt = math.ceil(heures_prestees)  # arrondi à l'unité supérieure
        montant_rgpt = round(rgpt_heure * heures_rgpt, 2)
        lignes_indemn.append({
            'libelle': f'Indemnité RGPT ({heures_rgpt}h)',
            'detail': f'{rgpt_heure:.4f} €/h',
            'jours': 0,
            'montant': montant_rgpt,
            'note': 'exonérée ONSS et IPP',
        })
    
    # ARAB (si saisi)
    montant_arab = 0.0
    if arab_heure > 0 and heures_prestees > 0:
        montant_arab = round(arab_heure * heures_prestees, 2)
        lignes_indemn.append({
            'libelle': 'Allocation de remplacement de bénéfice (ARAB)',
            'detail': f'{arab_heure:.4f} €/h',
            'jours': round(heures_prestees, 1),
            'montant': montant_arab,
            'note': 'exonérée ONSS dans limites légales',
        })
    
    # Chèques-repas (exonérés ONSS sous conditions)
    montant_cheques = 0.0
    cheques_jour = indemnites_cp.get('cheques_repas_jour', 0.0)
    if cheques_repas and cheques_jour > 0 and jours_prestes > 0:
        montant_cheques = round(cheques_jour * jours_prestes, 2)
        lignes_indemn.append({
            'libelle': f'Chèques-repas ({cheques_jour:.2f} €/jour)',
            'detail': f'{cheques_jour:.2f} €/jour',
            'jours': jours_prestes,
            'montant': montant_cheques,
            'note': 'exonéré ONSS (AR 28/11/1969)',
        })
    
    # Déduction avantage nature repas (CP 302 — déduit du net)
    deduction_avantage_repas = 0.0
    if avantage_repas_jour > 0 and montant_avantage_repas > 0:
        deduction_avantage_repas = -montant_avantage_repas
        lignes_indemn.append({
            'libelle': 'Calcul avantage en nature - repas',
            'montant': deduction_avantage_repas,
        })
    
    # Cotisation spéciale sécurité sociale
    css = 0.0 if is_etudiant else calcul_css(brut_imposable, etat_civil, nb_enfants)
    if css > 0:
        lignes_indemn.append({
            'libelle': 'Cotisation spéciale sécurité sociale',
            'montant': -css,
        })
    
    # ── SALAIRE NET ───────────────────────────────────────────────
    total_indemn_nettes = (
        montant_vetements + montant_deplacement + montant_km +
        montant_rgpt + montant_arab + montant_cheques +
        deduction_avantage_repas - css
    )
    salaire_net = round(brut_imposable - precompte + total_indemn_nettes, 2)
    
    # ── SECTION INFORMATION (charges employeur) ───────────────────
    onss_patronal_brut = round(brut_onss * onss_patronal_taux, 2)
    reduction_structurelle = calcul_reduction_structurelle(brut_onss)
    # Réduction premier engagement
    reduction_premier_engagement = 0.0
    if premier_engagement:
        max_mensuel = round(2000.0 / 3, 2)
        ratio_tp = heures_semaine_reel / heures_semaine if heures_semaine > 0 else 1.0
        reduction_premier_engagement = round(min(max_mensuel * ratio_tp, onss_patronal_brut), 2)
    onss_patronal_net = round(max(0, onss_patronal_brut - reduction_structurelle - reduction_premier_engagement), 2)
    cout_employeur = round(brut_onss + onss_patronal_net + montant_vetements + montant_deplacement + montant_km + montant_rgpt + montant_arab + montant_cheques, 2)
    
    # Ancienneté
    today = date.today()
    anciennete_mois = (today.year - date_entree.year) * 12 + today.month - date_entree.month if date_entree else 0
    anciennete_ans = anciennete_mois // 12
    anciennete_mois_reste = anciennete_mois % 12
    
    return {
        # En-tête
        'periode_debut': periode_debut,
        'periode_fin': periode_fin,
        'nom_societe': nom_societe,
        'adresse_societe': adresse_societe,
        'bce_societe': bce_societe,
        'rsz_societe': rsz_societe,
        'prenom': prenom,
        'nom': nom,
        'niss': niss,
        'adresse': adresse,
        'iban': iban,
        'date_naissance': date_naissance,
        'date_entree': date_entree,
        'anciennete': f'{anciennete_ans}a , {anciennete_mois_reste}m',
        'etat_civil': etat_civil,
        'nb_enfants': nb_enfants,
        'cp_key': cp_key,
        'categorie': categorie,
        'salaire_horaire': salaire_horaire,
        'heures_semaine': heures_semaine,
        'heures_semaine_reel': heures_semaine_reel,
        'heures_jour': heures_jour,
        'jours_semaine': jours_semaine,
        'regime_str': regime_str,
        'type_contrat': type_contrat,
        'is_etudiant': is_etudiant,
        # Éléments de salaire
        'lignes_salaire': lignes_salaire,
        'brut_onss': brut_onss,
        'onss_travailleur': -onss_travailleur,
        'onss_net': -onss_net,
        'bonus_emploi': bonus_emploi,
        'brut_imposable': brut_imposable,
        'precompte': -precompte,
        # Indemnités
        'lignes_indemn': lignes_indemn,
        # Résultat
        'salaire_net': salaire_net,
        # Section information
        'onss_patronal': onss_patronal_net,
        'premier_engagement': premier_engagement,
        'reduction_premier_engagement': reduction_premier_engagement,
        'ded_cot_onss_trav': bonus_emploi,
        'onss_bas_salaires_champ_b': reduction_structurelle,
        'cout_employeur': cout_employeur,
        # À payer
        'a_payer': salaire_net,
    }


# ── TEST ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    result = calculer_fiche_paie(
        prenom='Akattof', nom='Bilal', niss='06.10.18-379.82',
        adresse='Lidrusweg bâtiment 3/3.4 - 1130 Bruxelles', iban='BE75363178356651',
        date_naissance=date(2006, 10, 18), date_entree=date(2026, 7, 9),
        etat_civil='celibataire', nb_enfants=0,
        nom_societe="98'H BARBER", adresse_societe='Rue Marcel Marien/17 - 1030 Bruxelles',
        bce_societe='0800.078.071', rsz_societe='51365632-19',
        cp_key='CP 140.03', categorie='Personnel roulant — Niveau 1',
        salaire_horaire=14.9255, heures_semaine=38.0,
        type_contrat='CDD', is_etudiant=False,
        jours_prestes=21, heures_prestees=159.6,
        jours_feries_payes=0, heures_feries=0,
        rgpt_actif=True, cheques_repas=True, vehicule_societe=True,
        periode_debut=date(2026, 7, 1), periode_fin=date(2026, 7, 31),
    )
    print(f"Brut ONSS:    {result['brut_onss']:.2f} €")
    print(f"ONSS trav:    {result['onss_net']:.2f} €")
    print(f"Imposable:    {result['brut_imposable']:.2f} €")
    print(f"Précompte:    {result['precompte']:.2f} €")
    print(f"NET:          {result['salaire_net']:.2f} €")
    print(f"Bonus emploi: {result['bonus_emploi']:.2f} €")
    print(f"ONSS patron:  {result['onss_patronal']:.2f} €")
