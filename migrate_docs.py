from database import get_conn

def migrate():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            dossier_id INTEGER REFERENCES dossiers(id),
            travailleur_id INTEGER REFERENCES travailleurs(id),
            nom VARCHAR(200) NOT NULL,
            type_document VARCHAR(50),
            filename VARCHAR(500),
            filepath VARCHAR(500),
            taille INTEGER,
            uploaded_at TIMESTAMP DEFAULT NOW(),
            uploaded_by INTEGER REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS alertes (
            id SERIAL PRIMARY KEY,
            dossier_id INTEGER REFERENCES dossiers(id),
            travailleur_id INTEGER REFERENCES travailleurs(id),
            type_alerte VARCHAR(50),
            message TEXT,
            date_echeance DATE,
            statut VARCHAR(20) DEFAULT 'active',
            created_at TIMESTAMP DEFAULT NOW()
        );

        ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS statut VARCHAR(20) DEFAULT 'actif';
        ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS derniere_visite TIMESTAMP;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS dernier_dossier_id INTEGER;
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("Migration OK")

if __name__ == "__main__":
    migrate()
