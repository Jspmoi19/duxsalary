# -*- coding: utf-8 -*-
"""
branding.py -- DuxSalary
EMPLACEMENT UNIQUE de l'identite visuelle des documents PDF: nom, logo,
couleurs, pied de page. Tout nouveau PDF doit passer par get_branding() et ne
jamais definir ses propres couleurs ou son propre nom.

Source: la table `tenants` (multi-tenant) quand un tenant est fourni, sinon les
valeurs par defaut ci-dessous. Pour changer la charte: modifier DEFAUT (ou la
ligne du tenant) et deposer le logo dans static/logo.png.

Les anciens PDF (fiches de paie, contrats, lettres ONSS) ont encore leurs
couleurs en dur: ils seront branches ici lors du rebranding (tache 1).
"""
import os

RACINE = os.path.dirname(os.path.abspath(__file__))

DEFAUT = {
    'nom': 'DuxSalary',
    'logo_text': 'DuxSalary',
    'logo_path': os.path.join(RACINE, 'static', 'logo.png'),   # utilise s'il existe
    'couleur_primaire': '#1F4E79',
    'couleur_accent': '#4fc3f7',
    'couleur_texte': '#1a1a1a',
    'couleur_texte_secondaire': '#555555',
    'couleur_fond_clair': '#f5f5f5',
    'couleur_ligne': '#cccccc',
    'pied_de_page': 'Document établi avec DuxSalary',
}


def get_branding(tenant=None):
    """Identite visuelle a appliquer. tenant: dict de la table tenants (ou None)."""
    b = dict(DEFAUT)
    t = tenant or {}
    for cle in ('nom', 'logo_text', 'logo_path', 'couleur_primaire', 'couleur_accent', 'pied_de_page'):
        if t.get(cle):
            b[cle] = t[cle]
    if t.get('nom') and not t.get('pied_de_page'):
        b['pied_de_page'] = f"Document établi avec {t['nom']}"
    if not (b['logo_path'] and os.path.exists(b['logo_path'])):
        b['logo_path'] = None   # pas de fichier: le nom est affiche en texte
    return b
