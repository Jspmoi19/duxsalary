# Patch #7 -- reduction structurelle degressive (au lieu du montant fixe 521.47)
with open('/var/www/duxsalary/moteur_paie.py', 'r') as f:
    content = f.read()

old = "    red_struct = 0.0 if is_etudiant else calcul_reduction_structurelle(base_onss_pat, onss_pat_taux_base)"
if old not in content:
    raise SystemExit("ECHEC: ligne red_struct non trouvee -- rien modifie")

new = """    red_struct = 0.0 if is_etudiant else profil.reduction_structurelle(onss_pat_brut, base_salariale_mensuelle=base_onss_pat)"""
content = content.replace(old, new)

with open('/var/www/duxsalary/moteur_paie.py', 'w') as f:
    f.write(content)
print("OK -- reduction structurelle degressive appliquee")
