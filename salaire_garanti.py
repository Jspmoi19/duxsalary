# -*- coding: utf-8 -*-
"""
salaire_garanti.py -- DuxSalary
Maladie et accident DE DROIT COMMUN: ventilation de chaque jour calendrier d'une
incapacite dans sa tranche de salaire garanti, et calcul des montants.
Module pur (aucun acces a la base). Tous les parametres (durees, pourcentages,
delai de rechute, plafond AMI) viennent de parametres_dates.py, dates et sources.

Hors perimetre (non gere, signale): accident du travail, maladie
professionnelle, maternite, etudiants, exclusions de l'art. 52 § 3 / 73 § 2
(accident sportif remunere, faute grave).

Tranches (codes du calendrier des prestations):
  MG  salaire garanti a 100 % -- remuneration ordinaire, soumise a l'ONSS
      (code prestation 1 ; compte dans le bonus a l'emploi et les reductions)
  M2  indemnite de la 2e semaine (jours 8 a 14) -- hors ONSS, imposable
      (code prestation 10)
  MC  complement des jours 15 a 30 (CCT 12bis / 13bis) -- hors ONSS, imposable
      (code prestation 11)
  MM  a charge de la mutuelle -- rien n'est du par l'employeur
"""
from datetime import date, timedelta
from calendar import monthrange
from parametres_dates import get_salaire_garanti_params, get_delai_rechute, get_plafond_ami

CODES_INCAPACITE = ('MG', 'M2', 'MC', 'MM')
LIBELLES_TRANCHES = {
    'MG': 'Salaire garanti à 100 % (soumis ONSS)',
    'M2': 'Indemnité 2e semaine (hors ONSS, imposable)',
    'MC': 'Complément jours 15 à 30 (hors ONSS, imposable)',
    'MM': 'Mutuelle (rien à charge de l\'employeur)',
}
TYPES_INCAPACITE = {'maladie': 'Maladie', 'accident': 'Accident de droit commun'}


def _jj(d):
    return d.strftime('%d/%m/%Y') if d else ''


def _plus_mois(d, n):
    """Meme quantieme n mois plus tard (dernier jour du mois si le quantieme n'existe pas)."""
    m = d.month - 1 + n
    a, m = d.year + m // 12, m % 12 + 1
    return date(a, m, min(d.day, monthrange(a, m)[1]))


# ─────────────────────────────────────────────────────────────────
# REGIME APPLICABLE ET ANCIENNETE
# ─────────────────────────────────────────────────────────────────
def regime_salaire_garanti(is_ouvrier, type_contrat, date_debut_contrat=None, date_fin_contrat=None):
    """'ouvrier' (art. 52), 'employe' (art. 70: CDI, ou CDD d'au moins trois mois),
    'employe_court' (art. 71: engage pour moins de trois mois), None = non gere (etudiant)."""
    if type_contrat == 'STU':
        return None
    if is_ouvrier:
        return 'ouvrier'
    if type_contrat == 'CDD' and date_debut_contrat and date_fin_contrat and \
            date_fin_contrat + timedelta(days=1) < _plus_mois(date_debut_contrat, 3):
        return 'employe_court'
    return 'employe'


def debut_occupation_ininterrompue(contrats, jour):
    """Debut de l'occupation ININTERROMPUE a la date `jour`: on remonte les contrats
    qui se suivent sans un seul jour d'ecart (art. 52 § 1er: « demeure sans
    interruption au service de la meme entreprise »). None si aucun contrat ne
    couvre le jour."""
    cs = sorted((c for c in contrats or [] if c.get('date_debut')), key=lambda c: c['date_debut'])
    courant = None
    for c in cs:
        if c['date_debut'] <= jour and (not c.get('date_fin') or c['date_fin'] >= jour):
            courant = c
    if not courant:
        return None
    debut = courant['date_debut']
    for c in reversed(cs):
        if c['date_debut'] < debut and c.get('date_fin') and c['date_fin'] + timedelta(days=1) >= debut:
            debut = c['date_debut']
    return debut


