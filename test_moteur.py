# -*- coding: utf-8 -*-
"""
test_moteur.py -- DuxSalary
Tests de BOUT EN BOUT du moteur (calculer_fiche_paie), sur les dossiers reels.
Complement de test_profils.py (qui teste les briques une par une).
Lancer: python3 test_moteur.py   -- doit afficher TOUS LES TESTS PASSENT
"""
import sys
from datetime import date
from moteur_paie import calculer_fiche_paie as _calculer_fiche_paie
ECHECS = []
NB_CONTROLES_COUT = [0]

def calculer_fiche_paie(*args, **kwargs):
    """CONTROLE PERMANENT sur TOUS les cas de ce fichier: le cout employeur couvre
    au moins tout ce qui est verse ou retenu pour le travailleur --
    cout >= net + ONSS travailleur + precompte + cotisation speciale."""
    r = _calculer_fiche_paie(*args, **kwargs)
    css = -sum(l['montant'] for l in r['lignes_indemn'] if 'Cotisation spéciale' in l['libelle'])
    minimum = round(r['salaire_net'] + abs(r['onss_net']) + r['prime_onss'] + r['pecule_retenue']
                    + abs(r['precompte']) + r['prime_precompte'] + r['pecule_precompte'] + css, 2)
    NB_CONTROLES_COUT[0] += 1
    if r['cout_employeur'] + 0.005 < minimum:
        label = f"Cout employeur {r['cout_employeur']} < net + ONSS + precompte + CSS = {minimum} (cas n° {NB_CONTROLES_COUT[0]})"
        print(f"❌ {label}"); ECHECS.append(label)
    return r
def check(label, obtenu, attendu, tol=0.01):
    nombres = isinstance(obtenu, (int, float)) and isinstance(attendu, (int, float))
    ok = abs(obtenu - attendu) <= tol if nombres else obtenu == attendu
    print(f"{'✅' if ok else '❌'} {label}: obtenu={obtenu} attendu={attendu}")
    if not ok: ECHECS.append(label)

print("=" * 70); print("BILAL -- juillet 2026, CP 140.03 ouvrier, 98'H BARBER (cat 000)"); print("=" * 70)
r = calculer_fiche_paie('Bilal','Akattof','n','a','BE',date(2008,1,1),date(2026,7,9),'98H','a','b','r',
    'CP 140.03','Chauffeur',14.93, heures_semaine=38.0, heures_jour=3.0, jours_semaine=5, type_contrat='CDD',
    premier_engagement=True, jours_prestes=16, heures_prestees=48.0, jours_feries_payes=1, heures_feries=3.0,
    periode_debut=date(2026,7,1), periode_fin=date(2026,7,31))
# Valeurs au 01/10/2026 (sorties du moteur, non recoupees avec une fiche reelle de Bilal):
#  - ONSS personnel sur 108% + bonus emploi sur prestations reelles (Instructions p.176, p.449-453)
#  - plus d'avantage repas automatique (un cheque-repas conforme est exonere): le brut perd
#    16 x 1,09 = 17,44 -> 761,43 (51 h x 14,93)
#  - pas de cheques-repas sectoriels (moins de 6 mois d'anciennete)
check("Brut = 51 h x 14,93, sans avantage repas automatique", r['brut_onss'], 761.43)
check("ONSS personnel 13,07% x 108% (822,34)", -r['onss_travailleur'], 107.48)
check("Bonus emploi A (H/U = 0,29)", r['bonus_emploi_a'], 39.94)
check("Bonus emploi B (S = 14,93 x 174,8 = 2.609,76)", r['bonus_emploi_b'], 27.74)
check("Net", r['salaire_net'], 808.87)
check("Part reductible 25% x 108%", r['onss_patronal_reductible'], 205.59)
check("Vacances 5,57% non reductible", r['onss_vacances_trimestrielle'], 45.80)
check("Reduction structurelle (temps partiel)", r['reduction_structurelle'], 119.61)
check("Premier engagement", r['reduction_premier_engagement'], 85.98)
# Cotisations 255 (0,02%), 256 (0,01%, T3 2026) et 859 (0,10%) sur 822,34
# (Instructions ONSS 2026/3 p.340-341 et p.346)
codes_b = {c['code']: c['montant'] for c in r['cotisations_complementaires']}
check("255 accidents du travail 0,02% sur 108%", codes_b.get('255', 0), 0.16)
check("256 Fonds amiante 0,01% sur 108% (du au T3 2026)", codes_b.get('256', 0), 0.08)
check("859 chomage temporaire 0,10% sur 108%", codes_b.get('859', 0), 0.82)
check("ONSS patronal net = vacances + cotisations non reductibles", r['onss_patronal'], 47.68)
check("Bilal: moins de 6 mois d'anciennete -> aucun cheque-repas sectoriel", r['cr_empl_total'], 0.0)
check("Bilal: alerte expliquant pourquoi", 1.0 if any('Anciennete 0 mois' in a for a in r['alertes_calcul']) else 0.0, 1.0)

print(); print("=" * 70); print("FICHE REELLE Interconsult -- ouvrier 10/38, 15,2097 EUR/h (socle commun, CP 302 non geree)"); print("=" * 70)
# Fiches de sources/fiches_reference (CP 302): seul le socle ONSS personnel /
# bonus emploi est compare, via le profil ouvrier de la CP 140.03.
kw_i = dict(heures_semaine=38.0, heures_jour=2.0, jours_semaine=5, type_contrat='CDI',
            rgpt_actif=False, cheques_repas=False, categorie_employeur='017')
r = calculer_fiche_paie('M','N','n','a','BE',date(2005,10,31),date(2026,5,27),'S','a','b','r','CP 140.03','Nettoyeur',15.2097,
    jours_prestes=22, heures_prestees=44.0, jours_feries_payes=1, heures_feries=2.0,
    periode_debut=date(2026,7,1), periode_fin=date(2026,7,31), **kw_i)
