"""Trip.com clients."""

from urllib.parse import urlsplit, urlunsplit


def normalize_trip_url_to_english(raw_url: str | None) -> str | None:
    """Force Trip URLs onto the global English domain when possible."""
    if not raw_url:
        return raw_url

    parts = urlsplit(raw_url)
    netloc = parts.netloc.replace("vn.trip.com", "trip.com")
    if netloc == parts.netloc:
        return raw_url

    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def get_trip_origin(raw_url: str | None) -> str:
    normalized_url = normalize_trip_url_to_english(raw_url) or "https://trip.com"
    parts = urlsplit(normalized_url)
    scheme = parts.scheme or "https"
    netloc = parts.netloc or "trip.com"
    return f"{scheme}://{netloc}"
