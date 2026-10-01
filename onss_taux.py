# -*- coding: utf-8 -*-
"""
onss_taux.py — DuxSalary
Taux ONSS officiels, VERSIONNES PAR TRIMESTRE, issus des fichiers TechLib
("Fichiers des taux au format XML", socialsecurity.be).

Principe:
- Chaque trimestre importe = un fichier onss_trimestres/AAAAQ.json.
  Rien n'est jamais supprime: une fiche de septembre 2026 utilise toujours
  2026Q3, meme apres l'import du 2026Q4.
- Si un trimestre n'est pas encore publie (debut de trimestre), on utilise
  le dernier trimestre disponible ET on le signale (parametres "reportes").
  Regle validee par l'utilisateur: on avance avec les anciens taux, les
  ecarts eventuels se regularisent via la DmfA.
- Une republication du meme trimestre (ex: version "sous-reserve" puis
  definitive) remplace le JSON du trimestre, l'ancienne version est archivee
  dans onss_trimestres/archives/ avec sa date de creation ONSS.

Import d'un nouveau trimestre (sur le serveur):
    python3 onss_taux.py importer /chemin/dmfa_rate_2026_4.zip
"""
import json, os, sys, zipfile, shutil, xml.etree.ElementTree as ET
from datetime import date

DOSSIER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'onss_trimestres')

# Codes DmfA utilises par DuxSalary, categorie employeur 000 (secteur prive
# general) par defaut. Sources: fichiers de taux 2026/2 et 2026/3 +
# Instructions administratives ONSS 2026/3.
CODE_TRAVAILLEUR = {'ouvrier': '015', 'employe': '495', 'etudiant': '840'}
CODE_VACANCES_OUVRIERS = '253'   # cotisation trimestrielle vacances annuelles (depuis 2024/1)
CATEGORIE_DEFAUT = '000'

# Cotisation ANNUELLE vacances ouvriers: percue par avis de debit annuel
# (avec le 1er trimestre de l'annee suivante), PAS dans les fichiers de taux
# trimestriels. Source: Instructions ONSS 2026/3 ("5,57 % est ajoute a la
# cotisation patronale de base ... et 10,27 % est percu via un avis de debit
# annuel"; total 15,84 % des remunerations a 108 %).
VACANCES_OUVRIERS_ANNUELLE = {2026: 0.1027}


def _lire(xml_bytes, tag):
    rows = []
    root = ET.fromstring(xml_bytes)
    header = {c.tag: (c.text or '').strip() for c in root.find('Header')}
    for el in root.iter(tag):
        rows.append({c.tag: (c.text or '').strip() for c in el})
    return header, rows


def importer(chemin_zip):
    """Importe un ZIP TechLib -> onss_trimestres/AAAAQ.json. Retourne le
    rapport de differences par rapport au trimestre precedent disponible."""
    os.makedirs(DOSSIER, exist_ok=True)
    with zipfile.ZipFile(chemin_zip) as z:
        noms = z.namelist()
        def trouver(prefixe):
            return next(n for n in noms if n.startswith(prefixe) and n.endswith('.xml'))
        h, cotis = _lire(z.read(trouver('NOSSContributionRate_')), 'ContributionRate')
        _, deduc = _lire(z.read(trouver('NOSSDeductionRate_')), 'DeductionRate')
        _, comb = _lire(z.read(trouver('NOSSWorkerAndContributionComb_')), 'WorkerAndContributionComb')
    q = h['Quarter']                      # ex: '20263'
    cle = f"{q[:4]}Q{q[4]}"               # ex: '2026Q3'
    data = {
        'trimestre': cle,
        'date_creation_onss': h.get('FormCreationDate'),
        'date_import': date.today().isoformat(),
        'source': f"TechLib ONSS - {os.path.basename(chemin_zip)}",
        'cotisations': cotis, 'deductions': deduc, 'combinaisons': comb,
    }
    cible = os.path.join(DOSSIER, f"{cle}.json")
    ancien = None
    if os.path.exists(cible):
        ancien = json.load(open(cible))
        os.makedirs(os.path.join(DOSSIER, 'archives'), exist_ok=True)
        shutil.copy(cible, os.path.join(DOSSIER, 'archives',
                    f"{cle}_{ancien.get('date_creation_onss', 'inconnu')}.json"))
    json.dump(data, open(cible, 'w'))
    _CACHE.pop(cle, None)
    reference = ancien or _precedent(cle)
    return cle, rapport_differences(reference, data) if reference else ["Premier trimestre importe."]


