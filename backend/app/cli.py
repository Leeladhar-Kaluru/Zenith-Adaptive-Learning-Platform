"""ZENITH admin CLI.  python -m app.cli <command>

  validate <dir>          check a content tree without touching the database
  import <dir>            load content as reviewable versions (idempotent)
  status                  what is live and what is waiting for review
  promote <email> <role>  give an existing account the reviewer or admin role
  backup                  encrypted dump of the zenith schema to Backblaze B2
  backups                 list backups in B2
  verify [file]           download, decrypt and checksum a backup (default: latest)
  restore <file|latest> <new_schema>   load a backup into an empty, migrated schema
  retention <days>        set how long B2 keeps backups before deleting them
  backup-key              create BACKUP_KEY and append it to backend/.env (never printed)
  dataset worldbank <indicator> <country> "<Title>"   import a World Bank indicator (CC BY 4.0), left pending for approval
  map import <file.geojson> <external-id>   import a Natural Earth GeoJSON a person has downloaded (public domain, left pending)
  assets-due              imported assets whose licence re-check date has passed
  new-lesson <content-dir> <chapter-slug> <lesson-slug> "<Title>" <concept,concept>   start a lesson from a TODO skeleton
  asset commons <File:Title>   import one Wikimedia Commons file (licence checked, left pending)
  asset approve <asset-id> <reviewer-email>   approve an imported asset for use in lessons
"""
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "validate":
        from app.cms import importer
        tree = importer.load_tree(Path(argv[2]))
        errs = importer.validate_tree(tree)
        print("OK" if not errs else "\n".join(errs))
        return 0 if not errs else 1
    if cmd == "new-lesson":
        from app.cms import draft
        try:
            path = draft.write_skeleton(Path(argv[2]), argv[3], argv[4], argv[5], argv[6].split(","))
        except draft.DraftError as e:
            print("Not created:", e)
            return 1
        print(f"Created {path}. Fill every TODO; `validate` fails until you do.")
        return 0
    if cmd in ("backup", "backups", "verify", "restore", "retention", "backup-key"):
        return ops(cmd, argv)
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        if cmd == "import":
            from app.cms import importer
            rep = importer.import_tree(db, importer.load_tree(Path(argv[2])))
            print(rep)
            return 0
        if cmd == "status":
            from sqlalchemy import func, select
            from app.models import Chapter, LessonVersion
            for st, n in db.execute(select(LessonVersion.status, func.count()).group_by(LessonVersion.status)):
                print(f"lesson versions {st}: {n}")
            for ch in db.scalars(select(Chapter).order_by(Chapter.grade, Chapter.slug)):
                print(f"class {ch.grade} {ch.subject_id} {ch.slug}: {ch.status}")
            return 0
        if cmd == "asset":
            from sqlalchemy import select
            from app.models import Profile
            if argv[2] == "commons":
                from app.ingest import commons
                who = db.scalar(select(Profile).where(Profile.role.in_(("reviewer", "admin"))))
                try:
                    a = commons.import_file(db, argv[3], who.id if who else None)
                except commons.CommonsError as e:
                    print("Not imported:", e)
                    return 1
                print(f"{a.status}: {a.external_id} [{a.licence_id}] {a.attribution_text}  (id {a.id})")
                return 0
            if argv[2] == "approve":
                import uuid as _uuid
                from app.ingest.assets import AssetError, approve_asset
                rv = db.scalar(select(Profile).where(Profile.email == argv[4].strip().lower(), Profile.role.in_(("reviewer", "admin"))))
                if rv is None:
                    print("That email is not a reviewer.")
                    return 1
                try:
                    approve_asset(db, _uuid.UUID(argv[3]), rv.id)
                except AssetError as e:
                    print("Not approved:", e)
                    return 1
                print("approved")
                return 0
        if cmd == "dataset" and argv[2] == "worldbank":
            from sqlalchemy import select
            from app.models import Profile
            from app.ingest import worldbank
            from app.ingest.datasets import DatasetError
            who = db.scalar(select(Profile).where(Profile.role.in_(("reviewer", "admin"))))
            try:
                a = worldbank.import_indicator(db, argv[3], argv[4], argv[5], who.id if who else None)
            except DatasetError as e:
                print("Not imported:", e)
                return 1
            print(f"{a.status}: {a.external_id} [{a.licence_id}] {len(a.data['rows'])} rows  (id {a.id})")
            return 0
        if cmd == "map" and argv[2] == "import":
            import json as _json
            from sqlalchemy import select
            from app.models import Profile
            from app.ingest import naturalearth
            who = db.scalar(select(Profile).where(Profile.role.in_(("reviewer", "admin"))))
            try:
                a = naturalearth.import_geojson(db, _json.loads(Path(argv[3]).read_text(encoding="utf-8")), argv[4], who.id if who else None)
            except naturalearth.GeoError as e:
                print("Not imported:", e)
                return 1
            print(f"{a.status}: {a.external_id} [{a.licence_id}] {len(a.data['features'])} countries, {a.bytes // 1024} kB  (id {a.id})")
            return 0
        if cmd == "assets-due":
            from app.ingest.recheck import due_for_recheck
            rows = due_for_recheck(db)
            for a in rows:
                print(f"{a.recheck_at.date()}  {a.licence_id:12} {a.external_id}  {a.url}")
            print(f"{len(rows)} asset(s) due for a licence re-check")
            return 0
        if cmd == "promote":
            from sqlalchemy import select
            from app.models import Profile
            if argv[3] not in ("reviewer", "admin", "teacher", "student"):
                print("role must be reviewer, admin, teacher or student")
                return 2
            p = db.scalar(select(Profile).where(Profile.email == argv[2].strip().lower()))
            if not p:
                print("No account with that email. Sign up first.")
                return 1
            p.role = argv[3]
            db.commit()
            print(f"{p.email} is now {p.role}")
            return 0
    finally:
        db.close()
    print(__doc__)
    return 2


def ops(cmd: str, argv: list[str]) -> int:
    from app.ops import backup as bk
    try:
        if cmd == "backup-key":
            env = Path(__file__).resolve().parents[1] / ".env"
            if "BACKUP_KEY=" in env.read_text(encoding="utf-8"):
                print("BACKUP_KEY already exists in backend/.env. Not changing it.")
                return 1
            with open(env, "a", encoding="utf-8") as f:
                f.write("\nBACKUP_KEY=" + bk.make_key() + "\n")
            print("BACKUP_KEY was added to backend/.env. COPY IT SOMEWHERE SAFE (password manager): without it no backup can be read.")
            return 0
        b2 = bk.B2()
        if cmd == "retention":
            b2.set_retention(int(argv[2]))
            print(f"B2 will delete backups {int(argv[2])} days after upload.")
        elif cmd == "backup":
            print(bk.run_backup(b2))
        elif cmd == "backups":
            for f in b2.list():
                print(f["fileName"], f["contentLength"], "bytes")
        elif cmd == "verify":
            name = argv[2] if len(argv) > 2 and argv[2] != "latest" else bk.latest(b2)
            manifest, _ = bk._unpack(bk.decrypt(b2.download(name), bk.settings.BACKUP_KEY))
            print(name, "OK:", {t["name"]: t["rows"] for t in manifest["tables"] if t["rows"]}, "| revision", manifest["alembic_revision"])
        elif cmd == "restore":
            name = argv[2] if argv[2] != "latest" else bk.latest(b2)
            print(bk.restore(bk.decrypt(b2.download(name), bk.settings.BACKUP_KEY), argv[3]))
        return 0
    except bk.BackupError as e:
        print("Backup error:", e)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
