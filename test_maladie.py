# -*- coding: utf-8 -*-
"""
test_maladie.py -- DuxSalary
Maladie et salaire garanti (salaire_garanti.py + moteur): un test par cas.
Lancer: python3 test_maladie.py   -- doit afficher TOUS LES TESTS PASSENT
Les montants attendus sont calcules a la main a partir des regles sourcees dans
parametres_dates.py (aucune fiche reelle de maladie disponible a ce jour).
"""
import sys, json
from datetime import date, timedelta
from salaire_garanti import (regime_salaire_garanti, debut_occupation_ininterrompue, ventiler_episodes,
                             tranches_par_date, indemnites_du_mois, jours_a_marquer, regles_affichees, resume_periodes)
from moteur_paie import calculer_fiche_paie
from documents_charges import valeurs_fiche
ECHECS = []

def check(label, obtenu, attendu=True, tol=0.01):
    nombres = isinstance(obtenu, (int, float)) and isinstance(attendu, (int, float)) \
        and not isinstance(obtenu, bool) and not isinstance(attendu, bool)
    ok = abs(obtenu - attendu) <= tol if nombres else obtenu == attendu
    print(f"{'✅' if ok else '❌'} {label}: obtenu={obtenu} attendu={attendu}")
    if not ok: ECHECS.append(label)

def ep(debut, fin, id=1, autre_cause=False, type='maladie'):
    return {'id': id, 'date_debut': debut, 'date_fin': fin, 'type': type, 'autre_cause': autre_cause}

def tranches(v):
    """'MG:7 M2:7 MC:16 MM:3' pour un episode ventile."""
    return ' '.join(f"{t}:{n}" for t, n in v['compte'].items() if n)

def bornes(v, tranche):
    js = [j['date'] for j in v['jours'] if j['tranche'] == tranche]
    return (min(js), max(js)) if js else None

ENTREE = date(2024, 1, 1)
HORIZON = date(2026, 12, 31)

print("=" * 70); print("REGIME APPLICABLE (loi du 03/07/1978, art. 52, 70 et 71)"); print("=" * 70)
check("Ouvrier CDI", regime_salaire_garanti(True, 'CDI', ENTREE, None), 'ouvrier')
check("Employe CDI", regime_salaire_garanti(False, 'CDI', ENTREE, None), 'employe')
check("Employe CDD de 2 mois et demi: regime court (art. 71)",
      regime_salaire_garanti(False, 'CDD', date(2026,9,1), date(2026,11,15)), 'employe_court')
check("Employe CDD de trois mois exactement (01/09 - 30/11): regime de 30 jours (art. 70)",
      regime_salaire_garanti(False, 'CDD', date(2026,9,1), date(2026,11,30)), 'employe')
check("Employe CDD un jour de moins que trois mois (01/09 - 29/11): regime court",
      regime_salaire_garanti(False, 'CDD', date(2026,9,1), date(2026,11,29)), 'employe_court')
check("Etudiant: non gere", regime_salaire_garanti(True, 'STU', date(2026,7,1), date(2026,8,31)), None)
try:
    ventiler_episodes([ep(date(2026,7,6), date(2026,7,8))], None, ENTREE, HORIZON); leve = False
except ValueError:
    leve = True
check("Etudiant: erreur claire plutot qu'un calcul devine", leve, True)

print(); print("=" * 70); print("EMPLOYE -- 30 jours calendrier a 100 %, puis mutuelle"); print("=" * 70)
v = ventiler_episodes([ep(date(2026,9,7), date(2026,10,16))], 'employe', ENTREE, HORIZON)[0]
check("40 jours: 30 garantis + 10 mutuelle", tranches(v), 'MG:30 MM:10')
check("Dernier jour garanti = 30e jour calendrier (06/10)", bornes(v, 'MG')[1], date(2026,10,6))
check("Alerte: passage a la mutuelle le 07/10", any('07/10/2026' in a and 'mutuelle' in a for a in v['alertes']), True)
v = ventiler_episodes([ep(date(2026,9,7), date(2026,9,9))], 'employe', date(2026,9,7), HORIZON)[0]
check("Employe malade le jour de son entree: garanti sans condition d'anciennete", tranches(v), 'MG:3')

print(); print("=" * 70); print("OUVRIER -- 7 jours a 100 %, 2e semaine, complement jusqu'au 30e jour"); print("=" * 70)
v = ventiler_episodes([ep(date(2026,9,7), date(2026,10,16))], 'ouvrier', ENTREE, HORIZON)[0]
check("40 jours: 7 + 7 + 16 + 10", tranches(v), 'MG:7 M2:7 MC:16 MM:10')
check("Jours 1 a 7 (07/09 - 13/09)", bornes(v, 'MG'), (date(2026,9,7), date(2026,9,13)))
check("Jours 8 a 14 (14/09 - 20/09)", bornes(v, 'M2'), (date(2026,9,14), date(2026,9,20)))
check("Jours 15 a 30 (21/09 - 06/10)", bornes(v, 'MC'), (date(2026,9,21), date(2026,10,6)))
check("Mutuelle des le 31e jour (07/10)", bornes(v, 'MM')[0], date(2026,10,7))
check("Pas de jour de carence: le premier jour est paye", v['jours'][0]['tranche'], 'MG')
check("Periodes affichees: 4", len(resume_periodes(v)), 4)

