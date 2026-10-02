# -*- coding: utf-8 -*-
"""
suppression_travailleur.py -- DuxSalary
Deux actions distinctes sur un travailleur (corrige le 02/10/2026: le bouton « Supprimer »
se contentait de le cacher -- actif = FALSE -- en laissant ses contrats, fiches et
prestations dans les documents de charges, les lettres ONSS et l'aide DmfA):

- ARCHIVER: le travailleur a quitte l'employeur. Il sort de la liste, mais TOUT son
  historique est conserve et continue de compter (compte individuel, attestation, DmfA).
  Reversible (« Restaurer »).
- SUPPRIMER DEFINITIVEMENT: le travailleur n'aurait jamais du exister (essai, doublon).
  Lui et toutes ses donnees sont effaces de la base: contrats, Dimona, prestations,
  incapacites, decomptes, documents... Irreversible, apres une page de confirmation qui
  liste ce qui sera efface.
  BLOQUEE des que le travailleur a au moins une fiche de paie (decision de Leo, 02/10/2026:
  les documents sociaux se conservent 5 ans): seul l'archivage est alors possible.
"""


class SuppressionBloquee(Exception):
    """Suppression definitive refusee: le travailleur a des fiches de paie."""


MESSAGE_BLOCAGE = ("Suppression définitive impossible : ce travailleur a {n} fiche(s) de paie. Les documents sociaux doivent "
                   "être conservés 5 ans : seul l'archivage est possible.")


def blocage(inv):
    """Message de blocage si le travailleur a au moins une fiche de paie (active ou remplacee), sinon None."""
    n = (inv or {}).get('fiches_paie', 0)
    return MESSAGE_BLOCAGE.format(n=n) if n else None

LIBELLES_TABLES = {
    'contrats': 'contrat(s)', 'dimona': 'Dimona', 'prestations': 'jour(s) de prestations', 'fiches_paie': 'fiche(s) de paie',
    'incapacites': 'incapacité(s)', 'decomptes_sortie': 'décompte(s) de sortie', 'documents': 'document(s)',
    'conges': 'congé(s)', 'calculs_mensuels': 'calcul(s) mensuel(s)', 'alertes': 'alerte(s)',
}


def tables_liees(cur):
    """Tables de la base qui ont une colonne travailleur_id (hors la table travailleurs)."""
    cur.execute("""SELECT table_name FROM information_schema.columns
                   WHERE column_name = 'travailleur_id' AND table_schema = current_schema() ORDER BY table_name""")
    return [(r['table_name'] if isinstance(r, dict) else r[0]) for r in cur.fetchall()]


def inventaire(cur, travailleur_id):
    """{table: nombre de lignes du travailleur} -- affiche avant la suppression definitive."""
    resultat = {}
    for table in tables_liees(cur):
        cur.execute(f'SELECT COUNT(*) AS n FROM "{table}" WHERE travailleur_id = %s', (travailleur_id,))
        r = cur.fetchone()
        n = r['n'] if isinstance(r, dict) else r[0]
        if n:
            resultat[table] = n
    return resultat


def libelle_inventaire(inv):
    """« 2 contrat(s), 3 fiche(s) de paie, 41 jour(s) de prestations » (ordre stable)."""
    return ', '.join(f"{n} {LIBELLES_TABLES.get(t, 'ligne(s) dans ' + t)}" for t, n in sorted(inv.items())) or 'aucune donnée liée'


def supprimer_par_passes(tables, supprimer):
    """Efface les lignes de chaque table en respectant les cles etrangeres SANS connaitre leur
    ordre: on tente chaque table ; celles qui echouent (une autre table les reference encore)
    sont retentees a la passe suivante. supprimer(table) leve une exception en cas d'echec.
    Retourne l'ordre effectif ; leve RuntimeError si une passe entiere n'avance plus."""
    restantes, ordre = list(tables), []
    while restantes:
        echecs, derniere_erreur = [], None
        for table in restantes:
            try:
                supprimer(table)
                ordre.append(table)
            except Exception as ex:      # cle etrangere encore referencee: a retenter
                echecs.append(table); derniere_erreur = ex
        if len(echecs) == len(restantes):
            raise RuntimeError(f"Suppression impossible pour : {', '.join(echecs)} ({derniere_erreur})")
        restantes = echecs
    return ordre


def effacer_travailleur(cur, travailleur_id):
    """Efface definitivement le travailleur et toutes ses donnees. Tout se passe dans la
    transaction du curseur (l'appelant valide ou annule). Retourne (inventaire, chemins des
    PDF a retirer du disque)."""
    inv = inventaire(cur, travailleur_id)
    refus = blocage(inv)
    if refus:
        raise SuppressionBloquee(refus)
    chemins = []
    for table, colonne in (('decomptes_sortie', 'pdf_path'), ('contrats', 'pdf_path')):
        if table in inv:
            cur.execute(f'SELECT {colonne} AS chemin FROM "{table}" WHERE travailleur_id = %s AND {colonne} IS NOT NULL',
                        (travailleur_id,))
            chemins += [(r['chemin'] if isinstance(r, dict) else r[0]) for r in cur.fetchall()]

    def supprimer(table):
        cur.execute('SAVEPOINT effacement')
        try:
            cur.execute(f'DELETE FROM "{table}" WHERE travailleur_id = %s', (travailleur_id,))
            cur.execute('RELEASE SAVEPOINT effacement')
        except Exception:
            cur.execute('ROLLBACK TO SAVEPOINT effacement')
            raise

    supprimer_par_passes(list(inv), supprimer)
    cur.execute('DELETE FROM travailleurs WHERE id = %s', (travailleur_id,))
    return inv, [c for c in chemins if c]
