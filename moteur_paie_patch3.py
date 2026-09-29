# Patch #3 — plafond fiscal 500EUR/an sur l'indemnite km voiture (precompte uniquement)
# Version autonome: calcule le surplus AVANT le bloc precompte, sans dependre
# de l'ordre du reste du fichier (evite tout crash de type "variable non definie").

with open('/var/www/duxsalary/moteur_paie.py', 'r') as f:
    content = f.read()

# 1) Calculer le surplus km AVANT le bloc precompte (variable independante,
#    utilise les memes parametres que le vrai calcul du km plus bas dans le fichier)
old1 = "    precompte_brut = profil.precompte_brut(brut_imposable, etat_civil, nb_enfants, partenaire_revenus_pro)"
if old1 not in content:
    raise SystemExit("ECHEC etape 1: ligne precompte_brut non trouvee — rien modifie")

new1 = """    # Plafond fiscal 500EUR/an sur indemnite km voiture (precompte uniquement,
    # PAS l'ONSS) -- source Securex + fin.belgium.be, annee de revenus 2026.
    montant_km_imposable_precompte = 0.0
    if km_domicile > 0 and moyen_transport == 'voiture' and not vehicule_societe and not cp.get('indem_deplacement_jour'):
        montant_km_estime = round(0.4444 * km_domicile * 2 * jours_prestes, 2)
        plafond_mensuel_km = round(500.0 / 12, 2)
        if montant_km_estime > plafond_mensuel_km:
            montant_km_imposable_precompte = round(montant_km_estime - plafond_mensuel_km, 2)
    brut_imposable_precompte = round(brut_imposable + montant_km_imposable_precompte, 2)
    precompte_brut = profil.precompte_brut(brut_imposable_precompte, etat_civil, nb_enfants, partenaire_revenus_pro)"""

content = content.replace(old1, new1)

# 2) Utiliser la meme base pour la reduction precompte bonus et la CSS (coherence fiscale)
old2 = "    if not is_etudiant and (bonus_a + bonus_b) > 0 and brut_imposable <= 3500:"
new2 = "    if not is_etudiant and (bonus_a + bonus_b) > 0 and brut_imposable_precompte <= 3500:"
if old2 in content:
    content = content.replace(old2, new2)

old3 = "    css = profil.css(brut_imposable)"
new3 = "    css = profil.css(brut_imposable_precompte)"
if old3 in content:
    content = content.replace(old3, new3)

with open('/var/www/duxsalary/moteur_paie.py', 'w') as f:
    f.write(content)

print("OK — patch km/precompte applique (version autonome, sans dependance d'ordre)")
