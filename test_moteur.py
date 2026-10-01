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
    ok = abs(obtenu - attendu) <= tol
    print(f"{'✅' if ok else '❌'} {label}: obtenu={obtenu} attendu={attendu}")
    if not ok: ECHECS.append(label)

print("=" * 70); print("BILAL -- juillet 2026, CP 140.03 ouvrier, 98'H BARBER (cat 000)"); print("=" * 70)
r = calculer_fiche_paie('Bilal','Akattof','n','a','BE',date(2008,1,1),date(2026,7,9),'98H','a','b','r',
    'CP 140.03','Chauffeur',14.93, heures_semaine=38.0, heures_jour=3.0, jours_semaine=5, type_contrat='CDD',
    premier_engagement=True, jours_prestes=16, heures_prestees=48.0, jours_feries_payes=1, heures_feries=3.0,
    periode_debut=date(2026,7,1), periode_fin=date(2026,7,31))
# 01/10/2026: ONSS personnel sur 108% + bonus emploi sur prestations reelles
# (Instructions ONSS 2026/3 p.176 et p.449-453) -> net 801,38 (etait 848,67)
check("ONSS personnel 13,07% x 108%", -r['onss_travailleur'], 109.94)
check("Bonus emploi A (H/U = 0,29)", r['bonus_emploi_a'], 39.94)
check("Bonus emploi B (S = 2.669,20)", r['bonus_emploi_b'], 22.71)
check("Net", r['salaire_net'], 801.38)
check("Part reductible 25% x 108%", r['onss_patronal_reductible'], 210.30)
check("Vacances 5,57% non reductible", r['onss_vacances_trimestrielle'], 46.85)
check("Reduction structurelle (temps partiel)", r['reduction_structurelle'], 113.42)
check("Premier engagement", r['reduction_premier_engagement'], 96.88)
# 01/10/2026: + cotisations 255 (0,02%), 256 (0,01%, T3 2026) et 859 (0,10%) sur 841,18
# (Instructions ONSS 2026/3 p.340-341 et p.346) -> 48,78 (etait 47,69)
codes_b = {c['code']: c['montant'] for c in r['cotisations_complementaires']}
check("255 accidents du travail 0,02% sur 108%", codes_b.get('255', 0), 0.17)
check("256 Fonds amiante 0,01% sur 108% (du au T3 2026)", codes_b.get('256', 0), 0.08)
check("859 chomage temporaire 0,10% sur 108%", codes_b.get('859', 0), 0.84)
check("ONSS patronal net = vacances + cotisations non reductibles", r['onss_patronal'], 48.78)

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
# Vacances legales d'un ouvrier: payees par la caisse -> hors heures payees (mu)
rc = calculer_fiche_paie('M','N','n','a','BE',date(2005,10,31),date(2026,5,27),'S','a','b','r','CP 140.03','Nettoyeur',15.2097,
    jours_prestes=22, heures_prestees=44.0, jours_conge=5, periode_debut=date(2026,6,1), periode_fin=date(2026,6,30), **kw_i)
check("Conges ouvrier sans effet sur la reduction structurelle", rc['reduction_structurelle'], r['reduction_structurelle'])
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
    'CP 121','Nettoyeuse',17.17, heures_semaine=36.5, heures_jour=4.0, jours_semaine=5, type_contrat='CDI',
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

print(); print("=" * 70); print("RGPT CP 121 -- par JOUR (1,63 EUR)"); print("=" * 70)
r = calculer_fiche_paie('N','T','n','a','BE',date(1990,1,1),date(2026,3,1),'X','a','b','r','CP 121','Nettoyeuse',17.17,
    heures_semaine=36.5, heures_jour=4.0, jours_semaine=5, type_contrat='CDI', jours_prestes=16, heures_prestees=64.0,
    rgpt_actif=True, cheques_repas=False, periode_debut=date(2026,10,1), periode_fin=date(2026,10,31))
rg = next((l['montant'] for l in r['lignes_indemn'] if 'RGPT' in l['libelle']), 0)
check("RGPT = 16 jours x 1,63 (et non 64 h x 1,63)", rg, 26.08)

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
check("Etudiant CP 336 a 13,00 < 13,021 (bareme etudiant 95 %): alerte",
      1.0 if 'Étudiant (95%)' in alerte_min(r) and '13,0210' in alerte_min(r) else 0.0, 1.0)
r = calculer_fiche_paie('A','B','n','a','BE',date(2005,1,1),date(2026,10,1),'X','a','b','r','CP 336','Etudiant',13.10,
    type_contrat='STU', is_etudiant=True, periode_debut=date(2026,10,1), periode_fin=date(2026,10,31), **kw_m)
check("Etudiant CP 336 a 13,10: pas d'alerte", 0.0 if alerte_min(r) else 1.0, 1.0)
r = calculer_fiche_paie('A','B','n','a','BE',date(2005,1,1),date(2026,8,1),'X','a','b','r','CP 140.03','Etudiant',14.00,
    type_contrat='STU', is_etudiant=True, periode_debut=date(2026,8,1), periode_fin=date(2026,8,31), **kw_m)
check("Etudiant CP 140.03 a 14,00 < 14,9255 (pas de bareme etudiant: minimum ordinaire, signale)",
      1.0 if '14,9255' in alerte_min(r) and 'pas de barème étudiant' in alerte_min(r) else 0.0, 1.0)
r = calculer_fiche_paie('A','B','n','a','BE',date(1990,1,1),date(2026,1,1),'X','a','b','r','CP 140.03','Personnel roulant — Niveau 2',15.00,
    type_contrat='CDI', periode_debut=date(2026,8,1), periode_fin=date(2026,8,31), **kw_m)
check("Ouvrier CP 140.03 niveau 2 a 15,00 < 15,4490 (categorie du contrat): alerte", 1.0 if '15,4490' in alerte_min(r) else 0.0, 1.0)

print(); print("=" * 70); print("CONTROLE PERMANENT -- cout employeur >= net + ONSS travailleur + precompte + CSS"); print("=" * 70)
check("Controle applique a tous les calculs de ce fichier", 1.0 if NB_CONTROLES_COUT[0] >= 20 else 0.0, 1.0)
print(f"  ({NB_CONTROLES_COUT[0]} fiches controlees)")

print(); print("=" * 70)
if ECHECS:
    print(f"❌ {len(ECHECS)} TEST(S) ECHOUE(S): {ECHECS}"); sys.exit(1)
print("✅ TOUS LES TESTS PASSENT -- moteur complet verifie de bout en bout.")
