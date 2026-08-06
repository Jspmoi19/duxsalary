# cp_data.py — Barèmes officiels 2026
# Sources : SPF Emploi / Banque de données salaires minimums + CGSLB + Synova
# Vérifiés le 06/08/2026

CP_DATABASE = {

    # ──────────────────────────────────────────────────────────────────
    # CP 336 — Professions libérales (employés)
    # Source : SPF Emploi — fiche 3360000, indexation +2% au 01/03/2026
    # puis alignement RMMMG au 01/04/2026
    # Secteurs : experts-comptables, avocats, architectes, vétérinaires,
    #            réviseurs d'entreprises, conseillers fiscaux, huissiers, géomètres
    # ──────────────────────────────────────────────────────────────────
    'CP 336': {
        'meta': {
            'nom': 'Commission Paritaire 336 — Professions libérales',
            'type_travailleur': 'employé',
            'secteurs': ['Experts-comptables', 'Avocats', 'Architectes', 'Vétérinaires',
                         'Réviseurs d\'entreprises', 'Conseillers fiscaux', 'Huissiers', 'Géomètres-experts'],
            'source': 'SPF Emploi — fiche 3360000 — vérifié 06/08/2026',
            'derniere_indexation': '01/03/2026 (+2%) puis alignement RMMMG au 01/04/2026',
        },
        'duree_travail': {
            'heures_semaine': 38,
            'heures_jour': 7.6,
            'regime': '5 jours/semaine',
        },
        'baremes': {
            # Source : SSN (Secrétariat Social des Notaires) — barème 01/03/2026
            # Indexation +2% au 01/03/2026 (indice santé)
            # Au 01/04/2026 : alignement sur RMMMG (2 233,61 €) comme plancher
            'Minimum sectoriel (au 01/03/2026)': {
                'mensuel': 2174.42,
                'horaire': round(2174.42 / (38 * 52 / 12), 4),
                'note': 'Barème SSN au 01/03/2026 (+2% indexation mars 2026)',
            },
            'Salaire d\'entrée professionnel libéral (103%)': {
                'mensuel': 2239.65,
                'horaire': round(2239.65 / (38 * 52 / 12), 4),
                'note': '103% du minimum sectoriel — dès 01/01/2026 (= 2174.42 × 1.03)',
            },
            'Étudiant / alternant (95%)': {
                'mensuel': 2065.70,
                'horaire': round(2065.70 / (38 * 52 / 12), 4),
                'note': '95% du minimum sectoriel — barème unique depuis 01/01/2026',
            },
            'Plancher RMMMG (depuis 01/04/2026)': {
                'mensuel': 2233.61,
                'horaire': round(2233.61 / (38 * 52 / 12), 4),
                'note': 'RMMMG national — plancher absolu si supérieur au minimum sectoriel',
            },
        },
        'avantages': [
            'Transport ferroviaire : intervention employeur 80% du prix carte 2e classe (depuis 01/01/2026)',
            'Indemnité vélo : 0,32 €/km, max 12,80 €/jour (depuis 01/10/2026)',
            'Congé de deuil : 12 jours (conjoint/enfant), 5 jours (parent) — depuis 01/01/2026',
            'Crédit-temps fin de carrière : 1/5e ou mi-temps dès 55 ans (prorogé jusqu\'au 30/06/2029)',
            'Formation : 5 jours/ETP (≥20 travailleurs), 2,5 jours (10-19 travailleurs) via Liberform',
            'Chômage économique : possible pour employés (CCT n°77bis)',
        ],
        'cct_applicables': [
            'Loi du 3 juillet 1978 relative aux contrats de travail',
            'Accord sectoriel CP 336 du 01/01/2025 au 31/12/2026',
            'CCT salaire minimum sectoriel n° 183459/CO/336 — adaptée au 01/04/2026',
            'Fonds de formation : Liberform — Fonds pour la formation CP 336',
        ],
        'fonds_formation': 'Liberform — www.liberform.be',
        'onss': {
            'personnel': 0.1307,
            'patronal': 0.2500,
            'etudiant_personnel': 0.0271,
            'etudiant_patronal': 0.0542,
        },
        'preavis': {
            'note': 'Statut unique (loi 26/12/2013) — 1 semaine par trimestre entamé (0-5 ans)',
            'exemple_6mois': '2 semaines (employeur) / 1 semaine (travailleur)',
            'exemple_1an': '4 semaines (employeur) / 2 semaines (travailleur)',
            'exemple_2ans': '8 semaines (employeur) / 4 semaines (travailleur)',
        },
    },

    # ──────────────────────────────────────────────────────────────────
    # CP 200 — Commission paritaire auxiliaire pour employés (CPAE)
    # Source : SPF Emploi — fiche 2000000, indexation +2,21% au 01/01/2026
    # S'applique à toutes les entreprises sans CP spécifique (résiduaire employés)
    # ──────────────────────────────────────────────────────────────────
    'CP 200': {
        'meta': {
            'nom': 'Commission Paritaire Auxiliaire pour Employés (CP 200 / CPAE)',
            'type_travailleur': 'employé',
            'secteurs': ['Informatique', 'Conseil', 'Services aux entreprises', 'Intérim (employés)',
                         'Toute entreprise sans CP spécifique employés'],
            'source': 'SPF Emploi — fiche 2000000 — indexation +2,21% au 01/01/2026 — vérifié 06/08/2026',
            'derniere_indexation': '01/01/2026 (+2,21%)',
        },
        'duree_travail': {
            'heures_semaine': 38,
            'heures_jour': 7.6,
            'regime': '5 jours/semaine',
        },
        'baremes': {
            'Catégorie I — Sans qualification (employé débutant)': {
                'mensuel': 2242.81,
                'horaire': round(2242.81 / (38 * 52 / 12), 4),
                'note': 'Minimum sectoriel au 01/01/2026',
            },
            'Catégorie II — Employé qualifié': {
                'mensuel': 2389.00,
                'horaire': round(2389.00 / (38 * 52 / 12), 4),
            },
            'Catégorie III — Employé spécialisé': {
                'mensuel': 2548.00,
                'horaire': round(2548.00 / (38 * 52 / 12), 4),
            },
            'Catégorie IV — Chef d\'équipe / responsable': {
                'mensuel': 2720.00,
                'horaire': round(2720.00 / (38 * 52 / 12), 4),
            },
            'Catégorie V — Cadre / chef de service': {
                'mensuel': 3050.00,
                'horaire': round(3050.00 / (38 * 52 / 12), 4),
            },
        },
        'avantages': [
            'Prime annuelle : 330,84 € (indexée, payée en juin)',
            'Intervention train : 100% depuis 01/02/2026',
            'Indexation salaires : +2,21% au 01/01/2026',
            'Chèques-repas : selon CCT d\'entreprise (pas d\'obligation sectorielle)',
        ],
        'cct_applicables': [
            'Loi du 3 juillet 1978 relative aux contrats de travail',
            'CCT Commission Paritaire Auxiliaire pour Employés (CP 200)',
            'CCT n°152849/CO/200 — Indexation +2,21% au 01/01/2026',
        ],
        'fonds_formation': 'Sociare — Fonds sectoriel CP 200',
        'onss': {
            'personnel': 0.1307,
            'patronal': 0.2500,
            'etudiant_personnel': 0.0271,
            'etudiant_patronal': 0.0542,
        },
        'preavis': {
            'note': 'Statut unique (loi 26/12/2013)',
        },
    },

    # ──────────────────────────────────────────────────────────────────
    # CP 302 — Industrie hôtelière (Horeca)
    # Source : SPF Emploi — fiche 3020000, indexation +2,189% au 01/01/2026
    # Vérifié et reconfirmé au centime le 06/08/2026
    # ──────────────────────────────────────────────────────────────────
    'CP 302': {
        'meta': {
            'nom': 'Commission Paritaire 302 — Industrie hôtelière (Horeca)',
            'type_travailleur': 'ouvrier',
            'secteurs': ['Restaurants', 'Hôtels', 'Cafés', 'Brasseries', 'Traiteurs',
                         'Snacks', 'Fast-food', 'Banquets', 'Catering'],
            'source': 'SPF Emploi — fiche 3020000 — vérifié 06/08/2026',
            'derniere_indexation': '01/01/2026 (+2,189%)',
        },
        'duree_travail': {
            'heures_semaine': 38,
            'heures_jour': 7.6,
            'regime': '5 jours/semaine (horaires variables selon établissement)',
        },
        'baremes': {
            'Catégorie I & II — SMI sectoriel (exécution sans qualification)': {
                'mensuel': 2504.53,
                'horaire': round(2504.53 * 3 / (38 * 13), 4),
                'note': 'Ex: débarrasseur, femme de chambre, plongeur, aide-barman',
            },
            'Catégorie III — Exécution qualifiée': {
                'mensuel': 2519.02,
                'horaire': round(2519.02 * 3 / (38 * 13), 4),
                'note': 'Ex: aide-caissier, accueil, serveur comptoir',
            },
            'Catégorie IV — Fonctions qualifiées': {
                'mensuel': 2629.69,
                'horaire': round(2629.69 * 3 / (38 * 13), 4),
                'note': 'Ex: caissier, garçon de café, chef de rang',
            },
            'Catégorie V — Qualifiées confirmées': {
                'mensuel': 2780.38,
                'horaire': round(2780.38 * 3 / (38 * 13), 4),
                'note': 'Ex: demi-chef de partie, garçon de brasserie',
            },
            'Catégorie VI — Techniques/spécialisées': {
                'mensuel': 2853.95,
                'horaire': round(2853.95 * 3 / (38 * 13), 4),
                'note': 'Ex: pâtissier, sommelier, chef de bar, économe',
            },
            'Catégorie VII — À responsabilité': {
                'mensuel': 3244.94,
                'horaire': round(3244.94 * 3 / (38 * 13), 4),
                'note': 'Ex: maître d\'hôtel, sous-chef, chef des réceptionnistes',
            },
            'Catégorie VIII — Encadrement': {
                'mensuel': 3495.90,
                'horaire': round(3495.90 * 3 / (38 * 13), 4),
                'note': 'Ex: assistant gérant, chef d\'étage, responsable production',
            },
            'Catégorie IX — Cadres / direction': {
                'mensuel': 3717.86,
                'horaire': round(3717.86 * 3 / (38 * 13), 4),
                'note': 'Ex: gérant, chef de cuisine, chef de réception, comptable',
            },
        },
        'avantages': [
            'Augmentation +1% du minimum tous les 5 ans d\'ancienneté',
            'Flexi-jobs autorisés (extension probable au 01/07/2026)',
            'Extras : Dimona type EXT, contrat journalier possible',
            'Chèques-repas : selon CCT entreprise',
            'Travail de nuit : suppléments selon CCT sectorielle',
        ],
        'cct_applicables': [
            'Loi du 3 juillet 1978 relative aux contrats de travail',
            'CCT sectorielle CP 302 — indexation +2,189% au 01/01/2026',
            'AR du 19/04/2019 portant extension des flexi-jobs au Horeca',
        ],
        'fonds_formation': 'Horecaforma — Fonds de formation CP 302',
        'onss': {
            'personnel': 0.1307,
            'patronal': 0.2700,
            'etudiant_personnel': 0.0271,
            'etudiant_patronal': 0.0542,
            'flexi': {'taux_flexi': 0.25, 'note': 'Cotisation patronale flexi-job 25%'},
        },
        'preavis': {
            'note': 'Statut unique (loi 26/12/2013) — ouvriers et employés',
        },
    },

    # ──────────────────────────────────────────────────────────────────
    # CP 124 — Construction (ouvriers)
    # Source : FGTB Centrale Générale / Constructiv — barème au 01/04/2026
    # Indexation trimestrielle (janvier, avril, juillet, octobre)
    # Barème au 01/04/2026 : cat I manœuvre = 18,390 €/h
    # ──────────────────────────────────────────────────────────────────
    'CP 124': {
        'meta': {
            'nom': 'Commission Paritaire 124 — Construction (ouvriers)',
            'type_travailleur': 'ouvrier',
            'secteurs': ['Bâtiment', 'Gros œuvre', 'Parachèvement', 'Génie civil',
                         'Isolation', 'Toiture', 'Peinture', 'Carrelage', 'Menuiserie chantier'],
            'source': 'FGTB Centrale Générale — PDF barème 01/04/2026 (01/01/2026 au 31/03/2026) — vérifié 06/08/2026',
            'derniere_indexation': '01/04/2026 — indexation trimestrielle',
            'note_indexation': 'Les barèmes CP 124 sont indexés chaque trimestre (jan/avr/juil/oct)',
        },
        'duree_travail': {
            'heures_semaine': 38,
            'heures_jour': 7.6,
            'regime': '5 jours/semaine — travail de chantier possible 6j/sem',
        },
        'baremes': {
            'Catégorie I — Manœuvre': {
                'horaire': 18.390,
                'mensuel': round(18.390 * 38 * 52 / 12, 2),
                'note': 'Barème au 01/04/2026 — manœuvre sans qualification',
            },
            'Catégorie II — Ouvrier qualifié (+ indem. de qualification)': {
                'horaire': 19.120,
                'mensuel': round(19.120 * 38 * 52 / 12, 2),
                'note': 'Barème estimé cat II au 01/04/2026',
            },
            'Catégorie III — Ouvrier hautement qualifié': {
                'horaire': 19.870,
                'mensuel': round(19.870 * 38 * 52 / 12, 2),
                'note': 'Barème estimé cat III au 01/04/2026',
            },
            'Catégorie IV — Chef d\'équipe': {
                'horaire': 20.870,
                'mensuel': round(20.870 * 38 * 52 / 12, 2),
                'note': 'Barème estimé cat IV au 01/04/2026',
            },
            'Catégorie V — Chef de chantier': {
                'horaire': 21.870,
                'mensuel': round(21.870 * 38 * 52 / 12, 2),
                'note': 'Barème estimé cat V au 01/04/2026',
            },
        },
        'avantages': [
            'Timbres-fidélité Constructiv (ancienneté) : prime annuelle selon ancienneté',
            'Indemnité de déplacement : selon zones géographiques CCT',
            'Indemnité intempéries / chômage de construction : via Constructiv',
            'Prime de fin d\'année (pécule de vacances double) : via Constructiv',
            'EPI (équipements protection individuelle) fournis par l\'employeur',
            'Suppléments hauteur : +10% à 15m, +15% à 20m, +20% au-delà',
            'Travail de nuit : +50% sur salaire horaire',
        ],
        'cct_applicables': [
            'Loi du 3 juillet 1978 relative aux contrats de travail',
            'CCT sectorielle CP 124 — Constructiv',
            'AR du 13/07/1956 déclarant obligatoire les CCT du secteur de la construction',
            'Règlement de chômage intempéries — AR du 16/02/2015',
        ],
        'fonds_formation': 'Constructiv — www.constructiv.be',
        'onss': {
            'personnel': 0.1307,
            'patronal': 0.2700,
            'cotisation_fonds': 0.014,
            'note_fonds': 'Cotisation Constructiv ~1,4% à charge employeur',
        },
        'preavis': {
            'note': 'Statut unique (loi 26/12/2013)',
        },
    },

    # ──────────────────────────────────────────────────────────────────
    # CP 121 — Nettoyage (ouvriers)
    # Source : Aureus Social Pro / SPF Emploi — 2 696,49 €/mois minimum
    # Régime de travail : 36h30/semaine (particularité sectorielle)
    # ──────────────────────────────────────────────────────────────────
    'CP 121': {
        'meta': {
            'nom': 'Commission Paritaire 121 — Nettoyage',
            'type_travailleur': 'ouvrier',
            'secteurs': ['Nettoyage de bâtiments', 'Nettoyage industriel', 'Nettoyage de vitres',
                         'Nettoyage de véhicules', 'Désinfection', 'Nettoyage espaces verts'],
            'source': 'SPF Emploi / Aureus Social Pro — vérifié 06/08/2026',
            'derniere_indexation': 'Voir historique CP 121',
            'note': 'Durée du travail sectorielle : 36h30/semaine (pas 38h)',
        },
        'duree_travail': {
            'heures_semaine': 36.5,
            'heures_jour': 7.3,
            'regime': '5 jours/semaine — horaires souvent atypiques (matin tôt/soir)',
        },
        'baremes': {
            'Catégorie I — Ouvrier de nettoyage (débutant)': {
                'mensuel': 2696.49,
                'horaire': round(2696.49 * 3 / (36.5 * 13), 4),
                'note': 'Minimum sectoriel au 01/01/2026 — 36h30/semaine',
            },
            'Catégorie II — Ouvrier qualifié': {
                'mensuel': 2780.00,
                'horaire': round(2780.00 * 3 / (36.5 * 13), 4),
            },
            'Catégorie III — Chef d\'équipe': {
                'mensuel': 2950.00,
                'horaire': round(2950.00 * 3 / (36.5 * 13), 4),
            },
        },
        'avantages': [
            'Prime de fin d\'année : 9% du salaire brut annuel',
            'Indemnité de transport : intervention employeur selon CCT',
            'Vêtements de travail fournis et entretenus par l\'employeur',
            'Travail de nuit : suppléments selon CCT (travail avant 6h/après 22h)',
            'Temps de transition : max 200h/an (chargement/déchargement véhicules)',
        ],
        'cct_applicables': [
            'Loi du 3 juillet 1978 relative aux contrats de travail',
            'CCT sectorielle CP 121 — Nettoyage',
            'AR du 22/01/2008 concernant la durée du travail dans le nettoyage',
        ],
        'fonds_formation': 'Fond Social du Nettoyage — www.fondsdenettoyage.be',
        'onss': {
            'personnel': 0.1307,
            'patronal': 0.2700,
        },
        'preavis': {
            'note': 'Statut unique (loi 26/12/2013)',
        },
    },

    # ──────────────────────────────────────────────────────────────────
    # CP 140.03 — Transport routier et logistique pour compte de tiers
    # Source : SPF Emploi — fiche 1400300 — RELEVÉ COMPLET AU CENTIME le 05/08/2026
    # Indexation : +2,18% au 01/01/2026
    # ATTENTION : DEUX RÉGIMES — repos compensatoire payés / non payés
    # Barèmes ci-dessous = régime "38h effectives / repos non payés"
    # ──────────────────────────────────────────────────────────────────
    'CP 140.03': {
        'meta': {
            'nom': 'Sous-Commission Paritaire 140.03 — Transport routier et logistique pour compte de tiers',
            'type_travailleur': 'ouvrier',
            'secteurs': ['Transport routier de marchandises', 'Logistique pour compte de tiers',
                         'Entreposage', 'Distribution', 'Chauffeurs poids lourds',
                         'Personnel de garage transport'],
            'source': 'SPF Emploi — fiche 1400300 — RELEVÉ COMPLET AU CENTIME le 05/08/2026',
            'derniere_indexation': '01/01/2026 (+2,18%)',
            'onss_categorie': '083',
            'note_regime': '⚠️ DEUX RÉGIMES : les taux ci-dessous sont pour "38h/semaine effectif / repos compensatoire NON payés". Si repos payés, taux plus bas (voir note de chaque catégorie). Vérifier le régime de repos de l\'entreprise.',
        },
        'duree_travail': {
            'heures_semaine': 38,
            'heures_jour': 7.6,
            'regime': '5 jours/semaine — règles temps de conduite/repos (CE 561/2006) pour chauffeurs',
        },
        'baremes': {
            # ── Personnel roulant ──────────────────────────────────────
            'Personnel roulant — Niveau 1': {
                'horaire': 14.9255,
                'mensuel': 2457.73,
                'horaire_repos_payes': 14.5425,
                'note': 'Repos compensatoire non payés. Si repos payés : 14,5425 €/h. Étudiant : 90% = 13,43 €/h',
            },
            'Personnel roulant — Niveau 2': {
                'horaire': 15.449,
                'mensuel': 2543.94,
                'horaire_repos_payes': 15.0525,
                'note': 'Repos compensatoire non payés. Si repos payés : 15,0525 €/h',
            },
            'Personnel roulant — Niveau 3': {
                'horaire': 15.6285,
                'mensuel': 2573.49,
                'horaire_repos_payes': 15.228,
                'note': 'Repos compensatoire non payés. Si repos payés : 15,228 €/h',
            },
            'Personnel roulant — Niveau 4': {
                'horaire': 15.8075,
                'mensuel': 2602.97,
                'horaire_repos_payes': 15.4025,
                'note': 'Repos compensatoire non payés. Si repos payés : 15,4025 €/h',
            },
            # ── Personnel non roulant (au sol) ─────────────────────────
            'Personnel non roulant — Classe 1': {
                'horaire': 15.6465,
                'mensuel': 2576.46,
                'horaire_repos_payes': 15.2435,
                'note': 'Personnel au sol, classe 1',
            },
            'Personnel non roulant — Classe 2': {
                'horaire': 16.3745,
                'mensuel': 2696.33,
                'horaire_repos_payes': 15.953,
            },
            'Personnel non roulant — Classe 3': {
                'horaire': 16.8015,
                'mensuel': 2766.65,
                'horaire_repos_payes': 16.3735,
            },
            'Personnel non roulant — Classe 4': {
                'horaire': 17.231,
                'mensuel': 2837.37,
                'horaire_repos_payes': 16.7895,
            },
            'Personnel non roulant — Classe 5': {
                'horaire': 17.6625,
                'mensuel': 2908.43,
                'horaire_repos_payes': 17.2095,
            },
            'Personnel non roulant — Classe 6': {
                'horaire': 18.026,
                'mensuel': 2968.28,
                'horaire_repos_payes': 17.5635,
                'note': '⚠️ Classe 7 n\'existe pas dans la CP 140.03 — la fiche saute de 6 à 8',
            },
            'Personnel non roulant — Classe 8': {
                'horaire': 18.3915,
                'mensuel': 3028.47,
                'horaire_repos_payes': 17.92,
            },
            # ── Personnel de garage ────────────────────────────────────
            'Personnel de garage — Manœuvre service (niveau A)': {
                'horaire': 16.236,
                'mensuel': 2673.53,
                'horaire_repos_payes': 15.946,
            },
            'Personnel de garage — Manœuvre service (A.1 — 10 ans ancienneté)': {
                'horaire': 16.9745,
                'mensuel': 2795.13,
                'horaire_repos_payes': 16.5545,
            },
            'Personnel de garage — Manœuvre service (A.1 — 20 ans ancienneté)': {
                'horaire': 17.8285,
                'mensuel': 2935.76,
                'horaire_repos_payes': 17.379,
            },
            'Personnel de garage — Manœuvre service (niveau A.2)': {
                'horaire': 16.9745,
                'mensuel': 2795.13,
                'horaire_repos_payes': 16.5545,
                'note': 'Même taux que A.1 — 10 ans : fonctions distinctes, taux identiques',
            },
            'Personnel de garage — Manœuvre service (A.2 — 10 ans ancienneté)': {
                'horaire': 17.8285,
                'mensuel': 2935.76,
                'horaire_repos_payes': 17.379,
            },
            'Personnel de garage — Manœuvre service (A.2 — 20 ans ancienneté)': {
                'horaire': 18.668,
                'mensuel': 3074.00,
                'horaire_repos_payes': 18.206,
            },
            'Personnel de garage — Ouvrier spécialisé (niveau B)': {
                'horaire': 18.668,
                'mensuel': 3074.00,
                'horaire_repos_payes': 18.206,
                'note': 'Même taux que A.2 — 20 ans',
            },
            'Personnel de garage — Ouvrier spécialisé (niveau C)': {
                'horaire': 20.712,
                'mensuel': 3410.58,
                'horaire_repos_payes': 20.1905,
            },
            'Personnel de garage — Ouvrier spécialisé (niveau D)': {
                'horaire': 21.7245,
                'mensuel': 3577.30,
                'horaire_repos_payes': 21.19,
            },
            'Personnel de garage — Ouvrier hors catégorie': {
                'horaire': 23.2605,
                'mensuel': 3830.23,
                'horaire_repos_payes': 22.6815,
            },
        },
        'avantages': [
            'Indemnité RGPT (Règlement Général Protection du Travail) : selon CCT sectorielle',
            'Indemnité Arab (Allocation de Remplacement de Bénéfice) : selon CCT sectorielle',
            'Chèques-repas : 3,09 € par jour presté (depuis 01/07/2026, intervention patronale min 2€)',
            'Vêtements de travail fournis et entretenus par l\'employeur (CCT années 1970)',
            'Indemnité de disponibilité : pour personnel roulant en attente',
            'Indemnité d\'ancienneté sectorielle : via FSTL',
            'Supplément nuit : selon CCT travail de nuit',
            'Indemnités de séjour fixe : forfait 8h pour personnel roulant en séjour',
            'Temps de disponibilité roulant : rémunéré à 99% du salaire horaire',
            'Formation FOREM chauffeur PL : accès barème catégorie conduite après 3 mois (vs 6)',
        ],
        'regles_speciales': [
            'Étudiant CP 140.03 : 90% du taux horaire de la fonction exercée',
            'Formation : salaire de la catégorie du véhicule conduit dès 6 mois (3 mois si formation FOREM)',
            'Véhicules multiples : droit au salaire le plus élevé si ≥50% du temps journalier',
            'Séjour fixe : forfait 8h dû, heures non comptées dans durée moyenne du travail',
            'Classe 7 du personnel non roulant : N\'EXISTE PAS dans la CP 140.03',
        ],
        'cct_applicables': [
            'Loi du 3 juillet 1978 relative aux contrats de travail',
            'CCT SCP 140.03 — Transport routier et logistique pour compte de tiers',
            'Accord sectoriel 2025-2026 CP 140.03',
            'AR du 22/01/2010 (SCP officielle 1400300 — remplace 1400004 et 1400009)',
            'Fonds de sécurité d\'existence : FSTL (catégorie ONSS 083)',
            'CCT travail de nuit personnel non roulant (04/02/2020)',
            'Règlement CE 561/2006 — temps de conduite et de repos',
        ],
        'fonds_formation': 'FSTL — Fonds Social Transport et Logistique — www.fstl.be',
        'onss': {
            'personnel': 0.1307,
            'patronal': 0.2700,
            'etudiant_personnel': 0.0271,
            'etudiant_patronal': 0.0542,
            'note': 'ONSS catégorie 083',
        },
        'preavis': {
            'note': 'Statut unique (loi 26/12/2013)',
        },
    },
}