check("Juillet: brut", r['brut_onss'], 699.65)
check("Juillet: ONSS personnel sur 108% (fiche 98,76)", -r['onss_travailleur'], 98.76)
check("Juillet: bonus emploi A (fiche 35,81)", r['bonus_emploi_a'], 35.81)
check("Juillet: bonus emploi B (fiche 21,16)", r['bonus_emploi_b'], 21.16)
r = calculer_fiche_paie('M','N','n','a','BE',date(2005,10,31),date(2026,5,27),'S','a','b','r','CP 140.03','Nettoyeur',15.2097,
    jours_prestes=3, heures_prestees=6.0, periode_debut=date(2026,5,27), periode_fin=date(2026,5,31), **kw_i)
check("Mai (entree le 27): ONSS personnel (fiche 12,88)", -r['onss_travailleur'], 12.88)
# 6 h sur 159,6 h -> H/U = 0,04 ; table du bonus au 01/04/2026 (A max 135,04)
check("Mai: bonus emploi A, mois incomplet (fiche 5,40)", r['bonus_emploi_a'], 5.40)
check("Mai: bonus emploi B, mois incomplet (fiche 5,28)", r['bonus_emploi_b'], 5.28)
r = calculer_fiche_paie('M','N','n','a','BE',date(2005,10,31),date(2026,5,27),'S','a','b','r','CP 140.03','Nettoyeur',15.2097,
    jours_prestes=22, heures_prestees=44.0, periode_debut=date(2026,6,1), periode_fin=date(2026,6,30), **kw_i)
check("Juin: bonus emploi A, table du 01/04/2026 (fiche 35,11)", r['bonus_emploi_a'], 35.11)
check("Juin: bonus emploi B, table du 01/04/2026 (fiche 25,55)", r['bonus_emploi_b'], 25.55)
# Vacances legales d'un ouvrier (code prestation 2), Instructions ONSS 2026/3 p.375-376:
# hors du H du salaire de reference S, mais DANS la fraction de prestation µ.
# Juin: S = 669,23 x 11,23 = 7.515,45 ; R = 552,04 + 325,08 = 877,12
#  sans conge: µ = 44 / 164,67 = 0,27 -> 877,12 x 0,27 x 1,18 / 3 = 93,15
#  5 jours de vacances (10 h): µ = 54 / 164,67 = 0,33 -> 877,12 x 0,33 x 1,18 / 3 = 113,85
rc = calculer_fiche_paie('M','N','n','a','BE',date(2005,10,31),date(2026,5,27),'S','a','b','r','CP 140.03','Nettoyeur',15.2097,
    jours_prestes=22, heures_prestees=44.0, jours_conge=5, periode_debut=date(2026,6,1), periode_fin=date(2026,6,30), **kw_i)
check("Sans conge: reduction structurelle 93,15", r['reduction_structurelle'], 93.15)
check("Vacances d'un ouvrier comptees dans µ (pas dans S): reduction structurelle 113,85", rc['reduction_structurelle'], 113.85)
check("... brut, ONSS personnel et net inchanges", (rc['brut_onss'], rc['onss_net'], rc['salaire_net']), (r['brut_onss'], r['onss_net'], r['salaire_net']))
check("Conges ouvrier sans effet sur le bonus emploi", rc['bonus_emploi'], r['bonus_emploi'])

print(); print("=" * 70); print("PLAFOND ANNUEL DU BONUS EMPLOI -- 3.594,36 EUR (Instructions ONSS 2026/3 p.453)"); print("=" * 70)
kw_p = dict(heures_semaine=38.0, heures_jour=2.0, jours_semaine=5, type_contrat='CDI', rgpt_actif=False,
            cheques_repas=False, jours_prestes=22, heures_prestees=44.0, jours_feries_payes=1, heures_feries=2.0,
            periode_debut=date(2026,7,1), periode_fin=date(2026,7,31))
rp = calculer_fiche_paie('M','N','n','a','BE',date(1990,1,1),date(2026,1,1),'S','a','b','r','CP 140.03','X',15.2097,
    bonus_emploi_cumul_annee=3550.00, **kw_p)
# reste 44,36 sous le plafond pour 35,81 + 21,16: le volet B est reduit en premier
check("Plafond: volet A conserve", rp['bonus_emploi_a'], 35.81)
check("Plafond: volet B limite au solde (44,36 - 35,81)", rp['bonus_emploi_b'], 8.55)
check("Plafond: alerte affichee", 1.0 if any('plafond annuel' in a for a in rp['alertes_calcul']) else 0.0, 1.0)
rp0 = calculer_fiche_paie('M','N','n','a','BE',date(1990,1,1),date(2026,1,1),'S','a','b','r','CP 140.03','X',15.2097,
    bonus_emploi_cumul_annee=3594.36, **kw_p)
check("Plafond deja atteint: plus de bonus", rp0['bonus_emploi'], 0.0)

print(); print("=" * 70); print("CIWAN -- octobre 2026, employe, Eysel (cat 010, FFE C, importance 1)"); print("=" * 70)
r = calculer_fiche_paie('Ciwan','Ilhan','n','a','BE',date(2004,11,17),date(2026,10,1),'Eysel','a','b','r',
    'CP 336','Comptable',13.71, heures_semaine=38.0, heures_jour=7.6, jours_semaine=5, type_contrat='CDI',
    premier_engagement=True, salaire_mensuel_fixe=2257.0, jours_prestes=22, heures_prestees=167.2,
    frais_nets=200.0, km_domicile=12, taux_km=0.08, rgpt_actif=False, cheques_repas=False,
    categorie_employeur='010', code_ffe='C', code_importance='1',
    periode_debut=date(2026,10,1), periode_fin=date(2026,10,31))