def rapport_differences(a, b):
    """Differences sur les taux (categorie defaut) entre deux versions."""
    def index(d):
        return {(r.get('EmployerClass'), r.get('ContributionWorkerCode') or r.get('WorkerCode'),
                 r.get('ContributionType')): r for r in d['cotisations']}
    ia, ib = index(a), index(b)
    lignes = []
    for k in sorted(set(ia) | set(ib), key=lambda x: tuple(v or '' for v in x)):
        if k[0] != CATEGORIE_DEFAUT:
            continue
        ra, rb = ia.get(k), ib.get(k)
        champs = ('PersonalRate', 'EmployerRate', 'SalaryModerationRate', 'TotalRate')
        if ra is None:
            lignes.append(f"NOUVEAU code {k[1]} type {k[2]}: " + ', '.join(f"{c}={rb.get(c)}" for c in champs))
        elif rb is None:
            lignes.append(f"SUPPRIME code {k[1]} type {k[2]}")
        else:
            diff = [f"{c}: {ra.get(c)} -> {rb.get(c)}" for c in champs if ra.get(c) != rb.get(c)]
            if diff:
                lignes.append(f"MODIFIE code {k[1]} type {k[2]}: " + '; '.join(diff))
    return lignes or [f"Aucune difference sur la categorie {CATEGORIE_DEFAUT}."]


_CACHE = {}

def _disponibles():
    if not os.path.isdir(DOSSIER):
        return []
    return sorted(f[:-5] for f in os.listdir(DOSSIER) if f.endswith('.json'))

def _charger(cle):
    if cle not in _CACHE:
        _CACHE[cle] = json.load(open(os.path.join(DOSSIER, f"{cle}.json"), encoding='utf-8'))
    return _CACHE[cle]

def _precedent(cle):
    avant = [c for c in _disponibles() if c < cle]
    return _charger(avant[-1]) if avant else None

def trimestre_de(d):
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"


def get_taux_onss(statut, reference_date, categorie=CATEGORIE_DEFAUT):
    """Taux ONSS du trimestre de reference_date pour un statut.
    Retourne un dict avec les taux ET la tracabilite (trimestre utilise,
    report eventuel). Leve une erreur si aucun trimestre anterieur n'existe."""
    voulu = trimestre_de(reference_date)
    dispo = [c for c in _disponibles() if c <= voulu]
    if not dispo:
        raise ValueError(f"Aucun fichier de taux ONSS pour {voulu} ni avant "
                         f"(disponibles: {_disponibles()}). Importer le fichier TechLib.")
    utilise = dispo[-1]
    data = _charger(utilise)
    code = CODE_TRAVAILLEUR[statut]

    def ligne(code_cot):
        for r in data['cotisations']:
            if r.get('EmployerClass') == categorie and \
               (r.get('ContributionWorkerCode') == code_cot or
                (not r.get('ContributionWorkerCode') and r.get('WorkerCode') == code_cot)):
                return r
        return None

    base = ligne(code)
    if base is None:
        raise ValueError(f"Code travailleur {code} absent du fichier {utilise} "
                         f"pour la categorie {categorie}.")
    res = {
        'trimestre_demande': voulu,
        'trimestre_utilise': utilise,
        'parametres_reportes': utilise != voulu,
        'date_creation_onss': data.get('date_creation_onss'),
        'categorie': categorie,
        'code_travailleur': code,
        'personnel': float(base['PersonalRate']) / 100,
        'patronal_base': float(base['EmployerRate']) / 100,
        'moderation_salariale': float(base.get('SalaryModerationRate') or 0) / 100,
        'vacances_trimestrielle': 0.0,
        'vacances_annuelle': 0.0,
    }
    if statut == 'ouvrier':
        vac = ligne(CODE_VACANCES_OUVRIERS)
        res['vacances_trimestrielle'] = float(vac['EmployerRate']) / 100 if vac else 0.0
        res['vacances_annuelle'] = VACANCES_OUVRIERS_ANNUELLE.get(reference_date.year, 0.0)
    return res


