# -*- coding: utf-8 -*-
"""
test_fin_contrat.py -- DuxSalary
Fin de contrat (fin_contrat.py): preavis, indemnite de rupture, pecule de sortie,
decompte de sortie PDF, lignes pour l'aide DmfA. Un test par cas.
Lancer: python3 test_fin_contrat.py   -- doit afficher TOUS LES TESTS PASSENT
        python3 test_fin_contrat.py outputs   -- ecrit aussi un PDF d'exemple (donnees fictives)
Montants attendus calcules a la main avec la loi du 03/07/1978, l'annexe III 2026 et les
Instructions ONSS 2026/3: aucun decompte reel disponible pour recouper.
"""
import sys, os, io, re
from datetime import date
from fin_contrat import (semaines_preavis, dates_preavis, ajouter_jours_ouvrables, anciennete_mois, remuneration_hebdomadaire,
                         avantages_hebdomadaires, avantages_proposes, precompte_indemnite_dedit, decompte_sortie, AVANTAGES, MOTIFS)
from profil_travailleur import construire_profil
ECHECS = []

def check(label, obtenu, attendu=True, tol=0.011):
    nombres = all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (obtenu, attendu))
    ok = abs(obtenu - attendu) <= tol if nombres else obtenu == attendu
    print(f"{'✅' if ok else '❌'} {label}: obtenu={obtenu} attendu={attendu}")
    if not ok: ECHECS.append(label)

AVANT, APRES = date(2026, 3, 2), date(2026, 9, 1)     # contrats debutes avant / a partir du 01/08/2026
sem = lambda auteur, mois, debut: semaines_preavis(auteur, mois, debut)[0]

print("=" * 70); print("PREAVIS -- CDI debute AVANT le 01/08/2026 (art. 37/2, table du 01/05/2018)"); print("=" * 70)
check("Licenciement: 1 semaine avant 3 mois, puis 3, 4 et 5 semaines a 3, 4 et 5 mois",
      [sem('employeur', m, AVANT) for m in (0, 2, 3, 4, 5)], [1, 1, 3, 4, 5])
check("Licenciement: 6, 7, 8, 9, 10, 11 semaines de 6 a 21 mois ; 12, 13, 15 semaines a 2, 3 et 4 ans",
      [sem('employeur', m, AVANT) for m in (6, 9, 12, 15, 18, 21, 24, 36, 48)], [6, 7, 8, 9, 10, 11, 12, 13, 15])
check("Licenciement: + 3 semaines par annee des 5 ans (18, 21, 24, 27, 30), 60 a 19 ans, 62 a 20 ans, 63 a 21 ans, 64 a 22 ans",
      [sem('employeur', a * 12, AVANT) for a in (5, 6, 7, 8, 9, 19, 20, 21, 22)], [18, 21, 24, 27, 30, 60, 62, 63, 64])
check("Demission: 1 semaine avant 3 mois, 2 de 3 a 6 mois, puis 3, 4, 5, 6, 7, 9, 10, 12 et 13 au maximum",
      [sem('travailleur', m, AVANT) for m in (0, 3, 5, 6, 12, 18, 24, 48, 60, 72, 84, 96, 300)], [1, 2, 2, 3, 4, 5, 6, 7, 9, 10, 12, 13, 13])
check("Contre-preavis: 1, 2, 3, 4 semaines", [sem('contre_preavis', m, AVANT) for m in (0, 3, 6, 12, 100)], [1, 2, 3, 4, 4])
check("Pas de plafond de 52 semaines pour un contrat debute avant le 01/06/2026", sem('employeur', 25 * 12, AVANT), 67)

print(); print("=" * 70); print("PREAVIS -- CDI debute A PARTIR du 01/08/2026 (loi du 03/06/2026)"); print("=" * 70)
check("Licenciement: 1 semaine pendant les six premiers mois, puis la meme table",
      [sem('employeur', m, APRES) for m in (0, 3, 4, 5, 6, 9, 12, 24)], [1, 1, 1, 1, 6, 7, 8, 12])
check("Demission: 1 semaine pendant les six premiers mois, puis 3 semaines", [sem('travailleur', m, APRES) for m in (0, 3, 5, 6, 12)], [1, 1, 1, 3, 4])
check("Contre-preavis: 1 semaine avant 6 mois, puis 3 et 4", [sem('contre_preavis', m, APRES) for m in (0, 5, 6, 12)], [1, 1, 3, 4])
check("Plafond de 52 semaines des 17 ans d'anciennete (contrat debute a partir du 01/06/2026)",
      [sem('employeur', a * 12, APRES) for a in (16, 17, 25)], [51, 52, 52])
check("Contrat debute le 01/07/2026: ancienne table des premiers mois, mais plafond de 52 semaines",
      (sem('employeur', 4, date(2026, 7, 1)), sem('employeur', 20 * 12, date(2026, 7, 1))), (4, 52))
check("Le critere est la date de debut du CONTRAT: 4 mois d'anciennete -> 4 semaines (contrat de mars) ou 1 semaine (contrat de septembre)",
      (sem('employeur', 4, AVANT), sem('employeur', 4, APRES)), (4, 1))
try:
    semaines_preavis('employeur', 200, date(2010, 5, 1)); leve = False
