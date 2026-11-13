# SPDX-License-Identifier: AGPL-3.0-or-later
"""Ed25519 con hashlib, sin pip. Sirve para firmar certificados educativos de SMC.

La clave privada no se imprime ni se versiona. Quien verifica sólo necesita la pública.
"""
import hashlib

Q = 2 ** 255 - 19
L = 2 ** 252 + 27742317777372353535851937790883648493
D = (-121665 * pow(121666, Q - 2, Q)) % Q
I = pow(2, (Q - 1) // 4, Q)
BY = (4 * pow(5, Q - 2, Q)) % Q


def _sha(data):
    return hashlib.sha512(data).digest()


def _xrecover(y):
    xx = (y * y - 1) * pow(D * y * y + 1, Q - 2, Q) % Q
    x = pow(xx, (Q + 3) // 8, Q)
    if (x * x - xx) % Q != 0:
        x = (x * I) % Q
    if x % 2 != 0:
        x = Q - x
    return x


BX = _xrecover(BY)
B = (BX % Q, BY % Q, 1, (BX * BY) % Q)


def _edwards(p, r):
    x1, y1, z1, t1 = p
    x2, y2, z2, t2 = r
    a = (y1 - x1) * (y2 - x2) % Q
    b = (y1 + x1) * (y2 + x2) % Q
    c = (2 * t1 * t2 * D) % Q
    d = (2 * z1 * z2) % Q
    e = (b - a) % Q
    f = (d - c) % Q
    g = (d + c) % Q
    h = (b + a) % Q
    return (e * f % Q, g * h % Q, f * g % Q, e * h % Q)


def _scalarmult(point, exponent):
    exponent %= L
    result = (0, 1, 1, 0)
    for shift in range(255, -1, -1):
        result = _edwards(result, result)
        if (exponent >> shift) & 1:
            result = _edwards(result, point)
    return result


def _bit(blob, index):
    return (blob[index // 8] >> (index % 8)) & 1


def _encode_int(value):
    return int(value).to_bytes(32, 'little')


def _decode_int(blob):
    return int.from_bytes(blob, 'little')


def _encode_point(point):
    x, y, z, _t = point
    inv = pow(z, Q - 2, Q)
    x = (x * inv) % Q
    y = (y * inv) % Q
    raw = bytearray(_encode_int(y))
    raw[31] |= (x & 1) << 7
    return bytes(raw)


def _decode_point(blob):
    y = _decode_int(blob) & ((1 << 255) - 1)
    x = _xrecover(y)
    if (x & 1) != ((blob[31] >> 7) & 1):
        x = Q - x
    point = (x, y, 1, (x * y) % Q)
    if not _on_curve(point):
        raise ValueError('punto Ed25519 inválido')
    return point


def _on_curve(point):
    x, y, z, t = point
    return (
        z % Q != 0
        and (x * y - z * t) % Q == 0
        and (y * y - x * x - z * z - D * t * t) % Q == 0
    )


def _affine(point):
    x, y, z, _t = point
    inv = pow(z, Q - 2, Q)
    return ((x * inv) % Q, (y * inv) % Q)


def _secret_scalar(seed):
    digest = _sha(seed)
    value = 2 ** 254 + sum(2 ** i * _bit(digest, i) for i in range(3, 254))
    return digest, value


def _hint(data):
    digest = _sha(data)
    return sum(2 ** i * _bit(digest, i) for i in range(512))


def publickey(seed):
    """Devuelve los 32 bytes de la clave pública a partir de una semilla de 32 bytes."""
    if len(seed) != 32:
        raise ValueError('la semilla Ed25519 mide 32 bytes')
    _digest, scalar = _secret_scalar(seed)
    return _encode_point(_scalarmult(B, scalar))


def sign(message, seed):
    """Firma bytes. Devuelve 64 bytes (R || S)."""
    if isinstance(message, str):
        message = message.encode('utf-8')
    pubkey = publickey(seed)
    digest, scalar = _secret_scalar(seed)
    nonce = _hint(digest[32:] + message)
    commitment = _encode_point(_scalarmult(B, nonce))
    challenge = _hint(commitment + pubkey + message)
    signature_s = (nonce + challenge * scalar) % L
    return commitment + _encode_int(signature_s)


def verify(signature, message, pubkey):
    """True si la firma Ed25519 corresponde al mensaje y a la clave pública."""
    if isinstance(message, str):
        message = message.encode('utf-8')
    if not isinstance(signature, (bytes, bytearray)) or len(signature) != 64:
        return False
    if not isinstance(pubkey, (bytes, bytearray)) or len(pubkey) != 32:
        return False
    try:
        commitment = _decode_point(signature[:32])
        point = _decode_point(bytes(pubkey))
    except (ValueError, OverflowError):
        return False
    signature_s = _decode_int(signature[32:])
    if signature_s >= L:
        return False
    challenge = _hint(bytes(signature[:32]) + bytes(pubkey) + message)
    left = _affine(_scalarmult(B, signature_s))
    right = _affine(_edwards(commitment, _scalarmult(point, challenge)))
    return left == right