# 30/09/2026: CSS au bareme officiel ONSS (11,07 au lieu de 19,33) -> +8,26 EUR net
check("Net (CSS officielle 11,07)", r['salaire_net'], 2341.16)
css_l = next(l['montant'] for l in r['lignes_indemn'] if 'Cotisation spéciale' in l['libelle'])
check("Cotisation speciale SS (bareme ONSS 2022+, isole)", css_l, -11.07)
check("Reduction structurelle (Group S 398,98)", r['reduction_structurelle'], 398.98)
check("Premier engagement (Group S 165,27)", r['reduction_premier_engagement'], 165.27)
codes = {c['code']: c['montant'] for c in r['cotisations_complementaires']}
check("810 FFE speciale 0,10%", codes.get('810', 0), 2.26)
check("809 FFE base commercial 0,34%", codes.get('809', 0), 7.67)
check("831 Fonds social CP 200 0,23%", codes.get('831', 0), 5.19)
check("255 accidents du travail 0,02%", codes.get('255', 0), 0.45)
check("859 chomage temporaire 0,10%", codes.get('859', 0), 2.26)
check("256 Fonds amiante NON du au T4 2026 (malgre le fichier T3 reporte)", codes.get('256', 0), 0.0)
# 2,26 + 7,67 + 5,19 + 0,45 + 2,26 = 17,83 (etait 15,12 sans les codes 255 et 859)
check("ONSS patronal net", r['onss_patronal'], 17.83)
# 01/10/2026: les frais propres a l'employeur (200) font partie du cout:
# 2257 + 17,83 + km 42,24 + 200 = 2.517,07 (etait 2.317,07)
check("Cout employeur, frais propres inclus", r['cout_employeur'], 2517.07)
ligne_sal = next(l for b in r['detail_calcul'] if b['titre'] == 'Rémunération brute' for l in b['lignes'] if l['libelle'] == 'Salaire mensuel')
check("Detail du calcul: base de « Salaire mensuel » = salaire mensuel (pas le taux horaire)", ligne_sal['base'], 2257.00)
check("Alerte T4 non publie presente", 1.0 if any('2026Q4' in a for a in r['alertes_calcul']) else 0.0, 1.0)

print(); print("=" * 70); print("CIWAN -- mois en cours, seulement 15 jours encodes (employe au mois)"); print("=" * 70)
r15 = calculer_fiche_paie('Ciwan','Ilhan','n','a','BE',date(2004,11,17),date(2026,10,1),'Eysel','a','b','r',
    'CP 200','Comptable',13.71, heures_semaine=38.0, heures_jour=7.6, jours_semaine=5, type_contrat='CDI',
    premier_engagement=True, salaire_mensuel_fixe=2257.0, jours_prestes=15, heures_prestees=114.0,
    rgpt_actif=False, cheques_repas=False, categorie_employeur='010', code_ffe='C', code_importance='1',
    periode_debut=date(2026,10,1), periode_fin=date(2026,10,31))
check("Reduction structurelle = mois complet (398,98) meme si calendrier incomplet", r15['reduction_structurelle'], 398.98)
check("Premier engagement = mois complet (165,27)", r15['reduction_premier_engagement'], 165.27)

print(); print("=" * 70); print("ETUDIANT -- solidarite uniquement"); print("=" * 70)
r = calculer_fiche_paie('Ryad','Draoui','n','a','BE',date(2005,1,1),date(2026,8,1),'98H','a','b','r',
    'CP 140.03','Etudiant',14.93, heures_semaine=38.0, heures_jour=7.6, jours_semaine=5, type_contrat='STU',
    is_etudiant=True, jours_prestes=12, heures_prestees=91.2, rgpt_actif=False, cheques_repas=False,
    periode_debut=date(2026,8,1), periode_fin=date(2026,8,31))
check("Patronal = 5,43% du brut", r['onss_patronal'], round(r['brut_onss'] * 0.0543, 2))
check("Aucune cotisation complementaire", len(r['cotisations_complementaires']), 0)
check("Aucune reduction", r['reduction_structurelle'] + r['reduction_premier_engagement'], 0.0)

print(); print("=" * 70); print("CHEQUES-REPAS -- calcul du suivi repris sur la fiche (CP 121: 64 h / 7,4 = 9 cheques)"); print("=" * 70)
from cheques_regles import cheques_repas_du_mois
cr = cheques_repas_du_mois('CP 121', 'ouvrier', 2026, 10, 16, 64.0, date(2026, 3, 1), {'actif': False})
check("Nombre de cheques (heures / 7,4 arrondi sup.)", cr['nombre'], 9)
r = calculer_fiche_paie('Nadia','Test','n','a','BE',date(1990,1,1),date(2026,3,1),'Test','a','b','r',
    'CP 121','Nettoyeuse',17.17, heures_semaine=37.0, heures_jour=4.0, jours_semaine=5, type_contrat='CDI',
    jours_prestes=16, heures_prestees=64.0, rgpt_actif=False, cheques_repas=False, cheques_repas_calc=cr,
    periode_debut=date(2026,10,1), periode_fin=date(2026,10,31))
ligne = next((l for l in r['lignes_indemn'] if 'Chèques-repas' in l['libelle']), None)
check("Part travailleur retenue sur la fiche (9 x 1,09)", ligne['montant'] if ligne else 0, -9.81)
check("Part employeur dans le cout (9 x 2,00)", r['cr_empl_total'], 18.00)

print(); print("=" * 70); print("ALLOCATIONS EXCEPTIONNELLES -- prime de fin d'annee et double pecule"); print("=" * 70)
base_kw = dict(heures_semaine=38.0, heures_jour=7.6, jours_semaine=5, type_contrat='CDI', premier_engagement=False,
               jours_prestes=22, heures_prestees=167.2, rgpt_actif=False, cheques_repas=False,
               categorie_employeur='000', code_ffe='C', code_importance='1')
sans = calculer_fiche_paie('A','B','n','a','BE',date(1990,1,1),date(2020,1,1),'X','a','b','r','CP 200','Employe',13.71,
    salaire_mensuel_fixe=2257.0, periode_debut=date(2026,12,1), periode_fin=date(2026,12,31), **base_kw)
avec = calculer_fiche_paie('A','B','n','a','BE',date(1990,1,1),date(2020,1,1),'X','a','b','r','CP 200','Employe',13.71,
    salaire_mensuel_fixe=2257.0, prime_exceptionnelle=2257.0, periode_debut=date(2026,12,1), periode_fin=date(2026,12,31), **base_kw)
