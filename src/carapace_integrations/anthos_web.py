"""Beginner-facing two-system workspace for the Bank of Anthos integration."""

from __future__ import annotations

import html
import json
import logging
import os
from functools import partial
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from starlette.concurrency import run_in_threadpool

from .anthos_demo import run_demo
from .bank_of_anthos import BankOfAnthosLedger
from .control_room_future import ASSURANCE_FLOW_HTML, FUTURE_CSS, FUTURE_JS


LOGGER = logging.getLogger(__name__)

BANK_OF_ANTHOS_SOURCE = {
    "application": "Google Bank of Anthos v0.6.10",
    "container": "Official ledger-db image (digest pinned)",
    "database": "postgresdb",
    "schema": "public",
    "table": "transactions",
    "collection_mode": "Server-side PostgreSQL adapter",
    "binding_rule": "Only exact transaction IDs returned by the trusted test flow",
}


DEMO_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>CARAPACE Control Room</title>
  <style>
    :root {--ink:#172033;--muted:#5f6b7a;--line:#dce3ed;--soft:#f4f7fb;--blue:#1a73e8;--navy:#0d1b2a;--cyan:#00a8b5;--green:#137c50;--green-bg:#e9f8f0;--red:#bd2434;--red-bg:#fff0f1;--amber:#946200;--amber-bg:#fff7df;--white:#fff;--shadow:0 18px 55px rgba(17,34,68,.09)}
    *{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--ink);background:#eef3f8;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}a{color:inherit}button{font:inherit}
    .topbar{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.94);backdrop-filter:blur(16px);border-bottom:1px solid var(--line)}.topbar-inner{width:min(1400px,calc(100% - 32px));min-height:68px;margin:auto;display:flex;align-items:center;justify-content:space-between;gap:20px}.brand{font-weight:900;letter-spacing:.11em;flex:0 0 auto}.brand span{color:var(--blue)}.toplinks{display:flex;gap:8px;align-items:center;overflow-x:auto;padding:8px 0;scrollbar-width:none}.toplinks::-webkit-scrollbar{display:none}.toplinks a{text-decoration:none;border:1px solid var(--line);border-radius:999px;padding:8px 12px;font-size:12px;font-weight:750;background:#fff;white-space:nowrap}
    main{width:min(1400px,calc(100% - 32px));margin:auto;padding:34px 0 72px}.hero{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(300px,.65fr);gap:22px;align-items:stretch}.hero-main,.hero-side,.panel{background:var(--white);border:1px solid var(--line);border-radius:22px;box-shadow:var(--shadow)}.hero-main{padding:36px;background:linear-gradient(135deg,#fff 45%,#eaf3ff)}.eyebrow{font-size:12px;font-weight:900;letter-spacing:.14em;color:var(--blue);text-transform:uppercase}h1{font-size:clamp(34px,5vw,64px);line-height:1;letter-spacing:-.052em;margin:14px 0 18px;max-width:850px}.lead{font-size:18px;line-height:1.6;color:var(--muted);max-width:850px;margin:0}.hero-side{padding:26px;background:var(--navy);color:#fff}.hero-side h2{font-size:18px;margin:0 0 18px}.hero-side ol{padding-left:22px;margin:0}.hero-side li{padding:0 0 16px 5px;line-height:1.45;color:#c9d5e3}.hero-side li::marker{color:#6adbe1;font-weight:900}
    .statusbar{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:22px 0}.status{background:#fff;border:1px solid var(--line);border-radius:16px;padding:15px 17px}.status small{display:block;color:var(--muted);margin-bottom:7px}.status strong{font-size:14px}.dot{display:inline-block;width:9px;height:9px;margin-right:8px;border-radius:50%;background:#c28a14}.dot.ok{background:#20a66a;box-shadow:0 0 0 4px #dff5e9}
    .section-head{display:flex;align-items:end;justify-content:space-between;gap:18px;margin:38px 0 14px}.section-head h2{font-size:27px;letter-spacing:-.03em;margin:5px 0 0}.section-head p{max-width:680px;color:var(--muted);line-height:1.5;margin:0}.number{color:var(--blue);font-weight:900}
    .bank-layout{display:grid;grid-template-columns:320px minmax(0,1fr);gap:0;overflow:hidden}.bank-guide{padding:25px;background:#f8fafc;border-right:1px solid var(--line)}.bank-guide h3{margin:0 0 10px}.bank-guide p,.bank-guide li{color:var(--muted);line-height:1.55;font-size:14px}.bank-guide ul{padding-left:19px}.credential{background:#fff;border:1px solid var(--line);border-radius:12px;padding:13px;margin:18px 0}.credential small{display:block;color:var(--muted);margin-bottom:7px}.credential code{font-size:12px;display:block;margin:5px 0}.open-bank{display:inline-block;text-decoration:none;background:var(--blue);color:#fff;border-radius:999px;padding:11px 16px;font-weight:800;font-size:13px}.bank-frame-wrap{min-width:0;background:#fff}.windowbar{height:44px;background:#edf1f6;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:7px;padding:0 15px;color:var(--muted);font-size:12px}.windowbar i{width:9px;height:9px;border-radius:50%;background:#c7ced9}.windowbar span{margin-left:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}iframe{display:block;width:100%;height:620px;border:0;background:#fff}
    .pipe{display:grid;grid-template-columns:1fr 62px 1fr 62px 1fr;align-items:center;gap:8px;margin:14px 0}.pipe div{background:#fff;border:1px solid var(--line);border-radius:16px;padding:17px;text-align:center;min-height:92px}.pipe b{display:block;font-size:14px;margin-bottom:6px}.pipe span{font-size:12px;color:var(--muted)}.pipe-arrow{font-size:26px;color:var(--blue);font-weight:900;text-align:center}
    .source-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;padding:18px;border-bottom:1px solid var(--line);background:#f8fafc}.source-item small{display:block;color:var(--muted);margin-bottom:5px}.source-item strong{font-size:13px;overflow-wrap:anywhere}.table-toolbar{display:flex;justify-content:space-between;align-items:center;padding:18px;gap:15px}.table-toolbar p{color:var(--muted);font-size:13px;margin:0}.secondary{border:1px solid var(--line);background:#fff;border-radius:999px;padding:9px 14px;font-weight:800;cursor:pointer;color:var(--ink)}.table-scroll{overflow:auto;border-top:1px solid var(--line)}table{width:100%;border-collapse:collapse;min-width:900px}th,td{text-align:left;padding:13px 16px;border-bottom:1px solid #e9edf3;font-size:13px;white-space:nowrap}th{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);background:#fbfcfe}td code{font-size:12px}.empty{text-align:center!important;color:var(--muted);padding:38px!important}.badge{display:inline-block;border-radius:999px;padding:5px 9px;font-size:11px;font-weight:850}.unbound{color:var(--amber);background:var(--amber-bg)}.matched{color:var(--green);background:var(--green-bg)}.failed{color:var(--red);background:var(--red-bg)}
    .experiment{display:grid;grid-template-columns:340px minmax(0,1fr);gap:0;overflow:hidden}.promise{padding:25px;background:var(--navy);color:#fff}.promise h3{margin:7px 0 18px;font-size:23px}.promise dl{margin:0}.promise-row{display:grid;grid-template-columns:1fr 1.35fr;gap:8px;padding:11px 0;border-bottom:1px solid #2b3e51}.promise dt{color:#9fb0c2;font-size:12px}.promise dd{margin:0;font-size:13px;font-weight:750;text-align:right}.experiment-main{padding:28px}.experiment-main h3{margin:0 0 8px}.experiment-main>p{color:var(--muted);line-height:1.55;margin:0 0 20px}.flow{display:grid;grid-template-columns:repeat(5,1fr);gap:9px;margin:22px 0}.step{background:var(--soft);border-radius:13px;padding:13px;min-height:112px}.step b{display:block;color:var(--blue);font-size:11px;margin-bottom:8px}.step span{font-size:12px;line-height:1.45;color:var(--muted)}
    .primary{appearance:none;border:0;border-radius:999px;padding:14px 21px;background:linear-gradient(110deg,var(--blue),var(--cyan));color:#fff;font-weight:900;cursor:pointer;box-shadow:0 10px 24px rgba(26,115,232,.22)}.primary:disabled{opacity:.55;cursor:wait}.runline{display:flex;gap:15px;align-items:center;flex-wrap:wrap}.runline small{color:var(--muted)}#results{display:none;margin-top:22px;border-top:1px solid var(--line);padding-top:22px}#results.visible{display:block}.result-banner{padding:18px;border-radius:15px;background:var(--green-bg);color:var(--green);font-weight:850}.result-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-top:12px}.result-card{border:1px solid var(--line);border-radius:14px;padding:16px}.result-card small{display:block;color:var(--muted);margin-bottom:7px}.result-card strong{font-size:14px;overflow-wrap:anywhere}.mismatch-text{color:var(--red)}.receipt{margin-top:14px;border:1px solid #b8dfce;background:linear-gradient(135deg,#f6fffa,#eef8ff);border-radius:16px;padding:18px}.receipt-head{display:flex;align-items:start;justify-content:space-between;gap:16px}.receipt-head small{display:block;color:var(--muted);margin-bottom:5px}.receipt-head strong{overflow-wrap:anywhere}.receipt-level{display:inline-block;border-radius:999px;padding:7px 10px;background:var(--green-bg);color:var(--green);font-size:11px;font-weight:900;white-space:nowrap}.receipt>p{color:var(--muted);line-height:1.5;margin:12px 0}.receipt-stages{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.receipt-stage{border:1px solid var(--line);background:#fff;border-radius:11px;padding:11px;font-size:12px}.receipt-stage b{display:block;margin-bottom:5px}.receipt-stage span{color:var(--muted)}
    .mapping{margin-top:18px;border:1px solid var(--line);border-radius:14px;overflow:hidden}.mapping h4{padding:14px 16px;margin:0;background:#f7f9fc;border-bottom:1px solid var(--line)}.mapping-row{display:grid;grid-template-columns:1fr 40px 1fr 1fr;gap:8px;padding:12px 16px;border-bottom:1px solid #edf0f4;font-size:13px}.mapping-row:last-child{border:0}.mapping-row b:nth-child(2){color:var(--blue);text-align:center}.good{color:var(--green)}.bad{color:var(--red)}.honesty{margin-top:18px;padding:18px;border:1px solid #f1d185;background:var(--amber-bg);border-radius:15px;color:#694b00;line-height:1.55;font-size:14px}.error{color:var(--red)!important}
    .proofops{margin-top:18px;border:1px solid #b8caef;border-radius:16px;padding:18px;background:linear-gradient(135deg,#f7f9ff,#f2fbff)}.proofops h4{margin:6px 0 8px;font-size:19px}.proofops>p{color:var(--muted);line-height:1.5}.proof-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:14px}.proof-card{padding:13px;background:#fff;border:1px solid var(--line);border-radius:12px}.proof-card small{display:block;color:var(--muted);margin-bottom:5px}.proof-card strong{font-size:13px;overflow-wrap:anywhere}.scenario-list{margin:13px 0 0;padding-left:20px;color:var(--muted);font-size:13px}.scenario-list li{margin:7px 0;line-height:1.45}
    .lens-layout{display:grid;grid-template-columns:minmax(320px,.9fr) minmax(360px,1.1fr);overflow:hidden}.lens-form{padding:27px;background:#f8fafc;border-right:1px solid var(--line)}.lens-form label{display:block;font-size:12px;font-weight:850;margin:15px 0 7px}.lens-form textarea,.lens-form input{width:100%;border:1px solid #cbd5e1;border-radius:12px;padding:12px 13px;background:#fff;color:var(--ink);font:inherit;line-height:1.45}.lens-form textarea{min-height:112px;resize:vertical}.upload-row{display:grid;grid-template-columns:auto 1fr;align-items:center;gap:10px;margin-top:10px}.upload-row input{position:absolute;inline-size:1px;block-size:1px;opacity:0;pointer-events:none}.upload-label{display:inline-block!important;margin:0!important;border:1px solid var(--line);background:#fff;border-radius:999px;padding:9px 14px;font-weight:800!important;cursor:pointer}.scan-state{font-size:12px;color:var(--muted)}.lens-result{padding:27px}.lens-result h3{margin:0 0 8px;font-size:24px}.lens-result>p{color:var(--muted);line-height:1.55}.lens-facts{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:20px 0}.lens-fact{padding:14px;background:var(--soft);border-radius:12px}.lens-fact small{display:block;color:var(--muted);margin-bottom:6px}.lens-findings{padding-left:20px}.lens-findings li{margin:10px 0;line-height:1.45}.mode-note{font-size:12px;color:var(--muted);margin-top:14px}
    @media(max-width:1000px){.hero,.bank-layout,.experiment,.lens-layout{grid-template-columns:1fr}.bank-guide,.lens-form{border-right:0;border-bottom:1px solid var(--line)}.statusbar{grid-template-columns:repeat(2,1fr)}.flow{grid-template-columns:repeat(2,1fr)}.source-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:650px){main,.topbar-inner{width:min(100% - 20px,1400px)}.hero-main{padding:25px}.statusbar,.result-grid,.source-grid,.lens-facts,.receipt-stages,.proof-grid{grid-template-columns:1fr}.pipe{grid-template-columns:1fr}.pipe-arrow{transform:rotate(90deg)}.flow{grid-template-columns:1fr}.mapping-row{grid-template-columns:1fr}.mapping-row b:nth-child(2){text-align:left}.toplinks a:first-child{display:none}iframe{height:560px}}
  </style>
</head>
<body>
  <header class="topbar"><div class="topbar-inner"><div class="brand"><i class="ph-fill ph-shield-check"></i><div>CARA<span>PACE</span></div><small>Assurance Flow</small></div><nav class="toplinks" aria-label="CARAPACE modules"><a href="#assurance"><i class="ph ph-wave-sine"></i>Check</a><a href="#bank"><i class="ph ph-credit-card"></i>Payment</a><a href="#data"><i class="ph ph-database"></i>Witness</a><a href="#verification"><i class="ph ph-shield-check"></i>ProofOps</a></nav><div class="system-strip"><div class="system-live"><i class="pulse"></i><b>GEMINI LIVE</b><small>Evidence-bounded AI</small></div><div class="system-live"><i class="pulse"></i><b>All systems online</b><small>Bank · Ledger · AI</small></div><div class="system-avatar">SO</div></div></div></header>
  <main>
    <section class="hero"><div class="hero-main"><div class="eyebrow">Local lab · official Google sample bank · artificial money</div><h1>See the bank. See the data. See the proof.</h1><p class="lead">This workspace makes the connection visible. Use Google’s Bank of Anthos, inspect the exact rows its ledger stored, then watch CARAPACE compare those rows with one customer-approved Payment Promise.</p></div><aside class="hero-side"><h2>The whole story in plain English</h2><ol><li>A customer approves exactly one payment.</li><li>Bank of Anthos records the payment in PostgreSQL.</li><li>CARAPACE reads the server record—not the webpage.</li><li>A forced retry creates a second debit.</li><li>CARAPACE proves the mismatch and opens an incident.</li></ol></aside></section>
    <section class="statusbar" aria-label="Live system status"><div class="status"><small>Official bank website</small><strong><i id="bank-dot" class="dot"></i><span id="bank-status">Checking…</span></strong></div><div class="status"><small>Bank ledger database</small><strong><i id="ledger-dot" class="dot"></i><span id="ledger-status">Checking…</span></strong></div><div class="status"><small>CARAPACE assurance API</small><strong><i id="api-dot" class="dot"></i><span id="api-status">Checking…</span></strong></div><div class="status"><small>Money and environment</small><strong>Artificial · your Mac only</strong></div></section>
    <div id="lens" class="section-head"><div><div class="eyebrow"><span class="number">01</span> · CARAPACE Lens</div><h2>Check the story before opening the bank</h2></div><p>Lens compares what a message promises with what the decoded UPI request will actually do. AI extracts meaning; fixed rules decide whether the two contradict.</p></div>
    <section class="panel lens-layout"><form id="lens-form" class="lens-form"><div class="eyebrow">Try the refund scam example</div><label for="lens-message">Message or surrounding story</label><textarea id="lens-message" required>ABC Support: Urgent! We are refunding ₹4,999. Scan this QR and enter your UPI PIN now.</textarea><label for="lens-uri">Decoded UPI QR / payment link</label><input id="lens-uri" required value="upi://pay?pa=rktraders@upi&amp;pn=R%20K%20Traders&amp;am=4999&amp;cu=INR&amp;tn=Refund"><div class="upload-row"><input id="lens-qr-file" type="file" accept="image/*"><label class="upload-label" for="lens-qr-file">Choose QR image</label><span id="lens-scan-state" class="scan-state">Or paste the decoded UPI link above.</span></div><button id="lens-check" class="primary" type="submit" style="margin-top:17px">Check before paying</button><div id="lens-runtime" class="mode-note">Checking AI runtime…</div><div class="mode-note">QR decoding happens only after you choose an image. PINs, OTPs, CVVs, passwords and card numbers are redacted before any AI provider receives the text.</div></form><div class="lens-result" aria-live="polite"><div class="eyebrow">Evidence-backed result</div><h3 id="lens-decision">Not checked yet</h3><p id="lens-summary">Run the example to see the expected action, actual payment and named contradictions.</p><div class="lens-facts"><div class="lens-fact"><small>Story expects</small><strong id="lens-expected">—</strong></div><div class="lens-fact"><small>Request actually does</small><strong id="lens-actual">—</strong></div><div class="lens-fact"><small>Resolved payee</small><strong id="lens-payee">—</strong></div></div><ul id="lens-findings" class="lens-findings"></ul><div id="lens-provider" class="mode-note">Provider details appear after analysis.</div></div></section>
    <div class="honesty"><b>Trust boundary:</b> Gemini is allowed to interpret the untrusted message. It does not parse the authoritative UPI fields, make the final policy decision, or declare a payment universally safe.</div>
    <div id="bank" class="section-head"><div><div class="eyebrow"><span class="number">02</span> · Customer view</div><h2>Use the actual Bank of Anthos website</h2></div><p>This is Google’s official sample banking frontend running locally. It is not a CARAPACE imitation and it does not use real money.</p></div>
    <section class="panel bank-layout"><aside class="bank-guide"><h3>Try the bank</h3><p>The bank is embedded here so you can see both systems together. You can also open it full-size.</p><div class="credential"><small>Public demo login</small><code>Username: testuser</code><code>Password: bankofanthos</code></div><a class="open-bank" href="__BANK_URL_HTML__" target="_blank" rel="noopener">Open official bank ↗</a><h3 style="margin-top:24px">Important</h3><p>A payment made manually in the bank is visible to CARAPACE as a ledger row, but it is marked <b>unbound</b> because no CARAPACE Payment Promise was created for it.</p></aside><div class="bank-frame-wrap"><div class="windowbar"><i></i><i></i><i></i><span>__BANK_URL_HTML__ · Bank of Anthos</span></div><iframe title="Official local Bank of Anthos website" src="__BANK_URL_HTML__"></iframe></div></section>
    <div class="section-head"><div><div class="eyebrow"><span class="number">03</span> · Evidence pipe</div><h2>Where CARAPACE gets the data</h2></div><p>CARAPACE does not read pixels or scrape the bank page. Its adapter reads authoritative server-side rows from the official ledger database.</p></div>
    <div class="pipe" aria-label="Data path"><div><b>Bank website</b><span>Customer sends artificial payment</span></div><span class="pipe-arrow">→</span><div><b>Official services + PostgreSQL</b><span>Bank processes and stores it</span></div><span class="pipe-arrow">→</span><div><b>CARAPACE Ledger Witness</b><span>Reads exact IDs and checks contracts</span></div></div>
    <section id="data" class="panel"><div class="source-grid"><div class="source-item"><small>Application</small><strong id="source-app">Loading…</strong></div><div class="source-item"><small>Database → table</small><strong id="source-table">Loading…</strong></div><div class="source-item"><small>Collection method</small><strong id="source-method">Loading…</strong></div><div class="source-item"><small>Trust rule</small><strong id="source-rule">Loading…</strong></div></div><div class="table-toolbar"><p>These are the newest raw artificial-money rows. <b>Unbound</b> means CARAPACE saw a row but has no customer promise to compare it with.</p><button id="refresh" class="secondary" type="button">Refresh rows</button></div><div class="table-scroll"><table><thead><tr><th>ID</th><th>From account</th><th>To account</th><th>Amount</th><th>Stored at</th><th>CARAPACE relationship</th></tr></thead><tbody id="ledger-body"><tr><td class="empty" colspan="6">Loading live ledger rows…</td></tr></tbody></table></div></section>
    <div id="fees" class="section-head"><div><div class="eyebrow">New India rule · FeeShield</div><h2>Prove the customer was not charged merchant MDR</h2></div><p>CARAPACE now calculates the permitted UPI MDR deterministically, binds customer fee = INR 0, and later checks the processor's merchant deduction.</p></div>
    <section class="panel" style="padding:24px;display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px">
      <div class="result-card"><small>Standard INR 10,000 P2M</small><strong>Merchant MDR: INR 40</strong><br><span class="good">Customer MDR: INR 0</span></div>
      <div class="result-card"><small>P2P or eligible small P2PM</small><strong>Free at every amount</strong><br><span>Verified classification required</span></div>
      <div class="result-card"><small>Essential sectors above INR 2,000</small><strong>Flat merchant MDR: INR 5</strong><br><span>Rail, telecom, insurance, fuel, agriculture</span></div>
      <div class="result-card"><small>What CARAPACE catches</small><strong class="mismatch-text">Hidden surcharge or wrong deduction</strong><br><span>Also flags suspicious threshold splitting</span></div>
      <div class="result-card"><small>Live deterministic check</small><strong>₹10,000 purchase + hidden ₹40 customer MDR</strong><br><button id="fee-check" class="secondary" type="button" style="margin-top:12px">Run FeeShield check</button><div id="fee-result" style="margin-top:10px;color:var(--muted)">Not checked yet.</div></div>
    </section>
    <div class="honesty"><b>Important:</b> this is not a 0.4% customer tax. The Ministry of Finance says customers must not pay MDR or hidden platform fees. FeeShield protects that rule and produces evidence for both customer and merchant.</div>
    <div id="verification" class="section-head"><div><div class="eyebrow"><span class="number">04</span> · Bound verification</div><h2>Run one complete safety experiment</h2></div><p>This controlled flow creates a promise first, so CARAPACE can prove what should have happened and compare it with what the bank stored.</p></div>
    <section class="panel experiment"><aside class="promise"><div class="eyebrow" style="color:#72dbe2">Payment Promise</div><h3>Customer approves one payment</h3><dl><div class="promise-row"><dt>Direction</dt><dd>SEND</dd></div><div class="promise-row"><dt>Amount</dt><dd>$49.99</dd></div><div class="promise-row"><dt>Recipient</dt><dd>Demo merchant</dd></div><div class="promise-row"><dt>Maximum debits</dt><dd>ONE</dd></div><div class="promise-row"><dt>Environment</dt><dd>Artificial money</dd></div></dl></aside><div class="experiment-main"><h3>What the button really does</h3><p>It creates a signed-style contract record, writes one Bank of Anthos ledger transaction, verifies it, deliberately repeats the debit as a faulty retry, then verifies both exact row IDs.</p><div class="flow"><div class="step"><b>1 · BIND</b><span>Create the customer’s expected payment.</span></div><div class="step"><b>2 · POST</b><span>Store one official ledger row.</span></div><div class="step"><b>3 · MATCH</b><span>Confirm one correct debit.</span></div><div class="step"><b>4 · MUTATE</b><span>Force a second retry debit.</span></div><div class="step"><b>5 · PROVE</b><span>Detect the rule violation.</span></div></div><div class="runline"><button id="run" class="primary" type="button">Run the bound safety test</button><small id="run-note">Creates fresh artificial accounts on every run.</small></div>
      <section id="results" aria-live="polite"><div id="result-banner" class="result-banner">CARAPACE caught the duplicate debit.</div><div class="receipt"><div class="receipt-head"><div><small>Customer Trust Receipt</small><strong id="receipt-id"></strong></div><span id="receipt-level" class="receipt-level"></span></div><p id="receipt-summary"></p><div class="receipt-stages"><div class="receipt-stage"><b class="good">✓ Payment fields bound</b><span>Amount and recipient matched the promise.</span></div><div class="receipt-stage"><b class="good">✓ Bank posting matched</b><span>One correct ledger debit was observed.</span></div><div class="receipt-stage"><b id="settlement-stage">… Settlement pending</b><span>Bank posting is not the same as final rail settlement.</span></div></div></div><div class="result-grid"><div class="result-card"><small>Payment Promise ID</small><strong id="contract-id"></strong></div><div class="result-card"><small>Evidence incident</small><strong id="case-id"></strong></div><div class="result-card"><small>First stored row</small><strong id="first-result" class="good"></strong></div><div class="result-card"><small>Forced retry row</small><strong id="duplicate-result" class="mismatch-text"></strong></div><div class="result-card"><small>Mismatch receipt</small><strong id="mismatch-receipt" class="mismatch-text"></strong></div><div class="result-card"><small>Why it is red</small><strong class="mismatch-text">Two debits broke the one-debit promise</strong></div></div><div class="mapping"><h4>Exact field mapping: promise → bank row → deterministic rule</h4><div class="mapping-row"><b>Approved amount: $49.99</b><b>→</b><span id="map-amount">Bank rows loading…</span><strong id="check-amount"></strong></div><div class="mapping-row"><b>Approved payer</b><b>→</b><span id="map-payer">Bank value loading…</span><strong id="check-payer"></strong></div><div class="mapping-row"><b>Maximum debits: 1</b><b>→</b><span id="map-count">Bank row count loading…</span><strong id="check-count"></strong></div></div><div id="proofops" class="proofops"><div class="eyebrow">ProofOps · Counterfactual Safety Search</div><h4 id="proof-title">Waiting for an evidence incident</h4><p id="proof-summary">After CARAPACE proves a failure, AI ranks testable causes and an allowlisted algorithm searches for the smallest intervention that restores every financial invariant.</p><div class="proof-grid"><div class="proof-card"><small>Reasoning provider</small><strong id="proof-provider">—</strong></div><div class="proof-card"><small>Suspected boundary</small><strong id="proof-component">—</strong></div><div class="proof-card"><small>Deterministic rerun</small><strong id="proof-verdict">—</strong></div><div class="proof-card"><small>Minimal intervention</small><strong id="proof-intervention">—</strong></div><div class="proof-card"><small>Experiments executed</small><strong id="proof-experiments">—</strong></div><div class="proof-card"><small>Release authority</small><strong>Human approval required</strong></div></div><ul id="proof-scenarios" class="scenario-list"></ul></div></section>
    </div></section><div class="honesty"><b>Why this is honest:</b> Bank of Anthos is the real official sample application, but all accounts and money are artificial. The test button currently uses a trusted local harness to create an exactly bound transaction. In a funded bank deployment, the bank SDK or processor would supply that binding and the ledger connector would be read-only.</div>
  </main>
  <script>
    const bankUrl=__BANK_URL_JSON__;const byId=id=>document.getElementById(id);const money=cents=>`$${(cents/100).toFixed(2)}`;
    function setStatus(key,ready){byId(`${key}-status`).textContent=ready?'Connected':'Unavailable';byId(`${key}-dot`).classList.toggle('ok',Boolean(ready))}
    async function refreshStatus(){try{const response=await fetch('/api/status');const data=await response.json();setStatus('bank',data.bank);setStatus('ledger',data.ledger);setStatus('api',data.api)}catch(_){for(const key of ['bank','ledger','api'])setStatus(key,false)}}
    async function refreshAiRuntime(){try{const response=await fetch('/api/ai/status');const data=await response.json();if(!response.ok)throw new Error(data.detail||'AI runtime unavailable');byId('lens-runtime').textContent=`AI runtime: ${data.mode} · ${data.model}. ${data.message}`;}catch(error){byId('lens-runtime').textContent=`AI runtime unavailable: ${error.message}`;byId('lens-runtime').className='mode-note error'}}
    function cell(row,value,asCode=false){const td=document.createElement('td');if(asCode){const code=document.createElement('code');code.textContent=value;td.appendChild(code)}else{td.textContent=value}row.appendChild(td)}
    function relationCell(row,record){const td=document.createElement('td');const badge=document.createElement('span');badge.className='badge '+(record.assurance_state==='MATCH'?'matched':record.assurance_state==='MISMATCH_SOURCE'?'failed':'unbound');badge.textContent=record.assurance_label;td.appendChild(badge);row.appendChild(td)}
    async function analyzeProofOps(caseId){byId('proof-title').textContent='Testing AI hypothesis in an isolated counterfactual…';byId('proof-summary').textContent='AI is restricted to ranked, allowlisted interventions. The financial verifier—not the model—decides whether an intervention works.';try{const response=await fetch('/api/proofops/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({case_id:caseId})});const data=await response.json();if(!response.ok)throw new Error(data.detail||'ProofOps analysis failed');byId('proof-title').textContent=data.verification_status==='COUNTERFACTUAL_VERIFIED'?'Minimal repair hypothesis independently verified':'No safe counterfactual repair found';byId('proof-summary').textContent=data.root_cause_summary;byId('proof-provider').textContent=`${data.mode} · ${data.model}`;byId('proof-component').textContent=data.suspected_component;byId('proof-verdict').textContent=`${data.counterfactual_search.original_verdict} → ${data.counterfactual_search.counterfactual_verdict}`;byId('proof-verdict').className=data.counterfactual_search.counterfactual_verdict==='MATCH'?'good':'bad';byId('proof-intervention').textContent=data.counterfactual_search.minimal_interventions.join(' + ')||'None';byId('proof-experiments').textContent=String(data.counterfactual_search.experiments_run);const list=byId('proof-scenarios');list.replaceChildren();for(const scenario of data.regression_scenarios){const item=document.createElement('li');const name=document.createElement('strong');name.textContent=scenario.name+': ';const detail=document.createTextNode(`${scenario.fault_injection} Expected: ${scenario.expected_contract}`);item.append(name,detail);list.appendChild(item)}}catch(error){byId('proof-title').textContent='ProofOps unavailable';byId('proof-title').className='error';byId('proof-summary').textContent=error.message}}
    async function refreshLedger(){const button=byId('refresh');button.disabled=true;try{const response=await fetch('/api/ledger/recent?limit=20');const data=await response.json();if(!response.ok)throw new Error(data.detail||'Could not read ledger');byId('source-app').textContent=data.source.application;byId('source-table').textContent=`${data.source.database} → ${data.source.schema}.${data.source.table}`;byId('source-method').textContent=data.source.collection_mode;byId('source-rule').textContent=data.source.binding_rule;const body=byId('ledger-body');body.replaceChildren();if(!data.records.length){const row=document.createElement('tr');const td=document.createElement('td');td.colSpan=6;td.className='empty';td.textContent='The ledger has no rows yet.';row.appendChild(td);body.appendChild(row)}for(const record of data.records){const row=document.createElement('tr');cell(row,`#${record.transaction_id}`,true);cell(row,record.from_account,true);cell(row,record.to_account,true);cell(row,money(record.amount_minor));cell(row,new Date(record.timestamp).toLocaleString());relationCell(row,record);body.appendChild(row)}}catch(error){const body=byId('ledger-body');body.replaceChildren();const row=document.createElement('tr');const td=document.createElement('td');td.colSpan=6;td.className='empty error';td.textContent=error.message;row.appendChild(td);body.appendChild(row)}finally{button.disabled=false}}
    byId('refresh').addEventListener('click',refreshLedger);
    byId('lens-qr-file').addEventListener('change',async event=>{const state=byId('lens-scan-state');const file=event.target.files&&event.target.files[0];if(!file){state.textContent='No image selected.';return}if(!('BarcodeDetector' in window)){state.textContent='This browser cannot decode QR images yet. Paste the UPI link instead.';return}state.textContent='Reading the selected image…';try{const detector=new BarcodeDetector({formats:['qr_code']});const bitmap=await createImageBitmap(file);const codes=await detector.detect(bitmap);bitmap.close();const upi=codes.map(code=>code.rawValue).find(value=>value&&value.toLowerCase().startsWith('upi://'));if(!upi)throw new Error('No UPI QR code was found in that image.');byId('lens-uri').value=upi;state.textContent='UPI QR decoded. Review the fields, then run the check.';}catch(error){state.textContent=error.message}});
    byId('lens-form').addEventListener('submit',async event=>{event.preventDefault();const button=byId('lens-check');button.disabled=true;button.textContent='Comparing story with payment…';byId('lens-decision').textContent='Checking…';try{const response=await fetch('/api/lens/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message_text:byId('lens-message').value,payment_uri:byId('lens-uri').value,locale:'en-IN'})});const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Lens analysis failed');byId('lens-decision').textContent=data.decision;byId('lens-decision').className=data.decision==='STOP'?'bad':data.decision==='ALLOW'?'good':'';byId('lens-summary').textContent=data.plain_language_result;const expectedAmount=data.intent.expected_amount_minor===null?'amount unknown':`₹${(data.intent.expected_amount_minor/100).toFixed(2)}`;const actualAmount=data.payment.amount_minor===null?'amount not fixed':`₹${(data.payment.amount_minor/100).toFixed(2)}`;byId('lens-expected').textContent=`${data.intent.expected_direction} · ${expectedAmount}`;byId('lens-actual').textContent=`${data.payment.direction} · ${actualAmount}`;byId('lens-payee').textContent=`${data.payment.payee_name||'Name unavailable'} · ${data.payment.payee_id}`;const list=byId('lens-findings');list.replaceChildren();for(const finding of data.findings){const item=document.createElement('li');const title=document.createElement('strong');title.textContent=`${finding.severity}: ${finding.title}`;const detail=document.createElement('div');detail.textContent=finding.explanation;item.append(title,detail);list.appendChild(item)}if(!data.findings.length){const item=document.createElement('li');item.textContent='No contradiction found in the checked fields.';list.appendChild(item)}const redaction=data.provenance.input_redaction_applied?' Sensitive credentials were redacted before extraction.':'';byId('lens-provider').textContent=`Extraction: ${data.provenance.provider} / ${data.provenance.model} (${data.provenance.mode}). Final rule: ${data.provenance.deterministic_policy}.${redaction}`;}catch(error){byId('lens-decision').textContent='UNAVAILABLE';byId('lens-decision').className='error';byId('lens-summary').textContent=error.message}finally{button.disabled=false;button.textContent='Check again'}});
    byId('fee-check').addEventListener('click',async()=>{const button=byId('fee-check');button.disabled=true;button.textContent='Checking exact policy…';try{const response=await fetch('/api/fee-shield-demo',{method:'POST'});const data=await response.json();if(!response.ok)throw new Error(data.detail||'Fee check failed');byId('fee-result').innerHTML=`<b class="${data.verdict==='COMPLIANT'?'good':'bad'}">${data.verdict}</b><br>Expected merchant MDR: ₹${(data.expected_mdr_minor/100).toFixed(2)}<br>Customer MDR detected: ₹${(data.customer_mdr_surcharge_minor/100).toFixed(2)}<br>${data.violations.join(', ')}`;}catch(error){byId('fee-result').textContent=error.message;byId('fee-result').className='error'}finally{button.disabled=false;button.textContent='Run again'}});
    byId('run').addEventListener('click',async()=>{const button=byId('run');button.disabled=true;button.textContent='Running five real steps…';byId('run-note').textContent='Promise → official row → MATCH → duplicate row → incident';try{const response=await fetch('/api/run',{method:'POST'});const data=await response.json();if(!response.ok)throw new Error(data.detail||'Safety test failed');byId('contract-id').textContent=data.contract_id;byId('case-id').textContent=data.incident_case_id;byId('receipt-id').textContent=data.trust_receipt_id;byId('receipt-level').textContent=data.trust_receipt_level.replaceAll('_',' ');byId('receipt-summary').textContent=data.trust_receipt_summary;byId('settlement-stage').textContent=data.settlement_state==='PASS'?'✓ Settlement confirmed':'… Settlement pending';byId('settlement-stage').className=data.settlement_state==='PASS'?'good':'';byId('mismatch-receipt').textContent=`${data.mismatch_receipt_id} · ${data.mismatch_receipt_level}`;byId('first-result').textContent=`#${data.first_transaction_id} · ${data.correct_payment_verdict}`;byId('duplicate-result').textContent=`#${data.duplicate_transaction_id} · ${data.duplicate_payment_verdict}`;byId('map-amount').textContent=`Both rows contain ${money(data.amount_minor)}`;byId('check-amount').textContent='✓ amount matched';byId('check-amount').className='good';byId('map-payer').textContent=`Both rows debit ${data.payer_account}`;byId('check-payer').textContent='✓ payer matched';byId('map-count').textContent='2 POSTED debit rows';byId('check-count').textContent='✕ expected at most 1';byId('check-count').className='bad';byId('result-banner').textContent=data.overall==='PASS'?'CARAPACE caught the duplicate debit and preserved the evidence.':'The integration did not produce the expected proof.';byId('result-banner').className='result-banner '+(data.overall==='PASS'?'':'error');byId('results').classList.add('visible');byId('run-note').textContent='Incident preserved. ProofOps is now testing the smallest safe repair hypothesis.';await refreshLedger();await analyzeProofOps(data.incident_case_id);byId('run-note').textContent='Complete. Failure reproduced and counterfactual repair tested.';byId('results').scrollIntoView({behavior:'smooth',block:'start'})}catch(error){byId('run-note').textContent=error.message;byId('run-note').className='error'}finally{button.disabled=false;button.textContent='Run another bound test'}});
    refreshStatus();refreshAiRuntime();refreshLedger();setInterval(refreshStatus,15000);
  </script>
</body>
</html>"""


def _url_is_ready(url: str) -> bool:
    try:
        with urlopen(url, timeout=3) as response:
            return response.status == 200
    except (OSError, URLError):
        return False


def _post_json(
    url: str,
    payload: dict[str, object],
    headers: dict[str, str],
    timeout_seconds: int = 10,
) -> dict[str, object]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_json(url: str) -> dict[str, object]:
    with urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def create_demo_app() -> FastAPI:
    if os.getenv("CARAPACE_DEMO_ENABLED", "false").lower() != "true":
        raise RuntimeError("CARAPACE_DEMO_ENABLED=true is required")
    database_url = os.environ["BOA_DATABASE_URL"]
    api_base_url = os.environ["CARAPACE_API_BASE_URL"]
    bank_internal_url = os.getenv("BOA_FRONTEND_URL", "http://anthos-frontend:8080")
    bank_public_url = os.getenv("BOA_PUBLIC_FRONTEND_URL", "http://localhost:8081")
    tenant = os.getenv("CARAPACE_TENANT", "demo-bank")
    api_key = os.getenv("CARAPACE_API_KEY", "local-demo-key-change-me")
    bindings: dict[int, dict[str, str | None]] = {}
    ledger = BankOfAnthosLedger(database_url)
    application = FastAPI(title="CARAPACE Bank of Anthos Control Room",docs_url=None,redoc_url=None,openapi_url=None)

    @application.get("/", response_class=HTMLResponse)
    async def home() -> HTMLResponse:
        page = (
            DEMO_HTML
            .replace("</head>", '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@phosphor-icons/web@2.1.1/src/regular/style.css"><link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@phosphor-icons/web@2.1.1/src/fill/style.css"></head>')
            .replace("</style>", f"{FUTURE_CSS}</style>")
            .replace("<main>", f"<main>{ASSURANCE_FLOW_HTML}", 1)
            .replace("</body>", f"{FUTURE_JS}</body>")
            .replace("__BANK_URL_HTML__", html.escape(bank_public_url, quote=True))
            .replace("__BANK_URL_JSON__", json.dumps(bank_public_url))
        )
        return HTMLResponse(
            page,
            headers={
                "Cache-Control": "no-store",
                "Content-Security-Policy": (
                    "default-src 'self'; "
                    "style-src 'unsafe-inline' https://cdn.jsdelivr.net; "
                    "font-src 'self' https://cdn.jsdelivr.net; "
                    "script-src 'unsafe-inline' https://cdn.jsdelivr.net; "
                    "connect-src 'self' https://cdn.jsdelivr.net; "
                    "img-src 'self' data:; "
                    "frame-src http://localhost:8081 http://127.0.0.1:8081"
                ),
            },
        )

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status":"ok","service":"carapace-anthos-control-room"}

    @application.get("/api/status")
    async def integration_status() -> dict[str, object]:
        api_ready,bank_ready,ledger_ready=await run_in_threadpool(lambda:(_url_is_ready(f"{api_base_url.rstrip('/')}/health/ready"),_url_is_ready(f"{bank_internal_url.rstrip('/')}/ready"),ledger.is_ready()))
        return {"api":api_ready,"bank":bank_ready,"ledger":ledger_ready,"full_bank_application":bank_ready,"scope":"official-bank-of-anthos-local-compose"}

    @application.get("/api/ledger/recent")
    async def recent_ledger_rows(limit: int = 20) -> dict[str, object]:
        try:
            rows=await run_in_threadpool(ledger.fetch_recent_transactions,limit)
        except ValueError as error:
            raise HTTPException(status_code=400,detail=str(error)) from error
        except Exception as error:
            LOGGER.exception("Could not read Bank of Anthos ledger")
            raise HTTPException(status_code=503,detail="The official ledger is not available.") from error
        records=[]
        for row in rows:
            record=row.as_public_record();binding=bindings.get(row.transaction_id)
            if binding is None: record.update(assurance_state="UNBOUND",assurance_label="Observed · no Payment Promise",contract_id=None)
            else: record.update(binding)
            records.append(record)
        return {"source":BANK_OF_ANTHOS_SOURCE,"records":records}

    @application.post("/api/run")
    async def run_integration() -> dict[str, object]:
        operation=partial(run_demo,database_url=database_url,api_base_url=api_base_url,tenant=tenant,api_key=api_key)
        try:
            result=await run_in_threadpool(operation)
        except Exception as error:
            LOGGER.exception("Bank of Anthos integration demo failed")
            raise HTTPException(status_code=500,detail="The local integration could not complete. Check Docker logs.") from error
        bindings.clear()
        bindings[result.first_transaction_id]={"assurance_state":"MATCH","assurance_label":"Bound · first row matched","contract_id":result.contract_id}
        bindings[result.duplicate_transaction_id]={"assurance_state":"MISMATCH_SOURCE","assurance_label":"Bound · duplicate caused mismatch","contract_id":result.contract_id}
        return result.as_dict()

    @application.post("/api/lens/analyze")
    async def run_lens_analysis(payload: dict[str, object]) -> dict[str, object]:
        try:
            return await run_in_threadpool(
                _post_json,
                f"{api_base_url.rstrip('/')}/v1/lens/analyze",
                payload,
                {},
            )
        except Exception as error:
            LOGGER.exception("Lens demonstration failed")
            raise HTTPException(
                status_code=503,
                detail="The Lens analysis API is not available.",
            ) from error

    @application.get("/api/ai/status")
    async def ai_runtime_status() -> dict[str, object]:
        try:
            return await run_in_threadpool(
                _get_json,
                f"{api_base_url.rstrip('/')}/v1/ai/status",
            )
        except Exception as error:
            LOGGER.exception("AI runtime status is unavailable")
            raise HTTPException(
                status_code=503,
                detail="The CARAPACE AI runtime status is unavailable.",
            ) from error

    @application.post("/api/proofops/analyze")
    async def run_proofops_analysis(payload: dict[str, object]) -> dict[str, object]:
        case_id = payload.get("case_id")
        if not isinstance(case_id, str) or not case_id.startswith("case_"):
            raise HTTPException(status_code=400, detail="A valid evidence case is required.")
        headers = {
            "X-Carapace-Tenant": tenant,
            "X-Carapace-API-Key": api_key,
        }
        try:
            return await run_in_threadpool(
                _post_json,
                f"{api_base_url.rstrip('/')}/v1/cases/{quote(case_id, safe='')}/analyze",
                {},
                headers,
                45,
            )
        except Exception as error:
            LOGGER.exception("ProofOps incident analysis failed")
            raise HTTPException(
                status_code=503,
                detail="ProofOps could not analyze the evidence incident.",
            ) from error

    @application.post("/api/fee-shield-demo")
    async def run_fee_shield_demo() -> dict[str, object]:
        payload: dict[str, object] = {
            "amount_minor": 1_000_000,
            "initiated_on": "2026-10-15",
            "payment_kind": "P2M",
            "customer_mdr_surcharge_minor": 4_000,
            "actual_merchant_mdr_minor": 4_000,
            "sector": "STANDARD",
        }
        headers = {
            "X-Carapace-Tenant": tenant,
            "X-Carapace-API-Key": api_key,
        }
        try:
            return await run_in_threadpool(
                _post_json,
                f"{api_base_url.rstrip('/')}/v1/fees/upi/assess",
                payload,
                headers,
            )
        except Exception as error:
            LOGGER.exception("FeeShield demonstration failed")
            raise HTTPException(
                status_code=503,
                detail="The FeeShield API is not available.",
            ) from error

    return application


app=create_demo_app()


def main() -> None:
    port=int(os.getenv("PORT","8090"));uvicorn.run("carapace_integrations.anthos_web:app",host="0.0.0.0",port=port)


if __name__ == "__main__":
    main()
