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


def charges_famille_du_formulaire(form):
    """Situation familiale et charges de famille saisies dans les formulaires
    travailleur (gabarit _charges_famille.html) -> colonnes de `travailleurs`.
    Ce sont les donnees lues par le calcul du precompte (annexes 3 a 5 de la
    formule-cle): rien n'est calcule ici."""
    def entier(nom):
        try:
            return max(0, int(form.get(nom) or 0))
        except (TypeError, ValueError):
            return 0
    etat_civil = form.get('etat_civil') or 'celibataire'
    if etat_civil not in LIBELLES_ETAT_CIVIL:
        etat_civil = 'celibataire'
    return {
        'etat_civil': etat_civil,
        'partenaire_revenus_pro': form.get('partenaire_revenus_pro') or 'non',
        'partenaire_pensions': form.get('partenaire_pensions') or 'non',
        'nb_enfants_sans_handicap': entier('nb_enfants_sans_handicap'),
        'nb_enfants_avec_handicap': entier('nb_enfants_avec_handicap'),
        'nb_personnes_charge_66': entier('nb_personnes_charge_66'),
        'nb_autres_personnes_charge': entier('nb_autres_personnes_charge'),
        'parent_isole': form.get('parent_isole') == 'on',
        'handicape': form.get('handicape') == 'on',
        'conjoint_handicape': form.get('conjoint_handicape') == 'on',
    }


def personnel_roulant(categorie_personnel):
    """Type de personnel du travailleur (travailleurs.categorie_personnel, saisi dans le
    suivi des cheques): True = roulant, False = non roulant ou garage, None = non renseigne."""
    c = (categorie_personnel or '').strip()
    return None if not c else c == 'roulant'


def rgpt_coche_par_defaut(categorie_personnel):
    """Case RGPT du formulaire de generation en CP 140.03: cochee par defaut pour le
    personnel roulant ou quand le type de personnel n'est pas renseigne, decochee pour
    le personnel non roulant et de garage. Simple valeur par defaut: Leo peut la changer."""
    return personnel_roulant(categorie_personnel) is not False


def contrat_actif(contrat, aujourd_hui=None):
    """Un contrat compte comme ACTIF quand son statut est « actif » ET que sa date de fin
    est vide ou n'est pas encore depassee (un contrat qui se termine aujourd'hui est encore
    actif aujourd'hui). Rien n'est modifie en base: un contrat echu garde son statut."""
    from datetime import date as _date
    jour = aujourd_hui or _date.today()
    return contrat.get('statut', 'actif') == 'actif' and (not contrat.get('date_fin') or contrat['date_fin'] >= jour)


def contrats_actifs(contrats, aujourd_hui=None):
    return [c for c in contrats or [] if contrat_actif(c, aujourd_hui)]


def km_a_proposer(derniere_fiche, km_travailleur=None, taux_defaut=0.4444):
    """Km domicile-travail, taux et moyen de transport proposes dans le formulaire de
    generation: ceux de la DERNIERE fiche du travailleur (pour ne pas les oublier), a
    defaut les km de la fiche du travailleur et le taux maximal. Simple proposition:
    Leo peut les modifier. Retourne {'km', 'taux', 'moyen_transport', 'origine'}."""
    f = derniere_fiche or {}
    if f.get('km_domicile') is not None:
        return {'km': int(f['km_domicile']), 'taux': float(f['taux_km'] if f.get('taux_km') is not None else taux_defaut),
                'moyen_transport': f.get('moyen_transport') or 'voiture',
                'origine': f"repris de la fiche de {f['periode_debut']:%m/%Y}" if f.get('periode_debut') else 'repris de la dernière fiche'}
    return {'km': int(km_travailleur or 0), 'taux': float(taux_defaut), 'moyen_transport': 'voiture', 'origine': None}


def libelle_statut_profession(is_ouvrier, is_etudiant, fonction=None):
    """« Statut/Profession » de la fiche de paie: statut du travailleur et fonction du
    contrat (« Employé — Comptable »), jamais la categorie du bareme."""
    statut = 'Étudiant' if is_etudiant else ('Ouvrier' if is_ouvrier else 'Employé')
    fonction = (fonction or '').strip()
    return f"{statut} — {fonction}" if fonction and fonction != '—' else statut


# Libelles de categorie trop generiques pour etre lus seuls sur une fiche de paie
CATEGORIES_GENERIQUES = ('minimum sectoriel',)


