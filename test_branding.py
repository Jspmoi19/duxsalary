# -*- coding: utf-8 -*-
"""
test_branding.py -- DuxSalary
Identite unique (branding.py): logo, mentions et couleurs sur les pages et les
PDF ; navigation commune (fil d'Ariane, bouton retour, selecteur de dossier).
Sans base de donnees: gabarits rendus avec des donnees FICTIVES.
Lancer: python3 test_branding.py   -- doit afficher TOUS LES TESTS PASSENT
    python3 test_branding.py <dossier>   conserve des apercus HTML et PDF
"""
import glob
import io
import os
import re
import sys
from datetime import date

from jinja2 import Environment, FileSystemLoader

import branding
from branding import get_branding

RACINE = os.path.dirname(os.path.abspath(__file__))
GABARITS = os.path.join(RACINE, 'templates')
SORTIE = sys.argv[1] if len(sys.argv) > 1 else None
ECHECS = []
def check(label, obtenu, attendu=True):
    ok = obtenu == attendu
    print(f"{'✅' if ok else '❌'} {label}" + ('' if ok else f": obtenu={obtenu} attendu={attendu}"))
    if not ok: ECHECS.append(label)

lire = lambda chemin: io.open(chemin, encoding='utf-8').read()

print("=" * 70); print("IDENTITE -- branding.py, source unique"); print("=" * 70)
b = get_branding()
check("Logo present dans static/", bool(b['logo_path']) and os.path.exists(b['logo_path']))
check("Mentions legales", b['mentions'], "Global Smart Services · BCE 0805.778.307 · Jozef Van Elewijckstraat 86, 1853 Grimbergen")
check("Couleurs du logo", (b['couleur_primaire'], b['couleur_accent']), ('#1F4E79', '#4FC3F7'))
blanche = get_branding({'societe': 'Autre Société', 'couleur_primaire': '#112233'})
check("Marque blanche: identite propre possible par tenant", (blanche['societe'], blanche['couleur_primaire']), ('Autre Société', '#112233'))
check("Marque blanche: valeurs par defaut pour le reste", blanche['bce'], b['bce'])

print(); print("=" * 70); print("AUCUNE IDENTITE EN DUR ailleurs que dans branding.py"); print("=" * 70)
for nom in ('generer_fiche_pdf.py', 'contrats.py', 'contrats_nl.py', 'pdf_charges.py', 'app.py'):
    source = lire(os.path.join(RACINE, nom))
    check(f"{nom}: PDF habilles par branding.pdf_decor", 'pdf_decor(' in source)
    check(f"{nom}: pas de bleu de marque en dur", "HexColor('#1F4E79')" in source, False)
    check(f"{nom}: tous les doc.build passent par pdf_decor",
          len(re.findall(r'doc\.build\(', source)), len(re.findall(r'doc\.build\([^)]*pdf_decor\(', source)))

print(); print("=" * 70); print("GABARITS -- meme apparence et meme navigation partout"); print("=" * 70)
env = Environment(loader=FileSystemLoader(GABARITS))
env.filters['basename'] = lambda p: os.path.basename(p) if p else ''
pages = sorted(glob.glob(os.path.join(GABARITS, '*.html')))
heritent = [p for p in pages if '{% extends "base.html" %}' in lire(p)]
for chemin in pages:
    env.get_template(os.path.basename(chemin))        # erreur de syntaxe -> exception
check("Tous les gabarits se compilent", True)
check("Aucun bouton retour propre a une page (un seul, dans base.html)",
      [os.path.basename(p) for p in heritent if 'btn-back' in lire(p)], [])
check("Scripts des pages hors du bloc de contenu, avec leur balise",
      [os.path.basename(p) for p in heritent
       if '{% block scripts %}' in lire(p) and not re.search(r'\{% endblock %\}\s*\{% block scripts %\}\s*<script', lire(p))], [])
check("Plus de mention NexSocial sur les pages DuxSalary",
      [os.path.basename(p) for p in pages if not os.path.basename(p).startswith('nexsocial_')
       and re.search(r'NEX<span>|Propulsé par|NexSocial</', lire(p))], [])