print(); print("=" * 70); print("EMPLOYE ENGAGE POUR MOINS DE TROIS MOIS (art. 71 + CCT 13bis)"); print("=" * 70)
v = ventiler_episodes([ep(date(2026,10,5), date(2026,10,25))], 'employe_court', date(2026,9,1), HORIZON)[0]
check("21 jours: 7 + 7 + 7", tranches(v), 'MG:7 M2:7 MC:7')
v = ventiler_episodes([ep(date(2026,9,14), date(2026,9,18))], 'employe_court', date(2026,9,1), HORIZON)[0]
check("Moins d'un mois d'anciennete: mutuelle", tranches(v), 'MM:5')

print(); print("=" * 70); print("OUVRIER -- MOINS D'UN MOIS D'ANCIENNETE (art. 52 § 1er)"); print("=" * 70)
v = ventiler_episodes([ep(date(2026,9,28), date(2026,10,10))], 'ouvrier', date(2026,9,1), HORIZON)[0]
check("Entre le 01/09, malade du 28/09 au 10/10: 3 jours sans droit, puis jours 4 a 7 garantis, puis 2e semaine",
      tranches(v), 'MG:4 M2:6 MM:3')
check("Le droit s'ouvre le 01/10 (un mois atteint), au rang 4", (bornes(v, 'MG')[0], v['jours'][3]['rang']), (date(2026,10,1), 4))
check("Alerte d'anciennete", any("Moins d'un mois d'ancienneté" in a and '01/10/2026' in a for a in v['alertes']), True)
check("Pas d'alerte « fin du salaire garanti » pour ces 3 jours", any('Fin du salaire garanti' in a for a in v['alertes']), False)
contrats = [{'date_debut': date(2026,6,1), 'date_fin': date(2026,8,31)},
            {'date_debut': date(2026,9,1), 'date_fin': None}]
check("Contrats qui se suivent: anciennete depuis le premier", debut_occupation_ininterrompue(contrats, date(2026,9,28)), date(2026,6,1))
contrats[0]['date_fin'] = date(2026,8,28)
check("Interruption entre deux contrats: anciennete depuis le second", debut_occupation_ininterrompue(contrats, date(2026,9,28)), date(2026,9,1))
check("Aucun contrat a cette date", debut_occupation_ininterrompue(contrats, date(2026,5,1)), None)

print(); print("=" * 70); print("RECHUTE -- 8 semaines depuis le 01/01/2026, 14 jours avant (art. 52 § 2 et 73 § 1er)"); print("=" * 70)
A = ep(date(2026,3,2), date(2026,3,11), id=1)                      # 10 jours
vs = ventiler_episodes([A, ep(date(2026,4,20), date(2026,4,30), id=2)], 'ouvrier', ENTREE, HORIZON)
check("2026: nouvelle incapacite 40 jours apres la fin -> rechute, le decompte reprend au jour 11",
      (vs[1]['rechute_de'], vs[1]['jours'][0]['rang'], tranches(vs[1])), (1, 11, 'M2:4 MC:7'))
check("Alerte de rechute avec la source", any('Rechute' in a and '8 semaines' in a and '19/12/2025' in a for a in vs[1]['alertes']), True)
vs = ventiler_episodes([A, ep(date(2026,4,20), date(2026,4,30), id=2, autre_cause=True)], 'ouvrier', ENTREE, HORIZON)
check("Autre maladie attestee par certificat: nouveau salaire garanti", (vs[1]['rechute_de'], tranches(vs[1])), (None, 'MG:7 M2:4'))
check("... et rappel du certificat", any('certificat' in i for i in vs[1]['infos']), True)
vs = ventiler_episodes([A, ep(date(2026,5,6), date(2026,5,8), id=2)], 'ouvrier', ENTREE, HORIZON)
check("56 jours apres la fin (11/03 -> 06/05): encore une rechute", vs[1]['rechute_de'], 1)
vs = ventiler_episodes([A, ep(date(2026,5,7), date(2026,5,9), id=2)], 'ouvrier', ENTREE, HORIZON)
check("57 jours apres la fin: nouveau salaire garanti", (vs[1]['rechute_de'], tranches(vs[1])), (None, 'MG:3'))
A25 = ep(date(2025,3,3), date(2025,3,12), id=1)
vs = ventiler_episodes([A25, ep(date(2025,4,21), date(2025,4,30), id=2)], 'ouvrier', ENTREE, HORIZON)
check("2025: 40 jours apres la fin -> pas une rechute (delai de 14 jours)", (vs[1]['rechute_de'], tranches(vs[1])), (None, 'MG:7 M2:3'))
vs = ventiler_episodes([A25, ep(date(2025,3,20), date(2025,3,25), id=2)], 'ouvrier', ENTREE, HORIZON)
check("2025: 8 jours apres la fin -> rechute", (vs[1]['rechute_de'], vs[1]['jours'][0]['rang']), (1, 11))
check("2025: pourcentages signales comme non verifies pour l'epoque", any('non vérifiés' in a for a in vs[1]['alertes']), True)
vs = ventiler_episodes([ep(date(2026,3,2), date(2026,3,26), id=1), ep(date(2026,4,6), date(2026,4,20), id=2)],
                       'employe', ENTREE, HORIZON)
