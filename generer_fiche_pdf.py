"""
generer_fiche_pdf.py — DuxSalary
Génère la fiche de paie PDF complète type Human Social Process SA
"""

import os
from datetime import date, datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from branding import couleur, pdf_decor, get_branding
from occupation import libelle_etat_civil

try:
    pdfmetrics.registerFont(TTFont('DVSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('DVSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
    FN, FNB = 'DVSans', 'DVSans-Bold'
except:
    FN, FNB = 'Helvetica', 'Helvetica-Bold'

BLACK = colors.black
DARK = colors.HexColor('#1a1a1a')
GRAY = colors.HexColor('#555555')
LGRAY = colors.HexColor('#f5f5f5')
LINE = colors.HexColor('#cccccc')

def style(name, font=None, size=8, bold=False, align=TA_LEFT, color=BLACK):
    return ParagraphStyle(name,
        fontName=(FNB if bold else FN),
        fontSize=size, leading=size+3,
        textColor=color, alignment=align)

def p(text, **kw):
    return Paragraph(str(text) if text is not None else '', style('x', **kw))

def generer_fiche_paie_pdf(data, filepath):
    """Génère le PDF de la fiche de paie."""
    doc = SimpleDocTemplate(filepath, pagesize=A4,
        topMargin=1.5*cm, bottomMargin=1.5*cm,   # marge haute: place du logo (branding.pdf_decor)
        leftMargin=1.5*cm, rightMargin=1.5*cm)
    
    w = 18*cm  # largeur utile
    elems = []
    
    # ── EN-TÊTE ──────────────────────────────────────────────────────
    header = Table([[
        Table([
            [p(data['nom_societe'], bold=True, size=9)],
            [p(data['adresse_societe'], size=8, color=GRAY)],
            [p(f"BCE : {data['bce_societe']}  |  RSZ : {data['rsz_societe']}", size=8, color=GRAY)],
        ], colWidths=[9*cm]),
        Table([
            [p('FEUILLE DE PAIE', bold=True, size=16, align=TA_RIGHT)],
            [p(f"Période : {_fmt_date(data['periode_debut'])} – {_fmt_date(data['periode_fin'])}", 
               size=9, align=TA_RIGHT, color=GRAY)],
        ], colWidths=[9*cm]),
    ]], colWidths=[9*cm, 9*cm])
    header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    elems.append(header)
    elems.append(HRFlowable(width='100%', thickness=1.5, color=DARK, spaceAfter=6))
    
    # ── DONNÉES TRAVAILLEUR + ADRESSE ─────────────────────────────
    date_entree_fmt = _fmt_date(data['date_entree']) if data.get('date_entree') else '—'
    
    heures_j = data.get('heures_jour', 7.6)
    jours_sem = data.get('jours_semaine', 5)
    h_sem_reel = data.get('heures_semaine_reel', data['heures_semaine'])
    genre = 'Temps partiel' if h_sem_reel < 36 else 'Temps plein'
    
    left_data = [
        ['Travailleur :', f"{data['prenom']} {data['nom']}"],
        ['Statut/Profession :', data.get('categorie', '—')[:30]],
        ['Régime/Système :', f"{jours_sem}j/sem · {heures_j}h/j"],
        ['Salaire mensuel de base :' if not data.get('is_ouvrier') and not data.get('is_etudiant') else 'Salaire de base :',
            f"{data.get('salaire_mensuel_fixe', round(data['salaire_horaire'] * data.get('heures_semaine', 38) * 52 / 12, 2)):.2f} €"
            if not data.get('is_ouvrier') and not data.get('is_etudiant')
            else f"{data['salaire_horaire']:.4f} €/heure"],
        ['Genre travail :', genre],
        ['Heures :', f"{h_sem_reel:.2f}/{data['heures_semaine']:.2f}"],
        ['Commission Paritaire :', f"{data['cp_key']}"],
        ['N° NISS :', data.get('niss', '—')],
        ['Catégorie prof. :', data.get('categorie', '—')[:20]],
        ['Date d\'entrée :', f"{date_entree_fmt}  Anc.: {data.get('anciennete', '0a')}"],
        ['', ''],
        ['Etat civil :', libelle_etat_civil(data.get('etat_civil'))],
        ['No.Rég.Nat. :', data.get('niss', '—')],
        ['A charge :', f"Enf.:{data.get('nb_enfants', 0)}"],
    ]
    
    left_table = Table(
        [[p(r[0], size=7.5, color=GRAY), p(r[1], size=7.5)] for r in left_data],
        colWidths=[3.5*cm, 5*cm]
    )
    left_table.setStyle(TableStyle([
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    
    right_table = Table([
        [p(f"{data['prenom']} {data['nom']}", bold=True, size=12)],
        [p('')],
        [p(data.get('adresse', ''), size=9)],
    ], colWidths=[8*cm])
    
    worker_header = Table([[left_table, right_table]], colWidths=[8.5*cm, 9*cm])
    worker_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOX', (0,0), (0,0), 0.5, LINE),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (0,0), 6),
    ]))
    elems.append(worker_header)
    elems.append(Spacer(1, 0.3*cm))
    
    # ── NOTE LÉGALE ──────────────────────────────────────────────
    elems.append(p('A conserver, cette fiche de rémunération fait partie de votre compte individuel.',
                   size=7, color=GRAY))
    elems.append(Spacer(1, 0.2*cm))
    
    # ── TABLEAU ÉLÉMENTS DES SALAIRES ────────────────────────────
    cols = [6.5*cm, 2.5*cm, 1.5*cm, 1.0*cm, 1.6*cm, 1.8*cm, 2.6*cm]
    
    def row_sal(libelle, base='', suppl='', pct='', jours='', heures='', montant='', bold=False):
        return [
            p(libelle, bold=bold, size=8),
            p(str(base) if base else '', size=8, align=TA_RIGHT),
            p(str(suppl) if suppl else '', size=8, align=TA_RIGHT),
            p(str(pct) if pct else '', size=8, align=TA_RIGHT),
            p(str(jours) if jours else '', size=8, align=TA_RIGHT),
            p(str(heures) if heures else '', size=8, align=TA_RIGHT),
            p(f"{montant:.2f}" if isinstance(montant, (int, float)) else str(montant), size=8, align=TA_RIGHT),
        ]
    
    sal_rows = [
        row_sal('ELEMENTS DES SALAIRES', 'BASE', 'SUPPL.', '%', 'JOURS', 'HEURES', 'MONTANT', bold=True),
    ]
    
    # Lignes de salaire
    for ligne in data.get('lignes_salaire', []):
        sal_rows.append(row_sal(
            ligne['libelle'],
            f"{ligne['base']:.{ligne.get('base_decimales', 4)}f}" if ligne.get('base') else '',
            '',
            '',
            ligne.get('jours', '') if ligne.get('jours') else '',
            f"{ligne['heures']:.2f}" if ligne.get('heures') else '',
            ligne.get('montant', 0),
        ))
    
    # Brut ONSS
    sal_rows.append(row_sal('BRUT SOUMIS A L\'ONSS:', '', '', '', '', '', '', bold=False))
    sal_rows[-1][6] = p(f"EUR  {data['brut_onss']:.2f}", bold=True, size=8, align=TA_RIGHT, color=DARK)
    
    # ONSS travailleur
    onss_brut = abs(data['onss_travailleur'])
    sal_rows.append(row_sal(
        f"ONSS TRAVAILLEUR (DEDUCTION): (Base calcul: {data['brut_onss']:.2f})",
        '', '', '', '', '', -onss_brut
    ))
    if data.get('bonus_emploi_a', 0) > 0:
        sal_rows.append(row_sal(
            "Bonus a l'emploi - volet A",
            '', '', '', '', '', data.get('bonus_emploi_a', 0)
        ))
    if data.get('bonus_emploi_b', 0) > 0:
        sal_rows.append(row_sal(
            "Bonus a l'emploi - volet B",
            '', '', '', '', '', data.get('bonus_emploi_b', 0)
        ))
    # Imposable
    sal_rows.append(row_sal('IMPOSABLE:', '', '', '', '', '', '', bold=False))
    sal_rows[-1][6] = p(f"EUR  {data['brut_imposable']:.2f}", bold=True, size=8, align=TA_RIGHT)
    
    # Précompte
    pc_val = abs(data['precompte'])
    sal_rows.append(row_sal(
        f"PRECOMPTE PROFESSIONNEL (DEDUCTION): (Imposable normal: {data['brut_imposable']:.2f})",
        '', '', '', '', '', -pc_val
    ))
    
    # Indemnités
    for indemn in data.get('lignes_indemn', []):
        detail = indemn.get('detail', '')
        jours_str = f"{indemn['jours']} jours" if indemn.get('jours') and indemn['jours'] > 0 else ''
        sal_rows.append([
            p(indemn['libelle'], size=8),
            p(detail, size=8),
            p('', size=8),
            p('', size=8),
            p(jours_str, size=8, align=TA_RIGHT),
            p('', size=8),
            p(f"{indemn['montant']:.2f}", size=8, align=TA_RIGHT),
        ])
    
    # Salaire net
    sal_rows.append(row_sal('Salaire net', '', '', '', '', '', '', bold=True))
    sal_rows[-1][6] = p(f"EUR {data['salaire_net']:.2f}", bold=True, size=7.5, align=TA_RIGHT)
    
    sal_table = Table(sal_rows, colWidths=cols)
    sal_style = [
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW', (0,0), (-1,0), 0.5, LINE),
        ('BACKGROUND', (0,0), (-1,0), LGRAY),
        ('LINEABOVE', (0,-1), (-1,-1), 0.8, DARK),
    ]
    sal_table.setStyle(TableStyle(sal_style))
    elems.append(sal_table)
    elems.append(Spacer(1, 0.3*cm))
    
    # ── SECTION INFORMATION ───────────────────────────────────────
    info_data = [
        [p('INFORMATION:', bold=True, size=8), '', ''],
        [p('ONSS patronale', size=8), '', p(f"{data['onss_patronal']:.2f}", size=8, align=TA_RIGHT)],
        [p('Déd. cot. ONSS trav.', size=8), '', p(f"{data['ded_cot_onss_trav']:.2f}", size=8, align=TA_RIGHT)],
        [p('ONSS bas salaires - Champ B', size=8), '', p(f"{data['onss_bas_salaires_champ_b']:.2f}", size=8, align=TA_RIGHT)],
    ]
    if data.get('cr_empl_total', 0) > 0:
        info_data.append([p('Cheques-repas part empl (sans ONSS)', size=8), '', p(f"{data['cr_empl_total']:.2f}", size=8, align=TA_RIGHT)])
    if data.get('premier_engagement') and data.get('reduction_premier_engagement', 0) > 0:
        info_data.append([p('Red. 1er engagement', size=8), '', p(f"{data['reduction_premier_engagement']:.2f}", size=8, align=TA_RIGHT)])
    info_table = Table(info_data, colWidths=[8*cm, 7*cm, 3*cm])
    info_table.setStyle(TableStyle([
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LINEBELOW', (0,0), (-1,0), 0.5, LINE),
        ('BACKGROUND', (0,0), (-1,0), LGRAY),
    ]))
    elems.append(info_table)
    elems.append(Spacer(1, 0.2*cm))
    
    # ── COMMUNICATION + DÉCOMPTE ──────────────────────────────────
    bottom = Table([[
        Table([
            [p('COMMUNICATION:', bold=True, size=8)],
            [p('', size=8)],
            [p('')],
            [p(f"Etabli par : {get_branding()['societe']}", size=7.5, color=GRAY)],
        ], colWidths=[9*cm]),
        Table([
            [p('DECOMPTE:', bold=True, size=8), ''],
            [p('Salaire net', size=8), p(f"{data['salaire_net']:.2f} EUR", bold=True, size=7.5, align=TA_RIGHT)],
            [p('A payer', bold=True, size=8), p(f"{data['a_payer']:.2f} EUR", bold=True, size=8, align=TA_RIGHT)],
        ], colWidths=[3.5*cm, 5.2*cm]),
    ]], colWidths=[9*cm, 9*cm])
    bottom.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOX', (1,0), (1,0), 0.5, LINE),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (1,0), (1,0), 2),
        ('RIGHTPADDING', (1,0), (1,0), 2),
    ]))
    elems.append(bottom)
    elems.append(Spacer(1, 0.3*cm))
    
    # ── FORMULE DE PAIEMENT ──────────────────────────────────────
    elems.append(HRFlowable(width='100%', thickness=0.5, color=LINE))
    elems.append(Spacer(1, 0.15*cm))
    elems.append(p('FORMULE DE PAIEMENT', bold=True, size=8))
    iban = data.get('iban', '—')
    elems.append(p(
        f"{data['a_payer']:.2f} EUR par virement sur compte bancaire {iban} "
        f"de {data['prenom']} {data['nom']}", size=8))
    
    doc.build(elems, **pdf_decor())
    return filepath

