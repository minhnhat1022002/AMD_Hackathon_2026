import json
import re
from datetime import date
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from scrapling.fetchers import StealthySession

from clients._threading import run_in_clean_thread
from clients.trip import normalize_trip_url_to_english
from common.text import clean_text

TRIP_ROOM_LIST_CAPTURE_SCRIPT = r"""
(() => {
  if (window.__tripRoomListHookInstalled) return;
  window.__tripRoomListHookInstalled = true;
  window.__tripRoomListResponses = [];
  window.__tripRoomPopInfoResponses = [];

  const pushPayload = (url, text) => {
    try {
      const normalizedUrl = String(url || '');
      if (normalizedUrl.includes('getHotelRoomListOversea')) {
        window.__tripRoomListResponses.push({ url: normalizedUrl, text: String(text || '') });
      }
      if (normalizedUrl.includes('getHotelRoomPopInfoPCOnline')) {
        window.__tripRoomPopInfoResponses.push({ url: normalizedUrl, text: String(text || '') });
      }
    } catch (_) {}
  };

  const originalFetch = window.fetch;
  window.fetch = async (...args) => {
    const response = await originalFetch(...args);
    try {
      const requestUrl = args && args[0] && (args[0].url || args[0]);
      const cloned = response.clone();
      cloned.text().then((text) => pushPayload(requestUrl || response.url, text)).catch(() => {});
    } catch (_) {}
    return response;
  };

  const OriginalXHR = window.XMLHttpRequest;
  function WrappedXHR() {
    const xhr = new OriginalXHR();
    let requestUrl = '';
    const open = xhr.open;
    xhr.open = function(method, url, ...rest) {
      requestUrl = url || '';
      return open.call(this, method, url, ...rest);
    };
    xhr.addEventListener('load', function() {
      try {
        pushPayload(requestUrl || xhr.responseURL, xhr.responseText);
      } catch (_) {}
    });
    return xhr;
  }
  WrappedXHR.prototype = OriginalXHR.prototype;
  window.XMLHttpRequest = WrappedXHR;
})();
"""

TITLE_SELECTORS = [
    "h1",
    '[class*="hotel-name"]',
    '[class*="detail-headline"]',
    '[data-testid="PageHeader"] h1',
]

TRIP_DEFAULT_CURRENCY = "VND"
TRIP_ENGLISH_LOCALE = "en-GB"
TRIP_BUSINESS_ITEM_BATCH_PATH = "/restapi/soa2/19478/getBusinessItemBatchV2"


def _safe_json_loads(value: str | None):
    if not value:
        return None
    try:
        return json.loads(value)
    except Exception:
        return None


def _pick_first_text(root, selectors: list[str]) -> str | None:
    for selector in selectors:
        locator = root.locator(selector)
        if locator.count() == 0:
            continue
        try:
            value = clean_text(locator.first.evaluate("(el) => el.innerText || el.textContent || ''"))
        except Exception:
            value = clean_text(locator.first.text_content())
        if value:
            return value
    return None


def _extract_page_hotel_name(page) -> str | None:
    direct_name = _pick_first_text(page, TITLE_SELECTORS)
    if direct_name:
        return direct_name

    try:
        candidates = page.evaluate(
            r"""
() => [
  document.querySelector('meta[property="og:title"]')?.getAttribute('content'),
  document.querySelector('meta[name="title"]')?.getAttribute('content'),
  document.title,
]
"""
        )
    except Exception:
        candidates = []

    if not isinstance(candidates, list):
        return None

    for candidate in candidates:
        normalized = clean_text(str(candidate) if candidate else None)
        if not normalized:
            continue
        return clean_text(re.split(r"\s*[-|]\s*", normalized)[0])

    return None


