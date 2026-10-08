from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

from carapace_integrations.financial_friday_ui import FINANCIAL_FRIDAY_HTML
from carapace_integrations.friday_experience import EXPERIENCE_JS, EXPERIENCE_CSS


class FridayWorkspaceUITests(unittest.TestCase):
    def test_generated_application_scripts_parse(self):
        node = "/usr/local/bin/node" if Path("/usr/local/bin/node").exists() else shutil.which("node")
        if not node:
            self.skipTest("Node is optional; syntax checks need Node")
        scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", FINANCIAL_FRIDAY_HTML, re.S)
        self.assertTrue(scripts)
        for script in scripts:
            result = subprocess.run([node, "--check"], input=script, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_real_app_has_money_route_and_clear_capability_coverage(self):
        self.assertIn('data-screen-link="money"', FINANCIAL_FRIDAY_HTML)
        self.assertIn("const moneyView=view('money'", FINANCIAL_FRIDAY_HTML)
        self.assertIn("if(name==='money')refreshMoney()", EXPERIENCE_JS)
        self.assertIn("01 / UNDERSTAND", EXPERIENCE_JS)
        self.assertIn("02 / HANDLE", EXPERIENCE_JS)
        self.assertIn("03 / PROTECT", EXPERIENCE_JS)
        self.assertIn("Kernel tested · connector pending", EXPERIENCE_JS)
        self.assertIn("not all your bank accounts", EXPERIENCE_JS)
        self.assertIn(".money-summary,.money-capabilities{grid-template-columns:1fr}", EXPERIENCE_CSS)

    def run_workspace(self, data=None, failure=False):
        # Execute the actual production renderer, not a separately maintained UI mock.
        node = "/usr/local/bin/node" if Path("/usr/local/bin/node").exists() else shutil.which("node")
        if not node:
            self.skipTest("Node is optional; runtime UI checks need Node")
        helper = EXPERIENCE_JS.split("      function workspaceMoney", 1)[1].split(
            "      moneyRefresh.addEventListener", 1
        )[0]
        program = r"""
class E {
  constructor(tag){this.tag=tag;this.children=[];this.dataset={};this.textContent='';this.disabled=false;}
  append(...items){this.children.push(...items);}
  replaceChildren(...items){this.children=items;}
  setAttribute(name,value){this[name]=value;}
}
function element(tag,text,cls){const e=new E(tag);if(text)e.textContent=text;return e;}
function collect(e){return [e.textContent,...e.children.map(collect)].flat();}
let moneyBusy=false;const moneyRefresh=new E('button'),moneyContent=new E('div'),moneyFeedback=new E('p'),moneyUpdated=new E('p');
const calls=[];
async function jsonRequest(path,...rest){calls.push({path,rest});if(FAILURE)throw new Error('offline');return DATA;}
""".replace("FAILURE", json.dumps(failure)).replace("DATA", json.dumps(data))
        program += "function workspaceMoney" + helper
        program += "\nrefreshMoney().then(()=>process.stdout.write(JSON.stringify({text:collect(moneyContent),feedback:moneyFeedback.textContent,state:moneyFeedback.dataset.state,disabled:moneyRefresh.disabled,calls})));"
        result = subprocess.run([node, "-e", program], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def workspace(self):
        return {
            "scope": "ARTIFICIAL_MONEY", "balance_minor": 500000,
            "protected_balance_minor": 100000, "available_above_reserve_minor": 400000,
            "upcoming_total_minor": 450000,
            "budget": {"committed_minor": 450000, "remaining_after_bills_minor": -50000, "shortfall_minor": 50000},
            "bills": [{"bill_reference": "BILL-1", "provider_name": "Electricity", "amount_minor": 450000,
                       "due_date": "2026-10-15", "payee_id": "power@upi", "status": "UNPAID_RECORD",
                       "reason": "No matching internal payment receipt; external payment status is unknown.",
                       "history_status": "AVAILABLE",
                       "previous_amount_minor": 300000}],
            "recent_runs": [{"run_id": "ff_recorded", "status": "HELD", "case_id": "changed_payee"}],
            "capabilities": [{"id": "resolution", "title": "Resolution", "status": "CONNECTOR_PENDING", "description": "No external biller connected"}],
            "coverage": {"bill_records_returned": 1, "limit": 100, "may_be_truncated": True},
            "limits": ["No real funds"],
        }

    def test_real_renderer_is_read_only_and_explains_reserve_shortfall(self):
        result = self.run_workspace(self.workspace())
        text = " ".join(result["text"])
        self.assertEqual(result["calls"], [{"path": "/api/friday/workspace", "rest": []}])
        self.assertEqual(result["state"], "ready")
        self.assertFalse(result["disabled"])
        self.assertIn("₹5,000.00", text)
        self.assertIn("exceed the amount above your reserve by ₹500.00", text)
        self.assertIn("not money reserved or paid", text)
        self.assertIn("Limited snapshot", text)
        self.assertIn("HELD", text)
        self.assertIn("CONNECTOR_PENDING", text)
        self.assertIn("Potential bill commitments (external status unknown)", text)
        self.assertIn("No matching internal receipt", text)
        self.assertIn("external payment status is unknown", text)
        self.assertNotIn("Upcoming unpaid", text)

    def test_missing_history_is_visible_without_a_previous_amount_claim(self):
        data = self.workspace()
        data["bills"][0]["history_status"] = "NOT_AVAILABLE"
        result = self.run_workspace(data)
        text = " ".join(result["text"])
        self.assertIn("Historical comparison unavailable", text)
        self.assertNotIn("Previous amount", text)

    def test_missing_and_negative_balances_are_not_claimed_as_available(self):
        data = self.workspace()
        data["balance_minor"] = -1
        data["available_above_reserve_minor"] = None
        result = self.run_workspace(data)
        self.assertGreaterEqual(result["text"].count("Not available"), 2)
        self.assertNotIn("₹-", " ".join(result["text"]))

    def test_empty_records_and_errors_do_not_show_success_or_stale_balance(self):
        data = self.workspace()
        data["bills"], data["recent_runs"], data["capabilities"] = [], [], []
        result = self.run_workspace(data)
        self.assertIn("No bill records", " ".join(result["text"]))
        self.assertIn("No recorded outcomes yet", " ".join(result["text"]))
        failed = self.run_workspace(data, failure=True)
        self.assertEqual(failed["text"], [""])
        self.assertEqual(failed["state"], "error")
        self.assertFalse(failed["disabled"])
        self.assertIn("No balance or successful action is assumed", failed["feedback"])

    def test_unexpected_scope_is_rejected_and_provider_text_is_not_html(self):
        data = self.workspace()
        data["scope"] = "LIVE_BANK"
        self.assertEqual(self.run_workspace(data)["state"], "error")
        data["scope"] = "ARTIFICIAL_MONEY"
        data["bills"][0]["provider_name"] = "<script>alert('x')</script>"
        result = self.run_workspace(data)
        self.assertIn(data["bills"][0]["provider_name"], result["text"])
        helper = EXPERIENCE_JS.split("const moneyView=view", 1)[1].split("moneyRefresh.addEventListener", 1)[0]
        self.assertNotIn("innerHTML", helper)
        self.assertNotIn("'POST'", helper)
        self.assertIn("moneyRefresh.disabled=true", helper)


if __name__ == "__main__":
    unittest.main()
