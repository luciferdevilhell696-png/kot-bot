from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Union

import ujson
from geopy import Nominatim
from geopy.exc import GeocoderServiceError

from app.bot.libs.http import AiohttpClient
from app.config import settings


@dataclass(slots=True)
class WeatherArticleResponse:
    city: str
    country: str
    temp_c: float
    condition: str
    condition_code: int
    feelslike_c: float
    humidity: int
    pressure_mb: int
    wind_mph: float
    last_updated: str
    vis_km: int
    wind_dir: str
    sunrise: str
    sunset: str
    day_1_night_temp: float
    day_1_night_condition: str
    day_1_night_condition_code: int
    day_1_morning_temp: float
    day_1_morning_condition: str
    day_1_morning_condition_code: int
    day_1_day_temp: float
    day_1_day_condition: str
    day_1_day_condition_code: int
    day_1_evening_temp: float
    day_1_evening_condition: str
    day_1_evening_condition_code: int
    day_2_date: str
    day_2_morning_temp: float
    day_2_morning_condition: str
    day_2_morning_condition_code: int
    day_2_day_temp: float
    day_2_day_condition: str
    day_2_day_condition_code: int
    day_2_evening_temp: float
    day_2_evening_condition: str
    day_2_evening_condition_code: int
    day_2_night_temp: float
    day_2_night_condition: str
    day_2_night_condition_code: int
    day_3_date: str
    day_3_morning_temp: float
    day_3_morning_condition: str
    day_3_morning_condition_code: int
    day_3_day_temp: float
    day_3_day_condition: str
    day_3_day_condition_code: int
    day_3_evening_temp: float
    day_3_evening_condition: str
    day_3_evening_condition_code: int
    day_3_night_temp: float
    day_3_night_condition: str
    day_3_night_condition_code: int


@dataclass(slots=True)
class Coordinate:
    latitude: float
    longitude: float


def get_coordinates(city: str) -> Optional[Coordinate]:
    geo = Nominatim(user_agent="my_services_bot")

    try:
        loc = geo.geocode(city)
    except GeocoderServiceError:
        return None

    if loc is None:
        return None

    return Coordinate(
        latitude=loc.latitude,
        longitude=loc.longitude,
    )


def generate_current_date(date_timestamp: float) -> str:
    return datetime.fromtimestamp(date_timestamp).strftime("%d.%m.%Y")


