# -*- coding: utf-8 -*-
"""
pecule_vacances.py — DuxSalary
Calcul du double pecule de vacances EMPLOYE, integre a la fiche de paie
du mois de versement (typiquement mai ou juin).

Structure validee contre une fiche de paie REELLE (Liantis/SD Worx,
juin 2024, CP 336, employe) fournie par l'utilisateur:
  - "double pecule de vacances sur salaire fixe"        2.274,87 EUR
  - "double pecule de vacances conventionnel"             187,34 EUR (CP 336)
  - "reten. double pec vac" (13,07%)                     -297,33 EUR
  - "precompte professionnel vacances"                   -786,72 EUR
Verification: 297,33 / 0,1307 = 2.274,87 -> ce montant affiche sur la
fiche est la PART SOUMISE (85/92 du brut), pas le brut total. Le pecule
brut reel etait donc d'environ 2.462 EUR (2.274,87 x 92/85).
Regle confirmee par Securex ("a savoir 85% de ce pecule de vacances") et
par les Instructions administratives ONSS ("la base de calcul correspond
au montant brut multiplie par la fraction 85/92").

REGLE CLE (confirmee ONSS + calculateur-de-salaire.be):
le double pecule vaut 92% du brut mensuel, mais se decompose en:
  - 85% soumis a la retenue speciale de 13,07%
  - 7%  (a partir du 3e jour de la 4e semaine) NON soumis a cette retenue
Le TOUT reste imposable (precompte exceptionnel sur le brut - retenue).

⚠️ LIMITE CONNUE: le bareme du precompte "allocations exceptionnelles"
pour les EMPLOYES (0% a 53,50% selon la remuneration annuelle brute, en
escalier) n'est PAS implemente -- les valeurs exactes des tranches n'ont
pas pu etre recuperees d'une source officielle. Le module retourne donc
le brut et l'imposable, mais laisse le precompte a saisir manuellement.
Pour les OUVRIERS, les taux SONT connus (17,16% / 23,22%) mais le pecule
ouvrier est paye par l'ONVA, pas par l'employeur -- donc hors fiche de paie.

Sources: Instructions administratives ONSS 2026/2 (retenue 13,07%),
ONVA (taux ouvriers 2026), Securex, calculateur-de-salaire.be.
Verifie le 29/09/2026.
"""

RETENUE_DOUBLE_PECULE = 0.1307      # taux identique aux cotisations ONSS ordinaires
PART_SOUMISE_RETENUE = 85.0 / 92.0  # 85% des 92% subissent la retenue
POURCENTAGE_DOUBLE_PECULE = 0.92    # 92% du brut mensuel


def calculer_double_pecule_employe(salaire_mensuel_brut: float,
                                     mois_prestes_annee_reference: int,
                                     complement_conventionnel: float = 0.0) -> dict:
    """Calcule le double pecule d'un EMPLOYE, a integrer dans la fiche de
    paie du mois de versement.

    salaire_mensuel_brut: brut du mois OU le pecule est verse (pas celui de
        l'annee de reference -- specificite du regime employe).
    mois_prestes_annee_reference: mois ouvrant droit durant l'annee N-1
        (ATTENTION: les mois sous contrat etudiant ne comptent pas, voir
        conges_legaux.mois_ouvrant_droit()).
    complement_conventionnel: complement sectoriel eventuel (ex: CP 336),
        NON soumis a la retenue de 13,07% -- a saisir manuellement car il
        depend de la CCT.
    """
    if mois_prestes_annee_reference <= 0:
        return {
            'droit': False,
            'pecule_brut': 0.0,
            'raison': "Aucun mois ouvrant droit durant l'annee de reference "
                       "(N-1). Pas de double pecule du.",
        }

    mois = min(12, mois_prestes_annee_reference)

    # Double pecule BRUT total = 92% du brut mensuel, proratise
    pecule_base = round(salaire_mensuel_brut * POURCENTAGE_DOUBLE_PECULE * mois / 12, 2)

    # REGLE CONFIRMEE (Securex + Instructions ONSS): seuls 85/92 du pecule
    # subissent la retenue speciale de 13,07%. La part restante (7/92, soit
    # la remuneration a partir du 3e jour de la 4e semaine) en est exemptee.
    # Sur une fiche de paie, c'est souvent la PART SOUMISE (85/92) qui est
    # affichee en ligne "double pecule sur salaire fixe" -- le brut total
    # n'apparait pas toujours tel quel.
    base_soumise = round(pecule_base * PART_SOUMISE_RETENUE, 2)
    part_exemptee = round(pecule_base - base_soumise, 2)
    retenue = round(base_soumise * RETENUE_DOUBLE_PECULE, 2)

    pecule_brut_total = round(pecule_base + complement_conventionnel, 2)
    imposable = round(pecule_brut_total - retenue, 2)

    return {
        'droit': True,
        'pecule_base': pecule_base,
        'complement_conventionnel': round(complement_conventionnel, 2),
        'pecule_brut_total': pecule_brut_total,
        'base_soumise_retenue': base_soumise,
        'part_exemptee_retenue': part_exemptee,
        'retenue_double_pecule': retenue,
        'montant_imposable': imposable,
        'mois_pris_en_compte': mois,
        'methode': (f"92% de {salaire_mensuel_brut:.2f}EUR x {mois}/12 mois"
                     + (f" + {complement_conventionnel:.2f}EUR conventionnel"
                        if complement_conventionnel else "")),
        # Le precompte n'est PAS calcule -- bareme exceptionnel non implemente
        'precompte_vacances': None,
        'montant_net': None,
        'avertissement': (
            "Le precompte professionnel sur pecule de vacances suit le bareme "
            "des ALLOCATIONS EXCEPTIONNELLES (0% a 53,50% selon la remuneration "
            "annuelle brute normale, en escalier). Ce bareme n'est pas implemente "
            "dans DuxSalary -- le montant doit etre saisi manuellement. "
            "Sur la fiche de reference (juin 2024, brut 2700EUR/mois), "
            "le precompte vacances etait de 786,72EUR pour un pecule brut de "
            "2462,21EUR, soit environ 32%."
        ),
    }


# Taux precompte pecule OUVRIER (connus, mais payes par l'ONVA -- informatif)
PRECOMPTE_OUVRIER_2026 = {
    'seuil': 1740.0,
    'taux_sous_seuil': 0.1716,
    'taux_au_dessus': 0.2322,
    'note': "Pecule ouvrier paye par l'ONVA, pas par l'employeur. "
             "Ces taux sont fournis a titre informatif uniquement.",
}
