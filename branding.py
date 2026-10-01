# -*- coding: utf-8 -*-
"""
branding.py -- DuxSalary
EMPLACEMENT UNIQUE de l'identite: logo, mentions legales et couleurs, pour les
pages de l'application ET pour tous les PDF. Aucun autre fichier ne doit
definir un nom, une adresse, un logo ou une couleur de marque.

  - pages : la variable `marque` est injectee dans tous les gabarits (app.py)
  - PDF   : pdf_logo(), pdf_pied_de_page() et couleur() ci-dessous

Pour changer la charte: modifier DEFAUT et remplacer static/logo.png.
Marque blanche: get_branding(tenant) remplace les valeurs par celles du tenant
(colonnes de la table `tenants`: nom, societe, bce, adresse, logo_path,
couleur_primaire, couleur_accent) quand elles sont renseignees. Aujourd'hui
l'application n'en passe aucun: une seule identite partout.
"""
import os

RACINE = os.path.dirname(os.path.abspath(__file__))

DEFAUT = {
    'nom': 'DuxSalary',                       # nom commercial (deja dans le logo: ne pas le repeter a cote)
    'societe': 'Global Smart Services',
    'bce': '0805.778.307',
    'adresse': 'Jozef Van Elewijckstraat 86, 1853 Grimbergen',
    'logo_path': os.path.join(RACINE, 'static', 'logo.png'),   # fichier fourni, jamais retouche
    'logo_url': '/static/logo.png',
    'logo_ratio': 600 / 127,                  # largeur / hauteur du fichier
    # Couleurs relevees dans le logo
    'couleur_primaire': '#1F4E79',
    'couleur_accent': '#4FC3F7',
    'couleur_texte': '#1A2733',
    'couleur_texte_secondaire': '#64748B',
    'couleur_fond_clair': '#F5F8FB',
    'couleur_ligne': '#DCE4EC',
}
CLES_TENANT = ('nom', 'societe', 'bce', 'adresse', 'logo_path', 'logo_url', 'logo_ratio',
               'couleur_primaire', 'couleur_accent')


def url_statique(nom):
    """Adresse d'un fichier de static/ suivie de sa date de modification
    (ex. /static/style.css?v=1790859000): le navigateur recharge le fichier
    des qu'il change, et le garde en cache sinon. A utiliser pour TOUT fichier
    statique (dans les gabarits: {{ statique('style.css') }})."""
    try:
        version = int(os.path.getmtime(os.path.join(RACINE, 'static', nom)))
    except OSError:
        return f"/static/{nom}"
    return f"/static/{nom}?v={version}"


def get_branding(tenant=None):
    """Identite a appliquer. tenant: dict d'identite propre (marque blanche) ou None."""
    b = dict(DEFAUT, logo_url=url_statique('logo.png'))
    for cle in CLES_TENANT:
        if (tenant or {}).get(cle):
            b[cle] = tenant[cle]
    if not (b['logo_path'] and os.path.exists(b['logo_path'])):
        b['logo_path'] = None   # logo absent: le nom commercial est affiche en texte
    b['mentions'] = f"{b['societe']} · BCE {b['bce']} · {b['adresse']}"
    return b


# ── PDF (reportlab importe ici seulement: les pages n'en ont pas besoin) ──
def couleur(cle, tenant=None):
    """Couleur de marque pour reportlab: couleur('primaire'), couleur('ligne')..."""
    from reportlab.lib import colors
    return colors.HexColor(get_branding(tenant)[f'couleur_{cle}'])


def pdf_logo(largeur_cm=4.2, tenant=None, alignement='LEFT'):
    """Logo a placer en tete d'un PDF (ou le nom commercial si le fichier manque)."""
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import Image, Paragraph
    b = get_branding(tenant)
    if b['logo_path']:
        img = Image(b['logo_path'], width=largeur_cm * cm, height=largeur_cm * cm / b['logo_ratio'])
        img.hAlign = alignement
        return img
    return Paragraph(b['nom'], ParagraphStyle('marque', fontName='Helvetica-Bold', fontSize=15, leading=18,
                                              textColor=couleur('primaire', tenant)))


def pdf_pied_de_page(tenant=None, numeroter=True):
    """Fonction onFirstPage / onLaterPages: mentions legales en bas de chaque page.
    Usage: pied = pdf_pied_de_page(); doc.build(elements, onFirstPage=pied, onLaterPages=pied)"""
    from reportlab.lib.units import cm
    b = get_branding(tenant)

    def pied(canvas, doc):
        largeur = doc.pagesize[0]
        canvas.saveState()
        canvas.setStrokeColor(couleur('ligne', tenant)); canvas.setLineWidth(0.4)
        canvas.line(doc.leftMargin, 1.0 * cm, largeur - doc.rightMargin, 1.0 * cm)
        canvas.setFont('Helvetica', 6.5); canvas.setFillColor(couleur('texte_secondaire', tenant))
        canvas.drawString(doc.leftMargin, 0.65 * cm, b['mentions'])
        if numeroter:
            canvas.drawRightString(largeur - doc.rightMargin, 0.65 * cm, f"Page {doc.page}")
        canvas.restoreState()
    return pied


def pdf_decor(tenant=None, logo=True, numeroter=True):
    """Habillage commun d'un PDF, a passer a doc.build(elements, **pdf_decor()):
    logo dans la marge haute de la premiere page (le contenu du document ne
    bouge pas) et mentions legales en pied de chaque page. logo=False quand le
    document place deja pdf_logo() dans son propre en-tete."""
    from reportlab.lib.units import cm
    b = get_branding(tenant)
    pied = pdf_pied_de_page(tenant, numeroter)

    def premiere(canvas, doc):
        if logo and b['logo_path']:
            largeur = 4.2 * cm
            hauteur = largeur / b['logo_ratio']
            canvas.drawImage(b['logo_path'], doc.leftMargin, doc.pagesize[1] - 0.3 * cm - hauteur,
                             width=largeur, height=hauteur, mask='auto')
        pied(canvas, doc)
    return {'onFirstPage': premiere, 'onLaterPages': pied}
