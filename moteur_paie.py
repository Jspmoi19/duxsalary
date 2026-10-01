"""
moteur_paie_final.py — DuxSalary v2.1
Calcul fiche de paie belge 2026
Validé sur base fiche Liantis FDLR Logistics CP 140.03
"""
from datetime import date
import math
import sys as _sys; _sys.path.insert(0, '/var/www/duxsalary')
from profil_travailleur import construire_profil
from parametres_dates import get_precompte_params, get_bonus_emploi_plafond_annuel

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
        'cr_part_empl_jour': 6.91,
        'onss_patronal': 0.2500,
        'type_travailleur': 'employe',
        'sal_bareme_mensuel_etp': 2242.81,
        'prime_annuelle': 330.84,
    },
    'CP 336': {
        'avantage_repas_jour': 0.0,
        'cr_part_coll_jour': 1.09,
        'cr_part_empl_jour': 6.91,
        'onss_patronal': 0.2500,
        'type_travailleur': 'employe',
        'sal_bareme_mensuel_etp': 2254.30,    # minimum sectoriel 01/09/2026
        'sal_bareme_prof_liberal': 2321.93,   # professionnel libéral 103%
        'sal_bareme_etudiant': 2141.59,       # étudiant 95%
    },
    'CP 121': {
        'avantage_repas_jour': 0.0,
        'cr_part_coll_jour': 1.09,
        'cr_part_empl_jour': 5.82,
        'rgpt_jour': 1.63,   # PAR JOUR (ACCG, primes CP 121 au 01/07/2026) - corrige le 30/09/2026
        'onss_patronal': 0.2700,
        'type_travailleur': 'ouvrier',
        'sal_bareme_mensuel_etp': 2696.49,  # indexé 01/07/2026
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


def calcul_precompte(brut_imposable, etat_civil='celibataire', nb_enfants=0,
                     partenaire_revenus_pro='non', partenaire_pensions='non'):
    """Précompte professionnel 2026 — barèmes officiels SPF Finances."""
    annuel = brut_imposable * 12

    # Quotité exemptée selon état civil
    # Célibataire/divorcé/veuf/séparé : 10160€
    # Marié/cohabitant légal avec partenaire sans revenus ou revenus limités : 11320€
    etats_seuls = ['celibataire', 'divorce', 'veuf', 'separe_fait', 'separe_corps']
    etats_couple = ['marie', 'cohabitation_legale']

    if etat_civil in etats_couple:
        # Partenaire avec revenus professionnels > 290€/mois → quotité normale 10160
        if partenaire_revenus_pro == 'oui':
            quotite = 10160
        elif partenaire_revenus_pro == 'oui_max290':
            quotite = 11320  # partenaire revenus limités → transfert partiel
        else:
            quotite = 11320  # partenaire sans revenus → quotité majorée
    else:
        quotite = 10160

    # Réduction pour enfants à charge 2026
    red_enf = {1: 1850, 2: 4760, 3: 10660, 4: 16000, 5: 21000}.get(min(nb_enfants, 5), 0)
    if nb_enfants > 5:
        red_enf = 21000 + (nb_enfants - 5) * 5000

    base = max(0, annuel - quotite)
    pp = 0.0
    for bas, haut, taux in [(10160,14850,0.2675),(14850,24800,0.3765),(24800,40480,0.4360),(40480,float('inf'),0.4930)]:
        if base <= 0: break
        tr = min(base, (haut-bas) if haut != float('inf') else base)
        pp += tr * taux; base -= tr
    return round(max(0, pp - red_enf) / 12, 2)


def get_cp_from_db(cp_key):
    """Récupère les barèmes depuis la BDD si disponibles."""
    try:
        import sys; sys.path.insert(0, '/var/www/duxsalary')
        from database import get_conn
        from psycopg2.extras import RealDictCursor
        conn = get_conn(); cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM baremes_cp WHERE cp_key=%s ORDER BY montant_mensuel", (cp_key,))
        rows = cur.fetchall()
        cur.close(); conn.close()
        if rows:
            # Reconstruire le dict barèmes
            baremes = {r['categorie']: {'horaire': float(r['montant_horaire']), 'mensuel': float(r['montant_mensuel'])} for r in rows}
            return {'baremes': baremes, 'min_mensuel': min(float(r['montant_mensuel']) for r in rows)}
    except:
        pass
    return None

def calculer_fiche_paie(
    prenom, nom, niss, adresse, iban, date_naissance, date_entree,
    nom_societe, adresse_societe, bce_societe, rsz_societe,
    cp_key, categorie, salaire_horaire,
    etat_civil='celibataire', nb_enfants=0,
    partenaire_revenus_pro='non', partenaire_pensions='non',
    salaire_mensuel_fixe=0.0,
    categorie_employeur='000', code_ffe=None, code_importance=None,
    cheques_repas_calc=None,
    prime_exceptionnelle=0.0, libelle_prime="Prime de fin d'année",
    double_pecule=0.0, precompte_pecule_manuel=None,
    charges_famille=None,
    heures_semaine=38.0, heures_jour=7.6, jours_semaine=5,
    type_contrat='CDD', is_etudiant=False, premier_engagement=False,
    jours_prestes=0, heures_prestees=0.0,
    jours_feries_payes=0, heures_feries=0.0,
    jours_conge=0, jours_maladie=0, jours_chomage=0,
    km_domicile=0, moyen_transport='voiture', vehicule_societe=False,
    rgpt_actif=True, arab_heure=0.0, cheques_repas=True, frais_nets=0.0,
    taux_km=0.4444,
    periode_debut=None, periode_fin=None,
    bonus_emploi_cumul_annee=0.0,
):
    cp = CP_INDEMNITES.get(cp_key, {})
    # Override avec barèmes BDD si disponibles
    cp_db = get_cp_from_db(cp_key)
    if cp_db:
        cp = dict(cp)
        cp['sal_bareme_mensuel_etp'] = cp_db['min_mensuel']
    is_ouvrier = cp.get('type_travailleur', 'ouvrier') == 'ouvrier'

    # ── PROFIL TRAVAILLEUR — source unique pour les décisions ONSS/précompte/bonus ──
    statut_profil = 'etudiant' if is_etudiant else ('ouvrier' if is_ouvrier else 'employe')
    profil = construire_profil(cp_key, statut_profil, type_contrat=type_contrat,
                                heures_semaine=heures_semaine, jours_semaine=jours_semaine,
                                reference_date=periode_fin if periode_fin else date.today(),
                                categorie_employeur=categorie_employeur or '000')
    onss_info = profil.onss_officiel   # trimestre utilise + report eventuel

    onss_pers_taux = profil.onss_personnel_taux
    onss_pat_taux_base = profil.onss_patronal_taux_base
    heures_sem_reel = round(heures_jour * jours_semaine, 2)
    ratio_tp = min(1.0, heures_sem_reel / heures_semaine) if heures_semaine > 0 else 1.0

    # ── LIGNES SOUMISES ONSS ──────────────────────────────────────────
    lignes_salaire = []
    # Employé CDI/CDD temps plein → salaire mensuel fixe
    # Ouvrier ou étudiant → salaire calculé sur heures prestées
    is_employe_fixe = profil.salaire_est_mensuel_fixe
    if is_employe_fixe:
        # Salaire mensuel fixe = salaire_horaire × heures_semaine × 52 / 12
        sal_mensuel_brut = salaire_mensuel_fixe if salaire_mensuel_fixe and salaire_mensuel_fixe > 0 else round(salaire_horaire * heures_semaine * 52 / 12, 2)
        # Déduction congé sans solde uniquement
        deduction_cnp = 0.0
        if jours_chomage > 0:
            # Calcul jours ouvrables du mois (base de division)
            from datetime import date, timedelta
            if periode_debut and periode_fin:
                jours_ouv_mois = sum(1 for n in range((periode_fin - periode_debut).days + 1)
                    if (periode_debut + timedelta(n)).weekday() < 5)
            else:
                jours_ouv_mois = round(jours_semaine * 52 / 12)
            deduction_cnp = round(sal_mensuel_brut / jours_ouv_mois * jours_chomage, 2)
        sal_mensuel = round(sal_mensuel_brut - deduction_cnp, 2)
        # Base affichee = salaire MENSUEL (pas le taux horaire) pour un employe au mois
        lignes_salaire.append({'libelle': 'Salaire mensuel', 'base': sal_mensuel_brut, 'base_decimales': 2,
            'jours': jours_prestes, 'heures': heures_prestees,
            'montant': sal_mensuel, 'soumis_onss': True})
        if deduction_cnp > 0:
            lignes_salaire.append({'libelle': f'Congé sans solde ({jours_chomage}j)',
                'base': 0, 'jours': jours_chomage, 'heures': 0,
                'montant': -deduction_cnp, 'soumis_onss': True})
    elif jours_prestes > 0:
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
    # Ouvriers: base a 108% (Instructions ONSS 2026/3 p.176) -- corrige le 01/10/2026
    onss_trav_brut = profil.onss_personnel(brut_onss)

    # Bonus emploi: salaire de reference S et prorata sur les PRESTATIONS REELLES
    # du mois (Instructions ONSS 2026/3 p.449-453) -- corrige le 01/10/2026:
    # l'ancien calcul proratisait par la fraction contractuelle, meme pour un
    # mois incomplet (entree en cours de mois, absences non payees).
    bonus_a, bonus_b = 0.0, 0.0
    alerte_plafond_bonus = None
    if profil.bonus_emploi_applicable:
        ref_date_params = periode_fin if periode_fin else date.today()
        # Jours/heures declares (prestations, feries, conges payes par l'employeur ;
        # les vacances legales des ouvriers sont payees par la caisse: exclues)
        jours_conge_payes = 0 if is_ouvrier else (jours_conge or 0)
        jours_bonus = (jours_prestes or 0) + (jours_feries_payes or 0) + jours_conge_payes
        if is_employe_fixe and periode_debut and periode_fin:
            from datetime import timedelta as _td_b
            jours_bonus = max(0, sum(1 for n in range((periode_fin - periode_debut).days + 1)
                                     if (periode_debut + _td_b(n)).weekday() < 5) - (jours_chomage or 0))
        if is_employe_fixe:
            heures_bonus = jours_bonus * float(heures_jour or 0)
        else:
            heures_bonus = float(heures_prestees or 0) + float(heures_feries or 0) + \
                           jours_conge_payes * float(heures_jour or 0)
        sal_ref_bonus, fraction_bonus = profil.reference_bonus_emploi(
            brut_onss, ref_date_params, jours=jours_bonus, heures=heures_bonus, temps_partiel=ratio_tp < 1.0)
        # Ecretement integre dans bonus_emploi(): volet B en premier, jusqu'a 0,
        # PUIS volet A si toujours insuffisant (Instructions p.452, verifie
        # au centime contre une simulation Group S reelle CP336 employe).
        if sal_ref_bonus is not None:
            bonus_a, bonus_b = profil.bonus_emploi(sal_ref_bonus, fraction_bonus, onss_du=onss_trav_brut, reference_date=ref_date_params)
        # Plafond annuel par travailleur (Instructions ONSS 2026/3 p.453). Le cumul
        # deja accorde dans l'annee vient des fiches enregistrees (fiches_paie).
        # Imputation du depassement: volet B puis volet A, comme l'ecretement.
        plafond_bonus = get_bonus_emploi_plafond_annuel(ref_date_params)
        cumul_bonus = round(float(bonus_emploi_cumul_annee or 0), 2)
        if plafond_bonus and (bonus_a + bonus_b) > 0:
            reste_plafond = round(max(0.0, plafond_bonus['plafond_annuel'] - cumul_bonus), 2)
            exces_plafond = round(bonus_a + bonus_b - reste_plafond, 2)
            if exces_plafond > 0:
                retrait_b = min(bonus_b, exces_plafond)
                bonus_b = round(bonus_b - retrait_b, 2)
                bonus_a = round(max(0.0, bonus_a - (exces_plafond - retrait_b)), 2)
                alerte_plafond_bonus = (
                    f"Bonus à l'emploi limité par le plafond annuel de {plafond_bonus['plafond_annuel']:.2f} € "
                    f"(déjà accordé cette année : {cumul_bonus:.2f} €).")
        elif cumul_bonus > 0 and not plafond_bonus:
            alerte_plafond_bonus = ("Plafond annuel du bonus à l'emploi non chargé pour cette période "
                                    "(connu à partir du 01/07/2026) : non contrôlé.")

    onss_trav_net = round(max(0, onss_trav_brut - bonus_a - bonus_b), 2)
    brut_imposable = round(brut_onss - onss_trav_net, 2)
    # Plafond fiscal 500EUR/an sur indemnite km voiture (precompte uniquement,
    # PAS l'ONSS) -- source Securex + fin.belgium.be, annee de revenus 2026.
    ref_date_fiscale = periode_fin if periode_fin else date.today()
    montant_km_imposable_precompte = 0.0
    if km_domicile > 0 and moyen_transport == 'voiture' and not vehicule_societe and not cp.get('indem_deplacement_jour'):
        montant_km_estime = round(taux_km * km_domicile * 2 * jours_prestes, 2)
        plafond_annuel_km = (get_precompte_params(ref_date_fiscale)['exoneration_km_voiture_annuelle']
                             if profil.precompte_applicable else 500.0)
        plafond_mensuel_km = round(plafond_annuel_km / 12, 2)
        if montant_km_estime > plafond_mensuel_km:
            montant_km_imposable_precompte = round(montant_km_estime - plafond_mensuel_km, 2)
    brut_imposable_precompte = round(brut_imposable + montant_km_imposable_precompte, 2)
    precompte_brut = profil.precompte_brut(brut_imposable_precompte, etat_civil, nb_enfants, partenaire_revenus_pro,
                                           reference_date=ref_date_fiscale, charges=charges_famille)
    # Réduction précompte sur bonus emploi (AR 27/08/1993 art. 38§3quater, taux 33.14% confirmé Liantis)
    red_precompte_bonus = profil.reduction_precompte_bonus(bonus_a, bonus_b, brut_imposable,
                                                            reference_date=ref_date_fiscale)
    red_precompte_bonus = min(red_precompte_bonus, precompte_brut)
    precompte = round(precompte_brut - red_precompte_bonus, 2)
    # Cotisation speciale SS: bareme officiel ONSS (depuis 01/04/2022), base =
    # remuneration BRUTE declaree (108% ouvriers, primes incluses, hors double pecule)
    base_css = round((brut_onss + (prime_exceptionnelle or 0)) * profil.coeff_base_onss_patronal, 2)
    css = profil.css_mensuelle(base_css, etat_civil, partenaire_revenus_pro, reference_date=ref_date_fiscale)

    # ── INDEMNITÉS EXONÉRÉES ──────────────────────────────────────────
    lignes_indemn = []

    # RGPT
    montant_rgpt = 0.0
    rgpt_h = cp.get('rgpt_heure', 0.0)
    rgpt_j = cp.get('rgpt_jour', 0.0)
    if rgpt_j > 0 and rgpt_actif and jours_prestes > 0:
        montant_rgpt = round(rgpt_j * jours_prestes, 2)
        lignes_indemn.append({'libelle': f'Indemnité RGPT ({jours_prestes} j)',
            'detail': f'{rgpt_j:.4f} €/jour', 'jours': jours_prestes, 'montant': montant_rgpt})
    elif rgpt_h > 0 and rgpt_actif and heures_prestees > 0:
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
        montant_km = round(taux_km * km_domicile * 2 * jours_prestes, 2)
        lignes_indemn.append({'libelle': f'Indemnité km ({km_domicile} km)',
            'detail': f'{taux_km:.4f} €/km', 'jours': jours_prestes, 'montant': montant_km})

    # Chèques-repas — déduction part collectivité uniquement
    montant_cr_ded = 0.0
    cr_coll = cp.get('cr_part_coll_jour', 0.0)
    cr_empl_j = cp.get('cr_part_empl_jour', 0.0)
    cr_empl_total = 0.0
    if cheques_repas_calc is not None:
        # Nombre et montants calcules par le SUIVI DES CHEQUES du dossier
        # (regles sectorielles: jours prestes, ou heures/7,4 en CP 121)
        nb_cr = int(cheques_repas_calc.get('nombre') or 0)
        if nb_cr > 0:
            pt_cr = float(cheques_repas_calc.get('part_travailleur') or 0)
            montant_cr_ded = -round(nb_cr * pt_cr, 2)
            cr_empl_total = round(nb_cr * float(cheques_repas_calc.get('part_patronale') or 0), 2)
            lignes_indemn.append({'libelle': f'Chèques-repas part travailleur ({nb_cr} x {pt_cr:.2f} €)',
                'detail': f"{nb_cr} chèques de {float(cheques_repas_calc.get('valeur') or 0):.2f} € — suivi des chèques",
                'jours': 0, 'montant': montant_cr_ded})
    elif cheques_repas and cr_coll > 0 and jours_prestes > 0:
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
    # CSS
    if css > 0:
        lignes_indemn.append({'libelle': 'Cotisation spéciale SS', 'montant': -css})

    # ── NET ───────────────────────────────────────────────────────────
    # ── ALLOCATIONS EXCEPTIONNELLES (prime, 13e mois, double pecule) ──────
    # Hors bonus emploi et hors precompte mensuel: precompte special sur
    # "allocations exceptionnelles" (bareme en escalier, parametres_dates 2026).
    # Remuneration annuelle brute NORMALE = salaire mensuel x 12 (allocation exclue).
    lignes_exc = []
    net_exceptionnel = 0.0
    remu_annuelle_normale = round((salaire_mensuel_fixe or brut_onss) * 12, 2)
    prime_onss = prime_imposable = prime_precompte = 0.0
    if prime_exceptionnelle and prime_exceptionnelle > 0 and not is_etudiant:
        prime_onss = _r2_prime = profil.onss_personnel(prime_exceptionnelle)
        prime_imposable = round(prime_exceptionnelle - prime_onss, 2)
        prime_precompte, taux_pp_prime = profil.precompte_exceptionnel(
            prime_imposable, remu_annuelle_normale, 'autres', reference_date=ref_date_fiscale)
        net_prime = round(prime_imposable - prime_precompte, 2)
        net_exceptionnel += net_prime
        lignes_exc += [
            {'libelle': f'{libelle_prime} (brut)', 'detail': 'Allocation exceptionnelle', 'jours': 0, 'montant': round(prime_exceptionnelle, 2)},
            {'libelle': f'ONSS sur {libelle_prime.lower()}', 'detail': f'{onss_pers_taux*100:.2f} %', 'jours': 0, 'montant': -prime_onss},
            {'libelle': f'Précompte sur {libelle_prime.lower()}', 'detail': f'{taux_pp_prime*100:.2f} % (barème allocations exceptionnelles)', 'jours': 0, 'montant': -prime_precompte},
        ]
    pecule_retenue = pecule_imposable = pecule_precompte = 0.0
    if double_pecule and double_pecule > 0 and not is_etudiant:
        # Retenue speciale 13,07% sur 85/92 du double pecule (Instructions ONSS, Securex)
        pecule_base_soumise = round(double_pecule * 85 / 92, 2)
        pecule_retenue = round(pecule_base_soumise * 0.1307, 2)
        pecule_imposable = round(double_pecule - pecule_retenue, 2)
        if precompte_pecule_manuel is not None and precompte_pecule_manuel > 0:
            pecule_precompte, taux_pp_pec = round(precompte_pecule_manuel, 2), None
        else:
            pecule_precompte, taux_pp_pec = profil.precompte_exceptionnel(
                pecule_imposable, remu_annuelle_normale, 'double_pecule', reference_date=ref_date_fiscale)
        net_pecule = round(pecule_imposable - pecule_precompte, 2)
        net_exceptionnel += net_pecule
        lignes_exc += [
            {'libelle': 'Double pécule de vacances (brut)', 'detail': 'Allocation exceptionnelle', 'jours': 0, 'montant': round(double_pecule, 2)},
            {'libelle': 'Retenue double pécule', 'detail': f'13,07 % sur 85/92 ({pecule_base_soumise:.2f})', 'jours': 0, 'montant': -pecule_retenue},
            {'libelle': 'Précompte double pécule', 'detail': ('saisi manuellement' if taux_pp_pec is None
                        else f'{taux_pp_pec*100:.2f} % (barème allocations exceptionnelles)'), 'jours': 0, 'montant': -pecule_precompte},
        ]
    lignes_indemn.extend(lignes_exc)
    net_exceptionnel = round(net_exceptionnel, 2)

    total_indemn = montant_rgpt + montant_arab + montant_vet + montant_dep + montant_km + montant_cr_ded + montant_frais_nets - css + net_exceptionnel
    salaire_net = round(brut_imposable - precompte + total_indemn, 2)

    # ── CHARGES PATRONALES ────────────────────────────────────────────
    # Coefficient 108% pour ouvriers (pécule vacances ONVA — source ONSS officiel)
    coeff_ouvrier = profil.coeff_base_onss_patronal
    base_onss_pat = round(brut_onss * coeff_ouvrier, 2)
    ref_date_struct = periode_fin if periode_fin else date.today()
    _r2 = profil._r2   # arrondi officiel ONSS (0,005 vers le haut)
    # 1) Part REDUCTIBLE: cotisation de base + moderation (seule base des reductions)
    onss_pat_reductible = _r2(base_onss_pat * profil.onss_patronal_reductible_taux)
    # 2) Cotisation vacances ouvriers (code 253): hors plafond des reductions
    onss_vacances_253 = _r2(base_onss_pat * profil.onss_vacances_trimestrielle_taux)
    # 3) Cotisations complementaires (FFE, 1,60%, fonds sectoriels): non reductibles
    from onss_taux import cotisations_complementaires
    cotis_compl, avertissements_onss = cotisations_complementaires(
        profil.statut, ref_date_struct, categorie=categorie_employeur or '000',
        code_ffe=code_ffe, code_importance=code_importance)
    for cc in cotis_compl:
        cc['base'] = base_onss_pat
        cc['montant'] = _r2(base_onss_pat * cc['taux'])
    total_compl = round(sum(cc['montant'] for cc in cotis_compl), 2)
    onss_pat_brut = round(onss_pat_reductible + onss_vacances_253 + total_compl, 2)

    # Jours / heures payes du mois (codes prestation ONSS 1, 3, 4, 5...):
    # prestations + jours feries payes + conges payes par l'employeur
    # Ouvriers: les vacances legales sont payees par la caisse de vacances (code
    # prestation 2), pas par l'employeur -> hors J/H (corrige le 01/10/2026).
    jours_conge_employeur = 0 if is_ouvrier else (jours_conge or 0)
    jours_payes_onss = (jours_prestes or 0) + (jours_feries_payes or 0) + jours_conge_employeur
    if profil.salaire_est_mensuel_fixe and periode_debut and periode_fin:
        # Employe au mois: le salaire couvre TOUS les jours ouvrables du mois
        # (le calendrier peut etre incomplet en cours de mois). Seules les
        # absences non payees (jours_chomage) sont retirees.
        from datetime import timedelta as _td
        jours_ouvr_mois = sum(1 for n in range((periode_fin - periode_debut).days + 1)
                              if (periode_debut + _td(n)).weekday() < 5)
        jours_payes_onss = max(0, jours_ouvr_mois - (jours_chomage or 0))
    heures_payees_onss = float(heures_prestees or 0) + float(heures_feries or 0) + \
                         float(jours_conge_employeur) * float(heures_jour or 0)
    red_struct = 0.0 if is_etudiant else profil.reduction_structurelle(
        onss_pat_reductible, reference_date=ref_date_struct, remuneration_mois=brut_onss,
        jours_payes=jours_payes_onss, heures_payees=heures_payees_onss)

    # Premier engagement (plafonne a la part reductible restante)
    red_pe = 0.0
    if premier_engagement and not is_etudiant:
        reste_apres_struct = round(max(0, onss_pat_reductible - red_struct), 2)
        red_pe = profil.reduction_premier_engagement(
            reste_apres_struct, ratio_tp, reference_date=ref_date_struct,
            jours_payes=jours_payes_onss, heures_payees=heures_payees_onss)

    onss_pat_net = round(max(0, onss_pat_reductible - red_struct - red_pe)
                         + onss_vacances_253 + total_compl, 2)
    # Cotisation ANNUELLE vacances ouvriers (10.27% des remunerations a 108%),
    # facturee par l'ONSS l'annee suivante -- provisionnee ici pour un cout reel
    provision_vacances_annuelles = round(brut_onss * profil.coeff_base_onss_patronal
                                         * profil.vacances_annuelles_taux, 2)
    # Cotisations patronales sur la prime (le double pecule employe n'en supporte pas).
    # Prudence: aucune reduction n'est imputee sur la prime (calcul conservateur).
    onss_pat_prime = 0.0
    if prime_exceptionnelle and prime_exceptionnelle > 0 and not is_etudiant:
        onss_pat_prime = _r2(prime_exceptionnelle * profil.coeff_base_onss_patronal *
                             (profil.onss_patronal_taux_base + sum(cc['taux'] for cc in cotis_compl)))
    onss_pat_net = round(onss_pat_net + onss_pat_prime, 2)
    # Frais propres a l'employeur inclus (corrige le 01/10/2026: ils etaient payes
    # au travailleur dans le net mais absents du cout). Controle permanent dans
    # test_moteur.py: cout >= net + ONSS travailleur + precompte + CSS.
    cout_empl = round(brut_onss + onss_pat_net + montant_rgpt + montant_arab + montant_vet + montant_dep + montant_km + cr_empl_total
                      + montant_frais_nets + provision_vacances_annuelles + (prime_exceptionnelle or 0) + (double_pecule or 0), 2)

    # ── DETAIL COMPLET DU CALCUL (page "Calculer la paie") ─────────────
    onss_info = profil.onss_officiel
    pp_detail = profil.precompte_detail(brut_imposable_precompte, etat_civil, nb_enfants,
                                        partenaire_revenus_pro, reference_date=ref_date_fiscale,
                                        charges=charges_famille)
    def L(libelle, montant, base=None, taux=None, source=None, info=False, total=False):
        return {'libelle': libelle, 'montant': (round(montant, 2) + 0.0) if montant is not None else None,
                'base': base, 'taux': taux, 'source': source, 'info': info, 'total': total}
    detail_calcul = [
        {'titre': 'Rémunération brute', 'lignes':
            [L(l['libelle'], l['montant'], base=l.get('base'), source=f"{l.get('jours',0)} j / {l.get('heures',0)} h")
             for l in lignes_salaire] +
            [L('Brut soumis à l\'ONSS', brut_onss, total=True)]},
        {'titre': 'ONSS travailleur', 'lignes': [
            L('Cotisation personnelle' + (' (base 108 %)' if profil.coeff_base_onss_patronal != 1.0 else ''),
              -onss_trav_brut, base=profil.base_onss_patronale(brut_onss), taux=onss_pers_taux,
              source=f"TechLib ONSS {onss_info['trimestre_utilise']}, code {onss_info['code_travailleur']}"),
            L('Bonus à l\'emploi volet A', bonus_a, source='Tables datées bonus emploi (parametres_dates)'),
            L('Bonus à l\'emploi volet B', bonus_b, source='Écrêtement : volet B en premier'),
            L('ONSS travailleur net', -onss_trav_net, total=True)]},
        {'titre': 'Précompte professionnel', 'lignes':
            [L(lib, mt, info=True) for lib, mt in pp_detail['etapes']] + [
            L('Base imposable mensuelle', brut_imposable_precompte,
              source=('dont surplus km imposable ' + str(montant_km_imposable_precompte)) if montant_km_imposable_precompte else None),
            L('Précompte avant réduction', -precompte_brut,
              source=f"Formule-clé SPF {pp_detail.get('annee_fiscale', '')}" if pp_detail['applicable'] else 'Non applicable'),
            L('Réduction liée au bonus à l\'emploi', red_precompte_bonus, source='33,14 % volet A / 52,54 % volet B'),
            L('Précompte retenu', -precompte, total=True)]},
        {'titre': 'Indemnités et retenues nettes', 'lignes':
            [L(l['libelle'], l['montant'], source=l.get('detail')) for l in lignes_indemn]},
        {'titre': 'Allocations exceptionnelles', 'lignes':
            ([L('Rémunération annuelle brute normale (base du taux)', remu_annuelle_normale, info=True)] if lignes_exc else []) +
            [L(l['libelle'], l['montant'], source=l['detail']) for l in lignes_exc] +
            ([L('Net des allocations exceptionnelles', net_exceptionnel, total=True)] if lignes_exc else [])},
        {'titre': 'Net à payer', 'lignes': [L('Salaire net', salaire_net, total=True)]},
        {'titre': 'Cotisations patronales', 'lignes': [
            L('Base patronale' + (' (108 %)' if coeff_ouvrier != 1.0 else ''), base_onss_pat, info=True),
            L('Cotisation de solidarité étudiant' if is_etudiant else 'Cotisation de base + modération (réductible)',
              onss_pat_reductible, base=base_onss_pat,
              taux=profil.onss_patronal_reductible_taux,
              source=f"TechLib {onss_info['trimestre_utilise']}, catégorie {onss_info['categorie']}")] +
            ([L('Vacances annuelles ouvriers (code 253, non réductible)', onss_vacances_253, base=base_onss_pat,
                taux=profil.onss_vacances_trimestrielle_taux, source='Instructions ONSS 2026/3')] if onss_vacances_253 else []) +
            [L(f"{cc['code']} – {cc['libelle'][:80]}", cc['montant'], base=cc['base'], taux=cc['taux'],
               source=cc['source'] + (' — à vérifier' if cc['a_verifier'] else '')) for cc in cotis_compl] +
            ([L('Réduction structurelle', -red_struct, source='Ps = R × µ × ß (Instructions ONSS 2026/3 p.382)')] if red_struct else []) +
            ([L('Réduction premier engagement', -red_pe, source='Pg = G × µ × ß, G = forfait daté')] if red_pe else []) +
            [L('ONSS patronal net', onss_pat_net, total=True)]},
        {'titre': 'Coût employeur', 'lignes': [
            L('Provision vacances annuelles ouvriers (10,27 %, facturée l\'année suivante)',
              provision_vacances_annuelles, info=True) if provision_vacances_annuelles else None,
            L('Coût employeur total', cout_empl, total=True)]},
    ]
    for bloc_d in detail_calcul:
        bloc_d['lignes'] = [x for x in bloc_d['lignes'] if x]
    alertes_calcul = list(avertissements_onss)
    if alerte_plafond_bonus:
        alertes_calcul.append(alerte_plafond_bonus)
    if onss_info['parametres_reportes']:
        alertes_calcul.insert(0, f"Taux ONSS du {onss_info['trimestre_demande']} pas encore publiés : "
                                 f"calcul avec le {onss_info['trimestre_utilise']} (à régulariser via la DmfA).")

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
        'type_contrat': type_contrat, 'is_etudiant': is_etudiant, 'is_ouvrier': is_ouvrier,
        'libelle_salaire_base': profil.libelle_salaire_base,
        'onss_trimestre_utilise': onss_info['trimestre_utilise'],
        'detail_calcul': detail_calcul,
        'alertes_calcul': alertes_calcul,
        'onss_patronal_reductible': onss_pat_reductible,
        'onss_vacances_trimestrielle': onss_vacances_253,
        'cotisations_complementaires': cotis_compl,
        'prime_exceptionnelle': prime_exceptionnelle or 0.0, 'prime_onss': prime_onss, 'prime_precompte': prime_precompte,
        'double_pecule': double_pecule or 0.0, 'pecule_retenue': pecule_retenue, 'pecule_precompte': pecule_precompte,
        'onss_patronal_prime': onss_pat_prime, 'net_exceptionnel': net_exceptionnel,
        'onss_categorie_employeur': onss_info['categorie'],
        'onss_parametres_reportes': onss_info['parametres_reportes'],
        'onss_date_fichier': onss_info['date_creation_onss'],
        'onss_taux_patronal_applique': profil.onss_patronal_taux_base,
        'provision_vacances_annuelles': provision_vacances_annuelles,
        'salaire_mensuel_fixe': salaire_mensuel_fixe,
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
        'premier_engagement': premier_engagement,
        # Detail conserve dans fiches_paie pour les documents de charges
        # (compte individuel, attestation salariale, ventilation)
        'jours_prestes': jours_prestes, 'heures_prestees': heures_prestees,
        'jours_feries_payes': jours_feries_payes, 'heures_feries': heures_feries,
        'jours_conge': jours_conge, 'jours_maladie': jours_maladie, 'jours_chomage': jours_chomage,
        'brut_majore': base_onss_pat,
        'css': css,
        'libelle_prime': libelle_prime,
        'cr_part_travailleur': round(-montant_cr_ded, 2),
        'indemnites_detail': [{'libelle': lib, 'montant': mt} for lib, mt in (
            ('Indemnité RGPT', montant_rgpt), ('Indemnité ARAB', montant_arab),
            ('Vêtements de travail', montant_vet),
            ('Déplacement domicile-travail', round(montant_dep + montant_km, 2)),
            ("Frais propres à l'employeur", montant_frais_nets)) if mt],
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
