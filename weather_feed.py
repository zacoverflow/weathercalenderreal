#!/usr/bin/env python3
"""
Builds a Google-Calendar-friendly .ics weather feed for Mosman, Sydney.

One all-day event per day:
  title:        "17-23° | Wind 15-30 km/h NE | Rain 60% (4 mm)"
  description:  3-hourly breakdown of temp, wind, gusts and rain.

Data: Open-Meteo (free, no API key): https://open-meteo.com
Only the Python standard library is used.

Edit the CONFIG block below to change location, days or what is shown.
"""

import json
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# ----------------------------- CONFIG ------------------------------------
LOCATION_NAME = "Mosman"
LATITUDE = -33.829
LONGITUDE = 151.244
TIMEZONE = "Australia/Sydney"
FORECAST_DAYS = 14          # Open-Meteo allows up to 16
HOURLY_STEP = 3             # hours between rows in the description
HOURLY_FROM, HOURLY_TO = 6, 21   # first / last hour shown in the breakdown
OUTPUT_FILE = Path("docs/weather.ics")

SHOW_GUSTS_IN_TITLE = False  # True -> "Wind 15-30 (gusts 45) km/h NE"
# -------------------------------------------------------------------------

API = "https://api.open-meteo.com/v1/forecast"

DAILY_FIELDS = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_probability_max",
    "precipitation_sum",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "wind_direction_10m_dominant",
]
HOURLY_FIELDS = [
    "temperature_2m",
    "precipitation_probability",
    "precipitation",
    "wind_speed_10m",
    "wind_gusts_10m",
    "wind_direction_10m",
]

# WMO weather codes -> short text
WMO = {
    0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    56: "Freezing drizzle", 57: "Freezing drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    66: "Freezing rain", 67: "Freezing rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Light showers", 81: "Showers", 82: "Heavy showers",
    85: "Snow showers", 86: "Snow showers",
    95: "Thunderstorm", 96: "Thunderstorm, hail", 99: "Thunderstorm, hail",
}

COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def compass(deg):
    if deg is None:
        return "?"
    return COMPASS[int((deg % 360) / 22.5 + 0.5) % 16]


def fetch_forecast():
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "daily": ",".join(DAILY_FIELDS),
        "hourly": ",".join(HOURLY_FIELDS),
        "timezone": TIMEZONE,
        "forecast_days": FORECAST_DAYS,
        "wind_speed_unit": "kmh",
        "temperature_unit": "celsius",
        "precipitation_unit": "mm",
    }
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "mosman-weather-calendar/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def rnd(v, nd=0):
    if v is None:
        return None
    return round(v, nd) if nd else int(round(v))


def day_hourly_rows(hourly, day_str):
    """Return 3-hourly rows for one date string like '2026-10-24'."""
    rows = []
    times = hourly["time"]
    for i, t in enumerate(times):
        if not t.startswith(day_str):
            continue
        hour = int(t[11:13])
        if hour < HOURLY_FROM or hour > HOURLY_TO:
            continue
        if (hour - HOURLY_FROM) % HOURLY_STEP != 0:
            continue
        temp = rnd(hourly["temperature_2m"][i])
        wind = rnd(hourly["wind_speed_10m"][i])
        gust = rnd(hourly["wind_gusts_10m"][i])
        wdir = compass(hourly["wind_direction_10m"][i])
        pp = hourly["precipitation_probability"][i]
        pr = hourly["precipitation"][i]
        pp_txt = f"{int(pp)}%" if pp is not None else "-"
        pr_txt = f"{pr:.1f}mm" if pr is not None else "-"
        rows.append(
            f"{hour:02d}:00  {temp}°  wind {wind} {wdir} (gust {gust})  rain {pp_txt} {pr_txt}"
        )
    return rows


def build_events(data):
    daily = data["daily"]
    hourly = data["hourly"]
    events = []
    for i, day_str in enumerate(daily["time"]):
        tmax = rnd(daily["temperature_2m_max"][i])
        tmin = rnd(daily["temperature_2m_min"][i])
        wmax = rnd(daily["wind_speed_10m_max"][i])
        gmax = rnd(daily["wind_gusts_10m_max"][i])
        wdir = compass(daily["wind_direction_10m_dominant"][i])
        pprob = daily["precipitation_probability_max"][i]
        psum = daily["precipitation_sum"][i]
        cond = WMO.get(daily["weather_code"][i], "")

        rain_txt = f"Rain {int(pprob)}%" if pprob is not None else "Rain -"
        if psum is not None and psum >= 0.1:
            rain_txt += f" ({psum:.1f} mm)"

        if SHOW_GUSTS_IN_TITLE:
            wind_txt = f"Wind {wmax} (gusts {gmax}) km/h {wdir}"
        else:
            wind_txt = f"Wind up to {wmax} km/h {wdir}"

        title = f"{tmin}-{tmax}° | {wind_txt} | {rain_txt}"

        lines = [
            f"{LOCATION_NAME}: {cond}",
            f"Temp {tmin}° to {tmax}°",
            f"Wind up to {wmax} km/h {wdir}, gusts up to {gmax} km/h",
            rain_txt,
            "",
            "Through the day:",
        ]
        lines += day_hourly_rows(hourly, day_str)
        lines += ["", "Data: Open-Meteo.com"]

        events.append({"date": day_str, "title": title, "description": "\n".join(lines)})
    return events


# ------------------------------ ICS --------------------------------------
def ics_escape(text):
    return (text.replace("\\", "\\\\")
                .replace(";", "\\;")
                .replace(",", "\\,")
                .replace("\r\n", "\n")
                .replace("\n", "\\n"))


def fold(line):
    """Fold to <=75 octets per RFC 5545 (continuation lines start with a space)."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    out, cur = [], b""
    limit = 75
    for ch in line:
        b = ch.encode("utf-8")
        if len(cur) + len(b) > limit:
            out.append(cur.decode("utf-8"))
            cur = b
            limit = 74  # continuation lines lose one octet to the leading space
        else:
            cur += b
    if cur:
        out.append(cur.decode("utf-8"))
    return "\r\n ".join(out)


def build_ics(events):
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    cal = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//mosman-weather-calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{ics_escape(LOCATION_NAME + ' Weather')}",
        f"X-WR-TIMEZONE:{TIMEZONE}",
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
        "X-PUBLISHED-TTL:PT6H",
    ]
    for ev in events:
        d = date.fromisoformat(ev["date"])
        nxt = d + timedelta(days=1)
        cal += [
            "BEGIN:VEVENT",
            # Stable UID per day so each refresh updates the same event.
            f"UID:weather-{d:%Y%m%d}@mosman-weather-calendar",
            f"DTSTAMP:{now}",
            f"DTSTART;VALUE=DATE:{d:%Y%m%d}",
            f"DTEND;VALUE=DATE:{nxt:%Y%m%d}",
            f"SUMMARY:{ics_escape(ev['title'])}",
            f"DESCRIPTION:{ics_escape(ev['description'])}",
            "TRANSP:TRANSPARENT",   # shows as "free", doesn't block your time
            "END:VEVENT",
        ]
    cal.append("END:VCALENDAR")
    return "\r\n".join(fold(l) for l in cal) + "\r\n"


def main():
    # Optional: `python weather_feed.py sample.json` to build from a saved response.
    if len(sys.argv) > 1:
        data = json.loads(Path(sys.argv[1]).read_text())
    else:
        data = fetch_forecast()
    events = build_events(data)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(build_ics(events), encoding="utf-8", newline="")
    print(f"Wrote {len(events)} days to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
