from flask import Flask, render_template, request, send_file, session, redirect, url_for
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_JUSTIFY
from branding import couleur, pdf_decor, get_branding, url_statique
import os, json as jsonlib
from datetime import datetime, date
import calendar
import werkzeug.utils

from cp_data import CP_DATABASE, get_heures_semaine, is_ouvrier, calcul_preavis_semaines
from contrats import generer_contrat_cdi, generer_contrat_cdd
from contrats_nl import generer_contrat_cdd_nl, generer_certificat_travail_nl, generer_c4_nl
from database import (init_db, get_all_dossiers, get_dossier, create_dossier,
                      update_dossier, get_travailleurs, get_travailleur,
                      create_travailleur, get_contrats, create_contrat,
                      get_fiches_paie, create_fiche_paie, get_conn)
from auth import login_required, authenticate
from occupation import contrats_actifs
from social_belgique import (CODES_JOURNALIERS, get_jours_feries,
                              calcul_paie_complet, calcul_onss)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'duxsalary2026secretkey')
OUTPUT_DIR = "outputs"
UPLOAD_DIR = "uploads"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.template_filter('basename')
def basename_filter(path):
    return os.path.basename(path) if path else ''

@app.context_processor
def injecter_marque():
    """Identite (logo, mentions, couleurs) disponible dans tous les gabarits -- branding.py."""
    return {'marque': get_branding(), 'statique': url_statique}

def get_context_base():
    tous = get_all_dossiers()
    actifs = [d for d in tous if d.get('statut') != 'archive']
    archives = [d for d in tous if d.get('statut') == 'archive']
    return {'tous_les_dossiers': actifs, 'dossiers_archives': archives}

def get_alertes_dossier(dossier_id):
    alertes = []
    today = date.today()
    mois = today.month
    annee = today.year
    dossier = get_dossier(dossier_id)
    date_activation = dossier.get('date_activation_rsz')

    def trimestre_actif(mois_debut, annee_act=None):
        if not date_activation: return True
        if annee_act is None: annee_act = annee
        import calendar as cal
        last_day = cal.monthrange(annee_act, mois_debut + 2)[1]
        fin_trimestre = date(annee_act, mois_debut + 2, last_day)
        return date_activation <= fin_trimestre

    if mois in [10, 11] and trimestre_actif(7):
        alertes.append({'message': f'DmfA Q3/{annee} à introduire sur socialsecurity.be', 'date': f'31/10/{annee}', 'niveau': 'urgent' if mois == 10 else 'warn'})
        alertes.append({'message': f'Paiement ONSS Q3/{annee}', 'date': f'31/10/{annee}', 'niveau': 'info'})
    if mois in [1, 2] and trimestre_actif(10, annee - 1):
        alertes.append({'message': f'DmfA Q4/{annee-1} à introduire', 'date': f'31/01/{annee}', 'niveau': 'warn'})
    if mois in [4, 5] and trimestre_actif(1):
        alertes.append({'message': f'DmfA Q1/{annee} à introduire', 'date': f'30/04/{annee}', 'niveau': 'warn'})
    if mois in [7, 8] and trimestre_actif(4):
        alertes.append({'message': f'DmfA Q2/{annee} à introduire', 'date': f'31/07/{annee}', 'niveau': 'warn'})
    if mois in [1, 2]:
        alertes.append({'message': f'Fiches 281.10 (Belcotax) — revenus {annee-1}', 'date': f'28/02/{annee}', 'niveau': 'warn'})

    # CDD arrivant à échéance
    conn = get_conn()
    from psycopg2.extras import RealDictCursor
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT t.prenom || ' ' || t.nom as nom, c.date_fin
        FROM contrats c JOIN travailleurs t ON t.id = c.travailleur_id
        WHERE c.dossier_id = %s AND c.type_contrat = 'CDD' AND c.date_fin IS NOT NULL
        AND c.date_fin BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days'
        AND c.statut = 'actif'
    """, (dossier_id,))
    for row in cur.fetchall():
        alertes.append({'message': f"CDD de {row['nom']} arrive à échéance", 'date': row['date_fin'].strftime('%d/%m/%Y'), 'niveau': 'urgent'})
    cur.close()
    conn.close()
    return alertes

# ── AUTH ──────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = authenticate(request.form['email'], request.form['password'])
        if user:
            session['user_id'] = user['id']
            session['user_nom'] = user['nom']
            session['user_role'] = user['role']
            dernier = session.get('dernier_dossier_id')
            if dernier:
                return redirect(url_for('dossier_dashboard', dossier_id=dernier))
            return redirect(url_for('dossiers'))
        return render_template('login.html', error='Email ou mot de passe incorrect.', tenant=get_tenant())
    return render_template('login.html', tenant=get_tenant())

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    dernier = session.get('dernier_dossier_id')
    if dernier:
        return redirect(url_for('dossier_dashboard', dossier_id=dernier))
    return redirect(url_for('dossiers'))

# ── DOSSIERS ──────────────────────────────────────────────────────────
@app.route('/dossiers')
@login_required
def dossiers():
    ctx = get_context_base()
    ctx['tenant'] = get_tenant()
    tous = get_all_dossiers()
    actifs = [d for d in tous if d.get('statut') != 'archive']
    return render_template('dossiers.html', dossiers=actifs, **ctx)

@app.route('/dossier/nouveau', methods=['GET', 'POST'])
@login_required
def nouveau_dossier():
    ctx = get_context_base()
    ctx['tenant'] = get_tenant()
    if request.method == 'POST':
        did = create_dossier(request.form)
        return redirect(url_for('dossier_dashboard', dossier_id=did))
    return render_template('nouveau_dossier.html', **ctx)

@app.route('/dossier/<int:dossier_id>')
@login_required
def dossier_dashboard(dossier_id):
    dossier = get_dossier(dossier_id)
    if not dossier:
        return redirect(url_for('dossiers'))
    session['dernier_dossier_id'] = dossier_id
    ctx = get_context_base()
    ctx['tenant'] = get_tenant()
    return render_template('dashboard.html',
                           dossier=dossier, dossier_actif=dossier,
                           echeances=get_echeances_dossier(dossier_id),
                           travailleurs=get_travailleurs(dossier_id),
                           contrats=get_contrats(dossier_id=dossier_id),
                           nb_contrats_actifs=len(contrats_actifs(get_contrats(dossier_id=dossier_id))),
                           fiches=get_fiches_paie(dossier_id=dossier_id, actives_seulement=True), **ctx)

@app.route('/dossier/<int:dossier_id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier_dossier(dossier_id):
    from onss_taux import categorie_existe, liste_categories, CODES_IMPORTANCE, CODES_FFE
    dossier = get_dossier(dossier_id)
    ctx = get_context_base()
    ctx['tenant'] = get_tenant()
    listes = dict(categories_onss=liste_categories(), codes_importance=CODES_IMPORTANCE, codes_ffe=CODES_FFE)
    if request.method == 'POST':
        # Donnees ONSS de l'employeur: validees AVANT tout enregistrement
        cat = (request.form.get('categorie_employeur') or '000').strip().zfill(3)
        imp = (request.form.get('code_importance') or '').strip()
        ffe = (request.form.get('code_ffe') or '').strip().upper()
        erreur = None
        if not categorie_existe(cat):
            erreur = f"Catégorie « {cat} » introuvable dans le fichier de taux ONSS."
        elif imp and imp not in dict(CODES_IMPORTANCE):
            erreur = f"Code d'importance « {imp} » invalide (0 à 9)."
        elif ffe and ffe not in dict(CODES_FFE):
            erreur = f"Code FFE « {ffe} » invalide (C, B, N ou O)."
        from dmfa import normaliser_unite_etablissement
        unite, erreur_unite = normaliser_unite_etablissement(request.form.get('numero_unite_etablissement'))
        erreur = erreur or erreur_unite
        if erreur:
            return render_template('modifier_dossier.html', dossier=dossier, dossier_actif=dossier,
                                   erreur_onss=erreur, **listes, **ctx)
        update_dossier(dossier_id, request.form)
        conn_c = get_conn(); cur_c = conn_c.cursor()
        cur_c.execute("UPDATE dossiers SET categorie_employeur=%s, code_importance=%s, code_ffe=%s, "
                      "numero_unite_etablissement=%s WHERE id=%s", (cat, imp or None, ffe or None, unite, dossier_id))
        conn_c.commit(); cur_c.close(); conn_c.close()
        return redirect(url_for('dossier_dashboard', dossier_id=dossier_id))
    return render_template('modifier_dossier.html', dossier=dossier, dossier_actif=dossier, **listes, **ctx)

@app.route('/dossier/<int:dossier_id>/archiver', methods=['POST'])
@login_required
def archiver_dossier(dossier_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE dossiers SET statut = 'archive', updated_at = NOW() WHERE id = %s", (dossier_id,))
    conn.commit(); cur.close(); conn.close()
    session.pop('dernier_dossier_id', None)
    return redirect(url_for('dossiers'))

@app.route('/dossier/<int:dossier_id>/supprimer', methods=['POST'])
@login_required
def supprimer_dossier(dossier_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE dossiers SET actif = FALSE WHERE id = %s", (dossier_id,))
    conn.commit(); cur.close(); conn.close()
    return redirect(url_for('dossiers'))

# ── TRAVAILLEURS ──────────────────────────────────────────────────────
def _enregistrer_premier_engagement(cur, travailleur_id, dossier_id, form):
    """Case « ce travailleur ouvre le droit au premier engagement » (code 3315): un seul
    travailleur par dossier -- la cocher ici la retire aux autres travailleurs du dossier."""
    coche = form.get('premier_engagement_travailleur') == 'on'
    if coche:
        cur.execute("UPDATE travailleurs SET premier_engagement = FALSE WHERE dossier_id = %s AND id <> %s",
                    (dossier_id, travailleur_id))
    cur.execute("UPDATE travailleurs SET premier_engagement = %s WHERE id = %s", (coche, travailleur_id))


def _titulaire_premier_engagement(dossier_id, sauf_id=None):
    """Nom de l'autre travailleur du dossier deja designe pour le premier engagement (ou None)."""
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT prenom, nom FROM travailleurs WHERE dossier_id = %s AND premier_engagement = TRUE AND id <> %s LIMIT 1",
                    (dossier_id, sauf_id or 0))
        row = cur.fetchone()
        cur.close(); conn.close()
        return f"{row[0]} {row[1]}" if row else None
    except Exception as ex:
        app.logger.warning(f"Premier engagement (titulaire): {ex}")
        return None


def _enregistrer_charges_famille(cur, travailleur_id, form):
    """Situation familiale et charges de famille (gabarit _charges_famille.html):
    memes colonnes pour la creation et la modification d'un travailleur."""
    from occupation import charges_famille_du_formulaire
    valeurs = charges_famille_du_formulaire(form)
    colonnes = list(valeurs)
    cur.execute(f"UPDATE travailleurs SET {', '.join(c + ' = %s' for c in colonnes)} WHERE id = %s",
                [valeurs[c] for c in colonnes] + [travailleur_id])


@app.route('/dossier/<int:dossier_id>/travailleur/nouveau', methods=['GET', 'POST'])
@login_required
def nouveau_travailleur(dossier_id):
    dossier = get_dossier(dossier_id)
    ctx = get_context_base()
    ctx['tenant'] = get_tenant()
    if request.method == 'POST':
        data = dict(request.form)
        data['dossier_id'] = dossier_id
        ddn = data.get('date_naissance', '')
        if ddn:
            try:
                p = ddn.split('/'); data['date_naissance'] = f"{p[2]}-{p[1]}-{p[0]}"
            except: data['date_naissance'] = None
        tid = create_travailleur(data)
        conn = get_conn(); cur = conn.cursor()
        _enregistrer_charges_famille(cur, tid, request.form)
        _enregistrer_premier_engagement(cur, tid, dossier_id, request.form)
        conn.commit(); cur.close(); conn.close()
        return redirect(url_for('fiche_travailleur', travailleur_id=tid))
    return render_template('nouveau_travailleur.html', dossier=dossier, dossier_actif=dossier, cp_keys=list(CP_DATABASE.keys()),
                           titulaire_premier_engagement=_titulaire_premier_engagement(dossier_id), **ctx)

@app.route('/travailleur/<int:travailleur_id>')
@login_required
def fiche_travailleur(travailleur_id):
    from fiches_remplacees import libelle_remplacement
    from occupation import contrat_actif
    travailleur = get_travailleur(travailleur_id)
    dossier = get_dossier(travailleur['dossier_id'])
    ctx = get_context_base()
    ctx['tenant'] = get_tenant()
    tab = request.args.get('tab', 'info')
    documents = get_documents_travailleur(travailleur_id)
    return render_template('fiche_travailleur.html',
                           travailleur=travailleur, dossier=dossier, dossier_actif=dossier,
                           tab=tab, contrats=[dict(c, en_cours=contrat_actif(c)) for c in get_contrats(travailleur_id=travailleur_id)],
                           fiches=[dict(f, remplacement=libelle_remplacement(f))
                                   for f in get_fiches_paie(travailleur_id=travailleur_id)],
                           documents=documents, **ctx)

