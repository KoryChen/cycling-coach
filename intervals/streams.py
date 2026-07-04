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


def resample_to_1hz(times, values):
    """Resample non-uniform time-series to 1Hz using forward-fill."""
    pairs = [(int(t), v) for t, v in zip(times, values) if t is not None and v is not None]
    if not pairs:
        return []
    t_start, t_end = pairs[0][0], pairs[-1][0]
    result = []
    idx = 0
    for t in range(t_start, t_end + 1):
        while idx + 1 < len(pairs) and pairs[idx + 1][0] <= t:
            idx += 1
        result.append(pairs[idx][1])
    return result


def best_effort(data, window):
    if len(data) < window:
        return None
    total = sum(data[:window])
    best = total
    for i in range(window, len(data)):
        total += data[i] - data[i - window]
        if total > best:
            best = total
    return round(best / window, 1)


def half_avg(data):
    if not data:
        return None, None
    mid = len(data) // 2
    def avg(lst): return round(sum(lst) / len(lst), 1) if lst else None
    return avg(data[:mid]), avg(data[mid:])


def analyze(activity_id: str, ftp: int = 305) -> dict:
    from intervals.client import IntervalsClient
    client = IntervalsClient()
    streams = client.get_activity_streams(
        activity_id,
        types=["time", "watts", "heartrate", "cadence", "altitude"],
    )

    by_type = {ch["type"]: ch.get("data", []) for ch in streams}
    times = by_type.get("time", [])
    watts = resample_to_1hz(times, by_type.get("watts", []))
    hr = resample_to_1hz(times, by_type.get("heartrate", []))

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