check("Pages publiques: logo et mentions",
      [n for n in ('login.html', 'portail_formulaire.html', 'portail_public.html', 'portail_confirmation.html', 'portail_invalide.html')
       if 'marque.logo_url' not in lire(os.path.join(GABARITS, n)) or 'marque.mentions' not in lire(os.path.join(GABARITS, n))], [])

class Requete:
    def __init__(self, path): self.path = path; self.form = {}; self.args = {}
dossier = {'id': 7, 'nom': 'Société Fictive SRL', 'bce': '0000.000.000', 'rsz': '000-0000000-00', 'cp_principale': 'CP 200'}
travailleur = {'id': 3, 'prenom': 'Camille', 'nom': 'Exemple', 'dossier_id': 7}
commun = dict(marque=b, statique=branding.url_statique, session={'user_id': 1, 'user_nom': 'Utilisateur'}, tenant={},
              tous_les_dossiers=[dossier, {'id': 8, 'nom': 'Éts Démo SA'}], dossiers_archives=[{'id': 9, 'nom': 'Ancien Client SPRL'}])

def rendre(gabarit, chemin, **ctx):
    html = env.get_template(gabarit).render(request=Requete(chemin), **dict(commun, **ctx))
    if SORTIE:
        nom = 'apercu_' + gabarit.replace('.html', '') + '_' + (chemin.strip('/').replace('/', '_') or 'accueil') + '.html'
        io.open(os.path.join(SORTIE, nom), 'w', encoding='utf-8').write(
            html.replace('"/static/', '"' + ('../static/' if os.path.basename(os.path.abspath(SORTIE)) == 'outputs' else RACINE.replace('\\', '/') + '/static/')))
    return html

from documents_charges import attestation_salariale, formater
doc = attestation_salariale([], dossier, date(2026, 7, 1), date(2026, 8, 31))
ctx_doc = dict(document=doc, formater=formater, date_debut='2026-07-01', date_fin='2026-08-31', retour_url='/', retour_libelle='x',
               onglets=[{'libelle': 'Attestation salariale', 'url': '/dossier/7/resume-charge', 'actif': True},
                        {'libelle': 'Liste de ventilation', 'url': '/dossier/7/ventilation', 'actif': False}])

h = rendre('document_charges.html', '/dossier/7/resume-charge', dossier=dossier, dossier_actif=dossier, **ctx_doc)
check("En-tete: logo, sans le nom commercial en texte a cote", '<img src="/static/logo.png?v=' in h and '>DuxSalary<' not in h)
version_css = int(os.path.getmtime(os.path.join(RACINE, 'static', 'style.css')))
check("Fichiers statiques versionnes par leur date (style.css?v=<date du fichier>)",
      f'href="/static/style.css?v={version_css}"' in h and f"logo.png?v={int(os.path.getmtime(b['logo_path']))}" in h)
check("Aucune adresse /static/ sans version dans les gabarits",
      [os.path.basename(p) for p in pages if re.search(r'["\']/static/', lire(p))], [])
check("En-tete: plus de NEXSOCIAL", 'NEX' not in h.upper().replace('NEXT', ''))
check("Fil d'Ariane: Dossiers › dossier", 'href="/dossiers">Dossiers</a>' in h and 'href="/dossier/7">Société Fictive SRL</a>' in h)
check("Bouton retour explicite vers le dossier", 'Retour au dossier Société Fictive SRL' in h)
check("Selecteur de dossier: recherche et dossiers archives", 'selecteur-recherche' in h and 'Ancien Client SPRL' in h and '<select' not in h.split('app-body')[0])
check("Export PDF: nouvel onglet + message", 'formtarget="_blank"' in h and 'data-pdf="Attestation salariale"' in h and 'afficherMessage' in h)

