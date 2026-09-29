# Patch #6 -- CRITIQUE: bonus emploi structure 2024+ (volet A+B pour tous statuts)
# + ecretement correct (volet B en premier, pas proportionnel)
with open('/var/www/duxsalary/moteur_paie.py', 'r') as f:
    content = f.read()

old = """        sal_propre_etp = salaire_horaire * heures_semaine * 52 / 12
        bonus_a, bonus_b = profil.bonus_emploi(sal_propre_etp, ratio_tp)
        # Plafonner au max de l'ONSS dû
        total_bonus = min(bonus_a + bonus_b, onss_trav_brut)
        if bonus_a + bonus_b > 0:
            f = total_bonus / (bonus_a + bonus_b)
            bonus_a = round(bonus_a * f, 2)
            bonus_b = round(total_bonus - bonus_a, 2)"""

new = """        sal_propre_etp = salaire_horaire * heures_semaine * 52 / 12
        # Ecretement CORRECT integre dans bonus_emploi(): volet B en premier,
        # jusqu'a 0, PUIS volet A si toujours insuffisant -- PAS une reduction
        # proportionnelle des deux (erreur corrigee le 29/09/2026, verifiee
        # au centime contre une simulation Group S reelle CP336 employe).
        bonus_a, bonus_b = profil.bonus_emploi(sal_propre_etp, ratio_tp, onss_du=onss_trav_brut)"""

if old not in content:
    raise SystemExit("ECHEC: bloc bonus emploi non trouve -- rien modifie. "
                      "Le fichier moteur_paie.py a peut-etre change entre-temps.")
content = content.replace(old, new)

with open('/var/www/duxsalary/moteur_paie.py', 'w') as f:
    f.write(content)
print("OK -- ecretement bonus emploi corrige (volet B en premier)")