check("Prime: ONSS 13,07%", avec['prime_onss'], round(2257 * 0.1307, 2))
# remuneration annuelle normale 27.084 EUR -> tranche 26.340-31.830: 40,38% (autres allocations)
check("Prime: precompte 40,38% sur (2257 - ONSS)", avec['prime_precompte'], round((2257 - round(2257*0.1307, 2)) * 0.4038, 2))
# La CSS du mois inclut la prime (remuneration brute du trimestre, primes comprises)
css_de = lambda d: next((l['montant'] for l in d['lignes_indemn'] if 'Cotisation spéciale' in l['libelle']), 0)
check("Prime: net du mois = net prime - hausse de la CSS", round(avec['salaire_net'] - sans['salaire_net'], 2),
      round(avec['net_exceptionnel'] + css_de(avec) - css_de(sans), 2))
check("Salaire regulier inchange (bonus emploi non touche)", avec['bonus_emploi'], sans['bonus_emploi'])

# Fiche REELLE SD Worx juin 2024 (Leo): pecule 2.462,21 / retenue 297,33 / precompte saisi 786,72
r = calculer_fiche_paie('Leo','P','n','a','BE',date(2002,1,1),date(2024,1,1),'X','a','b','r','CP 336','Comptable',16.47,
    salaire_mensuel_fixe=2700.0, double_pecule=2462.21, precompte_pecule_manuel=786.72,
    periode_debut=date(2026,6,1), periode_fin=date(2026,6,30), **base_kw)
check("Pecule: retenue 13,07% sur 85/92 (fiche reelle 297,33)", r['pecule_retenue'], 297.33)
check("Pecule: precompte saisi repris (786,72)", r['pecule_precompte'], 786.72)
check("Pecule: net = 2462,21 - 297,33 - 786,72", r['net_exceptionnel'], 1378.16)
r2 = calculer_fiche_paie('Leo','P','n','a','BE',date(2002,1,1),date(2024,1,1),'X','a','b','r','CP 336','Comptable',16.47,
    salaire_mensuel_fixe=2700.0, double_pecule=2462.21, periode_debut=date(2026,6,1), periode_fin=date(2026,6,30), **base_kw)
# 2026: remuneration annuelle 32.400 -> tranche 31.830-34.640: 39,37% (double pecule)
check("Pecule: precompte automatique bareme 2026 (39,37%)", r2['pecule_precompte'], round((2462.21 - 297.33) * 0.3937, 2))

print(); print("=" * 70); print("SITUATION FAMILIALE -- enfants et charges de famille"); print("=" * 70)
kw_f = dict(heures_semaine=38.0, heures_jour=7.6, jours_semaine=5, type_contrat='CDI', jours_prestes=22, heures_prestees=167.2,
            rgpt_actif=False, cheques_repas=False, salaire_mensuel_fixe=3000.0,
            periode_debut=date(2026,10,1), periode_fin=date(2026,10,31))
base = calculer_fiche_paie('A','B','n','a','BE',date(1990,1,1),date(2020,1,1),'X','a','b','r','CP 200','E',18.0, **kw_f)
dep = calculer_fiche_paie('A','B','n','a','BE',date(1990,1,1),date(2020,1,1),'X','a','b','r','CP 200','E',18.0,
                          charges_famille={'nb_personnes_charge_dependance': 1}, **kw_f)
check("Personne 65+ dependante: -166 EUR/mois de precompte (1.992/12)", round(abs(base['precompte']) - abs(dep['precompte']), 2), 166.0)
e2 = calculer_fiche_paie('A','B','n','a','BE',date(1990,1,1),date(2020,1,1),'X','a','b','r','CP 200','E',18.0, nb_enfants=2, **kw_f)
check("2 enfants (dont 1 handicape transmis comme 2 = 3): reduction annexe 3", round(abs(base['precompte']) - abs(
      calculer_fiche_paie('A','B','n','a','BE',date(1990,1,1),date(2020,1,1),'X','a','b','r','CP 200','E',18.0, nb_enfants=3, **kw_f)['precompte']), 2), 367.0)

# Tache 3: les autres charges de famille des formulaires travailleur (annexes 4 et 5 de la formule-cle)
def pp(etat_civil='celibataire', partenaire='non', **charges):
    return abs(calculer_fiche_paie('A','B','n','a','BE',date(1990,1,1),date(2020,1,1),'X','a','b','r','CP 200','E',18.0,
        etat_civil=etat_civil, partenaire_revenus_pro=partenaire, charges_famille=charges or None, **kw_f)['precompte'])
check("Parent isole avec enfant a charge: -52 EUR/mois (624/12)", round(pp() - pp(parent_isole=True), 2), 52.0)
check("Parent isole: sans effet pour une personne mariee", round(pp('marie', 'oui') - pp('marie', 'oui', parent_isole=True), 2), 0.0)
check("Travailleur handicape: -52 EUR/mois", round(pp() - pp(handicape=True), 2), 52.0)
check("Conjoint handicape (conjoint sans revenus): -52 EUR/mois", round(pp('marie', 'non') - pp('marie', 'non', conjoint_handicape=True), 2), 52.0)
check("Conjoint handicape: sans effet si le conjoint a des revenus", round(pp('marie', 'oui') - pp('marie', 'oui', conjoint_handicape=True), 2), 0.0)
check("Autres personnes a charge: -52 EUR/mois chacune (2 personnes)", round(pp() - pp(nb_autres_personnes_charge=2), 2), 104.0)
check("Personnes de 65 ans et plus dependantes: -166 EUR/mois chacune (2 personnes)", round(pp() - pp(nb_personnes_charge_dependance=2), 2), 332.0)
check("Cumul: parent isole + handicap + 1 autre personne + 1 personne 65+ = -322 EUR/mois",
      round(pp() - pp(parent_isole=True, handicape=True, nb_autres_personnes_charge=1, nb_personnes_charge_dependance=1), 2), 322.0)

print(); print("=" * 70); print("RGPT CP 121 -- par JOUR (1,63 EUR)"); print("=" * 70)
r = calculer_fiche_paie('N','T','n','a','BE',date(1990,1,1),date(2026,3,1),'X','a','b','r','CP 121','Nettoyeuse',17.17,
    heures_semaine=37.0, heures_jour=4.0, jours_semaine=5, type_contrat='CDI', jours_prestes=16, heures_prestees=64.0,
    rgpt_actif=True, cheques_repas=False, periode_debut=date(2026,10,1), periode_fin=date(2026,10,31))
