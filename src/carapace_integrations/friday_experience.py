"""Multi-screen presentation over Friday's existing, authenticated API controls.

No financial permission, execution gate, or backend credential lives here.
Hash routes work through both the local server and the private cloud gateway.
"""

EXPERIENCE_CSS = r"""
<style id="friday-experience-styles">
  body{background:#060b13;background-image:radial-gradient(ellipse at 50% 8%,#10283c 0,transparent 55%);color:#eef6ff}
  .topbar{position:relative;background:rgba(6,11,19,.92);border-bottom:1px solid #203242}
  .shell.layout{display:block;max-width:1120px;padding:28px 0 48px}.sidebar{display:none!important}
  .workspace{border:0;background:none;box-shadow:none;overflow:visible}.workspace>.body{display:none!important}
  .friday-nav{display:flex;align-items:center;justify-content:center;gap:6px;padding:16px 12px;border-bottom:1px solid #172635;flex-wrap:wrap}
  .friday-nav button,.screen-back{border:1px solid transparent;background:transparent;color:#a7bbce;min-height:44px;padding:10px 18px;border-radius:24px;font:600 13px inherit;cursor:pointer}
  .friday-nav button:hover,.screen-back:hover{background:#142536;color:white}.friday-nav button[aria-current="page"]{background:#16394c;border-color:#327188;color:#c9f8ff}
  button:focus-visible,a:focus-visible,input:focus-visible,textarea:focus-visible,summary:focus-visible{outline:3px solid #9cecff!important;outline-offset:4px}
  .friday-view[hidden]{display:none!important}.friday-view{animation:screen-arrive .28s ease-out;min-width:0}
  @keyframes screen-arrive{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
  .screen-heading{max-width:760px;margin:4px auto 28px}.screen-heading .eyebrow{color:#8dccdf;letter-spacing:.17em;font-size:11px}
  .screen-heading h1{font-size:clamp(30px,4vw,46px);line-height:1.1;letter-spacing:-.035em;margin:12px 0;color:#f0f8ff}
  .screen-heading p{font-size:15px;line-height:1.65;color:#a0b8cc;max-width:660px}.screen-back{padding-left:0;margin-bottom:8px}
  .friday-view .card,.friday-view .mission-details,.friday-view .assurance-board{border-radius:22px;border:1px solid #294152;background:linear-gradient(145deg,rgba(19,36,53,.94),rgba(8,18,29,.97));box-shadow:0 14px 50px #0003;clip-path:none}
  .friday-view .card{padding:28px}.friday-view .card-head{gap:12px;flex-wrap:wrap}.friday-view .run,.friday-view .planner{border-radius:14px;min-height:48px;padding:13px 22px;font-size:14px;clip-path:none}
  .friday-view .run{background:#9ce8f8;color:#06202d;border-color:#9ce8f8;box-shadow:0 5px 24px #4cceeb20}.friday-view .run:hover{background:#c0f5ff;transform:translateY(-1px)}
  .friday-view .planner{background:#13283a;color:#d6e9fa;border:1px solid #36556b}.friday-view .field,.friday-view textarea{background:#07131f;color:#e6f4ff;border:1px solid #38566c;border-radius:14px;font-size:15px;line-height:1.6;padding:16px}
  .friday-view .label{font-size:12px;color:#c3d4e3;letter-spacing:.03em}.friday-view label{color:#c3d4e3;font-size:13px}
  .friday-view[data-screen="home"] .hero{display:flex;flex-direction:column-reverse;align-items:center;text-align:center;border:0;background:none;padding:0 20px 22px;gap:6px}
  .friday-view[data-screen="home"] .hero:before,.friday-view[data-screen="home"] .hero:after{display:none}
  .friday-view[data-screen="home"] .hero-main{max-width:820px}.friday-view[data-screen="home"] .hero h2{font-size:clamp(35px,5.5vw,62px);line-height:1.08;letter-spacing:-.045em;text-align:center;margin:12px 0}
  .friday-view[data-screen="home"] .hero p{font-size:16px;line-height:1.6;color:#a4bdcf;max-width:660px;margin:18px auto 0}
  .friday-view[data-screen="home"] .core-console{height:200px;transform:scale(.8);margin:-18px 0 -12px}.friday-view[data-screen="home"] .system-line{display:none}
  .home-command{max-width:760px;margin:12px auto 26px;padding:12px;display:flex;gap:12px;border:1px solid #355769;border-radius:22px;background:#0c1b29;box-shadow:0 8px 40px #5ee1ff09}
  .home-command input{flex:1;min-width:0;background:transparent;border:0;color:#ebf7ff;padding:10px 14px;font-size:15px}.home-command input::placeholder{color:#87a4ba}
  .task-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;max-width:1000px;margin:0 auto}
  .task-tile{min-height:165px;text-align:left;border-radius:22px;border:1px solid #294658;background:linear-gradient(145deg,#132b3c,#0b1928);color:#effaff;padding:24px;cursor:pointer;transition:transform .18s,border-color .18s,background .18s;position:relative}
  .task-tile:hover{transform:translateY(-5px);border-color:#83d9ef;background:linear-gradient(145deg,#1a3c50,#102337)}
  .task-tile .tile-label{display:block;font-size:10px;color:#8fc5db;text-transform:uppercase;letter-spacing:.14em;margin-bottom:20px}.task-tile b{display:block;font-size:18px;margin-bottom:9px;letter-spacing:-.015em}.task-tile small{display:block;font-size:12px;color:#afc5d7;line-height:1.6}
  .screen-note{max-width:760px;margin:24px auto;color:#92aabd;font-size:12px;line-height:1.7;text-align:center}
  .task-form{max-width:760px;margin:auto}.live-card{margin:0!important}.command-prompt{display:block}.command-avatar{display:none}.command-input{min-height:150px}.command-copy h3{font-size:23px}.command-copy p{font-size:14px;line-height:1.7;color:#a6bece}
  .provider-setup{margin-top:25px;padding:20px;border-radius:15px;background:#091723;border-color:#31495c}.provider-setup summary{font-size:11px;line-height:1.6}.form-grid{gap:15px}
  .upload-row{display:flex;flex-direction:column;align-items:stretch;gap:18px;border:0;margin:0;padding:10px 0}.upload-row input{padding:30px 18px;border:1px dashed #527e96;border-radius:18px;background:#0a1b29;font-size:14px;width:100%}.upload-note{font-size:12px;color:#a2baca}.upload-row .planner{align-self:flex-start}
  .demo-layout{display:grid;grid-template-columns:1.15fr 1fr;gap:24px}.demo-layout .scenario-list{gap:12px;grid-template-columns:1fr}.demo-layout .scenario{min-height:80px;padding:17px;border-radius:16px;border:1px solid #28475a;background:#0b1d2d}.scenario b{font-size:15px}.scenario small{font-size:12px;line-height:1.5;color:#a7becd}.scenario[aria-pressed="true"]{border-color:#84dbed;background:#153647}
  .demo-controls{padding:28px;border-radius:22px;border:1px solid #2c4e62;background:#102536;align-self:start;position:sticky;top:20px}.demo-controls h2{font-size:23px}.demo-controls p{color:#b2c9db;font-size:14px;line-height:1.7}.demo-controls .run-controls{display:grid;position:static;width:100%;gap:14px;grid-template-columns:1fr}.scope{font-size:12px;color:#abc3d5}
  .run-heading{max-width:none;display:block;position:relative;padding-right:240px}.run-heading h1{font-size:36px}.run-signal{position:absolute;right:0;top:55px;border:1px solid #3b6278;border-radius:30px;padding:10px 18px;font-size:12px;color:#b8eaff;white-space:nowrap}
  [data-screen="run"][data-state="working"] .run-signal{animation:status-breathe 1.4s ease-in-out infinite}
  @keyframes status-breathe{50%{box-shadow:0 0 22px #52d8fa35;border-color:#9cecff}}
  [data-screen="run"][data-state="complete"] .run-signal{color:#9df1c9;border-color:#397d65;background:#0f2b25}
  [data-screen="run"][data-state="held"] .run-signal{color:#ffc3ca;border-color:#a34e5b;background:#301b28}
  .run-source{padding:18px 24px;border:1px solid #28495d;border-radius:18px;background:#091d2a;margin-bottom:22px;line-height:1.65;color:#c9ddeb;overflow-wrap:anywhere}.run-source:empty{display:none}.run-source>p{font-size:13px}.run-source blockquote{font-size:12px;border-left:2px solid #7dd7ed;padding-left:12px;color:#a9c6d9}
  .assurance-board{padding:25px!important;margin-bottom:22px}.stage{border-radius:16px;clip-path:none;min-height:120px;padding:18px}.stage b{font-size:14px}.stage em{font-size:11px;color:#bfd3e2;line-height:1.6}.stage.done{border-color:#3c927f;background:linear-gradient(140deg,#133d36,#0c2728)}.stage.blocked{border-color:#b45768;background:linear-gradient(140deg,#3c2030,#261b28)}
  .briefing{border-radius:22px;overflow:hidden;grid-template-columns:1.1fr 1fr}.brief-main{padding:24px;background:#102739}.brief-main:after{display:none}.brief-main h3{font-size:25px}.brief-main p{font-size:14px;line-height:1.7}.brief-side{gap:12px}.metric{border-radius:14px;padding:16px}.metric span{font-size:10px}.metric b{font-size:23px}.metric small{font-size:11px}
  .verdict{border-radius:18px;padding:22px;clip-path:none;margin:18px 0}.verdict h3{font-size:20px}.verdict p{font-size:14px;line-height:1.7}.mission-details{padding:22px}.mission-details>summary{font-size:12px}.result-toolbar{flex-wrap:wrap;gap:8px;font-size:11px;color:#9fb5c5}
  .run-actions{display:flex;gap:12px;justify-content:center;margin:28px 0;flex-wrap:wrap}.permission-card{max-width:760px;margin:auto}.permission-card details{border:0;background:none;padding:0}.permission-card summary{font-size:17px;margin-bottom:20px}.promise{max-width:760px;margin:22px auto;grid-template-columns:repeat(3,1fr)}
  .activity-list{display:grid;gap:12px;max-width:860px;margin:auto}.activity-entry{display:flex;gap:18px;align-items:center;text-align:left;color:#e1f4ff;background:#102435;border:1px solid #30516a;border-radius:18px;padding:20px;width:100%;cursor:pointer}.activity-entry:hover{border-color:#92d9ed}.activity-entry b{display:block;font-size:14px}.activity-entry small{display:block;font-size:11px;color:#96b4c9;margin-top:6px}.activity-entry .status{margin-left:auto;font-size:12px;white-space:nowrap}.activity-entry .status.good{color:#92eac7}.activity-entry .status.held{color:#ffafbc}
  .activity-empty{padding:35px;text-align:center;border:1px dashed #355267;border-radius:20px;color:#b8cede}.activity-refresh{display:block;margin:0 auto 24px}.route-announcement{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}
  @media(max-width:800px){.task-grid{grid-template-columns:repeat(2,1fr)}.demo-layout{grid-template-columns:1fr}.demo-controls{position:static}.briefing{grid-template-columns:1fr}.friday-nav{gap:0}.friday-nav button{padding:9px 12px;font-size:12px}.shell.layout{padding-top:20px}.pipeline{grid-template-columns:repeat(2,1fr)}}
  @media(max-width:520px){.home-command{flex-direction:column}.task-grid{grid-template-columns:1fr 1fr;gap:10px}.task-tile{min-height:165px;padding:17px}.task-tile b{font-size:16px}.task-tile .tile-label{margin-bottom:13px}.screen-heading h1{font-size:32px}.friday-view .card{padding:20px}.promise{grid-template-columns:1fr}.run-heading{display:block;padding-right:0}.run-signal{position:static;display:inline-block;margin:10px 0}.pipeline{grid-template-columns:1fr}.activity-entry{padding:16px;gap:8px;flex-wrap:wrap}.friday-view[data-screen="home"] .core-console{transform:scale(.7);margin:-28px 0}.topbar .pill.optional{display:none}}
  @media(prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
</style>
"""

