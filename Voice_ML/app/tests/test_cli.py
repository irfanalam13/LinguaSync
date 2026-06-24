"""Tests for the CLI entry point — run_pipeline is mocked."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.cli import main as cli
from app.core.exceptions import InvalidVideoError
from app.schemas.pipeline import PipelineResult, StageTimings


def _fake_result(target="ne", source="en", preserve=False, sim=None):
    return PipelineResult(
        job_id="job123",
        source_language=source,
        target_language=target,
        output_video="/tmp/out.mp4",
        transcript_text="hi",
        translated_text="नमस्ते",
        artifacts_dir="/tmp/job123",
        preserve_voice=preserve,
        similarity=sim,
        timings=StageTimings(total=1.0),
    )


def _patch_base(monkeypatch, fn):
    monkeypatch.setattr(cli.translation_pipeline, "run_pipeline", fn)


def _patch_preserve(monkeypatch, fn):
    monkeypatch.setattr(cli.speaker_preservation_pipeline, "run_pipeline", fn)


def test_cli_success(fake_video, monkeypatch, capsys):
    _patch_base(monkeypatch, lambda **kw: _fake_result())
    rc = cli.main([str(fake_video), "--target", "ne"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Translation complete" in out
    assert "job123" in out


def test_cli_preserve_voice_routes_and_reports_similarity(fake_video, monkeypatch, capsys):
    called = {"preserve": False}

    def fake(**kw):
        called["preserve"] = True
        return _fake_result(preserve=True, sim=0.73)

    _patch_preserve(monkeypatch, fake)
    rc = cli.main([str(fake_video), "--target", "ne", "--preserve-voice"])
    assert rc == 0 and called["preserve"]
    out = capsys.readouterr().out
    assert "PRESERVED" in out and "0.73" in out


def test_cli_missing_input(monkeypatch, capsys):
    rc = cli.main(["does_not_exist.mp4", "--target", "ne"])
    assert rc == 2
    assert "not found" in capsys.readouterr().err


def test_cli_pipeline_error(fake_video, monkeypatch, capsys):
    def boom(**kw):
        raise InvalidVideoError("bad video")

    _patch_base(monkeypatch, boom)
    rc = cli.main([str(fake_video), "--target", "en"])
    assert rc == 2
    assert "bad video" in capsys.readouterr().err


def test_cli_rejects_bad_target(fake_video):
    with pytest.raises(SystemExit):  # argparse choices rejection
        cli.main([str(fake_video), "--target", "fr"])


def test_cli_passes_source_and_target(fake_video, monkeypatch):
    captured = {}

    def capture(**kw):
        captured.update(kw)
        return _fake_result(target=kw["target_language"], source=kw["source_language"])

    _patch_base(monkeypatch, capture)
    cli.main([str(fake_video), "--target", "en", "--source", "ne"])
    assert captured["target_language"] == "en"
    assert captured["source_language"] == "ne"
