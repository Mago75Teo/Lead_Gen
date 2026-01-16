from __future__ import annotations
import io
import json
import os
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from pathlib import Path
from typing import Any, Dict, List

from .settings import settings
from .security import require_bearer
from .config_loader import load_focus_config
from .telemetry import init_db, log_event, TelemetryEvent
from .models import (
    DiscoverRequest, EnrichRequest, IdentifyRequest, VerifyRequest, ScoreRequest, ExportRequest, RunRequest, RunResponse,
    CompanyCandidate, CompanyProfile, LeadRecord
)
from .pipeline.discover import discover_candidates
from .pipeline.enrich import enrich_candidates
from .pipeline.identify import identify_for_companies
from .pipeline.verify import verify_leads
from .pipeline.score import score_leads
from .pipeline.exporter import export_leads, export_leads_bytes, EXPORT_DIR
from .pipeline.orchestrator import run_pipeline
from .profile_cache import purge_expired, flush_cache
from .pipeline.linkedin_import import parse_linkedin_csv

app = FastAPI(title="Lead Scouting Agent (B2B)", version="0.1.0")
FOCUS = load_focus_config(settings.FOCUS_CONFIG_PATH)

if FOCUS.telemetry_enabled:
    init_db()

@app.get("/", response_class=HTMLResponse)
async def index():
    html = """<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Lead Scouting Agent</title>
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:24px;max-width:1100px}
.card{border:1px solid #ddd;border-radius:14px;padding:16px;margin-top:14px}
input,select,textarea{width:100%;padding:10px;border-radius:10px;border:1px solid #ddd;box-sizing:border-box}
textarea{height:140px}
button{padding:10px 14px;border-radius:10px;border:1px solid #222;background:#222;color:#fff;cursor:pointer}
small{color:#666}
pre{white-space:pre-wrap}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
hr{border:none;border-top:1px solid #eee;margin:16px 0}
label{font-weight:600;font-size:13px}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;border:1px solid #ddd;font-size:12px}
</style>
</head>
<body>
<h1>Lead Scouting Agent (B2B)</h1>
<p><small>Config: <code>%%FOCUS_CONFIG_PATH%%</code> — Agent: <b>%%AGENT_NAME%%</b></small></p>

<div class="card">
  <h2>Run end-to-end</h2>
  <div class="grid">
    <div><label>Sito di riferimento</label><input id="ref_url" value="%%REF_URL%%"/></div>
    <div><label>Preset (opzionale)</label>
      <select id="preset">
        <option value="" selected>(none)</option>
        <option value="teleimpianti">Teleimpianti</option>
        <option value="produzione">Produzione</option>
        <option value="logistica">Logistica</option>
        <option value="trasporti_distribuzione">Trasporti e distribuzione</option>
        <option value="retail">Retail</option>
        <option value="banche">Banche e assicurazioni</option>
        <option value="hospitality">Hospitality</option>
        <option value="automotive">Automotive</option>
        <option value="aerospace_difesa">Aerospace e difesa</option>
        <option value="edilizia">Edilizia e cantieri</option>
        <option value="eventi_musei">Strutture eventi e musei</option>
        <option value="studi_tecnici_categoria">Studi tecnici e associazioni di categoria</option>
      </select>
    </div>

    <div><label>Settore merceologico</label><input id="industry" value="produzione"/></div>
    <div><label>Paese</label><input id="country" value="Italia"/></div>
    <div><label>Regione</label><input id="region" value="Emilia-Romagna"/></div>
    <div><label>Province (CSV)</label><input id="provs" value="Bologna,Modena,Reggio Emilia"/></div>

    <div><label>Segmento</label>
      <select id="segtype"><option>PMI</option><option>Enterprise</option><option selected>Unknown</option></select>
    </div>
    <div><label>Dipendenti min</label><input id="emp_min" value="50"/></div>
    <div><label>Dipendenti max</label><input id="emp_max" value="500"/></div>

    <div><label>Finestra investimento (mesi, es. 4,6)</label><input id="win" value="4,6"/></div>
    <div><label>Canali consentiti (CSV)</label><input id="channels" value="email,linkedin"/></div>
    <div><label>Limit aziende</label><input id="limit" value="20"/></div>

    <div><label>Includi bozze email (OpenAI/Perplexity)</label>
      <select id="drafts"><option value="false" selected>false</option><option value="true">true</option></select>
    </div>
  </div>

  <hr/>
  <h3>Impostazioni avanzate</h3>
  <div class="grid" style="margin-top:8px">
    <div><label>Web provider (auto/serper/perplexity/newsapi)</label><input id="k_webprov" value="auto"/></div>
    <div><label>Project Profiles (abilita)</label>
      <select id="prof_on"><option value="true" selected>true</option><option value="false">false</option></select>
    </div>
    <div><label>Force refresh profile (ignora cache)</label>
      <select id="prof_refresh"><option value="false" selected>false</option><option value="true">true</option></select>
    </div>
  </div>

  <hr/>
  <h3>API Keys (facoltative)</h3>
  <p><small>Per test: puoi inserire chiavi qui (verranno inviate al backend). In produzione: usa env vars su Vercel/AWS.</small></p>
  <div class="grid">
    <div><label>Serper API Key</label><input id="k_serper" placeholder="SERPER_API_KEY"/></div>
    <div><label>Perplexity API Key</label><input id="k_pplx" placeholder="PERPLEXITY_API_KEY"/></div>
    <div><label>NewsAPI Key</label><input id="k_newsapi" placeholder="NEWSAPI_KEY"/></div>
    <div><label>Hunter API Key</label><input id="k_hunter" placeholder="HUNTER_API_KEY"/></div>
    <div><label>OpenCorporates API Key</label><input id="k_openc" placeholder="OPENCORPORATES_API_KEY"/></div>
    <div><label>OpenAI API Key</label><input id="k_openai" placeholder="OPENAI_API_KEY"/></div>
    <div><label>OpenAI Model</label><input id="k_model" value="gpt-4o-mini"/></div>
  </div>

  <p style="margin-top:14px">
    <button onclick="run()">Esegui pipeline</button>
    <button id="btn_csv" onclick="downloadExport("csv")" disabled>Scarica CSV</button>
    <button id="btn_xlsx" onclick="downloadExport("xlsx")" disabled>Scarica XLSX</button>
  </p>
  <h3>Risultato</h3>
  <pre id="out"></pre>
</div>

<div class="card">
  <h2>Import LinkedIn (opzionale)</h2>
  <p><small><b>Wizard mapping colonne:</b> dopo aver scelto il CSV, puoi mappare le colonne ai campi standard. Se lasci un campo su <span class="badge">(auto)</span> il parser prova ad auto-detectare.</small></p>
  <input type="file" id="li_file" accept=".csv" onchange="previewCsvHeaders()"/>

  <div id="map_box" style="display:none;margin-top:12px">
    <div class="grid">
      <div><label>First name</label><select id="m_first"></select></div>
      <div><label>Last name</label><select id="m_last"></select></div>
      <div><label>Company</label><select id="m_company"></select></div>
      <div><label>Position/Title</label><select id="m_pos"></select></div>
      <div><label>Email</label><select id="m_email"></select></div>
      <div><label>LinkedIn URL</label><select id="m_li"></select></div>
      <div><label>Website</label><select id="m_site"></select></div>
    </div>
  </div>

  <p style="margin-top:14px"><button onclick="importLinkedIn()">Importa CSV</button></p>
  <pre id="li_out"></pre>
</div>

<script>
function csvToList(v){ return v.split(',').map(s=>s.trim()).filter(Boolean); }

function buildPayload(){
  return {
    preset: (document.getElementById('preset').value || null),
    enable_project_profile: document.getElementById('prof_on').value === 'true',
    force_refresh_profile: document.getElementById('prof_refresh').value === 'true',
    reference_company_url: document.getElementById('ref_url').value,
    geography: {
      country: document.getElementById('country').value,
      region: document.getElementById('region').value,
      provinces: csvToList(document.getElementById('provs').value)
    },
    industry: document.getElementById('industry').value,
    segment: {
      type: document.getElementById('segtype').value,
      employees_min: parseInt(document.getElementById('emp_min').value || "0") || null,
      employees_max: parseInt(document.getElementById('emp_max').value || "0") || null
    },
    investment_window_months: csvToList(document.getElementById('win').value).map(x=>parseInt(x)).filter(x=>!isNaN(x)),
    allowed_channels: csvToList(document.getElementById('channels').value),
    limit: parseInt(document.getElementById('limit').value || "20"),
    include_email_drafts: document.getElementById('drafts').value === "true",
    session_id: "ui",
    api_keys: {
      serper_api_key: document.getElementById('k_serper').value || null,
      perplexity_api_key: document.getElementById('k_pplx').value || null,
      newsapi_key: document.getElementById('k_newsapi').value || null,
      hunter_api_key: document.getElementById('k_hunter').value || null,
      opencorporates_api_key: document.getElementById('k_openc').value || null,
      openai_api_key: document.getElementById('k_openai').value || null,
      openai_model: document.getElementById('k_model').value || null,
      web_provider: document.getElementById('k_webprov').value || 'auto'
    }
  };
}

async function run(){
  const out = document.getElementById('out');
  out.textContent = "Elaborazione...";
  const r = await fetch('/run', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(buildPayload())});
  const j = await r.json();
  window.lastRun = j;
  const ok = !!(j && j.leads && j.leads.length);
  document.getElementById('btn_csv').disabled = !ok;
  document.getElementById('btn_xlsx').disabled = !ok;
  out.textContent = JSON.stringify(j, null, 2);
}

async function downloadExport(fmt){
  if(!window.lastRun || !window.lastRun.leads || !window.lastRun.leads.length){
    alert('Esegui prima la pipeline.');
    return;
  }
  const payload = {leads: window.lastRun.leads, file_format: fmt, session_id: 'ui'};
  const r = await fetch('/export/download', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
  if(!r.ok){
    const t = await r.text();
    alert('Errore export: ' + t);
    return;
  }
  const blob = await r.blob();
  const cd = r.headers.get('content-disposition') || '';
  let fname = 'leads.' + fmt;
  const m = cd.match(/filename="?([^";]+)"?/i);
  if(m && m[1]) fname = m[1];
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fname;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

async function previewCsvHeaders(){
  const box = document.getElementById('map_box');
  const f = document.getElementById('li_file').files[0];
  if(!f){ box.style.display='none'; return; }
  const txt = await f.text();
  const firstLine = (txt.split(/\r?\n/)[0] || '').trim();
  if(!firstLine){ box.style.display='none'; return; }

  // naive CSV header split with quotes (best effort)
  const headers = [];
  let cur='', inQ=false;
  for(let i=0;i<firstLine.length;i++){
    const ch = firstLine[i];
    if(ch === '"'){ inQ = !inQ; continue; }
    if(ch === ',' && !inQ){ headers.push(cur.trim()); cur=''; continue; }
    cur += ch;
  }
  headers.push(cur.trim());
  const uniq = headers.filter(h=>h.length>0);

  function fill(selId){
    const sel = document.getElementById(selId);
    sel.innerHTML = '';
    const opt0 = document.createElement('option');
    opt0.value = '';
    opt0.textContent = '(auto)';
    sel.appendChild(opt0);
    uniq.forEach(h=>{
      const opt = document.createElement('option');
      opt.value = h;
      opt.textContent = h;
      sel.appendChild(opt);
    });
  }
  ['m_first','m_last','m_company','m_pos','m_email','m_li','m_site'].forEach(fill);
  box.style.display = 'block';
}

function buildMapping(){
  const m = {
    first_name: document.getElementById('m_first').value || null,
    last_name: document.getElementById('m_last').value || null,
    company: document.getElementById('m_company').value || null,
    position: document.getElementById('m_pos').value || null,
    email: document.getElementById('m_email').value || null,
    linkedin_url: document.getElementById('m_li').value || null,
    website: document.getElementById('m_site').value || null
  };
  Object.keys(m).forEach(k=>{ if(!m[k]) delete m[k]; });
  return m;
}

async function importLinkedIn(){
  const out = document.getElementById('li_out');
  out.textContent = "Import in corso...";
  const f = document.getElementById('li_file').files[0];
  if(!f){ out.textContent = "Seleziona un file CSV."; return; }
  const fd = new FormData();
  fd.append('file', f);
  fd.append('mapping', JSON.stringify(buildMapping()));
  const r = await fetch('/import/linkedin?session_id=ui', {method:'POST', body: fd});
  const j = await r.json();
  out.textContent = JSON.stringify(j, null, 2);
}
</script>

</body>
</html>"""

    html = (html
        .replace("%%FOCUS_CONFIG_PATH%%", settings.FOCUS_CONFIG_PATH)
        .replace("%%AGENT_NAME%%", FOCUS.agent_name)
        .replace("%%REF_URL%%", getattr(FOCUS, "reference_company_url", "") or "")
    )
    return HTMLResponse(html)

