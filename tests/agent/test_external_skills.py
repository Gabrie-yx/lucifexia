"""Tests for external skill directories (skills.external_dirs config)."""

import json
import os
from unittest.mock import patch

import pytest


@pytest.fixture
def external_skills_dir(tmp_path):
    """Create a temp dir with a sample external skill."""
    ext_dir = tmp_path / "external-skills"
    skill_dir = ext_dir / "my-external-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-external-skill\ndescription: A skill from an external directory\n---\n\n# My External Skill\n\nDo external things.\n"
    )
    return ext_dir


@pytest.fixture
def LUCIFEX_HOME(tmp_path):
    """Create a minimal LUCIFEX_HOME with config."""
    home = tmp_path / ".hermes"
    home.mkdir()
    (home / "skills").mkdir()
    return home


class TestGetExternalSkillsDirs:
    def test_empty_config(self, LUCIFEX_HOME):
        (LUCIFEX_HOME / "config.yaml").write_text("skills:\n  external_dirs: []\n")
        with patch.dict(os.environ, {"LUCIFEX_HOME": str(LUCIFEX_HOME)}):
            from agent.skill_utils import get_external_skills_dirs
            result = get_external_skills_dirs()
        assert result == []

    def test_nonexistent_dir_skipped(self, LUCIFEX_HOME):
        (LUCIFEX_HOME / "config.yaml").write_text(
            "skills:\n  external_dirs:\n    - /nonexistent/path\n"
        )
        with patch.dict(os.environ, {"LUCIFEX_HOME": str(LUCIFEX_HOME)}):
            from agent.skill_utils import get_external_skills_dirs
            result = get_external_skills_dirs()
        assert result == []

    def test_valid_dir_returned(self, LUCIFEX_HOME, external_skills_dir):
        (LUCIFEX_HOME / "config.yaml").write_text(
            f"skills:\n  external_dirs:\n    - {external_skills_dir}\n"
        )
        with patch.dict(os.environ, {"LUCIFEX_HOME": str(LUCIFEX_HOME)}):
            from agent.skill_utils import get_external_skills_dirs
            result = get_external_skills_dirs()
        assert len(result) == 1
        assert result[0] == external_skills_dir.resolve()

    def test_duplicate_dirs_deduplicated(self, LUCIFEX_HOME, external_skills_dir):
        (LUCIFEX_HOME / "config.yaml").write_text(
            f"skills:\n  external_dirs:\n    - {external_skills_dir}\n    - {external_skills_dir}\n"
        )
        with patch.dict(os.environ, {"LUCIFEX_HOME": str(LUCIFEX_HOME)}):
            from agent.skill_utils import get_external_skills_dirs
            result = get_external_skills_dirs()
        assert len(result) == 1

    def test_local_skills_dir_excluded(self, LUCIFEX_HOME):
        local_skills = LUCIFEX_HOME / "skills"
        (LUCIFEX_HOME / "config.yaml").write_text(
            f"skills:\n  external_dirs:\n    - {local_skills}\n"
        )
        with patch.dict(os.environ, {"LUCIFEX_HOME": str(LUCIFEX_HOME)}):
            from agent.skill_utils import get_external_skills_dirs
            result = get_external_skills_dirs()
        assert result == []

    def test_no_config_file(self, LUCIFEX_HOME):
        # No config.yaml at all
        with patch.dict(os.environ, {"LUCIFEX_HOME": str(LUCIFEX_HOME)}):
            from agent.skill_utils import get_external_skills_dirs
            result = get_external_skills_dirs()
        assert result == []

    def test_string_value_converted_to_list(self, LUCIFEX_HOME, external_skills_dir):
        (LUCIFEX_HOME / "config.yaml").write_text(
            f"skills:\n  external_dirs: {external_skills_dir}\n"
        )
        with patch.dict(os.environ, {"LUCIFEX_HOME": str(LUCIFEX_HOME)}):
            from agent.skill_utils import get_external_skills_dirs
            result = get_external_skills_dirs()
        assert len(result) == 1


class TestGetAllSkillsDirs:
    def test_local_always_first(self, LUCIFEX_HOME, external_skills_dir):
        (LUCIFEX_HOME / "config.yaml").write_text(
            f"skills:\n  external_dirs:\n    - {external_skills_dir}\n"
        )
        with patch.dict(os.environ, {"LUCIFEX_HOME": str(LUCIFEX_HOME)}):
            from agent.skill_utils import get_all_skills_dirs
            result = get_all_skills_dirs()
        assert result[0] == LUCIFEX_HOME / "skills"
        assert result[1] == external_skills_dir.resolve()


class TestExternalSkillsInFindAll:
    def test_external_skills_found(self, LUCIFEX_HOME, external_skills_dir):
        (LUCIFEX_HOME / "config.yaml").write_text(
            f"skills:\n  external_dirs:\n    - {external_skills_dir}\n"
        )
        local_skills = LUCIFEX_HOME / "skills"
        with (
            patch.dict(os.environ, {"LUCIFEX_HOME": str(LUCIFEX_HOME)}),
            patch("tools.skills_tool.SKILLS_DIR", local_skills),
        ):
            from tools.skills_tool import _find_all_skills
            skills = _find_all_skills()
        names = [s["name"] for s in skills]
        assert "my-external-skill" in names

    def test_local_takes_precedence(self, LUCIFEX_HOME, external_skills_dir):
        """If the same skill name exists locally and externally, local wins."""
        local_skills = LUCIFEX_HOME / "skills"
        local_skill = local_skills / "my-external-skill"
        local_skill.mkdir(parents=True)
        (local_skill / "SKILL.md").write_text(
            "---\nname: my-external-skill\ndescription: Local version\n---\n\nLocal.\n"
        )
        (LUCIFEX_HOME / "config.yaml").write_text(
            f"skills:\n  external_dirs:\n    - {external_skills_dir}\n"
        )
        with (
            patch.dict(os.environ, {"LUCIFEX_HOME": str(LUCIFEX_HOME)}),
            patch("tools.skills_tool.SKILLS_DIR", local_skills),
        ):
            from tools.skills_tool import _find_all_skills
            skills = _find_all_skills()
        matching = [s for s in skills if s["name"] == "my-external-skill"]
        assert len(matching) == 1
        assert matching[0]["description"] == "Local version"


class TestExternalSkillView:
    def test_skill_view_finds_external(self, LUCIFEX_HOME, external_skills_dir):
        (LUCIFEX_HOME / "config.yaml").write_text(
            f"skills:\n  external_dirs:\n    - {external_skills_dir}\n"
        )
        local_skills = LUCIFEX_HOME / "skills"
        with (
            patch.dict(os.environ, {"LUCIFEX_HOME": str(LUCIFEX_HOME)}),
            patch("tools.skills_tool.SKILLS_DIR", local_skills),
        ):
            from tools.skills_tool import skill_view
            result = json.loads(skill_view("my-external-skill"))
        assert result["success"] is True
        assert "external things" in result["content"]
