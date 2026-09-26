#!/usr/bin/env python3
"""
alertes_cp.py — DuxSalary
Script de surveillance des CP actives — à lancer quotidiennement via cron
Surveille: socialsecurity.be, groupS.be, Liantis pour les CP des dossiers actifs
"""

import os, sys, json, hashlib, smtplib, ssl, requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv('/var/www/duxsalary/.env')
sys.path.insert(0, '/var/www/duxsalary')
from database import get_conn
from psycopg2.extras import RealDictCursor

CACHE_FILE = '/var/www/duxsalary/alertes_cp_cache.json'

# Sources à surveiller par CP
SOURCES_CP = {
    'CP 140.03': [
        {'url': 'https://www.salairesminimums.be/fr/pc/140030000', 'label': 'SPF Emploi — CP 140.03'},
        {'url': 'https://www.socialsecurity.be/employer/instructions/dmfa/fr/latest/instructions/salaries/particularsalaries/cp140.html', 'label': 'ONSS CP 140.03'},
    ],
    'CP 336': [
        {'url': 'https://www.salairesminimums.be/fr/pc/336', 'label': 'SPF Emploi — CP 336'},
        {'url': 'https://www.aureussocial.be/baremes/cp-336', 'label': 'Aureus CP 336'},
    ],
    'CP 200': [
        {'url': 'https://www.salairesminimums.be/fr/pc/200', 'label': 'SPF Emploi — CP 200'},
        {'url': 'https://www.aureussocial.be/baremes/cp-200', 'label': 'Aureus CP 200'},
    ],
    'CP 302': [
        {'url': 'https://www.salairesminimums.be/fr/pc/302', 'label': 'SPF Emploi — CP 302'},
    ],
    'CP 121': [
        {'url': 'https://www.salairesminimums.be/fr/pc/124', 'label': 'SPF Emploi — CP 121'},
    ],
    'CP 124': [
        {'url': 'https://www.salairesminimums.be/fr/pc/124', 'label': 'SPF Emploi — CP 124'},
    ],
}

def get_cp_actives():
    """Récupère les CP des dossiers actifs depuis la BDD."""
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT DISTINCT cp_principale 
        FROM dossiers 
        WHERE actif = TRUE AND cp_principale IS NOT NULL AND cp_principale != ''
    """)
    cps = [r['cp_principale'] for r in cur.fetchall()]
    cur.close(); conn.close()
    return cps

def get_dossiers_par_cp(cp):
    """Récupère les noms de dossiers actifs pour une CP."""
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT nom FROM dossiers WHERE actif=TRUE AND cp_principale=%s", (cp,))
    noms = [r['nom'] for r in cur.fetchall()]
    cur.close(); conn.close()
    return noms

def fetch_content(url):
    """Récupère le contenu d'une page web."""
    try:
        r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0 DuxSalary-AlertCP/1.0'})
        return r.text if r.status_code == 200 else None
    except:
        return None

def hash_content(content):
    """Hash le contenu pour détecter les changements."""
    return hashlib.md5(content.encode()).hexdigest() if content else None

def load_cache():
    """Charge le cache des hashes précédents."""
    if Path(CACHE_FILE).exists():
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}

def save_cache(cache):
    """Sauvegarde le cache."""
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

def send_alert(changements):
    """Envoie un email d'alerte."""
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    
    now = datetime.now().strftime('%d/%m/%Y à %H:%M')
    
    html = f"""
    <h2 style='color:#1F4E79'>🔔 Alertes CP — DuxSalary</h2>
    <p style='color:#555'>Détectées le {now}</p>
    <hr>
    """
    
    for cp, sources in changements.items():
        dossiers = get_dossiers_par_cp(cp)
        html += f"""
        <h3 style='color:#1F4E79;margin-top:20px'>{cp}</h3>
        <p style='color:#888;font-size:12px'>Dossiers concernés: {', '.join(dossiers)}</p>
        <ul>
        """
        for s in sources:
            html += f"<li><a href='{s['url']}'>{s['label']}</a> — contenu modifié</li>"
        html += "</ul>"
    
    html += "<hr><p style='font-size:11px;color:#aaa'>DuxSalary — Alertes automatiques CP</p>"
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"[DuxSalary] ⚠️ Modifications détectées dans {len(changements)} CP"
    msg['From'] = os.getenv('SMTP_FROM')
    msg['To'] = os.getenv('NOTIFY_EMAIL')
    msg.attach(MIMEText(html, 'html'))
    
    with smtplib.SMTP(os.getenv('SMTP_HOST'), int(os.getenv('SMTP_PORT', 587))) as s:
        s.starttls()
        s.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD'))
        s.sendmail(msg['From'], msg['To'], msg.as_string())
    
    print(f"Email envoyé — {len(changements)} CP modifiées")

def main():
    print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M')}] Démarrage surveillance CP...")
    
    cp_actives = get_cp_actives()
    print(f"CP actives: {cp_actives}")
    
    cache = load_cache()
    changements = {}
    
    for cp in cp_actives:
        sources = SOURCES_CP.get(cp, [])
        if not sources:
            print(f"  {cp}: pas de source configurée")
            continue
        
        for source in sources:
            url = source['url']
            content = fetch_content(url)
            if not content:
                print(f"  {cp} — {source['label']}: impossible de récupérer")
                continue
            
            new_hash = hash_content(content)
            old_hash = cache.get(url)
            
            if old_hash and new_hash != old_hash:
                print(f"  ⚠️ CHANGEMENT: {cp} — {source['label']}")
                if cp not in changements:
                    changements[cp] = []
                changements[cp].append(source)
            elif not old_hash:
                print(f"  {cp} — {source['label']}: première vérification (cache initialisé)")
            else:
                print(f"  {cp} — {source['label']}: pas de changement")
            
            cache[url] = new_hash
    
    save_cache(cache)
    
    if changements:
        print(f"\n{len(changements)} CP avec changements — envoi email...")
        send_alert(changements)
    else:
        print("\nAucun changement détecté.")

if __name__ == '__main__':
    main()