rg = next((l['montant'] for l in r['lignes_indemn'] if 'RGPT' in l['libelle']), 0)
check("RGPT = 16 jours x 1,63 (et non 64 h x 1,63)", rg, 26.08)

print(); print("=" * 70); print("CHEQUES-REPAS -- source unique cheques_regles.py, la configuration du dossier prime"); print("=" * 70)
import io, os
from cheques_regles import cheques_repas_du_mois
def fiche_cr(cp, statut_cat, taux, entree, debut, fin, jours, heures, **kw):
    """Fiche avec la case cheques-repas cochee ; retourne (part employeur, part travailleur retenue, alertes cheques)."""
    r = calculer_fiche_paie('A','B','n','a','BE',date(1990,1,1),entree,'X','a','b','r',cp,statut_cat,taux,
        **dict(dict(heures_semaine=38.0, heures_jour=7.6, jours_semaine=5, type_contrat='CDI', jours_prestes=jours,
                    heures_prestees=heures, rgpt_actif=False, cheques_repas=True, periode_debut=debut, periode_fin=fin), **kw))
    retenue = -sum(l['montant'] for l in r['lignes_indemn'] if 'Chèques-repas' in l['libelle'])
    return r['cr_empl_total'], round(retenue, 2), [a for a in r['alertes_calcul'] if 'hèques-repas' in a]
OCT = (date(2026,10,1), date(2026,10,31))
e, t, a = fiche_cr('CP 140.03', 'Chauffeur', 15.50, date(2025,1,1), *OCT, 22, 167.2)
check("CP 140.03, plus de 6 mois: 22 jours x 2,00 employeur", e, 44.00)
check("CP 140.03: 22 x 1,09 retenus au travailleur", t, 23.98)
e, t, a = fiche_cr('CP 140.03', 'Chauffeur', 15.50, date(2025,1,1), date(2026,6,1), date(2026,6,30), 22, 167.2)
check("CP 140.03 avant le 01/07/2026 (entree en vigueur): aucun cheque, alerte", (e, t, len(a)), (0.0, 0.0, 1))
e, t, a = fiche_cr('CP 140.03', 'Chauffeur', 15.50, date(2026,8,1), *OCT, 22, 167.2)
check("CP 140.03, moins de 6 mois d'anciennete: aucun cheque, alerte", (e, t, len(a)), (0.0, 0.0, 1))
e, t, a = fiche_cr('CP 121', 'Nettoyeuse', 17.17, date(2026,9,1), *OCT, 16, 64.0, heures_semaine=37.0, heures_jour=4.0)
check("CP 121: heures / 7,4 arrondi superieur = 9 cheques x 2,00 (et non 16 jours)", e, 18.00)
check("CP 121: 9 x 1,09 retenus", t, 9.81)
e, t, a = fiche_cr('CP 200', 'Employe', 13.71, date(2020,1,1), *OCT, 22, 167.2, salaire_mensuel_fixe=2257.0)
check("CP 200, case cochee sans configuration du dossier: aucun cheque (pas d'obligation), alerte", (e, t, len(a)), (0.0, 0.0, 1))
e, t, a = fiche_cr('CP 336', 'Comptable', 13.71, date(2020,1,1), *OCT, 22, 167.2, salaire_mensuel_fixe=2257.0)
check("CP 336, case cochee sans configuration du dossier: aucun cheque, alerte", (e, t, len(a)), (0.0, 0.0, 1))
e, t, a = fiche_cr('CP 140.03', 'Etudiant', 15.50, date(2025,1,1), *OCT, 22, 167.2, type_contrat='STU', is_etudiant=True)
check("Etudiant: non vise par l'obligation sectorielle", (e, t), (0.0, 0.0))
# Dossier a 8 EUR (6,91 employeur + 1,09 travailleur): la configuration du dossier prime
cfg8 = {'actif': True, 'valeur': 8.00, 'part_patronale': 6.91, 'part_travailleur': 1.09}
cr8 = cheques_repas_du_mois('CP 140.03', 'ouvrier', 2026, 10, 22, 167.2, date(2025,1,1), cfg8)
e, t, a = fiche_cr('CP 140.03', 'Chauffeur', 15.50, date(2025,1,1), *OCT, 22, 167.2, cheques_repas_calc=cr8)
check("Dossier a 8 EUR en CP 140.03: 22 x 6,91 employeur (plus que le minimum sectoriel)", e, 152.02)
check("Dossier a 8 EUR: 22 x 1,09 travailleur, aucune alerte (dans le cadre legal)", (t, len(a)), (23.98, 0))
cr8_200 = cheques_repas_du_mois('CP 200', 'employe', 2026, 10, 22, 167.2, date(2020,1,1), cfg8)
e, t, a = fiche_cr('CP 200', 'Employe', 13.71, date(2020,1,1), *OCT, 22, 167.2, salaire_mensuel_fixe=2257.0, cheques_repas_calc=cr8_200)
check("Dossier a 8 EUR en CP 200 (aucune obligation): les cheques du dossier s'appliquent", (e, t), (152.02, 23.98))
hors = cheques_repas_du_mois('CP 200', 'employe', 2026, 10, 22, 167.2, date(2020,1,1),
                             {'actif': True, 'valeur': 11.00, 'part_patronale': 10.00, 'part_travailleur': 1.00})
e, t, a = fiche_cr('CP 200', 'Employe', 13.71, date(2020,1,1), *OCT, 22, 167.2, salaire_mensuel_fixe=2257.0, cheques_repas_calc=hors)
check("Hors cadre legal (11 EUR, 10 employeur, 1 travailleur): trois alertes dans le calcul", len(a), 3)
sous = cheques_repas_du_mois('CP 140.03', 'ouvrier', 2026, 10, 22, 167.2, date(2025,1,1),
                             {'actif': True, 'valeur': 2.50, 'part_patronale': 1.41, 'part_travailleur': 1.09})