except ValueError:
    leve = True
check("Contrat debute avant 2014: erreur claire, pas de calcul devine", leve)

print(); print("=" * 70); print("DATES DU PREAVIS (art. 37 § 1er et 37/1) ET ANCIENNETE (art. 37/4)"); print("=" * 70)
d = dates_preavis(date(2026, 10, 7), 'recommande', 6)      # mercredi 07/10
check("Recommande expedie le mercredi 07/10/2026: effet le 3e jour ouvrable (samedi 10/10), preavis du lundi 12/10 au dimanche 22/11",
      (d['effet'], d['debut'], d['fin']), (date(2026, 10, 10), date(2026, 10, 12), date(2026, 11, 22)))
d = dates_preavis(date(2026, 10, 9), 'recommande', 1)      # vendredi: effet le mardi 13 -> preavis le lundi 19
check("Recommande expedie le vendredi 09/10: effet le mardi 13/10 (le dimanche ne compte pas), preavis des le lundi 19/10",
      (d['effet'], d['debut']), (date(2026, 10, 13), date(2026, 10, 19)))
d = dates_preavis(date(2026, 10, 9), 'remise', 3)
check("Remise d'un ecrit le vendredi 09/10: effet le jour meme, preavis du lundi 12/10 au dimanche 01/11",
      (d['effet'], d['debut'], d['fin']), (date(2026, 10, 9), date(2026, 10, 12), date(2026, 11, 1)))
check("Jour ferie non compte: 3 jours ouvrables apres le jeudi 29/10/2026 = lundi 02/11 (le dimanche 01/11, ferie, ne compte pas)",
      ajouter_jours_ouvrables(date(2026, 10, 29), 3), date(2026, 11, 2))
check("Anciennete en mois complets", [anciennete_mois(date(2026, 3, 2), x) for x in (date(2026, 9, 1), date(2026, 9, 2), date(2027, 3, 1))], [5, 6, 11])

print(); print("=" * 70); print("REMUNERATION DE REFERENCE ET AVANTAGES (art. 39)"); print("=" * 70)
check("Employe paye au mois: 3.000,00 x 3 / 13 = 692,31", remuneration_hebdomadaire(True, salaire_mensuel=3000.0)[0], 692.31)
check("Ouvrier a horaire fixe: 38 h x 15,00 = 570,00", remuneration_hebdomadaire(False, salaire_horaire=15.0, heures_semaine=38.0)[0], 570.0)
fiches_var = [{'periode_debut': date(2026, m, 1), 'salaire_brut': 1300.0, 'prime_brut': 0.0} for m in (7, 8, 9)]
h_var, expl = remuneration_hebdomadaire(False, horaire_variable=True, fiches=fiches_var, date_fin=date(2026, 9, 30), date_entree=date(2026, 7, 1))
check("Ouvrier a horaire variable, entre le 01/07: moyenne depuis l'entree = 3.900,00 / (92 jours / 7) = 296,74", h_var, 296.74)
fiches_an = [{'periode_debut': date(a, m, 1), 'salaire_brut': 2000.0, 'prime_brut': 0.0}
             for a, m in [(2025, m) for m in range(1, 13)] + [(2026, m) for m in range(1, 10)]]
h_an, _ = remuneration_hebdomadaire(False, horaire_variable=True, fiches=fiches_an, date_fin=date(2026, 9, 30), date_entree=date(2020, 1, 1))
check("... avec plus d'un an d'anciennete: seules les fiches des douze derniers mois comptent (12 x 2.000 / 365 x 7)", h_an, round(24000 / (365 / 7), 2))
try:
    remuneration_hebdomadaire(False, horaire_variable=True, fiches=[], date_fin=date(2026, 9, 30)); leve = False
except ValueError:
    leve = True
check("Horaire variable sans fiche: erreur claire", leve)
lig, tot_av = avantages_hebdomadaires({'prime_fin_annee': 3000.0, 'double_pecule': 2760.0, 'voiture_societe': 0})
check("Avantages annuels / 52: 3.000 -> 57,69 ; 2.760 -> 53,08 ; total 110,77 ; un avantage a 0 n'apparait pas",
      ([l[2] for l in lig], tot_av), ([57.69, 53.08], 110.77))
check("Les 7 avantages prevus", [k for k, _ in AVANTAGES], ['prime_fin_annee', 'double_pecule', 'cheques_repas', 'ecocheques',
      'assurance_groupe', 'assurance_hospitalisation', 'voiture_societe'])
prop = avantages_proposes(True, 3000.0, 692.31, cheque_part_patronale=6.91, jours_semaine=5, ecocheques_annuels=250.0, a_prime_fin_annee=True)
check("Proposition pour un employe: 13e mois 3.000, double pecule 2.760 (92 %), cheques 6,91 x 5 x 47 = 1.623,85, ecocheques 250",
      (prop['prime_fin_annee'], prop['double_pecule'], prop['cheques_repas'], prop['ecocheques'], prop['voiture_societe']),
      (3000.0, 2760.0, 1623.85, 250.0, 0.0))

