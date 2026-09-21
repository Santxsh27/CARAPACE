"""Future-facing presentation layer for the CARAPACE Control Room.

The existing Control Room remains the functional source of truth.  These
fragments add a judge-friendly assurance narrative without duplicating any
backend behaviour or inventing demo data.
"""

FUTURE_CSS = r"""
    :root {
      --ink:#f5f8ff;--muted:#91a4c2;--line:rgba(145,184,235,.20);
      --soft:rgba(12,28,49,.76);--blue:#78a8ff;--navy:#07111f;
      --cyan:#45eee0;--green:#45e6bb;--green-bg:rgba(35,177,139,.12);
      --red:#ff6678;--red-bg:rgba(255,77,100,.12);--amber:#ffd479;
      --amber-bg:rgba(255,190,73,.10);--white:rgba(8,21,37,.86);
      --shadow:0 28px 80px rgba(0,0,0,.34)
    }
    html{background:#030914;color-scheme:dark}
    body{background:#030914;color:var(--ink);overflow-x:hidden}
    body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:-2;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='80' height='80' viewBox='0 0 80 80'%3E%3Cpath d='M80 0H0V80' fill='none' stroke='%231b3854' stroke-opacity='.28' stroke-width='.55'/%3E%3C/svg%3E")}
    body::after{content:"";position:fixed;inset:0;pointer-events:none;z-index:-1;background:rgba(2,8,18,.34)}
    .topbar{background:rgba(3,10,20,.84);border-color:var(--line);backdrop-filter:blur(24px)}
    .topbar-inner{min-height:72px}.brand{font-size:14px;color:#edf4ff}.brand span{color:var(--cyan)}
    .toplinks{border:1px solid var(--line);border-radius:999px;padding:5px;background:rgba(7,18,32,.72)}
    .toplinks a{border:0;background:transparent;color:var(--muted);padding:9px 14px;transition:color .2s ease,background .2s ease,transform .2s ease}
    .toplinks a:hover,.toplinks a:focus-visible{color:var(--ink);background:rgba(103,154,236,.13);transform:translateY(-1px)}
    main{width:min(1540px,calc(100% - 38px));padding-top:20px}
    .hero{display:none}
    .panel,.status,.pipe div{background:rgba(6,18,33,.82);border-color:var(--line);box-shadow:var(--shadow)}
    .section-head{scroll-margin-top:92px}.section-head h2{color:#f5f8ff}.section-head p,.lead,.bank-guide p,.bank-guide li,.table-toolbar p,.experiment-main>p,.proofops>p,.lens-result>p{color:var(--muted)}
    .eyebrow{color:var(--cyan)}
    .statusbar{margin:14px 0 34px}.status{background:rgba(5,18,32,.68);padding:13px 16px}.status small{color:#7790b4}.status strong{color:#dfeaff}.dot.ok{background:var(--green);box-shadow:0 0 0 4px rgba(69,230,187,.12),0 0 18px rgba(69,230,187,.52)}
    .bank-guide,.lens-form,.source-grid{background:rgba(8,23,41,.72);border-color:var(--line)}
    .credential,.lens-form textarea,.lens-form input,.receipt-stage,.proof-card,.result-card,.secondary{background:rgba(4,14,27,.76);border-color:var(--line);color:var(--ink)}
    .lens-form textarea:focus,.lens-form input:focus{outline:2px solid rgba(69,238,224,.5);outline-offset:2px}
    .bank-frame-wrap{background:#fff}.windowbar{background:#0a1728;border-color:var(--line);color:var(--muted)}
    th{background:#08172a;color:#8297b7}td,th{border-color:rgba(137,171,217,.13)}
    .table-scroll,.mapping{border-color:var(--line)}
    .promise{background:#071526}.promise-row{border-color:var(--line)}
    .step,.lens-fact{background:rgba(83,125,183,.10)}
    .proofops,.receipt{background:rgba(6,24,41,.78);border-color:rgba(97,175,235,.31)}
    .mapping h4{background:rgba(8,23,41,.9);border-color:var(--line)}.mapping-row{border-color:var(--line)}
    .honesty{background:rgba(255,196,75,.08);border-color:rgba(255,196,75,.28);color:#f0dca6}
    .primary,.open-bank{background:#2f70dc;color:#fff;box-shadow:0 12px 34px rgba(47,112,220,.30);transition:transform .2s ease,box-shadow .2s ease}
    .primary:hover,.open-bank:hover{transform:translateY(-2px);box-shadow:0 18px 38px rgba(47,112,220,.38)}
    .future-shell{position:relative;min-height:760px;border:1px solid var(--line);border-radius:30px;overflow:hidden;background:rgba(4,14,27,.72);box-shadow:0 38px 110px rgba(0,0,0,.42)}
    #assurance-canvas{position:absolute;inset:0;width:100%;height:100%;opacity:.95;pointer-events:none}
    .future-grid{position:relative;z-index:2;display:grid;grid-template-columns:minmax(0,1fr) 330px;min-height:760px}
    .future-main{padding:42px 34px 112px;min-width:0}.future-aside{border-left:1px solid var(--line);background:rgba(4,13,25,.78);padding:24px 20px;backdrop-filter:blur(18px)}
    .future-intro{display:flex;align-items:flex-start;justify-content:space-between;gap:28px;margin-bottom:34px}.future-intro h1{font-size:clamp(38px,4.5vw,68px);max-width:760px;margin:9px 0 12px}.future-intro h1 span{color:var(--blue)}
    .future-intro p{max-width:670px;color:#a7b8d0;font-size:17px;line-height:1.55;margin:0}.live-pill{display:flex;align-items:center;gap:10px;border:1px solid rgba(69,230,187,.28);border-radius:999px;padding:9px 13px;color:#9af4dc;background:rgba(12,48,43,.36);font-size:11px;font-weight:850;letter-spacing:.1em;white-space:nowrap}.live-pill::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--green);box-shadow:0 0 16px var(--green)}
    .flow-stage{position:relative;min-height:385px;display:flex;align-items:center;padding:22px 0;perspective:1100px}
    .flow-track{position:absolute;left:4%;right:4%;top:50%;height:1px;background:rgba(93,170,226,.38);box-shadow:0 0 18px rgba(69,238,224,.28)}
    .flow-progress{position:absolute;left:4%;top:50%;height:2px;width:0;background:var(--cyan);box-shadow:0 0 20px rgba(69,238,224,.78);transition:width 1s cubic-bezier(.2,.75,.2,1),background .4s ease}
    .flow-nodes{position:relative;width:100%;display:grid;grid-template-columns:repeat(5,1fr);gap:16px;align-items:center}
    .flow-node{position:relative;min-height:188px;padding:20px 15px;border:1px solid rgba(129,184,239,.25);background:rgba(10,30,52,.52);backdrop-filter:blur(14px);border-radius:18px;transform:rotateY(-7deg) translateZ(0);transition:transform .65s cubic-bezier(.2,.7,.2,1),border .4s ease,box-shadow .4s ease,opacity .4s ease;box-shadow:inset 0 1px rgba(255,255,255,.08),0 25px 48px rgba(0,0,0,.24)}
    .flow-node:nth-child(even){transform:rotateY(7deg) translateY(16px)}.flow-node:hover{transform:rotateY(0) translateY(-8px) scale(1.025);border-color:rgba(103,178,255,.55)}
    .flow-node .stage-no{display:block;color:#7f9bc0;font-size:10px;letter-spacing:.15em;margin-bottom:46px}.flow-node b{display:block;color:#f4f8ff;font-size:13px;line-height:1.35}.flow-node small{display:block;color:#8398b7;line-height:1.45;margin-top:7px;font-size:11px}.flow-node::after{content:"";position:absolute;width:9px;height:9px;border-radius:50%;left:50%;bottom:-28px;transform:translateX(-50%);background:#274363;border:1px solid #57799f;transition:background .3s ease,box-shadow .3s ease}
    .flow-node.active{border-color:rgba(69,238,224,.75);box-shadow:inset 0 1px rgba(255,255,255,.13),0 0 35px rgba(69,238,224,.18)}.flow-node.active::after,.flow-node.done::after{background:var(--cyan);box-shadow:0 0 18px rgba(69,238,224,.85)}
    .flow-node.incident{border-color:rgba(255,102,120,.75);box-shadow:0 0 38px rgba(255,74,96,.20)}.flow-node.incident::after{background:var(--red);box-shadow:0 0 18px rgba(255,102,120,.9)}
    .payment-token{position:absolute;left:-1.5%;top:calc(50% - 23px);width:56px;height:46px;border:1px solid rgba(117,209,255,.65);border-radius:14px;background:rgba(29,93,142,.68);display:grid;place-items:center;color:#fff;font-weight:900;font-size:15px;box-shadow:0 0 28px rgba(66,187,255,.42);transform:translateY(-62px);transition:left 1s cubic-bezier(.2,.75,.2,1),transform .6s ease,background .4s ease,opacity .4s ease;z-index:3}.payment-token.incident{background:rgba(170,41,62,.78);transform:translateY(-62px) scale(1.05)}.payment-token.repaired{background:rgba(20,133,109,.76);transform:translateY(-62px) scale(1.08)}
    .split-token{position:absolute;left:65%;top:calc(50% + 20px);width:40px;height:34px;border:1px solid rgba(255,102,120,.75);border-radius:12px;background:rgba(139,27,47,.76);display:grid;place-items:center;color:#ffd8dc;font-size:11px;font-weight:850;opacity:0;transform:translateY(0) scale(.6);transition:opacity .45s ease,transform .65s ease,left .8s ease;box-shadow:0 0 25px rgba(255,82,105,.34);z-index:3}.future-shell[data-phase="incident"] .split-token{opacity:1;transform:translateY(35px) scale(1)}.future-shell[data-phase="resolved"] .split-token{opacity:0;left:77%;transform:translateY(0) scale(.55)}
    .future-actions{display:flex;align-items:center;gap:15px;flex-wrap:wrap}.future-actions .primary{padding:14px 19px}.future-actions small{color:var(--muted);max-width:560px;line-height:1.45}.motion-toggle{margin-left:auto;display:flex;align-items:center;gap:9px;color:#8297b6;font-size:11px}.switch{width:38px;height:22px;border-radius:999px;border:1px solid var(--line);background:#11243b;padding:3px;cursor:pointer}.switch::after{content:"";display:block;width:14px;height:14px;border-radius:50%;background:#dce9f8;transition:transform .2s ease}.switch[aria-checked="true"]::after{transform:translateX(16px);background:var(--cyan)}
    .aside-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px}.aside-head h2{font-size:17px;margin:0}.aside-head span{color:#7890af;font-size:11px}.plain-story{margin-bottom:20px}.plain-story p{font-size:17px;line-height:1.45;margin:0 0 11px;color:#dfe9f8}.plain-story p:last-child{margin-bottom:0}.evidence-block{border:1px solid var(--line);border-radius:16px;padding:15px;margin-top:12px;background:rgba(8,24,42,.55)}.evidence-block small{display:block;color:#7890b1;margin-bottom:7px}.evidence-block strong{display:block;font-size:13px;line-height:1.45}.evidence-block.danger{border-color:rgba(255,102,120,.42);background:rgba(78,18,31,.26)}.evidence-block.danger strong{color:#ff9ba8}.evidence-block.good-evidence{border-color:rgba(69,230,187,.35)}
    .future-timeline{position:absolute;z-index:4;left:20px;right:20px;bottom:18px;min-height:76px;border:1px solid var(--line);border-radius:18px;background:rgba(4,15,28,.88);backdrop-filter:blur(22px);display:grid;grid-template-columns:170px 1fr 180px;align-items:center;gap:18px;padding:14px 16px}.timeline-title strong{display:block;font-size:13px}.timeline-title small{color:#7690b2}.timeline-steps{display:grid;grid-template-columns:repeat(5,1fr);gap:6px}.timeline-step{text-align:center;color:#7590b4;font-size:10px;position:relative;padding-top:19px}.timeline-step::before{content:"";position:absolute;top:2px;left:50%;width:9px;height:9px;border-radius:50%;transform:translateX(-50%);background:#243e5c;border:1px solid #56789d}.timeline-step.done{color:#a8f6e2}.timeline-step.done::before{background:var(--green);box-shadow:0 0 13px rgba(69,230,187,.62)}.timeline-step.fail{color:#ff9aa7}.timeline-step.fail::before{background:var(--red);box-shadow:0 0 13px rgba(255,102,120,.65)}.review-link{text-align:center;border:1px solid rgba(105,158,255,.45);border-radius:12px;padding:11px 13px;color:#dce8ff;text-decoration:none;font-size:12px;font-weight:800;background:rgba(42,88,165,.18)}
    .lab-divider{display:flex;align-items:center;gap:16px;margin:42px 0 0;color:#6f87a9;font-size:11px;letter-spacing:.16em;text-transform:uppercase}.lab-divider::before,.lab-divider::after{content:"";height:1px;background:var(--line);flex:1}
    @media(max-width:1150px){.future-grid{grid-template-columns:1fr;min-height:auto}.future-main{padding-bottom:34px}.future-aside{border-left:0;border-top:1px solid var(--line);display:grid;grid-template-columns:1fr 1fr;gap:14px}.aside-head,.plain-story{grid-column:1/-1}.future-shell{padding-bottom:0}.future-timeline{position:relative;left:auto;right:auto;bottom:auto;margin:18px 20px;grid-template-columns:150px 1fr}.review-link{display:none}.flow-stage{min-height:330px}}
    @media(max-width:820px){.future-main{padding:28px 20px 120px}.future-intro{display:block}.live-pill{display:inline-flex;margin-top:18px}.flow-stage{overflow-x:auto;min-height:360px}.flow-nodes{min-width:850px}.flow-track,.flow-progress{min-width:760px}.payment-token{display:none}.future-timeline{grid-template-columns:1fr;gap:10px}.timeline-title{display:none}.future-aside{grid-template-columns:1fr}.future-shell{padding-bottom:155px}.motion-toggle{margin-left:0}.toplinks a:nth-last-child(-n+3){display:none}}
    @media(max-width:550px){main{width:min(100% - 18px,1540px)}.future-shell{border-radius:22px}.future-intro h1{font-size:39px}.future-timeline{left:10px;right:10px}.timeline-steps{overflow-x:auto;grid-template-columns:repeat(5,90px)}.statusbar{grid-template-columns:1fr 1fr}.topbar-inner{width:calc(100% - 18px)}.brand{font-size:12px}}
    @media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;animation:none!important;transition-duration:.01ms!important}}
"""


