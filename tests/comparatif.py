# -*- coding: utf-8 -*-
"""
tests/comparatif.py -- DuxSalary
Comparatif du moteur avec les fiches de paie REELLES de sources/fiches_reference/
(dossier hors de GitHub). A relancer apres chaque modification du moteur:

    python tests/comparatif.py

Les donnees sont LUES dans les PDF a chaque execution: aucun nom, NISS ou IBAN
n'est ecrit dans ce fichier, ni affiche (les fiches sont designees par leur
numero d'ordre, leur CP et leur periode). Necessite: pip install pypdf.

Format gere: "FICHE DE PAIE" Interconsult / Easypay (une fiche par page).
Les autres documents (comptes individuels, attestations, ventilations) et les
annees dont les parametres ne sont pas charges sont signales et ignores.

Les CP absentes de regles_cp.py ne sont PAS calculees comme telles: seul le
SOCLE COMMUN (ONSS personnel, bonus emploi, precompte, CSS) est compare, via un
profil de substitution du meme statut. Les indemnites sectorielles et l'ONSS
patronal sont affiches pour information ("hors socle").
Code de sortie: 1 s'il reste un ecart sur le socle commun, 0 sinon.
"""
import os
import re
import sys
from datetime import date, datetime

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
DOSSIER_FICHES = os.path.join(RACINE, 'sources', 'fiches_reference')
PROFIL_SUBSTITUT = {'ouvrier': 'CP 140.03', 'employe': 'CP 200'}
TOLERANCE = 0.015


def nb(txt):
    return float(txt.replace('.', '').replace(',', '.'))


def cherche(motif, texte, defaut=None):
    m = re.search(motif, texte, re.M)
    return m.groups() if m else defaut


def jour(txt):
    return datetime.strptime(txt, '%d/%m/%Y').date()


def lire_fiche(texte):
    """Extrait les donnees d'une page 'FICHE DE PAIE'. Retourne un dict, ou
    None si une donnee indispensable est illisible (pas de valeur devinee)."""
    periode = cherche(r'^(\d{2}/\d{2}/\d{4}) - (\d{2}/\d{2}/\d{4})$', texte)
    horaire = cherche(r'Salaire horaire (\d+,\d+)', texte)
    fraction = cherche(r'Fraction temps de travail (\d+,\d+) / (\d+,\d+)', texte)
    prestees = cherche(r'^1101 HEURES PRESTEES (\d+,\d{2}) \d+,\d{4} (\d+,\d{2}) ?(\d+,\d{2})$', texte)
    totaux = cherche(r'ACOMPTE NET\n([\d ,.]+)$', texte)
    net = cherche(r'NET À PAYER ([\d.]+,\d{2})', texte)
    if not (periode and horaire and fraction and prestees and totaux and net):
        return None
    feries = cherche(r'^1102 HEURES JOUR FERIE (\d+,\d{2}) \d+,\d{4} (\d+,\d{2}) ?(\d+,\d{2})$', texte)
    t = [nb(x) for x in totaux[0].split()]   # brut, brut 108, ONSS, hors ONSS, imposable, [PP], hors PP
    categorie_cat = (cherche(r'Catégorie (.+)$', texte) or ('',))[0].lower()
    statut = 'ouvrier' if 'ouvrier' in categorie_cat else 'employe'
    ligne = lambda motif: nb((cherche(motif, texte) or ('0',))[-1])
    return {
        'debut': jour(periode[0]), 'fin': jour(periode[1]),
        'entree': jour((cherche(r"Date d'entrée contrat (\d{2}/\d{2}/\d{4})", texte) or (periode[0],))[0]),
        'cp': (cherche(r'Commission paritaire (\S+)', texte) or ('?',))[0],
        'statut': statut,
        'marie': 'mari' in (cherche(r'Etat civil (\S+)', texte) or ('',))[0].lower(),
        'cat_employeur': (cherche(r'^(\d{3})-\d{7}-\d{2}$', texte) or ('000',))[0],
        'salaire_horaire': nb(horaire[0]),
        'heures_semaine_trav': nb(fraction[0]), 'heures_semaine_ref': nb(fraction[1]),
        'heures': nb(prestees[0]), 'jours': int(nb(prestees[2])),
        'heures_feries': nb(feries[0]) if feries else 0.0, 'jours_feries': int(nb(feries[2])) if feries else 0,
        'ref': {
            'brut': t[0], 'onss': t[2],
            'bonus_a': ligne(r'BONUS EMPLOI \(VOLET A\) ([\d.]+,\d{2})'),
            'bonus_b': ligne(r'BONUS EMPLOI \(VOLET B\) ([\d.]+,\d{2})'),
            'pp': t[5] if len(t) >= 7 else 0.0,
            'deplacement': ligne(r'^2293 .* ([\d.]+,\d{2})$'),
            'vetements': ligne(r'^2362 .* ([\d.]+,\d{2})$'),
            'net': nb(net[0]),
            'patronal': ligne(r'ONSS PATR ([\d.]+,\d{2})'),
        },
    }


