# Patch -- calcul AUTOMATIQUE des mois ouvrant droit depuis les contrats
with open('/var/www/duxsalary/app.py', 'r') as f:
    content = f.read()

old = """    # GET: charger l'historique
    cur.execute(\"\"\"SELECT * FROM conges_droits WHERE travailleur_id=%s
        ORDER BY annee_vacances DESC\"\"\", (travailleur_id,))
    historique = [dict(r) for r in cur.fetchall()]"""

if old not in content:
    raise SystemExit("ECHEC: bloc historique non trouve -- rien modifie")

new = """    # GET: charger l'historique
    cur.execute(\"\"\"SELECT * FROM conges_droits WHERE travailleur_id=%s
        ORDER BY annee_vacances DESC\"\"\", (travailleur_id,))
    historique = [dict(r) for r in cur.fetchall()]

    # CALCUL AUTOMATIQUE des mois ouvrant droit, depuis les contrats reels
    cur.execute(\"\"\"SELECT id, type_contrat, statut, date_debut, date_fin
        FROM contrats WHERE travailleur_id=%s ORDER BY date_debut\"\"\", (travailleur_id,))
    tous_contrats = [dict(r) for r in cur.fetchall()]
    from conges_legaux import calculer_mois_depuis_contrats
    calcul_auto = {}
    for annee_vac in (_d.today().year, _d.today().year + 1):
        calcul_auto[annee_vac] = calculer_mois_depuis_contrats(tous_contrats, annee_vac - 1)"""

content = content.replace(old, new)

# Passer calcul_auto au template
old2 = """    return render_template('conges_travailleur.html',
        travailleur=travailleur, dossier=dossier, dossier_actif=dossier,
        historique=historique, statut=statut, cp_key=cp_key,
        is_etudiant_contrat=is_etudiant_contrat,
        estimation=estimation, annee_courante=annee_courante, **ctx)"""
new2 = """    return render_template('conges_travailleur.html',
        travailleur=travailleur, dossier=dossier, dossier_actif=dossier,
        historique=historique, statut=statut, cp_key=cp_key,
        is_etudiant_contrat=is_etudiant_contrat, calcul_auto=calcul_auto,
        estimation=estimation, annee_courante=annee_courante, **ctx)"""
if old2 not in content:
    raise SystemExit("ECHEC: bloc render_template non trouve -- rien modifie")
content = content.replace(old2, new2)

with open('/var/www/duxsalary/app.py', 'w') as f:
    f.write(content)
print("OK -- calcul automatique branche")
