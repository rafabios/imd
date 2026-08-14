from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def _first_query_value(values: dict[str, list[str]], key: str, default: str = "") -> str:
    items = values.get(key) or []
    return str(items[0]).strip() if items else default


def normalize_google_sheet_csv_url(value: object) -> str:
    """Convert a regular Google Sheets link to its CSV export endpoint.

    Non-Google URLs and local paths are returned unchanged so existing CSV
    workflows continue to work.
    """

    url = str(value or "").strip()
    if not url:
        return ""

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname != "docs.google.com":
        return url

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 4 or parts[:2] != ["spreadsheets", "d"]:
        return url

    query = parse_qs(parsed.query, keep_blank_values=True)
    fragment = parse_qs(parsed.fragment, keep_blank_values=True)
    gid = _first_query_value(query, "gid") or _first_query_value(fragment, "gid", "0")

    if parts[2] == "e" and len(parts) >= 5:
        published_id = parts[3]
        published_query = {"output": "csv", "gid": gid}
        if _first_query_value(query, "single"):
            published_query["single"] = _first_query_value(query, "single")
        return urlunparse(
            ("https", "docs.google.com", f"/spreadsheets/d/e/{published_id}/pub", "", urlencode(published_query), "")
        )

    spreadsheet_id = parts[2]
    if not spreadsheet_id:
        return url
    return urlunparse(
        (
            "https",
            "docs.google.com",
            f"/spreadsheets/d/{spreadsheet_id}/export",
            "",
            urlencode({"format": "csv", "gid": gid}),
            "",
        )
    )