@app.route('/travailleur/<int:travailleur_id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier_travailleur(travailleur_id):
    travailleur = get_travailleur(travailleur_id)
    dossier = get_dossier(travailleur['dossier_id'])
    ctx = get_context_base()
    ctx['tenant'] = get_tenant()
    if request.method == 'POST':
        conn = get_conn()
        cur = conn.cursor()
        ddn = request.form.get('date_naissance', '')
        ddn_db = None
        if ddn:
            try:
                p = ddn.split('/'); ddn_db = f"{p[2]}-{p[1]}-{p[0]}"
            except: pass
        cur.execute("""UPDATE travailleurs SET prenom=%s, nom=%s, niss=%s, date_naissance=%s,
            adresse=%s, iban=%s, email=%s, telephone=%s, langue=%s,
            sexe=%s, date_sortie=%s, caisse_allocations_familiales=%s
            WHERE id=%s""",
            (request.form['prenom'], request.form['nom'], request.form.get('niss'),
             ddn_db, request.form.get('adresse'), request.form.get('iban'),
             request.form.get('email'), request.form.get('telephone'),
             request.form.get('langue', 'fr'),
             request.form.get('sexe') or None, request.form.get('date_sortie') or None,
             request.form.get('caisse_allocations_familiales') or None,
             travailleur_id))
        _enregistrer_charges_famille(cur, travailleur_id, request.form)
        _enregistrer_premier_engagement(cur, travailleur_id, travailleur['dossier_id'], request.form)
        conn.commit(); cur.close(); conn.close()
        return redirect(url_for('fiche_travailleur', travailleur_id=travailleur_id))
    return render_template('modifier_travailleur.html', travailleur=travailleur, dossier=dossier, dossier_actif=dossier, cp_keys=list(CP_DATABASE.keys()),
                           titulaire_premier_engagement=_titulaire_premier_engagement(travailleur['dossier_id'], travailleur_id), **ctx)

@app.route('/travailleur/<int:travailleur_id>/supprimer', methods=['POST'])
@login_required
def supprimer_travailleur(travailleur_id):
    travailleur = get_travailleur(travailleur_id)
    dossier_id = travailleur['dossier_id']
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE travailleurs SET actif = FALSE WHERE id = %s", (travailleur_id,))
    conn.commit(); cur.close(); conn.close()
    return redirect(url_for('dossier_dashboard', dossier_id=dossier_id))

# ── DOCUMENTS ─────────────────────────────────────────────────────────
def get_documents_travailleur(travailleur_id):
    conn = get_conn()
    from psycopg2.extras import RealDictCursor
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM documents WHERE travailleur_id = %s ORDER BY uploaded_at DESC", (travailleur_id,))
    docs = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return docs

@app.route('/travailleur/<int:travailleur_id>/document/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter_document(travailleur_id):
    travailleur = get_travailleur(travailleur_id)
    dossier = get_dossier(travailleur['dossier_id'])
    ctx = get_context_base()
    ctx['tenant'] = get_tenant()
    if request.method == 'POST':
        fichier = request.files.get('fichier')
        if fichier and fichier.filename:
            filename = werkzeug.utils.secure_filename(fichier.filename)
            unique_name = f"{travailleur_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            filepath = os.path.join(UPLOAD_DIR, unique_name)
            fichier.save(filepath)
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("""INSERT INTO documents (dossier_id, travailleur_id, nom, type_document, filename, filepath, taille, uploaded_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (travailleur['dossier_id'], travailleur_id,
                 request.form.get('nom', filename), request.form.get('type_document', 'autre'),
                 unique_name, filepath, os.path.getsize(filepath), session['user_id']))
            conn.commit(); cur.close(); conn.close()
        return redirect(url_for('fiche_travailleur', travailleur_id=travailleur_id, tab='documents'))
    return render_template('upload_document.html', travailleur=travailleur, dossier=dossier, dossier_actif=dossier, **ctx)

@app.route('/contrat/<int:contrat_id>/archiver', methods=['POST'])
@login_required
def archiver_contrat(contrat_id):
    conn = get_conn()
    from psycopg2.extras import RealDictCursor
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT dossier_id, travailleur_id FROM contrats WHERE id = %s", (contrat_id,))
    c = cur.fetchone()
    cur.execute("UPDATE contrats SET statut = 'archive' WHERE id = %s", (contrat_id,))
    conn.commit(); cur.close(); conn.close()
    return redirect(url_for('fiche_travailleur', travailleur_id=c['travailleur_id'], tab='contrats'))

@app.route('/dossier/<int:dossier_id>/document/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter_document_dossier(dossier_id):
    dossier = get_dossier(dossier_id)
    ctx = get_context_base()
    ctx['tenant'] = get_tenant()
    if request.method == 'POST':
        fichier = request.files.get('fichier')
        if fichier and fichier.filename:
            filename = werkzeug.utils.secure_filename(fichier.filename)
            unique_name = f"dossier_{dossier_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            filepath = os.path.join(UPLOAD_DIR, unique_name)
            fichier.save(filepath)
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("""INSERT INTO documents (dossier_id, travailleur_id, nom, type_document, filename, filepath, taille, uploaded_by, niveau)
                VALUES (%s, NULL, %s, %s, %s, %s, %s, %s, 'dossier')""",
                (dossier_id, request.form.get('nom', filename),
                 request.form.get('type_document', 'autre'),
                 unique_name, filepath, os.path.getsize(filepath), session['user_id']))
            conn.commit(); cur.close(); conn.close()
        return redirect(url_for('dossier_dashboard', dossier_id=dossier_id))
    return render_template('upload_document_dossier.html', dossier=dossier, dossier_actif=dossier, **ctx)

@app.route('/document/<int:doc_id>/download')
@login_required
def download_document(doc_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT filepath, nom FROM documents WHERE id = %s", (doc_id,))
    doc = cur.fetchone()
    cur.close(); conn.close()
    if doc and os.path.exists(doc[0]):
        return send_file(doc[0], as_attachment=True, download_name=doc[1])
    return "Document introuvable", 404

# ── DIMONA ────────────────────────────────────────────────────────────
def get_dimona_travailleur(travailleur_id):
    conn = get_conn()
    from psycopg2.extras import RealDictCursor
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM dimona WHERE travailleur_id = %s ORDER BY date_debut DESC", (travailleur_id,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows

def get_dimona(dimona_id):
    conn = get_conn()
    from psycopg2.extras import RealDictCursor
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM dimona WHERE id = %s", (dimona_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return dict(row) if row else None

@app.route('/travailleur/<int:travailleur_id>/dimona')
@login_required
def dimona_list(travailleur_id):
    travailleur = get_travailleur(travailleur_id)
    dossier = get_dossier(travailleur['dossier_id'])
    ctx = get_context_base()
    ctx['tenant'] = get_tenant()
    return render_template('dimona_list.html', travailleur=travailleur,
                           dossier=dossier, dossier_actif=dossier,
                           dimona_list=get_dimona_travailleur(travailleur_id), **ctx)

@app.route('/travailleur/<int:travailleur_id>/dimona/nouvelle', methods=['GET', 'POST'])
@login_required
def nouvelle_dimona(travailleur_id):
    travailleur = get_travailleur(travailleur_id)
    dossier = get_dossier(travailleur['dossier_id'])
    ctx = get_context_base()
    ctx['tenant'] = get_tenant()
    if request.method == 'POST':
        form = request.form
        conn = get_conn()
        cur = conn.cursor()
        contrat_id = form.get('contrat_id') or None
        if contrat_id: contrat_id = int(contrat_id)
        cur.execute("""INSERT INTO dimona (dossier_id, travailleur_id, type_dimona, date_debut, date_fin, numero_reference, notes, contrat_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (travailleur['dossier_id'], travailleur_id, form['type_dimona'], form['date_debut'],
             form.get('date_fin') or None, form.get('numero_reference') or None, form.get('notes') or None, contrat_id))
        did = cur.fetchone()[0]
        conn.commit(); cur.close(); conn.close()
        return redirect(url_for('calendrier_prestations', dimona_id=did))
    # Récupérer les contrats actifs du travailleur pour le sélecteur
    from psycopg2.extras import RealDictCursor
    conn2 = get_conn()
    cur2 = conn2.cursor(cursor_factory=RealDictCursor)
    cur2.execute("""SELECT id, type_contrat, salaire_horaire, date_debut FROM contrats 
        WHERE travailleur_id=%s AND statut='actif' ORDER BY date_debut DESC""", (travailleur_id,))
    contrats_actifs = cur2.fetchall()
    cur2.close(); conn2.close()
    return render_template('nouvelle_dimona.html', travailleur=travailleur, dossier=dossier, 
                           dossier_actif=dossier, contrats_actifs=contrats_actifs, **ctx)

# ── CALENDRIER PRESTATIONS ────────────────────────────────────────────
@app.route('/dimona/<int:dimona_id>/prestations')
@login_required
def calendrier_prestations(dimona_id):
    dimona = get_dimona(dimona_id)
    travailleur = get_travailleur(dimona['travailleur_id'])
    dossier = get_dossier(dimona['dossier_id'])
    ctx = get_context_base()
    ctx['tenant'] = get_tenant()

    annee = request.args.get('annee', date.today().year, type=int)
    mois = request.args.get('mois', date.today().month, type=int)

    conn = get_conn()
    from psycopg2.extras import RealDictCursor
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""SELECT date_prestation, code_journee, heures FROM prestations
        WHERE travailleur_id = %s AND EXTRACT(YEAR FROM date_prestation) = %s
        AND EXTRACT(MONTH FROM date_prestation) = %s""",
        (travailleur['id'], annee, mois))
    # Incapacites en cours ou touchant ce mois: le calendrier est complete jusqu'a la
    # fin du mois affiche (episode sans date de fin), puis relu
    incapacites_mois, incapacites_alertes, par_date_inc = [], [], None
    try:
        fin_mois_aff = date(annee, mois, calendar.monthrange(annee, mois)[1])
        ctx_inc = _contexte_incapacites(cur, travailleur['id'], fin_mois_aff)
        incapacites_mois = [v for v in ctx_inc['ventilation']
                            if v['debut'] <= fin_mois_aff and v['fin'] >= date(annee, mois, 1)]
        if any(v['en_cours'] for v in incapacites_mois):
            cur.execute("SELECT MAX(date_prestation) AS m FROM prestations WHERE travailleur_id = %s "
                        "AND code_journee IN ('MG','M2','MC','MM')", (travailleur['id'],))
            deja = cur.fetchone()['m']
            if not deja or deja < fin_mois_aff:
                _marquer_incapacites_au_calendrier(cur, travailleur['id'], dossier['id'], ctx_inc)
                conn.commit()
        incapacites_alertes = ctx_inc['alertes'] + [a for v in incapacites_mois for a in v['alertes']]
        par_date_inc = ctx_inc['par_date'] if ctx_inc['regime'] else None
    except Exception as ex_inc:
        conn.rollback()
        app.logger.warning(f"Incapacites (calendrier): {ex_inc}")
        incapacites_alertes = [f"Incapacités non lues ({ex_inc}) : lancez python3 migrate_charges.py si la table n'existe pas."]
    cur.execute("""SELECT date_prestation, code_journee, heures FROM prestations
        WHERE travailleur_id = %s AND EXTRACT(YEAR FROM date_prestation) = %s
        AND EXTRACT(MONTH FROM date_prestation) = %s""",
        (travailleur['id'], annee, mois))
    prests_dict = {row['date_prestation']: dict(row) for row in cur.fetchall()}
    cur.close(); conn.close()
    # Protection: jours codes maladie sans episode d'incapacite -> alerte + creation en un clic
    from salaire_garanti import jours_maladie_sans_episode
    maladie_sans_episode = [] if par_date_inc is None else jours_maladie_sans_episode(
        [(d_p, row['code_journee']) for d_p, row in prests_dict.items()], par_date_inc)

    jours_feries = get_jours_feries(annee)
    _, nb_jours = calendar.monthrange(annee, mois)
    premier_jour = date(annee, mois, 1)
    premier_jour_semaine = premier_jour.weekday()

    jours = []
    stats = {'jours_prestes': 0, 'heures_prestees': 0, 'jours_conge': 0,
             'jours_maladie': 0, 'jours_ferie': 0, 'jours_chomage': 0, 'jours_cnp': 0}

    date_debut_dimona = dimona['date_debut']
    date_fin_dimona = dimona['date_fin']
    # Heures/jour depuis le contrat réel du travailleur (pas le défaut CP du dossier)
    conn_c = get_conn(); cur_c = conn_c.cursor(cursor_factory=RealDictCursor)
    if dimona.get('contrat_id'):
        cur_c.execute("SELECT heures_jour FROM contrats WHERE id=%s", (dimona['contrat_id'],))
    else:
        cur_c.execute("""SELECT heures_jour FROM contrats WHERE travailleur_id=%s AND statut='actif'
            AND type_contrat=%s ORDER BY date_debut DESC LIMIT 1""",
            (dimona['travailleur_id'], dimona['type_dimona']))
    row_c = cur_c.fetchone()
    cur_c.close(); conn_c.close()
    heures_jour = float(row_c['heures_jour']) if row_c and row_c.get('heures_jour') else get_heures_semaine(dossier.get('cp_principale', 'CP 336')) / 5

    for j in range(1, nb_jours + 1):
        d = date(annee, mois, j)
        weekend = d.weekday() >= 5
        ferie = d in jours_feries
        hors_dimona = d < date_debut_dimona or (date_fin_dimona and d > date_fin_dimona)

        if hors_dimona:
            jours.append({'jour': j, 'date': str(d), 'hors_dimona': True, 'weekend': False,
                         'code': 'HD', 'heures': 0, 'couleur': '#eee', 'texte': '#bbb', 'ferie': False})
            continue
        if weekend and d not in prests_dict:
            jours.append({'jour': j, 'date': str(d), 'hors_dimona': False, 'weekend': True,
                         'code': 'WE', 'heures': 0, 'couleur': '#eceff1', 'texte': '#90a4ae', 'ferie': False})
            continue

        if d in prests_dict:
            code = prests_dict[d]['code_journee']
            heures = float(prests_dict[d]['heures'])
        elif ferie:
            code = 'F'; heures = 0
        else:
            code = 'P'; heures = round(heures_jour, 2)

        info = CODES_JOURNALIERS.get(code, CODES_JOURNALIERS['P'])
        if code == 'P': stats['jours_prestes'] += 1; stats['heures_prestees'] += heures
        elif code in ['CL','CE','VP']: stats['jours_conge'] += 1
        elif code in ['MA','AC','MG','M2','MC','MM']: stats['jours_maladie'] += 1
        elif code in ['F','FM']: stats['jours_ferie'] += 1
        elif code in ['CT','CI']: stats['jours_chomage'] += 1
        elif code == 'CNP': stats['jours_cnp'] += 1

        jours.append({'jour': j, 'date': str(d), 'hors_dimona': False, 'weekend': False,
                      'code': code, 'heures': heures,
                      'couleur': info['couleur'], 'texte': info['texte'], 'ferie': ferie})

    calcul = None
    contrats = get_contrats(travailleur_id=travailleur['id'])
    salaire_horaire = 0
    statut = travailleur.get('statut_travailleur', 'employe')
    if contrats:
        salaire_horaire = float(contrats[0]['salaire_horaire'] or 0)
    if stats['heures_prestees'] > 0 and salaire_horaire > 0:
        calcul = calcul_paie_complet(
            salaire_horaire=salaire_horaire,
            heures_prestees=stats['heures_prestees'],
            statut=statut,
            situation_familiale=travailleur.get('situation_familiale', 'isole'),
            personnes_charge=int(travailleur.get('personnes_charge', 0) or 0))

    mois_noms = ['','Janvier','Février','Mars','Avril','Mai','Juin',
                 'Juillet','Août','Septembre','Octobre','Novembre','Décembre']

    return render_template('calendrier_prestations.html',
                           dimona=dimona, travailleur=travailleur, dossier=dossier, dossier_actif=dossier,
                           jours=jours, stats=stats, calcul=calcul, annee=annee, mois=mois,
                           mois_nom=mois_noms[mois], premier_jour_semaine=premier_jour_semaine,
                           codes=CODES_JOURNALIERS, codes_json=jsonlib.dumps(CODES_JOURNALIERS),
                           heures_jour=round(heures_jour, 2),
                           incapacites_mois=incapacites_mois, incapacites_alertes=incapacites_alertes,
                           maladie_sans_episode=maladie_sans_episode, **ctx)

@app.route('/prestation/sauvegarder', methods=['POST'])
@login_required
def sauvegarder_prestation():
    data = request.get_json()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""INSERT INTO prestations (dimona_id, travailleur_id, dossier_id, date_prestation, code_journee, heures)
        VALUES (%s,%s,%s,%s,%s,%s)
        ON CONFLICT (travailleur_id, date_prestation)
        DO UPDATE SET code_journee = EXCLUDED.code_journee, heures = EXCLUDED.heures""",
        (data['dimona_id'], data['travailleur_id'], data['dossier_id'],
         data['date'], data['code'], data['heures']))
    conn.commit(); cur.close(); conn.close()
    return jsonlib.dumps({'ok': True, 'reload': True})

# ── CONTRATS ──────────────────────────────────────────────────────────
@app.route('/dossier/<int:dossier_id>/contrat/nouveau', methods=['GET', 'POST'])
@login_required
def nouveau_contrat_dossier(dossier_id):
    dossier = get_dossier(dossier_id)
    travailleurs = get_travailleurs(dossier_id)
    ctx = get_context_base()
    ctx['tenant'] = get_tenant()
    # Barèmes depuis BDD en priorité
    from psycopg2.extras import RealDictCursor
    conn_cp = get_conn(); cur_cp = conn_cp.cursor(cursor_factory=RealDictCursor)
    cur_cp.execute("SELECT * FROM baremes_cp ORDER BY cp_key, montant_mensuel")
    baremes_bdd = {}
    for r in cur_cp.fetchall():
        cp_k = r['cp_key']
        if cp_k not in baremes_bdd: baremes_bdd[cp_k] = {}
        baremes_bdd[cp_k][r['categorie']] = {'horaire': float(r['montant_horaire']), 'mensuel': float(r['montant_mensuel'])}
    cur_cp.close(); conn_cp.close()
    
    cp_data_merged = {}
    from baremes_experience import bareme_categories_en_vigueur
    for k, v in CP_DATABASE.items():
        officiel = {cat: {kk: vv for kk, vv in val.items() if kk in ['horaire','mensuel']}
                    for cat, val in v['baremes'].items() if isinstance(val, dict)}
        # Bareme officiel charge (salairesminimums.be): il prime sur la page « Barèmes CP »
        baremes = officiel if bareme_categories_en_vigueur(k, date.today()) else baremes_bdd.get(k, officiel)
        cp_data_merged[k] = {'meta': v['meta'], 'duree_travail': v['duree_travail'], 'baremes': baremes}
    cp_json = jsonlib.dumps(cp_data_merged)
    prefill_travailleur_id = request.args.get('travailleur_id', type=int)

    from regles_cp import cp_geree
    from contrat_etudiant import contexte_regles
    if request.method == 'POST':
        form = request.form
        if not cp_geree(form.get('cp_key', '')):
            # CP sans regles enregistrees: aucun contrat (le formulaire bloque deja le bouton)
            return redirect(url_for('nouveau_contrat_dossier', dossier_id=dossier_id, erreur='cp',
                                    travailleur_id=form.get('travailleur_id')))
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
            'salaire_unite': form.get('salaire_unite', 'horaire'),
            'salaire_mensuel': form.get('salaire_mensuel', '').replace(' €', ''),
            'lieu_travail': form.get('lieu_travail', dossier['adresse'] or ''),
            'lieu_signature': form.get('lieu_signature') or contexte_regles(dossier)['lieu_signature'],
            'date_signature': datetime.now().strftime('%d/%m/%Y'),
            'motif_cdd': form.get('motif_cdd', ''),
            'heures_jour': float(form.get('heures_jour', 7.6) or 7.6),
            'jours_semaine': int(form.get('jours_semaine', 5) or 5),
        }

        # Détecter langue du travailleur
        travailleur_obj = get_travailleur(travailleur_id)
        langue_doc = get_langue_document(dossier, travailleur_obj)
        if langue_doc == 'nl' and type_contrat in ('CDD',):
            filepath, filename = generer_contrat_cdd_nl(data)
        else:
            filepath, filename = (generer_contrat_cdi(data) if type_contrat == 'CDI' else generer_contrat_cdd(data))

        def pd(d):
            if not d: return None
            try: p = d.split('/'); return f"{p[2]}-{p[1]}-{p[0]}"
            except: return None

        create_contrat({'dossier_id': dossier_id, 'travailleur_id': travailleur_id,
            'type_contrat': type_contrat, 'cp_key': form['cp_key'],
            'fonction': form['fonction'], 'categorie': form.get('categorie'),
            'salaire_horaire': float(form.get('salaire_horaire', 0) or 0),
            'salaire_mensuel': float((form.get('salaire_mensuel') or '0').replace(' €','') or 0),
            'heures_semaine': get_heures_semaine(form['cp_key']),
            'heures_jour': float(form.get('heures_jour', 7.6) or 7.6),
            'jours_semaine': int(form.get('jours_semaine', 5) or 5),
            'horaire_journalier': form.get('horaire_journalier'),
            'lieu_travail': form.get('lieu_travail'),
            'date_debut': pd(form['date_debut']), 'date_fin': pd(form.get('date_fin')),
            'motif_cdd': form.get('motif_cdd'), 'temps_plein': form.get('temps_plein','1')=='1',
            'annees_experience': int(form['annees_experience']) if (form.get('annees_experience') or '').isdigit() else None,
            'pdf_path': os.path.join(OUTPUT_DIR, filename)})

        return redirect(url_for('fiche_travailleur', travailleur_id=travailleur_id, tab='contrats'))

    # Pré-remplir depuis contrat existant si travailleur sélectionné
    prefill_travailleur = None
    prefill_contrat = None
    if prefill_travailleur_id:
        prefill_travailleur = get_travailleur(prefill_travailleur_id)
        contrats_t = get_contrats(travailleur_id=prefill_travailleur_id)
        prefill_contrat = contrats_t[0] if contrats_t else None

    # JSON travailleurs pour JS
    import json as _json
    travailleurs_json = jsonlib.dumps([{
        'id': t['id'], 'prenom': t.get('prenom',''), 'nom': t.get('nom',''),
        'niss': t.get('niss',''), 'adresse': t.get('adresse',''),
        'iban': t.get('iban',''),
        'date_naissance': t['date_naissance'].strftime('%d/%m/%Y') if t.get('date_naissance') else '',
    } for t in travailleurs])

    return render_template('contrat_cdi_cdd.html', profil=dossier, profil_id=dossier_id,
                           dossier=dossier, dossier_actif=dossier,
                           travailleurs=travailleurs, cp_data=CP_DATABASE, cp_json=cp_json,
                           travailleurs_json=travailleurs_json,
                           prefill_travailleur_id=prefill_travailleur_id,
                           prefill_travailleur=prefill_travailleur,
                           prefill_contrat=prefill_contrat,
                           **contexte_regles(dossier), **ctx)

# ── DOWNLOAD ──────────────────────────────────────────────────────────
@app.route('/download/<filename>')
@login_required
def download(filename):
    filepath = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(filepath):
        return "Fichier introuvable — veuillez regénérer la fiche.", 404
    # Les PDF s'affichent dans le navigateur (lien ouvert dans un nouvel onglet par base.html)
    return send_file(filepath, as_attachment=not filename.lower().endswith('.pdf'))

# ── BASE CP ──────────────────────────────────────────────────────────
@app.route('/base-cp')
@login_required
def base_cp():
    from cp_data import CP_DATABASE
    from datetime import datetime
    from psycopg2.extras import RealDictCursor
    ctx = get_context_base(); ctx['tenant'] = get_tenant()
    
    # Lire barèmes depuis BDD
    conn = get_conn(); cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM baremes_cp ORDER BY cp_key, montant_mensuel")
    baremes_db = {}
    for r in cur.fetchall():
        cp = r['cp_key']
        if cp not in baremes_db: baremes_db[cp] = []
        baremes_db[cp].append(dict(r))
    cur.execute("SELECT cp_key, MAX(updated_at) as last FROM baremes_cp GROUP BY cp_key")
    last_updates = {r['cp_key']: r['last'].strftime('%d/%m/%Y') for r in cur.fetchall()}
    cur.close(); conn.close()
    
    # Enrichir avec cp_data
    cp_enrichi = {}
    for k, v in CP_DATABASE.items():
        cp_enrichi[k] = dict(v)
        cp_enrichi[k]['baremes_db'] = baremes_db.get(k, [])
        cp_enrichi[k]['last_update'] = last_updates.get(k, '—')
    
    last_update = datetime.now().strftime('%d/%m/%Y')
    return render_template('base_cp.html', cp_data=cp_enrichi, last_update=last_update, **ctx)

@app.route('/base-cp/modifier/<int:bareme_id>', methods=['POST'])
@login_required
def modifier_bareme(bareme_id):
    from psycopg2.extras import RealDictCursor
    conn = get_conn(); cur = conn.cursor()
    mensuel = float(request.form.get('montant_mensuel', 0))
    horaire = float(request.form.get('montant_horaire', 0))
    date_vigueur = request.form.get('date_vigueur')
    source = request.form.get('source', 'Manuel')
    cur.execute("""UPDATE baremes_cp SET montant_mensuel=%s, montant_horaire=%s, 
        date_vigueur=%s, source=%s, updated_at=NOW() WHERE id=%s""",
        (mensuel, horaire, date_vigueur, source, bareme_id))
    conn.commit(); cur.close(); conn.close()
    return redirect(url_for('base_cp'))

@app.route('/base-cp/ajouter', methods=['POST'])
@login_required
def ajouter_bareme():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""INSERT INTO baremes_cp (cp_key, categorie, montant_mensuel, montant_horaire, date_vigueur, source)
        VALUES (%s,%s,%s,%s,%s,%s)""",
        (request.form['cp_key'], request.form['categorie'],
         float(request.form.get('montant_mensuel',0)),
         float(request.form.get('montant_horaire',0)),
         request.form.get('date_vigueur'), request.form.get('source','Manuel')))
    conn.commit(); cur.close(); conn.close()
    return redirect(url_for('base_cp'))

@app.route('/base-cp/update')
@login_required
def base_cp_update():
    import subprocess
    subprocess.Popen(['/var/www/duxsalary/venv/bin/python3', '/var/www/duxsalary/check_baremes.py'])
    return redirect(url_for('base_cp'))

# ── ASSISTANT JURIDIQUE ───────────────────────────────────────────────
import anthropic as anthropic_client

@app.route('/assistant')
@login_required
def assistant():
    ctx = get_context_base()
    ctx['tenant'] = get_tenant()
    cps = [
        {'key': 'CP 336', 'secteur': 'Professions libérales'},
        {'key': 'CP 200', 'secteur': 'Auxiliaire employés / IT'},
        {'key': 'CP 302', 'secteur': 'Horeca'},
        {'key': 'CP 124', 'secteur': 'Construction'},
        {'key': 'CP 121', 'secteur': 'Nettoyage'},
        {'key': 'CP 140.03', 'secteur': 'Transport & logistique'},
    ]
    themes = ['Salaire minimum', 'Heures supplémentaires', 'Préavis de licenciement',
              'Calcul ONSS', 'Précompte professionnel', 'Congés annuels',
              'Indemnités transport', 'CDD autorisés', 'Dimona obligations', 'DmfA échéances']
    return render_template('assistant.html', cps=cps, themes=themes, dossier_actif=None, **ctx)

@app.route('/assistant/question', methods=['POST'])
@login_required
def assistant_question():
    data = request.get_json()
    question = data.get('question', '').strip()
    cp_key = data.get('cp', '')
    if not question:
        return jsonlib.dumps({'reponse': 'Veuillez poser une question.'})
    cp_context = ''
    if cp_key and cp_key in CP_DATABASE:
        cp = CP_DATABASE[cp_key]
        cp_context = f"Commission paritaire : {cp_key} — {cp['meta']['nom']} — {cp['meta']['type_travailleur']} — {cp['duree_travail']['heures_semaine']}h/semaine"
    system_prompt = f"""Tu es un expert en droit social belge pour DuxSalary, secrétariat social digital.
Taux ONSS 2026 : ouvrier 13,07% + ~27% patronal, employé 13,07% + ~25%, étudiant 2,71% + 5,42%.
Statut unique depuis loi 26/12/2013. Réponds en français, de manière précise et pratique. {cp_context}"""
    try:
        client = anthropic_client.Anthropic()
        message = client.messages.create(model="claude-sonnet-4-6", max_tokens=1000,
            system=system_prompt, messages=[{"role": "user", "content": question}])
        reponse = message.content[0].text
    except Exception as e:
        reponse = f"Erreur : {str(e)}"
    return jsonlib.dumps({'reponse': reponse})

if __name__ == '__main__':
    init_db()
    app.run(debug=False, host='0.0.0.0')

# ── GESTION DES ÉCHÉANCES v2 ──────────────────────────────────────────

def get_echeances_dossier(dossier_id):
    """Génère les échéances dynamiquement + récupère DmfA/Belcotax depuis la BDD."""
    from psycopg2.extras import RealDictCursor
    today = date.today()
    annee = today.year
    mois = today.month
    dossier = get_dossier(dossier_id)
    date_activation = dossier.get('date_activation_rsz')
    echeances = []

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # ── 1. DmfA et Belcotax depuis la BDD (seules choses stockées) ──
    # Générer les DmfA si pas encore en base
    def trim_actif(debut_mois, an=None):
        if not date_activation: return True
        if an is None: an = annee
        import calendar as cal
        last = cal.monthrange(an, debut_mois + 2)[1]
        return date_activation <= date(an, debut_mois + 2, last)

    trimestres = [
        ('Q1', 1, date(annee, 4, 30), 'warn'),
        ('Q2', 4, date(annee, 7, 31), 'warn'),
        ('Q3', 7, date(annee, 10, 31), 'urgent' if mois in [9,10] else 'warn'),
        ('Q4', 10, date(annee+1, 1, 31), 'warn'),
    ]
    for trim_code, m_debut, d_ech, niv in trimestres:
        if not trim_actif(m_debut): continue
        cur.execute("SELECT id, statut, date_realisation, document_nom FROM echeances WHERE dossier_id=%s AND type_echeance='dmfa' AND trimestre=%s AND annee=%s",
                    (dossier_id, trim_code, annee))
        row = cur.fetchone()
        if not row:
            cur.execute("""INSERT INTO echeances (dossier_id, type_echeance, description, date_echeance, trimestre, annee, statut, niveau)
                VALUES (%s,'dmfa',%s,%s,%s,%s,'en_attente',%s) ON CONFLICT ON CONSTRAINT echeances_unique DO NOTHING RETURNING id""",
                (dossier_id, f"DmfA {trim_code}/{annee} — socialsecurity.be", d_ech, trim_code, annee, niv))
            conn.commit()
            cur.execute("SELECT id, statut, date_realisation, document_nom FROM echeances WHERE dossier_id=%s AND type_echeance='dmfa' AND trimestre=%s AND annee=%s",
                        (dossier_id, trim_code, annee))
            row = cur.fetchone()
        if row:
            echeances.append({
                'id': row['id'], 'type_echeance': 'dmfa',
                'description': f"DmfA {trim_code}/{annee} — à introduire sur socialsecurity.be",
                'date_echeance': d_ech, 'statut': row['statut'],
                'niveau': niv, 'date_realisation': row['date_realisation'],
                'document_nom': row['document_nom'],
            })

    # ── 2. Échéances dynamiques (jamais stockées en base) ──

    # ONSS mensuel — afficher les 2 derniers mois non payés
    from datetime import timedelta
    MOIS_FR = ['','Janvier','Fevrier','Mars','Avril','Mai','Juin','Juillet','Aout','Septembre','Octobre','Novembre','Decembre']
    for delta_mois in [1, 2]:
        mois_onss = mois - delta_mois
        annee_onss = annee
        if mois_onss <= 0:
            mois_onss += 12
            annee_onss -= 1
        # Date limite : 5 du mois suivant
        mois_paiement = mois_onss + 1 if mois_onss < 12 else 1
        annee_paiement = annee_onss if mois_onss < 12 else annee_onss + 1
        date_onss = date(annee_paiement, mois_paiement, 5)
        # Afficher seulement si la date limite est dans le futur ou récente (30 jours)
        if (today - date_onss).days <= 30:
            # Stocker en BDD si pas encore existant
            cur.execute("SELECT id FROM echeances WHERE dossier_id=%s AND type_echeance='onss_mensuel' AND date_echeance=%s",
                        (dossier_id, date_onss))
            existing = cur.fetchone()
            if not existing:
                cur.execute("""INSERT INTO echeances (dossier_id, type_echeance, description, date_echeance, trimestre, annee, statut, niveau)
                    VALUES (%s,'onss_mensuel',%s,%s,NULL,%s,'en_attente',%s) RETURNING id""",
                    (dossier_id, f"Paiement ONSS {MOIS_FR[mois_onss]} {annee_onss} — avant le {date_onss.strftime('%d/%m/%Y')}",
                     date_onss, annee_onss, 'urgent' if today > date_onss else 'warn'))
                conn.commit()
                existing = cur.fetchone()
            if existing:
                cur.execute("SELECT * FROM echeances WHERE id=%s", (existing['id'],))
                ech = dict(cur.fetchone())
                echeances.append(ech)

    # CDD/STU arrivant à échéance (1 seul par contrat actif)
    cur.execute("""
        SELECT DISTINCT ON (c.id) t.prenom, t.nom, c.date_fin, c.id as contrat_id,
               c.type_contrat
        FROM contrats c JOIN travailleurs t ON t.id = c.travailleur_id
        WHERE c.dossier_id = %s AND c.type_contrat IN ('CDD','STU')
        AND c.date_fin IS NOT NULL
        AND c.date_fin BETWEEN CURRENT_DATE - INTERVAL '60 days' AND CURRENT_DATE + INTERVAL '45 days'
        AND c.statut = 'actif'
    """, (dossier_id,))
    for row in cur.fetchall():
        label = 'Contrat étudiant' if row['type_contrat'] == 'STU' else 'Contrat CDD'
        desc_cdd = f"{label} {row['prenom']} {row['nom']} — échéance {row['date_fin'].strftime('%d/%m/%Y')}"
        type_ech = f"cdd_{row['contrat_id']}"
        cur.execute("SELECT id, statut, date_realisation, document_nom FROM echeances WHERE dossier_id=%s AND type_echeance=%s AND annee=%s",
                    (dossier_id, type_ech, annee))
        existing_cdd = cur.fetchone()
        if not existing_cdd:
            cur.execute("""INSERT INTO echeances (dossier_id, type_echeance, description, date_echeance, trimestre, annee, statut, niveau)
                VALUES (%s,%s,%s,%s,NULL,%s,'en_attente','urgent') RETURNING id""",
                (dossier_id, type_ech, desc_cdd, row['date_fin'], annee))
            conn.commit()
            existing_cdd = cur.fetchone()
        if existing_cdd:
            cur.execute("SELECT * FROM echeances WHERE id=%s", (existing_cdd['id'],))
            echeances.append(dict(cur.fetchone()))

    cur.close(); conn.close()

    # Trier par date
    echeances.sort(key=lambda x: (x['statut'] != 'en_attente', x['date_echeance'] or date(2099,1,1)))
    return echeances


def generer_pdf_etudiant(data, filepath):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle, KeepTogether
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
    from datetime import datetime

    NAVY  = couleur('primaire')
    DARK  = colors.HexColor('#1a1a1a')
    MUTED = colors.HexColor('#555555')

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    try:
        pdfmetrics.registerFont(TTFont('DVSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
        pdfmetrics.registerFont(TTFont('DVSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
        fn, fnb = 'DVSans', 'DVSans-Bold'
    except:
        fn, fnb = 'Helvetica', 'Helvetica-Bold'
    sN  = ParagraphStyle('N', fontName=fn,  fontSize=10, leading=15, textColor=DARK)
    sB  = ParagraphStyle('B', fontName=fnb, fontSize=10, leading=15, textColor=DARK)
    sT  = ParagraphStyle('T', fontName=fnb, fontSize=15, leading=22, textColor=NAVY, alignment=TA_CENTER)
    sS  = ParagraphStyle('S', fontName=fnb, fontSize=11, leading=16, textColor=NAVY)
    sJ  = ParagraphStyle('J', fontName=fn,  fontSize=10, leading=15, alignment=TA_JUSTIFY, textColor=DARK)
    sC  = ParagraphStyle('C', fontName=fn,  fontSize=9,  leading=13, alignment=TA_CENTER, textColor=MUTED)
    sMu = ParagraphStyle('M', fontName=fn,  fontSize=9,  leading=13, textColor=MUTED)

    doc = SimpleDocTemplate(filepath, pagesize=A4,
        topMargin=2*cm, bottomMargin=2*cm,
        leftMargin=2.5*cm, rightMargin=2.5*cm)

    # Calculs
    heures_j  = float(data.get('heures_jour', 7.6))
    nb_jours  = int(data.get('nb_jours', 0))
    sal_h     = float(data.get('salaire_horaire', 0))
    # Taux repos payés CP 140.03 niveau 1
    sal_h_rep = round(sal_h * (14.5425 / 14.9255), 4) if 'CP 140.03' in data.get('cp_key','') else sal_h
    heures_tot= round(heures_j * nb_jours, 2)
    brut      = round(sal_h * heures_tot, 2)
    onss      = round(brut * 0.0271, 2)
    net       = round(brut - onss, 2)
    cp_key    = data.get('cp_key', '')

    e = []

    # ── EN-TÊTE ──
    e.append(Spacer(1, 0.5*cm))  # espace logo
    e.append(HRFlowable(width='100%', thickness=2, color=NAVY))
    e.append(Spacer(1, 0.3*cm))
    e.append(Paragraph("CONTRAT D'OCCUPATION D'ETUDIANT", sT))
    if nb_jours == 1:
        e.append(Paragraph("Dagcontract — Contrat journalier", sC))
    else:
        e.append(Paragraph(f"Contrat a duree determinee — {nb_jours} jours ouvrables", sC))
    e.append(Spacer(1, 0.2*cm))
    e.append(Paragraph(f"{cp_key} — Fonction : {data.get('fonction','')}", sC))
    e.append(Spacer(1, 0.3*cm))
    e.append(HRFlowable(width='100%', thickness=0.5, color=MUTED))
    e.append(Spacer(1, 0.5*cm))

    # ── PARTIES ──
    e.append(Paragraph("ENTRE LES SOUSSIGNES :", sS))
    e.append(Spacer(1, 0.3*cm))
    e.append(Paragraph("<b>L'EMPLOYEUR :</b>", sB))
    e.append(Paragraph(
        f"{data['nom_societe']}, dont le siege social est etabli a {data.get('adresse_societe','')}, "
        f"inscrit a la BCE sous le numero {data.get('bce_societe','')}, "
        f"identifie a l'ONSS sous le numero {data.get('rsz_societe','')}, "
        f"represente par {data.get('representant','')}, ci-apres designe « l'Employeur »,", sJ))
    e.append(Spacer(1, 0.3*cm))
    e.append(Paragraph("<b>ET L'ETUDIANT(E) :</b>", sB))
    for label, val in [
        ("Nom et prenom :", f"<b>{data.get('nom_etudiant','')}</b>"),
        ("Adresse :", data.get('adresse_etudiant', '')),
        ("Date de naissance :", data.get('ddn_etudiant', '')),
        ("N° NISS :", data.get('niss_etudiant', '')),
        ("Etablissement d'enseignement :", data.get('ecole_etudiant', '') or 'A completer'),
    ]:
        e.append(Paragraph(f"{label} {val}", sN))
    e.append(Paragraph("ci-apres designe « l'Etudiant(e) »,", sN))
    e.append(Spacer(1, 0.3*cm))
    e.append(Paragraph("Il a ete convenu ce qui suit :", sN))
    e.append(Spacer(1, 0.4*cm))
    e.append(HRFlowable(width='100%', thickness=0.3, color=colors.HexColor('#DDDDDD')))
    e.append(Spacer(1, 0.3*cm))

    def art(num, titre, texte):
        block = [
            Paragraph(f"<b>Article {num} – {titre}</b>", sS),
            Spacer(1, 0.1*cm),
            Paragraph(texte, sJ),
            Spacer(1, 0.3*cm),
        ]
        return KeepTogether(block)

    # ── ARTICLES ──
    e.append(art("1", "Nature et duree du contrat",
        f"Le present contrat est un contrat d'occupation d'etudiant conclu conformement "
        f"au Titre VII (articles 120 a 130bis) de la loi du 3 juillet 1978 relative aux contrats de travail. "
        f"Il est conclu pour la periode du <b>{data.get('date_debut','')}</b> "
        f"au <b>{data.get('date_fin','')}</b> inclus, soit <b>{nb_jours} jour(s) ouvrable(s)</b>. "
        f"Le contrat prend fin de plein droit a l'echeance du terme, sans preavis ni indemnite."))

    e.append(art("2", "Statut etudiant et contingent Student@Work",
        f"L'Etudiant(e) declare etre principalement occupe(e) a suivre des etudes a temps plein "
        f"et remplir les conditions legales pour etre employe(e) comme etudiant(e). "
        f"L'Etudiant(e) s'engage a respecter le contingent annuel de <b>650 heures</b> autorise "
        f"a cotisations ONSS reduites (2,71% personnel + 5,42% patronal) conformement a "
        f"l'article 17bis de l'arrete royal du 28 novembre 1969. Au-dela des 650 heures, "
        f"les cotisations ONSS ordinaires sont dues. L'Etudiant(e) peut consulter son quota "
        f"disponible sur <b>studentatwork.be</b>."))

    e.append(art("3", "Fonction et classification",
        f"L'Etudiant(e) est engage(e) en qualite de <b>{data.get('fonction','')}</b>. "
        f"Ce contrat est regi par la <b>{cp_key}</b> et l'ensemble de ses conventions collectives de travail."))

    e.append(art("4", "Lieu de travail",
        f"Lieu de travail principal : <b>{data.get('lieu_travail','')}</b>. "
        f"L'Employeur se reserve le droit de modifier le lieu de travail en fonction "
        f"des necessites operationnelles, dans les limites fixees par la loi."))

    e.append(art("5", "Duree du travail et horaire",
        f"L'Etudiant(e) est occupe(e) a raison de <b>{heures_j}h par jour</b> "
        f"({data.get('horaire_journalier','')}) soit <b>{heures_tot}h au total</b> pour la duree du contrat. "
        f"Les dispositions legales en matiere de duree du travail, de temps de repos et de pauses "
        f"restent pleinement applicables."))

    e.append(art("6", "Remuneration",
        f"L'Etudiant(e) percoit un salaire brut de <b>{sal_h} EUR de l'heure</b> "
        f"pour <b>{heures_j}h par jour</b>, "
        f"conformement aux baremes de la {cp_key}. "
        f"Cotisation ONSS etudiant : 2,71% a charge de l'etudiant(e) + 5,42% patronal. "
        f"Le salaire est paye par virement bancaire conformement a la loi du 12 avril 1965 "
        f"concernant la protection de la remuneration des travailleurs."))

    e.append(art("7", "Heures supplementaires et majorations",
        f"Les prestations au-dela de la duree normale de travail donnent droit a : "
        f"un supplement de <b>50%</b> pour les heures supplementaires en semaine ; "
        f"un supplement de <b>100%</b> pour les prestations le dimanche et les jours feries legaux, "
        f"conformement a la legislation en vigueur et aux CCT de la {cp_key}."))

    e.append(art("8", "Pas de periode d'essai",
        "Les parties conviennent expressement qu'aucune periode d'essai n'est applicable "
        "au present contrat d'etudiant journalier."))

    e.append(art("9", "Obligations de l'Etudiant(e)",
        "L'Etudiant(e) s'engage a : executer ses taches avec soin et diligence ; "
        "respecter le reglement de travail et les instructions de l'Employeur ; "
        "maintenir la confidentialite sur les informations de l'entreprise ; "
        "signaler immediatement tout incident, accident ou dommage a l'Employeur. "
        "Les amendes et sanctions administratives resultant de fautes personnelles de l'Etudiant(e) "
        "sont a sa charge."))

    e.append(art("10", "Assurance accidents du travail",
        f"L'Employeur souscrit la police d'assurance accidents du travail obligatoire "
        f"conformement a la loi du 10 avril 1971. "
        f"L'Etudiant(e) respecte strictement les regles de securite et de bien-etre au travail."))

    e.append(art("11", "Droit applicable",
        f"Le present contrat est regi par le droit belge, la loi du 3 juillet 1978 "
        f"relative aux contrats de travail, le reglement de travail et les conventions "
        f"collectives de la {cp_key}. Les tribunaux du travail belges sont seuls competents."))

    e.append(art("12", "Dispositions finales",
        f"Le present contrat est etabli en deux exemplaires originaux, dont un remis a chaque partie. "
        f"Fait a <b>{data.get('lieu_signature','Bruxelles')}</b>, le <b>{datetime.now().strftime('%d/%m/%Y')}</b>."))

    # ── SIGNATURES ──
    e.append(Spacer(1, 0.5*cm))
    sig = Table([[
        Paragraph(f"<b>L'EMPLOYEUR</b><br/>{data['nom_societe']}<br/>{data.get('representant','')}<br/><br/><br/>_______________________<br/>Signature et cachet",
                  ParagraphStyle('', fontName='Helvetica', fontSize=10, leading=15, alignment=TA_LEFT)),
        Paragraph(f"<b>L'ETUDIANT(E)</b><br/>{data.get('nom_etudiant','')}<br/><br/><br/><br/>_______________________<br/>Signature : Lu et approuve",
                  ParagraphStyle('', fontName='Helvetica', fontSize=10, leading=15, alignment=TA_LEFT)),
    ]], colWidths=[8.5*cm, 8.5*cm])
    sig.setStyle(TableStyle([
        ('VALIGN', (0,0),(-1,-1), 'TOP'),
        ('TOPPADDING', (0,0),(-1,-1), 8),
        ('LEFTPADDING', (0,0),(-1,-1), 0),
        ('LINEAFTER', (0,0),(0,0), 0.5, colors.HexColor('#CCCCCC')),
    ]))
    e.append(sig)
    e.append(Spacer(1, 0.4*cm))
    e.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#CCCCCC')))
    e.append(Spacer(1, 0.2*cm))
    e.append(Paragraph(
        "Document etabli conformement a la loi du 3 juillet 1978 et au Titre VII relatif aux contrats d'occupation d'etudiants.",
        sMu))

    doc.build(e, **pdf_decor())


@app.route('/contrat/etudiant/nouveau', methods=['GET', 'POST'])
@login_required
def nouveau_contrat_etudiant():
    """Genere UNIQUEMENT le contrat d'occupation d'etudiant (PDF + enregistrement).
    Aucune fiche de paie ici: elles passent par le calendrier et « Calculer la paie »."""
    from occupation import commune_de_l_adresse
    dossier_id = request.args.get('dossier_id', type=int) or request.form.get('dossier_id', type=int)
    travailleur_id = request.args.get('travailleur_id', type=int) or request.form.get('travailleur_id', type=int)
    dossier = get_dossier(dossier_id)
    travailleur = get_travailleur(travailleur_id)
    ctx = get_context_base()
    ctx['tenant'] = get_tenant()

    if request.method == 'POST':
        form = request.form
        cp_key = form.get('commission_paritaire_key', dossier.get('cp_principale', 'CP 140.03'))
        from regles_cp import cp_geree
        if not cp_geree(cp_key):
            # CP sans regles enregistrees: aucun contrat (le formulaire bloque deja le bouton)
            return redirect(url_for('nouveau_contrat_etudiant', dossier_id=dossier_id,
                                    travailleur_id=travailleur_id, erreur='cp'))

        def pd(d):
            if not d: return None
            try: p = d.split('/'); return f"{p[2]}-{p[1]}-{p[0]}"
            except: return None

        # Générer PDF
        filename = f"contrat_etudiant_{travailleur['prenom']}_{travailleur['nom']}_{form.get('date_debut','').replace('/','')}.pdf"
        filepath = os.path.join(OUTPUT_DIR, filename)

        data_pdf = {
            'nom_societe': dossier['nom'],
            'adresse_societe': dossier.get('adresse', ''),
            'bce_societe': dossier.get('bce', ''),
            'rsz_societe': dossier.get('rsz', ''),
            'representant': dossier.get('representant', ''),
            'nom_etudiant': f"{travailleur['prenom']} {travailleur['nom']}",
            'adresse_etudiant': travailleur.get('adresse', ''),
            'ddn_etudiant': travailleur['date_naissance'].strftime('%d/%m/%Y') if travailleur.get('date_naissance') else '',
            'niss_etudiant': travailleur.get('niss', ''),
            'ecole_etudiant': form.get('ecole_etudiant', ''),
            'date_debut': form.get('date_debut', ''),
            'date_fin': form.get('date_fin', ''),
            'nb_jours': form.get('nb_jours', 0),
            'heures_jour': form.get('heures_jour', 7.6),
            'horaire_journalier': form.get('horaire_journalier', ''),
            'salaire_horaire': form.get('salaire_horaire', 0),
            'fonction': form.get('fonction', ''),
            'lieu_travail': form.get('lieu_travail', dossier.get('adresse', '')),
            'lieu_signature': form.get('lieu_signature') or commune_de_l_adresse(dossier.get('adresse')),
            'cp_key': cp_key,
        }

        try:
            generer_pdf_etudiant(data_pdf, filepath)
            pdf_path = filepath
        except Exception as ex:
            pdf_path = None
            print(f"Erreur PDF étudiant: {ex}")

        create_contrat({
            'dossier_id': dossier_id,
            'travailleur_id': travailleur_id,
            'type_contrat': 'STU',
            'cp_key': cp_key,
            'fonction': form.get('fonction', ''),
            'categorie': 'etudiant',
            'salaire_horaire': float(form.get('salaire_horaire', 0) or 0),
            'salaire_mensuel': 0,
            'heures_semaine': get_heures_semaine(cp_key),
            'horaire_journalier': form.get('horaire_journalier', ''),
            'lieu_travail': form.get('lieu_travail', dossier.get('adresse', '')),
            'date_debut': pd(form.get('date_debut', '')),
            'date_fin': pd(form.get('date_fin', '')),
            'motif_cdd': 'Contrat etudiant',
            'temps_plein': True,
            'pdf_path': pdf_path,
        })

        return redirect(url_for('fiche_travailleur', travailleur_id=travailleur_id, tab='contrats'))

    # Formulaire: regles de la CP, bareme etudiant, contingent annuel, lieu de signature
    from psycopg2.extras import RealDictCursor
    from contrat_etudiant import contexte_formulaire
    conn = get_conn(); cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM baremes_cp ORDER BY cp_key, montant_mensuel")
    baremes_db = {}
    for r in cur.fetchall():
        baremes_db.setdefault(r['cp_key'], []).append(dict(r))
    # Heures etudiant deja prestees cette annee civile chez cet employeur (calendrier des prestations)
    cur.execute("""SELECT COALESCE(SUM(p.heures), 0) AS heures
                   FROM prestations p JOIN dimona d ON d.id = p.dimona_id
                   WHERE p.travailleur_id = %s AND d.dossier_id = %s AND d.type_dimona = 'STU'
                     AND p.code_journee IN ('P', 'S', 'HS', 'PP')
                     AND EXTRACT(YEAR FROM p.date_prestation) = %s""",
                (travailleur_id, dossier_id, date.today().year))
    heures_deja = float(cur.fetchone()['heures'] or 0)
    cur.close(); conn.close()
    # Age de l'etudiant: certaines CP ont un bareme des etudiants par age
    ddn, auj = travailleur.get('date_naissance'), date.today()
    age_etudiant = (auj.year - ddn.year - ((auj.month, auj.day) < (ddn.month, ddn.day))) if ddn else None

    return render_template('contrat_etudiant.html',
                           dossier=dossier, travailleur=travailleur,
                           dossier_actif=dossier,
                           cp_data=CP_DATABASE,
                           **contexte_formulaire(dossier, heures_deja, date.today(), baremes_db, age=age_etudiant),
                           **ctx)


@app.route('/dimona/<int:dimona_id>/supprimer', methods=['POST'])
@login_required
def supprimer_dimona(dimona_id):
    dimona = get_dimona(dimona_id)
    travailleur_id = dimona['travailleur_id']
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM prestations WHERE dimona_id = %s", (dimona_id,))
    cur.execute("DELETE FROM dimona WHERE id = %s", (dimona_id,))
    conn.commit(); cur.close(); conn.close()
    return redirect(url_for('dimona_list', travailleur_id=travailleur_id))

# ── SYSTÈME MULTI-TENANT ──────────────────────────────────────────────

def get_tenant():
    """Récupère le tenant depuis le sous-domaine de la requête."""
    from psycopg2.extras import RealDictCursor
    host = request.host or ''
    subdomain = 'duxsalary'
    
    if 'nexsocial' in host:
        parts = host.split('.')
        idx = next((i for i, p in enumerate(parts) if 'nexsocial' in p), None)
        if idx and idx > 0:
            subdomain = parts[idx-1]
    
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM tenants WHERE subdomain = %s AND actif = TRUE", (subdomain,))
    tenant = cur.fetchone()
    cur.close(); conn.close()
    
    if tenant:
        return dict(tenant)
    
    return {
        'subdomain': 'duxsalary',
        'nom': 'DuxSalary',
        'couleur_primaire': '#1F4E79',
        'couleur_accent': '#4fc3f7',
        'logo_text': 'DuxSalary',
    }

def get_context_base_tenant():
    """Context de base avec tenant."""
    ctx = get_context_base()
    ctx['tenant'] = get_tenant()
    ctx['tenant'] = get_tenant()
    return ctx

def get_langue_document(dossier, travailleur=None):
    region = (dossier.get('region_linguistique') or 'bruxelles_fr')
    if region == 'flandre':
        return 'nl'
    elif region in ('bruxelles_nl',):
        return (travailleur or {}).get('langue', 'fr') or 'fr'
    return 'fr'

# ── PORTAIL ADMIN NEXSOCIAL ───────────────────────────────────────────

NEXSOCIAL_ADMIN_EMAIL = "leo@nexsocial.be"
NEXSOCIAL_ADMIN_PASSWORD_HASH = None  # défini au démarrage

def get_nexsocial_password_hash(password):
    import hashlib
    return hashlib.sha256(f"nexsocial2026{password}".encode()).hexdigest()

def is_nexsocial_admin():
    return session.get('nexsocial_admin') == True

def nexsocial_admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_nexsocial_admin():
            return redirect('/nexsocial/login')
        return f(*args, **kwargs)
    return decorated

@app.route('/nexsocial/login', methods=['GET', 'POST'])
def nexsocial_login():
    # Cette route fonctionne seulement sur app.nexsocial.be
    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password', '')
        pw_hash = get_nexsocial_password_hash(password)
        
        conn = get_conn()
        from psycopg2.extras import RealDictCursor
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM nexsocial_admins WHERE email = %s AND password_hash = %s AND actif = TRUE",
                    (email, pw_hash))
        admin = cur.fetchone()
        cur.close(); conn.close()
        
        if admin:
            session['nexsocial_admin'] = True
            session['nexsocial_admin_nom'] = admin['nom']
            return redirect('/nexsocial/dashboard')
        error = "Email ou mot de passe incorrect."
    
    return render_template('nexsocial_login.html', error=error)

@app.route('/nexsocial/logout')
def nexsocial_logout():
    session.pop('nexsocial_admin', None)
    session.pop('nexsocial_admin_nom', None)
    return redirect('/nexsocial/login')

@app.route('/nexsocial/dashboard')
@nexsocial_admin_required
def nexsocial_dashboard():
    conn = get_conn()
    from psycopg2.extras import RealDictCursor
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM tenants ORDER BY created_at DESC")
    clients = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return render_template('nexsocial_dashboard.html', clients=clients,
                           admin_nom=session.get('nexsocial_admin_nom', 'Admin'))

@app.route('/nexsocial/client/nouveau', methods=['GET', 'POST'])
@nexsocial_admin_required
def nexsocial_nouveau_client():
    if request.method == 'POST':
        form = request.form
        import hashlib
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO tenants (subdomain, nom, couleur_primaire, couleur_accent, 
                                logo_text, email_admin, plan, nb_dossiers_max)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            form['subdomain'].lower().strip(),
            form['nom'],
            form.get('couleur_primaire', '#1F4E79'),
            form.get('couleur_accent', '#4fc3f7'),
            form['logo_text'],
            form.get('email_admin', ''),
            form.get('plan', 'standard'),
            int(form.get('nb_dossiers_max', 50))
        ))
        conn.commit(); cur.close(); conn.close()
        return redirect('/nexsocial/dashboard')
    return render_template('nexsocial_nouveau_client.html',
                           admin_nom=session.get('nexsocial_admin_nom', 'Admin'))

@app.route('/nexsocial/client/<int:client_id>/toggle', methods=['POST'])
@nexsocial_admin_required
def nexsocial_toggle_client(client_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE tenants SET actif = NOT actif WHERE id = %s", (client_id,))
    conn.commit(); cur.close(); conn.close()
    return redirect('/nexsocial/dashboard')

@app.route('/echeance/<int:echeance_id>/valider', methods=['POST'])
@login_required
def valider_echeance(echeance_id):
    fichier = request.files.get('document')
    date_real = request.form.get('date_realisation')
    note = request.form.get('note', '')
    if not fichier or not fichier.filename:
        return jsonlib.dumps({'ok': False, 'error': 'Veuillez joindre un document.'})
    filename = werkzeug.utils.secure_filename(fichier.filename)
    unique_name = f"echeance_{echeance_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
    filepath = os.path.join(UPLOAD_DIR, unique_name)
    fichier.save(filepath)
    conn = get_conn()
    from psycopg2.extras import RealDictCursor
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM echeances WHERE id = %s", (echeance_id,))
    ech = cur.fetchone()
    if not ech:
        cur.close(); conn.close()
        return jsonlib.dumps({'ok': False, 'error': 'Échéance introuvable.'})
    cur.execute("""UPDATE echeances SET statut='fait', date_realisation=%s,
        document_path=%s, document_nom=%s, note=%s, updated_at=NOW() WHERE id=%s""",
        (date_real or date.today(), filepath, filename, note, echeance_id))
    cur.execute("""INSERT INTO documents (dossier_id, travailleur_id, nom, type_document, filename, filepath, taille, uploaded_by, niveau)
        VALUES (%s, NULL, %s, 'echeance', %s, %s, %s, %s, 'dossier')""",
        (ech['dossier_id'], f"Preuve — {ech['description'][:50]}",
         unique_name, filepath, os.path.getsize(filepath), session['user_id']))
    conn.commit(); cur.close(); conn.close()
    from datetime import datetime as dt
    date_fmt = dt.strptime(date_real, '%Y-%m-%d').strftime('%d/%m/%Y') if date_real else date.today().strftime('%d/%m/%Y')
    return jsonlib.dumps({'ok': True, 'description': ech['description'], 'date': date_fmt, 'document_nom': filename})

@app.route('/echeance/<int:echeance_id>/document')
@login_required
def download_echeance_document(echeance_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT document_path, document_nom FROM echeances WHERE id = %s", (echeance_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if row and row[0] and os.path.exists(row[0]):
        return send_file(row[0], as_attachment=True, download_name=row[1])
    return "Document introuvable", 404

# ── INCAPACITES DE TRAVAIL (maladie / accident de droit commun) ───────
# Un enregistrement par episode (table incapacites, migrate_charges.py). Les
# tranches de salaire garanti de chaque jour sont calculees par salaire_garanti.py
# et posees dans le calendrier des prestations (codes MG, M2, MC, MM).

def _contexte_incapacites(cur, travailleur_id, jusqu_au, contrat=None):
    """Episodes du travailleur ventiles par tranche jusqu'a `jusqu_au`.
    Le regime (ouvrier / employe / employe engage pour moins de trois mois) est
    celui du contrat transmis, a defaut du contrat qui couvre `jusqu_au`, a
    defaut du plus recent."""
    from salaire_garanti import contexte_incapacites
    from occupation import contrat_de_la_periode
    from moteur_paie import CP_INDEMNITES
    cur.execute('SELECT * FROM contrats WHERE travailleur_id = %s', (travailleur_id,))
    tous = [dict(c) for c in cur.fetchall()]
    cur.execute('SELECT * FROM incapacites WHERE travailleur_id = %s ORDER BY date_debut', (travailleur_id,))
    episodes = [dict(e) for e in cur.fetchall()]
    if contrat is None:
        contrat = (contrat_de_la_periode(tous, jusqu_au, jusqu_au)
                   or (max(tous, key=lambda c: c['date_debut']) if tous else None))
    ouvrier = bool(contrat) and CP_INDEMNITES.get(contrat['cp_key'], {}).get('type_travailleur', 'ouvrier') == 'ouvrier'
    return contexte_incapacites(episodes, tous, contrat, ouvrier, jusqu_au)


def _marquer_incapacites_au_calendrier(cur, travailleur_id, dossier_id, ctx_inc):
    """Pose dans le calendrier le code de tranche de chaque jour d'incapacite prevu
    a l'horaire. Ne touche qu'aux jours vides, prestes (P), ou deja marques maladie:
    un conge, un ferie ou un jour retire a la main sont laisses tels quels.
    Retourne les messages a afficher."""
    from salaire_garanti import jours_a_marquer, CODES_INCAPACITE
    from occupation import contrat_de_la_periode
    messages = []
    cur.execute('SELECT id, date_debut, date_fin FROM dimona WHERE travailleur_id = %s ORDER BY date_debut', (travailleur_id,))
    dimonas = [dict(d) for d in cur.fetchall()]
    voulus = {}
    for v in ctx_inc['ventilation']:
        annees = {j['date'].year for j in v['jours']}
        feries = set()
        for a in annees:
            feries |= set(get_jours_feries(a))
        c_ep = contrat_de_la_periode(ctx_inc['contrats'], v['debut'], v['fin']) or ctx_inc['contrat'] or {}
        jours_sem = int(c_ep.get('jours_semaine') or 5)
        h_jour = float(c_ep.get('heures_jour') or 7.6)
        a_marquer, feries_vus = jours_a_marquer(v, jours_sem, feries)
        for j in a_marquer:
            voulus[j['date']] = (j['tranche'], h_jour)
        if feries_vus:
            messages.append("Jour(s) férié(s) pendant l'incapacité du " + v['debut'].strftime('%d/%m/%Y') + " : "
                            + ', '.join(d.strftime('%d/%m/%Y') for d in feries_vus)
                            + " — non modifié(s) dans le calendrier, à encoder vous-même (férié payé ou mutuelle).")
        if jours_sem < 5:
            messages.append(f"Horaire de {jours_sem} jours par semaine : tous les jours du lundi au vendredi de l'incapacité "
                            f"ont été marqués. Remettez en « WE » les jours où le travailleur ne devait pas travailler.")
    # Jours marques maladie qui ne sont plus dans un episode: retires du calendrier
    cur.execute("SELECT date_prestation FROM prestations WHERE travailleur_id = %s AND code_journee IN %s",
                (travailleur_id, CODES_INCAPACITE))
    for row in cur.fetchall():
        if row['date_prestation'] not in voulus:
            cur.execute("DELETE FROM prestations WHERE travailleur_id = %s AND date_prestation = %s",
                        (travailleur_id, row['date_prestation']))
    hors_dimona = 0
    for d, (tranche, h_jour) in sorted(voulus.items()):
        dim = next((x for x in dimonas if x['date_debut'] <= d and (not x['date_fin'] or x['date_fin'] >= d)), None)
        if not dim:
            hors_dimona += 1
            continue
        cur.execute("""INSERT INTO prestations (dimona_id, travailleur_id, dossier_id, date_prestation, code_journee, heures)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT (travailleur_id, date_prestation) DO UPDATE
            SET code_journee = EXCLUDED.code_journee,
                heures = CASE WHEN prestations.code_journee IN ('MG','M2','MC','MM') THEN prestations.heures ELSE EXCLUDED.heures END
            WHERE prestations.code_journee IN ('MG','M2','MC','MM','MA','P')""",
            (dim['id'], travailleur_id, dossier_id, d, tranche, h_jour))
    if hors_dimona:
        messages.append(f"{hors_dimona} jour(s) d'incapacité hors de toute Dimona : non inscrit(s) au calendrier.")
    return messages


def _fin_du_mois(d):
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


@app.route('/travailleur/<int:travailleur_id>/incapacites', methods=['GET', 'POST'])
@login_required
def incapacites_travailleur(travailleur_id):
    from psycopg2.extras import RealDictCursor
    from salaire_garanti import TYPES_INCAPACITE
    travailleur = get_travailleur(travailleur_id)
    dossier = get_dossier(travailleur['dossier_id'])
    conn = get_conn(); cur = conn.cursor(cursor_factory=RealDictCursor)
    messages, erreur = [], None

    def _date(nom):
        v = (request.form.get(nom) or '').strip()
        return datetime.strptime(v, '%Y-%m-%d').date() if v else None

    def _horizon():
        cur.execute("SELECT MAX(date_prestation) AS m FROM prestations WHERE travailleur_id = %s "
                    "AND code_journee IN ('MG','M2','MC','MM')", (travailleur_id,))
        deja = cur.fetchone()['m']
        cur.execute("SELECT MAX(COALESCE(date_fin, date_debut)) AS m FROM incapacites WHERE travailleur_id = %s", (travailleur_id,))
        dernier = cur.fetchone()['m']
        return max(x for x in (_fin_du_mois(date.today()), deja, _fin_du_mois(dernier) if dernier else None) if x)

    try:
        if request.method == 'POST':
            action = request.form.get('action')
            type_inc = request.form.get('type_incapacite') if request.form.get('type_incapacite') in TYPES_INCAPACITE else 'maladie'
            autre = request.form.get('autre_cause') == 'on'
            debut, fin = _date('date_debut'), _date('date_fin')
            if action in ('creer', 'modifier') and (not debut or (fin and fin < debut)):
                erreur = "Dates invalides : la date de début est obligatoire et la date de fin ne peut pas la précéder."
            elif action == 'creer':
                cur.execute("""INSERT INTO incapacites (travailleur_id, dossier_id, date_debut, date_fin, type_incapacite, autre_cause, note)
                               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                            (travailleur_id, dossier['id'], debut, fin, type_inc, autre, request.form.get('note') or None))
            elif action == 'modifier':
                cur.execute("""UPDATE incapacites SET date_debut=%s, date_fin=%s, type_incapacite=%s, autre_cause=%s, note=%s
                               WHERE id=%s AND travailleur_id=%s""",
                            (debut, fin, type_inc, autre, request.form.get('note') or None,
                             request.form.get('incapacite_id', type=int), travailleur_id))
            elif action == 'supprimer':
                cur.execute("DELETE FROM incapacites WHERE id=%s AND travailleur_id=%s",
                            (request.form.get('incapacite_id', type=int), travailleur_id))
            if not erreur:
                ctx_inc = _contexte_incapacites(cur, travailleur_id, _horizon())
                messages = _marquer_incapacites_au_calendrier(cur, travailleur_id, dossier['id'], ctx_inc)
                messages.insert(0, "Incapacité enregistrée : le calendrier des prestations a été mis à jour "
                                   "(un code par tranche de salaire garanti).")
                conn.commit()
        ctx_inc = _contexte_incapacites(cur, travailleur_id, _horizon())
    except Exception as ex:
        conn.rollback()
        app.logger.warning(f"Incapacites: {ex}")
        erreur = (f"Les incapacités ne peuvent pas être lues ou enregistrées ({ex}). "
                  f"Si la table n'existe pas encore, lancez : python3 migrate_charges.py")
        ctx_inc = {'episodes': [], 'ventilation': [], 'regime': None, 'contrat': None, 'alertes': [], 'regles': []}
    try:
        cur.execute('SELECT id, type_dimona, date_debut, date_fin FROM dimona WHERE travailleur_id = %s ORDER BY date_debut DESC',
                    (travailleur_id,))
        dimonas = [dict(d) for d in cur.fetchall()]
    except Exception:
        conn.rollback(); dimonas = []
    cur.close(); conn.close()
    ctx = get_context_base(); ctx['tenant'] = get_tenant()
    return render_template('incapacites.html', travailleur=travailleur, dossier=dossier, dossier_actif=dossier,
                           inc=ctx_inc, messages=messages, erreur=erreur, types=TYPES_INCAPACITE, dimonas=dimonas,
                           aujourd_hui=date.today(), **ctx)


