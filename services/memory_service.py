from repos.memories_repo import MemoriesRepo
from services.geocode_service import GeocodeService
from services.weather_service import WeatherService


class MemoryService:
    def __init__(self):
        self.repo = MemoriesRepo()
        self.geocode = GeocodeService()
        self.weather = WeatherService()

    def save_moment(
        self,
        family_id: int,
        user_id: int,
        photo_file_id: str,
        caption: str,
        latitude: float | None,
        longitude: float | None,
    ) -> dict:
        city = place = weather = None
        temperature = None
        if latitude is not None and longitude is not None:
            city, place = self.geocode.reverse(latitude, longitude)
            weather, temperature = self.weather.by_coords(latitude, longitude)

        self.repo.create_moment(
            family_id,
            user_id,
            photo_file_id,
            caption,
            latitude,
            longitude,
            city,
            place,
            weather,
            temperature,
        )
        return {
            "caption": caption,
            "city": city,
            "place": place,
            "weather": weather,
            "temperature": temperature,
        }

    def feed(self, family_id: int):
        return self.repo.latest(family_id)
