"""
database.py — Gestion base de données PostgreSQL pour DuxSalary
Tables : users, dossiers, travailleurs, contrats, fiches_paie
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
import hashlib
import secrets

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://duxsalary:DuxSalary2026x@localhost/duxsalary')

def get_conn():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    """Crée toutes les tables si elles n'existent pas."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            nom VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(256) NOT NULL,
            role VARCHAR(20) DEFAULT 'gestionnaire',
            actif BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS dossiers (
            id SERIAL PRIMARY KEY,
            nom VARCHAR(200) NOT NULL,
            bce VARCHAR(20),
            rsz VARCHAR(20),
            adresse TEXT,
            email VARCHAR(100),
            telephone VARCHAR(20),
            cp_principale VARCHAR(20),
            representant VARCHAR(100),
            assurance_at VARCHAR(200),
            actif BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS travailleurs (
            id SERIAL PRIMARY KEY,
            dossier_id INTEGER REFERENCES dossiers(id),
            nom VARCHAR(100) NOT NULL,
            prenom VARCHAR(100) NOT NULL,
            niss VARCHAR(20),
            adresse TEXT,
            date_naissance DATE,
            iban VARCHAR(34),
            email VARCHAR(100),
            telephone VARCHAR(20),
            nationalite VARCHAR(50) DEFAULT 'Belge',
            actif BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS contrats (
            id SERIAL PRIMARY KEY,
            dossier_id INTEGER REFERENCES dossiers(id),
            travailleur_id INTEGER REFERENCES travailleurs(id),
            type_contrat VARCHAR(10) NOT NULL,
            cp_key VARCHAR(20) NOT NULL,
            fonction VARCHAR(200),
            categorie VARCHAR(100),
            salaire_horaire DECIMAL(8,2),
            salaire_mensuel DECIMAL(10,2),
            heures_semaine DECIMAL(5,2),
            horaire_journalier VARCHAR(50),
            lieu_travail TEXT,
            date_debut DATE NOT NULL,
            date_fin DATE,
            motif_cdd TEXT,
            temps_plein BOOLEAN DEFAULT TRUE,
            statut VARCHAR(20) DEFAULT 'actif',
            pdf_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS fiches_paie (
            id SERIAL PRIMARY KEY,
            dossier_id INTEGER REFERENCES dossiers(id),
            travailleur_id INTEGER REFERENCES travailleurs(id),
            contrat_id INTEGER REFERENCES contrats(id),
            periode_debut DATE NOT NULL,
            periode_fin DATE NOT NULL,
            nb_jours INTEGER,
            heures_totales DECIMAL(8,2),
            salaire_brut DECIMAL(10,2),
            onss_personnel DECIMAL(10,2),
            precompte DECIMAL(10,2) DEFAULT 0,
            transport_montant DECIMAL(10,2) DEFAULT 0,
            salaire_net DECIMAL(10,2),
            onss_patronal DECIMAL(10,2),
            cout_employeur DECIMAL(10,2),
            total_onss DECIMAL(10,2),
            statut_paiement VARCHAR(20) DEFAULT 'en_attente',
            pdf_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    # Créer l'admin par défaut si pas d'utilisateurs
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    if count == 0:
        pwd_hash = hash_password('DuxSalary2026')
        cur.execute("""
            INSERT INTO users (nom, email, password_hash, role)
            VALUES ('Administrateur', 'info@duxsalary.be', %s, 'admin')
        """, (pwd_hash,))

        # Dossier DuxSalary par défaut
        cur.execute("""
            INSERT INTO dossiers (nom, bce, adresse, email, cp_principale, representant)
            VALUES ('Fiduciaire Duxcompta & Co', '0798.198.053', 
                    'Sint-Amandsstraat 2, 1853 Grimbergen',
                    'info@duxsalary.be', 'CP 336', 'Achraf El Harrak')
        """)

    conn.commit()
    cur.close()
    conn.close()
    print("Base de données initialisée.")


def hash_password(password):
    salt = 'duxsalary2026'
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed


# ── USERS ──────────────────────────────────────────────────────────────

def get_user_by_email(email):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM users WHERE email = %s AND actif = TRUE", (email,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return dict(user) if user else None

def create_user(nom, email, password, role='gestionnaire'):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO users (nom, email, password_hash, role)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (nom, email, hash_password(password), role))
        user_id = cur.fetchone()[0]
        conn.commit()
        return user_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


# ── DOSSIERS ───────────────────────────────────────────────────────────

def get_all_dossiers():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT d.*, 
               COUNT(DISTINCT t.id) as nb_travailleurs,
               COUNT(DISTINCT c.id) as nb_contrats_actifs
        FROM dossiers d
        LEFT JOIN travailleurs t ON t.dossier_id = d.id AND t.actif = TRUE
        LEFT JOIN contrats c ON c.dossier_id = d.id AND c.statut = 'actif'
        WHERE d.actif = TRUE
        GROUP BY d.id
        ORDER BY d.nom
    """)
    dossiers = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return dossiers

def get_dossier(dossier_id):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM dossiers WHERE id = %s", (dossier_id,))
    d = cur.fetchone()
    cur.close()
    conn.close()
    return dict(d) if d else None

def _taux_provision(data):
    """Taux (%) de la provision estimee du pecule de vacances des employes: 18,80 par defaut."""
    try:
        return float(str(data.get('taux_provision_pecule_employes') or '18.80').replace(',', '.'))
    except ValueError:
        return 18.80

def create_dossier(data):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO dossiers (nom, bce, rsz, adresse, email, telephone, cp_principale, representant, assurance_at,
                              caisse_vacances, service_medical, assurance_groupe, taux_provision_pecule_employes)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
    """, (data['nom'], data.get('bce'), data.get('rsz'), data.get('adresse'),
          data.get('email'), data.get('telephone'), data.get('cp_principale'),
          data.get('representant'), data.get('assurance_at'),
          data.get('caisse_vacances') or None, data.get('service_medical') or None,
          data.get('assurance_groupe') or None, _taux_provision(data)))
    did = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return did

def update_dossier(dossier_id, data):
    conn = get_conn()
    cur = conn.cursor()
    date_rsz = data.get('date_activation_rsz') or None
    cur.execute("""
        UPDATE dossiers SET nom=%s, bce=%s, rsz=%s, adresse=%s, email=%s,
        telephone=%s, cp_principale=%s, representant=%s, assurance_at=%s,
        date_activation_rsz=%s, premier_engagement=%s, premier_engagement_depuis=%s,
        caisse_vacances=%s, service_medical=%s, assurance_groupe=%s, taux_provision_pecule_employes=%s,
        updated_at=NOW()
        WHERE id=%s
    """, (data['nom'], data.get('bce'), data.get('rsz'), data.get('adresse'),
          data.get('email'), data.get('telephone'), data.get('cp_principale'),
          data.get('representant'), data.get('assurance_at'),
          date_rsz,
          data.get('premier_engagement') == 'on',
          data.get('premier_engagement_depuis') or None,
          data.get('caisse_vacances') or None, data.get('service_medical') or None,
          data.get('assurance_groupe') or None, _taux_provision(data),
          dossier_id))
    conn.commit()
    cur.close()
    conn.close()


# ── TRAVAILLEURS ───────────────────────────────────────────────────────

def get_travailleurs(dossier_id):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT t.*, 
               c.type_contrat, c.fonction, c.cp_key, c.salaire_horaire, c.statut as statut_contrat
        FROM travailleurs t
        LEFT JOIN contrats c ON c.travailleur_id = t.id AND c.statut = 'actif'
        WHERE t.dossier_id = %s AND t.actif = TRUE
        ORDER BY t.nom, t.prenom
    """, (dossier_id,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows

def get_travailleur(travailleur_id):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM travailleurs WHERE id = %s", (travailleur_id,))
    t = cur.fetchone()
    cur.close()
    conn.close()
    return dict(t) if t else None

def create_travailleur(data):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO travailleurs (dossier_id, nom, prenom, niss, adresse, date_naissance, iban, email, telephone,
                                  sexe, caisse_allocations_familiales)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
    """, (data['dossier_id'], data['nom'], data['prenom'], data.get('niss'),
          data.get('adresse'), data.get('date_naissance') or None,
          data.get('iban'), data.get('email'), data.get('telephone'),
          data.get('sexe') or None, data.get('caisse_allocations_familiales') or None))
    tid = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return tid


# ── CONTRATS ───────────────────────────────────────────────────────────

def get_contrats(dossier_id=None, travailleur_id=None):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    query = """
        SELECT c.*, t.nom || ' ' || t.prenom as travailleur_nom
        FROM contrats c
        JOIN travailleurs t ON t.id = c.travailleur_id
        WHERE c.statut = 'actif'
    """
    params = []
    if dossier_id:
        query += " AND c.dossier_id = %s"
        params.append(dossier_id)
    if travailleur_id:
        query += " AND c.travailleur_id = %s"
        params.append(travailleur_id)
    query += " ORDER BY c.created_at DESC"
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows

def create_contrat(data):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO contrats (dossier_id, travailleur_id, type_contrat, cp_key, fonction,
        categorie, salaire_horaire, salaire_mensuel, heures_semaine, heures_jour, jours_semaine,
        horaire_journalier, lieu_travail, date_debut, date_fin, motif_cdd, temps_plein, pdf_path,
        annees_experience)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
    """, (data['dossier_id'], data['travailleur_id'], data['type_contrat'],
          data['cp_key'], data.get('fonction'), data.get('categorie'),
          data.get('salaire_horaire'), data.get('salaire_mensuel'),
          data.get('heures_semaine'), data.get('heures_jour', 7.6), data.get('jours_semaine', 5),
          data.get('horaire_journalier'), data.get('lieu_travail'),
          data['date_debut'], data.get('date_fin'),
          data.get('motif_cdd'), data.get('temps_plein', True), data.get('pdf_path'),
          data.get('annees_experience')))
    cid = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return cid


# ── FICHES DE PAIE ─────────────────────────────────────────────────────

def get_fiches_paie(dossier_id=None, travailleur_id=None, actives_seulement=False):
    """Fiches de paie, remplacees comprises (avec la date de la fiche qui les remplace),
    sauf actives_seulement=True. Voir fiches_remplacees.py."""
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    query = """
        SELECT f.*, t.nom || ' ' || t.prenom as travailleur_nom, r.created_at AS remplacante_creee_le
        FROM fiches_paie f
        JOIN travailleurs t ON t.id = f.travailleur_id
        LEFT JOIN fiches_paie r ON r.id = f.remplacee_par
        WHERE 1=1
    """
    params = []
    if actives_seulement:
        query += " AND f.remplacee_par IS NULL"
    if dossier_id:
        query += " AND f.dossier_id = %s"
        params.append(dossier_id)
    if travailleur_id:
        query += " AND f.travailleur_id = %s"
        params.append(travailleur_id)
    query += " ORDER BY f.periode_debut DESC, f.id DESC"
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows

def create_fiche_paie(data):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO fiches_paie (dossier_id, travailleur_id, contrat_id,
        periode_debut, periode_fin, nb_jours, heures_totales,
        salaire_brut, onss_personnel, precompte, transport_montant,
        salaire_net, onss_patronal, cout_employeur, total_onss, pdf_path)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
    """, (data['dossier_id'], data['travailleur_id'], data.get('contrat_id'),
          data['periode_debut'], data['periode_fin'], data.get('nb_jours'),
          data.get('heures_totales'), data['salaire_brut'], data['onss_personnel'],
          data.get('precompte', 0), data.get('transport_montant', 0),
          data['salaire_net'], data['onss_patronal'], data['cout_employeur'],
          data['total_onss'], data.get('pdf_path')))
    fid = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return fid


if __name__ == "__main__":
    init_db()
