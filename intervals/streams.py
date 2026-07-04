"""
從 intervals.icu 抓取單次騎乘的 streams 資料，輸出精簡分析摘要（JSON）。

用法：
  python3 -m intervals.streams <activity_id> [ftp]

輸出：
  {
    "power_curve": { "5s": {"watts": 450, "pct_ftp": 148}, ... },
    "fatigue": {
      "first_half_avg_watts": 185, "second_half_avg_watts": 158,
      "power_drop_pct": 14.6,
      "first_half_avg_hr": 145, "second_half_avg_hr": 159, "hr_drift_bpm": 14
    }
  }
"""

import sys
import json
from dotenv import load_dotenv

load_dotenv()

DURATIONS = {
    "5s": 5, "30s": 30, "1min": 60,
    "5min": 300, "10min": 600, "20min": 1200,
}


def best_effort(data, window):
    filled = [v for v in data if v is not None]
    if len(filled) < window:
        return None
    total = sum(filled[:window])
    best = total
    for i in range(window, len(filled)):
        total += filled[i] - filled[i - window]
        if total > best:
            best = total
    return round(best / window, 1)


def half_avg(data):
    vals = [v for v in data if v is not None]
    if not vals:
        return None, None
    mid = len(vals) // 2
    def avg(lst): return round(sum(lst) / len(lst), 1) if lst else None
    return avg(vals[:mid]), avg(vals[mid:])


def analyze(activity_id: str, ftp: int = 305) -> dict:
    from intervals.client import IntervalsClient
    client = IntervalsClient()
    streams = client.get_activity_streams(
        activity_id,
        types=["time", "watts", "heartrate", "cadence", "altitude"],
    )

    by_type = {ch["type"]: ch.get("data", []) for ch in streams}
    watts = by_type.get("watts", [])
    hr = by_type.get("heartrate", [])

    power_curve = {}
    for label, secs in DURATIONS.items():
        best = best_effort(watts, secs)
        if best is not None:
            power_curve[label] = {
                "watts": int(best),
                "pct_ftp": round(best / ftp * 100, 1),
            }

    w_first, w_second = half_avg(watts)
    hr_first, hr_second = half_avg(hr)

    fatigue = {}
    if w_first and w_second:
        fatigue["first_half_avg_watts"] = w_first
        fatigue["second_half_avg_watts"] = w_second
        fatigue["power_drop_pct"] = round((w_first - w_second) / w_first * 100, 1)
    if hr_first and hr_second:
        fatigue["first_half_avg_hr"] = hr_first
        fatigue["second_half_avg_hr"] = hr_second
        fatigue["hr_drift_bpm"] = round(hr_second - hr_first, 1)

    return {"power_curve": power_curve, "fatigue": fatigue}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python3 -m intervals.streams <activity_id> [ftp]", file=sys.stderr)
        sys.exit(1)
    activity_id = sys.argv[1]
    ftp = int(sys.argv[2]) if len(sys.argv) > 2 else 305
    result = analyze(activity_id, ftp)
    print(json.dumps(result, ensure_ascii=False, indent=2))
