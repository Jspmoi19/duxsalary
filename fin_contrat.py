# -*- coding: utf-8 -*-
"""
fin_contrat.py -- DuxSalary
FIN DE CONTRAT: preavis, indemnite de rupture, pecule de vacances de sortie.
Module pur (aucun acces a la base). Tous les parametres (tables de preavis, baremes
de precompte, taux) viennent de parametres_dates.py, dates et sources.

Regles (loi du 3 juillet 1978 relative aux contrats de travail, Justel):
- art. 37/1: le preavis prend cours le lundi qui suit la semaine de sa notification ;
- art. 37/2: delais de preavis (table selon la DATE DE DEBUT DU CONTRAT) ;
- art. 37/4: anciennete acquise au moment ou le preavis prend cours, service ininterrompu ;
- art. 39: indemnite = remuneration en cours + avantages acquis, pour la duree du
  preavis ou la partie restant a courir ; paye au mois: semaine = mois x 3 / 13 ;
  partie variable: moyenne des douze mois anterieurs ;
- art. 40: contrat a duree determinee -- rupture avant terme sans motif grave:
  remuneration restant a echoir, plafonnee au double du preavis d'un CDI ; pendant la
  premiere moitie du contrat (6 mois au plus), preavis de l'art. 37/2 ;
- art. 35: motif grave -- ni preavis ni indemnite (3 jours ouvrables + 3 jours ouvrables).
Hors perimetre (alerte): contrats debutes avant 2014, protections contre le licenciement,
imputation du reclassement professionnel, CCT n° 109.

Le DECOMPTE DE SORTIE remis au client ne contient aucune source: les sources restent
dans 'regles' et 'alertes' (usage interne), jamais dans 'lignes'.
"""
from datetime import date, timedelta
from calendar import monthrange

from parametres_dates import (get_preavis_params, get_preavis_plafond, PREAVIS_SEUIL_RECLASSEMENT_SEMAINES,
                              get_indemnites_dedit_params, get_pecule_sortie_params, get_cotisation_rupture_params)

MOTIFS = {
    'licenciement': "Licenciement par l'employeur",
    'demission': 'Démission du travailleur',
    'motif_grave': 'Rupture pour motif grave',
    'commun_accord': "Rupture d'un commun accord",
    'fin_cdd': 'Fin du contrat à durée déterminée à son terme',
}
# Avantages acquis en vertu du contrat, compris dans l'indemnite de rupture (art. 39: la
# loi ne les enumere pas). Liste validee par Leo le 02/10/2026 ; chacun est modifiable.
AVANTAGES = [
    ('prime_fin_annee', "Prime de fin d'année"),
    ('double_pecule', 'Double pécule de vacances'),
    ('cheques_repas', 'Chèques-repas – part employeur'),
    ('ecocheques', 'Écochèques'),
    ('assurance_groupe', 'Assurance-groupe – primes patronales'),
    ('assurance_hospitalisation', 'Assurance hospitalisation – primes patronales'),
    ('voiture_societe', 'Voiture de société – avantage de toute nature'),
]