def _rgpt_du_mois(cp_key, annee, mois):
    """Indemnite RGPT en vigueur le dernier jour du mois (parametres_dates.RGPT_VERSIONS), ou None."""
    from parametres_dates import get_rgpt
    return get_rgpt(cp_key, date(annee, mois, calendar.monthrange(annee, mois)[1]))


# ── FICHE DE PAIE DEPUIS CALENDRIER ──────────────────────────────────

@app.route('/dimona/<int:dimona_id>/generer-paie', methods=['GET', 'POST'])
@login_required
def generer_fiche_depuis_calendrier(dimona_id):
    from psycopg2.extras import RealDictCursor
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Récupérer dimona + travailleur + contrat + dossier
    cur.execute("""
        SELECT d.*, t.prenom, t.nom, t.niss, t.adresse, t.iban, t.statut_travailleur,
               t.premier_engagement AS premier_engagement_travailleur, t.categorie_personnel,
               t.date_naissance, t.etat_civil, t.nb_enfants_charge,
               t.km_domicile_travail, t.moyen_transport, t.vehicule_societe,
               dos.nom as dossier_nom, dos.adresse as dossier_adresse,
               dos.bce, dos.rsz, dos.id as dossier_id,
               dos.premier_engagement, dos.premier_engagement_depuis,
               dos.categorie_employeur, dos.code_importance, dos.code_ffe,
               t.etat_civil, t.partenaire_revenus_pro, t.partenaire_pensions,
               t.nb_enfants_sans_handicap, t.nb_enfants_avec_handicap, t.nb_personnes_charge_66,
               t.parent_isole, t.handicape, t.conjoint_handicape, t.nb_autres_personnes_charge
        FROM dimona d
        JOIN travailleurs t ON t.id = d.travailleur_id
        JOIN dossiers dos ON dos.id = d.dossier_id
        WHERE d.id = %s
    """, (dimona_id,))
    dimona = cur.fetchone()
    if not dimona:
        return "Dimona introuvable", 404

    annee = request.args.get('annee', date.today().year, type=int)
    mois = request.args.get('mois', date.today().month, type=int)

    # Contrat applicable a la PERIODE de la fiche: le contrat lie a la dimona en
    # priorite, sinon celui qui couvre le mois -- meme termine ou archive (un mois
    # sous contrat etudiant reste etudiant quand un CDI est actif depuis).
    # A defaut seulement: le contrat actif, comme avant.
    from occupation import contrat_de_la_periode, date_premiere_occupation
    from calendar import monthrange as _jours_du_mois   # (calendar est reimporte plus bas dans la fonction)
    cur.execute('SELECT * FROM contrats WHERE travailleur_id = %s', (dimona['travailleur_id'],))
    tous_contrats = [dict(c) for c in cur.fetchall()]
    contrat = contrat_de_la_periode(
        tous_contrats,
        date(annee, mois, 1), date(annee, mois, _jours_du_mois(annee, mois)[1]),
        contrat_id=dimona.get('contrat_id'), type_contrat=dimona.get('type_dimona'))
    if not contrat:
        cur.execute("""SELECT * FROM contrats WHERE travailleur_id = %s AND statut = 'actif'
            AND type_contrat = %s ORDER BY date_debut DESC LIMIT 1""",
            (dimona['travailleur_id'], dimona['type_dimona']))
        contrat = cur.fetchone()
        if not contrat:
            cur.execute("""SELECT * FROM contrats WHERE travailleur_id = %s AND statut = 'actif'
                ORDER BY created_at DESC LIMIT 1""", (dimona['travailleur_id'],))
            contrat = cur.fetchone()

    # Incapacites de travail (maladie / accident de droit commun) touchant ce mois:
    # tranches de salaire garanti, regles appliquees, suivi et alertes
    debut_mois_p = date(annee, mois, 1)
    fin_mois_p = date(annee, mois, _jours_du_mois(annee, mois)[1])
    maladie_infos, maladie_alertes, ctx_inc = [], [], None
    try:
        ctx_inc = _contexte_incapacites(cur, dimona['travailleur_id'], fin_mois_p, contrat=dict(contrat) if contrat else None)
        du_mois = [v for v in ctx_inc['ventilation'] if v['debut'] <= fin_mois_p and v['fin'] >= debut_mois_p]
        maladie_alertes = list(ctx_inc['alertes']) if ctx_inc['episodes'] else []
        for v in du_mois:
            maladie_infos.append(
                f"{v['libelle_type']} du {v['debut']:%d/%m/%Y} au {v['fin']:%d/%m/%Y}"
                + (' (en cours)' if v['en_cours'] else '') + f" — {v['libelle_regime']}"
                + (f", rechute : décompte repris au jour {v['rang_depart'] + 1}" if v['rechute_de'] else '') + " : "
                + ' ; '.join(f"{p_['libelle']} du {p_['du']:%d/%m} au {p_['au']:%d/%m} ({p_['jours']} j"
                             + (f", {p_['motif']}" if p_['motif'] else '') + ")" for p_ in v['periodes']))
            maladie_infos += v['infos']
            maladie_alertes += v['alertes']
        if du_mois:
            maladie_infos += ctx_inc['regles']
            # Le statut vient de la CP du contrat: si la fiche du travailleur dit « employe »
            # alors que la CP est une CP d'ouvriers, le salaire garanti suit l'art. 52
            # (un mois d'anciennete) et non l'art. 70 -- on le dit clairement.
            if ctx_inc['regime'] == 'ouvrier' and (dimona.get('statut_travailleur') or '') == 'employe':
                maladie_alertes.insert(0,
                    f"Ce travailleur est encodé comme employé, mais son contrat est en {contrat['cp_key']}, une commission "
                    f"paritaire d'ouvriers : la paie et le salaire garanti sont calculés selon les règles des ouvriers "
                    f"(un mois d'ancienneté requis, art. 52). Un employé a droit à 30 jours de rémunération dès le premier "
                    f"jour (art. 70) : si c'est un employé, corrigez la commission paritaire du contrat.")
    except Exception as ex_inc:
        conn.rollback()
        app.logger.warning(f"Incapacites (fiche): {ex_inc}")
        maladie_alertes = [f"Incapacités non lues ({ex_inc}) : le salaire garanti n'est pas calculé. "
                           f"Lancez python3 migrate_charges.py si la table n'existe pas."]

    # Km domicile-travail, taux et moyen de transport de la derniere fiche du travailleur:
    # proposes dans le formulaire pour ne pas les oublier
    from occupation import km_a_proposer, personnel_roulant, rgpt_coche_par_defaut
    derniere_fiche_km = None
    try:
        cur.execute("""SELECT km_domicile, taux_km, moyen_transport, periode_debut FROM fiches_paie
                       WHERE travailleur_id = %s AND remplacee_par IS NULL AND km_domicile IS NOT NULL
                       ORDER BY periode_debut DESC, id DESC LIMIT 1""", (dimona['travailleur_id'],))
        derniere_fiche_km = cur.fetchone()
    except Exception as ex_km:
        conn.rollback()
        app.logger.warning(f"Km de la derniere fiche non lus: {ex_km}")
    km_propose = km_a_proposer(derniere_fiche_km, dimona.get('km_domicile_travail'))

    if request.method == 'POST':
        form = request.form

        # Récupérer les prestations du mois depuis la BDD
        import calendar
        premier_jour = date(annee, mois, 1)
        dernier_jour = date(annee, mois, calendar.monthrange(annee, mois)[1])

        cur.execute("""
            SELECT code_journee, heures, date_prestation
            FROM prestations
            WHERE dimona_id = %s
            AND date_prestation BETWEEN %s AND %s
        """, (dimona_id, premier_jour, dernier_jour))
        prestations = cur.fetchall()

        # Codes journaliers payés comme prestations
        CODES_PRESTES = {'P', 'S', 'HS', 'PP'}
        CODES_FERIES = {'F', 'FM'}
        CODES_CONGE = {'CL', 'CE', 'VP'}
        CODES_MALADIE = {'MA', 'AC', 'MAT', 'PAT', 'MG', 'M2', 'MC', 'MM'}
        CODES_SALAIRE_GARANTI = {'MA', 'MG', 'M2', 'MC', 'MM'}   # maladie / accident de droit commun
        heures_jour = float(contrat.get('heures_jour') or 7.6) if contrat else 7.6
        CODES_CHOMAGE = {'CT', 'CI', 'CNP'}

        jours_prestes = sum(1 for p in prestations if p['code_journee'] in CODES_PRESTES)
        heures_prestees = float(sum(p['heures'] or 0 for p in prestations if p['code_journee'] in CODES_PRESTES))
        jours_feries = sum(1 for p in prestations if p['code_journee'] in CODES_FERIES)
        heures_feries = float(sum(p['heures'] or heures_jour for p in prestations if p['code_journee'] in CODES_FERIES))
        jours_conge = sum(1 for p in prestations if p['code_journee'] in CODES_CONGE)
        jours_maladie = sum(1 for p in prestations if p['code_journee'] in CODES_MALADIE)
        jours_chomage = sum(1 for p in prestations if p['code_journee'] in CODES_CHOMAGE)

        # Paramètres indemnités depuis le form
        rgpt_actif = form.get('rgpt_actif') == 'on'
        arab_heure = float(form.get('arab_heure', 0) or 0)
        cheques_repas = form.get('cheques_repas') == 'on'
        vehicule_societe = form.get('vehicule_societe') == 'on' or (dimona.get('vehicule_societe') or False)
        km_domicile = int(form.get('km_domicile', dimona.get('km_domicile_travail', 0)) or 0)
        moyen_transport = form.get('moyen_transport', dimona.get('moyen_transport', 'voiture'))

        # Jours de maladie du calendrier -> tranche de salaire garanti recalculee depuis
        # les episodes (le code affiche dans le calendrier n'est qu'un rappel)
        jours_incapacite, hors_episode = [], 0
        for p in prestations:
            if p['code_journee'] not in CODES_SALAIRE_GARANTI:
                continue
            j_inc = ctx_inc['par_date'].get(p['date_prestation']) if ctx_inc else None
            if j_inc:
                jours_incapacite.append({'date': p['date_prestation'], 'tranche': j_inc['tranche'],
                                         'heures': float(p['heures'] or heures_jour)})
            else:
                hors_episode += 1
        maladie_sans_episode = []
        if hors_episode:
            maladie_alertes.append(
                f"{hors_episode} jour(s) codé(s) maladie dans le calendrier hors de tout épisode d'incapacité : rien n'est "
                f"calculé pour ces jours. Créez l'épisode (bouton ci-dessous ou page « Maladie » du travailleur), puis recalculez.")
            if ctx_inc and ctx_inc['regime']:
                from salaire_garanti import jours_maladie_sans_episode
                maladie_sans_episode = jours_maladie_sans_episode(
                    [(p['date_prestation'], p['code_journee']) for p in prestations], ctx_inc['par_date'])
        incapacite = {'regime': ctx_inc['regime'] if ctx_inc else None, 'jours': jours_incapacite,
                      'infos': maladie_infos, 'alertes': maladie_alertes}

        if jours_prestes == 0 and jours_feries == 0 and not jours_incapacite:
            cur.close(); conn.close()
            return redirect(url_for('calendrier_prestations',
                dimona_id=dimona_id, annee=annee, mois=mois,
                error='Aucune prestation encodée pour ce mois'))

        # Importer le moteur
        import sys
        sys.path.insert(0, '/var/www/duxsalary')
        from moteur_paie import calculer_fiche_paie
        from generer_fiche_pdf import generer_fiche_paie_pdf

        # Premier engagement
        # Premier engagement (code 3315): le dossier ouvre le droit (case + date de debut),
        # mais la reduction ne vise que LE travailleur designe (case de sa fiche)
        from occupation import premier_engagement_du_travailleur
        cur.execute("SELECT COUNT(*) AS n FROM travailleurs WHERE dossier_id = %s AND premier_engagement = TRUE",
                    (dimona['dossier_id'],))
        premier_engagement, alerte_pe = premier_engagement_du_travailleur(
            dimona.get('premier_engagement'), dimona.get('premier_engagement_travailleur'), cur.fetchone()['n'])
        cp_key = contrat['cp_key'] if contrat else dimona.get('cp_key', 'CP 140.03')
        salaire_h = float(contrat['salaire_horaire']) if contrat else 14.9255
        heures_sem = float(contrat['heures_semaine']) if contrat else 38.0
        heures_jour = float(contrat.get('heures_jour') or 7.6) if contrat else 7.6
        jours_semaine = int(contrat.get('jours_semaine') or 5) if contrat else 5
        is_etudiant = contrat['type_contrat'] == 'STU' if contrat else False
        # Situation familiale pour calcul précompte
        etat_civil_trav = dimona.get('etat_civil', 'celibataire') or 'celibataire'
        nb_enfants = int((dimona.get('nb_enfants_sans_handicap') or 0)) + int((dimona.get('nb_enfants_avec_handicap') or 0))

        import calendar as cal
        periode_debut = date(annee, mois, 1)
        periode_fin = date(annee, mois, cal.monthrange(annee, mois)[1])

        # Cheques-repas: nombre et montants issus du SUIVI DES CHEQUES du dossier
        # (applique si le dossier les a actives ou si la CP les rend obligatoires)
        cr_calc = None
        repas_fournis = False   # option du dossier (page « Chèques »): l'employeur fournit des repas
        try:
            cfg_cr = _config_cheques(cur, dimona['dossier_id'])
            repas_fournis = cfg_cr['repas_fournis']
            cur.execute("SELECT * FROM travailleurs WHERE id=%s", (dimona['travailleur_id'],))
            calc_cr = _calcul_cheques_travailleur(cur, dict(cur.fetchone()), annee, mois, cfg_cr)
            if calc_cr and (cfg_cr['actif'] or calc_cr['repas']['obligatoire']) and calc_cr['repas']['nombre']:
                cr_calc = calc_cr['repas']
        except Exception as ex_cr:
            app.logger.warning(f"Suivi cheques non applique: {ex_cr}")
            conn.rollback()

        # Allocations exceptionnelles saisies (decembre: prime de fin d'annee;
        # juin CP 200: prime annuelle; mai/juin: double pecule employe)
        def _montant(nom):
            try:
                return float((form.get(nom) or '0').replace(',', '.') or 0)
            except ValueError:
                return 0.0
        prime_fa, prime_an = _montant('prime_fin_annee'), _montant('prime_annuelle')
        libelles_prime = []
        if prime_fa: libelles_prime.append("Prime de fin d'année")
        if prime_an: libelles_prime.append('Prime annuelle sectorielle')

        # Bonus a l'emploi deja accorde cette annee civile (plafond annuel par
        # travailleur) -- fiches enregistrees des mois precedents uniquement
        cur.execute("""SELECT COALESCE(SUM(COALESCE(bonus_emploi_a, 0) + COALESCE(bonus_emploi_b, 0)), 0) AS cumul
                       FROM fiches_paie
                       WHERE travailleur_id = %s AND EXTRACT(YEAR FROM periode_fin) = %s AND periode_fin < %s
                         AND remplacee_par IS NULL""",
                    (dimona['travailleur_id'], annee, periode_debut))
        bonus_cumul_annee = float(cur.fetchone()['cumul'] or 0)

        data = calculer_fiche_paie(
            incapacite=incapacite,
            bonus_emploi_cumul_annee=bonus_cumul_annee,
            repas_fournis=repas_fournis,
            # Bareme par annees d'experience (alerte de salaire minimum)
            annees_experience=contrat.get('annees_experience') if contrat else None,
            date_debut_contrat=contrat['date_debut'] if contrat else None,
            cheques_repas_calc=cr_calc,
            prime_exceptionnelle=prime_fa + prime_an,
            libelle_prime=' + '.join(libelles_prime) or "Prime de fin d'année",
            double_pecule=_montant('double_pecule'),
            precompte_pecule_manuel=_montant('precompte_pecule') or None,
            prenom=dimona['prenom'], nom=dimona['nom'],
            niss=dimona['niss'] or '—', adresse=dimona['adresse'] or '—',
            iban=dimona['iban'] or '—',
            date_naissance=dimona['date_naissance'],
            # Date d'entree et anciennete: PREMIERE occupation chez l'employeur
            # (premier contrat, etudiant compris), comme sur le compte individuel
            date_entree=date_premiere_occupation(tous_contrats)
                        or (contrat['date_debut'] if contrat else periode_debut),
            nom_societe=dimona['dossier_nom'],
            adresse_societe=dimona['dossier_adresse'] or '—',
            bce_societe=dimona['bce'] or '—',
            rsz_societe=dimona['rsz'] or '—',
            cp_key=cp_key, categorie=contrat['categorie'] if contrat else '—',
            fonction=contrat.get('fonction') if contrat else None,
            personnel_roulant=personnel_roulant(dimona.get('categorie_personnel')),
            salaire_horaire=salaire_h,
            salaire_mensuel_fixe=float(contrat.get('salaire_mensuel') or 0) if contrat else 0.0,
            etat_civil=dimona.get('etat_civil', 'celibataire') or 'celibataire',
            # Enfants de la situation familiale (enfant handicape compte pour deux,
            # annexe 3 formule-cle). Corrige le 30/09/2026: l'ancien champ
            # nb_enfants_charge etait transmis a la place des nouveaux champs.
            nb_enfants=(int(dimona.get('nb_enfants_sans_handicap') or 0)
                        + 2 * int(dimona.get('nb_enfants_avec_handicap') or 0))
                       or int(dimona.get('nb_enfants_charge', 0) or 0),
            charges_famille={
                'parent_isole': bool(dimona.get('parent_isole')),
                'handicape': bool(dimona.get('handicape')),
                'conjoint_handicape': bool(dimona.get('conjoint_handicape')),
                'nb_personnes_charge_dependance': int(dimona.get('nb_personnes_charge_66') or 0),
                'nb_autres_personnes_charge': int(dimona.get('nb_autres_personnes_charge') or 0),
            },
            partenaire_revenus_pro=dimona.get('partenaire_revenus_pro', 'non') or 'non',
            partenaire_pensions=dimona.get('partenaire_pensions', 'non') or 'non',
            type_contrat=contrat['type_contrat'] if contrat else 'CDD',
            heures_jour=heures_jour,
            heures_semaine=float(contrat.get('heures_semaine') or 38.0) if contrat else 38.0,
            jours_semaine=int(contrat.get('jours_semaine') or 5) if contrat else 5,
            is_etudiant=is_etudiant,
            jours_prestes=jours_prestes, heures_prestees=heures_prestees,
            jours_feries_payes=jours_feries, heures_feries=heures_feries,
            jours_conge=jours_conge, jours_maladie=jours_maladie, jours_chomage=jours_chomage,
            premier_engagement=premier_engagement,
            categorie_employeur=dimona.get('categorie_employeur') or '000',
            code_ffe=dimona.get('code_ffe'), code_importance=dimona.get('code_importance'),
            frais_nets=float(form.get('frais_nets', 0) or 0),
            km_domicile=km_domicile, moyen_transport=moyen_transport,
            vehicule_societe=vehicule_societe,
            rgpt_actif=rgpt_actif, arab_heure=arab_heure, cheques_repas=cheques_repas,
            taux_km=float(form.get('taux_km', 0.4444) or 0.4444),
            periode_debut=periode_debut, periode_fin=periode_fin,
        )

        if alerte_pe:
            data['alertes_calcul'].append(alerte_pe)

        # Aide a la DmfA: jours et heures par code prestation ONSS, enregistres avec la fiche
        # (meme calcul que la page « Aide DmfA », qui compare ensuite avec le calendrier)
        if contrat:
            try:
                from dmfa import jours_du_calendrier, prestations_occupation, prestations_json
                data['prestations_dmfa'] = prestations_json(prestations_occupation(
                    dict(contrat), jours_du_calendrier(prestations, ctx_inc['par_date'] if ctx_inc else None),
                    periode_debut, periode_fin))
            except Exception as ex_dmfa:
                app.logger.warning(f"Detail DmfA non enregistre: {ex_dmfa}")

        # ── ETAPE 1 : "Calculer la paie" -> page de detail, RIEN n'est ecrit ──
        # Le PDF et l'enregistrement en base ne se font qu'apres validation
        # explicite sur la page de detail (action=generer).
        if form.get('action') != 'generer':
            cur.close(); conn.close()
            ctx = get_context_base(); ctx['tenant'] = get_tenant()
            mois_nom_calc = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet',
                             'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'][mois]
            champs = [(k, v) for k, v in form.items(multi=True) if k != 'action']
            return render_template('calcul_paie_detail.html', data=data, dimona=dimona, contrat=contrat,
                                   annee=annee, mois=mois, mois_nom=mois_nom_calc, champs=champs,
                                   maladie_sans_episode=maladie_sans_episode,
                                   dossier_actif=get_dossier(dimona['dossier_id']), **ctx)

        # ── ETAPE 2 : "Generer la fiche" (valide sur la page de detail) ──
        # Générer le PDF
        mois_nom = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'][mois]
        # Le PDF d'une fiche deja emise n'est jamais ecrase (c'est ce qui a ete envoye au
        # client): une fiche regeneree recoit un nouveau nom de fichier (_v2, _v3...)
        from fiches_remplacees import chemin_pdf_libre
        filename = f"fiche_paie_{dimona['nom']}_{dimona['prenom']}_{mois_nom}_{annee}.pdf"
        filepath = chemin_pdf_libre(os.path.join(OUTPUT_DIR, filename))
        filename = os.path.basename(filepath)
        generer_fiche_paie_pdf(data, filepath)

        # Sauvegarder en BDD
        # Colonnes de la fiche: source unique documents_charges.valeurs_fiche
        # (totaux + detail pour le compte individuel, l'attestation, la ventilation)
        from documents_charges import valeurs_fiche
        valeurs = dict(valeurs_fiche(data),
                       dossier_id=dimona['dossier_id'], travailleur_id=dimona['travailleur_id'],
                       contrat_id=contrat['id'] if contrat else None,
                       periode_debut=periode_debut, periode_fin=periode_fin,
                       pdf_path=filepath, statut_paiement='genere')
        colonnes = list(valeurs)
        cur.execute(f"INSERT INTO fiches_paie ({', '.join(colonnes)}) "
                    f"VALUES ({', '.join(['%s'] * len(colonnes))}) RETURNING id",
                    [valeurs[c] for c in colonnes])
        fiche_id = cur.fetchone()['id']
        # Une seule fiche active par travailleur, contrat et periode: les fiches precedentes
        # passent au statut « remplacee » (elles restent consultables avec leur PDF, mais
        # sortent de l'attestation, du compte individuel, de la ventilation, de l'aide DmfA
        # et des lettres ONSS)
        cur.execute("""UPDATE fiches_paie SET remplacee_par = %s, remplacee_le = NOW()
                       WHERE travailleur_id = %s AND contrat_id IS NOT DISTINCT FROM %s
                         AND periode_debut = %s AND periode_fin = %s AND id <> %s AND remplacee_par IS NULL""",
                    (fiche_id, dimona['travailleur_id'], contrat['id'] if contrat else None,
                     periode_debut, periode_fin, fiche_id))
        conn.commit()
        cur.close(); conn.close()

        if not os.path.exists(filepath):
            return redirect(url_for('fiche_travailleur', travailleur_id=dimona['travailleur_id'], tab='fiches'))
        return send_file(filepath, as_attachment=False,
                            download_name=filename, mimetype='application/pdf')

    # GET — afficher le formulaire popup
    cur.close(); conn.close()

    import calendar as cal
    mois_nom = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'][mois]
    cp_key = contrat['cp_key'] if contrat else 'CP 140.03'

    # Suggestion prime de fin d'annee (decembre uniquement, indicative)
    prime_suggestion = None
    if mois == 12:
        try:
            from regles_cp import get_regles_cp
            from prime_fin_annee import calculer_prime_fin_annee
            regles_prime = get_regles_cp(cp_key).get('prime_fin_annee')
            if regles_prime and contrat and contrat.get('date_debut'):
                periode_fin_calc = date(annee, mois, cal.monthrange(annee, mois)[1])
                anciennete_m = (periode_fin_calc.year - contrat['date_debut'].year) * 12 + \
                               (periode_fin_calc.month - contrat['date_debut'].month)
                sal_h = float(contrat.get('salaire_horaire') or 0)
                heures_sem_c = float(contrat.get('heures_semaine') or 38)
                sal_mensuel_calc = float(contrat.get('salaire_mensuel') or 0) or \
                    round(sal_h * heures_sem_c * 52 / 12, 2)
                prime_suggestion = calculer_prime_fin_annee(
                    regles_prime, salaire_mensuel_brut=sal_mensuel_calc,
                    mois_prestes_annee=12, anciennete_mois=anciennete_m)
        except Exception as ex:
            app.logger.warning(f"Suggestion prime fin annee: {ex}")
            prime_suggestion = None

    # Juin: prime annuelle sectorielle (CP 200: 330,84 EUR, periode juin N-1 -> mai N)
    # et indication du double pecule (mai/juin, employes) -- indicatives uniquement
    prime_annuelle_suggestion = pecule_suggestion = None
    try:
        from regles_cp import get_regles_cp
        regle_pa = get_regles_cp(cp_key).get('prime_annuelle_sectorielle') if contrat else None
        if mois == 6 and regle_pa and regle_pa.get('applicable'):
            p_deb, p_fin = date(annee - 1, 6, 1), date(annee, 5, 31)
            d0 = max(contrat['date_debut'], p_deb) if contrat.get('date_debut') else p_deb
            d1 = min(contrat['date_fin'] or p_fin, p_fin)
            nb_mois = max(0, min(12, (d1.year - d0.year) * 12 + d1.month - d0.month + 1)) if d1 >= d0 else 0
            hs = float(contrat.get('heures_semaine') or 38) or 38.0
            regime = min(1.0, float(contrat.get('heures_jour') or 7.6) * int(contrat.get('jours_semaine') or 5) / hs)
            montant = round(regle_pa['montant_brut_annuel'] * nb_mois / 12 * regime, 2)
            prime_annuelle_suggestion = {
                'montant': montant,
                'methode': f"{regle_pa['montant_brut_annuel']:.2f} € x {nb_mois}/12 mois x régime {regime:.0%}",
                'regle': f"Payée en juin, période de référence {p_deb:%m/%Y} – {p_fin:%m/%Y}, au prorata des prestations et du régime."}
        if mois in (5, 6) and contrat and contrat.get('type_contrat') != 'STU':
            from conges_legaux import calculer_mois_depuis_contrats
            from pecule_vacances import calculer_double_pecule_employe
            statut_c = get_regles_cp(cp_key).get('type_travailleur_defaut', 'employe')
            if statut_c == 'employe':
                cur2 = get_conn().cursor(cursor_factory=RealDictCursor)
                cur2.execute("SELECT id, type_contrat, statut, date_debut, date_fin FROM contrats WHERE travailleur_id=%s",
                             (dimona['travailleur_id'],))
                m_ref = calculer_mois_depuis_contrats([dict(x) for x in cur2.fetchall()], annee - 1)['mois_ouvrant_droit']
                cur2.connection.close()
                hs = float(contrat.get('heures_semaine') or 38) or 38.0
                sal = float(contrat.get('salaire_mensuel') or 0) or round(float(contrat.get('salaire_horaire') or 0) * hs * 52 / 12, 2)
                dp = calculer_double_pecule_employe(sal, m_ref)
                if dp.get('droit'):
                    pecule_suggestion = {'montant': dp['pecule_base'], 'methode': dp['methode'] + f" ({m_ref} mois ouvrant droit en {annee-1})"}
    except Exception as ex_s:
        app.logger.warning(f"Suggestions juin: {ex_s}")

    ctx = get_context_base()
    ctx['tenant'] = get_tenant()
    return render_template('generer_fiche_form.html',
        dimona=dimona, contrat=contrat, prime_suggestion=prime_suggestion,
        prime_annuelle_suggestion=prime_annuelle_suggestion, pecule_suggestion=pecule_suggestion,
        annee=annee, mois=mois, mois_nom=mois_nom,
        cp_key=cp_key,
        vehicule_societe=dimona.get('vehicule_societe', False),
        km_domicile=km_propose['km'], km_propose=km_propose,
        rgpt=_rgpt_du_mois(cp_key, annee, mois),
        rgpt_defaut=rgpt_coche_par_defaut(dimona.get('categorie_personnel')),
        categorie_personnel=dimona.get('categorie_personnel'),
        maladie_infos=maladie_infos, maladie_alertes=maladie_alertes,
        **ctx)

