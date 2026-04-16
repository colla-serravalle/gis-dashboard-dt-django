# Documento di Design del Software
## Reports Serravalle — Ambiente di Produzione

---

| Campo              | Valore                             |
|--------------------|------------------------------------|
| **ID Documento**   | SDD-PROD-001                       |
| **Versione**       | 1.0                                |
| **Data**           | 2026-04-15                         |
| **Applicazione**   | Reports Serravalle                 |
| **Autore**         | Stefano Colla                      |
| **Stato**          | Rilasciato                         |

---

### Storico delle Revisioni

| Versione | Data       | Autore         | Descrizione              |
|----------|------------|----------------|--------------------------|
| 1.0      | 2026-04-15 | Stefano Colla  | Prima emissione          |

### Revisori

| Nome | Ruolo | Data |
|------|-------|------|
|      |       |      |

---

## Indice

1. [Introduzione](#1-introduzione)
2. [Panoramica del Sistema](#2-panoramica-del-sistema)
3. [Componenti del Sistema](#3-componenti-del-sistema)
4. [Design di Dettaglio](#4-design-di-dettaglio)

---

## 1. Introduzione

### 1.1 Scopo

Questo documento descrive l'architettura di produzione e il design di dettaglio dell'applicazione Reports Serravalle, distribuita su una macchina virtuale on-premises tramite Docker. Costituisce il riferimento autorevole per la configurazione dell'infrastruttura, le interazioni tra servizi e le procedure operative.

### 1.2 Ambito

Il documento copre:

- Lo stack di produzione containerizzato (Nginx, Django/Gunicorn, PostgreSQL, Redis)
- La gestione della rete e dei volumi Docker
- I controlli di sicurezza a livello infrastrutturale e applicativo
- Le integrazioni esterne (ArcGIS Enterprise, Azure AD OIDC)
- Il logging e l'osservabilità
- Le procedure di manutenzione (rinnovo certificato TLS)

### 1.3 Definizioni e Abbreviazioni

| Termine    | Definizione                                                                    |
|------------|--------------------------------------------------------------------------------|
| OIDC       | OpenID Connect — protocollo di identità utilizzato per l'autenticazione Azure AD |
| ArcGIS     | Esri ArcGIS Enterprise — piattaforma GIS che fornisce dati dei feature layer    |
| Gunicorn   | Server HTTP WSGI Python utilizzato per servire l'applicazione Django            |
| uv         | Package manager Python per la gestione delle dipendenze e l'esecuzione dei comandi |
| CSP        | Content Security Policy                                                         |
| SCRAM      | Salted Challenge Response Authentication Mechanism (autenticazione PostgreSQL)  |
| TLS        | Transport Layer Security — protocollo di crittografia per le comunicazioni HTTPS |

### 1.4 Riferimenti

- Documentazione Django: https://docs.djangoproject.com
- mozilla-django-oidc: https://mozilla-django-oidc.readthedocs.io
- Specifica Docker Compose: https://docs.docker.com/compose
- Integrazione Azure AD OIDC: `docs/2026-02-27-azure_auth_integration.md`

---

## 2. Panoramica del Sistema

### 2.1 Sintesi dell'Architettura

Reports Serravalle è un'applicazione web Django 6 che interroga i feature layer di ArcGIS Enterprise e presenta i dati dei rapporti di ispezione sul campo agli utenti autenticati. In produzione viene eseguita come stack completamente containerizzato su una VM Linux on-premises, orchestrato con Docker Compose.

Tutto il traffico in ingresso transita attraverso Nginx, che termina TLS e inoltra le richieste a Gunicorn sulla rete bridge Docker interna. PostgreSQL fornisce lo storage relazionale persistente per i modelli Django, le sessioni e i dati di audit. Redis fornisce una cache in memoria per i token di autenticazione ArcGIS e il framework cache di Django.

### 2.2 Struttura dello Stack Docker

```
VM Host  (Linux, Docker Engine)
│
├── docker-compose.prod.yml
│
├── [rete bridge: backend]
│   │
│   ├── nginx          (porte 80, 443 → host)
│   │     ├── Terminazione TLS (star_serravalle_it_2025)
│   │     ├── Redirect HTTP → HTTPS
│   │     ├── Servizio file statici (/static/)
│   │     └── Reverse proxy → app:8000
│   │
│   ├── app            (Django 6 / Gunicorn)
│   │     ├── 3 worker × 4 thread = 12 richieste concorrenti
│   │     ├── Legge: postgres-data (via db), redis (cache)
│   │     ├── Scrive: volume static-files (collectstatic)
│   │     └── Scrive: volume app-logs
│   │
│   ├── db             (PostgreSQL 16-alpine)
│   │     └── Scrive: volume postgres-data
│   │
│   └── redis          (Redis 7-alpine)
│         └── Solo in memoria (maxmemory 256 MB, allkeys-lru)
│
├── [volumi]
│   ├── postgres-data   → /var/lib/postgresql/data
│   ├── static-files    → /app/staticfiles (app rw, nginx ro)
│   └── app-logs        → /app/logs
│
└── [dipendenze esterne]
    ├── gisserver.serravalle.it:443   (ArcGIS Enterprise)
    └── login.microsoftonline.com     (Azure AD / OIDC)
```

### 2.3 Flusso delle Richieste

```
Browser
  │  HTTPS :443
  ▼
Nginx (terminazione TLS)
  │  HTTP  :8000 (proxy_pass)
  ▼
Gunicorn (WSGI)
  │
  ▼
Stack middleware Django
  ├── SecurityMiddleware
  ├── SessionRefresh (rinnovo token OIDC)
  ├── ServiceAccessMiddleware (autorizzazione per gruppo)
  └── Logica di vista
        ├── PostgreSQL (query ORM)
        ├── Redis (cache token ArcGIS / cache Django)
        └── ArcGIS REST API (HTTPS in uscita)
```

---

## 3. Componenti del Sistema

### 3.1 Nginx (Reverse Proxy)

| Proprietà        | Valore                                          |
|------------------|-------------------------------------------------|
| Immagine         | Custom — costruita da `docker/nginx/Dockerfile` |
| Immagine base    | `nginx:alpine`                                  |
| Porte esposte    | `80` (redirect), `443` (TLS)                    |
| Dipende da       | `app` (healthy)                                 |
| Restart policy   | `unless-stopped`                                |

**Responsabilità:**

- Terminare TLS tramite il certificato wildcard `star_serravalle_it_2025`
- Redirigere tutto il traffico HTTP verso HTTPS (301)
- Servire i file statici Django dal volume condiviso `static-files`
- Limitare le richieste in ingresso: 10 req/s per IP, burst 20
- Inoltrare le richieste applicative ad `app:8000` via reverse proxy
- Iniettare header di sicurezza: `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`, `Referrer-Policy`
- Inoltrare `X-Forwarded-Proto: https` a Django per la corretta rilevazione dello schema URL

### 3.2 Applicazione Django (app)

| Proprietà        | Valore                                                     |
|------------------|------------------------------------------------------------|
| Immagine         | Custom — costruita da `docker/app/Dockerfile`              |
| Immagine base    | `python:3.13-slim`                                         |
| Utente runtime   | `reports_user` (UID 1000, senza home directory)            |
| Package manager  | `uv` — tutti i comandi prefissati con `uv run`             |
| Server WSGI      | Gunicorn                                                   |
| Indirizzo listen | `0.0.0.0:8000` (solo interno, non esposto all'host)        |
| Dipende da       | `db` (healthy), `redis` (healthy)                          |
| Restart policy   | `unless-stopped`                                           |

**Configurazione Gunicorn (`docker/app/gunicorn.conf.py`):**

| Parametro             | Valore                                    |
|-----------------------|-------------------------------------------|
| workers               | 3                                         |
| worker_class          | gthread                                   |
| threads               | 4                                         |
| timeout               | 120s                                      |
| max_requests          | 1000                                      |
| max_requests_jitter   | 50                                        |
| worker_tmp_dir        | /tmp                                      |
| accesslog / errorlog  | stdout / stderr (→ Docker logs)           |

**Processo di build:**

1. Installazione dipendenze di sistema (libpq, gcc, libcairo2, pkg-config, libgirepository)
2. Sincronizzazione dipendenze Python via `uv sync --frozen --no-dev`
3. Copia del codice applicativo
4. Esecuzione `collectstatic` a build time con `SECRET_KEY` dummy
5. Creazione directory log e static con proprietà corrette
6. Il container viene eseguito come `reports_user`

### 3.3 PostgreSQL (db)

| Proprietà          | Valore                                  |
|--------------------|-----------------------------------------|
| Immagine           | `postgres:16-alpine`                    |
| Metodo di auth     | SCRAM-SHA-256                           |
| Max connessioni    | 50                                      |
| Restart policy     | `unless-stopped`                        |
| Persistenza        | Volume named `postgres-data`            |
| Health check       | `pg_isready` ogni 10s                   |

**Audit logging abilitato:**

- `log_connections = on`
- `log_disconnections = on`
- `log_statement = ddl`

**Tabelle Django utilizzate:**

- `auth_user`, `auth_group`, `auth_permission` — gestione utenti e gruppi
- `django_session` — storage sessioni lato server
- `authorization_service` — mappature servizio-gruppo di accesso
- `accounts_*` — dati profilo utente

### 3.4 Redis (redis)

| Proprietà          | Valore                                        |
|--------------------|-----------------------------------------------|
| Immagine           | `redis:7-alpine`                              |
| Memoria massima    | 256 MB                                        |
| Policy di eviction | `allkeys-lru`                                 |
| Autenticazione     | `requirepass` (password da `.env.prod`)       |
| Restart policy     | `unless-stopped`                              |
| Health check       | `redis-cli ping` ogni 10s                     |
| Persistenza        | Nessuna (solo in memoria)                     |

**Comandi disabilitati (hardening sicurezza):**

- `FLUSHALL`, `FLUSHDB`, `DEBUG` — rinominati a stringa vuota

**Utilizzo cache Django:**

- Token di autenticazione ArcGIS (TTL = durata token − 1 minuto)
- Mapping CSV campi ArcGIS (TTL = `ARCGIS_MAPPING_CACHE_TIMEOUT`, default 300s)

---

## 4. Design di Dettaglio

### 4.1 Autenticazione — Azure AD OIDC

L'autenticazione è delegata ad Azure Active Directory tramite il protocollo OpenID Connect, implementato con `mozilla-django-oidc`.

**Flusso:**

1. L'utente non autenticato accede a un URL protetto
2. Django reindirizza a `/auth/login/`
3. L'utente clicca "Login con Azure" → reindirizzato a `/oidc/authenticate/`
4. `mozilla-django-oidc` reindirizza all'endpoint di autorizzazione Azure AD
5. Azure AD autentica l'utente e reindirizza a `/oidc/callback/`
6. Django valida il token, crea o aggiorna il record utente locale
7. Il middleware `SessionRefresh` rinnova silenziosamente il token OIDC ogni 15 minuti

**Configurazione principale:**

| Impostazione                         | Valore                                             |
|--------------------------------------|----------------------------------------------------|
| `OIDC_RP_SIGN_ALGO`                  | RS256                                              |
| `OIDC_RP_SCOPES`                     | openid email profile                               |
| `OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS` | 900 (15 min)                                       |
| `SESSION_COOKIE_SAMESITE`            | Lax (necessario per i redirect OIDC)               |
| `CSRF_COOKIE_SAMESITE`               | Strict                                             |
| `SECURE_PROXY_SSL_HEADER`            | `HTTP_X_FORWARDED_PROTO: https`                    |
| `USE_X_FORWARDED_HOST`               | True                                               |
| `CSRF_TRUSTED_ORIGINS`               | `https://reports.serravalle.it`                    |

**Requisiti Azure App Registration:**

- URI di reindirizzamento: `https://reports.serravalle.it/oidc/callback/`
- Tipo token: ID token (RS256)
- Scope concessi: `openid`, `email`, `profile`

### 4.2 Autorizzazione ai Servizi

Il controllo degli accessi è applicato a livello di namespace URL da `ServiceAccessMiddleware`. Ogni record del modello `Service` mappa un namespace applicativo Django (`app_label`) a uno o più oggetti `auth.Group`.

| Servizio     | App Label    | Gruppi autorizzati                             |
|--------------|--------------|------------------------------------------------|
| Dashboard    | `core`       | `dashboard_users`, `managers`                  |
| Reports      | `reports`    | `reports_users`, `managers`                    |
| Reports API  | `reports_api`| `reports_users`, `managers`                    |
| Profiles     | `profiles`   | `dashboard_users`, `reports_users`, `managers` |

I superutenti bypassano tutti i controlli. Gli URL sotto namespace esenti (`admin`, `oidc`, `accounts`, `authorization`) non vengono mai verificati.

### 4.3 Integrazione ArcGIS

L'applicazione si connette ad ArcGIS Enterprise (`gisserver.serravalle.it:443`) per i dati dei feature layer e il recupero degli allegati.

**Gestione token:**

1. Alla prima richiesta, `ArcGISService` chiama `/portal/sharing/rest/generateToken` con `ARCGIS_USERNAME` e `ARCGIS_PASSWORD`
2. Il token viene messo in cache su Redis per tutta la sua durata meno 1 minuto
3. Le richieste successive usano il token in cache — nessuna ri-autenticazione
4. La verifica SSL usa `truststore` per delegare al certificate store del sistema operativo (gestisce CA interne/aziendali)

**Requisiti di rete in uscita:**

| Destinazione                     | Porta | Protocollo |
|----------------------------------|-------|------------|
| `gisserver.serravalle.it`        | 443   | HTTPS      |
| `login.microsoftonline.com`      | 443   | HTTPS      |
| `graph.microsoft.com`            | 443   | HTTPS      |

### 4.4 File Statici

I file statici vengono raccolti a build time (`collectstatic`) e salvati nel volume Docker named `static-files`. Nginx li serve direttamente da questo volume senza passare per Gunicorn.

| Impostazione          | Valore                               |
|-----------------------|--------------------------------------|
| Output a build time   | `/app/staticfiles`                   |
| Volume                | `static-files`                       |
| Path Nginx            | `/static/` → `/app/staticfiles/`     |
| Cache-Control         | `public, immutable`, scadenza 30 gg  |

### 4.5 Logging

I log applicativi vengono scritti nel volume named `app-logs` in `/app/logs` all'interno del container. I log di accesso ed errore di Gunicorn vanno su stdout/stderr e sono accessibili via `docker compose logs`.

| File di log   | Handler                               | Rotazione          | Contenuto                               |
|---------------|---------------------------------------|--------------------|-----------------------------------------|
| `app.log`     | `CompressedRotatingFileHandler`       | 10 MB / 5 backup   | Eventi applicativi (logger `apps.*`)    |
| `audit.log`   | `WindowsSafeTimedRotatingFileHandler` | Giornaliera / 365 gg | Audit NIS2 in formato JSON            |
| `arcgis.log`  | File handler                          | —                  | Errori token e API ArcGIS               |
| `django.log`  | `CompressedRotatingFileHandler`       | 10 MB / 5 backup   | Errori di sistema e richieste Django    |

**Livello di log:** Controllato dalla variabile d'ambiente `LOG_LEVEL` (default: `INFO`).

**Accesso dall'host:**

```bash
LOG_DIR=$(sudo docker volume inspect $(docker volume ls -q | grep app-logs) \
  --format '{{ .Mountpoint }}')
sudo tail -f $LOG_DIR/app.log
sudo tail -f $LOG_DIR/audit.log
sudo tail -f $LOG_DIR/arcgis.log
```

### 4.6 Riepilogo Controlli di Sicurezza

| Livello      | Controllo                                                                         |
|--------------|-----------------------------------------------------------------------------------|
| Rete         | Solo porte 80 e 443 esposte all'host; traffico inter-servizio su bridge interno   |
| TLS          | Solo TLSv1.2/1.3; cipher suite forti; session ticket disabilitati                 |
| Header HTTP  | X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy       |
| Rate limiting| 10 req/s per IP, burst 20 (Nginx)                                                 |
| CSRF         | Middleware CSRF Django; `CSRF_TRUSTED_ORIGINS` impostato al dominio prod          |
| Auth         | Azure AD OIDC; nessun login locale tranne superutente Django admin                |
| Container    | Utente non-root `reports_user` (UID 1000); senza home directory                   |
| Database     | Cifratura password SCRAM-SHA-256; audit logging DDL abilitato                     |
| Redis        | Protetto da password; comandi distruttivi disabilitati                            |
| Segreti      | Tutti i segreti in `.env.prod` (non committato nel version control)               |

### 4.7 Variabili d'Ambiente

| Variabile                   | Obbligatoria | Descrizione                                          |
|-----------------------------|--------------|------------------------------------------------------|
| `SECRET_KEY`                | Sì           | Chiave segreta Django                                |
| `DEBUG`                     | Sì           | Deve essere `False` in produzione                    |
| `ALLOWED_HOSTS`             | Sì           | Hostname separati da virgola                         |
| `CSRF_TRUSTED_ORIGINS`      | Sì           | Origini attendibili con schema (es. https://...)     |
| `DATABASE_URL`              | Sì           | Stringa di connessione PostgreSQL                    |
| `POSTGRES_USER`             | Sì           | Username PostgreSQL                                  |
| `POSTGRES_PASSWORD`         | Sì           | Password PostgreSQL                                  |
| `POSTGRES_DB`               | Sì           | Nome database PostgreSQL                             |
| `REDIS_URL`                 | Sì           | Stringa di connessione Redis                         |
| `REDIS_PASSWORD`            | Sì           | Password AUTH Redis                                  |
| `AZURE_TENANT_ID`           | Sì           | UUID tenant Azure AD                                 |
| `AZURE_CLIENT_ID`           | Sì           | Client ID applicazione Azure AD                      |
| `AZURE_CLIENT_SECRET`       | Sì           | Client secret applicazione Azure AD                  |
| `ARCGIS_USERNAME`           | Sì           | Username portale ArcGIS Enterprise                   |
| `ARCGIS_PASSWORD`           | Sì           | Password portale ArcGIS Enterprise                   |
| `ARCGIS_PORTAL_TOKEN_URL`   | No           | Endpoint generazione token (default: derivato da env)|
| `ARCGIS_FEATURE_SERVICE_URL`| No           | URL base del feature service                         |
| `LOG_LEVEL`                 | No           | Livello di logging (default: `INFO`)                 |
| `SESSION_TIMEOUT`           | No           | TTL sessione in secondi (default: `3600`)            |

---

### 4.8 Procedura di Rinnovo del Certificato TLS

Il certificato wildcard `*.serravalle.it` è collocato in `docker/nginx/ssl/`. Alla scadenza è necessario rinnovarlo seguendo la procedura sotto. **L'applicazione resterà operativa fino alla sostituzione — il downtime è limitato al solo riavvio di Nginx (pochi secondi).**

#### 4.8.1 File coinvolti

| File                                          | Descrizione                        |
|-----------------------------------------------|------------------------------------|
| `docker/nginx/ssl/star_serravalle_it.crt`| Certificato (catena completa)      |
| `docker/nginx/ssl/star_serravalle_it.key`| Chiave privata                     |

> **Nota:** I file `.crt` e `.key` sono elencati in `.gitignore` e non sono committati nel repository.

#### 4.8.2 Verifica scadenza

Controllare la scadenza del certificato attivo:

```bash
# Dall'host — verifica sul file
openssl x509 -enddate -noout \
  -in docker/nginx/ssl/star_serravalle_it.crt

# Dal container Nginx (certificato in uso dal processo live)
docker compose --env-file .env.prod -f docker-compose.prod.yml exec nginx \
  openssl x509 -enddate -noout \
  -in /etc/nginx/ssl/star_serravalle_it.crt
```

#### 4.8.3 Sostituzione del certificato

**Step 1 — Ottenere il nuovo certificato**

Richiedere il nuovo certificato wildcard `*.serravalle.it` all'ente di certificazione (CA) interno o esterno. Sono necessari:

- Il file `.crt` con la catena completa (certificato + intermediate CA)
- Il file `.key` con la chiave privata corrispondente

**Step 2 — Verificare il nuovo certificato prima di installarlo**

```bash
# Verificare che il certificato e la chiave corrispondano
openssl x509 -noout -modulus -in nuovo_certificato.crt | md5sum
openssl rsa  -noout -modulus -in nuova_chiave.key       | md5sum
# I due hash MD5 devono essere identici

# Verificare la catena
openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt nuovo_certificato.crt

# Verificare la data di scadenza del nuovo certificato
openssl x509 -enddate -noout -in nuovo_certificato.crt
```

**Step 3 — Copiare i nuovi file sul server**

```bash
# Dall'host, nella directory del progetto
cp /percorso/nuovo_certificato.crt  docker/nginx/ssl/star_serravalle_it_2025.crt
cp /percorso/nuova_chiave.key       docker/nginx/ssl/star_serravalle_it_2025.key

# Verificare i permessi
chmod 644 docker/nginx/ssl/star_serravalle_it.crt
chmod 600 docker/nginx/ssl/star_serravalle_it.key
```

**Step 4 — Ricostruire e riavviare Nginx**

Il certificato è copiato nell'immagine Nginx durante il build. È necessario ricostruire l'immagine:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml build nginx --no-cache
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d nginx
```

**Step 5 — Verificare il certificato in produzione**

```bash
# Verifica SSL dal browser o da riga di comando
openssl s_client -connect reports.serravalle.it:443 -servername reports.serravalle.it \
  </dev/null 2>/dev/null | openssl x509 -noout -dates

# Oppure con curl
curl -vI https://reports.serravalle.it 2>&1 | grep -E "expire|issuer|subject"
```

#### 4.8.4 Rollback

In caso di problemi con il nuovo certificato, ripristinare il precedente:

```bash
# Ripristinare i file originali (se conservati in backup)
cp backup/star_serravalle_it_2025.crt docker/nginx/ssl/star_serravalle_it_2025.crt
cp backup/star_serravalle_it_2025.key docker/nginx/ssl/star_serravalle_it_2025.key

docker compose --env-file .env.prod -f docker-compose.prod.yml build nginx --no-cache
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d nginx
```

#### 4.8.5 Aggiornamento nome file (opzionale)

Se si desidera rinominare il file per riflettere l'anno del nuovo certificato (es. `star_serravalle_it_2026.crt`), aggiornare anche il percorso in `docker/nginx/nginx.conf`:

```nginx
ssl_certificate     /etc/nginx/ssl/star_serravalle_it.crt;
ssl_certificate_key /etc/nginx/ssl/star_serravalle_it.key;
```

E nel `docker/nginx/Dockerfile` la riga `COPY` corrispondente. Ricostruire l'immagine Nginx dopo la modifica.
