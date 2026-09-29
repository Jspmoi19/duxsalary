# -*- coding: utf-8 -*-
"""
conges_legaux.py — DuxSalary
Calcul des droits aux conges legaux et du pecule de vacances, Belgique.

Principe fondamental (loi coordonnee du 28/06/1971 sur les vacances
annuelles): les conges de l'ANNEE N se calculent sur le travail preste
durant l'EXERCICE DE VACANCES = annee N-1. Un travailleur qui n'a pas
preste du tout en N-1 (ex: nouvel entrant sur le marche du travail,
etudiant, premier emploi) n'a AUCUN droit a conges payes en N.

Employe: conges + pecule geres et payes DIRECTEMENT par l'employeur.
Ouvrier: conges geres par l'employeur (nombre de jours), mais le PECULE
(l'argent) est calcule et paye par l'ONVA ou une caisse de vacances
sectorielle -- PAS par l'employeur sur la fiche de paie mensuelle.

Sources recoupees le 29/09/2026: calculateur-de-salaire.be, Securex,
Shyfter, ONVA (onva.fgov.be) -- gratuites/publiques, pas de source unique
"officielle" telechargeable comme pour le precompte, mais convergentes
sur tous les taux (8%/7.38%/15.38% ouvrier, 92% employe).
"""


# Statuts qui N'OUVRENT AUCUN DROIT aux conges payes ni au pecule.
# Raison: ces travailleurs ne paient qu'une cotisation de solidarite reduite
# (2.71% etudiant) au lieu des cotisations ordinaires (13.07%) -- or le droit
# aux vacances annuelles se construit UNIQUEMENT sur les cotisations
# ordinaires. Verifie le 29/09/2026 sur 6 sources independantes concordantes:
# Infor Jeunes, Bruxelles-J, Wikifin (autorite publique), studentatwork.be
# (site officiel ONSS), CSC, Trixxo.
# ==> Les mois prestes sous contrat STU ne comptent PAS dans
#     mois_prestes_annee_precedente. L'etudiant garde par contre ses droits
#     aux jours feries legaux (regle distincte, non geree ici).
STATUTS_SANS_DROIT_CONGES = ('etudiant',)
TYPES_CONTRAT_SANS_DROIT_CONGES = ('STU',)


def mois_ouvrant_droit(mois_par_type_contrat: dict) -> int:
    """Calcule le nombre de mois qui ouvrent reellement un droit a conges,
    en excluant les periodes sous statut etudiant (STU) ou assimile.

    mois_par_type_contrat: dict {type_contrat: nombre_de_mois}
        ex: {'STU': 2, 'CDI': 3} -> retourne 3 (seuls les mois CDI comptent)
    """
    total = 0
    for type_contrat, nb_mois in mois_par_type_contrat.items():
        if type_contrat and type_contrat.upper() in TYPES_CONTRAT_SANS_DROIT_CONGES:
            continue  # STU: aucun droit ouvert
        total += int(nb_mois or 0)
    return min(12, total)