check("Dossier sous le minimum sectoriel (1,41 < 2,00 employeur): alerte", 1.0 if any('minimum sectoriel' in x for x in sous['alertes']) else 0.0, 1.0)
racine = os.path.dirname(os.path.abspath(__file__))
en_dur = [f for f in ('moteur_paie.py', 'regles_cp.py', 'profil_travailleur.py', 'contrats.py', 'cp_data.py')
          if any(m in io.open(os.path.join(racine, f), encoding='utf-8').read() for m in ('6.91', '5.82', '3,09', '3.09', 'cr_part_empl_jour'))]
check("Aucun montant de cheque-repas ecrit hors de cheques_regles.py", 1.0 if not en_dur else 0.0, 1.0)
if en_dur: print("   fichiers concernes:", en_dur)

print(); print("=" * 70); print("REPAS FOURNIS PAR L'EMPLOYEUR -- avantage de toute nature, option du dossier"); print("=" * 70)
kw_r = dict(heures_semaine=38.0, heures_jour=7.6, jours_semaine=5, type_contrat='CDI', jours_prestes=22, heures_prestees=167.2,
            rgpt_actif=False, periode_debut=date(2026,10,1), periode_fin=date(2026,10,31))
base_r = calculer_fiche_paie('A','B','n','a','BE',date(1990,1,1),date(2025,1,1),'X','a','b','r','CP 140.03','Chauffeur',15.50,
    cheques_repas=True, **kw_r)
check("Cheques-repas coches, option desactivee: aucun avantage repas dans le brut", base_r['brut_onss'], round(15.50 * 167.2, 2))
check("Aucune ligne d'avantage repas", len([l for l in base_r['lignes_salaire'] if 'repas' in l['libelle'].lower()]), 0)
avec_r = calculer_fiche_paie('A','B','n','a','BE',date(1990,1,1),date(2025,1,1),'X','a','b','r','CP 140.03','Chauffeur',15.50,
    cheques_repas=True, repas_fournis=True, **kw_r)
check("Option activee: 22 repas x 1,09 ajoutes au brut (Instructions ONSS p.76)", round(avec_r['brut_onss'] - base_r['brut_onss'], 2), 23.98)
check("Soumis ONSS: cotisation personnelle plus elevee", 1.0 if -avec_r['onss_travailleur'] > -base_r['onss_travailleur'] else 0.0, 1.0)
check("Avantage recu en nature: retire du net a payer", next(l['montant'] for l in avec_r['lignes_indemn'] if 'reçu en nature' in l['libelle']), -23.98)
check("Net plus bas qu'avant (cotisations sur l'avantage, rien de verse en plus)", 1.0 if avec_r['salaire_net'] < base_r['salaire_net'] else 0.0, 1.0)
check("Meme option dans toutes les CP (CP 200)", round(
    calculer_fiche_paie('A','B','n','a','BE',date(1990,1,1),date(2020,1,1),'X','a','b','r','CP 200','E',13.71, salaire_mensuel_fixe=2257.0,
        cheques_repas=False, repas_fournis=True, **kw_r)['brut_onss'], 2), 2280.98)
avant = calculer_fiche_paie('A','B','n','a','BE',date(1990,1,1),date(2020,1,1),'X','a','b','r','CP 200','E',13.71, salaire_mensuel_fixe=2257.0,
    cheques_repas=False, repas_fournis=True, **dict(kw_r, periode_debut=date(2026,6,1), periode_fin=date(2026,6,30)))
check("Montant charge pour 2026 seulement: toujours applique en juin 2026", round(avant['brut_onss'], 2), 2280.98)

print(); print("=" * 70); print("ALERTE -- salaire sous le minimum de la CP a la date de la periode"); print("=" * 70)
kw_m = dict(heures_semaine=38.0, heures_jour=7.6, jours_semaine=5, jours_prestes=22, heures_prestees=167.2,
            rgpt_actif=False, cheques_repas=False)
def alerte_min(r):
    return next((a for a in r['alertes_calcul'] if 'minimum' in a.lower() or 'Minimum' in a), '')
r = calculer_fiche_paie('A','B','n','a','BE',date(1990,1,1),date(2026,1,1),'X','a','b','r','CP 336','Minimum sectoriel',13.50,
    salaire_mensuel_fixe=2200.0, type_contrat='CDI', periode_debut=date(2026,10,1), periode_fin=date(2026,10,31), **kw_m)
check("Employe CP 336 a 2.200 < 2.254,30: alerte", 1.0 if 'inférieur au minimum de la CP 336' in alerte_min(r) and '2 254,30' in alerte_min(r) else 0.0, 1.0)
check("L'alerte ne modifie pas le salaire saisi", r['brut_onss'], 2200.0)
r = calculer_fiche_paie('A','B','n','a','BE',date(1990,1,1),date(2026,1,1),'X','a','b','r','CP 336','Minimum sectoriel',13.71,
    salaire_mensuel_fixe=2257.0, type_contrat='CDI', periode_debut=date(2026,10,1), periode_fin=date(2026,10,31), **kw_m)
check("Employe CP 336 a 2.257: pas d'alerte", 0.0 if alerte_min(r) else 1.0, 1.0)
r = calculer_fiche_paie('A','B','n','a','BE',date(1990,1,1),date(2026,1,1),'X','a','b','r','CP 336','Minimum sectoriel',13.71,
    salaire_mensuel_fixe=1128.5, type_contrat='CDI', periode_debut=date(2026,10,1), periode_fin=date(2026,10,31),
    **dict(kw_m, heures_jour=3.8))
check("Mi-temps a 1.128,50 (= 2.257 temps plein): pas d'alerte", 0.0 if alerte_min(r) else 1.0, 1.0)
r = calculer_fiche_paie('A','B','n','a','BE',date(1990,1,1),date(2026,1,1),'X','a','b','r','CP 336','Minimum sectoriel',13.71,
    salaire_mensuel_fixe=2257.0, type_contrat='CDI', periode_debut=date(2026,6,1), periode_fin=date(2026,6,30), **kw_m)
check("Periode anterieure au bareme connu (juin 2026, CP 336): minimum non disponible, pas de comparaison",
      1.0 if 'non disponible pour cette période' in alerte_min(r) else 0.0, 1.0)
r = calculer_fiche_paie('A','B','n','a','BE',date(2005,1,1),date(2026,10,1),'X','a','b','r','CP 336','Etudiant',13.00,
    type_contrat='STU', is_etudiant=True, periode_debut=date(2026,10,1), periode_fin=date(2026,10,31), **kw_m)