def categorie_existe(categorie, reference_date=None):
    """Verifie qu'une categorie employeur existe dans le fichier de taux du
    trimestre (ou du dernier disponible). Utilise a l'enregistrement du
    dossier pour refuser une categorie mal encodee."""
    ref = reference_date or date.today()
    voulu = trimestre_de(ref)
    dispo = [c for c in _disponibles() if c <= voulu] or _disponibles()
    if not dispo:
        return False
    data = _charger(dispo[-1])
    return any(r.get('EmployerClass') == categorie for r in data['cotisations'])


# ─────────────────────────────────────────────────────────────────
# COTISATIONS PATRONALES COMPLEMENTAIRES (non couvertes par les reductions)
# ─────────────────────────────────────────────────────────────────
# Regles officielles (Instructions administratives ONSS 2026/3 + legende de
# la feuille "comb" du fichier des taux):
#   810 FFE speciale   : due par TOUS les employeurs, pour tout travailleur
#                        soumis au chomage (donc pas les etudiants) - p.343
#   809 FFE de base    : employeur commercial (code FFE "C")
#   811 FFE de base    : employeur non commercial (code FFE "B")
#                        codes FFE N / O: pas de FFE de base - p.342
#   855 cotisation 1,60% : employeurs de code d'importance 3 a 9
#   Fonds sectoriels (codes 820-839) : dus si la combinaison categorie/code
#                        travailleur porte le renvoi (1) = "due, sauf apprentis
#                        de plus de 18 ans" -- ex. 831 Fonds social CP 200 (cat. 010)
# La reduction structurelle et le premier engagement NE s'appliquent PAS a ces
# cotisations (Instructions p.376: pas sur le FFE ni sur la moderation du 1,60%).
#   255 accidents du travail (cot. speciale) 0,02% : employeurs soumis a la loi
#                        du 10/04/1971 - p.340
#   256 Fonds amiante 0,01% : tous les employeurs, certains trimestres - p.340-341
#   859 chomage temporaire et chomeurs ages 0,10% : tous les employeurs sauf
#                        secteur public / enseignement / dispenses - p.346
#   Ces trois cotisations se calculent sur le brut porte a 108% pour les ouvriers,
#   sont declarees par ligne travailleur (hors taux de base depuis 2024/1 pour
#   255 et 256) et n'entrent pas dans le plafond des reductions.
# Fonds amiante: "a partir de 2017 la cotisation est uniquement percue pour le
# 1er et le 2eme trimestre, excepte si determine autrement par le Roi" ;
# "pour 2026 la cotisation est percue pour le 1er, le 2eme et le 3eme trimestre"
# (Instructions ONSS 2026/3 p.340-341). Ajouter ici chaque annee derogatoire.
FONDS_AMIANTE_TRIMESTRES_DEFAUT = (1, 2)
FONDS_AMIANTE_TRIMESTRES = {2026: (1, 2, 3)}

def fonds_amiante_du(reference_date):
    """La cotisation Fonds amiante (256) est-elle percue pour ce trimestre ?
    Decide sur le trimestre de la PERIODE, pas sur le fichier de taux utilise
    (un trimestre non publie reprend le fichier precedent)."""
    trimestre = (reference_date.month - 1) // 3 + 1
    return trimestre in FONDS_AMIANTE_TRIMESTRES.get(reference_date.year, FONDS_AMIANTE_TRIMESTRES_DEFAUT)

_LIBELLES = None

def libelle_code(code):
    global _LIBELLES
    if _LIBELLES is None:
        p = os.path.join(DOSSIER, 'libelles_codes.json')
        _LIBELLES = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {'cotisations': {}, 'reductions': {}}
    return _LIBELLES['cotisations'].get(str(code), f"Cotisation code {code}")


