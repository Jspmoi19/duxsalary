"""
social_belgique.py — Logique sociale belge
Taux ONSS, précompte professionnel, jours fériés, codes journaliers
"""
from datetime import date, timedelta
from decimal import Decimal

# ── JOURS FÉRIÉS LÉGAUX BELGES ────────────────────────────────────────
def get_jours_feries(annee):
    """Retourne les 10 jours fériés légaux belges pour une année donnée."""
    jf = [
        date(annee, 1, 1),   # Nouvel An
        date(annee, 5, 1),   # Fête du Travail
        date(annee, 7, 21),  # Fête Nationale
        date(annee, 8, 15),  # Assomption
        date(annee, 11, 1),  # Toussaint
        date(annee, 11, 11), # Armistice
        date(annee, 12, 25), # Noël
    ]
    # Pâques (calcul algorithmique)
    paques = calcul_paques(annee)
    jf.append(paques)                           # Lundi de Pâques
    jf.append(date(annee, paques.month, paques.day) + timedelta(days=39))  # Ascension
    jf.append(paques + timedelta(days=49))      # Lundi de Pentecôte
    
    return sorted(jf)

def calcul_paques(annee):
    """Algorithme de Meeus/Jones/Butcher pour calculer Pâques."""
    a = annee % 19
    b = annee // 100
    c = annee % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mois = (h + l - 7 * m + 114) // 31
    jour = ((h + l - 7 * m + 114) % 31) + 1
    # Retourner le LUNDI de Pâques
    paques_dimanche = date(annee, mois, jour)
    return paques_dimanche + timedelta(days=1)

# ── CODES JOURNALIERS ─────────────────────────────────────────────────
CODES_JOURNALIERS = {
    # Prestations
    'P':   {'label': 'Presté', 'couleur': '#e8f5ee', 'texte': '#1a6b4a', 'paye': True, 'prestation': True},
    'S':   {'label': 'Samedi presté', 'couleur': '#d4edda', 'texte': '#155724', 'paye': True, 'prestation': True},
    'HS':  {'label': 'Heures supplémentaires', 'couleur': '#cce5ff', 'texte': '#004085', 'paye': True, 'prestation': True},
    # Congés payés
    'CL':  {'label': 'Congé légal', 'couleur': '#fff3cd', 'texte': '#856404', 'paye': True, 'prestation': False},
    'CE':  {'label': 'Congé extra-légal', 'couleur': '#ffeeba', 'texte': '#856404', 'paye': True, 'prestation': False},
    'F':   {'label': 'Jour férié légal', 'couleur': '#d1ecf1', 'texte': '#0c5460', 'paye': True, 'prestation': False},
    'FM':  {'label': 'Férié compensatoire', 'couleur': '#bee5eb', 'texte': '#0c5460', 'paye': True, 'prestation': False},
    'PP':  {'label': 'Petit chômage', 'couleur': '#e2d9f3', 'texte': '#4a235a', 'paye': True, 'prestation': False},
    # Maladie / accident de droit commun: codes poses automatiquement depuis les episodes
    # d'incapacite du travailleur (salaire_garanti.py) -- une tranche par jour
    'MG':  {'label': 'Maladie – salaire garanti 100 %', 'couleur': '#f8d7da', 'texte': '#721c24', 'paye': True, 'prestation': False},
    'M2':  {'label': 'Maladie – 2e semaine (hors ONSS)', 'couleur': '#f5c2c7', 'texte': '#721c24', 'paye': True, 'prestation': False},
    'MC':  {'label': 'Maladie – complément jours 15 à 30', 'couleur': '#f1aeb5', 'texte': '#58151c', 'paye': True, 'prestation': False},
    'MM':  {'label': 'Maladie – mutuelle', 'couleur': '#e2e3e5', 'texte': '#58151c', 'paye': False, 'prestation': False},
    'MA':  {'label': 'Maladie sans épisode (non calculée)', 'couleur': '#f8d7da', 'texte': '#721c24', 'paye': True, 'prestation': False},
    'AC':  {'label': 'Accident du travail', 'couleur': '#f5c6cb', 'texte': '#721c24', 'paye': True, 'prestation': False},
    'MAT': {'label': 'Congé maternité', 'couleur': '#fce4ec', 'texte': '#880e4f', 'paye': True, 'prestation': False},
    'PAT': {'label': 'Congé paternité', 'couleur': '#e8eaf6', 'texte': '#283593', 'paye': True, 'prestation': False},
    'VP':  {'label': 'Vacances (ONVA)', 'couleur': '#fff9c4', 'texte': '#f57f17', 'paye': True, 'prestation': False},
    # Non payés
    'CNP': {'label': 'Congé sans solde', 'couleur': '#f5f5f5', 'texte': '#757575', 'paye': False, 'prestation': False},
    'IN':  {'label': 'Absence injustifiée', 'couleur': '#ffcdd2', 'texte': '#b71c1c', 'paye': False, 'prestation': False},
    # Chômage
    'CT':  {'label': 'Chômage temporaire', 'couleur': '#ffe0b2', 'texte': '#e65100', 'paye': False, 'prestation': False},
    'CI':  {'label': 'Chômage intempéries', 'couleur': '#fff8e1', 'texte': '#f57f17', 'paye': False, 'prestation': False},
    # Spécial
    'WE':  {'label': 'Week-end', 'couleur': '#eceff1', 'texte': '#90a4ae', 'paye': False, 'prestation': False},
    'HD':  {'label': 'Hors Dimona', 'couleur': '#eeeeee', 'texte': '#bdbdbd', 'paye': False, 'prestation': False},
}