check("Employe: rechute apres 25 jours -> solde de 5 jours garantis, puis mutuelle", tranches(vs[1]), 'MG:5 MM:10')
vs = ventiler_episodes([ep(date(2026,3,2), date(2026,3,6), id=1), ep(date(2026,3,16), date(2026,3,18), id=2),
                        ep(date(2026,4,20), date(2026,4,22), id=3)], 'ouvrier', ENTREE, HORIZON)
check("Rechutes en chaine: 5 + 3 jours consommes, la troisieme reprend au jour 9", vs[2]['jours'][0]['rang'], 9)
vs = ventiler_episodes([ep(date(2026,3,2), None, id=1)], 'ouvrier', ENTREE, date(2026,3,31))
check("Incapacite sans date de fin: calculee jusqu'a l'horizon, avec alerte",
      (len(vs[0]['jours']), any('sans date de fin' in a for a in vs[0]['alertes'])), (30, True))

print(); print("=" * 70); print("CHEVAUCHEMENT DE DEUX MOIS -- ouvrier, du 24/09 au 09/10/2026"); print("=" * 70)
v = ventiler_episodes([ep(date(2026,9,24), date(2026,10,9))], 'ouvrier', ENTREE, HORIZON)[0]
par_date = tranches_par_date([v])
check("Septembre: 7 jours garantis (24/09 - 30/09)", sum(1 for d, j in par_date.items() if d.month == 9 and j['tranche'] == 'MG'), 7)
check("Octobre: 2e semaine du 01/10 au 07/10, complement les 08 et 09/10",
      ''.join(par_date[date(2026,10,n)]['tranche'] for n in range(1, 10)), 'M2' * 7 + 'MC' * 2)
marques, feries = jours_a_marquer(v, jours_semaine=5)
check("Calendrier: seuls les jours du lundi au vendredi sont marques (12 sur 16)", len(marques), 12)
marques, feries = jours_a_marquer(ventiler_episodes([ep(date(2026,10,26), date(2026,11,3))], 'ouvrier', ENTREE, HORIZON)[0],
                                  jours_feries=[date(2026,11,2)])
check("Calendrier: un jour ferie pendant l'incapacite n'est pas ecrase, il est signale", (len(marques), feries), (6, [date(2026,11,2)]))

print(); print("=" * 70); print("MONTANTS -- ouvrier 15,00 EUR/h, 7,6 h/j, octobre 2026"); print("=" * 70)
OCT = dict(periode_debut=date(2026,10,1), periode_fin=date(2026,10,31))
def jours_oct(v, heures=7.6, mois=10):
    return [{'date': j['date'], 'tranche': j['tranche'], 'heures': heures}
            for j in jours_a_marquer(v, 5)[0] if j['date'].month == mois]
def ouvrier(jours_prestes, incapacite=None, **kw):
    return calculer_fiche_paie('A','B','n','a','BE',date(1990,1,1),ENTREE,'X','a','b','r','CP 140.03','Chauffeur',15.0,
        heures_semaine=38.0, heures_jour=7.6, jours_semaine=5, type_contrat='CDI', rgpt_actif=False, cheques_repas=False,
        jours_prestes=jours_prestes, heures_prestees=round(jours_prestes * 7.6, 2), incapacite=incapacite, **OCT, **kw)
js = jours_oct(v)
m = indemnites_du_mois('ouvrier', js, salaire_horaire=15.0, heures_jour=7.6, jours_semaine=5)
check("2e semaine: 5 jours ouvres x 7,6 h x 15 x 85,88 % = 489,52", m['compte']['M2']['montant'], 489.52)
check("Complement: 2 jours x 7,6 h x 15 x 25,88 % = 59,01", m["compte"]["MC"]["montant"], 59.01)
sans = ouvrier(15)
r = ouvrier(15, {'regime': 'ouvrier', 'jours': js, 'infos': regles_affichees('ouvrier', date(2026,10,1)), 'alertes': v['alertes']})
check("Brut ONSS inchange: les jours 8 a 30 ne sont pas soumis", r['brut_onss'], sans['brut_onss'])
check("ONSS personnel inchange", r['onss_travailleur'], sans['onss_travailleur'])
check("Bonus a l'emploi inchange (jours 8 a 30 hors J/H)", r['bonus_emploi'], sans['bonus_emploi'])
check("ONSS patronal inchange (hors µ)", r['onss_patronal'], sans['onss_patronal'])
check("Imposable = imposable sans maladie + 548,53", r['brut_imposable'], round(sans['brut_imposable'] + 548.53, 2))
check("Precompte plus eleve (indemnites imposables)", r['precompte'] < sans['precompte'], True)
check("Cout employeur + 548,53", r['cout_employeur'], round(sans['cout_employeur'] + 548.53, 2))
check("Net = imposable - precompte - CSS", r['salaire_net'], round(r['brut_imposable'] + r['precompte'] - r['css'], 2))
check("Deux lignes hors ONSS sur la fiche", [l['tranche'] for l in r['lignes_hors_onss']], ['M2', 'MC'])
check("Bloc « Maladie et salaire garanti » dans le detail du calcul, avec les regles",
      any(b['titre'] == 'Maladie et salaire garanti' and any('85,88' in l['libelle'] for l in b['lignes']) for b in r['detail_calcul']), True)