def cotisations_complementaires(statut, reference_date, categorie=CATEGORIE_DEFAUT,
                                 code_ffe=None, code_importance=None):
    """Liste des cotisations patronales complementaires dues pour ce statut.
    Chaque element: code, type, libelle, taux (fraction, moderation incluse),
    reductible (toujours False), source, a_verifier.
    code_ffe / code_importance: donnees du dossier (Repertoire des employeurs).
    S'ils ne sont pas renseignes, seules les cotisations certaines sont
    appliquees et un avertissement est renvoye."""
    avert = []
    if statut == 'etudiant':
        return [], avert   # etudiant: cotisation de solidarite uniquement
    voulu = trimestre_de(reference_date)
    dispo = [c for c in _disponibles() if c <= voulu]
    if not dispo:
        return [], [f"Aucun fichier de taux pour {voulu}."]
    data = _charger(dispo[-1])
    code_trav = CODE_TRAVAILLEUR[statut]

    def taux(code, type_cot='0'):
        for r in data['cotisations']:
            if r.get('EmployerClass') == categorie and r.get('ContributionWorkerCode') == code \
               and r.get('ContributionType') == type_cot:
                return float(r.get('TotalRate') or 0) / 100
        return None

    comb = {r.get('ContributionWorkerCode'): r.get('OwednessCode')
            for r in data['combinaisons']
            if r.get('EmployerClass') == categorie and r.get('WorkerCode') == code_trav}
    res = []

    def ajouter(code, type_cot, source, a_verifier=False):
        t = taux(code, type_cot)
        if t is None:
            avert.append(f"Code {code} type {type_cot} absent du fichier {dispo[-1]} (categorie {categorie}).")
            return
        res.append({'code': code, 'type': type_cot, 'libelle': libelle_code(code),
                    'taux': t, 'reductible': False, 'source': source, 'a_verifier': a_verifier})

    # 810 FFE speciale -- tous les employeurs
    if code_ffe != 'O' and '810' in comb:
        ajouter('810', '0', "Instructions ONSS 2026/3 p.343: due par tous les employeurs")

    # 255 cotisation speciale accidents du travail -- employeurs soumis a la loi
    # du 10/04/1971 (secteur prive), 0,02% du brut (108% ouvriers)
    if '255' in comb:
        ajouter('255', '0', "Instructions ONSS 2026/3 p.340: employeurs soumis à la loi sur les accidents du travail ; "
                            "hors taux de base depuis 2024/1")
    # 256 Fonds amiante -- tous les employeurs, 0,01% du brut (108% ouvriers),
    # mais seulement certains trimestres (voir FONDS_AMIANTE_TRIMESTRES)
    if '256' in comb and fonds_amiante_du(reference_date):
        ajouter('256', '0', "Instructions ONSS 2026/3 p.340-341: tous les employeurs ; "
                            "perçue aux trimestres 1 à 3 en 2026")
    # 859 chomage temporaire et chomeurs ages -- tous les employeurs du secteur
    # prive, 0,10% du brut (108% ouvriers). Les employeurs dispenses par le
    # Ministre de l'Emploi (type 8, taux 0%) ne sont pas geres: cas a signaler.
    if '859' in comb:
        ajouter('859', '0', "Instructions ONSS 2026/3 p.346: tous les employeurs, sauf secteur public, "
                            "enseignement et employeurs dispensés")

    # 809 / 811 FFE de base selon le code FFE du dossier
    imp = int(code_importance) if str(code_importance or '').isdigit() else None
    if code_ffe == 'C':
        if imp is not None and imp > 3:
            ajouter('809', '5', "Instructions ONSS p.342: commercial, code d'importance > 3", a_verifier=True)
        else:
            ajouter('809', '0', "Instructions ONSS p.342: employeur commercial (FFE C), code d'importance <= 3")
    elif code_ffe == 'B':
        ajouter('811', '0', "Instructions ONSS p.342: employeur non commercial (FFE B)")
    elif code_ffe in (None, ''):
        avert.append("Code FFE non renseigne dans le dossier: FFE de base (809/811) non calcule.")

    # 855 cotisation 1,60% -- codes d'importance 3 a 9
    if imp is not None and 3 <= imp <= 9 and '855' in comb:
        ajouter('855', '0', "Fichier des taux: employeurs de code d'importance 3 a 9")
    elif imp is None:
        avert.append("Code d'importance non renseigne: cotisation 1,60% (employeurs >= 10 travailleurs) non verifiee.")

    # Fonds sectoriels propres a la categorie (renvoi (1) = du)
    for code, owed in sorted(comb.items()):
        if code and '820' <= code <= '839' and owed == '1':
            ajouter(code, '0', f"Fichier des taux: due pour la categorie {categorie} (renvoi 1)")
    return res, avert


