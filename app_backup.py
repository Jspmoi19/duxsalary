from flask import Flask, render_template, request, send_file, session, redirect, url_for
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
import os
from datetime import datetime
import json

from cp_data import CP_DATABASE, get_heures_semaine, is_ouvrier, calcul_preavis_semaines
from contrats import generer_contrat_cdi, generer_contrat_cdd
from database import (init_db, get_all_dossiers, get_dossier, create_dossier,
                      get_travailleurs, get_travailleur, create_travailleur,
                      get_contrats, create_contrat, get_fiches_paie, create_fiche_paie)
from auth import login_required, authenticate
from cp_data import CP_DATABASE, liste_cp, calcul_preavis_semaines, is_ouvrier, get_heures_semaine
from contrats import generer_contrat_cdi, generer_contrat_cdd
app = Flask(__name__)
app.secret_key = 'payrolltool2026'
OUTPUT_DIR = "outputs"

# ─── PROFILS ─────────────────────────────────────────────────────────────────

PROFILS = {
    "eysel": {
        "nom": "Eysel Consult BV",
        "adresse": "Werkhuizenstraat 73, 1800 Vilvoorde",
        "bce": "1028.267.306",
        "rsz": "1078139-47",
        "representant": "Leo Plavmyzha, Gérant",
        "cp_disponibles": ["CP 336"],
        "couleur": "#1F4E79",
        "icon": "💼"
    },
    "fdlr": {
        "nom": "FDLR Logistics BV",
        "adresse": "À compléter",
        "bce": "À compléter",
        "rsz": "À compléter",
        "representant": "Leo Plavmyzha, Gérant",
        "cp_disponibles": ["CP 140.03"],
        "couleur": "#7B3F00",
        "icon": "🚛"
    },
    "duxcompta": {
        "nom": "Fiduciaire Duxcompta & Co",
        "adresse": "Sint-Amandsstraat 2, 1853 Grimbergen",
        "bce": "0798.198.053",
        "rsz": "À compléter",
        "representant": "Achraf El Harrak, Gérant",
        "cp_disponibles": ["CP 336", "CP 200", "CP 140.03", "CP 302", "CP 124", "CP 200"],
        "couleur": "#0F4C75",
        "icon": "🏢"
    }
}

# ─── DONNÉES CP ──────────────────────────────────────────────────────────────

CP_DATA = {
    "CP 336": {
        "nom_complet": "Commission Paritaire 336 – Professions libérales",
        "type": "employé",
        "salaire_min_mensuel": 2174.42,
        "salaire_min_etudiant_mensuel": 2065.70,
        "heures_semaine": 38,
        "preavis_employeur_moins1an": "4 semaines",
        "preavis_employeur_1a5ans": "8 semaines",
        "preavis_travailleur_moins1an": "2 semaines",
        "conges_legaux": 20,
        "fonds_formation": "Liberform (Fonds de formation CP 336)",
        "avantages": [
            "Intervention train : 80% du prix carte 2e classe (depuis 01/01/2026)",
            "Indemnité vélo : 0,32 €/km max 12,80 €/jour (depuis 01/10/2026)",
            "Congé de deuil : 12 jours (conjoint/enfant), 5 jours (parent)",
            "Crédit-temps fin de carrière : 1/5e ou mi-temps dès 55 ans",
            "Formation : 2,5 à 5 jours/ETP selon taille entreprise (Liberform)",
        ],
        "mentions_contrat": [
            "Loi du 3 juillet 1978 relative aux contrats de travail",
            "CCT n° 183459/CO/336 du 27 septembre 2023 relative au salaire mensuel minimum sectoriel",
            "Accord sectoriel CP 336 du 1er janvier 2025 au 31 décembre 2026",
            "Fonds de formation : Liberform – Fonds pour la formation des travailleurs de la CP 336",
        ],
        "onss_patronal_taux": 0.2500,
        "onss_personnel_taux": 0.1307,
        "onss_etudiant_patronal": 0.0542,
        "onss_etudiant_personnel": 0.0271,
    },
    "CP 140.03": {
        "nom_complet": "Sous-commission paritaire 140.03 – Transport routier et logistique pour compte de tiers",
        "type": "ouvrier",
        "salaire_min_mensuel": 2100.00,
        "salaire_min_etudiant_mensuel": 1995.00,
        "heures_semaine": 38,
        "preavis_employeur_moins1an": "Selon statut unique (semaine/ancienneté)",
        "preavis_travailleur_moins1an": "Selon statut unique",
        "conges_legaux": 20,
        "fonds_formation": "FSTL – Fonds Social Transport et Logistique",
        "avantages": [
            "Chèques-repas : 3,09 € par jour presté (depuis 01/07/2026, intervention patronale +2€)",
            "Vêtements de travail fournis et entretenus par l'employeur",
            "Indemnité de disponibilité, indemnité d'ancienneté, indemnité RGPT",
            "Supplément nuit, indemnités de séjour",
            "Classification fonctions : catégories 1 à 4 (funct14003.be)",
        ],
        "mentions_contrat": [
            "Loi du 3 juillet 1978 relative aux contrats de travail",
            "CCT SCP 140.03 – Transport routier et logistique pour compte de tiers",
            "Accord sectoriel 2025-2026 CP 140.03",
            "Fonds de sécurité d'existence : FSTL (catégorie ONSS 083)",
        ],
        "onss_patronal_taux": 0.2500,
        "onss_personnel_taux": 0.1307,
        "onss_etudiant_patronal": 0.0542,
        "onss_etudiant_personnel": 0.0271,
    },
    "CP 200": {
        "nom_complet": "Commission Paritaire auxiliaire pour employés (CP 200)",
        "type": "employé",
        "salaire_min_mensuel": 2189.81,
        "salaire_min_etudiant_mensuel": 2080.32,
        "heures_semaine": 38,
        "preavis_employeur_moins1an": "Selon statut unique",
        "preavis_travailleur_moins1an": "Selon statut unique",
        "conges_legaux": 20,
        "fonds_formation": "SFONDS 200 – Fonds sectoriel CP 200",
        "avantages": [
            "Prime annuelle : 330,84 € (indexée, payée en juin)",
            "Intervention train : 100% depuis 01/02/2026",
            "Indexation salaires : +2,21% au 01/01/2026",
        ],
        "mentions_contrat": [
            "Loi du 3 juillet 1978 relative aux contrats de travail",
            "CCT Commission paritaire auxiliaire pour employés (CP 200)",
            "Indexation : +2,21% au 01/01/2026",
        ],
        "onss_patronal_taux": 0.2500,
        "onss_personnel_taux": 0.1307,
        "onss_etudiant_patronal": 0.0542,
        "onss_etudiant_personnel": 0.0271,
    }
}

