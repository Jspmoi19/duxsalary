# -*- coding: utf-8 -*-
"""
fiches_remplacees.py -- DuxSalary
Une seule fiche de paie ACTIVE par travailleur, contrat et periode.

Quand une fiche est regeneree, l'ancienne passe au statut « remplacee »
(fiches_paie.remplacee_par = id de la nouvelle fiche, remplacee_le = date). Elle
reste consultable avec son PDF (c'est ce qui a ete envoye au client), mais elle est
exclue de tout ce qui additionne les fiches: attestation salariale, compte
individuel, liste de ventilation, aide DmfA, lettres ONSS, cumul annuel du bonus a
l'emploi. Toute requete qui additionne des fiches doit contenir FICHES_ACTIVES.

Doublons deja presents en base (fiches generees plusieurs fois avant cette regle):
    python3 fiches_remplacees.py              -> affiche la liste, NE MODIFIE RIEN
    python3 fiches_remplacees.py --appliquer  -> garde la plus recente comme active,
                                                marque les autres « remplacee »
Colonnes: python3 migrate_charges.py (a lancer avant).
"""
import os
import sys

# Condition SQL des fiches actives (alias de table optionnel: fiches_actives('f'))
FICHES_ACTIVES = "remplacee_par IS NULL"


def fiches_actives(alias=None):
    return f"{alias}.{FICHES_ACTIVES}" if alias else FICHES_ACTIVES


def cle_fiche(f):
    """Deux fiches se remplacent quand elles ont le meme travailleur, le meme contrat
    et la meme periode. (Un etudiant passe en CDI dans le mois a deux fiches legitimes:
    une par contrat.)"""
    return (f['travailleur_id'], f.get('contrat_id'), f['periode_debut'], f['periode_fin'])


def _ordre(f):
    """La plus recente = date de creation la plus tardive, puis identifiant le plus grand."""
    return (f.get('created_at') is not None, f.get('created_at'), f['id'])


def plan_doublons(fiches):
    """fiches: lignes de fiches_paie (id, travailleur_id, contrat_id, periode_debut,
    periode_fin, created_at, remplacee_par...). Ne regarde que les fiches encore actives.
    Retourne [{'cle', 'gardee': fiche, 'remplacees': [fiches]}] pour chaque groupe ou
    plusieurs fiches actives coexistent ; ne modifie rien."""
    groupes = {}
    for f in fiches:
        if f.get('remplacee_par') is None:
            groupes.setdefault(cle_fiche(f), []).append(f)
    plan = []
    for cle, g in groupes.items():
        if len(g) > 1:
            g = sorted(g, key=_ordre)
            plan.append({'cle': cle, 'gardee': g[-1], 'remplacees': g[:-1]})
    return sorted(plan, key=lambda p: (p['cle'][0], p['cle'][2]))


def memes_mois_autres_contrats(fiches):
    """Fiches actives du meme travailleur et de la meme periode mais de contrats
    differents: PAS des doublons pour le script (cas etudiant puis CDI), listees pour
    controle. Retourne [(travailleur_id, periode_debut, [fiches])]."""
    groupes = {}
    for f in fiches:
        if f.get('remplacee_par') is None:
            groupes.setdefault((f['travailleur_id'], f['periode_debut'], f['periode_fin']), []).append(f)
    return [(k[0], k[1], g) for k, g in sorted(groupes.items(), key=lambda x: (x[0][0], x[0][1]))
            if len({x.get('contrat_id') for x in g}) > 1]


def chemin_pdf_libre(chemin, existe=os.path.exists):
    """Chemin de PDF qui n'ecrase aucun fichier existant: « x.pdf », puis « x_v2.pdf »,
    « x_v3.pdf »... Le PDF d'une fiche remplacee doit rester tel qu'il a ete envoye."""
    if not existe(chemin):
        return chemin
    base, ext = os.path.splitext(chemin)
    n = 2
    while existe(f"{base}_v{n}{ext}"):
        n += 1
    return f"{base}_v{n}{ext}"


def libelle_remplacement(f):
    """« Remplacée par la fiche du 02/10/2026 » (date de la fiche qui la remplace)."""
    if f.get('remplacee_par') is None:
        return None
    d = f.get('remplacante_creee_le') or f.get('remplacee_le')
    return "Remplacée par la fiche du " + d.strftime('%d/%m/%Y') if d else "Remplacée par une fiche plus récente"


