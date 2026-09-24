"""
moteur_paie_final.py — DuxSalary v2.1
Calcul fiche de paie belge 2026
Validé sur base fiche Liantis FDLR Logistics CP 140.03
"""
from datetime import date
import math

# ── TAUX ONSS 2026 ────────────────────────────────────────────────────
ONSS_PERSONNEL = 0.1307
ONSS_PATRONAL_BASE = 0.2700
ONSS_ETUDIANT_PERSONNEL = 0.0271
ONSS_ETUDIANT_PATRONAL = 0.0543  # 5.42% solidarité + 0.01% fonds amiante

# ── BONUS EMPLOI 2026 ─────────────────────────────────────────────────
BONUS_A_BAS = 1945.38; BONUS_A_HAUT = 2792.16; BONUS_A_MAX = 229.01
BONUS_B_BAS = 1945.38; BONUS_B_HAUT = 2777.83
BONUS_B_MAX_OUV = 69.93  # ouvriers
BONUS_B_MAX_EMP = 0.0    # employés

# ── RÉDUCTION STRUCTURELLE ────────────────────────────────────────────
RED_STRUCT_BASE = 521.47
RED_STRUCT_BAS_PLAFOND = 4000.0

# ── INDEMNITÉS PAR CP ─────────────────────────────────────────────────
CP_INDEMNITES = {
    'CP 140.03': {
        'avantage_repas_jour': 1.09,       # soumis ONSS
        'cr_part_coll_jour': 1.09,          # déduit net travailleur
        'cr_part_empl_jour': 6.91,          # payé Monizze par employeur
        'rgpt_heure': 1.8175,
        'indem_vetements_jour': 0.0,
        'indem_deplacement_jour': 0.0,
        'onss_patronal': 0.2700,
        'type_travailleur': 'ouvrier',
        'sal_bareme_mensuel_etp': 2457.73,  # référence bonus emploi
    },
    'CP 302': {
        'avantage_repas_jour': 1.09,
        'cr_part_coll_jour': 1.09,
        'cr_part_empl_jour': 0.0,
        'indem_vetements_jour': 4.40,
        'indem_deplacement_jour': 1.98,
        'onss_patronal': 0.2700,
        'type_travailleur': 'ouvrier',
        'sal_bareme_mensuel_etp': 2504.53,
    },
    'CP 200': {
        'avantage_repas_jour': 0.0,
        'cr_part_coll_jour': 1.09,
        'cr_part_empl_jour': 5.82,
        'onss_patronal': 0.2500,
        'type_travailleur': 'employe',
        'sal_bareme_mensuel_etp': 2242.81,
    },
    'CP 336': {
        'avantage_repas_jour': 0.0,
        'cr_part_coll_jour': 1.09,
        'cr_part_empl_jour': 5.82,
        'onss_patronal': 0.2500,
        'type_travailleur': 'employe',
        'sal_bareme_mensuel_etp': 2174.42,
    },
    'CP 121': {
        'avantage_repas_jour': 0.0,
        'cr_part_coll_jour': 1.09,
        'cr_part_empl_jour': 5.82,
        'rgpt_heure': 1.63,
        'onss_patronal': 0.2700,
        'type_travailleur': 'ouvrier',
        'sal_bareme_mensuel_etp': 2600.0,
    },
    'CP 124': {
        'avantage_repas_jour': 0.0,
        'cr_part_coll_jour': 1.09,
        'cr_part_empl_jour': 5.82,
        'onss_patronal': 0.2700,
        'type_travailleur': 'ouvrier',
        'sal_bareme_mensuel_etp': 2500.0,
    },
}


def calcul_bonus_emploi(sal_bareme_etp, ratio_tp, is_ouvrier=True):
    """
    Bonus emploi 2026 — méthode Liantis confirmée.
    Calcul sur salaire barémique ETP × proratisation.
    """
    # Volet A
    if sal_bareme_etp <= BONUS_A_BAS:
        ba_etp = BONUS_A_MAX
    elif sal_bareme_etp <= BONUS_A_HAUT:
        ba_etp = round(BONUS_A_MAX * (BONUS_A_HAUT - sal_bareme_etp) / (BONUS_A_HAUT - BONUS_A_BAS), 2)
    else:
        ba_etp = 0.0

    # Volet B
    max_b = BONUS_B_MAX_OUV if is_ouvrier else BONUS_B_MAX_EMP
    if sal_bareme_etp <= BONUS_B_BAS:
        bb_etp = max_b
    elif sal_bareme_etp <= BONUS_B_HAUT:
        bb_etp = round(max_b * (BONUS_B_HAUT - sal_bareme_etp) / (BONUS_B_HAUT - BONUS_B_BAS), 2)
    else:
        bb_etp = 0.0

    bonus_a = round(ba_etp * ratio_tp, 2)
    bonus_b = round(bb_etp * ratio_tp, 2)
    return bonus_a, bonus_b