# ─── CALCUL PAIE ─────────────────────────────────────────────────────────────

def calcul_indemnite_transport(moyen, nb_jours, distance_km=0, cout_abonnement=0):
    """
    Calcule l'indemnité transport domicile-travail selon CP 336 2026.
    Toutes les indemnités transport sont exonérées ONSS et précompte.
    """
    indemnite = 0.0
    description = ""

    if moyen == "train":
        # CP 336 : 80% du prix carte train 2e classe
        indemnite = round(cout_abonnement * 0.80, 2)
        description = f"Train – 80% abonnement 2e classe ({cout_abonnement:.2f} €)"
    elif moyen == "bus_tram_metro":
        # Remboursement forfaitaire CCT n°19/11 (interprofessionnel)
        # Montant forfaitaire selon distance – simplifié : on prend le coût réel
        indemnite = round(cout_abonnement, 2)
        description = f"Transports publics urbains – remboursement abonnement ({cout_abonnement:.2f} €)"
    elif moyen == "velo":
        # CP 336 : 0,10€/km jusqu'au 30/09/2026, puis 0,32€/km dès 01/10/2026
        # On applique 0,10€/km (valeur juillet 2026)
        taux_velo = 0.10
        indemnite = round(taux_velo * distance_km * 2 * nb_jours, 2)  # aller-retour
        description = f"Vélo – {distance_km} km × 2 × {nb_jours} jours × {taux_velo} €/km"
    elif moyen == "voiture":
        # CP 336 : non obligatoire mais si accordé → max 0,4449€/km exonéré (tarif annuel jul/25-jun/26)
        taux_voiture = 0.4449
        indemnite = round(taux_voiture * distance_km * 2 * nb_jours, 2)
        description = f"Voiture – {distance_km} km × 2 × {nb_jours} jours × {taux_voiture} €/km (exonéré ONSS)"
    elif moyen == "aucun":
        indemnite = 0.0
        description = "Aucune intervention transport"

    return {"montant": indemnite, "description": description, "moyen": moyen, "exonere_onss": True}


def calcul_paie_etudiant(salaire_horaire, heures_jour, nb_jours, transport=None):
    heures_totales = round(heures_jour * nb_jours, 2)
    brut = round(salaire_horaire * heures_totales, 2)
    onss_personnel = round(brut * 0.0271, 2)
    net_avant_transport = round(brut - onss_personnel, 2)
    onss_patronal = round(brut * 0.0542, 2)

    # Transport exonéré ONSS → s'ajoute au net sans impact sur les cotisations
    transport_montant = transport['montant'] if transport else 0.0
    net = round(net_avant_transport + transport_montant, 2)
    cout_employeur = round(brut + onss_patronal + transport_montant, 2)
    total_onss = round(onss_personnel + onss_patronal, 2)

    return {
        "heures_totales": heures_totales,
        "nb_jours": nb_jours,
        "brut": brut,
        "onss_personnel": onss_personnel,
        "net_avant_transport": net_avant_transport,
        "transport_montant": transport_montant,
        "net": net,
        "onss_patronal": onss_patronal,
        "cout_employeur": cout_employeur,
        "total_onss": total_onss,
    }

# ─── FICHE DE PAIE PDF (style secrétariat social) ────────────────────────────