print(); print("=" * 70); print("PRECOMPTE DE L'INDEMNITE DE RUPTURE (annexe III 2026, n° 58 a 62)"); print("=" * 70)
R = date(2026, 10, 12)
check("Remuneration de reference 41.760 EUR: 29,93 %", precompte_indemnite_dedit(7581.56, 41760.16, R)[:2], (2269.16, 0.2993))
check("Limites des tranches: 11.860 -> 0 % ; 11.860,01 -> 2,68 % ; 62.465 -> 36,90 % ; 200.000 -> 48 %",
      [precompte_indemnite_dedit(1000.0, x, R)[1] for x in (11860, 11860.01, 62465, 200000)], [0.0, 0.0268, 0.369, 0.48])
pp, taux, exo = precompte_indemnite_dedit(3000.0, 20000.0, R, nb_enfants=2)
check("2 enfants a charge, reference 20.000 EUR: 22.470 - 20.000 = 2.470 EUR exoneres, 13,55 % sur 530,00 = 71,82", (pp, taux, exo), (71.82, 0.1355, 2470.0))
check("Dispense quand le douzieme de la reference ne donne pas de precompte (n° 61)", precompte_indemnite_dedit(3000.0, 20000.0, R, precompte_mensuel_nul=True)[0], 0.0)

print(); print("=" * 70); print("DECOMPTES -- un cas par situation"); print("=" * 70)
EMP = construire_profil('CP 200', 'employe', type_contrat='CDI', reference_date=date(2026, 10, 31), categorie_employeur='010')
OUV = construire_profil('CP 140.03', 'ouvrier', type_contrat='CDI', reference_date=date(2026, 10, 31), categorie_employeur='000')
H_EMP = remuneration_hebdomadaire(True, salaire_mensuel=3000.0)
H_OUV = remuneration_hebdomadaire(False, salaire_horaire=15.0, heures_semaine=38.0)

# 1. Employe en CDI depuis le 01/01/2025, licencie par recommande du 07/10/2026, preavis non preste (fin le 11/10)
r = decompte_sortie(EMP, 'licenciement', 'CDI', date(2025, 1, 1), None, date(2025, 1, 1), date(2026, 10, 7), 'recommande',
                    preavis_preste=False, date_fin_effective=date(2026, 10, 11), hebdo_base=H_EMP[0], explication_hebdo=H_EMP[1],
                    avantages_annuels={'prime_fin_annee': 3000.0, 'double_pecule': 2760.0},
                    pecule={'brut_annee_en_cours': 30000.0, 'brut_annee_precedente': 36000.0, 'jours_vacances_pris': 12, 'double_deja_paye': True})
i = r['indemnite']
check("Employe licencie (21 mois d'anciennete au 12/10/2026): preavis de 11 semaines", (r['preavis']['semaines'], r['preavis']['anciennete_mois']), (11, 21))
check("Indemnite: (692,31 + 110,77) x 11 semaines = 8.833,88", (i['hebdo'], i['semaines'], i['brut']), (803.08, 11.0, 8833.88))
check("ONSS travailleur 13,07 % = 1.154,59 ; imposable 7.679,29", (i['onss'], i['imposable']), (1154.59, 7679.29))
check("Precompte: reference 803,08 x 52 = 41.760,16 -> 29,93 % = 2.298,41 ; net 5.380,88", (i['reference_annuelle'], i['precompte'], i['net']), (41760.16, 2298.41, 5380.88))
check("Indemnite sur la DmfA: code remuneration 3, periode du 12/10/2026 au 27/12/2026 (11 semaines des le lendemain de la fin)",
      [(x['code_remuneration'], x.get('du'), x.get('au')) for x in r['dmfa'] if x['code_remuneration'] == 3], [(3, date(2026, 10, 12), date(2026, 12, 27))])
p = r['pecule']
check("Pecule de sortie 2026: 7,67 % x 30.000 = 2.301,00 simple et 2.301,00 double", [(b[3], b[4]) for b in p['blocs']][0], (2301.0, 2301.0))
check("Pecule sur 2025, 12 jours de vacances pris sur 20, double deja paye: simple 7,67 % x 36.000 x 8/20 = 1.104,48, pas de double",
      [(b[3], b[4]) for b in p['blocs']][1], (1104.48, 0.0))
check("ONSS du pecule simple: 13,07 % x 3.405,48 = 445,10 ; retenue du double: 13,07 % x (6,80 % x 30.000) = 266,63",
      (p['onss_simple'], p['base_retenue_double'], p['retenue_double']), (445.1, 2040.0, 266.63))
check("Precompte du pecule: 42,39 % (remuneration annuelle normale 36.000 EUR, annexe III n° 53) sur 4.994,75 = 2.117,27", (p['taux_precompte'], p['precompte']), (0.4239, 2117.27))
check("Total net du decompte = indemnite nette + pecule net", r['totaux']['net'], round(i['net'] + p['net'], 2))
check("Alertes: suspension du preavis, protections non controlees", (any('suspension' in a for a in r['alertes']), any('protections' in a for a in r['alertes'])), (True, True))
check("ONSS des avantages: simple rappel dans les regles, plus une alerte",
      (any('soumise en entier aux cotisations ordinaires, avantages compris' in x for x in r['regles']),
       any('cotisations ordinaires' in a for a in r['alertes'])), (True, False))

