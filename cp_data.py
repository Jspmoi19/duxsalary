"""
cp_data.py — Base de données des commissions paritaires belges
Mise à jour : juillet 2026
Sources : SPF Emploi, salairesminimums.be, CCT sectorielles

Structure de chaque CP :
- meta : infos générales
- baremes : salaires minimums par catégorie/fonction
- duree_travail : régime hebdomadaire
- indemnites : primes et indemnités obligatoires
- conges : régime vacances annuelles
- transport : règles remboursement domicile-travail
- mentions_contrat : clauses légales obligatoires
- regles_speciales : particularités sectorielles
"""

CP_DATABASE = {

    # ══════════════════════════════════════════════════════════════════
    # CP 336 — PROFESSIONS LIBÉRALES (employés)
    # ══════════════════════════════════════════════════════════════════
    "CP 336": {
        "meta": {
            "nom": "Commission Paritaire 336 – Professions libérales",
            "type_travailleur": "employé",
            "secteurs": ["Comptabilité", "Expertise comptable", "Conseil fiscal", "Architecture", "Avocat", "Notaire", "Vétérinaire", "Géomètre"],
            "fonds_securite": "Liberform",
            "onss_categorie": "010",
            "regime_vacances": "employé",  # employeur paie
        },
        "duree_travail": {
            "heures_semaine": 38,
            "heures_jour": 7.6,
            "jours_semaine": 5,
            "regime": "fixe",
        },
        "baremes": {
            # Au 01/01/2026 — indexation +2%
            "etudiant": {"mensuel": 2065.70, "horaire": 12.54, "note": "95% du minimum sectoriel"},
            "entree": {"mensuel": 2239.65, "horaire": 13.60, "note": "103% du minimum sectoriel — nouveaux professionnels libéraux"},
            "minimum_sectoriel": {"mensuel": 2174.42, "horaire": 13.20},
            # Pas de barèmes par ancienneté stricts — salaire réel négocié au-dessus du minimum
        },
        "indemnites": {
            "transport_train": {"taux": 0.80, "base": "abonnement_2e_classe", "obligatoire": True, "note": "80% depuis 01/01/2026"},
            "velo": {"taux_par_km": 0.10, "max_jour": 4.00, "obligatoire": True, "note": "0,10€/km jusqu'au 30/09/2026, puis 0,32€/km"},
            "velo_oct2026": {"taux_par_km": 0.32, "max_jour": 12.80, "date_vigueur": "01/10/2026"},
            "voiture": {"taux_par_km": 0.4449, "obligatoire": False, "note": "Facultatif — exonéré ONSS si accordé"},
        },
        "conges": {
            "jours_legaux": 20,
            "jours_extra_legaux": 0,
            "prise_en_charge": "employeur",
            "pecule_simple": 0.0892,  # 8,92% du brut annuel
            "pecule_double": 0.92,    # 92% d'un mois de salaire
        },
        "mentions_contrat": [
            "Loi du 3 juillet 1978 relative aux contrats de travail",
            "CCT n° 183459/CO/336 du 27 septembre 2023 relative au salaire mensuel minimum sectoriel",
            "Accord sectoriel CP 336 du 1er janvier 2025 au 31 décembre 2026",
            "Fonds de formation : Liberform – Fonds pour la formation des travailleurs de la CP 336",
            "CCT du 15 décembre 2025 – accord sectoriel 2025-2026",
        ],
        "preavis": {
            "note": "Statut unique (loi du 26 décembre 2013) — délais par tranches d'ancienneté",
            "semaines_par_tranche": [
                (0, 3, 2), (3, 6, 4), (6, 9, 6), (9, 12, 7),
                (12, 18, 8), (18, 24, 9), (24, 36, 10), (36, 48, 12),
                (48, 60, 13), (60, 72, 15), (72, 84, 18), (84, 96, 21),
                (96, 108, 24), (108, 120, 27), (120, 999, 30),
            ],
            "unite": "semaines",
        },
        "regles_speciales": [
            "Clause de paix sociale : accord 2025-2026, pas de revendications supplémentaires",
            "Télétravail : dialogue social encouragé au niveau de l'entreprise",
            "Formation : 2,5 à 5 jours/ETP selon taille (Liberform)",
            "Congé de deuil étendu : 12j conjoint/enfant, 5j parent (depuis 01/01/2026)",
        ],
    },

    # ══════════════════════════════════════════════════════════════════
    # CP 200 — AUXILIAIRE POUR EMPLOYÉS (fourre-tout employés)
    # ══════════════════════════════════════════════════════════════════
    "CP 200": {
        "meta": {
            "nom": "Commission Paritaire auxiliaire pour employés (CP 200)",
            "type_travailleur": "employé",
            "secteurs": ["IT / Informatique", "Publicité", "Bureaux d'études", "Agences de voyage", "Commerce automobile", "Industrie graphique", "Call centers", "Divers employés"],
            "fonds_securite": "SFONDS 200",
            "onss_categorie": "010",
            "regime_vacances": "employé",
            "note": "CP résiduelle — s'applique si aucune autre CP spécifique",
        },
        "duree_travail": {
            "heures_semaine": 38,
            "heures_jour": 7.6,
            "jours_semaine": 5,
            "regime": "fixe",
        },
        "baremes": {
            # Au 01/01/2026 — indexation +2,21%
            # Classification par classe A à E selon fonction
            "classe_A": {
                "0_an": {"mensuel": 2189.81, "horaire": 13.30, "note": "RMMMG — fonctions d'exécution simple"},
            },
            "classe_B": {
                "0_an": {"mensuel": 2350.00, "horaire": 14.27},
                "5_ans": {"mensuel": 2520.00, "horaire": 15.30},
            },
            "classe_C": {
                "0_an": {"mensuel": 2520.00, "horaire": 15.30},
                "5_ans": {"mensuel": 2750.00, "horaire": 16.70},
                "10_ans": {"mensuel": 3050.00, "horaire": 18.52},
            },
            "classe_D": {
                "0_an": {"mensuel": 3000.00, "horaire": 18.22},
                "5_ans": {"mensuel": 3400.00, "horaire": 20.65},
            },
            "classe_E": {
                "0_an": {"mensuel": 3500.00, "horaire": 21.25},
                "5_ans": {"mensuel": 4000.00, "horaire": 24.29},
            },
            "minimum_general": {"mensuel": 2189.81, "horaire": 13.30},
            "etudiant": {"mensuel": 2189.81, "horaire": 13.30, "note": "Minimum RMMMG"},
            "note_IT": "En IT, les salaires réels sont bien supérieurs aux barèmes CP 200 — négociés au niveau entreprise",
        },
        "indemnites": {
            "prime_annuelle": {"montant": 330.84, "note": "Indexée, payée en juin", "obligatoire": True},
            "transport_train": {"taux": 1.00, "base": "abonnement_2e_classe", "obligatoire": True, "note": "100% depuis 01/02/2026"},
            "velo": {"taux_par_km": 0.30, "max_jour": 12.00, "obligatoire": True, "note": "0,30€/km — indemnité supplétive minimale"},
            "voiture": {"taux_par_km": 0.4449, "obligatoire": False},
        },
        "conges": {
            "jours_legaux": 20,
            "jours_extra_legaux": 0,
            "prise_en_charge": "employeur",
            "pecule_simple": 0.0892,
            "pecule_double": 0.92,
        },
        "mentions_contrat": [
            "Loi du 3 juillet 1978 relative aux contrats de travail",
            "CCT Commission paritaire auxiliaire pour employés (CP 200)",
            "Indexation salariale : +2,21% au 01/01/2026",
            "Prime annuelle : 330,84 € (indexée, payée en juin via SFONDS 200)",
        ],
        "preavis": {
            "note": "Statut unique — mêmes délais que CP 336",
            "semaines_par_tranche": [
                (0, 3, 2), (3, 6, 4), (6, 9, 6), (9, 12, 7),
                (12, 18, 8), (18, 24, 9), (24, 36, 10), (36, 48, 12),
                (48, 60, 13), (60, 72, 15), (72, 84, 18), (84, 96, 21),
                (96, 108, 24), (108, 120, 27), (120, 999, 30),
            ],
            "unite": "semaines",
        },
        "regles_speciales": [
            "Indexation salariale annuelle au 01/01 — +2,21% en 2026",
            "Intervention train 100% depuis 01/02/2026 (tiers payant SNCB recommandé)",
            "IT : pas de grille salariale obligatoire — négociation entreprise",
        ],
    },

    # ══════════════════════════════════════════════════════════════════
    # CP 302 — HORECA (ouvriers et quelques employés)
    # ══════════════════════════════════════════════════════════════════
    "CP 302": {
        "meta": {
            "nom": "Commission Paritaire 302 – Industrie hôtelière (Horeca)",
            "type_travailleur": "ouvrier",
            "secteurs": ["Hôtels", "Restaurants", "Cafés", "Traiteurs", "Snack-bars", "Cantines", "Discothèques"],
            "fonds_securite": "Fonds Horeca (fondshoreca.be)",
            "onss_categorie": "083",
            "regime_vacances": "ouvrier",  # ONVA / Office National des Vacances Annuelles
            "note": "Indexation annuelle au 01/01 (+2,189% en 2026). 9 catégories de fonctions.",
        },
        "duree_travail": {
            "heures_semaine": 38,
            "heures_jour": 7.6,
            "jours_semaine": 5,
            "regime": "flexible",
            "note": "Horaire variable fréquent — max 9h/jour, période de référence trimestrielle",
        },
        "baremes": {
            # Au 01/01/2026 — indexation +2,189%
            # 9 catégories de fonctions (I à IX) — barèmes horaires bruts
            # Ancienneté : 0 an, puis 6 mois → an 1, puis annuellement
            "cat_I": {  # Personnel non qualifié
                "an_0": {"horaire": 14.16, "mensuel": 2331.49, "fonctions": ["Aide de cuisine", "Plongeur", "Garçon de salle débutant", "Femme de chambre débutante"]},
                "an_1": {"horaire": 14.47, "mensuel": 2382.54},
                "an_2": {"horaire": 14.63, "mensuel": 2408.85},
                "an_3": {"horaire": 14.79, "mensuel": 2435.24},
                "an_4": {"horaire": 14.95, "mensuel": 2461.55},
                "an_5": {"horaire": 15.11, "mensuel": 2487.90},
            },
            "cat_II": {  # Personnel semi-qualifié
                "an_0": {"horaire": 14.47, "mensuel": 2382.44, "fonctions": ["Commis de cuisine", "Serveur", "Réceptionniste débutant"]},
                "an_1": {"horaire": 14.79, "mensuel": 2435.24},
                "an_2": {"horaire": 14.95, "mensuel": 2461.55},
                "an_3": {"horaire": 15.11, "mensuel": 2487.90},
                "an_4": {"horaire": 15.27, "mensuel": 2514.28},
                "an_5": {"horaire": 15.42, "mensuel": 2540.55},
            },
            "cat_III": {  # Personnel qualifié
                "an_0": {"horaire": 14.95, "mensuel": 2461.55, "fonctions": ["Cuisinier", "Garçon de salle qualifié", "Réceptionniste", "Barman qualifié"]},
                "an_1": {"horaire": 15.27, "mensuel": 2514.28},
                "an_2": {"horaire": 15.42, "mensuel": 2540.55},
                "an_3": {"horaire": 15.58, "mensuel": 2566.97},
                "an_4": {"horaire": 15.74, "mensuel": 2593.30},
                "an_5": {"horaire": 15.89, "mensuel": 2619.55},
            },
            "cat_IV": {  # Chef de partie / responsable de section
                "an_0": {"horaire": 15.58, "mensuel": 2566.97, "fonctions": ["Chef de partie", "Maître d'hôtel adjoint", "Réceptionniste senior"]},
                "an_1": {"horaire": 15.89, "mensuel": 2619.55},
                "an_3": {"horaire": 16.21, "mensuel": 2668.48},
                "an_5": {"horaire": 16.51, "mensuel": 2717.82},
            },
            "cat_V": {  # Chef cuisinier / maître d'hôtel
                "an_0": {"horaire": 16.21, "mensuel": 2668.48, "fonctions": ["Chef cuisinier", "Maître d'hôtel", "Chef de réception"]},
                "an_3": {"horaire": 16.83, "mensuel": 2770.22},
                "an_5": {"horaire": 17.14, "mensuel": 2821.67},
            },
            "cat_VI": {  # Sous-chef / Chef de cuisine adjoint
                "an_0": {"horaire": 17.14, "mensuel": 2821.67, "fonctions": ["Sous-chef exécutif", "Food & Beverage Manager adjoint"]},
            },
            "cat_VII": {  # Chef exécutif / Directeur restauration
                "an_0": {"horaire": 18.33, "mensuel": 3017.88, "fonctions": ["Chef exécutif", "Directeur de restauration"]},
            },
            "etudiant": {
                "note": "Étudiant = catégorie de la fonction exercée MOINS 2 catégories (sauf école hôtelière)",
                "exemple": "Étudiant commis de cuisine (cat II normalement) → rémunéré cat I",
            },
            "flexi": {
                "minimum_horaire_net": 11.87,
                "note": "Flexi-job : salaire net min 11,87€/h (01/03/2026) + 7,67% pécule vacances",
                "maximum_horaire_net": 19.17,
                "plafond_annuel_exonere": 18440,
            },
        },
        "indemnites": {
            "vetements": {"montant_jour": 2.20, "obligatoire": True, "note": "Si employeur ne fournit pas/n'entretient pas les vêtements de travail"},
            "nuit": {"montant_heure": 1.6209, "heures": "00h00-05h00", "obligatoire": True, "note": "Travail de nuit"},
            "transport_train": {"taux": 0.718, "base": "abonnement_2e_classe", "obligatoire": True},
            "velo": {"taux_par_km": 0.27, "obligatoire": False, "note": "0,27€/km selon CCT interne"},
            "prime_fin_annee": {"note": "Prime de fin d'année sectorielle — voir Fonds Horeca"},
            "plan_pension": {"note": "Plan de pension sectoriel complémentaire — Fonds Horeca"},
        },
        "conges": {
            "jours_legaux": 20,
            "prise_en_charge": "ONVA",  # Office National des Vacances Annuelles
            "pecule_simple": 0.1027,    # 10,27% du brut déclaré à l'ONSS
            "note": "Régime ouvrier — pécule payé par ONVA, pas par l'employeur directement",
        },
        "mentions_contrat": [
            "Loi du 3 juillet 1978 relative aux contrats de travail",
            "CCT Commission Paritaire 302 – Industrie hôtelière",
            "Classification des fonctions : CCT fondshoreca.be — catégories I à IX",
            "Indexation salariale : +2,189% au 01/01/2026",
            "Fonds Horeca (Fonds de sécurité d'existence) : fondshoreca.be",
            "Régime des vacances annuelles : Office National des Vacances Annuelles (ONVA)",
        ],
        "preavis": {
            "note": "Statut unique — mêmes délais légaux",
            "semaines_par_tranche": [
                (0, 3, 2), (3, 6, 4), (6, 9, 6), (9, 12, 7),
                (12, 18, 8), (18, 24, 9), (24, 36, 10), (36, 48, 12),
                (48, 60, 13), (60, 72, 15), (72, 84, 18), (84, 96, 21),
                (96, 108, 24), (108, 120, 27), (120, 999, 30),
            ],
            "unite": "semaines",
        },
        "regles_speciales": [
            "Extras : contrats journaliers autorisés — Dimona type EXT",
            "Flexi-jobs : régime spécifique — pas de cotisations sociales normales",
            "50 jours travailleur occasionnel horeca : Dimona type OTH + cotisations forfaitaires",
            "Pourboires : système du 'tronc' possible si prévu au règlement de travail",
            "Classification fonction : vérifier sur fondshoreca.be — sous-classification sanctionnée",
            "Saisonniers : régime spécifique ancienneté (130 jours dans saison)",
        ],
    },

    # ══════════════════════════════════════════════════════════════════
    # CP 124 — CONSTRUCTION (ouvriers)
    # ══════════════════════════════════════════════════════════════════
    "CP 124": {
        "meta": {
            "nom": "Commission Paritaire 124 – Construction",
            "type_travailleur": "ouvrier",
            "secteurs": ["Maçonnerie", "Gros œuvre", "Finitions", "Génie civil", "Démolition", "Couverture", "Peinture", "Carrelage", "Menuiserie extérieure", "Ferraillage"],
            "fonds_securite": "Constructiv (ex-FONDS DE SECURITE D'EXISTENCE)",
            "onss_categorie": "083",
            "regime_vacances": "ouvrier",
            "note": "Indexation TRIMESTRIELLE (1/1, 1/4, 1/7, 1/10). Barèmes : 1er avril 2026.",
        },
        "duree_travail": {
            "heures_semaine": 38,
            "heures_jour": 7.6,
            "jours_semaine": 5,
            "regime": "flexible",
            "note": "Régime flexible autorisé : max 45h/semaine avec compensation. AR n°213 : 180h/an dérogation été.",
        },
        "baremes": {
            # Barèmes au 01/04/2026 (indexation trimestrielle +0,8717%)
            "cat_I": {
                "horaire": 18.39,
                "mensuel": 3028.81,
                "note": "Manœuvre — travaux généraux sans qualification",
                "fonctions": ["Manœuvre", "Aide démolisseur", "Terrassier simple", "Manutentionnaire"],
            },
            "cat_I_A": {
                "horaire": 18.55,
                "mensuel": 3055.22,
                "note": "Manœuvre spécialisé — 6 mois expérience",
                "fonctions": ["Aide-maçon après 6 mois", "Aide-boiseur", "Bétonneurs ordinaires"],
            },
            "cat_II": {
                "horaire": 19.61,
                "mensuel": 3229.65,
                "note": "Ouvrier semi-qualifié",
                "fonctions": ["Aide-fumiste", "Aide-maçon qualifié", "Dameur de pavage", "Décapeur jet de sable", "Démolisseur"],
            },
            "cat_II_A": {
                "horaire": 19.94,
                "mensuel": 3283.94,
                "note": "Semi-qualifié avec habileté reconnue",
                "fonctions": ["Ouvrier semi-qualifié avec expérience reconnue"],
            },
            "cat_III": {
                "horaire": 20.85,
                "mensuel": 3432.86,
                "note": "Ouvrier qualifié — catégorie principale (la plus courante)",
                "fonctions": ["Maçon", "Charpentier", "Ferrailler", "Carreleur", "Couvreur ardoises/tuiles", "Menuisier", "Peintre qualifié", "Plombier", "Électricien", "Conducteur camion-mixer"],
            },
            "cat_IV": {
                "horaire": 22.13,
                "mensuel": 3643.88,
                "note": "Ouvrier hautement qualifié",
                "fonctions": ["Maçon expert", "Charpentier expert", "Carreleur expert", "Chef d'équipe adjoint"],
            },
            "chef_equipe_A": {
                "horaire": 22.93,
                "mensuel": 3775.24,
                "note": "Chef d'équipe (équipe principalement cat III) — au moins +10% vs sa propre cat",
                "fonctions": ["Chef d'équipe (ouvriers cat III principalement)"],
            },
            "chef_equipe_B": {
                "horaire": 24.35,
                "mensuel": 4009.00,
                "note": "Chef d'équipe (équipe cat IV)",
            },
            "contremaitre": {
                "horaire": 26.56,
                "mensuel": 4373.38,
                "note": "Contremaître — supervise plusieurs chefs d'équipe",
            },
            "etudiant": {
                "note": "Depuis 01/01/2024 : barèmes étudiants supprimés. Salaire minimum = catégorie I",
                "horaire": 18.39,
                "mensuel": 3028.81,
            },
        },
        "indemnites": {
            "petits_deplacements": {
                "note": "Indemnité mobilité selon distance domicile-chantier. Barèmes Constructiv.",
                "obligatoire": True,
                "km_max_exonere": 28500,  # Au-delà → 1 jour mobilité supplémentaire
            },
            "logement_nourriture": {
                "note": "Si chantier trop éloigné pour rentrer journellement — employeur oblige de loger/nourrir/entretenir",
                "obligatoire": True,
            },
            "outillage": {
                "note": "Indemnité si ouvrier utilise ses propres outils",
                "obligatoire": False,  # Si outils propres utilisés → indemnité usure
            },
            "hauteur": {
                "taux_15m": 0.10,  # +10% au-delà de 15m
                "note": "+10% pour travaux en hauteur >15m (corniches, échafaudages suspendus)",
                "obligatoire": True,
            },
            "amiante": {
                "note": "Supplément spécifique pour travaux désamiantage — voir CCT",
                "obligatoire": True,
            },
            "prime_anciennete": {
                "25_ans": 500,
                "35_ans": 700,
                "note": "Prime ancienneté ininterrompue dans la même entreprise",
                "obligatoire": True,
            },
            "assurance_hospitalisation": {
                "note": "Après 6 mois dans le secteur — via Constructiv",
                "obligatoire": True,
            },
            "pension_complementaire": {
                "note": "Pension complémentaire sectorielle — cotisation patronale mensuelle via Constructiv",
                "obligatoire": True,
                "anciennete_taux": "progressif selon ancienneté sectorielle",
            },
            "timbres_fidelite": {
                "note": "TIMBRES-FIDÉLITÉ : cotisation patronale ~18,8% sur brut → crédits congés intempéries + formation via Constructiv",
                "taux_patronal_approx": 0.188,
                "obligatoire": True,
            },
            "transport_train": {"taux": 0.718, "obligatoire": True},
        },
        "conges": {
            "jours_legaux": 20,
            "prise_en_charge": "ONVA",
            "pecule_simple": 0.1027,
            "note": "Régime ouvrier — ONVA + Constructiv pour congés intempéries",
            "conges_intemperies": "Financés par Constructiv via timbres-fidélité",
        },
        "mentions_contrat": [
            "Loi du 3 juillet 1978 relative aux contrats de travail",
            "CCT Commission Paritaire 124 – Construction (CP 124)",
            "Classification des fonctions : CCT du 12 juin 2014 (n° 123570)",
            "Barèmes indexés trimestriellement — au 01/04/2026 : cat.I 18,39€/h",
            "Constructiv (ex-Fonds de Sécurité d'Existence Construction) : constructiv.be",
            "Régime timbres-fidélité obligatoire (AR n°213 du 26/09/1983)",
            "Assurance hospitalisation sectorielle après 6 mois d'ancienneté",
            "Pension complémentaire sectorielle obligatoire",
            "Avantage fiscal employeur (dispense PP 18%) si salaire brut ≥ 17,64€/h",
        ],
        "preavis": {
            "note": "Statut unique — mêmes délais légaux",
            "semaines_par_tranche": [
                (0, 3, 2), (3, 6, 4), (6, 9, 6), (9, 12, 7),
                (12, 18, 8), (18, 24, 9), (24, 36, 10), (36, 48, 12),
                (48, 60, 13), (60, 72, 15), (72, 84, 18), (84, 96, 21),
                (96, 108, 24), (108, 120, 27), (120, 999, 30),
            ],
            "unite": "semaines",
        },
        "regles_speciales": [
            "Indexation TRIMESTRIELLE (jan/avr/jul/oct) — vérifier Constructiv à chaque trimestre",
            "Régime flexible été (AR 213) : max 180h/an dérogation, rémunérées au taux normal",
            "Chef d'équipe : salaire min = +10% vs ouvrier le plus qualifié de l'équipe",
            "Timbres-fidélité : contribution ~18,8% patronale → déclaration via Constructiv obligatoire",
            "Dispense PP 18% si travail en équipe ≥2 personnes ET salaire ≥17,64€/h (2026)",
            "Amiante : supplément obligatoire + EPI spécifiques réglementés",
            "Pas de CDD de principe — CDI recommandé (CDD autorisé pour remplacement ou travaux définis)",
        ],
    },

    # ══════════════════════════════════════════════════════════════════
    # CP 121 — NETTOYAGE (ouvriers)
    # ══════════════════════════════════════════════════════════════════
    "CP 121": {
        "meta": {
            "nom": "Commission Paritaire 121 – Nettoyage",
            "type_travailleur": "ouvrier",
            "secteurs": ["Nettoyage industriel", "Nettoyage de bureaux", "Nettoyage de vitres", "Collecte déchets", "Car wash", "Ramonage"],
            "fonds_securite": "Fonds Social Nettoyage",
            "onss_categorie": "083",
            "regime_vacances": "ouvrier",
            "note": "Indexation SEMESTRIELLE (01/01 et 01/07). Semaine de 36h30 (pas 38h).",
        },
        "duree_travail": {
            "heures_semaine": 36.5,   # ATTENTION : 36h30 en nettoyage !
            "heures_jour": 7.3,
            "jours_semaine": 5,
            "regime": "fixe",
            "note": "IMPORTANT : 36h30/semaine (et non 38h). Heures sup au-delà de 36h30.",
        },
        "baremes": {
            # Au 01/01/2026 — indexation +0,56%
            "cat_1": {
                "horaire": 14.38,
                "mensuel": 2289.43,  # 14.38 × 159.17h (36h30/sem)
                "fonctions": ["Agent de nettoyage — nettoyage standard (bureaux, locaux)", "Nettoyage quotidien"],
            },
            "cat_2": {
                "horaire": 14.54,
                "mensuel": 2314.91,
                "fonctions": ["Agent nettoyage spécialisé", "Nettoyage avec produits spécifiques"],
            },
            "cat_3": {
                "horaire": 14.97,
                "mensuel": 2383.40,
                "fonctions": ["Agent nettoyage qualifié", "Polyvalent multi-techniques"],
            },
            "cat_4": {
                "horaire": 15.57,
                "mensuel": 2478.97,
                "fonctions": ["Laveur de vitres qualifié", "Travail en hauteur — fenêtres, lanterneaux"],
            },
            "cat_5": {
                "note": "Personnel de métier — régime de la CP compétente (électricien, plombier...)",
                "fonctions": ["Conducteur Clark/élévateur/Bobcat inclus"],
            },
            "cat_6": {
                "horaire": 14.38,
                "fonctions": ["Personnel Car Wash"],
            },
            "cat_7": {
                "horaire": 15.00,
                "fonctions": ["Ramoneur"],
            },
            "cat_8A": {
                "horaire": 14.70,
                "fonctions": ["Nettoyage industriel — catégorie de base"],
            },
            "etudiant": {
                "note": "Salaire minimum = catégorie exercée (pas de réduction spécifique étudiants en CP 121)",
                "horaire": 14.38,
            },
            "titres_services": {
                "note": "Régime titres-services : CCT spécifique — salaire min 14,38€/h (cat 1)",
                "horaire_min": 14.38,
            },
        },
        "indemnites": {
            "prime_fin_annee": {
                "taux": 0.09,  # 9% des salaires bruts déclarés à l'ONSS
                "note": "9% du brut ONSS — versée par le Fonds Social Nettoyage",
                "periode_reference": "01/07 N-1 au 30/06 N",
                "obligatoire": True,
            },
            "transport_train": {"taux": 0.718, "obligatoire": True},
            "vetements": {
                "note": "Vêtements de travail fournis et entretenus par l'employeur",
                "obligatoire": True,
            },
            "nuit": {
                "taux_majoration": 0.20,  # +20%
                "heures": "nuit (selon CCT)",
                "obligatoire": True,
            },
        },
        "conges": {
            "jours_legaux": 20,
            "prise_en_charge": "ONVA",
            "pecule_simple": 0.1027,
            "note": "Régime ouvrier — 20 jours base + congés récupération selon CCT",
        },
        "mentions_contrat": [
            "Loi du 3 juillet 1978 relative aux contrats de travail",
            "CCT Commission Paritaire 121 – Nettoyage",
            "Durée hebdomadaire : 36h30 (et non 38h)",
            "Indexation semestrielle : 01/01 et 01/07",
            "Prime de fin d'année : 9% des salaires bruts (Fonds Social Nettoyage)",
            "Vêtements de travail fournis et entretenus par l'employeur",
        ],
        "preavis": {
            "note": "Statut unique",
            "semaines_par_tranche": [
                (0, 3, 2), (3, 6, 4), (6, 9, 6), (9, 12, 7),
                (12, 18, 8), (18, 24, 9), (24, 36, 10), (36, 48, 12),
                (48, 60, 13), (60, 72, 15), (72, 84, 18), (84, 96, 21),
                (96, 108, 24), (108, 120, 27), (120, 999, 30),
            ],
            "unite": "semaines",
        },
        "regles_speciales": [
            "ATTENTION : 36h30/semaine — pas 38h ! Heures sup à partir de 36h31",
            "Indexation 2x/an : vérifier au 01/07/2026",
            "Titres-services : régime CCT spécifique — Dimona type STD ou autre selon cas",
            "Collecte déchets : régime de transition (temps d'attente chargement/déchargement ≤200h/an)",
            "Cat 4 laveur vitres : qualification obligatoire + vérification sécurité hauteur",
        ],
    },

    # ══════════════════════════════════════════════════════════════════
    # CP 140.03 — TRANSPORT ROUTIER ET LOGISTIQUE (ouvriers)
    # ══════════════════════════════════════════════════════════════════
    "CP 140.03": {
        "meta": {
            "nom": "Sous-commission paritaire 140.03 – Transport routier et logistique pour compte de tiers",
            "type_travailleur": "ouvrier",
            "secteurs": ["Transport de marchandises", "Logistique", "Distribution", "Messagerie", "Transport international"],
            "fonds_securite": "FSTL – Fonds Social Transport et Logistique (fstl.be)",
            "onss_categorie": "083",
            "regime_vacances": "ouvrier",
            "note": "Indexation annuelle au 01/01 (+2,18% en 2026). Classification 4 catégories + non-roulant.",
        },
        "duree_travail": {
            "heures_semaine": 38,
            "heures_jour": 7.6,
            "jours_semaine": 5,
            "regime": "variable",
            "note": "Régime transport : règlement CE 561/2006 pour le personnel roulant. Repos obligatoires.",
        },
        "baremes": {
            # Au 01/01/2026 — indexation +2,18%
            # Personnel ROULANT — 4 catégories selon type de véhicule et permis
            "cat_1_roulant": {
                "horaire": 17.45,
                "mensuel": 2874.34,
                "fonctions": ["Conducteur véhicule ≤3,5T", "Livreur", "Coursier"],
                "note": "Permis B — véhicules légers",
            },
            "cat_2_roulant": {
                "horaire": 18.12,
                "mensuel": 2984.57,
                "fonctions": ["Conducteur PL (>3,5T)", "Chauffeur camion porteur", "Conducteur citerne simple"],
                "note": "Permis C — poids lourds",
            },
            "cat_3_roulant": {
                "horaire": 18.80,
                "mensuel": 3096.60,
                "fonctions": ["Conducteur articulation (semi-remorque)", "Chauffeur grue auxiliaire", "Transport spécial"],
                "note": "Permis CE — semi-remorques",
            },
            "cat_4_roulant": {
                "horaire": 19.48,
                "mensuel": 3208.63,
                "fonctions": ["Conducteur transport exceptionnel", "Conducteur citerne spécialisée (ADR)", "Chef de convoi"],
                "note": "Permis spéciaux + ADR",
            },
            # Personnel NON-ROULANT (logistique, entrepôt)
            "non_roulant_A": {
                "horaire": 14.90,
                "mensuel": 2453.00,
                "fonctions": ["Manutentionnaire", "Préparateur commandes", "Aide logisticien"],
            },
            "non_roulant_B": {
                "horaire": 15.55,
                "mensuel": 2560.60,
                "fonctions": ["Cariste (CACES)", "Magasinier qualifié", "Opérateur logistique"],
            },
            "non_roulant_C": {
                "horaire": 16.20,
                "mensuel": 2667.00,
                "fonctions": ["Chef d'équipe logistique", "Gestionnaire stocks", "Dispatcher"],
            },
            "etudiant": {
                "note": "Salaire minimum = catégorie exercée. Après 6 mois → cat. de la fonction.",
                "horaire": 14.90,
                "note2": "Travailleur en formation : cat inférieure pendant max 6 mois, puis cat du véhicule conduit",
            },
        },
        "indemnites": {
            "cheques_repas": {
                "valeur": 3.09,
                "intervention_patronale_min": 2.00,
                "note": "Depuis 01/07/2026 — intervention patronale +2€ (employeurs n'ayant pas encore de chèques-repas)",
                "obligatoire": True,
            },
            "vetements": {
                "note": "Vêtements de travail fournis et entretenus par l'employeur (CCT historique depuis années 70)",
                "obligatoire": True,
            },
            "disponibilite": {
                "note": "Indemnité de disponibilité pour le personnel roulant (attentes chargement/déchargement)",
                "obligatoire": True,
            },
            "anciennete": {
                "note": "Indemnité d'ancienneté sectorielle progressive",
                "obligatoire": True,
            },
            "nuit": {
                "note": "Indemnité de nuit pour travail entre 20h et 6h",
                "obligatoire": True,
            },
            "sejour": {
                "note": "Indemnités de séjour pour découchers — montants selon CCT",
                "obligatoire": True,
            },
            "transport_train": {"taux": 0.718, "obligatoire": True},
            "tenue": {
                "note": "Indemnité de tenue (entretien uniforme)",
                "obligatoire": False,
            },
        },
        "conges": {
            "jours_legaux": 20,
            "prise_en_charge": "ONVA",
            "pecule_simple": 0.1027,
            "note": "Régime ouvrier",
        },
        "mentions_contrat": [
            "Loi du 3 juillet 1978 relative aux contrats de travail",
            "CCT Sous-commission paritaire 140.03 – Transport routier et logistique",
            "Règlement CE n° 561/2006 relatif aux temps de conduite et de repos (personnel roulant)",
            "Classification des fonctions : funct14003.be (catégories 1 à 4 + non-roulant)",
            "FSTL – Fonds Social Transport et Logistique : fstl.be",
            "Chèques-repas : 3,09€/jour (depuis 01/07/2026)",
            "Indexation annuelle au 01/01/2026 : +2,18%",
        ],
        "preavis": {
            "note": "Statut unique",
            "semaines_par_tranche": [
                (0, 3, 2), (3, 6, 4), (6, 9, 6), (9, 12, 7),
                (12, 18, 8), (18, 24, 9), (24, 36, 10), (36, 48, 12),
                (48, 60, 13), (60, 72, 15), (72, 84, 18), (84, 96, 21),
                (96, 108, 24), (108, 120, 27), (120, 999, 30),
            ],
            "unite": "semaines",
        },
        "regles_speciales": [
            "Personnel roulant : règlement CE 561/2006 — temps conduite max 9h/jour, 56h/semaine",
            "Tachygraphe obligatoire pour véhicules >3,5T — contrôle ONSS et SPF Mobilité",
            "ADR : permis spécial obligatoire pour transport matières dangereuses",
            "Classification fonctions : vérifier sur funct14003.be — 10 critères d'évaluation",
            "Chèques-repas : mise en place obligatoire depuis 01/07/2026 si pas déjà en place",
            "Formation continue obligatoire (CPC) pour permis C et CE : 35h/5 ans",
        ],
    },

}