def generer_fiche_paie(data, calcul):
    filename = f"fiche_paie_{data['nom_etudiant'].replace(' ', '_')}_{data['date_debut'].replace('/', '')}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm,
                            leftMargin=1.8*cm, rightMargin=1.8*cm)

    BLUE = colors.HexColor('#1F4E79')
    DARK = colors.HexColor('#1a1a1a')
    GREY_BG = colors.HexColor('#f5f5f5')
    GREY_LINE = colors.HexColor('#cccccc')
    WHITE = colors.white
    BLACK = colors.black

    sN = ParagraphStyle('sN', fontName='Helvetica', fontSize=8, leading=11, textColor=DARK)
    sB = ParagraphStyle('sB', fontName='Helvetica-Bold', fontSize=8, leading=11, textColor=DARK)
    sT = ParagraphStyle('sT', fontName='Helvetica-Bold', fontSize=10, leading=13, textColor=WHITE)
    sR = ParagraphStyle('sR', fontName='Helvetica', fontSize=8, leading=11, textColor=DARK, alignment=TA_RIGHT)
    sRB = ParagraphStyle('sRB', fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=DARK, alignment=TA_RIGHT)
    sC = ParagraphStyle('sC', fontName='Helvetica', fontSize=8, leading=11, textColor=DARK, alignment=TA_CENTER)
    sCB = ParagraphStyle('sCB', fontName='Helvetica-Bold', fontSize=8, leading=11, textColor=DARK, alignment=TA_CENTER)
    sTitle = ParagraphStyle('sTitle', fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=WHITE, alignment=TA_RIGHT)
    sSub = ParagraphStyle('sSub', fontName='Helvetica', fontSize=7.5, leading=10, textColor=colors.HexColor('#555555'))
    sGrey = ParagraphStyle('sGrey', fontName='Helvetica-Bold', fontSize=7.5, leading=10, textColor=WHITE)

    elements = []
    W = 17.4*cm

    # ── BLOC EN-TÊTE ──
    header = Table([
        [
            Table([
                [Paragraph(f"<b>{data['nom_societe']}</b>", sB)],
                [Paragraph(data['adresse_societe'], sN)],
                [Paragraph(f"BCE : {data['bce_societe']}  |  N° RSZ : {data['rsz_societe']}", sN)],
                [Paragraph(f"Assurance accidents travail : {data.get('assurance_at', '—')}", sN)],
            ], colWidths=[9*cm], style=[('TOPPADDING',(0,0),(-1,-1),1),('BOTTOMPADDING',(0,0),(-1,-1),1)]),
            Table([
                [Paragraph("DÉCOMPTE DE RÉMUNÉRATION", sTitle)],
                [Paragraph(f"Période du {data['date_debut']} au {data['date_fin']}", ParagraphStyle('', fontName='Helvetica', fontSize=8, textColor=WHITE, alignment=TA_RIGHT))],
                [Paragraph(f"Date de calcul : {datetime.now().strftime('%d/%m/%Y')}", ParagraphStyle('', fontName='Helvetica', fontSize=7.5, textColor=colors.HexColor('#ccddee'), alignment=TA_RIGHT))],
                [Paragraph("Conservez soigneusement ce document.", ParagraphStyle('', fontName='Helvetica-Oblique', fontSize=7, textColor=colors.HexColor('#aabbcc'), alignment=TA_RIGHT))],
            ], colWidths=[8*cm], style=[('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2)]),
        ]
    ], colWidths=[9*cm, 8.4*cm])
    header.setStyle(TableStyle([
        ('BACKGROUND', (1,0), (1,0), BLUE),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (0,0), 0),
        ('LEFTPADDING', (1,0), (1,0), 8),
        ('RIGHTPADDING', (1,0), (1,0), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LINEBELOW', (0,0), (-1,0), 1, BLUE),
    ]))
    elements.append(header)
    elements.append(Spacer(1, 0.3*cm))

    # ── DONNÉES PERSONNELLES & CONTRAT ──
    ref = f"{data['rsz_societe']} / {data['niss_etudiant']}"
    bloc_pers = Table([
        [Paragraph(f"<b>{ref}</b>", sB), '', Paragraph("<b>Données personnelles :</b>", sB), Paragraph("<b>Données du contrat :</b>", sB)],
        ['', '', Paragraph(f"NISS : {data['niss_etudiant']}", sN), Paragraph(f"Statut : Étudiant(e) jobiste", sN)],
        [Paragraph(f"<b>CONFIDENTIEL</b>", ParagraphStyle('', fontName='Helvetica-Bold', fontSize=7.5, textColor=colors.HexColor('#cc0000'))), '', Paragraph(f"État civil : {data.get('etat_civil', '—')}", sN), Paragraph(f"Contrat : STU (Art. 121 L. 03/07/1978)", sN)],
        [Paragraph(f"<b>{data['nom_etudiant'].upper()}</b>", sB), '', Paragraph(f"Pers. à charge : {data.get('personnes_charge', 'aucune')}", sN), Paragraph(f"CP : {data['commission_paritaire']}", sN)],
        [Paragraph(data['adresse_etudiant'], sN), '', '', Paragraph(f"Fonction : {data['fonction']}", sN)],
    ], colWidths=[5.5*cm, 0.3*cm, 5.8*cm, 5.8*cm])
    bloc_pers.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LINEAFTER', (1,0), (1,-1), 0.5, GREY_LINE),
    ]))
    elements.append(bloc_pers)
    elements.append(Spacer(1, 0.2*cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=GREY_LINE))
    elements.append(Spacer(1, 0.2*cm))

    # ── SALAIRE DE BASE ──
    sal_base = calcul['brut']
    elements.append(Paragraph(f"Salaire de base : {sal_base:.2f} €  ({calcul['heures_totales']}h × {data['salaire_horaire']} €/h – {calcul['nb_jours']} jours ouvrables)", 
                               ParagraphStyle('', fontName='Helvetica-Oblique', fontSize=8, textColor=colors.HexColor('#555555'))))
    elements.append(Spacer(1, 0.15*cm))

    # ── TABLEAU PRESTATIONS ──
    prest_header = ['Code', 'Description', 'Jours', 'Heures', 'Montants']
    transport = data.get('transport', {'montant': 0, 'description': '', 'moyen': 'aucun'})
    prest_rows = [
        ['1100', 'Salaire de base étudiant', str(calcul['nb_jours']), f"{calcul['heures_totales']}h", f"{calcul['brut']:.2f}"],
    ]
    if transport['montant'] > 0:
        prest_rows.append(['4000', f"Indemnité transport ({transport['description']})", '', '', f"{transport['montant']:.2f}"])

    table_data = [prest_header] + prest_rows
    table_data.append(['', Paragraph('<b>Montant brut</b>', sB), '', '', Paragraph(f"<b>{calcul['brut']:.2f}</b>", sRB)])
    table_data.append(['2500', f"Cotisation de sécurité sociale (ONSS)   (Base: {calcul['brut']:.2f})", '', '', f"-{calcul['onss_personnel']:.2f}"])
    table_data.append(['', Paragraph('<b>Imposable</b>', sB), '', '', Paragraph(f"<b>{(calcul['brut'] - calcul['onss_personnel']):.2f}</b>", sRB)])
    table_data.append(['3000', "Précompte professionnel", '', '', "0,00"])
    if transport['montant'] > 0:
        table_data.append(['4000', f"Indemnité transport (exonérée ONSS et précompte)", '', '', f"+ {transport['montant']:.2f}"])
    table_data.append(['', '', '', '', ''])
    table_data.append(['', Paragraph('<b>Salaire net</b>', sB), '', '', Paragraph(f"<b>{calcul['net']:.2f}</b>", sRB)])

    col_w = [1.2*cm, 10*cm, 1.5*cm, 1.8*cm, 2.9*cm]
    prest_table = Table(table_data, colWidths=col_w)
    prest_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0,0), (-1,0), DARK),
        ('TEXTCOLOR', (0,0), (-1,0), WHITE),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
        ('ALIGN', (0,0), (1,-1), 'LEFT'),
        # Lignes alternées
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, GREY_BG]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        # Ligne montant brut
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#e8e8e8')),
        # Ligne imposable
        ('BACKGROUND', (0,4), (-1,4), colors.HexColor('#e8e8e8')),
        # Ligne salaire net
        ('BACKGROUND', (0,-1), (-1,-1), DARK),
        ('TEXTCOLOR', (0,-1), (-1,-1), WHITE),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.3, GREY_LINE),
    ]))
    elements.append(prest_table)
    elements.append(Spacer(1, 0.15*cm))

    # Mention net reporté
    net_box = Table([[
        Paragraph("net reporté", sSub),
        Paragraph(f"€ {calcul['net']:.2f}", ParagraphStyle('', fontName='Helvetica-Bold', fontSize=10, alignment=TA_RIGHT, textColor=DARK)),
    ]], colWidths=[14*cm, 3.4*cm])
    net_box.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,0), 1, DARK),
        ('LINEBELOW', (0,0), (-1,0), 1, DARK),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (1,0), (1,0), 0),
    ]))
    elements.append(net_box)
    elements.append(Spacer(1, 0.4*cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=GREY_LINE))
    elements.append(Spacer(1, 0.3*cm))

    # ── BLOC INFORMATIF (coût employeur) ──
    elements.append(Paragraph("Informatif", ParagraphStyle('', fontName='Helvetica-Bold', fontSize=8, textColor=BLUE)))
    info_data = [
        ["Coût salarial pour l'employeur", f"{calcul['cout_employeur']:.2f}"],
        ["Montant à charge de l'employeur (cotisations patronales)", f"-{calcul['onss_patronal']:.2f}"],
        ["Montant brut attribué au travailleur", f"{calcul['brut']:.2f}"],
        ["Montant net payé au travailleur", f"{calcul['net']:.2f}"],
    ]
    info_table = Table(info_data, colWidths=[13*cm, 4.4*cm])
    info_table.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('BOX', (0,0), (-1,-1), 0.5, GREY_LINE),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [GREY_BG, WHITE]),
        ('GRID', (0,0), (-1,-1), 0.3, GREY_LINE),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.3*cm))

    # ── DÉTAILS JOURS ──
    elements.append(Paragraph("Détails jours et heures de travail", ParagraphStyle('', fontName='Helvetica-Bold', fontSize=8, textColor=BLUE)))
    jours_data = [
        [Paragraph('<b>Code</b>', sCB), Paragraph('<b>Description</b>', sCB), Paragraph('<b>Jours</b>', sCB), Paragraph('<b>Heures</b>', sCB)],
        ['0100', 'Jours ouvrables prestés', str(calcul['nb_jours']), f"{calcul['heures_totales']}h"],
    ]
    jours_table = Table(jours_data, colWidths=[2*cm, 9*cm, 2.5*cm, 3.9*cm])
    jours_table.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ALIGN', (2,0), (-1,-1), 'CENTER'),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e0e0e0')),
        ('GRID', (0,0), (-1,-1), 0.3, GREY_LINE),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(jours_table)
    elements.append(Spacer(1, 0.5*cm))

    # ── PIED DE PAGE ──
    elements.append(HRFlowable(width="100%", thickness=0.5, color=GREY_LINE))
    footer = Table([[
        Paragraph(f"{data['nom_societe']}  |  BCE {data['bce_societe']}", sSub),
        Paragraph(f"Généré via PayrollTool  |  {datetime.now().strftime('%d/%m/%Y')}", ParagraphStyle('', fontName='Helvetica', fontSize=7, textColor=colors.grey, alignment=TA_RIGHT)),
    ]], colWidths=[10*cm, 7.4*cm])
    footer.setStyle(TableStyle([('TOPPADDING',(0,0),(-1,-1),3)]))
    elements.append(footer)

    doc.build(elements)
    return filepath, filename

