import pytest

from app.services.encryption_service import decrypt, encrypt


def test_encrypt_decrypt_roundtrip(monkeypatch):
    import base64
    key = base64.urlsafe_b64encode(b"x" * 32).decode()
    monkeypatch.setattr("app.services.encryption_service.settings.encryption_key", key)
    plain = "secret token 123"
    cipher = encrypt(plain)
    assert cipher != plain
    assert decrypt(cipher) == plain


def test_decrypt_wrong_key_fails(monkeypatch):
    import base64
    key = base64.urlsafe_b64encode(b"x" * 32).decode()
    monkeypatch.setattr("app.services.encryption_service.settings.encryption_key", key)
    cipher = encrypt("secret")
    monkeypatch.setattr("app.services.encryption_service.settings.encryption_key", base64.urlsafe_b64encode(b"y" * 32).decode())
    with pytest.raises(ValueError, match="Decryption failed"):
        decrypt(cipher)


def test_encrypt_empty_key_raises(monkeypatch):
    monkeypatch.setattr("app.services.encryption_service.settings.encryption_key", "")
    with pytest.raises(ValueError, match="ENCRYPTION_KEY"):
        encrypt("x")
