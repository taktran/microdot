import asyncio
import sys
import unittest
from microdot import Microdot
from microdot.websocket import with_websocket, WebSocket
from microdot.test_client import TestClient


class TestWebSocket(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if hasattr(asyncio, 'set_event_loop'):
            asyncio.set_event_loop(asyncio.new_event_loop())
        cls.loop = asyncio.get_event_loop()

    def _run(self, coro):
        return self.loop.run_until_complete(coro)

    def test_websocket_echo(self):
        app = Microdot()

        @app.route('/echo')
        @with_websocket
        async def index(req, ws):
            while True:
                data = await ws.receive()
                await ws.send(data)

        results = []

        def ws():
            data = yield 'hello'
            results.append(data)
            data = yield b'bye'
            results.append(data)
            data = yield b'*' * 300
            results.append(data)
            data = yield b'+' * 65537
            results.append(data)

        client = TestClient(app)
        res = self._run(client.websocket('/echo', ws))
        self.assertIsNone(res)
        self.assertEqual(results, ['hello', b'bye', b'*' * 300, b'+' * 65537])

    @unittest.skipIf(sys.implementation.name == 'micropython',
                     'no support for async generators in MicroPython')
    def test_websocket_echo_async_client(self):
        app = Microdot()

        @app.route('/echo')
        @with_websocket
        async def index(req, ws):
            while True:
                data = await ws.receive()
                await ws.send(data)

        results = []

        async def ws():
            data = yield 'hello'
            results.append(data)
            data = yield b'bye'
            results.append(data)
            data = yield b'*' * 300
            results.append(data)
            data = yield b'+' * 65537
            results.append(data)

        client = TestClient(app)
        res = self._run(client.websocket('/echo', ws))
        self.assertIsNone(res)
        self.assertEqual(results, ['hello', b'bye', b'*' * 300, b'+' * 65537])

    def test_bad_websocket_request(self):
        app = Microdot()

        @app.route('/echo')
        @with_websocket
        def index(req, ws):
            return 'hello'

        client = TestClient(app)
        res = self._run(client.get('/echo'))
        self.assertEqual(res.status_code, 400)
        res = self._run(client.get('/echo', headers={'Connection': 'Upgrade'}))
        self.assertEqual(res.status_code, 400)
        res = self._run(client.get('/echo', headers={'Connection': 'foo'}))
        self.assertEqual(res.status_code, 400)
        res = self._run(client.get('/echo', headers={'Upgrade': 'websocket'}))
        self.assertEqual(res.status_code, 400)
        res = self._run(client.get('/echo', headers={'Upgrade': 'bar'}))
        self.assertEqual(res.status_code, 400)
        res = self._run(client.get('/echo', headers={'Connection': 'Upgrade',
                                                     'Upgrade': 'websocket'}))
        self.assertEqual(res.status_code, 400)
        res = self._run(client.get(
            '/echo', headers={'Sec-WebSocket-Key': 'xxx'}))
        self.assertEqual(res.status_code, 400)

    def test_process_websocket_frame(self):
        ws = WebSocket(None)
        ws.closed = True

        self.assertEqual(ws._process_websocket_frame(WebSocket.TEXT, b'foo'),
                         (None, 'foo'))
        self.assertEqual(ws._process_websocket_frame(WebSocket.BINARY, b'foo'),
                         (None, b'foo'))
        self.assertRaises(OSError, ws._process_websocket_frame,
                          WebSocket.CLOSE, b'')
        self.assertEqual(ws._process_websocket_frame(WebSocket.PING, b'foo'),
                         (WebSocket.PONG, b'foo'))
        self.assertEqual(ws._process_websocket_frame(WebSocket.PONG, b'foo'),
                         (None, None))
