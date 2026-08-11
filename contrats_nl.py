"""
contrats_nl.py — DuxSalary
Templates contrats en néerlandais pour la région flamande
"""

import os
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle, KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

try:
    pdfmetrics.registerFont(TTFont('DVSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('DVSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
    FN, FNB = 'DVSans', 'DVSans-Bold'
except:
    FN, FNB = 'Helvetica', 'Helvetica-Bold'

NAVY = colors.HexColor('#1F4E79')
DARK = colors.HexColor('#1a1a1a')
GRAY = colors.HexColor('#555555')
LINE = colors.HexColor('#cccccc')

OUTPUT_DIR = '/var/www/duxsalary/outputs'

def sN(size=10, bold=False, align=TA_LEFT):
    return ParagraphStyle('x', fontName=FNB if bold else FN,
                          fontSize=size, leading=size+4, textColor=DARK, alignment=align)

def p(text, size=10, bold=False, align=TA_LEFT, color=DARK):
    return Paragraph(str(text or ''), ParagraphStyle('x', fontName=FNB if bold else FN,
                     fontSize=size, leading=size+4, textColor=color, alignment=align))


def generer_contrat_cdd_nl(data):
    """Génère un contrat CDD en néerlandais (région flamande)."""
    filename = f"arbeidsovereenkomst_CDD_{data['nom_travailleur'].replace(' ','_')}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    heures_j = float(data.get('heures_jour', 7.6))
    jours_s = int(data.get('jours_semaine', 5))
    h_sem = round(heures_j * jours_s, 1)
    regime = f"{heures_j:.1f}u/dag × {jours_s} dagen = {h_sem:.1f}u/week"
    temps = 'voltijds' if h_sem >= 36 else 'deeltijds'
    cp_key = data.get('cp_key', '')

    doc = SimpleDocTemplate(filepath, pagesize=A4,
        topMargin=2*cm, bottomMargin=2*cm, leftMargin=2.5*cm, rightMargin=2.5*cm)
    e = []

    # EN-TÊTE
    e.append(p(data['nom_societe'], size=11, bold=True))
    e.append(p(data.get('adresse_societe', ''), size=9, color=GRAY))
    e.append(p(f"Ondernemingsnummer: {data.get('bce_societe','')}  |  RSZ: {data.get('rsz_societe','')}", size=9, color=GRAY))
    e.append(Spacer(1, 0.3*cm))
    e.append(HRFlowable(width='100%', thickness=2, color=NAVY))
    e.append(Spacer(1, 0.3*cm))
    e.append(p('ARBEIDSOVEREENKOMST VOOR BEPAALDE DUUR', size=14, bold=True, align=TA_CENTER))
    e.append(p(f"ARBEIDER — {cp_key}", size=10, align=TA_CENTER, color=GRAY))
    e.append(p("Wet van 3 juli 1978 betreffende de arbeidsovereenkomsten – Artikel 9", size=9, align=TA_CENTER, color=GRAY))
    e.append(Spacer(1, 0.5*cm))

    # PARTIJEN
    e.append(p("TUSSEN DE ONDERGETEKENDEN:", size=11, bold=True, color=NAVY))
    e.append(Spacer(1, 0.2*cm))
    e.append(p("<b>DE WERKGEVER:</b>", size=10))
    e.append(p(
        f"{data['nom_societe']}, vennootschap met beperkte aansprakelijkheid, "
        f"met maatschappelijke zetel te {data.get('adresse_societe','')}, "
        f"ingeschreven bij de KBO onder het nummer {data.get('bce_societe','')}, "
        f"geïdentificeerd bij de RSZ onder het nummer {data.get('rsz_societe','')}, "
        f"vertegenwoordigd door {data.get('representant','')}, hierna 'de werkgever' genoemd,",
        size=10, align=TA_JUSTIFY))
    e.append(Spacer(1, 0.2*cm))
    e.append(p("<b>EN DE WERKNEMER:</b>", size=10))
    for label, val in [
        ("Naam en voornaam:", f"<b>{data['nom_travailleur']}</b>"),
        ("Adres:", data.get('adresse_travailleur', '—')),
        ("Geboortedatum:", data.get('ddn_travailleur', '—')),
        ("Rijksregisternummer:", data.get('niss_travailleur', '—')),
    ]:
        e.append(p(f"{label} {val}", size=10))
    e.append(p("hierna 'de werknemer' genoemd,", size=10))
    e.append(Spacer(1, 0.3*cm))
    e.append(p("Werd het volgende overeengekomen:", size=10))
    e.append(Spacer(1, 0.3*cm))
    e.append(HRFlowable(width='100%', thickness=0.3, color=LINE))
    e.append(Spacer(1, 0.2*cm))

    def art(num, titre, texte):
        return KeepTogether([
            p(f"<b>Artikel {num} – {titre}</b>", size=11, color=NAVY),
            Spacer(1, 0.1*cm),
            p(texte, size=10, align=TA_JUSTIFY),
            Spacer(1, 0.3*cm),
        ])

    motif_nl = {
        'emploi saisonnier': 'seizoensarbeid',
        'accroissement temporaire de travail': 'tijdelijke vermeerdering van werk',
        'remplacement': 'vervanging van een vaste werknemer',
    }.get(data.get('motif_cdd', ''), data.get('motif_cdd', 'tijdelijk werk'))

    e.append(art("1", "Aard en duur van de overeenkomst",
        f"Deze overeenkomst is een arbeidsovereenkomst voor BEPAALDE DUUR (ABD), gesloten "
        f"overeenkomstig artikel 9 van de wet van 3 juli 1978. Ze wordt gesloten voor de periode "
        f"van <b>{data.get('date_debut','')}</b> tot en met <b>{data.get('date_fin','')}</b>. "
        f"De overeenkomst eindigt van rechtswege bij het verstrijken van de termijn, zonder dat een "
        f"opzeg vereist is. Reden: {motif_nl}."))

    e.append(art("2", "Rechtvaardiging van de ABD",
        f"Overeenkomstig artikel 10 van de wet van 3 juli 1978 is het sluiten van een "
        f"arbeidsovereenkomst voor bepaalde duur gerechtvaardigd door: {motif_nl}. "
        f"Bij gebrek aan een geldige reden of bij feitelijke voortzetting na de einddatum wordt de "
        f"overeenkomst van rechtswege omgezet in een overeenkomst voor onbepaalde duur. "
        f"Maximum 4 opeenvolgende ABD bij dezelfde werkgever voor een totale duur van 2 jaar."))

    e.append(art("3", "Statuut en paritair comité",
        f"De werknemer wordt aangeworven als <b>arbeider</b>. Deze overeenkomst wordt beheerst door "
        f"het <b>{cp_key}</b> en al zijn collectieve arbeidsovereenkomsten."))

    e.append(art("4", "Functie en arbeidsplaats",
        f"De werknemer wordt aangeworven als <b>{data.get('fonction','')}</b> "
        f"(categorie: {data.get('categorie','—')}). Arbeidsplaats: {data.get('lieu_travail', data.get('adresse_societe','—'))}."))

    e.append(art("5", "Arbeidsduur",
        f"De werknemer is {temps} tewerkgesteld, à rato van <b>{regime}</b> "
        f"({data.get('horaire_journalier','')}), overeenkomstig het arbeidsreglement."))

    e.append(art("6", "Bezoldiging",
        f"Het brutoloon bedraagt <b>{data.get('salaire_horaire','')} EUR bruto per uur</b>, "
        f"overeenkomstig de loonbarema's van het {cp_key}. "
        f"Betaling per bankoverschrijving, uiterlijk de laatste werkdag van de maand."))

    e.append(art("7", "Vroegtijdige beëindiging",
        f"Gedurende de eerste 6 maanden kan elke partij de overeenkomst beëindigen met een opzeg "
        f"berekend als voor een overeenkomst voor onbepaalde duur (2 weken voor de werkgever, "
        f"1 week voor de werknemer, tijdens de eerste 3 maanden). Na 6 maanden geeft vroegtijdige "
        f"beëindiging recht op een vergoeding gelijk aan het loon voor de helft van de resterende "
        f"duur (art. 40 wet 03/07/1978), behalve bij dringende reden."))

    e.append(art("8", "Verlenging",
        f"Deze overeenkomst kan worden verlengd binnen de grenzen van artikel 10bis van de wet "
        f"van 3 juli 1978: maximum 4 opeenvolgende overeenkomsten bij dezelfde werkgever voor "
        f"een totale gecumuleerde duur van maximum 2 jaar. Elke overschrijding leidt tot omzetting "
        f"in een overeenkomst voor onbepaalde duur."))

    e.append(art("9", "Arbeidsongevallenverzekering",
        f"De werknemer is gedekt door de wettelijk verplichte arbeidsongevallenverzekering van "
        f"de werkgever bij: {data.get('assurance_at', '—')} (wet van 10 april 1971)."))

    e.append(art("10", "Vertrouwelijkheid en arbeidsreglement",
        f"De werknemer verbindt zich ertoe de vertrouwelijkheid te bewaren en het arbeidsreglement "
        f"van de onderneming na te leven, waarvan hij/zij een exemplaar heeft ontvangen. "
        f"Dit reglement maakt integraal deel uit van deze overeenkomst."))

    e.append(art("11", "Toepasselijk recht",
        f"Deze overeenkomst wordt beheerst door het Belgisch recht. De Belgische "
        f"arbeidsrechtbanken zijn als enige bevoegd."))

    e.append(art("12", "Jaarlijkse vakantie (arbeiders)",
        f"Arbeidersstelsel: vakantiegeld berekend en uitbetaald door de RJV op basis van de "
        f"RSZ-bijdragen aangegeven door de werkgever (≈10,27% van het bruto)."))

    if '140' in cp_key:
        e.append(art("13", f"Bepalingen {cp_key} Transport",
            f"Rijdend personeel: verordening EG 561/2006. Maaltijdcheques 3,09€/dag. "
            f"Kledij voorzien. CPC-opleiding gehandhaafd."))

    # HANDTEKENINGEN
    e.append(Spacer(1, 0.5*cm))
    e.append(p(f"Opgesteld te {data.get('lieu_signature','Brussel')}, op {data.get('date_signature', datetime.now().strftime('%d/%m/%Y'))}, "
               f"in twee originele exemplaren, waarvan één voor elke partij.", size=9))
    e.append(Spacer(1, 0.5*cm))

    sig = Table([[
        p(f"<b>DE WERKGEVER</b><br/>{data['nom_societe']}<br/>{data.get('representant','')}<br/><br/><br/>_______________________<br/>Handtekening en stempel",
          size=10, align=TA_LEFT),
        p(f"<b>DE WERKNEMER</b><br/>{data['nom_travailleur']}<br/><br/><br/><br/>_______________________<br/>Handtekening: Gelezen en goedgekeurd",
          size=10, align=TA_LEFT),
    ]], colWidths=[8.5*cm, 8.5*cm])
    sig.setStyle(TableStyle([
        ('VALIGN', (0,0),(-1,-1),'TOP'),
        ('TOPPADDING', (0,0),(-1,-1), 8),
        ('LINEAFTER', (0,0),(0,0), 0.5, LINE),
    ]))
    e.append(sig)
    e.append(Spacer(1, 0.3*cm))
    e.append(HRFlowable(width='100%', thickness=0.5, color=LINE))
    e.append(p("Opgesteld overeenkomstig de wet van 3 juli 1978 betreffende de arbeidsovereenkomsten.", size=8, color=GRAY))

    doc.build(e)
    return filepath, filename


def generer_certificat_travail_nl(c):
    """Certificat de travail en néerlandais."""
    filename = f"arbeidsattest_{c['nom']}_{c['prenom']}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4,
        topMargin=2*cm, bottomMargin=2*cm, leftMargin=2.5*cm, rightMargin=2.5*cm)
    e = []

    e.append(p(c['dossier_nom'], size=11, bold=True))
    e.append(p(c.get('dossier_adresse',''), size=9, color=GRAY))
    e.append(Spacer(1, 0.5*cm))
    e.append(HRFlowable(width='100%', thickness=2, color=NAVY))
    e.append(Spacer(1, 0.5*cm))
    e.append(p("ARBEIDSATTEST", size=14, bold=True, align=TA_CENTER))
    e.append(p("Artikel 21 van de wet van 3 juli 1978 betreffende de arbeidsovereenkomsten", size=9, align=TA_CENTER, color=GRAY))
    e.append(Spacer(1, 0.8*cm))

    debut = c['date_debut'].strftime('%d/%m/%Y') if c.get('date_debut') else '—'
    fin = c['date_fin'].strftime('%d/%m/%Y') if c.get('date_fin') else date.today().strftime('%d/%m/%Y')

    e.append(p(f"Ondergetekende, <b>{c.get('representant','—')}</b>, vertegenwoordiger van de vennootschap "
               f"<b>{c['dossier_nom']}</b>, verklaart dat:", size=10, align=TA_JUSTIFY))
    e.append(Spacer(1, 0.4*cm))
    e.append(p(f"<b>De heer/Mevrouw {c['prenom']} {c['nom']}</b>", size=11, bold=True))
    for label, val in [
        ("Rijksregisternummer:", c.get('niss','—')),
        ("Adres:", c.get('adresse','—')),
        ("Tewerkgesteld van:", f"{debut} tot {fin}"),
        ("Als:", c.get('fonction','—')),
        ("Paritair comité:", c.get('cp_key','—')),
        ("Type overeenkomst:", c.get('type_contrat','—')),
    ]:
        e.append(p(f"<b>{label}</b> {val}", size=10))
    e.append(Spacer(1, 0.4*cm))
    e.append(p("Dit attest wordt afgegeven overeenkomstig artikel 21 van de wet van 3 juli 1978. "
               "Het mag geen andere vermeldingen bevatten, tenzij op uitdrukkelijk verzoek van de werknemer.", 
               size=10, align=TA_JUSTIFY))
    e.append(Spacer(1, 1*cm))
    e.append(p(f"Opgesteld te _____________________, op {date.today().strftime('%d/%m/%Y')}", size=10))
    e.append(Spacer(1, 1.5*cm))
    e.append(p("_______________________", size=10))
    e.append(p(c.get('representant','—'), size=10))
    e.append(p(c['dossier_nom'], size=10))

    doc.build(e)
    return send_file(filepath, as_attachment=False, download_name=filename, mimetype='application/pdf')


def generer_c4_nl(c, form):
    """Formulaire C4 en néerlandais."""
    filename = f"C4_NL_{c['nom']}_{c['prenom']}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4,
        topMargin=1.5*cm, bottomMargin=1.5*cm, leftMargin=2*cm, rightMargin=2*cm)
    e = []

    e.append(p("FORMULIER C4 — WERKLOOSHEIDSBEWIJS", size=13, bold=True, align=TA_CENTER))
    e.append(p("Koninklijk besluit van 25 november 1991 houdende de werkloosheidsreglementering", size=8, align=TA_CENTER, color=GRAY))
    e.append(Spacer(1, 0.3*cm))
    e.append(HRFlowable(width='100%', thickness=1.5, color=NAVY))
    e.append(Spacer(1, 0.3*cm))

    debut = c['date_debut'].strftime('%d/%m/%Y') if c.get('date_debut') else '—'
    fin = c['date_fin'].strftime('%d/%m/%Y') if c.get('date_fin') else date.today().strftime('%d/%m/%Y')
    motif_nl = {
        'Fin de contrat à durée déterminée': 'Einde arbeidsovereenkomst voor bepaalde duur',
        'Licenciement par l\'employeur': 'Ontslag door de werkgever',
        'Démission du travailleur': 'Ontslag door de werknemer',
        'Rupture d\'un commun accord': 'Beëindiging in onderling akkoord',
        'Fin de contrat étudiant': 'Einde studentenovereenkomst',
    }.get(form.get('motif_fin',''), form.get('motif_fin','—'))

    salaire_ref = form.get('salaire_reference', '')
    if not salaire_ref:
        from flask import g
        salaire_ref = '—'

    sections = [
        ("WERKGEVER", [
            ("Naam/Benaming", c['dossier_nom']),
            ("Adres", c.get('dossier_adresse','—')),
            ("RSZ-nummer", c.get('rsz','—')),
            ("KBO", c.get('bce','—')),
            ("Paritair comité", c.get('cp_key','—')),
        ]),
        ("WERKNEMER", [
            ("Naam en voornaam", f"{c['nom']} {c['prenom']}"),
            ("Rijksregisternummer", c.get('niss','—')),
            ("Adres", c.get('adresse','—')),
            ("Statuut", "Arbeider"),
        ]),
        ("TEWERKSTELLING", [
            ("Startdatum", debut),
            ("Einddatum", fin),
            ("Functie", c.get('fonction','—')),
            ("Type overeenkomst", c.get('type_contrat','—')),
            ("Arbeidsregime", f"{float(c.get('heures_jour') or 7.6):.1f}u/dag × {int(c.get('jours_semaine') or 5)}d = {float(c.get('heures_jour') or 7.6) * int(c.get('jours_semaine') or 5):.1f}u/week"),
            ("Referentieloon bruto", f"{salaire_ref} EUR/maand"),
        ]),
        ("EINDE VAN DE OVEREENKOMST", [
            ("Reden van beëindiging", motif_nl),
            ("Wie heeft beëindigd", {'Employeur': 'Werkgever', 'Travailleur': 'Werknemer', 'D\'un commun accord': 'In onderling akkoord'}.get(form.get('qui_fin',''), form.get('qui_fin','—'))),
            ("Gepresteerde opzeg", "Niet van toepassing — ABD"),
        ]),
    ]

    sN_label = ParagraphStyle('L', fontName=FN, fontSize=9, leading=13)
    sN_val = ParagraphStyle('V', fontName=FN, fontSize=9, leading=13)
    sN_sec = ParagraphStyle('S', fontName=FNB, fontSize=9, leading=13)

    for titre, lignes in sections:
        e.append(Paragraph(titre, sN_sec))
        t_data = [[Paragraph(l, sN_label), Paragraph(v, sN_val)] for l, v in lignes]
        t = Table(t_data, colWidths=[6*cm, 10.5*cm])
        t.setStyle(TableStyle([
            ('TOPPADDING', (0,0),(-1,-1), 3),
            ('BOTTOMPADDING', (0,0),(-1,-1), 3),
            ('LINEBELOW', (0,0),(-1,-2), 0.3, colors.HexColor('#eeeeee')),
            ('BACKGROUND', (0,0),(0,-1), colors.HexColor('#f9f9f9')),
        ]))
        e.append(t)
        e.append(Spacer(1, 0.3*cm))

    e.append(HRFlowable(width='100%', thickness=0.5, color=LINE))
    e.append(Spacer(1, 0.2*cm))
    e.append(Paragraph(
        "<b>Belangrijk:</b> Dit formulier C4 moet uiterlijk op de laatste werkdag aan de werknemer worden overhandigd, "
        "overeenkomstig artikel 137 van het KB van 25 november 1991. De werknemer bezorgt het aan zijn "
        "uitbetalingsinstelling (HVW of vakbond) om werkloosheidsuitkeringen aan te vragen.",
        ParagraphStyle('', fontName=FN, fontSize=9, leading=13)))
    e.append(Spacer(1, 0.5*cm))
    e.append(Paragraph(f"Opgesteld te _____________________, op {date.today().strftime('%d/%m/%Y')}", 
                       ParagraphStyle('', fontName=FN, fontSize=9)))
    e.append(Spacer(1, 1*cm))
    sig = Table([[
        Paragraph("<b>Handtekening werkgever</b><br/><br/><br/>_______________________",
                  ParagraphStyle('', fontName=FNB, fontSize=9)),
        Paragraph("<b>Handtekening werknemer</b><br/><br/><br/>_______________________",
                  ParagraphStyle('', fontName=FNB, fontSize=9)),
    ]], colWidths=[8*cm, 8*cm])
    e.append(sig)

    doc.build(e)
    return filepath, filename
