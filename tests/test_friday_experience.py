from __future__ import annotations

import unittest

from carapace_integrations.financial_friday_ui import FINANCIAL_FRIDAY_HTML
from carapace_integrations.friday_experience import EXPERIENCE_JS, EXPERIENCE_CSS


class FridayExperienceTests(unittest.TestCase):
    def test_navigation_is_in_the_real_app_not_a_separate_mock(self):
        for screen in ("home", "bill", "document", "activity", "demos", "settings"):
            self.assertIn(f'data-screen-link="{screen}"', FINANCIAL_FRIDAY_HTML)
        self.assertIn("const experience=", FINANCIAL_FRIDAY_HTML)
        self.assertIn("/api/friday/live-input", FINANCIAL_FRIDAY_HTML)
        self.assertIn("/api/friday/documents", FINANCIAL_FRIDAY_HTML)

    def test_hidden_screens_and_reduced_motion_are_explicit(self):
        self.assertIn(".friday-view[hidden]{display:none!important}", EXPERIENCE_CSS)
        self.assertIn("prefers-reduced-motion:reduce", EXPERIENCE_CSS)
        self.assertIn("focus-visible", EXPERIENCE_CSS)
        self.assertIn("aria-current", EXPERIENCE_JS)

    def test_one_task_at_a_time_and_unknown_outcomes_do_not_retry(self):
        self.assertIn("if(busy)", EXPERIENCE_JS)
        self.assertIn("Check its outcome before starting another", EXPERIENCE_JS)
        self.assertIn("Check activity before retrying any financial task", EXPERIENCE_JS)
        self.assertNotIn("setInterval", EXPERIENCE_JS)

    def test_saved_run_navigation_only_loads_existing_evidence(self):
        helper = EXPERIENCE_JS.split("async function openRun(id)", 1)[1].split("document.addEventListener", 1)[0]
        self.assertIn("/api/friday/runs/", helper)
        self.assertNotIn("'POST'", helper)
        self.assertIn("No payment was submitted", helper)

    def test_progress_is_derived_from_backend_results(self):
        self.assertIn("const originalRender=render", EXPERIENCE_JS)
        self.assertIn("r.status==='HELD'", EXPERIENCE_JS)
        self.assertIn("await fn()", EXPERIENCE_JS)
        self.assertNotIn("setTimeout", EXPERIENCE_JS)
        self.assertIn("awaiting verified result", EXPERIENCE_JS)
        self.assertIn("completedStatuses.includes(r.status)", EXPERIENCE_JS)
        self.assertIn("Attention · outcome not confirmed", EXPERIENCE_JS)
        self.assertIn("location.pathname+location.search+'#run'", FINANCIAL_FRIDAY_HTML)

    def test_cloud_monitor_removal_does_not_remove_navigation(self):
        import re
        html = re.sub(r"let watching=false;.*?(?=\$\('save-mandate'\))", "", FINANCIAL_FRIDAY_HTML, flags=re.S)
        self.assertIn("const experience=", html)
        self.assertNotIn("async function refreshInbox", html)

    def test_motion_and_outcome_styling_do_not_grant_authority(self):
        self.assertIn("rotateX(var(--rx", EXPERIENCE_CSS)
        self.assertIn("pointerleave", EXPERIENCE_JS)
        self.assertIn("reduced.matches||motionPreference==='off'", EXPERIENCE_JS)
        self.assertIn("friday-motion", EXPERIENCE_JS)
        self.assertIn("b.dataset.outcome", EXPERIENCE_JS)
        self.assertIn("Needs verification", EXPERIENCE_JS)
        self.assertIn("[data-state=\"attention\"]", EXPERIENCE_CSS)
        self.assertNotIn("requestAnimationFrame", EXPERIENCE_JS)

    def test_home_briefing_is_read_only_and_limited_to_real_recent_runs(self):
        helper = EXPERIENCE_JS.split("async function refreshBriefing()", 1)[1].split("const moneyView=view", 1)[0]
        self.assertIn("/api/friday/today", helper)
        self.assertIn("data.recent_runs||[]", helper)
        self.assertIn("most recent", helper)
        self.assertNotIn("'POST'", helper)
        self.assertIn("No task was submitted", helper)

    def test_guidance_and_activity_filters_are_accessible_and_non_financial(self):
        self.assertIn("guide.showModal()", EXPERIENCE_JS)
        self.assertIn("guideReturn?.isConnected", EXPERIENCE_JS)
        self.assertIn("Search recorded activity", EXPERIENCE_JS)
        self.assertIn("No matching outcomes", EXPERIENCE_JS)
        self.assertIn("e.target.closest('input,textarea,select", EXPERIENCE_JS)
        self.assertIn("function filterActivity()", EXPERIENCE_JS)

    def test_home_has_one_direct_request_and_discloses_saved_permission(self):
        self.assertIn("hero.querySelector('.hero-main').append(command)", EXPERIENCE_JS)
        self.assertIn("if(value){$('live-input').value=value;checkLive();}", EXPERIENCE_JS)
        self.assertIn("Allowed tasks may complete automatically", EXPERIENCE_JS)
        self.assertIn(".command-hints{display:none}", EXPERIENCE_CSS)

    def test_outcome_summary_uses_evidence_not_decorative_progress(self):
        self.assertIn("const originalSignalResult=showLiveResult", EXPERIENCE_JS)
        self.assertIn("data.state==='READY'", EXPERIENCE_JS)
        self.assertIn("Needs approval · no payment yet", EXPERIENCE_JS)
        self.assertIn("No success is assumed", EXPERIENCE_JS)
        self.assertIn("aria-atomic", EXPERIENCE_JS)
        self.assertIn("evidenceDetails.insertBefore($('briefing')", EXPERIENCE_JS)
        self.assertIn("$('verdict').hidden=true", EXPERIENCE_JS)


if __name__ == "__main__":
    unittest.main()