@app.post("/discover", dependencies=[Depends(require_bearer)])
async def discover(req: DiscoverRequest):
    try:
        res = await discover_candidates(FOCUS, req.industry, req.geography, req.segment, limit=req.limit, api_keys=req.api_keys)
        if FOCUS.telemetry_enabled:
            log_event(TelemetryEvent(session_id=req.session_id, event_type="discover", payload={"industry": req.industry, "limit": req.limit, "results": len(res)}))
        return {"candidates": [c.model_dump() for c in res]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/enrich", dependencies=[Depends(require_bearer)])
async def enrich(req: EnrichRequest):
    companies = await enrich_candidates(req.candidates)
    if FOCUS.telemetry_enabled:
        log_event(TelemetryEvent(session_id=req.session_id, event_type="enrich", payload={"items": len(companies)}))
    return {"companies": [c.model_dump() for c in companies]}

@app.post("/identify", dependencies=[Depends(require_bearer)])
async def identify(req: IdentifyRequest):
    pairs = await identify_for_companies(req.companies)
    leads: List[LeadRecord] = []
    for comp, dm in pairs:
        leads.append(LeadRecord(company=comp, decision_maker=dm, investment_window_months=[4,6], score=0, score_class="cold", status="nuovo"))
    if FOCUS.telemetry_enabled:
        log_event(TelemetryEvent(session_id=req.session_id, event_type="identify", payload={"items": len(leads)}))
    return {"leads": [l.model_dump() for l in leads]}

@app.post("/verify", dependencies=[Depends(require_bearer)])
async def verify(req: VerifyRequest):
    leads = await verify_leads(req.leads)
    if FOCUS.telemetry_enabled:
        log_event(TelemetryEvent(session_id=req.session_id, event_type="verify", payload={"items": len(leads)}))
    return {"leads": [l.model_dump() for l in leads]}

@app.post("/score", dependencies=[Depends(require_bearer)])
async def score(req: ScoreRequest):
    leads = score_leads(req.leads, FOCUS)
    if FOCUS.telemetry_enabled:
        log_event(TelemetryEvent(session_id=req.session_id, event_type="score", payload={"items": len(leads)}))
    return {"leads": [l.model_dump() for l in leads]}

@app.post("/export", dependencies=[Depends(require_bearer)])
async def export(req: ExportRequest):
    # Metadata endpoint (serverless-safe): actual file is generated on-demand via /export/download
    if FOCUS.telemetry_enabled:
        log_event(TelemetryEvent(session_id=req.session_id, event_type="export", payload={"file_format": req.file_format}))
    return {"download_url": "/export/download", "file_format": req.file_format}

@app.post("/export/download", dependencies=[Depends(require_bearer)])
async def export_download(req: ExportRequest):
    content, fname, mime = export_leads_bytes(req.leads, file_format=req.file_format)
    if FOCUS.telemetry_enabled:
        log_event(TelemetryEvent(session_id=req.session_id, event_type="export_download", payload={"file_format": req.file_format, "file": fname}))
    headers = {"Content-Disposition": f'attachment; filename="{fname}"'}
    return StreamingResponse(io.BytesIO(content), media_type=mime, headers=headers)

@app.get("/download/{filename}", dependencies=[Depends(require_bearer)])
async def download(filename: str):
    path = (EXPORT_DIR / filename).resolve()
    if not path.exists() or path.is_dir():
        raise HTTPException(status_code=404, detail="File not found")
    # basic path traversal prevention
    if path.parent != EXPORT_DIR.resolve():
        raise HTTPException(status_code=400, detail="Invalid path")
    return FileResponse(path)


@app.post("/import/linkedin", dependencies=[Depends(require_bearer)])
async def import_linkedin(file: UploadFile = File(...), session_id: str = "linkedin", mapping: str = Form(default="")):
    content = await file.read()
    map_obj = None
    if mapping:
        try:
            map_obj = json.loads(mapping)
        except Exception:
            map_obj = None
    leads = parse_linkedin_csv(content, mapping=map_obj)
    if FOCUS.telemetry_enabled:
        log_event(TelemetryEvent(session_id=session_id, event_type="linkedin_import", payload={"rows": len(leads)}))
    return {"imported_rows": len(leads), "leads": [l.model_dump() for l in leads]}


@app.post("/admin/cache/purge", dependencies=[Depends(require_bearer)])
async def admin_cache_purge():
    purged = purge_expired()
    return {"purged": purged, "ttl_days": int(os.environ.get("PROFILE_CACHE_TTL_DAYS", "183"))}

@app.post("/admin/cache/flush", dependencies=[Depends(require_bearer)])
async def admin_cache_flush():
    deleted = flush_cache()
    return {"deleted": deleted}

@app.post("/run", response_model=RunResponse, dependencies=[Depends(require_bearer)])
async def run(req: RunRequest):
    result = await run_pipeline(req, FOCUS)
    if FOCUS.telemetry_enabled:
        log_event(TelemetryEvent(session_id=req.session_id, event_type="run", payload={"run_id": result["run_id"], "leads": len(result["leads"])}))
    # Serialize leads to dicts for response_model compatibility
    return RunResponse(
        run_id=result["run_id"],
        leads=result["leads"],
        export=result.get("export") or None,
        email_drafts=result.get("email_drafts") or None,
    )
