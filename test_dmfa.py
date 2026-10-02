# -*- coding: utf-8 -*-
"""
test_dmfa.py -- DuxSalary
Aide a la DmfA (dmfa.py): codes prestation, detail enregistre dans les fiches,
recalcul trimestriel des reductions, document a recopier, page et PDF.
Lancer: python3 test_dmfa.py   -- doit afficher TOUS LES TESTS PASSENT
        python3 test_dmfa.py outputs   -- ecrit aussi un apercu et un PDF (donnees fictives)
Les montants attendus sont calcules a la main avec les formules des Instructions
ONSS 2026/3 (p.375-377, 383): aucune DmfA reelle disponible pour recouper.
"""
import sys, os, io, json
from datetime import date, timedelta
from moteur_paie import calculer_fiche_paie
from documents_charges import valeurs_fiche
from dmfa import (code_prestation, prestations_par_code, prestations_occupation, prestations_json, jours_du_calendrier,
                  reductions_trimestre, beta, aide_dmfa, bornes_trimestre, normaliser_unite_etablissement, jours_ouvrables)
ECHECS = []

def check(label, obtenu, attendu=True, tol=0.011):
    nombres = all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (obtenu, attendu))
    ok = abs(obtenu - attendu) <= tol if nombres else obtenu == attendu
    print(f"{'✅' if ok else '❌'} {label}: obtenu={obtenu} attendu={attendu}")
    if not ok: ECHECS.append(label)

T3 = bornes_trimestre(2026, 3)
check("Bornes du T3 2026", T3, (date(2026,7,1), date(2026,9,30)))

print("=" * 70); print("CODES PRESTATION (Instructions ONSS 2026/3 p.547-553)"); print("=" * 70)
for cj, statut, attendu in [('P', 'ouvrier', 1), ('F', 'employe', 1), ('PP', 'ouvrier', 1), ('MG', 'ouvrier', 1),
                            ('M2', 'ouvrier', 10), ('MC', 'employe', 11), ('MM', 'ouvrier', 50), ('CNP', 'employe', 30),
                            ('IN', 'ouvrier', 30), ('CI', 'ouvrier', 72), ('MAT', 'employe', 51),
                            ('CL', 'employe', 1), ('CL', 'ouvrier', 2), ('VP', 'ouvrier', 2), ('CE', 'ouvrier', 3)]:
    check(f"Calendrier « {cj} » ({statut}) -> code prestation {attendu}", code_prestation(cj, statut)[0], attendu)
for cj, statut, mot in [('MA', 'ouvrier', 'sans épisode'), ('CT', 'ouvrier', '71'), ('PAT', 'employe', '52'),
                        ('AC', 'ouvrier', '60'), ('VP', 'employe', 'employé')]:
    code, motif = code_prestation(cj, statut)
    check(f"Calendrier « {cj} » ({statut}): code a determiner, avec l'explication", (code, mot in motif), (None, True))

print(); print("=" * 70); print("JOURS ET HEURES PAR CODE"); print("=" * 70)
jours = [(date(2026,7,1), 'P', 3.0), (date(2026,7,2), 'P', 3.0), (date(2026,7,3), 'F', 3.0), (date(2026,7,6), 'VP', 0),
         (date(2026,7,7), 'M2', 3.0), (date(2026,7,8), 'CT', 0), (date(2026,7,11), 'WE', 0)]
p = prestations_par_code(jours, 'ouvrier', heures_jour=3.0)
check("Ouvrier: code 1 = 3 jours / 9 h ; code 2 = 1 jour / 3 h (heures du contrat) ; code 10 = 1 jour",
      {k: (v['jours'], v['heures']) for k, v in p['codes'].items()}, {1: (3, 9.0), 2: (1, 3.0), 10: (1, 3.0)})
check("... chomage temporaire: a determiner (1 jour), week-end ignore", {k: v['jours'] for k, v in p['a_determiner'].items()}, {'CT': 1})
p = prestations_par_code([(date(2026,7,6), 'CNP', 0), (date(2026,7,7), 'CL', 7.6)], 'employe', 7.6, au_mois=True,
                         jours_ouvrables_periode=jours_ouvrables(date(2026,7,1), date(2026,7,31)))
check("Employe au mois, juillet 2026 (23 jours ouvrables), 1 conge sans solde: code 1 = 22 jours, code 30 = 1 jour",
      {k: v['jours'] for k, v in p['codes'].items()}, {1: 22, 30: 1})
