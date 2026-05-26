from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.base import Base
from app.models import project  # noqa: F401
from app.models import task  # noqa: F401

engine = create_engine(
    settings.house_diy_database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_db() -> None:
    """
    SQLite 增量迁移：为已有表补列

    create_all 不会 ALTER 已有表，启动时补缺失列
    """
    inspector = inspect(engine)
    if "projects" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("projects")}
    statements: list[str] = []
    if "max_step" not in columns:
        statements.append(
            "ALTER TABLE projects ADD COLUMN max_step VARCHAR(20) NOT NULL DEFAULT 'upload'"
        )
    if "active_scheme_id" not in columns:
        statements.append("ALTER TABLE projects ADD COLUMN active_scheme_id VARCHAR(64)")
    if "annotation_confirmed_at" not in columns:
        statements.append("ALTER TABLE projects ADD COLUMN annotation_confirmed_at DATETIME")

    if not statements:
        return

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def init_db():
    Base.metadata.create_all(bind=engine)
    migrate_db()
