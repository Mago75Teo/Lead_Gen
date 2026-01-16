# Lead Scouting Agent (B2B) — progetto esportabile (FastAPI)

Agente AI “end-to-end” per **lead scouting, enrichment, decision maker discovery, email verification, scoring e export** (CSV/XLSX) con focus su **Bologna / Modena / Reggio Emilia**.

Funziona come:
- **API backend** (FastAPI) + UI minimale per test
- **Pipeline** ripetibile: Discover → Enrich → Identify → Verify → Score → Export
- Provider **plug-in**: search/news (Serper/NewsAPI), registri aziendali (OpenCorporates), email (Hunter/Verifier)
- Modulo opzionale **LLM** (OpenAI o Perplexity) per **personalizzazione su Teleimpianti S.p.A.** (o altra azienda di riferimento)

> **Compliance**: il repo evita scraping di piattaforme con ToS restrittive (es. LinkedIn). Per dati LinkedIn usa **API ufficiali**, export manuale o strumenti autorizzati.

---

## 1) Avvio rapido (locale)

```bash
git clone <repo>
cd lead-scouting-agent
cp .env.example .env
# Inserisci le API key che vuoi usare (minimo: SERPER oppure un provider a tua scelta)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Apri:
- UI test: http://localhost:8000/
- Swagger: http://localhost:8000/docs

---

## 2) Avvio rapido (Docker)

```bash
cp .env.example .env
docker compose up --build
```

---

## 3) Pipeline (API)

### 3.1 Discover (ricerca aziende con segnali di crescita)
```bash
curl -X POST "http://localhost:8000/discover" -H "Content-Type: application/json" -d '{
  "reference_company_url":"https://www.teleimpianti.it",
  "geography":{"country":"Italia","region":"Emilia-Romagna","provinces":["Bologna","Modena","Reggio Emilia"]},
  "industry":"logistica",
  "segment":{"type":"PMI","employees_min":50,"employees_max":500},
  "investment_window_months":[4,6],
  "allowed_channels":["email","linkedin"],
  "limit":30
}'
```

### 3.2 Run end-to-end (Discover→Export)
```bash
curl -X POST "http://localhost:8000/run" -H "Content-Type: application/json" -d '{
  "reference_company_url":"https://www.teleimpianti.it",
  "geography":{"country":"Italia","region":"Emilia-Romagna","provinces":["Bologna","Modena","Reggio Emilia"]},
  "industry":"produzione",
  "segment":{"type":"PMI","employees_min":50,"employees_max":500},
  "investment_window_months":[4,6],
  "allowed_channels":["email"],
  "limit":25,
  "include_email_drafts": true
}'
```

Output include:
- elenco lead + decision maker
- score
- link per download CSV/XLSX generato

---

## 4) Provider supportati (plug-in)

### Search / News
- **Serper.dev** (consigliato): `SERPER_API_KEY`
- (opzionale) **NewsAPI**: `NEWSAPI_KEY`
- (opzionale) **OpenCorporates**: `OPENCORPORATES_API_KEY`

### Email enrichment / verification
- **Hunter.io**: `HUNTER_API_KEY`
- Email verifier generico: `EMAIL_VERIFY_PROVIDER` + `EMAIL_VERIFY_API_KEY`

### LLM (opzionale)
- OpenAI: `OPENAI_API_KEY`, `OPENAI_MODEL`
- Perplexity: `PERPLEXITY_API_KEY`

---

## 5) Export (CRM-ready)

Colonne principali:
- Azienda, Settore, Provincia, Dimensione, Trigger di crescita (fonte), Budget stimato, Timing, Decision maker, Email verificata, Fonte contatto, Score, Stato

File generati in `data/exports/`.

---

## 6) Note su GDPR e contatti B2B
- Tratta solo dati **pubblici** e pertinenti; conserva l’evidenza (fonti) a supporto.
- Prediligi indirizzi **generici** (info@, commerciale@) se non hai base legale per il contatto nominale.
- Per campagne email, implementa **opt-out** e policy di conservazione.

Licenza: MIT

---
## 7) Stima budget (30k–50k+ più robusta)

Implementata in `app/pipeline/budget.py`.  
La stima è **euristica** e restituisce:
- `estimated_budget_eur` (valore indicativo)
- razionale in `company.evidences` (entry `budget_estimate`)

Segnali usati:
- dimensione (dipendenti/fatturato se disponibili)
- settore (moltiplicatore)
- numero evidenze (web/news/site)
- keyword su espansione/investimenti/commesse/ICT/sicurezza/automazione

---
## 8) Modulo opzionale “LinkedIn import” (facoltativo)

Endpoint:
- `POST /import/linkedin` (multipart/form-data: `file` CSV)

Supporta export connessioni e varianti di export lead list (match colonne flessibile).  
I lead importati sono “seed”: consigliato poi fare enrichment/verify o importarli direttamente nel CRM.

---
## 9) Deploy su Vercel

⚠️ **Errore “Serverless Function...250 MB”**

Vercel impone un limite massimo di **250 MB uncompressed** per bundle di una Function. Questa repo e' stata resa
piu' leggera per rientrare nel limite rimuovendo dipendenze Python molto pesanti (es. `pandas/numpy`, `lxml`,
vector store).

Inoltre e' incluso `.vercelignore` per evitare di caricare su Vercel file locali inutili (es. `data/`, cache, env).

Inclusi:
- `api/index.py`
- `vercel.json`

Passi:
1. Push su GitHub
2. Import repo su Vercel
3. Imposta env vars nel pannello (consigliato): `SERPER_API_KEY`, `HUNTER_API_KEY`, `OPENAI_API_KEY`, ecc.

Nota: la UI consente anche l’inserimento chiavi nella request (utile per test), ma in produzione è meglio usare env vars.

**Nota importante (Serverless filesystem):** su Vercel la directory del progetto è tipicamente "read-only"; per questo **cache/telemetry/export** usano `/tmp`.

Per il download file, la via più robusta è l’endpoint **`POST /export/download`** (generazione on-the-fly) e i bottoni **Scarica CSV/XLSX** in home. L’endpoint `/download/{filename}` resta come best-effort, ma non è garantito in ambienti serverless.

---
## 10) Deploy su AWS

### AWS Lambda + API Gateway (SAM)
Template: `aws/template.yaml`

Esempio:
```bash
cd aws
sam build
sam deploy --guided
```

### ECS/Fargate (Docker)
Usa `Dockerfile` e `docker-compose.yml` come base per containerizzare su ECS.

---
## 11) Project Profiles (dinamici dall’URL di riferimento)

Se `enable_project_profile=true`, la pipeline:
1) scarica e analizza il sito di riferimento (`reference_company_url`)
2) estrae un **Project Profile** (servizi/settori/tecnologie/proof points + range deal se deducibile)
3) usa il profilo per:
- calibrare la stima budget
- migliorare lo scoring “allineamento portfolio”
- personalizzare le bozze email con servizi e proof points coerenti

File:
- builder: `app/pipeline/project_profile.py`
- orchestrazione: `app/pipeline/orchestrator.py`

---
## 12) Perplexity API (alternativa per analisi web)

Puoi usare Perplexity in alternativa a Serper/NewsAPI per la fase Discover/News:
- env var: `PERPLEXITY_API_KEY`
- oppure in request/UI: `api_keys.perplexity_api_key`
- selezione provider: `api_keys.web_provider = auto|serper|perplexity|newsapi`

Provider implementato via Perplexity Search API (`POST https://api.perplexity.ai/search`).
In assenza di OpenAI, il builder Project Profile può usare Perplexity Chat Completions con output JSON schema.

