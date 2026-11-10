import base64
import os

import pytest

from app.ops import backup as bk

KEY = base64.b64encode(os.urandom(32)).decode()


def test_encrypt_round_trip_including_multi_chunk_and_empty():
    for size in (0, 10, bk.CHUNK + 5, 3 * bk.CHUNK):
        data = os.urandom(size)
        assert bk.decrypt(bk.encrypt(data, KEY), KEY) == data


def test_wrong_key_and_tampering_are_rejected():
    blob = bk.encrypt(b"student data", KEY)
    with pytest.raises(bk.BackupError, match="decrypt"):
        bk.decrypt(blob, base64.b64encode(os.urandom(32)).decode())
    tampered = bytearray(blob)
    tampered[-1] ^= 1
    with pytest.raises(bk.BackupError, match="decrypt"):
        bk.decrypt(bytes(tampered), KEY)
    with pytest.raises(bk.BackupError, match="not a ZENITH"):
        bk.decrypt(b"hello", KEY)


def test_missing_or_short_key_is_an_error():
    with pytest.raises(bk.BackupError, match="BACKUP_KEY"):
        bk.encrypt(b"x", None)
    with pytest.raises(bk.BackupError, match="32"):
        bk.encrypt(b"x", base64.b64encode(b"short").decode())


def test_plaintext_never_appears_in_the_encrypted_file():
    secret = b"Asha Kumar is in Class 7B"
    assert secret not in bk.encrypt(secret * 100, KEY)


def test_backup_and_restore_refuse_dangerous_schemas():
    with pytest.raises(bk.BackupError, match="legacy public"):
        bk.dump("public")
    with pytest.raises(bk.BackupError, match="Refusing to restore"):
        bk.restore(b"", "public")
    with pytest.raises(bk.BackupError, match="Refusing to restore"):
        bk.restore(b"", "zenith_test")     # the schema the app is currently pointed at


def test_dump_and_unpack_a_real_schema(db):
    from tests.conftest import make_profile
    make_profile(db, "student")
    archive, manifest = bk.dump()
    meta, files = bk._unpack(archive)
    rows = {t["name"]: t["rows"] for t in meta["tables"]}
    assert rows["profiles"] == 1 and rows["boards"] == 1 and manifest["alembic_revision"] == "003"
    assert "profiles.bin" in files
    flipped = bytearray(archive)
    with pytest.raises(Exception):
        bk._unpack(bytes(flipped[: len(flipped) // 2]))   # a truncated backup must not load silently
