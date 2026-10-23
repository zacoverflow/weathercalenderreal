# Mosman weather calendar feed

A tiny script that builds a calendar feed (`docs/weather.ics`) with one all-day
event per day for the next 14 days:

```
17-23° | Wind up to 28 km/h NE | Rain 60% (4.2 mm)
```

Open an event to see a 3-hourly breakdown (6am to 9pm) of temperature, wind,
gusts and rain chance/amount. Data comes from [Open-Meteo](https://open-meteo.com)
(free, no API key). A GitHub Action rebuilds the file every 6 hours.

## Setup (about 5 minutes)

1. **Create a public GitHub repo** (e.g. `mosman-weather`). Public is needed for
   free GitHub Pages. The feed only contains Mosman weather, nothing personal.
2. **Upload these files** keeping the same structure:
   - `weather_feed.py`
   - `.github/workflows/update.yml`
   - `README.md`
3. **Allow the Action to push:** repo Settings > Actions > General >
   Workflow permissions > select **Read and write permissions** > Save.
4. **Run it once:** Actions tab > "Update weather feed" > Run workflow.
   After it finishes, `docs/weather.ics` should appear in the repo.
5. **Turn on Pages:** Settings > Pages > Source: *Deploy from a branch* >
   Branch: `main`, folder: `/docs` > Save.
6. Your feed URL will be:

   ```
   https://YOUR-GITHUB-USERNAME.github.io/mosman-weather/weather.ics
   ```

   Open that URL in a browser first to check it loads (it may download as a file, which is fine).

## Add it to Google Calendar

On a computer (the phone app can't add subscriptions):

1. Google Calendar > the **+** next to "Other calendars" > **From URL**.
2. Paste the feed URL > **Add calendar**.
3. It will appear under "Other calendars" and also sync to your phone.
   Tip: rename it and pick a colour in its settings.

Google refreshes subscribed calendars on its own schedule, often every
12 to 24 hours, so changes can lag behind the 6-hourly rebuilds.
That's a Google limitation, not something the script can speed up.

## Customising

Edit the CONFIG block at the top of `weather_feed.py`:

| Setting | What it does |
| --- | --- |
| `LATITUDE` / `LONGITUDE` | Location (currently Mosman) |
| `FORECAST_DAYS` | 1 to 16 |
| `HOURLY_STEP` | Hours between rows in the description (1 = hourly) |
| `HOURLY_FROM` / `HOURLY_TO` | Hours shown in the breakdown |
| `SHOW_GUSTS_IN_TITLE` | Put gust speed in the event title |

To show different values, change the title string in `build_events()`.
Open-Meteo has many more fields (UV index, humidity, apparent temperature,
etc.): see https://open-meteo.com/en/docs

## Run locally

```
python weather_feed.py
```

Needs Python 3.8+ and no extra packages.

## Notes

- GitHub pauses scheduled workflows on repos with no activity for 60 days.
  The bot's own commits normally count, but if the feed stops updating, check
  the Actions tab and re-enable the workflow.
- Open-Meteo's free tier is for non-commercial use. Four runs a day is far
  below its limits.
