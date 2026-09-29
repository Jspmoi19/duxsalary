# Patch #4 — permettre de choisir le taux km (ou le laisser au max legal 0.4444)
with open('/var/www/duxsalary/moteur_paie.py', 'r') as f:
    content = f.read()

# 1) Ajouter le parametre taux_km avec valeur par defaut = taux legal max
old1 = "    rgpt_actif=True, arab_heure=0.0, cheques_repas=True, frais_nets=0.0,"
new1 = "    rgpt_actif=True, arab_heure=0.0, cheques_repas=True, frais_nets=0.0,\n    taux_km=0.4444,"
if old1 not in content:
    raise SystemExit("ECHEC etape 1 - rien modifie")
content = content.replace(old1, new1)

# 2) Utiliser taux_km au lieu de la valeur codee en dur (2 endroits: montant_km_estime + montant reel)
old2 = "        montant_km_estime = round(0.4444 * km_domicile * 2 * jours_prestes, 2)"
new2 = "        montant_km_estime = round(taux_km * km_domicile * 2 * jours_prestes, 2)"
if old2 not in content:
    raise SystemExit("ECHEC etape 2 - rien modifie")
content = content.replace(old2, new2)

old3 = "        montant_km = round(0.4444 * km_domicile * 2 * jours_prestes, 2)\n        lignes_indemn.append({'libelle': f'Indemnité km ({km_domicile} km)',\n            'detail': '0.4444 €/km', 'jours': jours_prestes, 'montant': montant_km})"
new3 = "        montant_km = round(taux_km * km_domicile * 2 * jours_prestes, 2)\n        lignes_indemn.append({'libelle': f'Indemnité km ({km_domicile} km)',\n            'detail': f'{taux_km:.4f} €/km', 'jours': jours_prestes, 'montant': montant_km})"
if old3 not in content:
    raise SystemExit("ECHEC etape 3 - rien modifie")
content = content.replace(old3, new3)

with open('/var/www/duxsalary/moteur_paie.py', 'w') as f:
    f.write(content)
print("OK moteur_paie.py")