# 2. Meme employe, preavis preste: aucune indemnite
r = decompte_sortie(EMP, 'licenciement', 'CDI', date(2025, 1, 1), None, date(2025, 1, 1), date(2026, 10, 7), 'recommande',
                    preavis_preste=True, hebdo_base=H_EMP[0])
check("Preavis preste jusqu'a son terme (27/12/2026): aucune indemnite de rupture", (r['indemnite'], r['preavis']['dates']['fin'], r['totaux']['brut']), (None, date(2026, 12, 27), 0.0))
# 3. Preavis preste en partie
r = decompte_sortie(EMP, 'licenciement', 'CDI', date(2025, 1, 1), None, date(2025, 1, 1), date(2026, 10, 7), 'recommande',
                    preavis_preste=False, date_fin_effective=date(2026, 11, 29), hebdo_base=H_EMP[0])
check("Preavis interrompu le 29/11/2026: 4 semaines restant a courir, indemnite 4 x 692,31 = 2.769,24", (r['indemnite']['semaines'], r['indemnite']['brut']), (4.0, 2769.24))

# 4. CDI debute apres le 01/08/2026, licencie apres 4 mois: 1 semaine
r = decompte_sortie(EMP, 'licenciement', 'CDI', date(2026, 9, 1), None, date(2026, 9, 1), date(2027, 1, 6), 'recommande',
                    preavis_preste=False, date_fin_effective=date(2027, 1, 10), hebdo_base=H_EMP[0])
check("CDI debute le 01/09/2026, licencie apres 4 mois: preavis d'une semaine, indemnite 692,31", (r['preavis']['semaines'], r['indemnite']['brut']), (1, 692.31))
r = decompte_sortie(EMP, 'licenciement', 'CDI', date(2026, 3, 2), None, date(2026, 3, 2), date(2026, 7, 8), 'recommande',
                    preavis_preste=False, date_fin_effective=date(2026, 7, 12), hebdo_base=H_EMP[0])
check("CDI debute le 02/03/2026, licencie apres 4 mois: 4 semaines, indemnite 2.769,24", (r['preavis']['semaines'], r['indemnite']['brut']), (4, 2769.24))

# 5. Demission
r = decompte_sortie(EMP, 'demission', 'CDI', date(2025, 1, 1), None, date(2025, 1, 1), date(2026, 10, 9), 'remise', preavis_preste=True, hebdo_base=H_EMP[0])
check("Demission apres 21 mois: preavis de 5 semaines, du 12/10 au 15/11/2026, aucune indemnite",
      (r['preavis']['semaines'], r['preavis']['dates']['debut'], r['preavis']['dates']['fin'], r['indemnite']), (5, date(2026, 10, 12), date(2026, 11, 15), None))
r = decompte_sortie(EMP, 'demission', 'CDI', date(2025, 1, 1), None, date(2025, 1, 1), date(2026, 10, 9), 'remise',
                    preavis_preste=False, date_fin_effective=date(2026, 10, 9), hebdo_base=H_EMP[0])
check("Demission sans prester le preavis: indemnite de 5 semaines due PAR le travailleur (3.461,55), JAMAIS retenue d'office",
      (r['indemnite']['due_par'], r['indemnite']['brut'], r['totaux']['onss'], r['totaux']['net'], r['lignes']),
      ('travailleur', 3461.55, 0.0, 0.0, []))
check("... le montant du est mentionne sur le document, a regler separement",
      r['mentions'], ["Indemnité de rupture due par le travailleur à l'employeur : 3461,55 EUR (5 semaines), à régler séparément."])
check("... alerte: loi du 12/04/1965 art. 23, liste limitative et cinquieme du net", any(
      "loi du 12/04/1965 (art. 23)" in a and 'cinquième' in a and "ne figure pas dans cette liste" in a for a in r['alertes']))
PEC = {'brut_annee_en_cours': 27000.0}
dem = lambda retenue: decompte_sortie(EMP, 'demission', 'CDI', date(2025, 1, 1), None, date(2025, 1, 1), date(2026, 10, 9), 'remise',
                                      preavis_preste=False, date_fin_effective=date(2026, 10, 9), hebdo_base=H_EMP[0], pecule=PEC,
                                      retenue_travailleur=retenue)
r0 = dem(0)
check("Demission avec un pecule de sortie a payer: le net du pecule est verse en entier, rien n'est retenu",
      (r0['totaux']['net'], r0['pecule']['net'], r0['indemnite']['retenue']), (r0['pecule']['net'], r0['pecule']['net'], 0.0))
check("... le cinquieme du net est affiche comme repere", r0['indemnite']['cinquieme_net'], round(r0['pecule']['net'] / 5, 2))
r1 = dem(r0['indemnite']['cinquieme_net'])
check("Retenue saisie par Leo (un cinquieme du net): deduite, avec le solde encore du",
      (round(r0['totaux']['net'] - r1['totaux']['net'], 2), r1['indemnite']['solde_du'], r1['lignes'][-1]['libelle']),
      (r0['indemnite']['cinquieme_net'], round(3461.55 - r0['indemnite']['cinquieme_net'], 2),
       "Retenue convenue sur l'indemnité de rupture due par le travailleur"))
