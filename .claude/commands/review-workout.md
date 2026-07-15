列出指定月份的騎乘活動，讓使用者選擇後進行結構訓練 review，並對照原定課表計畫。

## 步驟

### 第一步：確定目標月份

從 `$ARGUMENTS` 讀取月份參數（格式 YYYY-MM）。
若未提供，使用今天的年月（例如 2026-07）。

### 第二步：列出該月活動

讀取 `data/YYYY/MM/` 目錄下的所有 `.json` 檔案，排除 `wellness.json` 和 `events.json`。

將活動列成編號清單，格式如下：

```
📅 2026 年 07 月 活動列表

 1. 2026-07-04  WP團練_北宜來回
 2. 2026-07-02  大佳河濱
 3. 2026-07-01  早餐騎_明德宮_阿清豆漿
...

請輸入編號來 review 該次訓練（或輸入 q 取消）：
```

### 第三步：等待使用者選擇

等使用者輸入編號後，再繼續。

### 第四步：讀取活動與體能資料

讀取使用者選擇的活動 JSON 檔案。

同時讀取同月的 `data/YYYY/MM/wellness.json`，找出該活動日期當天或最接近的 wellness 記錄，取得 CTL、ATL、TSB。

讀取 `coach/review_rules.md` 與 `coach/workout_review_rules.md` 作為評估依據。

### 第四點五步：取得暖身／緩和時間與 Laps 資訊（主段定義）

執行以下指令，從 intervals.icu 取得該活動的 `warmup_secs`、`cooldown_secs` 與 `lap_count`：

```bash
python3 -c "
from intervals.client import IntervalsClient
import json
client = IntervalsClient()
d = client.get_activity_detail('<activity_id>')
print(json.dumps({'warmup_secs': d['warmup_secs'], 'cooldown_secs': d['cooldown_secs'], 'lap_count': d['lap_count'], 'paired_event_id': d['paired_event_id']}))
"
```

- 若 `warmup_secs > 0` 或 `cooldown_secs > 0`：主段 = 總時間去除暖身與緩和
- 若兩者皆為 0：fallback 使用 active seconds（過濾 ≤30W）

記下 `lap_count` 判斷分段資料來源：
- `lap_count > 1`：活動有 device laps → 使用 laps 資料為主（在第六步加 `--has-laps`）
- `lap_count == 1`：無 device laps → fallback 使用 intervals.icu 自動分段

同時記下 `paired_event_id`（若非 null，後續直接用來查課表）。

### 第五步：取得原定課表計畫

先嘗試讀取本機 `data/YYYY/MM/events.json`，找出與活動**同日期**且 `category == "WORKOUT"` 的 event。

若本機沒有，執行以下指令從 API 查詢：

```bash
python3 -c "
from intervals.client import IntervalsClient
import json
client = IntervalsClient()
plan = client.get_workout_plan_for_date('YYYY-MM-DD')
print(json.dumps(plan))
"
```

若找到課表計畫，記錄：
- `name`：課表名稱
- `description`：人讀格式的課表內容
- `load`：預計 TSS

若找不到，在報告中註明「本次訓練無對應課表計畫」。

### 第六步：抓取 Streams 分析

從活動 JSON 取得 `id` 欄位，依第四點五步的 `lap_count` 決定指令（將 `WARMUP` 與 `COOLDOWN` 替換為秒數，`FTP` 替換為 goals.md 中的 FTP）：

**若 `lap_count > 1`（有 device laps，優先使用）：**
```bash
python3 -m intervals.streams <activity_id> <ftp> --warmup <WARMUP> --cooldown <COOLDOWN> --with-intervals --has-laps
```

**若 `lap_count == 1`（無 device laps，fallback 使用 intervals.icu 自動分段）：**
```bash
python3 -m intervals.streams <activity_id> <ftp> --warmup <WARMUP> --cooldown <COOLDOWN> --with-intervals
```

FTP 從 `goals.md` 讀取（格式：`| FTP | XXX W`）。