def _fmt_date(d):
    if not d:
        return '—'
    if isinstance(d, (date, datetime)):
        return d.strftime('%d-%m-%Y')
    return str(d)

if __name__ == '__main__':
    from moteur_paie import calculer_fiche_paie
    result = calculer_fiche_paie(
        prenom='Akattof', nom='Bilal', niss='06.10.18-379.82',
        adresse='Lidrusweg bâtiment 3/3.4 - 1130 Bruxelles', iban='BE75363178356651',
        date_naissance=date(2006, 10, 18), date_entree=date(2026, 7, 9),
        nom_societe="98'H BARBER", adresse_societe='Rue Marcel Marien/17 - 1030 Bruxelles',
        bce_societe='0800.078.071', rsz_societe='51365632-19',
        cp_key='CP 140.03', categorie='Personnel roulant — Niveau 1',
        salaire_horaire=14.9255, heures_semaine=38.0,
        jours_prestes=21, heures_prestees=159.6,
        rgpt_actif=True, cheques_repas=True, vehicule_societe=True,
        periode_debut=date(2026, 7, 1), periode_fin=date(2026, 7, 31),
    )
    generer_fiche_paie_pdf(result, '/home/claude/test_fiche_bilal.pdf')
    print(f"PDF généré — Net: {result['salaire_net']:.2f} €")
