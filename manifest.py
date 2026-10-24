"""Small local journal: claim durably before HTTP, never automatically retry a claim."""

import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import tempfile


class CampaignManifest:
    def __init__(self, directory, campaign_id, binding):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", campaign_id):
            raise ValueError(
                "Campaign ID must contain 1 to 64 letters, digits, underscores or hyphens"
            )
        self.directory = Path(directory)
        self.path = self.directory / (campaign_id + ".json")
        self.lock = self.directory / (campaign_id + ".lock")
        self.binding = binding
        self.data = None

    def __enter__(self):
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        # A stale lock intentionally blocks sending until the operator verifies no process remains.
        fd = os.open(self.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        try:
            if self.path.exists():
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
                if (
                    self.data.get("binding") != self.binding
                    or self.data.get("version") != 1
                    or not isinstance(self.data.get("salt"), str)
                    or len(self.data["salt"]) != 64
                    or not isinstance(self.data.get("entries"), dict)
                    or any(
                        v not in {"pending", "accepted", "rejected", "unknown"}
                        for v in self.data["entries"].values()
                    )
                ):
                    raise ValueError(
                        "Campaign journal does not match this preflight or is invalid"
                    )
            else:
                self.data = {
                    "version": 1,
                    "binding": self.binding,
                    "salt": secrets.token_hex(32),
                    "entries": {},
                }
                self._save()
            return self
        except BaseException:
            self.lock.unlink()
            raise

    def __exit__(self, *_):
        self.lock.unlink()

    def reference(self, phone):
        return hmac.new(
            self.data["salt"].encode(), phone.encode(), hashlib.sha256
        ).hexdigest()

    def status(self, phone):
        return self.data["entries"].get(self.reference(phone))

    def record(self, phone, status):
        self.data["entries"][self.reference(phone)] = status
        self._save()

    def _save(self):
        fd, temporary = tempfile.mkstemp(
            dir=self.directory, prefix=".journal-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(self.data, stream, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            if os.name == "posix":
                directory_fd = os.open(self.directory, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
