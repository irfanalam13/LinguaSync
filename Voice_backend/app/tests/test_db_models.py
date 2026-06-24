"""DB model tests on an isolated in-memory SQLite engine (no global state)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import ApiKey, Job, JobMode, JobStatus, User, Video


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    Base.metadata.drop_all(engine)


def test_create_user_video_job(session):
    user = User(email="a@b.com", hashed_password="x", full_name="A B")
    session.add(user)
    session.flush()
    assert len(user.id) == 32  # uuid hex

    video = Video(user_id=user.id, filename="clip.mp4", storage_key="k/clip.mp4", size_bytes=100)
    session.add(video)
    session.flush()

    job = Job(
        user_id=user.id, video_id=video.id, target_language="ne",
        mode=JobMode.localize.value, status=JobStatus.queued.value,
    )
    session.add(job)
    session.commit()

    got = session.scalar(select(Job).where(Job.id == job.id))
    assert got.status == "queued" and got.mode == "localize"
    assert got.user.email == "a@b.com"
    assert got.video.filename == "clip.mp4"


def test_user_email_unique(session):
    session.add(User(email="dup@x.com", hashed_password="x"))
    session.commit()
    session.add(User(email="dup@x.com", hashed_password="y"))
    with pytest.raises(Exception):
        session.commit()


def test_cascade_delete_user_removes_children(session):
    user = User(email="c@d.com", hashed_password="x")
    session.add(user)
    session.flush()
    v = Video(user_id=user.id, filename="f.mp4", storage_key="k")
    session.add(v)
    session.flush()
    session.add(Job(user_id=user.id, video_id=v.id, target_language="en"))
    session.add(ApiKey(user_id=user.id, name="k", prefix="vc_abc", hashed_key="h"))
    session.commit()

    session.delete(user)
    session.commit()
    assert session.scalar(select(Video).where(Video.user_id == user.id)) is None
    assert session.scalar(select(Job).where(Job.user_id == user.id)) is None


def test_job_status_enum_values():
    assert {s.value for s in JobStatus} == {"queued", "running", "completed", "failed", "cancelled"}
    assert {m.value for m in JobMode} == {"translate", "preserve", "clone", "localize"}
