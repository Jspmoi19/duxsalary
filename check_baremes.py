#!/usr/bin/env python3
"""
check_baremes.py — DuxSalary
Script mensuel : vérifie les indexations SPF Emploi et envoie une alerte email.
Lancer via cron : 0 8 1 * * /var/www/duxsalary/venv/bin/python3 /var/www/duxsalary/check_baremes.py
"""

import urllib.request
import json
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# ── CONFIG ────────────────────────────────────────────────────────────
EMAIL_TO   = "info@duxsalary.be"
EMAIL_FROM = "info@duxsalary.be"
SMTP_HOST  = "ssl0.ovh.net"
SMTP_PORT  = 465
SMTP_USER  = "info@duxsalary.be"
SMTP_PASS  = os.environ.get("EMAIL_PASSWORD", "")

# Fichier qui stocke les derniers barèmes connus
STATE_FILE = "/var/www/duxsalary/baremes_state.json"

# Pages SPF à surveiller (jcId = identifiant fiche SPF Emploi)
CP_URLS = {
    "CP 140.03": "https://www.salairesminimums.be/document.html?jcId=e4f43b8462814a79b780b4feb1ae1eaa",
    "CP 302":    "https://www.salairesminimums.be/document.html?jcId=ceaa4cb322cc4933bdb1b933335760ee",
    "CP 200":    "https://www.salairesminimums.be/document.html?jcId=8e8cddf22c5d4cc9b9fe6234b4ea569e",
    "CP 124":    "https://www.salairesminimums.be/document.html?jcId=c206d961982d4ec6b997c7a485e0bf32",
    "CP 121":    "https://www.salairesminimums.be/document.html?jcId=indexation-cp121",
    "CP 336":    "https://www.salairesminimums.be/document.html?jcId=3360000-indexation",
}

# Barèmes actuels en mémoire (référence)
BAREMES_ACTUELS = {
    "CP 140.03": {"taux_cat1": 14.9255, "date": "01/01/2026", "indexation": "+2,18%"},
    "CP 302":    {"taux_cat1": 2504.53, "date": "01/01/2026", "indexation": "+2,189%"},
    "CP 200":    {"taux_cat1": 2242.81, "date": "01/01/2026", "indexation": "+2,21%"},
    "CP 124":    {"taux_cat1": 18.390,  "date": "01/04/2026", "indexation": "trimestrielle"},
    "CP 121":    {"taux_cat1": 2696.49, "date": "01/01/2026", "indexation": "variable"},
    "CP 336":    {"taux_cat1": 2210.10, "date": "01/04/2026", "indexation": "+2% (03/2026)"},
}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def check_spf_page(cp_name, url):
    """Vérifie si la page SPF a changé depuis la dernière visite."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'DuxSalary-BaremeChecker/1.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            content = r.read().decode('utf-8', errors='ignore')
            # Cherche les mentions d'indexation dans le contenu
            keywords = ['indexation', 'Indexation', 'en vigueur au', 'En vigueur au',
                       '2026', '2027', 'adaptation', 'Adaptation']
            found = [k for k in keywords if k in content]
            # Hash simple du contenu pour détecter les changements
            content_hash = str(len(content)) + str(hash(content[:500]))
            return content_hash, found
    except Exception as e:
        return None, [f"Erreur: {str(e)}"]

def send_alert(changes):
    """Envoie un email d'alerte si des changements sont détectés."""
    now = datetime.now().strftime('%d/%m/%Y')
    
    body = f"""Bonjour Leo,

Le vérificateur automatique de barèmes DuxSalary a détecté des changements potentiels.

DATE DE VÉRIFICATION : {now}

CHANGEMENTS DÉTECTÉS :
{''.join([f"• {cp}: {msg}\n" for cp, msg in changes])}

ACTION REQUISE :
1. Vérifier les barèmes sur https://www.salairesminimums.be
2. Contacter Claude sur claude.ai pour mettre à jour cp_data.py
3. Envoyer le nouveau cp_data.py sur le serveur
4. Faire un backup (taper "backup" dans SSH)

Barèmes actuels en référence :
{json.dumps(BAREMES_ACTUELS, indent=2, ensure_ascii=False)}

---
DuxSalary — Vérificateur automatique
"""
    
    if not SMTP_PASS:
        print("EMAIL_PASSWORD non défini — alerte non envoyée par email")
        print(body)
        return

    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = f'⚠️ DuxSalary — Vérification barèmes {now}'
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
        print(f"Email d'alerte envoyé à {EMAIL_TO}")
    except Exception as e:
        print(f"Erreur envoi email : {e}")
        print(body)

def main():
    print(f"[{datetime.now()}] Vérification barèmes DuxSalary...")
    
    state = load_state()
    changes = []
    
    for cp_name, url in CP_URLS.items():
        print(f"  Vérification {cp_name}...")
        current_hash, keywords = check_spf_page(cp_name, url)
        
        if current_hash is None:
            changes.append((cp_name, f"Impossible d'accéder à la page SPF"))
            continue
        
        old_hash = state.get(cp_name, {}).get('hash')
        
        if old_hash and old_hash != current_hash:
            changes.append((cp_name, f"Page modifiée depuis la dernière vérification — vérifier manuellement"))
        
        state[cp_name] = {
            'hash': current_hash,
            'last_check': datetime.now().isoformat(),
            'keywords': keywords[:5],
        }
    
    save_state(state)
    
    # Alerte mensuelle systématique (rappel de vérification)
    today = datetime.now()
    if today.day == 1:
        changes.append(("RAPPEL MENSUEL", 
                        "Vérification manuelle recommandée sur salairesminimums.be — "
                        "CP 124 indexée trimestriellement (jan/avr/juil/oct)"))
    
    if changes:
        print(f"  → {len(changes)} alerte(s) — envoi email...")
        send_alert(changes)
    else:
        print("  → Aucun changement détecté")
    
    print("Vérification terminée.")

if __name__ == '__main__':
    main()
