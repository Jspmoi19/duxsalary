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

print(); print("=" * 70); print("FORMULAIRE CONTRAT ETUDIANT -- regles CP, minimum, contingent, lieu de signature"); print("=" * 70)
import json
from contrat_etudiant import contexte_formulaire
from cp_data import CP_DATABASE
from occupation import commune_de_l_adresse, suivi_contingent_etudiant
check("Commune du dossier", commune_de_l_adresse('Jozef Van Elewijckstraat 86, 1853 Grimbergen'), 'Grimbergen')
check("Commune en majuscules remise en forme", commune_de_l_adresse('BOULEVARD EXEMPLE 93 1000 BRUXELLES'), 'Bruxelles')
check("Adresse sans code postal: pas de commune devinee", commune_de_l_adresse('Rue Exemple 1'), '')
s = suivi_contingent_etudiant(600, 76, date(2026, 10, 1))
check("Contingent 650 h par annee civile (Instructions ONSS p.25-26)", (s['plafond'], s['restant'], s['depassement']), (650.0, 50.0, 26.0))
check("Depassement: alerte et cotisations ordinaires", 'cotisations ordinaires' in (s['alerte'] or ''))
check("Sous le contingent: pas d'alerte", suivi_contingent_etudiant(100, 76, date(2026, 10, 1))['alerte'], None)
check("Annee sans contingent charge: signale, pas de chiffre devine",
      (suivi_contingent_etudiant(0, 10, date(2025, 6, 1))['plafond'], 'non chargé' in suivi_contingent_etudiant(0, 10, date(2025, 6, 1))['alerte']), (None, True))

dossier_e = dict(dossier, adresse='Rue Exemple 1, 1853 Grimbergen', cp_principale='CP 336')
ctx_e = contexte_formulaire(dossier_e, 120.0, date(2026, 10, 1))
minimums = json.loads(ctx_e['minimums_json'])
check("Bareme etudiant de la CP 336 (officiel: 2.141,59 par mois)", (minimums['CP 336']['horaire'], minimums['CP 336']['categorie']),
      (13.0056, 'Étudiants et formation en alternance'))
check("CP 140.03: etudiant a 90 % du salaire de la fonction (officiel)", 'Étudiant : 90 %' in minimums['CP 140.03']['categorie'])
check("CP sans bareme etudiant (CP 121): minimum ordinaire, signale", 'pas de barème étudiant' in minimums['CP 121']['note'])
check("CP 200 sans age connu: bareme ordinaire, signale", "âge de l'étudiant inconnu" in minimums['CP 200']['note'])
check("CP sans bareme date: raison affichee, pas de minimum", 'raison' in minimums['CP 302'] and 'horaire' not in minimums['CP 302'])
check("Regles de la CP issues de regles_cp.py", any('Chèques-repas' in l for l in json.loads(ctx_e['regles_json'])['CP 140.03']))
from regles_cp import resume_regles_cp
r200 = ' | '.join(resume_regles_cp('CP 200', reference_date=date(2026, 10, 1)))
check("CP 200: 13e mois et prime annuelle (regles_cp.py)",
      "13e mois) : 1 mois de salaire, après 6 mois d'ancienneté" in r200 and 'Prime annuelle : 330,84 € brut, payée en juin' in r200)
check("CP 200: ecocheques 250 EUR en juin, pas d'obligation de cheques-repas (cheques_regles.py)",
      'Écochèques : 250,00 € par an à temps plein' in r200 and 'payés en juin' in r200 and 'Chèques-repas : aucune obligation sectorielle' in r200)
r140 = ' | '.join(resume_regles_cp('CP 140.03', reference_date=date(2026, 10, 1)))
check("CP 140.03: cheques-repas 3,09 depuis le 01/07/2026, ecocheques 200 EUR sous condition",
      'Chèques-repas obligatoires depuis le 01/07/2026 : 3,09 € par jour (2,00 € employeur + 1,09 € travailleur)' in r140
      and 'Écochèques : 200,00 €' in r140 and 'personnel non roulant et garage' in r140)
check("CP 140.03 avant le 01/07/2026: pas encore d'obligation de cheques-repas",
      'Chèques-repas : aucune obligation' in ' | '.join(resume_regles_cp('CP 140.03', reference_date=date(2026, 6, 1))))
