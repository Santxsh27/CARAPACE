"""Simplification must retain consent and original financial handlers."""
import unittest
import json
import shutil
import subprocess
from pathlib import Path
from carapace_integrations.financial_friday_ui import FINANCIAL_FRIDAY_HTML
from carapace_integrations.friday_simple import SIMPLE_CSS, SIMPLE_JS


class FridaySimpleTests(unittest.TestCase):
    def test_simple_layer_is_in_the_real_local_and_cloud_html(self):
        self.assertIn('id="friday-simple-styles"', FINANCIAL_FRIDAY_HTML)
        self.assertIn('Hi. I’m Friday.', FINANCIAL_FRIDAY_HTML)
        self.assertIn('Review spending', FINANCIAL_FRIDAY_HTML)
        self.assertIn('CSV format & privacy', FINANCIAL_FRIDAY_HTML)
        self.assertIn('Demo wallet · artificial funds', FINANCIAL_FRIDAY_HTML)

    def test_forms_are_moved_not_replaced_or_permission_changed(self):
        self.assertIn('statementSection,personalInbox,walletFold', SIMPLE_JS)
        self.assertIn('statementConsent', SIMPLE_JS)
        self.assertIn('liftApproval(data)', SIMPLE_JS)
        self.assertIn('review.amount_minor', SIMPLE_JS)
        self.assertIn('review.payee_id', SIMPLE_JS)
        self.assertIn('source.querySelector', SIMPLE_JS)
        self.assertNotIn('fetch(', SIMPLE_JS)
        self.assertNotIn('jsonRequest(', SIMPLE_JS)
        self.assertNotIn('localStorage', SIMPLE_JS)
        self.assertNotIn('innerHTML', SIMPLE_JS)
        self.assertNotIn('automatic_sandbox_execution', SIMPLE_JS)

    def test_detail_disclosure_and_mobile_layout_have_accessible_controls(self):
        self.assertIn("element('details'", SIMPLE_JS)
        self.assertIn("element('summary'", SIMPLE_JS)
        self.assertIn("e.key==='Escape'", SIMPLE_JS)
        self.assertIn('selectMoneyPanel(null)', SIMPLE_JS)
        self.assertIn('.simple-panel[hidden]', SIMPLE_CSS)
        self.assertIn('@media(max-width:640px)', SIMPLE_CSS)
        self.assertIn('No real bank account connected', SIMPLE_JS)

    def test_actual_approval_presenter_keeps_fields_and_original_button(self):
        node = '/usr/local/bin/node' if Path('/usr/local/bin/node').exists() else shutil.which('node')
        if not node:
            self.skipTest('Node needed for UI runtime verification')
        helper = 'function liftApproval' + SIMPLE_JS.split('function liftApproval', 1)[1].split('const simplerSignal', 1)[0]
        harness = """
let button={original:true};const source={querySelector:()=>button};
const approvalArea={children:[],replaceChildren(){this.children=[]},append(...nodes){this.children.push(...nodes)}};
const element=(tag,text)=>({tag,text});const workspaceMoney=value=>'INR '+(value/100).toFixed(2);
"""
        harness += helper + """
liftApproval({bill_review:{amount_minor:246813,payee_id:'verified@upi',provider_name:'Known biller'}});
const visible=approvalArea.children[0].text;const retained=approvalArea.children[1]===button;
button=null;liftApproval({state:'ATTENTION'});
process.stdout.write(JSON.stringify({visible,retained,cleared:approvalArea.children.length===0}));
"""
        result = subprocess.run([node, '-e', harness], text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)
        self.assertIn('INR 2468.13', evidence['visible'])
        self.assertIn('verified@upi', evidence['visible'])
        self.assertIn('Artificial payment', evidence['visible'])
        self.assertTrue(evidence['retained'])
        self.assertTrue(evidence['cleared'])
