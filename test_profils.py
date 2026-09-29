# -*- coding: utf-8 -*-
"""
test_profils.py — DuxSalary
Jeu de tests de non-régression basé sur des fiches de paie RÉELLES et VALIDÉES.
Toute modification de regles_cp.py ou profil_travailleur.py doit faire passer
ce fichier avant d'être déployée. Lancer: python3 test_profils.py
"""
import sys
sys.path.insert(0, '.')
from profil_travailleur import construire_profil

ECHECS = []

def check(label, actual, expected, tol=0.02):
    ok = abs(actual - expected) <= tol
    status = "✅" if ok else "❌"
    print(f"{status} {label}: obtenu={actual}  attendu={expected}")
    if not ok:
        ECHECS.append(label)

print("=" * 70)
print("TEST 1 — Bilal Akattof, 98'H BARBER, CP 140.03, ouvrier CDD, juillet 2026")
print("=" * 70)
p = construire_profil('CP 140.03', 'ouvrier', type_contrat='CDD')
brut_onss = 778.87   # 48h prestées + 3h férié + avantage repas 16j, tel que fiche validée
onss_pers = p.onss_personnel(brut_onss)
check("ONSS personnel brut", onss_pers, 101.80)

# Bilal: 15h/38h (temps partiel), salaire propre ETP = 14.93 * 38 * 52/12 = 2457.73
ratio_bilal = 15 / 38
bonus_a, bonus_b = p.bonus_emploi(2457.73, ratio_temps_partiel=ratio_bilal)
check("Bonus emploi volet A (15/38 temps partiel)", bonus_a, 35.70, tol=0.5)
check("Bonus emploi volet B ouvrier (15/38 temps partiel)", bonus_b, 10.61, tol=0.5)

onss_pat_brut = p.onss_patronal_brut(brut_onss)
check("ONSS patronal brut (×1.08 coeff)", onss_pat_brut, 227.12, tol=0.5)
red_struct = p.reduction_structurelle(onss_pat_brut)
check("Réduction structurelle", red_struct, min(521.47, onss_pat_brut))
reste = round(onss_pat_brut - red_struct, 2)
red_pe = p.reduction_premier_engagement(reste)
onss_pat_net = round(max(0, onss_pat_brut - red_struct - red_pe), 2)
check("ONSS patronal NET (avec 1er engagement)", onss_pat_net, 0.0)

print()
print("=" * 70)
print("TEST 2 — Ryad Draoui, 98'H BARBER, CP 140.03, étudiant, août 2026")
print("=" * 70)
p2 = construire_profil('CP 140.03', 'etudiant')
brut_onss2 = 1439.06
check("ONSS personnel étudiant (2.71%)", p2.onss_personnel(brut_onss2), 39.00)
onss_pat_brut2 = p2.onss_patronal_brut(brut_onss2)
check("ONSS patronal brut étudiant (5.43%, pas de coeff 108%)", onss_pat_brut2, 78.14, tol=0.1)
check("Réduction structurelle étudiant (doit être 0)", p2.reduction_structurelle(onss_pat_brut2), 0.0)
check("Réduction 1er engagement étudiant (doit être 0)",
      p2.reduction_premier_engagement(onss_pat_brut2), 0.0)
bonus_a2, bonus_b2 = p2.bonus_emploi(2457.73)
check("Bonus emploi étudiant (doit être 0)", bonus_a2 + bonus_b2, 0.0)
check("Précompte étudiant (doit être 0)", p2.precompte_brut(1400.06), 0.0)

print()
print("=" * 70)
print("TEST 3 — Ciwan Ilhan, Eysel Consult, CP 336, employé CDI, octobre 2026")
print("=" * 70)
p3 = construire_profil('CP 336', 'employe', type_contrat='CDI')
check("Salaire mensuel fixe applicable", 1.0 if p3.salaire_est_mensuel_fixe else 0.0, 1.0)
check("Libellé salaire", 1.0 if p3.libelle_salaire_base == "Salaire mensuel de base" else 0.0, 1.0)
brut_onss3 = 2191.27
check("ONSS personnel employé", p3.onss_personnel(brut_onss3), 286.40, tol=0.2)
onss_pat_brut3 = p3.onss_patronal_brut(brut_onss3)
check("ONSS patronal brut employé (pas de coeff 108%)", onss_pat_brut3, round(2191.27*0.25,2), tol=0.5)
# Bonus emploi = fonction du salaire PROPRE de Ciwan (2191.27, temps plein), PAS du minimum CP
bonus_a3, bonus_b3 = p3.bonus_emploi(2191.27)
check("Bonus emploi volet A employé (sur salaire propre, pas minimum CP)", bonus_a3, 162.53, tol=1.0)
check("Bonus emploi volet B employé (doit être 0)", bonus_b3, 0.0)
onss_net3 = round(onss_pat_brut3 - p3.onss_personnel(brut_onss3), 2)  # sanity only

print()
print("=" * 70)
print("TEST 4 — Précompte professionnel, isolé sans enfant, employé CP 200")
print("Référence: tableau indépendant (calculateur-de-salaire.be), hors zone bonus emploi")
print("=" * 70)
p4 = construire_profil('CP 200', 'employe', type_contrat='CDI')

for brut, attendu in [(3500.0, 617.41), (4000.0, 826.70), (5000.0, 1245.27)]:
    onss = round(brut * 0.1307, 2)
    imposable = round(brut - onss, 2)
    pp = p4.precompte_brut(imposable, etat_civil='celibataire', nb_enfants=0)
    check(f"Précompte isolé — brut {brut:.0f}€", pp, attendu, tol=0.05)

print()
print("=" * 70)
print("TEST 5 — Précompte, marié/cohabitant conjoint SANS revenus (quotient conjugal)")
print("Référence: simulateur SPF Finances verrouillé, execute reellement le 29/09/2026")
print("=" * 70)
pp5 = p4.precompte_brut(2500.0, etat_civil='marie', nb_enfants=0, partenaire_revenus_pro='non')
check("Précompte marié conjoint sans revenus — imposable 2500€", pp5, 35.99, tol=0.05)
pp5b = p4.precompte_brut(2500.0, etat_civil='celibataire', nb_enfants=0)
check("Précompte isolé (comparaison) — imposable 2500€", pp5b, 381.01, tol=0.05)

print()
print("=" * 70)
if ECHECS:
    print(f"❌ {len(ECHECS)} TEST(S) ÉCHOUÉ(S): {ECHECS}")
    print("NE PAS DÉPLOYER tant que ces tests ne passent pas.")
    sys.exit(1)
else:
    print("✅ TOUS LES TESTS PASSENT — le socle reproduit les fiches réelles connues.")
    sys.exit(0)
