from pathlib import Path

from app.services.service_logs import read_log_chunk


def test_read_log_chunk_tail(tmp_path: Path):
    log_file = tmp_path / "sample.log"
    log_file.write_text("line-1\nline-2\nline-3\n", encoding="utf-8")

    from app.core.config import settings

    original = settings.house_diy_vault_log_path
    settings.house_diy_vault_log_path = str(log_file)
    try:
        chunk = read_log_chunk("vault", offset=0, tail_lines=2)
    finally:
        settings.house_diy_vault_log_path = original

    assert chunk["exists"] is True
    assert chunk["lines"] == ["line-2", "line-3"]
    assert chunk["offset"] == log_file.stat().st_size
