from app.db.session import engine
from app.db.base import Base
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    conn.commit()
