# -*- coding: utf-8 -*-
"""
dmfa.py -- DuxSalary
AIDE A LA DmfA: regroupement trimestriel, par employeur et par travailleur, des
donnees a recopier dans la DmfA web (socialsecurity.be). Module pur: il additionne
les fiches de paie enregistrees (fiches_paie) et relit le calendrier des
prestations ; il n'envoie rien a l'ONSS et ne remplace pas la declaration.

Source: Instructions administratives ONSS 2026/3 (sources/dmfa-instructions.pdf):
- codes prestation: p.547-553 (codes ordinaires 1, 2, 3, 10, 11, 30 ; codes
  indicatifs 50, 51, 52, 60, 70, 71, 72) ;
- codes remuneration 1 et 2: chapitre « Code remuneration » ;
- reductions: p.375-377 (S, µ, µ(glob), ß, plancher de 0,275), p.383 (reduction
  structurelle, code 3000, bloc 90109), premiers engagements (code 3315, bloc
  90109, G = 2 000 EUR depuis le 01/07/2026), bonus a l'emploi (code 0001, bloc
  90110, « se calcule mensuellement et se declare globalement pour le trimestre ») ;
- cotisation speciale de securite sociale: bloc 90001, code 856 (a encoder
  soi-meme sur le web) ; double pecule des employes: bloc 90002, code 870 ;
  etudiants: bloc 90003, codes 840 / 841.
"""
import json
from datetime import date, timedelta
from calendar import monthrange

# ─────────────────────────────────────────────────────────────────
# CODES
# ─────────────────────────────────────────────────────────────────
CODES_TRAVAILLEUR = {'ouvrier': '015', 'employe': '495', 'etudiant_ouvrier': '840', 'etudiant_employe': '841'}

LIBELLES_PRESTATION = {
    1: 'Travail, jours fériés, petit chômage, salaire garanti à 100 %, vacances des employés',
    2: 'Vacances légales des ouvriers',
    3: 'Vacances complémentaires des ouvriers (payées par l\'employeur)',
    10: 'Salaire garanti 2e semaine',
    11: 'Incapacité avec complément CCT 12bis / 13bis',
    30: 'Congé sans solde et autres absences non payées',
    50: 'Maladie ou accident de droit commun (mutuelle)',
    51: 'Protection de la maternité',
    72: 'Chômage temporaire pour intempéries',
}

# Code journalier du calendrier -> code prestation ONSS, pour tous les statuts.
# Verifies un a un dans les Instructions 2026/3 p.547-553.
_PRESTATION_COMMUNE = {
    'P': 1, 'S': 1, 'HS': 1,      # travail effectif normal, prestations supplementaires (code 1)
    'PP': 1,                       # petits chomages (code 1)
    'F': 1, 'FM': 1,               # jours feries et jours de remplacement (code 1)
    'MG': 1,                       # incapacite avec revenu garanti premiere semaine / mensuel garanti (code 1)
    'M2': 10,                      # salaire garanti deuxieme semaine (code 10)
    'MC': 11,                      # complement CCT 12bis/13bis (code 11)
    'MM': 50,                      # maladie ou accident de droit commun, sans salaire (code indicatif 50)
    'CNP': 30,                     # conge sans solde (code 30)
    'IN': 30,                      # « toutes les autres donnees ... pour lesquelles l'employeur ne paie pas » (code 30)
    'CI': 72,                      # chomage temporaire pour cause d'intemperies (code indicatif 72)
    'MAT': 51,                     # protection de la maternite (code indicatif 51)
}
# Selon le statut: vacances
_PRESTATION_STATUT = {
    'employe': {'CL': 1, 'CE': 1},     # vacances legales et complementaires des employes (code 1)
    'ouvrier': {'CL': 2, 'VP': 2,      # vacances legales des ouvriers (code 2)
                'CE': 3},              # vacances complementaires des ouvriers, payees par l'employeur (code 3)
}
# Codes que l'outil ne peut PAS determiner seul: alerte « code a determiner »
A_DETERMINER = {
    'MA': "maladie sans épisode d'incapacité : créez l'épisode (code 1, 10, 11 ou 50 selon le jour)",
    'CT': "chômage temporaire : code 71 (chômage économique) ou code 70 (autre motif) — le calendrier ne précise pas le motif",
    'PAT': "congé de naissance : code 1 pour les jours payés par l'employeur, code 52 pour les jours à charge de la mutuelle",
    'AC': "accident du travail : code 1 pour les jours de salaire garanti, code 60 ensuite",
    'VP': "vacances « ONVA » encodées pour un employé : code 1 si ce sont des vacances légales payées par l'employeur",
}
IGNORES = {'WE', 'HD'}
CODES_J_S = {1, 3, 4, 5, 20, 38}                          # J / H du salaire de reference S (p.375)
CODES_X_MU = {1, 2, 3, 4, 5, 12, 16, 17, 20, 38, 72}      # X / Z de la fraction de prestation µ (p.376)


