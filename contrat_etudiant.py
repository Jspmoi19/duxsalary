# -*- coding: utf-8 -*-
"""
contrat_etudiant.py -- DuxSalary
Donnees des formulaires de contrat (aucun acces a la base, aucun montant defini
ici): regles de la CP, CP gerees, lieu de signature -- communs aux formulaires
CDI/CDD et etudiant -- puis bareme etudiant et contingent annuel pour le
formulaire etudiant. Le formulaire etudiant ne genere QUE le contrat: les fiches
de paie passent par le calendrier et « Calculer la paie ».
"""
import json

from cp_data import CP_DATABASE
from minimums_cp import minimum_cp
from occupation import commune_de_l_adresse, suivi_contingent_etudiant
from regles_cp import cp_geree, resume_regles_cp

STUDENT_AT_WORK = 'https://www.studentatwork.be'


def contexte_regles(dossier, etudiant=False):
    """Commun aux deux formulaires: regles de chaque CP (regles_cp.py), liste des
    CP gerees par le moteur de paie, lieu de signature (commune du dossier)."""
    return {
        'regles_json': json.dumps({cp: resume_regles_cp(cp, etudiant=etudiant) for cp in CP_DATABASE}, ensure_ascii=False),
        'cp_gerees': [cp for cp in CP_DATABASE if cp_geree(cp)],
        'lieu_signature': commune_de_l_adresse((dossier or {}).get('adresse')),
    }


def contexte_formulaire(dossier, heures_deja, aujourd_hui, baremes_db=None):
    """Variables du gabarit contrat_etudiant.html.
    heures_deja: heures etudiant deja prestees cette annee chez cet employeur.
    baremes_db: {cp_key: [lignes de baremes_cp]} quand la base en contient."""
    minimums = {}
    for cp_key in CP_DATABASE:
        minimum, raison = minimum_cp(cp_key, aujourd_hui, is_etudiant=True, lignes_db=(baremes_db or {}).get(cp_key))
        if minimum:
            minimums[cp_key] = {'horaire': minimum['horaire'], 'categorie': minimum['categorie'], 'note': minimum['note'],
                                'depuis': minimum['depuis'].isoformat(), 'depuis_fr': f"{minimum['depuis']:%d/%m/%Y}",
                                'source': minimum['source']}
        else:
            minimums[cp_key] = {'raison': raison}
    return dict(contexte_regles(dossier, etudiant=True),
                minimums_json=json.dumps(minimums, ensure_ascii=False),
                contingent=suivi_contingent_etudiant(heures_deja, 0, aujourd_hui),
                student_at_work=STUDENT_AT_WORK)
