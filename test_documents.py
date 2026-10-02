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
def check(label, obtenu, attendu=True, tol=0.011):
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
check("Colonnes par statut, etudiants a part", at['colonnes'], ['Ouvriers', 'Employés', 'Étudiants', 'Total'])
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

print(); print("=" * 70); print("FRAIS PROPRES A L'EMPLOYEUR -- dans le cout et dans le total des frais salariaux"); print("=" * 70)
check("Cout employeur d'une fiche = brut + patronal + frais propres (200)", e7['cout_employeur'],
      round(e7['salaire_brut'] + e7['onss_patronal'] + 200.0, 2))
check("Total frais salariaux (employes) = brut + patronal net + frais propres",
      val(at, 'Total', 'TOTAL FRAIS SALARIAUX', 'Employés'),
      round(sum(f['salaire_brut'] + f['onss_patronal'] for f in (e7, e8)) + 400.0, 2))
check("Total frais salariaux = somme des couts employeur (hors provision vacances ouvriers)",
      val(at, 'Total', 'TOTAL FRAIS SALARIAUX', 'Total'),
      round(sum(f['cout_employeur'] - f['provision_vacances_ouvrier'] for f in fiches), 2))

print(); print("=" * 70); print("ETUDIANT PUIS CDI -- colonne Etudiants, provision, date d'entree (cas type Ciwan)"); print("=" * 70)
from occupation import contrat_de_la_periode, date_premiere_occupation, libelle_etat_civil
def etudiant(debut, fin):
    return fiche(calculer_fiche_paie('E', 'M', 'n', 'a', 'BE', date(2004, 1, 1), date(2026, 7, 1), 'S', 'a', 'b', 'r',
        'CP 200', 'Etudiant', 13.71, heures_semaine=38.0, heures_jour=7.6, jours_semaine=5, type_contrat='STU',
        is_etudiant=True, jours_prestes=15, heures_prestees=114.0, rgpt_actif=False, cheques_repas=False,
        categorie_employeur='010', periode_debut=debut, periode_fin=fin), debut, 2)
s7, s9 = etudiant(date(2026, 7, 1), date(2026, 7, 31)), etudiant(date(2026, 9, 1), date(2026, 9, 30))
cdi10 = employe(date(2026, 10, 1), date(2026, 10, 31))
parcours = [s7, s9, cdi10]
at_c = attestation_salariale(parcours, dossier, date(2026, 1, 1), date(2026, 12, 31))
check("Brut des mois etudiants dans la colonne Etudiants", val(at_c, 'Rémunérations', 'TOTAL BRUT', 'Étudiants'),
      s7['salaire_brut'] + s9['salaire_brut'])
check("Colonne Employes = le mois de CDI uniquement", val(at_c, 'Rémunérations', 'TOTAL BRUT', 'Employés'), 2257.0)
check("Provision de pecule: 18,80 % sur 2.257 seulement (mois etudiants exclus)",
      val(at_c, 'Provisions pécule de vacances', 'Employés – provision', 'Total'), round(2257.0 * 0.188, 2))
check("Aucune provision dans la colonne Etudiants", val(at_c, 'Provisions pécule de vacances', 'Employés – provision', 'Étudiants'), 0.0)
mal_marquee = dict(s7, is_etudiant=False)     # type de contrat STU sans l'indicateur etudiant
check("Fiche de contrat STU sans indicateur etudiant: toujours hors provision",
      val(attestation_salariale([mal_marquee, cdi10], dossier, date(2026, 1, 1), date(2026, 12, 31)),
          'Provisions pécule de vacances', 'Employés – provision', 'Total'), round(2257.0 * 0.188, 2))

contrats_c = [{'id': 1, 'type_contrat': 'STU', 'date_debut': date(2026, 7, 1), 'date_fin': date(2026, 7, 31), 'statut': 'archive'},
              {'id': 2, 'type_contrat': 'STU', 'date_debut': date(2026, 9, 14), 'date_fin': date(2026, 9, 30), 'statut': 'archive'},
              {'id': 3, 'type_contrat': 'CDI', 'date_debut': date(2026, 10, 1), 'date_fin': None, 'statut': 'actif',
               'cp_key': 'CP 200', 'fonction': 'Comptable', 'heures_semaine': 38}]
