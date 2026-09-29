from conges_legaux import jours_conges_acquis, double_pecule_employe, pecule_ouvrier_information

ECHECS = []
def check(label, actual, expected, tol=0.05):
    ok = abs(actual - expected) <= tol
    print(f"{'✅' if ok else '❌'} {label}: obtenu={actual}  attendu={expected}")
    if not ok: ECHECS.append(label)

print("=" * 70)
print("CAS 1 — Bilal: entre en juillet 2026, JAMAIS travaille avant (2025: 0 mois)")
print("=" * 70)
jours = jours_conges_acquis('ouvrier', 5, mois_prestes_annee_precedente=0)
check("Jours conges 2026 (0 mois prestes en 2025)", jours, 0.0)

print()
print("=" * 70)
print("CAS 2 — Employe temps plein, 12 mois prestes l'annee precedente")
print("=" * 70)
jours2 = jours_conges_acquis('employe', 5, mois_prestes_annee_precedente=12)
check("Jours conges (12 mois prestes, regime 5j)", jours2, 20.0)

print()
print("=" * 70)
print("CAS 3 — Employe embauche 1er avril N-1, 2300EUR brut, 9 mois prestes")
print("Reference: exemple Securex")
print("=" * 70)
jours3 = jours_conges_acquis('employe', 5, mois_prestes_annee_precedente=9)
check("Jours conges (9 mois prestes)", jours3, 15.0)
pecule3 = double_pecule_employe(2300.0, mois_prestes_annee_precedente=9)
check("Double pecule (Securex: 1587EUR)", pecule3, 1587.0, tol=1.0)

print()
print("=" * 70)
print("CAS 4 — Ouvrier: 30000EUR brut annuel de reference")
print("Reference: exemple calculateur-de-salaire.be")
print("=" * 70)
info4 = pecule_ouvrier_information(30000.0)
check("Simple pecule ouvrier (attendu 2592EUR)", info4['simple_pecule'], 2592.0)
print(f"  (info) Double pecule brut: {info4['double_pecule_brut']}EUR")
print(f"  (info) Double pecule net (apres retenue 13.07%): {info4['double_pecule_net']}EUR")
print(f"  (info) Paye par: {info4['paye_par']}")

print()
print("=" * 70)
print("CAS 5 — Ciwan: employe CDI temps partiel avant octobre (etudiant, pas de droit)")
print("Ciwan etait ETUDIANT jusqu'en octobre -- les mois en tant qu'etudiant")
print("NE comptent PAS pour les conges employe (regime different)")
print("=" * 70)
# Ciwan n'a pas preste en 2025 du tout (nouvel arrivant sur le marche)
jours5 = jours_conges_acquis('employe', 5, mois_prestes_annee_precedente=0)
check("Jours conges Ciwan 2026 (0 mois en 2025)", jours5, 0.0)
print("  (Ciwan n'aura droit a des conges qu'en 2027, sur base de ses mois 2026)")

print()
print("=" * 70)
if ECHECS:
    print(f"❌ {len(ECHECS)} TEST(S) ECHOUE(S): {ECHECS}")
else:
    print("✅ TOUS LES TESTS PASSENT")