def recalculer(f):
    from moteur_paie import calculer_fiche_paie
    return calculer_fiche_paie(
        '-', '-', '-', '-', '-', date(1990, 1, 1), f['entree'], '-', '-', '-', '-',
        PROFIL_SUBSTITUT[f['statut']], '-', f['salaire_horaire'],
        etat_civil='marie' if f['marie'] else 'celibataire',
        heures_semaine=f['heures_semaine_ref'],
        heures_jour=round(f['heures'] / f['jours'], 2) if f['jours'] else 0.0,
        jours_semaine=5, type_contrat='CDI', premier_engagement=False,
        jours_prestes=f['jours'], heures_prestees=f['heures'],
        jours_feries_payes=f['jours_feries'], heures_feries=f['heures_feries'],
        rgpt_actif=False, cheques_repas=False,
        categorie_employeur=f['cat_employeur'], periode_debut=f['debut'], periode_fin=f['fin'])


def comparer(f, r):
    """Affiche le tableau des ecarts ; retourne le nombre d'ecarts sur le socle."""
    ind = lambda mot: round(sum(l['montant'] for l in r['lignes_indemn'] if mot in l['libelle'].lower()), 2)
    ref = f['ref']
    lignes = [
        (True,  'Brut ONSS',          ref['brut'],    r['brut_onss']),
        (True,  'ONSS personnel',     ref['onss'],    -r['onss_travailleur']),
        (True,  'Bonus emploi A',     ref['bonus_a'], r['bonus_emploi_a']),
        (True,  'Bonus emploi B',     ref['bonus_b'], r['bonus_emploi_b']),
        (True,  'Precompte',          ref['pp'],      -r['precompte']),
        (False, 'Deplacement',        ref['deplacement'], ind('déplacement') + ind('km')),
        (False, 'Vetements',          ref['vetements'],   ind('vêtements')),
        (False, 'NET',                ref['net'],     r['salaire_net']),
        (False, 'ONSS patronal net',  ref['patronal'], r['onss_patronal']),
    ]
    print(f"  {'Ligne':<20}{'Fiche':>10}{'Moteur':>10}{'Ecart':>10}")
    ecarts = 0
    for socle, libelle, fiche, moteur in lignes:
        e = round(moteur - fiche, 2)
        marque = ''
        if abs(e) > TOLERANCE:
            marque = '  <-- ECART' if socle else '  (hors socle)'
            ecarts += 1 if socle else 0
        print(f"  {libelle:<20}{fiche:>10.2f}{moteur:>10.2f}{e:>+10.2f}{marque}")
    return ecarts


def main():
    try:
        from pypdf import PdfReader
    except ImportError:
        print("pypdf manquant: pip install pypdf"); return 2
    if not os.path.isdir(DOSSIER_FICHES):
        print(f"Dossier introuvable: {DOSSIER_FICHES}"); return 2
    pdfs = sorted(os.path.join(d, n) for d, _, noms in os.walk(DOSSIER_FICHES)
                  for n in noms if n.lower().endswith('.pdf'))
    total_fiches = total_ecarts = 0
    for i, chemin in enumerate(pdfs, 1):
        pages = [p.extract_text() or '' for p in PdfReader(chemin).pages]
        fiches = [t for t in pages if 'FICHE DE PAIE' in t]
        if not fiches:
            print(f"\nDocument {i} ({len(pages)} p.): pas de fiche de paie mensuelle au format gere -- ignore.")
            continue
        for texte in fiches:
            f = lire_fiche(texte)
            if f is None:
                print(f"\nDocument {i}: une page 'FICHE DE PAIE' illisible -- ignoree."); continue
            print(f"\nDocument {i} -- CP {f['cp']} {f['statut']} {f['heures_semaine_trav']:g}/{f['heures_semaine_ref']:g}"
                  f" -- du {f['debut']:%d/%m/%Y} au {f['fin']:%d/%m/%Y}"
                  f" (socle via profil {PROFIL_SUBSTITUT[f['statut']]}, cat. employeur {f['cat_employeur']})")
            try:
                r = recalculer(f)
            except Exception as e:   # ex.: parametres de l'annee non charges
                print(f"  Non recalculee -- {type(e).__name__}: {e}"); continue
            total_fiches += 1
            total_ecarts += comparer(f, r)
    print('\n' + '=' * 70)
    print(f"{total_fiches} fiche(s) recalculee(s), {total_ecarts} ecart(s) sur le socle commun.")
    return 1 if total_ecarts else 0


if __name__ == '__main__':
    sys.exit(main())