ASSURANCE_FLOW_HTML = r"""
    <section id="assurance" class="future-shell" data-phase="idle" aria-labelledby="assurance-title">
      <canvas id="assurance-canvas" aria-hidden="true"></canvas>
      <div class="future-grid">
        <div class="future-main">
          <div class="future-intro">
            <div>
              <div class="eyebrow">Continuous payment assurance</div>
              <h1 id="assurance-title">See every payment.<br><span>Stop what is wrong.</span></h1>
              <p>One understandable journey from customer intent to bank evidence, verified repair and human approval.</p>
            </div>
            <div id="ai-live-pill" class="live-pill">GEMINI STATUS CHECKING</div>
          </div>
          <div class="flow-stage" aria-label="Payment assurance lifecycle">
            <div class="flow-track"></div><div id="flow-progress" class="flow-progress"></div>
            <div id="payment-token" class="payment-token">$49.99</div><div class="split-token">DEBIT 2</div>
            <div class="flow-nodes">
              <article class="flow-node" data-stage="1"><span class="stage-no">01 · CONTEXT</span><b>Intent checked</b><small>Gemini compares the story with the real action.</small></article>
              <article class="flow-node" data-stage="2"><span class="stage-no">02 · CONTRACT</span><b>Payment bound</b><small>Recipient, amount and maximum debits are fixed.</small></article>
              <article class="flow-node" data-stage="3"><span class="stage-no">03 · BANK</span><b>Bank authorised</b><small>The approved request enters the bank normally.</small></article>
              <article class="flow-node" data-stage="4"><span class="stage-no">04 · WITNESS</span><b>Ledger witnessed</b><small>Exact server records are checked independently.</small></article>
              <article class="flow-node" data-stage="5"><span class="stage-no">05 · PROOFOPS</span><b>Repair verified</b><small>AI proposes; deterministic reruns prove.</small></article>
            </div>
          </div>
          <div class="future-actions">
            <button id="hero-run" class="primary" type="button">Run live assurance story</button>
            <small id="hero-run-note">Uses artificial money in the official Bank of Anthos ledger.</small>
            <label class="motion-toggle"><button id="motion-switch" class="switch" type="button" role="switch" aria-checked="true" aria-label="Toggle ambient motion"></button> Ambient motion</label>
          </div>
        </div>
        <aside class="future-aside" aria-live="polite">
          <div class="aside-head"><h2>What happened</h2><span id="story-state">READY</span></div>
          <div class="plain-story">
            <p id="story-line-1">A customer will approve one artificial $49.99 payment.</p>
            <p id="story-line-2">CARAPACE will compare that promise with the bank ledger.</p>
            <p id="story-line-3">Run the story to create and repair a controlled retry fault.</p>
          </div>
          <div id="incident-evidence" class="evidence-block"><small>Assurance status</small><strong id="incident-status">Ready for a live evidence run</strong></div>
          <div class="evidence-block"><small>AI reasoning</small><strong id="ai-provenance">Provider status loading…</strong></div>
          <div class="evidence-block"><small>Deterministic authority</small><strong id="contract-status">Financial verifier controls PASS / FAIL</strong></div>
          <div class="evidence-block good-evidence"><small>Release authority</small><strong>Human approval always required</strong></div>
        </aside>
      </div>
      <div class="future-timeline">
        <div class="timeline-title"><strong>Assurance timeline</strong><small>Live evidence, not a video</small></div>
        <div class="timeline-steps">
          <div class="timeline-step" data-time-stage="1">Intent checked</div><div class="timeline-step" data-time-stage="2">Payment bound</div><div class="timeline-step" data-time-stage="3">Bank authorised</div><div class="timeline-step" data-time-stage="4">Mismatch detected</div><div class="timeline-step" data-time-stage="5">Repair verified</div>
        </div>
        <a class="review-link" href="#verification">Review full evidence</a>
      </div>
    </section>
    <div class="lab-divider">Explore every evidence surface</div>
"""