def _normalize_currency_code(value: str | None) -> str | None:
    normalized = clean_text(value)
    if not normalized:
        return None
    normalized = normalized.upper()
    if normalized in {"VND", "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "SGD", "THB"}:
        return normalized
    aliases = {
        "VNĐ": "VND",
        "₫": "VND",
        "$": "USD",
        "US$": "USD",
        "€": "EUR",
        "£": "GBP",
        "¥": "JPY",
    }
    return aliases.get(normalized)


def _apply_search_params(
    url: str,
    checkin_date: date,
    checkout_date: date,
    adults: int,
    children: int,
    rooms: int,
    currency: str,
) -> str:
    normalized_url = normalize_trip_url_to_english(url) or url
    parts = urlsplit(normalized_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))

    # Trip.com uses these keys on hotel detail pages. If the URL already has them, preserve them.
    query.setdefault("checkIn", checkin_date.isoformat())
    query.setdefault("checkOut", checkout_date.isoformat())
    query.setdefault("adult", str(adults))
    query.setdefault("children", str(children))
    query.setdefault("crn", str(rooms))
    query.setdefault("locale", TRIP_ENGLISH_LOCALE)
    query.setdefault("curr", currency)

    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _extract_property_id(url: str | None) -> str | None:
    normalized = clean_text(url)
    if not normalized:
        return None
    match = re.search(r"hotel-detail-(\d+)", normalized)
    if match:
        return match.group(1)
    query_match = re.search(r"[?&]hotelId=(\d+)", normalized)
    if query_match:
        return query_match.group(1)
    return None


def _is_trip_room_list_url(url: str | None) -> bool:
    normalized = clean_text(url)
    return bool(normalized and "getHotelRoomListOversea" in normalized)


def _is_trip_room_pop_info_url(url: str | None) -> bool:
    normalized = clean_text(url)
    return bool(normalized and "getHotelRoomPopInfoPCOnline" in normalized)


def _install_room_capture_hook(page) -> None:
    try:
        page.evaluate(TRIP_ROOM_LIST_CAPTURE_SCRIPT)
        page.wait_for_timeout(200)
    except Exception:
        pass


def _reset_intercepted_room_payloads(page) -> None:
    try:
        page.evaluate(
            "() => { window.__tripRoomListResponses = []; window.__tripRoomPopInfoResponses = []; }"
        )
    except Exception:
        pass


def _read_intercepted_entries(page, variable_name: str) -> list[dict]:
    try:
        entries = page.evaluate(f"() => window.{variable_name} || []")
    except Exception:
        return []

    normalized_entries: list[dict] = []
    if not isinstance(entries, list):
        return normalized_entries

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        normalized_entry: dict = {}
        url = clean_text(entry.get("url"))
        if url:
            normalized_entry["url"] = url

        raw_text = entry.get("text")
        parsed = _safe_json_loads(raw_text if isinstance(raw_text, str) else None)
        if parsed is not None:
            normalized_entry["payload"] = parsed
        else:
            text = clean_text(raw_text if isinstance(raw_text, str) else None)
            if text:
                normalized_entry["text"] = text

        if normalized_entry:
            normalized_entries.append(normalized_entry)
    return normalized_entries


def _read_intercepted_payloads(page, variable_name: str) -> list[dict]:
    payloads: list[dict] = []
    for entry in _read_intercepted_entries(page, variable_name):
        parsed = entry.get("payload")
        if isinstance(parsed, dict):
            payloads.append(parsed)
    return payloads


def _read_intercepted_room_payloads(page) -> list[dict]:
    return _read_intercepted_payloads(page, "__tripRoomListResponses")


def _read_intercepted_room_pop_info_payloads(page) -> list[dict]:
    return _read_intercepted_payloads(page, "__tripRoomPopInfoResponses")


def _read_cookie_value(page, cookie_name: str) -> str | None:
    try:
        value = page.evaluate(
            f"""
() => {{
  const name = {json.dumps(cookie_name)} + '=';
  for (const part of String(document.cookie || '').split(';')) {{
    const trimmed = part.trim();
    if (trimmed.startsWith(name)) {{
      return decodeURIComponent(trimmed.slice(name.length));
    }}
  }}
  return null;
}}
"""
        )
    except Exception:
        return None
    return clean_text(value)


def _normalize_trip_business_locale(value: str | None) -> str:
    normalized = clean_text(value) or "en-XX"
    normalized = normalized.replace("_", "-")
    parts = normalized.split("-")
    if len(parts) == 2:
        return f"{parts[0].lower()}-{parts[1].upper()}"
    return normalized