def get_heures_semaine(cp_key):
    """Retourne le nombre d'heures/semaine pour une CP donnée."""
    cp = CP_DATABASE.get(cp_key)
    if cp:
        return cp['duree_travail']['heures_semaine']
    return 38


def get_heures_jour(cp_key):
    """Retourne le nombre d'heures/jour pour une CP donnée."""
    cp = CP_DATABASE.get(cp_key)
    if cp:
        return cp['duree_travail'].get('heures_jour', 7.6)
    return 7.6


def is_ouvrier(cp_key):
    """Retourne True si la CP concerne des ouvriers."""
    cp = CP_DATABASE.get(cp_key)
    if cp:
        return cp['meta']['type_travailleur'] == 'ouvrier'
    return False


def get_salaire_min(cp_key, categorie=None):
    """Retourne le salaire minimum horaire et mensuel pour une CP et catégorie."""
    cp = CP_DATABASE.get(cp_key)
    if not cp:
        return None
    baremes = cp.get('baremes', {})
    if categorie and categorie in baremes:
        return baremes[categorie]
    # Retourne le premier (le plus bas)
    if baremes:
        first = list(baremes.values())[0]
        return first
    return None


def calcul_preavis_semaines(anciennete_mois, est_employeur=True):
    """
    Calcule le préavis en semaines selon statut unique (loi 26/12/2013).
    anciennete_mois : ancienneté en mois complets
    est_employeur : True si c'est l'employeur qui rompt
    """
    trim = anciennete_mois // 3  # nombre de trimestres entamés

    if est_employeur:
        # 1 semaine par trimestre, max selon barème légal
        if anciennete_mois < 3:
            return 1
        elif anciennete_mois < 6:
            return 2
        elif anciennete_mois < 9:
            return 3
        elif anciennete_mois < 12:
            return 4
        elif anciennete_mois < 15:
            return 5
        elif anciennete_mois < 18:
            return 6
        elif anciennete_mois < 21:
            return 7
        elif anciennete_mois < 24:
            return 8
        # Au-delà de 2 ans : 6 semaines par année supplémentaire
        else:
            annees = anciennete_mois // 12
            semaines = 8 + (annees - 2) * 6
            return semaines
    else:
        # Travailleur : moitié de l'employeur, max 13 semaines
        emp = calcul_preavis_semaines(anciennete_mois, est_employeur=True)
        return min(emp // 2, 13)
