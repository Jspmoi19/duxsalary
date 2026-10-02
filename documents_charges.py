# -*- coding: utf-8 -*-
"""
documents_charges.py -- DuxSalary
Documents de charges salariales, pour n'importe quelle periode:
  - compte individuel (par travailleur, une colonne par mois)
  - attestation salariale (par employeur, colonnes ouvriers / employes / total)
  - liste de ventilation (attestation + resume ONSS et precompte a verser)

Tout est calcule a partir des lignes de la table fiches_paie: ce module ne
recalcule AUCUN montant de paie, il additionne ce qui a ete enregistre a la
generation de chaque fiche. L'ecran (document_charges.html) et le PDF
(pdf_charges.py) affichent la meme structure:

    {'titre', 'periode', 'entete': [(libelle, valeur)], 'colonnes': [...],
     'sections': [{'titre', 'lignes': [{'libelle', 'valeurs', 'style', 'fmt'}]}],
     'avertissements': [...]}

Une valeur None signifie « detail non disponible »: la fiche a ete generee
avant l'ajout des colonnes de detail (detail_complet = FALSE) et doit etre
regeneree pour apparaitre en entier.
"""
import json
import re
from datetime import date

from occupation import libelle_etat_civil

MOIS = ['', 'Janv.', 'Févr.', 'Mars', 'Avril', 'Mai', 'Juin', 'Juil.', 'Août', 'Sept.', 'Oct.', 'Nov.', 'Déc.']
TAUX_PROVISION_EMPLOYES_DEFAUT = 18.80   # % -- provision ESTIMEE, modifiable par dossier
ND = 'n.d.'
SANS_FICHE = '—'   # mois sans fiche de paie


# ─────────────────────────────────────────────────────────────────
# ENREGISTREMENT: valeurs d'une fiche calculee -> colonnes de fiches_paie
# ─────────────────────────────────────────────────────────────────
def valeurs_fiche(data):
    """Colonnes de fiches_paie (hors identifiants, periode et PDF) a partir du
    resultat de calculer_fiche_paie. Source UNIQUE de ce qui est enregistre."""
    onss_exc = round(data.get('prime_onss', 0) + data.get('pecule_retenue', 0), 2)
    pp_exc = round(data.get('prime_precompte', 0) + data.get('pecule_precompte', 0), 2)
    onss_retenu = round(abs(data['onss_net']) + onss_exc, 2)
    fixe = data.get('salaire_mensuel_fixe') or 0
    return {
        'salaire_brut': round(data['brut_onss'] + data.get('prime_exceptionnelle', 0), 2),
        'onss_personnel': onss_retenu,
        'precompte': round(abs(data['precompte']) + pp_exc, 2),
        'salaire_net': data['salaire_net'],
        'total_onss': round(onss_retenu + data['onss_patronal'], 2),
        'onss_patronal': data['onss_patronal'],
        'cout_employeur': data['cout_employeur'],
        'bonus_emploi_a': data.get('bonus_emploi_a', 0), 'bonus_emploi_b': data.get('bonus_emploi_b', 0),
        'precompte_avant_reduction': abs(data.get('precompte_brut', 0)),
        'reduction_precompte_bonus': data.get('red_precompte_bonus', 0),
        'reduction_structurelle': data.get('reduction_structurelle', 0),
        'reduction_premier_engagement': data.get('reduction_premier_engagement', 0),
        'frais_nets_montant': data.get('frais_nets', 0),
        'jours_prestes': data.get('jours_prestes', 0), 'heures_prestees': data.get('heures_prestees', 0),
        'is_ouvrier': data.get('is_ouvrier'), 'is_etudiant': data.get('is_etudiant'),
        'cp_key': data.get('cp_key'), 'type_contrat': data.get('type_contrat'),
        'prime_brut': data.get('prime_exceptionnelle', 0), 'pecule_brut': data.get('double_pecule', 0),
        'onss_exceptionnel': onss_exc, 'precompte_exceptionnel': pp_exc,
        # ── detail pour les documents de charges ──
        'detail_complet': True,
        'jours_feries': data.get('jours_feries_payes', 0), 'heures_feries': data.get('heures_feries', 0),
        'jours_conge': data.get('jours_conge', 0), 'jours_maladie': data.get('jours_maladie', 0),
        'jours_absence_non_payee': data.get('jours_chomage', 0),
        'salaire_base': fixe if (fixe and not data.get('is_ouvrier')) else data.get('salaire_horaire'),
        'salaire_base_periodicite': 'mois' if (fixe and not data.get('is_ouvrier')) else 'heure',
        'remunerations': json.dumps([{'libelle': l['libelle'], 'montant': l['montant'],
                                      'jours': l.get('jours', 0), 'heures': l.get('heures', 0)}
                                     for l in data.get('lignes_salaire', [])], ensure_ascii=False),
        'libelle_prime': data.get('libelle_prime') if data.get('prime_exceptionnelle') else None,
        'brut_majore': data.get('brut_majore'),
        'onss_personnel_brut': abs(data['onss_travailleur']),
        'brut_imposable': data['brut_imposable'],
        'css': data.get('css', 0),
        'indemnites': json.dumps(data.get('indemnites_detail', []), ensure_ascii=False),
        'cr_part_travailleur': data.get('cr_part_travailleur', 0),
        'cr_part_employeur': data.get('cr_empl_total', 0),
        'onss_patronal_reductible': data.get('onss_patronal_reductible'),
        'onss_vacances_253': data.get('onss_vacances_trimestrielle', 0),
        'cotisations_complementaires': json.dumps(
            [{'code': c['code'], 'libelle': c['libelle'], 'taux': c['taux'], 'montant': c['montant']}
             for c in data.get('cotisations_complementaires', [])], ensure_ascii=False),
        'onss_patronal_prime': data.get('onss_patronal_prime', 0),
        'provision_vacances_ouvrier': data.get('provision_vacances_annuelles', 0),
        'onss_trimestre': data.get('onss_trimestre_utilise'),
        'categorie_employeur': data.get('onss_categorie_employeur'),
        # Jours et heures par code prestation ONSS (aide a la DmfA), calcules a la generation
        # par dmfa.prestations_occupation ; None pour un calcul hors calendrier
        'prestations_dmfa': data.get('prestations_dmfa'),
        # Reductions de cette fiche qui risquent de ne pas etre accordees a la DmfA (estimation du
        # plancher de 27,5 % sur le trimestre): reprises sur la lettre ONSS
        'patronal_risque_trimestre': data.get('patronal_risque_trimestre', 0),
        # Km domicile-travail saisis: reproposes dans le formulaire de la fiche suivante
        'km_domicile': data.get('km_domicile'), 'taux_km': data.get('taux_km'), 'moyen_transport': data.get('moyen_transport'),
    }


