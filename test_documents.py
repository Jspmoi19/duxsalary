# -*- coding: utf-8 -*-
"""
test_documents.py -- DuxSalary
Documents de charges salariales (compte individuel, attestation salariale,
liste de ventilation): chaine complete moteur -> colonnes de fiches_paie ->
document -> ecran et PDF, sur des fiches FICTIVES (aucune base de donnees).
Lancer: python3 test_documents.py   -- doit afficher TOUS LES TESTS PASSENT
"""
import json
import os
import sys
from datetime import date
from moteur_paie import calculer_fiche_paie
from documents_charges import (valeurs_fiche, compte_individuel, attestation_salariale,
                               liste_ventilation, formater)
from pdf_charges import generer_pdf_charges
from branding import get_branding

ECHECS = []
def check(label, obtenu, attendu, tol=0.011):
    if isinstance(attendu, (int, float)) and isinstance(obtenu, (int, float)):
        ok = abs(obtenu - attendu) <= tol
    else:
        ok = obtenu == attendu
    print(f"{'✅' if ok else '❌'} {label}: obtenu={obtenu} attendu={attendu}")
    if not ok: ECHECS.append(label)


def fiche(data, debut, travailleur_id):
    """Simule l'enregistrement puis la relecture d'une ligne de fiches_paie."""
    v = valeurs_fiche(data)
    for col in ('remunerations', 'indemnites', 'cotisations_complementaires'):
        v[col] = json.loads(v[col])          # JSONB relu par psycopg2 = liste Python
    return dict(v, periode_debut=debut, travailleur_id=travailleur_id)


def ouvrier(debut, fin, jours, heures, jf=0, hf=0.0):
    return fiche(calculer_fiche_paie('O', 'U', 'n', 'a', 'BE', date(1995, 1, 1), date(2026, 5, 1), 'S', 'a', 'b', 'r',
        'CP 140.03', 'Chauffeur', 15.2097, heures_semaine=38.0, heures_jour=2.0, jours_semaine=5, type_contrat='CDI',
        jours_prestes=jours, heures_prestees=heures, jours_feries_payes=jf, heures_feries=hf, rgpt_actif=True,
        cheques_repas=False, categorie_employeur='000', code_ffe='C', code_importance='1',
        periode_debut=debut, periode_fin=fin), debut, 1)


def employe(debut, fin, prime=0.0):
    return fiche(calculer_fiche_paie('E', 'M', 'n', 'a', 'BE', date(1990, 1, 1), date(2026, 1, 1), 'S', 'a', 'b', 'r',
        'CP 200', 'Comptable', 13.71, salaire_mensuel_fixe=2257.0, heures_semaine=38.0, heures_jour=7.6, jours_semaine=5,
        type_contrat='CDI', premier_engagement=True, jours_prestes=22, heures_prestees=167.2, rgpt_actif=False,
        cheques_repas=False, frais_nets=200.0, prime_exceptionnelle=prime, categorie_employeur='010', code_ffe='C',
        code_importance='1', periode_debut=debut, periode_fin=fin), debut, 2)


o6 = ouvrier(date(2026, 6, 1), date(2026, 6, 30), 22, 44.0)
o7 = ouvrier(date(2026, 7, 1), date(2026, 7, 31), 22, 44.0, 1, 2.0)
e7 = employe(date(2026, 7, 1), date(2026, 7, 31))
e8 = employe(date(2026, 8, 1), date(2026, 8, 31), prime=500.0)
# Fiche generee AVANT l'ajout du detail: seules les anciennes colonnes existent
ancienne = {'periode_debut': date(2026, 5, 1), 'travailleur_id': 1, 'salaire_brut': 600.0, 'onss_personnel': 20.0,
            'precompte': 0.0, 'salaire_net': 580.0, 'onss_patronal': 90.0, 'bonus_emploi_a': 30.0, 'bonus_emploi_b': 28.42,
            'reduction_structurelle': 80.0, 'reduction_premier_engagement': 0.0, 'jours_prestes': 20,
            'heures_prestees': 40.0, 'is_ouvrier': True, 'is_etudiant': False, 'prime_brut': 0, 'pecule_brut': 0,
            'onss_exceptionnel': 0}
dossier = {'nom': 'Société Fictive SRL', 'adresse': 'Rue Exemple 1, 1000 Bruxelles', 'bce': '0000.000.000',
           'rsz': '000-0000000-00', 'taux_provision_pecule_employes': None}