check("Alerte precompte a recouper", any('barème ordinaire du précompte' in a for a in r['alertes_calcul']), True)
check("Sans maladie: aucun bloc ni alerte de maladie",
      (any(b['titre'] == 'Maladie et salaire garanti' and b['lignes'] for b in sans['detail_calcul']),
       any('Maladie' in a for a in sans['alertes_calcul'])), (False, False))
vf = valeurs_fiche(dict(r))
check("Enregistrement: indemnites de maladie dans le detail hors ONSS de la fiche",
      round(sum(i['montant'] for i in json.loads(vf['indemnites']) if 'maladie' in i['libelle'].lower()), 2), 548.53)

# Premiere semaine: remuneration ordinaire
v1 = ventiler_episodes([ep(date(2026,10,5), date(2026,10,9))], 'ouvrier', ENTREE, HORIZON)[0]
r = ouvrier(15, {'regime': 'ouvrier', 'jours': jours_oct(v1), 'infos': [], 'alertes': []})
avec20 = ouvrier(20)
check("5 jours garantis a 100 %: meme brut ONSS que 20 jours prestes (15 + 5)", r['brut_onss'], avec20['brut_onss'])
check("... meme ONSS, meme bonus a l'emploi, meme net", (r['onss_net'], r['bonus_emploi'], r['salaire_net']),
      (avec20['onss_net'], avec20['bonus_emploi'], avec20['salaire_net']))
check("... meme ONSS patronal (jours garantis dans µ)", r['onss_patronal'], avec20['onss_patronal'])
check("Ligne « Salaire garanti maladie (100 %) »: 38 h x 15 = 570,00",
      next(l['montant'] for l in r['lignes_salaire'] if 'Salaire garanti' in l['libelle']), 570.0)

# Mutuelle: rien
vm = ventiler_episodes([ep(date(2026,8,3), date(2026,10,9))], 'ouvrier', ENTREE, HORIZON)[0]
r = ouvrier(15, {'regime': 'ouvrier', 'jours': jours_oct(vm), 'infos': [], 'alertes': []})
check("Jours a charge de la mutuelle: rien a payer, fiche identique a 15 jours prestes",
      (r['brut_onss'], r['salaire_net'], r['cout_employeur']), (sans['brut_onss'], sans['salaire_net'], sans['cout_employeur']))
check("... mais les 7 jours sont comptes", r['incapacite']['compte']['MM']['jours'], 7)

print(); print("=" * 70); print("MONTANTS -- employe au mois, octobre 2026 (22 jours ouvrables)"); print("=" * 70)
def employe(mensuel, incapacite=None, type_contrat='CDI', **kw):
    return calculer_fiche_paie('A','B','n','a','BE',date(1990,1,1),ENTREE,'X','a','b','r','CP 200','Classe A',0.0,
        salaire_mensuel_fixe=mensuel, heures_semaine=38.0, heures_jour=7.6, jours_semaine=5, type_contrat=type_contrat,
        cheques_repas=False, jours_prestes=22, heures_prestees=167.2, incapacite=incapacite, **OCT, **kw)
sans = employe(3000.0)
ve = ventiler_episodes([ep(date(2026,10,5), date(2026,10,16))], 'employe', ENTREE, HORIZON)[0]
r = employe(3000.0, {'regime': 'employe', 'jours': jours_oct(ve), 'infos': [], 'alertes': []})
check("Employe, 10 jours garantis: remuneration maintenue, fiche identique",
      (r['brut_onss'], r['salaire_net'], r['onss_patronal'], r['cout_employeur']),
      (sans['brut_onss'], sans['salaire_net'], sans['onss_patronal'], sans['cout_employeur']))
# Cas reel du 02/10/2026 (dossier de categorie 010): employe en CDI a partir du 01/09/2026, malade des le 01/09.
# Loi du 03/07/1978, art. 70: remuneration maintenue 30 jours, sans condition d'anciennete.
c_j1 = {'id': 1, 'type_contrat': 'CDI', 'cp_key': 'CP 200', 'date_debut': date(2026,9,1), 'date_fin': None}
from salaire_garanti import contexte_incapacites as _ctx
inc_j1 = _ctx([{'id': 1, 'date_debut': date(2026,9,1), 'date_fin': None, 'type_incapacite': 'maladie', 'autre_cause': False}],
              [c_j1], c_j1, False, date(2026,9,30))
