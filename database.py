# database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Get the database URL from the environment, falling back to a local SQLite DB
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tasks.db")

# Heroku uses 'postgres://', but SQLAlchemy needs 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create the SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    # connect_args are only for SQLite
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a Base class for declarative models
Base = declarative_base()


# --- Task Model ---
from sqlalchemy import Column, Integer, String, JSON

class Task(Base):
    """
    Represents a forwarding task in the database.
    """
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    sources = Column(JSON)  # List of source channel IDs
    targets = Column(JSON)  # List of target channel IDs
    ai_options = Column(JSON)
    filters = Column(JSON)

    def __repr__(self):
        return f"<Task(name='{self.name}')>"


def init_db():
    """
    Creates the database tables.
    """
    Base.metadata.create_all(bind=engine)