def jours_conges_acquis(statut: str, jours_semaine_ref: float,
                         mois_prestes_annee_precedente: int,
                         jours_semaine_annee_precedente: float = None) -> float:
    """Nombre de jours de conges legaux acquis pour l'annee EN COURS, sur
    base des mois prestes durant l'annee PRECEDENTE (exercice de vacances).

    statut: 'employe' ou 'ouvrier' (meme regle des 2j/mois pour les deux,
            la distinction porte sur QUI paie le pecule, pas sur le nombre
            de jours -- confirme par 3 sources independantes).
    jours_semaine_ref: regime de travail actuel (pour proratiser un temps
            partiel), typiquement 5.
    mois_prestes_annee_precedente: nombre de mois COMPLETS prestes ou
            assimiles (maladie, maternite, chomage temporaire... certaines
            periodes sont assimilees, d'autres non -- non modelise ici,
            a completer si un cas concret se presente).
    jours_semaine_annee_precedente: regime de travail durant l'annee de
            reference (si different du regime actuel) -- pour un temps
            partiel qui devient temps plein, par exemple.

    Retourne le nombre de jours de conges en REGIME 5 JOURS (le regime le
    plus courant). Le calcul officiel se fait en base 6 jours puis se
    convertit, mais le resultat final en base 5 est directement le nombre
    de jours ouvrables de conge.
    """
    # Un statut etudiant n'ouvre JAMAIS de droit, meme avec des mois prestes
    if statut and statut.lower() in STATUTS_SANS_DROIT_CONGES:
        return 0.0

    if mois_prestes_annee_precedente <= 0:
        return 0.0  # AUCUN droit si pas de prestation l'annee precedente

    mois = min(12, mois_prestes_annee_precedente)  # jamais plus de 12 mois
    regime_ref = jours_semaine_annee_precedente or jours_semaine_ref

    # Base officielle: 2 jours/mois en regime 6 jours = 24j/an pour 12 mois
    jours_base_6j = mois * 2.0
    # Conversion vers le regime 5 jours (le plus courant)
    jours_base_5j = round(jours_base_6j * 5 / 6, 2)

    # Proratisation pour temps partiel (regime de reference != 5j standard)
    if regime_ref and regime_ref != 5:
        jours_base_5j = round(jours_base_5j * regime_ref / 5, 2)

    return jours_base_5j


def double_pecule_employe(salaire_mensuel_brut_actuel: float,
                           mois_prestes_annee_precedente: int) -> float:
    """Double pecule de vacances -- EMPLOYES UNIQUEMENT (les ouvriers sont
    payes par l'ONVA, pas par ce calcul). = 92% du salaire mensuel brut
    ACTUEL, proratise selon les mois prestes l'annee de reference (N-1).
    Si l'employe n'a pas preste toute l'annee N-1, le pecule est reduit
    proportionnellement (pas seulement les jours de conge, le pecule aussi).

    ATTENTION: la base de calcul est le salaire ACTUEL (au moment du
    paiement du pecule), PAS le salaire de l'annee de reference -- c'est
    une specificite du regime employe (different de l'ouvrier, ou tout se
    base sur la remuneration de N-1). Confirme par Securex.
    """
    if mois_prestes_annee_precedente <= 0:
        return 0.0
    mois = min(12, mois_prestes_annee_precedente)
    return round(salaire_mensuel_brut_actuel * 0.92 * mois / 12, 2)


def verifier_statut_ouvre_droit(type_contrat: str) -> tuple:
    """Retourne (ouvre_droit: bool, message: str) pour un type de contrat.
    A utiliser dans l'interface pour avertir l'utilisateur."""
    if type_contrat and type_contrat.upper() in TYPES_CONTRAT_SANS_DROIT_CONGES:
        return (False, "Contrat etudiant (STU): cotisation de solidarite "
                        "uniquement -- n'ouvre AUCUN droit aux conges payes "
                        "ni au pecule de vacances. Seuls les jours feries "
                        "legaux restent dus.")
    return (True, "")


def pecule_ouvrier_information(remuneration_brute_annuelle_reference: float) -> dict:
    """Le pecule OUVRIER n'est PAS paye par l'employeur -- il est calcule
    et verse par l'ONVA (ou une caisse de vacances sectorielle) sur base
    de la remuneration brute de l'annee de reference. Cette fonction ne
    sert qu'a des fins D'INFORMATION (afficher au client combien attendre,
    pas a generer un paiement sur la fiche de paie mensuelle).

    Base = remuneration brute annuelle (N-1) x 108% (coefficient ouvrier
    deja utilise ailleurs dans le moteur pour l'ONSS).
    """
    base = round(remuneration_brute_annuelle_reference * 1.08, 2)
    simple = round(base * 0.08, 2)
    double_brut = round(base * 0.0738, 2)
    retenue_onss_double = round(double_brut * 0.1307, 2)
    double_net = round(double_brut - retenue_onss_double, 2)
    return {
        'base_calcul': base,
        'simple_pecule': simple,
        'double_pecule_brut': double_brut,
        'retenue_onss_sur_double': retenue_onss_double,
        'double_pecule_net': double_net,
        'total_estime': round(simple + double_net, 2),
        'paye_par': 'ONVA ou caisse de vacances sectorielle (PAS l\'employeur)',
        'periode_paiement_usuelle': 'entre le 2 mai et le 30 juin',
    }



