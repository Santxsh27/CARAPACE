"""Beginner-facing local page for the Bank of Anthos integration demo."""

from __future__ import annotations

import logging
import os
from functools import partial
from urllib.error import URLError
from urllib.request import urlopen

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from starlette.concurrency import run_in_threadpool

from .anthos_demo import run_demo
from .bank_of_anthos import BankOfAnthosLedger


LOGGER = logging.getLogger(__name__)


DEMO_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <title>CARAPACE × Bank of Anthos</title>
  <style>
    :root {
      --ink: #f6f7fb; --muted: #aeb5c7; --panel: #141923;
      --line: #293142; --violet: #9d8cff; --cyan: #6ee7f2;
      --green: #58dc9b; --red: #ff7187; --amber: #ffc96b;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0; min-height: 100vh; color: var(--ink);
      background:
        radial-gradient(circle at 12% -10%, #26306a 0, transparent 32rem),
        radial-gradient(circle at 100% 30%, #123c46 0, transparent 35rem), #090c12;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif;
    }
    main { width: min(1120px, calc(100% - 32px)); margin: auto; padding: 42px 0 70px; }
    .eyebrow { color: var(--cyan); font-size: 12px; font-weight: 800; letter-spacing: .16em; }
    h1 { font-size: clamp(34px, 6vw, 68px); letter-spacing: -.055em; line-height: .96; margin: 14px 0 20px; }
    .lead { color: var(--muted); max-width: 760px; font-size: 18px; line-height: 1.6; }
    .statusbar, .grid, .flow, .result-grid { display: grid; gap: 14px; }
    .statusbar { grid-template-columns: repeat(3, 1fr); margin: 34px 0; }
    .card, .step, .result-card {
      background: color-mix(in srgb, var(--panel) 92%, transparent);
      border: 1px solid var(--line); border-radius: 18px; padding: 20px;
      box-shadow: 0 18px 60px rgba(0,0,0,.22);
    }
    .card span { color: var(--muted); font-size: 13px; }
    .card strong { display: block; margin-top: 8px; font-size: 17px; }
    .dot { display: inline-block; width: 9px; height: 9px; margin-right: 8px; border-radius: 50%; background: var(--amber); }
    .dot.ok { background: var(--green); box-shadow: 0 0 14px var(--green); }
    .flow { grid-template-columns: repeat(5, 1fr); align-items: stretch; margin: 20px 0 40px; }
    .step { min-height: 138px; position: relative; }
    .step:not(:last-child)::after { content: "→"; color: var(--violet); position: absolute; right: -13px; top: 52px; z-index: 2; font-size: 22px; }
    .step b { display: block; color: var(--violet); font-size: 12px; margin-bottom: 12px; }
    .step p { margin: 0; color: var(--muted); font-size: 14px; line-height: 1.5; }
    .action { display: flex; align-items: center; gap: 18px; margin: 34px 0; flex-wrap: wrap; }
    button {
      appearance: none; border: 0; border-radius: 999px; padding: 15px 24px;
      background: linear-gradient(115deg, var(--violet), var(--cyan)); color: #090c12;
      font: inherit; font-weight: 850; cursor: pointer; transition: transform .15s ease;
    }
    button:hover { transform: translateY(-2px); }
    button:disabled { cursor: wait; opacity: .58; transform: none; }
    #run-note { color: var(--muted); font-size: 14px; }
    #results { display: none; margin-top: 28px; }
    #results.visible { display: block; }
    .result-grid { grid-template-columns: repeat(2, 1fr); }
    .result-card strong { display: block; margin-bottom: 8px; }
    .match { color: var(--green); } .mismatch { color: var(--red); }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; overflow-wrap: anywhere; }
    .explain { border-left: 2px solid var(--cyan); padding-left: 18px; color: var(--muted); line-height: 1.65; margin-top: 36px; }
    .truth { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-top: 42px; }
    .truth h2 { font-size: 18px; margin-top: 0; }
    .truth li { color: var(--muted); margin: 10px 0; }
    .error { color: var(--red); }
    @media (max-width: 800px) {
      .statusbar, .flow, .result-grid, .truth { grid-template-columns: 1fr; }
      .step:not(:last-child)::after { content: "↓"; right: 50%; top: auto; bottom: -19px; }
    }
  </style>
</head>
<body>
<main>
  <div class="eyebrow">LOCAL INTEGRATION LAB · ARTIFICIAL MONEY ONLY</div>
  <h1>Watch CARAPACE catch a bank fault.</h1>
  <p class="lead">This page connects CARAPACE to Google's official Bank of Anthos ledger schema. One click stores a correct artificial payment, verifies it, forces a duplicate debit, and proves CARAPACE opens an incident.</p>

  <section class="statusbar" aria-label="System status">
    <div class="card"><span>CARAPACE assurance API</span><strong><i id="api-dot" class="dot"></i><span id="api-status">Checking…</span></strong></div>
    <div class="card"><span>Bank of Anthos ledger</span><strong><i id="ledger-dot" class="dot"></i><span id="ledger-status">Checking…</span></strong></div>
    <div class="card"><span>Integration scope</span><strong>Official ledger slice · local Docker</strong></div>
  </section>

  <section class="flow" aria-label="Demo workflow">
    <div class="step"><b>01 · PROMISE</b><p>CARAPACE records the payer, payee and exact $49.99 approval.</p></div>
    <div class="step"><b>02 · REAL ROW</b><p>The test harness writes artificial money into the official Anthos ledger.</p></div>
    <div class="step"><b>03 · WITNESS</b><p>CARAPACE reads the authoritative transaction ID and verifies one debit.</p></div>
    <div class="step"><b>04 · FAULT</b><p>The harness simulates a bad retry that writes a second debit.</p></div>
    <div class="step"><b>05 · INCIDENT</b><p>The deterministic engine detects the mismatch and preserves evidence.</p></div>
  </section>

  <div class="action">
    <button id="run" type="button">Run the live safety test</button>
    <span id="run-note">Fresh accounts and transaction IDs are created on every run.</span>
  </div>

  <section id="results" aria-live="polite">
    <div class="eyebrow">VERIFIED RUN RESULT</div>
    <h2 id="result-title">Integration complete</h2>
    <div class="result-grid">
      <div class="result-card"><strong>First ledger transaction</strong><span id="first-id" class="mono"></span><br><span id="correct-verdict" class="match"></span></div>
      <div class="result-card"><strong>Forced retry transaction</strong><span id="duplicate-id" class="mono"></span><br><span id="duplicate-verdict" class="mismatch"></span></div>
      <div class="result-card"><strong>Payment Promise</strong><span id="contract-id" class="mono"></span></div>
      <div class="result-card"><strong>Evidence case</strong><span id="case-id" class="mono"></span></div>
    </div>
    <p class="explain" id="plain-result"></p>
  </section>

  <section class="truth">
    <div class="card"><h2>What this proves now</h2><ul><li>A real external Bank of Anthos ledger is connected.</li><li>CARAPACE checks stored database rows, not sample JSON files.</li><li>A duplicate debit becomes a persisted, rule-backed incident.</li></ul></div>
    <div class="card"><h2>What comes later</h2><ul><li>The complete seven-service Kubernetes banking application.</li><li>Gemini scam-context analysis and root-cause repair proposals.</li><li>A real bank integration with read-only adapters and trusted event binding.</li></ul></div>
  </section>
</main>
<script>
  const byId = id => document.getElementById(id);
  async function refreshStatus() {
    try {
      const response = await fetch('/api/status');
      const data = await response.json();
      for (const key of ['api', 'ledger']) {
        byId(`${key}-status`).textContent = data[key] ? 'Connected' : 'Unavailable';
        byId(`${key}-dot`).classList.toggle('ok', Boolean(data[key]));
      }
    } catch (_) {
      byId('api-status').textContent = 'Unavailable';
      byId('ledger-status').textContent = 'Unavailable';
    }
  }
  byId('run').addEventListener('click', async () => {
    const button = byId('run');
    button.disabled = true;
    button.textContent = 'Running through the ledger…';
    byId('run-note').textContent = 'Creating promise → writing ledger row → verifying → injecting retry…';
    try {
      const response = await fetch('/api/run', { method: 'POST' });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Demo failed');
      byId('first-id').textContent = `#${data.first_transaction_id}`;
      byId('duplicate-id').textContent = `#${data.duplicate_transaction_id}`;
      byId('correct-verdict').textContent = `CARAPACE verdict: ${data.correct_payment_verdict}`;
      byId('duplicate-verdict').textContent = `CARAPACE verdict: ${data.duplicate_payment_verdict}`;
      byId('contract-id').textContent = data.contract_id;
      byId('case-id').textContent = data.incident_case_id;
      byId('result-title').textContent = data.overall === 'PASS' ? 'CARAPACE caught the duplicate debit.' : 'The check did not pass.';
      byId('result-title').className = data.overall === 'PASS' ? 'match' : 'error';
      byId('plain-result').textContent = `The customer approved one $${(data.amount_minor / 100).toFixed(2)} payment. Bank of Anthos stored transaction #${data.first_transaction_id}, which matched. The forced retry stored transaction #${data.duplicate_transaction_id}. CARAPACE saw two debits for one promise, rejected the execution, and opened incident ${data.incident_case_id}.`;
      byId('results').classList.add('visible');
      byId('results').scrollIntoView({ behavior: 'smooth', block: 'start' });
      byId('run-note').textContent = 'Completed using fresh artificial-money records.';
    } catch (error) {
      byId('run-note').textContent = error.message;
      byId('run-note').className = 'error';
    } finally {
      button.disabled = false;
      button.textContent = 'Run another safety test';
    }
  });
  refreshStatus();
</script>
</body>
</html>"""


def create_demo_app() -> FastAPI:
    if os.getenv("CARAPACE_DEMO_ENABLED", "false").lower() != "true":
        raise RuntimeError("CARAPACE_DEMO_ENABLED=true is required")

    database_url = os.environ["BOA_DATABASE_URL"]
    api_base_url = os.environ["CARAPACE_API_BASE_URL"]
    tenant = os.getenv("CARAPACE_TENANT", "demo-bank")
    api_key = os.getenv("CARAPACE_API_KEY", "local-demo-key-change-me")
    application = FastAPI(
        title="CARAPACE Bank of Anthos Demo",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @application.get("/", response_class=HTMLResponse)
    async def home() -> HTMLResponse:
        return HTMLResponse(
            DEMO_HTML,
            headers={
                "Cache-Control": "no-store",
                "Content-Security-Policy": (
                    "default-src 'self'; style-src 'unsafe-inline'; "
                    "script-src 'unsafe-inline'; connect-src 'self'; "
                    "img-src 'self' data:"
                ),
            },
        )

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "carapace-anthos-demo"}

    @application.get("/api/status")
    async def integration_status() -> dict[str, object]:
        try:
            with urlopen(f"{api_base_url.rstrip('/')}/health/ready", timeout=3) as response:
                api_ready = response.status == 200
        except (OSError, URLError):
            api_ready = False
        ledger_ready = await run_in_threadpool(
            BankOfAnthosLedger(database_url).is_ready
        )
        return {
            "api": api_ready,
            "ledger": ledger_ready,
            "full_bank_application": False,
            "scope": "official-bank-of-anthos-ledger-slice",
        }

    @application.post("/api/run")
    async def run_integration() -> dict[str, object]:
        operation = partial(
            run_demo,
            database_url=database_url,
            api_base_url=api_base_url,
            tenant=tenant,
            api_key=api_key,
        )
        try:
            result = await run_in_threadpool(operation)
        except Exception as error:
            LOGGER.exception("Bank of Anthos integration demo failed")
            raise HTTPException(
                status_code=500,
                detail="The local integration could not complete. Check Docker logs.",
            ) from error
        return result.as_dict()

    return application


app = create_demo_app()


def main() -> None:
    port = int(os.getenv("PORT", "8090"))
    uvicorn.run("carapace_integrations.anthos_web:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