# ─────────────────────────────────────────────────────────────────
# OUTILS
# ─────────────────────────────────────────────────────────────────
def _n(v):
    return float(v) if v is not None else 0.0


def _liste(v):
    """Colonne JSONB (deja decodee par psycopg2) ou texte JSON -> liste."""
    if not v:
        return []
    return json.loads(v) if isinstance(v, str) else list(v)


def _libelle_remu(lib):
    return re.sub(r'\s*\(\d+\s*j\)', '', lib or '').strip()


def _groupe(f):
    """Statut de la fiche. Un mois sous contrat etudiant (indicateur etudiant OU
    type de contrat STU) est toujours « Étudiants »: jamais dans les employes."""
    if f.get('is_etudiant') or f.get('type_contrat') == 'STU':
        return 'Étudiants'
    return 'Ouvriers' if f.get('is_ouvrier') else 'Employés'


def _somme(fiches, valeur, detail=False):
    """Somme de valeur(f) sur les fiches. detail=True: None des qu'une fiche
    n'a pas le detail (on n'affiche jamais un total partiel comme s'il etait complet)."""
    if detail and any(not f.get('detail_complet') for f in fiches):
        return None
    return round(sum(_n(valeur(f)) for f in fiches), 2)


def _col(nom):
    return lambda f: f.get(nom)


def _dans_json(colonne, libelle, cle='libelle', normaliser=None):
    def valeur(f):
        return sum(_n(x.get('montant')) for x in _liste(f.get(colonne))
                   if (normaliser(x.get(cle)) if normaliser else x.get(cle)) == libelle)
    return valeur


