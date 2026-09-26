#!/bin/bash
DATE=$(date +%d-%m-%Y)
BACKUP_DIR="/tmp/backup_duxsalary_$DATE"
mkdir -p $BACKUP_DIR

# Backup BDD
sudo -u postgres pg_dump duxsalary > $BACKUP_DIR/database.sql

# Backup fichiers importants
cp /var/www/duxsalary/moteur_paie.py $BACKUP_DIR/
cp /var/www/duxsalary/cp_data.py $BACKUP_DIR/
cp /var/www/duxsalary/app.py $BACKUP_DIR/
cp /var/www/duxsalary/.env $BACKUP_DIR/

# Compression
tar -czf /tmp/backup_duxsalary_$DATE.tar.gz -C /tmp backup_duxsalary_$DATE

# Envoi email
python3 << 'PYEOF'
import smtplib, os
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from dotenv import load_dotenv
load_dotenv('/var/www/duxsalary/.env')

date = os.popen('date +%d/%m/%Y').read().strip()
filepath = f"/tmp/backup_duxsalary_{os.popen('date +%d-%m-%Y').read().strip()}.tar.gz"

msg = MIMEMultipart()
msg['Subject'] = f"[DuxSalary] Backup automatique — {date}"
msg['From'] = os.getenv('SMTP_FROM')
msg['To'] = os.getenv('NOTIFY_EMAIL')
msg.attach(MIMEText(f"Backup automatique DuxSalary du {date}. Conservez cet email en lieu sûr.", 'plain'))

with open(filepath, 'rb') as f:
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename=backup_{date.replace("/","-")}.tar.gz')
    msg.attach(part)

with smtplib.SMTP(os.getenv('SMTP_HOST'), int(os.getenv('SMTP_PORT', 587))) as s:
    s.starttls()
    s.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD'))
    s.sendmail(msg['From'], msg['To'], msg.as_string())
    print(f"Backup envoyé — {date}")
PYEOF

# Nettoyage
rm -rf $BACKUP_DIR /tmp/backup_duxsalary_*.tar.gz