class WeatherAPI:
    BASE_URL = "https://api.weatherapi.com/v1/forecast.json?key={api_key}&q={coordinate}&days=3&aqi=no&lang=ru"

    def __init__(self) -> None:
        self.http = AiohttpClient()
        self._api_key = settings.WEATHER_API_KEY.get_secret_value()

    async def get_article(
        self, city: str
    ) -> Union[Optional[WeatherArticleResponse], str]:
        coordinate = get_coordinates(city)

        if coordinate is None:
            return "Город не найден"

        response = await self.http.request_raw(
            self.BASE_URL.format(
                api_key=self._api_key,
                coordinate=f"{coordinate.latitude},{coordinate.longitude}",
            )
        )

        match response.status:
            case 200:
                data = await response.json(
                    encoding="utf-8", loads=ujson.loads, content_type=None
                )

                location = data["location"]
                current = data["current"]

                forecast_day_1: dict = data["forecast"]["forecastday"][0]
                forecast_day_2: dict = data["forecast"]["forecastday"][1]
                forecast_day_3: dict = data["forecast"]["forecastday"][2]
                "".rstrip()
                sunrise = forecast_day_1["astro"]["sunrise"].rstrip(" AM")
                sunset_12_hour = (
                    forecast_day_1["astro"]["sunset"].rstrip(" PM").split(":")
                )
                sunset = f"{int(sunset_12_hour[0]) + 12}:{sunset_12_hour[1]}"

                return WeatherArticleResponse(
                    city=location["name"],
                    country=location["country"],
                    temp_c=current["temp_c"],
                    condition=current["condition"]["text"],
                    condition_code=int(current["condition"]["code"]),
                    feelslike_c=current["feelslike_c"],
                    humidity=current["humidity"],
                    pressure_mb=round(int(current["pressure_mb"]) * 0.750062),
                    wind_mph=current["wind_mph"],
                    vis_km=current["vis_km"],
                    wind_dir=current["wind_dir"],
                    last_updated=datetime.fromtimestamp(
                        current["last_updated_epoch"]
                    ).strftime("%d.%m.%Y в %H:%M"),
                    sunrise=sunrise,
                    sunset=sunset,
                    day_1_morning_temp=forecast_day_1["hour"][7]["temp_c"],
                    day_1_day_temp=forecast_day_1["hour"][12]["temp_c"],
                    day_1_evening_temp=forecast_day_1["hour"][18]["temp_c"],
                    day_1_night_temp=forecast_day_1["hour"][0]["temp_c"],
                    day_1_morning_condition=forecast_day_1["hour"][7]["condition"][
                        "text"
                    ],
                    day_1_morning_condition_code=forecast_day_1["hour"][7]["condition"][
                        "code"
                    ],
                    day_1_day_condition=forecast_day_1["hour"][12]["condition"]["text"],
                    day_1_day_condition_code=forecast_day_1["hour"][12]["condition"][
                        "code"
                    ],
                    day_1_evening_condition=forecast_day_1["hour"][18]["condition"][
                        "text"
                    ],
                    day_1_evening_condition_code=forecast_day_1["hour"][18][
                        "condition"
                    ]["code"],
                    day_1_night_condition=forecast_day_1["hour"][0]["condition"][
                        "text"
                    ],
                    day_1_night_condition_code=forecast_day_1["hour"][0]["condition"][
                        "code"
                    ],
                    day_2_date=generate_current_date(forecast_day_2["date_epoch"]),
                    day_2_morning_temp=forecast_day_2["hour"][7]["temp_c"],
                    day_2_day_temp=forecast_day_2["hour"][12]["temp_c"],
                    day_2_evening_temp=forecast_day_2["hour"][18]["temp_c"],
                    day_2_night_temp=forecast_day_2["hour"][0]["temp_c"],
                    day_2_morning_condition=forecast_day_2["hour"][7]["condition"][
                        "text"
                    ],
                    day_2_morning_condition_code=forecast_day_2["hour"][7]["condition"][
                        "code"
                    ],
                    day_2_day_condition=forecast_day_2["hour"][12]["condition"]["text"],
                    day_2_day_condition_code=forecast_day_2["hour"][12]["condition"][
                        "code"
                    ],
                    day_2_evening_condition=forecast_day_2["hour"][18]["condition"][
                        "text"
                    ],
                    day_2_evening_condition_code=forecast_day_2["hour"][18][
                        "condition"
                    ]["code"],
                    day_2_night_condition=forecast_day_2["hour"][0]["condition"][
                        "text"
                    ],
                    day_2_night_condition_code=forecast_day_2["hour"][0]["condition"][
                        "code"
                    ],
                    day_3_date=generate_current_date(forecast_day_3["date_epoch"]),
                    day_3_morning_temp=forecast_day_3["hour"][7]["temp_c"],
                    day_3_day_temp=forecast_day_3["hour"][12]["temp_c"],
                    day_3_evening_temp=forecast_day_3["hour"][18]["temp_c"],
                    day_3_night_temp=forecast_day_3["hour"][0]["temp_c"],
                    day_3_morning_condition=forecast_day_3["hour"][7]["condition"][
                        "text"
                    ],
                    day_3_morning_condition_code=forecast_day_3["hour"][7]["condition"][
                        "code"
                    ],
                    day_3_day_condition=forecast_day_3["hour"][12]["condition"]["text"],
                    day_3_day_condition_code=forecast_day_3["hour"][12]["condition"][
                        "code"
                    ],
                    day_3_evening_condition=forecast_day_3["hour"][18]["condition"][
                        "text"
                    ],
                    day_3_evening_condition_code=forecast_day_3["hour"][18][
                        "condition"
                    ]["code"],
                    day_3_night_condition=forecast_day_3["hour"][0]["condition"][
                        "text"
                    ],
                    day_3_night_condition_code=forecast_day_3["hour"][0]["condition"][
                        "code"
                    ],
                )
            case 400:
                return "Город не найден"
            case 404:
                return "Сервер погоды недоступен, попробуйте повторить через некоторое время"
            case _:
                return None
