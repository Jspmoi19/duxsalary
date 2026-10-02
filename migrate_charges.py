# -*- coding: utf-8 -*-
"""
Migration « documents de charges salariales » -- DuxSalary
Ajoute les colonnes necessaires au compte individuel, a l'attestation salariale
et a la liste de ventilation. Relancable sans risque (ADD COLUMN IF NOT EXISTS).

    python3 migrate_charges.py

A lancer AVANT de deployer le code qui lit ces colonnes.
"""
from database import get_conn

COLONNES = {
    'fiches_paie': [
        # Colonnes deja creees sur le serveur par d'anciens patchs (rappelees ici
        # pour qu'une base neuve soit complete)
        ('bonus_emploi_a', 'DECIMAL(10,2) DEFAULT 0'), ('bonus_emploi_b', 'DECIMAL(10,2) DEFAULT 0'),
        ('precompte_avant_reduction', 'DECIMAL(10,2) DEFAULT 0'), ('reduction_precompte_bonus', 'DECIMAL(10,2) DEFAULT 0'),
        ('reduction_structurelle', 'DECIMAL(10,2) DEFAULT 0'), ('reduction_premier_engagement', 'DECIMAL(10,2) DEFAULT 0'),
        ('frais_nets_montant', 'DECIMAL(10,2) DEFAULT 0'), ('jours_prestes', 'INTEGER'), ('heures_prestees', 'DECIMAL(8,2)'),
        ('is_ouvrier', 'BOOLEAN'), ('is_etudiant', 'BOOLEAN'), ('cp_key', 'VARCHAR(20)'), ('type_contrat', 'VARCHAR(10)'),
        ('prime_brut', 'DECIMAL(10,2) DEFAULT 0'), ('pecule_brut', 'DECIMAL(10,2) DEFAULT 0'),
        ('onss_exceptionnel', 'DECIMAL(10,2) DEFAULT 0'), ('precompte_exceptionnel', 'DECIMAL(10,2) DEFAULT 0'),
        # Nouvelles colonnes
        ('detail_complet', 'BOOLEAN DEFAULT FALSE'),   # FALSE = fiche anterieure: detail non disponible
        ('jours_feries', 'INTEGER DEFAULT 0'), ('heures_feries', 'DECIMAL(8,2) DEFAULT 0'),
        ('jours_conge', 'INTEGER DEFAULT 0'), ('jours_maladie', 'INTEGER DEFAULT 0'),
        ('jours_absence_non_payee', 'INTEGER DEFAULT 0'),
        ('salaire_base', 'DECIMAL(10,4)'), ('salaire_base_periodicite', 'VARCHAR(10)'),
        ('remunerations', 'JSONB'),                    # [{libelle, montant, jours, heures}]
        ('libelle_prime', 'VARCHAR(100)'),
        ('brut_majore', 'DECIMAL(10,2)'),              # base ONSS (108 % ouvriers)
        ('onss_personnel_brut', 'DECIMAL(10,2)'),      # avant bonus a l'emploi, hors primes
        ('brut_imposable', 'DECIMAL(10,2)'),
        ('css', 'DECIMAL(10,2) DEFAULT 0'),
        ('indemnites', 'JSONB'),                       # [{libelle, montant}]
        ('cr_part_travailleur', 'DECIMAL(10,2) DEFAULT 0'), ('cr_part_employeur', 'DECIMAL(10,2) DEFAULT 0'),
        ('onss_patronal_reductible', 'DECIMAL(10,2)'), ('onss_vacances_253', 'DECIMAL(10,2) DEFAULT 0'),
        ('cotisations_complementaires', 'JSONB'),      # [{code, libelle, taux, montant}]
        ('onss_patronal_prime', 'DECIMAL(10,2) DEFAULT 0'),
        ('provision_vacances_ouvrier', 'DECIMAL(10,2) DEFAULT 0'),
        ('onss_trimestre', 'VARCHAR(8)'), ('categorie_employeur', 'VARCHAR(3)'),
        # Aide a la DmfA: {codes: {code prestation: {jours, heures}}, a_determiner: {code journalier: jours}}
        ('prestations_dmfa', 'JSONB'),
        # Fiche remplacee par une fiche plus recente (meme travailleur, contrat et periode):
        # NULL = fiche active. Voir fiches_remplacees.py.
        ('remplacee_par', 'INTEGER'), ('remplacee_le', 'TIMESTAMP'),
        # Km domicile-travail, taux et moyen de transport saisis a la generation: reproposes
        # dans le formulaire de la fiche suivante (occupation.km_a_proposer)
        ('km_domicile', 'INTEGER'), ('taux_km', 'DECIMAL(6,4)'), ('moyen_transport', 'VARCHAR(20)'),
    ],
    'travailleurs': [
        ('sexe', 'VARCHAR(1)'), ('date_sortie', 'DATE'), ('caisse_allocations_familiales', 'VARCHAR(200)'),
        # Charges de famille (precompte): deja creees sur le serveur par d'anciens patchs,
        # rappelees ici pour qu'une base neuve soit complete
        ('etat_civil', "VARCHAR(30) DEFAULT 'celibataire'"), ('partenaire_revenus_pro', "VARCHAR(20) DEFAULT 'non'"),
        ('partenaire_pensions', "VARCHAR(20) DEFAULT 'non'"),
        ('nb_enfants_sans_handicap', 'INTEGER DEFAULT 0'), ('nb_enfants_avec_handicap', 'INTEGER DEFAULT 0'),
        ('nb_personnes_charge_66', 'INTEGER DEFAULT 0'), ('nb_autres_personnes_charge', 'INTEGER DEFAULT 0'),
        ('parent_isole', 'BOOLEAN DEFAULT FALSE'), ('handicape', 'BOOLEAN DEFAULT FALSE'),
        ('conjoint_handicape', 'BOOLEAN DEFAULT FALSE'),
        # Travailleur qui ouvre le droit a la reduction « premier engagement » (code 3315):
        # un seul par dossier ; le dossier garde la case generale et la date de debut du droit
        ('premier_engagement', 'BOOLEAN DEFAULT FALSE'),
        # Type de personnel en CP 140.03 (roulant / non_roulant / garage): ecocheques et case RGPT.
        # Colonne deja creee sur le serveur par le suivi des cheques, rappelee pour une base neuve
        ('categorie_personnel', 'VARCHAR(20)'),
    ],
    # Option « l'employeur fournit des repas » (avantage de toute nature), page « Chèques »
    'cheques_config': [
        ('repas_fournis', 'BOOLEAN DEFAULT FALSE'),
        # Periode de validite des cheques du dossier: ils ne s'appliquent qu'aux fiches dont
        # la periode commence a partir de la date de debut (et au plus tard a la date de fin)
        ('repas_date_debut', 'DATE'), ('repas_date_fin', 'DATE'),
        ('repas_inclure_etudiants', 'BOOLEAN DEFAULT FALSE'),
        ('eco_date_debut', 'DATE'), ('eco_date_fin', 'DATE'),
    ],
    # Annees d'experience professionnelle a la date du contrat (bareme par experience, tache 4)
    'contrats': [
        ('annees_experience', 'INTEGER'),
    ],
    # Lettres ONSS: une seule lettre active par dossier et par periode (lettres_remplacees.py).
    # NULL = lettre active. created_at: ajoute s'il manquait (les lettres existantes recoivent
    # la date de la migration).
    'lettres_onss': [
        ('remplacee_par', 'INTEGER'), ('remplacee_le', 'TIMESTAMP'), ('created_at', 'TIMESTAMP DEFAULT NOW()'),
    ],
    'dossiers': [
        ('caisse_vacances', 'VARCHAR(200)'), ('service_medical', 'VARCHAR(200)'), ('assurance_groupe', 'VARCHAR(200)'),
        # Provision ESTIMEE du pecule de vacances des employes (convention comptable,
        # pas un parametre legal): modifiable par dossier
        ('taux_provision_pecule_employes', 'DECIMAL(5,2) DEFAULT 18.80'),
        # Numero d'unite d'etablissement BCE (2.xxx.xxx.xxx), demande sur la ligne d'occupation de la DmfA
        ('numero_unite_etablissement', 'VARCHAR(13)'),
    ],
}