def _r2(x):
    from decimal import Decimal, ROUND_HALF_UP
    return float(Decimal(str(x)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def _n(v):
    return float(v) if v is not None else 0.0


def montant(v):
    return f"{v:,.2f}".replace(',', ' ').replace('.', ',')


def nombre(v):
    return f"{v:g}".replace('.', ',')


def bornes_trimestre(annee, trimestre):
    m = 3 * (trimestre - 1) + 1
    return date(annee, m, 1), date(annee, m + 2, monthrange(annee, m + 2)[1])


def trimestre_de(d):
    return d.year, (d.month - 1) // 3 + 1


def code_prestation(code_journee, statut):
    """(code prestation ONSS, None) ou (None, motif) quand le code est a determiner
    par Leo. statut: 'ouvrier' | 'employe' (un etudiant suit le statut de son travail)."""
    if code_journee in _PRESTATION_COMMUNE:
        return _PRESTATION_COMMUNE[code_journee], None
    if code_journee in _PRESTATION_STATUT.get(statut, {}):
        return _PRESTATION_STATUT[statut][code_journee], None
    return None, A_DETERMINER.get(code_journee, f"code « {code_journee} » inconnu de l'aide DmfA")


def jours_ouvrables(debut, fin):
    return sum(1 for n in range((fin - debut).days + 1) if (debut + timedelta(n)).weekday() < 5) if fin >= debut else 0


def prestations_par_code(jours, statut, heures_jour=7.6, au_mois=False, jours_ouvrables_periode=None):
    """jours: [(date, code journalier, heures)] du calendrier pour une occupation et
    une periode. Retourne {'codes': {code: {'jours', 'heures'}}, 'a_determiner':
    {code journalier: {'jours', 'motif'}}}.
    Les heures d'une absence sans heures encodees valent les heures par jour du contrat.
    au_mois (employe paye au mois): comme dans le moteur, le salaire couvre tous les
    jours ouvrables ; le code 1 est complete a (jours ouvrables - autres jours)."""
    codes, a_det = {}, {}
    for d, cj, heures in jours:
        if cj in IGNORES:
            continue
        code, motif = code_prestation(cj, statut)
        if code is None:
            x = a_det.setdefault(cj, {'jours': 0, 'motif': motif})
            x['jours'] += 1
            continue
        h = _n(heures) or float(heures_jour or 0)
        c = codes.setdefault(code, {'jours': 0, 'heures': 0.0})
        c['jours'] += 1; c['heures'] = round(c['heures'] + h, 2)
    if au_mois and jours_ouvrables_periode is not None:
        autres = sum(c['jours'] for k, c in codes.items() if k != 1) + sum(x['jours'] for x in a_det.values())
        j1 = max(0, jours_ouvrables_periode - autres)
        codes[1] = {'jours': j1, 'heures': round(j1 * float(heures_jour or 0), 2)}
        if not j1:
            del codes[1]
    return {'codes': codes, 'a_determiner': a_det}


def jours_du_calendrier(lignes, par_date):
    """Lignes de la table prestations -> [(date, code, heures)], les codes maladie
    etant ramenes a la tranche recalculee depuis les episodes d'incapacite (par_date =
    salaire_garanti.tranches_par_date), ou a « MA » quand aucun episode ne couvre le jour."""
    resultat = []
    for l in lignes:
        d, code = l['date_prestation'], l['code_journee']
        if code in ('MA', 'MG', 'M2', 'MC', 'MM'):
            code = (par_date or {}).get(d, {}).get('tranche') or 'MA'
        resultat.append((d, code, l.get('heures')))
    return resultat


def prestations_occupation(contrat, jours, debut, fin):
    """Jours par code prestation d'un contrat sur [debut, fin] (un mois pour la fiche,
    un trimestre pour l'aide): meme calcul des deux cotes, pour qu'ils soient comparables."""
    statut_travail = _statut_cp(contrat['cp_key'])
    du, au = max(contrat['date_debut'], debut), min(contrat.get('date_fin') or fin, fin)
    au_mois = statut_travail == 'employe' and contrat.get('type_contrat') in ('CDI', 'CDD')
    return prestations_par_code([(d, cj, h) for d, cj, h in jours if du <= d <= au], statut_travail,
                                _n(contrat.get('heures_jour')) or 7.6, au_mois, jours_ouvrables(du, au) if au_mois else None)


def prestations_json(p):
    """Forme enregistree dans fiches_paie.prestations_dmfa."""
    return json.dumps({'codes': {str(k): v for k, v in sorted(p['codes'].items())},
                       'a_determiner': {k: v['jours'] for k, v in p['a_determiner'].items()}}, ensure_ascii=False)


def _lire_json(v):
    if not v:
        return None
    return json.loads(v) if isinstance(v, str) else v


def _additionner(listes):
    total = {}
    for codes in listes:
        for k, v in codes.items():
            t = total.setdefault(int(k), {'jours': 0, 'heures': 0.0})
            t['jours'] += v['jours']; t['heures'] = round(t['heures'] + _n(v['heures']), 2)
    return total


# ─────────────────────────────────────────────────────────────────
# REDUCTIONS: RECALCUL TRIMESTRIEL OFFICIEL (Instructions 2026/3 p.375-377, 383)
# ─────────────────────────────────────────────────────────────────
def beta(mu_glob, structurelle=True, mi_temps=True):
    """Facteur ß (jamais arrondi). Plancher: µ(glob) < 0,275 -> 0, sauf contrat au
    moins a mi-temps (p.377)."""
    if mu_glob <= 0 or (mu_glob < 0.275 and not mi_temps):
        return 0.0
    base, pente = (1.18, 0.28) if structurelle else (1.0, 1.0)
    if mu_glob < 0.55:
        return base
    if mu_glob < 0.80:
        return base + (mu_glob - 0.55) * pente
    return 1 / mu_glob


def reductions_trimestre(W, codes, en_jours, D, U, fin_trimestre, mu_glob=None, mi_temps=True,
                         premier_engagement=False, cotisations_reductibles=None):
    """Reduction structurelle (Ps) et premier engagement (Pg) d'une ligne d'occupation,
    calcules sur le TRIMESTRE comme le fait la DmfA.
      W: masse salariale du trimestre a 100 % ; codes: {code prestation: {'jours','heures'}} ;
      en_jours: occupation declaree uniquement en jours (temps plein) ; D: jours par
      semaine du regime ; U: heures par semaine du travailleur de reference.
      S = W x (13 x D / J) ou W x (13 x U / H), J/H = codes 1, 3, 4, 5, 20, 38
      µ = X / (13 x D) ou Z / (13 x U), X/Z = codes 1, 2, 3, 4, 5, 12, 16, 17, 20, 38, 72
      Ps = R x µ x ßs ; Pg = G x µ x ßg ; plafond: cotisations reductibles, Pg reduit en premier."""
    from parametres_dates import get_reduction_structurelle_params, get_premier_engagement_params
    cle = 'jours' if en_jours else 'heures'
    denominateur = 13 * (D if en_jours else U)
    j_s = sum(_n(v[cle]) for k, v in codes.items() if k in CODES_J_S)
    x_mu = sum(_n(v[cle]) for k, v in codes.items() if k in CODES_X_MU)
    r = {'unite': cle, 'J': j_s, 'X': x_mu, 'W': _r2(W), 'facteur': None, 'S': None, 'R': 0.0, 'mu': 0.0,
         'mu_glob': None, 'beta_s': 0.0, 'beta_g': 0.0, 'Ps': 0.0, 'Pg': 0.0, 'G': None, 'plafonne': False}
    if not j_s or not denominateur or W <= 0:
        return r
    p = get_reduction_structurelle_params(fin_trimestre)
    r['facteur'] = _r2(denominateur / j_s)
    r['S'] = _r2(W * r['facteur'])
    r['R'] = _r2(max(0.0, _r2(p['coeff_bas'] * (p['seuil_bas'] - r['S'])))
                 + max(0.0, _r2(p['coeff_tres_bas'] * (p['seuil_tres_bas'] - r['S']))))
    r['mu'] = _r2(x_mu / denominateur)
    r['mu_glob'] = r['mu'] if mu_glob is None else mu_glob
    r['beta_s'], r['beta_g'] = beta(r['mu_glob'], True, mi_temps), beta(r['mu_glob'], False, mi_temps)
    r['Ps'] = _r2(r['R'] * r['mu'] * r['beta_s'])
    if premier_engagement:
        r['G'] = get_premier_engagement_params(fin_trimestre)['forfait_1er_trimestriel']
        r['Pg'] = _r2(r['G'] * r['mu'] * r['beta_g'])
    if cotisations_reductibles is not None and r['Ps'] + r['Pg'] > cotisations_reductibles:
        r['plafonne'] = True
        exces = _r2(r['Ps'] + r['Pg'] - cotisations_reductibles)
        retrait_g = min(r['Pg'], exces)
        r['Pg'] = _r2(r['Pg'] - retrait_g)
        r['Ps'] = _r2(max(0.0, r['Ps'] - (exces - retrait_g)))
    return r


def estimer_mu_trimestre(periode_debut, periode_fin, en_jours, D, U, heures_jour, quantite_mois, quantite_precedente=0.0,
                         date_fin_contrat=None):
    """ESTIMATION, des la fiche d'un mois, de la fraction de prestation µ du TRIMESTRE entier
    (c'est elle que la DmfA compare au plancher de 0,275, Instructions ONSS 2026/3 p.377 et
    p.399). quantite_mois: jours (occupation declaree en jours) ou heures du mois de la fiche ;
    quantite_precedente: celles des mois deja payes du trimestre ; le reste du trimestre est
    PREVU selon l'horaire du contrat, jusqu'a la fin du contrat si elle tombe avant la fin du
    trimestre. Retourne {'mu', 'realise', 'prevu', 'fin_trimestre', 'contrat_termine'}."""
    _, fin_t = bornes_trimestre(*trimestre_de(periode_debut))
    fin_prevue = min(fin_t, date_fin_contrat) if date_fin_contrat else fin_t
    jours_restants = jours_ouvrables(periode_fin + timedelta(days=1), fin_prevue) * (int(D or 5) / 5)
    prevu = jours_restants if en_jours else jours_restants * float(heures_jour or 0)
    realise = float(quantite_precedente or 0) + float(quantite_mois or 0)
    denominateur = 13 * (int(D or 5) if en_jours else float(U or 38))
    return {'mu': _r2((realise + prevu) / denominateur) if denominateur else 0.0, 'realise': round(realise, 2),
            'prevu': round(prevu, 2), 'unite': 'jours' if en_jours else 'heures', 'fin_trimestre': fin_t,
            'contrat_termine': bool(date_fin_contrat and date_fin_contrat <= fin_t)}


# ─────────────────────────────────────────────────────────────────
# AIDE DmfA
# ─────────────────────────────────────────────────────────────────
def _statut_cp(cp_key):
    from moteur_paie import CP_INDEMNITES
    return CP_INDEMNITES.get(cp_key, {}).get('type_travailleur', 'ouvrier')


def _numero_cp(cp_key):
    """« CP 200 » -> 200.00 ; « CP 140.03 » -> 140.03 (forme de la DmfA)."""
    n = (cp_key or '').replace('CP', '').strip()
    return n if '.' in n else (n + '.00' if n else '')


def _tableau(titre, colonnes, lignes, note=None):
    return {'titre': titre, 'colonnes': colonnes, 'lignes': lignes, 'note': note}


def _occupation(c, fiches, jours, dossier, debut_t, fin_t):
    """Donnees brutes d'une ligne d'occupation (un contrat) pour le trimestre."""
    from profil_travailleur import construire_profil
    from onss_taux import cotisations_complementaires
    etudiant = c.get('type_contrat') == 'STU'
    statut_travail = _statut_cp(c['cp_key'])
    statut = 'etudiant' if etudiant else statut_travail
    code_trav = CODES_TRAVAILLEUR[f'etudiant_{statut_travail}' if etudiant else statut_travail]
    du, au = max(c['date_debut'], debut_t), min(c.get('date_fin') or fin_t, fin_t)
    D = int(c.get('jours_semaine') or 5)
    h_jour = _n(c.get('heures_jour')) or 7.6
    U = _n(c.get('heures_semaine')) or 38.0
    Q = round(h_jour * D, 2)
    temps_plein = Q >= U - 0.005
    au_mois = statut == 'employe' and c.get('type_contrat') in ('CDI', 'CDD')
    alertes = []

    # Prestations: calendrier (jours de l'occupation dans le trimestre)
    cal = prestations_occupation(c, jours, debut_t, fin_t)
    # Prestations: detail enregistre dans les fiches (a partir du 02/10/2026)
    details = [_lire_json(f.get('prestations_dmfa')) for f in fiches]
    enregistre = _additionner([d['codes'] for d in details]) if fiches and all(details) else None
    mois_fiches = {(f['periode_debut'].year, f['periode_debut'].month) for f in fiches}
    mois_occ = sorted({(d.year, d.month) for d in (du + timedelta(n) for n in range((au - du).days + 1))}) if au >= du else []
    manquants = [m for m in mois_occ if m not in mois_fiches]
    if manquants:
        alertes.append("Pas de fiche de paie pour " + ', '.join(f"{m:02d}/{a}" for a, m in manquants)
                       + " : rémunérations et cotisations de ces mois absentes des totaux.")
    if fiches and enregistre is None:
        alertes.append("Fiche(s) générée(s) avant l'enregistrement du détail des jours par code : comparaison avec le "
                       "calendrier impossible (régénérez la fiche pour l'obtenir).")
    elif enregistre is not None and not manquants:
        def _cle(x):
            return {k: (v['jours'], round(_n(v['heures']), 2)) for k, v in x.items() if v['jours']}
        if _cle(enregistre) != _cle(cal['codes']):
            alertes.append(
                "Le calendrier ne correspond plus aux fiches enregistrées — calendrier : "
                + ' ; '.join(f"code {k} = {v['jours']} j / {nombre(v['heures'])} h" for k, v in sorted(cal['codes'].items()))
                + " — fiches : "
                + ' ; '.join(f"code {k} = {v['jours']} j / {nombre(v['heures'])} h" for k, v in sorted(enregistre.items()))
                + ". Régénérez la fiche du mois modifié ou corrigez le calendrier.")
    for cj, x in cal['a_determiner'].items():
        alertes.append(f"Code à déterminer pour {x['jours']} jour(s) « {cj} » : {x['motif']}.")
    if any(not f.get('detail_complet') for f in fiches):
        alertes.append("Fiche antérieure sans détail (« n.d. ») : cotisations par code incomplètes, régénérez-la.")
    if au_mois and D != 5:
        alertes.append(f"Employé au mois avec un régime de {D} jours par semaine : les jours du code 1 sont comptés du "
                       f"lundi au vendredi, à contrôler.")

    # Remunerations (a 100 %)
    prime = sum(_n(f.get('prime_brut')) for f in fiches)
    remu1 = _r2(sum(_n(f.get('salaire_brut')) for f in fiches) - prime)
    pecule = sum(_n(f.get('pecule_brut')) for f in fiches)
    W = _r2(remu1 + prime)

    o = {'contrat': c, 'statut': statut, 'statut_travail': statut_travail, 'etudiant': etudiant, 'code_travailleur': code_trav,
         'du': du, 'au': au, 'D': D, 'Q': Q, 'U': U, 'temps_plein': temps_plein, 'au_mois': au_mois,
         'prestations': cal['codes'], 'a_determiner': cal['a_determiner'], 'prestations_fiches': enregistre,
         'remunerations': {1: remu1, 2: _r2(prime)}, 'W': W, 'double_pecule': _r2(pecule), 'alertes': alertes,
         'nb_fiches': len(fiches), 'heures_etudiant': None, 'cotisations': [], 'reductions': {}}

    categorie = (dossier.get('categorie_employeur') or '000')
    profil = construire_profil(c['cp_key'], statut, type_contrat=c.get('type_contrat') or 'CDI', heures_semaine=U,
                               jours_semaine=D, reference_date=fin_t, categorie_employeur=categorie)
    info = profil.onss_officiel
    if info.get('parametres_reportes'):
        alertes.append(f"Taux ONSS du {info['trimestre_demande']} pas encore publiés : recalcul avec le {info['trimestre_utilise']}.")
    base = _r2(W * profil.coeff_base_onss_patronal)
    o['base'] = base
    cot = []   # (code, libelle, base, taux, recalcul)
    if etudiant:
        o['heures_etudiant'] = round(sum(_n(f.get('heures_prestees')) + _n(f.get('heures_feries')) for f in fiches), 2)
        cot.append((code_trav, 'Cotisation de solidarité — part de l\'étudiant', W, profil.onss_personnel_taux,
                    _r2(W * profil.onss_personnel_taux)))
        cot.append((code_trav, 'Cotisation de solidarité — part de l\'employeur', W, profil.onss_patronal_reductible_taux,
                    _r2(W * profil.onss_patronal_reductible_taux)))
        fiches_cot = _r2(sum(_n(f.get('onss_personnel')) + _n(f.get('onss_patronal')) for f in fiches))
    else:
        cot.append((code_trav, 'Cotisation personnelle', base, profil.onss_personnel_taux, _r2(base * profil.onss_personnel_taux)))
        cot.append((code_trav, 'Cotisation patronale de base + modération salariale (réductible)', base,
                    profil.onss_patronal_reductible_taux, _r2(base * profil.onss_patronal_reductible_taux)))
        if profil.onss_vacances_trimestrielle_taux:
            cot.append(('253', 'Vacances annuelles des ouvriers', base, profil.onss_vacances_trimestrielle_taux,
                        _r2(base * profil.onss_vacances_trimestrielle_taux)))
        compl, avert = cotisations_complementaires(statut, fin_t, categorie=categorie, code_ffe=dossier.get('code_ffe'),
                                                   code_importance=dossier.get('code_importance'))
        alertes += [a for a in avert]
        for cc in compl:
            cot.append((cc['code'], cc['libelle'][:70], base, cc['taux'], _r2(base * cc['taux'])))
        # Total des fiches: personnel avant bonus (primes comprises, hors retenue du double pecule)
        # + patronal avant reductions
        retenue_pecule = sum(_r2(_r2(_n(f.get('pecule_brut')) * 85 / 92) * 0.1307) for f in fiches)
        fiches_cot = _r2(sum(_n(f.get('onss_personnel_brut')) + _n(f.get('onss_exceptionnel')) + _n(f.get('onss_patronal'))
                             + _n(f.get('reduction_structurelle')) + _n(f.get('reduction_premier_engagement'))
                             for f in fiches) - retenue_pecule)
    o['cotisations'] = cot
    o['cotisations_recalcul'] = _r2(sum(x[4] for x in cot))
    o['cotisations_fiches'] = fiches_cot
    o['reductible_recalcul'] = 0.0 if etudiant else cot[1][4]
    o['css'] = _r2(sum(_n(f.get('css')) for f in fiches))
    o['bonus'] = _r2(sum(_n(f.get('bonus_emploi_a')) + _n(f.get('bonus_emploi_b')) for f in fiches))
    o['reductions_fiches'] = {'3000': _r2(sum(_n(f.get('reduction_structurelle')) for f in fiches)),
                              '3315': _r2(sum(_n(f.get('reduction_premier_engagement')) for f in fiches))}
    return o


def aide_dmfa(dossier, annee, trimestre, travailleurs):
    """travailleurs: [{'travailleur': {...}, 'contrats': [...], 'fiches': [lignes de
    fiches_paie du trimestre], 'jours': [(date, code journalier, heures)]}] -- les
    codes maladie du calendrier sont deja ramenes a leur tranche (MG, M2, MC, MM) ou
    a « MA » quand aucun episode ne les couvre.
    Retourne un document: entete, alertes, travailleurs (tableaux a recopier +
    donnees brutes), totaux."""
    from occupation import contrat_de_la_periode
    debut_t, fin_t = bornes_trimestre(annee, trimestre)
    d = dossier or {}
    alertes = []
    if not d.get('numero_unite_etablissement'):
        alertes.append("Numéro d'unité d'établissement non renseigné dans le dossier : il est demandé sur chaque ligne "
                       "d'occupation de la DmfA (page « Modifier le dossier »).")
    resultat, tot = [], {'cot_recalcul': 0.0, 'cot_fiches': 0.0, 'css': 0.0, 'bonus': 0.0, 's_fiches': 0.0, 's_recalcul': 0.0,
                         'g_fiches': 0.0, 'g_recalcul': 0.0, 'double_pecule': 0.0, 'remu': 0.0}
    for t in travailleurs:
        trav, contrats = t['travailleur'], list(t.get('contrats') or [])
        fiches, jours = list(t.get('fiches') or []), list(t.get('jours') or [])
        alertes_t = []
        # Une ligne d'occupation par contrat touchant le trimestre: contrat actif, ou
        # contrat (meme archive) auquel une fiche du trimestre est rattachee
        par_contrat = {}
        for f in fiches:
            c = next((x for x in contrats if x.get('id') == f.get('contrat_id')), None) or \
                contrat_de_la_periode(contrats, f['periode_debut'], f['periode_fin'])
            if c is None:
                alertes_t.append(f"Fiche de {f['periode_debut']:%m/%Y} sans contrat retrouvé : non reprise.")
                continue
            par_contrat.setdefault(c['id'], []).append(f)
        retenus = [c for c in contrats if c.get('date_debut') and c['date_debut'] <= fin_t
                   and (not c.get('date_fin') or c['date_fin'] >= debut_t)
                   and (c['id'] in par_contrat or c.get('statut') == 'actif')]
        if not retenus:
            continue
        occupations = []
        for c in sorted(retenus, key=lambda x: x['date_debut']):
            try:
                occupations.append(_occupation(c, par_contrat.get(c['id'], []), jours, d, debut_t, fin_t))
            except ValueError as ex:      # CP non geree, taux absents...: pas de calcul devine
                alertes_t.append(f"Contrat {c.get('type_contrat')} en {c.get('cp_key')} non repris : {ex}")
        ordinaires = [o for o in occupations if not o['etudiant']]
        # Reductions: recalcul trimestriel par ligne d'occupation, ß sur µ(glob) du travailleur
        mus = {}
        for o in ordinaires:
            r0 = reductions_trimestre(o['W'], o['prestations'], o['temps_plein'], o['D'], o['U'], fin_t)
            mus[id(o)] = r0['mu']
        mu_glob = _r2(sum(mus.values())) if mus else 0.0
        pe = bool(d.get('premier_engagement')) and bool(trav.get('premier_engagement'))
        if not pe and any(o['reductions_fiches']['3315'] > 0 for o in ordinaires):
            alertes_t.append("Des fiches du trimestre contiennent une réduction « premier engagement » alors que ce travailleur "
                             "n'est pas (ou plus) désigné pour le premier engagement : recalcul trimestriel à 0, à régulariser.")
        for o in ordinaires:
            o['reductions'] = reductions_trimestre(
                o['W'], o['prestations'], o['temps_plein'], o['D'], o['U'], fin_t, mu_glob=mu_glob,
                mi_temps=o['Q'] >= o['U'] / 2, premier_engagement=pe, cotisations_reductibles=o['reductible_recalcul'])
            if o['a_determiner']:
                o['alertes'].append("Réductions recalculées sans les jours dont le code est à déterminer : à revoir une "
                                    "fois ces codes fixés.")

        # ── Tableaux a recopier ──
        tableaux = []
        for o in occupations:
            c = o['contrat']
            tableaux.append(_tableau(
                f"Ligne travailleur — code travailleur {o['code_travailleur']} · catégorie d'employeur "
                f"{d.get('categorie_employeur') or '000'}",
                ['Zone de la ligne d\'occupation', 'Valeur'],
                [['Date de début de l\'occupation', f"{c['date_debut']:%d/%m/%Y}"],
                 ['Date de fin', f"{c['date_fin']:%d/%m/%Y}" if c.get('date_fin') and c['date_fin'] <= fin_t else '—'],
                 ['Commission paritaire', _numero_cp(c['cp_key'])],
                 ['Jours par semaine du régime de travail', str(o['D'])],
                 ['Type de contrat', 'Temps plein' if o['temps_plein'] else 'Temps partiel'],
                 ['Heures par semaine du travailleur (Q)', nombre(o['Q'])],
                 ['Heures par semaine de la personne de référence (S)', nombre(o['U'])],
                 ['Statut', {'ouvrier': 'Ouvrier', 'employe': 'Employé', 'etudiant': 'Étudiant'}[o['statut']]
                  + f" — contrat {c.get('type_contrat') or ''}"],
                 ['Numéro d\'unité d\'établissement', d.get('numero_unite_etablissement') or 'à compléter']]))
            if o['etudiant']:
                tableaux.append(_tableau(
                    "Cotisation travailleur étudiant (bloc 90003)", ['Zone', 'Valeur'],
                    [['Rémunération de l\'étudiant', montant(o['W'])], ['Nombre d\'heures', nombre(o['heures_etudiant'])],
                     ['Cotisation de solidarité (recalcul sur le trimestre)', montant(o['cotisations_recalcul'])],
                     ['Cotisation de solidarité (somme des fiches)', montant(o['cotisations_fiches'])]],
                    note="Le contingent de 650 heures par an se contrôle sur Student@work."))
            else:
                lignes_p = [[str(k), LIBELLES_PRESTATION.get(k, ''), str(v['jours']),
                             '' if o['temps_plein'] else nombre(v['heures'])] for k, v in sorted(o['prestations'].items())]
                lignes_p += [['à déterminer', f"« {cj} » : {x['motif']}", str(x['jours']), '']
                             for cj, x in o['a_determiner'].items()]
                tableaux.append(_tableau(
                    "Prestations (bloc 90018)", ['Code', 'Nature', 'Jours', 'Heures'], lignes_p,
                    note=None if not o['temps_plein'] else "Temps plein : la déclaration se fait en jours uniquement."))
                tableaux.append(_tableau(
                    "Rémunérations (bloc 90019) — à 100 %, la DmfA applique elle-même les 108 % des ouvriers",
                    ['Code', 'Nature', 'Montant'],
                    [[str(k), {1: 'Rémunération liée aux prestations du trimestre', 2: 'Primes (fin d\'année, annuelle)'}[k],
                      montant(v)] for k, v in o['remunerations'].items() if v]))
            tableaux.append(_tableau(
                "Cotisations — contrôle de ce que la DmfA calcule", ['Code', 'Cotisation', 'Base', 'Taux', 'Recalcul trimestriel'],
                [[x[0], x[1], montant(x[2]), f"{x[3] * 100:.2f} %".replace('.', ','), montant(x[4])] for x in o['cotisations']]
                + [['', 'TOTAL — recalcul sur le trimestre', '', '', montant(o['cotisations_recalcul'])],
                   ['', 'TOTAL — somme des fiches', '', '', montant(o['cotisations_fiches'])],
                   ['', 'Écart', '', '', montant(_r2(o['cotisations_recalcul'] - o['cotisations_fiches']))]]
                + ([['856', 'Cotisation spéciale de sécurité sociale — à encoder vous-même', '', '', montant(o['css'])]]
                   if not o['etudiant'] else [])))
            if not o['etudiant']:
                r = o['reductions']
                detail = (f"W = {montant(r['W'])} ; " + ("J" if o['temps_plein'] else "H") + f" = {nombre(r['J'])} ; "
                          f"S = {montant(r['S'])} ; R = {montant(r['R'])} ; µ = {nombre(r['mu'])} ; µ(glob) = {nombre(r['mu_glob'])}"
                          if r['S'] is not None else "aucune prestation ou rémunération : pas de réduction")
                lignes_r = [['0001', 'Bonus à l\'emploi (ligne travailleur, total du trimestre)', montant(o['bonus']),
                             'calcul mensuel', ''],
                            ['3000', 'Réduction structurelle (ligne d\'occupation)', montant(o['reductions_fiches']['3000']),
                             montant(r['Ps']), montant(_r2(r['Ps'] - o['reductions_fiches']['3000']))]]
                if r['G'] is not None or o['reductions_fiches']['3315']:
                    lignes_r.append(['3315', "Premier engagement — 1er travailleur"
                                     + (f" (G = {montant(r['G'])})" if r['G'] is not None else " (travailleur non désigné)"),
                                     montant(o['reductions_fiches']['3315']), montant(r['Pg']),
                                     montant(_r2(r['Pg'] - o['reductions_fiches']['3315']))])
                tableaux.append(_tableau(
                    "Réductions", ['Code', 'Réduction', 'Somme des fiches', 'Recalcul trimestriel', 'Écart'], lignes_r,
                    note=detail + (" — plafonné aux cotisations réductibles" if r['plafonne'] else '')))
            for k in ('cotisations_recalcul',):
                tot['cot_recalcul'] += o[k]
            tot['cot_fiches'] += o['cotisations_fiches']; tot['css'] += o['css']; tot['bonus'] += o['bonus']
            tot['remu'] += o['W']; tot['double_pecule'] += o['double_pecule']
            tot['s_fiches'] += o['reductions_fiches']['3000']; tot['g_fiches'] += o['reductions_fiches']['3315']
            if not o['etudiant']:
                tot['s_recalcul'] += o['reductions']['Ps']; tot['g_recalcul'] += o['reductions']['Pg']
        # Fin de contrat: lignes des decomptes de sortie generes dans le trimestre (fin_contrat.py)
        for sortie in t.get('sorties') or []:
            lignes_s = []
            for x in _lire_json(sortie.get('dmfa')) or []:
                periode = ''
                if x.get('du') and x.get('au'):
                    periode = ' au '.join('/'.join(reversed(str(v)[:10].split('-'))) for v in (x['du'], x['au']))
                lignes_s.append([str(x['code_remuneration']), x['libelle'], periode, montant(_n(x['montant']))])
            if lignes_s:
                fin_s = '/'.join(reversed(str(sortie['date_fin'])[:10].split('-')))
                tableaux.append(_tableau(
                    f"Fin de contrat le {fin_s} — à déclarer en plus des lignes ci-dessus",
                    ['Code', 'Élément', 'Période couverte', 'Montant'], lignes_s,
                    note="Code 3 : indemnité de rupture, sur une ligne d'occupation séparée, avec les dates de la période "
                         "couverte (à scinder par trimestre et par année) ; ni réduction structurelle ni bonus à l'emploi. "
                         "Code 7 : pécule simple de sortie. Code 870 : double pécule de sortie, au niveau de l'employeur."))
        resultat.append({'nom': f"{trav.get('nom') or ''} {trav.get('prenom') or ''}".strip(), 'niss': trav.get('niss') or '',
                         'id': trav.get('id'), 'occupations': occupations, 'tableaux': tableaux,
                         'alertes': alertes_t + [a for o in occupations for a in o['alertes']]})

    tot = {k: _r2(v) for k, v in tot.items()}
    retenue_dp = _r2(_r2(tot['double_pecule'] * 85 / 92) * 0.1307)
    net_recalcul = _r2(tot['cot_recalcul'] + tot['css'] + retenue_dp - tot['bonus'] - tot['s_recalcul'] - tot['g_recalcul'])
    net_fiches = _r2(tot['cot_fiches'] + tot['css'] + retenue_dp - tot['bonus'] - tot['s_fiches'] - tot['g_fiches'])
    ligne = lambda lib, a, b: [lib, montant(a), montant(b), montant(_r2(b - a))]
    totaux = _tableau(
        "Totaux de l'employeur", ['', 'Somme des fiches', 'Recalcul trimestriel', 'Écart'],
        [ligne('Cotisations personnelles et patronales (avant réductions)', tot['cot_fiches'], tot['cot_recalcul']),
         ligne('Cotisation spéciale de sécurité sociale (856)', tot['css'], tot['css']),
         ligne('Double pécule des employés — retenue 13,07 % sur 85/92 (bloc 90002, code 870)', retenue_dp, retenue_dp),
         ligne('Bonus à l\'emploi (0001)', -tot['bonus'], -tot['bonus']),
         ligne('Réduction structurelle (3000)', -tot['s_fiches'], -tot['s_recalcul']),
         ligne('Premier engagement (3315)', -tot['g_fiches'], -tot['g_recalcul']),
         ligne('MONTANT NET DÛ À L\'ONSS', net_fiches, net_recalcul)],
        note="Le recalcul trimestriel est le chiffre à comparer à la DmfA web ; la somme des fiches est ce qui a été "
             "retenu et provisionné mois par mois.")
    designes = [t['travailleur'] for t in travailleurs if t['travailleur'].get('premier_engagement')]
    if d.get('premier_engagement') and not designes:
        alertes.append("Premier engagement : le dossier ouvre le droit, mais aucun travailleur n'est désigné — réduction 3315 "
                       "non calculée. Cochez la case dans la fiche du travailleur qui ouvre le droit.")
    elif len(designes) > 1:
        alertes.append("Premier engagement : plusieurs travailleurs désignés (" + ', '.join(
            f"{x.get('prenom') or ''} {x.get('nom') or ''}".strip() for x in designes)
            + ") — un seul peut l'être ; les 2e à 6e travailleurs (codes 3324 et suivants) ne sont pas gérés.")
    elif designes and not d.get('premier_engagement'):
        alertes.append("Premier engagement : un travailleur est désigné, mais la case du dossier n'est pas cochée — "
                       "réduction 3315 non calculée.")
    if not resultat:
        alertes.append("Aucun travailleur avec un contrat ou une fiche de paie dans ce trimestre.")
    return {
        'type': 'aide_dmfa', 'titre': f"Aide à la DmfA — {annee}/{trimestre}", 'annee': annee, 'trimestre': trimestre,
        'periode': (debut_t, fin_t),
        'entete': [('Employeur', d.get('nom') or ''), ('N° ONSS', d.get('rsz') or ''), ('N° d\'entreprise', d.get('bce') or ''),
                   ('Trimestre', f"{annee}/{trimestre}"), ('Catégorie d\'employeur', d.get('categorie_employeur') or '000'),
                   ('Code d\'importance', str(d.get('code_importance') or 'non renseigné')),
                   ('Code FFE', d.get('code_ffe') or 'non renseigné'),
                   ('Unité d\'établissement', d.get('numero_unite_etablissement') or 'à compléter')],
        'alertes': alertes, 'travailleurs': resultat, 'totaux': totaux,
        'donnees_totaux': dict(tot, retenue_double_pecule=retenue_dp, net_recalcul=net_recalcul, net_fiches=net_fiches),
        'source': "Instructions administratives ONSS 2026/3 — aide à l'encodage : ce document n'est pas une déclaration.",
    }


# ─────────────────────────────────────────────────────────────────
# NUMERO D'UNITE D'ETABLISSEMENT (BCE)
# ─────────────────────────────────────────────────────────────────
def normaliser_unite_etablissement(valeur):
    """Format BCE d'une unite d'etablissement: 2.xxx.xxx.xxx (10 chiffres, le premier
    de 2 a 8). Retourne (numero formate ou None si vide, erreur ou None)."""
    brut = (valeur or '').strip()
    if not brut:
        return None, None
    chiffres = ''.join(ch for ch in brut if ch.isdigit())
    if len(chiffres) != 10 or chiffres[0] not in '2345678' or any(ch not in '0123456789. ' for ch in brut):
        return None, f"Numéro d'unité d'établissement « {brut} » invalide : format attendu 2.xxx.xxx.xxx (10 chiffres)."
    return f"{chiffres[0]}.{chiffres[1:4]}.{chiffres[4:7]}.{chiffres[7:]}", None