check("Premiere occupation = premier contrat, etudiant compris", date_premiere_occupation(contrats_c), date(2026, 7, 1))
check("Contrat de juillet = le contrat etudiant, meme archive", contrat_de_la_periode(contrats_c, date(2026, 7, 1), date(2026, 7, 31))['id'], 1)
check("Contrat d'octobre = le CDI", contrat_de_la_periode(contrats_c, date(2026, 10, 1), date(2026, 10, 31))['id'], 3)
check("Contrat lie a la dimona prioritaire", contrat_de_la_periode(contrats_c, date(2026, 10, 1), date(2026, 10, 31), contrat_id=2)['id'], 2)
ci_c = compte_individuel(parcours, dict(travailleur, etat_civil='celibataire'), dossier, date(2026, 7, 1), date(2026, 10, 31),
                         contrat=contrats_c[2], date_entree=date_premiere_occupation(contrats_c))
entete_c = dict(ci_c['entete'])
check("Compte individuel: date d'entree = premiere occupation", entete_c["Date d'entrée"], '01/07/2026')
check("Etat civil avec accent et majuscule", (entete_c['État civil'], libelle_etat_civil('marie')), ('Célibataire', 'Marié(e)'))
check("Salaire de base « 2 257,00 €/mois », insecable", val(ci_c, 'Prestations', 'Salaire de base', 'Oct. 2026'), '2 257,00 €/mois')
check("Mois sans fiche: « — »", val(ci_c, 'Rémunérations', 'BRUT', 'Août 2026'), '—')
check("Total de la periode inchange par les mois sans fiche", val(ci_c, 'Rémunérations', 'BRUT', 'Total'), sum(f['salaire_brut'] for f in parcours))

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

print(); print("=" * 70); print("CONTRATS ACTIFS ; KM DE LA DERNIERE FICHE"); print("=" * 70)
from occupation import contrat_actif, contrats_actifs, km_a_proposer
JOUR = date(2026, 10, 2)
cs = [{'id': 1, 'statut': 'actif', 'date_fin': None}, {'id': 2, 'statut': 'actif', 'date_fin': date(2026, 12, 31)},
      {'id': 3, 'statut': 'actif', 'date_fin': date(2026, 10, 2)}, {'id': 4, 'statut': 'actif', 'date_fin': date(2026, 8, 31)},
      {'id': 5, 'statut': 'archive', 'date_fin': None}]
check("Contrats actifs: statut actif ET date de fin vide ou non depassee -> 3 sur 4 contrats au statut actif",
      [c['id'] for c in contrats_actifs(cs, JOUR)], [1, 2, 3])
check("Contrat dont la date de fin est passee (31/08): plus compte, sans etre modifie", (contrat_actif(cs[3], JOUR), cs[3]['statut']), (False, 'actif'))
check("Contrat qui se termine aujourd'hui: encore actif aujourd'hui", contrat_actif(cs[2], JOUR), True)
check("Contrat archive: jamais actif", contrat_actif(cs[4], JOUR), False)
_racine = os.path.dirname(os.path.abspath(__file__))
_lire = lambda n: open(os.path.join(_racine, n), encoding='utf-8').read()
check("Tableau de bord: le compteur vient de la regle commune, plus du nombre de lignes",
      ('{{ nb_contrats_actifs }}' in _lire('templates/dashboard.html'), 'contrats|length' in _lire('templates/dashboard.html'),
       'nb_contrats_actifs=len(contrats_actifs(' in _lire('app.py')), (True, False, True))
