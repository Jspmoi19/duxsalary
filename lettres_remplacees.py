# -*- coding: utf-8 -*-
"""
lettres_remplacees.py -- DuxSalary
Une seule lettre ONSS ACTIVE par dossier et par periode (mois, annee) -- meme logique
que les fiches de paie remplacees (fiches_remplacees.py).

Quand une lettre est regeneree, l'ancienne passe au statut « remplacee »
(lettres_onss.remplacee_par = id de la nouvelle lettre, remplacee_le = date). Son PDF
est conserve (jamais ecrase) et elle reste visible, grisee, dans l'historique ONSS avec
« Remplacée par la lettre du … » ; seule la lettre active porte les montants a payer.
Aucune mention de paiement: l'outil ne sait pas si une ancienne lettre a ete payee.

Doublons deja presents en base:
    python3 lettres_remplacees.py              -> affiche la liste, NE MODIFIE RIEN
    python3 lettres_remplacees.py --appliquer  -> garde la plus recente comme active,
                                                 marque les autres « remplacee »
Colonnes: python3 migrate_charges.py (a lancer avant).
"""
import sys

LETTRES_ACTIVES = "remplacee_par IS NULL"
MOIS = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']


def cle_lettre(l):
    return (l['dossier_id'], l['annee'], l['mois'])


def _ordre(l):
    """La plus recente = date de creation la plus tardive, puis identifiant le plus grand."""
    return (l.get('created_at') is not None, l.get('created_at'), l['id'])


def plan_doublons(lettres):
    """lettres: lignes de lettres_onss. Ne regarde que les lettres encore actives.
    Retourne [{'cle', 'gardee', 'remplacees'}] pour chaque periode ou plusieurs lettres
    actives coexistent ; ne modifie rien."""
    groupes = {}
    for l in lettres:
        if l.get('remplacee_par') is None:
            groupes.setdefault(cle_lettre(l), []).append(l)
    plan = []
    for cle, g in groupes.items():
        if len(g) > 1:
            g = sorted(g, key=_ordre)
            plan.append({'cle': cle, 'gardee': g[-1], 'remplacees': g[:-1]})
    return sorted(plan, key=lambda p: p['cle'])


def libelle_remplacement(l):
    """« Remplacée par la lettre du 02/10/2026 » (date de la lettre qui la remplace)."""
    if l.get('remplacee_par') is None:
        return None
    d = l.get('remplacante_creee_le') or l.get('remplacee_le')
    return "Remplacée par la lettre du " + d.strftime('%d/%m/%Y') if d else "Remplacée par une lettre plus récente"


def pour_historique(lettres):
    """Lettres pretes pour la page « Historique ONSS »: nom du mois, libelle de remplacement,
    lettre active de chaque periode en premier puis ses versions remplacees (les plus recentes
    d'abord). Retourne (lettres, totaux des lettres ACTIVES uniquement)."""
    resultat = []
    for l in lettres:
        l = dict(l, mois_nom=MOIS[l['mois']], remplacement=libelle_remplacement(l))
        resultat.append(l)
    resultat.sort(key=lambda l: (-l['annee'], -l['mois'], l['remplacement'] is not None, -l['id']))
    actives = [l for l in resultat if not l['remplacement']]
    totaux = {k: round(sum(float(l.get(k) or 0) for l in actives), 2)
              for k in ('total_brut', 'total_onss_personnel', 'total_onss_patronal', 'total_onss')}
    return resultat, dict(totaux, nombre=len(actives))


def rapport(plan, noms=None, appliquer=False):
    noms = noms or {}
    m = lambda v: f"{float(v or 0):.2f}".replace('.', ',')
    lignes = ["LETTRES ONSS EN DOUBLE (meme dossier, meme periode)", "=" * 78]
    if not plan:
        lignes.append("Aucun doublon: rien a modifier.")
    for p in plan:
        dossier_id, annee, mois = p['cle']
        lignes.append(f"\n{noms.get(dossier_id, 'Dossier n° ' + str(dossier_id))} — {MOIS[mois]} {annee}")
        for l, mention in [(p['gardee'], "GARDÉE (la plus récente)")] + \
                          [(x, f"-> « remplacée » par la lettre n° {p['gardee']['id']}") for x in p['remplacees']]:
            cree = l['created_at'].strftime('%d/%m/%Y %H:%M') if l.get('created_at') else 'date inconnue'
            lignes.append(f"      lettre n° {l['id']:<6} créée le {cree}   total ONSS {m(l.get('total_onss')):>10}   {mention}")
        if {x.get('pdf_path') for x in p['remplacees']} & {p['gardee'].get('pdf_path')} - {None}:
            lignes.append("      (ces lettres partagent le même fichier PDF: l'ancien PDF a déjà été écrasé par le plus récent)")
    nb = sum(len(p['remplacees']) for p in plan)
    lignes += ["", "=" * 78,
               (f"{nb} lettre(s) marquee(s) « remplacee » dans {len(plan)} periode(s)." if appliquer else
                f"{nb} lettre(s) seraient marquee(s) « remplacee » dans {len(plan)} periode(s). RIEN N'A ETE MODIFIE.\n"
                f"Pour appliquer: python3 lettres_remplacees.py --appliquer")]
    return '\n'.join(lignes)


def main(appliquer=False):
    from database import get_conn
    from psycopg2.extras import RealDictCursor
    conn = get_conn(); cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM lettres_onss")
    lettres = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT id, nom FROM dossiers")
    noms = {r['id']: r['nom'] for r in cur.fetchall()}
    plan = plan_doublons(lettres)
    if appliquer:
        for p in plan:
            for l in p['remplacees']:
                cur.execute(f"UPDATE lettres_onss SET remplacee_par = %s, remplacee_le = NOW() WHERE id = %s AND {LETTRES_ACTIVES}",
                            (p['gardee']['id'], l['id']))
        conn.commit()
    print(rapport(plan, noms, appliquer))
    cur.close(); conn.close()


if __name__ == '__main__':
    main(appliquer='--appliquer' in sys.argv[1:])