# ── TAUX ONSS 2026 ────────────────────────────────────────────────────
TAUX_ONSS = {
    'employe': {
        'personnel': 0.1307,
        'patronal': 0.2500,  # Taux de base (avant réductions)
        'reduction_structurelle_base': 0.0,  # Calculée selon salaire
    },
    'ouvrier': {
        'personnel': 0.1307,
        'patronal': 0.2700,  # Légèrement supérieur aux employés
        'vacances_onva': 0.1027,  # Cotisation vacances annuelles ouvriers
    },
    'etudiant': {
        'personnel': 0.0271,
        'patronal': 0.0542,
    },
    'flexi': {
        'personnel': 0.0,
        'patronal': 0.2500,
    }
}

def calcul_reduction_structurelle(salaire_mensuel_brut, statut='employe'):
    """
    Calcul de la réduction structurelle ONSS (R1 et R2).
    Montants 2026 — simplification linéaire.
    """
    if statut == 'etudiant':
        return 0.0
    
    # Réduction de base (R1) — tous employeurs
    # Formule : R = 0.2714 × S - min(519.29, R)
    # Pour salaires < 4200€ : réduction maximale ~440€/trimestre
    if salaire_mensuel_brut <= 1800:
        reduction = 442.34  # Max trimestriel / 3
    elif salaire_mensuel_brut <= 2500:
        reduction = max(0, 442.34 - (salaire_mensuel_brut - 1800) * 0.3)
    elif salaire_mensuel_brut <= 4200:
        reduction = max(0, 230 - (salaire_mensuel_brut - 2500) * 0.1)
    else:
        reduction = 0
    
    return round(reduction / 3, 2)  # Mensuel

def calcul_onss(salaire_brut, statut='employe', annee=2026):
    """Calcule les cotisations ONSS complètes."""
    taux = TAUX_ONSS.get(statut, TAUX_ONSS['employe'])
    
    onss_personnel = round(salaire_brut * taux['personnel'], 2)
    onss_patronal_base = round(salaire_brut * taux['patronal'], 2)
    
    # Réduction structurelle (uniquement employe/ouvrier)
    reduction = calcul_reduction_structurelle(salaire_brut, statut) if statut not in ['etudiant','flexi'] else 0
    onss_patronal_net = max(0, round(onss_patronal_base - reduction, 2))
    
    # Pécule vacances ouvriers
    pecule_vacances = 0
    if statut == 'ouvrier':
        pecule_vacances = round(salaire_brut * taux.get('vacances_onva', 0), 2)
    
    imposable = round(salaire_brut - onss_personnel, 2)
    
    return {
        'onss_personnel': onss_personnel,
        'onss_patronal_base': onss_patronal_base,
        'reduction_structurelle': reduction,
        'onss_patronal_net': onss_patronal_net,
        'pecule_vacances_onva': pecule_vacances,
        'imposable': imposable,
        'total_onss': round(onss_personnel + onss_patronal_net, 2),
        'cout_employeur': round(salaire_brut + onss_patronal_net + pecule_vacances, 2),
    }

