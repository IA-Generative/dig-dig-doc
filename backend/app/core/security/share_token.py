import hashlib
import hmac
import secrets

from app.config import SharingSettings

_settings = SharingSettings()


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    # HMAC plutôt qu'un simple sha256 : sans la clé secrète du serveur, un
    # accès à la base ne suffit pas à forger un jeton qui matchera un hash.
    return hmac.new(_settings.SHARE_SECRET_KEY.encode(), token.encode(), hashlib.sha256).hexdigest()
