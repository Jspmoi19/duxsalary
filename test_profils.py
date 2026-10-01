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
p = construire_profil('CP 140.03', 'ouvrier', type_contrat='CDD', reference_date=date(2026, 7, 31))
brut_onss = 778.87   # 48h prestées + 3h férié + avantage repas 16j, tel que fiche validée
onss_pers = p.onss_personnel(brut_onss)
# CORRECTION 01/10/2026: ONSS personnel ouvrier sur 108% (Instructions ONSS
# 2026/3 p.176 ; fiches reelles Interconsult et Liantis FDLR): 841,18 x 13,07%.
check("ONSS personnel brut (13,07% x 108%)", onss_pers, 109.94)

# CORRECTION 01/10/2026: bonus emploi selon la formule officielle (Instructions
# ONSS 2026/3 p.449-453), sur les prestations REELLES du mois:
# juillet 2026 = 23 jours -> U = 23 x 7,6 = 174,8 h ; H = 51 h
# S = (W/H) x U = 15,27 x 174,8 = 2.669,20 ; H/U = 0,29
# L'ancien calcul (fraction contractuelle 15/38, salaire horaire x 38 x 52/12)
# effacait a tort tout l'ONSS de Bilal.
s_bilal, frac_bilal = p.reference_bonus_emploi(brut_onss, date(2026, 7, 31), heures=51.0, temps_partiel=True)
check("Bonus emploi: salaire de reference S", s_bilal, 2669.20)
check("Bonus emploi: fraction H/U", frac_bilal, 0.29)
bonus_a, bonus_b = p.bonus_emploi(s_bilal, ratio_temps_partiel=frac_bilal, onss_du=onss_pers,
                                    reference_date=date(2026, 7, 31))
check("Bonus emploi volet A (137,74 x 0,29)", bonus_a, 39.94)
check("Bonus emploi volet B (78,31 x 0,29)", bonus_b, 22.71)
# Temps plein, mois incomplet: S = (W/J) x D, P = (J/D) x R (exemple 1 des Instructions)
p_tp = construire_profil('CP 200', 'employe', reference_date=date(2026, 7, 31))
s_inc, frac_inc = p_tp.reference_bonus_emploi(2015.00, date(2026, 7, 31), jours=19)
check("Temps plein incomplet: S = (2015/19 = 106,05) x 23", s_inc, 2439.15)
check("Temps plein incomplet: J/D = 19/23", frac_inc, 0.83)

onss_pat_brut = p.onss_patronal_brut(brut_onss)
# CORRECTION 30/09/2026: l'ancien 227.12 utilisait 27% (sans source officielle).
# Taux officiel TechLib 2026/3, code 015 cat. 000: 19.88% + 5.12% moderation
# + 5.57% vacances annuelles (code 253) = 30.57%, sur 108% du brut.
# 778.87 x 1.08 = 841.18 -> x 30.57% = 257.15
check("ONSS patronal brut ouvrier (30.57% officiel x 108%)", onss_pat_brut, 257.15, tol=0.05)
# Formules officielles (Instructions ONSS 2026/3): Ps = R x mu x beta_s sur
# S = W(100%) x 13 x U / H ; Pg = G x mu x beta_g, G = 2000EUR depuis 01/07/2026
red_struct = p.reduction_structurelle(onss_pat_brut, remuneration_mois=778.87, heures_payees=51.0)
check("Reduction structurelle (temps partiel, proportionnee)", red_struct, 113.42)
reste = round(onss_pat_brut - red_struct, 2)
red_pe = p.reduction_premier_engagement(reste, heures_payees=51.0)
check("Premier engagement (couvre le reste)", red_pe, 143.73)
onss_pat_net = round(max(0, onss_pat_brut - red_struct - red_pe), 2)
check("ONSS patronal NET (avec 1er engagement)", onss_pat_net, 0.0)

print()
print("=" * 70)
print("TEST 2 — Ryad Draoui, 98'H BARBER, CP 140.03, étudiant, août 2026")
print("=" * 70)
p2 = construire_profil('CP 140.03', 'etudiant', reference_date=date(2026, 8, 31))
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
p3 = construire_profil('CP 336', 'employe', type_contrat='CDI', reference_date=date(2026, 10, 31))
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
red_ciwan = p7.reduction_structurelle(onss_pat_brut_ciwan, remuneration_mois=2257.00,
                                     jours_payes=22, reference_date=date(2026, 10, 31))
