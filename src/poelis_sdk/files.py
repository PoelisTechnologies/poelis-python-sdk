from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import NamedTuple

import httpx

from ._transport import Transport
from .exceptions import UploadError
from .models import UploadedFile

MAX_UPLOAD_BYTES = 5 * 1024 * 1024 * 1024

_SLOW_BYTES_PER_SECOND = 256 * 1024
_UPLOAD_TIMEOUT_CAP_SECONDS = 7200.0


class FilesClient:
    def __init__(self, transport: Transport) -> None:
        self._t = transport

    def upload(
        self,
        path: str | Path,
        *,
        item_id: str | None = None,
        property_id: str | None = None,
        property_type: str | None = None,
        allow_duplicate: bool = False,
    ) -> UploadedFile:
        """Upload ``path`` and link it to an item or a property.

        The file is measured locally first. An empty file or a file over
        5 GiB is refused before any request. Bytes go to the signed storage
        URL, not through the API process.

        Args:
            path: Filesystem path of the file to upload.
            item_id: Item that should own the file.
            property_id: Property that should own the file.
            property_type: Property type required with ``property_id``.
            allow_duplicate: When false, the API rejects a file whose size
                and content type already exist in the workspace.

        Returns:
            The stored file identifiers and size reported by the API.
        """

        prepared = prepare_upload(path)
        target = _target_body(
            item_id=item_id,
            property_id=property_id,
            property_type=property_type,
        )
        initiate = {
            **target,
            "filename": prepared.filename,
            "content_type": prepared.content_type,
            "size_bytes": prepared.size_bytes,
            "allow_duplicate": allow_duplicate,
        }
        started = self._t.post_json("/v1/storage/uploads/signed-put", initiate, retry=False).json()
        upload_url = started["upload_url"]
        object_path = started["object_path"]
        required_headers = started["required_headers"]
        with prepared.path.open("rb") as handle:
            self._t.put_stream(
                upload_url,
                handle,
                required_headers,
                _upload_timeout(prepared.size_bytes),
            )

        completed = self._t.post_json(
            "/v1/storage/uploads/complete",
            {
                **target,
                "object_path": object_path,
                "expected_size_bytes": prepared.size_bytes,
                "expected_content_type": required_headers["Content-Type"],
                "allow_duplicate": allow_duplicate,
            },
            retry=False,
        ).json()
        return UploadedFile.model_validate(completed)


def prepare_upload(path: str | Path) -> PreparedUpload:
    file_path = Path(path)
    if not file_path.is_file():
        raise UploadError(f"Not a file: {file_path}")
    filename = file_path.name
    size_bytes = file_path.stat().st_size
    if size_bytes <= 0:
        raise UploadError("File is empty")
    if size_bytes > MAX_UPLOAD_BYTES:
        raise UploadError(
            f"File too large: {size_bytes} bytes exceeds limit {MAX_UPLOAD_BYTES} bytes"
        )
    return PreparedUpload(
        path=file_path,
        filename=filename,
        size_bytes=size_bytes,
        content_type=_content_type_for_name(filename),
    )


def _upload_timeout(size_bytes: int) -> httpx.Timeout:
    seconds = min(
        _UPLOAD_TIMEOUT_CAP_SECONDS,
        60.0 + (size_bytes / _SLOW_BYTES_PER_SECOND),
    )
    return httpx.Timeout(connect=30.0, read=seconds, write=seconds, pool=30.0)


class PreparedUpload(NamedTuple):
    path: Path
    filename: str
    size_bytes: int
    content_type: str


def _content_type_for_name(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".msg"):
        return "application/vnd.ms-outlook"
    guessed, _encoding = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def _target_body(
    *,
    item_id: str | None,
    property_id: str | None,
    property_type: str | None,
) -> dict[str, str]:
    if item_id is not None and property_id is None and property_type is None:
        return {"item_id": item_id}
    if item_id is None and property_id and property_type:
        return {"property_id": property_id, "property_type": property_type}
    raise UploadError("Pass item_id, or both property_id and property_type")
