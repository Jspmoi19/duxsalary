# -*- coding: utf-8 -*-
"""
pdf_fin_contrat.py -- DuxSalary
Decompte de sortie (PDF remis au client et au travailleur) a partir du resultat de
fin_contrat.decompte_sortie. Document CLIENT: uniquement des libelles, bases, taux,
nombres et montants -- aucune source ni note interne (les 'regles' et 'alertes' du
calcul ne sont jamais imprimees ici). Identite visuelle: branding uniquement.
"""
from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from branding import get_branding, pdf_decor, pdf_logo

FN, FNB = 'Helvetica', 'Helvetica-Bold'


def montant(v):
    return f"{v:,.2f}".replace(',', ' ').replace('.', ',')


def generer_pdf_decompte(decompte, contexte, tenant=None):
    """contexte: {'employeur', 'adresse_employeur', 'bce', 'travailleur', 'niss', 'fonction',
    'type_contrat', 'date_entree', 'date_fin', 'iban'}. Retourne le PDF (bytes)."""
    b = get_branding(tenant)
    primaire = colors.HexColor(b['couleur_primaire'])
    texte = colors.HexColor(b['couleur_texte'])
    secondaire = colors.HexColor(b['couleur_texte_secondaire'])
    fond = colors.HexColor(b['couleur_fond_clair'])
    trait = colors.HexColor(b['couleur_ligne'])
    st = lambda nom, **kw: ParagraphStyle(nom, fontName=kw.pop('font', FN), fontSize=kw.pop('size', 8.5),
                                          leading=kw.pop('size_l', 11), textColor=kw.pop('color', texte), **kw)
    s_c, s_g, s_n, s_ng = st('c'), st('g', font=FNB), st('n', alignment=TA_RIGHT), st('ng', font=FNB, alignment=TA_RIGHT)
    s_h = st('h', font=FNB, color=colors.white)
    esc = lambda v: str(v).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    jj = lambda d: d.strftime('%d/%m/%Y') if d else '—'

    tampon = BytesIO()
    largeur = A4[0] - 3 * cm
    doc = SimpleDocTemplate(tampon, pagesize=A4, topMargin=1.2 * cm, bottomMargin=1.6 * cm, leftMargin=1.5 * cm,
                            rightMargin=1.5 * cm, title='Décompte de sortie', author=b['nom'])
    e = []
    titre = [Paragraph('Décompte de sortie', st('t', font=FNB, size=15, size_l=18, color=primaire, alignment=TA_RIGHT)),
             Paragraph(f"Établi le {datetime.now():%d/%m/%Y}", st('p', size=8.5, color=secondaire, alignment=TA_RIGHT))]
    e.append(Table([[pdf_logo(4.6, tenant), titre]], colWidths=[largeur * 0.4, largeur * 0.6],
                   style=TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LINEBELOW', (0, 0), (-1, 0), 1.2, primaire),
                                     ('BOTTOMPADDING', (0, 0), (-1, 0), 6)])))
    e.append(Spacer(1, 0.3 * cm))

    c = contexte or {}
    paires = [('Employeur', c.get('employeur')), ('N° d\'entreprise', c.get('bce')), ('Adresse', c.get('adresse_employeur')),
              ('Travailleur', c.get('travailleur')), ('N° registre national', c.get('niss')), ('Fonction', c.get('fonction')),
              ('Type de contrat', c.get('type_contrat')), ('Date d\'entrée', jj(c.get('date_entree'))),
              ('Fin du contrat', jj(c.get('date_fin'))), ('Motif', decompte.get('libelle_motif'))]
    cellules = [Paragraph(f"<font color='{b['couleur_texte_secondaire']}'>{esc(l)} :</font> <b>{esc(v)}</b>", s_c)
                for l, v in paires if v]
    lignes = [cellules[i:i + 2] + [''] * (2 - len(cellules[i:i + 2])) for i in range(0, len(cellules), 2)]
    e.append(Table(lignes, colWidths=[largeur / 2] * 2,
                   style=TableStyle([('BACKGROUND', (0, 0), (-1, -1), fond), ('BOX', (0, 0), (-1, -1), 0.4, trait),
                                     ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2)])))
    e.append(Spacer(1, 0.3 * cm))

    p = decompte.get('preavis')
    if p:
        qui = "l'employeur" if p['auteur'] == 'employeur' else 'le travailleur'
        phrase = f"Délai de préavis : <b>{p['semaines']} semaine(s)</b> (congé donné par {qui})."
        if p.get('dates'):
            d = p['dates']
            phrase += (f" Notification prenant effet le {jj(d['effet'])} ; préavis du <b>{jj(d['debut'])}</b> au "
                       f"<b>{jj(d['fin'])}</b>" + (", presté." if p.get('preste') else ", non presté ou presté en partie."))
        e.append(Paragraph(phrase, s_c))
        e.append(Spacer(1, 0.25 * cm))

    fr = lambda x: str(x).replace('.', ',')
    data = [[Paragraph(x, s_h) for x in ('Élément', 'Base', 'Taux / nombre', 'Montant')]]
    for l in decompte.get('lignes') or []:
        data.append([Paragraph(esc(l['libelle']), s_c), Paragraph(montant(l['base']) if l.get('base') is not None else '', s_n),
                     Paragraph(esc(fr(l.get('nombre') or '')), s_n), Paragraph(montant(l['montant']), s_n)])
    if len(data) == 1:
        data.append([Paragraph("Aucune indemnité de rupture ni pécule de sortie à payer.", s_c), '', '', ''])
    t = decompte.get('totaux') or {}
    for lib, v in (('Total brut', t.get('brut', 0)), ('Retenues ONSS', -t.get('onss', 0)),
                   ('Précompte professionnel', -t.get('precompte', 0))):
        data.append([Paragraph(lib, s_c), '', '', Paragraph(montant(v), s_n)])
    data.append([Paragraph('NET À PAYER', s_g), '', '', Paragraph(montant(t.get('net', 0)), s_ng)])
    n = len(data)
    e.append(Table(data, colWidths=[largeur - 8.4 * cm, 2.8 * cm, 3 * cm, 2.6 * cm], repeatRows=1, style=TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primaire), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (0, 0), (-1, -1), 0.25, trait), ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5), ('LINEABOVE', (0, n - 4), (-1, n - 4), 0.6, texte),
        ('LINEABOVE', (0, n - 1), (-1, n - 1), 0.8, texte), ('BACKGROUND', (0, n - 1), (-1, n - 1), fond)])))
    e.append(Spacer(1, 0.3 * cm))
    for mention in decompte.get('mentions') or []:
        e.append(Paragraph(esc(mention), s_c))
    e.append(Spacer(1, 0.2 * cm))
    if c.get('iban') and t.get('net', 0) > 0:
        e.append(Paragraph(f"{montant(t['net'])} EUR par virement sur le compte {esc(c['iban'])} de {esc(c.get('travailleur') or '')}.", s_c))
    e.append(Spacer(1, 0.8 * cm))
    e.append(Table([[Paragraph("Pour l'employeur", s_c), Paragraph('Pour réception, le travailleur', s_c)]],
                   colWidths=[largeur / 2] * 2))

    doc.build(e, **pdf_decor(tenant, logo=False))
    return tampon.getvalue()