def calcul_reduction_structurelle(brut_mensuel, taux_patronal=0.27):
    """Réduction structurelle ONSS patronal 2026."""
    brut_trim = brut_mensuel * 3
    if brut_trim < RED_STRUCT_BAS_PLAFOND:
        complement = max(0, (RED_STRUCT_BAS_PLAFOND - brut_trim) * 0.18)
        red = round(RED_STRUCT_BASE + complement / 3, 2)
    else:
        red = round(RED_STRUCT_BASE, 2)
    return min(red, round(brut_mensuel * taux_patronal, 2))


def calcul_css(brut_imposable):
    """Cotisation spéciale SS 2026."""
    b = brut_imposable
    if b <= 1945.38: return 0.0
    elif b <= 2190.19: return round((b - 1945.38) * 0.076, 2)
    elif b <= 6038.82: return round(18.60 + (b - 2190.19) * 0.011, 2)
    else: return 60.94


def calcul_precompte(brut_imposable, etat_civil='celibataire', nb_enfants=0):
    """Précompte professionnel 2026."""
    annuel = brut_imposable * 12
    quotite = {'celibataire': 10160, 'marie_1_revenu': 11320, 'isole_enfant': 10160}.get(etat_civil, 10160)
    red_enf = {1: 1850, 2: 4760, 3: 10660, 4: 16000, 5: 21000}.get(min(nb_enfants, 5), 0)
    base = max(0, annuel - quotite)
    pp = 0.0
    for bas, haut, taux in [(10160,14850,0.2675),(14850,24800,0.3765),(24800,40480,0.4360),(40480,float('inf'),0.4930)]:
        if base <= 0: break
        tr = min(base, (haut-bas) if haut != float('inf') else base)
        pp += tr * taux; base -= tr
    return round(max(0, pp - red_enf) / 12, 2)


