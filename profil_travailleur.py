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
from parametres_dates import get_bonus_emploi_params, get_reduction_structurelle_params, get_precompte_params
from datetime import date as _date

STATUTS_VALIDES = ('ouvrier', 'etudiant', 'employe')


@dataclass
class ProfilTravailleur:
    cp_key: str
    statut: str                      # 'ouvrier' | 'etudiant' | 'employe'
    type_contrat: str = 'CDI'        # 'CDI' | 'CDD' | 'STU' | ...
    heures_semaine: float = 38.0
    jours_semaine: int = 5
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
    def onss_personnel_taux(self) -> float:
        if self.is_etudiant:
            return ONSS['etudiant_personnel']
        return ONSS['personnel_taux']

    @property
    def onss_patronal_taux_base(self) -> float:
        """Taux ONSS patronal SANS coefficient — le coefficient 108% est appliqué séparément.
        Lu depuis regles_cp[cp]['onss_patronal_taux_base'] — chaque CP a son propre taux facial."""
        if self.is_etudiant:
            return ONSS['etudiant_patronal'] + ONSS['etudiant_fonds_amiante']
        return self.regles_cp.get('onss_patronal_taux_base', ONSS['patronal_taux_defaut'])

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

    def reduction_structurelle(self, onss_patronal_brut, base_salariale_mensuelle=None, reference_date=None):
        """Reduction structurelle DEGRESSIVE, parametres VERSIONNES PAR DATE
        (voir parametres_dates.py). Sans base_salariale_mensuelle, retombe
        sur l'ancien montant fixe (deprecated, imprecis)."""
        if not self.reduction_structurelle_applicable:
            return 0.0
        if base_salariale_mensuelle is None:
            return round(min(onss_patronal_brut,
                REDUCTION_STRUCTURELLE['ancien_montant_fixe_deprecated']), 2)

        ref = reference_date or _date.today()
        p = get_reduction_structurelle_params(ref)
        s_trim = base_salariale_mensuelle * 3
        terme_bas = max(0.0, p['coeff_bas'] * (p['seuil_bas'] - s_trim))
        terme_tres_bas = max(0.0, p['coeff_tres_bas'] * (p['seuil_tres_bas'] - s_trim))
        r_mensuel = round((terme_bas + terme_tres_bas) / 3, 2)
        return round(min(onss_patronal_brut, r_mensuel), 2)

    def reduction_premier_engagement(self, onss_patronal_apres_struct: float, ratio_temps_partiel: float = 1.0) -> float:
        if not self.premier_engagement_applicable:
            return 0.0
        plafond_mensuel = round(PREMIER_ENGAGEMENT['1er_travailleur_plafond_trim'] / 3, 2)
        plafond = round(plafond_mensuel * ratio_temps_partiel, 2)
        return round(min(plafond, max(0.0, onss_patronal_apres_struct)), 2)

    def precompte_brut(self, brut_imposable_mensuel: float, etat_civil: str = 'celibataire',
                        nb_enfants: int = 0, partenaire_revenus_pro: str = 'non',
                        reference_date=None) -> float:
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

        impot_final_annuel = max(0.0, impot - red_enfants)
        return round(impot_final_annuel / 12, 2)

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
                       heures_semaine: float = None, jours_semaine: int = 5) -> ProfilTravailleur:
    """Point d'entrée unique à appeler depuis app.py / moteur_paie.py.
    C'est CETTE fonction qui doit être appelée dès qu'on connaît le statut
    choisi dans le formulaire — tout le reste en découle."""
    return ProfilTravailleur(
        cp_key=cp_key,
        statut=statut,
        type_contrat=type_contrat,
        heures_semaine=heures_semaine or 38.0,
        jours_semaine=jours_semaine,
    )
