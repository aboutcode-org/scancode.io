# scanpipe/archiving.py
# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
# The ScanCode.io software is licensed under the Apache License version 2.0.
# Data generated with ScanCode.io is provided as-is without warranties.
# ScanCode is a trademark of nexB Inc.
#
# You may not use this software except in compliance with the License.
# You may obtain a copy of the License at: http://apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#
# Data Generated with ScanCode.io is provided on an "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, either express or implied. No content created from
# ScanCode.io should be considered or used as legal advice. Consult an Attorney
# for any legal advice.
#
# ScanCode.io is a free software code scanning tool from nexB Inc. and others.
# Visit https://github.com/aboutcode-org/scancode.io for support and download.

import hashlib
import json
import logging
import os
import stat
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class Download:
    sha256: str
    download_date: str
    download_url: str
    filename: str


class DownloadStore(ABC):
    def _compute_sha256(self, content: bytes) -> str:
        """Compute SHA256 hash for content."""
        return hashlib.sha256(content).hexdigest()

    def _compute_origin_hash(
        self, filename: str, download_date: str, download_url: str
    ) -> str:
        """Compute a hash for the metadata to name the origin JSON file."""
        to_hash = f"{filename}{download_date}{download_url}".encode()
        return hashlib.sha256(to_hash).hexdigest()

    def _build_metadata(
        self, sha256: str, filename: str, download_date: str, download_url: str
    ) -> dict:
        """Build metadata dictionary for JSON storage."""
        return {
            "sha256": sha256,
            "filename": filename,
            "download_date": download_date,
            "download_url": download_url,
        }

    @abstractmethod
    def _get_content_path(self, sha256: str) -> str:
        """Get the storage path/key for the content based on SHA256."""
        pass

    @abstractmethod
    def list(self):
        """Return an iterable of all stored downloads."""
        pass

    @abstractmethod
    def get(self, sha256_checksum: str):
        """Return a Download object for this checksum or None."""
        pass

    @abstractmethod
    def put(self, content: bytes, download_url: str, download_date: str, filename: str):
        """
        Store content with its metadata. Return a Download object on success.
        Raise an exception on error.
        """
        pass

    @abstractmethod
    def find(
        self, download_url: str = None, filename: str = None, download_date: str = None
    ):
        """Return a Download object matching the metadata or None."""
        pass


class LocalFilesystemProvider(DownloadStore):
    def __init__(self, root_path: Path):
        self.root_path = root_path

    def _get_content_path(self, sha256: str) -> Path:
        """Create a nested path like 59/4c/67/... based on the SHA256 hash."""
        return self.root_path / sha256[:2] / sha256[2:4] / sha256[4:]

    def list(self):
        """Return an iterable of all stored downloads."""
        downloads = []
        for content_path in self.root_path.rglob("content"):
            origin_files = list(content_path.parent.glob("origin-*.json"))
            for origin_file in origin_files:
                try:
                    with open(origin_file) as f:
                        data = json.load(f)
                    downloads.append(Download(**data))
                except Exception as e:
                    logger.error(f"Error reading {origin_file}: {e}")
        return downloads

    def get(self, sha256_checksum: str):
        """Retrieve a Download object for the given SHA256 hash."""
        content_path = self._get_content_path(sha256_checksum)
        if content_path.exists():
            origin_files = list(content_path.glob("origin-*.json"))
            if origin_files:
                try:
                    with open(origin_files[0]) as f:
                        data = json.load(f)
                    return Download(**data)
                except Exception as e:
                    logger.error(
                        f"Error reading origin file for {sha256_checksum}: {e}"
                    )
        return None

    def put(self, content: bytes, download_url: str, download_date: str, filename: str):
        """Store the content and its metadata."""
        sha256 = self._compute_sha256(content)
        content_path = self._get_content_path(sha256)
        content_path.mkdir(parents=True, exist_ok=True)

        content_file = content_path / "content"
        if not content_file.exists():
            try:
                with open(content_file, "wb") as f:
                    f.write(content)
            except Exception as e:
                raise Exception(f"Failed to write content to {content_file}: {e}")

        origin_hash = self._compute_origin_hash(filename, download_date, download_url)
        origin_filename = f"origin-{origin_hash}.json"
        origin_path = content_path / origin_filename
        if origin_path.exists():
            raise Exception(f"Origin {origin_filename} already exists")

        metadata = self._build_metadata(sha256, filename, download_date, download_url)
        try:
            with open(origin_path, "w") as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            raise Exception(f"Failed to write metadata to {origin_path}: {e}")

        return Download(**metadata)

    def find(
        self, download_url: str = None, filename: str = None, download_date: str = None
    ):
        """Find a download based on metadata."""
        if not (download_url or filename or download_date):
            return None
        for content_path in self.root_path.rglob("origin-*.json"):
            try:
                with open(content_path) as f:
                    data = json.load(f)
                if (
                    (download_url is None or data.get("url") == download_url)
                    and (filename is None or data.get("filename") == filename)
                    and (
                        download_date is None
                        or data.get("download_date") == download_date
                    )
                ):
                    return Download(**data)
            except Exception as e:
                logger.error(f"Error reading {content_path}: {e}")
        return None


