# Patch à appliquer sur /var/www/duxsalary/moteur_paie.py
# Objectif: remplacer les décisions dupliquées par des appels à profil_travailleur,
# sans toucher à la réduction structurelle (déjà correcte et plus riche).

import re

with open('/var/www/duxsalary/moteur_paie.py', 'r') as f:
    content = f.read()

original = content

# 1. Import du nouveau module en haut du fichier
old_import = "from datetime import date\nimport math"
new_import = "from datetime import date\nimport math\nimport sys as _sys; _sys.path.insert(0, '/var/www/duxsalary')\nfrom profil_travailleur import construire_profil"
if old_import not in content:
    raise SystemExit("ÉCHEC: import non trouvé — abandon sans modification")
content = content.replace(old_import, new_import)

# 2. Construire le profil juste après avoir chargé cp / is_ouvrier
old_block = """    cp = CP_INDEMNITES.get(cp_key, {})
    # Override avec barèmes BDD si disponibles
    cp_db = get_cp_from_db(cp_key)
    if cp_db:
        cp = dict(cp)
        cp['sal_bareme_mensuel_etp'] = cp_db['min_mensuel']
    is_ouvrier = cp.get('type_travailleur', 'ouvrier') == 'ouvrier'
    onss_pers_taux = ONSS_ETUDIANT_PERSONNEL if is_etudiant else ONSS_PERSONNEL
    onss_pat_taux = ONSS_ETUDIANT_PATRONAL if is_etudiant else cp.get('onss_patronal', 0.27)
    onss_pat_taux_base = onss_pat_taux
    heures_sem_reel = round(heures_jour * jours_semaine, 2)
    ratio_tp = min(1.0, heures_sem_reel / heures_semaine) if heures_semaine > 0 else 1.0"""

new_block = """    cp = CP_INDEMNITES.get(cp_key, {})
    # Override avec barèmes BDD si disponibles
    cp_db = get_cp_from_db(cp_key)
    if cp_db:
        cp = dict(cp)
        cp['sal_bareme_mensuel_etp'] = cp_db['min_mensuel']
    is_ouvrier = cp.get('type_travailleur', 'ouvrier') == 'ouvrier'

    # ── PROFIL TRAVAILLEUR — source unique pour les décisions ONSS/précompte/bonus ──
    statut_profil = 'etudiant' if is_etudiant else ('ouvrier' if is_ouvrier else 'employe')
    profil = construire_profil(cp_key, statut_profil, type_contrat=type_contrat,
                                heures_semaine=heures_semaine, jours_semaine=jours_semaine)

    onss_pers_taux = profil.onss_personnel_taux
    onss_pat_taux_base = profil.onss_patronal_taux_base
    heures_sem_reel = round(heures_jour * jours_semaine, 2)
    ratio_tp = min(1.0, heures_sem_reel / heures_semaine) if heures_semaine > 0 else 1.0"""

if old_block not in content:
    raise SystemExit("ÉCHEC: bloc profil non trouvé — abandon sans modification")
content = content.replace(old_block, new_block)

# 3. Bonus emploi — remplacer calcul_bonus_emploi() par profil.bonus_emploi()
old_bonus = """    bonus_a, bonus_b = 0.0, 0.0
    if not is_etudiant:
        sal_bar_etp = cp.get('sal_bareme_mensuel_etp', salaire_horaire * heures_semaine * 52/12)
        bonus_a, bonus_b = calcul_bonus_emploi(sal_bar_etp, ratio_tp, is_ouvrier)"""
new_bonus = """    bonus_a, bonus_b = 0.0, 0.0
    if profil.bonus_emploi_applicable:
        # Salaire PROPRE du travailleur en ETP (pas le minimum sectoriel — corrigé 29/09/2026)
        sal_propre_etp = salaire_horaire * heures_semaine * 52 / 12
        bonus_a, bonus_b = profil.bonus_emploi(sal_propre_etp, ratio_tp)"""
if old_bonus not in content:
    raise SystemExit("ÉCHEC: bloc bonus non trouvé — abandon sans modification")
content = content.replace(old_bonus, new_bonus)

# 4. Précompte + réduction précompte bonus + CSS — via profil
old_precompte = """    precompte_brut = 0.0 if is_etudiant else calcul_precompte(brut_imposable, etat_civil, nb_enfants, partenaire_revenus_pro, partenaire_pensions)
    # Réduction précompte sur bonus emploi (AR 27/08/1993 art. 38§3quater)
    # Taux 33.14% confirmé sur fiche Liantis
    red_precompte_bonus = 0.0
    if not is_etudiant and (bonus_a + bonus_b) > 0 and brut_imposable <= 3500:
        red_precompte_bonus = round((bonus_a + bonus_b) * 0.3314, 2)
        red_precompte_bonus = min(red_precompte_bonus, precompte_brut)
    precompte = round(precompte_brut - red_precompte_bonus, 2)
    css = 0.0 if is_etudiant else calcul_css(brut_imposable)"""
new_precompte = """    precompte_brut = profil.precompte_brut(brut_imposable, etat_civil, nb_enfants, partenaire_revenus_pro)
    # Réduction précompte sur bonus emploi (AR 27/08/1993 art. 38§3quater, taux 33.14% confirmé Liantis)
    red_precompte_bonus = profil.reduction_precompte_bonus(bonus_a, bonus_b, brut_imposable)
    red_precompte_bonus = min(red_precompte_bonus, precompte_brut)
    precompte = round(precompte_brut - red_precompte_bonus, 2)
    css = profil.css(brut_imposable)"""
if old_precompte not in content:
    raise SystemExit("ÉCHEC: bloc précompte non trouvé — abandon sans modification")
content = content.replace(old_precompte, new_precompte)

# 5. Coefficient ouvrier — via profil (même valeur, source unique)
old_coeff = "    coeff_ouvrier = 1.08 if (is_ouvrier and not is_etudiant) else 1.0"
new_coeff = "    coeff_ouvrier = profil.coeff_base_onss_patronal"
if old_coeff not in content:
    raise SystemExit("ÉCHEC: bloc coeff non trouvé — abandon sans modification")
content = content.replace(old_coeff, new_coeff)

# 6. is_employe_fixe — via profil (gate identique, source unique)
old_fixe = "    is_employe_fixe = (not is_ouvrier and not is_etudiant and type_contrat in ('CDI', 'CDD'))"
new_fixe = "    is_employe_fixe = profil.salaire_est_mensuel_fixe"
if old_fixe not in content:
    raise SystemExit("ÉCHEC: bloc is_employe_fixe non trouvé — abandon sans modification")
content = content.replace(old_fixe, new_fixe)

# 7. Ajouter le libellé correct dans le dict retourné (pour que generer_fiche_pdf.py
#    n'ait plus besoin de redeviner is_ouvrier/is_etudiant lui-même)
old_return = "        'type_contrat': type_contrat, 'is_etudiant': is_etudiant, 'is_ouvrier': is_ouvrier,"
new_return = "        'type_contrat': type_contrat, 'is_etudiant': is_etudiant, 'is_ouvrier': is_ouvrier,\n        'libelle_salaire_base': profil.libelle_salaire_base,"
if old_return not in content:
    raise SystemExit("ÉCHEC: bloc return non trouvé — abandon sans modification")
content = content.replace(old_return, new_return)

with open('/var/www/duxsalary/moteur_paie.py', 'w') as f:
    f.write(content)

print(f"OK — patch appliqué, {len(content) - len(original)} caractères ajoutés (net)")