輸出包含：
- `power_curve`：各時長最佳功率與佔 FTP 百分比
- `fatigue`：主段前半 vs 後半的平均功率、衰退百分比、心率飄移
- `fatigue.segment`：說明主段定義方式（intervals.icu 切割 or active seconds fallback）
- `intervals`：每個 WORK/RECOVERY 段的逐組資料
  - WORK：`n`（組次）、`duration_secs`、`avg_watts`、`np_watts`、`avg_hr`、`avg_cadence`、`intensity_pct`、`zone`
    - `within.segments`：前段/中段/後段（≥90s）或前半/後半的功率/心率/踏頻均值
    - `within.delta`：首段到末段的數值變化量
  - RECOVERY：`end_hr`（最後 10 秒平均心率，代表進入下一組前的 HR 水位）
- `intervals_source`：分段資料來源（`"device laps"` 或 `"intervals.icu 自動分段"`）

若指令執行失敗，繼續使用摘要資料，並在報告中註明 streams 資料無法取得。

### 第六點五步：比對功率 PR

先從 `goals.md` 讀取體重（kg）。格式為 `- 體重：XX kg`，解析後取整數。

取得活動日期（YYYY-MM-DD）與年份（YYYY），計算活動前一天作為查詢截止日，執行以下指令：

```bash
python3 -c "
from intervals.client import IntervalsClient
from datetime import date, timedelta
import json
client = IntervalsClient()
activity_date = date.fromisoformat('YYYY-MM-DD')
day_before = (activity_date - timedelta(days=1)).isoformat()
year_start = 'YYYY-01-01'
all_time = client.get_power_bests(end=day_before, weight=WEIGHT)
year = client.get_power_bests(start=year_start, end=day_before, weight=WEIGHT)
print(json.dumps({'all_time': all_time, 'year': year}))
"
```

將 streams 的 `power_curve` 各時段與上述數字逐一比對：
- 大於等於 `all_time` → 🏆 All-time PR
- 大於等於 `year` 但未達 all-time → ⭐ 年度最佳
- 未達 → 顯示距離年度最佳的差距（-X W）

### 第七步：輸出 Review 報告

依照 `coach/review_rules.md` 輸出完整 review，並加入以下結構訓練專用段落：

```
📋 原定課表
  名稱：W2: tempo with neuromuscular power burst
  計畫 TSS：XX
  內容：
    8x 5min 90% FTP + 15s 150-170%
    6x 2min 115-130% / 3min z1

✅ 執行對照
  [對照 description 與 intervals 資料，說明目標功率區間達成情況]

**主段定義**：[說明 warmup/cooldown 切割方式或 fallback]
**分段來源**：[device laps（X 圈） 或 intervals.icu 自動分段（fallback）]

🔁 逐組分析
  [依 coach/workout_review_rules.md 的格式輸出逐組表格]
  [每個 WORK 組顯示：時長、zone、avg/NP 功率、avg HR、avg 踏頻]
  [組內三段（前/中/後）的功率、心率、踏頻數值與 delta]
  [RECOVERY 組顯示：時長、end_hr（代表下組前的 HR 水位）]

📊 組間趨勢摘要
  功率趨勢：[各 WORK 組 avg_watts 序列]
  心率趨勢：[各 WORK 組 avg_hr 序列]
  踏頻趨勢：[各 WORK 組 avg_cadence 序列]
  恢復 HR：[各 RECOVERY end_hr 序列]

**Power Curve（全程最佳努力）**
  5s：XXX W（XX% FTP）[🏆 / ⭐ / -X W]
  30s：XXX W（XX% FTP）
  1min：XXX W（XX% FTP）[🏆 / ⭐ / -X W]
  5min：XXX W（XX% FTP）[🏆 / ⭐ / -X W]
  20min：XXX W（XX% FTP）[🏆 / ⭐ / -X W]

**疲勞分析（主段）**
  前半段：平均 XXX W / 心率 XXX bpm
  後半段：平均 XXX W / 心率 XXX bpm
  功率衰退：XX%　心率飄移：+XX bpm
```

用繁體中文回覆，技術術語保留英文縮寫（TSS、CTL、NP、IF、VI 等）。