def libelle_categorie_bareme(categorie, cp_key=None):
    """« Catégorie prof. »: la categorie du bareme telle qu'elle est enregistree ; un
    libelle officiel generique (« Minimum sectoriel ») est complete par la CP."""
    import unicodedata
    texte = (categorie or '').strip() or '—'
    simple = unicodedata.normalize('NFD', texte).encode('ascii', 'ignore').decode().lower()
    if simple in ('etudiant', 'etudiante', 'etudiant(e)'):
        return 'Étudiant'
    if simple in CATEGORIES_GENERIQUES and cp_key and cp_key.lower() not in simple:
        return f"{texte} {cp_key}"
    return texte


def premier_engagement_du_travailleur(dossier_coche, travailleur_coche, nb_designes):
    """Reduction « premier engagement » (1er travailleur, code 3315): le dossier ouvre le
    droit (case et date de debut), la reduction ne vise que LE travailleur designe dans sa
    fiche -- un seul par dossier. Retourne (appliquer, alerte ou None)."""
    if not dossier_coche:
        if travailleur_coche:
            return False, ("Premier engagement : ce travailleur est désigné, mais la case « premier engagement » du dossier "
                           "n'est pas cochée — réduction non appliquée.")
        return False, None
    if nb_designes == 0:
        return False, ("Premier engagement : le dossier ouvre le droit, mais aucun travailleur n'est désigné — réduction non "
                       "appliquée. Cochez la case dans la fiche du travailleur qui ouvre le droit.")
    if nb_designes > 1:
        return bool(travailleur_coche), ("Premier engagement : plusieurs travailleurs du dossier sont désignés, un seul peut "
                                         "l'être (les 2e à 6e travailleurs ne sont pas gérés).")
    return bool(travailleur_coche), None


def commune_de_l_adresse(adresse):
    """Commune d'une adresse belge (« Rue X 2, 1853 Grimbergen » -> « Grimbergen »),
    pour le lieu de signature des contrats. Chaine vide si elle n'est pas reconnue."""
    import re
    m = re.search(r'\b\d{4}\s+([^,;\d]+?)\s*$', (adresse or '').strip())
    if not m:
        return ''
    commune = m.group(1).strip(' -')
    return commune.title() if commune.isupper() else commune


def suivi_contingent_etudiant(heures_deja, heures_contrat, reference_date, heures_autres_employeurs=0):
    """Suivi du contingent etudiant de l'annee civile de reference_date. Le
    contingent vaut PAR ETUDIANT, tous employeurs confondus:
    - heures_deja: heures deja prestees cette annee CHEZ CET EMPLOYEUR (calendrier) ;
    - heures_autres_employeurs: heures chez d'autres employeurs, saisies d'apres
      l'attestation Student@work de l'etudiant (l'outil ne peut pas les connaitre).
    Retourne un dict (plafond, deja, autres, contrat, restant, depassement, alerte,
    source) ; plafond None si le contingent de l'annee n'est pas charge."""
    from parametres_dates import get_contingent_etudiant
    v = get_contingent_etudiant(reference_date)
    deja, contrat = round(float(heures_deja or 0), 2), round(float(heures_contrat or 0), 2)
    autres = round(float(heures_autres_employeurs or 0), 2)
    if v is None:
        return {'annee': reference_date.year, 'plafond': None, 'deja': deja, 'autres': autres, 'contrat': contrat,
                'restant': None, 'depassement': 0.0, 'source': None,
                'alerte': f"Contingent étudiant {reference_date.year} non chargé dans l'outil : non contrôlé."}
    plafond = float(v['heures'])
    depassement = round(max(0.0, deja + autres + contrat - plafond), 2)
    alerte = None
    if depassement > 0:
        alerte = (f"Ce contrat fait dépasser le contingent étudiant de {plafond:g} heures pour {reference_date.year} "
                  f"({deja:g} h chez cet employeur + {autres:g} h chez d'autres employeurs + {contrat:g} h prévues) : "
                  f"{depassement:g} h au-delà du contingent, soumises aux cotisations ordinaires.")
    return {'annee': reference_date.year, 'plafond': plafond, 'deja': deja, 'autres': autres, 'contrat': contrat,
            'restant': round(max(0.0, plafond - deja - autres), 2), 'depassement': depassement,
            'alerte': alerte, 'source': v['source']}


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