# ─────────────────────────────────────────────────────────────────
# SCRIPT: doublons deja presents en base
# ─────────────────────────────────────────────────────────────────
def _montant(v):
    return f"{float(v or 0):.2f}".replace('.', ',')


def _ligne(f, mention):
    cree = f['created_at'].strftime('%d/%m/%Y %H:%M') if f.get('created_at') else 'date inconnue'
    return (f"      fiche n° {f['id']:<6} créée le {cree}   brut {_montant(f.get('salaire_brut')):>10}   "
            f"net {_montant(f.get('salaire_net')):>10}   {mention}")


def rapport(plan, autres, noms=None, appliquer=False):
    """Texte affiche par le script (liste de ce qui serait modifie)."""
    noms = noms or {}
    lignes = ["FICHES DE PAIE EN DOUBLE (meme travailleur, meme contrat, meme periode)", "=" * 78]
    if not plan:
        lignes.append("Aucun doublon: rien a modifier.")
    for p in plan:
        tid, contrat_id, debut, fin = p['cle']
        lignes.append(f"\n{noms.get(tid, 'Travailleur n° ' + str(tid))} — période du {debut:%d/%m/%Y} au {fin:%d/%m/%Y} "
                      f"— contrat n° {contrat_id if contrat_id is not None else 'non renseigné'}")
        lignes.append(_ligne(p['gardee'], "GARDÉE (la plus récente)"))
        for f in p['remplacees']:
            lignes.append(_ligne(f, f"-> « remplacée » par la fiche n° {p['gardee']['id']}"))
        chemins = {f.get('pdf_path') for f in p['remplacees']} & {p['gardee'].get('pdf_path')} - {None}
        if chemins:
            lignes.append("      (ces fiches partagent le même fichier PDF: l'ancien PDF a déjà été écrasé par le plus récent)")
    if autres:
        lignes += ["", "A CONTROLER — meme travailleur et meme periode, mais contrats differents (NON modifie):"]
        for tid, debut, g in autres:
            lignes.append(f"  {noms.get(tid, 'Travailleur n° ' + str(tid))} — {debut:%m/%Y} : fiches n° "
                          + ', '.join(f"{f['id']} (contrat {f.get('contrat_id')})" for f in g))
    nb = sum(len(p['remplacees']) for p in plan)
    lignes += ["", "=" * 78,
               (f"{nb} fiche(s) marquee(s) « remplacee » dans {len(plan)} groupe(s)." if appliquer else
                f"{nb} fiche(s) seraient marquee(s) « remplacee » dans {len(plan)} groupe(s). RIEN N'A ETE MODIFIE.\n"
                f"Pour appliquer: python3 fiches_remplacees.py --appliquer")]
    return '\n'.join(lignes)


def main(appliquer=False):
    from database import get_conn
    from psycopg2.extras import RealDictCursor
    conn = get_conn(); cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""SELECT id, travailleur_id, contrat_id, dossier_id, periode_debut, periode_fin, created_at, salaire_brut,
                          salaire_net, pdf_path, remplacee_par FROM fiches_paie""")
    fiches = [dict(r) for r in cur.fetchall()]
    cur.execute("""SELECT t.id, t.nom || ' ' || t.prenom || ' (' || d.nom || ')' AS libelle
                   FROM travailleurs t JOIN dossiers d ON d.id = t.dossier_id""")
    noms = {r['id']: r['libelle'] for r in cur.fetchall()}
    plan, autres = plan_doublons(fiches), memes_mois_autres_contrats(fiches)
    if appliquer:
        for p in plan:
            for f in p['remplacees']:
                cur.execute(f"UPDATE fiches_paie SET remplacee_par = %s, remplacee_le = NOW() WHERE id = %s AND {FICHES_ACTIVES}",
                            (p['gardee']['id'], f['id']))
        conn.commit()
    print(rapport(plan, autres, noms, appliquer))
    cur.close(); conn.close()


if __name__ == '__main__':
    main(appliquer='--appliquer' in sys.argv[1:])
