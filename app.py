from flask import Flask, render_template, request, send_file, session, redirect, url_for
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_JUSTIFY
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
                           fiches=get_fiches_paie(dossier_id=dossier_id), **ctx)

@app.route('/dossier/<int:dossier_id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier_dossier(dossier_id):
    dossier = get_dossier(dossier_id)
    ctx = get_context_base()
    ctx['tenant'] = get_tenant()
    if request.method == 'POST':
        update_dossier(dossier_id, request.form)
        return redirect(url_for('dossier_dashboard', dossier_id=dossier_id))
    return render_template('modifier_dossier.html', dossier=dossier, dossier_actif=dossier, **ctx)

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
        return redirect(url_for('fiche_travailleur', travailleur_id=tid))
    return render_template('nouveau_travailleur.html', dossier=dossier, dossier_actif=dossier, cp_keys=list(CP_DATABASE.keys()), **ctx)

@app.route('/travailleur/<int:travailleur_id>')
@login_required
def fiche_travailleur(travailleur_id):
    travailleur = get_travailleur(travailleur_id)
    dossier = get_dossier(travailleur['dossier_id'])
    ctx = get_context_base()
    ctx['tenant'] = get_tenant()
    tab = request.args.get('tab', 'info')
    documents = get_documents_travailleur(travailleur_id)
    return render_template('fiche_travailleur.html',
                           travailleur=travailleur, dossier=dossier, dossier_actif=dossier,
                           tab=tab, contrats=get_contrats(travailleur_id=travailleur_id),
                           fiches=get_fiches_paie(travailleur_id=travailleur_id),
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
            adresse=%s, iban=%s, email=%s, telephone=%s, langue=%s WHERE id=%s""",
            (request.form['prenom'], request.form['nom'], request.form.get('niss'),
             ddn_db, request.form.get('adresse'), request.form.get('iban'),
             request.form.get('email'), request.form.get('telephone'),
             request.form.get('langue', 'fr'), travailleur_id))
        conn.commit(); cur.close(); conn.close()
        return redirect(url_for('fiche_travailleur', travailleur_id=travailleur_id))
    return render_template('modifier_travailleur.html', travailleur=travailleur, dossier=dossier, dossier_actif=dossier, cp_keys=list(CP_DATABASE.keys()), **ctx)

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
        cur.execute("""INSERT INTO dimona (dossier_id, travailleur_id, type_dimona, date_debut, date_fin, numero_reference, notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (travailleur['dossier_id'], travailleur_id, form['type_dimona'], form['date_debut'],
             form.get('date_fin') or None, form.get('numero_reference') or None, form.get('notes') or None))
        did = cur.fetchone()[0]
        conn.commit(); cur.close(); conn.close()
        return redirect(url_for('calendrier_prestations', dimona_id=did))
    return render_template('nouvelle_dimona.html', travailleur=travailleur, dossier=dossier, dossier_actif=dossier, **ctx)

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
    prests_dict = {row['date_prestation']: dict(row) for row in cur.fetchall()}
    cur.close(); conn.close()

    jours_feries = get_jours_feries(annee)
    _, nb_jours = calendar.monthrange(annee, mois)
    premier_jour = date(annee, mois, 1)
    premier_jour_semaine = premier_jour.weekday()

    jours = []
    stats = {'jours_prestes': 0, 'heures_prestees': 0, 'jours_conge': 0,
             'jours_maladie': 0, 'jours_ferie': 0, 'jours_chomage': 0, 'jours_cnp': 0}

    date_debut_dimona = dimona['date_debut']
    date_fin_dimona = dimona['date_fin']
    heures_jour = get_heures_semaine(dossier.get('cp_principale', 'CP 336')) / 5

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
        elif code in ['MA','AC']: stats['jours_maladie'] += 1
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
                           heures_jour=round(heures_jour, 2), **ctx)

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
    cp_json = jsonlib.dumps({k: {'meta': v['meta'], 'duree_travail': v['duree_travail'],
        'baremes': {cat: {kk: vv for kk, vv in val.items() if kk in ['horaire','mensuel','fonctions']}
                    for cat, val in v['baremes'].items() if isinstance(val, dict)}}
        for k, v in CP_DATABASE.items()})
    prefill_travailleur_id = request.args.get('travailleur_id', type=int)

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
                           prefill_contrat=prefill_contrat, **ctx)

