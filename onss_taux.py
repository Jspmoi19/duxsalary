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
        _CACHE[cle] = json.load(open(os.path.join(DOSSIER, f"{cle}.json")))
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


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == 'importer':
        cle, rapport = importer(sys.argv[2])
        print(f"Trimestre {cle} importe. Differences:")
        for l in rapport:
            print("  -", l)
    else:
        print(__doc__)
