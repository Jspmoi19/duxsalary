# -*- coding: utf-8 -*-
"""
pdf_dmfa.py -- DuxSalary
Export PDF de l'aide a la DmfA (structure produite par dmfa.aide_dmfa).
Identite visuelle: branding.get_branding() uniquement.
"""
from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from branding import get_branding, pdf_decor, pdf_logo

FN, FNB = 'Helvetica', 'Helvetica-Bold'


def generer_pdf_dmfa(document, tenant=None):
    """Retourne le PDF (bytes) de l'aide a la DmfA."""
    b = get_branding(tenant)
    primaire = colors.HexColor(b['couleur_primaire'])
    texte = colors.HexColor(b['couleur_texte'])
    secondaire = colors.HexColor(b['couleur_texte_secondaire'])
    fond = colors.HexColor(b['couleur_fond_clair'])
    trait = colors.HexColor(b['couleur_ligne'])
    st = lambda nom, **kw: ParagraphStyle(nom, fontName=kw.pop('font', FN), fontSize=kw.pop('size', 7.5),
                                          leading=kw.pop('size_l', 9.5), textColor=kw.pop('color', texte), **kw)
    s_c, s_g, s_n, s_h = st('c'), st('g', font=FNB), st('n', alignment=TA_RIGHT), st('h', font=FNB, color=colors.white)
    s_alerte, s_note = st('a', color=colors.HexColor('#8a5a00')), st('o', size=6.8, size_l=8.5, color=secondaire)
    esc = lambda v: str(v).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    tampon = BytesIO()
    largeur = A4[0] - 2.4 * cm
    debut, fin = document['periode']
    doc = SimpleDocTemplate(tampon, pagesize=A4, topMargin=1 * cm, bottomMargin=1.4 * cm, leftMargin=1.2 * cm,
                            rightMargin=1.2 * cm, title=document['titre'], author=b['nom'])
    e = []
    titre = [Paragraph(esc(document['titre']), st('t', font=FNB, size=14, size_l=17, color=primaire, alignment=TA_RIGHT)),
             Paragraph(f"Du {debut:%d/%m/%Y} au {fin:%d/%m/%Y} — imprimé le {datetime.now():%d/%m/%Y}",
                       st('p', size=8.5, size_l=11, color=secondaire, alignment=TA_RIGHT))]
    e.append(Table([[pdf_logo(4.6, tenant), titre]], colWidths=[largeur * 0.4, largeur * 0.6],
                   style=TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LINEBELOW', (0, 0), (-1, 0), 1.2, primaire),
                                     ('BOTTOMPADDING', (0, 0), (-1, 0), 6)])))
    e.append(Spacer(1, 0.25 * cm))
    cellules = [Paragraph(f"<font color='{b['couleur_texte_secondaire']}'>{esc(l)} :</font> <b>{esc(v)}</b>", s_c)
                for l, v in document['entete'] if v]
    lignes = [cellules[i:i + 2] + [''] * (2 - len(cellules[i:i + 2])) for i in range(0, len(cellules), 2)]
    e.append(Table(lignes, colWidths=[largeur / 2] * 2,
                   style=TableStyle([('BACKGROUND', (0, 0), (-1, -1), fond), ('BOX', (0, 0), (-1, -1), 0.4, trait),
                                     ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2)])))
    for a in document['alertes']:
        e.append(Paragraph('⚠ ' + esc(a), s_alerte))

    def tableau(t):
        n = len(t['colonnes'])
        # premiere colonne etroite quand c'est un code ; la colonne de texte prend la place restante
        code_en_tete = t['colonnes'][0] == 'Code'
        if n == 2:
            larg = [largeur * 0.55, largeur * 0.45]
        elif code_en_tete:
            reste = n - 2
            larg = [1.7 * cm, largeur - 1.7 * cm - reste * 2.7 * cm] + [2.7 * cm] * reste
        else:
            larg = [largeur - (n - 1) * 3 * cm] + [3 * cm] * (n - 1)
        num = lambda i: i >= (2 if code_en_tete else 1) and n > 2
        data = [[Paragraph(esc(c), s_h) for c in t['colonnes']]]
        style = [('BACKGROUND', (0, 0), (-1, 0), primaire), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                 ('LINEBELOW', (0, 0), (-1, -1), 0.25, trait), ('TOPPADDING', (0, 0), (-1, -1), 1.5),
                 ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5), ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3)]
        for l in t['lignes']:
            gras = any(str(x).startswith(('TOTAL', 'MONTANT NET')) for x in l)
            data.append([Paragraph(esc(v), (st('ng', font=FNB, alignment=TA_RIGHT) if gras else s_n) if num(i)
                                   else (s_g if gras else s_c)) for i, v in enumerate(l)])
        bloc = [Paragraph(esc(t['titre']), st('s', font=FNB, size=8.5, size_l=11, color=primaire)),
                Table(data, colWidths=larg, repeatRows=1, style=TableStyle(style))]
        if t.get('note'):
            bloc.append(Paragraph(esc(t['note']), s_note))
        bloc.append(Spacer(1, 0.2 * cm))
        return KeepTogether(bloc)

    for t in document['travailleurs']:
        e.append(Spacer(1, 0.3 * cm))
        e.append(Table([[Paragraph(f"<b>{esc(t['nom'])}</b> — NISS : {esc(t['niss'] or 'non renseigné')}",
                                   st('w', size=10, size_l=13, color=colors.white))]], colWidths=[largeur],
                       style=TableStyle([('BACKGROUND', (0, 0), (-1, -1), primaire), ('TOPPADDING', (0, 0), (-1, -1), 3),
                                         ('BOTTOMPADDING', (0, 0), (-1, -1), 4)])))
        for a in t['alertes']:
            e.append(Paragraph('⚠ ' + esc(a), s_alerte))
        e.append(Spacer(1, 0.15 * cm))
        e += [tableau(x) for x in t['tableaux']]
    e.append(Spacer(1, 0.3 * cm))
    e.append(tableau(document['totaux']))
    e.append(Paragraph(esc(document['source']), s_note))

    doc.build(e, **pdf_decor(tenant, logo=False))
    return tampon.getvalue()