v_j1 = inc_j1['ventilation'][0]
check("CDI et maladie le meme jour (01/09/2026): regime employe, 30 jours garantis, aucun a la mutuelle",
      (inc_j1['regime'], tranches(v_j1)), ('employe', 'MG:30'))
SEPT = dict(periode_debut=date(2026,9,1), periode_fin=date(2026,9,30))
def employe_sept(incapacite, jours_prestes):
    return calculer_fiche_paie('A','B','n','a','BE',date(1990,1,1),date(2026,9,1),'X','a','b','r','CP 200','Classe A',0.0,
        salaire_mensuel_fixe=2500.0, heures_semaine=38.0, heures_jour=7.6, jours_semaine=5, type_contrat='CDI',
        categorie_employeur='010', cheques_repas=False, jours_prestes=jours_prestes, heures_prestees=jours_prestes * 7.6,
        incapacite=incapacite, **SEPT)
r = employe_sept({'regime': inc_j1['regime'], 'jours': jours_oct(v_j1, mois=9), 'infos': [], 'alertes': v_j1['alertes']}, 0)
ref = employe_sept(None, 22)
check("... mois entier de maladie, aucun jour preste: brut = salaire mensuel complet (2.500,00), pas 0", r['brut_onss'], 2500.0)
check("... meme net, meme ONSS patronal et meme cout qu'un mois preste normalement",
      (r['salaire_net'], r['onss_patronal'], r['cout_employeur']), (ref['salaire_net'], ref['onss_patronal'], ref['cout_employeur']))
check("... 22 jours ouvres comptes en salaire garanti", r['incapacite']['compte']['MG']['jours'], 22)
# Meme situation sous une CP d'ouvriers: pas de droit avant un mois d'anciennete, et la page le dit
c_ouv = dict(c_j1, cp_key='CP 140.03')
inc_ouv = _ctx([{'id': 1, 'date_debut': date(2026,9,1), 'date_fin': None, 'type_incapacite': 'maladie', 'autre_cause': False}],
               [c_ouv], c_ouv, True, date(2026,9,30))
check("Ouvrier malade des son premier jour: 30 jours a la mutuelle, explique clairement",
      (tranches(inc_ouv['ventilation'][0]),
       any("pas de salaire garanti" in a and "à charge de la mutuelle" in a for a in inc_ouv['ventilation'][0]['alertes'])),
      ('MM:30', True))
ve = ventiler_episodes([ep(date(2026,8,27), date(2026,10,2))], 'employe', ENTREE, HORIZON)[0]   # 30e jour = 25/09
r = employe(3000.0, {'regime': 'employe', 'jours': jours_oct(ve), 'infos': [], 'alertes': []})
check("Employe au-dela de 30 jours: 2 jours de mutuelle retires, brut = 3000 - 2 x 3000/22 = 2.727,27", r['brut_onss'], 2727.27)
check("... aucune indemnite a charge de l'employeur", r['indemnites_maladie_hors_onss'], 0.0)
vc = ventiler_episodes([ep(date(2026,9,24), date(2026,10,9))], 'employe_court', date(2026,8,1), HORIZON)[0]
r = employe(2200.0, {'regime': 'employe_court', 'jours': jours_oct(vc), 'infos': [], 'alertes': []}, type_contrat='CDD')
check("Employe < 3 mois: 7 jours retires du brut (2200 - 7 x 100 = 1.500,00)", r['brut_onss'], 1500.0)
check("... 2e semaine 5 x 100 x 86,93 % = 434,65", r['lignes_hors_onss'][0]['montant'], 434.65)
check("... complement 2 x 100 x 26,93 % = 53,86", r['lignes_hors_onss'][1]['montant'], 53.86)
check("... imposable = brut - ONSS net + 488,51", r['brut_imposable'], round(1500.0 + r['onss_net'] + 488.51, 2))

print(); print("=" * 70); print("PLAFOND AMI -- 189,3583 EUR/jour (6 j) au 01/09/2026, soit 1.136,15 EUR/semaine"); print("=" * 70)
m = indemnites_du_mois('employe_court', [{'date': date(2026,10,8), 'tranche': 'MC', 'heures': 7.6}],
                       salaire_mensuel=6000.0, jours_ouvrables_mois=22)
# 6000 x 12/52 = 1384,62/sem. > 1136,15: part sous plafond 82,0542 %
# 272,73 x (0,820542 x 26,93 % + 0,179458 x 86,93 %) = 102,81
check("Salaire de 6.000 EUR/mois: complement d'un jour = 102,81 (26,93 % sous plafond + 86,93 % au-dessus)", m['compte']['MC']['montant'], 102.81)
check("... alerte: plafond applique (montant confirme sur le PDF INAMI: plus de mention « a confirmer »)",
      (any('supérieure au plafond AMI' in a for a in m['alertes']), any('à confirmer' in a for a in m['alertes'])), (True, False))
