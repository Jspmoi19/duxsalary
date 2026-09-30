# Patch -- reduction structurelle et premier engagement selon les formules
# OFFICIELLES (Instructions ONSS 2026/3): Ps = R x mu x beta_s, Pg = G x mu x beta_g,
# sur le salaire a 100% et les jours/heures reellement payes du mois.
# ATOMIQUE: rien n'est ecrit si une etape echoue.
import shutil, ast
CHEMIN = '/var/www/duxsalary/moteur_paie.py'
content = open(CHEMIN).read()
etapes = [
    ("reduction structurelle",
     "    red_struct = 0.0 if is_etudiant else profil.reduction_structurelle(onss_pat_brut, base_salariale_mensuelle=base_onss_pat, reference_date=ref_date_struct)",
     """    # Jours / heures payes du mois (codes prestation ONSS 1, 3, 4, 5...):
    # prestations + jours feries payes + conges payes par l'employeur
    jours_payes_onss = (jours_prestes or 0) + (jours_feries_payes or 0) + (jours_conge or 0)
    heures_payees_onss = float(heures_prestees or 0) + float(heures_feries or 0) + \\
                         float(jours_conge or 0) * float(heures_jour or 0)
    red_struct = 0.0 if is_etudiant else profil.reduction_structurelle(
        onss_pat_brut, reference_date=ref_date_struct, remuneration_mois=brut_onss,
        jours_payes=jours_payes_onss, heures_payees=heures_payees_onss)"""),
    ("premier engagement",
     "        red_pe = round(min(round(2000/3, 2) * ratio_tp, reste_apres_struct), 2)",
     """        red_pe = profil.reduction_premier_engagement(
            reste_apres_struct, ratio_tp, reference_date=ref_date_struct,
            jours_payes=jours_payes_onss, heures_payees=heures_payees_onss)"""),
]
for label, old, new in etapes:
    n = content.count(old)
    if n != 1:
        raise SystemExit(f"ECHEC ({label}): trouve {n} fois, attendu 1 -- RIEN n'a ete modifie.")
    content = content.replace(old, new)
ast.parse(content)
shutil.copy(CHEMIN, CHEMIN + '.avant_reductions_officielles')
open(CHEMIN, 'w').write(content)
print("OK -- reductions calculees selon les formules officielles ONSS 2026/3")