def _address_text_from_value(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        normalized = clean_text(value)
        return normalized if normalized else None
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            text = _address_text_from_value(item)
            if text and text not in parts:
                parts.append(text)
        if parts:
            return ", ".join(parts)
        return None
    if isinstance(value, dict):
        for key in ("fullAddress", "addressLine", "addressLine1", "streetAddress", "address", "name"):
            if key in value:
                text = _address_text_from_value(value.get(key))
                if text:
                    return text
        parts: list[str] = []
        for key in ("line1", "line2", "street", "ward", "district", "city", "province", "country"):
            if key in value:
                text = _address_text_from_value(value.get(key))
                if text and text not in parts:
                    parts.append(text)
        if parts:
            return ", ".join(parts)
    return None


def _extract_address_from_business_item_payload(node) -> str | None:
    if isinstance(node, dict):
        for key in (
            "address",
            "fullAddress",
            "addressLine",
            "addressInfo",
            "displayAddress",
            "locationAddress",
        ):
            if key in node:
                text = _address_text_from_value(node.get(key))
                if text:
                    return text

        for key, value in node.items():
            if "address" in str(key).lower():
                text = _address_text_from_value(value)
                if text:
                    return text

        for value in node.values():
            text = _extract_address_from_business_item_payload(value)
            if text:
                return text

    elif isinstance(node, list):
        for item in node:
            text = _extract_address_from_business_item_payload(item)
            if text:
                return text

    return None


def _extract_address_from_business_item_entries(entries: list[dict]) -> str | None:
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        payload = entry.get("payload")
        text = _extract_address_from_business_item_payload(payload)
        if text:
            return text
    return None


def _fetch_business_item_batch_entry(
    page,
    request_url: str,
    property_id: str,
    checkin_date: date,
    checkout_date: date,
    adults: int,
    children: int,
    rooms: int,
    currency: str,
) -> dict | None:
    ibulocale = _read_cookie_value(page, "ibulocale")
    locale = _normalize_trip_business_locale(ibulocale or TRIP_ENGLISH_LOCALE)
    guid = _read_cookie_value(page, "GUID") or ""
    group = _read_cookie_value(page, "ibugroup") or "trip"

    body = {
        "mapHead": {
            "locale": locale,
            "group": group,
            "timezone": "7",
            "currency": currency,
            "scene": "xtaro_travel_map",
            "mapPageName": "xtaro_nearby_map",
            "platform": "online",
            "mapVersion": "20260122",
            "mapMakerType": "Google",
            "distanceUnit": "metric",
            "userLocation": {"curCityId": "", "location": None},
        },
        "userInfo": {"cid": guid},
        "searchNodes": [{"id": property_id, "type": "hotel"}],
        "hotelFilter": {
            "roomQuantity": rooms,
            "childAges": [],
            "childNum": children,
            "adultNum": adults,
            "pointDeductSwitch": False,
            "checkIn": checkin_date.strftime("%Y%m%d"),
            "checkOut": checkout_date.strftime("%Y%m%d"),
            "commentMode": "10",
            "visible": True,
            "displayPrice": True,
        },
        "extraNodeInfo": {"isTarget": True},
        "head": {
            "cid": guid,
            "ctok": "",
            "cver": "1.0",
            "lang": "01",
            "sid": "8888",
            "syscode": "09",
            "auth": "",
            "xsid": "",
            "extension": [
                {"name": "group", "value": group},
                {"name": "locale", "value": locale},
            ],
        },
    }

    try:
        result = page.evaluate(
            f"""
async () => {{
  const requestBody = {json.dumps(body, ensure_ascii=False)};
  const guid = {json.dumps(guid)};
  const traceId = `${{guid || Date.now()}}-${{Date.now()}}-${{Math.floor(Math.random() * 9000000) + 1000000}}`;
  const endpoint = new URL({json.dumps(TRIP_BUSINESS_ITEM_BATCH_PATH)}, window.location.origin);
  endpoint.searchParams.set('_fxpcqlniredt', guid);
  endpoint.searchParams.set('x-traceID', traceId);

  const response = await fetch(endpoint.toString(), {{
    method: 'POST',
    credentials: 'include',
    headers: {{
      'accept': '*/*',
      'content-type': 'application/json',
      'cookieorigin': window.location.origin,
    }},
    body: JSON.stringify(requestBody),
  }});

  const text = await response.text();
  return {{
    url: response.url,
    status: response.status,
    ok: response.ok,
    request_body: requestBody,
    text,
  }};
}}
"""
        )
    except Exception:
        return None

    if not isinstance(result, dict):
        return None

    entry: dict = {
        "request_url": clean_text(result.get("url")) or f"{urlsplit(request_url).scheme}://{urlsplit(request_url).netloc}{TRIP_BUSINESS_ITEM_BATCH_PATH}",
        "request_body": result.get("request_body") if isinstance(result.get("request_body"), dict) else body,
        "status": result.get("status"),
        "ok": result.get("ok"),
    }
    parsed = _safe_json_loads(result.get("text") if isinstance(result.get("text"), str) else None)
    if parsed is not None:
        entry["payload"] = parsed
    else:
        text = clean_text(result.get("text") if isinstance(result.get("text"), str) else None)
        if text:
            entry["text"] = text
    return entry


def _trigger_room_pop_info_requests(page) -> None:
    try:
        page.evaluate(
            r"""
async () => {
  const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const clicked = new Set();
  const closePopups = () => {
    for (const node of document.querySelectorAll('button, [role="button"], svg')) {
      const text = String(node.innerText || node.textContent || node.getAttribute('aria-label') || '').toLowerCase();
      if (text.includes('close') || text.includes('đóng') || text.includes('x')) {
        try { node.click(); } catch (_) {}
      }
    }
  };
  const isVisible = (node) => {
    const rect = node.getBoundingClientRect();
    const style = window.getComputedStyle(node);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  };
  const targets = () => Array.from(document.querySelectorAll('button, a, [role="button"], div, span'))
    .filter(isVisible)
    .filter((node) => {
      const text = String(node.innerText || node.textContent || '').trim().toLowerCase();
      if (!text) return false;
      return (
        text.includes('chi tiết phòng') ||
        text.includes('thông tin phòng') ||
        text.includes('tiện nghi') ||
        text.includes('room details') ||
        text.includes('room info') ||
        text.includes('facilities') ||
        text.includes('amenities')
      );
    });

  for (let round = 0; round < 5; round += 1) {
    window.scrollBy(0, Math.floor(window.innerHeight * 0.8));
    await delay(500);
    for (const node of targets()) {
      if (clicked.size >= 8) return;
      const key = `${node.innerText || node.textContent || ''}:${node.getBoundingClientRect().top}`;
      if (clicked.has(key)) continue;
      clicked.add(key);
      try {
        node.click();
        await delay(900);
        closePopups();
      } catch (_) {}
    }
  }
}
"""
        )
        page.wait_for_timeout(1500)
    except Exception:
        pass


def _find_room_payload(node) -> dict | None:
    if isinstance(node, dict):
        has_physic = isinstance(node.get("physicRoomMap"), dict)
        has_sale = isinstance(node.get("saleRoomMap"), dict)
        if has_physic and has_sale:
            return node
        for value in node.values():
            found = _find_room_payload(value)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_room_payload(item)
            if found is not None:
                return found
    return None


def _parse_amount(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    normalized = clean_text(str(value))
    if not normalized:
        return None

    candidate = normalized.replace(" ", "")
    digits = re.sub(r"\D", "", candidate)
    if not digits:
        return None

    matches = re.findall(r"\d[\d.,]*", candidate)
    if not matches:
        return None

    picked = max(matches, key=lambda item: len(re.sub(r"\D", "", item)))
    separators = re.findall(r"[.,]", picked)
    if not separators:
        return float(re.sub(r"\D", "", picked))
    if len(separators) > 1:
        return float(re.sub(r"[.,]", "", picked))

    whole, fractional = picked.rsplit(separators[0], 1)
    if len(re.sub(r"\D", "", fractional)) in (1, 2):
        try:
            whole_digits = re.sub(r"\D", "", whole)
            fractional_digits = re.sub(r"\D", "", fractional)
            return float(f"{whole_digits}.{fractional_digits}")
        except ValueError:
            return None
    return float(re.sub(r"[.,]", "", picked))


def _extract_currency(*values) -> str | None:
    for value in values:
        normalized = clean_text(str(value) if value is not None else None)
        code = _normalize_currency_code(normalized)
        if code:
            return code
        if not normalized:
            continue
        lowered = normalized.lower()
        if "vnd" in lowered or "vnđ" in lowered or "₫" in lowered:
            return "VND"
        if "usd" in lowered or "$" in normalized:
            return "USD"
        if "eur" in lowered or "€" in normalized:
            return "EUR"
    return None


def _extract_tax_and_fee(*values) -> float | None:
    for value in values:
        if not isinstance(value, str):
            continue
        normalized = clean_text(value)
        if not normalized:
            continue
        parsed = _parse_amount(normalized)
        if parsed is not None and ("thuế" in normalized.lower() or "tax" in normalized.lower() or "fee" in normalized.lower()):
            return parsed
    return None


def _pick_first_value(data: dict, keys: list[str]):
    lowered_map = {str(key).lower(): value for key, value in data.items()}
    for key in keys:
        value = lowered_map.get(key.lower())
        if value not in (None, "", [], {}):
            return value
    return None


def _pick_first_amount(data: dict, keys: list[str]) -> float | None:
    value = _pick_first_value(data, keys)
    return _parse_amount(value)


def _pick_first_int(*values) -> int | None:
    for value in values:
        if value in (None, "", [], {}):
            continue
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        match = re.search(r"\d+", str(value))
        if match:
            return int(match.group(0))
    return None


def _append_unique_text(values: list[str], value: str | None) -> None:
    normalized = clean_text(value)
    if not normalized:
        return
    if len(normalized) > 120:
        return
    lowered = normalized.lower()
    if lowered in {item.lower() for item in values}:
        return
    values.append(normalized)


def _extract_facility_texts(node) -> list[str]:
    facilities: list[str] = []

    def visit(value, facility_context: bool = False) -> None:
        if value in (None, "", [], {}):
            return
        if isinstance(value, str):
            if facility_context:
                for part in re.split(r"[,;|/•·\n]+", value):
                    _append_unique_text(facilities, part)
            return
        if isinstance(value, (int, float, bool)):
            return
        if isinstance(value, list):
            for item in value:
                visit(item, facility_context)
            return
        if not isinstance(value, dict):
            return

        dict_is_facility = facility_context or any(
            "facility" in str(key).lower() or "amenit" in str(key).lower()
            for key in value
        )
        if dict_is_facility:
            for key in ("name", "facilityName", "title", "text", "content", "label", "desc", "description"):
                if key in value:
                    _append_unique_text(facilities, str(value.get(key)) if value.get(key) is not None else None)

        for key, child in value.items():
            lowered_key = str(key).lower()
            child_context = dict_is_facility or "facility" in lowered_key or "amenit" in lowered_key
            if child_context:
                visit(child, True)

    visit(node, False)
    return facilities


def _extract_room_id_values(data: dict) -> list[str]:
    ids: list[str] = []
    for key in (
        "physicalRoomId",
        "physicRoomId",
        "roomId",
        "roomID",
        "saleRoomId",
        "subHotelId",
        "id",
    ):
        value = data.get(key)
        if value in (None, "", [], {}):
            continue
        text_value = str(value)
        if text_value not in ids:
            ids.append(text_value)
    return ids


def _build_facilities_by_room_id(payloads: list[dict]) -> dict[str, list[str]]:
    facilities_by_room_id: dict[str, list[str]] = {}
    all_facilities: list[str] = []

    def merge(target_key: str, values: list[str]) -> None:
        if not values:
            return
        current = facilities_by_room_id.setdefault(target_key, [])
        for value in values:
            _append_unique_text(current, value)

    def visit(node) -> None:
        if isinstance(node, dict):
            facilities = _extract_facility_texts(node)
            if facilities:
                for facility in facilities:
                    _append_unique_text(all_facilities, facility)
                for room_id in _extract_room_id_values(node):
                    merge(room_id, facilities)
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    for payload in payloads:
        visit(payload)

    if all_facilities:
        merge("__all__", all_facilities)

    return facilities_by_room_id


def _pick_room_facilities(
    facilities_by_room_id: dict[str, list[str]],
    *room_ids,
) -> list[str]:
    for room_id in room_ids:
        if room_id in (None, "", [], {}):
            continue
        facilities = facilities_by_room_id.get(str(room_id))
        if facilities:
            return facilities
    return facilities_by_room_id.get("__all__", [])


def _collect_offers_from_payload(
    payload: dict,
    query_name: str,
    input_url: str,
    property_url: str,
    checkin_date: date,
    checkout_date: date,
    preferred_currency: str | None,
    include_raw: bool,
    hotel_name: str | None,
    facilities_by_room_id: dict[str, list[str]] | None = None,
    business_item_batch_entries: list[dict] | None = None,
) -> list[dict]:
    room_payload = _find_room_payload(payload)
    if room_payload is None:
        return []

    physic_room_map = room_payload.get("physicRoomMap")
    sale_room_map = room_payload.get("saleRoomMap")
    if not isinstance(physic_room_map, dict) or not isinstance(sale_room_map, dict):
        return []

    outputs: list[dict] = []
    seen_keys: set[tuple[str, float]] = set()
    address = _extract_address_from_business_item_entries(business_item_batch_entries or [])

    for sale_room_key, sale_room_value in sale_room_map.items():
        if not isinstance(sale_room_value, dict):
            continue

        physical_room_id = sale_room_value.get("physicalRoomId")
        if physical_room_id is None:
            candidate_id = sale_room_value.get("id")
            if str(candidate_id) in physic_room_map:
                physical_room_id = candidate_id

        physical_room = physic_room_map.get(str(physical_room_id), {})
        if not isinstance(physical_room, dict):
            physical_room = {}

        room_name = clean_text(physical_room.get("name")) or clean_text(sale_room_value.get("name"))
        price_info = sale_room_value.get("priceInfo")
        if not isinstance(price_info, dict):
            price_info = {}
        total_price_info = sale_room_value.get("totalPriceInfo")
        if not isinstance(total_price_info, dict):
            total_price_info = {}

        price_before_tax = _pick_first_amount(
            price_info,
            ["price", "displayPrice", "basePrice", "salePrice", "roomPrice"],
        )
        price_after_tax = _pick_first_amount(
            total_price_info,
            ["price", "displayPrice", "totalPrice", "amount", "payAmount"],
        )
        if price_after_tax is None:
            price_after_tax = _pick_first_amount(
                price_info,
                ["priceAfterTax", "inclusivePrice", "totalPrice"],
            )
        if price_before_tax is None and price_after_tax is None:
            continue

        currency = preferred_currency or _extract_currency(
            price_info.get("currency"),
            price_info.get("displayPrice"),
            total_price_info.get("currency"),
            total_price_info.get("displayPrice"),
        )

        tax_and_fee = _extract_tax_and_fee(
            price_info.get("taxText"),
            price_info.get("priceExplanation"),
            price_info.get("priceExplanationHighlight"),
            total_price_info.get("taxText"),
        )

        if price_before_tax is None and price_after_tax is not None and tax_and_fee is not None:
            price_before_tax = max(price_after_tax - tax_and_fee, 0)
        if price_before_tax is None:
            price_before_tax = price_after_tax
        if price_after_tax is None and price_before_tax is not None and tax_and_fee is not None:
            price_after_tax = price_before_tax + tax_and_fee
        if price_after_tax is None:
            price_after_tax = price_before_tax

        total_price = price_after_tax
        original_price = _pick_first_amount(
            price_info,
            ["originalPrice", "strikePrice", "marketPrice", "basePriceBeforeDiscount"],
        ) or _pick_first_amount(
            total_price_info,
            ["originalPrice", "strikePrice", "marketPrice"],
        )
        discount = None
        if (
            original_price is not None
            and total_price is not None
            and original_price > total_price
        ):
            discount = original_price - total_price

        rate_name = clean_text(price_info.get("priceExplanationHighlight")) or clean_text(
            price_info.get("priceExplanation")
        )
        booking_status_info = sale_room_value.get("bookingStatusInfo")
        if not isinstance(booking_status_info, dict):
            booking_status_info = {}
        remaining_room = _pick_first_int(
            _pick_first_value(
                booking_status_info,
                ["remainRoomQuantity", "remainingRoomQuantity", "roomsLeft", "roomLeft"],
            ),
            _pick_first_value(
                sale_room_value,
                [
                    "roomsLeft",
                    "roomLeft",
                    "remainingRoom",
                    "remainRoomQuantity",
                    "remainingRoomQuantity",
                    "availableRooms",
                    "stock",
                ],
            ),
            _pick_first_value(
                price_info,
                ["roomsLeft", "roomLeft", "remainingRoom", "availableRooms", "stock"],
            ),
            _pick_first_value(
                physical_room,
                ["roomsLeft", "roomLeft", "remainingRoom", "availableRooms", "stock"],
            ),
        )
        services = {
            "rate": rate_name,
            "meal": _pick_first_value(price_info, ["mealPlan", "mealText", "boardType"]),
            "cancellation": _pick_first_value(
                price_info,
                ["cancelPolicy", "cancellationPolicy", "refundPolicy", "refundText"],
            ),
            "bed": _pick_first_value(physical_room, ["bedInfo", "bedType", "bedText"]),
        }
        facilities = _pick_room_facilities(
            facilities_by_room_id or {},
            physical_room_id,
            sale_room_value.get("id"),
            sale_room_key,
        )
        if not facilities:
            facilities = _extract_facility_texts(physical_room) or _extract_facility_texts(sale_room_value)
        if facilities:
            services["facilities"] = facilities
        services = {key: value for key, value in services.items() if value}

        dedupe_key = (str(sale_room_key), total_price or 0)
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)

        raw_payload = {}
        if include_raw:
            raw_payload = {
                "sale_room_key": sale_room_key,
                "physical_room_id": physical_room_id,
                "price_info": price_info,
                "total_price_info": total_price_info,
                "physical_room": physical_room,
            }
            if business_item_batch_entries:
                raw_payload["get_business_item_batch_v2_responses"] = business_item_batch_entries

        outputs.append(
            {
                "query_name": query_name,
                "input_url": input_url,
                "is_found": True,
                "sale_room_key": sale_room_key,
                "hotel_name": hotel_name,
                "property_url": property_url,
                "property_id": _extract_property_id(property_url)
                or _extract_property_id(input_url),
                "room_name": room_name,
                "room_type": room_name,
                "facilities": facilities,
                "rate_name": rate_name,
                "occupancy_text": None,
                "currency": currency,
                "address": address,
                "price_before_tax": price_before_tax,
                "price_after_tax": price_after_tax,
                "discount": discount,
                "remaining_room": remaining_room,
                "services": services,
                "original_price": original_price,
                "total_price": total_price,
                "nightly_price": price_before_tax,
                "tax_and_fee": tax_and_fee,
                "checkin_date": checkin_date,
                "checkout_date": checkout_date,
                "raw": raw_payload,
            }
        )

    outputs.sort(
        key=lambda item: (
            item.get("total_price") is None,
            item.get("total_price") or 0,
        )
    )
    return outputs


def _capture_debug_snapshot(page) -> dict:
    snapshot: dict = {"page_url": page.url}
    try:
        body_text = clean_text(page.locator("body").text_content())
        if body_text:
            snapshot["body_excerpt"] = body_text[:2000]
    except Exception:
        pass
    return snapshot


class TripPriceClient:
    async def fetch_prices(
        self,
        hotel_urls: list[str],
        hotel_names: list[str],
        checkin_date: date,
        checkout_date: date,
        adults: int,
        children: int,
        rooms: int,
        currency: str | None,
        include_raw: bool = False,
    ) -> list[dict]:
        return await run_in_clean_thread(
            self._fetch_prices_sync,
            hotel_urls,
            hotel_names,
            checkin_date,
            checkout_date,
            adults,
            children,
            rooms,
            currency,
            include_raw,
        )

    def _fetch_prices_sync(
        self,
        hotel_urls: list[str],
        hotel_names: list[str],
        checkin_date: date,
        checkout_date: date,
        adults: int,
        children: int,
        rooms: int,
        currency: str | None,
        include_raw: bool,
    ) -> list[dict]:
        preferred_currency = _normalize_currency_code(currency) or TRIP_DEFAULT_CURRENCY
        outputs: list[dict] = []

        if hotel_names and not hotel_urls:
            for hotel_name in hotel_names:
                outputs.append(
                    {
                        "query_name": hotel_name,
                        "input_url": None,
                        "is_found": False,
                        "error": "Trip.com price collection currently supports hotel_urls only",
                        "hotel_name": None,
                        "property_url": None,
                        "property_id": None,
                        "checkin_date": checkin_date,
                        "checkout_date": checkout_date,
                        "raw": {},
                    }
                )
            return outputs

        with StealthySession(
            headless=True,
            solve_cloudflare=False,
            google_search=True,
            real_chrome=True,
            locale=TRIP_ENGLISH_LOCALE,
            timezone_id="Asia/Ho_Chi_Minh",
            block_webrtc=True,
            allow_webgl=True,
        ) as session:
            for hotel_url in hotel_urls:
                request_url = _apply_search_params(
                    url=hotel_url,
                    checkin_date=checkin_date,
                    checkout_date=checkout_date,
                    adults=adults,
                    children=children,
                    rooms=rooms,
                    currency=preferred_currency,
                )
                room_payloads: list[dict] = []
                room_pop_info_payloads: list[dict] = []
                business_item_batch_entries: list[dict] = []
                captured_hotel_name: str | None = None

                def on_response(response) -> None:
                    try:
                        is_room_list = _is_trip_room_list_url(response.url)
                        is_room_pop_info = _is_trip_room_pop_info_url(response.url)
                        if not is_room_list and not is_room_pop_info:
                            return

                        text = None
                        try:
                            payload = response.json()
                        except Exception:
                            payload = None

                        if payload is None:
                            try:
                                text = response.text()
                            except Exception:
                                text = None
                            payload = _safe_json_loads(text)

                        if isinstance(payload, dict):
                            if is_room_list:
                                room_payloads.append(payload)
                            if is_room_pop_info:
                                room_pop_info_payloads.append(payload)
                    except Exception:
                        return

                def capture(page) -> None:
                    nonlocal captured_hotel_name
                    _install_room_capture_hook(page)
                    _reset_intercepted_room_payloads(page)
                    page.on("response", on_response)
                    page.wait_for_timeout(1500)

                    try:
                        page.reload(wait_until="networkidle", timeout=60000)
                    except Exception:
                        pass

                    page.wait_for_timeout(5000)
                    captured_hotel_name = _extract_page_hotel_name(page)
                    room_payloads.extend(_read_intercepted_room_payloads(page))
                    _trigger_room_pop_info_requests(page)
                    room_pop_info_payloads.extend(_read_intercepted_room_pop_info_payloads(page))
                    property_id = _extract_property_id(request_url) or _extract_property_id(hotel_url)
                    if property_id:
                        business_item_entry = _fetch_business_item_batch_entry(
                            page=page,
                            request_url=request_url,
                            property_id=property_id,
                            checkin_date=checkin_date,
                            checkout_date=checkout_date,
                            adults=adults,
                            children=children,
                            rooms=rooms,
                            currency=preferred_currency,
                        )
                        if business_item_entry:
                            business_item_batch_entries.append(business_item_entry)

                    if not room_payloads and include_raw:
                        room_payloads.append(
                            {
                                "hotel_name": captured_hotel_name,
                                "query_name": hotel_url,
                                "input_url": hotel_url,
                                "error": "No Trip.com getHotelRoomListOversea response captured",
                                "checkin_date": checkin_date,
                                "checkout_date": checkout_date,
                                "request_url": request_url,
                                "debug": _capture_debug_snapshot(page)
                                | {
                                    "room_payload_count": 0,
                                    "room_pop_info_payload_count": len(room_pop_info_payloads),
                                    "business_item_batch_response_count": len(business_item_batch_entries),
                                    "get_business_item_batch_v2_responses": business_item_batch_entries,
                                },
                            }
                        )

                try:
                    session.fetch(
                        request_url,
                        google_search=True,
                        wait=3000,
                        timeout=90000,
                        page_action=capture,
                    )
                except Exception as exc:
                    outputs.append(
                        {
                            "query_name": hotel_url,
                            "input_url": hotel_url,
                            "error": clean_text(str(exc)),
                            "checkin_date": checkin_date,
                            "checkout_date": checkout_date,
                            "request_url": request_url,
                        }
                    )
                    continue

                if room_payloads:
                    extracted_offers: list[dict] = []
                    facilities_by_room_id = _build_facilities_by_room_id(room_pop_info_payloads)
                    for payload in room_payloads:
                        if isinstance(payload, dict):
                            extracted_offers.extend(
                                _collect_offers_from_payload(
                                    payload=payload,
                                    query_name=hotel_url,
                                    input_url=hotel_url,
                                    property_url=request_url,
                                    checkin_date=checkin_date,
                                    checkout_date=checkout_date,
                                    preferred_currency=preferred_currency,
                                    include_raw=include_raw,
                                    hotel_name=captured_hotel_name,
                                    facilities_by_room_id=facilities_by_room_id,
                                    business_item_batch_entries=business_item_batch_entries,
                                )
                            )
                    if extracted_offers:
                        outputs.extend(extracted_offers)
                        continue

                    if include_raw:
                        outputs.append(
                            {
                                "hotel_name": captured_hotel_name,
                                "query_name": hotel_url,
                                "input_url": hotel_url,
                                "error": "No Trip.com room offer extracted from captured payloads",
                                "checkin_date": checkin_date,
                                "checkout_date": checkout_date,
                                "request_url": request_url,
                                "raw": {
                                    "payloads": room_payloads,
                                    "room_pop_info_payloads": room_pop_info_payloads,
                                    "get_business_item_batch_v2_responses": business_item_batch_entries,
                                },
                            }
                        )
                        continue

                outputs.append(
                    {
                        "hotel_name": captured_hotel_name,
                        "query_name": hotel_url,
                        "input_url": hotel_url,
                        "error": "No Trip.com room payload captured",
                        "checkin_date": checkin_date,
                        "checkout_date": checkout_date,
                        "request_url": request_url,
                    }
                )

        return outputs
