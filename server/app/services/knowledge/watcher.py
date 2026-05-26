from __future__ import annotations

import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from app.core.config import settings
from app.services.knowledge.indexer import get_knowledge_indexer

DEBOUNCE_SECONDS = 2.0
WATCH_DIRS = ("Cases", "References", "Templates")


class _VaultIndexHandler(FileSystemEventHandler):
    def __init__(self, vault_root: Path) -> None:
        super().__init__()
        self.vault_root = vault_root
        self._pending: dict[str, float] = {}
        self._lock = threading.Lock()

    def _schedule(self, path: str) -> None:
        if not path.endswith(".md"):
            return
        with self._lock:
            self._pending[path] = time.time()

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._schedule(event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._schedule(event.src_path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory or not event.src_path.endswith(".md"):
            return
        try:
            relative = str(Path(event.src_path).relative_to(self.vault_root))
        except ValueError:
            return
        get_knowledge_indexer().remove_document(relative)

    def flush_due(self) -> None:
        now = time.time()
        due_paths: list[str] = []
        with self._lock:
            for path, scheduled_at in list(self._pending.items()):
                if now - scheduled_at >= DEBOUNCE_SECONDS:
                    due_paths.append(path)
                    del self._pending[path]
        indexer = get_knowledge_indexer()
        for path in due_paths:
            indexer.index_markdown_file(Path(path))


class VaultWatcher:
    """Vault Markdown 变更监听，debounce 后增量 reindex"""

    def __init__(self, vault_root: Path | None = None) -> None:
        self.vault_root = vault_root or settings.vault_path()
        self._observer: Observer | None = None
        self._handler = _VaultIndexHandler(self.vault_root)
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None

    def _watch_loop(self) -> None:
        while not self._stop_event.is_set():
            self._handler.flush_due()
            time.sleep(0.5)

    def start(self) -> None:
        if self._observer is not None:
            return
        self.vault_root.mkdir(parents=True, exist_ok=True)
        observer = Observer()
        for directory in WATCH_DIRS:
            target = self.vault_root / directory
            target.mkdir(parents=True, exist_ok=True)
            observer.schedule(self._handler, str(target), recursive=True)
        observer.start()
        self._observer = observer
        self._worker = threading.Thread(target=self._watch_loop, daemon=True)
        self._worker.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=3)
            self._observer = None


_vault_watcher: VaultWatcher | None = None


def start_vault_watcher() -> VaultWatcher:
    global _vault_watcher
    if _vault_watcher is None:
        _vault_watcher = VaultWatcher()
        _vault_watcher.start()
    return _vault_watcher


def stop_vault_watcher() -> None:
    global _vault_watcher
    if _vault_watcher is not None:
        _vault_watcher.stop()
        _vault_watcher = None