EXPERIENCE_NAV = """
<nav class="friday-nav" aria-label="Friday pages">
  <button type="button" data-screen-link="home">Friday</button>
  <button type="button" data-screen-link="bill">Bills</button>
  <button type="button" data-screen-link="document">Documents</button>
  <button type="button" data-screen-link="activity">Activity</button>
  <button type="button" data-screen-link="demos">Safety lab</button>
  <button type="button" data-screen-link="settings">My rules</button>
</nav>
<p id="route-announcement" class="route-announcement" role="status" aria-live="polite"></p>
"""

EXPERIENCE_JS = r"""
    // One purpose per route; all money actions still use the original backend.
    const experience=(()=>{
      const root=document.querySelector('.workspace');const oldBody=root.querySelector('.body');
      const sidebar=document.querySelector('.sidebar');const views={};let busy=false;let active='home';let loadedRun=null;
      const titles={home:'Your financial co-pilot',bill:'Let’s handle your bill.',document:'Let’s read the details.',demos:'See the safety system work.',run:'Friday is on it.',activity:'Everything Friday handled.',settings:'You’re always in control.'};
      const element=(tag,text,className)=>{const e=document.createElement(tag);if(text)e.textContent=text;if(className)e.className=className;return e;};
      function view(name,subtitle){const s=element('section',null,'friday-view');s.dataset.screen=name;s.hidden=true;s.setAttribute('aria-label',titles[name]);
        if(name!=='home'){const h=element('header',null,'screen-heading');const back=element('button','Back to Friday','screen-back');back.type='button';back.dataset.screenLink='home';h.append(back,element('div','FINANCIAL FRIDAY','eyebrow'));const title=element('h1',titles[name]);title.tabIndex=-1;h.append(title,element('p',subtitle));s.append(h);}root.append(s);views[name]=s;return s;}
      const home=view('home');const hero=root.querySelector('.hero');home.append(hero);
      $('workspace-title').innerHTML='A little less worry.<br><span class="accent">A lot more Friday.</span>';
      $('scenario-copy').textContent='What can I take off your mind? Choose a task. I’ll handle the steps within your rules.';
      const command=element('form',null,'home-command');command.innerHTML='<label class="route-announcement" for="home-command">What should Friday handle?</label><input id="home-command" autocomplete="off" placeholder="Ask Friday to handle a bill…"><button class="run" type="submit">Let’s do it</button>';home.append(command);
      const tiles=element('div',null,'task-grid');[
        ['bill','01 / HANDLE','Handle a bill','Give me the request. I’ll check it and handle the allowed task.'],
        ['document','02 / UNDERSTAND','Read a document','A bill image or PDF. Important facts, without the paperwork.'],
        ['activity','03 / REMEMBER','My activity','Your outcomes and receipts, ready whenever you need them.'],
        ['demos','04 / EXPLORE','Try the safety lab','Watch me resolve a trap, recover an outcome or stop safely.']
      ].forEach(([route,label,title,copy])=>{const b=element('button',null,'task-tile');b.type='button';b.dataset.screenLink=route;b.append(element('span',label,'tile-label'),element('b',title),element('small',copy));tiles.append(b);});home.append(tiles,element('p','Artificial-money pilot · No real bank account connected · You set the limits.','screen-note'));
      const bill=view('bill','Paste the bill request once. Friday checks the provider record and your saved permission before taking any action.');
      const live=root.querySelector('.live-card');live.classList.add('task-form');const upload=live.querySelector('.upload-row');const source=$('live-result');bill.append(live);
      $('live-input').value='';$('live-mode').textContent='Ready for a request';$('live-input').placeholder='For example: TN Power bill [reference], ₹2,487, payee tnpower@upi…';
      live.querySelector('h3').textContent='What should I handle?';live.querySelector('.command-copy p').textContent='Use the actual bill details. I won’t treat a message as permission to ignore your rules.';
      const doc=view('document','Choose a bill photo or PDF. Gemini extracts the facts; Friday checks them against the enrolled provider before a task can proceed.');const docCard=element('article',null,'card task-form');docCard.append(element('h2','One document. The important details.'),upload);doc.append(docCard,element('p','Raw uploads are discarded after analysis. Do not upload PINs, OTPs, credentials or identity documents.','screen-note'));
      const demos=view('demos','Controlled artificial-money scenarios, not real bank incidents. Choose one situation, then follow its dedicated run.');const demoLayout=element('div',null,'demo-layout');demoLayout.append($('scenarios'));const controls=element('article',null,'demo-controls');controls.append(element('h2','Choose a situation.'));const description=element('p',null);description.id='demo-description';controls.append(description,sidebar.querySelector('.sidebar-run'));demoLayout.append(controls);demos.append(demoLayout);
      const settings=view('settings','Friday can complete only tasks inside this saved permission. Changing the interface never changes your financial rules.');const permission=element('article',null,'card permission-card');const details=sidebar.querySelector('details');details.open=true;permission.append(details);settings.append(permission,root.querySelector('.promise'));
      const activity=view('activity','Reopen an actual recorded run. These are your sandbox outcomes—not a live connection to your personal bank.');const refresh=element('button','Refresh activity','planner activity-refresh');refresh.type='button';refresh.id='refresh-activity';const list=element('div',null,'activity-list');list.id='friday-activity';activity.append(refresh,list);
      const watcher=root.querySelector('.watch-card');if(watcher)activity.append(watcher);const cloudNote=oldBody.querySelector(':scope > p');if(cloudNote){cloudNote.classList.add('screen-note');activity.append(cloudNote);}
      const runView=view('run','A live task has its own space. Green means confirmed checks; red means an action was held or needs attention.');runView.dataset.state='idle';runView.querySelector('.screen-heading').classList.add('run-heading');const signal=element('span','Waiting for a task','run-signal');signal.id='run-signal';runView.querySelector('.screen-heading').append(signal);
      source.classList.add('run-source');runView.append(source,root.querySelector('.assurance-board'),$('result'));
      const actions=element('div',null,'run-actions');for(const [route,label] of [['home','New task'],['activity','View my activity']]){const b=element('button',label,'planner');b.type='button';b.dataset.screenLink=route;actions.append(b);}runView.append(actions,element('p','Never repeat an uncertain payment blindly. Check the recorded outcome first.','screen-note'));
      const originalSelect=selectScenario;selectScenario=function(id){originalSelect(id);$('demo-description').textContent=catalogue.find(x=>x.id===id)?.description||'Choose a scenario.';$('scenario-copy').textContent='What can I take off your mind? Choose a task. I’ll handle the steps within your rules.';if(active==='home')setCore('READY','What should I handle?');};
      function show(name,push=true){if(!views[name])name='home';active=name;Object.entries(views).forEach(([key,v])=>v.hidden=key!==name);
        document.querySelectorAll('.friday-nav [data-screen-link]').forEach(b=>b.setAttribute('aria-current',b.dataset.screenLink===name?'page':'false'));document.title='Financial Friday · '+titles[name];
        if(name==='home'&&!busy)setCore('READY','What should I handle?');if(push)history.pushState(null,'','#'+name);$('route-announcement').textContent=titles[name];window.scrollTo({top:0,behavior:'auto'});const h=views[name].querySelector('h1,h2');if(h){h.tabIndex=-1;h.focus({preventScroll:true});}if(name==='activity')refreshActivity();}
      function state(kind,text){runView.dataset.state=kind;signal.textContent=text;runView.setAttribute('aria-busy',String(kind==='working'));}
      const completedStatuses=['COMPLETED_SYNTHETIC','ALREADY_COMPLETED','RECONCILED_COMPLETED'];
      const originalRender=render;render=function(r){originalRender(r);loadedRun=r.run_id;if(source.textContent.startsWith('Loading'))source.textContent='Recorded outcome loaded. Viewing this receipt does not submit another payment.';show('run',false);state(completedStatuses.includes(r.status)?'complete':'held',r.status==='HELD'?'Held · no new payment':r.status==='ALREADY_COMPLETED'?'Already handled · no repeat':r.status==='RECONCILED_COMPLETED'?'Recovered · no retry':r.status==='COMPLETED_SYNTHETIC'?'Completed · receipt recorded':'Attention · outcome not confirmed');};
      async function execute(fn,label){if(busy){toast('Friday is already handling a task. Check its outcome before starting another.');show('run',false);return;}
        busy=true;show('run');loadedRun=null;source.textContent=label;state('working','Working · awaiting verified result');
        try{await fn();}finally{busy=false;if(runView.dataset.state==='working'){if(document.querySelector('[data-stage="ground"].blocked')||document.querySelector('[data-stage="understand"].blocked'))state('held','Attention · check the evidence');else if($('live-mode').textContent.toUpperCase()==='READY')state('idle','Ready · approval required');else state('idle','Check the task outcome below');}}}
      const oldCheck=checkLive;checkLive=()=>{if(!$('live-input').value.trim()){toast('Add a bill request first.');$('live-input').focus();return Promise.resolve();}return execute(oldCheck,'Understanding your bill request…');};
      const oldDocument=checkDocument;checkDocument=()=>{if(!$('document-input').files.length){toast('Choose a bill image or PDF first.');$('document-input').focus();return Promise.resolve();}return execute(oldDocument,'Reading your document…');};
      const oldRun=run;run=()=>execute(oldRun,'Running a controlled safety scenario…');
      const originalVoice=startVoice;startVoice=function(){show('bill');originalVoice();};
      command.addEventListener('submit',e=>{e.preventDefault();const value=$('home-command').value.trim();show('bill');if(value)$('live-input').value=value;$('live-input').focus();});
      async function refreshActivity(){list.replaceChildren(element('p','Loading recorded outcomes…','activity-empty'));refresh.disabled=true;
        try{const data=await jsonRequest('/api/friday/today');list.replaceChildren();const runs=data.recent_runs||[];if(!runs.length)list.append(element('p','Nothing handled yet. Start with a bill or the safety lab.','activity-empty'));
          runs.forEach(r=>{if(!/^[A-Za-z0-9_-]{1,100}$/.test(r.run_id))return;const b=element('button',null,'activity-entry');b.type='button';b.dataset.runId=r.run_id;const copy=element('div');copy.append(element('b',nice(String(r.case_id||'Recorded task').replaceAll('-','_'))),element('small',r.run_id));const status=element('span',nice(r.status),'status '+(completedStatuses.includes(r.status)?'good':'held'));b.append(copy,status);list.append(b);});
        }catch(e){list.replaceChildren(element('p','Activity could not be loaded. No payment was submitted. Try refreshing this read-only view.','activity-empty'));}finally{refresh.disabled=false;}}
      async function openRun(id){if(busy){toast('Wait for the current task to finish before reopening another run.');return;}show('run',false);$('result').classList.remove('visible');$('briefing').classList.remove('visible');source.textContent='Loading the recorded outcome. No payment is being submitted.';resetStages();state('working','Loading saved evidence');
        try{render(await jsonRequest('/api/friday/runs/'+encodeURIComponent(id)));}catch(e){state('held','Outcome unavailable');source.textContent='This recorded run could not be loaded. No payment was submitted. Check activity before retrying any financial task.';}}
      document.addEventListener('click',e=>{const target=e.target.closest('[data-screen-link],[data-run-id]');if(!target)return;if(target.dataset.runId){history.pushState(null,'','#run='+encodeURIComponent(target.dataset.runId));openRun(target.dataset.runId);}else show(target.dataset.screenLink);});refresh.addEventListener('click',refreshActivity);
      function route(load=true){if(location.hash.startsWith('#run=')){show('run',false);if(load)openRun(decodeURIComponent(location.hash.slice(5)));else{source.textContent='Loading your recorded run…';state('working','Loading saved evidence');}}else show(location.hash.slice(1)||'home',false);}
      window.addEventListener('popstate',()=>route());window.addEventListener('hashchange',()=>{if(location.hash.startsWith('#run=')&&loadedRun===decodeURIComponent(location.hash.slice(5)))return;route();});route(false);
      return {show,openRun};
    })();
"""


def enhance_friday_html(html: str) -> str:
    """Retain existing element IDs and API handlers while separating their views."""
    return (html.replace("</head>", EXPERIENCE_CSS + "</head>", 1)
            .replace('<main class="shell layout">', EXPERIENCE_NAV + '<main class="shell layout">', 1)
            .replace("    let watching=false;", EXPERIENCE_JS + "\n    let watching=false;", 1))
