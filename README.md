# AI 自行車教練

以 Claude AI 為核心的個人自行車訓練助手，整合 [intervals.icu](https://intervals.icu) API，支援訓練分析、課表規劃與騎乘 review。

## 功能

- **資料同步**：從 intervals.icu 下載歷史活動與體能數據，儲存為本地 JSON
- **Claude Code 指令**：在 Claude Code 中直接使用 `/fitness`、`/plan`、`/review-ride`、`/weekly-review`

## 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
cp .env.example .env
```

編輯 `.env`，填入以下兩個金鑰：

| 變數 | 說明 |
|---|---|
| `INTERVALS_ATHLETE_ID` | intervals.icu 運動員 ID |
| `INTERVALS_API_KEY` | intervals.icu API 金鑰 |

**取得 Athlete ID**：登入 intervals.icu 後，網址列會顯示 `intervals.icu/athlete/i/XXXXXXXX`，其中 `XXXXXXXX` 就是你的 Athlete ID。

**取得 API 金鑰**：前往 intervals.icu → 右上角頭像 → Settings → 捲動至頁面底部 → API → 點擊「Copy API Key」。

### 3. 建立訓練目標

在 Claude Code 中執行：

```
/create-goal
```

依照提示填入個人基本資料、FTP、年度目標與里程碑，指令會自動產生 `goals.md`。此檔案不納入版控，僅存在本地。

### 4. 同步訓練資料

```bash
python fetch.py           # 下載最近 90 天
python fetch.py --all     # 下載全部歷史（從 2020-01-01）
python fetch.py --start 2026-01-01  # 指定起始日期
```

### 5. 使用 Claude Code 指令

在 Claude Code 中執行 `/fitness`、`/plan`、`/review-ride`、`/weekly-review`。

## Claude Code 指令

在 Claude Code 中可直接使用以下斜線指令（需先同步資料）：

| 指令 | 說明 |
|---|---|
| `/create-goal` | 引導建立 `goals.md`（首次使用必做） |
| `/fitness` | 顯示體能快照：CTL、ATL、TSB 趨勢與目標進度 |
| `/plan [週數或月份]` | 規劃課表並建立至 intervals.icu（確認後才寫入） |
| `/review-ride [YYYY-MM]` | 選擇單次騎乘進行詳細 review，含 power curve 與 PR 比對 |
| `/weekly-review [參數]` | 分析整週或整月訓練，含目標進度評估與下週建議 |

`/weekly-review` 參數範例：`week`、`month`、`2026-06`、`2026-W27`

## 專案結構

```
cycling/
├── fetch.py              # intervals.icu 資料同步
├── goals.md              # 訓練目標與里程碑（個人設定）
├── requirements.txt
│
├── coach/
│   ├── review_rules.md         # 單次騎乘評估規則
│   └── weekly_review_rules.md  # 週訓練評估規則
│
├── intervals/
│   ├── client.py         # intervals.icu API 客戶端
│   └── streams.py        # 活動 streams 分析（power curve、疲勞）
│
├── data/                 # 本地資料（由 fetch.py 產生，不納入版控）
│   └── YYYY/MM/
│       ├── YYYY-MM-DD_活動名稱.json
│       └── wellness.json
│
└── .claude/commands/     # Claude Code 斜線指令定義
```

## 資料說明

`fetch.py` 將資料儲存於 `data/` 目錄（不納入版控）：

- **活動檔**：`data/YYYY/MM/YYYY-MM-DD_活動名稱.json`，每次騎乘一個檔案
- **體能檔**：`data/YYYY/MM/wellness.json`，每月一個檔案，包含每日 CTL/ATL/TSB 等

## 依賴

- `requests` — intervals.icu API 呼叫
- `python-dotenv` — 環境變數管理