from parametres_dates import get_plafond_ami
check("Plafonds INAMI dates: 183,1311 (01/01/2026), 186,7916 (01/03/2026), 189,3583 (01/09/2026)",
      [get_plafond_ami(d)['plafond_jour_6j'] for d in (date(2026,2,28), date(2026,3,1), date(2026,8,31), date(2026,9,1))],
      [183.1311, 186.7916, 186.7916, 189.3583])
m = indemnites_du_mois('employe_court', [{'date': date(2026,10,8), 'tranche': 'MC', 'heures': 7.6}],
                       salaire_mensuel=4900.0, jours_ouvrables_mois=22)
check("Salaire de 4.900 EUR/mois (< 189,3583 x 26 = 4.923,32): tout sous plafond, 222,73 x 26,93 % = 59,98, sans alerte",
      (m['compte']['MC']['montant'], m['alertes']), (59.98, []))
m = indemnites_du_mois('ouvrier', [{'date': date(2025,10,8), 'tranche': 'MC', 'heures': 8.0}], salaire_horaire=20.0)
check("Periode sans plafond charge (2025): alerte, pas de repli silencieux", any('non chargé' in a for a in m['alertes']), True)

print(); print("=" * 70); print("AFFICHAGE DANS L'OUTIL -- regles, suivi et alertes (pages, calendrier, fiche)"); print("=" * 70)
# python test_maladie.py outputs  -> ecrit aussi les apercus et un PDF d'exemple (donnees fictives)
import os, io
from jinja2 import Environment, FileSystemLoader
import branding
from salaire_garanti import contexte_incapacites, TYPES_INCAPACITE
from social_belgique import CODES_JOURNALIERS
RACINE = os.path.dirname(os.path.abspath(__file__))
SORTIE = sys.argv[1] if len(sys.argv) > 1 else None
env = Environment(loader=FileSystemLoader(os.path.join(RACINE, 'templates')))
env.filters['basename'] = lambda p: os.path.basename(p) if p else ''
class Requete:
    def __init__(self, path): self.path = path; self.form = {}; self.args = {}
dossier = {'id': 7, 'nom': 'Société Fictive SRL', 'bce': '0000.000.000', 'rsz': '000-0000000-00', 'cp_principale': 'CP 140.03'}
travailleur = {'id': 3, 'prenom': 'Camille', 'nom': 'Exemple', 'dossier_id': 7}
commun = dict(marque=branding.get_branding(), statique=branding.url_statique, session={'user_id': 1, 'user_nom': 'Utilisateur'},
              tenant={}, tous_les_dossiers=[dossier], dossiers_archives=[], dossier=dossier, dossier_actif=dossier, travailleur=travailleur)
def rendre(gabarit, chemin, **ctx):
    html = env.get_template(gabarit).render(request=Requete(chemin), **dict(commun, **ctx))
    if SORTIE:
        io.open(os.path.join(SORTIE, 'apercu_' + gabarit.replace('.html', '') + '_maladie.html'), 'w', encoding='utf-8').write(
            html.replace('"/static/', '"../static/'))
    return html

contrat = {'id': 1, 'type_contrat': 'CDI', 'cp_key': 'CP 140.03', 'date_debut': ENTREE, 'date_fin': None,
           'heures_jour': 7.6, 'jours_semaine': 5}
episodes = [{'id': 1, 'date_debut': date(2026,8,10), 'date_fin': date(2026,8,19), 'type_incapacite': 'maladie', 'autre_cause': False, 'note': None},
            {'id': 2, 'date_debut': date(2026,9,24), 'date_fin': date(2026,10,9), 'type_incapacite': 'maladie', 'autre_cause': False,
             'note': 'Certificat du 24/09'}]
inc = contexte_incapacites(episodes, [contrat], contrat, True, date(2026,10,31))
check("Contexte: regime ouvrier, 2 episodes ventiles, le second est une rechute (36 jours apres le 19/08)",
      (inc['regime'], len(inc['ventilation']), inc['ventilation'][1]['rechute_de']), ('ouvrier', 2, 1))
check("Rechute: 10 jours deja consommes -> reprise au jour 11 (2e semaine puis complement)",
      [(p['tranche'], p['jours']) for p in inc['ventilation'][1]['periodes']], [('M2', 4), ('MC', 12)])
h = rendre('incapacites.html', '/travailleur/3/incapacites', inc=inc, messages=[], erreur=None, types=TYPES_INCAPACITE,
           dimonas=[{'id': 5, 'type_dimona': 'OTH', 'date_debut': ENTREE, 'date_fin': None}], aujourd_hui=date(2026,10,2))
check("Page « Maladie »: regles avec leurs sources", 'art. 52 § 1er' in h and '85,88 %' in h and 'Instructions ONSS 2026/3' in h)
check("Page « Maladie »: suivi par tranche avec les dates", 'inc-code inc-M2' in h and '24/09' in h and 'Rechute — reprise au jour 11' in h)
check("Page « Maladie »: alerte de rechute et formulaire d'encodage", 'pas de nouveau salaire garanti' in h and 'name="autre_cause"' in h)
check("Page « Maladie »: fil d'Ariane et retour vers le travailleur", 'Retour à Camille Exemple' in h and 'btn-back' not in
      io.open(os.path.join(RACINE, 'templates', 'incapacites.html'), encoding='utf-8').read())