# ── SUPPRESSION FICHE DE PAIE ─────────────────────────────────────────

@app.route('/fiche/<int:fiche_id>/supprimer', methods=['POST'])
@login_required
def supprimer_fiche_paie(fiche_id):
    conn = get_conn()
    from psycopg2.extras import RealDictCursor
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT travailleur_id, pdf_path FROM fiches_paie WHERE id = %s", (fiche_id,))
    fiche = cur.fetchone()
    if not fiche:
        cur.close(); conn.close()
        return "Introuvable", 404
    travailleur_id = fiche['travailleur_id']
    # Les fiches que celle-ci remplacait redeviennent actives (sinon la periode n'aurait plus de fiche)
    cur.execute("UPDATE fiches_paie SET remplacee_par = NULL, remplacee_le = NULL WHERE remplacee_par = %s", (fiche_id,))
    # Supprimer le fichier PDF s'il existe et qu'aucune autre fiche ne l'utilise
    cur.execute("SELECT COUNT(*) AS n FROM fiches_paie WHERE pdf_path = %s AND id <> %s", (fiche.get('pdf_path'), fiche_id))
    pdf_partage = cur.fetchone()['n'] > 0
    if fiche.get('pdf_path') and os.path.exists(fiche['pdf_path']) and not pdf_partage:
        try:
            os.remove(fiche['pdf_path'])
        except:
            pass
    cur.execute("DELETE FROM fiches_paie WHERE id = %s", (fiche_id,))
    conn.commit(); cur.close(); conn.close()
    return redirect(url_for('fiche_travailleur', travailleur_id=travailleur_id, tab='fiches'))