check("CP sans prime enregistree: dit clairement, sans rien inventer", 'non enregistrées dans l\'outil' in r140)
check("CP 336: prime de fin d'annee signalee a verifier", 'à vérifier' in ' | '.join(resume_regles_cp('CP 336')))
check("Etudiant: non vise par cheques et ecocheques", 'Étudiant : non visé' in ' | '.join(resume_regles_cp('CP 200', etudiant=True)))

page_cheques = lire(os.path.join(GABARITS, 'cheques_dossier.html'))
check("Page Cheques: option « l'employeur fournit des repas », decochee par defaut",
      'name="repas_fournis" {% if config.repas_fournis %}checked{% endif %}' in page_cheques
      and "L'employeur fournit des repas (avantage de toute nature, 1,09 € par repas, soumis ONSS et précompte)" in page_cheques)
check("Plus d'avantage repas dans les regles de CP", any('Avantage repas' in l for cp in CP_DATABASE for l in resume_regles_cp(cp)), False)

print(); print("=" * 70); print("TACHE 3 -- charges de famille dans les formulaires travailleur"); print("=" * 70)
from occupation import charges_famille_du_formulaire
c = charges_famille_du_formulaire({'etat_civil': 'marie', 'partenaire_revenus_pro': 'non', 'nb_enfants_sans_handicap': '2',
                                   'nb_enfants_avec_handicap': '1', 'nb_personnes_charge_66': '1', 'nb_autres_personnes_charge': '',
                                   'handicape': 'on', 'conjoint_handicape': 'on'})
check("Formulaire -> colonnes du travailleur", (c['etat_civil'], c['nb_enfants_sans_handicap'], c['nb_enfants_avec_handicap'],
      c['nb_personnes_charge_66'], c['nb_autres_personnes_charge'], c['parent_isole'], c['handicape'], c['conjoint_handicape']),
      ('marie', 2, 1, 1, 0, False, True, True))
check("Valeurs absentes ou invalides: valeurs neutres", charges_famille_du_formulaire({'etat_civil': 'xx', 'nb_enfants_sans_handicap': 'abc'})
      ['etat_civil'] + str(charges_famille_du_formulaire({'nb_enfants_sans_handicap': '-3'})['nb_enfants_sans_handicap']), 'celibataire0')
champs = ('parent_isole', 'handicape', 'conjoint_handicape', 'nb_autres_personnes_charge', 'nb_personnes_charge_66',
          'nb_enfants_sans_handicap', 'nb_enfants_avec_handicap', 'etat_civil', 'partenaire_revenus_pro')
t_complet = dict(travailleur, etat_civil='marie', parent_isole=False, handicape=True, conjoint_handicape=True,
                 nb_autres_personnes_charge=2, nb_personnes_charge_66=1, date_naissance=None, date_sortie=None)
h_mod = rendre('modifier_travailleur.html', '/travailleur/3/modifier', dossier=dossier, dossier_actif=dossier,
               travailleur=t_complet, cp_keys=list(CP_DATABASE))
h_new = rendre('nouveau_travailleur.html', '/dossier/7/travailleur/nouveau', dossier=dossier, dossier_actif=dossier,
               cp_keys=list(CP_DATABASE))
check("Modifier le travailleur: tous les champs presents", [c for c in champs if f'name="{c}"' not in h_mod], [])
check("Nouveau travailleur: tous les champs presents", [c for c in champs if f'name="{c}"' not in h_new], [])
check("Valeurs enregistrees reaffichees (cases cochees, nombres)",
      'name="handicape" checked' in h_mod and 'name="conjoint_handicape" checked' in h_mod
      and 'name="parent_isole" checked' not in h_mod and 'name="nb_autres_personnes_charge" min="0" class="form-control" value="2"' in h_mod)
check("Anciens champs non enregistres retires (situation familiale, personnes a charge)",
      'name="situation_familiale"' in h_mod + h_new or 'name="personnes_charge"' in h_mod + h_new, False)
# Le moteur utilise bien ces charges: precompte plus bas avec un handicap et une autre personne a charge
from moteur_paie import calculer_fiche_paie as _calc
kw_c = dict(heures_semaine=38.0, heures_jour=7.6, jours_semaine=5, type_contrat='CDI', jours_prestes=22, heures_prestees=167.2,
            rgpt_actif=False, cheques_repas=False, salaire_mensuel_fixe=3000.0, periode_debut=date(2026, 10, 1), periode_fin=date(2026, 10, 31))