# ─────────────────────────────────────────────────────────────────
# VENTILATION DES JOURS PAR TRANCHE
# ─────────────────────────────────────────────────────────────────
def _tranche(rang, p):
    if rang <= p['fin_100']:
        return 'MG'
    if rang <= p['fin_2e_semaine']:
        return 'M2'
    if rang <= p['fin_periode']:
        return 'MC'
    return 'MM'


def ventiler_episodes(episodes, regime, debut_anciennete, jusqu_au):
    """episodes: [{'id', 'date_debut', 'date_fin' (None = en cours), 'type',
    'autre_cause' (True = autre maladie/accident prouve par certificat)}].
    regime: voir regime_salaire_garanti. debut_anciennete: debut de l'occupation
    ininterrompue. jusqu_au: horizon de calcul des episodes sans date de fin.
    Retourne un dict par episode: jours [{'date','rang','tranche','motif'}],
    'rechute_de', 'rang_depart', 'alertes', 'infos', 'compte'."""
    if regime is None:
        raise ValueError("Salaire garanti non géré pour ce contrat (étudiant) : ne pas deviner.")
    resultat, precedent = [], None
    for e in sorted(episodes or [], key=lambda x: x['date_debut']):
        debut = e['date_debut']
        fin = e.get('date_fin') or max(jusqu_au, debut)
        version = get_salaire_garanti_params(debut)
        p = version['regimes'][regime]
        delai = get_delai_rechute(debut)
        alertes, infos = [], []
        rang_depart, rechute_de = 0, None
        if precedent:
            ecart = (debut - precedent['fin']).days
            if ecart <= 0:
                alertes.append(f"Cette incapacité chevauche la précédente (du {_jj(precedent['debut'])} au "
                               f"{_jj(precedent['fin'])}) : corrigez les dates.")
            if ecart <= delai['jours']:
                if e.get('autre_cause'):
                    infos.append(f"Nouvelle incapacité dans les {delai['libelle']} suivant la fin de la précédente "
                                 f"({_jj(precedent['fin'])}), déclarée due à une autre maladie ou un autre accident : "
                                 f"nouvelle période de salaire garanti. Le certificat médical qui l'atteste doit être au dossier.")
                else:
                    rang_depart, rechute_de = precedent['dernier_rang'], precedent['id']
                    solde = max(0, p['fin_periode'] - rang_depart)
                    alertes.append(
                        f"Rechute : incapacité débutant {ecart} jour(s) après la fin de la précédente ({_jj(precedent['fin'])}), "
                        f"soit dans les {delai['libelle']} — pas de nouveau salaire garanti, le décompte reprend au jour "
                        f"{rang_depart + 1} (solde : {solde} jour(s) sur {p['fin_periode']}). "
                        f"Si un certificat médical atteste une autre maladie ou un autre accident, cochez « autre cause ». "
                        f"Source : {delai['source']}.")
        jours, sans_anciennete = [], 0
        seuil_anciennete = _plus_mois(debut_anciennete, p['anciennete_mois']) if debut_anciennete else None
        for i in range((fin - debut).days + 1):
            d = debut + timedelta(days=i)
            rang = rang_depart + i + 1
            tranche, motif = _tranche(rang, p), None
            if tranche == 'MM':
                motif = f"au-delà du {p['fin_periode']}e jour"
            if p['anciennete_mois'] and tranche != 'MM' and (seuil_anciennete is None or d < seuil_anciennete):
                tranche, motif = 'MM', "moins d'un mois d'ancienneté"
                sans_anciennete += 1
            jours.append({'date': d, 'rang': rang, 'tranche': tranche, 'motif': motif})
        if sans_anciennete:
            alertes.append(
                f"Moins d'un mois d'ancienneté ininterrompue"
                + (f" avant le {_jj(seuil_anciennete)}" if seuil_anciennete else " (aucun contrat ne couvre ces jours)")
                + f" : pas de salaire garanti pour {sans_anciennete} jour(s), à charge de la mutuelle. "
                  f"Le droit s'ouvre pour les jours restants dès que le mois est atteint (loi du 03/07/1978, art. 52 § 1er).")
        premier_mm = next((j for j in jours if j['tranche'] == 'MM' and j['motif'] != "moins d'un mois d'ancienneté"), None)
        if premier_mm:
            alertes.append(f"Fin du salaire garanti : à partir du {_jj(premier_mm['date'])} (jour {premier_mm['rang']}), "
                           f"l'incapacité est à charge de la mutuelle. Vérifiez que la mutuelle est informée "
                           f"(feuille de renseignements).")
        if not e.get('date_fin'):
            alertes.append(f"Incapacité sans date de fin : calculée jusqu'au {_jj(fin)}. "
                           f"Encodez la date de reprise dès qu'elle est connue.")
        if version.get('a_confirmer_avant') and debut < version['a_confirmer_avant']:
            alertes.append(f"Incapacité antérieure au {_jj(version['a_confirmer_avant'])} : pourcentages du salaire garanti "
                           f"non vérifiés sur une source de l'époque, à contrôler.")
        compte = {t: sum(1 for j in jours if j['tranche'] == t) for t in CODES_INCAPACITE}
        resultat.append({'episode': e, 'id': e.get('id'), 'debut': debut, 'fin': fin, 'en_cours': not e.get('date_fin'),
                         'regime': regime, 'libelle_regime': p['libelle'], 'rang_depart': rang_depart,
                         'rechute_de': rechute_de, 'jours': jours, 'compte': compte,
                         'alertes': alertes, 'infos': infos, 'source': version['source']})
        precedent = {'id': e.get('id'), 'debut': debut, 'fin': fin, 'dernier_rang': rang_depart + len(jours)}
    return resultat


