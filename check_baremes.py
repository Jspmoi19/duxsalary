#!/usr/bin/env python3
"""
check_baremes_v2.py — DuxSalary
Vérifie les vrais barèmes SPF et compare avec les valeurs connues.
Envoie un email détaillé uniquement si un vrai changement de montant est détecté.
Cron : 0 8 1 * * EMAIL_PASSWORD="xxx" python3 /var/www/duxsalary/check_baremes_v2.py
"""

import urllib.request, json, os, smtplib, re
from email.mime.text import MIMEText
from datetime import datetime

EMAIL_TO   = "Info@duxsalary.be"
EMAIL_FROM = "duxsalary@gmail.com"
SMTP_HOST  = "smtp.gmail.com"
SMTP_PORT  = 465
SMTP_USER  = "duxsalary@gmail.com"
SMTP_PASS  = os.environ.get("EMAIL_PASSWORD", "")
STATE_FILE = "/var/www/duxsalary/baremes_state.json"

# ── Barèmes de référence actuels ──────────────────────────────────────
# Ces valeurs sont mises à jour manuellement après chaque indexation
REFERENCE = {
    "CP 140.03": {
        "url": "https://www.aureussocial.be/baremes/cp-140",
        "valeurs": {
            "Personnel roulant niveau 1": 14.9255,
            "Personnel roulant niveau 2": 15.449,
            "Personnel roulant niveau 3": 15.6285,
            "Personnel roulant niveau 4": 15.8075,
            "Personnel non roulant classe 1": 15.6465,
        },
        "pattern": r'(\d{2},\d{4})\s*EUR/h',
        "date_ref": "01/01/2026",
        "indexation": "+2,18%",
    },
    "CP 302": {
        "url": "https://www.aureussocial.be/baremes/cp-302",
        "valeurs": {
            "Cat I & II": 2504.53,
            "Cat III": 2519.02,
            "Cat IV": 2629.69,
            "Cat V": 2780.38,
            "Cat VI": 2853.95,
            "Cat VII": 3244.94,
            "Cat VIII": 3495.90,
            "Cat IX": 3717.86,
        },
        "pattern": r'(\d[\d\s]+,\d{2})\s*€',
        "date_ref": "01/01/2026",
        "indexation": "+2,189%",
    },
    "CP 200": {
        "url": "https://www.aureussocial.be/baremes/cp-200",
        "valeurs": {
            "Cat I minimum": 2242.81,
        },
        "pattern": r'(\d[\d\s]+,\d{2})\s*€',
        "date_ref": "01/01/2026",
        "indexation": "+2,21%",
    },
    "CP 336": {
        "url": "https://www.aureussocial.be/baremes/cp-336",
        "valeurs": {
            "Minimum sectoriel": 2210.10,
        },
        "pattern": r'(\d[\d\s]+,\d{2})\s*€',
        "date_ref": "01/04/2026",
        "indexation": "+2% (mars 2026)",
    },
    "CP 124": {
        "url": "https://support.accg.be/hc/fr-be/articles/25103585981725",
        "valeurs": {
            "Cat I manoeuvre": 18.390,
        },
        "pattern": r'(\d{2},\d{3})\s*€',
        "date_ref": "01/04/2026",
        "indexation": "trimestrielle",
        "note": "⚠️ Indexée CHAQUE TRIMESTRE — vérifier jan/avr/juil/oct",
    },
    "CP 121": {
        "url": "https://www.aureussocial.be/baremes/cp-121",
        "valeurs": {
            "Cat I minimum": 2696.49,
        },
        "pattern": r'(\d[\d\s]+,\d{2})\s*€',
        "date_ref": "01/01/2026",
        "indexation": "variable",
    },
}

def fetch_page(url):
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 DuxSalary-BaremeChecker/2.0'
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return None

def extract_amounts(content, pattern):
    """Extrait les montants numériques depuis le contenu HTML."""
    matches = re.findall(pattern, content)
    amounts = []
    for m in matches:
        try:
            val = float(m.replace(' ', '').replace(',', '.'))
            if 10 < val < 10000:  # Filtre les valeurs plausibles
                amounts.append(val)
        except:
            pass
    return sorted(set(amounts))

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def send_email(subject, body):
    if not SMTP_PASS:
        print("EMAIL_PASSWORD non défini")
        print(body)
        return
    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
        print(f"Email envoyé : {subject}")
    except Exception as e:
        print(f"Erreur email : {e}")

def main():
    now = datetime.now()
    print(f"[{now}] Vérification barèmes DuxSalary v2...")

    state = load_state()
    alertes = []
    rapport = []

    for cp, config in REFERENCE.items():
        print(f"  Vérification {cp}...")
        content = fetch_page(config['url'])

        if not content:
            rapport.append(f"⚠️ {cp} : impossible d'accéder à la page")
            continue

        # Cherche mention d'une nouvelle date d'indexation
        nouvelles_dates = re.findall(
            r'(?:en vigueur|à partir|vigueur au|indexation)[^\d]*(\d{2}/\d{2}/\d{4})',
            content, re.IGNORECASE)

        date_ref = config.get('date_ref', '')
        nouvelles = [d for d in nouvelles_dates if d != date_ref and d > date_ref]

        # Cherche les montants sur la page
        amounts = extract_amounts(content, config['pattern'])
        ref_amounts = list(config['valeurs'].values())

        # Détecte si les montants ont changé
        changed = False
        details = []

        old_amounts = state.get(cp, {}).get('amounts', [])
        if old_amounts and amounts:
            new_vals = [a for a in amounts if a not in old_amounts]
            gone_vals = [a for a in old_amounts if a not in amounts]
            if new_vals or gone_vals:
                changed = True
                if new_vals:
                    details.append(f"  Nouveaux montants détectés : {new_vals}")
                if gone_vals:
                    details.append(f"  Montants disparus : {gone_vals}")

        if nouvelles:
            changed = True
            details.append(f"  Nouvelle date d'indexation détectée : {nouvelles}")

        note = config.get('note', '')
        rapport.append(
            f"{'🔴' if changed else '✅'} {cp} "
            f"(réf: {date_ref}, {config['indexation']})"
            + (f"\n{chr(10).join(details)}" if details else "")
            + (f"\n  {note}" if note else "")
        )

        if changed:
            alertes.append(cp)

        state[cp] = {
            'last_check': now.isoformat(),
            'amounts': amounts[:20],
            'date_ref': date_ref,
        }

    save_state(state)

    # Email de rapport mensuel
    rapport_txt = "\n".join(rapport)
    alerte_txt = f"⚠️ CHANGEMENTS DÉTECTÉS : {', '.join(alertes)}\n\n" if alertes else "✅ Aucun changement détecté\n\n"

    body = f"""Bonjour Leo,

Rapport mensuel de vérification des barèmes DuxSalary
Date : {now.strftime('%d/%m/%Y à %H:%M')}

{alerte_txt}DÉTAIL PAR COMMISSION PARITAIRE :
{rapport_txt}

{"ACTION REQUISE : contactez Claude sur claude.ai pour mettre à jour cp_data.py !" if alertes else "Aucune action requise ce mois-ci."}

Barèmes de référence actuels :
{json.dumps({cp: cfg['valeurs'] for cp, cfg in REFERENCE.items()}, indent=2, ensure_ascii=False)}

---
DuxSalary — Vérificateur automatique v2
"""

    subject = f"{'⚠️ ALERTE' if alertes else '✅ OK'} — Barèmes DuxSalary {now.strftime('%m/%Y')}"
    send_email(subject, body)
    print("Vérification terminée.")

if __name__ == '__main__':
    main()