# ─────────────────────────────────────────────────────────────────
# LISTES POUR LES MENUS DEROULANTS DU DOSSIER
# ─────────────────────────────────────────────────────────────────
# Code d'importance -- source: BCSS Datawarehouse, variable "Code d'importance"
# (ONSS). Codes 5 a 8: grille habituelle, non reprise explicitement dans la source.
CODES_IMPORTANCE = [
    ('0', 'Indéfini'),
    ('1', 'Moins de 5 travailleurs'),
    ('2', '5 à 9 travailleurs'),
    ('3', '10 à 19 travailleurs'),
    ('4', '20 à 49 travailleurs'),
    ('5', '50 à 99 travailleurs'),
    ('6', '100 à 199 travailleurs'),
    ('7', '200 à 499 travailleurs'),
    ('8', '500 à 999 travailleurs'),
    ('9', 'Plus de 1.000 travailleurs'),
]
# Code FFE -- Instructions administratives ONSS 2026/3 p.342-343
CODES_FFE = [
    ('C', 'C — Commercial / industriel : redevable du FFE de base (809)'),
    ('B', 'B — Non commercial (ASBL, professions libérales…) : FFE de base (811)'),
    ('N', 'N — Exclu du FFE de base (catégorie pourtant redevable)'),
    ('O', 'O — Catégorie exclue du FFE de base'),
]
_CACHE_CATEGORIES = {}
# Noms courts des fonds sectoriels, d'apres les libelles officiels (feuille comb)
NOMS_FONDS = {
    '820': "FSE ouvriers (108 %)", '825': "Pension sectorielle ouvriers",
    '826': "FSE ouvriers (forfait)", '827': "Pension sectorielle ouvriers (forfait)",
    '830': "FSE employés", '831': "Fonds social CP 200", '832': "Fonds social CP 201",
    '833': "Fonds social socio-culturel (CP 329.02)", '835': "Pension sectorielle employés",
    '836': "FSE employés (forfait)", '837': "Pension sectorielle employés (forfait)",
}

def liste_categories(reference_date=None):
    """Toutes les categories employeur du fichier de taux, avec une description
    GENEREE a partir des donnees officielles: fonds sectoriels propres
    (codes 820-839 dus) et taux de base particuliers. Le fichier ONSS ne
    fournit pas de libelle de categorie (annexe 27 non disponible)."""
    import re
    ref = reference_date or date.today()
    dispo = [c for c in _disponibles() if c <= trimestre_de(ref)] or _disponibles()
    if not dispo:
        return []
    cle = dispo[-1]
    if cle in _CACHE_CATEGORIES:
        return _CACHE_CATEGORIES[cle]
    data = _charger(cle)
    bases, fonds = {}, {}
    taux_idx = {}
    for r in data['cotisations']:
        cat, code = r.get('EmployerClass'), r.get('ContributionWorkerCode')
        if code in ('015', '495'):
            bases.setdefault(cat, set()).add((r.get('EmployerRate'), r.get('SalaryModerationRate')))
        if code and r.get('ContributionType') == '0':
            taux_idx[(cat, code)] = r.get('TotalRate')
    for r in data['combinaisons']:
        code = r.get('ContributionWorkerCode') or ''
        if '820' <= code <= '839' and r.get('OwednessCode') == '1' and r.get('WorkerCode') in ('015', '495'):
            fonds.setdefault(r.get('EmployerClass'), set()).add(code)
    res = []
    for cat in sorted(set(bases) | set(fonds) | {r.get('EmployerClass') for r in data['cotisations']}):
        morceaux = []
        for code in sorted(fonds.get(cat, [])):
            nom = NOMS_FONDS.get(code, f"Cotisation {code}")
            t = taux_idx.get((cat, code))
            morceaux.append(f"{nom} {t} %" if t else nom)
        b = bases.get(cat, set())
        if b and b != {('19.88', '5.12')}:
            e, m = sorted(b)[0]
            morceaux.insert(0, f"taux de base {e} % + {m} %")
        if cat == '000':
            desc = 'Secteur privé général' + (' — ' + ', '.join(morceaux) if morceaux else '')
        else:
            desc = ', '.join(morceaux) if morceaux else 'Taux de base général, sans fonds sectoriel propre'
        res.append({'code': cat, 'description': desc})
    _CACHE_CATEGORIES[cle] = res
    return res


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == 'importer':
        cle, rapport = importer(sys.argv[2])
        print(f"Trimestre {cle} importe. Differences:")
        for l in rapport:
            print("  -", l)
    else:
        print(__doc__)