check("Liste des dossiers: meme regle dans la requete", 'c.date_fin IS NULL OR c.date_fin >= CURRENT_DATE' in _lire('database.py'))
k = km_a_proposer({'km_domicile': 12, 'taux_km': 0.08, 'moyen_transport': 'voiture', 'periode_debut': date(2026, 9, 1)}, 30)
check("Km de la derniere fiche: 12 km a 0,08 EUR/km, avec l'origine affichee",
      (k['km'], k['taux'], k['moyen_transport'], k['origine']), (12, 0.08, 'voiture', 'repris de la fiche de 09/2026'))
k = km_a_proposer(None, 30)
check("Aucune fiche avec des km: km de la fiche du travailleur et taux maximal, sans mention", (k['km'], k['taux'], k['origine']), (30, 0.4444, None))
check("Derniere fiche a 0 km: 0 est repris (pas les km du travailleur)", km_a_proposer({'km_domicile': 0, 'taux_km': 0.4444}, 30)['km'], 0)
r_km = calculer_fiche_paie('E', 'M', 'n', 'a', 'BE', date(1990, 1, 1), date(2026, 1, 1), 'S', 'a', 'b', 'r', 'CP 200', 'Classe A', 13.71,
    salaire_mensuel_fixe=2257.0, type_contrat='CDI', jours_prestes=22, heures_prestees=167.2, cheques_repas=False,
    km_domicile=12, taux_km=0.08, moyen_transport='voiture', periode_debut=date(2026, 9, 1), periode_fin=date(2026, 9, 30))
v_km = valeurs_fiche(r_km)
check("La fiche enregistre les km, le taux et le moyen de transport saisis", (v_km['km_domicile'], v_km['taux_km'], v_km['moyen_transport']), (12, 0.08, 'voiture'))
check("... indemnite km de la fiche: 12 x 2 x 22 x 0,08 = 42,24",
      next(i['montant'] for i in json.loads(v_km['indemnites']) if 'placement' in i['libelle']), 42.24)
from jinja2 import Environment as _E2, FileSystemLoader as _F2
import branding as _b2
_e2 = _E2(loader=_F2(os.path.join(_racine, 'templates')))
class _R2:
    path = '/dimona/5/generer-paie'; form = {}; args = {}
_d2 = {'id': 7, 'nom': 'Société Fictive SRL'}
h_km = _e2.get_template('generer_fiche_form.html').render(
    request=_R2(), marque=_b2.get_branding(), statique=_b2.url_statique, session={'user_id': 1, 'user_nom': 'U'}, tenant={},
    tous_les_dossiers=[_d2], dossiers_archives=[], dossier_actif=_d2, dimona={'id': 5, 'prenom': 'C', 'nom': 'E', 'travailleur_id': 3},
    contrat={'salaire_horaire': 13.71, 'cp_key': 'CP 200', 'type_contrat': 'CDI'}, prime_suggestion=None,
    prime_annuelle_suggestion=None, pecule_suggestion=None, annee=2026, mois=10, mois_nom='Octobre', cp_key='CP 200',
    vehicule_societe=False, maladie_infos=[], maladie_alertes=[],
    km_propose=km_a_proposer({'km_domicile': 12, 'taux_km': 0.08, 'moyen_transport': 'train', 'periode_debut': date(2026, 9, 1)}),
    km_domicile=12)
check("Formulaire de generation: km, taux et moyen de transport pre-remplis",
      ('name="km_domicile" value="12"' in h_km, 'name="taux_km" value="0.0800"' in h_km,
       'value="train" selected' in h_km, 'repris de la fiche de 09/2026' in h_km), (True, True, True, True))

print(); print("=" * 70); print("FICHES REMPLACEES -- une seule fiche active par travailleur, contrat et periode"); print("=" * 70)
import io as _io, re as _re
from datetime import datetime
from fiches_remplacees import (plan_doublons, memes_mois_autres_contrats, chemin_pdf_libre, libelle_remplacement,
                               rapport, cle_fiche, FICHES_ACTIVES)
def fp(id, travailleur=1, contrat=10, mois=7, cree=None, remplacee_par=None, **kw):
    return dict({'id': id, 'travailleur_id': travailleur, 'contrat_id': contrat, 'periode_debut': date(2026, mois, 1),
                 'periode_fin': date(2026, mois, 28), 'created_at': cree, 'remplacee_par': remplacee_par,
                 'salaire_brut': 761.43, 'salaire_net': 808.87, 'pdf_path': '/x/fiche.pdf'}, **kw)
