"""Persistent, opt-in sandbox intake. Preparing a bill never executes it."""
import json
import time
from uuid import uuid4
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
            columns = {row['name'] for row in db.execute('PRAGMA table_info(friday_inbox)')}
            for name, definition in [('lease_until', 'REAL NOT NULL DEFAULT 0'),
                                     ('claim_id', "TEXT NOT NULL DEFAULT ''"),
                                     ('attempts', 'INTEGER NOT NULL DEFAULT 0')]:
                if name not in columns:
                    db.execute(f'ALTER TABLE friday_inbox ADD COLUMN {name} {definition}')

    def watch(self, tenant, enabled):
        with self.service.connect() as db:
            db.execute('INSERT INTO friday_watch VALUES (?,?) ON CONFLICT(tenant) DO UPDATE SET enabled=excluded.enabled', (tenant, int(enabled)))
        return self.read(tenant)

    def arrive(self, tenant, case_id):
        # Stable upstream identity collapses repeated delivery of the same fixture.
        load_case(case_id)
        due = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        with self.service.connect() as db:
            db.execute('INSERT OR IGNORE INTO friday_inbox (tenant,event_id,case_id,due_at,state,result) VALUES (?,?,?,?,?,?)',
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

    def retry(self, tenant, event_id):
        with self.service.connect() as db:
            changed = db.execute("UPDATE friday_inbox SET state='QUEUED', result='{}', lease_until=0 WHERE tenant=? AND event_id=? AND state='UNAVAILABLE' AND attempts<3",
                                 (tenant, event_id)).rowcount
        if not changed:
            raise ValueError('Check cannot be retried: missing, still active, or three-attempt limit reached.')
        return self.read(tenant)

    def tick(self):
        with self.service.connect() as db:
            # Expired claims can be reclaimed after a process restart. A token
            # prevents a slow former worker from overwriting the newer result.
            db.execute("UPDATE friday_inbox SET state='UNAVAILABLE', result=? WHERE state='CHECKING' AND lease_until<? AND attempts>=3",
                       (json.dumps({'message': 'Check interrupted three times. Review required.', 'money_moved': False}), time.time()))
            db.execute("UPDATE friday_inbox SET state='QUEUED' WHERE state='CHECKING' AND lease_until<? AND attempts<3", (time.time(),))
            rows = db.execute('SELECT i.* FROM friday_inbox i JOIN friday_watch w ON i.tenant=w.tenant WHERE w.enabled=1 AND i.state=? LIMIT 5', ('QUEUED',)).fetchall()
        for row in rows:
            claim_id = uuid4().hex
            with self.service.connect() as db:
                claimed = db.execute("UPDATE friday_inbox SET state='CHECKING', claim_id=?, lease_until=?, attempts=attempts+1 WHERE tenant=? AND event_id=? AND state='QUEUED' AND attempts<3 AND EXISTS(SELECT 1 FROM friday_watch WHERE tenant=? AND enabled=1)",
                                     (claim_id, time.time()+180, row['tenant'], row['event_id'], row['tenant'])).rowcount
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
                db.execute("UPDATE friday_inbox SET state=?, result=?, lease_until=0 WHERE tenant=? AND event_id=? AND claim_id=? AND state='CHECKING'",
                           (state, json.dumps(result), row['tenant'], row['event_id'], claim_id))