# ── LETTRE ONSS MENSUELLE ─────────────────────────────────────────────

@app.route('/dossier/<int:dossier_id>/lettre-onss', methods=['GET', 'POST'])
@login_required
def lettre_onss(dossier_id):
    from psycopg2.extras import RealDictCursor
    dossier = get_dossier(dossier_id)
    ctx = get_context_base()
    ctx['tenant'] = get_tenant()

    annee = request.args.get('annee', date.today().year, type=int)
    mois = request.args.get('mois', date.today().month, type=int)

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Récupérer toutes les fiches du mois pour ce dossier
    import calendar as cal
    premier = date(annee, mois, 1)
    dernier = date(annee, mois, cal.monthrange(annee, mois)[1])
    mois_nom = ['','Janvier','Février','Mars','Avril','Mai','Juin',
                'Juillet','Août','Septembre','Octobre','Novembre','Décembre'][mois]

    cur.execute("""
        SELECT f.*, t.prenom || ' ' || t.nom as nom_travailleur,
               t.niss, c.cp_key, c.type_contrat
        FROM fiches_paie f
        JOIN travailleurs t ON t.id = f.travailleur_id
        LEFT JOIN contrats c ON c.id = f.contrat_id
        WHERE f.dossier_id = %s
        AND f.periode_debut >= %s AND f.periode_fin <= %s
        AND f.remplacee_par IS NULL
    """, (dossier_id, premier, dernier))
    fiches = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()

    if request.method == 'POST':
        return generer_lettre_onss_pdf(dossier, fiches, annee, mois, mois_nom)

    return render_template('lettre_onss.html',
        dossier=dossier, dossier_actif=dossier,
        fiches=fiches, annee=annee, mois=mois, mois_nom=mois_nom,
        **ctx)