r2 = dem(99999.0)
check("Retenue saisie superieure au net: plafonnee au net disponible, avec une alerte « accord écrit »",
      (r2['totaux']['net'], any('accord écrit' in a for a in r2['alertes'])), (0.0, True))
check("Licenciement par remise d'un ecrit: alerte (non valable pour l'employeur)",
      any("remise d'un écrit n'est pas valable" in a for a in decompte_sortie(EMP, 'licenciement', 'CDI', date(2025, 1, 1), None,
          date(2025, 1, 1), date(2026, 10, 9), 'remise', hebdo_base=H_EMP[0])['alertes']))

# 6. Motif grave
r = decompte_sortie(EMP, 'motif_grave', 'CDI', date(2025, 1, 1), None, date(2025, 1, 1), date(2026, 10, 7), hebdo_base=H_EMP[0],
                    pecule={'brut_annee_en_cours': 30000.0})
check("Motif grave: ni preavis ni indemnite, mais le pecule de sortie reste du", (r['preavis'], r['indemnite'], r['pecule']['simple']), (None, None, 2301.0))
check("Motif grave: rappel des deux delais de 3 jours ouvrables (motif a notifier au plus tard le 10/10/2026)",
      any('3 jours ouvrables' in a and '10/10/2026' in a for a in r['alertes']))

# 7. CDD
CDD = dict(type_contrat='CDD', date_debut_contrat=date(2026, 9, 1), date_fin_contrat_prevue=date(2027, 2, 28), debut_anciennete=date(2026, 9, 1))
r = decompte_sortie(EMP, 'licenciement', mode_notification='recommande', date_notification=date(2026, 10, 7), preavis_preste=False,
                    date_fin_effective=date(2026, 10, 11), hebdo_base=H_EMP[0], **CDD)
check("CDD de 6 mois rompu pendant la premiere moitie (avant le 29/11/2026): preavis de l'art. 37/2 (1 semaine), indemnite 692,31",
      (r['preavis']['semaines'], r['indemnite']['brut']), (1, 692.31))
r = decompte_sortie(EMP, 'licenciement', mode_notification='recommande', date_notification=date(2026, 12, 9), preavis_preste=False,
                    date_fin_effective=date(2026, 12, 13), hebdo_base=H_EMP[0], **CDD)
check("CDD rompu apres la premiere moitie: remuneration restant a echoir (11 semaines) plafonnee au double du preavis (2 x 1 semaine) = 1.384,62",
      (r['indemnite']['semaines'], r['indemnite']['brut']), (2.0, 1384.62))
CDD_ANCIEN = dict(type_contrat='CDD', date_debut_contrat=date(2026, 3, 2), date_fin_contrat_prevue=date(2026, 12, 31), debut_anciennete=date(2026, 3, 2))
r = decompte_sortie(EMP, 'licenciement', mode_notification='recommande', date_notification=date(2026, 12, 9), preavis_preste=False,
                    date_fin_effective=date(2026, 12, 13), hebdo_base=H_EMP[0], **CDD_ANCIEN)
check("CDD debute en mars 2026 rompu le 13/12: 2,57 semaines restant a echoir, sous le plafond (2 x 7 semaines) -> 2,57 x 692,31 = 1.779,24",
      (r['indemnite']['semaines'], r['indemnite']['brut']), (2.57, 1779.24))
r = decompte_sortie(EMP, 'fin_cdd', date_notification=date(2026, 12, 31), date_fin_effective=date(2026, 12, 31), hebdo_base=H_EMP[0],
                    pecule={'brut_annee_en_cours': 6000.0}, **CDD_ANCIEN)
check("CDD arrive a son terme: ni preavis ni indemnite, pecule de sortie seulement", (r['preavis'], r['indemnite'], r['pecule']['simple']), (None, None, 460.2))

# 8. Ouvrier
r = decompte_sortie(OUV, 'licenciement', 'CDI', date(2024, 6, 3), None, date(2024, 6, 3), date(2026, 10, 7), 'recommande',
                    preavis_preste=False, date_fin_effective=date(2026, 10, 11), hebdo_base=H_OUV[0], explication_hebdo=H_OUV[1],
                    pecule={'brut_annee_en_cours': 20000.0})
i = r['indemnite']
check("Ouvrier licencie apres 2 ans et 4 mois: 12 semaines x 570,00 = 6.840,00", (r['preavis']['semaines'], i['brut']), (12, 6840.0))
check("Ouvrier: ONSS travailleur sur 108 % (7.387,20 x 13,07 % = 965,51)", i['onss'], 965.51)
check("Ouvrier: aucun pecule de sortie a charge de l'employeur, et la regle le dit", (r['pecule'], any('caisse de vacances' in x for x in r['regles'])), (None, True))
check("Meme table de preavis pour un ouvrier et un employe (statut unique)", sem('employeur', 28, date(2024, 6, 3)), 12)

# 9. Alertes de perimetre
r = decompte_sortie(EMP, 'licenciement', 'CDI', date(2016, 1, 4), None, date(2016, 1, 4), date(2026, 10, 7), 'recommande',
                    preavis_preste=False, date_fin_effective=date(2026, 10, 11), hebdo_base=2000.0)