def calculer_mois_depuis_contrats(contrats: list, annee_reference: int) -> dict:
    """Calcule AUTOMATIQUEMENT les mois ouvrant droit a conges, a partir de
    la liste des contrats d'un travailleur, pour une annee de reference.

    contrats: liste de dicts avec au minimum 'type_contrat', 'date_debut',
              'date_fin' (peut etre None = contrat en cours), 'statut'.
    annee_reference: l'annee N-1 (l'exercice de vacances).

    Regles appliquees:
    - Seuls les contrats ACTIFS sont comptes (les archives sont des
      versions remplacees, les compter ferait double emploi).
    - Les contrats STU sont EXCLUS (cotisation de solidarite -> aucun droit).
    - Un mois est compte des qu'il y a au moins un jour preste dedans.
    - Les mois couverts par plusieurs contrats ne sont comptes QU'UNE FOIS.
    - Les contrats incoherents (date_fin < date_debut) sont ignores et
      signales, plutot que de produire un calcul silencieusement faux.

    Retourne un dict detaille pour que l'utilisateur voie le raisonnement.
    """
    from datetime import date as _dt

    mois_ouvrant = set()       # {(annee, mois)} -- set = pas de doublon
    mois_exclus_stu = set()
    contrats_ignores = []
    detail = []

    for c in contrats:
        statut_c = (c.get('statut') or '').lower()
        if statut_c != 'actif':
            continue  # on ignore les archives (versions remplacees)

        type_c = (c.get('type_contrat') or '').upper()
        debut = c.get('date_debut')
        fin = c.get('date_fin')

        if not debut:
            contrats_ignores.append({'id': c.get('id'), 'raison': 'pas de date de debut'})
            continue

        # Garde-fou: donnees incoherentes
        if fin and fin < debut:
            contrats_ignores.append({
                'id': c.get('id'),
                'raison': f'date_fin ({fin}) anterieure a date_debut ({debut})'
            })
            continue

        # Borner sur l'annee de reference
        debut_annee = _dt(annee_reference, 1, 1)
        fin_annee = _dt(annee_reference, 12, 31)
        d = max(debut, debut_annee)
        f = min(fin, fin_annee) if fin else fin_annee
        if d > f:
            continue  # contrat hors de l'annee de reference

        # Collecter les mois couverts
        mois_de_ce_contrat = set()
        annee_cur, mois_cur = d.year, d.month
        while (annee_cur, mois_cur) <= (f.year, f.month):
            mois_de_ce_contrat.add((annee_cur, mois_cur))
            mois_cur += 1
            if mois_cur > 12:
                mois_cur = 1
                annee_cur += 1

        if type_c in TYPES_CONTRAT_SANS_DROIT_CONGES:
            mois_exclus_stu |= mois_de_ce_contrat
            detail.append({'id': c.get('id'), 'type': type_c,
                            'mois': sorted(mois_de_ce_contrat),
                            'compte': False, 'raison': 'contrat etudiant'})
        else:
            mois_ouvrant |= mois_de_ce_contrat
            detail.append({'id': c.get('id'), 'type': type_c,
                            'mois': sorted(mois_de_ce_contrat),
                            'compte': True, 'raison': ''})

    # Un mois couvert a la fois par un STU et un contrat ordinaire compte
    # (le contrat ordinaire ouvre le droit pour ce mois-la)
    mois_exclus_purs = mois_exclus_stu - mois_ouvrant

    return {
        'mois_ouvrant_droit': min(12, len(mois_ouvrant)),
        'mois_detail': sorted(mois_ouvrant),
        'mois_exclus_stu': sorted(mois_exclus_purs),
        'nb_mois_exclus_stu': len(mois_exclus_purs),
        'contrats_ignores': contrats_ignores,
        'detail_par_contrat': detail,
    }
