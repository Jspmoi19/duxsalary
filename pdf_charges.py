# -*- coding: utf-8 -*-
"""
pdf_charges.py -- DuxSalary
Export PDF des documents de charges salariales (structure produite par
documents_charges.py). Identite visuelle: branding.get_branding() uniquement.
"""
from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from branding import get_branding
from documents_charges import formater

FN, FNB = 'Helvetica', 'Helvetica-Bold'


def generer_pdf_charges(document, tenant=None):
    """Retourne le PDF (bytes) d'un document de charges."""
    b = get_branding(tenant)
    primaire = colors.HexColor(b['couleur_primaire'])
    texte = colors.HexColor(b['couleur_texte'])
    secondaire = colors.HexColor(b['couleur_texte_secondaire'])
    fond = colors.HexColor(b['couleur_fond_clair'])
    trait = colors.HexColor(b['couleur_ligne'])

    nb_col = len(document['colonnes'])
    taille = 6.2 if nb_col > 8 else 8
    st = lambda nom, **kw: ParagraphStyle(nom, fontName=kw.pop('font', FN), fontSize=kw.pop('size', taille),
                                          leading=kw.pop('size_l', taille + 2.5), textColor=kw.pop('color', texte), **kw)
    s_cell, s_gras = st('c'), st('g', font=FNB)

    tampon = BytesIO()
    largeur = landscape(A4)[0] - 2 * cm
    debut, fin = document['periode']

    def pied(canvas, doc):
        canvas.saveState()
        canvas.setFont(FN, 7); canvas.setFillColor(secondaire)
        canvas.drawString(1 * cm, 0.7 * cm, f"{b['pied_de_page']} — imprimé le {datetime.now():%d/%m/%Y à %H:%M}")
        canvas.drawRightString(landscape(A4)[0] - 1 * cm, 0.7 * cm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(tampon, pagesize=landscape(A4), topMargin=1 * cm, bottomMargin=1.3 * cm,
                            leftMargin=1 * cm, rightMargin=1 * cm, title=document['titre'], author=b['nom'])
    e = []

    # ── En-tete: logo (ou nom) + titre ──
    if b['logo_path']:
        marque = Image(b['logo_path'], width=3.2 * cm, height=1.2 * cm, kind='proportional')
    else:
        marque = Paragraph(b['logo_text'], st('logo', font=FNB, size=15, size_l=18, color=primaire))
    titre = [Paragraph(document['titre'], st('t', font=FNB, size=14, size_l=17, color=primaire, alignment=TA_RIGHT)),
             Paragraph(f"Période : {debut:%d/%m/%Y} – {fin:%d/%m/%Y}", st('p', size=8.5, size_l=11, color=secondaire, alignment=TA_RIGHT))]
    e.append(Table([[marque, titre]], colWidths=[largeur * 0.4, largeur * 0.6],
                   style=TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LINEBELOW', (0, 0), (-1, 0), 1.2, primaire),
                                     ('BOTTOMPADDING', (0, 0), (-1, 0), 6)])))
    e.append(Spacer(1, 0.25 * cm))

    # ── Bloc d'identification (paires libelle / valeur sur 3 colonnes) ──
    paires = [(l, v) for l, v in document.get('entete', []) if v]
    if paires:
        s_e = st('e', size=7.5, size_l=10)
        cellules = [Paragraph(f"<font color='{b['couleur_texte_secondaire']}'>{l} :</font> <b>{v}</b>", s_e) for l, v in paires]
        lignes = [cellules[i:i + 3] + [''] * (3 - len(cellules[i:i + 3])) for i in range(0, len(cellules), 3)]
        e.append(Table(lignes, colWidths=[largeur / 3] * 3,
                       style=TableStyle([('BACKGROUND', (0, 0), (-1, -1), fond), ('BOX', (0, 0), (-1, -1), 0.4, trait),
                                         ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2)])))
        e.append(Spacer(1, 0.25 * cm))

    # ── Tableau ──
    l_lib = min(11.5 * cm, max(5.2 * cm, largeur - nb_col * 3 * cm))
    l_val = (largeur - l_lib) / nb_col
    s_num, s_num_g = st('n', alignment=TA_RIGHT), st('ng', font=FNB, alignment=TA_RIGHT)
    s_tete = st('h', font=FNB, color=colors.white, alignment=TA_RIGHT)
    data = [[Paragraph('', s_tete)] + [Paragraph(c, s_tete) for c in document['colonnes']]]
    style = [('BACKGROUND', (0, 0), (-1, 0), primaire), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
             ('LINEBELOW', (0, 0), (-1, -1), 0.25, trait), ('TOPPADDING', (0, 0), (-1, -1), 1.5),
             ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5), ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3)]
    for section in document['sections']:
        data.append([Paragraph(section['titre'].upper(), st('s', font=FNB, color=primaire))] + [''] * nb_col)
        style += [('BACKGROUND', (0, len(data) - 1), (-1, len(data) - 1), fond), ('SPAN', (0, len(data) - 1), (-1, len(data) - 1))]
        for l in section['lignes']:
            total = l['style'] == 'total'
            valeurs = [formater(v, l['fmt']) or ('0,00' if total and l['fmt'] == 'montant' and v is not None else '') for v in l['valeurs']]
            data.append([Paragraph(l['libelle'], s_gras if total else (st('i', color=secondaire) if l['style'] == 'info' else s_cell))]
                        + [Paragraph(v, s_num_g if total else s_num) for v in valeurs])
            if total:
                style.append(('LINEABOVE', (0, len(data) - 1), (-1, len(data) - 1), 0.6, texte))
    e.append(Table(data, colWidths=[l_lib] + [l_val] * nb_col, repeatRows=1, style=TableStyle(style)))

    for a in document.get('avertissements', []):
        e.append(Spacer(1, 0.2 * cm))
        e.append(Paragraph(a, st('a', size=7.5, size_l=10, color=secondaire)))

    doc.build(e, onFirstPage=pied, onLaterPages=pied)
    return tampon.getvalue()