def _libelles_json(fiches, colonne, cle='libelle', normaliser=None):
    vus = []
    for f in fiches:
        for x in _liste(f.get(colonne)):
            lib = normaliser(x.get(cle)) if normaliser else x.get(cle)
            if lib and lib not in vus:
                vus.append(lib)
    return vus


def _ligne(libelle, valeurs, style='normal', fmt='montant'):
    return {'libelle': libelle, 'valeurs': valeurs, 'style': style, 'fmt': fmt}


def _epurer(sections):
    """Retire les lignes ordinaires entierement vides (rubrique sans objet sur la
    periode), comme sur les documents des secretariats sociaux. Les totaux, les
    lignes d'information et les lignes « n.d. » restent toujours affiches."""
    for s in sections:
        s['lignes'] = [l for l in s['lignes']
                       if l['style'] != 'normal' or any(v is None or v not in (0, '', SANS_FICHE) for v in l['valeurs'])]
    return [s for s in sections if s['lignes']]


def _avertissements(fiches):
    anciennes = sum(1 for f in fiches if not f.get('detail_complet'))
    if not anciennes:
        return []
    return [f"{anciennes} fiche(s) générée(s) avant l'ajout du détail : les lignes marquées « {ND} » "
            f"(détail non disponible) seront complètes après régénération de ces fiches."]


def formater(valeur, fmt='montant'):
    """Affichage commun ecran / PDF. None -> n.d. ; zero -> vide (sauf totaux, geres
    par l'appelant) ; texte (dont « — » = mois sans fiche) -> tel quel. Les
    milliers sont separes par une espace INSECABLE: un montant ne se coupe jamais."""
    if valeur is None:
        return ND
    if isinstance(valeur, str) or fmt == 'texte':
        return str(valeur)
    if fmt == 'nombre':
        return f"{valeur:g}".replace('.', ',') if valeur else ''
    if not valeur:
        return ''
    return montant_fr(valeur)


def montant_fr(valeur, decimales=2):
    return f"{valeur:,.{decimales}f}".replace(',', ' ').replace('.', ',')


def mois_de_la_periode(date_debut, date_fin):
    mois, a, m = [], date_debut.year, date_debut.month
    while (a, m) <= (date_fin.year, date_fin.month):
        mois.append((a, m))
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    return mois


# Getters reutilises par les trois documents
_onss_brut = lambda f: _n(f.get('onss_personnel')) + _n(f.get('bonus_emploi_a')) + _n(f.get('bonus_emploi_b'))
_bonus = lambda f: _n(f.get('bonus_emploi_a')) + _n(f.get('bonus_emploi_b'))
_imposable = lambda f: (_n(f.get('brut_imposable')) + _n(f.get('prime_brut')) + _n(f.get('pecule_brut'))
                        - _n(f.get('onss_exceptionnel')))
_indemnites = lambda f: sum(_n(x.get('montant')) for x in _liste(f.get('indemnites')))
_brut_regulier = lambda f: _n(f.get('salaire_brut')) - _n(f.get('prime_brut'))