def tranches_par_date(ventilation):
    """{date: jour} sur tous les episodes (le dernier episode l'emporte en cas de chevauchement)."""
    return {j['date']: dict(j, episode_id=v['id']) for v in ventilation for j in v['jours']}


def resume_periodes(v):
    """Periodes continues d'un episode par tranche: [(tranche, du, au, nb jours, motif)] -- pour l'affichage."""
    periodes = []
    for j in v['jours']:
        if periodes and periodes[-1][0] == j['tranche'] and periodes[-1][4] == j['motif']:
            periodes[-1] = (j['tranche'], periodes[-1][1], j['date'], periodes[-1][3] + 1, j['motif'])
        else:
            periodes.append((j['tranche'], j['date'], j['date'], 1, j['motif']))
    return periodes


def regles_affichees(regime, reference_date):
    """Regles appliquees, en clair et avec leur source (affichees dans l'outil)."""
    if regime is None:
        return ["Étudiant : salaire garanti non géré par l'outil. Les jours de maladie ne sont pas payés automatiquement."]
    v = get_salaire_garanti_params(reference_date)
    p = v['regimes'][regime]
    delai = get_delai_rechute(reference_date)
    pc = lambda x: f"{x * 100:.2f} %".replace('.', ',')
    lignes = []
    if regime == 'employe':
        lignes.append("Employé (CDI, ou CDD d'au moins trois mois) : rémunération maintenue à 100 % pendant les 30 premiers "
                      "jours calendrier, sans condition d'ancienneté ; ONSS et précompte ordinaires (loi du 03/07/1978, art. 70).")
    else:
        qui = "Ouvrier" if regime == 'ouvrier' else "Employé engagé pour moins de trois mois"
        art = "art. 52 § 1er" if regime == 'ouvrier' else "art. 71"
        cct = "CCT n° 12bis" if regime == 'ouvrier' else "CCT n° 13bis"
        lignes += [
            f"{qui} : un mois d'ancienneté ininterrompue requis ; le droit s'ouvre pour les jours restants quand le mois "
            f"est atteint pendant l'incapacité (loi du 03/07/1978, {art}).",
            f"Jours 1 à {p['fin_100']} : rémunération normale à 100 %, soumise à l'ONSS"
            + (" (base 108 %)" if regime == 'ouvrier' else "") + " et au précompte.",
            f"Jours {p['fin_100'] + 1} à {p['fin_2e_semaine']} : {pc(p['pct_2e_semaine'])} de la rémunération normale — "
            f"hors ONSS (Instructions ONSS 2026/3 p.115 et 506), imposable ({cct}).",
            f"Jours {p['fin_2e_semaine'] + 1} à {p['fin_periode']} : complément de {pc(p['pct_complement_sous_plafond'])} de la "
            f"partie sous le plafond AMI + {pc(p['pct_au_dessus_plafond'])} de la partie au-dessus — hors ONSS, imposable ({cct}). "
            f"La mutuelle paie le reste.",
        ]
    lignes += [
        f"À partir du 31e jour : mutuelle, plus rien à charge de l'employeur.",
        f"Rechute dans les {delai['libelle']} suivant la fin d'une incapacité : pas de nouveau salaire garanti, sauf le solde "
        f"non utilisé et sauf autre maladie ou autre accident attesté par certificat ({delai['source']}).",
        "Pas de jour de carence (supprimé le 01/01/2014, loi du 26/12/2013 art. 62).",
        "Les jours hors ONSS n'entrent ni dans le bonus à l'emploi ni dans les réductions patronales "
        "(Instructions ONSS 2026/3 p.450 : codes prestation 10 et 11).",
        "Non contrôlé par l'outil : accident du travail, maladie professionnelle, accident sportif rémunéré, faute grave "
        "(art. 52 § 3 et 73 § 2), jours fériés pendant l'incapacité.",
    ]
    return lignes


