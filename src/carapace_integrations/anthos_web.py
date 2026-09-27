"""Plain-language workspace for the CARAPACE payment-intent product."""

from __future__ import annotations

import os
import json
import base64
import threading
import time
from uuid import uuid4
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Literal
from fastapi.responses import HTMLResponse
from starlette.concurrency import run_in_threadpool

from .anthos_preflight_bridge import AnthosPreflightBridge


HOME_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CARAPACE · Payment Intent Firewall</title>
  <style>
    :root{font-family:ui-sans-serif,system-ui,sans-serif;color:#162236;background:#f6f8fb}
    *{box-sizing:border-box}[hidden]{display:none!important}body{margin:0}header{background:#fff;border-bottom:1px solid #dce3ed}
    header div,main{width:min(1060px,calc(100% - 32px));margin:auto}header div{min-height:64px;display:flex;align-items:center;justify-content:space-between;gap:16px}
    .brand{font-weight:850;letter-spacing:.12em}.brand span{color:#2563eb}nav{display:flex;gap:15px;flex-wrap:wrap}a{color:#1555bd}nav a{text-decoration:none;font-size:14px}
    main{padding:48px 0 80px}.eyebrow{font-size:12px;font-weight:800;letter-spacing:.14em;text-transform:uppercase;color:#1555bd}h1{font-size:clamp(35px,5vw,62px);line-height:1.05;letter-spacing:-.045em;max-width:760px;margin:12px 0 18px}h2{margin:0 0 12px;font-size:23px;letter-spacing:-.025em}p{line-height:1.65;color:#4a596c} .lead{font-size:18px;max-width:760px}
    .card{background:#fff;border:1px solid #dce3ed;border-radius:18px;padding:25px;box-shadow:0 12px 35px rgba(15,34,62,.045)}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:30px 0}.step{font-size:13px;font-weight:800;color:#1555bd;text-transform:uppercase;letter-spacing:.08em}.card strong{display:block;margin:12px 0 6px;font-size:19px}.card p{margin:0;font-size:14px}
    .example{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:24px 0}.danger{border-left:5px solid #c43747}.safe{border-left:5px solid #26845b}.tag{display:inline-block;border-radius:999px;background:#fff1f1;color:#aa2130;padding:7px 10px;font-size:12px;font-weight:800}.tag.good{background:#e7f7ed;color:#166a43}
    .note{background:#eaf1ff;border-radius:14px;padding:17px 20px;font-size:14px;color:#334865}.actions{display:flex;gap:10px;flex-wrap:wrap;margin:23px 0}.button{display:inline-block;padding:12px 16px;background:#1555bd;color:#fff;border-radius:11px;text-decoration:none;font-weight:750}.button.secondary{background:#fff;color:#1555bd;border:1px solid #b8cce9}
    button.button{border:0;cursor:pointer}button.button:disabled{opacity:.55;cursor:wait}.evidence-image{display:block;width:100%;max-height:230px;object-fit:contain;border:1px solid #dce3ed;border-radius:9px;margin-top:12px}.order-box{margin-top:12px;background:#f4f7fb;padding:16px;border-radius:10px;line-height:1.7}.small{font-size:13px;color:#607086}details{margin-top:16px}summary{cursor:pointer;font-weight:700;color:#1555bd}
    @media(max-width:720px){.grid,.example{grid-template-columns:1fr}header div{align-items:flex-start;flex-direction:column;padding:15px 0}main{padding-top:32px}}
  </style>
</head>
<body>
  <header><div><div class="brand">CARA<span>PACE</span></div><nav><a href="#how-it-works">How it works</a><a href="#scenarios">Scenarios</a><a href="http://localhost:8080/docs" target="_blank" rel="noopener">API docs ↗</a></nav></div></header>
  <main>
    <div class="eyebrow">Payment Intent Firewall · development workspace</div>
    <h1>Know what a payment will actually do.</h1>
    <p class="lead">CARAPACE compares the message or bill that persuaded a person to pay with the amount and recipient supplied by the bank. It can stop a dangerous contradiction before an artificial-money transfer is submitted.</p>
    <div class="actions"><a class="button" href="#scenarios">See the two test cases</a></div>
    <div class="note"><strong>Working local path:</strong> a signed payment order, Gemini context check, enforced HOLD gate, browser-signed choice, and locally witnessed protection records. A valid PROCEED choice is required before a test posting. When configured, the demo then binds that posting to one exact row in Bank of Anthos's artificial-money PostgreSQL ledger. This does not use Anthos's official transfer service or real money.</div>
    <div id="how-it-works" class="grid">
      <div class="card"><span class="step">01 · Understand</span><strong>Read the story</strong><p>Gemini extracts supported claims from a customer-shared message or screenshot.</p></div>
      <div class="card"><span class="step">02 · Compare</span><strong>Check the actual payment</strong><p>Deterministic rules compare those claims with bank-controlled amount, direction and recipient.</p></div>
      <div class="card"><span class="step">03 · Confirm and enforce</span><strong>Stop or proceed</strong><p>The test gateway refuses HOLD. A genuine bill pauses until this browser signs an explicit PROCEED choice.</p></div>
    </div>
    <h2 id="scenarios">The first two scenarios</h2>
    <div class="example">
      <div class="card danger"><span class="tag">Expected: HOLD</span><strong>Fake refund</strong><p>A generated test screenshot promises money coming in. The signed order sends money out.</p><button class="button" id="run-refund" type="button">Run refund test</button></div>
      <div class="card safe"><span class="tag good">Expected: ALLOW</span><strong>Genuine bill</strong><p>The generated bill and bank-controlled payee and amount match. One synthetic transfer may post.</p><button class="button" id="run-bill" type="button">Run bill test</button></div>
    </div>
    <div id="demo-evidence" class="example" hidden><div class="card"><span class="step">What the person saw</span><strong>Customer-shared screenshot</strong><img id="context-image" class="evidence-image" alt="Generated test payment context screenshot"></div><div class="card"><span class="step">What the bank signed</span><strong>Actual payment order</strong><div id="bank-order" class="order-box"></div><p class="small">Development bank key · artificial accounts</p></div></div>
    <div class="card" aria-live="polite"><span class="step">Live walkthrough</span><strong id="demo-title">Choose a test case above</strong><p id="demo-status">The bank gateway will sign the order, ask Gemini to read a generated screenshot, decide, and pause before submission.</p><p id="demo-reason"></p><div class="actions"><button class="button" id="confirm-payment" type="button" hidden>Confirm this artificial-money payment</button><button class="button secondary" id="cancel-payment" type="button" hidden>Cancel this test payment</button></div><p id="demo-ack"></p><p id="demo-proof"></p><details><summary>See technical evidence</summary><pre id="demo-output" style="white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;color:#334865"></pre></details></div>
    <p>The browser creates a temporary test-device key when you confirm. Its signature proves control of that key over the exact bank details, warning and choice; it cannot prove a person read or understood the words. The local witness is not independently operated. The optional Anthos ledger bridge is a direct artificial-money test insert with an exact ID binding, not its official payment API.</p>
  </main>
  <script>
    function screenshot(scenario) {
      const canvas = document.createElement('canvas'); canvas.width=900; canvas.height=440;
      const c=canvas.getContext('2d'); c.fillStyle='#fff'; c.fillRect(0,0,900,440);
      c.fillStyle=scenario==='refund'?'#b4233b':'#185bb8'; c.fillRect(0,0,900,80);
      c.fillStyle='#fff'; c.font='bold 30px system-ui'; c.fillText(scenario==='refund'?'Refund notification':'Example Power bill',35,50);
      c.fillStyle='#14233a'; c.font='26px system-ui';
      const lines=scenario==='refund'
        ? ['Your refund of INR 4,999 is ready.', 'Scan the QR to receive it.', 'Enter your UPI PIN to claim the refund.']
        : ['Bill 7782 for electricity', 'Pay INR 4,999 to Example Power.', 'Amount due: INR 4,999'];
      lines.forEach((line,i)=>c.fillText(line,35,155+i*70));
      return canvas.toDataURL('image/png').split(',')[1];
    }
    let pendingFlow=null;
    function b64(buffer){return btoa(String.fromCharCode(...new Uint8Array(buffer)));}
    async function run(scenario) {
      const buttons=[document.getElementById('run-refund'),document.getElementById('run-bill')]; buttons.forEach(b=>b.disabled=true);
      pendingFlow=null;document.getElementById('confirm-payment').hidden=true;document.getElementById('cancel-payment').hidden=true;
      const image=screenshot(scenario);
      document.getElementById('demo-evidence').hidden=false;
      document.getElementById('context-image').src='data:image/png;base64,'+image;
      document.getElementById('bank-order').textContent='SEND INR 4,999 to '+(scenario==='refund'?'R K Traders':'Example Power');
      document.getElementById('demo-title').textContent='Running '+scenario+'…';
      document.getElementById('demo-status').textContent='Creating a bank-signed order and checking the screenshot.';
      document.getElementById('demo-reason').textContent='';
      document.getElementById('demo-ack').textContent='';
      document.getElementById('demo-proof').textContent='';
      document.getElementById('demo-output').textContent='';
      try {
        const response=await fetch('/api/demo/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({scenario,image_base64:image})});
        const result=await response.json(); if(!response.ok) throw new Error(result.detail||'Demo failed');
        pendingFlow=result.flow_id;
        document.getElementById('demo-title').textContent=result.verdict==='HOLD'?'Payment stopped before posting':'Genuine bill is waiting for your confirmation';
        document.getElementById('demo-status').textContent='AI mode: '+result.ai_mode+' · Model call completed: '+result.live_model_called+' · Gateway result: '+result.gateway_result;
        document.getElementById('demo-reason').textContent=result.customer_message;
        document.getElementById('confirm-payment').hidden=!pendingFlow;
        document.getElementById('cancel-payment').hidden=!pendingFlow;
        document.getElementById('demo-proof').textContent=result.local_proof_verified
          ? 'Decision record signed and included in local witness checkpoint #'+result.witness_tree_size+'.'
          : 'Protection proof unavailable or failed verification.';
        document.getElementById('demo-output').textContent=JSON.stringify(result,null,2);
      } catch(error) { document.getElementById('demo-title').textContent='Demo could not finish'; document.getElementById('demo-status').textContent=String(error); }
      finally { buttons.forEach(b=>b.disabled=false); }
    }
    async function finishPayment(choice){
      if(!pendingFlow)return;
      const flowId=pendingFlow;pendingFlow=null;
      const buttons=[document.getElementById('confirm-payment'),document.getElementById('cancel-payment')];buttons.forEach(button=>button.disabled=true);
      document.getElementById('demo-status').textContent='Creating a temporary browser key and signing your exact '+choice+' choice…';
      try{
        if(!window.crypto || !crypto.subtle)throw new Error('Browser signing is unavailable in this context. Use localhost or a secure origin.');
        const deviceId='browser_'+crypto.randomUUID().replaceAll('-','');
        const keys=await crypto.subtle.generateKey({name:'ECDSA',namedCurve:'P-256'},true,['sign','verify']);
        const publicKey=b64(await crypto.subtle.exportKey('spki',keys.publicKey));
        const preparedResponse=await fetch('/api/demo/prepare-confirm',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({flow_id:flowId,device_id:deviceId,public_key_spki_base64:publicKey,choice})});
        const prepared=await preparedResponse.json();if(!preparedResponse.ok)throw new Error(prepared.detail||'Could not prepare browser confirmation');
        const signature=b64(await crypto.subtle.sign({name:'ECDSA',hash:'SHA-256'},keys.privateKey,new TextEncoder().encode(prepared.statement_json)));
        const completedResponse=await fetch('/api/demo/complete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({flow_id:flowId,device_id:deviceId,signature_base64:signature,choice})});
        const completed=await completedResponse.json();if(!completedResponse.ok)throw new Error(completed.detail||'Test gateway refused confirmation');
        const anthos=completed.anthos_test_ledger;
        document.getElementById('demo-title').textContent=choice==='CANCEL'?'Cancelled; no transfer posted':anthos?.status==='MATCH'?'Confirmed; two test ledgers match':'Confirmed locally; Anthos test check pending';
        document.getElementById('demo-status').textContent='Gateway result: '+completed.gateway_result+(completed.synthetic_transfer_id?' · Transfer: '+completed.synthetic_transfer_id:'');
        document.getElementById('demo-ack').textContent='This browser signed '+choice+' over the exact amount, payee and warning. The signature proves key control, not human understanding.';
        document.getElementById('demo-proof').textContent=completed.local_proof_verified
          ? 'Device choice'+(choice==='PROCEED'?' and synthetic posting were':' was')+' recorded; latest local witness checkpoint #'+completed.witness_tree_size+'.'+(anthos?.status==='MATCH'?' Exact Bank of Anthos test-ledger row #'+anthos.anthos_transaction_id+' matched amount and accounts.':choice==='PROCEED'?' Anthos test-ledger check is '+(anthos?.status||'UNAVAILABLE')+'; do not treat it as verified.':'')
          : 'Choice or posting proof unavailable or failed verification.';
        document.getElementById('demo-output').textContent=JSON.stringify({prepared,completed},null,2);
      }catch(error){document.getElementById('demo-title').textContent='Confirmation did not complete';document.getElementById('demo-status').textContent=String(error)+' Start a new bill test to try again.';}
      finally{buttons.forEach(button=>{button.hidden=true;button.disabled=false;});}
    }
    document.getElementById('run-refund').addEventListener('click',()=>run('refund'));
    document.getElementById('run-bill').addEventListener('click',()=>run('bill'));
    document.getElementById('confirm-payment').addEventListener('click',()=>finishPayment('PROCEED'));
    document.getElementById('cancel-payment').addEventListener('click',()=>finishPayment('CANCEL'));
  </script>
</body>
</html>"""


class DemoRequest(BaseModel):
    scenario: str = Field(pattern="^(refund|bill)$")
    image_base64: str = Field(min_length=1, max_length=3_000_000)


class PrepareConfirmation(BaseModel):
    flow_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    device_id: str = Field(pattern=r"^[A-Za-z0-9_-]{8,80}$")
    public_key_spki_base64: str = Field(min_length=80, max_length=500)
    choice: Literal["PROCEED", "CANCEL"]


class CompleteConfirmation(BaseModel):
    flow_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    device_id: str = Field(pattern=r"^[A-Za-z0-9_-]{8,80}$")
    signature_base64: str = Field(min_length=80, max_length=120)
    choice: Literal["PROCEED", "CANCEL"]


def _api_call(base_url: str, path: str, method: str, body: dict | None = None) -> tuple[int, dict]:
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(
        base_url + path,
        data=payload,
        method=method,
        headers={
            "Content-Type": "application/json",
            "X-Carapace-Tenant": os.getenv("CARAPACE_TENANT", "demo-bank"),
            "X-Carapace-API-Key": os.getenv("CARAPACE_API_KEY", "local-demo-key-change-me"),
        },
    )
    try:
        with urlopen(request, timeout=45) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def _ready(url: str) -> bool:
    try:
        with urlopen(url, timeout=2) as response:
            return response.status == 200
    except (OSError, URLError):
        return False


def create_demo_app() -> FastAPI:
    if os.getenv("CARAPACE_DEMO_ENABLED", "false").lower() != "true":
        raise RuntimeError("CARAPACE_DEMO_ENABLED=true is required")
    api_base_url = os.getenv("CARAPACE_API_BASE_URL", "http://api:8080").rstrip("/")
    bank_internal_url = os.getenv("BOA_FRONTEND_URL", "http://anthos-frontend:8080").rstrip("/")
    anthos_database_url = os.getenv("BOA_DATABASE_URL", "")
    test_bridge = AnthosPreflightBridge(
        anthos_database_url, allow_test_writes=True,
    ) if anthos_database_url else None
    application = FastAPI(title="CARAPACE Payment Intent Workspace", docs_url=None, redoc_url=None, openapi_url=None)
    pending_flows: dict[str, dict] = {}
    pending_lock = threading.Lock()

    def pending(flow_id: str) -> dict:
        with pending_lock:
            flow = pending_flows.get(flow_id)
            if flow is None or time.monotonic() - flow["created_monotonic"] > 900:
                pending_flows.pop(flow_id, None)
                raise RuntimeError("test confirmation expired; start a new payment")
            return dict(flow)

    @application.get("/", response_class=HTMLResponse)
    async def home() -> HTMLResponse:
        return HTMLResponse(HOME_HTML, headers={"Cache-Control": "no-store"})

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "carapace-workspace"}

    @application.get("/api/status")
    async def status() -> dict[str, bool]:
        bank, api = await run_in_threadpool(
            lambda: (_ready(f"{bank_internal_url}/ready"), _ready(f"{api_base_url}/health/ready"))
        )
        return {"bank": bank, "api": api}

    @application.post("/api/demo/run")
    async def run_demo(request: DemoRequest) -> dict:
        def execute() -> dict:
            payee = "R K Traders" if request.scenario == "refund" else "Example Power"
            context = (
                "Refund notification: Your refund of INR 4,999 is ready. Scan to receive it. Enter your UPI PIN."
                if request.scenario == "refund" else
                "Example Power bill 7782: Pay INR 4,999 to Example Power."
            )
            order_code, order = _api_call(
                api_base_url, "/v1/preflight/orders", "POST",
                {"payer_account": "1000000001", "payee_account": "2000000002",
                 "payee_display_name": payee, "amount_minor": 499900,
                 "currency": "INR", "reference": f"demo-{uuid4().hex[:12]}"},
            )
            if order_code != 201:
                raise RuntimeError(f"bank order failed: {order}")
            order_id = order["envelope"]["order_id"]
            decision_code, decision = _api_call(
                api_base_url, f"/v1/preflight/orders/{order_id}/evaluate", "POST",
                {"context_text": context, "image_base64": request.image_base64,
                 "image_mime_type": "image/png", "locale": "en-IN"},
            )
            if decision_code != 200:
                raise RuntimeError(f"preflight evaluation failed: {decision}")
            if request.scenario == "bill" and decision["verdict"] == "ALLOW":
                flow_id = uuid4().hex
                with pending_lock:
                    for key, value in list(pending_flows.items()):
                        if time.monotonic() - value["created_monotonic"] > 900:
                            pending_flows.pop(key, None)
                    pending_flows[flow_id] = {
                        "created_monotonic": time.monotonic(),
                        "order_id": order_id,
                        "decision_id": decision["decision_id"],
                        "decision_receipt_id": decision["protection_bundle"]["receipt"]["receipt_id"],
                        "device_id": None,
                        "choice": None,
                        "statement_json": None,
                    }
            else:
                flow_id = None
            submit_code, submit = (None, {})
            if flow_id is None:
                submit_code, submit = _api_call(
                    api_base_url, f"/v1/preflight/orders/{order_id}/submit", "POST",
                    {"decision_id": decision["decision_id"]},
                )
                if submit_code != 409:
                    raise RuntimeError(f"test gateway did not safely refuse this payment: {submit}")
            receipt_id = decision["protection_bundle"]["receipt"]["receipt_id"]
            receipt_code, proof = _api_call(
                api_base_url, f"/v1/preflight/receipts/{receipt_id}", "GET"
            )
            if receipt_code != 200:
                raise RuntimeError(f"protection proof unavailable: {proof}")
            return {
                "scenario": request.scenario,
                "order_id": order_id,
                "bank_signature_present": bool(order["bank_signature"]),
                "signed_payee": payee,
                "amount_minor": order["envelope"]["amount_minor"],
                "verdict": decision["verdict"],
                "reason_codes": decision["reason_codes"],
                "customer_message": decision["customer_message"],
                "ai_mode": decision["provider_mode"],
                "live_model_called": decision["live_model_called"],
                "gateway_result": "AWAITING_BROWSER_CONFIRMATION" if flow_id else "BLOCKED",
                "synthetic_transfer_id": None,
                "protection_receipt_id": receipt_id,
                "posting_receipt_id": None,
                "flow_id": flow_id,
                "local_proof_verified": proof["local_proof_verified"],
                "witness_tree_size": proof["bundle"]["tree_head"]["tree_size"],
                "proof_scope": proof["verification_scope"],
                "test_ledger_only": True,
            }
        return await run_in_threadpool(execute)

    @application.post("/api/demo/prepare-confirm")
    async def prepare_confirmation(request: PrepareConfirmation) -> dict:
        def execute() -> dict:
            flow = pending(request.flow_id)
            if flow["device_id"] is not None:
                raise RuntimeError("this test flow has already prepared a device")
            code, registered = _api_call(
                api_base_url, "/v1/preflight/devices", "POST",
                {"payer_account": "1000000001", "device_id": request.device_id,
                 "public_key_spki_base64": request.public_key_spki_base64},
            )
            if code != 201:
                raise RuntimeError(f"test device enrollment failed: {registered}")
            query = urlencode({"device_id": request.device_id, "choice": request.choice})
            code, challenge = _api_call(
                api_base_url,
                f"/v1/preflight/orders/{flow['order_id']}/acknowledgement-challenge?{query}",
                "GET",
            )
            if code != 200:
                raise RuntimeError(f"signed payment challenge failed: {challenge}")
            with pending_lock:
                saved = pending_flows.get(request.flow_id)
                if saved is None or saved["device_id"] is not None:
                    raise RuntimeError("test flow changed during device enrollment")
                saved["device_id"] = request.device_id
                saved["choice"] = request.choice
                saved["statement_json"] = challenge["statement_json"]
            return {
                "statement_json": challenge["statement_json"],
                "statement": challenge["statement"],
                "device_key_sha256": registered["device_key_sha256"],
                "scope": challenge["scope"],
            }
        return await run_in_threadpool(execute)

    @application.post("/api/demo/complete")
    async def complete_confirmation(request: CompleteConfirmation) -> dict:
        def execute() -> dict:
            with pending_lock:
                flow = pending_flows.pop(request.flow_id, None)
            if flow is None or time.monotonic() - flow["created_monotonic"] > 900:
                raise RuntimeError("test confirmation expired; start a new payment")
            if (
                flow["device_id"] != request.device_id
                or flow["choice"] != request.choice
                or flow["statement_json"] is None
            ):
                raise RuntimeError("test device did not prepare this payment")
            order_id = flow["order_id"]
            code, acknowledgement = _api_call(
                api_base_url, f"/v1/preflight/orders/{order_id}/acknowledge", "POST",
                {"device_id": request.device_id, "choice": request.choice,
                 "statement_json": flow["statement_json"],
                 "signature_base64": request.signature_base64},
            )
            if code != 200:
                raise RuntimeError(f"test device acknowledgement failed: {acknowledgement}")
            submit = None
            anthos_test_ledger = None
            if request.choice == "PROCEED":
                code, submit = _api_call(
                    api_base_url, f"/v1/preflight/orders/{order_id}/submit", "POST",
                    {"decision_id": flow["decision_id"]},
                )
                if code != 200:
                    raise RuntimeError(f"confirmed test payment was rejected: {submit}")
                if test_bridge is None:
                    anthos_test_ledger = {"status": "NOT_CONFIGURED", "reason_codes": ["BOA_DATABASE_URL_MISSING"]}
                elif not submit["protection_bundle"].get("head_signature"):
                    anthos_test_ledger = {"status": "UNAVAILABLE", "reason_codes": ["POSTING_PROOF_MISSING"]}
                else:
                    try:
                        key_code, keys = _api_call(api_base_url, "/v1/preflight/public-keys", "GET")
                        if key_code != 200:
                            raise RuntimeError("test public keys unavailable")
                        anthos_test_ledger = test_bridge.post_once_and_reconcile(
                            submit["transfer"], submit["protection_bundle"],
                            bank_public_key=base64.b64decode(keys["bank"]["ed25519_public_key_base64"], validate=True),
                            witness_public_key=base64.b64decode(keys["witness"]["ed25519_public_key_base64"], validate=True),
                        )
                    except Exception as error:
                        # The CARAPACE local posting already committed. Never claim
                        # an external match or silently retry with a new transfer.
                        anthos_test_ledger = {
                            "status": "UNAVAILABLE",
                            "reason_codes": ["ANTHOS_TEST_BRIDGE_FAILED"],
                            "error_type": type(error).__name__,
                        }
            receipt_id = (
                submit["protection_bundle"]["receipt"]["receipt_id"]
                if submit else acknowledgement["protection_bundle"]["receipt"]["receipt_id"]
            )
            proof_code, proof = _api_call(
                api_base_url, f"/v1/preflight/receipts/{receipt_id}", "GET"
            )
            if proof_code != 200:
                raise RuntimeError(f"posting proof unavailable: {proof}")
            return {
                "gateway_result": "POSTED_SYNTHETIC" if submit else "CANCELLED_NO_POSTING",
                "synthetic_transfer_id": submit["transfer"]["transfer_id"] if submit else None,
                "acknowledgement_receipt_id": acknowledgement["protection_bundle"]["receipt"]["receipt_id"],
                "posting_receipt_id": receipt_id if submit else None,
                "local_proof_verified": proof["local_proof_verified"],
                "witness_tree_size": proof["bundle"]["tree_head"]["tree_size"],
                "device_signature_verified": True,
                "proof_scope": proof["verification_scope"],
                "test_ledger_only": True,
                "anthos_test_ledger": anthos_test_ledger,
            }
        return await run_in_threadpool(execute)

    return application


app = create_demo_app()


def main() -> None:
    port = int(os.getenv("PORT", "8090"))
    uvicorn.run("carapace_integrations.anthos_web:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