# ─────────────────────────────────────────────────────────────────
# COMPTE INDIVIDUEL
# ─────────────────────────────────────────────────────────────────
def compte_individuel(fiches, travailleur, dossier, date_debut, date_fin, contrat=None, date_entree=None):
    """fiches: lignes de fiches_paie du travailleur dans la periode.
    date_entree: date de la PREMIERE occupation chez l'employeur (premier contrat,
    etudiant compris) ; a defaut, debut du contrat transmis."""
    mois = mois_de_la_periode(date_debut, date_fin)
    par_mois = [[f for f in fiches if (f['periode_debut'].year, f['periode_debut'].month) == am] for am in mois]
    groupes = par_mois + [fiches]   # derniere colonne = total

    def ligne(libelle, valeur, detail=False, style='normal', fmt='montant'):
        mois_ = [_somme(g, valeur, detail) if g else SANS_FICHE for g in par_mois]
        return _ligne(libelle, mois_ + [_somme(fiches, valeur, detail) if fiches else 0], style, fmt)

    def base(g):
        if not g:
            return SANS_FICHE
        f = g[-1]
        if not f.get('detail_complet') or f.get('salaire_base') is None:
            return None
        if f.get('salaire_base_periodicite') == 'mois':
            return montant_fr(_n(f['salaire_base'])) + ' €/mois'      # 2 257,00 €/mois
        return montant_fr(_n(f['salaire_base']), 4) + ' €/h'           # 15,2097 €/h

    prestations = [
        _ligne('Salaire de base', [base(g) for g in par_mois] + [''], fmt='texte'),
        ligne('Jours prestés', _col('jours_prestes'), fmt='nombre'),
        ligne('Jours fériés payés', _col('jours_feries'), True, fmt='nombre'),
        ligne('Jours de congé', _col('jours_conge'), True, fmt='nombre'),
        ligne('Jours de maladie', _col('jours_maladie'), True, fmt='nombre'),
        ligne('Jours d\'absence non payée', _col('jours_absence_non_payee'), True, fmt='nombre'),
        ligne('Heures prestées', _col('heures_prestees'), fmt='nombre'),
        ligne('Heures fériés payés', _col('heures_feries'), True, fmt='nombre'),
    ]
    remu = [ligne(lib, _dans_json('remunerations', lib, normaliser=_libelle_remu), True)
            for lib in _libelles_json(fiches, 'remunerations', normaliser=_libelle_remu)]
    remu += [
        ligne('Primes (fin d\'année, annuelle…)', _col('prime_brut')),
        ligne('BRUT', _col('salaire_brut'), style='total'),
        ligne('Brut majoré (base ONSS, 108 % ouvriers)', _col('brut_majore'), True, style='info'),
        ligne('Double pécule de vacances', _col('pecule_brut')),
    ]
    retenues = [
        ligne('ONSS personnel', lambda f: -_onss_brut(f)),
        ligne('Bonus à l\'emploi (volet A)', _col('bonus_emploi_a')),
        ligne('Bonus à l\'emploi (volet B)', _col('bonus_emploi_b')),
        ligne('ONSS retenu', lambda f: -_n(f.get('onss_personnel')), style='total'),
        ligne('IMPOSABLE', _imposable, True, style='total'),
        ligne('Précompte professionnel', lambda f: -_n(f.get('precompte'))),
        ligne('Cotisation spéciale de sécurité sociale', lambda f: -_n(f.get('css')), True),
    ]
    hors = [ligne(lib, _dans_json('indemnites', lib), True) for lib in _libelles_json(fiches, 'indemnites')]
    hors.append(ligne('Chèques-repas – part travailleur', lambda f: -_n(f.get('cr_part_travailleur')), True))
    net = [ligne('NET', _col('salaire_net'), style='total')]

    t, d, c = travailleur or {}, dossier or {}, contrat or {}
    jj = lambda x: x.strftime('%d/%m/%Y') if x else ''
    sexe = {'M': 'Masculin', 'F': 'Féminin', 'X': 'Autre'}.get(t.get('sexe') or '', '')
    entete = [
        ('Employeur', d.get('nom') or ''), ('Adresse', d.get('adresse') or ''),
        ('N° d\'entreprise', d.get('bce') or ''), ('N° ONSS', d.get('rsz') or ''),
        ('Caisse de vacances', d.get('caisse_vacances') or ''), ('Assurance-loi', d.get('assurance_at') or ''),
        ('Assurance-groupe', d.get('assurance_groupe') or ''), ('Service médical', d.get('service_medical') or ''),
        ('Travailleur', f"{t.get('nom') or ''} {t.get('prenom') or ''}".strip()), ('Adresse du travailleur', t.get('adresse') or ''),
        ('N° registre national', t.get('niss') or ''), ('Date de naissance', jj(t.get('date_naissance'))),
        ('Sexe', sexe), ('Nationalité', t.get('nationalite') or ''),
        ('État civil', libelle_etat_civil(t.get('etat_civil'))),
        ('Caisse d\'alloc. familiales', t.get('caisse_allocations_familiales') or ''),
        ('Date d\'entrée', jj(date_entree or c.get('date_debut'))), ('Date de sortie', jj(t.get('date_sortie'))),
        ('Commission paritaire', c.get('cp_key') or ''), ('Fonction', c.get('fonction') or ''),
        ('Type de contrat', c.get('type_contrat') or ''),
        ('Régime de travail', f"{_n(c.get('heures_semaine')):g} h/sem." if c.get('heures_semaine') else ''),
    ]
    return {
        'type': 'compte_individuel', 'titre': 'Compte individuel',
        'periode': (date_debut, date_fin), 'entete': entete,
        'colonnes': [f"{MOIS[m]} {a}" for a, m in mois] + ['Total'],
        'sections': _epurer([{'titre': 'Prestations', 'lignes': prestations},
                             {'titre': 'Rémunérations', 'lignes': remu},
                             {'titre': 'Retenues', 'lignes': retenues},
                             {'titre': 'Indemnités et retenues nettes', 'lignes': hors},
                             {'titre': 'Net', 'lignes': net}]),
        'avertissements': _avertissements(fiches),
    }


