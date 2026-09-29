# Patch #5 — passer taux_km depuis le formulaire de generation de fiche
with open('/var/www/duxsalary/app.py', 'r') as f:
    content = f.read()

old = "            rgpt_actif=rgpt_actif, arab_heure=arab_heure, cheques_repas=cheques_repas,"
new = "            rgpt_actif=rgpt_actif, arab_heure=arab_heure, cheques_repas=cheques_repas,\n            taux_km=float(form.get('taux_km', 0.4444) or 0.4444),"
if old not in content:
    raise SystemExit("ECHEC - ligne non trouvee dans app.py, rien modifie")
content = content.replace(old, new)

with open('/var/www/duxsalary/app.py', 'w') as f:
    f.write(content)
import ast
ast.parse(content)
print("OK app.py")