check("10 ans d'anciennete: 33 semaines -> alerte de reclassement professionnel, sans deduction",
      (r['preavis']['semaines'], any('reclassement professionnel' in a for a in r['alertes']), r['indemnite']['semaines']), (33, True, 33.0))
check("Salaire annuel de reference de 104.000 EUR: cotisation 812 de 3 % a charge de l'employeur (1.980,00)", r['indemnite']['cotisation_812'], 1980.0)
try:
    decompte_sortie(EMP, 'licenciement', 'CDI', date(2012, 1, 2), None, date(2012, 1, 2), date(2026, 10, 7), hebdo_base=700.0); leve = False
except ValueError as ex:
    leve = 'avant le 01/01/2014' in str(ex)
check("Contrat debute avant 2014: erreur claire (non gere)", leve)
ETU = construire_profil('CP 200', 'etudiant', type_contrat='STU', reference_date=date(2026, 8, 31))
r = decompte_sortie(ETU, 'commun_accord', 'STU', date(2026, 7, 1), date(2026, 8, 31), date(2026, 7, 1), date(2026, 8, 10), hebdo_base=400.0)
check("Rupture d'un commun accord: ni preavis ni indemnite", (r['preavis'], r['indemnite'], r['totaux']['brut']), (None, None, 0.0))

print(); print("=" * 70); print("DECOMPTE DE SORTIE PDF -- document client, aucune source"); print("=" * 70)
from pdf_fin_contrat import generer_pdf_decompte
from pypdf import PdfReader
INTERDITS = ['easypay', 'liantis', 'securex', 'partena', 'acerta', 'csc', 'techlib', 'instructions onss', 'instructions administratives',
             'spf', 'justel', 'annexe iii', 'art.', 'loi du', 'source', 'parametres_dates', '.py', 'à valider', 'à confirmer',
             'non contrôlé', 'n° 5', 'n° 6', 'code rémunération', 'dmfa']
complet = decompte_sortie(EMP, 'licenciement', 'CDI', date(2025, 1, 1), None, date(2025, 1, 1), date(2026, 10, 7), 'recommande',
                          preavis_preste=False, date_fin_effective=date(2026, 10, 11), hebdo_base=H_EMP[0], explication_hebdo=H_EMP[1],
                          avantages_annuels={'prime_fin_annee': 3000.0, 'double_pecule': 2760.0, 'cheques_repas': 1623.85},
                          pecule={'brut_annee_en_cours': 30000.0, 'brut_annee_precedente': 36000.0, 'jours_vacances_pris': 12})
ctx = {'employeur': 'Société Fictive SRL', 'adresse_employeur': 'Rue Exemple 1, 1000 Bruxelles', 'bce': '0000.000.000',
       'travailleur': 'Camille Exemple', 'niss': '00.00.00-000.00', 'fonction': 'Comptable', 'type_contrat': 'CDI',
       'date_entree': date(2025, 1, 1), 'date_fin': date(2026, 10, 11), 'iban': 'BE00 0000 0000 0000'}
pdf = generer_pdf_decompte(complet, ctx)
texte = re.sub(r'\s+', ' ', ' '.join((p.extract_text() or '') for p in PdfReader(io.BytesIO(pdf)).pages))
check("PDF genere, sur une page", (pdf[:4], len(PdfReader(io.BytesIO(pdf)).pages)), (b'%PDF', 1))
check("Le decompte contient les libelles, bases, taux et montants", all(x in texte for x in (
    'Décompte de sortie', 'Indemnité de rupture', '11 semaines', 'Pécule simple de sortie', 'NET À PAYER', 'Camille Exemple',
    'préavis du 12/10/2026 au 27/12/2026')))
check("Aucune source ni note interne dans le decompte client", [m for m in INTERDITS if m in texte.lower()], [])
check("... alors que les regles internes citent bien leurs sources", any('annexe III' in x for x in complet['regles']) and any('art. 39' in x for x in complet['regles']))
check("Aucune source dans les lignes du decompte, quel que soit le cas",
      [l['libelle'] for l in complet['lignes'] if any(m in (l['libelle'] + str(l.get('nombre'))).lower() for m in INTERDITS)], [])
check("Mentions de l'editeur en pied de page", 'Global Smart Services' in texte)
vide = generer_pdf_decompte(decompte_sortie(EMP, 'demission', 'CDI', date(2025, 1, 1), None, date(2025, 1, 1), date(2026, 10, 9),
                                            'remise', preavis_preste=True, hebdo_base=H_EMP[0]), ctx)
check("Decompte sans rien a payer: document genere avec la mention correspondante",
      'Aucune indemnité de rupture ni pécule de sortie' in re.sub(r'\s+', ' ', PdfReader(io.BytesIO(vide)).pages[0].extract_text()))
pdf_dem = generer_pdf_decompte(r1, ctx)
t_dem = re.sub(r'\s+', ' ', ' '.join((p.extract_text() or '') for p in PdfReader(io.BytesIO(pdf_dem)).pages))
check("Decompte d'une demission: montant du par le travailleur et retenue convenue imprimes, toujours sans source",
      ('Indemnité de rupture due par le travailleur' in t_dem, 'Retenue convenue' in t_dem, [m for m in INTERDITS if m in t_dem.lower()]),
      (True, True, []))
