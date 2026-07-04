列出指定月份的騎乘活動，讓使用者選擇後進行單次騎乘 review。

## 步驟

### 第一步：確定目標月份

從 `$ARGUMENTS` 讀取月份參數（格式 YYYY-MM）。
若未提供，使用今天的年月（例如 2026-07）。

### 第二步：列出該月活動

讀取 `data/YYYY/MM/` 目錄下的所有 `.json` 檔案，排除 `wellness.json`。

將活動列成編號清單，格式如下：

```
📅 2026 年 07 月 活動列表

 1. 2026-07-04  WP團練_北宜來回
 2. 2026-07-02  大佳河濱
 3. 2026-07-01  早餐騎_明德宮_阿清豆漿
...

請輸入編號來 review 該次騎乘（或輸入 q 取消）：
```

檔名格式為 `YYYY-MM-DD_活動名稱.json`，從檔名解析日期與名稱顯示給使用者。
若該目錄不存在或沒有活動檔，告知使用者並建議先執行 `python3 fetch.py`。

### 第三步：等待使用者選擇

等使用者輸入編號後，再繼續。

### 第四步：讀取摘要資料

讀取使用者選擇的活動 JSON 檔案。

同時讀取同月的 `data/YYYY/MM/wellness.json`，找出該活動日期當天或最接近的 wellness 記錄，取得 CTL、ATL、TSB。

讀取 `coach/review_rules.md` 作為評估依據。

### 第五步：抓取 Streams 分析

從活動 JSON 取得 `id` 欄位，執行以下指令抓取完整騎乘資料並計算分析摘要：

```bash
python3 -m intervals.streams <activity_id> <ftp>
```

FTP 從 `goals.md` 讀取（目前 305 W）。

輸出為 JSON，包含：
- `power_curve`：各時長（5s、30s、1min、5min、10min、20min）的最佳功率與佔 FTP 百分比
- `fatigue`：前半段 vs 後半段的平均功率、功率衰退百分比、平均心率、心率飄移

若指令執行失敗（例如 activity_id 無效），繼續使用摘要資料進行 review，並在報告中註明 streams 資料無法取得。

### 第五點五步：比對功率 PR

取得活動年份（從活動日期的 YYYY），執行以下指令抓取 all-time 與當年度功率最佳紀錄：

```bash
python3 -c "
from intervals.client import IntervalsClient
import json
client = IntervalsClient()
all_time = client.get_power_bests(weight=75)
year = client.get_power_bests(start='YYYY-01-01', end='YYYY-12-31', weight=75)
print(json.dumps({'all_time': all_time, 'year': year}))
"
```

（將 `YYYY` 替換為活動的實際年份）

拿到的 `all_time` 與 `year` 分別代表歷史 PR 與年度最佳。

將 streams 的 `power_curve` 各時段最佳功率與上述數字逐一比對：

- 若本次某時段功率 **超過 `all_time` 對應值** → 標記為 🏆 All-time PR
- 若本次某時段功率 **超過 `year` 對應值** 但未超過 all-time → 標記為 ⭐ 年度最佳
- 若未超過 → 顯示距離年度最佳的差距（-X W）

可比對的時段：5s、1min、5min、20min（streams 有對應值的時段才比）。

若抓取失敗，跳過此步驟並在報告中註明。

### 第六步：輸出 Review 報告

依照 `coach/review_rules.md` 中定義的報告格式，輸出完整的騎乘 review，並加入 streams 分析結果。

**報告格式補充（streams 部分）：**

在「強度總結」之後加入：

```
**Power Curve（最佳努力）**
  5s：XXX W（XX% FTP）[🏆 All-time PR / ⭐ 年度最佳 / -X W]
  30s：XXX W（XX% FTP）
  1min：XXX W（XX% FTP）[🏆 / ⭐ / -X W]
  5min：XXX W（XX% FTP）[🏆 / ⭐ / -X W]
  20min：XXX W（XX% FTP）[🏆 / ⭐ / -X W]

  PR 狀態說明：🏆 All-time PR　⭐ 年度最佳　-X W 距年度最佳差距

**疲勞分析**
  前半段：平均 XXX W / 心率 XXX bpm
  後半段：平均 XXX W / 心率 XXX bpm
  功率衰退：XX%　心率飄移：+XX bpm
```

用繁體中文回覆，技術術語保留英文縮寫（TSS、CTL、NP、IF、VI 等）。
