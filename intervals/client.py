from __future__ import annotations

import os
import requests
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://intervals.icu/api/v1"


class IntervalsClient:
    def __init__(self):
        self.athlete_id = os.environ["INTERVALS_ATHLETE_ID"]
        self.api_key = os.environ["INTERVALS_API_KEY"]
        self.session = requests.Session()
        self.session.auth = ("API_KEY", self.api_key)

    def _get(self, path: str, params: dict = None) -> dict | list:
        url = f"{BASE_URL}/athlete/{self.athlete_id}/{path}"
        resp = self.session.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict) -> dict:
        url = f"{BASE_URL}/athlete/{self.athlete_id}/{path}"
        resp = self.session.post(url, json=body)
        resp.raise_for_status()
        return resp.json()

    def get_athlete_profile(self) -> dict:
        data = self._get("")
        return {
            "name": data.get("name"),
            "ftp": data.get("ftp"),
            "weight": data.get("weight"),
            "pace_units": data.get("pace_units"),
        }

    def get_recent_activities(self, days: int = 14) -> list[dict]:
        oldest = (date.today() - timedelta(days=days)).isoformat()
        newest = date.today().isoformat()
        return self.get_activities_in_range(oldest, newest)

    def get_activities_in_range(self, oldest: str, newest: str) -> list[dict]:
        activities = self._get("activities", params={"oldest": oldest, "newest": newest})
        result = []
        for a in activities:
            result.append({
                "id": a.get("id"),
                "name": a.get("name"),
                "date": a.get("start_date_local", "")[:10],
                "type": a.get("type"),
                "duration_seconds": a.get("moving_time"),
                "distance_m": a.get("distance"),
                "elevation_gain_m": a.get("total_elevation_gain"),
                "avg_power_watts": a.get("icu_average_watts"),
                "normalized_power_watts": a.get("icu_weighted_avg_watts"),
                "avg_heart_rate": a.get("average_heartrate"),
                "tss": a.get("icu_training_load"),
                "intensity_factor": a.get("icu_intensity"),
            })
        return result

    def get_activity_detail(self, activity_id: str) -> dict:
        result = self._get(f"activities/{activity_id}")
        data = result[0] if isinstance(result, list) else result
        return {
            "id": data.get("id"),
            "name": data.get("name"),
            "date": data.get("start_date_local", "")[:10],
            "type": data.get("type"),
            "duration_seconds": data.get("moving_time"),
            "distance_m": data.get("distance"),
            "elevation_gain_m": data.get("total_elevation_gain"),
            "avg_power_watts": data.get("icu_average_watts"),
            "normalized_power_watts": data.get("icu_weighted_avg_watts"),
            "variability_index": data.get("icu_variability_index"),
            "efficiency_factor": data.get("icu_efficiency_factor"),
            "avg_heart_rate": data.get("average_heartrate"),
            "max_heart_rate": data.get("max_heartrate"),
            "avg_cadence": data.get("average_cadence"),
            "decoupling": data.get("decoupling"),
            "tss": data.get("icu_training_load"),
            "intensity_factor": data.get("icu_intensity"),
            "power_zone_times": data.get("icu_zone_times"),
            "hr_zone_times": data.get("icu_hr_zone_times"),
            "hr_zones": data.get("icu_hr_zones"),
            "power_zones": data.get("icu_power_zones"),
        }

    def get_wellness(self, days: int = 14) -> list[dict]:
        oldest = (date.today() - timedelta(days=days)).isoformat()
        newest = date.today().isoformat()
        return self.get_wellness_in_range(oldest, newest)

    def get_wellness_in_range(self, oldest: str, newest: str) -> list[dict]:
        records = self._get("wellness", params={"oldest": oldest, "newest": newest})
        result = []
        for r in records:
            ctl = r.get("ctl")
            atl = r.get("atl")
            tsb = r.get("tsb")
            if tsb is None and ctl is not None and atl is not None:
                tsb = round(ctl - atl, 2)
            result.append({
                "date": r.get("id"),
                "ctl": ctl,
                "atl": atl,
                "tsb": tsb,
                "hrv": r.get("hrv"),
                "sleep_seconds": r.get("sleepSecs"),
                "fatigue": r.get("fatigue"),
                "mood": r.get("mood"),
                "soreness": r.get("soreness"),
            })
        return result

    def get_activity_streams(self, activity_id: str, types: list[str] = None) -> list[dict]:
        if types is None:
            types = ["time", "watts", "heartrate", "cadence", "altitude"]
        url = f"https://intervals.icu/api/v1/activity/{activity_id}/streams"
        resp = self.session.get(url, params={"types": ",".join(types)})
        resp.raise_for_status()
        return resp.json()

    def get_upcoming_events(self, days: int = 30) -> list[dict]:
        oldest = date.today().isoformat()
        newest = (date.today() + timedelta(days=days)).isoformat()
        events = self._get("events", params={"oldest": oldest, "newest": newest})
        result = []
        for e in events:
            result.append({
                "id": e.get("id"),
                "name": e.get("name"),
                "date": e.get("start_date_local", "")[:10],
                "type": e.get("type"),
                "description": e.get("description"),
            })
        return result

    def get_power_bests(
        self,
        start: str = None,
        end: str = None,
        weight: float = None,
        activity_type: str = "Ride",
    ) -> dict:
        """
        Returns best power for standard durations.
        No start/end = all-time PR. Provide both for a date range.
        """
        if start is None and end is None:
            params = {"type": activity_type, "curves": "all"}
        else:
            params = {"type": activity_type}
            if start:
                params["start"] = start
            if end:
                params["end"] = end

        data = self._get("power-curves", params=params)
        curves = data.get("list", [])
        if not curves:
            return {}

        curve = curves[0]
        secs_list = curve["secs"]
        values = curve["values"]

        def best_at(target_secs: int) -> int:
            idx = min(range(len(secs_list)), key=lambda i: abs(secs_list[i] - target_secs))
            return values[idx]

        targets = {"5s": 5, "1min": 60, "5min": 300, "20min": 1200, "60min": 3600}
        result = {}
        for label, s in targets.items():
            w = best_at(s)
            entry = {"watts": w}
            if weight:
                entry["wkg"] = round(w / weight, 2)
            result[label] = entry

        return result

    def create_workout(
        self,
        start_date: str,
        name: str,
        description: str,
        workout_type: str = "Ride",
        load: int = None,
    ) -> dict:
        body = {
            "category": "WORKOUT",
            "start_date_local": f"{start_date}T00:00:00",
            "name": name,
            "description": description,
            "type": workout_type,
        }
        if load is not None:
            body["load"] = load
        return self._post("events", body)
