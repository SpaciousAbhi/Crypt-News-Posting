# database.py

import os
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    BigInteger,
    DateTime,
    ForeignKey,
    JSON,
    func,
)
from sqlalchemy.orm import sessionmaker, relationship, declarative_base

# --- Database Configuration ---

# Get the database URL from the environment, falling back to a local SQLite DB for development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tasks.db")

# Heroku uses 'postgres://', but SQLAlchemy needs 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create the SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a Base class for declarative models
Base = declarative_base()


# --- Model Definitions ---


class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    role = Column(String, nullable=False, default="user")  # 'user', 'admin', 'owner'
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    tasks = relationship("Task", back_populates="owner", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"
    task_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    name = Column(String, nullable=False)
    enabled = Column(Boolean, nullable=False, default=False)
    priority = Column(Integer, nullable=False, default=10)
    rate_limit_rpm = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    owner = relationship("User", back_populates="tasks")
    sources = relationship(
        "Source", back_populates="task", cascade="all, delete-orphan"
    )
    targets = relationship(
        "Target", back_populates="task", cascade="all, delete-orphan"
    )
    ai_rules = relationship(
        "AIRule", back_populates="task", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Task(task_id={self.task_id}, name='{self.name}', enabled={self.enabled})>"


class Source(Base):
    __tablename__ = "sources"
    source_id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.task_id"), nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    chat_type = Column(String, nullable=False)

    task = relationship("Task", back_populates="sources")


class Target(Base):
    __tablename__ = "targets"
    target_id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.task_id"), nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    chat_type = Column(String, nullable=False)

    task = relationship("Task", back_populates="targets")


class AIRule(Base):
    __tablename__ = "ai_rules"
    rule_id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.task_id"), nullable=False)
    rule_type = Column(String, nullable=False)
    config = Column(JSON, nullable=False)
    version = Column(String, nullable=False, default="1.0")

    task = relationship("Task", back_populates="ai_rules")


class ProcessedMessage(Base):
    __tablename__ = "processed_messages"
    message_key = Column(String, primary_key=True)
    source_chat_id = Column(BigInteger, nullable=False)
    source_message_id = Column(BigInteger, nullable=False)
    expires_at = Column(DateTime, nullable=False)


# --- Database Initialization ---


def init_db():
    """
    Creates all the database tables defined in the models.
    This should be run once on initial setup.
    """
    Base.metadata.create_all(bind=engine, checkfirst=True)
