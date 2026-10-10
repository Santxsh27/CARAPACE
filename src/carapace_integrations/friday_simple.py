"""Progressive disclosure for the existing Friday routes, not another app.

Auth, consent and approvals stay with their original handlers. Bill planning
adds one read-only request; essential scope labels never disappear.
"""

SIMPLE_CSS = r"""
<style id="friday-simple-styles">
  .shell.layout{max-width:1000px;padding:24px 24px 48px}
  .friday-nav{justify-content:flex-start;max-width:1000px;margin:auto;border-bottom:0;padding:12px 24px;gap:8px}
  .friday-nav button{font-size:14px;min-height:44px}
  .simple-more{margin-left:auto;position:relative}.simple-more>summary{cursor:pointer;padding:12px 16px;min-height:44px;box-sizing:border-box;color:#c3d4e3;border:1px solid #355363;border-radius:12px;list-style:none}
  .simple-more[open]>div{position:absolute;right:0;top:52px;z-index:20;width:210px;display:grid;padding:10px;background:#121e2a;border:1px solid #355363;border-radius:16px;box-shadow:0 12px 32px #0008}
  .simple-more button{text-align:left}.simple-more button.motion-toggle{margin:4px 0}
  .simple-home .hero{min-height:0!important;padding:32px!important;border-radius:24px!important;display:grid!important;grid-template-columns:1fr!important;text-align:left!important}
  .simple-home .hero-main{max-width:none!important}.simple-home .hero h2{font-size:clamp(30px,4vw,44px)!important;margin:0 0 12px!important;text-align:left!important}
  .simple-home .hero p{margin:0!important;font-size:15px!important;line-height:1.6!important;max-width:none!important}
  .simple-home .hero .core-console,.simple-home .hero .system-line,.simple-home .hero .eyebrow,.simple-home .command-hints{display:none!important}
  .simple-home .home-command{margin:24px 0 10px!important;max-width:none;padding:8px!important}.simple-home .home-command input{min-height:42px;font-size:15px}
  .simple-home .hero .permission-note{font-size:12px!important;color:#b6c6ce!important;margin:10px 0 0!important}
  .simple-home .task-grid{grid-template-columns:repeat(3,minmax(0,1fr));margin:20px 0}
  .simple-home .task-tile{min-height:125px;padding:24px;transform:none!important;transition:background .2s,border-color .2s}
  .simple-home .task-tile .tile-label{display:none}.simple-home .task-tile b{font-size:18px}.simple-home .task-tile small{font-size:13px;line-height:1.6}
  .simple-fold{border:1px solid #355363;border-radius:16px;background:#101c28;margin:16px 0;padding:0 18px}
  .simple-fold>summary{cursor:pointer;font-size:14px;min-height:48px;display:flex;align-items:center;gap:10px;color:#dce8ed;font-weight:600;list-style:none}
  .simple-fold>summary:after{content:'+';margin-left:auto}.simple-fold[open]>summary:after{content:'−'}
  .simple-fold>div{padding-bottom:18px}.simple-fold>div>p{font-size:13px;line-height:1.7;color:#bdcbd4}
  .simple-home .cockpit-tools{margin:0 0 16px}.simple-home .cockpit-tools>span{font-size:12px;letter-spacing:0;text-transform:none}
  .simple-home .screen-note{margin:16px 0;font-size:12px}.simple-fold .household-inbox,.simple-fold .cockpit-brief{margin:0;border:0;background:none;padding:16px 0;box-shadow:none}
  .simple-home h2[tabindex="-1"]:focus{outline:none}
  .screen-heading{max-width:820px;margin:0 auto 20px}.screen-heading h1{font-size:32px}.screen-heading>.eyebrow{display:none}.screen-heading p{font-size:14px;margin:10px 0}.screen-back{font-size:13px}
  .simple-money-picker{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin:20px 0}
  .simple-money-picker button{border:1px solid #355363;background:#132332;color:#ecf5f8;border-radius:18px;text-align:left;min-height:120px;padding:24px;cursor:pointer;transition:border-color .18s,background .18s}
  .simple-money-picker button:hover{background:#192f40;border-color:#79b7c9}.simple-money-picker b,.simple-money-picker small{display:block}.simple-money-picker b{font-size:20px;margin-bottom:8px}.simple-money-picker small{color:#b8cbd5;font-size:13px}
  .simple-panel[hidden],.simple-money-picker[hidden],.simple-panel-back[hidden]{display:none!important}
  .simple-statement-form[hidden]{display:none!important}.simple-statement-form>.planner{display:block}
  .simple-panel-back{margin-bottom:12px}.money-section{margin:16px 0;padding:24px}.money-section h2{font-size:19px}.money-section>p{font-size:14px}
  .simple-panel input[type=file]{display:block;width:100%;margin:12px 0 16px;padding:16px;border:1px dashed #547282;border-radius:12px;box-sizing:border-box}
  .simple-panel input[type=checkbox]{margin:10px 8px 18px 0;vertical-align:middle;width:18px;height:18px}.simple-panel label{line-height:1.6}
  .simple-panel .planner{margin:8px 8px 8px 0}.simple-panel .screen-note{font-size:12px}.simple-evidence{max-width:820px;margin:18px auto}.simple-evidence .assurance-board,.simple-evidence #result{margin:16px 0}
  .simple-approval{max-width:820px;margin:14px auto}.simple-approval button{width:100%}.outcome-summary{max-width:820px;margin:16px auto!important;padding:26px!important}.outcome-summary h2{font-size:25px!important}.outcome-summary p{font-size:15px!important}
  .friday-view .task-form{max-width:760px;margin:auto}.friday-view .command-copy>p{font-size:14px}.friday-view .command-input{min-height:150px}
  .simple-scope{font-size:12px;color:#b4c7d1;margin:16px 0}.simple-fold .money-capabilities{display:none}
  @media(max-width:640px){.shell.layout{padding:20px 16px 40px}.friday-nav{padding:10px 16px;gap:4px}.friday-nav button{padding:10px 12px}.simple-home .hero{padding:24px!important}.simple-home .home-command{flex-direction:column}.simple-home .task-grid,.simple-money-picker{grid-template-columns:1fr}.simple-home .task-tile{min-height:100px}.screen-heading h1{font-size:28px}.money-section{padding:20px}.simple-more[open]>div{width:190px}}
  /* Task hierarchy: reuse the existing palette, remove ornamental motion. */
  .simple-home .hero{background:#121a22!important;border-color:#3b4b55!important;padding:42px!important}
  .simple-home .hero h2{max-width:650px;font-size:clamp(34px,4.8vw,58px)!important;line-height:1.08;letter-spacing:-.045em}
  .simple-home .hero p{max-width:570px!important;color:#c2d0db!important}
  .friday-primary-plan{display:flex;align-items:center;gap:18px;margin:28px 0 4px;flex-wrap:wrap}
  .friday-primary-plan button{padding:15px 22px;min-height:52px;border-radius:14px;font-size:16px;font-weight:650;cursor:pointer}
  .friday-primary-plan small{color:#a9c4ba;font-size:13px}
  .simple-home .home-command{border:0!important;border-top:1px solid #34404c!important;border-radius:0!important;background:none!important;padding:22px 0 0!important;margin-top:26px!important}
  .simple-home .home-command input{border:1px solid #465967!important;border-radius:12px;background:#0b1219;padding:12px!important;min-width:0}
  .simple-home .task-tile{min-height:115px;border-radius:16px;background:#121a22!important}
  .simple-home .task-tile:hover,.simple-money-picker button:hover{background:#1b2a32!important;border-color:#8cbcaf}
  .activity-entry{background:#141e28!important;border-radius:14px;box-shadow:none!important;padding:18px 22px}
  .activity-entry b{text-transform:capitalize;font-size:16px}.activity-entry small{font-size:12px;margin-top:8px}
  .activity-entry .status{font-size:12px;line-height:1.4;max-width:210px;text-align:right}
  .plan-row-action{display:flex;align-items:center;gap:14px;flex-wrap:wrap}.plan-row-action button{min-height:44px;border:1px solid #6a9d8d;border-radius:10px;background:#18342c;color:#dbf5e9;padding:10px 14px;cursor:pointer}
  .plan-row-action button:hover{background:#234c3e}.plan-next-note{color:#b7c8d3;font-size:12px;line-height:1.6}
  button:focus-visible,summary:focus-visible,input:focus-visible{outline:2px solid #b5ecdc!important;outline-offset:4px}
  @media(max-width:640px){.simple-home .hero{padding:26px!important}.friday-primary-plan{gap:10px}.friday-primary-plan button{width:100%}.activity-entry .status{text-align:left;max-width:none}.plan-row-action{width:100%;justify-content:space-between}}
  /* Colour communicates the task; outcome colours always follow server evidence. */
  body{background:#0b1020!important;background-image:radial-gradient(ellipse at 90% 0%,#26275166,transparent 55%)!important}
  .topbar{background:#0b1020!important}.friday-nav{background:#11182a!important;border-radius:18px}
  .friday-nav button[aria-current="page"]{background:#293059!important;border-color:#929ced!important;color:#eef0ff!important}
  .simple-home .hero{background:linear-gradient(125deg,#20294b,#151d31 72%)!important;border-color:#535d8a!important}
  .simple-home .hero h2{color:#f2f4ff!important}.simple-home .hero p{color:#d1daee!important}
  .friday-primary-plan .run,.simple-home .home-command .run{background:#c4baff!important;color:#20183e!important;border-color:#c4baff!important;box-shadow:none!important}
  .friday-primary-plan .run:hover,.simple-home .home-command .run:hover{background:#ded7ff!important}
  .simple-home .home-command input{background:#0f172a!important;border-color:#68749a!important}
  .simple-home .task-tile[data-screen-link="bill"]{background:#163a37!important;border-color:#427f76!important}
  .simple-home .task-tile[data-screen-link="document"]{background:#302649!important;border-color:#796599!important}
  .simple-home .task-tile[data-screen-link="money"]{background:#332e23!important;border-color:#88734e!important}
  .simple-home .task-tile small{color:#d0d8e3!important}.simple-home .task-tile:hover{filter:brightness(1.15)}
  .simple-home .task-tile,.simple-money-picker button,.plan-row-action button{transition:filter .18s,background .18s,border-color .18s,box-shadow .18s}
  .simple-money-picker button{background:#192640;border-color:#546b99}.simple-fold{background:#121c30;border-color:#425476}
  .money-section,.friday-view .card{border-color:#43567b!important;background:#141f34!important}
  .plan-row-action button{background:#164b40;color:#d5fff0;border-color:#5eac97}
  .friday-work{max-width:820px;margin:18px auto;padding:24px;background:#16213a;border:1px solid #536899;border-radius:20px}
  .friday-work h2{font-size:19px;margin:0 0 10px}.friday-work>p{color:#d4dded;font-size:14px;line-height:1.65;margin:0}
  .friday-work dl{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:20px 0 0}
  .friday-work dl>div{padding:16px;border-radius:12px;background:#202f4d;border:1px solid #536587}
  .friday-work dt{font-size:12px;color:#c9d7ee}.friday-work dd{font-size:21px;font-weight:650;margin:8px 0 0;color:#e8e2ff}
  .friday-work.corrected{background:#202743;border-color:#9b8ccc}
  [data-state="complete"] .outcome-summary{background:#143b32!important;border-color:#64af94!important}
  [data-state="held"] .outcome-summary{background:#401f2e!important;border-color:#d88599!important}
  [data-state="attention"] .outcome-summary{background:#3a3020!important;border-color:#c9a66a!important}
  .activity-entry .status.good{color:#a9f0cb}.activity-entry .status.bad{color:#ffb5c7}.activity-entry .status.warn{color:#f6d29a}
  @media(max-width:640px){.friday-work{padding:20px}.friday-work dl{grid-template-columns:1fr}.friday-work dl>div{display:flex;align-items:center;justify-content:space-between}.friday-work dd{margin:0;font-size:18px}}
  @media(prefers-reduced-motion:reduce){.simple-home .task-tile,.simple-money-picker button,.plan-row-action button{transition:none}}
</style>
"""

