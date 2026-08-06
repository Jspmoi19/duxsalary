"""
Migration v2 — Tables Dimona, Prestations, mise à jour travailleurs
"""
from database import get_conn

def migrate():
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        -- Situation familiale et précompte sur travailleur
        ALTER TABLE travailleurs ADD COLUMN IF NOT EXISTS situation_familiale VARCHAR(30) DEFAULT 'isole';
        ALTER TABLE travailleurs ADD COLUMN IF NOT EXISTS personnes_charge INTEGER DEFAULT 0;
        ALTER TABLE travailleurs ADD COLUMN IF NOT EXISTS statut_travailleur VARCHAR(20) DEFAULT 'employe';
        ALTER TABLE travailleurs ADD COLUMN IF NOT EXISTS numero_ordre INTEGER;

        -- Table Dimona manuelle
        CREATE TABLE IF NOT EXISTS dimona (
            id SERIAL PRIMARY KEY,
            dossier_id INTEGER REFERENCES dossiers(id),
            travailleur_id INTEGER REFERENCES travailleurs(id),
            contrat_id INTEGER REFERENCES contrats(id),
            type_dimona VARCHAR(10) NOT NULL,
            date_debut DATE NOT NULL,
            date_fin DATE,
            statut VARCHAR(20) DEFAULT 'active',
            numero_reference VARCHAR(50),
            notes TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );

        -- Table Prestations journalières
        CREATE TABLE IF NOT EXISTS prestations (
            id SERIAL PRIMARY KEY,
            dimona_id INTEGER REFERENCES dimona(id),
            travailleur_id INTEGER REFERENCES travailleurs(id),
            dossier_id INTEGER REFERENCES dossiers(id),
            date_prestation DATE NOT NULL,
            code_journee VARCHAR(10) NOT NULL DEFAULT 'P',
            heures DECIMAL(5,2) DEFAULT 0,
            salaire_horaire DECIMAL(8,2),
            notes VARCHAR(200),
            UNIQUE(travailleur_id, date_prestation)
        );

        -- Table calculs mensuels (résultat du calcul de paie)
        CREATE TABLE IF NOT EXISTS calculs_mensuels (
            id SERIAL PRIMARY KEY,
            dossier_id INTEGER REFERENCES dossiers(id),
            travailleur_id INTEGER REFERENCES travailleurs(id),
            dimona_id INTEGER REFERENCES dimona(id),
            annee INTEGER NOT NULL,
            mois INTEGER NOT NULL,
            -- Heures et jours
            jours_prestes INTEGER DEFAULT 0,
            heures_prestees DECIMAL(8,2) DEFAULT 0,
            jours_conge INTEGER DEFAULT 0,
            jours_maladie INTEGER DEFAULT 0,
            jours_ferie INTEGER DEFAULT 0,
            jours_chomage INTEGER DEFAULT 0,
            jours_cnp INTEGER DEFAULT 0,
            -- Rémunération
            salaire_brut DECIMAL(10,2) DEFAULT 0,
            remuneration_conge DECIMAL(10,2) DEFAULT 0,
            remuneration_ferie DECIMAL(10,2) DEFAULT 0,
            -- ONSS
            onss_personnel DECIMAL(10,2) DEFAULT 0,
            onss_patronal DECIMAL(10,2) DEFAULT 0,
            reduction_structurelle DECIMAL(10,2) DEFAULT 0,
            -- Précompte
            precompte_professionnel DECIMAL(10,2) DEFAULT 0,
            -- Net
            salaire_net DECIMAL(10,2) DEFAULT 0,
            cout_employeur DECIMAL(10,2) DEFAULT 0,
            -- PDF
            pdf_fiche_paie VARCHAR(500),
            pdf_lettre_onss VARCHAR(500),
            statut_paiement VARCHAR(20) DEFAULT 'en_attente',
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(travailleur_id, annee, mois)
        );

        -- Documents au niveau dossier
        ALTER TABLE documents ADD COLUMN IF NOT EXISTS niveau VARCHAR(20) DEFAULT 'travailleur';
        
        -- Date activation RSZ sur dossier
        ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS date_activation_rsz DATE;
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    print("Migration v2 OK")

if __name__ == "__main__":
    migrate()