FUTURE_JS = r"""
  <script type="module">
    const shell=document.getElementById('assurance');
    const heroRun=document.getElementById('hero-run');
    const originalRun=document.getElementById('run');
    const progress=document.getElementById('flow-progress');
    const token=document.getElementById('payment-token');
    const note=document.getElementById('hero-run-note');
    const storyState=document.getElementById('story-state');
    const incident=document.getElementById('incident-evidence');
    const motionSwitch=document.getElementById('motion-switch');
    const nodes=[...document.querySelectorAll('.flow-node')];
    const timeSteps=[...document.querySelectorAll('.timeline-step')];
    let ambient=true,stageTimer=null;

    function setStage(stage,phase='running'){
      shell.dataset.phase=phase;
      nodes.forEach((node,index)=>{
        node.classList.toggle('done',index+1<stage);
        node.classList.toggle('active',index+1===stage && phase!=='incident');
        node.classList.toggle('incident',index+1===4 && phase==='incident');
      });
      timeSteps.forEach((item,index)=>{
        item.classList.toggle('done',index+1<stage || (index+1===stage && phase==='resolved'));
        item.classList.toggle('fail',index+1===4 && phase==='incident');
      });
      const positions=[-1.5,18,39,60,80];
      token.style.left=`${positions[Math.max(0,stage-1)]}%`;
      progress.style.width=`${Math.max(0,(stage-1)*23)}%`;
      token.className='payment-token'+(phase==='incident'?' incident':phase==='resolved'?' repaired':'');
      if(phase==='incident') progress.style.background='var(--red)';
      if(phase==='resolved') progress.style.background='var(--green)';
    }

    function resetStory(){
      clearInterval(stageTimer);setStage(1,'running');storyState.textContent='RUNNING';
      heroRun.disabled=true;heroRun.textContent='Watching the live evidence…';
      note.textContent='Payment Promise → bank posting → ledger witness → ProofOps';
      document.getElementById('story-line-1').textContent='The customer approved one artificial $49.99 payment.';
      document.getElementById('story-line-2').textContent='CARAPACE is following its evidence into the bank ledger.';
      document.getElementById('story-line-3').textContent='No result is declared until the deterministic verifier checks it.';
      incident.classList.remove('danger');document.getElementById('incident-status').textContent='Live experiment running';
      document.getElementById('contract-status').textContent='Waiting for ledger evidence';
      let stage=1;stageTimer=setInterval(()=>{if(stage<3){stage+=1;setStage(stage,'running')}},1300);
    }

    heroRun.addEventListener('click',()=>{resetStory();originalRun.click()});
    // Keep the judge-facing story in view. The explicit evidence link below
    // remains the user's deliberate route to the deep technical result.
    document.getElementById('results').scrollIntoView=()=>{};
    const resultObserver=new MutationObserver(()=>{
      if(!document.getElementById('results').classList.contains('visible'))return;
      clearInterval(stageTimer);setStage(4,'incident');storyState.textContent='MISMATCH';incident.classList.add('danger');
      document.getElementById('story-line-1').textContent='You approved one artificial $49.99 payment.';
      document.getElementById('story-line-2').textContent='The bank recorded two matching debit rows.';
      document.getElementById('story-line-3').textContent='CARAPACE preserved the exact counterexample and started ProofOps.';
      document.getElementById('incident-status').textContent='Critical mismatch contained in the test environment';
      document.getElementById('contract-status').textContent='Contract F1 failed: maximum one posted debit';
    });
    resultObserver.observe(document.getElementById('results'),{attributes:true,attributeFilter:['class']});

    const proofObserver=new MutationObserver(()=>{
      const title=document.getElementById('proof-title').textContent;
      if(!title.toLowerCase().includes('verified'))return;
      setStage(5,'resolved');storyState.textContent='VERIFIED';
      document.getElementById('story-line-3').textContent='The retry fault was reproduced and the smallest repair passed an independent rerun.';
      document.getElementById('incident-status').textContent='Mismatch explained; candidate repair verified';
      document.getElementById('contract-status').textContent='MISMATCH → MATCH under deterministic replay';
      heroRun.disabled=false;heroRun.textContent='Run another live story';note.textContent='Complete. Human approval remains required before release.';
    });
    proofObserver.observe(document.getElementById('proof-title'),{childList:true,subtree:true});
    const runNoteObserver=new MutationObserver(()=>{if(document.getElementById('run-note').classList.contains('error')){clearInterval(stageTimer);heroRun.disabled=false;heroRun.textContent='Retry live assurance story';note.textContent=document.getElementById('run-note').textContent;storyState.textContent='NEEDS ATTENTION'}});
    runNoteObserver.observe(document.getElementById('run-note'),{childList:true,attributes:true});

    motionSwitch.addEventListener('click',()=>{ambient=!ambient;motionSwitch.setAttribute('aria-checked',String(ambient));if(window.carapaceScene)window.carapaceScene.ambient=ambient});
    document.querySelector('.review-link').addEventListener('click',()=>document.getElementById('results').classList.add('visible'));
    fetch('/api/ai/status').then(response=>response.json()).then(data=>{
      document.getElementById('ai-live-pill').textContent=data.mode==='GEMINI_API'?'GEMINI LIVE':'SAFE LOCAL MODE';
      document.getElementById('ai-provenance').textContent=`${data.mode} · ${data.model} · advisory reasoning only`;
    }).catch(()=>{document.getElementById('ai-live-pill').textContent='AI STATUS UNAVAILABLE';document.getElementById('ai-provenance').textContent='The deterministic verifier remains available.'});

    try{
      const THREE=await import('https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.min.js');
      const canvas=document.getElementById('assurance-canvas');
      const renderer=new THREE.WebGLRenderer({canvas,alpha:true,antialias:true,powerPreference:'high-performance'});
      renderer.setPixelRatio(Math.min(devicePixelRatio,1.6));
      const scene=new THREE.Scene();const camera=new THREE.PerspectiveCamera(46,1,.1,100);camera.position.set(0,1.6,10);
      const particles=new THREE.BufferGeometry();const count=260;const positions=new Float32Array(count*3);
      for(let i=0;i<count;i++){positions[i*3]=(Math.random()-.5)*15;positions[i*3+1]=(Math.random()-.5)*7;positions[i*3+2]=(Math.random()-.5)*6}
      particles.setAttribute('position',new THREE.BufferAttribute(positions,3));
      const points=new THREE.Points(particles,new THREE.PointsMaterial({color:0x4a8cca,size:.025,transparent:true,opacity:.7}));scene.add(points);
      const assuranceCurve=new THREE.CatmullRomCurve3([
        new THREE.Vector3(-6.4,-.05,0),new THREE.Vector3(-3.4,.18,.15),
        new THREE.Vector3(-.8,-.12,.05),new THREE.Vector3(2.1,.14,.1),
        new THREE.Vector3(6.4,-.02,0)
      ]);
      const assuranceMaterial=new THREE.MeshBasicMaterial({color:0x45eee0,transparent:true,opacity:.42});
      const assuranceGlowMaterial=new THREE.MeshBasicMaterial({color:0x438cff,transparent:true,opacity:.09});
      const assuranceTube=new THREE.Mesh(new THREE.TubeGeometry(assuranceCurve,160,.035,10,false),assuranceMaterial);
      const assuranceGlow=new THREE.Mesh(new THREE.TubeGeometry(assuranceCurve,160,.12,10,false),assuranceGlowMaterial);
      scene.add(assuranceGlow,assuranceTube);
      const faultCurve=new THREE.CatmullRomCurve3([
        new THREE.Vector3(1.3,.12,.12),new THREE.Vector3(2.5,.72,.18),
        new THREE.Vector3(3.8,.62,.14),new THREE.Vector3(5.0,.04,.06)
      ]);
      const faultMaterial=new THREE.MeshBasicMaterial({color:0xff536b,transparent:true,opacity:0});
      const faultTube=new THREE.Mesh(new THREE.TubeGeometry(faultCurve,90,.055,10,false),faultMaterial);scene.add(faultTube);
      const rings=[];for(let i=0;i<5;i++){const ring=new THREE.Mesh(new THREE.TorusGeometry(.8,.012,8,80),new THREE.MeshBasicMaterial({color:i===3?0xff6678:0x45eee0,transparent:true,opacity:.22}));ring.position.set(-5.3+i*2.65,0,-1.5+i*.12);ring.rotation.y=.7;rings.push(ring);scene.add(ring)}
      const state={ambient:true};window.carapaceScene=state;
      function resize(){const rect=shell.getBoundingClientRect();renderer.setSize(rect.width,rect.height,false);camera.aspect=rect.width/rect.height;camera.updateProjectionMatrix()}
      new ResizeObserver(resize).observe(shell);resize();let last=0;
      function render(time){requestAnimationFrame(render);const phase=shell.dataset.phase;if(phase==='incident'){faultMaterial.opacity=.72;assuranceMaterial.color.setHex(0xff6678)}else if(phase==='resolved'){faultMaterial.opacity=Math.max(0,faultMaterial.opacity-.025);assuranceMaterial.color.setHex(0x45e6bb)}else{faultMaterial.opacity=0;assuranceMaterial.color.setHex(0x45eee0)}if(state.ambient&&!matchMedia('(prefers-reduced-motion: reduce)').matches){const delta=(time-last)/1000;points.rotation.y+=delta*.018;points.rotation.x=Math.sin(time*.00008)*.08;assuranceTube.rotation.z=Math.sin(time*.00035)*.012;assuranceGlow.rotation.z=assuranceTube.rotation.z;rings.forEach((r,i)=>{r.rotation.x=Math.sin(time*.00045+i)*.12;r.rotation.z+=delta*(.025+i*.004)})}last=time;renderer.render(scene,camera)}render(0);
    }catch(error){console.info('CARAPACE ambient 3D fallback active',error)}
  </script>
"""