check("Forme enregistree dans la fiche", json.loads(prestations_json(p)),
      {'codes': {'1': {'jours': 22, 'heures': 167.2}, '30': {'jours': 1, 'heures': 7.6}}, 'a_determiner': {}})
lignes = [{'date_prestation': date(2026,9,24), 'code_journee': 'MG', 'heures': 7.6},
          {'date_prestation': date(2026,9,25), 'code_journee': 'MA', 'heures': 7.6},
          {'date_prestation': date(2026,9,28), 'code_journee': 'MG', 'heures': 7.6}]
check("Codes maladie du calendrier: tranche recalculee depuis l'episode, « MA » hors episode",
      [c for _, c, _ in jours_du_calendrier(lignes, {date(2026,9,24): {'tranche': 'MG'}, date(2026,9,25): {'tranche': 'M2'}})],
      ['MG', 'M2', 'MA'])

print(); print("=" * 70); print("REDUCTIONS -- recalcul trimestriel officiel (p.375-377, 383)"); print("=" * 70)
# Employe temps plein, 2.257,00 EUR/mois, T3 2026: 66 jours (23 + 21 + 22), D = 5
# facteur = 65/66 = 0,98 ; S = 6771 x 0,98 = 6.635,58
# R = 0,14 x (11.687,74 - 6.635,58) + 0,16 x (9.738,14 - 6.635,58) = 707,30 + 496,41 = 1.203,71
# µ = 66/65 = 1,02 ; ß = 1/1,02 -> Ps = R = 1.203,71 ; Pg = G = 2.000,00
r = reductions_trimestre(6771.0, {1: {'jours': 66, 'heures': 501.6}}, True, 5, 38.0, T3[1], premier_engagement=True)
check("Temps plein: facteur 13 x D / J = 0,98", r['facteur'], 0.98)
check("S = 6.635,58", r['S'], 6635.58)
check("R = 1.203,71", r['R'], 1203.71)
check("µ = 1,02", r['mu'], 1.02)
check("Reduction structurelle du trimestre = 1.203,71", r['Ps'], 1203.71)
check("Premier engagement = G = 2.000,00 (depuis le 01/07/2026)", (r['G'], r['Pg']), (2000.0, 2000.0))
r = reductions_trimestre(6771.0, {1: {'jours': 66, 'heures': 501.6}}, True, 5, 38.0, T3[1], premier_engagement=True,
                         cotisations_reductibles=1692.75)
check("Plafond des cotisations reductibles (1.692,75): le premier engagement est reduit en premier",
      (r['Ps'], r['Pg'], r['plafonne']), (1203.71, 489.04, True))
# Ouvrier temps partiel 15 h / 38 h: 195 h prestees + 15 h de vacances legales (code 2), W = 2.911,35
# S: H = 195 (code 2 exclu) -> facteur = 494/195 = 2,53 ; S = 7.365,72
# R = 0,14 x (11.687,74 - 7.365,72) + 0,16 x (9.738,14 - 7.365,72) = 605,08 + 379,59 = 984,67
# µ: Z = 210 (code 2 compris) -> 210/494 = 0,43 ; ß = 1,18 -> Ps = 984,67 x 0,43 x 1,18 = 499,62
codes = {1: {'jours': 65, 'heures': 195.0}, 2: {'jours': 5, 'heures': 15.0}, 50: {'jours': 3, 'heures': 9.0}}
r = reductions_trimestre(2911.35, codes, False, 5, 38.0, T3[1], mi_temps=False)
check("Temps partiel: H du salaire de reference sans les vacances des ouvriers (195 h), facteur 2,53", (r['J'], r['facteur']), (195.0, 2.53))
check("... S = 7.365,72 et R = 984,67", (r['S'], r['R']), (7365.72, 984.67))
check("... µ avec les vacances des ouvriers (210 h): 0,43 ; jours de mutuelle exclus", (r['X'], r['mu']), (210.0, 0.43))
check("... reduction structurelle = 984,67 x 0,43 x 1,18 = 499,62", r['Ps'], 499.62)
check("Plancher: µ(glob) < 0,275 sans contrat a mi-temps -> ß = 0", beta(0.20, True, mi_temps=False), 0.0)
check("... mais ß = 1,18 avec un contrat au moins a mi-temps", beta(0.20, True, mi_temps=True), 1.18)
check("ß entre 0,55 et 0,80: 1,18 + (0,60 - 0,55) x 0,28 = 1,194", beta(0.60), 1.194, tol=0.0001)
check("Sans prestation: aucune reduction", reductions_trimestre(0.0, {}, True, 5, 38.0, T3[1])['Ps'], 0.0)