# ── FICHES DE PAIE ────────────────────────────────────────────────────
def calcul_paie_etudiant(salaire_horaire, heures_jour, nb_jours, transport=None):
    heures_totales = round(heures_jour * nb_jours, 2)
    brut = round(salaire_horaire * heures_totales, 2)
    onss_personnel = round(brut * 0.0271, 2)
    transport_montant = transport['montant'] if transport else 0
    net = round(brut - onss_personnel + transport_montant, 2)
    onss_patronal = round(brut * 0.0542, 2)
    return {'heures_totales': heures_totales, 'nb_jours': nb_jours, 'brut': brut,
            'onss_personnel': onss_personnel, 'net': net, 'onss_patronal': onss_patronal,
            'cout_employeur': round(brut + onss_patronal + transport_montant, 2),
            'total_onss': round(onss_personnel + onss_patronal, 2),
            'transport_montant': transport_montant}

def generer_fiche_paie(data, calcul):
    filename = f"fiche_{data.get('nom_etudiant','').replace(' ','_')}_{data.get('date_debut','').replace('/','')}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)
    from reportlab.platypus import KeepTogether
    BLUE = colors.HexColor('#1F4E79')
    DARK = colors.HexColor('#1a1a1a')
    GREY_BG = colors.HexColor('#f5f5f5')
    GREY_LINE = colors.HexColor('#cccccc')
    sN = ParagraphStyle('sN', fontName='Helvetica', fontSize=8, leading=11, textColor=DARK)
    sB = ParagraphStyle('sB', fontName='Helvetica-Bold', fontSize=8, leading=11, textColor=DARK)
    sRB = ParagraphStyle('sRB', fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=DARK, alignment=TA_RIGHT)
    sCB = ParagraphStyle('sCB', fontName='Helvetica-Bold', fontSize=8, leading=11, textColor=DARK, alignment=TA_CENTER)
    sTitle = ParagraphStyle('sTitle', fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=colors.white, alignment=TA_RIGHT)
    sSub = ParagraphStyle('sSub', fontName='Helvetica', fontSize=7.5, leading=10, textColor=colors.HexColor('#555555'))

    doc = SimpleDocTemplate(filepath, pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm, leftMargin=1.8*cm, rightMargin=1.8*cm)
    elements = []

    header = Table([[
        Table([[Paragraph(f"<b>{data.get('nom_societe','')}</b>", sB)],
               [Paragraph(data.get('adresse_societe',''), sN)],
               [Paragraph(f"BCE : {data.get('bce_societe','')}  |  N° RSZ : {data.get('rsz_societe','')}", sN)]],
              colWidths=[9*cm], style=[('TOPPADDING',(0,0),(-1,-1),1),('BOTTOMPADDING',(0,0),(-1,-1),1)]),
        Table([[Paragraph("DÉCOMPTE DE RÉMUNÉRATION", sTitle)],
               [Paragraph(f"Période du {data.get('date_debut','')} au {data.get('date_fin','')}", ParagraphStyle('',fontName='Helvetica',fontSize=8,textColor=colors.white,alignment=TA_RIGHT))]],
              colWidths=[8*cm], style=[('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2)])
    ]], colWidths=[9*cm, 8.4*cm])
    header.setStyle(TableStyle([('BACKGROUND',(1,0),(1,0),BLUE),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('LEFTPADDING',(1,0),(1,0),8),('RIGHTPADDING',(1,0),(1,0),8),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
    elements.append(header)
    elements.append(Spacer(1, 0.3*cm))

    table_data = [
        ['Code', 'Description', 'Jours', 'Heures', 'Montants'],
        ['1100', 'Salaire de base', str(calcul['nb_jours']), f"{calcul['heures_totales']}h", f"{calcul['brut']:.2f}"],
        ['', Paragraph('<b>Montant brut</b>', sB), '', '', Paragraph(f"<b>{calcul['brut']:.2f}</b>", sRB)],
        ['2500', f"Cotisation ONSS ({100*0.0271:.2f}%)", '', '', f"-{calcul['onss_personnel']:.2f}"],
        ['', Paragraph('<b>Imposable</b>', sB), '', '', Paragraph(f"<b>{calcul['brut']-calcul['onss_personnel']:.2f}</b>", sRB)],
        ['3000', 'Précompte professionnel', '', '', '0,00'],
        ['', Paragraph('<b>Salaire net</b>', sB), '', '', Paragraph(f"<b>{calcul['net']:.2f}</b>", sRB)],
    ]
    pt = Table(table_data, colWidths=[1.2*cm, 10*cm, 1.5*cm, 1.8*cm, 2.9*cm])
    pt.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),DARK),('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),8),
        ('ALIGN',(2,0),(-1,-1),'RIGHT'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,GREY_BG]),
        ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
        ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
        ('BACKGROUND',(0,2),(-1,2),colors.HexColor('#e8e8e8')),
        ('BACKGROUND',(0,4),(-1,4),colors.HexColor('#e8e8e8')),
        ('BACKGROUND',(0,-1),(-1,-1),DARK),('TEXTCOLOR',(0,-1),(-1,-1),colors.white),
        ('FONTNAME',(0,-1),(-1,-1),'Helvetica-Bold'),('GRID',(0,0),(-1,-1),0.3,GREY_LINE),
    ]))
    elements.append(pt)
    elements.append(Spacer(1, 0.3*cm))
    net_box = Table([[Paragraph("net reporté", sSub),
        Paragraph(f"€ {calcul['net']:.2f}", ParagraphStyle('',fontName='Helvetica-Bold',fontSize=10,alignment=TA_RIGHT,textColor=DARK))]],
        colWidths=[14*cm, 3.4*cm])
    net_box.setStyle(TableStyle([('LINEABOVE',(0,0),(-1,0),1,DARK),('LINEBELOW',(0,0),(-1,0),1,DARK),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    elements.append(net_box)
    doc.build(elements)
    return filepath, filename

@app.route('/dossier/<int:dossier_id>/fiche/nouvelle', methods=['GET', 'POST'])
@login_required
def nouvelle_fiche(dossier_id):
    dossier = get_dossier(dossier_id)
    travailleurs = get_travailleurs(dossier_id)
    ctx = get_context_base()
    ctx['tenant'] = get_tenant()
    prefill_travailleur_id = request.args.get('travailleur_id', type=int)

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
            'nom_etudiant': f"{travailleur['prenom']} {travailleur['nom']}",
            'niss_etudiant': travailleur['niss'] or '',
            'date_debut': form['date_debut'], 'date_fin': form['date_fin'],
            'salaire_horaire': str(salaire_horaire), 'transport': transport,
            'fonction': form.get('fonction', ''),
        }
        filepath, filename = generer_fiche_paie(data, calcul)

        def pd(d):
            if not d: return None
            try: p = d.split('/'); return f"{p[2]}-{p[1]}-{p[0]}"
            except: return None

        create_fiche_paie({'dossier_id': dossier_id, 'travailleur_id': travailleur_id, 'contrat_id': None,
            'periode_debut': pd(form['date_debut']), 'periode_fin': pd(form['date_fin']),
            'nb_jours': nb_jours, 'heures_totales': calcul['heures_totales'],
            'salaire_brut': calcul['brut'], 'onss_personnel': calcul['onss_personnel'],
            'precompte': 0, 'transport_montant': transport_montant,
            'salaire_net': calcul['net'], 'onss_patronal': calcul['onss_patronal'],
            'cout_employeur': calcul['cout_employeur'], 'total_onss': calcul['total_onss'],
            'pdf_path': os.path.join(OUTPUT_DIR, filename)})
        return redirect(url_for('fiche_travailleur', travailleur_id=travailleur_id, tab='fiches'))

    return render_template('nouvelle_fiche.html', dossier=dossier, dossier_actif=dossier,
                           travailleurs=travailleurs, prefill_travailleur_id=prefill_travailleur_id, **ctx)

# ── DOWNLOAD ──────────────────────────────────────────────────────────
@app.route('/download/<filename>')
@login_required
def download(filename):
    filepath = os.path.join(OUTPUT_DIR, filename)
    return send_file(filepath, as_attachment=True)

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

    NAVY  = colors.HexColor('#1F4E79')
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

    doc.build(e)


@app.route('/contrat/etudiant/nouveau', methods=['GET', 'POST'])
@login_required
def nouveau_contrat_etudiant():
    dossier_id = request.args.get('dossier_id', type=int) or request.form.get('dossier_id', type=int)
    travailleur_id = request.args.get('travailleur_id', type=int) or request.form.get('travailleur_id', type=int)
    dossier = get_dossier(dossier_id)
    travailleur = get_travailleur(travailleur_id)
    ctx = get_context_base()
    ctx['tenant'] = get_tenant()

    if request.method == 'POST':
        form = request.form
        cp_key = form.get('commission_paritaire_key', dossier.get('cp_principale', 'CP 140.03'))

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
            'lieu_signature': form.get('lieu_signature', 'Bruxelles'),
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

    return render_template('contrat_etudiant.html',
                           dossier=dossier, travailleur=travailleur,
                           dossier_actif=dossier,
                           cp_data=CP_DATABASE,
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

# ── FICHE DE PAIE DEPUIS CALENDRIER ──────────────────────────────────

@app.route('/dimona/<int:dimona_id>/generer-paie', methods=['GET', 'POST'])
@login_required
def generer_fiche_depuis_calendrier(dimona_id):
    from psycopg2.extras import RealDictCursor
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Récupérer dimona + travailleur + contrat + dossier
    cur.execute("""
        SELECT d.*, t.prenom, t.nom, t.niss, t.adresse, t.iban,
               t.date_naissance, t.etat_civil, t.nb_enfants_charge,
               t.km_domicile_travail, t.moyen_transport, t.vehicule_societe,
               dos.nom as dossier_nom, dos.adresse as dossier_adresse,
               dos.bce, dos.rsz, dos.id as dossier_id,
               dos.premier_engagement, dos.premier_engagement_depuis
        FROM dimona d
        JOIN travailleurs t ON t.id = d.travailleur_id
        JOIN dossiers dos ON dos.id = d.dossier_id
        WHERE d.id = %s
    """, (dimona_id,))
    dimona = cur.fetchone()
    if not dimona:
        return "Dimona introuvable", 404

    # Récupérer le contrat actif du travailleur
    cur.execute("""
        SELECT * FROM contrats 
        WHERE travailleur_id = %s AND statut = 'actif'
        ORDER BY created_at DESC LIMIT 1
    """, (dimona['travailleur_id'],))
    contrat = cur.fetchone()

    annee = request.args.get('annee', date.today().year, type=int)
    mois = request.args.get('mois', date.today().month, type=int)

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
        CODES_MALADIE = {'MA', 'AC', 'MAT', 'PAT'}
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

        if jours_prestes == 0 and jours_feries == 0:
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
        premier_engagement = bool(dimona.get('premier_engagement', False))
        cp_key = contrat['cp_key'] if contrat else dimona.get('cp_key', 'CP 140.03')
        salaire_h = float(contrat['salaire_horaire']) if contrat else 14.9255
        heures_sem = float(contrat['heures_semaine']) if contrat else 38.0
        heures_jour = float(contrat.get('heures_jour') or 7.6) if contrat else 7.6
        jours_semaine = int(contrat.get('jours_semaine') or 5) if contrat else 5
        is_etudiant = contrat['type_contrat'] == 'STU' if contrat else False

        import calendar as cal
        periode_debut = date(annee, mois, 1)
        periode_fin = date(annee, mois, cal.monthrange(annee, mois)[1])

        data = calculer_fiche_paie(
            prenom=dimona['prenom'], nom=dimona['nom'],
            niss=dimona['niss'] or '—', adresse=dimona['adresse'] or '—',
            iban=dimona['iban'] or '—',
            date_naissance=dimona['date_naissance'],
            date_entree=contrat['date_debut'] if contrat else periode_debut,
            nom_societe=dimona['dossier_nom'],
            adresse_societe=dimona['dossier_adresse'] or '—',
            bce_societe=dimona['bce'] or '—',
            rsz_societe=dimona['rsz'] or '—',
            cp_key=cp_key, categorie=contrat['categorie'] if contrat else '—',
            salaire_horaire=salaire_h,
            etat_civil=dimona.get('etat_civil', 'celibataire') or 'celibataire',
            nb_enfants=int(dimona.get('nb_enfants_charge', 0) or 0),
            heures_semaine=heures_sem, heures_jour=heures_jour, jours_semaine=jours_semaine,
            type_contrat=contrat['type_contrat'] if contrat else 'CDD',
            is_etudiant=is_etudiant,
            jours_prestes=jours_prestes, heures_prestees=heures_prestees,
            jours_feries_payes=jours_feries, heures_feries=heures_feries,
            jours_conge=jours_conge, jours_maladie=jours_maladie, jours_chomage=jours_chomage,
            premier_engagement=premier_engagement,
            km_domicile=km_domicile, moyen_transport=moyen_transport,
            vehicule_societe=vehicule_societe,
            rgpt_actif=rgpt_actif, arab_heure=arab_heure, cheques_repas=cheques_repas,
            periode_debut=periode_debut, periode_fin=periode_fin,
        )

        # Générer le PDF
        mois_nom = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'][mois]
        filename = f"fiche_paie_{dimona['nom']}_{dimona['prenom']}_{mois_nom}_{annee}.pdf"
        filepath = os.path.join(OUTPUT_DIR, filename)
        generer_fiche_paie_pdf(data, filepath)

        # Sauvegarder en BDD
        cur.execute("""
            INSERT INTO fiches_paie (
                dossier_id, travailleur_id, contrat_id,
                periode_debut, periode_fin,
                salaire_brut, onss_personnel, precompte,
                salaire_net, total_onss,
                cout_employeur, pdf_path, statut_paiement
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'genere')
            RETURNING id
        """, (
            dimona['dossier_id'], dimona['travailleur_id'],
            contrat['id'] if contrat else None,
            periode_debut, periode_fin,
            data['brut_onss'], abs(data['onss_net']),
            abs(data['precompte']), data['salaire_net'],
            abs(data['onss_net']) + data['onss_patronal'],
            data['cout_employeur'], filepath
        ))
        fiche_id = cur.fetchone()['id']
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

    ctx = get_context_base()
    ctx['tenant'] = get_tenant()
    return render_template('generer_fiche_form.html',
        dimona=dimona, contrat=contrat,
        annee=annee, mois=mois, mois_nom=mois_nom,
        cp_key=cp_key,
        vehicule_societe=dimona.get('vehicule_societe', False),
        km_domicile=dimona.get('km_domicile_travail', 0),
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
    # Supprimer le fichier PDF si existe
    if fiche.get('pdf_path') and os.path.exists(fiche['pdf_path']):
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

    NAVY = colors.HexColor('#1F4E79')
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
        ['ONSS patronal (~27%)', f"{total_onss_pat:.2f} EUR"],
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
    e.append(p(f"Etabli par : DuxSalary — Secrétariat Social Digital", size=8))

    doc.build(e)
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

    NAVY = colors.HexColor('#1F4E79')
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

    doc.build(e)
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

    NAVY = colors.HexColor('#1F4E79')
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
        cur_ref.execute("SELECT AVG(salaire_brut) as moy FROM fiches_paie WHERE travailleur_id=%s", (c['travailleur_id'],))
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

    doc.build(e)
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

