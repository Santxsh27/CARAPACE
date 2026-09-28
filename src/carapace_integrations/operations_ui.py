"""Simple development UI for observable, autonomous financial case resolution."""

OPERATIONS_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CARAPACE · Financial operations guardian</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f5f7fa;color:#17243a;font:16px/1.6 system-ui,sans-serif}
header{background:white;border-bottom:1px solid #dde4ec}header>div,main{max-width:1100px;margin:auto;padding:20px 24px}
header>div{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}nav{display:flex;gap:20px}a{color:#1c54ae}
main{padding-top:40px;padding-bottom:80px}h1{font-size:clamp(32px,5vw,52px);line-height:1.12;letter-spacing:-.035em;max-width:860px;margin:12px 0 22px}h2{font-size:22px;margin-top:0}
.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:.12em;font-weight:750;color:#1c54ae}.lead{max-width:850px;color:#4b5d72;font-size:18px}
.notice{padding:16px 20px;border:1px solid #cad8eb;background:#edf3fc;border-radius:12px;margin:24px 0}.controls{display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin:24px 0}
select,button{font:inherit;border:1px solid #b9c8d9;border-radius:8px;padding:9px 13px;background:white;color:#17243a}button{background:#1856b2;color:white;border-color:#1856b2;cursor:pointer}button:disabled{opacity:.55;cursor:wait}button:focus-visible,a:focus-visible,select:focus-visible{outline:3px solid #fdad27;outline-offset:3px}
.cases{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.card,.result{background:white;border:1px solid #dce4ee;border-radius:12px;padding:22px}.card{display:flex;flex-direction:column;gap:10px}.card p{color:#53657b;font-size:14px;margin:0 0 12px;flex:1}.card h2{font-size:18px;margin:0}.card button{align-self:flex-start}
.result{margin-top:28px;scroll-margin-top:24px}.metrics{display:flex;gap:24px;flex-wrap:wrap;padding:16px 0}.metrics div{min-width:140px}.metrics b{display:block;font-size:24px}.muted{color:#53657b;font-size:14px}.timeline{padding-left:24px}.timeline li{padding:8px 0}.timeline p{margin:4px 0;color:#53657b}.status{font-weight:800;color:#1c54ae}.next-step{border-left:3px solid #1856b2;background:#f1f6ff;padding:14px 18px;margin:20px 0}.next-step p{margin:5px 0}.outcomes{padding-left:22px}.outcomes li{padding:6px 0}.scope{font-size:13px;color:#53657b}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f7fa;padding:16px;font:13px/1.6 ui-monospace,monospace}summary{cursor:pointer;color:#1c54ae;padding:12px 0}details{border-top:1px solid #e5eaf1} [hidden]{display:none!important}
@media(max-width:800px){.cases{grid-template-columns:1fr 1fr}}@media(max-width:520px){.cases{grid-template-columns:1fr}header>div,main{padding-left:16px;padding-right:16px}}
</style></head><body>
<header><div><strong>CARAPACE</strong><nav><a href="#cases">Operations</a><a href="/payment-check">Payment check</a><a href="http://localhost:8080/docs" target="_blank" rel="noopener">API docs ↗</a></nav></div></header>
<main><div class="eyebrow">Financial resolution agent · development workspace</div>
<h1>Let CARAPACE resolve<br>the payment paperwork.</h1>
<p class="lead">Choose an invoice. CARAPACE checks what was delivered, applies approved credits, prepares a resolution and completes the permitted test payment. You see the outcome and anything still needed.</p>
<div class="notice"><strong>Try it with artificial money.</strong> These six examples use sample business records. Gemini can create the action plan; a separate verifier checks it before anything is recorded. No real account is connected.</div>
<details><summary>What can it do today?</summary><p class="muted">Read five kinds of sample records, generate and verify a financial action plan, record delivery deferrals and credits, and post to the local test ledger under a pre-agreed spending policy. Real document uploads, business connectors and bank transfers are still being built. The earlier Anthos experiment is under Payment check.</p></details>
<div class="controls"><label for="planner">Run with</label><select id="planner"><option value="configured">Google AI · configured provider</option><option value="local">Local demo · no AI call</option></select><span id="provider" class="muted">Checking provider…</span></div>
<section id="cases" class="cases" aria-label="Financial resolution cases"></section>
<section id="result" class="result" aria-live="polite"><span class="eyebrow">Your result</span><h2 id="headline" tabindex="-1">Start with “Partial delivery + credit”</h2><p id="progress">See how CARAPACE turns a ₹4.8 lakh invoice into a supported ₹3.6 lakh test payment, applies a credit and keeps undelivered goods out of the payment.</p>
<div id="metrics" class="metrics" hidden></div><ul id="outcomes" class="outcomes" hidden></ul>
<div id="next-step" class="next-step" hidden><strong id="next-title"></strong><p id="next-copy"></p></div>
<details id="investigation-detail" hidden><summary>How CARAPACE reached this result</summary><p id="mode" class="muted"></p><p id="constraint" class="status"></p><ol id="timeline" class="timeline"></ol></details>
<details id="graph-detail" hidden><summary>Inspect retrieved records and their relationships</summary><pre id="graph"></pre></details>
<details id="evidence-detail" hidden><summary>Inspect the complete saved run and signed result</summary><pre id="raw"></pre></details>
</section><p class="muted">A blocked case stays stopped. An unavailable model does not silently become a successful AI run. Re-running a paid invoice reuses its existing verified test posting.</p></main>
<script>
const names={supplier_registry:'Supplier identity and beneficiary',purchase_order:'Agreed order and payment terms',delivery_receipts:'Warehouse delivery evidence',credit_notes:'Approved credit notes',payment_history:'Previous payment allocations'};
const labels={POSTED_SYNTHETIC:'Resolution completed in the test ledger',ALREADY_POSTED:'Resolution confirmed in the test ledger',HELD:'Payment stopped',UNRESOLVED:'Resolution needs another attempt',NO_PAYMENT_DUE:'Nothing more to pay'};
const money=n=>n==null?'—':new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:2}).format(n/100);
function node(tag,text){const e=document.createElement(tag);e.textContent=text;return e;}
function outcomeCopy(r){
 const executed=r.resolution?.executed;
 const rows=[];
 if(executed){for(const effect of r.resolution.receipt.payload.effects){const text={DEFER_UNDELIVERED:'Deferred until goods are received: ',APPLY_APPROVED_CREDIT:'Approved credit recorded: ',RECOGNISE_PRIOR_PAYMENT:'Previous payment recognised: ',POST_PAYMENT:'Payment matched in the test ledger: '}[effect.action];rows.push(text+money(effect.amount_minor));}}
 else if(r.status==='ALREADY_POSTED')rows.push('The existing payment still matches. No new payment was made.');
 else if(r.status==='POSTED_SYNTHETIC')rows.push('A test payment was recorded by the earlier workflow. This saved run predates action-plan verification.');
 else rows.push('No new payment was made in this run.');
 const codes=r.assessment.conflicts.map(c=>c.code);
 let title='No action needed for this completed test',copy='CARAPACE recorded the permitted outcome and checked the stored result.';
 if(executed && r.resolution.verification.deferred_minor>0){title='Received goods are resolved; undelivered goods remain open';copy=money(r.resolution.verification.deferred_minor)+' is deferred, not forgiven. A later delivery record is needed before that amount can be reconsidered.';}
 else if(r.status==='HELD'){title='What must be resolved before payment';copy=codes.includes('BENEFICIARY_CHANGE_UNVERIFIED')?'The requested bank account differs from the enrolled supplier account. Your finance team needs independent supplier verification; CARAPACE did not replace the account.':codes.includes('SOURCE_UNAVAILABLE')?'The warehouse delivery record is unavailable. Payment stays stopped until a valid record is supplied.':codes.includes('CONFLICTING_DELIVERY_EVIDENCE')?'The delivery records disagree. A corrected authoritative record is needed before payment.':'The evidence or spending policy does not support this payment. Open the explanation below for the exact reason.';}
 else if(r.status==='UNRESOLVED'){title='A verified resolution could not be completed';copy='Retry the case, or choose Local demo to test without a model call. CARAPACE will reconcile an existing posting before creating another.';}
 else if(r.status==='NO_PAYMENT_DUE'){title='No payment needed';copy='The supported obligation is already covered by credits or prior payments.';}
 return {rows,title,copy};
}
function render(r){
 if(['INVESTIGATING','READY'].includes(r.status)){document.getElementById('headline').textContent='Saved resolution has not finished';document.getElementById('progress').textContent='This run has no completed result. Re-run its case to reconcile safely; an interrupted run is not automatically resumed yet.';return;}
 document.getElementById('headline').textContent=labels[r.status]||r.status;
 document.getElementById('progress').textContent=r.resolution?.executed?(r.resolution.reused_posting?'The plan passed independent checks. CARAPACE matched the existing payment and verified each recorded adjustment. No new payment was made.':'The action plan passed independent checks. Its effects are recorded and checked in the local test ledger.'):r.status==='ALREADY_POSTED'?'CARAPACE checked the previous payment instead of paying again.':r.status==='POSTED_SYNTHETIC'?'This saved run recorded a test payment before action-plan generation was added.':'CARAPACE kept the payment stopped where the evidence or a verified plan was incomplete.';
 document.getElementById('mode').textContent='Provider: '+r.provenance.mode+' · '+r.provenance.model+' · Successful model calls: '+r.provenance.successful_model_calls+' · Resolution-generation calls: '+(r.provenance.successful_resolution_calls||0)+' · Saved run: '+r.run_id;
 const metrics=document.getElementById('metrics');metrics.replaceChildren();metrics.hidden=false;
 [['Invoice requested',money(r.assessment.requested_minor)],['Supported payment',money(r.assessment.payable_minor)]].forEach(([k,v])=>{const box=node('div','');box.append(node('span',k),node('b',v));metrics.append(box);});
 const copy=outcomeCopy(r),outcomes=document.getElementById('outcomes');outcomes.replaceChildren(...copy.rows.map(text=>node('li',text)));outcomes.hidden=false;
 document.getElementById('next-title').textContent=copy.title;document.getElementById('next-copy').textContent=copy.copy;document.getElementById('next-step').hidden=false;
 document.getElementById('constraint').textContent=r.assessment.conflicts.map(c=>c.code.replaceAll('_',' ')+' ['+c.sources.join(' + ')+']').join(' · ');
 const timeline=document.getElementById('timeline');timeline.replaceChildren();
 r.events.forEach(ev=>{const li=node('li','');if(ev.type==='PLAN'){li.append(node('strong','Evidence plan'),node('p',ev.rationale));}else if(ev.type==='EVIDENCE_RETRIEVED'){li.append(node('strong','Checked: '+names[ev.source]),node('p','Sample record retrieved; exact values are available below.'));}else if(ev.type==='RESOLUTION_PROPOSED'){li.append(node('strong','Action plan generated'),node('p',ev.program.explanation),node('p',ev.verification.passed?'Independent checks passed.':'Rejected: '+ev.verification.errors.join(', ')));}else if(ev.type==='RESOLUTION_VERIFIED'){li.append(node('strong','Action plan tested'),node('p',ev.checks+' bounded checks rejected changed or incomplete instructions.'));}else if(ev.type==='EXECUTED_AND_READ_BACK'){li.append(node('strong','Payment recorded and checked: '+money(ev.amount_minor)));}else if(ev.type==='RESOLUTION_ACTIONS_RECONCILED'){li.append(node('strong','All resolution effects recorded and checked'));}else{li.append(node('strong',ev.type.replaceAll('_',' ')),node('p',ev.outcome||ev.error_type||''));}timeline.append(li);});
 document.getElementById('graph').textContent=JSON.stringify(r.graph,null,2);document.getElementById('raw').textContent=JSON.stringify(r,null,2);
 document.getElementById('graph-detail').hidden=false;document.getElementById('evidence-detail').hidden=false;
 document.getElementById('investigation-detail').hidden=false;
 history.replaceState(null,'','#run='+encodeURIComponent(r.run_id));
}
async function run(id){
 document.querySelectorAll('button,select').forEach(b=>b.disabled=true);
 document.getElementById('headline').textContent='CARAPACE is working on this case…';document.getElementById('progress').textContent='Checking business records, preparing a resolution and verifying its actions. This can take a little time; you do not need to confirm each step.';
 document.getElementById('result').scrollIntoView({behavior:'auto',block:'start'});document.getElementById('headline').focus({preventScroll:true});
 for(const id of ['outcomes','next-step','investigation-detail'])document.getElementById(id).hidden=true;
 document.getElementById('timeline').replaceChildren();document.getElementById('metrics').hidden=true;document.getElementById('constraint').textContent='';document.getElementById('mode').textContent='';document.getElementById('graph-detail').hidden=true;document.getElementById('evidence-detail').hidden=true;
 try{const res=await fetch('/api/operations/cases/'+id+'/resolve',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({planner:document.getElementById('planner').value})});const r=await res.json();if(!res.ok)throw new Error(r.detail||'Request failed');render(r);}catch(e){document.getElementById('headline').textContent='Result unavailable';document.getElementById('progress').textContent=String(e)+' A lost response does not prove whether an action ran. Re-run this case to reconcile its existing test posting.';}finally{document.querySelectorAll('button,select').forEach(b=>b.disabled=false);}
}
async function init(){try{const res=await fetch('/api/operations/cases');const data=await res.json();if(!res.ok)throw new Error(data.detail||'API unavailable');document.getElementById('provider').textContent=data.configured_mode+' · '+data.model;
 const order=['partial-credit','routine','redirected','missing','conflicting','injected'];data.cases.sort((a,b)=>order.indexOf(a.id)-order.indexOf(b.id));
 for(const c of data.cases){const card=node('article','');card.className='card';const button=node('button',c.id==='partial-credit'?'Resolve this invoice':c.id==='routine'?'Process this invoice':'Run this protection case');button.type='button';button.setAttribute('aria-label',button.textContent+': '+c.name);button.addEventListener('click',()=>run(c.id));card.append(node('h2',c.name),node('p',c.description),button);document.getElementById('cases').append(card);}
 if(location.hash.startsWith('#run=')){const saved=await fetch('/api/operations/runs/'+encodeURIComponent(decodeURIComponent(location.hash.slice(5))));if(saved.ok)render(await saved.json());}
 }catch(e){document.getElementById('provider').textContent='API unavailable: '+e;}}
init();
</script></body></html>"""
