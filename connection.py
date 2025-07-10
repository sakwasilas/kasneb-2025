import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load from environment (Render will inject DATABASE_URL)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///kasneb.db")

# Use SQLite config only if it's SQLite
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()