# ─────────────────────────────────────────────────────────────────
# ATTESTATION SALARIALE ET LISTE DE VENTILATION
# ─────────────────────────────────────────────────────────────────
def _document_employeur(fiches, dossier, date_debut, date_fin):
    d = dossier or {}
    noms = ['Ouvriers', 'Employés', 'Étudiants']   # toujours les trois statuts, puis le total
    groupes = [[f for f in fiches if _groupe(f) == g] for g in noms] + [fiches]
    colonnes = noms + ['Total']

    def ligne(libelle, valeur, detail=False, style='normal', fmt='montant'):
        return _ligne(libelle, [_somme(g, valeur, detail) for g in groupes], style, fmt)

    def seulement(nom_groupe, valeur, detail=False):
        """Valeur qui ne concerne qu'un statut (vide dans les autres colonnes)."""
        return [_somme([f for f in g if _groupe(f) == nom_groupe], valeur, detail) for g in groupes]

    remu = [ligne(lib, _dans_json('remunerations', lib, normaliser=_libelle_remu), True)
            for lib in _libelles_json(fiches, 'remunerations', normaliser=_libelle_remu)]
    remu += [ligne('Primes (fin d\'année, annuelle…)', _col('prime_brut')),
             ligne('TOTAL BRUT', _col('salaire_brut'), style='total'),
             ligne('Double pécule de vacances', _col('pecule_brut'))]

    travailleur = [
        ligne('ONSS travailleur', lambda f: -_onss_brut(f)),
        ligne('Bonus à l\'emploi', _bonus),
        ligne('ONSS travailleur retenu', lambda f: -_n(f.get('onss_personnel')), style='total'),
    ]
    travailleur += [ligne(lib, _dans_json('indemnites', lib), True) for lib in _libelles_json(fiches, 'indemnites')]
    travailleur += [
        ligne('TOTAL HORS ONSS (indemnités)', _indemnites, True, style='total'),
        ligne('IMPOSABLE', _imposable, True, style='total'),
        ligne('Précompte professionnel', lambda f: -_n(f.get('precompte'))),
        ligne('Cotisation spéciale de sécurité sociale', lambda f: -_n(f.get('css')), True),
        ligne('Chèques-repas – part travailleur', lambda f: -_n(f.get('cr_part_travailleur')), True),
        ligne('NET', _col('salaire_net'), style='total'),
    ]

    codes = {}
    for f in fiches:
        for c in _liste(f.get('cotisations_complementaires')):
            codes.setdefault(c['code'], c.get('libelle') or f"Cotisation {c['code']}")
    patronal = [ligne('Cotisation de base + modération salariale', _col('onss_patronal_reductible'), True)]
    if any(_n(f.get('onss_vacances_253')) for f in fiches):
        patronal.append(ligne('Vacances annuelles ouvriers 5,57 % (code 253)', _col('onss_vacances_253'), True))
    for code in sorted(codes):
        lib = codes[code]
        patronal.append(ligne(f"{code} – {lib[:62]}{'…' if len(lib) > 62 else ''}",
                              _dans_json('cotisations_complementaires', code, cle='code'), True))
    if any(_n(f.get('onss_patronal_prime')) for f in fiches):
        patronal.append(ligne('Cotisations patronales sur les primes', _col('onss_patronal_prime'), True))
    patronal += [
        ligne('Réduction structurelle', lambda f: -_n(f.get('reduction_structurelle'))),
        ligne('ONSS patronal après réduction structurelle',
              lambda f: _n(f.get('onss_patronal')) + _n(f.get('reduction_premier_engagement')), style='total'),
        ligne('Réduction premier engagement', lambda f: -_n(f.get('reduction_premier_engagement'))),
        ligne('ONSS PATRONAL NET', _col('onss_patronal'), style='total'),
    ]

    divers = [ligne('Chèques-repas – part employeur', _col('cr_part_employeur'), True)]

    taux = _n(d.get('taux_provision_pecule_employes')) if d.get('taux_provision_pecule_employes') is not None \
        else TAUX_PROVISION_EMPLOYES_DEFAUT
    base_empl = seulement('Employés', _brut_regulier)
    provisions = [
        _ligne('Ouvriers – base (rémunérations à 108 %)', seulement('Ouvriers', _col('brut_majore'), True), 'info'),
        _ligne('Ouvriers – cotisation annuelle vacances 10,27 % (avis de débit ONSS)',
               seulement('Ouvriers', _col('provision_vacances_ouvrier'), True)),
        _ligne('Employés – base (brut hors primes)', base_empl, 'info'),
        _ligne(f"Employés – provision estimée ({taux:.2f} %)".replace('.', ','),
               [round(b * taux / 100, 2) for b in base_empl]),
    ]

    informatif = [
        ligne('Jours prestés', _col('jours_prestes'), fmt='nombre'),
        ligne('Jours rémunérés non prestés (fériés, congés)',
              lambda f: _n(f.get('jours_feries')) + (0 if f.get('is_ouvrier') else _n(f.get('jours_conge'))), True, fmt='nombre'),
        ligne('Heures prestées', _col('heures_prestees'), fmt='nombre'),
        ligne('Heures fériés payés', _col('heures_feries'), True, fmt='nombre'),
        ligne('Nombre de fiches', lambda f: 1, fmt='nombre'),
    ]

    total = [ligne('TOTAL FRAIS SALARIAUX (hors provisions de pécule)',
                   lambda f: (_n(f.get('salaire_brut')) + _n(f.get('pecule_brut')) + _indemnites(f)
                              + _n(f.get('onss_patronal')) + _n(f.get('cr_part_employeur'))), True, style='total')]

    entete = [('Employeur', d.get('nom') or ''), ('Adresse', d.get('adresse') or ''),
              ('N° d\'entreprise', d.get('bce') or ''), ('N° ONSS', d.get('rsz') or '')]
    sections = [{'titre': 'Rémunérations', 'lignes': remu},
                {'titre': 'Travailleur', 'lignes': travailleur},
                {'titre': 'ONSS patronal', 'lignes': patronal},
                {'titre': 'Divers', 'lignes': divers},
                {'titre': 'Provisions pécule de vacances', 'lignes': provisions},
                {'titre': 'Informatif', 'lignes': informatif},
                {'titre': 'Total', 'lignes': total}]
    return {'periode': (date_debut, date_fin), 'entete': entete, 'colonnes': colonnes,
            'sections': _epurer(sections), 'avertissements': _avertissements(fiches)}, ligne


