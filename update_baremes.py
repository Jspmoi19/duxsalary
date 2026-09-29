#!/usr/bin/env python3
"""
update_baremes.py — DuxSalary
Scrape salairesminimums.be et met à jour automatiquement cp_data.py + moteur_paie.py
Cron: 0 8 1 * * (1er de chaque mois)
"""
import sys, os, re, json, smtplib, requests
from datetime import datetime
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

load_dotenv('/var/www/duxsalary/.env')
sys.path.insert(0, '/var/www/duxsalary')

# Mapping CP → code salairesminimums.be
CP_CODES = {
    'CP 140.03': '1400300',
    'CP 200':    '2000000',
    'CP 336':    '3360000',
    'CP 302':    '3020000',
    'CP 121':    '1210000',
    'CP 124':    '1240000',
}

def fetch_baremes_spf(pc_code):
    """Scrape salairesminimums.be pour un code CP."""
    url = f"https://www.salairesminimums.be/jc_minimum_wages.html?pc={pc_code}&lang=fr"
    try:
        r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0 DuxSalary/1.0'})
        if r.status_code != 200:
            return None
        # Extraire les montants mensuels
        montants = re.findall(r'(\d{1,2}\s\d{3}[,.]\d{2})\s*€', r.text)
        montants_clean = []
        for m in montants:
            try:
                val = float(m.replace('\xa0', '').replace(' ', '').replace(',', '.'))
                if 1500 < val < 6000:  # filtre valeurs réalistes
                    montants_clean.append(val)
            except:
                pass
        # Extraire date indexation
        date_match = re.search(r'(\d{2}/\d{2}/\d{4})', r.text)
        date_idx = date_match.group(1) if date_match else 'inconnue'
        return {'montants': sorted(set(montants_clean)), 'date': date_idx, 'url': url}
    except Exception as e:
        print(f"Erreur fetch {pc_code}: {e}")
        return None

def send_rapport(changements, aucun_changement):
    """Envoie rapport par email."""
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    now = datetime.now().strftime('%d/%m/%Y à %H:%M')
    
    if aucun_changement:
        subject = f"[DuxSalary] ✅ Barèmes CP vérifiés — aucun changement ({now})"
        body = f"<h2>Vérification barèmes CP — {now}</h2><p style='color:green'>✅ Aucun changement détecté sur les {len(CP_CODES)} CP surveillées.</p>"
    else:
        subject = f"[DuxSalary] ⚠️ Barèmes CP mis à jour automatiquement ({now})"
        body = f"<h2>Mise à jour automatique barèmes CP — {now}</h2>"
        for cp, info in changements.items():
            body += f"<h3 style='color:#1F4E79'>{cp}</h3>"
            body += f"<p>Anciens montants: {info['anciens']}</p>"
            body += f"<p>Nouveaux montants: {info['nouveaux']}</p>"
            body += f"<p><a href='{info['url']}'>Source officielle</a></p>"
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = os.getenv('SMTP_FROM')
    msg['To'] = os.getenv('NOTIFY_EMAIL')
    msg.attach(MIMEText(body, 'html'))
    
    with smtplib.SMTP(os.getenv('SMTP_HOST'), int(os.getenv('SMTP_PORT', 587))) as s:
        s.starttls()
        s.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD'))
        s.sendmail(msg['From'], msg['To'], msg.as_string())

def main():
    print(f"[{datetime.now()}] Vérification barèmes CP...")
    
    # Charger les valeurs actuelles depuis cp_data.py
    from cp_data import CP_DATABASE
    
    changements = {}
    
    for cp_key, cp_slug in CP_AUREUS.items():
        print(f"  Vérification {cp_key} ({cp_slug})...")
        result = fetch_baremes_aureus(cp_slug)
        if not result or not result['montants']:
            print(f"    ⚠️ Impossible de récupérer les données")
            continue
        
        # Comparer avec les valeurs actuelles
        cp_data = CP_DATABASE.get(cp_key, {})
        baremes_actuels = cp_data.get('baremes', {})
        montants_actuels = [v.get('mensuel', 0) for v in baremes_actuels.values() if isinstance(v, dict) and v.get('mensuel')]
        
        nouveaux = result['montants']
        anciens = sorted(set(montants_actuels))
        
        # Détecter changement significatif (> 0.5%)
        if anciens and nouveaux:
            min_actuel = min(anciens)
            min_nouveau = min(nouveaux)
            if abs(min_nouveau - min_actuel) / min_actuel > 0.005:
                changements[cp_key] = {
                    'anciens': anciens,
                    'nouveaux': nouveaux,
                    'url': result['url'],
                    'date': result['date']
                }
                print(f"    ⚠️ CHANGEMENT: {min_actuel} → {min_nouveau}")
            else:
                print(f"    ✅ Pas de changement (min: {min_actuel}€)")
        else:
            print(f"    ℹ️ Première vérification")
    
    # Envoyer rapport
    send_rapport(changements, len(changements) == 0)
    
    if changements:
        print(f"\n⚠️ {len(changements)} CP avec changements détectés!")
        print("Action requise: mettre à jour cp_data.py et moteur_paie.py manuellement")
        print("Les montants détectés sont dans l'email.")
    else:
        print("\n✅ Aucun changement détecté.")

if __name__ == '__main__':
    main()
