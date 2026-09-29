# Patch #8 -- brancher les parametres versionnes par date (bonus emploi +
# reduction structurelle) sur la vraie periode de la fiche, pas la date du jour
with open('/var/www/duxsalary/moteur_paie.py', 'r') as f:
    content = f.read()

old1 = "        bonus_a, bonus_b = profil.bonus_emploi(sal_propre_etp, ratio_tp, onss_du=onss_trav_brut)"
if old1 not in content:
    raise SystemExit("ECHEC etape 1: ligne bonus_emploi non trouvee -- rien modifie")
new1 = "        ref_date_params = periode_fin if periode_fin else date.today()\n        bonus_a, bonus_b = profil.bonus_emploi(sal_propre_etp, ratio_tp, onss_du=onss_trav_brut, reference_date=ref_date_params)"
content = content.replace(old1, new1)

old2 = "    red_struct = 0.0 if is_etudiant else profil.reduction_structurelle(onss_pat_brut, base_salariale_mensuelle=base_onss_pat)"
if old2 not in content:
    raise SystemExit("ECHEC etape 2: ligne reduction_structurelle non trouvee -- rien modifie")
new2 = "    ref_date_struct = periode_fin if periode_fin else date.today()\n    red_struct = 0.0 if is_etudiant else profil.reduction_structurelle(onss_pat_brut, base_salariale_mensuelle=base_onss_pat, reference_date=ref_date_struct)"
content = content.replace(old2, new2)

with open('/var/www/duxsalary/moteur_paie.py', 'w') as f:
    f.write(content)
print("OK -- parametres dates branches sur periode_fin de la fiche")
