import http.client
from http.server import HTTPServer
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import Handler, Store


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


class HTTPWorkspaceTests(unittest.TestCase):
    def test_rejected_host_does_not_wait_for_an_unsent_request_body(self):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        try:
            connection.putrequest('POST', '/api/ask', skip_host=True)
            connection.putheader('Host', 'attacker.example')
            connection.putheader('Content-Length', '100000')
            connection.endheaders()
            response = connection.getresponse()
            self.assertEqual(response.status, 403)
            self.assertIn('error', json.loads(response.read()))
        finally:
            connection.close()

    def test_json_responses_declare_their_encoded_body_length(self):
        cases = [('GET', '/api/health', None, {}, 200),
                 ('POST', '/api/ask', b'{"query":"launch"}',
                  {'Host': 'attacker.example', 'Content-Type': 'application/json'}, 403),
                 ('POST', '/api/ask', b'{"query":"launch"}', {'Content-Type': 'text/plain'}, 400)]
        for method, route, body, headers, status in cases:
            with self.subTest(status=status):
                connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
                try:
                    connection.request(method, route, body, headers)
                    response = connection.getresponse()
                    raw = response.read()
                    self.assertEqual(response.status, status)
                    self.assertEqual(response.getheader('Content-Length'), str(len(raw)))
                    self.assertIsInstance(json.loads(raw), dict)
                finally:
                    connection.close()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.server = HTTPServer(('127.0.0.1', 0), QuietHandler)
        self.server.store = Store(Path(self.temp.name) / 'http.db')
        self.server.sessions = {}
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()

    def tearDown(self):
        self.server.shutdown()
        self.worker.join()
        self.server.server_close()
        self.server.store.db.close()
        self.temp.cleanup()

    def request(self, route, data=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        request_headers = {'Content-Type': 'application/json'}
        request_headers.update(headers or {})
        body = data if isinstance(data, bytes) else json.dumps(data).encode() if data is not None else None
        connection.request('POST' if body is not None else 'GET', route, body, request_headers)
        response = connection.getresponse()
        raw = response.read()
        status = response.status
        connection.close()
        return status, json.loads(raw)

    def test_foreign_and_malformed_hosts_rejected_on_reads_and_writes(self):
        for host in ('attacker.example', '127.0.0.1.evil:8762', 'localhost', '127.0.0.1:1', '[::1]:bad'):
            self.assertEqual(self.request('/api/health', headers={'Host': host})[0], 403)
            self.assertEqual(self.request('/api/ask', {'query': 'launch'}, {'Host': host})[0], 403)
        self.assertEqual(self.request('/api/health', headers={'Host': 'localhost:' + str(self.server.server_port)})[0], 200)

    def test_deep_duplicate_unknown_and_wrong_content_type_are_json_errors(self):
        for body in (b'[' * 1500 + b'0' + b']' * 1500, b'{"query":"launch","query":"field"}', b'{"query":"launch","owner":"jules"}'):
            status, data = self.request('/api/ask', body)
            self.assertEqual(status, 400)
            self.assertIsInstance(data['error'], str)
        self.assertEqual(self.request('/api/ask', {'query': 'launch'}, {'Content-Type': 'text/plain'})[0], 400)
        self.assertEqual(self.request('/api/identity', {'actor': []})[0], 400)
        self.assertEqual(self.request('/ask', {'query': 'launch'})[0], 400)
        self.assertEqual(self.request('/api/health')[0], 200)