# ─────────────────────────────────────────────────────────────────
# MONTANTS DU MOIS
# ─────────────────────────────────────────────────────────────────
def indemnites_du_mois(regime, jours, salaire_horaire=0.0, salaire_mensuel=None, jours_ouvrables_mois=None,
                       heures_jour=7.6, jours_semaine=5):
    """jours: [{'date', 'tranche', 'heures'}] = jours PREVUS A L'HORAIRE tombant dans
    une incapacite, pour le mois de paie. Salaire normal d'un jour (decision de Leo,
    02/10/2026): ce que le travailleur aurait gagne selon son horaire contractuel
    -- heures prevues x taux horaire, ou salaire mensuel / jours ouvrables du mois
    quand salaire_mensuel est transmis (employe paye au mois).
    Retourne {'lignes' (soumis_onss True/False), 'compte', 'jours_non_garantis',
    'hors_onss', 'alertes'}."""
    au_mois = bool(salaire_mensuel)
    compte = {t: {'jours': 0, 'heures': 0.0, 'normal': 0.0, 'montant': 0.0} for t in CODES_INCAPACITE}
    alertes, plafond_joue, plafond_absent, plafond_a_confirmer = [], False, False, None
    if au_mois:
        if not jours_ouvrables_mois:
            raise ValueError("Salaire garanti d'un employé payé au mois : jours ouvrables du mois requis.")
        hebdo = salaire_mensuel * 12 / 52
    else:
        hebdo = salaire_horaire * float(heures_jour or 0) * int(jours_semaine or 0)
    for j in jours or []:
        t = j['tranche']
        if t not in compte:
            continue
        heures = float(j.get('heures') or 0)
        normal = (salaire_mensuel / jours_ouvrables_mois) if au_mois else salaire_horaire * heures
        p = get_salaire_garanti_params(j['date'])['regimes'][regime]
        c = compte[t]
        c['jours'] += 1; c['heures'] += heures; c['normal'] += normal
        if t == 'MG':
            c['montant'] += normal
        elif t == 'M2':
            c['montant'] += normal * p['pct_2e_semaine']
        elif t == 'MC':
            # Part du salaire sous le plafond AMI: comparaison A LA SEMAINE (plafond
            # journalier x 6), equivalente au plafond mensuel x 26 et au plafond
            # journalier x 6/5 en regime de 5 jours (parametres_dates.PLAFOND_AMI_VERSIONS)
            plafond = get_plafond_ami(j['date'])
            fraction_sous = 1.0
            if plafond is None:
                plafond_absent = True
            elif hebdo > plafond['plafond_jour_6j'] * 6:
                fraction_sous = plafond['plafond_jour_6j'] * 6 / hebdo
                plafond_joue = True
                plafond_a_confirmer = plafond if plafond.get('a_confirmer') else plafond_a_confirmer
            c['montant'] += normal * (fraction_sous * p['pct_complement_sous_plafond']
                                      + (1 - fraction_sous) * p['pct_au_dessus_plafond'])
    for c in compte.values():
        c['heures'] = round(c['heures'], 2); c['normal'] = round(c['normal'], 2); c['montant'] = round(c['montant'], 2)
    if plafond_absent:
        alertes.append("Plafond AMI non chargé pour cette période : complément des jours 15 à 30 calculé comme si toute la "
                       "rémunération était sous le plafond. À vérifier si le salaire est élevé.")
    if plafond_joue:
        alertes.append("Rémunération supérieure au plafond AMI : complément des jours 15 à 30 calculé avec la partie "
                       "au-dessus du plafond (comparaison à la semaine, plafond journalier × 6)."
                       + (" Montant du plafond à confirmer sur le PDF de l'INAMI." if plafond_a_confirmer else ""))
    if au_mois and int(jours_semaine or 5) < 5 and any(compte[t]['jours'] for t in ('M2', 'MC', 'MM')):
        alertes.append("Employé au mois avec un horaire de moins de 5 jours par semaine : la valeur d'un jour de maladie est "
                       "calculée sur les jours ouvrables du mois (lundi à vendredi), à contrôler.")

    p = get_salaire_garanti_params(min((j['date'] for j in jours), default=date.today()))['regimes'][regime] if jours else None
    pc = lambda x: f"{x * 100:.2f} %".replace('.', ',')
    lignes = []
    non_garantis = sum(compte[t]['jours'] for t in ('M2', 'MC', 'MM'))
    base = salaire_mensuel if au_mois else salaire_horaire
    if compte['MG']['jours'] and not au_mois:
        lignes.append({'libelle': 'Salaire garanti maladie (100 %)', 'base': base, 'jours': compte['MG']['jours'],
                       'heures': compte['MG']['heures'], 'montant': compte['MG']['montant'], 'soumis_onss': True,
                       'tranche': 'MG'})
    if au_mois and non_garantis:
        retenue = round(sum(compte[t]['normal'] for t in ('M2', 'MC', 'MM')), 2)
        lignes.append({'libelle': f'Maladie – jours hors salaire garanti à 100 % ({non_garantis} j)', 'base': 0,
                       'jours': non_garantis, 'heures': 0, 'montant': -retenue, 'soumis_onss': True, 'tranche': 'retenue'})
    if compte['M2']['jours']:
        lignes.append({'libelle': f"Indemnité maladie 2e semaine ({pc(p['pct_2e_semaine'])})", 'base': base,
                       'base_decimales': 2 if au_mois else 4,
                       'jours': compte['M2']['jours'], 'heures': compte['M2']['heures'],
                       'montant': compte['M2']['montant'], 'soumis_onss': False, 'tranche': 'M2'})
    if compte['MC']['jours']:
        lignes.append({'libelle': f"Complément maladie jours 15 à 30 ({pc(p['pct_complement_sous_plafond'])}"
                                  + (f" + {pc(p['pct_au_dessus_plafond'])} au-dessus du plafond" if plafond_joue else '') + ")",
                       'base': base, 'base_decimales': 2 if au_mois else 4,
                       'jours': compte['MC']['jours'], 'heures': compte['MC']['heures'],
                       'montant': compte['MC']['montant'], 'soumis_onss': False, 'tranche': 'MC'})
    return {'lignes': lignes, 'compte': compte, 'jours_non_garantis': non_garantis,
            'hors_onss': round(compte['M2']['montant'] + compte['MC']['montant'], 2), 'alertes': alertes}


