# -*- coding: utf-8 -*-
"""
cheques_regles.py -- DuxSalary
Obligations sectorielles CHEQUES-REPAS et ECOCHEQUES par CP, datees et sourcees,
+ calcul des quantites a commander.

Sources verifiees le 30/09/2026 (croisement de plusieurs sources par CP):
- CP 200 ecocheques + prime annuelle: CGSLB "CP 200 conditions de travail",
  CSC-CNE (06/2026), SETCa, Acerta (CCT du 9 juin 2016, MB 14/02/2017), UCM.
- CP 140.03: protocole d'accord 2025-2026 du 18/12/2025 (FGTB-UBT, Synova,
  CGSLB), easypay (ecocheques personnel non roulant/garage).
- CP 121: accord sectoriel 2025-2026 (CGSLB x2, CSC, ACCG primes 01/07/2026).
- CP 336: accord sectoriel 2025-2026 (SSN, Securex): aucune obligation.
- Cadre legal commun 2026: cheque-repas max 10 EUR (8,91 employeur, min 1,09
  travailleur); ecocheques max 250 EUR/an, valeur faciale max 10 EUR.

Principe: l'outil ne DECIDE rien a la place de l'utilisateur. Il affiche la
regle applicable (selon la CP, l'anciennete, l'historique de l'employeur et
le type de personnel), signale une obligation non respectee et calcule les
quantites a commander.
"""
import math
from datetime import date

CADRE_LEGAL = {
    'repas_valeur_max': 10.00,
    'repas_part_patronale_max': 8.91,
    'repas_part_travailleur_min': 1.09,
    'eco_max_annuel': 250.00,
    'eco_valeur_faciale_max': 10.00,
}

# ─────────────────────────────────────────────────────────────────
# REGLES PAR CP (chaque regle a une periode de validite)
# ─────────────────────────────────────────────────────────────────
REGLES_CHEQUES = {
    'CP 200': {
        'repas': [],   # aucune obligation sectorielle trouvee
        'eco': [{
            'du': date(2010, 1, 1), 'au': None,
            'montants_par_regime': [(0.8, 250.0), (0.6, 200.0), (0.5, 150.0), (0.0, 100.0)],
            'mois_paiement': 6,
            'periode_reference': 'du 1er juin N-1 au 31 mai N',
            'prorata': "au prorata des prestations en cas d'entree/sortie en cours de periode",
            'convertible': "convertible en avantage equivalent si accord conclu au plus tard le 31/10 de l'annee precedente",
            'source': 'CCT CP 200 du 09/06/2016 (MB 14/02/2017); CGSLB, CSC-CNE, SETCa, Acerta',
        }],
        'autres': ["Prime annuelle 330,84 EUR brut (2026) payee en juin, meme periode de reference que les ecocheques.",
                   "Prime de fin d'annee (13e mois) en decembre, minimum 6 mois d'anciennete."],
    },
    'CP 140.03': {
        'repas': [{
            'du': date(2026, 7, 1), 'au': None,
            'mode': 'jours',
            'valeur_introduction': 3.09, 'part_patronale_introduction': 2.00, 'part_travailleur': 1.09,
            'augmentation_si_existant': 2.00, 'existant_avant': date(2025, 1, 1),
            'anciennete_min_mois': 6, 'statuts': ('ouvrier',),
            'alternative': "ou indemnite de repas pour chaque jour travaille d'au moins 4 heures (au choix de l'employeur)",
            'source': "Protocole d'accord CP 140.03 2025-2026 du 18/12/2025 (FGTB-UBT, Synova, CGSLB)",
        }],
        'eco': [{
            'du': date(2016, 1, 1), 'au': None,
            'montant_temps_plein': 200.0, 'mois_paiement': 12,
            'personnel': ('non_roulant', 'garage'),
            'condition': "uniquement si l'employeur n'octroyait ni cheques-repas ni ecocheques au 01/01/2016",
            'convertible': 'remplacables par des cheques-repas depuis le 01/01/2022',
            'source': 'easypay-group (indexations CP 140.03.02), CGSLB, Synova',
        }],
        'autres': ["Le personnel roulant n'est pas vise par les ecocheques sectoriels."],
    },
    'CP 121': {
        'repas': [{
            'du': date(2026, 1, 1), 'au': date(2027, 12, 31),
            'mode': 'heures_7_4',
            'valeur_introduction': 3.09, 'part_patronale_introduction': 2.00, 'part_travailleur': 1.09,
            'augmentation_si_existant': 2.00, 'existant_avant': date(2026, 1, 1),
            'anciennete_min_mois': 0, 'statuts': ('ouvrier', 'employe'),
            'calcul': "heures prestees / 7,4 arrondi a l'unite superieure, maximum = jours ouvrables d'un temps plein",
            'source': 'Accord sectoriel CP 121 2025-2026 (CGSLB, CSC, ACCG)',
        }],
        'eco': [],
        'autres': ["Accord valable pour 2026-2027 : a reverifier pour 2028."],
    },
    'CP 336': {'repas': [], 'eco': [], 'autres': ["Aucune obligation sectorielle de cheques-repas ni d'ecocheques (accord 2025-2026)."]},
}