base_fiches = [
    fp(1, cree=datetime(2026, 8, 3, 10, 0)), fp(2, cree=datetime(2026, 10, 2, 9, 0)), fp(3, cree=datetime(2026, 9, 1, 8, 0)),
    fp(4, mois=8, cree=datetime(2026, 9, 2, 8, 0)),                                # seule sur sa periode
    fp(5, travailleur=2, contrat=20, cree=datetime(2026, 8, 3, 10, 0)),            # etudiant...
    fp(6, travailleur=2, contrat=21, cree=datetime(2026, 8, 4, 10, 0)),            # ... puis CDI, meme mois
    fp(7, travailleur=3, contrat=None, cree=None), fp(8, travailleur=3, contrat=None, cree=None),   # sans date ni contrat
    fp(9, travailleur=4, cree=datetime(2026, 8, 1), remplacee_par=10), fp(10, travailleur=4, cree=datetime(2026, 9, 1)),
]
plan = plan_doublons(base_fiches)
check("Doublons: 2 groupes a traiter (travailleur 1 en juillet, travailleur 3)", [x['cle'][0] for x in plan], [1, 3])
check("Trois fiches du meme mois: la plus recente (creee le 02/10) est gardee, les deux autres remplacees",
      (plan[0]['gardee']['id'], sorted(f['id'] for f in plan[0]['remplacees'])), (2, [1, 3]))
check("Sans date de creation: l'identifiant le plus grand est garde", (plan[1]['gardee']['id'], [f['id'] for f in plan[1]['remplacees']]), (8, [7]))
check("Une fiche seule sur sa periode, ou deja remplacee: jamais dans la liste",
      any(f['id'] in (4, 9, 10) for x in plan for f in [x['gardee']] + x['remplacees']), False)
check("Meme mois mais contrats differents (etudiant puis CDI): pas un doublon, liste a part pour controle",
      ([f['id'] for _, _, g in memes_mois_autres_contrats(base_fiches) for f in g],
       any(f['id'] in (5, 6) for x in plan for f in [x['gardee']] + x['remplacees'])), ([5, 6], False))
check("La liste ne modifie aucune fiche", [f['remplacee_par'] for f in base_fiches], [None] * 8 + [10, None])
texte = rapport(plan, memes_mois_autres_contrats(base_fiches), {1: 'Exemple Camille (Société Fictive)'})
check("Script sans --appliquer: liste lisible, et « RIEN N'A ETE MODIFIE »",
      all(x in texte for x in ('Exemple Camille (Société Fictive)', 'fiche n° 2', 'GARDÉE', '« remplacée » par la fiche n° 2',
                               '3 fiche(s) seraient', "RIEN N'A ETE MODIFIE", 'A CONTROLER', '--appliquer')))
check("... il signale un PDF partage (ancien PDF deja ecrase)", 'même fichier PDF' in texte)
check("Aucun doublon: message clair", 'Aucun doublon' in rapport([], []))
existants = {'/pdf/fiche.pdf', '/pdf/fiche_v2.pdf'}
check("PDF d'une fiche regeneree: nouveau nom, l'ancien n'est jamais ecrase",
      (chemin_pdf_libre('/pdf/fiche.pdf', existants.__contains__), chemin_pdf_libre('/pdf/autre.pdf', existants.__contains__)),
      ('/pdf/fiche_v3.pdf', '/pdf/autre.pdf'))
check("Libelle: « Remplacée par la fiche du 02/10/2026 »",
      libelle_remplacement(fp(1, remplacee_par=2, remplacante_creee_le=datetime(2026, 10, 2, 9, 0))), 'Remplacée par la fiche du 02/10/2026')