def _r2(x):
    from decimal import Decimal, ROUND_HALF_UP
    return float(Decimal(str(x)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def _jj(d):
    return d.strftime('%d/%m/%Y') if d else ''


def _plus_mois(d, n):
    m = d.month - 1 + n
    a, m = d.year + m // 12, m % 12 + 1
    return date(a, m, min(d.day, monthrange(a, m)[1]))


def anciennete_mois(debut, a_la_date):
    """Mois complets d'anciennete entre le debut de l'occupation ininterrompue et une date."""
    if not debut or a_la_date < debut:
        return 0
    n = (a_la_date.year - debut.year) * 12 + a_la_date.month - debut.month
    return n - (1 if a_la_date.day < debut.day else 0)


# ─────────────────────────────────────────────────────────────────
# PREAVIS
# ─────────────────────────────────────────────────────────────────
def _palier(table, mois):
    return max((p for p in table if p[0] <= mois), key=lambda p: p[0])[1]


def semaines_preavis(auteur, mois_anciennete, date_debut_contrat):
    """Delai de preavis d'un CDI en semaines. auteur: 'employeur' (licenciement),
    'travailleur' (demission) ou 'contre_preavis'. La table depend de la date de debut
    d'execution du contrat. Retourne (semaines, version, plafonne)."""
    v = get_preavis_params(date_debut_contrat)
    mois = max(0, int(mois_anciennete))
    if auteur != 'employeur':
        return _palier(v[auteur], mois), v, False
    annees = mois // 12
    if annees < 5:
        semaines = _palier(v['employeur'], mois)
    elif annees <= 19:
        semaines = 18 + 3 * (annees - 5)
    elif annees == 20:
        semaines = 62
    else:
        semaines = 63 + (annees - 21)
    plafond = get_preavis_plafond(date_debut_contrat)
    if plafond and annees >= plafond['anciennete_annees']:
        return plafond['semaines'], v, True
    return semaines, v, False


def _paques(annee):
    a, b, c = annee % 19, annee // 100, annee % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mois, jour = (h + l - 7 * m + 114) // 31, (h + l - 7 * m + 114) % 31 + 1
    return date(annee, mois, jour)


def jours_feries(annee):
    p = _paques(annee)
    return {date(annee, 1, 1), p + timedelta(1), date(annee, 5, 1), p + timedelta(39), p + timedelta(50),
            date(annee, 7, 21), date(annee, 8, 15), date(annee, 11, 1), date(annee, 11, 11), date(annee, 12, 25)}


def ajouter_jours_ouvrables(d, n):
    """n jours ouvrables apres d: tous les jours sauf les dimanches et les jours feries
    (le samedi est un jour ouvrable)."""
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() != 6 and d not in jours_feries(d.year):
            n -= 1
    return d


def dates_preavis(date_notification, mode, semaines):
    """Prise d'effet de la notification, debut et fin du preavis.
    mode: 'recommande' (effet le 3e jour ouvrable suivant l'expedition, art. 37 § 1er),
    'huissier' ou 'remise' (effet le jour meme ; la remise d'un ecrit n'est valable que
    pour un conge donne par le travailleur). Le preavis prend cours le lundi suivant la
    semaine de la prise d'effet (art. 37/1)."""
    effet = ajouter_jours_ouvrables(date_notification, 3) if mode == 'recommande' else date_notification
    debut = effet + timedelta(days=7 - effet.weekday())
    return {'effet': effet, 'debut': debut, 'fin': debut + timedelta(weeks=semaines) - timedelta(days=1)}


# ─────────────────────────────────────────────────────────────────
# REMUNERATION DE REFERENCE
# ─────────────────────────────────────────────────────────────────
def remuneration_hebdomadaire(paye_au_mois, salaire_mensuel=0.0, salaire_horaire=0.0, heures_semaine=0.0,
                              horaire_variable=False, fiches=None, date_fin=None, date_entree=None):
    """Remuneration hebdomadaire en cours, hors avantages.
    - paye au mois: mensuel x 3 / 13 (art. 39 § 1er) ;
    - paye a l'heure, horaire fixe: heures par semaine du contrat x taux horaire ;
    - paye a l'heure, horaire variable: moyenne des douze derniers mois, ou depuis l'entree
      si c'est plus court, a partir des fiches enregistrees (brut hors primes / semaines).
    Retourne (montant, explication)."""
    if paye_au_mois:
        return _r2(salaire_mensuel * 3 / 13), f"{salaire_mensuel:.2f} € × 3 / 13"
    if not horaire_variable:
        return _r2(heures_semaine * salaire_horaire), f"{heures_semaine:g} h × {salaire_horaire:.4f} €"
    if not date_fin:
        raise ValueError("Horaire variable : la date de fin est requise pour calculer la moyenne.")
    debut = max(_plus_mois(date_fin, -12) + timedelta(days=1), date_entree or date.min)
    retenues = [f for f in fiches or [] if debut <= f['periode_debut'] <= date_fin]
    if not retenues:
        raise ValueError("Horaire variable : aucune fiche de paie sur les douze derniers mois, la moyenne ne peut pas "
                         "être calculée.")
    brut = sum(float(f.get('salaire_brut') or 0) - float(f.get('prime_brut') or 0) for f in retenues)
    semaines = ((date_fin - debut).days + 1) / 7
    return _r2(brut / semaines), (f"moyenne de {len(retenues)} fiche(s) du {_jj(debut)} au {_jj(date_fin)} : "
                                  f"{brut:.2f} € / {semaines:.2f} semaines")


def avantages_hebdomadaires(avantages_annuels):
    """avantages_annuels: {cle de AVANTAGES: montant annuel a charge de l'employeur}.
    Retourne ([(libelle, annuel, hebdomadaire)], total hebdomadaire) -- annuel / 52."""
    libelles = dict(AVANTAGES)
    lignes = [(libelles.get(k, k), _r2(v), _r2(float(v) / 52)) for k, v in (avantages_annuels or {}).items() if v]
    return lignes, _r2(sum(l[2] for l in lignes))


def avantages_proposes(paye_au_mois, salaire_mensuel, hebdo_base, cheque_part_patronale=0.0, jours_semaine=5,
                       ecocheques_annuels=0.0, a_prime_fin_annee=False):
    """Montants annuels PROPOSES (modifiables par Leo): prime de fin d'annee = un mois (ou
    52/12 semaines), double pecule de l'employe = 92 % d'un mois, cheques-repas = part
    patronale x jours prestes par an (jours par semaine x 47 semaines), ecocheques annuels.
    Assurances et voiture: 0, a saisir."""
    mensuel = salaire_mensuel if paye_au_mois else hebdo_base * 52 / 12
    return {
        'prime_fin_annee': _r2(mensuel) if a_prime_fin_annee else 0.0,
        'double_pecule': _r2(mensuel * 0.92) if paye_au_mois else 0.0,
        'cheques_repas': _r2(cheque_part_patronale * jours_semaine * 47),
        'ecocheques': _r2(ecocheques_annuels),
        'assurance_groupe': 0.0, 'assurance_hospitalisation': 0.0, 'voiture_societe': 0.0,
    }


# ─────────────────────────────────────────────────────────────────
# PRECOMPTE (annexe III 2026)
# ─────────────────────────────────────────────────────────────────
def precompte_indemnite_dedit(imposable, remuneration_reference_annuelle, reference_date, nb_enfants=0,
                              precompte_mensuel_nul=False):
    """Precompte de l'indemnite de rupture: taux unique lu sur la remuneration de reference
    annuelle (n° 58 et 62), exoneration pour enfants a charge (n° 60), dispense quand le
    douzieme de la remuneration de reference ne donne pas de precompte (n° 61).
    Retourne (precompte, taux, montant exonere)."""
    if imposable <= 0 or precompte_mensuel_nul:
        return 0.0, 0.0, 0.0
    p = get_indemnites_dedit_params(reference_date)
    taux = next(t for plafond, t in p['tranches'] if remuneration_reference_annuelle <= plafond)
    exonere = 0.0
    if nb_enfants:
        limite = p['limites_enfants'].get(min(int(nb_enfants), max(p['limites_enfants'])), 0)
        exonere = min(imposable, max(0.0, limite - remuneration_reference_annuelle))
    return _r2((imposable - exonere) * taux), taux, _r2(exonere)


# ─────────────────────────────────────────────────────────────────
# DECOMPTE DE SORTIE
# ─────────────────────────────────────────────────────────────────
def decompte_sortie(profil, motif, type_contrat, date_debut_contrat, date_fin_contrat_prevue, debut_anciennete,
                    date_notification, mode_notification='recommande', preavis_preste=True, date_fin_effective=None,
                    hebdo_base=0.0, explication_hebdo='', avantages_annuels=None, nb_enfants=0,
                    remuneration_annuelle_normale=None, precompte_mensuel_nul=None,
                    pecule=None, retenue_travailleur=0.0, situation_familiale=None, jours_suspension=0):
    """Calcule le decompte de sortie.
    profil: ProfilTravailleur (statut, taux ONSS). motif: cle de MOTIFS.
    preavis_preste: le preavis est preste jusqu'a son terme (aucune indemnite) ; sinon le
    contrat prend fin a date_fin_effective et la partie de preavis restant a courir est
    payee en indemnite.
    pecule (employes): {'brut_annee_en_cours', 'brut_annee_precedente', 'jours_vacances_pris',
    'double_deja_paye'} ou None.
    precompte_mensuel_nul: None = calcule (dispense du n° 61 de l'annexe III: aucun precompte
    quand le douzieme de la remuneration de reference n'en donne pas au bareme mensuel, selon
    situation_familiale = {'etat_civil', 'nb_enfants', 'partenaire_revenus_pro', 'charges'}).
    jours_suspension: jours calendrier de suspension du contrat pendant le preavis (maladie,
    vacances...) quand le conge est donne par l'employeur: la fin du preavis est reportee
    d'autant (art. 38 § 2).
    retenue_travailleur: montant que Leo decide de retenir sur le net quand l'indemnite est due
    PAR le travailleur (demission sans preavis preste). Rien n'est retenu d'office: voir plus bas.
    Retourne {'preavis', 'indemnite', 'pecule', 'lignes' (pour le document client, SANS
    source), 'totaux', 'regles' et 'alertes' (internes), 'dmfa'}."""
    if motif not in MOTIFS:
        raise ValueError(f"Motif de fin de contrat inconnu : {motif}")
    alertes, regles = [], []
    cdd = type_contrat == 'CDD'
    etudiant = profil.is_etudiant
    ref = date_fin_effective or date_notification
    lignes = []                      # document client: libelle, base, taux/nombre, montant -- jamais de source
    res = {'motif': motif, 'libelle_motif': MOTIFS[motif], 'preavis': None, 'indemnite': None, 'pecule': None}
    mentions = []                    # phrases imprimees sur le document client (sans source)
    lig_av, hebdo_av = avantages_hebdomadaires(avantages_annuels)
    hebdo = _r2(hebdo_base + hebdo_av)

    # ── Preavis ──
    semaines, version, plafonne, dates = 0, None, False, None
    semaines_indemnite = 0.0
    if motif == 'motif_grave':
        regles.append("Motif grave : ni préavis ni indemnité (loi du 03/07/1978, art. 35).")
        alertes.append(
            f"Motif grave : le congé doit être donné dans les 3 jours ouvrables de la connaissance du fait, et le motif "
            f"notifié dans les 3 jours ouvrables suivants (au plus tard le {_jj(ajouter_jours_ouvrables(date_notification, 3))} "
            f"pour un congé du {_jj(date_notification)}), par recommandé, exploit d'huissier ou remise d'un écrit.")
    elif motif in ('licenciement', 'demission'):
        auteur = 'employeur' if motif == 'licenciement' else 'travailleur'
        if mode_notification == 'remise' and auteur == 'employeur':
            alertes.append("Congé donné par l'employeur : la remise d'un écrit n'est pas valable, seuls le recommandé et "
                           "l'exploit d'huissier le sont (art. 37 § 1er).")
        effet = ajouter_jours_ouvrables(date_notification, 3) if mode_notification == 'recommande' else date_notification
        debut_preavis = effet + timedelta(days=7 - effet.weekday())
        mois = anciennete_mois(debut_anciennete, debut_preavis)
        semaines, version, plafonne = semaines_preavis(auteur, mois, date_debut_contrat)
        dates = dates_preavis(date_notification, mode_notification, semaines)
        report = int(jours_suspension or 0) if auteur == 'employeur' else 0
        if report > 0:
            dates = dict(dates, fin_sans_suspension=dates['fin'], fin=dates['fin'] + timedelta(days=report), jours_suspension=report)
            regles.append(f"Préavis suspendu pendant {report} jour(s) (maladie, vacances…) : sa fin est reportée du "
                          f"{_jj(dates['fin_sans_suspension'])} au {_jj(dates['fin'])} (art. 38 § 2 : en cas de congé donné par "
                          f"l'employeur, le délai de préavis ne court pas pendant la suspension).")
        elif int(jours_suspension or 0) > 0:
            regles.append("Congé donné par le travailleur : le préavis court pendant la suspension, sa fin n'est pas reportée "
                          "(art. 38 § 1er).")
        auteur_txt = "l'employeur" if auteur == 'employeur' else 'le travailleur'
        regles.append(f"Préavis de {semaines} semaine(s) : congé donné par {auteur_txt}, "
                      f"{mois} mois d'ancienneté au {_jj(debut_preavis)}, {version['libelle']} ({version['source']}).")
        if plafonne:
            regles.append("Préavis plafonné à 52 semaines (contrat débuté à partir du 01/06/2026, 17 ans d'ancienneté ou plus).")
        if cdd:
            # art. 40 § 2: preavis possible pendant la premiere moitie du contrat, 6 mois au plus
            duree = (date_fin_contrat_prevue - date_debut_contrat).days + 1 if date_fin_contrat_prevue else None
            limite = None
            if duree:
                limite = min(date_debut_contrat + timedelta(days=duree // 2 - 1), _plus_mois(date_debut_contrat, 6) - timedelta(days=1))
            if not duree:
                alertes.append("CDD sans date de fin enregistrée : la règle de l'art. 40 ne peut pas être appliquée.")
            elif effet <= limite:
                regles.append(f"CDD rompu pendant la première moitié du contrat (jusqu'au {_jj(limite)}) : préavis de "
                              f"l'art. 37/2 possible (art. 40 § 2). Pour des CDD successifs, seulement pour le premier.")
            else:
                # art. 40 § 1er: remuneration restant a echoir, plafonnee au double du preavis d'un CDI
                fin_eff = date_fin_effective or effet
                restant = max(0, (date_fin_contrat_prevue - fin_eff).days) / 7
                semaines_indemnite = round(min(restant, 2 * semaines), 2)
                regles.append(f"CDD rompu après la première moitié du contrat ({_jj(limite)}) : pas de préavis possible. "
                              f"Indemnité = rémunération restant à échoir jusqu'au {_jj(date_fin_contrat_prevue)} "
                              f"({restant:.2f} semaines), plafonnée au double du préavis d'un CDI (2 × {semaines} = "
                              f"{2 * semaines} semaines) : {semaines_indemnite:g} semaines (art. 40 § 1er).")
                dates, preavis_preste = None, False
                semaines = 0
        if dates and not preavis_preste:
            fin_eff = date_fin_effective or dates['effet']
            if fin_eff >= dates['fin']:
                semaines_indemnite = 0.0
            elif fin_eff < dates['debut']:
                semaines_indemnite = float(semaines)
            else:
                semaines_indemnite = round(((dates['fin'] - fin_eff).days) / 7, 2)
            regles.append(f"Préavis non presté (ou partiellement) : fin du contrat le {_jj(fin_eff)}, indemnité pour "
                          f"{semaines_indemnite:g} semaine(s) restant à courir (art. 39 § 1er).")
        if dates and auteur == 'employeur' and not dates.get('jours_suspension'):
            alertes.append("Congé donné par l'employeur : le préavis ne court pas pendant une suspension du contrat "
                           "(vacances, maladie…). Indiquez les jours de suspension pour reporter la date de fin (art. 38 § 2).")
        if semaines >= PREAVIS_SEUIL_RECLASSEMENT_SEMAINES and auteur == 'employeur':
            alertes.append(f"Préavis de {semaines} semaines (30 ou plus) : reclassement professionnel obligatoire. Son "
                           f"imputation (4 semaines) sur l'indemnité de rupture n'est pas calculée par l'outil.")
        res['preavis'] = {'semaines': semaines, 'auteur': auteur, 'anciennete_mois': mois, 'dates': dates,
                          'preste': preavis_preste, 'plafonne': plafonne, 'version': version['libelle']}
    elif motif == 'fin_cdd':
        regles.append("Fin d'un CDD à son terme : ni préavis ni indemnité.")
    else:
        regles.append("Rupture d'un commun accord : ni préavis ni indemnité légale (les parties conviennent des modalités).")
    if motif in ('licenciement',):
        alertes.append("Non contrôlé par l'outil : protections contre le licenciement (maternité, crédit-temps, délégué, "
                       "CCT n° 109 sur la motivation du licenciement…).")

    # ── Indemnite de rupture ──
    tot = {'brut': 0.0, 'onss': 0.0, 'precompte': 0.0, 'net': 0.0, 'onss_patronal': 0.0, 'cotisation_812': 0.0}
    dmfa = []
    if semaines_indemnite > 0 and not etudiant:
        brut = _r2(hebdo * semaines_indemnite)
        doit_payer = 'employeur' if motif == 'licenciement' else 'travailleur'
        if doit_payer == 'travailleur':
            # Indemnite due PAR le travailleur: JAMAIS deduite d'office du net (corrige le 02/10/2026).
            # Loi du 12/04/1965 concernant la protection de la remuneration, art. 23 (Justel,
            # consolidee au 14/04/2026): « Peuvent seuls être imputés sur la rémunération du
            # travailleur » six retenues enumerees (fiscales et sociales, amendes, indemnites de
            # l'art. 18 de la loi du 03/07/1978, avances, cautionnement, horaire flottant) ; leur
            # total « ne peut dépasser le cinquième de la rémunération en espèces due à chaque
            # paie ». L'indemnite de rupture due par le travailleur (art. 39) n'est pas dans cette
            # liste: l'outil affiche le montant du, et ne retient que ce que Leo saisit.
            regles.append("Démission sans préavis presté : l'indemnité est due PAR le travailleur à l'employeur (art. 39) ; "
                          "elle n'est pas une rémunération et n'est pas retenue d'office sur ce décompte.")
            res['indemnite'] = {'due_par': 'travailleur', 'semaines': semaines_indemnite, 'hebdo': hebdo, 'brut': brut,
                                'retenue': 0.0, 'cinquieme_net': 0.0}
            eur = lambda x: f"{x:.2f}".replace('.', ',')
            mentions.append(f"Indemnité de rupture due par le travailleur à l'employeur : {eur(brut)} EUR "
                            + f"({semaines_indemnite:g} semaines)".replace('.', ',') + ", à régler séparément.")
        else:
            onss = profil.onss_personnel(brut)
            base_pat = profil.base_onss_patronale(brut)
            onss_pat = _r2(base_pat * profil.onss_patronal_taux_base)
            annuel_ref = _r2(hebdo * 52)
            # Dispense du n° 61: le douzieme de la remuneration de reference donne-t-il du precompte au bareme mensuel ?
            dispense = precompte_mensuel_nul
            if dispense is None:
                sf = situation_familiale or {}
                mensuel_ref = _r2(annuel_ref / 12)
                imposable_ref = _r2(mensuel_ref - profil.onss_personnel(mensuel_ref))
                dispense = profil.precompte_brut(imposable_ref, sf.get('etat_civil') or 'celibataire', int(sf.get('nb_enfants') or 0),
                                                 sf.get('partenaire_revenus_pro') or 'non', reference_date=ref,
                                                 charges=sf.get('charges')) <= 0
            pp, taux_pp, exonere = precompte_indemnite_dedit(_r2(brut - onss), annuel_ref, ref, nb_enfants, dispense)
            if dispense:
                regles.append(f"Dispense de précompte sur l'indemnité : le douzième de la rémunération de référence "
                              f"({annuel_ref / 12:.2f} € par mois) ne donne pas de précompte au barème mensuel (annexe III 2026, n° 61).")
            c812 = 0.0
            p812 = get_cotisation_rupture_params(ref)
            taux_812 = next((t for seuil, t in (p812 or {}).get('paliers', []) if annuel_ref >= seuil), 0.0)
            if taux_812:
                c812 = _r2(brut * taux_812)
                alertes.append(f"Cotisation spéciale sur l'indemnité de rupture (code 812) à charge de l'employeur : "
                               f"{taux_812 * 100:.0f} % (salaire annuel de référence {annuel_ref:.2f} €) = {c812:.2f} €.")
            res['indemnite'] = {'due_par': 'employeur', 'semaines': semaines_indemnite, 'hebdo_base': hebdo_base,
                                'hebdo_avantages': hebdo_av, 'hebdo': hebdo, 'avantages': lig_av, 'brut': brut, 'onss': onss,
                                'imposable': _r2(brut - onss), 'precompte': pp, 'taux_precompte': taux_pp,
                                'exonere_enfants': exonere, 'reference_annuelle': annuel_ref, 'net': _r2(brut - onss - pp),
                                'onss_patronal': onss_pat, 'cotisation_812': c812}
            lignes += [
                {'libelle': 'Indemnité de rupture', 'base': hebdo, 'nombre': f"{semaines_indemnite:g} semaines".replace('.', ','), 'montant': brut},
                {'libelle': 'ONSS travailleur sur l\'indemnité de rupture', 'base': profil.base_onss_patronale(brut),
                 'nombre': f"{profil.onss_personnel_taux * 100:.2f} %".replace('.', ','), 'montant': -onss},
                {'libelle': 'Précompte professionnel sur l\'indemnité de rupture', 'base': _r2(brut - onss - exonere),
                 'nombre': f"{taux_pp * 100:.2f} %".replace('.', ','), 'montant': -pp},
            ]
            regles += [
                f"Indemnité de rupture : rémunération hebdomadaire {hebdo_base:.2f} € ({explication_hebdo}) + avantages "
                f"{hebdo_av:.2f} € = {hebdo:.2f} € × {semaines_indemnite:g} semaines (art. 39).",
                "ONSS : cotisations ordinaires, code rémunération 3, période couverte à partir du lendemain de la fin du "
                "contrat ; ni réduction structurelle ni bonus à l'emploi (Instructions ONSS 2026/3).",
            ]
            if not dispense:
                regles.append(
                    f"Précompte : {taux_pp * 100:.2f} % sur l'imposable, rémunération de référence annuelle {annuel_ref:.2f} € "
                    f"(annexe III 2026, n° 58 à 62)" + (f", {exonere:.2f} € exonérés pour enfants à charge (n° 60)" if exonere else '') + ".")
            if lig_av:
                regles.append("Rappel : l'indemnité de rupture est soumise en entier aux cotisations ordinaires, avantages "
                              "compris (même ceux qui étaient exonérés pendant le contrat) ; les montants des avantages "
                              "sont ceux proposés ou saisis.")
            for k, v in (('brut', brut), ('onss', onss), ('precompte', pp), ('net', brut - onss - pp),
                         ('onss_patronal', onss_pat), ('cotisation_812', c812)):
                tot[k] += v
            debut_cv = (date_fin_effective or ref) + timedelta(days=1)
            dmfa.append({'code_remuneration': 3, 'libelle': 'Indemnité de rupture', 'montant': brut,
                         'du': debut_cv, 'au': debut_cv + timedelta(days=round(semaines_indemnite * 7) - 1)})
    elif semaines_indemnite > 0 and etudiant:
        alertes.append("Contrat d'étudiant : indemnité de rupture non calculée par l'outil.")

    # ── Pecule de vacances de sortie (employes) ──
    if profil.is_employe and pecule:
        pv = get_pecule_sortie_params(ref)
        blocs = []
        for libelle_exercice, base, fraction in (
                (f"prestations {ref.year}", float(pecule.get('brut_annee_en_cours') or 0), 1.0),
                (f"prestations {ref.year - 1} (vacances non prises)", float(pecule.get('brut_annee_precedente') or 0),
                 max(0.0, 1 - float(pecule.get('jours_vacances_pris') or 0) / float(pecule.get('jours_vacances_droit')
                                                                                  or pv['jours_vacances_temps_plein'])))):
            if base <= 0 or fraction <= 0:
                continue
            simple = _r2(base * pv['taux_simple'] * fraction)
            double_du = not (pecule.get('double_deja_paye') and 'non prises' in libelle_exercice)
            double = _r2(base * pv['taux_double'] * (fraction if 'non prises' in libelle_exercice else 1.0)) if double_du else 0.0
            if 'non prises' in libelle_exercice and not double_du:
                regles.append(f"Double pécule {ref.year} déjà payé : seul le pécule simple des jours de vacances non pris est dû.")
            blocs.append((libelle_exercice, base, fraction, simple, double))
        simple_t = _r2(sum(b[3] for b in blocs)); double_t = _r2(sum(b[4] for b in blocs))
        if simple_t or double_t:
            onss_simple = profil.onss_personnel(simple_t)
            base_retenue = _r2(sum(b[1] * pv['taux_base_retenue_double'] * (b[2] if 'non prises' in b[0] else 1.0)
                                   for b in blocs if b[4]))
            retenue_double = _r2(base_retenue * pv['retenue_double'])
            onss_pat_simple = _r2(simple_t * profil.onss_patronal_taux_base)
            annuel = float(remuneration_annuelle_normale or hebdo_base * 52)
            pp_pec, taux_pec = profil.precompte_exceptionnel(_r2(simple_t + double_t - onss_simple - retenue_double), annuel,
                                                             'double_pecule', reference_date=ref)
            res['pecule'] = {'blocs': blocs, 'simple': simple_t, 'double': double_t, 'onss_simple': onss_simple,
                             'base_retenue_double': base_retenue, 'retenue_double': retenue_double, 'precompte': pp_pec,
                             'taux_precompte': taux_pec, 'onss_patronal': onss_pat_simple,
                             'net': _r2(simple_t + double_t - onss_simple - retenue_double - pp_pec)}
            pc = lambda x: f"{x * 100:.2f} %".replace('.', ',')
            for lib, base, fraction, simple, double in blocs:
                frac = '' if fraction == 1.0 else f" × {fraction:.2f}".replace('.', ',')
                lignes.append({'libelle': f"Pécule simple de sortie – {lib}", 'base': _r2(base),
                               'nombre': pc(pv['taux_simple']) + frac, 'montant': simple})
                if double:
                    lignes.append({'libelle': f"Double pécule de sortie – {lib}", 'base': _r2(base),
                                   'nombre': pc(pv['taux_double']) + frac, 'montant': double})
            lignes += [
                {'libelle': 'ONSS travailleur sur le pécule simple de sortie', 'base': simple_t,
                 'nombre': pc(profil.onss_personnel_taux), 'montant': -onss_simple},
                {'libelle': 'Retenue sur le double pécule de sortie', 'base': base_retenue,
                 'nombre': pc(pv['retenue_double']), 'montant': -retenue_double},
                {'libelle': 'Précompte professionnel sur le pécule de sortie',
                 'base': _r2(simple_t + double_t - onss_simple - retenue_double), 'nombre': pc(taux_pec), 'montant': -pp_pec},
            ]
            regles += [
                f"Pécule de sortie de l'employé : {pc(pv['taux_simple'])} (simple) + {pc(pv['taux_double'])} (double) de la "
                f"rémunération brute ({pv['source']}).",
                "ONSS : pécule simple sous le code rémunération 7 (cotisations ordinaires) ; double pécule sous le code "
                "870, retenue de 13,07 % calculée sur 6,80 % de la rémunération, sans cotisation patronale.",
                f"Précompte du pécule : {pc(taux_pec)}, barème des allocations exceptionnelles, colonne des pécules de "
                f"vacances (annexe III 2026, n° 53), rémunération annuelle normale {annuel:.2f} €.",
            ]
            alertes.append("Pécule de sortie : la base (rémunération brute de l'exercice) est proposée à partir des fiches "
                           "enregistrées, à valider ; remettre l'attestation de vacances au travailleur.")
            for k, v in (('brut', simple_t + double_t), ('onss', onss_simple + retenue_double), ('precompte', pp_pec),
                         ('net', simple_t + double_t - onss_simple - retenue_double - pp_pec), ('onss_patronal', onss_pat_simple)):
                tot[k] += v
            dmfa += [{'code_remuneration': 7, 'libelle': 'Pécule simple de sortie', 'montant': simple_t},
                     {'code_remuneration': 870, 'libelle': 'Double pécule de sortie – base de la retenue de 13,07 %',
                      'montant': base_retenue}]
    elif profil.is_ouvrier:
        regles.append("Ouvrier : pas de pécule de sortie à charge de l'employeur (la caisse de vacances paie le pécule).")

    # ── Indemnite due par le travailleur: retenue facultative, decidee par Leo ──
    ind = res.get('indemnite')
    if ind and ind.get('due_par') == 'travailleur':
        net_avant = max(0.0, tot['net'])
        ind['cinquieme_net'] = _r2(net_avant / 5)
        retenue = _r2(min(max(0.0, float(retenue_travailleur or 0)), ind['brut'], net_avant))
        ind['retenue'], ind['solde_du'] = retenue, _r2(ind['brut'] - retenue)
        alertes.append(
            f"Indemnité de rupture due par le travailleur : {ind['brut']:.2f} €. Elle n'est PAS retenue d'office sur le net : la "
            f"loi du 12/04/1965 (art. 23) énumère les seules retenues permises sur la rémunération et les limite à un "
            f"cinquième du net de chaque paie ({ind['cinquieme_net']:.2f} € ici) ; l'indemnité de rupture due par le travailleur "
            f"ne figure pas dans cette liste. Une retenue suppose l'accord du travailleur, donné après la rupture ; à défaut, "
            f"le montant se réclame séparément.")
        if retenue > 0:
            lignes.append({'libelle': "Retenue convenue sur l'indemnité de rupture due par le travailleur", 'base': ind['brut'],
                           'nombre': '', 'montant': -retenue})
            tot['net'] -= retenue
            eur = lambda x: f"{x:.2f}".replace('.', ',')
            mentions[-1:] = [f"Indemnité de rupture due par le travailleur à l'employeur : {eur(ind['brut'])} EUR, dont "
                             f"{eur(retenue)} EUR retenus sur ce décompte ; solde : {eur(ind['solde_du'])} EUR."]
            if retenue > ind['cinquieme_net'] + 0.005:
                alertes.append(f"Retenue saisie ({retenue:.2f} €) supérieure au cinquième du net ({ind['cinquieme_net']:.2f} €) : "
                               f"à ne faire qu'avec l'accord écrit du travailleur.")
    res['mentions'] = mentions

    res.update(lignes=lignes, totaux={k: _r2(v) for k, v in tot.items()}, regles=regles, alertes=alertes, dmfa=dmfa,
               cout_employeur=_r2(tot['brut'] + tot['onss_patronal'] + tot['cotisation_812']))
    return res


# ─────────────────────────────────────────────────────────────────
# PAGE « FIN DE CONTRAT »: propositions et lecture du formulaire
# ─────────────────────────────────────────────────────────────────
def propositions(contrat, fiches, statut, date_fin, cheque_part_patronale=0.0, a_prime_fin_annee=False):
    """Valeurs PROPOSEES dans le formulaire du decompte (toutes modifiables par Leo): avantages
    annuels, bases du pecule de sortie lues dans les fiches enregistrees, jours de vacances
    deja pris, double pecule deja paye cette annee."""
    paye_au_mois = statut == 'employe'
    heures_contrat = float(contrat.get('heures_jour') or 7.6) * int(contrat.get('jours_semaine') or 5)
    horaire = float(contrat.get('salaire_horaire') or 0)
    mensuel = float(contrat.get('salaire_mensuel') or 0) or _r2(horaire * float(contrat.get('heures_semaine') or 38) * 52 / 12)
    hebdo, _ = remuneration_hebdomadaire(paye_au_mois, salaire_mensuel=mensuel, salaire_horaire=horaire, heures_semaine=heures_contrat)
    annee = date_fin.year
    de_l_annee = lambda a: [f for f in fiches or [] if f['periode_debut'].year == a and not f.get('is_etudiant')]
    brut = lambda fs: _r2(sum(float(f.get('salaire_brut') or 0) for f in fs))
    return {
        'paye_au_mois': paye_au_mois, 'salaire_mensuel': mensuel, 'salaire_horaire': horaire, 'heures_semaine': heures_contrat,
        'hebdo': hebdo,
        'avantages': avantages_proposes(paye_au_mois, mensuel, hebdo, cheque_part_patronale, int(contrat.get('jours_semaine') or 5),
                                        0.0, a_prime_fin_annee),
        'brut_annee_en_cours': brut(de_l_annee(annee)), 'brut_annee_precedente': brut(de_l_annee(annee - 1)),
        'jours_vacances_pris': sum(int(f.get('jours_conge') or 0) for f in de_l_annee(annee)),
        'double_deja_paye': any(float(f.get('pecule_brut') or 0) > 0 for f in de_l_annee(annee)),
    }


def decompte_depuis_formulaire(form, profil, contrat, contrats, fiches, nb_enfants=0, situation_familiale=None):
    """Lit le formulaire de la page « Fin de contrat » et calcule le decompte.
    form: dict (ou request.form). Retourne (decompte, saisie relue)."""
    from salaire_garanti import debut_occupation_ininterrompue

    def jour(nom):
        try:
            return date.fromisoformat((form.get(nom) or '').strip())
        except ValueError:
            return None

    def nombre(nom):
        try:
            return float((form.get(nom) or '0').replace(',', '.') or 0)
        except ValueError:
            return 0.0

    motif = form.get('motif') or 'licenciement'
    notification = jour('date_notification')
    if not notification:
        raise ValueError("La date de notification (ou de fin du contrat) est obligatoire.")
    fin_effective = jour('date_fin_effective')
    preste = form.get('preavis_preste') == 'on'
    if not preste and not fin_effective and motif in ('licenciement', 'demission'):
        raise ValueError("Préavis non presté jusqu'à son terme : indiquez le dernier jour du contrat.")
    statut = 'etudiant' if profil.is_etudiant else ('ouvrier' if profil.is_ouvrier else 'employe')
    paye_au_mois = statut == 'employe'
    horaire = float(contrat.get('salaire_horaire') or 0)
    mensuel = float(contrat.get('salaire_mensuel') or 0) or _r2(horaire * float(contrat.get('heures_semaine') or 38) * 52 / 12)
    heures_contrat = float(contrat.get('heures_jour') or 7.6) * int(contrat.get('jours_semaine') or 5)
    debut_anc = debut_occupation_ininterrompue(contrats, contrat['date_debut']) or contrat['date_debut']
    hebdo, explication = remuneration_hebdomadaire(
        paye_au_mois, salaire_mensuel=mensuel, salaire_horaire=horaire, heures_semaine=heures_contrat,
        horaire_variable=form.get('horaire_variable') == 'on' and not paye_au_mois, fiches=fiches,
        date_fin=fin_effective or notification, date_entree=debut_anc)
    avantages = {cle: nombre('av_' + cle) for cle, _ in AVANTAGES}
    pecule = None
    if form.get('inclure_pecule') == 'on' and statut == 'employe':
        pecule = {'brut_annee_en_cours': nombre('brut_annee_en_cours'), 'brut_annee_precedente': nombre('brut_annee_precedente'),
                  'jours_vacances_pris': nombre('jours_vacances_pris'), 'double_deja_paye': form.get('double_deja_paye') == 'on'}
    decompte = decompte_sortie(
        profil, motif, contrat.get('type_contrat'), contrat['date_debut'], contrat.get('date_fin'), debut_anc, notification,
        form.get('mode_notification') or 'recommande', preavis_preste=preste, date_fin_effective=fin_effective,
        hebdo_base=hebdo, explication_hebdo=explication, avantages_annuels=avantages, nb_enfants=nb_enfants,
        remuneration_annuelle_normale=mensuel * 12 if paye_au_mois else hebdo * 52, pecule=pecule,
        retenue_travailleur=nombre('retenue_travailleur'), situation_familiale=situation_familiale,
        jours_suspension=int(nombre('jours_suspension')))
    decompte['date_fin'] = fin_effective or ((decompte['preavis'] or {}).get('dates') or {}).get('fin') or notification
    return decompte, {'hebdo': hebdo, 'explication_hebdo': explication, 'avantages': avantages, 'debut_anciennete': debut_anc}