# Injected inside the existing experience closure so no control is reimplemented.
SIMPLE_JS = r"""
      // A smaller interface over the same financial safety boundary.
      function disclosure(label, nodes){const fold=element('details',null,'simple-fold');fold.append(element('summary',label));const body=element('div');nodes.filter(Boolean).forEach(n=>body.append(n));fold.append(body);return fold;}
      function shortHeading(screen,title,copy){const heading=screen.querySelector('.screen-heading');heading.querySelector('h1').textContent=title;heading.querySelector('p').textContent=copy;}
      const nav=document.querySelector('.friday-nav');const more=element('details',null,'simple-more');more.append(element('summary','More'));const moreItems=element('div');['bill','document','demos','settings'].forEach(id=>moreItems.append(nav.querySelector('[data-screen-link="'+id+'"]')));moreItems.append($('motion-toggle'));more.append(moreItems);nav.append(more);nav.querySelector('[data-screen-link="home"]').textContent='Home';
      more.addEventListener('click',e=>{if(e.target.closest('[data-screen-link]'))more.open=false;});document.addEventListener('keydown',e=>{if(e.key==='Escape')more.open=false;});
      home.classList.add('simple-home');$('workspace-title').textContent='Less bill admin. More breathing room.';$('scenario-copy').textContent='Friday plans around your reserve, checks each request and follows the payment outcome.';$('home-command').placeholder='Have a bill message? Paste it here…';permissionNote.textContent='Sandbox only. Checking a request can trigger an artificial payment within your saved rules.';cockpitTools.querySelector('span').textContent='Hi. I’m Friday. Your financial co-pilot.';
      tiles.replaceChildren();[['bill','Check a bill','Message or payment request'],['document','Read a document','Bill photo or PDF'],['money','Understand my money','Statement or saved inputs']].forEach(([route,title,copy])=>{const b=element('button',null,'task-tile');b.type='button';b.dataset.screenLink=route;b.append(element('b',title),element('small',copy));tiles.append(b);});
      home.append(disclosure('Demo bills & recent activity',[billInbox,cockpitBrief]));
      shortHeading(bill,'Check a bill','Paste the request. Friday checks the details before any action.');live.querySelector('h3').textContent='What’s the request?';live.querySelector('.command-copy p').textContent='No PIN, OTP or password needed.';$('live-input').placeholder='Paste the bill message here';$('check-live').textContent='Check bill';
      const examples=live.querySelector('.customer-examples');const providerSetup=live.querySelector('.provider-setup');live.append(disclosure('Try a demo or set up a test bill',[examples,providerSetup]));
      shortHeading(doc,'Read a document','Choose a bill photo or PDF. Google Gemini reads it; the raw file is not saved.');docCard.querySelector('h2').textContent='Your bill';$('check-document').textContent='Read document';
      shortHeading(activity,'Activity','Your recorded tasks and receipts. Payments here use artificial funds.');shortHeading(settings,'My rules','Set the limits for automatic artificial payments.');shortHeading(demos,'Safety lab','Controlled payment tests with artificial funds.');shortHeading(runView,'Task result','Artificial-money pilot. No real bank account connected.');
      const assurance=runView.querySelector('.assurance-board');assurance.querySelector('h3').textContent='What Friday did';assurance.querySelector('.assurance-head p').textContent='Actual run evidence. Waiting does not mean verified.';const engineering=disclosure('How Friday checked this',[source,$('result')]);engineering.classList.add('simple-evidence');runView.insertBefore(assurance,actions);runView.insertBefore(engineering,actions);const approvalArea=element('div',null,'simple-approval');runView.insertBefore(approvalArea,engineering);
      function liftApproval(data){approvalArea.replaceChildren();const button=source.querySelector('button');if(button){const review=data.bill_review||{};approvalArea.append(element('p','Artificial payment: '+workspaceMoney(review.amount_minor)+' · Recipient: '+(review.payee_id||'Not verified')+' · '+(review.provider_name||'Provider not supplied')),button);}}
      const simplerSignal=showLiveResult;showLiveResult=function(data){simplerSignal(data);liftApproval(data);engineering.open=false;};
      Object.assign(reasonCopy,{EVIDENCE_PAYEE_MISMATCH:'The recipient does not match the permitted payee.',EVIDENCE_PROVIDER_MISMATCH:'This is not the permitted provider.',EVIDENCE_CURRENCY_MISMATCH:'The currency does not match the permitted task.'});
      const work=element('section',null,'friday-work');work.hidden=true;runView.insertBefore(work,assurance);
      // Read-only projection of recorded events: never infer AI or payment success.
      function workEvidence(data){
        const events=Array.isArray(data.events)?data.events:[];let rejected=0,corrected=false;
        events.forEach(event=>{if(event.type==='AI_PROGRAM_REJECTED'||(event.type==='AI_PROGRAM_PROPOSED'&&event.verification?.passed===false))rejected++;if(event.type==='AI_PROGRAM_PROPOSED'&&event.verification?.passed===true&&rejected>0)corrected=true;});
        const calls=data.provenance?.successful_model_calls;const liveMode=['VERTEX_AI','GEMINI_API'].includes(data.provenance?.mode);
        const modelCalls=liveMode&&Number.isSafeInteger(calls)&&calls>=0?calls:0;
        const live=modelCalls>0;
        const payment=data.outcome?.new_payment_created===true&&data.status==='COMPLETED_SYNTHETIC';
        let title,copy;
        if(corrected&&live){title='Friday corrected its plan before acting.';copy='The safety checker rejected an earlier proposal. The model received that feedback and returned a plan that passed. This is a task-plan correction—not a bank software repair.';}
        else if(live){title='Gemini planned. The safety checker decided.';copy='Friday used the model for restricted planning. Independent code checked permission and financial effects before execution.';}
        else if(data.provenance?.mode==='LOCAL_RULES'){title='Handled by the local rules engine.';copy='No live AI planning was used in this run. The same independent safety and execution checks apply.';}
        else{title='Existing evidence came first.';copy='No successful live planning call is recorded. Friday may stop a contradictory request or reconcile an existing result without asking AI to approve it.';}
        return {title,copy,corrected:corrected&&live,modelCalls,rejected,payment};
      }
      function showWork(data){const evidence=workEvidence(data);work.hidden=false;work.classList.toggle('corrected',evidence.corrected);work.replaceChildren(element('h2',evidence.title),element('p',evidence.copy));const metrics=element('dl');[['Live planning calls',String(evidence.modelCalls)],['Rejected proposals',String(evidence.rejected)],['New sandbox payment',evidence.payment?'1 recorded':'None confirmed']].forEach(([label,value])=>{const item=element('div');item.append(element('dt',label),element('dd',value));metrics.append(item);});work.append(metrics);}
      const simplerRender=render;render=function(data){simplerRender(data);showWork(data);approvalArea.replaceChildren();engineering.open=false;if(data.status==='HELD'){const explanations=(data.outcome?.reason||[]).map(code=>reasonCopy[code]||nice(code)).join(' ');summarize('Payment stopped.',explanations||'The request did not pass the saved safety rules.','No new artificial payment was made. Check the request before trying again.');}else if(completedStatuses.includes(data.status)){const receipt=data.outcome?.receipt?.payload;const text=data.status==='COMPLETED_SYNTHETIC'?'One artificial payment was recorded.':'An earlier result was found. No repeat payment was sent.';summarize(data.status==='COMPLETED_SYNTHETIC'?'Done. Receipt recorded.':'Already handled.',receipt?workspaceMoney(receipt.amount_minor)+' · '+receipt.payee_id+'. '+text:text,'Your receipt is saved in Activity.');}};
      const workSignal=showLiveResult;showLiveResult=function(data){work.hidden=true;workSignal(data);};
      const workShow=show;show=function(name,push=true){if(name==='run')work.hidden=true;workShow(name,push);};
      shortHeading(moneyView,'My money','Choose what you want to review. No bank account is connected.');
      const picker=element('div',null,'simple-money-picker');const panelBack=element('button','Back to My money','planner simple-panel-back');panelBack.type='button';panelBack.hidden=true;
      const wallet=element('div',null,'simple-panel');wallet.append(moneyControls,moneyFeedback,moneyContent);const walletFold=disclosure('Demo wallet · artificial funds',[wallet,followSection]);
      statementSection.classList.add('simple-panel');personalInbox.classList.add('simple-panel');statementSection.hidden=true;personalInbox.hidden=true;statementSection.querySelector('h2').textContent='Review your spending';statementSection.querySelector('p').textContent='Choose an INR statement CSV. No payment will be made.';statementHelp.textContent='INR CSV · 1 MB max. Remove personal identifiers before uploading.';statementSection.insertBefore(disclosure('CSV format & privacy',[element('p','Columns: date, description, debit, credit. Amounts in rupees; one debit or credit per row. Dates: YYYY-MM-DD or DD/MM/YYYY. Maximum 5,000 rows. Raw data is processed temporarily, not saved or sent to Gemini.')]),statementConsent);statementButton.textContent='Review statement';
      personalInbox.querySelector('h2').textContent='Saved inputs';personalInbox.querySelector('p').textContent='What Friday read from your messages and documents. Not verified bank evidence.';inboxRefresh.textContent='Refresh inputs';
      function selectMoneyPanel(id){picker.hidden=Boolean(id);panelBack.hidden=!id;statementSection.hidden=id!=='statement';personalInbox.hidden=id!=='inputs';walletFold.hidden=Boolean(id);if(id==='inputs'&&!inboxRefresh.disabled)inboxRefresh.click();if(id){const h=(id==='statement'?statementSection:personalInbox).querySelector('h2');h.tabIndex=-1;h.focus({preventScroll:true});}}
      [['statement','Review spending','Upload your statement CSV'],['inputs','Saved inputs','Messages and documents Friday read']].forEach(([id,title,copy])=>{const b=element('button');b.type='button';b.append(element('b',title),element('small',copy));b.addEventListener('click',()=>selectMoneyPanel(id));picker.append(b);});panelBack.addEventListener('click',()=>selectMoneyPanel(null));moneyWorkspace.replaceChildren(picker,panelBack,statementSection,personalInbox,walletFold);
      function foldWalletEvidence(){const nodes=Array.from(moneyContent.children);nodes.forEach(node=>{if(node.classList.contains('money-capabilities')){node.remove();return;}const h=node.querySelector('h2');if(h&&['What is connected now','Know the boundaries','Recent recorded outcomes','Bill records'].includes(h.textContent)){const fold=disclosure(h.textContent,[]);moneyContent.replaceChild(fold,node);fold.querySelector('div').append(node);}});}
      const originalMoneyRefresh=refreshMoney;moneyRefresh.removeEventListener('click',originalMoneyRefresh);refreshMoney=async function(){await originalMoneyRefresh();foldWalletEvidence();};moneyRefresh.addEventListener('click',refreshMoney);
      const originalShow=show;show=function(name,push=true){if(name==='money')selectMoneyPanel(null);originalShow(name,push);};
      const simpleSelect=selectScenario;selectScenario=function(id){simpleSelect(id);$('scenario-copy').textContent='Friday plans around your reserve, checks each request and follows the payment outcome.';};
      const statementForm=element('div',null,'simple-statement-form');statementSection.insertBefore(statementForm,statementStatus);statementForm.append(statementLabel,statementFile,statementHelp,statementSection.querySelector('.simple-fold'),statementConsent,consentLabel,statementButton);clearStatement.textContent='Clear results & start again';
      // Only presentation of already returned results; never an execution trigger.
      function compactStatementResults(){statementForm.hidden=statementResults.children.length>0;statementSection.querySelector('p').textContent=statementForm.hidden?'Read-only results. Net flow is not your account balance.':'Choose an INR statement CSV. No payment will be made.';const notes=[];Array.from(statementResults.children).forEach(child=>{if(child.classList.contains('simple-fold'))return;if(child.classList.contains('screen-note')){notes.push(child);return;}const heading=child.querySelector('h2');if(heading&&['Month-by-month cash flow','Largest outgoing entries'].includes(heading.textContent)){const fold=disclosure(heading.textContent,[]);statementResults.replaceChild(fold,child);fold.querySelector('div').append(child);}});if(notes.length)statementResults.append(disclosure('Processing & limitations',notes));}
      new MutationObserver(compactStatementResults).observe(statementResults,{childList:true});
      // Personalised read-only planning over current tenant records. Never pays.
      const planSection=workspaceSection('Your bill plan');planSection.classList.add('simple-panel');planSection.hidden=true;const planStatus=element('p');planStatus.setAttribute('role','status');const planRows=element('div');const planRefresh=element('button','Refresh bill plan','planner');planRefresh.type='button';planSection.append(element('p','Preserve your reserve and prioritise earlier bills. Artificial records only; no payment is made.'),planRefresh,planStatus,planRows);moneyWorkspace.insertBefore(planSection,walletFold);
      const planChoice=element('button');planChoice.type='button';planChoice.append(element('b','Plan my bills'),element('small','A reserve-aware plan, not just totals'));picker.prepend(planChoice);
      const originalPanelSelect=selectMoneyPanel;selectMoneyPanel=function(id){originalPanelSelect(id==='plan'?'plan':id);planSection.hidden=id!=='plan';if(id==='plan'){planSection.querySelector('h2').tabIndex=-1;planSection.querySelector('h2').focus({preventScroll:true});}};
      function preparePlannedBill(row){
        if(!Number.isSafeInteger(row.amount_minor)||row.amount_minor<=0||['provider_name','bill_reference','payee_id'].some(k=>typeof row[k]!=='string'||!row[k].trim()||row[k].length>200)){toast('This record needs verification. No request was prepared.');return;}
        const amount=String(Math.floor(row.amount_minor/100))+'.'+String(row.amount_minor%100).padStart(2,'0');
        $('live-input').value=`Please check this one-time ${row.provider_name} bill ${row.bill_reference} for INR ${amount}. Payee: ${row.payee_id}.`;
        show('bill');$('live-input').focus();
      }
      async function loadBillPlan(){if(planRefresh.disabled)return;planRefresh.disabled=true;planRows.replaceChildren();planStatus.textContent='Checking current bills and your reserve…';try{const data=await jsonRequest('/api/friday/bill-plan');if(data.scope!=='ARTIFICIAL_MONEY'||data.read_only!==true||data.money_moved!==false||data.payment_authorized!==false)throw new Error('Unexpected planning boundary');if(data.state!=='PLANNED'){planStatus.textContent='No complete plan available: '+nice(data.state)+'. Nothing was paid.';return;}planStatus.textContent=data.selected.length+' bills fit · '+workspaceMoney(data.planned_total_minor)+' planned · '+workspaceMoney(data.remaining_above_reserve_minor)+' remains above your reserve.';[['selected','Fits your plan'],['deferred','Does not fit your reserve'],['review','Needs verification'],['already_recorded','Already recorded internally']].forEach(([key,title])=>{if(!data[key].length)return;const section=workspaceSection(title);data[key].forEach(row=>{const detail=element('div',null,'money-row');const text=element('div');text.append(element('b',row.provider_name||row.provider_id),element('small',row.bill_reference+' · Due '+row.due_date));if(row.reason)text.append(element('small',nice(row.reason)));const action=element('div',null,'plan-row-action');action.append(element('b',workspaceMoney(row.amount_minor)));if(key==='selected'){const next=element('button','Prepare bill check');next.type='button';next.addEventListener('click',()=>preparePlannedBill(row));action.append(next);}detail.append(text,action);section.append(detail);});planRows.append(section);});planRows.append(element('p','Prepare bill check fills the request only. It does not submit it. Friday rechecks current provider records and saved permission when you choose Check bill.','plan-next-note'));planRows.append(disclosure('How the plan was calculated',[element('p',data.objective),element('p','Exact Pareto-frontier optimisation · '+data.frontier_states_explored+' states explored. Gemini interprets incoming bills; exact code calculates this plan.'),...data.limits.map(line=>element('p',line))]));}catch(error){planStatus.textContent='Plan unavailable. Nothing was paid; no affordability assumption is made.';}finally{planRefresh.disabled=false;}}
      planChoice.addEventListener('click',()=>{selectMoneyPanel('plan');loadBillPlan();});planRefresh.addEventListener('click',loadBillPlan);
      const primaryPlan=element('div',null,'friday-primary-plan');const primaryPlanButton=element('button','Plan my bills','run');primaryPlanButton.type='button';primaryPlan.append(primaryPlanButton,element('small','Read-only. Your reserve stays protected.'));hero.querySelector('.hero-main').insertBefore(primaryPlan,command);
      primaryPlanButton.addEventListener('click',()=>{show('money');selectMoneyPanel('plan');loadBillPlan();});
"""
