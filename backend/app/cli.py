"""ZENITH admin CLI.  python -m app.cli <command>

  validate <dir>          check a content tree without touching the database
  import <dir>            load content as reviewable versions (idempotent)
  status                  what is live and what is waiting for review
  promote <email> <role>  give an existing account the reviewer or admin role
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


if __name__ == "__main__":
    sys.exit(main(sys.argv))