inc_etu = contexte_incapacites(episodes[:1], [dict(contrat, type_contrat='STU')], dict(contrat, type_contrat='STU'), True, date(2026,10,31))
check("Etudiant: alerte « non gere », aucun jour ventile",
      (inc_etu['ventilation'], any('étudiant' in a.lower() for a in inc_etu['alertes'])), ([], True))
check("Sans contrat: alerte", any('Aucun contrat' in a for a in contexte_incapacites(episodes, [], None, False, HORIZON)['alertes']), True)

du_mois = [v for v in inc['ventilation'] if v['fin'] >= date(2026,10,1)]
par_date = inc['par_date']
jours_cal = []
for n in range(1, 32):
    d = date(2026,10,n)
    code = 'WE' if d.weekday() >= 5 else (par_date[d]['tranche'] if d in par_date else 'P')
    info = CODES_JOURNALIERS[code]
    jours_cal.append({'jour': n, 'date': str(d), 'hors_dimona': False, 'weekend': d.weekday() >= 5, 'code': code,
                      'heures': 0 if code == 'WE' else 7.6, 'couleur': info['couleur'], 'texte': info['texte'], 'ferie': False})
h = rendre('calendrier_prestations.html', '/dimona/5/prestations',
           dimona={'id': 5, 'type_dimona': 'OTH', 'date_debut': ENTREE, 'date_fin': None}, jours=jours_cal,
           stats={'jours_prestes': 15, 'heures_prestees': 114.0, 'jours_conge': 0, 'jours_maladie': 7, 'jours_ferie': 0,
                  'jours_chomage': 0, 'jours_cnp': 0}, calcul=None, annee=2026, mois=10, mois_nom='Octobre',
           premier_jour_semaine=3, codes=CODES_JOURNALIERS, codes_json=json.dumps(CODES_JOURNALIERS), heures_jour=7.6,
           incapacites_mois=du_mois, incapacites_alertes=[a for v in du_mois for a in v['alertes']])
check("Calendrier: codes de tranche dans la legende et sur les jours", 'id="btn_M2"' in h and '>MC<' in h)
check("Calendrier: encart de l'incapacite du mois avec ses tranches et le lien de gestion",
      'Maladie du 24/09/2026 au 09/10/2026' in h and '/travailleur/3/incapacites' in h and 'rechute' in h)

js = [{'date': date(2026,10,n), 'tranche': par_date[date(2026,10,n)]['tranche'], 'heures': 7.6}
      for n in range(1, 10) if date(2026,10,n).weekday() < 5]
infos = ["Maladie du 24/09/2026 au 09/10/2026 — Ouvrier (art. 52), rechute : décompte repris au jour 11"] + inc['regles']
r = ouvrier(15, {'regime': 'ouvrier', 'jours': js, 'infos': infos, 'alertes': du_mois[0]['alertes']})
# 4 jours M2 en septembre (24, 25, 28... non: 24-27/09 = rangs 11 a 14) -> octobre entierement en complement:
# 7 jours ouvres x 7,6 h x 15 x 25,88 % = 206,52
check("Rechute en octobre: 7 jours de complement = 206,52, aucune 2e semaine",
      [(l['tranche'], l['montant']) for l in r['lignes_hors_onss']], [('MC', 206.52)])
check("Fiche: alerte de rechute reprise dans les alertes du calcul", any('Maladie : Rechute' in a for a in r['alertes_calcul']), True)
h = rendre('calcul_paie_detail.html', '/dimona/5/generer-paie', data=r, dimona={'id': 5, 'prenom': 'Camille', 'nom': 'Exemple'},
           contrat=contrat, annee=2026, mois=10, mois_nom='Octobre', champs=[])
check("Page « Calculer la paie »: bloc Maladie (regles, tranches, montant) et alertes",
      'Maladie et salaire garanti' in h and 'Complément maladie jours 15 à 30' in h and '206.52' in h and 'Maladie : Rechute' in h)
h = rendre('generer_fiche_form.html', '/dimona/5/generer-paie', dimona={'id': 5, 'prenom': 'Camille', 'nom': 'Exemple', 'travailleur_id': 3},
           contrat=contrat, prime_suggestion=None, prime_annuelle_suggestion=None, pecule_suggestion=None, annee=2026, mois=10,
           mois_nom='Octobre', cp_key='CP 140.03', vehicule_societe=False, km_domicile=0,
           maladie_infos=infos, maladie_alertes=du_mois[0]['alertes'])
check("Formulaire de generation: rappel de l'incapacite du mois avant le calcul", 'Maladie et salaire garanti ce mois-ci' in h and 'Rechute' in h)

print(); print("=" * 70); print("PROTECTIONS -- jours maladie sans episode ; travailleur sans contrat actif"); print("=" * 70)
from salaire_garanti import jours_maladie_sans_episode
codes = [(date(2026,10,n), 'MA') for n in (12, 13, 14, 15, 16, 19, 20)] + [(date(2026,10,28), 'MG'), (date(2026,10,1), 'M2'),
         (date(2026,10,21), 'P'), (date(2026,10,22), 'CL')]
