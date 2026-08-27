"""
STATUS: stub, Day 6. Razorpay signs every webhook payload with your webhook secret
(HMAC-SHA256). Verify as the FIRST line of the handler, before touching the payload at all —
otherwise the execute layer is an open door for anyone who finds the endpoint URL to trigger
fake recovery actions or spend the WhatsApp/voice budget.

Real implementation (once WEBHOOK_SECRET is in env config):

    import hmac, hashlib

    def verify_signature(body: bytes, signature: str, secret: str) -> bool:
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
"""


import hmac
import hashlib

def verify_signature(body: bytes, signature: str, secret: str) -> bool:
    if not secret:
        return False
    expected = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