check("Reduction structurelle Ciwan (Group S: 398.98) -- ECART 11EUR RESOLU", red_ciwan, 398.98)
pe_ciwan = p7.reduction_premier_engagement(round(onss_pat_brut_ciwan - red_ciwan, 2),
                                            jours_payes=22, reference_date=date(2026, 10, 31))
check("Premier engagement Ciwan (Group S: 165.27)", pe_ciwan, 165.27)

# Bilal reste au plafond max car tres bas salaire (verifie que la formule
# degressive donne bien un montant tres eleve pour un tout petit salaire)
onss_pat_brut_bilal = round(841.18 * 0.27, 2)
red_bilal = p7.reduction_structurelle(onss_pat_brut_bilal, base_salariale_mensuelle=841.18, reference_date=date(2026, 7, 31))
print(f"  (info) Bilal (base 841.18EUR): reduction degressive = {red_bilal}EUR (plafonnee a onss du: {onss_pat_brut_bilal}EUR)")

print()
print("=" * 70)
print("TEST 8 — Precompte versionne par ANNEE fiscale")
print("=" * 70)
p8 = construire_profil('CP 200', 'employe', type_contrat='CDI')
pp8 = p8.precompte_brut(3042.55, reference_date=date(2026, 10, 31))
check("Precompte 2026 avec date explicite (isole, 3500 brut)", pp8, 617.41)
pp8b = p8.precompte_brut(2500.0, etat_civil='marie', partenaire_revenus_pro='non',
                          reference_date=date(2026, 3, 31))
check("Quotient conjugal 2026 avec date explicite", pp8b, 35.99)
red8 = p8.reduction_precompte_bonus(50.0, 20.0, 2500.0, reference_date=date(2026, 6, 30))
check("Reduction precompte bonus 2026 (taux A/B dates)", red8, round(50*0.3314 + 20*0.5254, 2))
try:
    p8.precompte_brut(3042.55, reference_date=date(2027, 1, 31))
    bloque = 0.0
except ValueError as e:
    bloque = 1.0
    print(f"  Message: {str(e)[:95]}...")
check("Janvier 2027 sans bareme 2027 = BLOQUE (pas de repli sur 2026)", bloque, 1.0)
etu = construire_profil('CP 140.03', 'etudiant')
check("Etudiant 2027: precompte 0 sans exiger de bareme", etu.precompte_brut(1400.0, reference_date=date(2027,1,31)), 0.0)

print()
print("=" * 70)
print("TEST 9 — Taux ONSS officiels versionnes par TRIMESTRE (TechLib)")
print("=" * 70)
po = construire_profil('CP 140.03', 'ouvrier', reference_date=date(2026, 7, 31))
check("Ouvrier Q3: patronal 30.57% (19.88+5.12+5.57)", po.onss_patronal_taux_base, 0.3057, tol=0.00001)
check("Ouvrier: provision vacances annuelles 10.27%", po.vacances_annuelles_taux, 0.1027, tol=0.00001)
pe = construire_profil('CP 336', 'employe', reference_date=date(2026, 9, 30))
check("Employe Q3: patronal 25%", pe.onss_patronal_taux_base, 0.25, tol=0.00001)
check("Employe: pas de cotisation vacances ONVA", pe.vacances_annuelles_taux, 0.0)
ps = construire_profil('CP 140.03', 'etudiant', reference_date=date(2026, 8, 31))
check("Etudiant Q3: 2.71% / 5.43%", ps.onss_personnel_taux + ps.onss_patronal_taux_base, 0.0814, tol=0.00001)
pr = construire_profil('CP 336', 'employe', reference_date=date(2026, 10, 31))
check("Octobre sans fichier Q4 -> Q3 utilise ET signale",
      1.0 if (pr.onss_officiel['trimestre_utilise'] == '2026Q3' and pr.onss_officiel['parametres_reportes']) else 0.0, 1.0)
pq2 = construire_profil('CP 140.03', 'ouvrier', reference_date=date(2026, 5, 31))
check("Mai 2026 -> fichier Q2 (pas Q3)", 1.0 if pq2.onss_officiel['trimestre_utilise'] == '2026Q2' else 0.0, 1.0)

print()
print("=" * 70)
if ECHECS:
    print(f"❌ {len(ECHECS)} TEST(S) ÉCHOUÉ(S): {ECHECS}")
    print("NE PAS DÉPLOYER tant que ces tests ne passent pas.")
    sys.exit(1)
else:
    print("✅ TOUS LES TESTS PASSENT — le socle reproduit les fiches réelles connues.")
    sys.exit(0)
