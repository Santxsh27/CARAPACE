"""Unseen statement data is parsed exactly without models or payments."""
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from carapace_api.config import Settings
from carapace_api.factory import create_app
from carapace_core.friday_statement import analyze_statement
from carapace_integrations.friday_cloud_web import ROUTES
import re


class StatementTests(unittest.TestCase):
    def test_arbitrary_cashflow_and_repeat_candidates(self):
        data = analyze_statement('Date,Description,Debit,Credit\n2026-09-30,Salary,,50000\n01/10/2026,Groceries,1456.78,\n01/10/2026,Groceries,1456.78,\n02/10/2026,Rent,"12,000.00",\n')
        self.assertEqual(data['totals'], {'money_in_minor': 5000000,
                         'money_out_minor': 1491356, 'net_flow_minor': 3508644})
        self.assertEqual(data['transaction_count'], 4)
        self.assertEqual(data['repeated_rows'][0]['count'], 2)
        self.assertEqual(len(data['monthly']), 2)
        self.assertFalse(data['money_moved'])
        self.assertFalse(data['raw_file_stored'])
        self.assertFalse(data['sent_to_ai'])

    def test_ambiguous_invalid_rows_rejected_not_silently_skipped(self):
        for row in ('2026-10-01,X,10,20', '2026-10-01,X,-10,',
                    '2026-10-01,X,10.001,', '2026-02-30,X,10,',
                    '2026-10-01,X,0,0', '2026-10-01,X,10',
                    '2026-10-01,X,NaN,', '2026-10-01,X,10,,extra'):
            with self.subTest(row=row), self.assertRaises(ValueError):
                analyze_statement('date,description,debit,credit\n'+row+'\n')

    def test_headers_limits_and_indian_grouping(self):
        data = analyze_statement('\ufeff Date ,Description,Debit,Credit\n10-10-2026,Tax,"₹1,23,456.78",\n')
        self.assertEqual(data['totals']['money_out_minor'], 12345678)
        for text in ('date,description,debit,credit\n', 'date,date,debit,credit\n',
                     'date,description,amount\n', 'x' * (1024 * 1024 + 1)):
            with self.assertRaises(ValueError):
                analyze_statement(text)
        with self.assertRaises(ValueError):
            analyze_statement('date,description,debit,credit\n' + '2026-10-10,X,1,\n' * 5001)
        with self.assertRaises(ValueError):
            analyze_statement('date,description,debit,credit,currency\n2026-10-10,X,10,,USD\n')

    def test_api_authenticated_and_balance_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(Settings(environment='test', database_path=Path(tmp)/'db',
                                     tenant_keys={'one': 'secret'}, ai_provider='local'))
            with TestClient(app) as client:
                path = '/v1/friday/statements/analyze'
                headers = {'X-Carapace-Tenant': 'one', 'X-Carapace-API-Key': 'secret'}
                body = {'csv_text': 'date,description,debit,credit\n2026-10-10,Unknown shop,123.45,\n'}
                self.assertNotEqual(client.post(path, json=body).status_code, 200)
                before = client.get('/v1/friday/mandate', headers=headers).json()
                result = client.post(path, json=body, headers=headers)
                self.assertEqual(result.status_code, 200, result.text)
                self.assertEqual(result.json()['totals']['money_out_minor'], 12345)
                self.assertEqual(client.get('/v1/friday/mandate', headers=headers).json(), before)
                self.assertEqual(client.post(path, json={'csv_text': 'bad'}, headers=headers).status_code, 422)
                self.assertEqual(client.post(path, json={**body, 'pay': True}, headers=headers).status_code, 422)
        self.assertIsNotNone(re.fullmatch(ROUTES['POST'], 'statements/analyze'))
