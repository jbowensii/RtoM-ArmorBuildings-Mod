"""Reusable log panel widget and stdout capture for GUI tabs."""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import QTextEdit


class _SignalBridge(QObject):
    """Thread-safe bridge: emits a signal so the QTextEdit is updated
    on the GUI thread even when the log record originates from a worker."""
    append_text = Signal(str)


class LogPanelHandler(logging.Handler):
    """Logging handler that appends formatted records to a QTextEdit."""

    def __init__(self, text_edit: QTextEdit) -> None:
        super().__init__()
        self._bridge = _SignalBridge()
        self._bridge.append_text.connect(text_edit.append)

    def emit(self, record: logging.LogRecord) -> None:
        self._bridge.append_text.emit(self.format(record))


class StdoutCapture:
    """Context manager that redirects *sys.stdout* writes to a QTextEdit."""

    def __init__(self, text_edit: QTextEdit) -> None:
        self._text_edit = text_edit
        self._bridge = _SignalBridge()
        self._bridge.append_text.connect(text_edit.append)
        self._old_stdout = sys.stdout

    def write(self, text: str) -> None:
        if text.strip():
            self._bridge.append_text.emit(text.rstrip())

    def flush(self) -> None:
        pass

    def __enter__(self) -> StdoutCapture:
        self._old_stdout = sys.stdout
        sys.stdout = self
        return self

    def __exit__(self, *args: object) -> None:
        sys.stdout = self._old_stdout
