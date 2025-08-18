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

from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib
import json
import logging
from pathlib import Path
import boto3 
from botocore.exceptions import ClientError 
import paramiko 
from paramiko.ssh_exception import SSHException 
import os

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

    def _compute_origin_hash(self, filename: str, download_date: str, download_url: str) -> str:
        """Compute a hash for the metadata to name the origin JSON file."""
        to_hash = f"{filename}{download_date}{download_url}".encode("utf-8")
        return hashlib.sha256(to_hash).hexdigest()

    def _build_metadata(self, sha256: str, filename: str, download_date: str, download_url: str) -> dict:
        """Build metadata dictionary for JSON storage."""
        return {
            "sha256": sha256,
            "filename": filename,
            "download_date": download_date,
            "url": download_url
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
        """Store content with its metadata. Return a Download object on success. Raise an exception on error."""
        pass

    @abstractmethod
    def find(self, download_url: str = None, filename: str = None, download_date: str = None):
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
            sha256 = str(content_path.parent.relative_to(self.root_path)).replace("/", "")
            origin_files = list(content_path.parent.glob("origin-*.json"))
            for origin_file in origin_files:
                try:
                    with open(origin_file, "r") as f:
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
                    with open(origin_files[0], "r") as f:
                        data = json.load(f)
                    return Download(**data)
                except Exception as e:
                    logger.error(f"Error reading origin file for {sha256_checksum}: {e}")
        return None

    def put(self, content: bytes, download_url: str, download_date: str, filename: str):
        """Store the content and its metadata."""
        sha256 = self._compute_sha256(content)
        content_path = self._get_content_path(sha256)
        content_path.mkdir(parents=True, exist_ok=True)

        content_file = content_path / "content"
        if not content_file.exists():
            try:
                with open(content_file, 'wb') as f:
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
            with open(origin_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            raise Exception(f"Failed to write metadata to {origin_path}: {e}")

        return Download(**metadata)

    def find(self, download_url: str = None, filename: str = None, download_date: str = None):
        """Find a download based on metadata."""
        if not (download_url or filename or download_date):
            return None
        for content_path in self.root_path.rglob("origin-*.json"):
            try:
                with open(content_path, "r") as f:
                    data = json.load(f)
                if (
                    (download_url is None or data.get("url") == download_url) and
                    (filename is None or data.get("filename") == filename) and
                    (download_date is None or data.get("download_date") == download_date)
                ):
                    return Download(**data)
            except Exception as e:
                logger.error(f"Error reading {content_path}: {e}")
        return None

class S3LikeProvider(DownloadStore):
    def __init__(self, bucket_name: str, aws_userid: str, aws_apikey: str, other_aws_credentials: dict):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_userid,
            aws_secret_access_key=aws_apikey,
            **(other_aws_credentials or {})
        )

    def _get_content_path(self, sha256: str) -> str:
        """S3 key like 59/4c/67/<sha256>/"""
        return f"{sha256[:2]}/{sha256[2:4]}/{sha256[4:]}/"

    def list(self):
        """List all stored downloads."""
        downloads = []
        try:
            paginator = self.s3_client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.bucket_name):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if key.endswith(".json"):
                        try:
                            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
                            data = json.loads(response["Body"].read())
                            downloads.append(Download(**data))
                        except Exception as e:
                            logger.error(f"Error reading S3 object {key}: {e}")
        except ClientError as e:
            logger.error(f"Failed to list S3 objects: {e}")
        return downloads

    def get(self, sha256_checksum: str):
        """Retrieve a Download object for the given SHA256 hash."""
        prefix = self._get_content_path(sha256_checksum)
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=1
            )
            if "Contents" in response:
                key = response["Contents"][0]["Key"]
                obj_response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
                data = json.loads(obj_response["Body"].read())
                return Download(**data)
        except ClientError as e:
            logger.error(f"Failed to get S3 object for {sha256_checksum}: {e}")
        return None

    def put(self, content: bytes, download_url: str, download_date: str, filename: str):
        """Store the content and its metadata."""
        sha256 = self._compute_sha256(content)
        content_key = self._get_content_path(sha256) + "content"
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=content_key)
            logger.info(f"Content already exists for {sha256}")
        except ClientError:
            try:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=content_key,
                    Body=content,
                )
            except ClientError as e:
                raise Exception(f"Failed to write content to S3 {content_key}: {e}")

        origin_hash = self._compute_origin_hash(filename, download_date, download_url)
        origin_filename = f"origin-{origin_hash}.json"
        origin_key = self._get_content_path(sha256) + origin_filename

        metadata = self._build_metadata(sha256, filename, download_date, download_url)
        metadata_json = json.dumps(metadata, indent=2).encode("utf-8")
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=origin_key,
                Body=metadata_json,
            )
        except ClientError as e:
            raise Exception(f"Failed to write metadata to S3 {origin_key}: {e}")

        return Download(**metadata)

    def find(self, download_url: str = None, filename: str = None, download_date: str = None):
        """Find a download based on metadata."""
        if not (download_url or filename or download_date):
            return None
        try:
            paginator = self.s3_client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.bucket_name):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if key.endswith(".json"):
                        try:
                            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
                            data = json.loads(response["Body"].read())
                            if (
                                (download_url is None or data.get("url") == download_url) and
                                (filename is None or data.get("filename") == filename) and
                                (download_date is None or data.get("download_date") == download_date)
                            ):
                                return Download(**data)
                        except Exception as e:
                            logger.error(f"Error reading S3 object {key}: {e}")
        except ClientError as e:
            logger.error(f"Failed to find in S3: {e}")
        return None

