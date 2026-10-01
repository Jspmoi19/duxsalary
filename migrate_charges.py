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
    ],
    'travailleurs': [
        ('sexe', 'VARCHAR(1)'), ('date_sortie', 'DATE'), ('caisse_allocations_familiales', 'VARCHAR(200)'),
    ],
    'dossiers': [
        ('caisse_vacances', 'VARCHAR(200)'), ('service_medical', 'VARCHAR(200)'), ('assurance_groupe', 'VARCHAR(200)'),
        # Provision ESTIMEE du pecule de vacances des employes (convention comptable,
        # pas un parametre legal): modifiable par dossier
        ('taux_provision_pecule_employes', 'DECIMAL(5,2) DEFAULT 18.80'),
    ],
}


def migrate():
    conn = get_conn()
    cur = conn.cursor()
    for table, colonnes in COLONNES.items():
        for nom, type_sql in colonnes:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {nom} {type_sql}")
    conn.commit()
    cur.close()
    conn.close()
    print("Migration documents de charges OK")


if __name__ == "__main__":
    migrate()
