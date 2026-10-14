"""Versioned, offline retrieval of the published knowledge-base documents."""

from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import re
import unicodedata


MAX_DOCUMENT_BYTES = 2_000_000
MAX_CONTENT_CHARS = 1_000_000
_DATA = Path(__file__).parent / "data"
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


class DocumentUnavailableError(RuntimeError):
    """The document artifact is missing, unreadable or incompatible."""


class DocumentNotFoundError(LookupError):
    """No document has the requested canonical slug."""


def validate_document_request(slug, max_chars=None):
    if not isinstance(slug, str) or len(slug) > 128 or not _SLUG.fullmatch(slug):
        raise ValueError(
            "slug must be a canonical document slug of at most 128 characters"
        )
    if max_chars is not None and (
        type(max_chars) is not int or not 0 <= max_chars <= MAX_CONTENT_CHARS
    ):
        raise ValueError(
            f"max_chars must be an integer between 0 and {MAX_CONTENT_CHARS}"
        )


def _slugify(text):
    text = (
        unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    )
    text = re.sub(r"[\s_]+", "-", text)
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9-]", "", text)).strip("-")


def _headings(content):
    fence = None
    offset = 0
    for line in content.splitlines(keepends=True):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if marker:
            value = marker.group(1)
            if fence is None:
                fence = value
            elif value[0] == fence[0] and len(value) >= len(fence):
                fence = None
        elif fence is None:
            match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
            if match:
                yield len(match[1]), match[2], offset, offset + len(line)
        offset += len(line)


def _parse(filename, content):
    number, rest = filename[:-3].split("-", 1)
    slug = f"{int(number)}-{_slugify(rest)}"
    headings = list(_headings(content))
    title_heading = next((h for h in headings if h[0] == 1), None)
    if title_heading is None:
        raise DocumentUnavailableError("The knowledge document has no title")
    title = re.sub(r"^\d+\.\s*", "", title_heading[1])
    summary_lines = []
    for line in content[title_heading[3] :].splitlines():
        stripped = line.strip()
        if stripped.startswith(("#", "Tags:", "---")) or (
            not stripped and summary_lines
        ):
            break
        if stripped:
            summary_lines.append(stripped)
    tags = sorted(
        {
            re.sub(r"[.;:]+$", "", tag.strip().lower())
            for match in re.finditer(r"^Tags?:\s*(.+)$", content, re.I | re.M)
            for tag in match[1].split(",")
            if tag.strip()
        }
    )
    sections, hierarchy, used = [], [], set()
    for i, (level, text, start, end) in enumerate(headings):
        if level not in (2, 3):
            continue
        hierarchy = [h for h in hierarchy if h[0] < level]
        numbered = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?\s+(.+)$", text)
        nums = None
        if numbered:
            nums = "-".join(str(int(n)) for n in numbered.groups()[:3] if n is not None)
            anchor = nums + "-" + _slugify(numbered[4])
        else:
            anchor = _slugify(text)
            parent_nums = next((h[2] for h in reversed(hierarchy) if h[2]), None)
            if parent_nums:
                anchor = parent_nums + "-" + anchor
        base, suffix = anchor, 1
        while anchor in used:
            anchor = f"{base}-{suffix}"
            suffix += 1
        used.add(anchor)
        stop = next(
            (heading[2] for heading in headings[i + 1 :] if heading[0] <= 3),
            len(content),
        )
        sections.append(
            {
                "anchor": anchor,
                "title": text,
                "level": level,
                "parent_anchor": hierarchy[-1][1] if hierarchy else None,
                "content": content[end:stop].strip(),
                "start_char": end,
                "end_char": stop,
            }
        )
        hierarchy.append((level, anchor, nums))
    return {
        "slug": slug,
        "title": title,
        "summary": " ".join(summary_lines) or None,
        "tags": tags,
        "content": content,
        "sections": sections,
    }