travailleur = {'nom': 'Fictif', 'prenom': 'Ouvrier', 'niss': '00.00.00-000.00', 'sexe': 'M', 'nationalite': 'Belge'}

def val(doc, section, libelle, colonne):
    """Valeur d'une ligne ; 0 si la ligne est sans objet sur la periode (non affichee)."""
    s = next((s for s in doc['sections'] if s['titre'] == section), {'lignes': []})
    l = next((l for l in s['lignes'] if l['libelle'].startswith(libelle)), None)
    return l['valeurs'][doc['colonnes'].index(colonne)] if l else 0.0

print("=" * 70); print("ENREGISTREMENT -- colonnes de fiches_paie"); print("=" * 70)
check("Ouvrier: brut majore = brut x 1,08", o7['brut_majore'], round(o7['salaire_brut'] * 1.08, 2))
check("Ouvrier: ONSS retenu = ONSS brut - bonus", o7['onss_personnel'],
      round(o7['onss_personnel_brut'] - o7['bonus_emploi_a'] - o7['bonus_emploi_b'], 2))
check("Employe: salaire de base mensuel", (e7['salaire_base'], e7['salaire_base_periodicite']), (2257.0, 'mois'))
check("Employe avec prime: ONSS exceptionnel 13,07%", e8['onss_exceptionnel'], round(500 * 0.1307, 2))

print(); print("=" * 70); print("COMPTE INDIVIDUEL -- ouvrier, juin a juillet 2026"); print("=" * 70)
ci = compte_individuel([o6, o7], travailleur, dossier, date(2026, 6, 1), date(2026, 7, 31))
check("Colonnes = mois de la periode + total", ci['colonnes'], ['Juin 2026', 'Juil. 2026', 'Total'])
check("Brut total", val(ci, 'Rémunérations', 'BRUT', 'Total'), o6['salaire_brut'] + o7['salaire_brut'])
check("Jours feries de juillet", val(ci, 'Prestations', 'Jours fériés', 'Juil. 2026'), 1)
check("Bonus A de juin", val(ci, 'Retenues', "Bonus à l'emploi (volet A)", 'Juin 2026'), o6['bonus_emploi_a'])
check("Imposable = brut - ONSS retenu", val(ci, 'Retenues', 'IMPOSABLE', 'Total'),
      val(ci, 'Rémunérations', 'BRUT', 'Total') + val(ci, 'Retenues', 'ONSS retenu', 'Total'))
net_recompose = (val(ci, 'Retenues', 'IMPOSABLE', 'Total') + val(ci, 'Retenues', 'Précompte', 'Total')
                 + val(ci, 'Retenues', 'Cotisation spéciale', 'Total')
                 + sum(l['valeurs'][-1] for l in next(s for s in ci['sections'] if s['titre'].startswith('Indemnités'))['lignes']))
check("Net = imposable - precompte - CSS + indemnites", val(ci, 'Net', 'NET', 'Total'), net_recompose)
check("Aucun avertissement (detail complet)", ci['avertissements'], [])
check("Rubriques sans objet non affichees (pas de double pecule)",
      any(l['libelle'].startswith('Double') for s in ci['sections'] for l in s['lignes']), False)

print(); print("=" * 70); print("ANCIENNE FICHE -- detail non disponible"); print("=" * 70)
ci_a = compte_individuel([ancienne, o6], travailleur, dossier, date(2026, 5, 1), date(2026, 6, 30))
check("Totaux existants affiches (brut de mai)", val(ci_a, 'Rémunérations', 'BRUT', 'Mai 2026'), 600.0)
check("Detail de mai = non disponible", val(ci_a, 'Retenues', 'IMPOSABLE', 'Mai 2026'), None)
check("Total avec un mois sans detail = non disponible", val(ci_a, 'Retenues', 'IMPOSABLE', 'Total'), None)
check("Detail de juin disponible", val(ci_a, 'Retenues', 'IMPOSABLE', 'Juin 2026') is not None, True)
check("Avertissement affiche", len(ci_a['avertissements']), 1)
check("Affichage 'n.d.'", formater(None), 'n.d.')