g = jours_maladie_sans_episode(codes, par_date)
check("Jours maladie hors episode regroupes (le week-end ne coupe pas): 12/10 -> 20/10 (7 j) et 28/10 (1 j)",
      [(x['debut'], x['fin'], x['jours']) for x in g], [(date(2026,10,12), date(2026,10,20), 7), (date(2026,10,28), date(2026,10,28), 1)])
check("Un jour maladie couvert par un episode (01/10) n'est pas signale ; ni les jours prestes ou de conge",
      any(x['debut'] <= date(2026,10,1) <= x['fin'] or x['debut'] <= date(2026,10,21) <= x['fin'] for x in g), False)
check("Aucun jour maladie orphelin: aucune alerte", jours_maladie_sans_episode([(date(2026,10,1), 'M2'), (date(2026,10,21), 'P')], par_date), [])
ctx_cal = dict(dimona={'id': 5, 'type_dimona': 'OTH', 'date_debut': ENTREE, 'date_fin': None}, jours=jours_cal,
               stats={'jours_prestes': 15, 'heures_prestees': 114.0, 'jours_conge': 0, 'jours_maladie': 7, 'jours_ferie': 0,
                      'jours_chomage': 0, 'jours_cnp': 0}, calcul=None, annee=2026, mois=10, mois_nom='Octobre',
               premier_jour_semaine=3, codes=CODES_JOURNALIERS, codes_json=json.dumps(CODES_JOURNALIERS), heures_jour=7.6,
               incapacites_mois=[], incapacites_alertes=[])
h = rendre('calendrier_prestations.html', '/dimona/5/prestations', maladie_sans_episode=g, **ctx_cal)
check("Calendrier: alerte claire + bouton de creation pre-rempli (du 12/10 au 20/10)",
      "sans épisode d'incapacité" in h and 'action="/travailleur/3/incapacites"' in h and 'name="date_debut" value="2026-10-12"' in h
      and 'name="date_fin" value="2026-10-20"' in h and 'name="action" value="creer"' in h)
check("Calendrier sans jour orphelin: pas d'alerte", "sans épisode d'incapacité" in
      rendre('calendrier_prestations.html', '/dimona/5/prestations', maladie_sans_episode=[], **ctx_cal), False)
h = rendre('calcul_paie_detail.html', '/dimona/5/generer-paie', data=r, dimona={'id': 5, 'prenom': 'Camille', 'nom': 'Exemple', 'travailleur_id': 3},
           contrat=contrat, annee=2026, mois=10, mois_nom='Octobre', champs=[], maladie_sans_episode=g)
check("« Calculer la paie »: meme alerte et meme bouton, hors du formulaire de generation",
      'name="date_debut" value="2026-10-12"' in h and h.index("sans épisode d'incapacité") < h.index('data-pdf="Fiche de paie"'))
ctx_ft = dict(tab='info', fiches=[], documents=[])
h = rendre('fiche_travailleur.html', '/travailleur/3', contrats=[], **ctx_ft)
check("Fiche du travailleur sans contrat actif: alerte avec les liens pour en creer un",
      'Aucun contrat actif pour ce travailleur' in h and '/dossier/7/contrat/nouveau?travailleur_id=3' in h)
check("Fiche du travailleur avec un contrat actif: pas d'alerte", 'Aucun contrat actif' in
      rendre('fiche_travailleur.html', '/travailleur/3', contrats=[dict(contrat, en_cours=True)], **ctx_ft), False)
h = rendre('fiche_travailleur.html', '/travailleur/3', contrats=[dict(contrat, date_fin=date(2026,8,31), en_cours=False)], **ctx_ft)
check("Fiche du travailleur dont le seul contrat est termine: alerte, et le contrat est marque « terminé »",
      'Aucun contrat actif pour ce travailleur' in h and
      'terminé' in rendre('fiche_travailleur.html', '/travailleur/3', contrats=[dict(contrat, date_fin=date(2026,8,31), en_cours=False)],
                          **dict(ctx_ft, tab='contrats')))
if SORTIE:
    from generer_fiche_pdf import generer_fiche_paie_pdf
    r.update(periode_debut=date(2026,10,1), periode_fin=date(2026,10,31))
    chemin_pdf = os.path.join(SORTIE, 'exemple_fiche_maladie.pdf')
    generer_fiche_paie_pdf(r, chemin_pdf)
    from pypdf import PdfReader
    texte = ' '.join((pg.extract_text() or '') for pg in PdfReader(chemin_pdf).pages)
    check("Fiche PDF: ligne du complement de maladie, hors ONSS, avant l'imposable",
          'hors ONSS' in texte and '206.52' in texte and texte.index('206.52') < texte.index('IMPOSABLE'), True)

print(); print("=" * 70)
if ECHECS:
    print(f"❌ {len(ECHECS)} TEST(S) ECHOUE(S): {ECHECS}"); sys.exit(1)
print("✅ TOUS LES TESTS PASSENT -- maladie et salaire garanti.")