---
## 13) Project Profile Cache (reset ogni 6 mesi)

Per evitare di rianalizzare ogni volta lo stesso sito di riferimento, i **Project Profiles** vengono cache-ati in SQLite con **TTL ~ 6 mesi (183 giorni)**.

- Implementazione: `app/profile_cache.py`
- Comportamento:
  - ad ogni build del profilo viene eseguita una purge delle entry scadute
  - se esiste una entry fresca, viene riusata
  - altrimenti viene rigenerata e salvata

Configurazione (env vars, opzionali):
- `PROFILE_CACHE_DB_PATH` (default: `./data/profile_cache.sqlite3`)
- `PROFILE_CACHE_TTL_DAYS` (default: `183`)

Nota serverless:
- su ambienti serverless lo storage locale può essere effimero; la cache è “best effort”.

---
## 14) Force refresh Project Profile + endpoint admin cache

### Force refresh (per singola run)
In `POST /run` puoi forzare il refresh del Project Profile ignorando la cache:
- `force_refresh_profile: true`

### Endpoint admin cache (best effort)
- `POST /admin/cache/purge` → elimina profili scaduti (TTL)
- `POST /admin/cache/flush` → svuota la cache

Gli endpoint sono protetti dal bearer token (uguale agli altri endpoint, se attivo).

---
## Wizard mapping colonne per CSV LinkedIn import

Nella UI (`/`) la sezione **Import LinkedIn** include un wizard che:
1) legge le intestazioni del CSV
2) permette di mappare le colonne ai campi standard:
   - first_name, last_name, company, position, email, linkedin_url, website
3) invia la mappatura al backend (`/import/linkedin`) nel field `mapping` (JSON in multipart)

Se una colonna non viene mappata, il parser prova comunque l’auto-detection.

---
## Modalità “Teleimpianti preset”

Se imposti `preset="teleimpianti"` (da UI o via API):
- **Discover**: arricchisce le query con keyword più forti sul vertical (videosorveglianza/impianti/ICT)
- **Budget**: aggiunge keyword-boost specifici (pattern/boost in YAML)
- **Scoring**: migliora “allineamento portfolio” anche quando il Project Profile non è disponibile
- **Email drafts**: include proof points base del preset se non c’è un Project Profile

Config del preset:
- `config/presets/teleimpianti.yaml`

Nota: la modalità preset **non disattiva** l’auto-detection dal sito: il Project Profile resta la fonte primaria quando disponibile.

---
## Preset disponibili

Puoi selezionare un preset da UI o passare `preset` nel payload di `/run`.

- `teleimpianti` — Teleimpianti
- `produzione` — Produzione
- `logistica` — Logistica
- `trasporti_distribuzione` — Trasporti e distribuzione
- `retail` — Retail
- `banche` — Banche e assicurazioni
- `hospitality` — Hospitality
- `automotive` — Automotive
- `aerospace_difesa` — Aerospace e difesa
- `edilizia` — Edilizia e cantieri
- `eventi_musei` — Strutture eventi e musei
- `studi_tecnici_categoria` — Studi tecnici e associazioni di categoria
