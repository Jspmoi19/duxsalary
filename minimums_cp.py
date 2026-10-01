# -*- coding: utf-8 -*-
"""
minimums_cp.py -- DuxSalary
Controle du salaire par rapport au MINIMUM de la commission paritaire a la date
de la periode de paie. Produit une alerte (jamais de blocage, jamais de
correction automatique: Leo decide).

Montants: ceux deja presents dans le projet -- la table `baremes_cp` de la base
(page « Barèmes CP », avec date de vigueur) quand le moteur peut la lire, sinon
cp_data.CP_DATABASE. Aucun montant n'est defini ici.

Dates: cp_data.py ne date pas ses baremes ; DATES_BAREMES donne, par CP, la date
a partir de laquelle ces montants sont en vigueur (derniere indexation notee
dans regles_cp.py / cp_data.py). Pour une periode ANTERIEURE, le minimum de
l'epoque n'est pas connu: l'alerte le dit au lieu de comparer a un chiffre d'une
autre periode. A chaque indexation: mettre a jour les montants ET cette date
(idealement, conserver l'ancienne version -- tache 4 du CLAUDE.md).
"""
from datetime import date, datetime

from cp_data import CP_DATABASE

DATES_BAREMES = {
    'CP 336':    (date(2026, 9, 1), "salairesminimums.be PC 3360000, indexation du 01/09/2026"),
    'CP 200':    (date(2026, 1, 1), "salairesminimums.be PC 2000000, indexation du 01/01/2026"),
    'CP 140.03': (date(2026, 1, 1), "salairesminimums.be PC 1400300, indexation du 01/01/2026"),
    'CP 121':    (date(2026, 7, 1), "salairesminimums.be PC 1210000, barème du 01/07/2026 (à recouper)"),
}
# Bareme propre aux etudiants, quand la CP en prevoit un dans cp_data.py
CATEGORIE_ETUDIANT = {'CP 336': 'Étudiant (95%)'}
# Montant mensuel non fiable dans cp_data.py (calcule sur 38 h alors que la CP est a 36,5 h):
# seul le minimum HORAIRE est controle
SANS_MINIMUM_MENSUEL = {'CP 121'}


def _date(valeur):
    if isinstance(valeur, datetime):
        return valeur.date()
    if isinstance(valeur, date):
        return valeur
    for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
        try:
            return datetime.strptime(str(valeur)[:10], fmt).date()
        except (TypeError, ValueError):
            pass
    return None


def minimum_cp(cp_key, reference_date, categorie=None, is_etudiant=False, lignes_db=None,
               annees_experience=None, anciennete_mois=None, age=None):
    """Minimum applicable. Retourne (minimum, raison):
    minimum = {'horaire', 'mensuel', 'categorie', 'depuis', 'source', 'note'} ou None,
    raison = explication quand le minimum n'est pas disponible.
    1) CP avec grille par classe et annees d'experience (baremes_experience.py): la
       grille s'applique -- annees_experience, anciennete_mois dans l'entreprise
       (bareme I / II) et age (bareme des etudiants) ;
    2) sinon minimum par categorie: lignes_db (table baremes_cp) puis cp_data.py."""
    from baremes_experience import minimum_experience
    minimum, raison = minimum_experience(cp_key, reference_date, categorie, annees_experience,
                                         anciennete_mois, is_etudiant, age)
    if minimum is not None or raison is not None:
        return minimum, raison
    baremes, depuis, source = {}, None, None
    if lignes_db:
        for r in lignes_db:
            baremes[r['categorie']] = {'horaire': float(r['montant_horaire'] or 0), 'mensuel': float(r['montant_mensuel'] or 0),
                                       'depuis': _date(r.get('date_vigueur')), 'source': r.get('source')}
    elif cp_key in CP_DATABASE and cp_key in DATES_BAREMES:
        depuis, source = DATES_BAREMES[cp_key]
        baremes = {k: dict(v, depuis=depuis, source=source) for k, v in CP_DATABASE[cp_key].get('baremes', {}).items()}
    if not baremes:
        return None, f"Aucun barème enregistré pour la {cp_key} : salaire minimum non contrôlé."

    cle_etudiant = CATEGORIE_ETUDIANT.get(cp_key)
    note = None
    if is_etudiant and cle_etudiant in baremes:
        cle = cle_etudiant
    else:
        ordinaires = {k: v for k, v in baremes.items() if k != cle_etudiant}
        if categorie in ordinaires:
            cle = categorie
        else:
            cle = min(ordinaires, key=lambda k: ordinaires[k]['horaire'] or ordinaires[k]['mensuel'])
            note = "catégorie la plus basse de la CP"
        if is_etudiant:
            note = "pas de barème étudiant propre à cette CP : minimum ordinaire" + (f", {note}" if note else '')
    b = baremes[cle]
    if not b['depuis']:
        return None, f"Barème de la {cp_key} sans date de vigueur : salaire minimum non contrôlé."
    if reference_date < b['depuis']:
        return None, (f"Minimum de la {cp_key} non disponible pour cette période "
                      f"(barème connu à partir du {b['depuis']:%d/%m/%Y}) : salaire non contrôlé.")
    return {'horaire': b['horaire'], 'mensuel': None if cp_key in SANS_MINIMUM_MENSUEL else b['mensuel'],
            'categorie': cle, 'depuis': b['depuis'], 'source': b['source'], 'note': note}, None


def alerte_minimum(cp_key, reference_date, salaire_horaire=0.0, salaire_mensuel_etp=None, paye_au_mois=False,
                   categorie=None, is_etudiant=False, lignes_db=None,
                   annees_experience=None, anciennete_mois=None, age=None):
    """Texte de l'alerte si le salaire est sous le minimum (ou si le minimum n'est
    pas disponible pour la periode) ; None si tout est en ordre.
    salaire_mensuel_etp: salaire mensuel ramene au temps plein (travailleur paye au mois)."""
    minimum, raison = minimum_cp(cp_key, reference_date, categorie, is_etudiant, lignes_db,
                                 annees_experience, anciennete_mois, age)
    if minimum is None:
        return raison
    fr = lambda x, d: f"{x:,.{d}f}".replace(',', ' ').replace('.', ',')
    detail = (f"{minimum['categorie']}" + (f" — {minimum['note']}" if minimum['note'] else '')
              + f", en vigueur depuis le {minimum['depuis']:%d/%m/%Y}" + (f", source : {minimum['source']}" if minimum['source'] else ''))
    if paye_au_mois and salaire_mensuel_etp and minimum['mensuel']:
        if salaire_mensuel_etp + 0.005 < minimum['mensuel']:
            return (f"Salaire mensuel (temps plein) de {fr(salaire_mensuel_etp, 2)} € inférieur au minimum de la {cp_key} : "
                    f"{fr(minimum['mensuel'], 2)} € ({detail}).")
        return None
    if salaire_horaire and minimum['horaire'] and salaire_horaire + 0.00005 < minimum['horaire']:
        return (f"Salaire horaire de {fr(salaire_horaire, 4)} € inférieur au minimum de la {cp_key} : "
                f"{fr(minimum['horaire'], 4)} € ({detail}).")
    return None