if len(sys.argv) > 1:
    io.open(os.path.join(sys.argv[1], 'exemple_decompte_sortie.pdf'), 'wb').write(pdf)
    io.open(os.path.join(sys.argv[1], 'exemple_decompte_demission.pdf'), 'wb').write(pdf_dem)

print(); print("=" * 70); print("PAGE « FIN DE CONTRAT » ET AIDE DmfA"); print("=" * 70)
import json
from fin_contrat import propositions, decompte_depuis_formulaire
CONTRAT = {'id': 11, 'type_contrat': 'CDI', 'cp_key': 'CP 200', 'date_debut': date(2025, 1, 1), 'date_fin': None,
           'salaire_mensuel': 3000.0, 'salaire_horaire': 18.22, 'heures_semaine': 38.0, 'heures_jour': 7.6, 'jours_semaine': 5,
           'fonction': 'Comptable', 'statut': 'actif'}
def fp(a, m, brut=3000.0, **kw):
    return dict({'periode_debut': date(a, m, 1), 'salaire_brut': brut, 'prime_brut': 0.0, 'pecule_brut': 0.0, 'jours_conge': 0,
                 'is_etudiant': False}, **kw)
FICHES = [fp(2025, m) for m in range(1, 13)] + [fp(2026, m, jours_conge=4 if m in (4, 7, 8) else 0,
                                                    pecule_brut=2760.0 if m == 5 else 0.0) for m in range(1, 10)]
prop = propositions(CONTRAT, FICHES, 'employe', date(2026, 10, 11), cheque_part_patronale=6.91, a_prime_fin_annee=True)
check("Propositions: semaine 692,31 ; brut 2026 = 27.000 ; brut 2025 = 36.000 ; 12 jours de vacances pris ; double pecule deja paye",
      (prop['hebdo'], prop['brut_annee_en_cours'], prop['brut_annee_precedente'], prop['jours_vacances_pris'], prop['double_deja_paye']),
      (692.31, 27000.0, 36000.0, 12, True))
check("Propositions d'avantages: 13e mois, double pecule 92 %, cheques-repas ; assurances et voiture a saisir",
      (prop['avantages']['prime_fin_annee'], prop['avantages']['double_pecule'], prop['avantages']['cheques_repas'],
       prop['avantages']['assurance_groupe'], prop['avantages']['voiture_societe']), (3000.0, 2760.0, 1623.85, 0.0, 0.0))
FORM = {'motif': 'licenciement', 'date_notification': '2026-10-07', 'mode_notification': 'recommande', 'date_fin_effective': '2026-10-11',
        'av_prime_fin_annee': '3000', 'av_double_pecule': '2760,00', 'av_voiture_societe': '1200', 'inclure_pecule': 'on',
        'brut_annee_en_cours': '27000', 'brut_annee_precedente': '36000', 'jours_vacances_pris': '12', 'double_deja_paye': 'on'}
dec, saisie = decompte_depuis_formulaire(FORM, EMP, CONTRAT, [CONTRAT], FICHES)
check("Formulaire -> decompte: 11 semaines x (692,31 + 57,69 + 53,08 + 23,08) = 9.087,76",
      (dec['preavis']['semaines'], dec['indemnite']['hebdo'], dec['indemnite']['brut']), (11, 826.16, 9087.76))
check("... les montants saisis avec une virgule sont lus, la voiture de societe est un avantage comme les autres",
      [x[0] for x in dec['indemnite']['avantages']], ["Prime de fin d'année", 'Double pécule de vacances', 'Voiture de société – avantage de toute nature'])
check("... pecule de sortie: 7,67 % x 27.000 = 2.070,90 (simple) ; date de fin retenue le 11/10/2026",
      (dec['pecule']['blocs'][0][3], dec['date_fin']), (2070.9, date(2026, 10, 11)))
try:
    decompte_depuis_formulaire({'motif': 'licenciement', 'date_notification': '2026-10-07'}, EMP, CONTRAT, [CONTRAT], FICHES); leve = False
except ValueError as ex:
    leve = 'dernier jour du contrat' in str(ex)
check("Preavis non preste sans dernier jour de contrat: erreur claire", leve)
dec_p, _ = decompte_depuis_formulaire({'motif': 'demission', 'date_notification': '2026-10-09', 'mode_notification': 'remise',
                                       'preavis_preste': 'on'}, EMP, CONTRAT, [CONTRAT], FICHES)
check("Demission avec preavis preste: fin du contrat = fin du preavis (15/11/2026)", dec_p['date_fin'], date(2026, 11, 15))
C_OUV = dict(CONTRAT, cp_key='CP 140.03', salaire_mensuel=None, salaire_horaire=15.0, heures_jour=4.0, date_debut=date(2026, 7, 1))
F_OUV = [{'periode_debut': date(2026, m, 1), 'salaire_brut': 1300.0, 'prime_brut': 0.0} for m in (7, 8, 9)]
dec_v, s_v = decompte_depuis_formulaire({'motif': 'licenciement', 'date_notification': '2026-09-23', 'mode_notification': 'recommande',
                                         'date_fin_effective': '2026-09-30', 'horaire_variable': 'on'}, OUV, C_OUV, [C_OUV], F_OUV)