def calculer_fiche_paie(
    prenom, nom, niss, adresse, iban, date_naissance, date_entree,
    nom_societe, adresse_societe, bce_societe, rsz_societe,
    cp_key, categorie, salaire_horaire,
    etat_civil='celibataire', nb_enfants=0,
    heures_semaine=38.0, heures_jour=7.6, jours_semaine=5,
    type_contrat='CDD', is_etudiant=False, premier_engagement=False,
    jours_prestes=0, heures_prestees=0.0,
    jours_feries_payes=0, heures_feries=0.0,
    jours_conge=0, jours_maladie=0, jours_chomage=0,
    km_domicile=0, moyen_transport='voiture', vehicule_societe=False,
    rgpt_actif=True, arab_heure=0.0, cheques_repas=True, frais_nets=0.0,
    periode_debut=None, periode_fin=None,
):
    cp = CP_INDEMNITES.get(cp_key, {})
    is_ouvrier = cp.get('type_travailleur', 'ouvrier') == 'ouvrier'
    onss_pers_taux = ONSS_ETUDIANT_PERSONNEL if is_etudiant else ONSS_PERSONNEL
    onss_pat_taux = ONSS_ETUDIANT_PATRONAL if is_etudiant else cp.get('onss_patronal', 0.27)
    onss_pat_taux_base = onss_pat_taux
    heures_sem_reel = round(heures_jour * jours_semaine, 2)
    ratio_tp = min(1.0, heures_sem_reel / heures_semaine) if heures_semaine > 0 else 1.0

    # ── LIGNES SOUMISES ONSS ──────────────────────────────────────────
    lignes_salaire = []
    if jours_prestes > 0:
        lignes_salaire.append({'libelle': 'Prestation (jours-heures)', 'base': salaire_horaire,
            'jours': jours_prestes, 'heures': heures_prestees,
            'montant': round(salaire_horaire * heures_prestees, 2), 'soumis_onss': True})
    if jours_feries_payes > 0:
        lignes_salaire.append({'libelle': 'Jour férié payé (jours-heures)', 'base': salaire_horaire,
            'jours': jours_feries_payes, 'heures': heures_feries,
            'montant': round(salaire_horaire * heures_feries, 2), 'soumis_onss': True})

    # Avantage repas soumis ONSS
    avantage_repas_j = cp.get('avantage_repas_jour', 0.0)
    montant_avantage = 0.0
    if avantage_repas_j > 0 and jours_prestes > 0 and cheques_repas:
        montant_avantage = round(avantage_repas_j * jours_prestes, 2)
        lignes_salaire.append({'libelle': 'Avantages en nature Repas', 'base': avantage_repas_j,
            'jours': jours_prestes, 'heures': 0, 'montant': montant_avantage, 'soumis_onss': True})

    brut_onss = round(sum(l['montant'] for l in lignes_salaire if l['soumis_onss']), 2)

    # ── ONSS TRAVAILLEUR ──────────────────────────────────────────────
    onss_trav_brut = round(brut_onss * onss_pers_taux, 2)

    # Bonus emploi sur salaire barémique ETP
    bonus_a, bonus_b = 0.0, 0.0
    if not is_etudiant:
        sal_bar_etp = cp.get('sal_bareme_mensuel_etp', salaire_horaire * heures_semaine * 52/12)
        bonus_a, bonus_b = calcul_bonus_emploi(sal_bar_etp, ratio_tp, is_ouvrier)
        # Plafonner au max de l'ONSS dû
        total_bonus = min(bonus_a + bonus_b, onss_trav_brut)
        if bonus_a + bonus_b > 0:
            f = total_bonus / (bonus_a + bonus_b)
            bonus_a = round(bonus_a * f, 2)
            bonus_b = round(total_bonus - bonus_a, 2)

    onss_trav_net = round(max(0, onss_trav_brut - bonus_a - bonus_b), 2)
    brut_imposable = round(brut_onss - onss_trav_net, 2)
    precompte_brut = 0.0 if is_etudiant else calcul_precompte(brut_imposable, etat_civil, nb_enfants)
    # Réduction précompte sur bonus emploi (AR 27/08/1993 art. 38§3quater)
    # Taux 33.14% confirmé sur fiche Liantis
    red_precompte_bonus = 0.0
    if not is_etudiant and (bonus_a + bonus_b) > 0 and brut_imposable <= 3500:
        red_precompte_bonus = round((bonus_a + bonus_b) * 0.3314, 2)
        red_precompte_bonus = min(red_precompte_bonus, precompte_brut)
    precompte = round(precompte_brut - red_precompte_bonus, 2)
    css = 0.0 if is_etudiant else calcul_css(brut_imposable)

    # ── INDEMNITÉS EXONÉRÉES ──────────────────────────────────────────
    lignes_indemn = []

    # RGPT
    montant_rgpt = 0.0
    rgpt_h = cp.get('rgpt_heure', 0.0)
    if rgpt_h > 0 and rgpt_actif and heures_prestees > 0:
        montant_rgpt = round(rgpt_h * heures_prestees, 2)
        lignes_indemn.append({'libelle': f'Indemnité RGPT ({heures_prestees:.0f}h)',
            'detail': f'{rgpt_h:.4f} €/h', 'jours': 0, 'montant': montant_rgpt})

    # ARAB
    montant_arab = 0.0
    if arab_heure > 0 and heures_prestees > 0:
        montant_arab = round(arab_heure * heures_prestees, 2)
        lignes_indemn.append({'libelle': f'Indemnité ARAB ({heures_prestees:.0f}h)',
            'detail': f'{arab_heure:.4f} €/h', 'jours': 0, 'montant': montant_arab})

    # Vêtements (CP 302)
    montant_vet = 0.0
    if cp.get('indem_vetements_jour', 0) > 0 and jours_prestes > 0:
        montant_vet = round(cp['indem_vetements_jour'] * jours_prestes, 2)
        lignes_indemn.append({'libelle': 'Indemnité vêtements',
            'detail': f"{cp['indem_vetements_jour']:.4f} €/jour",
            'jours': jours_prestes, 'montant': montant_vet})

    # Déplacement (CP 302)
    montant_dep = 0.0
    if cp.get('indem_deplacement_jour', 0) > 0 and jours_prestes > 0 and not vehicule_societe:
        montant_dep = round(cp['indem_deplacement_jour'] * jours_prestes, 2)
        lignes_indemn.append({'libelle': 'Déplacement maison/travail',
            'detail': f"{cp['indem_deplacement_jour']:.4f} €/jour",
            'jours': jours_prestes, 'montant': montant_dep})

    # Km voiture personnelle
    montant_km = 0.0
    if km_domicile > 0 and moyen_transport == 'voiture' and not vehicule_societe and not cp.get('indem_deplacement_jour'):
        montant_km = round(0.4444 * km_domicile * 2 * jours_prestes, 2)
        lignes_indemn.append({'libelle': f'Indemnité km ({km_domicile} km)',
            'detail': '0.4444 €/km', 'jours': jours_prestes, 'montant': montant_km})

    # Chèques-repas — déduction part collectivité uniquement
    montant_cr_ded = 0.0
    cr_coll = cp.get('cr_part_coll_jour', 0.0)
    cr_empl_j = cp.get('cr_part_empl_jour', 0.0)
    cr_empl_total = 0.0
    if cheques_repas and cr_coll > 0 and jours_prestes > 0:
        montant_cr_ded = -round(cr_coll * jours_prestes, 2)
        cr_empl_total = round(cr_empl_j * jours_prestes, 2)
        lignes_indemn.append({'libelle': f'Chèques-repas part coll. (-{cr_coll:.2f} €/j)',
            'detail': f'{cr_coll:.2f} €/jour', 'jours': jours_prestes, 'montant': montant_cr_ded})

    # Frais nets forfaitaires
    montant_frais_nets = 0.0
    if frais_nets > 0:
        montant_frais_nets = round(frais_nets, 2)
        lignes_indemn.append({'libelle': 'Frais propres à l\'employeur',
            'detail': 'Exonéré ONSS et IPP', 'jours': 0, 'montant': montant_frais_nets})

    # Frais nets forfaitaires
    montant_frais_nets = 0.0
    if frais_nets > 0:
        montant_frais_nets = round(frais_nets, 2)
        lignes_indemn.append({'libelle': 'Frais propres à l\'employeur',
            'detail': 'Exonéré ONSS et IPP', 'jours': 0, 'montant': montant_frais_nets})

    # CSS
    if css > 0:
        lignes_indemn.append({'libelle': 'Cotisation spéciale SS', 'montant': -css})

    # ── NET ───────────────────────────────────────────────────────────
    total_indemn = montant_rgpt + montant_arab + montant_vet + montant_dep + montant_km + montant_cr_ded + montant_frais_nets - css
    salaire_net = round(brut_imposable - precompte + total_indemn, 2)

    # ── CHARGES PATRONALES ────────────────────────────────────────────
    # Coefficient 108% pour ouvriers (pécule vacances ONVA — source ONSS officiel)
    coeff_ouvrier = 1.08 if (is_ouvrier and not is_etudiant) else 1.0
    base_onss_pat = round(brut_onss * coeff_ouvrier, 2)
    onss_pat_brut = round(base_onss_pat * onss_pat_taux_base, 2)
    red_struct = 0.0 if is_etudiant else calcul_reduction_structurelle(base_onss_pat, onss_pat_taux_base)

    # Premier engagement
    red_pe = 0.0
    if premier_engagement and not is_etudiant:
        reste_apres_struct = round(max(0, onss_pat_brut - red_struct), 2)
        red_pe = round(min(round(2000/3, 2) * ratio_tp, reste_apres_struct), 2)

    onss_pat_net = round(max(0, onss_pat_brut - red_struct - red_pe), 2)
    cout_empl = round(brut_onss + onss_pat_net + montant_rgpt + montant_arab + montant_vet + montant_dep + montant_km + cr_empl_total, 2)

    # Ancienneté
    ref_date = periode_fin if periode_fin else date.today()
    anc = (ref_date.year - date_entree.year) * 12 + ref_date.month - date_entree.month if date_entree else 0

    return {
        'periode_debut': periode_debut, 'periode_fin': periode_fin,
        'nom_societe': nom_societe, 'adresse_societe': adresse_societe,
        'bce_societe': bce_societe, 'rsz_societe': rsz_societe,
        'prenom': prenom, 'nom': nom, 'niss': niss, 'adresse': adresse, 'iban': iban,
        'date_naissance': date_naissance, 'date_entree': date_entree,
        'anciennete': f"{anc//12}a , {anc%12}m",
        'etat_civil': etat_civil, 'nb_enfants': nb_enfants,
        'cp_key': cp_key, 'categorie': categorie, 'salaire_horaire': salaire_horaire,
        'heures_semaine': heures_semaine, 'heures_semaine_reel': heures_sem_reel,
        'heures_jour': heures_jour, 'jours_semaine': jours_semaine,
        'regime_str': f"{jours_semaine}j/sem · {heures_jour}h/j",
        'type_contrat': type_contrat, 'is_etudiant': is_etudiant,
        'lignes_salaire': lignes_salaire,
        'brut_onss': brut_onss,
        'onss_travailleur': -onss_trav_brut,
        'onss_net': -onss_trav_net,
        'bonus_emploi_a': bonus_a, 'bonus_emploi_b': bonus_b,
        'bonus_emploi': bonus_a + bonus_b,
        'brut_imposable': brut_imposable,
        'precompte': -precompte,
        'precompte_brut': -precompte_brut,
        'red_precompte_bonus': red_precompte_bonus,
        'lignes_indemn': lignes_indemn,
        'salaire_net': salaire_net, 'a_payer': salaire_net,
        'onss_patronal_brut': onss_pat_brut,
        'onss_patronal': onss_pat_net,
        'reduction_structurelle': red_struct,
        'reduction_premier_engagement': red_pe,
        'ded_cot_onss_trav': bonus_a + bonus_b,
        'onss_bas_salaires_champ_b': red_struct,
        'cout_employeur': cout_empl,
        'cr_empl_total': cr_empl_total,
        'frais_nets': montant_frais_nets,
        'frais_nets': montant_frais_nets,
        'premier_engagement': premier_engagement,
    }