# Episodes d'incapacite de travail (maladie / accident de droit commun), tache 5:
# un enregistrement par episode, lie au travailleur. Les tranches de salaire
# garanti de chaque jour sont recalculees par salaire_garanti.py (jamais stockees).
TABLES = [
    """CREATE TABLE IF NOT EXISTS incapacites (
        id SERIAL PRIMARY KEY,
        travailleur_id INTEGER NOT NULL REFERENCES travailleurs(id) ON DELETE CASCADE,
        dossier_id INTEGER NOT NULL,
        date_debut DATE NOT NULL,
        date_fin DATE,                                   -- NULL = incapacite en cours
        type_incapacite VARCHAR(20) NOT NULL DEFAULT 'maladie',   -- maladie | accident (droit commun)
        autre_cause BOOLEAN NOT NULL DEFAULT FALSE,      -- autre maladie/accident atteste par certificat (pas une rechute)
        note TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_incapacites_travailleur ON incapacites (travailleur_id, date_debut)",
    # Decomptes de sortie (tache 6): un enregistrement par decompte genere (fin_contrat.py).
    # 'donnees' = resultat complet du calcul ; 'dmfa' = lignes a reprendre dans l'aide DmfA.
    """CREATE TABLE IF NOT EXISTS decomptes_sortie (
        id SERIAL PRIMARY KEY,
        dossier_id INTEGER NOT NULL,
        travailleur_id INTEGER NOT NULL REFERENCES travailleurs(id) ON DELETE CASCADE,
        contrat_id INTEGER,
        date_fin DATE NOT NULL,
        motif VARCHAR(30) NOT NULL,
        brut DECIMAL(10,2) DEFAULT 0, net DECIMAL(10,2) DEFAULT 0,
        dmfa JSONB, donnees JSONB, pdf_path VARCHAR(500),
        created_at TIMESTAMP DEFAULT NOW()
    )""",
]


# Lettres ONSS: une ancienne contrainte d'unicite (dossier, mois, annee) empecherait d'enregistrer
# la nouvelle lettre a cote de l'ancienne (la lettre regeneree n'etait alors pas enregistree:
# « ON CONFLICT DO NOTHING », d'ou les anciens montants dans l'historique). Les contraintes et
# index d'unicite autres que la cle primaire sont retires ; l'unicite de la lettre ACTIVE est
# assuree par l'application (app.py) et par lettres_remplacees.py.
SQL_LETTRES_UNICITE = """
DO $$
DECLARE c record;
BEGIN
    IF to_regclass('lettres_onss') IS NULL THEN RETURN; END IF;
    FOR c IN SELECT conname FROM pg_constraint WHERE conrelid = 'lettres_onss'::regclass AND contype = 'u' LOOP
        EXECUTE 'ALTER TABLE lettres_onss DROP CONSTRAINT ' || quote_ident(c.conname);
    END LOOP;
    FOR c IN SELECT i.relname FROM pg_index x JOIN pg_class i ON i.oid = x.indexrelid
             WHERE x.indrelid = 'lettres_onss'::regclass AND x.indisunique AND NOT x.indisprimary LOOP
        EXECUTE 'DROP INDEX ' || quote_ident(c.relname);
    END LOOP;
END $$;
"""


def migrate():
    conn = get_conn()
    cur = conn.cursor()
    for sql in TABLES:
        cur.execute(sql)
    cur.execute(SQL_LETTRES_UNICITE)
    for table, colonnes in COLONNES.items():
        for nom, type_sql in colonnes:
            # IF EXISTS: une table creee par un autre script (ex. cheques_config) peut manquer sur une base neuve
            cur.execute(f"ALTER TABLE IF EXISTS {table} ADD COLUMN IF NOT EXISTS {nom} {type_sql}")
    conn.commit()
    cur.close()
    conn.close()
    print("Migration documents de charges OK")


if __name__ == "__main__":
    migrate()