class DocumentStore:
    def __init__(self, root=None, catalog=None):
        source_kind = "custom" if root is not None else "package"
        catalog = (
            Path(catalog) if catalog is not None else _DATA / "document-catalog.json"
        )
        if root is None:
            root = _DATA / "documents"
            source = Path(__file__).parent.parent
            if not root.exists() and (source / "pyproject.toml").is_file():
                root = source / "knowledge-base"
                source_kind = "checkout"
        root = Path(root).resolve()
        try:
            manifest = json.loads(catalog.read_text(encoding="utf-8"))
            names = manifest["documents"]
            if (
                type(manifest["schema_version"]) is not int
                or manifest["schema_version"] != 1
                or not isinstance(names, list)
                or not names
                or len(names) > 100
                or any(
                    not isinstance(n, str)
                    or not re.fullmatch(r"\d{2}-[a-z0-9-]+\.md", n)
                    for n in names
                )
                or len(set(names)) != len(names)
            ):
                raise ValueError("Invalid document catalog")
            documents = {}
            digest = sha256()
            for name in names:
                path = root / name
                if path.is_symlink() or path.resolve().parent != root:
                    raise ValueError("Invalid document source")
                with path.open("rb") as stream:
                    raw = stream.read(MAX_DOCUMENT_BYTES + 1)
                if len(raw) > MAX_DOCUMENT_BYTES:
                    raise ValueError("Oversized document")
                doc = _parse(name, raw.decode("utf-8"))
                if len(doc["content"]) > MAX_CONTENT_CHARS or doc["slug"] in documents:
                    raise ValueError("Invalid document")
                digest.update(name.encode() + b"\0" + sha256(raw).digest())
                documents[doc["slug"]] = doc
        except (OSError, ValueError, KeyError, TypeError, RecursionError):
            raise DocumentUnavailableError(
                "The knowledge document artifact is unavailable"
            ) from None
        self._documents = documents
        try:
            package_version = (
                version("mangrove-kb") if source_kind == "package" else None
            )
        except PackageNotFoundError:
            package_version = None
        self._source = {
            "package": "mangrove-kb",
            "package_version": package_version,
            "source_kind": source_kind,
            "document_schema_version": 1,
            "artifact_sha256": digest.hexdigest(),
        }

    def list_documents(self):
        documents = [
            {
                **{k: doc[k] for k in ("slug", "title", "summary", "tags")},
                "section_count": len(doc["sections"]),
            }
            for doc in self._documents.values()
        ]
        return deepcopy(
            {"total": len(documents), "documents": documents, "source": self._source}
        )

    def get_document(self, slug, max_chars=None):
        validate_document_request(slug, max_chars)
        if slug not in self._documents:
            raise DocumentNotFoundError("The knowledge document was not found")
        doc = deepcopy(self._documents[slug])
        full_length = len(doc["content"])
        returned = full_length if max_chars is None else min(max_chars, full_length)
        doc["content"] = doc["content"][:returned]
        for section in doc["sections"]:
            start, end = section.pop("start_char"), section.pop("end_char")
            section["content"] = doc["content"][start : min(end, returned)].strip()
            section["truncated"] = returned < end
        return {
            **doc,
            "source": dict(self._source),
            "content_length": full_length,
            "returned_chars": returned,
            "truncated": returned < full_length,
        }

    def get_document_page(
        self,
        slug,
        max_chars=None,
        *,
        offset=0,
        full=False,
        view="content",
        section_anchor=None,
    ):
        validate_document_request(slug, max_chars)
        if type(offset) is not int or not 0 <= offset <= MAX_CONTENT_CHARS:
            raise ValueError("offset must be an integer between 0 and 1000000")
        if type(full) is not bool:
            raise ValueError("full must be a boolean")
        if full and (offset or max_chars is not None):
            raise ValueError("full cannot be combined with offset or max_chars")
        if slug not in self._documents:
            raise DocumentNotFoundError("The knowledge document was not found")
        if view not in ("overview", "section", "content"):
            raise ValueError("view must be overview, section or content")
        if view == "section":
            if (
                not isinstance(section_anchor, str)
                or not section_anchor
                or len(section_anchor) > 256
            ):
                raise ValueError("section view requires a section_anchor")
        elif section_anchor is not None:
            raise ValueError("section_anchor requires section view")
        if view != "content" and full:
            raise ValueError("full is only supported for content view")
        if view == "overview" and (offset or max_chars is not None):
            raise ValueError("overview does not accept offset or max_chars")
        doc = self._documents[slug]
        body = doc["content"]
        selected_sections = doc["sections"]
        base = 0
        if view == "section":
            index = next(
                (
                    i
                    for i, section in enumerate(selected_sections)
                    if section["anchor"] == section_anchor
                ),
                None,
            )
            if index is None:
                raise DocumentNotFoundError("The knowledge section was not found")
            selected = selected_sections[index]
            stop = index + 1
            while (
                stop < len(selected_sections)
                and selected_sections[stop]["level"] > selected["level"]
            ):
                stop += 1
            selected_sections = selected_sections[index:stop]
            base = selected["start_char"]
            body = body[base : selected_sections[-1]["end_char"]]
        if view == "overview":
            body = ""
        length = len(body)
        if offset > length:
            raise ValueError("offset exceeds the document length")
        budget = (
            length if full else min(6000 if max_chars is None else max_chars, 12000)
        )
        end = min(offset + budget, length)

        def page(end):
            sections = [
                {k: v for k, v in section.items() if k != "content"}
                for section in selected_sections
                if full
                or view == "overview"
                or (
                    section["end_char"] > base + offset
                    and section["start_char"] < base + end
                )
            ]
            return {
                "slug": doc["slug"],
                "title": doc["title"],
                "summary": doc["summary"],
                "tags": list(doc["tags"] if full else doc["tags"][:16]),
                "tags_truncated": not full and len(doc["tags"]) > 16,
                "view": view,
                "section_anchor": section_anchor,
                "content": body[offset:end],
                "sections": sections,
                "source": dict(self._source),
                "content_length": length,
                "offset": offset,
                "returned_chars": end - offset,
                "next_offset": end if end < length else None,
                "has_more": end < length,
                "truncated": offset > 0 or end < length,
            }

        result = page(end)
        while not full and len(json.dumps(result).encode()) > 24000:
            if end <= offset:
                raise DocumentUnavailableError(
                    "Document metadata exceeds the response budget"
                )
            end = offset + (end - offset) // 2
            result = page(end)
        return result


@lru_cache(maxsize=1)
def get_document_store():
    return DocumentStore()
