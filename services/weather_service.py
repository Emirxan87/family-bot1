import json
import urllib.parse
import urllib.request

from config import OPENWEATHER_API_KEY


class WeatherService:
    def by_coords(self, lat: float, lon: float) -> tuple[str | None, float | None]:
        if not OPENWEATHER_API_KEY:
            return None, None
        try:
            q = urllib.parse.urlencode(
                {
                    "lat": lat,
                    "lon": lon,
                    "appid": OPENWEATHER_API_KEY,
                    "units": "metric",
                    "lang": "ru",
                }
            )
            with urllib.request.urlopen(
                f"https://api.openweathermap.org/data/2.5/weather?{q}", timeout=5
            ) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            weather = data.get("weather", [{}])[0].get("description")
            temp = data.get("main", {}).get("temp")
            return weather, temp
        except Exception:
            return None, None
