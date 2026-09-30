# -*- coding: utf-8 -*-
"""
test_moteur.py -- DuxSalary
Tests de BOUT EN BOUT du moteur (calculer_fiche_paie), sur les dossiers reels.
Complement de test_profils.py (qui teste les briques une par une).
Lancer: python3 test_moteur.py   -- doit afficher TOUS LES TESTS PASSENT
"""
import sys
from datetime import date
from moteur_paie import calculer_fiche_paie
ECHECS = []
def check(label, obtenu, attendu, tol=0.01):
    ok = abs(obtenu - attendu) <= tol
    print(f"{'✅' if ok else '❌'} {label}: obtenu={obtenu} attendu={attendu}")
    if not ok: ECHECS.append(label)

print("=" * 70); print("BILAL -- juillet 2026, CP 140.03 ouvrier, 98'H BARBER (cat 000)"); print("=" * 70)
r = calculer_fiche_paie('Bilal','Akattof','n','a','BE',date(2008,1,1),date(2026,7,9),'98H','a','b','r',
    'CP 140.03','Chauffeur',14.93, heures_semaine=38.0, heures_jour=3.0, jours_semaine=5, type_contrat='CDD',
    premier_engagement=True, jours_prestes=16, heures_prestees=48.0, jours_feries_payes=1, heures_feries=3.0,
    periode_debut=date(2026,7,1), periode_fin=date(2026,7,31))
check("Net (inchange)", r['salaire_net'], 848.67)
check("Part reductible 25% x 108%", r['onss_patronal_reductible'], 210.30)
check("Vacances 5,57% non reductible", r['onss_vacances_trimestrielle'], 46.85)
check("Reduction structurelle (temps partiel)", r['reduction_structurelle'], 113.42)
check("Premier engagement", r['reduction_premier_engagement'], 96.88)
check("ONSS patronal net = vacances + FFE speciale", r['onss_patronal'], 47.69)

print(); print("=" * 70); print("CIWAN -- octobre 2026, employe, Eysel (cat 010, FFE C, importance 1)"); print("=" * 70)
r = calculer_fiche_paie('Ciwan','Ilhan','n','a','BE',date(2004,11,17),date(2026,10,1),'Eysel','a','b','r',
    'CP 336','Comptable',13.71, heures_semaine=38.0, heures_jour=7.6, jours_semaine=5, type_contrat='CDI',
    premier_engagement=True, salaire_mensuel_fixe=2257.0, jours_prestes=22, heures_prestees=167.2,
    frais_nets=200.0, km_domicile=12, taux_km=0.08, rgpt_actif=False, cheques_repas=False,
    categorie_employeur='010', code_ffe='C', code_importance='1',
    periode_debut=date(2026,10,1), periode_fin=date(2026,10,31))
check("Net (inchange)", r['salaire_net'], 2332.89)
check("Reduction structurelle (Group S 398,98)", r['reduction_structurelle'], 398.98)
check("Premier engagement (Group S 165,27)", r['reduction_premier_engagement'], 165.27)
codes = {c['code']: c['montant'] for c in r['cotisations_complementaires']}
check("810 FFE speciale 0,10%", codes.get('810', 0), 2.26)
check("809 FFE base commercial 0,34%", codes.get('809', 0), 7.67)
check("831 Fonds social CP 200 0,23%", codes.get('831', 0), 5.19)
check("ONSS patronal net", r['onss_patronal'], 15.12)
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
check("Prime: net ajoute au net du mois", round(avec['salaire_net'] - sans['salaire_net'], 2), avec['net_exceptionnel'])
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

print(); print("=" * 70); print("RGPT CP 121 -- par JOUR (1,63 EUR)"); print("=" * 70)
r = calculer_fiche_paie('N','T','n','a','BE',date(1990,1,1),date(2026,3,1),'X','a','b','r','CP 121','Nettoyeuse',17.17,
    heures_semaine=36.5, heures_jour=4.0, jours_semaine=5, type_contrat='CDI', jours_prestes=16, heures_prestees=64.0,
    rgpt_actif=True, cheques_repas=False, periode_debut=date(2026,10,1), periode_fin=date(2026,10,31))
rg = next((l['montant'] for l in r['lignes_indemn'] if 'RGPT' in l['libelle']), 0)
check("RGPT = 16 jours x 1,63 (et non 64 h x 1,63)", rg, 26.08)

print(); print("=" * 70)
if ECHECS:
    print(f"❌ {len(ECHECS)} TEST(S) ECHOUE(S): {ECHECS}"); sys.exit(1)
print("✅ TOUS LES TESTS PASSENT -- moteur complet verifie de bout en bout.")
