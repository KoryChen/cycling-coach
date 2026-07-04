"""
從 intervals.icu 抓取資料，儲存為結構化 JSON。

目錄結構：
  data/
  └── YYYY/
      └── MM/
          ├── YYYY-MM-DD_<活動名稱>.json  # 活動詳情（每次一個檔案）
          └── wellness.json               # 當月 CTL/ATL/TSB 等體能資料

用法：
  python fetch.py                        # 最近 90 天
  python fetch.py --start 2024-01-01     # 從指定日期到今天
  python fetch.py --start 2024-01-01 --end 2024-12-31
  python fetch.py --all                  # 全部歷史（從 2020-01-01）
  python fetch.py --verbose              # 顯示跳過的項目
"""

import os
import sys
import json
import argparse
import logging
import re
import time
from pathlib import Path
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

_required = ["INTERVALS_ATHLETE_ID", "INTERVALS_API_KEY"]
_missing = [k for k in _required if not os.environ.get(k)]
if _missing:
    print(f"錯誤：缺少環境變數 {', '.join(_missing)}")
    print("請複製 .env.example 為 .env 並填入你的 API 金鑰。")
    sys.exit(1)

from intervals.client import IntervalsClient

DATA_DIR = Path(__file__).parent / "data"

logger = logging.getLogger("fetch")


def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s  %(levelname)-5s  %(message)s",
        datefmt="%H:%M:%S",
        level=level,
        stream=sys.stdout,
    )


def slugify(name: str) -> str:
    slug = re.sub(r"[^\w一-鿿]+", "_", name)
    slug = slug.strip("_")
    return slug[:50] if slug else "activity"


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def fmt_eta(elapsed: float, done: int, total: int) -> str:
    if done == 0:
        return "--:--"
    rate = done / elapsed
    remaining = (total - done) / rate
    m, s = divmod(int(remaining), 60)
    return f"{m:02d}:{s:02d}"


def fetch_activities(client: IntervalsClient, oldest: str, newest: str) -> dict:
    logger.info("活動列表查詢：%s ~ %s", oldest, newest)
    activities = client.get_activities_in_range(oldest, newest)
    total = len(activities)
    logger.info("找到 %d 筆活動，開始下載...", total)

    stats = {"downloaded": 0, "skipped": 0, "errors": 0}
    start = time.monotonic()

    for i, act in enumerate(activities, 1):
        act_date = act.get("date", "")
        if not act_date or len(act_date) < 10:
            continue

        act_id = str(act.get("id", ""))
        act_name = act.get("name") or "untitled"
        year, month = act_date[:4], act_date[5:7]

        slug = slugify(act_name)
        filename = f"{act_date}_{slug}.json"
        path = DATA_DIR / year / month / filename

        pct = i / total * 100
        elapsed = time.monotonic() - start

        if path.exists():
            stats["skipped"] += 1
            logger.debug("[%d/%d | %5.1f%%] 跳過：%s", i, total, pct, filename)
            continue

        eta = fmt_eta(elapsed, i - 1 - stats["skipped"], stats["downloaded"] + stats["errors"] + 1)
        logger.info("[%d/%d | %5.1f%% | ETA %s] 下載：%s", i, total, pct, eta, filename)

        try:
            detail = client.get_activity_detail(act_id)
            save_json(path, detail)
            stats["downloaded"] += 1
        except Exception as e:
            stats["errors"] += 1
            logger.warning("[%d/%d] 錯誤 %s：%s", i, total, filename, e)

    elapsed = time.monotonic() - start
    logger.info(
        "活動完成｜下載 %d｜跳過 %d｜錯誤 %d｜耗時 %.1f 秒",
        stats["downloaded"], stats["skipped"], stats["errors"], elapsed,
    )
    return stats


def fetch_wellness(client: IntervalsClient, oldest: str, newest: str) -> dict:
    logger.info("體能資料查詢：%s ~ %s", oldest, newest)
    records = client.get_wellness_in_range(oldest, newest)
    logger.info("找到 %d 天體能資料，整理中...", len(records))

    by_month: dict[str, list] = {}
    for r in records:
        d = r.get("date", "")
        if not d or len(d) < 7:
            continue
        by_month.setdefault(d[:7], []).append(r)

    saved = 0
    for ym in sorted(by_month):
        year, month = ym.split("-")
        path = DATA_DIR / year / month / "wellness.json"

        if path.exists():
            with open(path, encoding="utf-8") as f:
                existing = {r["date"]: r for r in json.load(f)}
        else:
            existing = {}

        for r in by_month[ym]:
            existing[r["date"]] = r

        merged = sorted(existing.values(), key=lambda r: r.get("date", ""))
        save_json(path, merged)
        saved += len(merged)
        logger.debug("wellness %s：%d 筆", ym, len(merged))

    logger.info("體能完成｜共 %d 個月，%d 筆記錄已儲存", len(by_month), saved)
    return {"months": len(by_month), "records": saved}


def main():
    parser = argparse.ArgumentParser(description="從 intervals.icu 下載訓練資料")
    parser.add_argument("--start", help="開始日期 YYYY-MM-DD（預設：90 天前）")
    parser.add_argument("--end", help="結束日期 YYYY-MM-DD（預設：今天）")
    parser.add_argument("--all", action="store_true", dest="all_time",
                        help="下載全部歷史資料（從 2020-01-01）")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="顯示跳過的項目（DEBUG 層級）")
    args = parser.parse_args()

    setup_logging(args.verbose)

    today = date.today().isoformat()
    oldest = "2020-01-01" if args.all_time else (args.start or (date.today() - timedelta(days=90)).isoformat())
    newest = args.end or today

    logger.info("=" * 50)
    logger.info("intervals.icu 資料下載")
    logger.info("範圍：%s ~ %s", oldest, newest)
    logger.info("儲存至：%s", DATA_DIR)
    logger.info("=" * 50)

    t0 = time.monotonic()
    client = IntervalsClient()

    act_stats = fetch_activities(client, oldest, newest)
    fetch_wellness(client, oldest, newest)

    total_elapsed = time.monotonic() - t0
    logger.info("=" * 50)
    logger.info(
        "全部完成｜總耗時 %.1f 秒（%.1f 分鐘）",
        total_elapsed, total_elapsed / 60,
    )


if __name__ == "__main__":
    main()
