# -*- coding: utf-8 -*-
"""
occupation.py -- DuxSalary
Occupation d'un travailleur chez un employeur a partir de ses contrats:
contrat applicable a une periode, date de premiere occupation, libelles.
Fonctions pures (aucun acces a la base): testees dans test_documents.py.
"""

LIBELLES_ETAT_CIVIL = {
    'celibataire': 'Célibataire',
    'marie': 'Marié(e)',
    'cohabitation_legale': 'Cohabitant(e) légal(e)',
    'separe_fait': 'Séparé(e) de fait',
    'separe_corps': 'Séparé(e) de corps et de biens',
    'divorce': 'Divorcé(e)',
    'veuf': 'Veuf / veuve',
}


def libelle_etat_civil(code):
    """'celibataire' -> 'Célibataire', 'marie' -> 'Marié(e)'... (code inconnu: affiche tel quel, avec majuscule)."""
    if not code:
        return ''
    return LIBELLES_ETAT_CIVIL.get(code, str(code).replace('_', ' ').capitalize())


def date_premiere_occupation(contrats):
    """Date d'entree chez l'employeur = debut du PREMIER contrat, quel que soit
    son type (etudiant compris) et son statut (actif, termine, archive)."""
    dates = [c['date_debut'] for c in contrats or [] if c.get('date_debut')]
    return min(dates) if dates else None


def _couvre(contrat, debut, fin):
    return bool(contrat.get('date_debut')) and contrat['date_debut'] <= fin and \
        (not contrat.get('date_fin') or contrat['date_fin'] >= debut)


def contrat_de_la_periode(contrats, debut, fin, contrat_id=None, type_contrat=None):
    """Contrat qui s'applique a une periode de paie, parmi TOUS les contrats du
    travailleur (meme termines ou archives) -- un mois preste sous contrat
    etudiant doit etre calcule comme etudiant, meme si un CDI est actif depuis.
    Ordre: 1) le contrat designe (contrat_id) s'il existe ; 2) un contrat du type
    demande couvrant la periode ; 3) tout contrat couvrant la periode (le plus
    recent). Retourne None si aucun contrat ne couvre la periode."""
    contrats = list(contrats or [])
    for c in contrats:
        if contrat_id and c.get('id') == contrat_id:
            return c
    couvrants = sorted((c for c in contrats if _couvre(c, debut, fin)),
                       key=lambda c: c['date_debut'], reverse=True)
    for c in couvrants:
        if type_contrat and c.get('type_contrat') == type_contrat:
            return c
    return couvrants[0] if couvrants else None
