# Patch -- precompte versionne par annee fiscale: moteur_paie.py transmet la
# periode de la fiche (et non la date du jour) aux calculs fiscaux.
# ATOMIQUE: toutes les modifications sont verifiees AVANT ecriture. Si une
# seule ne correspond pas, rien n'est modifie.
import shutil

CHEMIN = '/var/www/duxsalary/moteur_paie.py'
with open(CHEMIN, 'r') as f:
    content = f.read()

remplacements = [
    # 1) import
    ("from profil_travailleur import construire_profil",
     "from profil_travailleur import construire_profil\n"
     "from parametres_dates import get_precompte_params"),
    # 2) date fiscale de reference, definie avant le bloc km/precompte
    ("    montant_km_imposable_precompte = 0.0",
     "    ref_date_fiscale = periode_fin if periode_fin else date.today()\n"
     "    montant_km_imposable_precompte = 0.0"),
    # 3) plafond km lu depuis l'annee fiscale (500EUR en 2026)
    ("        plafond_mensuel_km = round(500.0 / 12, 2)",
     "        plafond_annuel_km = (get_precompte_params(ref_date_fiscale)['exoneration_km_voiture_annuelle']\n"
     "                             if profil.precompte_applicable else 500.0)\n"
     "        plafond_mensuel_km = round(plafond_annuel_km / 12, 2)"),
    # 4) precompte calcule avec les parametres de l'annee de la fiche
    ("    precompte_brut = profil.precompte_brut(brut_imposable_precompte, etat_civil, nb_enfants, partenaire_revenus_pro)",
     "    precompte_brut = profil.precompte_brut(brut_imposable_precompte, etat_civil, nb_enfants, partenaire_revenus_pro,\n"
     "                                           reference_date=ref_date_fiscale)"),
    # 5) reduction precompte bonus emploi: taux de l'annee de la fiche
    ("    red_precompte_bonus = profil.reduction_precompte_bonus(bonus_a, bonus_b, brut_imposable)",
     "    red_precompte_bonus = profil.reduction_precompte_bonus(bonus_a, bonus_b, brut_imposable,\n"
     "                                                            reference_date=ref_date_fiscale)"),
]

for i, (old, new) in enumerate(remplacements, 1):
    n = content.count(old)
    if n != 1:
        raise SystemExit(f"ECHEC etape {i}: trouve {n} fois (attendu 1) -- RIEN n'a ete modifie.\n"
                         f"Ligne cherchee: {old[:80]}")
    content = content.replace(old, new)

import ast
ast.parse(content)  # verifie la syntaxe avant d'ecrire

shutil.copy(CHEMIN, CHEMIN + '.avant_precompte_annuel')
with open(CHEMIN, 'w') as f:
    f.write(content)
print("OK -- moteur_paie.py utilise le precompte de l'annee de la fiche")
print("   (copie de securite: moteur_paie.py.avant_precompte_annuel)")