# ── PRÉCOMPTE PROFESSIONNEL (Annexe III SPF Finances 2026) ────────────
def calcul_precompte(salaire_mensuel_imposable, situation_familiale='isole', personnes_charge=0):
    """
    Calcul du précompte professionnel mensuel selon barèmes 2026.
    Situations : isole, marie_deux_revenus, marie_un_revenu, isole_enfant
    """
    s = salaire_mensuel_imposable
    
    if situation_familiale == 'isole':
        # Isolé sans charge
        if s <= 1945:
            pp = 0
        elif s <= 2345:
            pp = (s - 1945) * 0.2625
        elif s <= 2720:
            pp = (s - 2345) * 0.3575 + 105
        elif s <= 4500:
            pp = (s - 2720) * 0.4225 + 239.19
        elif s <= 7170:
            pp = (s - 4500) * 0.4825 + 991.84
        else:
            pp = (s - 7170) * 0.535 + 2280.59
            
    elif situation_familiale == 'marie_deux_revenus':
        # Marié/cohabitant légal — deux revenus
        if s <= 2345:
            pp = 0
        elif s <= 2720:
            pp = (s - 2345) * 0.2625
        elif s <= 4500:
            pp = (s - 2720) * 0.3575 + 98.44
        elif s <= 7170:
            pp = (s - 4500) * 0.4225 + 734.09
        else:
            pp = (s - 7170) * 0.4825 + 1862.24
            
    elif situation_familiale == 'marie_un_revenu':
        # Marié/cohabitant — seul revenu du ménage
        if s <= 2720:
            pp = 0
        elif s <= 4500:
            pp = (s - 2720) * 0.2625
        elif s <= 7170:
            pp = (s - 4500) * 0.3575 + 467.25
        else:
            pp = (s - 7170) * 0.4225 + 1421.99
            
    elif situation_familiale == 'isole_enfant':
        # Parent isolé avec enfant(s) à charge
        if s <= 2345:
            pp = 0
        elif s <= 3120:
            pp = (s - 2345) * 0.1050
        elif s <= 4500:
            pp = (s - 3120) * 0.2625 + 81.38
        elif s <= 7170:
            pp = (s - 4500) * 0.3575 + 443.63
        else:
            pp = (s - 7170) * 0.4225 + 1397.98
    else:
        pp = 0
    
    pp = max(0, round(pp, 2))
    
    # Réduction pour personnes à charge
    reductions = {1: 37.50, 2: 75.00, 3: 150.00, 4: 225.00, 5: 300.00}
    if personnes_charge > 0:
        reduction_charge = reductions.get(min(personnes_charge, 5), 300.00)
        pp = max(0, round(pp - reduction_charge, 2))
    
    return pp

def calcul_paie_complet(salaire_horaire, heures_prestees, statut='employe',
                         situation_familiale='isole', personnes_charge=0,
                         heures_semaine=38):
    """
    Calcul complet de la paie mensuelle.
    Retourne tous les montants pour la fiche de paie.
    """
    brut = round(salaire_horaire * heures_prestees, 2)
    
    onss = calcul_onss(brut, statut)
    
    pp = calcul_precompte(onss['imposable'], situation_familiale, personnes_charge)
    
    net = round(onss['imposable'] - pp, 2)
    
    return {
        'salaire_brut': brut,
        'heures_prestees': heures_prestees,
        'onss_personnel': onss['onss_personnel'],
        'onss_patronal_base': onss['onss_patronal_base'],
        'reduction_structurelle': onss['reduction_structurelle'],
        'onss_patronal_net': onss['onss_patronal_net'],
        'pecule_vacances_onva': onss['pecule_vacances_onva'],
        'imposable': onss['imposable'],
        'precompte': pp,
        'net': net,
        'cout_employeur': onss['cout_employeur'],
        'total_onss_a_verser': round(onss['onss_personnel'] + onss['onss_patronal_net'], 2),
    }

if __name__ == "__main__":
    # Test
    jf = get_jours_feries(2026)
    print("Jours fériés 2026:", [j.strftime('%d/%m') for j in jf])
    
    calc = calcul_paie_complet(18.39, 160, 'ouvrier', 'marie_deux_revenus', 1)
    print("\nTest paie ouvrier CP124 :")
    for k, v in calc.items():
        print(f"  {k}: {v}")
