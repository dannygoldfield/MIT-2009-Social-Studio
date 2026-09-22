"""Policy tests use stand-in files; test_media verifies real codecs and outputs."""

import json
import zipfile

import pytest
from pydantic import ValidationError

from mit2009_studio.media import digest
from mit2009_studio.models import Approval, Generate, NewProject, Rating
from mit2009_studio.service import Studio
from mit2009_studio.store import packed
from mit2009_studio.styles import choose_styles


def complete(studio, batch_id):
    for c in studio.store.all("SELECT * FROM candidates WHERE batch_id=?", (batch_id,)):
        path = studio.store.path(f"test-artifacts/{c['id']}.mp4")
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(c["id"].encode())
        artifact = {"output": {"path": studio.store.relative(path), "sha256": digest(path)}}
        with studio.store.connect() as db:
            db.execute(
                "UPDATE candidates SET status='ready',artifacts=? WHERE id=?", (packed(artifact), c["id"])
            )
    with studio.store.connect() as db:
        db.execute("UPDATE jobs SET status='done' WHERE batch_id=?", (batch_id,))
    return studio.store.all("SELECT * FROM candidates WHERE batch_id=? ORDER BY slot", (batch_id,))


def loop(studio, project, source_assets):
    picks = {}
    for stage in ("audio", "video", "text", "assembly"):
        ids = (
            [a["id"] for a in source_assets if a["role"] == ("reference" if stage == "audio" else "photo")]
            if stage in ("audio", "video")
            else []
        )
        batch = studio.enqueue(
            project["id"], Generate(stage=stage, asset_ids=ids, keyword="CONNECT" if stage == "text" else "")
        )
        choice = complete(studio, batch["batch_id"])[0]
        studio.rate(choice["id"], 4)
        studio.select(choice["id"])
        picks[stage] = choice
    return picks


def test_three_distinct_families():
    for seed in range(25):
        for stage in ("audio", "video", "text", "assembly"):
            styles = choose_styles(stage, seed)
            assert len(styles) == len({s["family"] for s in styles}) == 3
            assert styles == choose_styles(stage, seed)


def test_keyword_and_duration_validation():
    for keyword in ("two words", "two\nwords", "a\u200bb", "!!!"):
        with pytest.raises(ValidationError):
            Generate(stage="text", keyword=keyword)
    assert Generate(stage="text", keyword=" CONNECT ").keyword == "CONNECT"
    with pytest.raises(ValidationError):
        NewProject(name="Test", author="Me", duration=20)
    for stars in (0, 6, 2.5, True, "5"):
        with pytest.raises(ValidationError):
            Rating(stars=stars)


def test_full_decisions_persist_and_approval_is_not_rating(studio, project, source_assets):
    picks = loop(studio, project, source_assets)
    final = picks["assembly"]
    studio.rate(final["id"], 5)
    reopened = Studio(studio.store.root)
    detail = reopened.detail(project["id"])
    assert len(detail["candidates"]) == 13
    assert all(c["settings"]["duration"] == 15 for c in detail["candidates"])
    assert detail["selections"]["assembly"] == final["id"]
    assert reopened.candidate(final["id"])["winner_at"]
    assert detail["approvals"] == []
    for explanation, confirmed in [(" ", True), ("This feels right.", False)]:
        with pytest.raises(ValidationError):
            Approval(candidate_id=final["id"], explanation=explanation, confirmed=confirmed)
    approved = reopened.approve(
        project["id"],
        Approval(candidate_id=final["id"], explanation="The pacing supports the story.", confirmed=True),
    )
    record = reopened.store.one("SELECT * FROM approvals WHERE id=?", (approved["approval_id"],))
    assert record["snapshot"]["selections"]["audio"] == picks["audio"]["id"]
    assert len(record["snapshot"]["candidates_considered"]) == 13
    assert len(record["snapshot"]["source_assets"]) == 4
    assert record["snapshot"]["approved_by"] == "Test author"
    reopened.rate(final["id"], 2)
    assert reopened.candidate(final["id"])["winner_at"]
    assert record == reopened.store.one("SELECT * FROM approvals WHERE id=?", (approved["approval_id"],))
    exported = reopened.export(approved["approval_id"])
    out = reopened.store.one("SELECT * FROM exports WHERE id=?", (exported["export_id"],))
    with zipfile.ZipFile(reopened.store.path(out["path"])) as archive:
        assert set(archive.namelist()) == {"approved.mp4", "provenance.json", "READ-ME.txt"}
        assert json.loads(archive.read("provenance.json"))["why_this_one"] == "The pacing supports the story."
    reopened.store.path(final["artifacts"]["output"]["path"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed"):
        reopened.export(approved["approval_id"])


def test_upstream_change_invalidates_selections_not_history(studio, project, source_assets):
    picks = loop(studio, project, source_assets)
    alternate = studio.store.one(
        "SELECT * FROM candidates WHERE stage='audio' AND id!=? LIMIT 1", (picks["audio"]["id"],)
    )
    studio.rate(alternate["id"], 3)
    studio.select(alternate["id"])
    assert studio.selections(project["id"]) == {"audio": alternate["id"]}
    assert len(studio.detail(project["id"])["candidates"]) == 13
    with pytest.raises(ValueError, match="earlier selections"):
        studio.select(picks["video"]["id"])
    with pytest.raises(ValueError, match="current ingredients"):
        studio.approve(
            project["id"],
            Approval(
                candidate_id=picks["assembly"]["id"], explanation="This should be rejected.", confirmed=True
            ),
        )


def test_cross_project_sources_and_selection_gate(studio, project, source_assets):
    second = studio.create_project(NewProject(name="Other", author="Other person"))
    with pytest.raises(ValueError):
        studio.enqueue(second["id"], Generate(stage="audio", asset_ids=[source_assets[0]["id"]]))
    with pytest.raises(ValueError, match="earlier stage"):
        studio.enqueue(project["id"], Generate(stage="assembly"))
    batch = studio.enqueue(project["id"], Generate(stage="audio", asset_ids=[source_assets[0]["id"]]))
    with pytest.raises(ValueError, match="current batch"):
        studio.enqueue(project["id"], Generate(stage="audio", asset_ids=[source_assets[0]["id"]]))
    candidates = complete(studio, batch["batch_id"])
    with pytest.raises(ValueError, match="rate"):
        studio.select(candidates[0]["id"])
    with pytest.raises(ValueError):
        studio.store.path("../../private.txt")


def test_cannot_approve_a_partial_final_batch(studio, project, source_assets):
    picks = loop(studio, project, source_assets)
    with studio.store.connect() as db:
        db.execute(
            "UPDATE candidates SET status='failed' WHERE stage='assembly' AND id!=?",
            (picks["assembly"]["id"],),
        )
    with pytest.raises(ValueError, match="all three"):
        studio.approve(
            project["id"],
            Approval(
                candidate_id=picks["assembly"]["id"], explanation="Needs complete comparison.", confirmed=True
            ),
        )
