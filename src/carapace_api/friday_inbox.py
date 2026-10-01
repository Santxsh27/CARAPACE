"""Persistent, opt-in sandbox intake. Preparing a bill never executes it."""
import json
from datetime import datetime, timedelta, timezone

from carapace_core.financial_friday import FinancialGoal, FinancialEvidence, verify_financial_program
from carapace_integrations.financial_friday_fixtures import load_case


class FridayInbox:
    def __init__(self, service):
        self.service = service
        with service.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS friday_watch(tenant TEXT PRIMARY KEY, enabled INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS friday_inbox(
                    tenant TEXT, event_id TEXT, case_id TEXT, due_at TEXT, state TEXT,
                    result TEXT, PRIMARY KEY(tenant,event_id));
            ''')

    def watch(self, tenant, enabled):
        with self.service.connect() as db:
            db.execute('INSERT INTO friday_watch VALUES (?,?) ON CONFLICT(tenant) DO UPDATE SET enabled=excluded.enabled', (tenant, int(enabled)))
        return self.read(tenant)

    def arrive(self, tenant, case_id):
        # Stable upstream identity collapses repeated delivery of the same fixture.
        load_case(case_id)
        due = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        with self.service.connect() as db:
            db.execute('INSERT OR IGNORE INTO friday_inbox VALUES (?,?,?,?,?,?)',
                       (tenant, 'sample-' + case_id, case_id, due, 'QUEUED', '{}'))
        return self.read(tenant)

    def read(self, tenant):
        with self.service.connect() as db:
            setting = db.execute('SELECT enabled FROM friday_watch WHERE tenant=?', (tenant,)).fetchone()
            rows = db.execute('SELECT * FROM friday_inbox WHERE tenant=? ORDER BY rowid DESC', (tenant,)).fetchall()
        now = datetime.now(timezone.utc)
        return {'enabled': bool(setting and setting[0]), 'scope': 'Sandbox feed; in-app reminders only',
                'items': [dict(event_id=r['event_id'], case_id=r['case_id'], state=r['state'],
                               due_at=r['due_at'], reminder_due=(datetime.fromisoformat(r['due_at'])-now).total_seconds() <= 172800,
                               result=json.loads(r['result'])) for r in rows]}

    def tick(self):
        with self.service.connect() as db:
            rows = db.execute('SELECT i.* FROM friday_inbox i JOIN friday_watch w ON i.tenant=w.tenant WHERE w.enabled=1 AND i.state=? LIMIT 5', ('QUEUED',)).fetchall()
        for row in rows:
            # Claim atomically; a second worker cannot charge for the same model call.
            with self.service.connect() as db:
                claimed = db.execute('UPDATE friday_inbox SET state=? WHERE tenant=? AND event_id=? AND state=?',
                                     ('CHECKING', row['tenant'], row['event_id'], 'QUEUED')).rowcount
            if not claimed:
                continue
            try:
                case = load_case(row['case_id'])
                plan = self.service.planner.plan(case)
                proof = verify_financial_program(plan, FinancialGoal.model_validate(case['goal']), FinancialEvidence.model_validate(case['evidence']))
                result = {'mode': self.service.planner.mode, 'model': self.service.planner.model_name,
                          'explanation': plan.explanation, 'checks': proof,
                          'money_moved': False, 'message': 'Bill checked. Ready for your decision.' if proof['passed'] else 'Bill needs attention. No payment prepared.'}
                state = 'READY' if proof['passed'] else 'ATTENTION'
            except Exception as error:
                state, result = 'UNAVAILABLE', {'message': 'Could not finish checking this bill.', 'error_type': type(error).__name__, 'money_moved': False}
            with self.service.connect() as db:
                db.execute('UPDATE friday_inbox SET state=?, result=? WHERE tenant=? AND event_id=?',
                           (state, json.dumps(result), row['tenant'], row['event_id']))
