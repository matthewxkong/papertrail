import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from server import Store


ROOT = Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
    def test_offline_tasks(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'tasks.db'
            store = Store(database)
            expected = store.task_list('alex', {'status': 'open', 'limit': 1})
            store.db.close()
            result = self.run_cli(database, 'tasks', '--status', 'open', '--limit', '1')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), expected)

    def run_cli(self, database, *args):
        return subprocess.run([sys.executable, 'cli.py', '--db', str(database), '--actor', 'alex', *args],
                              cwd=ROOT, capture_output=True, text=True, encoding='utf-8')

    def test_missing_database_is_reported_without_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'missing.sqlite3'
            result = self.run_cli(database, 'export')
            self.assertEqual(result.returncode, 2)
            self.assertIn('Papertrail:', result.stderr)
            self.assertFalse(database.exists())

    def test_unicode_export_round_trips_and_query_stays_scoped(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'notes.sqlite3'
            store = Store(database)
            store.mutate('alex', 'save', {'title': 'Résumé 中文', 'body': 'Private matériel', 'visibility': 'private'})
            store.db.close()
            result = self.run_cli(database, 'export')
            self.assertEqual(result.returncode, 0, result.stderr)
            exported = json.loads(result.stdout)
            self.assertIn('Résumé 中文', [doc['title'] for doc in exported['documents']])
            self.assertEqual(self.run_cli(database, 'query', 'field equipment').returncode, 0)
            query = json.loads(self.run_cli(database, 'query', 'field equipment').stdout)
            self.assertEqual(query['total'], 0)


if __name__ == '__main__':
    unittest.main()