check("Fiche active: pas de libelle", libelle_remplacement(fp(2)), None)
source_app = _io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py'), encoding='utf-8').read()
lectures = [m.start() for m in _re.finditer(r'FROM fiches_paie', source_app)]
sans_filtre = [source_app[i:i + 420].split('""")')[0].split('")')[0][:90] for i in lectures
               if 'remplacee_par' not in source_app[i:i + 420].split('""")')[0].split('")')[0]
               and 'WHERE id = %s' not in source_app[i:i + 120] and 'pdf_path = %s' not in source_app[i:i + 120]]
check("app.py: toutes les lectures de fiches_paie qui additionnent des fiches excluent les fiches remplacees "
      "(attestation, compte individuel, ventilation, aide DmfA, lettres ONSS, cumul du bonus)", sans_filtre, [])
check("... au moins 6 lectures controlees", len(lectures) >= 6, True)
check("Generation: l'ancienne fiche de la meme periode et du meme contrat passe a « remplacee »",
      'SET remplacee_par = %s, remplacee_le = NOW()' in source_app and 'contrat_id IS NOT DISTINCT FROM %s' in source_app)
check("Suppression de la fiche remplacante: l'ancienne redevient active",
      'SET remplacee_par = NULL, remplacee_le = NULL WHERE remplacee_par = %s' in source_app)