# ─────────────────────────────────────────────────────────────────
# CALENDRIER: jours a marquer pour un episode
# ─────────────────────────────────────────────────────────────────
def jours_a_marquer(v, jours_semaine=5, jours_feries=()):
    """Jours d'un episode ventile a inscrire au calendrier: jours prevus a l'horaire
    (lundi -> vendredi, ou samedi compris en regime de 6 jours), hors jours feries
    (laisses tels quels: l'outil ne decide pas a la place de Leo).
    Retourne (jours, feries_rencontres)."""
    dernier = 5 if int(jours_semaine or 5) >= 6 else 4
    feries = set(jours_feries or ())
    a_marquer = [j for j in v['jours'] if j['date'].weekday() <= dernier and j['date'] not in feries]
    return a_marquer, [j['date'] for j in v['jours'] if j['date'] in feries and j['date'].weekday() <= dernier]


# ─────────────────────────────────────────────────────────────────
# CONTEXTE COMPLET D'UN TRAVAILLEUR (pages, calendrier, fiche de paie)
# ─────────────────────────────────────────────────────────────────
def contexte_incapacites(episodes, contrats, contrat, is_ouvrier, jusqu_au):
    """Episodes ventiles + regles, suivi et alertes a afficher. episodes: lignes de
    la table incapacites ; contrats: tous les contrats du travailleur ; contrat:
    celui qui fixe le regime (ouvrier / employe / employe engage pour moins de
    trois mois)."""
    regime, debut_anc, alertes = None, None, []
    if contrat:
        regime = regime_salaire_garanti(is_ouvrier, contrat['type_contrat'], contrat.get('date_debut'), contrat.get('date_fin'))
        debut_anc = debut_occupation_ininterrompue(contrats, contrat['date_debut']) or contrat['date_debut']
    else:
        alertes.append("Aucun contrat pour ce travailleur : le salaire garanti ne peut pas être calculé.")
    ventilation = []
    if regime and episodes:
        try:
            ventilation = ventiler_episodes(episodes, regime, debut_anc, jusqu_au)
        except ValueError as ex:
            alertes.append(str(ex))
    elif episodes and contrat:
        alertes.append("Contrat étudiant : le salaire garanti n'est pas géré par l'outil. Les jours d'incapacité ne sont "
                       "ni marqués au calendrier ni payés automatiquement.")
    for v in ventilation:
        v['libelle_type'] = TYPES_INCAPACITE.get(v['episode'].get('type_incapacite'), 'Maladie')
        v['periodes'] = [{'tranche': t, 'libelle': LIBELLES_TRANCHES[t], 'du': du, 'au': au, 'jours': nb, 'motif': motif}
                         for t, du, au, nb, motif in resume_periodes(v)]
    return {'episodes': episodes, 'ventilation': ventilation, 'par_date': tranches_par_date(ventilation),
            'regime': regime, 'contrat': contrat, 'contrats': contrats, 'debut_anciennete': debut_anc, 'alertes': alertes,
            'regles': regles_affichees(regime, jusqu_au) if contrat else []}


# ─────────────────────────────────────────────────────────────────
# PROTECTION: jours « maladie » du calendrier sans episode
# ─────────────────────────────────────────────────────────────────
CODES_MALADIE_CALENDRIER = ('MA',) + CODES_INCAPACITE


def jours_maladie_sans_episode(jours_codes, par_date):
    """jours_codes: [(date, code du calendrier)] ; par_date: tranches_par_date(...).
    Retourne les groupes de jours codes maladie qui ne tombent dans AUCUN episode
    d'incapacite: [{'debut', 'fin', 'jours'}] -- un groupe par suite de jours
    (un week-end ou un jour ferie entre deux jours ne coupe pas le groupe).
    Sert a proposer la creation de l'episode, pre-rempli avec ces dates."""
    orphelins = sorted(d for d, code in jours_codes if code in CODES_MALADIE_CALENDRIER and d not in (par_date or {}))
    groupes = []
    for d in orphelins:
        if groupes and (d - groupes[-1]['fin']).days <= 4:
            groupes[-1]['fin'] = d; groupes[-1]['jours'] += 1
        else:
            groupes.append({'debut': d, 'fin': d, 'jours': 1})
    return groupes