check("Etudiant CP 336 a 13,00 < 13,0056 (officiel: 2.141,59 par mois, etudiants et alternance): alerte",
      1.0 if 'Étudiants et formation en alternance' in alerte_min(r) and '13,0056' in alerte_min(r) else 0.0, 1.0)
r = calculer_fiche_paie('A','B','n','a','BE',date(2005,1,1),date(2026,10,1),'X','a','b','r','CP 336','Etudiant',13.10,
    type_contrat='STU', is_etudiant=True, periode_debut=date(2026,10,1), periode_fin=date(2026,10,31), **kw_m)
check("Etudiant CP 336 a 13,10: pas d'alerte", 0.0 if alerte_min(r) else 1.0, 1.0)
r = calculer_fiche_paie('A','B','n','a','BE',date(2005,1,1),date(2026,8,1),'X','a','b','r','CP 140.03','Personnel roulant — Niveau 1',13.00,
    type_contrat='STU', is_etudiant=True, periode_debut=date(2026,8,1), periode_fin=date(2026,8,31), **kw_m)
check("Etudiant CP 140.03 a 13,00 < 13,4329 (officiel: 90 % du salaire de la fonction, 14,9255)",
      1.0 if '13,4329' in alerte_min(r) and '90 %' in alerte_min(r) else 0.0, 1.0)
r = calculer_fiche_paie('A','B','n','a','BE',date(2005,1,1),date(2026,8,1),'X','a','b','r','CP 140.03','Personnel roulant — Niveau 1',14.00,
    type_contrat='STU', is_etudiant=True, periode_debut=date(2026,8,1), periode_fin=date(2026,8,31), **kw_m)
check("Etudiant CP 140.03 a 14,00: pas d'alerte", 0.0 if alerte_min(r) else 1.0, 1.0)

print(); print("=" * 70); print("TACHE 4 -- baremes officiels salairesminimums.be: CP 336, 140.03 et 121"); print("=" * 70)
from baremes_experience import bareme_categories_en_vigueur, minimum_categorie
v336, v140, v121 = (bareme_categories_en_vigueur(c, date(2026,10,1)) for c in ('CP 336', 'CP 140.03', 'CP 121'))
check("CP 336 au 01/09/2026: minimum sectoriel, minimum d'entree, etudiants",
      (v336['date_debut'], v336['categories']['Minimum sectoriel'], v336['categories']["Minimum d'entrée"], v336['etudiants']['mensuel']),
      (date(2026,9,1), 2254.30, 2321.93, 2141.59))
check("CP 140.03 au 01/01/2026: 21 categories, deux regimes", (v140['date_debut'], len(v140['categories']), len(v140['categories_repos_payes'])),
      (date(2026,1,1), 21, 21))
check("CP 140.03: personnel roulant niveau 1 (38 h: 14,9255 ; repos compensatoire payes: 14,5425)",
      (v140['categories']['Personnel roulant — Niveau 1'], v140['categories_repos_payes']['Personnel roulant — Niveau 1']), (14.9255, 14.5425))
check("CP 140.03: garage hors categorie et non roulant classe 8", (v140['categories']['Personnel de garage — Hors catégorie'],
      v140['categories']['Personnel non roulant — Classe 8']), (23.2605, 18.3915))
from regles_cp import get_regles_cp
from cp_data import get_heures_semaine, get_heures_jour
check("CP 121: 37 h par semaine partout (regles, contrats, 7,4 h par jour)",
      (get_regles_cp('CP 121')['heures_semaine_defaut'], get_heures_semaine('CP 121'), get_heures_jour('CP 121')), (37, 37, 7.4))
check("CP 121 au 01/07/2026: 40 categories, regime 37 h", (v121['date_debut'], len(v121['categories']), v121['heures_semaine']), (date(2026,7,1), 40, 37))
check("CP 121: 1.A 17,1660 ; 2.E 18,9890 ; 4.D laveur de vitres 18 mois 20,5235 ; 10.F 23,6290",
      tuple(v121['categories'][k] for k in ('1.A. Nettoyage habituel', '2.E. Désinfection', '4.D. Laveur de vitres qualifié (18 mois)',
                                             "10.F. Centre d'enfouissement — ouvrier hautement qualifié")), (17.166, 18.989, 20.5235, 23.629))
check("Ancien libelle de contrat reconnu par son code (« Cat 2E — Désinfection »)",
      minimum_categorie('CP 121', date(2026,10,1), 'Cat 2E — Désinfection')[0]['horaire'], 18.989)
check("Ancien libelle CP 336 « Professionnel libéral (103%) » = minimum d'entree officiel",
      minimum_categorie('CP 336', date(2026,10,1), 'Professionnel libéral (103%)')[0]['mensuel'], 2321.93)
check("Avant la date du bareme officiel: pas de bareme officiel (rien de devine)",
      (bareme_categories_en_vigueur('CP 121', date(2026,6,30)), bareme_categories_en_vigueur('CP 336', date(2026,8,31))), (None, None))
r = calculer_fiche_paie('A','B','n','a','BE',date(1990,1,1),date(2026,1,1),'X','a','b','r','CP 121','Cat 2E — Désinfection',18.50,
    type_contrat='CDI', periode_debut=date(2026,10,1), periode_fin=date(2026,10,31), **dict(kw_m, heures_semaine=37.0))
check("CP 121 categorie 2.E a 18,50 < 18,9890: alerte avec la source officielle",
      1.0 if '18,9890' in alerte_min(r) and 'salairesminimums.be' in alerte_min(r) else 0.0, 1.0)
r = calculer_fiche_paie('A','B','n','a','BE',date(1990,1,1),date(2026,1,1),'X','a','b','r','CP 140.03','Personnel roulant — Niveau 2',15.20,
    type_contrat='CDI', periode_debut=date(2026,10,1), periode_fin=date(2026,10,31), **kw_m)
check("CP 140.03 niveau 2 a 15,20 < 15,4490: l'alerte rappelle le taux du regime repos compensatoire payes (15,0525)",
      1.0 if '15,4490' in alerte_min(r) and '15,0525' in alerte_min(r) else 0.0, 1.0)
