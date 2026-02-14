"""
CSV column detection and parsing. Uses exact GAP 1 keyword table (case-insensitive).
If no header matches the content field, raise so API can return 400.
"""

import io
from collections.abc import Iterator
from typing import Any

import pandas as pd

# GAP 1: Exact column names to match (case-insensitive). No other keywords.
_CONTENT_KEYWORDS = frozenset(
    {
        "feedback",
        "message",
        "text",
        "description",
        "content",
        "body",
        "comment",
        "note",
        "request",
    }
)
_AUTHOR_EMAIL_KEYWORDS = frozenset(
    {"email", "customer_email", "user_email", "requester_email", "contact_email"}
)
_AUTHOR_NAME_KEYWORDS = frozenset(
    {
        "name",
        "customer_name",
        "user_name",
        "requester_name",
        "contact_name",
        "author",
    }
)
_ORGANIZATION_NAME_KEYWORDS = frozenset(
    {
        "company",
        "customer",
        "organization",
        "org",
        "account",
        "company_name",
        "org_name",
    }
)
_TIMESTAMP_KEYWORDS = frozenset(
    {
        "date",
        "created",
        "created_at",
        "timestamp",
        "time",
        "submitted",
        "submitted_at",
    }
)

FIELD_KEYWORDS: dict[str, frozenset[str]] = {
    "content": _CONTENT_KEYWORDS,
    "author_email": _AUTHOR_EMAIL_KEYWORDS,
    "author_name": _AUTHOR_NAME_KEYWORDS,
    "organization_name": _ORGANIZATION_NAME_KEYWORDS,
    "timestamp": _TIMESTAMP_KEYWORDS,
}


class ContentColumnNotFoundError(Exception):
    """Raised when no CSV header matches the required content column."""

    pass


def detect_columns(headers: list[str]) -> dict[str, int]:
    """
    Map feedback fields to column indices using GAP 1 keywords (case-insensitive).
    Returns e.g. {"content": 0, "author_email": 2}. Raises ContentColumnNotFoundError
    if no header matches the content field.
    """
    normalized = [h.strip().lower() for h in headers]
    mapping: dict[str, int] = {}

    for field, keywords in FIELD_KEYWORDS.items():
        for idx, h in enumerate(normalized):
            if h in keywords:
                mapping[field] = idx
                break

    if "content" not in mapping:
        raise ContentColumnNotFoundError(
            "Could not detect which column contains the feedback text. "
            "Please use a column header such as: feedback, message, text, description, content, body, comment, note, or request."
        )
    return mapping


def parse_csv_row(row: list[Any] | tuple[Any, ...], column_mapping: dict[str, int]) -> dict[str, Any]:
    """
    Convert one CSV row to a feedback item dict using the given mapping.
    Indices refer to positions in row. Missing/empty values become None.
    """
    result: dict[str, Any] = {
        "content": None,
        "author_email": None,
        "author_name": None,
        "organization_name": None,
        "timestamp": None,
    }
    for field, idx in column_mapping.items():
        if idx < len(row):
            val = row[idx]
            if hasattr(val, "strip"):
                val = val.strip() if val else None
            elif val is not None and not isinstance(val, str):
                val = str(val).strip() or None
            if val:
                result[field] = val
    if result["content"] is None or (isinstance(result["content"], str) and not result["content"].strip()):
        result["content"] = None  # Will be skipped or rejected by caller
    return result


def parse_csv_file(
    file_path: str | None = None,
    file_content: bytes | None = None,
    column_mapping: dict[str, int] | None = None,
    chunk_size: int = 500,
) -> Iterator[list[dict[str, Any]]]:
    """
    Read CSV and yield chunks of parsed rows. If column_mapping is None,
    detect from first row (headers). file_path or file_content must be set.
    """
    if file_path and file_content:
        raise ValueError("Provide either file_path or file_content, not both.")
    if not file_path and not file_content:
        raise ValueError("Provide file_path or file_content.")

    if file_content is not None:
        df = pd.read_csv(io.BytesIO(file_content), header=0, dtype=str, keep_default_na=False)
    else:
        df = pd.read_csv(file_path, header=0, dtype=str, keep_default_na=False)

    headers = list(df.columns)
    mapping = column_mapping or detect_columns(headers)
    rows = df.values.tolist()

    for i in range(0, len(rows), chunk_size):
        chunk_rows = rows[i : i + chunk_size]
        chunk = [parse_csv_row(r, mapping) for r in chunk_rows]
        yield chunk