print(); print("=" * 70); print("ATTESTATION SALARIALE -- juillet et aout 2026"); print("=" * 70)
fiches = [o7, e7, e8]
at = attestation_salariale(fiches, dossier, date(2026, 7, 1), date(2026, 8, 31))
check("Colonnes par statut", at['colonnes'], ['Ouvriers', 'Employés', 'Total'])
check("Total brut = somme des fiches", val(at, 'Rémunérations', 'TOTAL BRUT', 'Total'), sum(f['salaire_brut'] for f in fiches))
check("Net employes", val(at, 'Travailleur', 'NET', 'Employés'), e7['salaire_net'] + e8['salaire_net'])
for colonne in at['colonnes']:
    lignes = next(s for s in at['sections'] if s['titre'] == 'ONSS patronal')['lignes']
    i = at['colonnes'].index(colonne)
    cotisations = sum(l['valeurs'][i] for l in lignes if l['style'] != 'total' and not l['libelle'].startswith('Réduction'))
    reductions = sum(l['valeurs'][i] for l in lignes if l['libelle'].startswith('Réduction'))
    check(f"{colonne}: cotisations + reductions = patronal net", round(cotisations + reductions, 2),
          val(at, 'ONSS patronal', 'ONSS PATRONAL NET', colonne), tol=0.03)
check("Patronal apres reduction structurelle = net + premier engagement",
      val(at, 'ONSS patronal', 'ONSS patronal après', 'Total'),
      val(at, 'ONSS patronal', 'ONSS PATRONAL NET', 'Total') - val(at, 'ONSS patronal', 'Réduction premier', 'Total'))
check("Premier engagement: employes uniquement ici", val(at, 'ONSS patronal', 'Réduction premier', 'Ouvriers'), 0.0)
check("Provision estimee employes 18,80% (brut hors primes)", val(at, 'Provisions pécule de vacances', 'Employés – provision', 'Total'),
      round(2 * 2257.0 * 0.188, 2))
at15 = attestation_salariale(fiches, dict(dossier, taux_provision_pecule_employes=15), date(2026, 7, 1), date(2026, 8, 31))
check("Taux de provision modifiable par dossier (15%)", val(at15, 'Provisions pécule de vacances', 'Employés – provision', 'Total'),
      round(2 * 2257.0 * 0.15, 2))
check("Provision ouvriers = cotisation annuelle 10,27% sur 108%", val(at, 'Provisions pécule de vacances', 'Ouvriers – cotisation', 'Ouvriers'),
      round(o7['brut_majore'] * 0.1027, 2))

print(); print("=" * 70); print("LISTE DE VENTILATION"); print("=" * 70)
ve = liste_ventilation(fiches, dossier, date(2026, 7, 1), date(2026, 8, 31))
check("Total general ONSS = travailleur + CSS + patronal net", val(ve, 'Résumé ONSS', 'TOTAL GÉNÉRAL ONSS', 'Total'),
      sum(f['onss_personnel'] + f['css'] + f['onss_patronal'] for f in fiches))
check("Precompte a verser", val(ve, 'Résumé précompte professionnel', 'TOTAL PRÉCOMPTE', 'Total'), sum(f['precompte'] for f in fiches))

print(); print("=" * 70); print("ECRAN ET PDF"); print("=" * 70)
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader
env = Environment(loader=ChoiceLoader([DictLoader({'base.html': '{% block content %}{% endblock %}'}),
                                       FileSystemLoader(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))]))
for nom, doc in (('compte individuel', ci_a), ('attestation', at), ('ventilation', ve)):
    html = env.get_template('document_charges.html').render(
        document=doc, formater=formater, date_debut='2026-07-01', date_fin='2026-08-31', retour_url='/', retour_libelle='x',
        onglets=[], marque=get_branding())
    check(f"Ecran {nom}: toutes les lignes affichees", html.count('<tr') - 1,
          sum(1 + len(s['lignes']) for s in doc['sections']))
    pdf = generer_pdf_charges(doc)
    check(f"PDF {nom} genere", pdf[:5], b'%PDF-')
    if len(sys.argv) > 1:   # python test_documents.py <dossier> : conserve les PDF pour relecture
        open(os.path.join(sys.argv[1], f"exemple_{nom.replace(' ', '_')}.pdf"), 'wb').write(pdf)

print(); print("=" * 70)
if ECHECS:
    print(f"❌ {len(ECHECS)} TEST(S) ECHOUE(S): {ECHECS}"); sys.exit(1)
print("✅ TOUS LES TESTS PASSENT -- documents de charges salariales.")
