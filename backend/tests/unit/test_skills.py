from __future__ import annotations

from core import skills


def test_scan_skills_and_refresh_snapshot(tmp_path, monkeypatch) -> None:
    skills_dir = tmp_path / "skills"
    snapshot = tmp_path / "SKILLS_SNAPSHOT.md"
    (skills_dir / "demo").mkdir(parents=True)
    (skills_dir / "fallback").mkdir(parents=True)

    (skills_dir / "demo" / "SKILL.md").write_text(
        "---\nname: demo_skill\ndescription: demo description\n---\n\n# demo\n",
        encoding="utf-8",
    )
    (skills_dir / "fallback" / "SKILL.md").write_text("# no frontmatter\n", encoding="utf-8")

    monkeypatch.setattr(skills, "SKILLS_DIR", skills_dir)
    monkeypatch.setattr(skills, "SKILLS_SNAPSHOT_FILE", snapshot)

    scanned = skills.scan_skills()
    names = [item.name for item in scanned]
    assert names == ["demo_skill", "fallback"]

    content = skills.refresh_skills_snapshot()
    assert "<name>demo_skill</name>" in content
    assert "<name>fallback</name>" in snapshot.read_text(encoding="utf-8")