def attestation_salariale(fiches, dossier, date_debut, date_fin):
    doc, _ = _document_employeur(fiches, dossier, date_debut, date_fin)
    doc.update(type='attestation', titre='Attestation salariale')
    return doc


def liste_ventilation(fiches, dossier, date_debut, date_fin):
    """Attestation + resume des montants a verser a l'ONSS et au SPF Finances."""
    doc, ligne = _document_employeur(fiches, dossier, date_debut, date_fin)
    resume_onss = [
        ligne('ONSS travailleur', _onss_brut),
        ligne('Bonus à l\'emploi', lambda f: -_bonus(f)),
        ligne('Total travailleur', _col('onss_personnel'), style='total'),
        ligne('Cotisation spéciale de sécurité sociale', _col('css'), True),
        ligne('ONSS patronal net', _col('onss_patronal')),
        ligne('TOTAL GÉNÉRAL ONSS', lambda f: _n(f.get('onss_personnel')) + _n(f.get('css')) + _n(f.get('onss_patronal')),
              True, style='total'),
    ]
    resume_pp = [ligne('TOTAL PRÉCOMPTE PROFESSIONNEL', _col('precompte'), style='total')]
    doc['sections'] += _epurer([{'titre': 'Résumé ONSS', 'lignes': resume_onss},
                                {'titre': 'Résumé précompte professionnel', 'lignes': resume_pp}])
    doc.update(type='ventilation', titre='Liste de ventilation comptable')
    return doc
