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
