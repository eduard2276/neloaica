"""Tests for ``.github/workflows/release.yml``.

We don't run GitHub Actions locally — instead we parse the YAML and
assert on the structural invariants the rest of the auto-update
roadmap relies on. If someone accidentally drops the tag verification
step, removes ``windows-latest``, or downgrades Python below 3.12,
the test breaks loudly.
"""

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

WORKFLOW_PATH = (
    Path(__file__).resolve().parent.parent.parent / ".github" / "workflows" / "release.yml"
)


@pytest.fixture(scope="module")
def workflow():
    """Parsed YAML for ``release.yml``."""
    if not WORKFLOW_PATH.is_file():
        pytest.fail(f"Missing workflow file: {WORKFLOW_PATH}")
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    return yaml.safe_load(text)


@pytest.fixture(scope="module")
def workflow_text():
    return WORKFLOW_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def build_steps(workflow):
    return workflow["jobs"]["build"]["steps"]


def _step_named(steps, name_substr):
    for s in steps:
        if "name" in s and name_substr.lower() in s["name"].lower():
            return s
    return None


# ===========================================================================
# TestStructure
# ===========================================================================


class TestStructure:
    def test_yaml_is_well_formed(self, workflow):
        assert isinstance(workflow, dict)

    def test_has_release_name(self, workflow):
        assert workflow.get("name") == "Release"

    def test_top_level_jobs_present(self, workflow):
        assert "jobs" in workflow
        assert "build" in workflow["jobs"]

    def test_permissions_grants_release_write(self, workflow):
        # softprops/action-gh-release needs `contents: write` to publish.
        assert workflow.get("permissions", {}).get("contents") == "write"

    def test_concurrency_does_not_cancel_releases(self, workflow):
        # We never want to cancel an in-flight release run because it leaves
        # half-published assets on the GitHub Release.
        conc = workflow.get("concurrency") or {}
        assert conc.get("cancel-in-progress") is False


# ===========================================================================
# TestTrigger
# ===========================================================================


class TestTrigger:
    def test_triggers_on_tag_push(self, workflow):
        # PyYAML parses the bare key ``on`` as the boolean True. Both keys
        # are handled to be defensive against future YAML revisions.
        on = workflow.get("on") or workflow.get(True)
        assert on is not None, "Workflow must have an `on:` trigger"
        assert "push" in on

    def test_triggers_only_on_semver_tags(self, workflow):
        on = workflow.get("on") or workflow.get(True)
        tags = on["push"].get("tags")
        assert tags == ["v*.*.*"], f"Expected ['v*.*.*'], got {tags!r}"

    def test_does_not_trigger_on_branches(self, workflow):
        # We don't want every push to main to publish — only tags.
        on = workflow.get("on") or workflow.get(True)
        push = on["push"]
        assert "branches" not in push, "Release must not trigger on branch pushes"


# ===========================================================================
# TestBuildJob
# ===========================================================================


class TestBuildJob:
    def test_runs_on_windows(self, workflow):
        assert workflow["jobs"]["build"]["runs-on"] == "windows-latest"

    def test_uses_python_3_12(self, build_steps):
        setup = _step_named(build_steps, "Set up Python")
        assert setup is not None
        assert setup["uses"].startswith("actions/setup-python@")
        assert setup["with"]["python-version"] == "3.12"

    def test_pip_cache_configured(self, build_steps):
        setup = _step_named(build_steps, "Set up Python")
        assert setup["with"].get("cache") == "pip"

    def test_installs_runtime_deps_from_requirements(self, build_steps):
        install = _step_named(build_steps, "Install")
        assert install is not None
        assert "requirements.txt" in install["run"]

    def test_installs_pyinstaller(self, build_steps):
        install = _step_named(build_steps, "Install")
        assert "pyinstaller" in install["run"].lower()

    def test_verify_tag_step_uses_helper_script(self, build_steps):
        step = _step_named(build_steps, "Verify tag")
        assert step is not None
        assert "scripts/verify_tag_matches_version.py" in step["run"]
        assert "github.ref_name" in step["run"]

    def test_verify_step_runs_before_build_step(self, build_steps):
        verify_idx = next(
            i
            for i, s in enumerate(build_steps)
            if s.get("name", "").lower().startswith("verify tag")
        )
        build_idx = next(
            i
            for i, s in enumerate(build_steps)
            if "PyInstaller" in s.get("run", "") and "--noconfirm" in s.get("run", "")
        )
        assert verify_idx < build_idx, "Tag check must run before the heavy build step"

    def test_build_step_uses_spec_file(self, build_steps):
        build = _step_named(build_steps, "Build with PyInstaller")
        assert build is not None
        assert "Neloaica.spec" in build["run"]

    def test_sanity_check_validates_exe_and_template(self, build_steps):
        sanity = _step_named(build_steps, "Sanity check")
        assert sanity is not None
        run = sanity["run"]
        assert "Neloaica.exe" in run
        assert "Template-deviz.xlsx" in run

    def test_zip_step_names_archive_with_tag(self, build_steps):
        zip_step = _step_named(build_steps, "Zip")
        assert zip_step is not None
        run = zip_step["run"]
        assert "Compress-Archive" in run
        assert "github.ref_name" in run

    def test_uploads_workflow_artefact(self, build_steps):
        upload = _step_named(build_steps, "Upload bundle")
        assert upload is not None
        assert upload["uses"].startswith("actions/upload-artifact@")
        # error-on-empty so a botched build can't silently produce a 0-byte zip.
        assert upload["with"].get("if-no-files-found") == "error"

    def test_creates_github_release(self, build_steps):
        release = _step_named(build_steps, "Create / Update GitHub Release")
        assert release is not None
        assert release["uses"].startswith("softprops/action-gh-release@")
        assert "files" in release["with"]
        assert release["with"].get("fail_on_unmatched_files") is True


