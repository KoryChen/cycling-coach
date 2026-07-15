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

from __future__ import annotations

import re
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

_GOALS_PATH = Path(__file__).parent.parent / "goals.md"


def _read_ftp_from_goals() -> int | None:
    if not _GOALS_PATH.exists():
        return None
    for line in _GOALS_PATH.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*FTP\s*\|\s*(\d+)\s*W", line)
        if m:
            return int(m.group(1))
    return None

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


def active_seconds(watts: list, hr: list, threshold: int = 30):
    """Filter to seconds where power > threshold (removes stops/coasting)."""
    w_active = [w for w in watts if w is not None and w > threshold]
    hr_active = [h for h, w in zip(hr, watts) if w is not None and w > threshold and h is not None]
    return w_active, hr_active


def interval_within(w_slice: list, hr_slice: list, cad_slice: list) -> dict | None:
    """Within-interval segment analysis: thirds for >=90s intervals, halves for shorter."""
    n = len(w_slice)
    if n == 0:
        return None

    def seg_avg(data, a, b, min_val=None):
        seg = [v for v in data[a:b] if v is not None and (min_val is None or v >= min_val)]
        return round(sum(seg) / len(seg), 1) if seg else None

    use_thirds = n >= 90
    cuts = [0, n // 3, 2 * n // 3, n] if use_thirds else [0, n // 2, n]
    labels = ["前段", "中段", "後段"] if use_thirds else ["前半", "後半"]

    segments = []
    for i, label in enumerate(labels):
        a, b = cuts[i], cuts[i + 1]
        segments.append({
            "label": label,
            "watts": seg_avg(w_slice, a, b),
            "hr": seg_avg(hr_slice, a, b),
            "cadence": seg_avg(cad_slice, a, b, min_val=20),
        })

    first, last = segments[0], segments[-1]
    delta = {}
    for key in ("watts", "hr", "cadence"):
        f, l = first.get(key), last.get(key)
        if f is not None and l is not None:
            delta[key] = round(l - f, 1)

    return {"segments": segments, "delta": delta}


def analyze(activity_id: str, ftp: int = 305, warmup_secs: int = 0, cooldown_secs: int = 0, with_intervals: bool = False, has_laps: bool = False) -> dict:
    from intervals.client import IntervalsClient
    client = IntervalsClient()
    streams = client.get_activity_streams(
        activity_id,
        types=["time", "watts", "heartrate", "cadence", "altitude"],
    )

    by_type = {ch["type"]: ch.get("data", []) for ch in streams}
    raw_times = by_type.get("time", [])

    # ride_t0: first timestamp (usually 0); needed to map interval indices to 1Hz positions
    valid_t = [int(t) for t in raw_times if t is not None]
    ride_t0 = valid_t[0] if valid_t else 0

    watts = resample_to_1hz(raw_times, by_type.get("watts", []))
    hr    = resample_to_1hz(raw_times, by_type.get("heartrate", []))
    cad   = resample_to_1hz(raw_times, by_type.get("cadence", []))

    # Main segment: trim warmup/cooldown if provided
    if warmup_secs > 0 or cooldown_secs > 0:
        end = len(watts) - cooldown_secs if cooldown_secs > 0 else len(watts)
        watts_main = watts[warmup_secs:end]
        hr_main = hr[warmup_secs:end]
        fatigue_note = f"主段（去除暖身 {warmup_secs//60}min、緩和 {cooldown_secs//60}min）"
    else:
        watts_main, hr_main = active_seconds(watts, hr)
        fatigue_note = "active seconds（過濾 ≤30W）"

    power_curve = {}
    for label, secs in DURATIONS.items():
        best = best_effort(watts, secs)
        if best is not None:
            power_curve[label] = {
                "watts": int(best),
                "pct_ftp": round(best / ftp * 100, 1),
            }

    w_first, w_second = half_avg(watts_main)
    hr_first, hr_second = half_avg(hr_main)

    fatigue = {"segment": fatigue_note}
    if w_first and w_second:
        fatigue["first_half_avg_watts"] = w_first
        fatigue["second_half_avg_watts"] = w_second
        fatigue["power_drop_pct"] = round((w_first - w_second) / w_first * 100, 1)
    if hr_first and hr_second:
        fatigue["first_half_avg_hr"] = hr_first
        fatigue["second_half_avg_hr"] = hr_second
        fatigue["hr_drift_bpm"] = round(hr_second - hr_first, 1)

    result: dict = {"power_curve": power_curve, "fatigue": fatigue}

    if with_intervals:
        icu_ivs = client.get_activity_intervals(activity_id)
        intervals_source = "device laps" if has_laps else "intervals.icu 自動分段"
        n_raw = len(raw_times)
        intervals_out = []
        work_n = 0

        for iv in icu_ivs:
            iv_type = iv.get("type")  # "WORK" or "RECOVERY"
            si = iv.get("start_index", 0)
            ei = iv.get("end_index", 0)

            # Map raw stream indices → 1Hz array positions
            t_s = int(raw_times[min(si, n_raw - 1)]) - ride_t0 if n_raw > 0 else 0
            t_e = int(raw_times[min(ei, n_raw - 1)]) - ride_t0 if n_raw > 0 else 0
            t_s, t_e = max(0, t_s), max(0, t_e)

            entry: dict = {
                "type": iv_type,
                "duration_secs": iv.get("moving_time"),
                "group_id": iv.get("group_id"),
                "zone": iv.get("zone"),
                "avg_watts": iv.get("average_watts"),
                "np_watts": iv.get("weighted_average_watts"),
                "avg_hr": iv.get("average_heartrate"),
                "avg_cadence": round(iv.get("average_cadence") or 0, 1),
                "intensity_pct": iv.get("intensity"),
            }

            if iv_type == "WORK":
                work_n += 1
                entry["n"] = work_n
                w_sl  = watts[t_s:t_e]
                hr_sl = hr[t_s:t_e]
                cd_sl = cad[t_s:t_e]
                entry["within"] = interval_within(w_sl, hr_sl, cd_sl)
            elif iv_type == "RECOVERY":
                # For recovery: just report end HR (last 10s) to show how well HR recovered
                hr_sl = hr[t_s:t_e]
                end_hr = None
                if hr_sl:
                    tail = [v for v in hr_sl[-10:] if v is not None]
                    end_hr = round(sum(tail) / len(tail), 1) if tail else None
                entry["end_hr"] = end_hr

            intervals_out.append(entry)

        result["intervals"] = intervals_out
        result["intervals_source"] = intervals_source

    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="分析單次騎乘 streams 資料")
    parser.add_argument("activity_id")
    parser.add_argument("ftp", nargs="?", type=int)
    parser.add_argument("--warmup", type=int, default=0, help="暖身秒數（從 intervals.icu 取得）")
    parser.add_argument("--cooldown", type=int, default=0, help="緩和秒數（從 intervals.icu 取得）")
    parser.add_argument("--with-intervals", action="store_true", help="輸出逐組組內分析（功率/心率/踏頻三段趨勢）")
    parser.add_argument("--has-laps", action="store_true", help="活動有 device laps（icu_lap_count > 1），分段來源標注為 device laps")
    args = parser.parse_args()

    ftp = args.ftp
    if ftp is None:
        ftp = _read_ftp_from_goals()
        if ftp is None:
            print("錯誤：未提供 FTP 且無法從 goals.md 讀取。請執行 /rider-setup 建立 goals.md，或手動傳入 FTP。", file=sys.stderr)
            sys.exit(1)

    result = analyze(
        args.activity_id, ftp,
        warmup_secs=args.warmup,
        cooldown_secs=args.cooldown,
        with_intervals=args.with_intervals,
        has_laps=args.has_laps,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