check("Ouvrier a horaire variable: semaine = moyenne des fiches depuis l'entree (296,74), et non 20 h x 15,00 = 300,00",
      (s_v['hebdo'], 'moyenne de 3 fiche(s)' in s_v['explication_hebdo']), (296.74, True))

from jinja2 import Environment, FileSystemLoader
import branding
from fin_contrat import MOTIFS as _M, AVANTAGES as _A
RACINE = os.path.dirname(os.path.abspath(__file__))
env = Environment(loader=FileSystemLoader(os.path.join(RACINE, 'templates')))
env.filters['basename'] = lambda x: os.path.basename(x) if x else ''
class Requete:
    path = '/contrat/11/fin-contrat'; form = {}; args = {}
dossier = {'id': 7, 'nom': 'Société Fictive SRL'}
commun = dict(request=Requete(), marque=branding.get_branding(), statique=branding.url_statique, session={'user_id': 1, 'user_nom': 'U'},
              tenant={}, tous_les_dossiers=[dossier], dossiers_archives=[], dossier_actif=dossier,
              contrat=dict(CONTRAT, prenom='Camille', nom='Exemple'))
fc = {'erreur': None, 'decompte': None, 'saisie': None, 'propositions': prop, 'motifs': _M, 'avantages': _A, 'statut': 'employe', 'nb_enfants': 0}
h = env.get_template('fin_contrat.html').render(fc=fc, formulaire={}, **commun)
check("Page: formulaire du decompte avec les motifs, les 7 avantages pre-remplis et le pecule de sortie",
      all(x in h for x in ('name="motif"', 'name="av_voiture_societe"', 'name="av_prime_fin_annee" class="form-control" value="3000.00"',
                           'name="brut_annee_en_cours" class="form-control" value="27000.00"', 'Certificat de travail', 'Formulaire C4')))
check("Page avant calcul: pas de bouton PDF", 'value="pdf"' in h, False)
h = env.get_template('fin_contrat.html').render(fc=dict(fc, decompte=dec, saisie=saisie), formulaire=FORM, **commun)
check("Page apres calcul: preavis, lignes, net a payer, regles et sources (usage interne), bouton PDF",
      all(x in h for x in ('11 semaine(s)', 'Indemnité de rupture', 'NET À PAYER', 'annexe III 2026', 'usage interne', 'value="pdf"')))
check("Page: la saisie est conservee apres le calcul", 'name="av_voiture_societe" class="form-control" value="1200"' in h and 'value="2026-10-07"' in h)
check("Page: erreur de saisie affichee", 'dernier jour du contrat' in env.get_template('fin_contrat.html').render(
      fc=dict(fc, erreur="Préavis non presté jusqu'à son terme : indiquez le dernier jour du contrat."), formulaire={}, **commun))
check("Page: pas de bouton retour propre a la page", 'btn-back' in io.open(os.path.join(RACINE, 'templates', 'fin_contrat.html'), encoding='utf-8').read(), False)

from dmfa import aide_dmfa
DOS = {'id': 7, 'nom': 'Société Fictive SRL', 'categorie_employeur': '010', 'code_ffe': 'C', 'code_importance': '1',
       'numero_unite_etablissement': '2.123.456.789'}
sortie = {'date_fin': date(2026, 10, 11), 'motif': 'licenciement', 'dmfa': json.dumps(dec['dmfa'], default=str)}   # relu de la base
doc = aide_dmfa(DOS, 2026, 4, [{'travailleur': {'id': 2, 'nom': 'Exemple', 'prenom': 'Camille'}, 'contrats': [CONTRAT], 'fiches': [],
                                'jours': [], 'sorties': [sortie]}])
tab = [x for x in doc['travailleurs'][0]['tableaux'] if x['titre'].startswith('Fin de contrat')]
check("Aide DmfA du trimestre de la sortie: tableau « Fin de contrat » avec les codes 3, 7 et 870", [l[0] for l in tab[0]['lignes']], ['3', '7', '870'])
check("... indemnite de rupture avec sa periode couverte (12/10/2026 au 27/12/2026) et son montant",
      (tab[0]['lignes'][0][2], tab[0]['lignes'][0][3]), ('12/10/2026 au 27/12/2026', '9 087,76'))
check("Sans decompte de sortie: pas de tableau", [x for x in aide_dmfa(DOS, 2026, 4, [{'travailleur': {'id': 2, 'nom': 'E', 'prenom': 'C'},
      'contrats': [CONTRAT], 'fiches': [], 'jours': []}])['travailleurs'][0]['tableaux'] if x['titre'].startswith('Fin de contrat')], [])
from cp_data import calcul_preavis_semaines
check("L'ancienne fonction de preavis renvoie a la table legale (4 mois, contrat de mars 2026: 4 semaines ; demission a 30 mois: 6)",
      (calcul_preavis_semaines(4, True, date(2026, 3, 2)), calcul_preavis_semaines(30, False, date(2024, 1, 1))), (4, 6))

print(); print("=" * 70)
if ECHECS:
    print(f"❌ {len(ECHECS)} TEST(S) ECHOUE(S): {ECHECS}"); sys.exit(1)
print("✅ TOUS LES TESTS PASSENT -- fin de contrat.")