print(); print("=" * 70); print("NUMERO D'UNITE D'ETABLISSEMENT"); print("=" * 70)
check("2.123.456.789 accepte", normaliser_unite_etablissement('2.123.456.789'), ('2.123.456.789', None))
check("2123456789 mis en forme", normaliser_unite_etablissement(' 2123456789 ')[0], '2.123.456.789')
check("Vide: pas d'erreur", normaliser_unite_etablissement(''), (None, None))
check("Numero d'entreprise (0...) refuse", normaliser_unite_etablissement('0805.778.307')[1] is not None)
check("Trop court refuse", normaliser_unite_etablissement('2.123.456')[1] is not None)

print(); print("=" * 70); print("DOCUMENT -- employe temps plein, T3 2026"); print("=" * 70)
DOSSIER = {'id': 7, 'nom': 'Société Fictive SRL', 'bce': '0000.000.000', 'rsz': '000-0000000-00', 'categorie_employeur': '010',
           'code_ffe': 'C', 'code_importance': '1', 'premier_engagement': True, 'numero_unite_etablissement': '2.123.456.789'}
C_EMP = {'id': 11, 'type_contrat': 'CDI', 'cp_key': 'CP 200', 'date_debut': date(2026,1,1), 'date_fin': None, 'statut': 'actif',
         'heures_jour': 7.6, 'jours_semaine': 5, 'heures_semaine': 38.0}

