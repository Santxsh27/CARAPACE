"""Single-page development console for the Financial Friday sandbox."""

FINANCIAL_FRIDAY_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Financial Friday safely plans, proves and executes bounded financial tasks in an artificial-money sandbox.">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 64 64%22><rect width=%2264%22 height=%2264%22 rx=%2218%22 fill=%22%23c7ff68%22/><text x=%2232%22 y=%2243%22 text-anchor=%22middle%22 font-family=%22Arial%22 font-size=%2236%22 font-weight=%22900%22 fill=%22%23080b10%22>F</text></svg>">
  <title>Financial Friday · AI financial operator</title>
  <style>
    :root{
      color-scheme:dark;--bg:#080b10;--panel:#10151d;--panel2:#151b24;--line:#27303d;
      --ink:#f4f7fb;--muted:#98a4b5;--lime:#c7ff68;--blue:#79a7ff;--cyan:#63e7e1;
      --red:#ff707d;--amber:#ffc969;--radius:20px;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif
    }
    *{box-sizing:border-box}html{background:var(--bg)}body{margin:0;color:var(--ink);background:radial-gradient(circle at 70% -20%,#1c2a38 0,transparent 35%),var(--bg);min-height:100vh}
    button,textarea,select{font:inherit}button{cursor:pointer}button:focus-visible,textarea:focus-visible,select:focus-visible,a:focus-visible{outline:3px solid rgba(121,167,255,.55);outline-offset:3px}
    .shell{width:min(1320px,calc(100% - 32px));margin:auto}.topbar{height:74px;border-bottom:1px solid var(--line);background:rgba(8,11,16,.84);backdrop-filter:blur(18px);position:sticky;top:0;z-index:20}
    .topbar .shell{height:100%;display:flex;align-items:center;gap:18px}.mark{width:36px;height:36px;border-radius:12px;background:var(--lime);color:#111;display:grid;place-items:center;font-weight:950;box-shadow:0 0 28px rgba(199,255,104,.18)}
    .brand{font-size:15px;font-weight:850;letter-spacing:-.01em}.brand small{display:block;color:var(--muted);font-weight:550;font-size:11px;margin-top:2px}.top-spacer{flex:1}.pill{display:flex;align-items:center;gap:8px;border:1px solid var(--line);padding:8px 11px;border-radius:999px;color:var(--muted);font-size:12px;background:#0d1218}.dot{width:7px;height:7px;border-radius:50%;background:var(--cyan);box-shadow:0 0 10px var(--cyan)}
    .layout{display:grid;grid-template-columns:300px minmax(0,1fr);gap:18px;padding:22px 0 44px}.sidebar,.workspace{border:1px solid var(--line);background:rgba(15,20,28,.88);border-radius:var(--radius)}
    .sidebar{padding:20px;align-self:start;position:sticky;top:96px}.eyebrow{color:var(--lime);font-size:10px;font-weight:850;letter-spacing:.15em;text-transform:uppercase}.sidebar h1{font-size:24px;line-height:1.12;margin:9px 0 8px;letter-spacing:-.035em}.sidebar>p{color:var(--muted);font-size:13px;line-height:1.55;margin:0 0 19px}
    .label{font-size:11px;font-weight:800;color:#dfe5ee;margin-bottom:8px;display:block}.goal{width:100%;min-height:116px;resize:none;border:1px solid #303b4a;border-radius:14px;background:#0a0f15;color:#dce4ef;padding:13px;line-height:1.45;font-size:13px}.goal-note{font-size:10px;color:#748095;line-height:1.45;margin:7px 0 18px}
    .scenario-list{display:grid;gap:7px}.scenario{width:100%;text-align:left;border:1px solid transparent;background:transparent;color:#b7c0ce;padding:11px 12px;border-radius:13px;display:grid;grid-template-columns:27px 1fr;gap:9px;align-items:start}.scenario:hover{background:#161d27}.scenario[aria-pressed="true"]{background:#1a222d;border-color:#3a4656;color:#fff}.scenario-icon{width:27px;height:27px;border-radius:9px;background:#242e3b;display:grid;place-items:center;font-size:12px}.scenario b{font-size:12px;display:block}.scenario small{display:block;color:#7f8b9e;margin-top:3px;line-height:1.3}.sidebar-links{border-top:1px solid var(--line);padding-top:15px;margin-top:18px;display:flex;gap:14px;flex-wrap:wrap}.sidebar-links a{font-size:11px;color:#9ba8bb;text-decoration:none}.sidebar-links a:hover{color:#fff}
    .workspace{min-height:760px;overflow:hidden}.hero{padding:32px 34px 25px;border-bottom:1px solid var(--line);display:grid;grid-template-columns:1fr auto;gap:24px;align-items:end;background:linear-gradient(130deg,rgba(121,167,255,.07),transparent 46%)}.hero h2{font-size:clamp(29px,4vw,45px);letter-spacing:-.052em;line-height:1.02;margin:9px 0 10px;max-width:680px}.hero p{margin:0;color:var(--muted);font-size:14px;line-height:1.55;max-width:690px}.hero strong{color:#fff}
    .run-controls{display:grid;gap:9px;min-width:200px}.planner{border:1px solid var(--line);border-radius:11px;background:#0b1016;color:#dce4ef;padding:9px 11px;font-size:12px}.run{border:0;border-radius:13px;background:var(--lime);color:#10130c;padding:13px 17px;font-weight:900;box-shadow:0 10px 30px rgba(199,255,104,.12)}.run:hover{filter:brightness(1.06);transform:translateY(-1px)}.run:disabled{opacity:.58;cursor:wait;transform:none}.scope{font-size:10px;color:#778396;text-align:center}
    .body{padding:25px 34px 34px}.promise{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:22px}.promise div{border:1px solid var(--line);border-radius:15px;background:#0c1118;padding:14px}.promise span{font-size:10px;color:#7f8a9a;display:block;margin-bottom:5px}.promise b{font-size:13px;font-weight:740}.promise i{color:var(--lime);font-style:normal;margin-right:6px}
    .pipeline{position:relative;display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:22px}.stage{position:relative;border:1px solid var(--line);border-radius:15px;padding:15px 13px;background:#0b1016;min-height:101px;transition:.24s ease}.stage .number{font-size:10px;color:#708096}.stage b{display:block;font-size:12px;margin:12px 0 4px}.stage small{display:block;color:#788598;line-height:1.35;font-size:10px}.stage.active{border-color:var(--blue);box-shadow:0 0 0 1px rgba(121,167,255,.22),0 12px 35px rgba(0,0,0,.2);transform:translateY(-2px)}.stage.done{border-color:rgba(99,231,225,.45)}.stage.done .number{color:var(--cyan)}.stage.blocked{border-color:rgba(255,112,125,.55)}.stage.blocked .number{color:var(--red)}
    .empty{border:1px dashed #303a47;border-radius:18px;padding:40px 24px;text-align:center;background:#0b0f15}.empty .orb{width:62px;height:62px;border:1px solid #364253;border-radius:50%;display:grid;place-items:center;margin:0 auto 15px;font-size:22px;color:var(--lime);background:radial-gradient(circle,#1f2b25,#0c1117 68%)}.empty h3{font-size:17px;margin:0 0 7px}.empty p{color:var(--muted);font-size:13px;margin:0 auto;max-width:470px;line-height:1.55}
    .result{display:none}.result.visible{display:block}.verdict{border:1px solid var(--line);border-radius:18px;padding:19px 20px;display:flex;gap:15px;align-items:flex-start;margin-bottom:15px;background:#0b1016}.verdict-icon{width:38px;height:38px;border-radius:12px;display:grid;place-items:center;background:#202a35;flex:0 0 auto}.verdict h3{margin:0 0 5px;font-size:18px}.verdict p{margin:0;color:var(--muted);line-height:1.5;font-size:13px}.verdict.good{border-color:rgba(99,231,225,.4)}.verdict.good .verdict-icon{background:rgba(99,231,225,.13);color:var(--cyan)}.verdict.bad{border-color:rgba(255,112,125,.45)}.verdict.bad .verdict-icon{background:rgba(255,112,125,.12);color:var(--red)}.verdict.warn{border-color:rgba(255,201,105,.4)}.verdict.warn .verdict-icon{background:rgba(255,201,105,.12);color:var(--amber)}
    .result-grid{display:grid;grid-template-columns:1.1fr .9fr;gap:15px}.card{border:1px solid var(--line);background:#0c1118;border-radius:17px;padding:18px}.card-head{display:flex;justify-content:space-between;align-items:start;gap:10px;margin-bottom:15px}.card h3{font-size:13px;margin:0}.badge{font-size:9px;letter-spacing:.08em;text-transform:uppercase;padding:5px 7px;border-radius:999px;background:#202834;color:#a9b4c5}.steps,.checks,.events{list-style:none;margin:0;padding:0;display:grid;gap:8px}.steps li,.checks li{display:grid;grid-template-columns:27px 1fr;gap:9px;align-items:center;border:1px solid #222b37;border-radius:11px;padding:9px 10px;font-size:11px;color:#c6cfda}.steps .step-icon,.checks .step-icon{width:27px;height:27px;border-radius:8px;background:#19222d;display:grid;place-items:center;color:var(--cyan);font-size:10px}.checks li{grid-template-columns:18px 1fr;padding:8px 10px}.checks .step-icon{width:18px;height:18px;background:transparent;color:var(--lime)}
    .facts{display:grid;grid-template-columns:1fr 1fr;gap:9px}.fact{border:1px solid #222b37;border-radius:11px;padding:10px}.fact span{display:block;color:#778397;font-size:9px;text-transform:uppercase;letter-spacing:.08em;margin-bottom:5px}.fact b{font-size:12px;overflow-wrap:anywhere}.receipt{margin-top:15px}.receipt code{display:block;background:#080c11;border:1px solid #222b37;border-radius:12px;padding:12px;font-size:10px;color:#99a7b9;overflow-wrap:anywhere;line-height:1.5}.activity{margin-top:15px}.events li{border-left:2px solid #334052;padding:2px 0 10px 12px}.events b{font-size:11px;display:block}.events small{font-size:10px;color:#7f8b9c;line-height:1.45}.technical{margin-top:15px}.technical summary{cursor:pointer;font-size:11px;color:#9faabd}.technical pre{background:#070b10;border-radius:12px;padding:13px;white-space:pre-wrap;overflow-wrap:anywhere;font:10px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace;color:#92a0b3;max-height:330px;overflow:auto}
    .toast{position:fixed;right:22px;bottom:22px;border:1px solid #3a4655;background:#151b24;color:#e8edf4;padding:12px 14px;border-radius:12px;font-size:12px;box-shadow:0 18px 55px #000;transform:translateY(25px);opacity:0;pointer-events:none;transition:.2s}.toast.show{transform:none;opacity:1}
    @media(max-width:920px){.layout{grid-template-columns:1fr}.sidebar{position:static}.scenario-list{grid-template-columns:1fr 1fr}.hero{grid-template-columns:1fr}.run-controls{grid-template-columns:1fr 1fr}.scope{grid-column:1/-1}.result-grid{grid-template-columns:1fr}}
    @media(max-width:620px){.shell{width:min(100% - 18px,1320px)}.pill.optional{display:none}.layout{padding-top:10px}.sidebar,.workspace{border-radius:16px}.hero,.body{padding:22px 18px}.scenario-list,.promise,.pipeline{grid-template-columns:1fr}.run-controls{grid-template-columns:1fr}.pipeline{padding-left:12px}.stage{min-height:auto}.topbar{height:64px}.facts{grid-template-columns:1fr}}
    @media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important}}
  </style>
</head>
<body>
  <header class="topbar"><div class="shell">
    <div class="mark" aria-hidden="true">F</div><div class="brand">Financial Friday<small>Your bounded AI financial operator</small></div>
    <div class="top-spacer"></div><div class="pill"><span class="dot"></span><span id="ai-status">Connecting…</span></div><div class="pill optional">Artificial money</div>
  </div></header>
  <main class="shell layout">
    <aside class="sidebar">
      <div class="eyebrow">Development sandbox</div><h1>Tell Friday the outcome. Not every step.</h1>
      <p>Friday plans the route, proves it stays inside your permission, and acts only through a restricted test provider.</p>
      <label class="label" for="goal">Current delegated goal</label>
      <textarea class="goal" id="goal" readonly>Pay this verified electricity bill once, with no subscription or extra fee.</textarea>
      <p class="goal-note">Locked for this first vertical slice. Free-form goals come only after the permission model is tested.</p>
      <span class="label">Try a real safety condition</span><div id="scenarios" class="scenario-list" aria-label="Sandbox scenarios"></div>
      <div class="sidebar-links"><a href="/operations">Earlier operations lab</a><a href="/payment-check">Payment check</a><a href="http://localhost:8080/docs" target="_blank" rel="noopener">API docs ↗</a></div>
    </aside>
    <section class="workspace" aria-labelledby="workspace-title">
      <div class="hero"><div><div class="eyebrow">Friday is ready</div><h2 id="workspace-title">One goal in. One verified outcome out.</h2><p id="scenario-copy">Choose a scenario and let <strong>Gemini plan</strong>. Independent code decides whether anything may execute.</p></div>
        <div class="run-controls"><select class="planner" id="planner" aria-label="Planning engine"><option value="configured">Gemini / configured AI</option><option value="local">Local rules comparison</option></select><button class="run" id="run" type="button">Ask Friday to handle it</button><div class="scope">Restricted sandbox · no real bank access</div></div>
      </div>
      <div class="body">
        <article class="card" style="margin-bottom:22px">
          <div class="card-head"><h3>Friday keeps an eye on your bills</h3><span class="badge" id="watch-status">Loading</span></div>
          <p>Enable the sandbox feed once. Friday checks incoming sample bills in the background, even when this page is closed while Docker runs. It prepares tasks and in-app due reminders; payments still require your decision.</p>
          <button class="run" id="watch-toggle" type="button" disabled>Enable bill monitoring</button>
          <button class="planner" id="deliver-bill" type="button">Deliver selected sample bill</button>
          <p id="inbox-error" role="status"></p><ul class="events" id="bill-inbox" aria-live="polite"></ul>
          <small>Sample provider data only. Real inbox connection and document extraction are not connected yet.</small>
        </article>
        <div class="promise" aria-label="Delegation limits"><div><span>Payment type</span><b><i>✓</i>One time only</b></div><div><span>Maximum total</span><b><i>✓</i>₹1,999.00</b></div><div><span>Permission</span><b><i>✓</i>No fee or subscription</b></div></div>
        <div class="pipeline" aria-label="Financial Friday execution pipeline">
          <div class="stage" data-stage="plan"><span class="number">01</span><b>AI plans</b><small>Gemini proposes typed actions, never code.</small></div>
          <div class="stage" data-stage="prove"><span class="number">02</span><b>Kernel proves</b><small>Exact payee, total, fee, cadence and sequence.</small></div>
          <div class="stage" data-stage="challenge"><span class="number">03</span><b>Attacks tested</b><small>Hostile mutations must all be rejected.</small></div>
          <div class="stage" data-stage="act"><span class="number">04</span><b>Sandbox acts</b><small>One idempotent artificial-money effect.</small></div>
        </div>
        <div class="empty" id="empty"><div class="orb">✦</div><h3>Friday has not acted yet</h3><p>Select a test situation on the left. The interface will show the plan, the proof and the outcome—not just an AI answer.</p></div>
        <div class="result" id="result" aria-live="polite">
          <div class="verdict" id="verdict"><div class="verdict-icon" id="verdict-icon">✓</div><div><h3 id="verdict-title"></h3><p id="verdict-copy"></p></div></div>
          <div class="result-grid">
            <article class="card"><div class="card-head"><h3>Verified action program</h3><span class="badge" id="model-badge">AI proposal</span></div><ol class="steps" id="steps"></ol><div class="activity"><div class="card-head"><h3>What Friday actually did</h3></div><ul class="events" id="events"></ul></div></article>
            <div><article class="card"><div class="card-head"><h3>Independent safety proof</h3><span class="badge" id="proof-badge">Not run</span></div><div class="facts" id="facts"></div><ul class="checks" id="checks"></ul></article><article class="card receipt"><div class="card-head"><h3>Outcome evidence</h3><span class="badge" id="receipt-badge">Sandbox</span></div><code id="receipt">No receipt was created.</code></article></div>
          </div>
          <details class="technical"><summary>Open complete technical evidence</summary><pre id="raw"></pre></details>
        </div>
      </div>
    </section>
  </main>
  <div class="toast" id="toast" role="status"></div>
  <script>
    const $=id=>document.getElementById(id);let selected='genuine-bill';let catalogue=[];
    const labels={
      'genuine-bill':['✓','Pay a genuine bill'],
      'subscription-trap':['↻','Avoid a subscription trap'],
      'recurring-only':['⊘','Refuse an unsafe option'],
      'recipient-swap':['⇄','Catch a changed recipient'],
      'unknown-outcome':['?','Recover after a timeout']
    };
    const nice=s=>String(s||'').toLowerCase().replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
    const money=n=>'₹'+((Number(n)||0)/100).toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2});
    function node(tag,text,cls){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(cls)el.className=cls;return el;}
    function toast(message){$('toast').textContent=message;$('toast').classList.add('show');setTimeout(()=>$('toast').classList.remove('show'),2400);}
    function selectScenario(id){selected=id;document.querySelectorAll('.scenario').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.id===id)));const item=catalogue.find(x=>x.id===id);$('scenario-copy').textContent=item?.description||'';$('result').classList.remove('visible');$('empty').hidden=false;resetStages();}
    function resetStages(){document.querySelectorAll('.stage').forEach(stage=>stage.classList.remove('active','done','blocked'));}
    function pulse(stage){resetStages();document.querySelector(`[data-stage="${stage}"]`)?.classList.add('active');}
    function fillStages(result){resetStages();const passed=Boolean(result.program?.verification?.passed);document.querySelector('[data-stage="plan"]').classList.add('done');document.querySelector('[data-stage="prove"]').classList.add(passed?'done':'blocked');if(passed)document.querySelector('[data-stage="challenge"]').classList.add(result.program.adversarial_checks.every(x=>x.rejected)?'done':'blocked');document.querySelector('[data-stage="act"]').classList.add(result.status==='HELD'?'blocked':'done');}
    function outcomeText(r){
      if(r.status==='COMPLETED_SYNTHETIC')return ['good','Task completed safely','Friday selected an allowed route, the kernel proved it, and exactly one artificial-money payment was recorded.'];
      if(r.status==='ALREADY_COMPLETED')return ['good','Already handled—nothing repeated','Friday found the signed earlier result and did not create another payment.'];
      if(r.status==='RECONCILED_COMPLETED')return ['warn','Previous payment found—no retry sent','The earlier provider outcome was checked first. It had already succeeded, so Friday created no new payment.'];
      const reasons=(r.outcome?.reason||['NO_VERIFIED_PROGRAM']).map(nice).join(' · ');return ['bad','Friday safely refused this task',`The request could not be completed without breaking your permission: ${reasons}. No money moved.`];
    }
    function render(r){
      $('empty').hidden=true;$('result').classList.add('visible');fillStages(r);const [tone,title,copy]=outcomeText(r);$('verdict').className='verdict '+tone;$('verdict-icon').textContent=tone==='bad'?'!':tone==='warn'?'↻':'✓';$('verdict-title').textContent=title;$('verdict-copy').textContent=copy;
      $('model-badge').textContent=`${r.provenance.mode} · ${r.provenance.model}`;$('steps').replaceChildren();const steps=r.program?.candidate?.steps||[];
      if(!steps.length){const li=node('li','No executable program passed the safety kernel.');li.prepend(node('span','—','step-icon'));$('steps').append(li);}else steps.forEach((step,index)=>{const li=node('li');li.append(node('span',String(index+1).padStart(2,'0'),'step-icon'),node('span',nice(step.action)+(step.option_id?' · '+step.option_id:'')));$('steps').append(li);});
      const verification=r.program?.verification;const attacks=r.program?.adversarial_checks||[];$('proof-badge').textContent=verification?.passed?'Verified':'Execution held';$('facts').replaceChildren();[
        ['Payee',r.goal.payee_id],['Maximum',money(r.goal.max_total_minor)],['New payment',String(Boolean(r.outcome?.new_payment_created))],['Model calls',String(r.provenance.successful_model_calls)]
      ].forEach(([key,value])=>{const box=node('div',undefined,'fact');box.append(node('span',key),node('b',value));$('facts').append(box);});
      $('checks').replaceChildren();if(attacks.length)attacks.forEach(check=>{const li=node('li');li.append(node('span',check.rejected?'✓':'!','step-icon'),node('span',check.name));$('checks').append(li);});else{const li=node('li');li.append(node('span',r.status==='HELD'?'✓':'—','step-icon'),node('span',r.status==='HELD'?'Unsafe execution was prevented':'No adversarial checks reported'));$('checks').append(li);}
      $('events').replaceChildren();r.events.forEach(event=>{const li=node('li');let detail='';if(event.type==='AI_PROGRAM_PROPOSED')detail=`Attempt ${event.attempt}: ${event.verification.passed?'accepted by the kernel':'rejected by the kernel'}.`;else if(event.type==='RESTRICTED_EXECUTOR_RESULT')detail=event.new_payment?'One artificial-money effect was written and read back.':'No new financial effect was created.';else if(event.type==='RECONCILED_BEFORE_RETRY')detail='Existing provider state was checked before any retry.';else detail=event.error_type||'';li.append(node('b',nice(event.type)),node('small',detail));$('events').append(li);});
      const receipt=r.outcome?.receipt;$('receipt-badge').textContent=receipt?'Signed receipt':r.status==='HELD'?'No execution':'Reconciled';$('receipt').textContent=receipt?`Operation ${receipt.payload.operation_id}\n${money(receipt.payload.amount_minor)} · ${receipt.payload.payee_id}\nKey ${receipt.key_id}\nSignature ${receipt.signature.slice(0,34)}…`:r.outcome?.message||'No receipt was created because the safety gate held execution.';
      $('raw').textContent=JSON.stringify(r,null,2);history.replaceState(null,'','#run='+encodeURIComponent(r.run_id));
    }
    async function run(){
      const button=$('run');button.disabled=true;button.textContent='Friday is working…';$('empty').hidden=false;$('result').classList.remove('visible');$('empty').querySelector('h3').textContent='Building a bounded action program';$('empty').querySelector('p').textContent='Gemini can propose. Only the independent safety kernel can authorize the sandbox executor.';pulse('plan');
      const stageTimer=null;
      try{const response=await fetch('/api/friday/scenarios/'+encodeURIComponent(selected)+'/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({planner:$('planner').value})});const result=await response.json();if(!response.ok)throw new Error(result.detail||'Financial Friday could not complete this run.');render(result);toast(result.status==='HELD'?'Unsafe action safely held':'Sandbox run complete');}
      catch(error){resetStages();document.querySelector('[data-stage="plan"]').classList.add('blocked');$('empty').querySelector('h3').textContent='Friday could not finish';$('empty').querySelector('p').textContent=String(error);toast('Run failed safely—no action assumed');}
      finally{clearTimeout(stageTimer);button.disabled=false;button.textContent='Ask Friday to handle it';}
    }
    async function init(){
      try{const response=await fetch('/api/friday/scenarios');const data=await response.json();if(!response.ok)throw new Error(data.detail||'API unavailable');catalogue=data.scenarios;$('ai-status').textContent=data.configured_mode==='LOCAL_RULES'?'Local baseline ready':data.model+' ready';
        data.scenarios.forEach(item=>{const [icon,title]=labels[item.id]||['·',item.name];const button=node('button',undefined,'scenario');button.type='button';button.dataset.id=item.id;button.setAttribute('aria-pressed','false');button.append(node('span',icon,'scenario-icon'));const copy=node('span');copy.append(node('b',title),node('small',item.description));button.append(copy);button.addEventListener('click',()=>selectScenario(item.id));$('scenarios').append(button);});selectScenario(selected);
        if(location.hash.startsWith('#run=')){const response=await fetch('/api/friday/runs/'+encodeURIComponent(decodeURIComponent(location.hash.slice(5))));if(response.ok)render(await response.json());}
      }catch(error){$('ai-status').textContent='API unavailable';$('run').disabled=true;$('scenario-copy').textContent=String(error);}
    }
    let watching=false;
    async function inboxRequest(path='/api/friday/inbox',body){
      const response=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      if(!response.ok)throw new Error('Inbox unavailable. Monitoring status could not be checked.');
      return response.json();
    }
    function showInbox(data){
      watching=data.enabled;$('watch-status').textContent=watching?'Monitoring enabled':'Paused';
      $('watch-toggle').textContent=watching?'Pause monitoring':'Enable bill monitoring';$('watch-toggle').disabled=false;
      $('bill-inbox').replaceChildren();
      data.items.forEach(item=>{const li=node('li');li.append(node('b',nice(item.case_id.replaceAll('-','_'))+' · '+nice(item.state)),node('small',item.result.message||'Waiting for the background worker.'));
        li.append(node('p','Sample due date: '+new Date(item.due_at).toLocaleDateString()+(item.reminder_due?' · Reminder: due within two days':'')));
        if(item.result.mode)li.append(node('small','Checked using '+item.result.mode+' · '+item.result.model));
        if(item.state==='UNAVAILABLE'){const retry=node('button','Retry check','planner');retry.type='button';retry.addEventListener('click',async()=>{retry.disabled=true;try{showInbox(await inboxRequest('/api/friday/inbox/'+encodeURIComponent(item.event_id)+'/retry',{}));}catch(e){$('inbox-error').textContent=e.message;retry.disabled=false;}});li.append(retry);}
        $('bill-inbox').append(li);
      });
      if(!data.items.length)$('bill-inbox').append(node('li','No bills received yet. Use “Deliver selected sample bill” to simulate a provider event.'));
      $('inbox-error').textContent='';
    }
    async function refreshInbox(){try{showInbox(await inboxRequest());}catch(e){$('inbox-error').textContent=e.message;$('watch-status').textContent='Status unavailable';}}
    $('watch-toggle').addEventListener('click',async()=>{try{showInbox(await inboxRequest('/api/friday/watch',{enabled:!watching}));}catch(e){$('inbox-error').textContent=e.message;}});
    $('deliver-bill').addEventListener('click',async()=>{try{showInbox(await inboxRequest('/api/friday/arrivals/'+encodeURIComponent(selected),{}));}catch(e){$('inbox-error').textContent=e.message;}});
    setInterval(refreshInbox,5000);refreshInbox();
    $('run').addEventListener('click',run);init();
  </script>
</body>
</html>"""
