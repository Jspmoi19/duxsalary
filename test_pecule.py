import sys; sys.path.insert(0, '.')
from pecule_vacances import calculer_double_pecule_employe

ECHECS = []
def check(label, actual, expected, tol=0.05):
    ok = (actual is None and expected is None) or (
        actual is not None and expected is not None and abs(actual - expected) <= tol)
    print(f"{'✅' if ok else '❌'} {label}: obtenu={actual}  attendu={expected}")
    if not ok: ECHECS.append(label)

print("=" * 72)
print("FICHE REELLE — Leo, juin 2024, CP 336 (exercice 2023, salaire 2676.32)")
print("Reference: fiche Liantis/SD Worx fournie par l'utilisateur")
print("Regle 85/92 confirmee: Securex + Instructions administratives ONSS")
print("=" * 72)
r = calculer_double_pecule_employe(2676.32, mois_prestes_annee_reference=12)
check("Pecule brut total", r['pecule_base'], 2462.21)
check("Part soumise a retenue (fiche: 2274.87)", r['base_soumise_retenue'], 2274.87)
check("Part exemptee 7/92 (fiche: 187.34)", r['part_exemptee_retenue'], 187.34)
check("Retenue 13.07% (fiche: 297.33)", r['retenue_double_pecule'], 297.33)
print()
print("  ==> La ligne 'double pecule conventionnel' de 187.34EUR sur la fiche")
print("      correspond EXACTEMENT a la part exemptee 7/92, pas a un")
print("      complement sectoriel CP 336 comme initialement suppose.")

print()
print("=" * 72)
print("CAS — Prorata: 6 mois prestes seulement")
print("=" * 72)
r2 = calculer_double_pecule_employe(3000.0, mois_prestes_annee_reference=6)
check("Pecule brut (92% x 3000 x 6/12)", r2['pecule_base'], 1380.0)
check("Part soumise (85/92)", r2['base_soumise_retenue'], 1275.0)
check("Retenue", r2['retenue_double_pecule'], 166.64)

print()
print("=" * 72)
print("CAS — Aucun droit (0 mois preste l'annee precedente)")
print("=" * 72)
r3 = calculer_double_pecule_employe(2257.0, mois_prestes_annee_reference=0)
check("Pas de droit", 0.0 if r3['droit'] else 1.0, 1.0)
check("Montant 0", r3['pecule_brut'], 0.0)

print()
print("=" * 72)
print("HONNETETE — le precompte vacances n'est PAS calcule")
print("=" * 72)
check("Precompte non calcule", 1.0 if r['precompte_vacances'] is None else 0.0, 1.0)
check("Net non calcule", 1.0 if r['montant_net'] is None else 0.0, 1.0)
print("  (bareme 'allocations exceptionnelles' employe non implemente)")

print()
print("=" * 72)
if ECHECS:
    print(f"❌ {len(ECHECS)} TEST(S) ECHOUE(S): {ECHECS}")
    sys.exit(1)
else:
    print("✅ TOUS LES TESTS PASSENT — module valide contre une fiche reelle")