def fin_mois(d):
    return (date(d.year + d.month // 12, d.month % 12 + 1, 1) - timedelta(days=1))

def fiche(data, contrat, debut, jours_cal=(), avec_detail=True):
    """Simule l'enregistrement d'une fiche comme le fait app.py (detail DmfA compris)."""
    if avec_detail:
        data['prestations_dmfa'] = prestations_json(prestations_occupation(contrat, list(jours_cal), debut, fin_mois(debut)))
    return dict(valeurs_fiche(data), periode_debut=debut, periode_fin=fin_mois(debut), contrat_id=contrat['id'])

def fiche_employe(debut, prime=0.0, jours_cal=(), avec_detail=True, jours_chomage=0):
    return fiche(calculer_fiche_paie('E', 'M', 'n', 'a', 'BE', date(1990,1,1), date(2026,1,1), 'S', 'a', 'b', 'r',
        'CP 200', 'Classe A', 13.71, salaire_mensuel_fixe=2257.0, heures_semaine=38.0, heures_jour=7.6, jours_semaine=5,
        type_contrat='CDI', premier_engagement=True, jours_prestes=22, heures_prestees=167.2, cheques_repas=False,
        prime_exceptionnelle=prime, categorie_employeur='010', code_ffe='C', code_importance='1', jours_chomage=jours_chomage,
        periode_debut=debut, periode_fin=fin_mois(debut)), C_EMP, debut, jours_cal, avec_detail)

MOIS = [date(2026,7,1), date(2026,8,1), date(2026,9,1)]
EMP = {'id': 2, 'nom': 'Exemple', 'prenom': 'Camille', 'niss': '00.00.00-000.00', 'premier_engagement': True}
fiches_e = [fiche_employe(m) for m in MOIS]
doc = aide_dmfa(DOSSIER, 2026, 3, [{'travailleur': EMP, 'contrats': [C_EMP], 'fiches': fiches_e, 'jours': []}])
t = doc['travailleurs'][0]; o = t['occupations'][0]
check("Code travailleur 495, une ligne d'occupation", (o['code_travailleur'], len(t['occupations'])), ('495', 1))
check("Prestations: code 1 = 66 jours (23 + 21 + 22), rien d'autre", {k: v['jours'] for k, v in o['prestations'].items()}, {1: 66})
check("Detail enregistre dans les fiches = calendrier: aucune alerte", t['alertes'], [])
check("Remuneration code 1 = 3 x 2.257,00 = 6.771,00", o['remunerations'], {1: 6771.0, 2: 0.0})
cot = {x[0] + '|' + x[1][:22]: x for x in o['cotisations']}
check("Cotisation personnelle: 13,07 % x 6.771,00 = 884,97", cot['495|Cotisation personnelle'][4], 884.97)
check("Recalcul des cotisations proche de la somme des fiches (ecart d'arrondi < 0,10)",
      abs(o['cotisations_recalcul'] - o['cotisations_fiches']) < 0.10)
check("Reduction structurelle: recalcul trimestriel 1.203,71", o['reductions']['Ps'], 1203.71)
check("... somme des fiches (calcul mensuel) differente du recalcul, les deux sont affichees",
      (o['reductions_fiches']['3000'] > 0, abs(o['reductions_fiches']['3000'] - 1203.71) > 0.01), (True, True))
check("Premier engagement plafonne: structurelle + premier engagement = cotisations reductibles",
      round(o['reductions']['Ps'] + o['reductions']['Pg'], 2), o['reductible_recalcul'])
titres = [x['titre'].split(' —')[0].split(' (')[0] for x in t['tableaux']]
check("Tableaux dans l'ordre de la DmfA web", titres, ['Ligne travailleur', 'Prestations', 'Rémunérations', 'Cotisations', 'Réductions'])
occ = dict(t['tableaux'][0]['lignes'])
check("Ligne d'occupation: CP 200.00, 5 jours, temps plein, Q = S = 38, unite d'etablissement",
      (occ['Commission paritaire'], occ['Jours par semaine du régime de travail'], occ['Type de contrat'],
       occ['Heures par semaine du travailleur (Q)'], occ["Numéro d'unité d'établissement"]),
      ('200.00', '5', 'Temps plein', '38', '2.123.456.789'))
red = {l[0]: l for l in t['tableaux'][4]['lignes']}
check("Reductions: codes 0001, 3000 et 3315, avec somme des fiches, recalcul et ecart", sorted(red), ['0001', '3000', '3315'])
check("... ligne 3000: recalcul 1 203,71", red['3000'][3], '1 203,71')
tot = doc['donnees_totaux']
check("Total: net du = cotisations + CSS - bonus - reductions (recalcul)",
      tot['net_recalcul'], round(tot['cot_recalcul'] + tot['css'] - tot['bonus'] - tot['s_recalcul'] - tot['g_recalcul'], 2))
check("En-tete: trimestre, categorie, codes FFE et d'importance",
      [v for l, v in doc['entete'] if l in ('Trimestre', "Catégorie d'employeur", 'Code FFE', "Code d'importance")],
      ['2026/3', '010', '1', 'C'])

print(); print("=" * 70); print("CONTROLES ET ALERTES"); print("=" * 70)
def alertes(travailleurs, dossier=DOSSIER):
    d = aide_dmfa(dossier, 2026, 3, travailleurs)
    return d['alertes'] + [a for t in d['travailleurs'] for a in t['alertes']], d
al, _ = alertes([{'travailleur': EMP, 'contrats': [C_EMP], 'fiches': fiches_e[:2], 'jours': []}])
check("Mois sans fiche (09/2026): alerte", any('Pas de fiche de paie pour 09/2026' in a for a in al))
al, _ = alertes([{'travailleur': EMP, 'contrats': [C_EMP], 'fiches': fiches_e, 'jours': [(date(2026,8,10), 'CNP', 0)]}])
check("Calendrier modifie apres la fiche (un conge sans solde ajoute): alerte avec les deux decomptes",
      any('ne correspond plus aux fiches' in a and 'code 30 = 1 j' in a for a in al))
anciennes = [fiche_employe(m, avec_detail=False) for m in MOIS]
al, d = alertes([{'travailleur': EMP, 'contrats': [C_EMP], 'fiches': anciennes, 'jours': []}])
check("Fiches generees avant l'enregistrement du detail: alerte, le calendrier sert seul",
      (any("avant l'enregistrement du détail" in a for a in al), d['travailleurs'][0]['occupations'][0]['prestations'][1]['jours']), (True, 66))
al, d = alertes([{'travailleur': EMP, 'contrats': [C_EMP], 'fiches': fiches_e, 'jours': [(date(2026,8,10), 'CT', 0)]}])
check("Chomage temporaire: « code a determiner », jamais devine",
      (any('Code à déterminer pour 1 jour(s) « CT »' in a and '71' in a for a in al),
       any(l[0] == 'à déterminer' for l in d['travailleurs'][0]['tableaux'][1]['lignes'])), (True, True))
al, _ = alertes([{'travailleur': EMP, 'contrats': [C_EMP], 'fiches': fiches_e, 'jours': []}],
                dict(DOSSIER, numero_unite_etablissement=None, code_ffe=None))
check("Unite d'etablissement manquante: alerte", any("unité d'établissement non renseigné" in a for a in al))
al, d = alertes([{'travailleur': EMP, 'contrats': [dict(C_EMP, cp_key='CP 302')], 'fiches': [], 'jours': []}])
check("CP non geree: alerte, aucun calcul devine", (any('CP 302 non repris' in a for a in al), d['travailleurs'][0]['occupations']), (True, []))
check("Trimestre sans travailleur: alerte", any('Aucun travailleur' in a for a in alertes([])[0]))
archive = dict(C_EMP, id=12, statut='archive')
_, d = alertes([{'travailleur': EMP, 'contrats': [archive], 'fiches': [], 'jours': []}])
check("Contrat archive sans fiche: non repris", d['travailleurs'], [])
prime = [fiche_employe(MOIS[0]), fiche_employe(MOIS[1]), fiche_employe(MOIS[2], prime=500.0)]
_, d = alertes([{'travailleur': EMP, 'contrats': [C_EMP], 'fiches': prime, 'jours': []}])
check("Prime: code remuneration 2 = 500,00, code 1 inchange", d['travailleurs'][0]['occupations'][0]['remunerations'], {1: 6771.0, 2: 500.0})


print(); print("=" * 70); print("PREMIER ENGAGEMENT -- un seul travailleur designe par dossier (code 3315)"); print("=" * 70)
from occupation import premier_engagement_du_travailleur as pe_trav
check("Dossier coche + travailleur designe: reduction appliquee, sans alerte", pe_trav(True, True, 1), (True, None))
check("Dossier coche, autre travailleur designe: pas de reduction pour celui-ci, sans alerte", pe_trav(True, False, 1), (False, None))
ap, al_pe = pe_trav(True, False, 0)
check("Dossier coche, aucun travailleur designe: pas de reduction + alerte", (ap, 'aucun travailleur' in al_pe), (False, True))
ap, al_pe = pe_trav(False, True, 1)
check("Travailleur designe mais dossier non coche: pas de reduction + alerte", (ap, 'dossier' in al_pe), (False, True))
check("Plusieurs designes: alerte", 'plusieurs' in pe_trav(True, True, 2)[1])
check("Ni dossier ni travailleur: rien", pe_trav(False, False, 0), (False, None))
NON = dict(EMP, id=4, premier_engagement=False)
sans_pe = [fiche(calculer_fiche_paie('E', 'M', 'n', 'a', 'BE', date(1990,1,1), date(2026,1,1), 'S', 'a', 'b', 'r',
    'CP 200', 'Classe A', 13.71, salaire_mensuel_fixe=2257.0, heures_semaine=38.0, heures_jour=7.6, jours_semaine=5,
    type_contrat='CDI', premier_engagement=False, jours_prestes=22, heures_prestees=167.2, cheques_repas=False,
    categorie_employeur='010', code_ffe='C', code_importance='1', periode_debut=m, periode_fin=fin_mois(m)), C_EMP, m) for m in MOIS]
al, d = alertes([{'travailleur': EMP, 'contrats': [C_EMP], 'fiches': fiches_e, 'jours': []},
                 {'travailleur': NON, 'contrats': [dict(C_EMP, id=13)], 'fiches': [dict(f, contrat_id=13) for f in sans_pe], 'jours': []}])
o_des, o_non = d['travailleurs'][0]['occupations'][0], d['travailleurs'][1]['occupations'][0]
check("DmfA: le travailleur designe a la reduction 3315, l'autre non", (o_des['reductions']['Pg'] > 0, o_non['reductions']['Pg']), (True, 0.0))
check("... pas de ligne 3315 pour le travailleur non designe, aucune alerte",
      (any(l[0] == '3315' for l in d['travailleurs'][1]['tableaux'][4]['lignes']), al), (False, []))
check("... l'autre travailleur garde toute sa reduction structurelle (1.203,71)", o_non['reductions']['Ps'], 1203.71)
al, d = alertes([{'travailleur': NON, 'contrats': [C_EMP], 'fiches': fiches_e, 'jours': []}])
check("Anciennes fiches avec premier engagement, travailleur non designe: ligne 3315 a 0 et alertes",
      (d['travailleurs'][0]['occupations'][0]['reductions']['Pg'], any('aucun travailleur' in a for a in al),
       any('à régulariser' in a for a in al)), (0.0, True, True))
al, _ = alertes([{'travailleur': EMP, 'contrats': [C_EMP], 'fiches': fiches_e, 'jours': []},
                 {'travailleur': dict(NON, premier_engagement=True), 'contrats': [dict(C_EMP, id=13)], 'fiches': [], 'jours': []}])
check("Deux travailleurs designes: alerte", any('plusieurs travailleurs désignés' in a for a in al))
h_pe = None

print(); print("=" * 70); print("OUVRIER A TEMPS PARTIEL AVEC MALADIE ; ETUDIANT"); print("=" * 70)
C_OUV = {'id': 21, 'type_contrat': 'CDI', 'cp_key': 'CP 140.03', 'date_debut': date(2026,1,1), 'date_fin': None, 'statut': 'actif',
         'heures_jour': 3.0, 'jours_semaine': 5, 'heures_semaine': 38.0}
OUV = {'id': 3, 'nom': 'Modèle', 'prenom': 'Sacha', 'niss': ''}
def calendrier_ouvrier(debut, speciaux=None):
    js = []
    d = debut
    while d <= fin_mois(debut):
        if d.weekday() < 5:
            js.append((d, (speciaux or {}).get(d, 'P'), 3.0))
        d += timedelta(days=1)
    return js
def fiche_ouvrier(debut, cal):
    prest = [j for j in cal if j[1] == 'P']
    tr = {'MG': [], 'M2': [], 'MC': [], 'MM': []}
    for d, c, h in cal:
        if c in tr: tr[c].append({'date': d, 'tranche': c, 'heures': h})
    inc = [x for v in tr.values() for x in v]
    return fiche(calculer_fiche_paie('O', 'U', 'n', 'a', 'BE', date(1995,1,1), date(2026,1,1), 'S', 'a', 'b', 'r',
        'CP 140.03', 'Chauffeur', 15.0, heures_semaine=38.0, heures_jour=3.0, jours_semaine=5, type_contrat='CDI',
        jours_prestes=len(prest), heures_prestees=3.0 * len(prest), rgpt_actif=False, cheques_repas=False,
        categorie_employeur='010', code_ffe='C', code_importance='1',
        incapacite={'regime': 'ouvrier', 'jours': inc, 'infos': [], 'alertes': []} if inc else None,
        periode_debut=debut, periode_fin=fin_mois(debut)), C_OUV, debut, cal)
# Septembre: malade du 07/09 au 30/09 -> 5 jours garantis, 5 jours de 2e semaine, 8 jours de complement
malade = {}
for n in range(7, 31):
    d = date(2026,9,n)
    malade[d] = 'MG' if n <= 13 else ('M2' if n <= 20 else 'MC')
cals = [calendrier_ouvrier(MOIS[0]), calendrier_ouvrier(MOIS[1], {date(2026,8,3): 'VP', date(2026,8,4): 'VP'}),
        calendrier_ouvrier(MOIS[2], malade)]
fiches_o = [fiche_ouvrier(m, c) for m, c in zip(MOIS, cals)]
doc_o = aide_dmfa(DOSSIER, 2026, 3, [{'travailleur': OUV, 'contrats': [C_OUV], 'fiches': fiches_o,
                                      'jours': [j for c in cals for j in c]}])
t = doc_o['travailleurs'][0]; o = t['occupations'][0]
check("Ouvrier: code travailleur 015, temps partiel (Q = 15, S = 38)", (o['code_travailleur'], o['temps_plein'], o['Q']), ('015', False, 15.0))
check("Prestations: code 1 = 51 j (46 prestes + 5 garantis), code 2 = 2 j, code 10 = 5 j, code 11 = 8 j",
      {k: v['jours'] for k, v in o['prestations'].items()}, {1: 51, 2: 2, 10: 5, 11: 8})
check("... en heures pour un temps partiel", o['prestations'][1]['heures'], 153.0)
check("Aucune alerte: le detail des fiches correspond au calendrier", t['alertes'], [])
check("Remuneration a 100 %: 153 h x 15,00 = 2.295,00 (indemnites de maladie des jours 8 a 30 non declarees)", o['remunerations'][1], 2295.0)
check("Base des cotisations a 108 %: 2.478,60", o['base'], 2478.60)
check("Cotisation vacances 253 presente", any(x[0] == '253' for x in o['cotisations']))
# S: H = 153 (codes 1) ; µ: Z = 153 + 6 (code 2) = 159 -> 159/494 = 0,32
check("Reductions: H = 153 h pour S, µ = 159/494 = 0,32", (o['reductions']['J'], o['reductions']['mu']), (153.0, 0.32))
C_STU = {'id': 31, 'type_contrat': 'STU', 'cp_key': 'CP 200', 'date_debut': date(2026,7,1), 'date_fin': date(2026,8,31),
         'statut': 'archive', 'heures_jour': 7.6, 'jours_semaine': 5, 'heures_semaine': 38.0}
def fiche_etudiant(debut):
    return fiche(calculer_fiche_paie('S', 'T', 'n', 'a', 'BE', date(2006,1,1), date(2026,7,1), 'S', 'a', 'b', 'r', 'CP 200',
        'Etudiant', 13.0, heures_semaine=38.0, heures_jour=7.6, jours_semaine=5, type_contrat='STU', is_etudiant=True,
        jours_prestes=10, heures_prestees=76.0, cheques_repas=False, categorie_employeur='010',
        periode_debut=debut, periode_fin=fin_mois(debut)), C_STU, debut)
C_CDI = dict(C_EMP, id=32, date_debut=date(2026,9,1))
doc_s = aide_dmfa(DOSSIER, 2026, 3, [{'travailleur': EMP, 'contrats': [C_STU, C_CDI],
                                      'fiches': [fiche_etudiant(MOIS[0]), fiche_etudiant(MOIS[1])], 'jours': []}])
occs = doc_s['travailleurs'][0]['occupations']
check("Etudiant puis CDI dans le trimestre: deux lignes, codes 841 (etudiant employe) et 495",
      [x['code_travailleur'] for x in occs], ['841', '495'])
check("Etudiant: remuneration 1.976,00 et 152 heures (bloc 90003)", (occs[0]['W'], occs[0]['heures_etudiant']), (1976.0, 152.0))
check("Etudiant: cotisation de solidarite 2,71 % + 5,43 % (taux TechLib, Fonds amiante compris) = 160,85 (recalcul)", occs[0]['cotisations_recalcul'], 160.85)
check("Etudiant: ni reduction ni CSS", (occs[0]['reductions'], occs[0]['css']), ({}, 0.0))
check("CDI commence le 01/09 sans fiche: alerte de fiche manquante",
      any('Pas de fiche de paie pour 09/2026' in a for a in doc_s['travailleurs'][0]['alertes']))
check("Contrat etudiant archive sans fiche: non repris", aide_dmfa(DOSSIER, 2026, 3, [{'travailleur': OUV, 'contrats': [dict(C_STU, cp_key='CP 140.03')],
      'fiches': [], 'jours': []}])['travailleurs'], [])   # archive sans fiche: non repris
from dmfa import CODES_TRAVAILLEUR
check("Codes travailleur", CODES_TRAVAILLEUR, {'ouvrier': '015', 'employe': '495', 'etudiant_ouvrier': '840', 'etudiant_employe': '841'})

print(); print("=" * 70); print("PAGE ET PDF"); print("=" * 70)
from jinja2 import Environment, FileSystemLoader
import branding
RACINE = os.path.dirname(os.path.abspath(__file__))
SORTIE = sys.argv[1] if len(sys.argv) > 1 else None
env = Environment(loader=FileSystemLoader(os.path.join(RACINE, 'templates')))
env.filters['basename'] = lambda p: os.path.basename(p) if p else ''
class Requete:
    def __init__(self, path): self.path = path; self.form = {}; self.args = {}
complet = aide_dmfa(DOSSIER, 2026, 3, [
    {'travailleur': EMP, 'contrats': [C_EMP], 'fiches': prime, 'jours': [(date(2026,8,10), 'CT', 0)]},
    {'travailleur': OUV, 'contrats': [C_OUV], 'fiches': fiches_o, 'jours': [j for c in cals for j in c]}])
h = env.get_template('aide_dmfa.html').render(
    request=Requete('/dossier/7/aide-dmfa'), marque=branding.get_branding(), statique=branding.url_statique,
    session={'user_id': 1, 'user_nom': 'Utilisateur'}, tenant={}, tous_les_dossiers=[DOSSIER], dossiers_archives=[],
    dossier=DOSSIER, dossier_actif=DOSSIER, document=complet)
check("Page: titre, choix du trimestre, export PDF", 'Aide à la DmfA — 2026/3' in h and 'name="trimestre"' in h and 'data-pdf=' in h)
check("Page: codes travailleur, prestation, remuneration et reduction", all(x in h for x in
      ('code travailleur 495', 'code travailleur 015', 'Prestations (bloc 90018)', 'Rémunérations (bloc 90019)', '>3000<', '>0001<', '>856<')))
check("Page: alerte « code à déterminer » et totaux de l'employeur", 'Code à déterminer' in h and 'MONTANT NET DÛ' in h)
check("Menu du dossier: lien Aide DmfA", 'href="/dossier/7/aide-dmfa"' in h and 'btn-back' not in
      io.open(os.path.join(RACINE, 'templates', 'aide_dmfa.html'), encoding='utf-8').read())
h2 = env.get_template('modifier_dossier.html').render(
    request=Requete('/dossier/7/modifier'), marque=branding.get_branding(), statique=branding.url_statique,
    session={'user_id': 1, 'user_nom': 'Utilisateur'}, tenant={}, tous_les_dossiers=[DOSSIER], dossiers_archives=[],
    dossier=dict(DOSSIER, taux_provision_pecule_employes=18.8, date_activation_rsz=None), dossier_actif=DOSSIER,
    categories_onss=[], codes_importance=[], codes_ffe=[])
check("Dossier: champ « numéro d'unité d'établissement » pre-rempli", 'name="numero_unite_etablissement"' in h2 and 'value="2.123.456.789"' in h2)
ctx_t = dict(request=Requete('/travailleur/2/modifier'), marque=branding.get_branding(), statique=branding.url_statique,
             session={'user_id': 1, 'user_nom': 'Utilisateur'}, tenant={}, tous_les_dossiers=[DOSSIER], dossiers_archives=[],
             dossier=DOSSIER, dossier_actif=DOSSIER, cp_keys=[])
h3 = env.get_template('modifier_travailleur.html').render(travailleur=dict(EMP, dossier_id=7), titulaire_premier_engagement=None, **ctx_t)
check("Fiche du travailleur designe: case « premier engagement » cochee",
      'name="premier_engagement_travailleur"' in h3 and h3.split('name="premier_engagement_travailleur"')[1].split('>')[0].strip().endswith('checked'))
h3 = env.get_template('modifier_travailleur.html').render(travailleur=dict(NON, dossier_id=7),
                                                          titulaire_premier_engagement='Camille Exemple', **ctx_t)
check("Autre travailleur: case non cochee, et le travailleur deja designe est indique",
      'checked' not in h3.split('name="premier_engagement_travailleur"')[1].split('>')[0] and 'Actuellement désigné dans ce dossier : Camille Exemple' in h3)
check("Nouveau travailleur: la case est proposee", 'name="premier_engagement_travailleur"' in
      env.get_template('nouveau_travailleur.html').render(titulaire_premier_engagement=None, **ctx_t))
from pdf_dmfa import generer_pdf_dmfa
pdf = generer_pdf_dmfa(complet)
check("PDF genere", pdf[:4] == b'%PDF' and len(pdf) > 3000)
try:
    from pypdf import PdfReader
    texte = ' '.join((pg.extract_text() or '') for pg in PdfReader(io.BytesIO(pdf)).pages)
    check("PDF: memes donnees que la page (codes, totaux, mentions de l'editeur)",
          all(x in texte for x in ('Aide à la DmfA', '3000', 'MONTANT NET', 'Global Smart Services')))
except ImportError:
    print("(pypdf absent: contenu du PDF non relu)")
if SORTIE:
    io.open(os.path.join(SORTIE, 'apercu_aide_dmfa.html'), 'w', encoding='utf-8').write(h.replace('"/static/', '"../static/'))
    io.open(os.path.join(SORTIE, 'exemple_aide_dmfa.pdf'), 'wb').write(pdf)

print(); print("=" * 70)
if ECHECS:
    print(f"❌ {len(ECHECS)} TEST(S) ECHOUE(S): {ECHECS}"); sys.exit(1)
print("✅ TOUS LES TESTS PASSENT -- aide a la DmfA.")
