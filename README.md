# AWS EC2 Notes App (DevOps Training Project)

Deploy a simple **note-taking web application** on **AWS EC2** with:

- **Amazon Linux 2023**
- **MariaDB** for persistence
- **Gunicorn + Flask** for the app
- **Nginx** reverse proxy on port **80**
- A separate **EBS volume mounted at `/backup`** for database backups
- Automated backups using `mysqldump` → `/backup/mariadb/*.sql.gz`

---

## 1) Architecture

EC2 (Amazon Linux 2023)
- Flask app (Gunicorn) on `127.0.0.1:8000`
- Nginx on `:80` reverse proxy
- MariaDB local DB
- Extra EBS volume mounted at `/backup`
- Backup job: `mysqldump` → `/backup/mariadb/notesdb_YYYYmmdd_HHMMSS.sql.gz`

---

## 2) EC2 prerequisites

Security Group inbound rules:
- TCP **22** (SSH) from your IP
- TCP **80** (HTTP) from anywhere (for testing)

---

## 3) Install packages (Amazon Linux 2023)

```bash
sudo dnf -y update

# MariaDB on AL2023 uses versioned packages
sudo dnf -y install mariadb105-server mariadb105

# Web server
sudo dnf -y install nginx

# Python dependencies
sudo dnf -y install python3-pip

# Optional OS firewall (Security Group already controls 80/22)
sudo dnf -y install firewalld
```

Enable & start:

```bash
sudo systemctl enable --now mariadb
sudo systemctl enable --now nginx
sudo systemctl enable --now firewalld
```

If using `firewalld`, open HTTP:

```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --reload
```

---

## 4) MariaDB: secure + create DB/table/user

Secure:

```bash
sudo mysql_secure_installation
```

Create DB + user + table:

```bash
sudo mysql -u root -p
```

```sql
CREATE DATABASE notesdb CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

CREATE USER 'notesuser'@'localhost' IDENTIFIED BY 'ChangeMe_StrongPassword';
GRANT ALL PRIVILEGES ON notesdb.* TO 'notesuser'@'localhost';
FLUSH PRIVILEGES;

USE notesdb;

CREATE TABLE notes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  content TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

EXIT;
```

---

## 5) Mount the backup EBS volume at `/backup`

### 5.1 Attach a new EBS volume
- Create EBS volume in the **same AZ** as the EC2 instance
- Attach it to the instance (device name varies)

### 5.2 Identify disk
```bash
lsblk
```

### 5.3 Partition + format (example)
> Replace `/dev/nvme1n1` with your actual device.

```bash
sudo parted -s /dev/nvme1n1 mklabel gpt
sudo parted -s /dev/nvme1n1 mkpart primary 0% 100%
sudo mkfs.xfs -f /dev/nvme1n1p1
```

Mount:

```bash
sudo mkdir -p /backup
sudo mount /dev/nvme1n1p1 /backup
df -hT | grep /backup
```

Persist across reboot:

```bash
sudo blkid /dev/nvme1n1p1
sudo nano /etc/fstab
```

Add:

```
UUID=YOUR_UUID_HERE  /backup  xfs  defaults,nofail  0  2
```

Test:

```bash
sudo umount /backup
sudo mount -a
df -hT | grep /backup
```

Prepare folders:

```bash
sudo mkdir -p /backup/mariadb
sudo chown -R root:root /backup
sudo chmod 750 /backup /backup/mariadb
```

---

## 6) Deploy the web app

Create app directory:

```bash
sudo mkdir -p /opt/notesapp
sudo chown ec2-user:ec2-user /opt/notesapp
```

Copy project files into place:

```bash
# from your local clone (or scp) copy app/ into /opt/notesapp
cp -r app/* /opt/notesapp/
cd /opt/notesapp
```

Create venv + install deps:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -U pip
pip install -r requirements.txt
deactivate
```

---

## 7) systemd service (Gunicorn)

Copy service file:

```bash
sudo cp systemd/notesapp.service /etc/systemd/system/notesapp.service
```

Edit DB password in service:

```bash
sudo nano /etc/systemd/system/notesapp.service
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now notesapp
sudo systemctl status notesapp --no-pager
```

Local test:

```bash
curl -i http://127.0.0.1:8000/health
```

---

## 8) Nginx reverse proxy

Copy nginx config:

```bash
sudo cp nginx/notesapp.conf /etc/nginx/conf.d/notesapp.conf
sudo nginx -t
sudo systemctl reload nginx
```

Open in browser:

```
http://EC2_PUBLIC_IP/
```

---

## 9) Backups to `/backup`

Create credentials file for `mysqldump`:

```bash
sudo nano /etc/notesapp.cnf
```

```ini
[client]
user=notesuser
password=ChangeMe_StrongPassword
host=localhost
```

Secure it:

```bash
sudo chmod 600 /etc/notesapp.cnf
```

Install script:

```bash
sudo cp backup/backup_notesdb.sh /usr/local/bin/backup_notesdb.sh
sudo chmod 700 /usr/local/bin/backup_notesdb.sh
```

Test backup manually:

```bash
sudo /usr/local/bin/backup_notesdb.sh
ls -lh /backup/mariadb | tail
```

Schedule daily backup at 01:00:

```bash
sudo crontab -e
```

Add:

```cron
0 1 * * * /usr/local/bin/backup_notesdb.sh >/var/log/backup_notesdb.log 2>&1
```

---

## 10) Deliverable screenshots checklist

Take screenshots of:

```bash
systemctl status notesapp --no-pager
systemctl status nginx --no-pager
systemctl status mariadb --no-pager

mysql -u notesuser -p -e "USE notesdb; SHOW TABLES; DESCRIBE notes; SELECT * FROM notes ORDER BY created_at DESC LIMIT 5;"

lsblk
df -hT | grep /backup
cat /etc/fstab | grep /backup

ls -lh /backup/mariadb | tail
```

And one browser screenshot showing:
- Add note
- Note displayed with timestamp

---

## Repo structure

```
.
├── app/
│   ├── app.py
│   └── requirements.txt
├── systemd/
│   └── notesapp.service
├── nginx/
│   └── notesapp.conf
├── backup/
│   └── backup_notesdb.sh
└── README.md
```
