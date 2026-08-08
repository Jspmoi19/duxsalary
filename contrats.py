"""
contrats.py — Génération des contrats CDI et CDD
Utilise cp_data.py pour les données sectorielles
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from datetime import datetime
import os

from cp_data import CP_DATABASE, calcul_preavis_semaines, is_ouvrier, get_heures_semaine

OUTPUT_DIR = "outputs"

BLUE = colors.HexColor('#1F4E79')
DARK = colors.HexColor('#1a1a1a')
GREY = colors.HexColor('#f5f5f5')
GREY_LINE = colors.HexColor('#cccccc')

def styles():
    sN = ParagraphStyle('N', fontName='Helvetica', fontSize=10, leading=14)
    sB = ParagraphStyle('B', fontName='Helvetica-Bold', fontSize=10, leading=14)
    sT = ParagraphStyle('T', fontName='Helvetica-Bold', fontSize=14, leading=20, alignment=TA_CENTER)
    sSub = ParagraphStyle('S', fontName='Helvetica-Bold', fontSize=11, leading=16, textColor=BLUE)
    sSm = ParagraphStyle('Sm', fontName='Helvetica', fontSize=9, leading=12)
    sC = ParagraphStyle('C', fontName='Helvetica', fontSize=10, leading=14, alignment=TA_CENTER)
    sJ = ParagraphStyle('J', fontName='Helvetica', fontSize=10, leading=14, alignment=TA_JUSTIFY)
    return sN, sB, sT, sSub, sSm, sC, sJ


def _entete(elements, data, sN, sB):
    elements.append(Paragraph(f"<b>{data['nom_societe']}</b>", sB))
    elements.append(Paragraph(data['adresse_societe'], sN))
    elements.append(Paragraph(f"BCE : {data['bce_societe']}  |  N° RSZ : {data['rsz_societe']}", sN))
    elements.append(Spacer(1, 0.4*cm))
    elements.append(HRFlowable(width="100%", thickness=2, color=BLUE))
    elements.append(Spacer(1, 0.5*cm))


def _parties(elements, data, cp_info, sN, sB, sJ):
    elements.append(Paragraph("<b>L'EMPLOYEUR :</b>", sB))
    elements.append(Paragraph(
        f"{data['nom_societe']}, société à responsabilité limitée, dont le siège social est établi à "
        f"{data['adresse_societe']}, inscrite à la BCE sous le numéro {data['bce_societe']}, "
        f"identifiée à l'ONSS sous le numéro {data['rsz_societe']}, "
        f"représentée par {data['representant']}, ci-après dénommé « l'employeur »,", sJ))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(Paragraph("<b>D'UNE PART, ET :</b>", sB))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph("<b>LE/LA TRAVAILLEUR(SE) :</b>", sB))
    for label, val in [
        ("Nom et prénom :", f"<b>{data['nom_travailleur']}</b>"),
        ("Adresse :", data['adresse_travailleur']),
        ("Date de naissance :", data['ddn_travailleur']),
        ("N° registre national (NISS) :", data['niss_travailleur']),
    ]:
        elements.append(Paragraph(f"{label} <b>{val}</b>" if "<b>" not in val else f"{label} {val}", sN))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph("ci-après dénommé(e) « le/la travailleur(se) »,", sN))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(Paragraph("<b>D'AUTRE PART,</b>", sB))
    elements.append(Spacer(1, 0.15*cm))
    elements.append(Paragraph("Il a été convenu ce qui suit :", sN))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=GREY_LINE))
    elements.append(Spacer(1, 0.25*cm))


def _signatures(elements, data, sN, sB, sC):
    elements.append(HRFlowable(width="100%", thickness=0.5, color=GREY_LINE))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(Paragraph(
        f"Fait à <b>{data['lieu_signature']}</b>, le <b>{data['date_signature']}</b>, "
        f"en deux exemplaires originaux, dont un exemplaire remis à chaque partie.", sN))
    elements.append(Spacer(1, 0.8*cm))
    sig_data = [
        [Paragraph("<b>L'EMPLOYEUR</b>", sC), Paragraph("<b>LE/LA TRAVAILLEUR(SE)</b>", sC)],
        [Paragraph(data['nom_societe'], sC), Paragraph(data['nom_travailleur'], sC)],
        [Paragraph(data['representant'], ParagraphStyle('', fontName='Helvetica', fontSize=9, alignment=TA_CENTER, textColor=colors.grey)), ''],
        [Spacer(1, 1.5*cm), Spacer(1, 1.5*cm)],
        [Paragraph("_______________________", sN), Paragraph("_______________________", sN)],
        [Paragraph("Signature et cachet", sN), Paragraph("Signature", sN)],
        [Spacer(1, 1*cm), Spacer(1, 1*cm)],
        [Paragraph("Lu et approuvé :", sN), Paragraph("Lu et approuvé :", sN)],
    ]
    sig_table = Table(sig_data, colWidths=[8.5*cm, 8.5*cm])
    sig_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('TOPPADDING', (0,0), (-1,-1), 4)]))
    elements.append(sig_table)


def generer_contrat_cdi(data):
    """Génère un contrat CDI complet selon la CP."""
    cp_key = data['cp_key']
    cp_info = CP_DATABASE.get(cp_key, {})
    ouvrier = is_ouvrier(cp_key)
    heures_sem = get_heures_semaine(cp_key)
    type_travailleur = "ouvrier" if ouvrier else "employé(e)"

    filename = f"contrat_CDI_{data['nom_travailleur'].replace(' ', '_')}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=2.5*cm, rightMargin=2.5*cm)

    sN, sB, sT, sSub, sSm, sC, sJ = styles()
    elements = []

    _entete(elements, data, sN, sB)

    titre = f"CONTRAT DE TRAVAIL À DURÉE INDÉTERMINÉE"
    sous_titre = f"{'OUVRIER' if ouvrier else 'EMPLOYÉ(E)'} — {cp_key}"
    elements.append(Paragraph(titre, sT))
    elements.append(Paragraph(sous_titre, ParagraphStyle('', fontName='Helvetica-Bold', fontSize=11, alignment=TA_CENTER, textColor=BLUE)))
    elements.append(Paragraph("Loi du 3 juillet 1978 relative aux contrats de travail", ParagraphStyle('', fontName='Helvetica', fontSize=10, alignment=TA_CENTER)))
    elements.append(Spacer(1, 0.6*cm))

    elements.append(Paragraph("ENTRE LES SOUSSIGNÉS :", ParagraphStyle('S2', fontName='Helvetica-Bold', fontSize=11, leading=16, textColor=BLUE)))
    elements.append(Spacer(1, 0.3*cm))
    _parties(elements, data, cp_info, sN, sB, sJ)

    # Articles
    preavis_semaines = calcul_preavis_semaines(cp_key, 0)  # Préavis départ à l'ancienneté 0

    baremes = cp_info.get("baremes", {})
    min_horaire = data.get('salaire_horaire', '—')

    articles = [
        ("Article 1 – Nature du contrat",
         f"Le présent contrat est un contrat de travail à durée <b>INDÉTERMINÉE (CDI)</b>, "
         f"conclu conformément à la loi du 3 juillet 1978 relative aux contrats de travail. "
         f"Il prend cours le <b>{data['date_debut']}</b> et demeure en vigueur jusqu'à sa rupture "
         f"par l'une des parties moyennant le respect des délais de préavis légaux."),

        ("Article 2 – Statut et commission paritaire",
         f"Le/la travailleur(se) est engagé(e) en qualité d'<b>{type_travailleur}</b> au sens de "
         f"la loi du 3 juillet 1978. Le présent contrat est régi par la <b>{cp_info.get('meta', {}).get('nom', cp_key)}</b>. "
         f"Les dispositions de la commission paritaire et de ses conventions collectives de travail "
         f"s'appliquent de plein droit."),

        ("Article 3 – Fonction et lieu de travail",
         f"Le/la travailleur(se) est engagé(e) en qualité de <b>{data['fonction']}</b> "
         f"(catégorie : {data.get('categorie', '—')}). "
         f"Le travail sera effectué principalement au lieu suivant : <b>{data['lieu_travail']}</b>, "
         f"sans préjudice de déplacements ponctuels liés à la nature de la fonction. "
         f"L'employeur se réserve le droit de modifier le lieu de travail dans les limites "
         f"autorisées par la loi et la commission paritaire applicable."),

        ("Article 4 – Durée du travail",
         f"Le/la travailleur(se) est occupé(e) à <b>{'temps plein' if data.get('temps_plein', True) else 'temps partiel'}</b>, "
         f"à raison de <b>{data.get('heures_jour', heures_sem/5):.1f}h/jour</b> × "
         f"<b>{data.get('jours_semaine', 5)} jours/semaine</b> = "
         f"<b>{float(data.get('heures_jour', heures_sem/5)) * int(data.get('jours_semaine', 5)):.1f}h/semaine</b> "
         f"({data.get('horaire_journalier', '')}), "
         f"conformément au règlement de travail. "
         f"{'Pour le personnel roulant : application du règlement CE n° 561/2006.' if '140' in cp_key else ''}"),

        ("Article 5 – Rémunération",
         f"La rémunération brute est fixée à <b>{data.get('salaire_horaire', '—')} € brut de l'heure</b> "
         f"{'(soit ' + str(data.get('salaire_mensuel', '—')) + ' € brut/mois à temps plein)' if data.get('salaire_mensuel') else ''}, "
         f"conformément aux barèmes minimaux de la {cp_key}. "
         f"Le salaire est payé par virement bancaire, le dernier jour ouvrable du mois concerné. "
         f"{'Les cotisations ONSS ordinaires sont appliquées (part personnelle 13,07% + part patronale ~25%).' if not ouvrier else 'Régime ouvrier : cotisations ONSS + pécule de vacances via Office National des Vacances Annuelles (ONVA).'}"
         ),

        ("Article 6 – Période d'essai",
         f"Conformément à la loi du 26 décembre 2013 instaurant le statut unique, "
         f"<b>aucune période d'essai ne peut être prévue</b> dans un contrat à durée indéterminée. "
         f"Durant les <b>6 premiers mois</b>, le délai de préavis est limité à 2 semaines "
         f"(pour l'employeur) ou 1 semaine (pour le travailleur)."),

        ("Article 7 – Délais de préavis",
         f"En cas de résiliation du présent contrat, les parties respecteront les délais de préavis "
         f"fixés par la loi du 26 décembre 2013 (statut unique). À titre indicatif, pour une ancienneté "
         f"de 0 à 3 mois, le délai est de <b>2 semaines</b> (employeur) ou <b>1 semaine</b> (travailleur). "
         f"Ce délai augmente progressivement avec l'ancienneté (jusqu'à 30 semaines pour >10 ans). "
         f"En cas de faute grave dûment constatée, le contrat peut être rompu sans préavis ni indemnité."),

        ("Article 8 – Indemnités de transport",
         "L'employeur intervient dans les frais de transport domicile-lieu de travail "
         "conformément aux dispositions de la " + cp_key + " et de la CCT interprofessionnelle n° 19/11. "
         "Les modalités (train, vélo, véhicule personnel) et montants sont précisés dans le "
         "document annexe relatif aux frais de déplacement, remis au travailleur lors de son entrée en service. "
         "Les indemnités transport sont exonérées de cotisations ONSS et de précompte professionnel "
         "dans les limites légales applicables."),

        ("Article 9 – Assurance accidents du travail",
         f"Le/la travailleur(se) est couvert(e) par la police d'assurance accidents du travail "
         f"souscrite par l'employeur auprès de : <b>{data.get('assurance_at', '—')}</b>, "
         f"conformément à la loi du 10 avril 1971 sur les accidents du travail."),

        ("Article 10 – Confidentialité et obligations",
         f"Le/la travailleur(se) s'engage à respecter la stricte confidentialité concernant "
         f"toutes les informations relatives à l'activité de l'employeur, à ses clients et partenaires, "
         f"et ce, tant pendant la durée du contrat qu'après sa cessation. "
         f"Cette obligation de discrétion s'étend aux données personnelles (RGPD) et aux "
         f"informations financières ou commerciales dont il/elle aurait connaissance dans l'exercice de ses fonctions."),

        ("Article 11 – Règlement de travail",
         f"Le/la travailleur(se) déclare avoir pris connaissance du règlement de travail "
         f"de l'entreprise, qui lui a été remis ce jour, et s'engage à en respecter l'ensemble des dispositions. "
         f"Le règlement de travail fait partie intégrante du présent contrat."),

        ("Article 12 – Droit applicable",
         f"Le présent contrat est régi exclusivement par le droit belge. "
         f"Les cours et tribunaux belges sont seuls compétents pour tout litige relatif à son exécution. "
         f"Toute disposition contraire à une norme d'ordre public ou impérative sera réputée non écrite, "
         f"sans affecter la validité des autres clauses."),
    ]

    # Clauses spécifiques ouvriers
    if ouvrier:
        articles.append((
            "Article 13 – Régime vacances annuelles (ouvriers)",
            f"Le/la travailleur(se) bénéficie du régime légal des vacances annuelles des ouvriers. "
            f"Le pécule de vacances (simple et double) est calculé et payé par l'Office National "
            f"des Vacances Annuelles (ONVA) sur base des salaires déclarés à l'ONSS. "
            f"L'employeur verse à l'ONSS les cotisations ONSS vacances (≈10,27% du brut). "
            f"Le pécule de vacances n'est PAS avancé par l'employeur."
        ))

    # Clauses spécifiques construction
    if "124" in cp_key:
        articles.append((
            "Article 14 – Dispositions spécifiques construction (CP 124)",
            f"En application des CCT de la CP 124 : "
            f"(1) Les timbres-fidélité Constructiv sont obligatoires — cotisation patronale ~18,8% sur brut. "
            f"(2) Le/la travailleur(se) bénéficie de l'assurance hospitalisation sectorielle après 6 mois. "
            f"(3) Une pension complémentaire sectorielle est constituée via Constructiv. "
            f"(4) Les travaux en hauteur (>15m) donnent droit à un supplément de 10%. "
            f"(5) Les barèmes sont indexés trimestriellement — l'employeur s'engage à appliquer "
            f"les indexations publiées par Constructiv (constructiv.be) dès leur entrée en vigueur."
        ))

    # Clauses spécifiques transport
    if "140" in cp_key:
        articles.append((
            "Article 14 – Dispositions spécifiques transport (CP 140.03)",
            f"En application des CCT de la CP 140.03 : "
            f"(1) Pour le personnel roulant : respect obligatoire du règlement CE 561/2006 "
            f"(temps de conduite, pauses, repos journaliers et hebdomadaires). "
            f"(2) Tachygraphe : utilisation obligatoire et conforme pour les véhicules >3,5T. "
            f"(3) Chèques-repas : 3,09€/jour presté (depuis 01/07/2026). "
            f"(4) Vêtements de travail fournis et entretenus par l'employeur. "
            f"(5) Formation CPC obligatoire pour permis C/CE : 35h tous les 5 ans."
        ))

    # Clauses spécifiques nettoyage
    if "121" in cp_key:
        articles.append((
            "Article 14 – Dispositions spécifiques nettoyage (CP 121)",
            f"En application des CCT de la CP 121 : "
            f"(1) Durée hebdomadaire : 36h30 (et non 38h). "
            f"(2) Prime de fin d'année : 9% des salaires bruts déclarés, versée par le Fonds Social Nettoyage. "
            f"(3) Vêtements de travail fournis et entretenus par l'employeur. "
            f"(4) Indexation semestrielle (01/01 et 01/07) — l'employeur s'engage à appliquer "
            f"les indexations dès leur entrée en vigueur."
        ))

    for titre_art, texte_art in articles:
        elements.append(Paragraph(f"<b>{titre_art}</b>", sSub))
        elements.append(Spacer(1, 0.15*cm))
        elements.append(Paragraph(texte_art, sJ))
        elements.append(Spacer(1, 0.35*cm))

    _signatures(elements, data, sN, sB, sC)

    # Mentions légales CCT
    elements.append(Spacer(1, 0.3*cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=GREY_LINE))
    elements.append(Spacer(1, 0.2*cm))
    mentions = cp_info.get("mentions_contrat", [])
    if mentions:
        elements.append(Paragraph("<b>Bases légales et conventionnelles applicables :</b>", ParagraphStyle('', fontName='Helvetica-Bold', fontSize=8, textColor=BLUE)))
        for m in mentions:
            elements.append(Paragraph(f"• {m}", ParagraphStyle('', fontName='Helvetica', fontSize=8, leading=11)))

    doc.build(elements)
    return filepath, filename


def generer_contrat_cdd(data):
    """Génère un contrat CDD complet selon la CP."""
    cp_key = data['cp_key']
    cp_info = CP_DATABASE.get(cp_key, {})
    ouvrier = is_ouvrier(cp_key)
    heures_sem = get_heures_semaine(cp_key)
    type_travailleur = "ouvrier" if ouvrier else "employé(e)"

    filename = f"contrat_CDD_{data['nom_travailleur'].replace(' ', '_')}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=2.5*cm, rightMargin=2.5*cm)

    sN, sB, sT, sSub, sSm, sC, sJ = styles()
    elements = []

    _entete(elements, data, sN, sB)

    elements.append(Paragraph("CONTRAT DE TRAVAIL À DURÉE DÉTERMINÉE", sT))
    elements.append(Paragraph(f"{'OUVRIER' if ouvrier else 'EMPLOYÉ(E)'} — {cp_key}", ParagraphStyle('', fontName='Helvetica-Bold', fontSize=11, alignment=TA_CENTER, textColor=BLUE)))
    elements.append(Paragraph("Loi du 3 juillet 1978 relative aux contrats de travail – Article 9", ParagraphStyle('', fontName='Helvetica', fontSize=10, alignment=TA_CENTER)))
    elements.append(Spacer(1, 0.6*cm))

    elements.append(Paragraph("ENTRE LES SOUSSIGNÉS :", ParagraphStyle('S2', fontName='Helvetica-Bold', fontSize=11, leading=16, textColor=BLUE)))
    elements.append(Spacer(1, 0.3*cm))
    _parties(elements, data, cp_info, sN, sB, sJ)

    motif_cdd = data.get('motif_cdd', 'accroissement temporaire de travail')

    articles = [
        ("Article 1 – Nature et durée du contrat",
         f"Le présent contrat est un contrat de travail à durée <b>DÉTERMINÉE (CDD)</b>, "
         f"conclu conformément à l'article 9 de la loi du 3 juillet 1978. "
         f"Il est conclu pour la période du <b>{data['date_debut']}</b> au <b>{data['date_fin']}</b> inclus. "
         f"Le contrat prend fin de plein droit à l'échéance du terme, sans qu'il soit nécessaire "
         f"de donner un préavis, sauf disposition contraire ci-après. "
         f"<b>Motif justificatif du CDD :</b> {motif_cdd}."),

        ("Article 2 – Justification du recours au CDD",
         f"Conformément à l'article 10 de la loi du 3 juillet 1978, le recours à un contrat "
         f"à durée déterminée est justifié par : <b>{motif_cdd}</b>. "
         f"À défaut de motif valable ou en cas de continuation de fait au-delà du terme, "
         f"le contrat sera requalifié en CDI conformément à l'article 11 de la même loi. "
         f"Le nombre maximum de CDD successifs autorisé est de 4 (ou 2 ans de durée cumulée) "
         f"sauf dérogation conventionnelle."),

        ("Article 3 – Statut et commission paritaire",
         f"Le/la travailleur(se) est engagé(e) en qualité d'<b>{type_travailleur}</b>. "
         f"Le présent contrat est régi par la <b>{cp_info.get('meta', {}).get('nom', cp_key)}</b> "
         f"et l'ensemble de ses conventions collectives de travail."),

        ("Article 4 – Fonction et lieu de travail",
         f"Le/la travailleur(se) est engagé(e) en qualité de <b>{data['fonction']}</b> "
         f"(catégorie : {data.get('categorie', '—')}). "
         f"Lieu de travail : <b>{data['lieu_travail']}</b>."),

        ("Article 5 – Durée du travail",
         f"Le/la travailleur(se) est occupé(e) à <b>{'temps plein' if data.get('temps_plein', True) else 'temps partiel'}</b>, "
         f"à raison de <b>{data.get('heures_jour', heures_sem/5):.1f}h/jour</b> × "
         f"<b>{data.get('jours_semaine', 5)} jours/semaine</b> = "
         f"<b>{float(data.get('heures_jour', heures_sem/5)) * int(data.get('jours_semaine', 5)):.1f}h/semaine</b> "
         f"({data.get('horaire_journalier', '')}), "
         f"conformément au règlement de travail."),

        ("Article 6 – Rémunération",
         f"La rémunération brute est fixée à <b>{data.get('salaire_horaire', '—')} € brut de l'heure</b>, "
         f"conformément aux barèmes de la {cp_key}. "
         f"Paiement par virement bancaire, le dernier jour ouvrable du mois."),

        ("Article 7 – Rupture anticipée",
         f"Durant les <b>6 premiers mois</b> d'exécution, chaque partie peut mettre fin au contrat "
         f"moyennant un préavis calculé comme pour un CDI (2 semaines pour l'employeur, "
         f"1 semaine pour le travailleur, dans les 3 premiers mois). "
         f"Après 6 mois, la rupture anticipée par l'une des parties donne droit à une indemnité "
         f"équivalente au salaire correspondant à la moitié de la durée restante du contrat "
         f"(art. 40 loi 03/07/1978), sauf faute grave dûment constatée."),

        ("Article 8 – Renouvellement",
         f"Le présent contrat peut être renouvelé dans les limites fixées par l'article 10bis "
         f"de la loi du 3 juillet 1978 : maximum 4 contrats successifs auprès du même employeur "
         f"pour une durée totale cumulée de 2 ans maximum. Tout dépassement de ces limites entraîne "
         f"la requalification en CDI."),

        ("Article 9 – Assurance accidents du travail",
         f"Le/la travailleur(se) est couvert(e) par la police accidents du travail de l'employeur "
         f"auprès de : <b>{data.get('assurance_at', '—')}</b> (loi du 10 avril 1971)."),

        ("Article 10 – Confidentialité et règlement de travail",
         f"Le/la travailleur(se) s'engage à respecter la confidentialité et le règlement de travail "
         f"de l'entreprise, dont un exemplaire lui a été remis. Ces documents font partie intégrante "
         f"du présent contrat."),

        ("Article 11 – Droit applicable",
         f"Le présent contrat est soumis au droit belge. "
         f"Les tribunaux du travail belges sont seuls compétents."),
    ]

    if ouvrier:
        articles.append((
            "Article 12 – Vacances annuelles (ouvriers)",
            f"Régime ouvrier : pécule de vacances calculé et payé par l'ONVA "
            f"sur base des cotisations ONSS déclarées par l'employeur (≈10,27% du brut)."
        ))

    if "124" in cp_key:
        articles.append((
            "Article 13 – Dispositions CP 124 Construction",
            f"Timbres-fidélité Constructiv obligatoires. Indexation trimestrielle applicable. "
            f"Assurance hospitalisation et pension complémentaire sectorielle via Constructiv. "
            f"Suppléments hauteur et amiante selon CCT."
        ))

    if "121" in cp_key:
        articles.append((
            "Article 13 – Dispositions CP 121 Nettoyage",
            f"Durée : 36h30/semaine. Prime fin d'année 9% (Fonds Social Nettoyage). "
            f"Indexation semestrielle applicable. Vêtements fournis par l'employeur."
        ))

    if "140" in cp_key:
        articles.append((
            "Article 13 – Dispositions CP 140.03 Transport",
            f"Personnel roulant : règlement CE 561/2006. Chèques-repas 3,09€/jour. "
            f"Vêtements fournis. Formation CPC maintenue."
        ))

    for titre_art, texte_art in articles:
        elements.append(Paragraph(f"<b>{titre_art}</b>", sSub))
        elements.append(Spacer(1, 0.15*cm))
        elements.append(Paragraph(texte_art, sJ))
        elements.append(Spacer(1, 0.35*cm))

    _signatures(elements, data, sN, sB, sC)

    elements.append(Spacer(1, 0.3*cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=GREY_LINE))
    elements.append(Spacer(1, 0.2*cm))
    mentions = cp_info.get("mentions_contrat", [])
    if mentions:
        elements.append(Paragraph("<b>Bases légales applicables :</b>", ParagraphStyle('', fontName='Helvetica-Bold', fontSize=8, textColor=BLUE)))
        for m in mentions:
            elements.append(Paragraph(f"• {m}", ParagraphStyle('', fontName='Helvetica', fontSize=8, leading=11)))

    doc.build(elements)
    return filepath, filename


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    test_data = {
        'nom_societe': 'Eysel Consult BV',
        'adresse_societe': 'Werkhuizenstraat 73, 1800 Vilvoorde',
        'bce_societe': '1028.267.306',
        'rsz_societe': '1078139-47',
        'representant': 'Leo Plavmyzha, Gérant',
        'assurance_at': 'Ethias – Police n° 45.678.901',
        'nom_travailleur': 'Jean DUPONT',
        'adresse_travailleur': 'Rue de la Loi 1, 1000 Bruxelles',
        'ddn_travailleur': '15/03/1995',
        'niss_travailleur': '95.03.15-123.45',
        'date_debut': '01/08/2026',
        'date_fin': '31/12/2026',
        'fonction': 'Aide-comptable',
        'categorie': 'Employé — minimum sectoriel',
        'lieu_travail': 'Werkhuizenstraat 73, 1800 Vilvoorde',
        'horaire_journalier': '08h00 – 16h36',
        'salaire_horaire': '13.20',
        'salaire_mensuel': '2174.42',
        'temps_plein': True,
        'cp_key': 'CP 336',
        'lieu_signature': 'Vilvoorde',
        'date_signature': '01/08/2026',
        'motif_cdd': 'accroissement temporaire de travail',
    }
    _, f1 = generer_contrat_cdi(test_data)
    _, f2 = generer_contrat_cdd(test_data)
    print(f"CDI généré : {f1}")
    print(f"CDD généré : {f2}")
