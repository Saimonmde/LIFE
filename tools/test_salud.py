# SPDX-License-Identifier: AGPL-3.0-or-later
"""Salud HTTP, el zip de la fuente y un WebSocket que no se cae con basura."""
import asyncio, base64, hashlib, json, os, struct, unittest
import server as s

GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'


def frame(text):
    data = text.encode()
    mask = os.urandom(4)
    payload = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
    n = len(data)
    if n < 126:
        head = bytes([0x81, 0x80 | n])
    else:
        head = bytes([0x81, 0xFE]) + struct.pack('!H', n)
    return head + mask + payload


async def read_http(reader):
    raw = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), 5)
    head, _, _ = raw.partition(b'\r\n\r\n')
    lines = head.decode().split('\r\n')
    headers = {}
    for line in lines[1:]:
        k, _, v = line.partition(':')
        headers[k.strip().lower()] = v.strip()
    status = int(lines[0].split(' ', 2)[1])
    length = int(headers.get('content-length') or 0)
    body = await reader.readexactly(length) if length else b''
    return status, headers, body


async def read_ws(reader):
    b1, b2 = await asyncio.wait_for(reader.readexactly(2), 5)
    op, n = b1 & 0x0F, b2 & 0x7F
    if n == 126:
        n = struct.unpack('!H', await reader.readexactly(2))[0]
    elif n == 127:
        n = struct.unpack('!Q', await reader.readexactly(8))[0]
    payload = await reader.readexactly(n)
    return op, payload


class SaludTests(unittest.TestCase):
    def test_level_and_health_shape(self):
        self.assertEqual(s.clamp_level('no', 4), 4)
        self.assertEqual(s.clamp_level(-3, 1), 1)
        self.assertEqual(s.clamp_level(10**9, 1), 9999)
        body = s.health_payload()
        self.assertTrue(body['ok'])
        self.assertIn('playersOnline', body)
        self.assertEqual(body['service'], 'saimon-city')

    def test_routes_and_bad_socket(self):
        asyncio.run(self._routes())

    async def _routes(self):
        srv = await asyncio.start_server(s.handle, '127.0.0.1', 0)
        port = srv.sockets[0].getsockname()[1]
        try:
            for path, expect in (
                ('/healthz', 200),
                ('/health', 200),
                ('/', 302),
                ('/play/', 200),
                ('/movil/', 200),
                ('/privacidad', 200),
                ('/terminos', 200),
                ('/play/licencias.html', 200),
                ('/favicon.ico', 200),
                ('/legal/estilo.css', 200),
                ('/play/shell.js', 200),
                ('/play/shell.css', 200),
                ('/graphics/ui/sol.png', 200),
                ('/graphics/ui/luna.png', 200),
                ('/auth/providers', 200),
                ('/releases/saimoncity-fuente.zip', 302 if not os.path.isfile(os.path.join(s.ROOT, 'releases', 'saimoncity-fuente.zip')) else 200),
            ):
                status, headers, body = await self._get(port, path)
                self.assertEqual(status, expect, path)
                if path == '/health':
                    payload = json.loads(body)
                    self.assertTrue(payload['ok'])
                if path == '/healthz':
                    self.assertEqual(body, b'ok')
                if path == '/':
                    self.assertEqual(headers.get('location'), '/play/')
                if path == '/releases/saimoncity-fuente.zip' and status == 302:
                    self.assertTrue(headers.get('location', '').startswith('https://github.com/Saimonmde/LIFE'))
                if path == '/play/licencias.html':
                    self.assertIn(b'https://github.com/Saimonmde/LIFE', body)
                    self.assertNotIn(b'releases/saimoncity-fuente.zip', body)
            await self._garbage(port)
        finally:
            srv.close()
            await srv.wait_closed()

    async def _get(self, port, path):
        reader, writer = await asyncio.open_connection('127.0.0.1', port)
        writer.write(f'GET {path} HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n'.encode())
        await writer.drain()
        try:
            return await read_http(reader)
        finally:
            writer.close()

    async def _garbage(self, port):
        reader, writer = await asyncio.open_connection('127.0.0.1', port)
        key = base64.b64encode(os.urandom(16)).decode()
        writer.write((
            'GET /ws HTTP/1.1\r\nHost: 127.0.0.1\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
            f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n'
        ).encode())
        await writer.drain()
        status, headers, _ = await read_http(reader)
        self.assertEqual(status, 101)
        accept = base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()
        self.assertEqual(headers.get('sec-websocket-accept'), accept)
        for blob in ('{', '[]', '{"t":"move","x":"no","y":{}}', '{"t":"hello","level":"nope","name":"<script>"}', '{"t":"ping","c":1}'):
            writer.write(frame(blob))
        await writer.drain()
        seen = False
        for _ in range(6):
            op, payload = await read_ws(reader)
            if op != 1:
                continue
            msg = json.loads(payload)
            if msg.get('t') in ('welcome', 'pong'):
                seen = True
                break
        self.assertTrue(seen)
        writer.close()


if __name__ == '__main__':
    unittest.main()