r = calculer_fiche_paie('A','B','n','a','BE',date(1990,1,1),date(2026,1,1),'X','a','b','r','CP 140.03','Personnel roulant — Niveau 2',15.00,
    type_contrat='CDI', periode_debut=date(2026,8,1), periode_fin=date(2026,8,31), **kw_m)
check("Ouvrier CP 140.03 niveau 2 a 15,00 < 15,4490 (categorie du contrat): alerte", 1.0 if '15,4490' in alerte_min(r) else 0.0, 1.0)

print(); print("=" * 70); print("TACHE 4 -- CP 200: bareme par classe et annees d'experience (01/01/2026)"); print("=" * 70)
from baremes_experience import grille_en_vigueur, minimum_experience
g200 = grille_en_vigueur('CP 200', date(2026,10,1))
check("Grille CP 200: 27 lignes (0 a 26 ans) en bareme I, 26 en bareme II", (len(g200['bareme_I']), len(g200['bareme_II'])), (27, 26))
check("Source officielle, sans mention « a confirmer »", ('salairesminimums.be' in g200['source'], 'confirmer' in g200['source']), (True, False))
check("Bareme I, 0 an, classes A a D (PDF officiel)", g200['bareme_I'][0], (2242.80, 2336.26, 2369.30, 2555.72))
check("Bareme II, 26 ans, classes A a D (PDF officiel)", g200['bareme_II'][26], (2526.17, 2897.81, 3262.72, 3722.54))
check("Pas de grille avant le 01/01/2026 (rien de devine)", grille_en_vigueur('CP 200', date(2025,12,31)), None)
check("Au-dela de 26 ans d'experience: plafonne a 26 ans", minimum_experience('CP 200', date(2026,10,1), 'Classe D', 40, 0)[0]['mensuel'], 3622.42)
def fiche200(mensuel, categorie, experience, entree, debut_contrat=None, fin=date(2026,10,31), **kw):
    r = calculer_fiche_paie('A','B','n','a','BE',date(1990,1,1),entree,'X','a','b','r','CP 200',categorie,13.71,
        salaire_mensuel_fixe=mensuel, annees_experience=experience, date_debut_contrat=debut_contrat or entree,
        **dict(dict(heures_semaine=38.0, heures_jour=7.6, jours_semaine=5, type_contrat='CDI', jours_prestes=22, heures_prestees=167.2,
                    rgpt_actif=False, cheques_repas=False, periode_debut=date(fin.year, fin.month, 1), periode_fin=fin), **kw))
    return alerte_min(r)
ENTREE = date(2026,9,1)   # premiere annee dans l'entreprise -> bareme I
check("Classe C, 5 ans, bareme I: 2.563,77 -- salaire 2.500: alerte",
      1.0 if '2 563,77' in fiche200(2500.0, 'Classe C — Spécialisé', 5, ENTREE) else 0.0, 1.0)
check("Classe C, 5 ans: salaire 2.563,77: pas d'alerte", 0.0 if fiche200(2563.77, 'Classe C — Spécialisé', 5, ENTREE) else 1.0, 1.0)
check("Meme salaire, classe A 5 ans (2.276,53): pas d'alerte", 0.0 if fiche200(2300.0, 'Classe A — Sans qualification', 5, ENTREE) else 1.0, 1.0)
check("Apres un an dans l'entreprise: bareme II (classe A, 1 an: 2.310,29)",
      1.0 if '2 310,29' in fiche200(2300.0, 'Classe A — Sans qualification', 0, date(2025,9,1)) and 'barème II' in
      fiche200(2300.0, 'Classe A — Sans qualification', 0, date(2025,9,1)) else 0.0, 1.0)
check("L'experience progresse avec le contrat: 5 ans a la signature le 01/09/2025 -> 6 ans en octobre 2026 (bareme II: 2.681,48)",
      1.0 if '2 681,48' in fiche200(2600.0, 'Classe C — Spécialisé', 5, date(2025,9,1)) else 0.0, 1.0)
check("Experience non renseignee: 0 an, signale dans l'alerte",
      1.0 if "années d'expérience non renseignées" in fiche200(2000.0, 'Classe A — Sans qualification', None, ENTREE) else 0.0, 1.0)
check("Classe non precisee: classe A, signale", 1.0 if 'classe non précisée' in fiche200(2000.0, 'Employe', 0, ENTREE) else 0.0, 1.0)
r = calculer_fiche_paie('A','B','n','a','BE',date(2007,6,1),date(2026,10,1),'X','a','b','r','CP 200','Etudiant',11.50,
    type_contrat='STU', is_etudiant=True, **kw_m, periode_debut=date(2026,10,1), periode_fin=date(2026,10,31))
check("Etudiant CP 200 de 19 ans a 11,50 < 11,9988 (bareme des etudiants: 1.975,81 / mois): alerte",
      1.0 if 'Barème des étudiants, 19 ans' in alerte_min(r) and '11,9988' in alerte_min(r) else 0.0, 1.0)
r = calculer_fiche_paie('A','B','n','a','BE',date(2007,6,1),date(2026,10,1),'X','a','b','r','CP 200','Etudiant',12.00,
    type_contrat='STU', is_etudiant=True, **kw_m, periode_debut=date(2026,10,1), periode_fin=date(2026,10,31))
check("Etudiant CP 200 de 19 ans a 12,00: pas d'alerte", 0.0 if alerte_min(r) else 1.0, 1.0)

print(); print("=" * 70); print("CONTROLE PERMANENT -- cout employeur >= net + ONSS travailleur + precompte + CSS"); print("=" * 70)
check("Controle applique a tous les calculs de ce fichier", 1.0 if NB_CONTROLES_COUT[0] >= 20 else 0.0, 1.0)
print(f"  ({NB_CONTROLES_COUT[0]} fiches controlees)")

print(); print("=" * 70)
if ECHECS:
    print(f"❌ {len(ECHECS)} TEST(S) ECHOUE(S): {ECHECS}"); sys.exit(1)
print("✅ TOUS LES TESTS PASSENT -- moteur complet verifie de bout en bout.")