class SftpProvider(DownloadStore):
    def __init__(self, host: str, root_path: str, ssh_credentials: dict):
        self.host = host
        self.root_path = Path(root_path)
        self.ssh_credentials = ssh_credentials
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh.connect(
                hostname=host,
                username=ssh_credentials.get("username"),
                password=ssh_credentials.get("password"),
            )
            self.sftp = self.ssh.open_sftp()
        except SSHException as e:
            raise Exception(f"Failed to connect to SFTP server {host}: {e}")

    def _get_content_path(self, sha256: str) -> str:
        """SFTP path like 59/4c/67/<sha256>/"""
        return str(self.root_path / sha256[:2] / sha256[2:4] / sha256[4:])

    def list(self):
        """List all stored downloads."""
        downloads = []
        try:
            for root, _, files in self._sftp_walk(self.root_path):
                for filename in files:
                    if filename.endswith(".json"):
                        file_path = os.path.join(root, filename)
                        try:
                            with self.sftp.open(file_path, "r") as f:
                                data = json.load(f)
                            downloads.append(Download(**data))
                        except Exception as e:
                            logger.error(f"Error reading SFTP file {file_path}: {e}")
        except SSHException as e:
            logger.error(f"Failed to list SFTP files: {e}")
        return downloads

    def _sftp_walk(self, path):
        """Recursively walk SFTP directory."""
        path = str(path)
        for entry in self.sftp.listdir_attr(path):
            full_path = os.path.join(path, entry.filename)
            if stat.S_ISDIR(entry.st_mode):
                yield from self._sftp_walk(full_path)
            else:
                yield path, [], [entry.filename]

    def get(self, sha256_checksum: str):
        """Retrieve a Download object for the given SHA256 hash."""
        content_path = self._get_content_path(sha256_checksum)
        try:
            files = self.sftp.listdir(content_path)
            origin_files = [f for f in files if f.startswith("origin-") and f.endswith(".json")]
            if origin_files:
                with self.sftp.open(os.path.join(content_path, origin_files[0]), "r") as f:
                    data = json.load(f)
                return Download(**data)
        except SSHException as e:
            logger.error(f"Failed to get SFTP file for {sha256_checksum}: {e}")
        return None

    def put(self, content: bytes, download_url: str, download_date: str, filename: str):
        """Store the content and its metadata."""
        sha256 = self._compute_sha256(content)
        content_path = self._get_content_path(sha256)
        try:
            self.sftp.mkdir(content_path)
        except SSHException:
            pass

        content_file = os.path.join(content_path, "content")
        try:
            self.sftp.stat(content_file)
            logger.info(f"Content already exists for {sha256}")
        except SSHException:
            try:
                with self.sftp.open(content_file, 'wb') as f:
                    f.write(content)
            except SSHException as e:
                raise Exception(f"Failed to write content to SFTP {content_file}: {e}")

        origin_hash = self._compute_origin_hash(filename, download_date, download_url)
        origin_filename = f"origin-{origin_hash}.json"
        origin_path = os.path.join(content_path, origin_filename)
        try:
            self.sftp.stat(origin_path)
            raise Exception(f"Origin {origin_filename} already exists")
        except SSHException:
            metadata = self._build_metadata(sha256, filename, download_date, download_url)
            metadata_json = json.dumps(metadata, indent=2).encode("utf-8")
            try:
                with self.sftp.open(origin_path, 'wb') as f:
                    f.write(metadata_json)
            except SSHException as e:
                raise Exception(f"Failed to write metadata to SFTP {origin_path}: {e}")

        return Download(**metadata)

    def find(self, download_url: str = None, filename: str = None, download_date: str = None):
        """Find a download based on metadata."""
        if not (download_url or filename or download_date):
            return None
        try:
            for root, _, files in self._sftp_walk(self.root_path):
                for filename in files:
                    if filename.endswith(".json"):
                        file_path = os.path.join(root, filename)
                        try:
                            with self.sftp.open(file_path, "r") as f:
                                data = json.load(f)
                            if (
                                (download_url is None or data.get("url") == download_url) and
                                (filename is None or data.get("filename") == filename) and
                                (download_date is None or data.get("download_date") == download_date)
                            ):
                                return Download(**data)
                        except Exception as e:
                            logger.error(f"Error reading SFTP file {file_path}: {e}")
        except SSHException as e:
            logger.error(f"Failed to find in SFTP: {e}")
        return None