def generer_lettre_onss_pdf(dossier, fiches, annee, mois, mois_nom):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    try:
        pdfmetrics.registerFont(TTFont('DVSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
        pdfmetrics.registerFont(TTFont('DVSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
        FN, FNB = 'DVSans', 'DVSans-Bold'
    except:
        FN, FNB = 'Helvetica', 'Helvetica-Bold'

    NAVY = couleur('primaire')
    LGRAY = colors.HexColor('#f5f5f5')
    LINE = colors.HexColor('#cccccc')

    def sty(bold=False, size=9, align=TA_LEFT):
        return ParagraphStyle('x', fontName=FNB if bold else FN,
                              fontSize=size, leading=size+3, alignment=align)
    def p(t, **kw): return Paragraph(str(t or ''), sty(**kw))

    filename = f"lettre_ONSS_{dossier['nom']}_{mois_nom}_{annee}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4,
        topMargin=2*cm, bottomMargin=2*cm, leftMargin=2*cm, rightMargin=2*cm)
    e = []

    # En-tête
    e.append(p(dossier['nom'], bold=True, size=12))
    e.append(p(dossier.get('adresse', ''), size=9))
    e.append(p(f"BCE : {dossier.get('bce','')}  |  RSZ : {dossier.get('rsz','')}", size=9))
    e.append(Spacer(1, 0.3*cm))
    e.append(HRFlowable(width='100%', thickness=1.5, color=NAVY))
    e.append(Spacer(1, 0.3*cm))
    e.append(p(f"DECLARATION ET PAIEMENT ONSS — {mois_nom.upper()} {annee}", bold=True, size=13))
    e.append(p(f"Date limite de paiement : 5e jour ouvrable du mois suivant", size=9))
    e.append(Spacer(1, 0.5*cm))

    # Totaux
    total_brut = sum(float(f.get('salaire_brut', 0) or 0) for f in fiches)
    total_onss_pers = sum(float(f.get('onss_personnel', 0) or 0) for f in fiches)
    total_onss_pat = sum(float(f.get('onss_patronal', 0) or 0) for f in fiches)
    total_onss = total_onss_pers + total_onss_pat

    # Tableau par travailleur
    cols = [5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 3*cm]
    rows = [[
        p('Travailleur', bold=True),
        p('Brut ONSS', bold=True, align=TA_RIGHT),
        p('ONSS pers.', bold=True, align=TA_RIGHT),
        p('ONSS pat.', bold=True, align=TA_RIGHT),
        p('Total ONSS', bold=True, align=TA_RIGHT),
    ]]
    for f in fiches:
        brut = float(f.get('salaire_brut', 0) or 0)
        op = float(f.get('onss_personnel', 0) or 0)
        opp = float(f.get('onss_patronal', 0) or 0)
        rows.append([
            p(f.get('nom_travailleur', '—')),
            p(f"{brut:.2f} €", align=TA_RIGHT),
            p(f"{op:.2f} €", align=TA_RIGHT),
            p(f"{opp:.2f} €", align=TA_RIGHT),
            p(f"{op+opp:.2f} €", align=TA_RIGHT),
        ])
    # Ligne total
    rows.append([
        p('TOTAL', bold=True),
        p(f"{total_brut:.2f} €", bold=True, align=TA_RIGHT),
        p(f"{total_onss_pers:.2f} €", bold=True, align=TA_RIGHT),
        p(f"{total_onss_pat:.2f} €", bold=True, align=TA_RIGHT),
        p(f"{total_onss:.2f} €", bold=True, align=TA_RIGHT),
    ])

    t = Table(rows, colWidths=cols)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), LGRAY),
        ('LINEBELOW', (0,0), (-1,0), 0.5, LINE),
        ('LINEABOVE', (0,-1), (-1,-1), 1, NAVY),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    e.append(t)
    e.append(Spacer(1, 0.5*cm))

    # Récapitulatif à payer
    recap = [
        ['ONSS personnel', f"{total_onss_pers:.2f} EUR"],
        ['ONSS patronal', f"{total_onss_pat:.2f} EUR"],
        ['TOTAL À PAYER À L\'ONSS', f"{total_onss:.2f} EUR"],
    ]
    for i, (label, val) in enumerate(recap):
        bold = i == len(recap) - 1
        e.append(Table([[p(label, bold=bold, size=10), p(val, bold=bold, size=10, align=TA_RIGHT)]],
                      colWidths=[12*cm, 4.5*cm]))
    e.append(Spacer(1, 0.5*cm))

    # Instructions paiement
    e.append(HRFlowable(width='100%', thickness=0.5, color=LINE))
    e.append(Spacer(1, 0.3*cm))
    e.append(p('INSTRUCTIONS DE PAIEMENT', bold=True, size=10))
    e.append(Spacer(1, 0.15*cm))
    e.append(p(f"Virement bancaire vers : BE63 6790 2618 1108 (BIC: GEBABEBB)", size=9))
    e.append(p(f"Communication : {dossier.get('rsz','').replace('-','')} - {mois:02d}/{annee}", size=9))
    e.append(p(f"Date limite : avant le 5e jour ouvrable de {['','Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre'][(mois%12)+1]}", size=9))
    e.append(Spacer(1, 0.3*cm))
    e.append(Spacer(1, 0.2*cm))
    e.append(p("Note : Ce montant correspond aux cotisations ONSS de base. Des cotisations sectorielles CP 140.03 (Fonds de sécurité d'existence, formation) seront calculées et facturées directement par l'ONSS après introduction de la DmfA trimestrielle.", size=8))
    e.append(Spacer(1, 0.1*cm))
    e.append(p(f"Etabli par : {get_branding()['societe']}", size=8))

    doc.build(e, **pdf_decor())
    # Sauvegarder en base
    from psycopg2.extras import RealDictCursor as RDC
    conn2 = get_conn()
    cur2 = conn2.cursor()
    cur2.execute('''INSERT INTO lettres_onss (dossier_id, mois, annee, total_brut, total_onss_personnel, total_onss_patronal, total_onss, pdf_path)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING''',
        (dossier['id'], mois, annee,
         round(sum(float(f.get('salaire_brut') or 0) for f in fiches), 2),
         round(sum(float(f.get('onss_personnel') or 0) for f in fiches), 2),
         round(sum(float(f.get('onss_patronal') or 0) for f in fiches), 2),
         round(sum(float(f.get('onss_personnel') or 0) + float(f.get('onss_patronal') or 0) for f in fiches), 2),
         filepath))
    conn2.commit(); cur2.close(); conn2.close()
    return send_file(filepath, as_attachment=False, download_name=filename, mimetype='application/pdf')


# ── DOCUMENTS FIN DE CONTRAT ──────────────────────────────────────────

@app.route('/contrat/<int:contrat_id>/fin-contrat', methods=['GET', 'POST'])
@login_required
def fin_contrat(contrat_id):
    from psycopg2.extras import RealDictCursor
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT c.*, t.prenom, t.nom, t.niss, t.adresse, t.iban,
               t.date_naissance, t.etat_civil,
               dos.nom as dossier_nom, dos.adresse as dossier_adresse,
               dos.bce, dos.rsz, dos.representant, dos.id as dossier_id
        FROM contrats c
        JOIN travailleurs t ON t.id = c.travailleur_id
        JOIN dossiers dos ON dos.id = c.dossier_id
        WHERE c.id = %s
    """, (contrat_id,))
    contrat = cur.fetchone()
    cur.close(); conn.close()
    if not contrat:
        return "Introuvable", 404

    ctx = get_context_base()
    ctx['tenant'] = get_tenant()

    if request.method == 'POST':
        doc_type = request.form.get('doc_type', 'certificat')
        travailleur_lng = {'langue': contrat.get('langue', 'fr')}
        dossier_lng = {'region_linguistique': contrat.get('region_linguistique', 'bruxelles_fr')}
        langue_doc = get_langue_document(dossier_lng, travailleur_lng)
        if doc_type == 'certificat':
            if langue_doc == 'nl':
                return generer_certificat_travail_nl(dict(contrat))
            return generer_certificat_travail(dict(contrat))
        elif doc_type == 'c4':
            if langue_doc == 'nl':
                fp, fn = generer_c4_nl(dict(contrat), request.form)
                return send_file(fp, as_attachment=False, download_name=fn, mimetype='application/pdf')
            return generer_c4(dict(contrat), request.form)

    return render_template('fin_contrat.html', contrat=contrat,
                           dossier_actif={'id': contrat['dossier_id'], 'nom': contrat['dossier_nom']},
                           **ctx)


def generer_certificat_travail(c):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    try:
        pdfmetrics.registerFont(TTFont('DVSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
        pdfmetrics.registerFont(TTFont('DVSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
        FN, FNB = 'DVSans', 'DVSans-Bold'
    except:
        FN, FNB = 'Helvetica', 'Helvetica-Bold'

    NAVY = couleur('primaire')
    sN = ParagraphStyle('N', fontName=FN, fontSize=10, leading=15)
    sB = ParagraphStyle('B', fontName=FNB, fontSize=10, leading=15)
    sT = ParagraphStyle('T', fontName=FNB, fontSize=14, leading=20, alignment=TA_CENTER)
    sJ = ParagraphStyle('J', fontName=FN, fontSize=10, leading=15, alignment=TA_JUSTIFY)

    filename = f"certificat_travail_{c['nom']}_{c['prenom']}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4,
        topMargin=2*cm, bottomMargin=2*cm, leftMargin=2.5*cm, rightMargin=2.5*cm)
    e = []

    e.append(Paragraph(c['dossier_nom'], sB))
    e.append(Paragraph(c.get('dossier_adresse', ''), sN))
    e.append(Paragraph(f"BCE : {c.get('bce','')}  |  RSZ : {c.get('rsz','')}", sN))
    e.append(Spacer(1, 0.5*cm))
    e.append(HRFlowable(width='100%', thickness=2, color=NAVY))
    e.append(Spacer(1, 0.5*cm))
    e.append(Paragraph("CERTIFICAT DE TRAVAIL", sT))
    e.append(Paragraph("Article 21 de la loi du 3 juillet 1978 relative aux contrats de travail", 
                       ParagraphStyle('C', fontName=FN, fontSize=9, alignment=TA_CENTER)))
    e.append(Spacer(1, 0.8*cm))

    debut = c['date_debut'].strftime('%d/%m/%Y') if c.get('date_debut') else '—'
    fin = c['date_fin'].strftime('%d/%m/%Y') if c.get('date_fin') else date.today().strftime('%d/%m/%Y')

    e.append(Paragraph(
        f"Je soussigné(e), <b>{c.get('representant', '—')}</b>, représentant(e) de la société "
        f"<b>{c['dossier_nom']}</b>, certifie que :", sJ))
    e.append(Spacer(1, 0.4*cm))
    e.append(Paragraph(f"<b>M./Mme {c['prenom']} {c['nom']}</b>", sB))
    for label, val in [
        ("N° NISS :", c.get('niss', '—')),
        ("Adresse :", c.get('adresse', '—')),
        ("A été occupé(e) du :", f"{debut} au {fin}"),
        ("En qualité de :", c.get('fonction', '—')),
        ("Commission paritaire :", c.get('cp_key', '—')),
        ("Type de contrat :", c.get('type_contrat', '—')),
    ]:
        e.append(Paragraph(f"<b>{label}</b> {val}", sN))
    e.append(Spacer(1, 0.4*cm))
    e.append(Paragraph(
        "Ce certificat est délivré conformément à l'article 21 de la loi du 3 juillet 1978 "
        "relative aux contrats de travail. Il ne peut contenir aucune autre mention, "
        "sauf à la demande expresse du travailleur.", sJ))
    e.append(Spacer(1, 1*cm))
    e.append(Paragraph(f"Fait à _____________________, le {date.today().strftime('%d/%m/%Y')}", sN))
    e.append(Spacer(1, 1.5*cm))
    e.append(Paragraph("_______________________", sN))
    e.append(Paragraph(f"{c.get('representant', '—')}", sN))
    e.append(Paragraph(f"{c['dossier_nom']}", sN))

    doc.build(e, **pdf_decor())
    return send_file(filepath, as_attachment=False, download_name=filename, mimetype='application/pdf')


def generer_c4(c, form):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    try:
        pdfmetrics.registerFont(TTFont('DVSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
        pdfmetrics.registerFont(TTFont('DVSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
        FN, FNB = 'DVSans', 'DVSans-Bold'
    except:
        FN, FNB = 'Helvetica', 'Helvetica-Bold'

    NAVY = couleur('primaire')
    sN = ParagraphStyle('N', fontName=FN, fontSize=9, leading=13)
    sB = ParagraphStyle('B', fontName=FNB, fontSize=9, leading=13)
    sT = ParagraphStyle('T', fontName=FNB, fontSize=13, leading=18, alignment=TA_CENTER)

    filename = f"C4_{c['nom']}_{c['prenom']}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4,
        topMargin=1.5*cm, bottomMargin=1.5*cm, leftMargin=2*cm, rightMargin=2*cm)
    e = []

    e.append(Paragraph("FORMULAIRE C4 — CERTIFICAT DE CHOMAGE", sT))
    e.append(Paragraph("Arrêté royal du 25 novembre 1991 portant réglementation du chômage", 
                       ParagraphStyle('C', fontName=FN, fontSize=8, alignment=TA_CENTER)))
    e.append(Spacer(1, 0.3*cm))
    e.append(HRFlowable(width='100%', thickness=1.5, color=NAVY))
    e.append(Spacer(1, 0.4*cm))

    debut = c['date_debut'].strftime('%d/%m/%Y') if c.get('date_debut') else '—'
    fin = c['date_fin'].strftime('%d/%m/%Y') if c.get('date_fin') else date.today().strftime('%d/%m/%Y')
    motif = form.get('motif_fin', 'Fin de contrat à durée déterminée')
    salaire_ref = form.get('salaire_reference', '')
    if not salaire_ref:
        from psycopg2.extras import RealDictCursor as RDC2
        conn_ref = get_conn()
        cur_ref = conn_ref.cursor(cursor_factory=RDC2)
        cur_ref.execute("SELECT AVG(salaire_brut) as moy FROM fiches_paie WHERE travailleur_id=%s AND remplacee_par IS NULL",
                        (c['travailleur_id'],))
        row_ref = cur_ref.fetchone()
        cur_ref.close(); conn_ref.close()
        if row_ref and row_ref['moy']:
            salaire_ref = str(round(float(row_ref['moy']), 2))

    sections = [
        ("EMPLOYEUR", [
            ("Nom/Dénomination", c['dossier_nom']),
            ("Adresse", c.get('dossier_adresse', '—')),
            ("N° RSZ (ONSS)", c.get('rsz', '—')),
            ("BCE", c.get('bce', '—')),
            ("Commission paritaire", c.get('cp_key', '—')),
        ]),
        ("TRAVAILLEUR", [
            ("Nom et prénom", f"{c['nom']} {c['prenom']}"),
            ("N° NISS", c.get('niss', '—')),
            ("Adresse", c.get('adresse', '—')),
            ("Statut", "Ouvrier" if c.get('cp_key') and is_ouvrier(c.get('cp_key','')) else "Employé"),
        ]),
        ("OCCUPATION", [
            ("Date de début", debut),
            ("Date de fin", fin),
            ("Fonction", c.get('fonction', '—')),
            ("Type de contrat", c.get('type_contrat', '—')),
            ("Régime de travail", f"{float(c.get('heures_jour') or 7.6):.1f}h/jour × {int(c.get('jours_semaine') or 5)}j = {float(c.get('heures_jour') or 7.6) * int(c.get('jours_semaine') or 5):.1f}h/semaine"),
            ("Salaire de référence brut", f"{salaire_ref} EUR/mois" if salaire_ref else "Voir fiches de paie"),
        ]),
        ("FIN DU CONTRAT", [
            ("Motif de la fin", motif),
            ("Qui a mis fin", form.get('qui_fin', 'Employeur')),
            ("Préavis presté", form.get('preavis', 'Non applicable — CDD')),
        ]),
    ]

    for titre, lignes in sections:
        e.append(Paragraph(titre, sB))
        t_data = [[Paragraph(l, sN), Paragraph(v, sN)] for l, v in lignes]
        t = Table(t_data, colWidths=[6*cm, 10.5*cm])
        t.setStyle(TableStyle([
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LINEBELOW', (0,0), (-1,-2), 0.3, colors.HexColor('#eeeeee')),
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f9f9f9')),
        ]))
        e.append(t)
        e.append(Spacer(1, 0.3*cm))

    e.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#cccccc')))
    e.append(Spacer(1, 0.3*cm))
    e.append(Paragraph(
        "<b>Important :</b> Ce formulaire C4 doit être remis au travailleur au plus tard le dernier "
        "jour de travail, conformément à l'article 137 de l'AR du 25 novembre 1991. "
        "Le travailleur le remet à son organisme de paiement (CAPAC ou syndicat) pour demander "
        "ses allocations de chômage.", sN))
    e.append(Spacer(1, 0.5*cm))
    e.append(Paragraph(f"Fait à _____________________, le {date.today().strftime('%d/%m/%Y')}", sN))
    e.append(Spacer(1, 1*cm))
    sig = Table([[
        Paragraph("<b>Signature employeur</b>\n\n\n_______________________", 
                  ParagraphStyle('', fontName=FNB, fontSize=9)),
        Paragraph("<b>Signature travailleur</b>\n\n\n_______________________",
                  ParagraphStyle('', fontName=FNB, fontSize=9)),
    ]], colWidths=[8*cm, 8*cm])
    e.append(sig)

    doc.build(e, **pdf_decor())
    return send_file(filepath, as_attachment=False, download_name=filename, mimetype='application/pdf')


@app.route('/echeance/<int:echeance_id>/retablir', methods=['POST'])
@login_required
def retablir_echeance(echeance_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""UPDATE echeances SET statut='en_attente', date_realisation=NULL,
        document_path=NULL, document_nom=NULL, note=NULL, updated_at=NOW() WHERE id=%s""", (echeance_id,))
    conn.commit(); cur.close(); conn.close()
    return jsonlib.dumps({'ok': True})