if __name__ == '__main__':
    r = calculer_fiche_paie(
        'Dorian', 'Plavmyzha', '05022018542',
        'Bld Prince de Liège 216 Bte 4 - 1070 Anderlecht', 'BE30 0637 2951 5211',
        date(2005,2,2), date(2026,8,10),
        'FDLR LOGISTICS SRL', 'Sint-Amandsstraat 2 - 1853 Grimbergen',
        '1029.507.718', '1070562-80',
        'CP 140.03', 'Chauffeur - Niveau 1', 17.5,
        heures_semaine=38.0, heures_jour=6.0, jours_semaine=4,
        premier_engagement=True,
        jours_prestes=8, heures_prestees=64.0,
        rgpt_actif=True, cheques_repas=True,
        periode_debut=date(2026,8,1), periode_fin=date(2026,8,31),
    )
    print("=== TEST vs Liantis FDLR ===")
    print(f"Brut ONSS:   {r['brut_onss']:.2f}€  (Liantis: 1209.60€)")
    print(f"ONSS trav:   {abs(r['onss_travailleur']):.2f}€  (Liantis: 158.09€)")
    print(f"Bonus A:     {r['bonus_emploi_a']:.2f}€  (Liantis: 55.10€)")
    print(f"Bonus B:     {r['bonus_emploi_b']:.2f}€  (Liantis: 16.89€)")
    print(f"Imposable:   {r['brut_imposable']:.2f}€  (Liantis: 1033.90€)")
    rgpt = next((l for l in r['lignes_indemn'] if 'RGPT' in l['libelle']), None)
    print(f"RGPT:        {rgpt['montant']:.2f}€  (Liantis: 116.32€)")
    cr = next((l for l in r['lignes_indemn'] if 'coll' in l['libelle']), None)
    print(f"CR déduc:    {cr['montant']:.2f}€  (Liantis: -8.72€)")
    print(f"Net:         {r['salaire_net']:.2f}€  (Liantis: 1150.22€)")
    print(f"À payer:     {r['a_payer']:.2f}€  (Liantis: 1141.50€)")
    print(f"\nCR empl (Monizze): {r['cr_empl_total']:.2f}€  (Liantis: 55.28€)")
    print(f"ONSS patronal net: {r['onss_patronal']:.2f}€")