def _regle_active(liste, d):
    for r in liste:
        if r['du'] <= d and (r['au'] is None or d <= r['au']):
            return r
    return None


def regles_pour(cp_key, d=None):
    """Regles repas / eco en vigueur a la date d pour une CP."""
    d = d or date.today()
    reg = REGLES_CHEQUES.get(cp_key)
    if reg is None:
        return {'connue': False, 'repas': None, 'eco': None, 'autres': []}
    return {'connue': True, 'repas': _regle_active(reg['repas'], d),
            'eco': _regle_active(reg['eco'], d), 'autres': reg.get('autres', [])}


def mois_entre(debut, fin):
    return (fin.year - debut.year) * 12 + (fin.month - debut.month)


def jours_ouvrables(annee, mois):
    import calendar
    n = calendar.monthrange(annee, mois)[1]
    return sum(1 for j in range(1, n + 1) if date(annee, mois, j).weekday() < 5)


def cheques_repas_du_mois(cp_key, statut, annee, mois, jours_prestes, heures_prestees,
                           date_anciennete, config):
    """Calcule les cheques-repas d'un travailleur pour un mois.
    config: parametres du dossier (actif, valeur, part_patronale, part_travailleur,
            octroi_avant_2025). Retourne un dict avec la regle et le calcul."""
    fin_mois = date(annee, mois, 28)
    regle = regles_pour(cp_key, fin_mois)['repas']
    res = {'obligatoire': False, 'eligible': True, 'motif': '', 'regle': regle,
           'nombre': 0, 'valeur': 0.0, 'part_patronale': 0.0, 'part_travailleur': 0.0}

    # Valeurs par defaut: celles du dossier, sinon la regle sectorielle
    valeur = float(config.get('valeur') or 0)
    pp = float(config.get('part_patronale') or 0)
    pt = float(config.get('part_travailleur') or 0)

    if regle:
        if statut not in regle['statuts'] or statut == 'etudiant':
            res.update(eligible=False, motif=f"Obligation sectorielle limitee aux statuts: {', '.join(regle['statuts'])}.")
        else:
            anc = mois_entre(date_anciennete, fin_mois) if date_anciennete else 0
            if anc < regle['anciennete_min_mois']:
                res.update(eligible=False,
                           motif=f"Anciennete {anc} mois < {regle['anciennete_min_mois']} mois requis : pas encore obligatoire.")
            else:
                res['obligatoire'] = True
                if config.get('octroi_avant_2025'):
                    res['motif'] = (f"Cheques deja octroyes avant le {regle['existant_avant']:%d/%m/%Y} : "
                                    f"part patronale a augmenter de {regle['augmentation_si_existant']:.2f} EUR.")
                else:
                    res['motif'] = (f"Introduction : {regle['valeur_introduction']:.2f} EUR "
                                    f"({regle['part_patronale_introduction']:.2f} employeur + {regle['part_travailleur']:.2f} travailleur).")
                    if not valeur:
                        valeur, pp, pt = (regle['valeur_introduction'], regle['part_patronale_introduction'],
                                          regle['part_travailleur'])

    if not config.get('actif') and not res['obligatoire']:
        return res
    if not res['eligible'] and not config.get('actif'):
        return res

    # Nombre de cheques
    if regle and regle['mode'] == 'heures_7_4':
        nb = math.ceil((heures_prestees or 0) / 7.4) if heures_prestees else 0
        nb = min(nb, jours_ouvrables(annee, mois))
    else:
        nb = int(jours_prestes or 0)
    res.update(nombre=nb, valeur=round(valeur, 2), part_patronale=round(pp, 2), part_travailleur=round(pt, 2),
               total_valeur=round(nb * valeur, 2), total_patronal=round(nb * pp, 2),
               total_travailleur=round(nb * pt, 2))
    # Controle du cadre legal
    alertes = []
    if pp > CADRE_LEGAL['repas_part_patronale_max'] + 1e-9:
        alertes.append(f"Part patronale {pp:.2f} > maximum legal {CADRE_LEGAL['repas_part_patronale_max']:.2f} EUR.")
    if valeur and pt < CADRE_LEGAL['repas_part_travailleur_min'] - 1e-9:
        alertes.append(f"Part travailleur {pt:.2f} < minimum legal {CADRE_LEGAL['repas_part_travailleur_min']:.2f} EUR.")
    if regle and res['obligatoire'] and not config.get('octroi_avant_2025') and pp + 1e-9 < regle['part_patronale_introduction']:
        alertes.append(f"Part patronale {pp:.2f} inferieure au minimum sectoriel {regle['part_patronale_introduction']:.2f} EUR.")
    res['alertes'] = alertes
    return res