sans = _calc('A', 'B', 'n', 'a', 'BE', date(1990, 1, 1), date(2020, 1, 1), 'X', 'a', 'b', 'r', 'CP 200', 'E', 18.0, **kw_c)
avec = _calc('A', 'B', 'n', 'a', 'BE', date(1990, 1, 1), date(2020, 1, 1), 'X', 'a', 'b', 'r', 'CP 200', 'E', 18.0,
             charges_famille={'handicape': True, 'nb_autres_personnes_charge': 1}, **kw_c)
check("Precompte reduit de 2 x 624 / 12 = 104 EUR par mois", round(abs(sans['precompte']) - abs(avec['precompte']), 2), 104.0)
s = suivi_contingent_etudiant(100, 76, date(2026, 10, 1), heures_autres_employeurs=500)
check("Heures chez d'autres employeurs comptees dans le contingent (100 + 500 + 76 = 676)", (s['depassement'], s['restant']), (26.0, 50.0))
check("L'alerte detaille les heures chez d'autres employeurs", "500 h chez d'autres employeurs" in (s['alerte'] or ''))
check("CP 302 et CP 124 non gerees ; les quatre CP du moteur gerees",
      sorted(ctx_e['cp_gerees']), ['CP 121', 'CP 140.03', 'CP 200', 'CP 336'])
h = rendre('contrat_etudiant.html', '/contrat/etudiant/nouveau', dossier=dossier_e, dossier_actif=dossier_e,
           travailleur=dict(travailleur, niss='', adresse='', date_naissance=None), cp_data=CP_DATABASE, **ctx_e)
check("Le bouton ne genere que le contrat", 'Générer le contrat PDF</button>' in h and 'fiche de paie</button>' not in h)
check("Plus de valeur ni d'exemple sous le minimum (13.50)", '13.50' in h or '13,50' in h, False)
check("Lieu de signature = commune du dossier, modifiable", 'name="lieu_signature" class="form-control" value="Grimbergen"' in h)
check("Plus de « Bruxelles » en dur", 'value="Bruxelles"' in h, False)
check("Contingent: heures deja prestees affichees", '>120 h<' in h and '>650 h<' in h)
check("Memes composants que le formulaire CDI/CDD", h.count('class="form-label"') >= 15 and 'cp_info_box' in h and 'bareme_table' in h)
check("Alerte de salaire des la saisie", 'oninput="majSalaire()"' in h and 'inférieur au minimum' in h)
check("Contingent: par etudiant, compteur limite a cet employeur, champ autres employeurs, Student@work",
      'tous employeurs confondus' in h and 'chez cet employeur uniquement' in h
      and 'name="heures_autres_employeurs"' in h and 'https://www.studentatwork.be' in h)
check("CP non geree marquee dans la liste et bouton bloque", 'CP 302 – Restaurants — non gérée' in h and 'bouton.disabled = !geree' in h)

print(); print("=" * 70); print("FORMULAIRE CDI / CDD -- meme source que le formulaire etudiant"); print("=" * 70)
from contrat_etudiant import contexte_regles
h = rendre('contrat_cdi_cdd.html', '/dossier/7/contrat/nouveau', profil=dossier_e, dossier=dossier_e, dossier_actif=dossier_e,
           travailleurs=[travailleur], cp_data=CP_DATABASE, cp_json=json.dumps({k: {'meta': v['meta'], 'duree_travail': v['duree_travail'],
           'baremes': v['baremes']} for k, v in CP_DATABASE.items()}), travailleurs_json='[]', prefill_travailleur_id=None,
           prefill_travailleur=None, prefill_contrat=None, **contexte_regles(dossier_e))
check("Regles de la CP tirees de regles_cp.py (plus de liste ecrite dans la page)",
      'Sous-commission paritaire du transport routier et logistique' in h and "Prime fin d\\'année: 330.84" not in h)
check("Lieu de signature = commune du dossier", 'name="lieu_signature" class="form-control" value="Grimbergen"' in h and 'value="Bruxelles"' not in h)
check("CP non geree marquee et bouton bloque", '— non gérée' in h and 'bouton.disabled = !geree' in h)
from regles_cp import cp_geree
check("Refus cote serveur: cp_geree()", (cp_geree('CP 302'), cp_geree('CP 124'), cp_geree('CP 200')), (False, False, True))
check("Tache 4: categorie choisie dans une liste (plus de saisie libre) et annees d'experience",
      '<select name="categorie" id="categorie_input"' in h and 'name="annees_experience"' in h and 'type="text" name="categorie"' not in h)