from jinja2 import Environment as _Env, FileSystemLoader as _FSL
import branding as _branding
_env = _Env(loader=_FSL(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')))
_env.filters['basename'] = lambda x: os.path.basename(x) if x else ''
class _Req:
    path = '/travailleur/3'; form = {}; args = {}
_dos = {'id': 7, 'nom': 'Société Fictive SRL'}
_fiches = [dict(fp(2, cree=datetime(2026, 10, 2)), remplacement=None, total_onss=100.0, pdf_path='/x/fiche_v2.pdf'),
           dict(fp(1, remplacee_par=2), remplacement='Remplacée par la fiche du 02/10/2026', total_onss=90.0)]
h = _env.get_template('fiche_travailleur.html').render(
    request=_Req(), marque=_branding.get_branding(), statique=_branding.url_statique, session={'user_id': 1, 'user_nom': 'U'},
    tenant={}, tous_les_dossiers=[_dos], dossiers_archives=[], dossier=_dos, dossier_actif=_dos,
    travailleur={'id': 3, 'prenom': 'Camille', 'nom': 'Exemple', 'dossier_id': 7, 'niss': None, 'date_naissance': None},
    tab='fiches', contrats=[{'id': 10, 'en_cours': True}], fiches=_fiches, documents=[])
check("Fiche du travailleur: « Remplacée par la fiche du 02/10/2026 » affiche, PDF de l'ancienne toujours accessible",
      'Remplacée par la fiche du 02/10/2026' in h and '/download/fiche.pdf' in h and '/download/fiche_v2.pdf' in h)
check("... l'onglet ne compte que la fiche active", 'Fiches de paie (1)' in h)

print(); print("=" * 70); print("LETTRES ONSS REMPLACEES -- une seule lettre active par dossier et par periode"); print("=" * 70)
from lettres_remplacees import (plan_doublons as plan_lettres, pour_historique, libelle_remplacement as lib_lettre,
                                rapport as rapport_lettres)
def lo(id, mois=7, dossier=7, total=100.0, cree=None, remplacee_par=None, **kw):
    return dict({'id': id, 'dossier_id': dossier, 'mois': mois, 'annee': 2026, 'total_brut': total * 4, 'total_onss_personnel': total / 4,
                 'total_onss_patronal': total * 3 / 4, 'total_onss': total, 'created_at': cree, 'remplacee_par': remplacee_par,
                 'pdf_path': '/x/lettre.pdf'}, **kw)
lettres_t = [lo(1, cree=datetime(2026, 8, 3), total=155.16), lo(2, cree=datetime(2026, 10, 2), total=155.16 - 39.8),
             lo(3, mois=8, cree=datetime(2026, 9, 2), total=200.0), lo(4, dossier=8, cree=datetime(2026, 8, 3)),
             lo(5, mois=9, cree=None), lo(6, mois=9, cree=None)]
pl = plan_lettres(lettres_t)
check("Doublons de lettres: juillet (dossier 7) et septembre ; aout et l'autre dossier ne sont pas touches",
      [(x['cle'], x['gardee']['id'], [l['id'] for l in x['remplacees']]) for x in pl], [((7, 2026, 7), 2, [1]), ((7, 2026, 9), 6, [5])])
check("La liste ne modifie aucune lettre", [l['remplacee_par'] for l in lettres_t], [None] * 6)
t_l = rapport_lettres(pl, {7: 'Société Fictive SRL'})
check("Script sans --appliquer: liste lisible et « RIEN N'A ETE MODIFIE »",
      all(x in t_l for x in ('Société Fictive SRL — Juillet 2026', 'lettre n° 2', 'GARDÉE', '« remplacée » par la lettre n° 2',
                             '2 lettre(s) seraient', "RIEN N'A ETE MODIFIE", '--appliquer')))
check("Aucun doublon: message clair", 'Aucun doublon' in rapport_lettres([]))
apres = [lo(1, cree=datetime(2026, 8, 3), total=155.16, remplacee_par=2, remplacante_creee_le=datetime(2026, 10, 2)),
         lo(2, cree=datetime(2026, 10, 2), total=115.36), lo(3, mois=8, cree=datetime(2026, 9, 2), total=200.0)]
hist, tot_l = pour_historique(apres)
check("Historique: aout, puis la lettre active de juillet, puis sa version remplacee", [l['id'] for l in hist], [3, 2, 1])
check("Libelle: « Remplacée par la lettre du 02/10/2026 » ; rien pour une lettre active",
      (hist[2]['remplacement'], hist[1]['remplacement']), ('Remplacée par la lettre du 02/10/2026', None))
check("Totaux: lettres actives seulement (115,36 + 200,00 = 315,36, sans les 155,16 de la lettre remplacee)",
      (tot_l['total_onss'], tot_l['nombre']), (315.36, 2))
h_l = _env.get_template('liste_lettres_onss.html').render(
    request=_Req(), marque=_branding.get_branding(), statique=_branding.url_statique, session={'user_id': 1, 'user_nom': 'U'},
    tenant={}, tous_les_dossiers=[_dos], dossiers_archives=[], dossier=_dos, dossier_actif=_dos, lettres=hist, totaux=tot_l)
check("Page « Historique ONSS »: lettre remplacee grisee avec son libelle, PDF toujours accessible, total des lettres actives",
      ('Remplacée par la lettre du 02/10/2026' in h_l, h_l.count('/download" class'), '315.36' in h_l, '2 lettre(s) active(s)' in h_l),
      (True, 3, True, True))
check("Aucune mention de paiement sur une lettre remplacee (l'outil ne sait pas si elle a ete payee)",
      any(m in h_l.lower() for m in ('payée', 'payee', 'déjà payé')), False)
check("Generation: la nouvelle lettre est toujours enregistree et l'ancienne passe a « remplacee » ; le PDF n'est pas ecrase",
      ('ON CONFLICT DO NOTHING' in source_app.split('def generer_lettre_onss_pdf')[1].split('\ndef ')[0],
       'UPDATE lettres_onss SET remplacee_par = %s, remplacee_le = NOW()' in source_app,
       "chemin_pdf_libre(os.path.join(OUTPUT_DIR, filename))" in source_app.split('def generer_lettre_onss_pdf')[1].split('\ndef ')[0]),
      (False, True, True))
_mig = _io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'migrate_charges.py'), encoding='utf-8').read()
check("Migration: colonnes des lettres et retrait de l'ancienne contrainte d'unicite",
      ("'lettres_onss': [" in _mig, "DROP CONSTRAINT" in _mig and "to_regclass('lettres_onss') IS NULL" in _mig), (True, True))

print(); print("=" * 70)
if ECHECS:
    print(f"❌ {len(ECHECS)} TEST(S) ECHOUE(S): {ECHECS}"); sys.exit(1)
print("✅ TOUS LES TESTS PASSENT -- documents de charges salariales.")
