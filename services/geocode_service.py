import json
import urllib.parse
import urllib.request


class GeocodeService:
    def reverse(self, lat: float, lon: float) -> tuple[str | None, str | None]:
        try:
            q = urllib.parse.urlencode({"format": "jsonv2", "lat": lat, "lon": lon, "zoom": 18})
            req = urllib.request.Request(
                f"https://nominatim.openstreetmap.org/reverse?{q}",
                headers={"User-Agent": "family-bot/1.0"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            addr = data.get("address", {})
            city = addr.get("city") or addr.get("town") or addr.get("village")
            place = data.get("name") or data.get("display_name")
            return city, place
        except Exception:
            return None, None
