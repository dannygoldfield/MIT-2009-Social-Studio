from pathlib import Path
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
import tempfile
import threading
import unittest
import uuid

from PIL import ImageFont
from mit2009_studio import render, server


class BrandAudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_data = server.DATA
        server.DATA = Path(self.temp.name)
        server.initialize()
        self.http = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join()
        server.DATA = self.old_data
        self.temp.cleanup()

    def request(self, path, payload=None):
        connection = HTTPConnection('127.0.0.1', self.http.server_port)
        headers = {'X-Studio-Request': '1', 'Content-Type': 'application/json'}
        connection.request('GET' if payload is None else 'POST', path,
                           None if payload is None else json.dumps(payload), headers)
        response = connection.getresponse()
        result = response.status, response.read()
        connection.close()
        return result

    def test_outfit_is_bundled_and_asset_routes_stay_inside_brand_folder(self):
        self.assertEqual(ImageFont.truetype(render.font_path(), 32).getname(), ('Outfit', 'Bold'))
        status, body = self.request('/brand-2026/brand.json')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['year'], 2026)
        self.assertEqual(self.request('/brand-2026/Outfit-Bold.ttf')[0], 200)
        self.assertEqual(self.request('/brand-2026/%2e%2e/app.js')[0], 404)
        self.assertEqual(self.request('/brand-2026/not-an-asset')[0], 404)

    def test_audio_assessments_persist_without_touching_original_files(self):
        identity = uuid.uuid4().hex
        original = server.DATA / 'inputs' / 'unchanged.wav'
        original.write_bytes(b'original source audio')
        server.add_entry(dict(id=identity, file='inputs/unchanged.wav', kind='audio', role='source'))
        changes = dict(id=identity, audio_bucket='wildcard', assessment='maybe', notes='Try on a reveal.')
        self.assertEqual(self.request('/api/audio-item', changes)[0], 200)
        saved = server.lookup(identity)
        self.assertEqual(saved['audio_bucket'], 'wildcard')
        self.assertEqual(saved['assessment'], 'maybe')
        self.assertEqual(saved['notes'], changes['notes'])
        self.assertEqual(original.read_bytes(), b'original source audio')
        for bad in [dict(assessment='approved'), dict(audio_bucket='wrong'), dict(notes='x'*501)]:
            self.assertEqual(self.request('/api/audio-item', dict(id=identity, **bad))[0], 400)
        self.assertEqual(server.lookup(identity)['assessment'], 'maybe')


if __name__ == '__main__':
    unittest.main()