# ══════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ══════════════════════════════════════════════════════════════════════

def get_cp(cp_key: str) -> dict:
    """Retourne les données d'une CP ou None si non trouvée."""
    return CP_DATABASE.get(cp_key)

def liste_cp() -> list:
    """Retourne la liste de toutes les CP disponibles."""
    return list(CP_DATABASE.keys())

def get_bareme_minimum(cp_key: str, categorie: str = None) -> dict:
    """Retourne le barème minimum d'une CP pour une catégorie donnée."""
    cp = CP_DATABASE.get(cp_key)
    if not cp:
        return {}
    baremes = cp.get("baremes", {})
    if categorie and categorie in baremes:
        return baremes[categorie]
    # Retourner le minimum général si pas de catégorie spécifiée
    return baremes.get("minimum_general", baremes.get("cat_I", baremes.get("classe_A", {})))

def calcul_preavis_semaines(cp_key: str, anciennete_mois: int) -> int:
    """Calcule le délai de préavis en semaines selon l'ancienneté."""
    cp = CP_DATABASE.get(cp_key)
    if not cp:
        return 0
    tranches = cp.get("preavis", {}).get("semaines_par_tranche", [])
    for (min_mois, max_mois, semaines) in tranches:
        if min_mois <= anciennete_mois < max_mois:
            return semaines
    return 30  # Maximum légal si ancienneté très longue

def get_heures_semaine(cp_key: str) -> float:
    """Retourne les heures hebdomadaires normales de la CP."""
    cp = CP_DATABASE.get(cp_key)
    if not cp:
        return 38.0
    return cp.get("duree_travail", {}).get("heures_semaine", 38.0)

def is_ouvrier(cp_key: str) -> bool:
    """Retourne True si la CP est un régime ouvrier."""
    cp = CP_DATABASE.get(cp_key)
    if not cp:
        return False
    return cp.get("meta", {}).get("type_travailleur") == "ouvrier"

if __name__ == "__main__":
    print("=== CP disponibles ===")
    for cp in liste_cp():
        data = CP_DATABASE[cp]
        print(f"  {cp} — {data['meta']['nom']}")
        print(f"    Type: {data['meta']['type_travailleur']} | Heures: {data['duree_travail']['heures_semaine']}h/sem")

