# Patch -- moteur_paie.py utilise les taux ONSS officiels du trimestre de la
# fiche (onss_taux.py / onss_trimestres/), provisionne la cotisation annuelle
# vacances ouvriers (10.27%) dans le cout employeur, et renvoie la
# tracabilite des taux utilises. ATOMIQUE: rien n'est ecrit si une etape echoue.
import shutil, ast

CHEMIN = '/var/www/duxsalary/moteur_paie.py'
content = open(CHEMIN).read()

etapes = [
    ("construire_profil avec la periode",
     """    profil = construire_profil(cp_key, statut_profil, type_contrat=type_contrat,
                                heures_semaine=heures_semaine, jours_semaine=jours_semaine)""",
     """    profil = construire_profil(cp_key, statut_profil, type_contrat=type_contrat,
                                heures_semaine=heures_semaine, jours_semaine=jours_semaine,
                                reference_date=periode_fin if periode_fin else date.today())
    onss_info = profil.onss_officiel   # trimestre utilise + report eventuel"""),
    ("provision vacances annuelles ouvriers dans le cout employeur",
     "    cout_empl = round(brut_onss + onss_pat_net + montant_rgpt + montant_arab + montant_vet + montant_dep + montant_km + cr_empl_total, 2)",
     """    # Cotisation ANNUELLE vacances ouvriers (10.27% des remunerations a 108%),
    # facturee par l'ONSS l'annee suivante -- provisionnee ici pour un cout reel
    provision_vacances_annuelles = round(brut_onss * profil.coeff_base_onss_patronal
                                         * profil.vacances_annuelles_taux, 2)
    cout_empl = round(brut_onss + onss_pat_net + montant_rgpt + montant_arab + montant_vet + montant_dep + montant_km + cr_empl_total
                      + provision_vacances_annuelles, 2)"""),
    ("tracabilite dans le resultat",
     "        'libelle_salaire_base': profil.libelle_salaire_base,",
     """        'libelle_salaire_base': profil.libelle_salaire_base,
        'onss_trimestre_utilise': onss_info['trimestre_utilise'],
        'onss_parametres_reportes': onss_info['parametres_reportes'],
        'onss_date_fichier': onss_info['date_creation_onss'],
        'onss_taux_patronal_applique': profil.onss_patronal_taux_base,
        'provision_vacances_annuelles': provision_vacances_annuelles,"""),
]
for label, old, new in etapes:
    n = content.count(old)
    if n != 1:
        raise SystemExit(f"ECHEC ({label}): trouve {n} fois, attendu 1 -- RIEN n'a ete modifie.")
    content = content.replace(old, new)

ast.parse(content)
shutil.copy(CHEMIN, CHEMIN + '.avant_onss_trimestres')
open(CHEMIN, 'w').write(content)
print("OK -- moteur_paie.py branche sur les taux ONSS officiels par trimestre")
print("   (copie de securite: moteur_paie.py.avant_onss_trimestres)")