# ─── CONTRAT ÉTUDIANT PDF ────────────────────────────────────────────────────

def generer_contrat_etudiant(data, cp_info):
    filename = f"contrat_etudiant_{data['nom_etudiant'].replace(' ', '_')}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=2.5*cm, rightMargin=2.5*cm)

    BLUE = colors.HexColor('#1F4E79')

    sN = ParagraphStyle('sN', fontName='Helvetica', fontSize=10, leading=14)
    sB = ParagraphStyle('sB', fontName='Helvetica-Bold', fontSize=10, leading=14)
    sT = ParagraphStyle('sT', fontName='Helvetica-Bold', fontSize=14, leading=20, alignment=TA_CENTER)
    sSub = ParagraphStyle('sSub', fontName='Helvetica-Bold', fontSize=11, leading=16, textColor=BLUE)
    sSm = ParagraphStyle('sSm', fontName='Helvetica', fontSize=9, leading=12)
    sC = ParagraphStyle('sC', fontName='Helvetica', fontSize=10, leading=14, alignment=TA_CENTER)
    sJ = ParagraphStyle('sJ', fontName='Helvetica', fontSize=10, leading=14, alignment=TA_JUSTIFY)

    elements = []

    # En-tête
    elements.append(Paragraph(f"<b>{data['nom_societe']}</b>", sB))
    elements.append(Paragraph(data['adresse_societe'], sN))
    elements.append(Paragraph(f"BCE : {data['bce_societe']}  |  N° RSZ : {data['rsz_societe']}", sN))
    elements.append(Spacer(1, 0.4*cm))
    elements.append(HRFlowable(width="100%", thickness=2, color=BLUE))
    elements.append(Spacer(1, 0.5*cm))

    # Titre
    elements.append(Paragraph("CONTRAT D'OCCUPATION D'ÉTUDIANT", sT))
    elements.append(Paragraph("Article 121 de la loi du 3 juillet 1978 relative aux contrats de travail", sC))
    elements.append(Spacer(1, 0.6*cm))

    # Parties
    elements.append(Paragraph("ENTRE LES SOUSSIGNÉS :", sSub))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(Paragraph("<b>L'EMPLOYEUR :</b>", sB))
    elements.append(Paragraph(
        f"{data['nom_societe']}, société à responsabilité limitée, dont le siège social est établi à "
        f"{data['adresse_societe']}, inscrite à la Banque-Carrefour des Entreprises sous le numéro "
        f"{data['bce_societe']}, identifiée à l'ONSS sous le numéro {data['rsz_societe']}, "
        f"représentée par {data['representant']}, ci-après dénommé « l'employeur »,", sJ))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(Paragraph("<b>D'UNE PART, ET :</b>", sB))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph("<b>L'ÉTUDIANT(E) :</b>", sB))

    info_data = [
        ["Nom et prénom :", f"<b>{data['nom_etudiant']}</b>"],
        ["Adresse :", data['adresse_etudiant']],
        ["Date de naissance :", data['ddn_etudiant']],
        ["N° registre national (NISS) :", data['niss_etudiant']],
        ["Établissement d'enseignement :", data['ecole_etudiant']],
    ]
    for label, val in info_data:
        elements.append(Paragraph(f"{label} <b>{val}</b>" if 'b>' not in val else f"{label} {val}", sN))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph("ci-après dénommé(e) « l'étudiant(e) »,", sN))
    elements.append(Spacer(1, 0.4*cm))
    elements.append(Paragraph("<b>D'AUTRE PART,</b>", sB))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph("Il a été convenu ce qui suit :", sN))
    elements.append(Spacer(1, 0.4*cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    elements.append(Spacer(1, 0.3*cm))

    # Articles
    articles = [
        ("Article 1 – Nature et durée du contrat",
         f"Le présent contrat est un contrat d'occupation d'étudiant conclu conformément à l'article 121 "
         f"et suivants de la loi du 3 juillet 1978 relative aux contrats de travail. Il est conclu pour une "
         f"durée déterminée du <b>{data['date_debut']}</b> au <b>{data['date_fin']}</b> inclus, soit "
         f"<b>{data['nb_jours']} jours ouvrables</b>. Le contrat prend fin de plein droit à l'échéance du terme, "
         f"sans qu'il soit nécessaire de donner un préavis."),

        ("Article 2 – Temps de travail",
         f"L'étudiant(e) est occupé(e) à raison de <b>{data['heures_jour']}h par jour</b> "
         f"({data['horaire_journalier']}), du lundi au vendredi, soit <b>38 heures par semaine</b>, "
         f"conformément au règlement de travail en vigueur dans l'entreprise et aux dispositions de la "
         f"Commission Paritaire {data['commission_paritaire']}."),

        ("Article 3 – Fonction et lieu de travail",
         f"L'étudiant(e) est engagé(e) en qualité de <b>{data['fonction']}</b> sous la supervision directe "
         f"de l'employeur ou de son délégué. Le travail sera effectué principalement au lieu suivant : "
         f"<b>{data['lieu_travail']}</b>, sans préjudice de déplacements ponctuels liés à la nature de la fonction."),

        ("Article 4 – Rémunération",
         f"La rémunération brute est fixée à <b>{data['salaire_horaire']} € brut de l'heure</b>, "
         f"conformément aux barèmes minimaux en vigueur dans la {data['commission_paritaire']}. "
         f"Sur ce salaire brut, il sera retenu une cotisation de solidarité ONSS de 2,71% "
         f"à charge de l'étudiant(e). Aucun précompte professionnel n'est retenu pour autant que le quota "
         f"annuel de 650 heures sous cotisations réduites ne soit pas dépassé. "
         f"Le salaire est payé par virement bancaire au compte de l'étudiant(e) au plus tard le dernier jour "
         f"de la période couverte par le contrat ou immédiatement après la fin de celui-ci."),

        ("Article 5 – Commission paritaire et droit applicable",
         f"Le présent contrat est régi par la <b>{cp_info['nom_complet']}</b>. "
         f"Les dispositions suivantes lui sont notamment applicables : " +
         " ; ".join(cp_info['mentions_contrat']) + "."),

        ("Article 6 – Déclaration immédiate à l'emploi (Dimona)",
         f"L'employeur déclare avoir effectué la déclaration Dimona de type STU auprès de l'ONSS avant "
         f"l'entrée en service de l'étudiant(e), conformément à l'article 38, §3 de la loi du "
         f"26 juillet 1996 portant modernisation de la sécurité sociale."),

        ("Article 7 – Quota d'heures et cotisations réduites",
         f"L'étudiant(e) déclare avoir vérifié son quota d'heures disponible sur Student@work "
         f"(www.studentatwork.be) et confirme disposer des heures nécessaires dans le cadre du régime "
         f"des 650 heures annuelles à cotisations réduites. L'étudiant(e) s'engage à informer "
         f"immédiatement l'employeur en cas de dépassement de ce quota."),

        ("Article 8 – Période d'essai",
         f"Conformément à l'article 130 de la loi du 3 juillet 1978, aucune période d'essai ne peut être "
         f"prévue dans un contrat d'occupation d'étudiant."),

        ("Article 9 – Rupture anticipée",
         f"Durant les trois premiers jours d'exécution du contrat, chacune des parties peut mettre fin au "
         f"contrat sans préavis ni indemnité. Après ces trois jours, la rupture anticipée du contrat par "
         f"l'une des parties donne droit à une indemnité équivalente au salaire correspondant à la moitié "
         f"de la durée du contrat restant à courir, conformément à l'article 124 de la loi du 3 juillet 1978."),

        ("Article 10 – Règlement de travail et obligations",
         f"L'étudiant(e) déclare avoir pris connaissance du règlement de travail de l'entreprise et "
         f"s'engage à le respecter. Il/elle est tenu(e) au respect des obligations de discrétion et de "
         f"confidentialité inhérentes à la nature des activités exercées, notamment en matière de données "
         f"clients et d'informations financières."),

        ("Article 10bis – Frais de transport domicile-lieu de travail",
         "L'étudiant(e) déclare utiliser le(s) moyen(s) de transport suivant(s) pour ses déplacements "
         "domicile-lieu de travail : <b>" + data.get('transport_description', 'à préciser') + "</b>. "
         "L'employeur intervient dans ces frais conformément aux dispositions de la "
         + data['commission_paritaire'] + " et de la CCT interprofessionnelle n° 19/11 du 8 avril 2024. "
         "L'indemnité de transport est exonérée de cotisations ONSS et de précompte professionnel "
         "dans les limites légales applicables. En cas de changement de moyen de transport, "
         "l'étudiant(e) en informera immédiatement l'employeur."),

        ("Article 11 – Assurance accidents du travail",
         f"L'étudiant(e) est couvert(e) par la police d'assurance accidents du travail souscrite par "
         f"l'employeur auprès de : <b>{data.get('assurance_at', '—')}</b>, conformément à la loi du "
         f"10 avril 1971 sur les accidents du travail."),
    ]

    for titre, texte in articles:
        elements.append(Paragraph(f"<b>{titre}</b>", sSub))
        elements.append(Spacer(1, 0.15*cm))
        elements.append(Paragraph(texte, sJ))
        elements.append(Spacer(1, 0.35*cm))

    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    elements.append(Spacer(1, 0.3*cm))

    elements.append(Paragraph(
        f"Fait à <b>{data['lieu_signature']}</b>, le <b>{data['date_signature']}</b>, "
        f"en deux exemplaires originaux, dont un exemplaire remis à chaque partie.", sN))
    elements.append(Spacer(1, 0.8*cm))

    sig_data = [
        [Paragraph("<b>L'EMPLOYEUR</b>", ParagraphStyle('', fontName='Helvetica-Bold', fontSize=10, alignment=TA_CENTER)),
         Paragraph("<b>L'ÉTUDIANT(E)</b>", ParagraphStyle('', fontName='Helvetica-Bold', fontSize=10, alignment=TA_CENTER))],
        [Paragraph(data['nom_societe'], sC), Paragraph(data['nom_etudiant'], sC)],
        [Paragraph(data['representant'], ParagraphStyle('', fontName='Helvetica', fontSize=9, alignment=TA_CENTER, textColor=colors.grey)), ''],
        [Spacer(1, 1.2*cm), Spacer(1, 1.2*cm)],
        [Paragraph("Signature et cachet :", sN), Paragraph("Signature :", sN)],
        [Spacer(1, 1*cm), Spacer(1, 1*cm)],
    ]
    sig_table = Table(sig_data, colWidths=[8.5*cm, 8.5*cm])
    sig_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('TOPPADDING', (0,0), (-1,-1), 4)]))
    elements.append(sig_table)

    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph(
        "Lu et approuvé – « Bon pour contrat d'occupation d'étudiant » – L'étudiant(e) reconnaît avoir "
        "reçu un exemplaire du présent contrat et du règlement de travail.", sSm))

    doc.build(elements)
    return filepath, filename