grilles = json.loads(contexte_regles(dossier_e)['grilles_json'])
check("Tache 4: grille CP 200 transmise au formulaire (27 lignes d'experience, 4 classes)",
      (sorted(grilles), len(grilles['CP 200']['bareme_I']), grilles['CP 200']['classes'], grilles['CP 200']['bareme_I']['5'][2]),
      (['CP 200'], 27, ['A', 'B', 'C', 'D'], 2563.77))
ctx_19 = json.loads(contexte_formulaire(dossier_e, 0, date(2026, 10, 1), age=19)['minimums_json'])
check("Contrat etudiant CP 200: bareme des etudiants selon l'age (19 ans, classe A: 1.975,81 EUR/mois)",
      (ctx_19['CP 200']['horaire'], 'Barème des étudiants, 19 ans' in ctx_19['CP 200']['categorie']), (11.9988, True))

print(); print("=" * 70); print("PDF -- logo et mentions sur les documents"); print("=" * 70)
import tempfile
from pypdf import PdfReader
from moteur_paie import calculer_fiche_paie
from generer_fiche_pdf import generer_fiche_paie_pdf
data = calculer_fiche_paie('Camille', 'Exemple', '00.00.00-000.00', 'Rue Exemple 1, 1000 Bruxelles', 'BE00 0000 0000 0000',
    date(1990, 1, 1), date(2026, 1, 1), 'Société Fictive SRL', 'Rue Exemple 1, 1000 Bruxelles', '0000.000.000', '000-0000000-00',
    'CP 200', 'Classe A — Sans qualification', 13.71, fonction='Comptable',
    salaire_mensuel_fixe=2257.0, heures_semaine=38.0, heures_jour=7.6, jours_semaine=5,
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
import re as _re2
aplat = _re2.sub(r'\s+', ' ', texte)
check("Fiche de paie: « Statut/Profession » = statut et fonction du contrat (Employé — Comptable)",
      'Statut/Profession : Employé — Comptable' in aplat)
check("Fiche de paie: « Catégorie prof. » = categorie du bareme, en entier", 'Catégorie prof. : Classe A — Sans qualification' in aplat)
from occupation import libelle_statut_profession, libelle_categorie_bareme
check("Statut sans fonction renseignee: le statut seul", libelle_statut_profession(True, False, ''), 'Ouvrier')
check("Etudiant avec fonction", libelle_statut_profession(False, True, 'Vendeur'), 'Étudiant — Vendeur')
check("Categorie generique completee par la CP", libelle_categorie_bareme('Minimum sectoriel', 'CP 336'), 'Minimum sectoriel CP 336')
check("Categorie precise: inchangee", libelle_categorie_bareme('Chauffeur - Niveau 1', 'CP 140.03'), 'Chauffeur - Niveau 1')
check("Categorie deja completee: pas de doublon", libelle_categorie_bareme('Minimum sectoriel CP 336', 'CP 336'), 'Minimum sectoriel CP 336')
check("Categorie vide: tiret", libelle_categorie_bareme(None, 'CP 200'), '—')
data336 = calculer_fiche_paie('Camille', 'Exemple', '00.00.00-000.00', 'Rue Exemple 1, 1000 Bruxelles', 'BE00 0000 0000 0000',
    date(1990, 1, 1), date(2026, 1, 1), 'Société Fictive SRL', 'Rue Exemple 1, 1000 Bruxelles', '0000.000.000', '000-0000000-00',
    'CP 336', 'Minimum sectoriel', 13.71, fonction='Assistante administrative', salaire_mensuel_fixe=2300.0, heures_semaine=38.0,
    heures_jour=7.6, jours_semaine=5, type_contrat='CDI', jours_prestes=22, heures_prestees=167.2, cheques_repas=False,
    categorie_employeur='010', periode_debut=date(2026, 9, 1), periode_fin=date(2026, 9, 30))
chemin_336 = os.path.join(tempfile.gettempdir(), 'exemple_fiche_cp336.pdf')
generer_fiche_paie_pdf(data336, chemin_336)
pages336 = PdfReader(chemin_336).pages
aplat336 = _re2.sub(r'\s+', ' ', pages336[0].extract_text())
os.remove(chemin_336)
check("Fiche CP 336: « Employé — Assistante administrative » et « Minimum sectoriel CP 336 », toujours sur une page",
      ('Statut/Profession : Employé — Assistante administrative' in aplat336, 'Catégorie prof. : Minimum sectoriel CP 336' in aplat336,
       len(pages336)), (True, True, 1))

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
