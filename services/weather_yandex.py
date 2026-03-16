from __future__ import annotations

import re
from dataclasses import dataclass

import aiohttp


YANDEX_SORTAVALA_URL = "https://yandex.ru/pogoda/sortavala"


@dataclass
class YandexWeatherNow:
    condition: str
    temperature_c: str
    feels_like_c: str
    wind_speed_ms: str | None = None
    wind_direction: str | None = None
    pressure_mm: str | None = None
    humidity_percent: str | None = None


def _clean_num(value: str) -> str:
    return value.replace("−", "-").replace(",", ".").strip()


def _extract_primary_block(text: str) -> YandexWeatherNow | None:
    pattern = re.compile(
        r"Сортавала,\s*погода сейчас:\s*([^\.]+)\.\s*"
        r"Сегодня[^\.]*\.\s*Температура воздуха\s*([+\-−]?\d+)[°º]?,\s*ощущается как\s*([+\-−]?\d+)",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return None

    condition = match.group(1).strip().capitalize()
    temp = _clean_num(match.group(2))
    feels = _clean_num(match.group(3))

    wind_match = re.search(
        r"Скорость ветра\s*([0-9]+(?:[.,][0-9]+)?)\s*[^,]*,\s*([^\.]+)\.",
        text,
        flags=re.IGNORECASE,
    )
    pressure_match = re.search(r"Давление\s*(\d+)\s*Миллиметров", text, flags=re.IGNORECASE)
    humidity_match = re.search(r"Влажность\s*(\d+)%", text, flags=re.IGNORECASE)

    return YandexWeatherNow(
        condition=condition,
        temperature_c=temp,
        feels_like_c=feels,
        wind_speed_ms=_clean_num(wind_match.group(1)) if wind_match else None,
        wind_direction=wind_match.group(2).strip() if wind_match else None,
        pressure_mm=pressure_match.group(1).strip() if pressure_match else None,
        humidity_percent=humidity_match.group(1).strip() if humidity_match else None,
    )


def _extract_faq_block(text: str) -> YandexWeatherNow | None:
    pattern = re.compile(
        r"Сейчас в Сортавале\s*([^,]+),\s*температура воздуха\s*([+\-−]?\d+)[°º]?,\s*"
        r"ощущается как\s*([+\-−]?\d+)[°º]?\.\s*"
        r"Ветер\s*([0-9]+(?:[.,][0-9]+)?)\s*м/с,\s*([^,]+),\s*влажность\s*(\d+)%,\s*"
        r"атмосферное давление\s*(\d+)\s*мм",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return None

    return YandexWeatherNow(
        condition=match.group(1).strip().capitalize(),
        temperature_c=_clean_num(match.group(2)),
        feels_like_c=_clean_num(match.group(3)),
        wind_speed_ms=_clean_num(match.group(4)),
        wind_direction=match.group(5).strip(),
        humidity_percent=match.group(6).strip(),
        pressure_mm=match.group(7).strip(),
    )


async def fetch_sortavala_weather() -> YandexWeatherNow | None:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
        ),
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    }
    timeout = aiohttp.ClientTimeout(total=10, connect=5, sock_read=7)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(YANDEX_SORTAVALA_URL, headers=headers) as response:
                if response.status != 200:
                    return None
                html = await response.text()
    except Exception:
        return None

    compact = re.sub(r"\s+", " ", html)
    return _extract_primary_block(compact) or _extract_faq_block(compact)
