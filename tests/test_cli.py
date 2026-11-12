import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from server import Store


ROOT = Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
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

    def test_query_pages_are_stable_scoped_and_do_not_change_database(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'notes.sqlite3'
            store = Store(database)
            for index in range(4):
                store.mutate('alex', 'save', {'title': f'Paginationmarker {index}',
                             'body': 'Paginationmarker evidence.', 'visibility': 'private'})
            store.mutate('sam', 'save', {'title': 'Paginationmarker hidden',
                         'body': 'Paginationmarker private.', 'visibility': 'private'})
            store.db.close()
            before = database.read_bytes()
            pages = []
            for offset in (0, 2):
                result = self.run_cli(database, 'query', 'Paginationmarker', '--limit', '2',
                                      '--offset', str(offset))
                self.assertEqual(result.returncode, 0, result.stderr)
                page = json.loads(result.stdout)
                self.assertEqual((page['total'], page['offset']), (4, offset))
                pages.extend(source['id'] for source in page['sources'])
            self.assertEqual(len(pages), 4)
            self.assertEqual(len(set(pages)), 4)
            for offset in ('-1', '100001'):
                invalid = self.run_cli(database, 'query', 'Paginationmarker', '--offset', offset)
                self.assertEqual(invalid.returncode, 2)
                self.assertEqual(invalid.stdout, '')
                self.assertIn('Offset must be', invalid.stderr)
            self.assertEqual(database.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
