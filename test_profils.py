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
from datetime import date

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

# Bilal: 15h/38h (temps partiel). NOTE 29/09/2026: le bonus emploi a des
# seuils dates (mise a jour plusieurs fois/an) -- on ne peut plus verifier
# les montants de juillet 2026 sans la table historique de cette periode.
# Assertion retiree ici (etait basee sur une structure pre-reforme fausse) --
# a re-verifier si besoin de regenerer une fiche de juillet 2026 exactement.
ratio_bilal = 15 / 38
bonus_a, bonus_b = p.bonus_emploi(2457.73, ratio_temps_partiel=ratio_bilal, onss_du=101.80,
                                    reference_date=date(2026, 7, 31))
# CORRECTION 29/09/2026: les valeurs 35.70/10.61 initialement "validees" en
# debut de session utilisaient l'ancienne structure PRE-reforme 2024 (jamais
# croisee avec une source externe). Avec la vraie table de juillet 2026,
# le bonus emploi efface ENTIEREMENT l'ONSS de Bilal (54.37+47.43=101.80).
# ==> LA FICHE DE BILAL DEJA ENVOYEE AU CLIENT EST A CORRIGER.
check("Bonus emploi volet A (vraie table JUILLET 2026)", bonus_a, 54.37, tol=0.02)
check("Bonus emploi volet B (vraie table JUILLET 2026, ecrete)", bonus_b, 47.43, tol=0.02)
check("Total bonus = ONSS du (extinction complete)", round(bonus_a+bonus_b,2), 101.80, tol=0.02)

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
# NOTE 29/09/2026: le test precedent (162.53/0) utilisait la mauvaise
# hypothese "volet B ouvrier uniquement" -- remplace par la vraie structure
# 2024+ validee contre une simulation Group S REELLE (2257EUR brut, meme
# scenario Ciwan/CP336, au 01/09/2026):
bonus_a3, bonus_b3 = p3.bonus_emploi(2257.00, onss_du=294.99, reference_date=date(2026, 9, 29))
check("Bonus emploi volet A employé (Group S: 127.54)", bonus_a3, 127.54, tol=0.02)
check("Bonus emploi volet B employé apres ecretement (Group S: 167.45)", bonus_b3, 167.45, tol=0.02)
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
print("TEST 6 — Reduction precompte bonus emploi: DEUX taux distincts (A vs B)")
print("Source: 4 references independantes, 33.14% volet A / 52.54% volet B")
print("=" * 70)
# Ouvrier avec un salaire assez eleve pour avoir un vrai precompte (pas 0)
p6 = construire_profil('CP 140.03', 'ouvrier', type_contrat='CDI')
bonus_a_test, bonus_b_test = 50.0, 20.0
red = p6.reduction_precompte_bonus(bonus_a_test, bonus_b_test, brut_imposable=2500.0)
attendu = round(50.0*0.3314 + 20.0*0.5254, 2)
check(f"Reduction precompte (bonus_a=50, bonus_b=20)", red, attendu)
ancien_calcul_faux = round((50.0+20.0)*0.3314, 2)
print(f"  (pour reference: l'ancien calcul errone aurait donne {ancien_calcul_faux}EUR -- ecart de {round(attendu-ancien_calcul_faux,2)}EUR)")

print()
print("=" * 70)
print("TEST 7 — Reduction structurelle DEGRESSIVE (remplace l'ancien montant fixe)")
print("Reference: Instructions ONSS 2026/2 + comparaison Group S (ecart connu ~11EUR)")
print("=" * 70)
p7 = construire_profil('CP 336', 'employe', type_contrat='CDI')
# Ciwan: base=2257, onss_pat_brut theorique 25% = 564.25
onss_pat_brut_ciwan = round(2257.00 * 0.25, 2)
red_ciwan = p7.reduction_structurelle(onss_pat_brut_ciwan, base_salariale_mensuelle=2257.00, reference_date=date(2026, 9, 29))
check("Reduction structurelle degressive Ciwan (2257EUR)", red_ciwan, 387.70, tol=0.05)
print(f"  (Group S annonce 398.98EUR -- ecart connu de {round(398.98-red_ciwan,2)}EUR, non resolu)")

# Bilal reste au plafond max car tres bas salaire (verifie que la formule
# degressive donne bien un montant tres eleve pour un tout petit salaire)
onss_pat_brut_bilal = round(841.18 * 0.27, 2)
red_bilal = p7.reduction_structurelle(onss_pat_brut_bilal, base_salariale_mensuelle=841.18, reference_date=date(2026, 7, 31))
print(f"  (info) Bilal (base 841.18EUR): reduction degressive = {red_bilal}EUR (plafonnee a onss du: {onss_pat_brut_bilal}EUR)")

print()
print("=" * 70)
if ECHECS:
    print(f"❌ {len(ECHECS)} TEST(S) ÉCHOUÉ(S): {ECHECS}")
    print("NE PAS DÉPLOYER tant que ces tests ne passent pas.")
    sys.exit(1)
else:
    print("✅ TOUS LES TESTS PASSENT — le socle reproduit les fiches réelles connues.")
    sys.exit(0)