# ─── AVIS DE PAIEMENT ONSS PDF ───────────────────────────────────────────────

def generer_avis_onss(data, calcul):
    filename = f"avis_ONSS_{data['nom_etudiant'].replace(' ', '_')}_Q3_2026.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=2.5*cm, rightMargin=2.5*cm)

    BLUE = colors.HexColor('#1F4E79')
    ORANGE = colors.HexColor('#C0392B')
    GREY = colors.HexColor('#f5f5f5')

    sN = ParagraphStyle('sN', fontName='Helvetica', fontSize=10, leading=14)
    sB = ParagraphStyle('sB', fontName='Helvetica-Bold', fontSize=10, leading=14)
    sSm = ParagraphStyle('sSm', fontName='Helvetica', fontSize=9, leading=12)
    sT = ParagraphStyle('sT', fontName='Helvetica-Bold', fontSize=14, leading=20, alignment=TA_CENTER, textColor=BLUE)

    elements = []

    elements.append(Paragraph(f"<b>{data['nom_societe']}</b>", sB))
    elements.append(Paragraph(data['adresse_societe'], sN))
    elements.append(Paragraph(f"BCE : {data['bce_societe']}  |  N° RSZ : {data['rsz_societe']}", sN))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(HRFlowable(width="100%", thickness=2, color=BLUE))
    elements.append(Spacer(1, 0.4*cm))

    elements.append(Paragraph("AVIS DE PAIEMENT ONSS", sT))
    elements.append(Paragraph("3ème trimestre 2026 (Q3/2026) – Cotisations étudiant jobiste", 
                               ParagraphStyle('', fontName='Helvetica', fontSize=11, alignment=TA_CENTER, textColor=colors.grey)))
    elements.append(Spacer(1, 0.6*cm))

    # Travailleur concerné
    elements.append(Paragraph("<b>Travailleur concerné :</b>", sB))
    elements.append(Paragraph(f"{data['nom_etudiant']}  |  NISS : {data['niss_etudiant']}  |  Contrat : STU", sN))
    elements.append(Paragraph(f"Période : {data['date_debut']} → {data['date_fin']}  |  {calcul['nb_jours']} jours  |  {calcul['heures_totales']}h", sN))
    elements.append(Spacer(1, 0.4*cm))

    # Détail cotisations
    elements.append(Paragraph("<b>Détail des cotisations :</b>", sB))
    detail_data = [
        [Paragraph('<b>Description</b>', ParagraphStyle('', fontName='Helvetica-Bold', fontSize=9)),
         Paragraph('<b>Base</b>', ParagraphStyle('', fontName='Helvetica-Bold', fontSize=9, alignment=TA_RIGHT)),
         Paragraph('<b>Taux</b>', ParagraphStyle('', fontName='Helvetica-Bold', fontSize=9, alignment=TA_RIGHT)),
         Paragraph('<b>Montant</b>', ParagraphStyle('', fontName='Helvetica-Bold', fontSize=9, alignment=TA_RIGHT))],
        ["Cotisation patronale étudiant (à charge employeur)", f"{calcul['brut']:.2f} €", "5,42%", f"{calcul['onss_patronal']:.2f} €"],
        ["Cotisation de solidarité (retenue sur salaire étudiant)", f"{calcul['brut']:.2f} €", "2,71%", f"{calcul['onss_personnel']:.2f} €"],
        [Paragraph('<b>TOTAL À VERSER À L\'ONSS</b>', ParagraphStyle('', fontName='Helvetica-Bold', fontSize=10)),
         '', '',
         Paragraph(f"<b>{calcul['total_onss']:.2f} €</b>", ParagraphStyle('', fontName='Helvetica-Bold', fontSize=11, alignment=TA_RIGHT, textColor=ORANGE))],
    ]
    detail_table = Table(detail_data, colWidths=[9*cm, 2.5*cm, 2*cm, 3.5*cm])
    detail_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1F4E79')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [GREY, colors.white]),
        ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#fdecea')),
        ('LINEABOVE', (0,-1), (-1,-1), 1.5, ORANGE),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(detail_table)
    elements.append(Spacer(1, 0.5*cm))

    # Instructions de paiement
    elements.append(Paragraph("<b>Instructions de paiement :</b>", sB))
    elements.append(Spacer(1, 0.2*cm))

    pay_data = [
        ["Bénéficiaire :", "ONSS – Office National de Sécurité Sociale"],
        ["Compte ONSS :", "BE76 6790 0001 9009  (BNP Paribas Fortis)"],
        ["Montant :", f"{calcul['total_onss']:.2f} €"],
        ["Communication :", f"N° RSZ : {data['rsz_societe']}  –  Trimestre : 2026/3"],
        ["Date limite :", "31 octobre 2026"],
    ]
    pay_table = Table(pay_data, colWidths=[4*cm, 13*cm])
    pay_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [GREY, colors.white]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#fdecea')),
        ('FONTNAME', (0,4), (-1,4), 'Helvetica-Bold'),
        ('TEXTCOLOR', (1,4), (1,4), ORANGE),
    ]))
    elements.append(pay_table)
    elements.append(Spacer(1, 0.4*cm))

    elements.append(Paragraph(
        "⚠️  Important : Mentionnez obligatoirement la communication structurée lors du virement. "
        "En l'absence de cette communication, l'ONSS ne pourra pas identifier votre paiement.", 
        ParagraphStyle('', fontName='Helvetica-Oblique', fontSize=9, textColor=ORANGE)))
    elements.append(Spacer(1, 0.4*cm))
    elements.append(Paragraph(
        "Ce document est établi à titre informatif par l'employeur. Il ne remplace pas les documents officiels de l'ONSS. "
        "La DmfA Q3/2026 doit être introduite sur socialsecurity.be avant le 31/10/2026.", sSm))

    elements.append(Spacer(1, 0.4*cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph(
        f"Document généré le {datetime.now().strftime('%d/%m/%Y')} | {data['nom_societe']} | PayrollTool",
        ParagraphStyle('', fontName='Helvetica', fontSize=8, textColor=colors.grey, alignment=TA_CENTER)))

    doc.build(elements)
    return filepath, filename

# ─── ROUTES ──────────────────────────────────────────────────────────────────

@app.route('/')
def accueil():
    return render_template('accueil.html', profils=PROFILS)

@app.route('/profil/<profil_id>')
def dashboard(profil_id):
    if profil_id not in PROFILS:
        return redirect(url_for('accueil'))
    session['profil'] = profil_id
    profil = PROFILS[profil_id]
    return render_template('dashboard.html', profil=profil, profil_id=profil_id)

@app.route('/nouveau-contrat-etudiant')
def nouveau_contrat():
    profil_id = session.get('profil', 'eysel')
    profil = PROFILS[profil_id]
    cp_list = profil['cp_disponibles']
    cp_data_filtered = {k: v for k, v in CP_DATA.items() if k in cp_list}
    return render_template('contrat_etudiant.html', profil=profil, profil_id=profil_id, cp_data=cp_data_filtered)


@app.template_filter('basename')
def basename_filter(path):
    return os.path.basename(path) if path else ''

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = authenticate(request.form['email'], request.form['password'])
        if user:
            session['user_id'] = user['id']
            session['user_nom'] = user['nom']
            session['user_role'] = user['role']
            return redirect(url_for('dossiers'))
        return render_template('login.html', error='Email ou mot de passe incorrect.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return redirect(url_for('dossiers'))

@app.route('/dossiers')
@login_required
def dossiers():
    return render_template('dossiers.html', dossiers=get_all_dossiers())

@app.route('/dossier/nouveau', methods=['GET', 'POST'])
@login_required
def nouveau_dossier():
    if request.method == 'POST':
        did = create_dossier(request.form)
        return redirect(url_for('dossier_detail', dossier_id=did))
    return render_template('nouveau_dossier.html')

@app.route('/dossier/<int:dossier_id>')
@login_required
def dossier_detail(dossier_id):
    dossier = get_dossier(dossier_id)
    if not dossier:
        return redirect(url_for('dossiers'))
    tab = request.args.get('tab', 'travailleurs')
    return render_template('dossier_detail.html', dossier=dossier, tab=tab,
                           travailleurs=get_travailleurs(dossier_id),
                           contrats=get_contrats(dossier_id=dossier_id),
                           fiches=get_fiches_paie(dossier_id=dossier_id))

@app.route('/dossier/<int:dossier_id>/travailleur/nouveau', methods=['GET', 'POST'])
@login_required
def nouveau_travailleur(dossier_id):
    dossier = get_dossier(dossier_id)
    if request.method == 'POST':
        data = dict(request.form)
        data['dossier_id'] = dossier_id
        ddn = data.get('date_naissance', '')
        if ddn:
            try:
                p = ddn.split('/')
                data['date_naissance'] = f"{p[2]}-{p[1]}-{p[0]}"
            except:
                data['date_naissance'] = None
        create_travailleur(data)
        return redirect(url_for('dossier_detail', dossier_id=dossier_id))
    return render_template('nouveau_travailleur.html', dossier=dossier)

@app.route('/dossier/<int:dossier_id>/contrat/nouveau', methods=['GET', 'POST'])
@login_required
def nouveau_contrat_dossier(dossier_id):
    dossier = get_dossier(dossier_id)
    travailleurs = get_travailleurs(dossier_id)
    cp_json = json.dumps({k: {'meta': v['meta'], 'duree_travail': v['duree_travail'],
        'baremes': {cat: {kk: vv for kk, vv in val.items() if kk in ['horaire','mensuel','fonctions']}
                    for cat, val in v['baremes'].items() if isinstance(val, dict)}}
        for k, v in CP_DATABASE.items()})

    if request.method == 'POST':
        form = request.form
        travailleur_id = int(form['travailleur_id'])
        travailleur = get_travailleur(travailleur_id)
        type_contrat = form.get('type_contrat', 'CDI')
        ddn = travailleur.get('date_naissance')
        ddn_str = ddn.strftime('%d/%m/%Y') if ddn else '—'

        data = {
            'nom_societe': dossier['nom'], 'adresse_societe': dossier['adresse'] or '',
            'bce_societe': dossier['bce'] or '', 'rsz_societe': dossier['rsz'] or '',
            'representant': dossier['representant'] or '', 'assurance_at': dossier['assurance_at'] or '—',
            'nom_travailleur': f"{travailleur['prenom']} {travailleur['nom']}",
            'adresse_travailleur': travailleur['adresse'] or '', 'ddn_travailleur': ddn_str,
            'niss_travailleur': travailleur['niss'] or '', 'iban_travailleur': travailleur['iban'] or '',
            'date_debut': form['date_debut'], 'date_fin': form.get('date_fin', ''),
            'cp_key': form['cp_key'], 'temps_plein': form.get('temps_plein', '1') == '1',
            'fonction': form['fonction'], 'categorie': form.get('categorie', ''),
            'horaire_journalier': form.get('horaire_journalier', ''),
            'salaire_horaire': form.get('salaire_horaire', ''),
            'salaire_mensuel': form.get('salaire_mensuel', '').replace(' €', ''),
            'lieu_travail': form.get('lieu_travail', dossier['adresse'] or ''),
            'lieu_signature': form.get('lieu_signature', 'Bruxelles'),
            'date_signature': datetime.now().strftime('%d/%m/%Y'),
            'motif_cdd': form.get('motif_cdd', ''),
        }

        filepath, filename = (generer_contrat_cdi(data) if type_contrat == 'CDI' else generer_contrat_cdd(data))

        def pd(d):
            if not d: return None
            try:
                p = d.split('/'); return f"{p[2]}-{p[1]}-{p[0]}"
            except: return None

        create_contrat({'dossier_id': dossier_id, 'travailleur_id': travailleur_id,
            'type_contrat': type_contrat, 'cp_key': form['cp_key'],
            'fonction': form['fonction'], 'categorie': form.get('categorie'),
            'salaire_horaire': float(form.get('salaire_horaire', 0) or 0),
            'salaire_mensuel': float((form.get('salaire_mensuel') or '0').replace(' €','') or 0),
            'heures_semaine': get_heures_semaine(form['cp_key']),
            'horaire_journalier': form.get('horaire_journalier'),
            'lieu_travail': form.get('lieu_travail'),
            'date_debut': pd(form['date_debut']), 'date_fin': pd(form.get('date_fin')),
            'motif_cdd': form.get('motif_cdd'), 'temps_plein': form.get('temps_plein','1')=='1',
            'pdf_path': os.path.join(OUTPUT_DIR, filename)})

        cp_info = CP_DATABASE.get(form['cp_key'], {})
        return render_template('resultat_contrat.html', data=data, filename=filename,
                               type_contrat=type_contrat,
                               preavis=calcul_preavis_semaines(form['cp_key'], 0),
                               cp_info=cp_info, heures_sem=get_heures_semaine(form['cp_key']),
                               ouvrier=is_ouvrier(form['cp_key']),
                               profil=dossier, profil_id=dossier_id, dossier_id=dossier_id)

    return render_template('contrat_cdi_cdd.html', profil=dossier, profil_id=dossier_id,
                           dossier=dossier, travailleurs=travailleurs,
                           cp_data=CP_DATABASE, cp_json=cp_json)

@app.route('/dossier/<int:dossier_id>/fiche/nouvelle', methods=['GET', 'POST'])
@login_required
def nouvelle_fiche(dossier_id):
    dossier = get_dossier(dossier_id)
    travailleurs = get_travailleurs(dossier_id)
    if request.method == 'POST':
        form = request.form
        travailleur_id = int(form['travailleur_id'])
        travailleur = get_travailleur(travailleur_id)
        heures_jour = float(form.get('heures_jour', 7.6))
        nb_jours = int(form.get('nb_jours', 0))
        salaire_horaire = float(form.get('salaire_horaire', 0))
        transport_montant = float(form.get('transport_montant', 0) or 0)
        transport = {'montant': transport_montant, 'description': form.get('transport_desc',''), 'moyen': 'autre'}
        calcul = calcul_paie_etudiant(salaire_horaire, heures_jour, nb_jours, transport)
        data = {
            'nom_societe': dossier['nom'], 'adresse_societe': dossier['adresse'] or '',
            'bce_societe': dossier['bce'] or '', 'rsz_societe': dossier['rsz'] or '',
            'assurance_at': dossier['assurance_at'] or '—',
            'nom_etudiant': f"{travailleur['prenom']} {travailleur['nom']}",
            'niss_etudiant': travailleur['niss'] or '', 'adresse_etudiant': travailleur['adresse'] or '',
            'fonction': form.get('fonction', ''), 'commission_paritaire': form.get('cp_key', ''),
            'date_debut': form['date_debut'], 'date_fin': form['date_fin'],
            'salaire_horaire': str(salaire_horaire), 'transport': transport,
        }
        filepath, filename = generer_fiche_paie(data, calcul)
        def pd(d):
            if not d: return None
            try:
                p = d.split('/'); return f"{p[2]}-{p[1]}-{p[0]}"
            except: return None
        create_fiche_paie({'dossier_id': dossier_id, 'travailleur_id': travailleur_id, 'contrat_id': None,
            'periode_debut': pd(form['date_debut']), 'periode_fin': pd(form['date_fin']),
            'nb_jours': nb_jours, 'heures_totales': calcul['heures_totales'],
            'salaire_brut': calcul['brut'], 'onss_personnel': calcul['onss_personnel'],
            'precompte': 0, 'transport_montant': transport_montant,
            'salaire_net': calcul['net'], 'onss_patronal': calcul['onss_patronal'],
            'cout_employeur': calcul['cout_employeur'], 'total_onss': calcul['total_onss'],
            'pdf_path': os.path.join(OUTPUT_DIR, filename)})
        return redirect(url_for('dossier_detail', dossier_id=dossier_id, tab='fiches'))
    return render_template('nouvelle_fiche.html', dossier=dossier, travailleurs=travailleurs)

@app.route('/download/<filename>')
@login_required
def download(filename):
    filepath = os.path.join(OUTPUT_DIR, filename)
    return send_file(filepath, as_attachment=True)

if __name__ == '__main__':
    init_db()
    app.run(debug=False, host='0.0.0.0')