@app.route('/dossier/<int:dossier_id>/lettres-onss')
@login_required
def liste_lettres_onss(dossier_id):
    from psycopg2.extras import RealDictCursor
    dossier = get_dossier(dossier_id)
    ctx = get_context_base()
    ctx['tenant'] = get_tenant()
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT * FROM lettres_onss WHERE dossier_id=%s ORDER BY annee DESC, mois DESC', (dossier_id,))
    lettres = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    MOIS_FR = ['','Janvier','Fevrier','Mars','Avril','Mai','Juin','Juillet','Aout','Septembre','Octobre','Novembre','Decembre']
    for l in lettres:
        l['mois_nom'] = MOIS_FR[l['mois']]
    return render_template('liste_lettres_onss.html', dossier=dossier, dossier_actif=dossier, lettres=lettres, **ctx)

@app.route('/lettre-onss/<int:lettre_id>/download')
@login_required
def download_lettre_onss(lettre_id):
    from psycopg2.extras import RealDictCursor
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT * FROM lettres_onss WHERE id=%s', (lettre_id,))
    lettre = cur.fetchone()
    cur.close(); conn.close()
    if lettre and lettre['pdf_path']:
        path = lettre['pdf_path']
        if not os.path.isabs(path):
            path = os.path.join('/var/www/duxsalary', path)
        if os.path.exists(path):
            return send_file(path, as_attachment=True, download_name=os.path.basename(path))
    return "Fichier introuvable", 404


import secrets
import json as jsonlib

# ── GÉNÉRATION TOKEN PORTAIL CLIENT ──────────────────────────────────

@app.route('/dossier/<int:dossier_id>/portail', methods=['GET', 'POST'])
@login_required
def portail_client(dossier_id):
    from psycopg2.extras import RealDictCursor
    dossier = get_dossier(dossier_id)
    ctx = get_context_base()
    ctx['tenant'] = get_tenant()
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'generer':
            token = secrets.token_urlsafe(32)
            cur.execute("""INSERT INTO portail_clients (dossier_id, token) 
                VALUES (%s, %s) ON CONFLICT DO NOTHING RETURNING token""", (dossier_id, token))
            conn.commit()
        elif action == 'desactiver':
            cur.execute("UPDATE portail_clients SET actif=FALSE WHERE dossier_id=%s", (dossier_id,))
            conn.commit()
        elif action == 'reactiver':
            cur.execute("UPDATE portail_clients SET actif=TRUE WHERE dossier_id=%s", (dossier_id,))
            conn.commit()
        cur.close(); conn.close()
        return redirect(url_for('portail_client', dossier_id=dossier_id))
    
    cur.execute("SELECT * FROM portail_clients WHERE dossier_id=%s ORDER BY created_at DESC LIMIT 1", (dossier_id,))
    portail = cur.fetchone()
    cur.execute("SELECT * FROM portail_demandes WHERE dossier_id=%s ORDER BY created_at DESC", (dossier_id,))
    demandes = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    
    base_url = request.host_url.rstrip('/')
    return render_template('portail_client.html', dossier=dossier, dossier_actif=dossier,
                           portail=portail, demandes=demandes, base_url=base_url, **ctx)


@app.route('/portail/<token>')
def portail_public(token):
    from psycopg2.extras import RealDictCursor
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""SELECT p.*, d.nom as dossier_nom, d.adresse as dossier_adresse
        FROM portail_clients p JOIN dossiers d ON d.id = p.dossier_id
        WHERE p.token = %s AND p.actif = TRUE""", (token,))
    portail = cur.fetchone()
    if not portail:
        cur.close(); conn.close()
        return render_template('portail_invalide.html'), 404
    cur.execute("UPDATE portail_clients SET last_access=NOW() WHERE token=%s", (token,))
    conn.commit()
    cur.execute("SELECT * FROM portail_demandes WHERE dossier_id=%s AND statut='en_attente' ORDER BY created_at DESC", (portail['dossier_id'],))
    demandes = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return render_template('portail_public.html', portail=portail, token=token, demandes=demandes)


@app.route('/portail/<token>/nouveau-travailleur', methods=['GET', 'POST'])
def portail_nouveau_travailleur(token):
    from psycopg2.extras import RealDictCursor
    import smtplib, ssl, os
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from dotenv import load_dotenv
    load_dotenv('/var/www/duxsalary/.env')
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""SELECT p.*, d.nom as dossier_nom FROM portail_clients p 
        JOIN dossiers d ON d.id = p.dossier_id WHERE p.token=%s AND p.actif=TRUE""", (token,))
    portail = cur.fetchone()
    cur.close(); conn.close()
    if not portail:
        return render_template('portail_invalide.html'), 404
    
    if request.method == 'POST':
        data = dict(request.form)
        # Construire le corps de l'email
        lines = [f"<h2>Nouvelle déclaration travailleur — {portail['dossier_nom']}</h2>"]
        sections = {
            'Informations personnelles': ['nom','prenom','initiale2','adresse','code_postal','localite','pays','email','niss','date_naissance','lieu_naissance','nationalite','date_entree','iban','sexe','langue','diplome'],
            'Situation familiale': ['etat_civil','partenaire_depuis','partenaire_revenus_pro','partenaire_pensions','nb_enfants_sans_handicap','nb_enfants_avec_handicap','nb_personnes_charge_66'],
            'Données contractuelles': ['statut','duree_contrat','date_sortie','lieu_occupation','fonction','cp','classification','heures_semaine','heures_jour','jours_semaine','type_horaire','h_lundi','h_mardi','h_mercredi','h_jeudi','h_vendredi','h_samedi','risque_at'],
            'Données salariales': ['salaire_brut','salaire_unite','km_voiture','km_velo','km_commun','transport_train','transport_sncb','transport_stib','transport_delijn','transport_mtb','cheques_repas','cr_valeur','cr_employeur','cr_travailleur','frais_nets','avantage_nature','avantage_montant','voiture_societe','voiture_plaque','voiture_valeur','voiture_co2','voiture_carburant'],
            'Réductions & Compléments': ['reduction_activa','reduction_premier_emploi','reduction_premier_engagement','reduction_autre','num_dimona','date_debut_dimona','remarques'],
        }
        for section, fields in sections.items():
            lines.append(f"<h3 style='color:#1F4E79;border-bottom:1px solid #ddd;padding-bottom:6px;margin-top:20px'>{section}</h3>")
            lines.append("<table style='width:100%;border-collapse:collapse'>")
            for f in fields:
                val = data.get(f, '')
                if val and val not in ['0','']:
                    lines.append(f"<tr><td style='padding:6px 12px;background:#f5f7fa;font-weight:600;width:40%'>{f.replace('_',' ').title()}</td><td style='padding:6px 12px;border-bottom:1px solid #eee'>{val}</td></tr>")
            lines.append("</table>")
        
        body = ''.join(lines)
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"[DuxSalary] Nouveau travailleur — {portail['dossier_nom']} — {data.get('prenom','')} {data.get('nom','')}"
        msg['From'] = os.getenv('SMTP_FROM', 'info@duxsalary.be')
        msg['To'] = os.getenv('NOTIFY_EMAIL', 'info@duxsalary.be')
        msg.attach(MIMEText(body, 'html'))
        
        try:
            with smtplib.SMTP(os.getenv('SMTP_HOST','ex2.mail.ovh.net'), int(os.getenv('SMTP_PORT',587))) as server:
                server.starttls()
                server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD'))
                server.sendmail(msg['From'], msg['To'], msg.as_string())
        except Exception as ex:
            app.logger.error(f"Email portail error: {ex}")
            # Fallback: sauvegarder en BDD si email échoue
            try:
                conn2 = get_conn()
                cur2 = conn2.cursor()
                cur2.execute("""INSERT INTO portail_demandes (dossier_id, token, type_demande, data, statut, notes)
                    VALUES (%s, %s, 'nouveau_travailleur', %s, 'en_attente', 'Email échoué - à traiter manuellement')""",
                    (portail['dossier_id'], token, jsonlib.dumps(data)))
                conn2.commit(); cur2.close(); conn2.close()
            except: pass
        
        return render_template('portail_confirmation.html', portail=portail, token=token)
    
    return render_template('portail_formulaire.html', portail=portail, token=token)


@app.route('/dossier/<int:dossier_id>/portail/demande/<int:demande_id>', methods=['GET', 'POST'])
@login_required
def traiter_demande(dossier_id, demande_id):
    from psycopg2.extras import RealDictCursor
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM portail_demandes WHERE id=%s AND dossier_id=%s", (demande_id, dossier_id))
    demande = cur.fetchone()
    if not demande:
        cur.close(); conn.close()
        return "Introuvable", 404
    
    data = demande['data'] if isinstance(demande['data'], dict) else jsonlib.loads(demande['data'])
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'valider':
            cur.execute("UPDATE portail_demandes SET statut='traite', traite_at=NOW() WHERE id=%s", (demande_id,))
            conn.commit()
        elif action == 'rejeter':
            cur.execute("UPDATE portail_demandes SET statut='rejete', traite_at=NOW(), notes=%s WHERE id=%s",
                       (request.form.get('notes', ''), demande_id))
            conn.commit()
        cur.close(); conn.close()
        return redirect(url_for('portail_client', dossier_id=dossier_id))
    
    cur.close(); conn.close()
    dossier = get_dossier(dossier_id)
    ctx = get_context_base(); ctx['tenant'] = get_tenant()
    return render_template('portail_demande.html', demande=demande, data=data,
                           dossier=dossier, dossier_actif=dossier, **ctx)

