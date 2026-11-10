"""Encrypted database backups to Backblaze B2.

No pg_dump needed: every table in the ZENITH schema is streamed with PostgreSQL's binary COPY (types are preserved
exactly), packed with a manifest, compressed, encrypted with AES-256-GCM (key stays with you) and uploaded to a private
bucket. `restore` loads a backup into an empty schema built by the same migration, so a backup is only trusted once it
has been verified.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import os
import struct
import tarfile
from datetime import datetime, timezone

import httpx
import psycopg
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from psycopg import sql

from app.core.config import settings
from app.models import Base

MAGIC = b"ZBK1"
CHUNK = 1 << 20
PREFIX = "backups/"
MAX_SINGLE_UPLOAD = 4_500_000_000


class BackupError(RuntimeError):
    pass


# ---- encryption --------------------------------------------------------------------------------
def make_key() -> str:
    return base64.b64encode(os.urandom(32)).decode()


def _key(b64: str | None) -> bytes:
    if not b64:
        raise BackupError("BACKUP_KEY is not set. Create one with `python -m app.cli backup-key` and keep a copy somewhere safe.")
    k = base64.b64decode(b64)
    if len(k) != 32:
        raise BackupError("BACKUP_KEY must be 32 random bytes, base64 encoded.")
    return k


def encrypt(data: bytes, key_b64: str | None) -> bytes:
    aes = AESGCM(_key(key_b64))
    out = bytearray(MAGIC)
    for i in range(0, max(len(data), 1), CHUNK):
        nonce = os.urandom(12)
        ct = aes.encrypt(nonce, data[i:i + CHUNK], MAGIC)
        out += struct.pack(">I", len(ct)) + nonce + ct
    return bytes(out)


def decrypt(blob: bytes, key_b64: str | None) -> bytes:
    if not blob.startswith(MAGIC):
        raise BackupError("This is not a ZENITH backup file.")
    aes, pos, out = AESGCM(_key(key_b64)), len(MAGIC), bytearray()
    while pos < len(blob):
        (n,) = struct.unpack(">I", blob[pos:pos + 4])
        nonce, ct = blob[pos + 4:pos + 16], blob[pos + 16:pos + 16 + n]
        try:
            out += aes.decrypt(nonce, ct, MAGIC)
        except Exception as exc:  # noqa: BLE001 - wrong key or tampered file
            raise BackupError("Could not decrypt: wrong key, or the file was changed.") from exc
        pos += 16 + n
    return bytes(out)


# ---- dump / restore ----------------------------------------------------------------------------
def _dsn() -> str:
    return settings.DATABASE_URL.replace("postgresql+psycopg://", "postgresql://", 1)


def _tables() -> list[str]:
    return [t.name for t in Base.metadata.sorted_tables] + ["alembic_version"]


def dump(schema: str | None = None) -> tuple[bytes, dict]:
    """Return (tar.gz bytes, manifest). Reads one consistent snapshot."""
    schema = schema or settings.DB_SCHEMA
    if schema == "public":
        raise BackupError("Refusing to back up the legacy public schema with this tool.")
    tar_buf = io.BytesIO()
    tables_meta = []
    with psycopg.connect(_dsn(), autocommit=False) as conn, tarfile.open(fileobj=tar_buf, mode="w") as tar:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        revision = conn.execute(sql.SQL("SELECT version_num FROM {}.alembic_version").format(sql.Identifier(schema))).fetchone()[0]
        present = {r[0] for r in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = %s", (schema,)).fetchall()}
        for name in (t for t in _tables() if t in present):      # a schema one migration behind the code is still backed up
            ident = sql.SQL("{}.{}").format(sql.Identifier(schema), sql.Identifier(name))
            rows = conn.execute(sql.SQL("SELECT count(*) FROM {}").format(ident)).fetchone()[0]
            buf = io.BytesIO()
            with conn.cursor().copy(sql.SQL("COPY {} TO STDOUT (FORMAT binary)").format(ident)) as cp:
                for chunk in cp:
                    buf.write(bytes(chunk))
            data = buf.getvalue()
            info = tarfile.TarInfo(f"{name}.bin")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
            tables_meta.append({"name": name, "rows": rows, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        conn.rollback()
        manifest = {"format": 1, "schema": schema, "alembic_revision": revision, "created_at": datetime.now(timezone.utc).isoformat(), "tables": tables_meta}
        mj = json.dumps(manifest, indent=1).encode()
        info = tarfile.TarInfo("manifest.json")
        info.size = len(mj)
        tar.addfile(info, io.BytesIO(mj))
    return gzip.compress(tar_buf.getvalue(), 6), manifest


def _unpack(archive_gz: bytes) -> tuple[dict, dict[str, bytes]]:
    with tarfile.open(fileobj=io.BytesIO(gzip.decompress(archive_gz)), mode="r") as tar:
        files = {m.name: tar.extractfile(m).read() for m in tar.getmembers()}
    manifest = json.loads(files.pop("manifest.json"))
    for t in manifest["tables"]:
        if hashlib.sha256(files[f"{t['name']}.bin"]).hexdigest() != t["sha256"]:
            raise BackupError(f"Table {t['name']} failed its checksum. The backup is damaged.")
    return manifest, files


def restore(archive_gz: bytes, target_schema: str) -> dict:
    """Load a backup into an EMPTY schema that already has the tables (run `alembic upgrade head` with DB_SCHEMA=target first)."""
    if target_schema in ("public", settings.DB_SCHEMA):
        raise BackupError("Refusing to restore into public or the live schema. Restore into a new schema, check it, then decide.")
    manifest, files = _unpack(archive_gz)
    counts = {}
    with psycopg.connect(_dsn(), autocommit=False) as conn:
        rev = conn.execute(sql.SQL("SELECT version_num FROM {}.alembic_version").format(sql.Identifier(target_schema))).fetchone()[0]
        if rev != manifest["alembic_revision"]:
            raise BackupError(f"Schema version {rev} does not match the backup ({manifest['alembic_revision']}).")
        for t in manifest["tables"]:
            ident = sql.SQL("{}.{}").format(sql.Identifier(target_schema), sql.Identifier(t["name"]))
            if t["name"] == "alembic_version":
                continue
            if conn.execute(sql.SQL("SELECT count(*) FROM {}").format(ident)).fetchone()[0]:
                raise BackupError(f"{t['name']} is not empty in {target_schema}.")
            with conn.cursor().copy(sql.SQL("COPY {} FROM STDIN (FORMAT binary)").format(ident)) as cp:
                cp.write(files[f"{t['name']}.bin"])
            counts[t["name"]] = conn.execute(sql.SQL("SELECT count(*) FROM {}").format(ident)).fetchone()[0]
            if counts[t["name"]] != t["rows"]:
                raise BackupError(f"{t['name']}: restored {counts[t['name']]} rows, expected {t['rows']}.")
        conn.commit()
    return {"schema": target_schema, "tables": len(counts), "rows": sum(counts.values())}


# ---- Backblaze B2 (native API) -----------------------------------------------------------------
class B2:
    def __init__(self):
        key_id, app_key, self.bucket = settings.B2_KEY_ID, settings.B2_APP_KEY, settings.B2_BUCKET
        if not (key_id and app_key and self.bucket):
            raise BackupError("Backblaze is not configured: set B2_KEY_ID, B2_APP_KEY (or BACK_BLAZE_API_KEY) and B2_BUCKET.")
        self.c = httpx.Client(timeout=120)
        r = self.c.get("https://api.backblazeb2.com/b2api/v3/b2_authorize_account", headers={"Authorization": "Basic " + base64.b64encode(f"{key_id}:{app_key}".encode()).decode()})
        if r.status_code != 200:
            raise BackupError("Backblaze refused the key. Check B2_KEY_ID and the application key.")
        j = r.json()
        self.api, self.dl = j["apiInfo"]["storageApi"]["apiUrl"], j["apiInfo"]["storageApi"]["downloadUrl"]
        self.h, self.account = {"Authorization": j["authorizationToken"]}, j["accountId"]
        b = self._post("b2_list_buckets", {"accountId": self.account, "bucketName": self.bucket})["buckets"]
        if not b:
            raise BackupError(f"Bucket {self.bucket} was not found for this key.")
        self.bucket_id, self.info = b[0]["bucketId"], b[0]

    def _post(self, op: str, body: dict) -> dict:
        r = self.c.post(f"{self.api}/b2api/v3/{op}", headers=self.h, json=body)
        if r.status_code >= 300:
            raise BackupError(f"Backblaze {op} failed: {r.json().get('message', r.status_code)}")
        return r.json()

    def upload(self, name: str, data: bytes) -> dict:
        if len(data) > MAX_SINGLE_UPLOAD:
            raise BackupError("Backup is too large for a single upload; time to add large-file support.")
        up = self._post("b2_get_upload_url", {"bucketId": self.bucket_id})
        r = self.c.post(up["uploadUrl"], content=data, headers={"Authorization": up["authorizationToken"], "X-Bz-File-Name": name,
                                                              "Content-Type": "application/octet-stream", "X-Bz-Content-Sha1": hashlib.sha1(data).hexdigest()})
        if r.status_code != 200:
            raise BackupError(f"Upload failed: {r.text[:200]}")
        return r.json()

    def list(self) -> list[dict]:
        out, start = [], None
        while True:
            j = self._post("b2_list_file_names", {"bucketId": self.bucket_id, "prefix": PREFIX, "maxFileCount": 1000, **({"startFileName": start} if start else {})})
            out += j["files"]
            start = j.get("nextFileName")
            if not start:
                return sorted(out, key=lambda f: f["fileName"])

    def download(self, name: str) -> bytes:
        r = self.c.get(f"{self.dl}/file/{self.bucket}/{name}", headers=self.h)
        if r.status_code != 200:
            raise BackupError(f"Download failed ({r.status_code}).")
        return r.content

    def set_retention(self, days: int) -> None:
        """Hide backups after `days`, then delete the hidden version a day later, so storage does not grow forever."""
        rules = [{"fileNamePrefix": PREFIX, "daysFromUploadingToHiding": days, "daysFromHidingToDeleting": 1}]
        self._post("b2_update_bucket", {"accountId": self.account, "bucketId": self.bucket_id, "lifecycleRules": rules})


def run_backup(b2: B2 | None = None) -> dict:
    b2 = b2 or B2()
    archive, manifest = dump()
    blob = encrypt(archive, settings.BACKUP_KEY)
    name = f"{PREFIX}zenith-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.zbk"
    b2.upload(name, blob)
    return {"file": name, "bytes": len(blob), "tables": len(manifest["tables"]), "rows": sum(t["rows"] for t in manifest["tables"]), "revision": manifest["alembic_revision"]}


def latest(b2: B2) -> str:
    files = b2.list()
    if not files:
        raise BackupError("There are no backups yet.")
    return files[-1]["fileName"]
