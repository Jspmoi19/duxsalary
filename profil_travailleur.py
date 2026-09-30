# -*- coding: utf-8 -*-
"""
profil_travailleur.py — DuxSalary
Point d'entrée UNIQUE pour déterminer le comportement de paie d'un travailleur.

Principe: le statut (ouvrier / étudiant / employé) + la CP déterminent
TOUT le reste automatiquement. Rien n'est décidé ailleurs dans le moteur.

Utilisation:
    profil = construire_profil('CP 140.03', 'ouvrier', type_contrat='CDD')
    profil.calcul_salaire_base(...)
    profil.onss_patronal_taux
    profil.applique_bonus_emploi
    etc.
"""

from dataclasses import dataclass, field
from regles_cp import get_regles_cp, ONSS, REDUCTION_STRUCTURELLE, PREMIER_ENGAGEMENT, BONUS_EMPLOI, PRECOMPTE, CSSS
from parametres_dates import get_bonus_emploi_params, get_reduction_structurelle_params, get_precompte_params, get_premier_engagement_params, get_css_params
from datetime import date as _date
from onss_taux import get_taux_onss

STATUTS_VALIDES = ('ouvrier', 'etudiant', 'employe')


@dataclass
class ProfilTravailleur:
    cp_key: str
    statut: str                      # 'ouvrier' | 'etudiant' | 'employe'
    type_contrat: str = 'CDI'        # 'CDI' | 'CDD' | 'STU' | ...
    heures_semaine: float = 38.0
    jours_semaine: int = 5
    reference_date: object = None     # periode de la fiche -> trimestre ONSS
    categorie_employeur: str = '000'  # categorie ONSS de l'employeur (dossier)
    regles_cp: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.statut not in STATUTS_VALIDES:
            raise ValueError(f"Statut '{self.statut}' invalide. Attendu: {STATUTS_VALIDES}")
        self.regles_cp = get_regles_cp(self.cp_key)
        if not self.heures_semaine:
            self.heures_semaine = self.regles_cp.get('heures_semaine_defaut', 38.0)

    # ── PROPRIÉTÉS DÉRIVÉES — tout le reste du moteur consulte CES propriétés,
    #    jamais des if is_ouvrier/is_etudiant éparpillés ────────────────────

    @property
    def is_ouvrier(self) -> bool:
        return self.statut == 'ouvrier'

    @property
    def is_etudiant(self) -> bool:
        return self.statut == 'etudiant'

    @property
    def is_employe(self) -> bool:
        return self.statut == 'employe'

    @property
    def salaire_est_mensuel_fixe(self) -> bool:
        """Employé CDI/CDD temps plein → salaire mensuel fixe, pas calculé sur heures.
        Ouvrier et étudiant → toujours calculé sur jours/heures réellement prestés."""
        return self.is_employe and self.type_contrat in ('CDI', 'CDD')

    @property
    def coeff_base_onss_patronal(self) -> float:
        """Coefficient appliqué à la base ONSS patronale (108% ouvrier, 100% sinon)."""
        if self.is_ouvrier and not self.is_etudiant:
            return ONSS['coeff_ouvrier']
        return 1.0

    @property
    def onss_officiel(self) -> dict:
        """Taux ONSS officiels du trimestre de la fiche (fichiers TechLib),
        avec tracabilite: trimestre utilise, report eventuel si le fichier
        du trimestre n'est pas encore publie."""
        return get_taux_onss(self.statut, self.reference_date or _date.today(),
                             categorie=self.categorie_employeur or '000')

    @property
    def onss_personnel_taux(self) -> float:
        return self.onss_officiel['personnel']

    @property
    def onss_patronal_taux_base(self) -> float:
        """Taux patronal SANS coefficient 108% (applique separement).
        = cotisation patronale de base + moderation salariale
          + pour les ouvriers: cotisation trimestrielle vacances annuelles
            (code 253, 5.57% au 2026/3 -- partie de la cotisation patronale
            de base selon les Instructions ONSS 2026/3).
        Remplace l'ancien taux par CP (27% CP 140.03) qui n'avait pas de
        source officielle (corrige le 30/09/2026)."""
        t = self.onss_officiel
        return round(t['patronal_base'] + t['moderation_salariale'] + t['vacances_trimestrielle'], 6)

    @property
    def onss_patronal_reductible_taux(self) -> float:
        """Part patronale sur laquelle les reductions PEUVENT s'appliquer:
        cotisation de base + moderation. Instructions ONSS 2026/3: la
        cotisation vacances ouvriers (code 253) n'entre PAS dans le plafond."""
        t = self.onss_officiel
        return round(t['patronal_base'] + t['moderation_salariale'], 6)

    @property
    def onss_vacances_trimestrielle_taux(self) -> float:
        """Cotisation trimestrielle vacances ouvriers (code 253): due en entier."""
        return self.onss_officiel['vacances_trimestrielle']

    @property
    def vacances_annuelles_taux(self) -> float:
        """Cotisation ANNUELLE vacances ouvriers (10.27% en 2026), facturee
        par avis de debit l'annee suivante -- a provisionner dans le cout."""
        return self.onss_officiel['vacances_annuelle']

    @property
    def reduction_structurelle_applicable(self) -> bool:
        """La réduction structurelle NE S'APPLIQUE JAMAIS aux étudiants."""
        return not self.is_etudiant

    @property
    def premier_engagement_applicable(self) -> bool:
        """Confirmé: le premier engagement ne s'applique jamais aux étudiants."""
        if self.is_etudiant:
            return False
        return PREMIER_ENGAGEMENT.get('applicable_etudiant', False) or not self.is_etudiant

    @property
    def bonus_emploi_applicable(self) -> bool:
        return not self.is_etudiant

    @property
    def bonus_emploi_volet_b_applicable(self) -> bool:
        """Volet B du bonus emploi: OUVRIERS SEULEMENT, jamais employé ni étudiant."""
        return self.is_ouvrier and not self.is_etudiant

    @property
    def precompte_applicable(self) -> bool:
        """Le précompte professionnel est toujours 0 pour un étudiant STU."""
        return not self.is_etudiant

    @property
    def css_applicable(self) -> bool:
        return not self.is_etudiant

    @property
    def avantage_repas_soumis_onss(self) -> dict | None:
        """Retourne le dict de règle avantage repas de la CP, ou None si non applicable."""
        ar = self.regles_cp.get('avantage_repas', {})
        return ar if ar.get('applicable') else None

    @property
    def cheques_repas_regle(self) -> dict:
        return self.regles_cp.get('cheques_repas', {})

    @property
    def rgpt_regle(self) -> dict | None:
        r = self.regles_cp.get('rgpt', {})
        return r if r.get('applicable') else None

    @property
    def libelle_salaire_base(self) -> str:
        """Ce que la fiche doit afficher en en-tête — JAMAIS d'horaire pour un employé fixe."""
        return "Salaire mensuel de base" if self.salaire_est_mensuel_fixe else "Salaire de base"

    # ── CALCULS ──────────────────────────────────────────────────────────

    def base_onss_patronale(self, brut_onss: float) -> float:
        """Base de calcul ONSS patronal, après coefficient (108% ouvrier)."""
        return round(brut_onss * self.coeff_base_onss_patronal, 2)

    def onss_patronal_brut(self, brut_onss: float) -> float:
        base = self.base_onss_patronale(brut_onss)
        return round(base * self.onss_patronal_taux_base, 2)

    def onss_personnel(self, brut_onss: float) -> float:
        return round(brut_onss * self.onss_personnel_taux, 2)

    def bonus_emploi(self, salaire_propre_etp_mensuel, ratio_temps_partiel=1.0,
                      onss_du=None, reference_date=None):
        """Bonus a l'emploi -- structure 2024+, parametres VERSIONNES PAR DATE
        (voir parametres_dates.py). reference_date = date de la periode de
        paie (periode_fin recommande) -- si omise, utilise la date du jour
        (comportement de secours, a eviter pour regenerer une fiche passee)."""
        if not self.bonus_emploi_applicable:
            return 0.0, 0.0
        ref = reference_date or _date.today()
        params = get_bonus_emploi_params(ref)
        statut_key = 'ouvrier' if self.is_ouvrier else 'employe'
        s = salaire_propre_etp_mensuel

        def montant_volet(p):
            if s <= p['seuil_bas']:
                m = p['montant_max']
            elif s <= p['seuil_haut']:
                m = p['montant_max'] - (p['pente'] * (s - p['seuil_bas']))
            else:
                m = 0.0
            return max(0.0, round(m, 2))

        volet_a = round(montant_volet(params['volet_a'][statut_key]) * ratio_temps_partiel, 2)
        volet_b = round(montant_volet(params['volet_b'][statut_key]) * ratio_temps_partiel, 2)

        if onss_du is not None and (volet_a + volet_b) > onss_du:
            exces = round((volet_a + volet_b) - onss_du, 2)
            reduction_b = min(volet_b, exces)
            volet_b = round(volet_b - reduction_b, 2)
            exces_restant = round(exces - reduction_b, 2)
            if exces_restant > 0:
                volet_a = round(max(0.0, volet_a - exces_restant), 2)

        return volet_a, volet_b

    def reduction_precompte_bonus(self, bonus_a: float, bonus_b: float, brut_imposable: float,
                                   reference_date=None) -> float:
        """Reduction precompte sur bonus emploi -- DEUX taux distincts:
        33.14% sur le volet A, 52.54% sur le volet B (ouvriers uniquement,
        jamais nul pour un employe). Confirme par 4 sources independantes
        le 29/09/2026 -- avant cette correction, le code appliquait a tort
        33.14% aux deux volets combines."""
        if not self.precompte_applicable:
            return 0.0
        if brut_imposable > BONUS_EMPLOI['reduction_precompte_plafond_imposable']:
            return 0.0
        P = get_precompte_params(reference_date or _date.today())
        red_a = bonus_a * P['reduction_precompte_taux_volet_a']
        red_b = bonus_b * P['reduction_precompte_taux_volet_b']
        return round(red_a + red_b, 2)

    # ── Reductions ONSS patronales: formules OFFICIELLES (Instructions ONSS
    #    2026/3, p.375-383 et 404-405), verifiees le 30/09/2026 ──────────────

    @staticmethod
    def _r2(x):
        """Arrondi officiel ONSS a l'eurocent: 0,005 arrondi vers le haut."""
        from decimal import Decimal, ROUND_HALF_UP
        return float(Decimal(str(x)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

    def _prestation(self, jours_payes=None, heures_payees=None):
        """Retourne (facteur_S, mu) pour la periode de la fiche.
        - declaration en jours (employe a salaire fixe): S = W x (13 x D / J),
          mu = J / (13 x D)
        - declaration en heures (ouvrier, temps partiel): S = W x (13 x U / H),
          mu = H / (13 x U), U = heures hebdomadaires du travailleur de reference
        Adaptation MENSUELLE (la regle ONSS est trimestrielle): J/H du mois,
        mu rapporte a un tiers de trimestre. Verifie contre Group S."""
        if self.salaire_est_mensuel_fixe and jours_payes:
            D = self.jours_semaine or 5
            facteur = self._r2(13 * D / jours_payes)
            mu = self._r2(jours_payes / (13 * D / 3))
        elif heures_payees:
            U = self.heures_semaine or 38.0
            facteur = self._r2(13 * U / heures_payees)
            mu = self._r2(heures_payees / (13 * U / 3))
        else:
            return None, None
        return facteur, mu

    @staticmethod
    def _beta(mu, structurelle=True):
        """Facteur de multiplication (jamais arrondi). Instructions p.377."""
        base, pente = (1.18, 0.28) if structurelle else (1.0, 1.0)
        if mu < 0.55:
            return base
        if mu < 0.80:
            return base + (mu - 0.55) * pente
        return 1 / mu   # prestations >= 80%: reduction complete

    def reduction_structurelle(self, onss_patronal_brut, base_salariale_mensuelle=None,
                                reference_date=None, remuneration_mois=None,
                                jours_payes=None, heures_payees=None):
        """Reduction structurelle mensuelle: Ps = R x mu x beta_s, R calcule
        sur le salaire de reference S (W a 100%, ramene temps plein).
        Plafonnee aux cotisations patronales sur lesquelles elle s'applique.
        Sans remuneration_mois + jours/heures: ancien calcul (deprecated)."""
        if not self.reduction_structurelle_applicable:
            return 0.0
        ref = reference_date or self.reference_date or _date.today()
        facteur, mu = (self._prestation(jours_payes, heures_payees)
                       if remuneration_mois is not None else (None, None))
        if facteur is None:
            if base_salariale_mensuelle is None:
                return round(min(onss_patronal_brut,
                    REDUCTION_STRUCTURELLE['ancien_montant_fixe_deprecated']), 2)
            p = get_reduction_structurelle_params(ref)
            s_trim = base_salariale_mensuelle * 3
            r = max(0.0, p['coeff_bas'] * (p['seuil_bas'] - s_trim)) + \
                max(0.0, p['coeff_tres_bas'] * (p['seuil_tres_bas'] - s_trim))
            return round(min(onss_patronal_brut, r / 3), 2)

        p = get_reduction_structurelle_params(ref)
        S = self._r2(remuneration_mois * facteur)
        R = max(0.0, self._r2(p['coeff_bas'] * (p['seuil_bas'] - S))) + \
            max(0.0, self._r2(p['coeff_tres_bas'] * (p['seuil_tres_bas'] - S)))
        ps_mensuel = self._r2(R * mu * self._beta(mu, True) / 3)
        return round(min(onss_patronal_brut, ps_mensuel), 2)

    def reduction_premier_engagement(self, onss_patronal_apres_struct, ratio_temps_partiel=1.0,
                                      reference_date=None, jours_payes=None, heures_payees=None):
        """Premier engagement (1er travailleur): Pg = G x mu x beta_g par
        trimestre, G = 2.000EUR depuis le 01/07/2026 (3.100EUR avant).
        Jamais pour un etudiant. Sans jours/heures: ancien calcul (deprecated)."""
        if not self.premier_engagement_applicable:
            return 0.0
        ref = reference_date or self.reference_date or _date.today()
        G = get_premier_engagement_params(ref)['forfait_1er_trimestriel']
        _, mu = self._prestation(jours_payes, heures_payees)
        if mu is None:
            pg = self._r2(G / 3 * ratio_temps_partiel)
        else:
            pg = self._r2(G * mu * self._beta(mu, False) / 3)
        return round(min(pg, max(0.0, onss_patronal_apres_struct)), 2)

    @staticmethod
    def _reductions_autres_charges(P, couple_un_revenu, charges):
        """Annexes 4 (isole / conjoint avec revenus) et 5 (conjoint sans revenus)
        de la formule-cle. Retourne [(libelle, montant annuel)]."""
        ch = charges or {}
        R = P['reductions_autres_charges']
        res = []
        if ch.get('parent_isole') and not couple_un_revenu and ch.get('etat_civil_isole', True):
            res.append(("Réduction parent isolé avec enfant à charge", R['parent_isole']))
        if ch.get('handicape'):
            res.append(("Réduction travailleur handicapé", R['handicape']))
        if ch.get('conjoint_handicape') and couple_un_revenu:
            res.append(("Réduction conjoint handicapé", R['conjoint_handicape']))
        n_dep = int(ch.get('nb_personnes_charge_dependance') or 0)
        if n_dep:
            res.append((f"Personnes à charge 65+ dépendantes ({n_dep})", n_dep * R['personne_charge_dependance']))
        n_aut = int(ch.get('nb_autres_personnes_charge') or 0)
        if n_aut:
            res.append((f"Autres personnes à charge ({n_aut})", n_aut * R['autre_personne_charge']))
        return res

    def precompte_detail(self, brut_imposable_mensuel, etat_civil='celibataire', nb_enfants=0,
                         partenaire_revenus_pro='non', reference_date=None, charges=None):
        """Etapes du calcul du precompte (formule-cle SPF), pour affichage.
        Doit toujours donner le meme resultat que precompte_brut (teste)."""
        if not self.precompte_applicable:
            return {'applicable': False, 'precompte_mensuel': 0.0, 'etapes': []}
        P = get_precompte_params(reference_date or self.reference_date or _date.today())
        annuel = brut_imposable_mensuel * 12
        frais = min(annuel * P['frais_forfaitaires_taux'], P['frais_forfaitaires_plafond_annuel'])
        net = max(0.0, annuel - frais)
        def tranches(base):
            impot = 0.0
            for bas, haut, taux, fixe in P['tranches_annuelles']:
                if base <= bas: break
                h = min(base, haut) if haut != float('inf') else base
                impot = fixe + (h - bas) * taux
            return impot
        couple = etat_civil in ('marie', 'cohabitation_legale') and partenaire_revenus_pro == 'non'
        etapes = [("Revenu imposable annuel", round(annuel, 2)),
                  ("Frais professionnels forfaitaires (30%, plafond)", -round(frais, 2)),
                  ("Revenu net imposable annuel", round(net, 2))]
        if couple:
            pc = round(min(net * P['quotient_conjugal_taux'], P['quotient_conjugal_plafond_annuel']), 2)
            i1, i2 = round(tranches(net - pc), 2), round(tranches(pc), 2)
            etapes += [("Quotient conjugal attribué au conjoint", pc),
                       ("Impôt sur la part du travailleur", i1), ("Impôt sur la part du conjoint", i2),
                       ("Réduction de base couple", -P['reduction_base_couple_annuelle'])]
            impot = max(0.0, i1 + i2 - P['reduction_base_couple_annuelle'])
        else:
            ib = round(tranches(net), 2)
            etapes += [("Impôt selon les tranches", ib), ("Réduction de base isolé", -P['reduction_base_isole_annuelle'])]
            impot = max(0.0, ib - P['reduction_base_isole_annuelle'])
        red_enf = P['reduction_enfants_charge'].get(min(nb_enfants, 8), 0.0)
        if nb_enfants > 8:
            red_enf += (nb_enfants - 8) * P['reduction_enfant_supplementaire_au_dela_8']
        if red_enf:
            etapes.append((f"Réduction enfants à charge ({nb_enfants})", -red_enf))
        autres = self._reductions_autres_charges(P, couple, dict(charges or {}, etat_civil_isole=etat_civil not in ('marie', 'cohabitation_legale')))
        for lib, mt in autres:
            etapes.append((lib, -mt))
        annuel_final = max(0.0, impot - red_enf - sum(mt for _, mt in autres))
        etapes.append(("Impôt annuel", round(annuel_final, 2)))
        return {'applicable': True, 'annee_fiscale': P['annee'], 'source': P['source'],
                'etapes': etapes, 'precompte_mensuel': round(annuel_final / 12, 2)}

    def precompte_exceptionnel(self, montant_imposable, remuneration_annuelle_normale,
                               nature='autres', reference_date=None):
        """Precompte sur allocation exceptionnelle (prime, 13e mois, double pecule).
        nature: 'double_pecule' ou 'autres'. Taux lu sur la remuneration annuelle
        brute NORMALE, applique en une fois (bareme en escalier, pas progressif).
        Retourne (precompte, taux)."""
        if not self.precompte_applicable or montant_imposable <= 0:
            return 0.0, 0.0
        P = get_precompte_params(reference_date or self.reference_date or _date.today())
        r = max(0.0, remuneration_annuelle_normale or 0.0)
        for bas, haut, t_dp, t_autres in P['allocations_exceptionnelles']:
            if bas <= r < haut or haut == float('inf'):
                taux = t_dp if nature == 'double_pecule' else t_autres
                return self._r2(montant_imposable * taux), taux
        return 0.0, 0.0

    def precompte_brut(self, brut_imposable_mensuel: float, etat_civil: str = 'celibataire',
                        nb_enfants: int = 0, partenaire_revenus_pro: str = 'non',
                        reference_date=None, charges=None) -> float:
        """Precompte professionnel -- formule-cle officielle (Annexe III, depuis 2023).
        Formule verifiee le 29/09/2026 via execution reelle du simulateur Excel
        verrouille du SPF Finances (pas une reconstitution manuelle).
        Deux mecanismes distincts selon la situation familiale:
        - isole (ou marie/cohabitant dont le conjoint a aussi des revenus propres):
          impot = tranches(revenu net imposable) - 2987.98EUR, une fois.
        - marie/cohabitant dont le conjoint N'A PAS de revenus propres: quotient
          conjugal -- le revenu est scinde en deux parts imposees separement,
          puis 5975.96EUR (le double) est soustrait de la somme des deux impots.
        """
        if not self.precompte_applicable:
            return 0.0

        # Parametres de l'ANNEE FISCALE de la periode (versionnes, voir
        # parametres_dates.PRECOMPTE_VERSIONS) -- erreur explicite si absents
        P = get_precompte_params(reference_date or _date.today())

        annuel_imposable = brut_imposable_mensuel * 12
        frais = min(annuel_imposable * P['frais_forfaitaires_taux'],
                    P['frais_forfaitaires_plafond_annuel'])
        revenu_net_imposable = max(0.0, annuel_imposable - frais)

        def impot_tranches(base):
            impot = 0.0
            for bas, haut, taux, fixe_cumule in P['tranches_annuelles']:
                if base <= bas:
                    break
                tranche_haut = min(base, haut) if haut != float('inf') else base
                impot = fixe_cumule + (tranche_haut - bas) * taux
            return impot

        etats_couple = ('marie', 'cohabitation_legale')
        conjoint_sans_revenus = (etat_civil in etats_couple and partenaire_revenus_pro == 'non')

        if conjoint_sans_revenus:
            part_conjoint = round(min(revenu_net_imposable * P['quotient_conjugal_taux'],
                                       P['quotient_conjugal_plafond_annuel']), 2)
            part_travailleur = revenu_net_imposable - part_conjoint
            impot_total = round(impot_tranches(part_travailleur), 2) + round(impot_tranches(part_conjoint), 2)
            impot = max(0.0, impot_total - P['reduction_base_couple_annuelle'])
        else:
            impot_brut = round(impot_tranches(revenu_net_imposable), 2)
            impot = max(0.0, impot_brut - P['reduction_base_isole_annuelle'])

        red_enfants = P['reduction_enfants_charge'].get(min(nb_enfants, 8), 0.0)
        if nb_enfants > 8:
            red_enfants += (nb_enfants - 8) * P['reduction_enfant_supplementaire_au_dela_8']

        autres = self._reductions_autres_charges(P, conjoint_sans_revenus,
                    dict(charges or {}, etat_civil_isole=etat_civil not in etats_couple))
        impot_final_annuel = max(0.0, impot - red_enfants - sum(mt for _, mt in autres))
        return round(impot_final_annuel / 12, 2)

    def css_mensuelle(self, remuneration_brute_mensuelle, etat_civil='celibataire',
                      partenaire_revenus_pro='non', reference_date=None):
        """Cotisation speciale de securite sociale, retenue MENSUELLE selon le
        bareme officiel (Instructions ONSS 2026/3 p.336-337). Base: remuneration
        brute declaree (108% ouvriers). Tranche selon la remuneration trimestrielle
        (= mensuelle x 3, methode des 2 premiers mois du trimestre)."""
        if not self.css_applicable:
            return 0.0
        C = get_css_params(reference_date or self.reference_date or _date.today())
        m = max(0.0, remuneration_brute_mensuelle or 0.0)
        q = m * 3
        couple = etat_civil in ('marie', 'cohabitation_legale')
        if not couple:
            for q_min, q_max, fixe, taux, seuil in C['individuelle']:
                if q_min <= q <= q_max or (q_max == float('inf') and q > q_min):
                    return self._r2(fixe / 3 + taux * max(0.0, m - seuil))
            return 0.0
        if partenaire_revenus_pro == 'oui':
            fq_min, fq_max, forfait = C['couple_deux_revenus']['forfait']
            t1 = C['couple_deux_revenus']['tranche_1']
            t2 = C['couple_deux_revenus']['tranche_2']
            if fq_min <= q < fq_max:
                return self._r2(forfait / 3)
            if t1[0] <= q <= t1[1]:
                return self._r2(max(t1[2] * (m - t1[3]), t1[4] / 3))
            if q > t2[0]:
                return self._r2(min(t2[1] / 3 + t2[2] * (m - t2[3]), t2[4] / 3))
            return 0.0
        t1 = C['couple_un_revenu']['tranche_1']
        t2 = C['couple_un_revenu']['tranche_2']
        if t1[0] <= q <= t1[1]:
            return self._r2(t1[2] * (m - t1[3]))
        if q > t2[0]:
            return self._r2(min(t2[1] / 3 + t2[2] * (m - t2[3]), t2[4] / 3))
        return 0.0

    def css(self, brut_imposable_mensuel: float) -> float:
        if not self.css_applicable:
            return 0.0
        b = brut_imposable_mensuel
        if b <= 1945.38:
            return 0.0
        elif b <= 2190.19:
            return round((b - 1945.38) * 0.076, 2)
        elif b <= 6038.82:
            return round(18.60 + (b - 2190.19) * 0.011, 2)
        return 60.94


def construire_profil(cp_key: str, statut: str, type_contrat: str = 'CDI',
                       heures_semaine: float = None, jours_semaine: int = 5,
                       reference_date=None, categorie_employeur: str = '000') -> ProfilTravailleur:
    """Point d'entrée unique à appeler depuis app.py / moteur_paie.py.
    C'est CETTE fonction qui doit être appelée dès qu'on connaît le statut
    choisi dans le formulaire — tout le reste en découle."""
    return ProfilTravailleur(
        cp_key=cp_key,
        statut=statut,
        type_contrat=type_contrat,
        heures_semaine=heures_semaine or 38.0,
        jours_semaine=jours_semaine,
        reference_date=reference_date,
        categorie_employeur=categorie_employeur or '000',
    )