h = rendre('document_charges.html', '/travailleur/3/compte-individuel', dossier=dossier, dossier_actif=dossier, travailleur=travailleur, **ctx_doc)
check("Fil d'Ariane: Dossiers › dossier › travailleur", 'href="/travailleur/3">Camille Exemple</a>' in h)
check("Bouton retour vers le travailleur", 'Retour à Camille Exemple' in h)

h = rendre('dossiers.html', '/dossiers', dossiers=[dossier])
check("Liste des dossiers: pas de bouton retour", 'btn-retour' in h, False)

h = env.get_template('login.html').render(marque=b, tenant={}, error=None)
check("Connexion: logo et mentions", '/static/logo.png' in h and b['mentions'] in h)
h = env.get_template('portail_formulaire.html').render(marque=b, portail={'dossier_nom': 'Société Fictive SRL'}, token='jeton')
check("Portail client (nouveau travailleur): logo et mentions", '/static/logo.png' in h and b['mentions'] in h)
if SORTIE:
    io.open(os.path.join(SORTIE, 'apercu_portail_formulaire.html'), 'w', encoding='utf-8').write(h.replace('"/static/', '"../static/'))
    io.open(os.path.join(SORTIE, 'apercu_login.html'), 'w', encoding='utf-8').write(
        env.get_template('login.html').render(marque=b, tenant={}, error=None).replace('"/static/', '"../static/'))

print(); print("=" * 70); print("PDF -- logo et mentions sur les documents"); print("=" * 70)
import tempfile
from pypdf import PdfReader
from moteur_paie import calculer_fiche_paie
from generer_fiche_pdf import generer_fiche_paie_pdf
data = calculer_fiche_paie('Camille', 'Exemple', '00.00.00-000.00', 'Rue Exemple 1, 1000 Bruxelles', 'BE00 0000 0000 0000',
    date(1990, 1, 1), date(2026, 1, 1), 'Société Fictive SRL', 'Rue Exemple 1, 1000 Bruxelles', '0000.000.000', '000-0000000-00',
    'CP 200', 'Comptable', 13.71, salaire_mensuel_fixe=2257.0, heures_semaine=38.0, heures_jour=7.6, jours_semaine=5,
    type_contrat='CDI', jours_prestes=22, heures_prestees=167.2, rgpt_actif=False, cheques_repas=False,
    categorie_employeur='010', code_ffe='C', code_importance='1', periode_debut=date(2026, 9, 1), periode_fin=date(2026, 9, 30))
chemin_pdf = os.path.join(SORTIE or tempfile.gettempdir(), 'exemple_fiche_de_paie.pdf')
generer_fiche_paie_pdf(data, chemin_pdf)
page = PdfReader(chemin_pdf).pages[0]
texte = page.extract_text()
check("Fiche de paie: mentions Global Smart Services en pied de page", 'Global Smart Services' in texte and '0805.778.307' in texte)
check("Fiche de paie: employeur toujours en tete du document", 'Société Fictive SRL' in texte)
check("Fiche de paie: nom commercial non repete en texte", 'DUXSALARY' in texte.upper(), False)
check("Fiche de paie: logo", len(page.images) >= 1)
check("Fiche de paie: une seule page", len(PdfReader(chemin_pdf).pages), 1)

from pdf_charges import generer_pdf_charges
pdf = generer_pdf_charges(doc)
chemin_pdf = os.path.join(SORTIE or tempfile.gettempdir(), 'exemple_attestation_vide.pdf')
open(chemin_pdf, 'wb').write(pdf)
page = PdfReader(chemin_pdf).pages[0]
check("Document de charges: logo et mentions", len(page.images) >= 1 and 'Global Smart Services' in page.extract_text())
if not SORTIE:
    os.remove(chemin_pdf); os.remove(os.path.join(tempfile.gettempdir(), 'exemple_fiche_de_paie.pdf'))

print(); print("=" * 70)
if ECHECS:
    print(f"❌ {len(ECHECS)} TEST(S) ECHOUE(S): {ECHECS}"); sys.exit(1)
print("✅ TOUS LES TESTS PASSENT -- identite et navigation.")
