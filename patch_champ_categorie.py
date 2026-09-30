# Patch -- champ "Categorie employeur ONSS" dans Modifier dossier, avec
# verification dans le fichier de taux ONSS. ATOMIQUE: verifie tout avant d'ecrire.
import shutil, ast

APP = '/var/www/duxsalary/app.py'
TPL = '/var/www/duxsalary/templates/modifier_dossier.html'
app = open(APP).read()
tpl = open(TPL).read()

old_route = """    if request.method == 'POST':
        update_dossier(dossier_id, request.form)
        return redirect(url_for('dossier_dashboard', dossier_id=dossier_id))
    return render_template('modifier_dossier.html', dossier=dossier, dossier_actif=dossier, **ctx)"""
new_route = """    if request.method == 'POST':
        # Categorie employeur ONSS: validee AVANT tout enregistrement
        from onss_taux import categorie_existe
        cat = (request.form.get('categorie_employeur') or '000').strip()
        if not (cat.isdigit() and len(cat) <= 3) or not categorie_existe(cat.zfill(3)):
            return render_template('modifier_dossier.html', dossier=dossier, dossier_actif=dossier,
                erreur_categorie=f"Catégorie « {cat} » introuvable dans le fichier de taux ONSS. "
                                 f"Vérifiez le code dans le Répertoire des employeurs (consultation sécurisée).",
                **ctx)
        update_dossier(dossier_id, request.form)
        conn_c = get_conn(); cur_c = conn_c.cursor()
        cur_c.execute("UPDATE dossiers SET categorie_employeur=%s WHERE id=%s", (cat.zfill(3), dossier_id))
        conn_c.commit(); cur_c.close(); conn_c.close()
        return redirect(url_for('dossier_dashboard', dossier_id=dossier_id))
    return render_template('modifier_dossier.html', dossier=dossier, dossier_actif=dossier, **ctx)"""

old_tpl = """          <div class="form-group">
            <label class="form-label">Premier engagement ONSS</label>"""
new_tpl = """          <div class="form-group">
            <label class="form-label">Catégorie employeur ONSS</label>
            <input type="text" name="categorie_employeur" maxlength="3" class="form-control"
                   style="max-width:120px{% if erreur_categorie %};border-color:#e74c3c{% endif %}"
                   value="{{ request.form.get('categorie_employeur') if erreur_categorie else (dossier.categorie_employeur or '000') }}">
            <small style="font-size:11px;color:#888">
              Code à 3 chiffres attribué par l'ONSS — Répertoire des employeurs (consultation sécurisée).
              Détermine les taux ONSS et les Fonds de sécurité d'existence. 000 = secteur privé général.
            </small>
            {% if erreur_categorie %}
            <div style="font-size:12px;color:#c0392b;margin-top:4px">⚠️ {{ erreur_categorie }}</div>
            {% endif %}
          </div>
          <div class="form-group">
            <label class="form-label">Premier engagement ONSS</label>"""

for nom, contenu, old in [('app.py', app, old_route), ('modifier_dossier.html', tpl, old_tpl)]:
    n = contenu.count(old)
    if n != 1:
        raise SystemExit(f"ECHEC {nom}: bloc trouve {n} fois -- RIEN n'a ete modifie.")

app = app.replace(old_route, new_route)
tpl = tpl.replace(old_tpl, new_tpl)
ast.parse(app)

shutil.copy(APP, APP + '.avant_champ_categorie')
shutil.copy(TPL, TPL + '.avant_champ_categorie')
open(APP, 'w').write(app)
open(TPL, 'w').write(tpl)
print("OK -- champ Categorie employeur ONSS ajoute dans Modifier dossier")
