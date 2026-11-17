from __future__ import annotations

from datetime import datetime, timezone
import mimetypes
import os
import tempfile
from pathlib import Path
from typing import Literal, NamedTuple

import httpx

from ._transport import Transport
from .exceptions import ClientError, FileNotDownloadableError, NotFoundError, UploadError
from .models import File, UploadedFile

MAX_UPLOAD_BYTES = 5 * 1024 * 1024 * 1024

_UPLOAD_STALL_TIMEOUT_SECONDS = 60.0

_PRODUCT_BASELINE_QUERY = """
query SdkProductBaselineVersion($id: ID!) {
  product(id: $id) { id baselineVersionNumber }
}
"""

_LIST_FILES_QUERY = """
query SdkListFiles(
  $itemId: ID
  $propertyId: ID
  $version: VersionInput
  $includePropertyFiles: Boolean
) {
  files(
    itemId: $itemId
    propertyId: $propertyId
    version: $version
    includePropertyFiles: $includePropertyFiles
  ) {
    files {
      id
      originalFileName
      userTitle
      revision
      code
      contentType
      description
      sizeBytes
      uploadedAt
      uploadedBy { id userName imageUrl }
      deleted
      itemId
      propertyId
    }
  }
}
"""


class FilesClient:
    def __init__(self, transport: Transport) -> None:
        self._t = transport

    def list(
        self,
        *,
        item_id: str | None = None,
        property_id: str | None = None,
        version: int | Literal["baseline"] | None = None,
        include_property_files: bool = False,
    ) -> list[File]:
        """List the files linked to an item or to a property.

        Pass exactly one of ``item_id`` or ``property_id``. The full list is
        returned in one call; there is no paging for these two scopes.

        Args:
            item_id: Item whose files to list.
            property_id: Property whose files to list.
            version: ``None`` for the draft, a product version number, or
                ``"baseline"`` for the product's baseline version. An item or
                property id from any version works; the files returned are the
                ones linked at the requested version.
            include_property_files: With ``item_id``, also return the files
                linked to the item's properties.

        Returns:
            The files, newest upload first. A version with no baseline set, or
            an id that does not exist, returns an empty list.
        """

        if (item_id is None) == (property_id is None):
            raise ValueError("Pass exactly one of item_id or property_id")
        if include_property_files and item_id is None:
            raise ValueError("include_property_files only applies with item_id")
        variables: dict[str, object] = {
            "itemId": item_id,
            "propertyId": property_id,
            "version": _version_variable(version),
        }
        if item_id is not None:
            variables["includePropertyFiles"] = include_property_files
        payload = self._t.graphql(_LIST_FILES_QUERY, variables).json()
        if "errors" in payload:
            raise RuntimeError(str(payload["errors"]))
        files = ((payload.get("data") or {}).get("files") or {}).get("files") or []
        parsed = [File.model_validate(row) for row in files]
        if include_property_files:
            epoch = datetime.min.replace(tzinfo=timezone.utc)
            parsed.sort(key=lambda file: file.uploaded_at or epoch, reverse=True)
        return parsed

    def download(
        self,
        file_id: str,
        dest: str | Path,
        *,
        product_id: str | None = None,
        version: int | Literal["baseline"] | None = None,
    ) -> Path:
        """Download a file's bytes to ``dest``.

        The API returns a short-lived signed URL and the bytes are streamed
        from storage without the API key. They are written to a temporary file
        next to ``dest`` and moved into place only when complete, so ``dest``
        never holds a partial file.

        Args:
            file_id: File to download, for example ``File.id`` from ``list``.
            dest: Path of the file to write. An existing file is replaced.
                The parent directory must exist.
            product_id: Product whose version to read. Required with
                ``version``.
            version: ``None`` for the current file, a product version number,
                or ``"baseline"`` for the product's baseline version.

        Returns:
            The path that was written.

        Raises:
            FileNotDownloadableError: The file has no stored bytes: a
                document written inside Poelis, or, with ``version``, a file
                that was not in that version.
            NotFoundError: The file, or the requested version of it, does
                not exist or is not visible to this API key.
        """

        target = Path(dest)
        if target.is_dir():
            raise ValueError(f"dest is a directory, pass a file path: {target}")
        if not target.parent.is_dir():
            raise ValueError(f"Directory does not exist: {target.parent}")
        version_number = self._version_number(product_id, version)
        body: dict[str, object] = {}
        if version_number is not None:
            body = {"product_id": product_id, "version_number": version_number}
        try:
            url = self._t.post_json(
                f"/v1/storage/objects/{file_id}/download-url", body
            ).json()["url"]
        except ClientError as exc:
            if exc.error_code == "no_blob":
                message = (
                    f"File {file_id} has no stored bytes to download. Documents "
                    "written inside Poelis cannot be downloaded through the SDK yet."
                )
                if version_number is not None:
                    message = (
                        f"File {file_id} has no stored bytes at version {version_number}. "
                        "Either it was not in that version, or it is a document written "
                        "inside Poelis, which cannot be downloaded through the SDK yet."
                    )
                raise FileNotDownloadableError(
                    exc.status_code,
                    message=message,
                    error_code=exc.error_code,
                ) from exc
            raise

        handle, part_name = tempfile.mkstemp(
            dir=target.parent, prefix=f".{target.name}.", suffix=".part"
        )
        part = Path(part_name)
        try:
            with os.fdopen(handle, "wb") as out, self._t.get_stream(
                url, _transfer_timeout()
            ) as response:
                for chunk in response.iter_bytes():
                    out.write(chunk)
            os.replace(part, target)
        except BaseException:
            part.unlink(missing_ok=True)
            raise
        return target

    def _version_number(
        self, product_id: str | None, version: int | str | None
    ) -> int | None:
        value = _version_variable(version)
        if value is None:
            return None
        if not product_id:
            raise ValueError("product_id is required when version is given")
        if value != "baseline":
            return int(value)
        payload = self._t.graphql(_PRODUCT_BASELINE_QUERY, {"id": product_id}).json()
        if "errors" in payload:
            raise RuntimeError(str(payload["errors"]))
        product = (payload.get("data") or {}).get("product")
        if not product:
            raise NotFoundError(404, message=f"Product not found: {product_id}")
        baseline = product.get("baselineVersionNumber")
        if baseline is None:
            raise NotFoundError(404, message=f"Product {product_id} has no baseline version")
        return int(baseline)

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
                _transfer_timeout(),
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


def _version_variable(version: int | str | None) -> int | str | None:
    if version is None:
        return None
    if isinstance(version, bool):
        raise ValueError("version must be an integer, 'baseline' or None")
    if isinstance(version, int):
        if version < 0:
            raise ValueError("version must not be negative")
        return version
    if isinstance(version, str) and version.strip().lower() == "baseline":
        return "baseline"
    raise ValueError("version must be an integer, 'baseline' or None")


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


def _transfer_timeout() -> httpx.Timeout:
    return httpx.Timeout(
        connect=30.0,
        read=_UPLOAD_STALL_TIMEOUT_SECONDS,
        write=_UPLOAD_STALL_TIMEOUT_SECONDS,
        pool=30.0,
    )


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