# ===========================================================================
# TestRawText
# ===========================================================================


class TestRawText:
    """A few invariants that are easier to assert as substrings."""

    def test_workflow_does_not_disable_default_status_checks(self, workflow_text):
        # Catches accidental `--no-verify` style escapes.
        assert "--no-verify" not in workflow_text

    def test_artifact_name_includes_tag(self, workflow_text):
        assert "Neloaica-${{ github.ref_name }}-windows" in workflow_text


# ===========================================================================
# TestManifestUpdateStep (PR #7)
# ===========================================================================


class TestManifestUpdateStep:
    """Guards around the post-release manifest-update step.

    These tests pin the structure introduced by PR #7: after the
    GitHub Release is created, the workflow computes the SHA-256 of
    the artefact, runs ``scripts/update_manifest.py``, and pushes the
    refreshed ``update-manifest.json`` to ``main``.
    """

    def test_sha_step_exists(self, build_steps):
        step = _step_named(build_steps, "Compute artefact SHA-256")
        assert step is not None, "Missing SHA-256 step after release publish"
        assert step.get("id") == "sha"
        assert "Get-FileHash" in step["run"]
        assert "SHA256" in step["run"]
        assert "GITHUB_OUTPUT" in step["run"]

    def test_manifest_update_step_exists(self, build_steps):
        step = _step_named(build_steps, "Update update-manifest.json")
        assert step is not None
        # Must never roll back a successful release if the push fails.
        assert step.get("continue-on-error") is True

    def test_manifest_step_runs_script_with_required_args(self, build_steps):
        step = _step_named(build_steps, "Update update-manifest.json")
        assert step is not None
        run = step["run"]
        assert "scripts/update_manifest.py" in run
        assert "--version" in run
        assert "--channel stable" in run
        assert "--sha256" in run
        assert "--owner" in run
        assert "--repo" in run
        assert "--asset" in run
        assert "--manifest update-manifest.json" in run

    def test_manifest_step_uses_sha_output(self, build_steps):
        step = _step_named(build_steps, "Update update-manifest.json")
        assert step is not None
        # The output reference ties the step to the previous SHA step.
        assert "steps.sha.outputs.sha256" in step["run"]

    def test_manifest_step_commits_to_main(self, build_steps):
        step = _step_named(build_steps, "Update update-manifest.json")
        assert step is not None
        run = step["run"]
        assert "git checkout main" in run
        assert "git push origin main" in run
        assert "github-actions[bot]" in run

    def test_manifest_step_uses_skip_ci_in_commit(self, build_steps):
        step = _step_named(build_steps, "Update update-manifest.json")
        assert step is not None
        # Avoid an infinite loop where the manifest commit triggers CI.
        assert "[skip ci]" in step["run"]

    def test_manifest_step_runs_after_release_publish(self, build_steps):
        names = [s.get("name", "") for s in build_steps]
        release_idx = next(i for i, n in enumerate(names) if "GitHub Release" in n)
        sha_idx = next(i for i, n in enumerate(names) if "SHA-256" in n)
        manifest_idx = next(i for i, n in enumerate(names) if "update-manifest.json" in n)
        assert release_idx < sha_idx < manifest_idx

    def test_manifest_step_checks_for_changes_via_lastexitcode(self, build_steps):
        # PowerShell does not expose native exit codes as booleans;
        # the workflow must check $LASTEXITCODE explicitly.
        step = _step_named(build_steps, "Update update-manifest.json")
        assert step is not None
        assert "$LASTEXITCODE" in step["run"]
