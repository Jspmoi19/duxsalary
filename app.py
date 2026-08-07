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
        return render_template('login.html', error='Email ou mot de passe incorrect.')
    return render_template('login.html')

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
    tous = get_all_dossiers()
    actifs = [d for d in tous if d.get('statut') != 'archive']
    return render_template('dossiers.html', dossiers=actifs, **ctx)

@app.route('/dossier/nouveau', methods=['GET', 'POST'])
@login_required
def nouveau_dossier():
    ctx = get_context_base()
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
            adresse=%s, iban=%s, email=%s, telephone=%s WHERE id=%s""",
            (request.form['prenom'], request.form['nom'], request.form.get('niss'),
             ddn_db, request.form.get('adresse'), request.form.get('iban'),
             request.form.get('email'), request.form.get('telephone'), travailleur_id))
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
    return render_template('dimona_list.html', travailleur=travailleur,
                           dossier=dossier, dossier_actif=dossier,
                           dimona_list=get_dimona_travailleur(travailleur_id), **ctx)

@app.route('/travailleur/<int:travailleur_id>/dimona/nouvelle', methods=['GET', 'POST'])
@login_required
def nouvelle_dimona(travailleur_id):
    travailleur = get_travailleur(travailleur_id)
    dossier = get_dossier(travailleur['dossier_id'])
    ctx = get_context_base()
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
        }

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
    conn = get_conn()
    from psycopg2.extras import RealDictCursor
    cur = conn.cursor(cursor_factory=RealDictCursor)

    today = date.today()
    annee = today.year
    mois = today.month
    dossier = get_dossier(dossier_id)
    date_activation = dossier.get('date_activation_rsz')

    def inserer(type_ech, desc, date_ech, trimestre=None, niveau='warn'):
        try:
            cur.execute("""
                INSERT INTO echeances (dossier_id, type_echeance, description, date_echeance, trimestre, annee, statut, niveau)
                VALUES (%s, %s, %s, %s, %s, %s, 'en_attente', %s)
                ON CONFLICT ON CONSTRAINT echeances_unique DO NOTHING
            """, (dossier_id, type_ech, desc, date_ech, trimestre, annee, niveau))
            conn.commit()
        except:
            conn.rollback()

    def trim_actif(debut_mois, an=None):
        if not date_activation: return True
        if an is None: an = annee
        import calendar as cal
        last = cal.monthrange(an, debut_mois + 2)[1]
        fin_trim = date(an, debut_mois + 2, last)
        debut_trim = date(an, debut_mois, 1)
        # Le trimestre est actif si la date d'activation est avant la fin du trimestre
        # ET le trimestre a démarré après (ou pendant) le mois d'activation
        return date_activation <= fin_trim and date_activation >= debut_trim - __import__('datetime').timedelta(days=95)

    # ── DmfA trimestrielle ────────────────────────────────────────────
    trimestres = [
        ('Q1', 1, f"30/04/{annee}", f"DmfA Q1/{annee} — socialsecurity.be"),
        ('Q2', 4, f"31/07/{annee}", f"DmfA Q2/{annee} — socialsecurity.be"),
        ('Q3', 7, f"31/10/{annee}", f"DmfA Q3/{annee} — socialsecurity.be"),
        ('Q4', 10, f"31/01/{annee+1}", f"DmfA Q4/{annee} — socialsecurity.be"),
    ]
    for trim_code, m_debut, date_str, desc in trimestres:
        if not trim_actif(m_debut):
            continue
        d_parts = date_str.split('/')
        try:
            d_ech = date(int(d_parts[2]), int(d_parts[1]), int(d_parts[0]))
        except:
            continue
        if d_ech < date(today.year - 1, 1, 1):
            continue
        niv = 'urgent' if (d_ech - today).days <= 30 else 'warn'
        inserer('dmfa', desc, d_ech, trim_code, niv)

    # ── Paiement ONSS mensuel ─────────────────────────────────────────
    # Dû avant le 5 du mois suivant
    import calendar as cal
    _, last_day = cal.monthrange(annee, mois)
    fin_mois = date(annee, mois, last_day)
    # ONSS mensuel dû le 5 du mois suivant
    if mois == 12:
        onss_echeance = date(annee + 1, 1, 5)
    else:
        onss_echeance = date(annee, mois + 1, 5)

    mois_noms = ['','Janvier','Février','Mars','Avril','Mai','Juin',
                 'Juillet','Août','Septembre','Octobre','Novembre','Décembre']

    # Vérifier si des travailleurs actifs existent ce mois
    cur.execute("""
        SELECT COUNT(*) as nb FROM contrats c
        WHERE c.dossier_id = %s AND c.statut = 'actif'
        AND c.date_debut <= %s
        AND (c.date_fin IS NULL OR c.date_fin >= %s)
    """, (dossier_id, fin_mois, date(annee, mois, 1)))
    row = cur.fetchone()
    nb_actifs = row['nb'] if row else 0

    if nb_actifs > 0 and date_activation and date_activation <= fin_mois:
        desc_onss = f"Paiement ONSS {mois_noms[mois]} {annee} — avant le {onss_echeance.strftime('%d/%m/%Y')}"
        niv_onss = 'urgent' if (onss_echeance - today).days <= 5 else 'warn'
        inserer('onss_mensuel', desc_onss, onss_echeance, None, niv_onss)

    # ── Fiches de paie manquantes ─────────────────────────────────────
    cur.execute("""
        SELECT t.id, t.prenom, t.nom, c.type_contrat, c.date_debut, c.date_fin
        FROM contrats c JOIN travailleurs t ON t.id = c.travailleur_id
        WHERE c.dossier_id = %s AND c.statut = 'actif'
        AND c.date_debut <= %s
        AND (c.date_fin IS NULL OR c.date_fin >= %s)
    """, (dossier_id, fin_mois, date(annee, mois, 1)))
    travailleurs_actifs = cur.fetchall()

    for t in travailleurs_actifs:
        # Vérifier si une fiche de paie existe pour ce mois
        cur.execute("""
            SELECT COUNT(*) as nb FROM fiches_paie
            WHERE travailleur_id = %s
            AND EXTRACT(MONTH FROM periode_debut) = %s
            AND EXTRACT(YEAR FROM periode_debut) = %s
        """, (t['id'], mois, annee))
        fiche_row = cur.fetchone()
        has_fiche = fiche_row['nb'] > 0 if fiche_row else False

        if not has_fiche:
            desc_fiche = f"Fiche de paie {mois_noms[mois]} {annee} — {t['prenom']} {t['nom']}"
            niv_fiche = 'urgent' if today.day >= 25 else 'warn'
            inserer('fiche_paie', desc_fiche, fin_mois, None, niv_fiche)

        # Fiche du mois précédent si pas encore faite
        mois_prec = mois - 1 if mois > 1 else 12
        annee_prec = annee if mois > 1 else annee - 1
        _, last_prec = cal.monthrange(annee_prec, mois_prec)
        fin_mois_prec = date(annee_prec, mois_prec, last_prec)

        if t['date_debut'] <= fin_mois_prec:
            cur.execute("""
                SELECT COUNT(*) as nb FROM fiches_paie
                WHERE travailleur_id = %s
                AND EXTRACT(MONTH FROM periode_debut) = %s
                AND EXTRACT(YEAR FROM periode_debut) = %s
            """, (t['id'], mois_prec, annee_prec))
            fiche_prec = cur.fetchone()
            has_fiche_prec = fiche_prec['nb'] > 0 if fiche_prec else False

            if not has_fiche_prec:
                desc_retard = f"⚠️ Fiche de paie {mois_noms[mois_prec]} {annee_prec} en retard — {t['prenom']} {t['nom']}"
                inserer('fiche_paie_retard', desc_retard, fin_mois_prec, None, 'urgent')

    # ── CDD/STU arrivant à échéance ───────────────────────────────────
    cur.execute("""
        SELECT t.prenom, t.nom, c.type_contrat, c.date_fin, c.id as contrat_id
        FROM contrats c JOIN travailleurs t ON t.id = c.travailleur_id
        WHERE c.dossier_id = %s AND c.type_contrat IN ('CDD', 'STU')
        AND c.date_fin IS NOT NULL
        AND c.date_fin BETWEEN CURRENT_DATE - INTERVAL '5 days' AND CURRENT_DATE + INTERVAL '30 days'
        AND c.statut = 'actif'
    """, (dossier_id,))
    for row in cur.fetchall():
        type_label = 'Contrat étudiant' if row['type_contrat'] == 'STU' else 'CDD'
        date_fin_fmt = row['date_fin'].strftime('%d/%m/%Y')
        jours = (row['date_fin'] - today).days
        if jours < 0:
            suffix = f"terminé le {date_fin_fmt} — à clôturer (Dimona OUT)"
            niv = 'urgent'
        elif jours == 0:
            suffix = f"se termine aujourd'hui — Dimona OUT obligatoire"
            niv = 'urgent'
        else:
            suffix = f"se termine le {date_fin_fmt} — dans {jours} jour(s)"
            niv = 'urgent' if jours <= 7 else 'warn'

        desc_cdd = f"{type_label} {row['prenom']} {row['nom']} — {suffix}"
        try:
            cur.execute("""
                INSERT INTO echeances (dossier_id, type_echeance, description, date_echeance, trimestre, annee, statut, niveau)
                VALUES (%s, %s, %s, %s, NULL, %s, 'en_attente', %s)
                ON CONFLICT ON CONSTRAINT echeances_unique DO UPDATE SET
                description = EXCLUDED.description, niveau = EXCLUDED.niveau
            """, (dossier_id, f"cdd_{row['contrat_id']}", desc_cdd, row['date_fin'], annee, niv))
            conn.commit()
        except:
            conn.rollback()

    # ── Belcotax annuel ───────────────────────────────────────────────
    if mois in [1, 2] and date_activation and date_activation.year < annee:
        inserer('belcotax',
                f"Belcotax 281.10 — fiches fiscales revenus {annee-1} — avant le 28/02/{annee}",
                date(annee, 2, 28), None, 'warn')

    # ── Récupérer toutes les échéances à afficher ─────────────────────
    cur.execute("""
        SELECT * FROM echeances
        WHERE dossier_id = %s
        AND (
            statut = 'en_attente'
            OR (statut = 'fait' AND updated_at > NOW() - INTERVAL '30 days')
        )
        ORDER BY
            CASE statut WHEN 'en_attente' THEN 0 ELSE 1 END,
            CASE niveau WHEN 'urgent' THEN 0 ELSE 1 END,
            date_echeance ASC NULLS LAST
        LIMIT 25
    """, (dossier_id,))
    result = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return result



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

    sN  = ParagraphStyle('N', fontName='Helvetica', fontSize=10, leading=15, textColor=DARK)
    sB  = ParagraphStyle('B', fontName='Helvetica-Bold', fontSize=10, leading=15, textColor=DARK)
    sT  = ParagraphStyle('T', fontName='Helvetica-Bold', fontSize=15, leading=22, textColor=NAVY, alignment=TA_CENTER)
    sS  = ParagraphStyle('S', fontName='Helvetica-Bold', fontSize=11, leading=16, textColor=NAVY)
    sJ  = ParagraphStyle('J', fontName='Helvetica', fontSize=10, leading=15, alignment=TA_JUSTIFY, textColor=DARK)
    sC  = ParagraphStyle('C', fontName='Helvetica', fontSize=9, leading=13, alignment=TA_CENTER, textColor=MUTED)
    sMu = ParagraphStyle('M', fontName='Helvetica', fontSize=9, leading=13, textColor=MUTED)

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
        f"L'Etudiant(e) percoit un salaire brut de <b>{sal_h} EUR de l'heure</b>, "
        f"conformement aux baremes de la {cp_key}. "
        f"Salaire brut total : <b>{brut} EUR</b>. "
        f"Cotisation ONSS etudiant (2,71%) : <b>{onss} EUR</b>. "
        f"Salaire net estime : <b>{net} EUR</b>. "
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