# ── GESTION DES CONGES ────────────────────────────────────────────────
@app.route('/travailleur/<int:travailleur_id>/conges', methods=['GET', 'POST'])
@login_required
def conges_travailleur(travailleur_id):
    from psycopg2.extras import RealDictCursor
    from conges_legaux import jours_conges_acquis, double_pecule_employe, pecule_ouvrier_information
    from datetime import date as _d

    travailleur = get_travailleur(travailleur_id)
    dossier = get_dossier(travailleur['dossier_id'])
    ctx = get_context_base(); ctx['tenant'] = get_tenant()

    conn = get_conn(); cur = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == 'POST':
        annee = int(request.form['annee_vacances'])
        mois_ref = int(request.form.get('mois_prestes_reference', 0) or 0)
        jours_sem = float(request.form.get('jours_semaine_reference', 5) or 5)
        jours_pris = float(request.form.get('jours_pris', 0) or 0)
        pecule_verse = float(request.form.get('double_pecule_verse', 0) or 0)
        date_vers = request.form.get('date_versement_pecule') or None
        notes = request.form.get('notes', '')

        # Determiner le statut pour le calcul
        cur.execute("""SELECT type_contrat, cp_key FROM contrats
            WHERE travailleur_id=%s AND statut='actif'
            ORDER BY date_debut DESC LIMIT 1""", (travailleur_id,))
        c = cur.fetchone()
        cp_key = (c['cp_key'] if c else None) or travailleur.get('cp_key') or 'CP 200'
        try:
            from regles_cp import get_regles_cp
            statut = get_regles_cp(cp_key).get('type_travailleur_defaut', 'employe')
        except Exception:
            statut = 'employe'

        jours_acquis = jours_conges_acquis(statut, jours_sem, mois_ref)

        cur.execute("""INSERT INTO conges_droits
            (travailleur_id, annee_vacances, mois_prestes_reference,
             jours_semaine_reference, jours_acquis, jours_pris,
             double_pecule_verse, date_versement_pecule, notes, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
            ON CONFLICT (travailleur_id, annee_vacances)
            DO UPDATE SET mois_prestes_reference=EXCLUDED.mois_prestes_reference,
                jours_semaine_reference=EXCLUDED.jours_semaine_reference,
                jours_acquis=EXCLUDED.jours_acquis,
                jours_pris=EXCLUDED.jours_pris,
                double_pecule_verse=EXCLUDED.double_pecule_verse,
                date_versement_pecule=EXCLUDED.date_versement_pecule,
                notes=EXCLUDED.notes, updated_at=NOW()""",
            (travailleur_id, annee, mois_ref, jours_sem, jours_acquis,
             jours_pris, pecule_verse, date_vers, notes))
        conn.commit()
        cur.close(); conn.close()
        return redirect(url_for('conges_travailleur', travailleur_id=travailleur_id))

    # GET: charger l'historique
    cur.execute("""SELECT * FROM conges_droits WHERE travailleur_id=%s
        ORDER BY annee_vacances DESC""", (travailleur_id,))
    historique = [dict(r) for r in cur.fetchall()]

    # CALCUL AUTOMATIQUE des mois ouvrant droit, depuis les contrats reels
    cur.execute("""SELECT id, type_contrat, statut, date_debut, date_fin
        FROM contrats WHERE travailleur_id=%s ORDER BY date_debut""", (travailleur_id,))
    tous_contrats = [dict(r) for r in cur.fetchall()]
    from conges_legaux import calculer_mois_depuis_contrats
    calcul_auto = {}
    for annee_vac in (_d.today().year, _d.today().year + 1):
        calcul_auto[annee_vac] = calculer_mois_depuis_contrats(tous_contrats, annee_vac - 1)

    # Contrat actif pour determiner statut + salaire
    cur.execute("""SELECT type_contrat, cp_key, salaire_horaire, salaire_mensuel,
        heures_jour, jours_semaine FROM contrats
        WHERE travailleur_id=%s AND statut='actif'
        ORDER BY date_debut DESC LIMIT 1""", (travailleur_id,))
    contrat = cur.fetchone()
    cur.close(); conn.close()

    cp_key = (contrat['cp_key'] if contrat else None) or travailleur.get('cp_key') or 'CP 200'
    try:
        from regles_cp import get_regles_cp
        regles = get_regles_cp(cp_key)
        statut = regles.get('type_travailleur_defaut', 'employe')
    except Exception:
        statut = 'employe'
    is_etudiant_contrat = bool(contrat and contrat['type_contrat'] == 'STU')

    # Estimation pecule pour l'annee en cours (informatif)
    estimation = None
    annee_courante = _d.today().year
    ligne_courante = next((h for h in historique if h['annee_vacances'] == annee_courante), None)
    if ligne_courante and ligne_courante['mois_prestes_reference']:
        if statut == 'employe' and not is_etudiant_contrat:
            sal_mensuel = 0.0
            if contrat:
                if contrat.get('salaire_mensuel'):
                    sal_mensuel = float(contrat['salaire_mensuel'])
                elif contrat.get('salaire_horaire'):
                    hs = float(contrat.get('heures_jour') or 7.6) * int(contrat.get('jours_semaine') or 5)
                    sal_mensuel = round(float(contrat['salaire_horaire']) * hs * 52 / 12, 2)
            estimation = {
                'type': 'employe',
                'double_pecule': double_pecule_employe(sal_mensuel, ligne_courante['mois_prestes_reference']),
                'salaire_base': sal_mensuel,
            }

    return render_template('conges_travailleur.html',
        travailleur=travailleur, dossier=dossier, dossier_actif=dossier,
        historique=historique, statut=statut, cp_key=cp_key,
        is_etudiant_contrat=is_etudiant_contrat, calcul_auto=calcul_auto,
        estimation=estimation, annee_courante=annee_courante, **ctx)

# ── DOCUMENTS DE CHARGES SALARIALES ─────────────────────────────────────
# Compte individuel, attestation salariale, liste de ventilation: calculs dans
# documents_charges.py, PDF dans pdf_charges.py, identite visuelle dans branding.py
def _periode_demandee():
    """Periode choisie (parametres date_debut / date_fin, ou annee) -- par defaut l'annee en cours."""
    annee = request.args.get('annee', type=int) or date.today().year
    def lire(nom, defaut):
        try:
            return date.fromisoformat(request.args.get(nom) or '')
        except ValueError:
            return defaut
    debut, fin = lire('date_debut', date(annee, 1, 1)), lire('date_fin', date(annee, 12, 31))
    return (debut, fin) if debut <= fin else (fin, debut)


def _fiches_periode(condition, parametre, debut, fin):
    from psycopg2.extras import RealDictCursor
    conn = get_conn(); cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(f"""SELECT * FROM fiches_paie WHERE {condition} = %s
                    AND periode_debut >= %s AND periode_debut <= %s AND remplacee_par IS NULL ORDER BY periode_debut""",
                (parametre, debut, fin))
    fiches = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return fiches


def _rendre_document(document, debut, fin, nom_fichier, retour_url, retour_libelle, onglets, **contexte):
    from documents_charges import formater
    tenant = get_tenant()
    if request.args.get('format') == 'pdf':
        from io import BytesIO
        from pdf_charges import generer_pdf_charges
        return send_file(BytesIO(generer_pdf_charges(document, tenant)), mimetype='application/pdf',
                         as_attachment=False, download_name=f"{nom_fichier}_{debut:%Y%m%d}_{fin:%Y%m%d}.pdf")
    ctx = get_context_base(); ctx['tenant'] = tenant
    return render_template('document_charges.html', document=document, formater=formater,
                           date_debut=debut.isoformat(), date_fin=fin.isoformat(),
                           retour_url=retour_url, retour_libelle=retour_libelle, onglets=onglets,
                           **contexte, **ctx)


def _document_dossier(dossier_id, type_document):
    from documents_charges import attestation_salariale, liste_ventilation
    dossier = get_dossier(dossier_id)
    debut, fin = _periode_demandee()
    fiches = _fiches_periode('dossier_id', dossier_id, debut, fin)
    construire = liste_ventilation if type_document == 'ventilation' else attestation_salariale
    onglets = [{'libelle': 'Attestation salariale', 'url': f'/dossier/{dossier_id}/resume-charge',
                'actif': type_document == 'attestation'},
               {'libelle': 'Liste de ventilation', 'url': f'/dossier/{dossier_id}/ventilation',
                'actif': type_document == 'ventilation'}]
    return _rendre_document(construire(fiches, dossier, debut, fin), debut, fin, type_document,
                            f'/dossier/{dossier_id}', dossier['nom'], onglets,
                            dossier=dossier, dossier_actif=dossier)


@app.route('/dossier/<int:dossier_id>/resume-charge')
@login_required
def resume_charge(dossier_id):
    return _document_dossier(dossier_id, 'attestation')


@app.route('/dossier/<int:dossier_id>/ventilation')
@login_required
def liste_ventilation_dossier(dossier_id):
    return _document_dossier(dossier_id, 'ventilation')


# ── AIDE A LA DmfA (regroupement trimestriel a recopier dans la DmfA web) ─────
@app.route('/dossier/<int:dossier_id>/aide-dmfa')
@login_required
def aide_dmfa_dossier(dossier_id):
    from psycopg2.extras import RealDictCursor
    from dmfa import aide_dmfa, bornes_trimestre, jours_du_calendrier, trimestre_de
    dossier = get_dossier(dossier_id)
    # Par defaut: le dernier trimestre termine
    a_def, q_def = trimestre_de(date.today())
    a_def, q_def = (a_def, q_def - 1) if q_def > 1 else (a_def - 1, 4)
    annee = request.args.get('annee', type=int) or a_def
    trimestre = request.args.get('trimestre', type=int) or q_def
    trimestre = min(4, max(1, trimestre))
    debut_t, fin_t = bornes_trimestre(annee, trimestre)
    conn = get_conn(); cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT * FROM travailleurs WHERE dossier_id = %s ORDER BY nom, prenom', (dossier_id,))
    travailleurs, alertes_lecture = [], []
    for trav in [dict(r) for r in cur.fetchall()]:
        cur.execute('SELECT * FROM contrats WHERE travailleur_id = %s', (trav['id'],))
        contrats = [dict(r) for r in cur.fetchall()]
        cur.execute("""SELECT * FROM fiches_paie WHERE travailleur_id = %s AND periode_debut >= %s AND periode_debut <= %s
                       AND remplacee_par IS NULL ORDER BY periode_debut""", (trav['id'], debut_t, fin_t))
        fiches = [dict(r) for r in cur.fetchall()]
        cur.execute("""SELECT date_prestation, code_journee, heures FROM prestations
                       WHERE travailleur_id = %s AND date_prestation BETWEEN %s AND %s""", (trav['id'], debut_t, fin_t))
        lignes = [dict(r) for r in cur.fetchall()]
        par_date = None
        try:
            par_date = _contexte_incapacites(cur, trav['id'], fin_t)['par_date']
        except Exception as ex_inc:
            conn.rollback()
            if not alertes_lecture:
                alertes_lecture.append(f"Incapacités non lues ({ex_inc}) : les jours de maladie sont à déterminer. "
                                       f"Lancez python3 migrate_charges.py si la table n'existe pas.")
        travailleurs.append({'travailleur': trav, 'contrats': contrats, 'fiches': fiches,
                             'jours': jours_du_calendrier(lignes, par_date)})
    cur.close(); conn.close()
    document = aide_dmfa(dossier, annee, trimestre, travailleurs)
    document['alertes'] = alertes_lecture + document['alertes']
    tenant = get_tenant()
    if request.args.get('format') == 'pdf':
        from io import BytesIO
        from pdf_dmfa import generer_pdf_dmfa
        return send_file(BytesIO(generer_pdf_dmfa(document, tenant)), mimetype='application/pdf', as_attachment=False,
                         download_name=f"aide_dmfa_{annee}_T{trimestre}.pdf")
    ctx = get_context_base(); ctx['tenant'] = tenant
    return render_template('aide_dmfa.html', document=document, dossier=dossier, dossier_actif=dossier, **ctx)


@app.route('/travailleur/<int:travailleur_id>/compte-individuel')
@login_required
def compte_individuel(travailleur_id):
    from documents_charges import compte_individuel as construire
    travailleur = get_travailleur(travailleur_id)
    dossier = get_dossier(travailleur['dossier_id'])
    debut, fin = _periode_demandee()
    fiches = _fiches_periode('travailleur_id', travailleur_id, debut, fin)
    # Tous les contrats du travailleur (meme termines): la date d'entree est celle
    # de la premiere occupation, contrat etudiant compris
    from psycopg2.extras import RealDictCursor
    from occupation import contrat_de_la_periode, date_premiere_occupation
    conn = get_conn(); cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT * FROM contrats WHERE travailleur_id = %s ORDER BY date_debut', (travailleur_id,))
    contrats = [dict(c) for c in cur.fetchall()]
    cur.close(); conn.close()
    contrat = contrat_de_la_periode(contrats, debut, fin) or (contrats[-1] if contrats else None)
    document = construire(fiches, travailleur, dossier, debut, fin, contrat=contrat,
                          date_entree=date_premiere_occupation(contrats))
    return _rendre_document(document, debut, fin, 'compte_individuel',
                            f'/travailleur/{travailleur_id}', f"{travailleur['prenom']} {travailleur['nom']}", [],
                            travailleur=travailleur, dossier=dossier, dossier_actif=dossier)


# ── SUIVI DES CHEQUES (cheques-repas + ecocheques) ────────────────────
def _config_cheques(cur, dossier_id):
    cur.execute("SELECT * FROM cheques_config WHERE dossier_id=%s", (dossier_id,))
    r = cur.fetchone()
    r = dict(r) if r else {}
    return {'actif': bool(r.get('repas_actif')), 'valeur': r.get('repas_valeur'),
            'part_patronale': r.get('repas_part_patronale'), 'part_travailleur': r.get('repas_part_travailleur'),
            'octroi_avant_2025': bool(r.get('repas_octroi_avant_2025')),
            'repas_fournis': bool(r.get('repas_fournis')),
            'eco_actif': bool(r.get('eco_actif')), 'eco_convertis': bool(r.get('eco_convertis')),
            'emetteur': r.get('emetteur') or '', 'notes': r.get('notes') or ''}


def _calcul_cheques_travailleur(cur, t, annee, mois, config):
    """Cheques-repas du mois + ecocheques previsionnels pour un travailleur."""
    import calendar
    from cheques_regles import cheques_repas_du_mois, ecocheques_annuels, regles_pour
    from regles_cp import get_regles_cp
    debut_m = date(annee, mois, 1)
    fin_m = date(annee, mois, calendar.monthrange(annee, mois)[1])
    cur.execute("SELECT * FROM contrats WHERE travailleur_id=%s AND statut='actif' ORDER BY date_debut", (t['id'],))
    contrats = [dict(x) for x in cur.fetchall()]
    couvrant = [c for c in contrats if c['date_debut'] and c['date_debut'] <= fin_m
                and (c['date_fin'] is None or c['date_fin'] >= debut_m)]
    contrat = couvrant[-1] if couvrant else (contrats[-1] if contrats else None)
    if not contrat:
        return None
    cp_key = contrat.get('cp_key') or t.get('cp_key') or ''
    if contrat.get('type_contrat') == 'STU':
        statut = 'etudiant'
    else:
        try:
            statut = get_regles_cp(cp_key).get('type_travailleur_defaut', 'employe')
        except Exception:
            statut = 'employe'
    cur.execute("""SELECT code_journee, heures FROM prestations WHERE travailleur_id=%s
                   AND date_prestation BETWEEN %s AND %s""", (t['id'], debut_m, fin_m))
    prest = cur.fetchall()
    jours = sum(1 for p in prest if p['code_journee'] in ('P', 'S', 'HS', 'PP'))
    heures = float(sum(p['heures'] or 0 for p in prest if p['code_journee'] in ('P', 'S', 'HS', 'PP')))
    date_anc = min(c['date_debut'] for c in contrats if c['date_debut'])
    repas = cheques_repas_du_mois(cp_key, statut, annee, mois, jours, heures, date_anc, config)

    # Ecocheques: prochaine echeance et prorata sur la periode de reference
    eco = None
    regle_eco = regles_pour(cp_key, date(annee, 6, 30))['eco']
    if regle_eco:
        mp = regle_eco['mois_paiement']
        n = annee if mois <= mp else annee + 1
        if mp == 6:   # CP 200: juin N-1 -> mai N
            p_deb, p_fin = date(n - 1, 6, 1), date(n, 5, 31)
        else:         # paiement annuel: annee civile N
            p_deb, p_fin = date(n, 1, 1), date(n, 12, 31)
        mois_couverts = set()
        for c in contrats:
            if c.get('type_contrat') == 'STU' or not c['date_debut']:
                continue
            d0, d1 = max(c['date_debut'], p_deb), min(c['date_fin'] or p_fin, p_fin)
            y, m = d0.year, d0.month
            while (y, m) <= (d1.year, d1.month):
                mois_couverts.add((y, m)); m += 1
                if m > 12: m, y = 1, y + 1
        hs = float(contrat.get('heures_semaine') or 38) or 38.0
        fraction = min(1.0, float(contrat.get('heures_jour') or 7.6) * int(contrat.get('jours_semaine') or 5) / hs)
        eco = ecocheques_annuels(cp_key, statut, n, fraction, len(mois_couverts),
                                 t.get('categorie_personnel'))
        eco.update(annee_paiement=n, periode=f"{p_deb:%m/%Y} – {p_fin:%m/%Y}", fraction_regime=round(fraction, 2),
                   mois_couverts=len(mois_couverts))
    return {'travailleur': t, 'contrat': contrat, 'cp_key': cp_key, 'statut': statut,
            'jours': jours, 'heures': heures, 'date_anciennete': date_anc, 'repas': repas, 'eco': eco}


@app.route('/dossier/<int:dossier_id>/cheques', methods=['GET', 'POST'])
@login_required
def suivi_cheques(dossier_id):
    from psycopg2.extras import RealDictCursor
    from cheques_regles import regles_pour, CADRE_LEGAL
    dossier = get_dossier(dossier_id)
    ctx = get_context_base(); ctx['tenant'] = get_tenant()
    annee = request.args.get('annee', date.today().year, type=int)
    mois = request.args.get('mois', date.today().month, type=int)
    conn = get_conn(); cur = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == 'POST':
        f = request.form
        def num(k):
            try: return float((f.get(k) or '').replace(',', '.')) if f.get(k) else None
            except ValueError: return None
        cur.execute("""INSERT INTO cheques_config (dossier_id, repas_actif, repas_valeur, repas_part_patronale,
                repas_part_travailleur, repas_octroi_avant_2025, eco_actif, eco_convertis, emetteur, notes,
                repas_fournis, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
            ON CONFLICT (dossier_id) DO UPDATE SET repas_actif=EXCLUDED.repas_actif, repas_valeur=EXCLUDED.repas_valeur,
                repas_part_patronale=EXCLUDED.repas_part_patronale, repas_part_travailleur=EXCLUDED.repas_part_travailleur,
                repas_octroi_avant_2025=EXCLUDED.repas_octroi_avant_2025, eco_actif=EXCLUDED.eco_actif,
                eco_convertis=EXCLUDED.eco_convertis, emetteur=EXCLUDED.emetteur, notes=EXCLUDED.notes,
                repas_fournis=EXCLUDED.repas_fournis, updated_at=NOW()""",
            (dossier_id, f.get('repas_actif') == 'on', num('repas_valeur'), num('repas_part_patronale'),
             num('repas_part_travailleur'), f.get('repas_octroi_avant_2025') == 'on', f.get('eco_actif') == 'on',
             f.get('eco_convertis') == 'on', f.get('emetteur', '')[:100], f.get('notes', ''),
             f.get('repas_fournis') == 'on'))
        for k, v in f.items():
            if k.startswith('categorie_personnel_') and k[20:].isdigit():
                cur.execute("UPDATE travailleurs SET categorie_personnel=%s WHERE id=%s AND dossier_id=%s",
                            (v or None, int(k[20:]), dossier_id))
        conn.commit(); cur.close(); conn.close()
        return redirect(url_for('suivi_cheques', dossier_id=dossier_id, annee=annee, mois=mois))

    config = _config_cheques(cur, dossier_id)
    cur.execute("SELECT * FROM travailleurs WHERE dossier_id=%s AND COALESCE(actif, TRUE) ORDER BY nom", (dossier_id,))
    lignes = [x for x in (_calcul_cheques_travailleur(cur, dict(t), annee, mois, config) for t in cur.fetchall()) if x]
    cur.close(); conn.close()

    cps = sorted({l['cp_key'] for l in lignes if l['cp_key']} | ({dossier.get('cp_principale')} - {None, ''}))
    regles = {cp: regles_pour(cp, date(annee, mois, 28)) for cp in cps}
    obligatoire_non_active = any(l['repas']['obligatoire'] for l in lignes) and not config['actif']
    tot = {'nombre': sum(l['repas']['nombre'] for l in lignes),
           'valeur': round(sum(l['repas'].get('total_valeur', 0) for l in lignes), 2),
           'patronal': round(sum(l['repas'].get('total_patronal', 0) for l in lignes), 2),
           'travailleur': round(sum(l['repas'].get('total_travailleur', 0) for l in lignes), 2)}
    suggestion = next((r['repas'] for r in regles.values() if r['repas']), None)
    mois_noms = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août',
                 'Septembre', 'Octobre', 'Novembre', 'Décembre']
    return render_template('cheques_dossier.html', dossier=dossier, dossier_actif=dossier, config=config,
                           lignes=lignes, regles=regles, tot=tot, annee=annee, mois=mois, mois_nom=mois_noms[mois],
                           obligatoire_non_active=obligatoire_non_active, suggestion=suggestion,
                           cadre=CADRE_LEGAL, **ctx)
