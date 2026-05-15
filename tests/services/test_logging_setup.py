"""Tests for ``src/services/logging_setup.py``.

Coverage targets:
  * setup_logging() creates the logs directory if missing
  * The configured handler actually writes log lines to disk
  * Calling setup_logging() twice does not stack handlers
  * Foreign handlers (e.g. pytest's) are not removed by reset/setup
  * RotatingFileHandler rolls files when ``maxBytes`` is exceeded
  * Default location matches :func:`src.paths.get_logs_dir`

Each test uses ``tmp_path`` so the real ``%LOCALAPPDATA%\\Neloaica\\logs``
folder is never touched.
"""

import logging
from pathlib import Path

import pytest

from src.services import logging_setup


@pytest.fixture(autouse=True)
def _clean_root_logger():
    """Snapshot/restore root handlers so tests don't leak into each other."""
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    yield
    logging_setup.reset_logging()
    # Restore exactly what was there before this test.
    for h in list(root.handlers):
        if h not in saved_handlers:
            root.removeHandler(h)
    for h in saved_handlers:
        if h not in root.handlers:
            root.addHandler(h)
    root.setLevel(saved_level)


# ===========================================================================
# TestSetupLoggingFilesystem
# ===========================================================================


class TestSetupLoggingFilesystem:
    def test_creates_logs_dir(self, tmp_path):
        target = tmp_path / "logs"
        assert not target.exists()
        log_file = logging_setup.setup_logging(target)
        assert target.is_dir()
        assert log_file == target / logging_setup.DEFAULT_LOG_FILENAME

    def test_works_with_existing_dir(self, tmp_path):
        target = tmp_path / "logs"
        target.mkdir()
        log_file = logging_setup.setup_logging(target)
        assert log_file.parent == target

    def test_returns_path_instance(self, tmp_path):
        log_file = logging_setup.setup_logging(tmp_path / "logs")
        assert isinstance(log_file, Path)

    def test_default_location_uses_paths_module(self, tmp_path, monkeypatch):
        from src import paths

        monkeypatch.setattr(paths, "get_user_data_dir", lambda: tmp_path)
        log_file = logging_setup.setup_logging()
        assert log_file == tmp_path / "logs" / logging_setup.DEFAULT_LOG_FILENAME


# ===========================================================================
# TestSetupLoggingHandlers
# ===========================================================================


class TestSetupLoggingHandlers:
    def test_writes_log_line_to_file(self, tmp_path):
        log_file = logging_setup.setup_logging(tmp_path / "logs")
        logging.getLogger("test").info("hello world")
        for h in logging.getLogger().handlers:
            h.flush()
        contents = log_file.read_text(encoding="utf-8")
        assert "hello world" in contents
        assert "[INFO]" in contents
        assert "test:" in contents

    def test_idempotent_no_duplicate_handlers(self, tmp_path):
        logging_setup.setup_logging(tmp_path / "logs")
        first_count = sum(1 for h in logging.getLogger().handlers if logging_setup._is_managed(h))
        logging_setup.setup_logging(tmp_path / "logs")
        second_count = sum(1 for h in logging.getLogger().handlers if logging_setup._is_managed(h))
        assert first_count == 1
        assert second_count == 1

    def test_idempotent_does_not_duplicate_log_lines(self, tmp_path):
        log_file = logging_setup.setup_logging(tmp_path / "logs")
        logging_setup.setup_logging(tmp_path / "logs")  # second call
        logging.getLogger("dup").info("once")
        for h in logging.getLogger().handlers:
            h.flush()
        contents = log_file.read_text(encoding="utf-8")
        assert contents.count("once") == 1

    def test_does_not_remove_foreign_handlers(self, tmp_path):
        foreign = logging.NullHandler()
        logging.getLogger().addHandler(foreign)
        try:
            logging_setup.setup_logging(tmp_path / "logs")
            assert foreign in logging.getLogger().handlers
        finally:
            logging.getLogger().removeHandler(foreign)

    def test_reset_removes_only_managed_handlers(self, tmp_path):
        foreign = logging.NullHandler()
        logging.getLogger().addHandler(foreign)
        try:
            logging_setup.setup_logging(tmp_path / "logs")
            logging_setup.reset_logging()
            handlers = logging.getLogger().handlers
            managed = [h for h in handlers if logging_setup._is_managed(h)]
            assert managed == []
            assert foreign in handlers
        finally:
            logging.getLogger().removeHandler(foreign)


# ===========================================================================
# TestRotation
# ===========================================================================


class TestRotation:
    def test_rotates_when_max_bytes_exceeded(self, tmp_path):
        log_file = logging_setup.setup_logging(tmp_path / "logs", max_bytes=200, backup_count=3)
        logger = logging.getLogger("rot")
        # Each line is ~80 bytes with the formatter, so a few lines will roll.
        for i in range(20):
            logger.info("filler line number %d - some extra padding xxxxxxxxxxxx", i)
        for h in logging.getLogger().handlers:
            h.flush()
        rolled = sorted(log_file.parent.glob(log_file.name + "*"))
        # Active file plus at least one rolled file.
        assert any(p.name != log_file.name for p in rolled)
        assert log_file.exists()


# ===========================================================================
# TestLevels
# ===========================================================================


class TestLevels:
    def test_level_param_applied_to_handler(self, tmp_path):
        logging_setup.setup_logging(tmp_path / "logs", level=logging.DEBUG)
        managed = [h for h in logging.getLogger().handlers if logging_setup._is_managed(h)]
        assert managed and managed[0].level == logging.DEBUG

    def test_level_does_not_lower_existing_more_permissive_root(self, tmp_path):
        logging.getLogger().setLevel(logging.DEBUG)
        logging_setup.setup_logging(tmp_path / "logs", level=logging.WARNING)
        # Root keeps DEBUG even though we asked for WARNING — we never raise it
        # above what's already configured.
        assert logging.getLogger().getEffectiveLevel() == logging.DEBUG
