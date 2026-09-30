# Patch -- categorie employeur ONSS stockee dans le DOSSIER et utilisee par
# toutes les fiches du dossier. ATOMIQUE par fichier: verifie tout avant d'ecrire.
import shutil, ast, sys
sys.path.insert(0, '/var/www/duxsalary')

def patcher(chemin, etapes):
    content = open(chemin).read()
    for label, old, new in etapes:
        n = content.count(old)
        if n != 1:
            raise SystemExit(f"ECHEC {chemin} ({label}): trouve {n} fois -- RIEN n'a ete modifie dans ce fichier.")
        content = content.replace(old, new)
    ast.parse(content)
    return content

# 1) Base de donnees: colonne sur le dossier (defaut 000)
from database import get_conn
conn = get_conn(); cur = conn.cursor()
cur.execute("ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS categorie_employeur VARCHAR(3) DEFAULT '000'")
conn.commit(); cur.close(); conn.close()
print("BDD: colonne dossiers.categorie_employeur OK")

# 2) moteur_paie.py
moteur = patcher('/var/www/duxsalary/moteur_paie.py', [
    ("parametre", "    salaire_mensuel_fixe=0.0,\n",
     "    salaire_mensuel_fixe=0.0,\n    categorie_employeur='000',\n"),
    ("profil", "                                reference_date=periode_fin if periode_fin else date.today())",
     "                                reference_date=periode_fin if periode_fin else date.today(),\n"
     "                                categorie_employeur=categorie_employeur or '000')"),
    ("resultat", "        'onss_trimestre_utilise': onss_info['trimestre_utilise'],",
     "        'onss_trimestre_utilise': onss_info['trimestre_utilise'],\n"
     "        'onss_categorie_employeur': onss_info['categorie'],"),
])

# 3) app.py: la route de generation lit la categorie du dossier
app = patcher('/var/www/duxsalary/app.py', [
    ("select dossier", "               dos.premier_engagement, dos.premier_engagement_depuis,\n",
     "               dos.premier_engagement, dos.premier_engagement_depuis,\n"
     "               dos.categorie_employeur,\n"),
    ("appel moteur", "            premier_engagement=premier_engagement,\n            frais_nets=",
     "            premier_engagement=premier_engagement,\n"
     "            categorie_employeur=dimona.get('categorie_employeur') or '000',\n"
     "            frais_nets="),
])

for chemin, contenu in [('/var/www/duxsalary/moteur_paie.py', moteur), ('/var/www/duxsalary/app.py', app)]:
    shutil.copy(chemin, chemin + '.avant_categorie')
    open(chemin, 'w').write(contenu)
print("OK -- moteur_paie.py et app.py utilisent la categorie du dossier")