def ecocheques_annuels(cp_key, statut, annee, fraction_regime, mois_dans_periode,
                        categorie_personnel=None):
    """Montant d'ecocheques du a la date de paiement de l'annee `annee`.
    fraction_regime: regime de travail (1.0 = temps plein, 0.5 = mi-temps...)
    mois_dans_periode: mois prestes dans la periode de reference (0-12)."""
    regle = regles_pour(cp_key, date(annee, 6, 30))['eco']
    if not regle or statut == 'etudiant':
        return {'du': False, 'regle': regle, 'montant': 0.0, 'motif': 'Aucune obligation sectorielle.' if not regle else 'Etudiant : non vise.'}
    if 'personnel' in regle:
        if categorie_personnel not in regle['personnel']:
            return {'du': False, 'regle': regle, 'montant': 0.0,
                    'motif': (f"Vise uniquement le personnel {' / '.join(regle['personnel'])} "
                              f"(type actuel : {categorie_personnel or 'non renseigne'}). "
                              f"Condition : {regle['condition']}.")}
        base = regle['montant_temps_plein']
    else:
        base = next(m for seuil, m in regle['montants_par_regime'] if fraction_regime >= seuil)
    mois = max(0, min(12, mois_dans_periode))
    montant = round(base * mois / 12, 2)
    return {'du': montant > 0, 'regle': regle, 'montant': montant, 'montant_plein': base,
            'mois_paiement': regle['mois_paiement'],
            'motif': f"{base:.0f} EUR pour une periode complete, x {mois}/12 mois (prorata approche par mois).",
            'nombre_cheques_10': int(montant // CADRE_LEGAL['eco_valeur_faciale_max']),
            'reste': round(montant % CADRE_LEGAL['eco_valeur_faciale_max'], 2)}
