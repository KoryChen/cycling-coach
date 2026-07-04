# AI 自行車教練

以 Claude AI 為核心的個人自行車訓練助手，整合 [intervals.icu](https://intervals.icu) API，支援訓練分析、課表規劃與騎乘 review。

## 功能

- **體能快照**：即時顯示 CTL、ATL、TSB 趨勢，對照目標進度
- **單次騎乘 Review**：分析 power curve、功率區間、疲勞分析，並與 all-time PR 及年度最佳比對
- **週訓練分析**：彙整週期總覽、強度分佈、目標進度評估與下週建議
- **課表規劃**：依當前體能與目標自動排課，確認後直接寫入 intervals.icu 行事曆
- **資料同步**：從 intervals.icu 下載歷史活動與體能數據，儲存為本地 JSON

## 前置需求

- Python 3.9+
- [Claude Code](https://claude.ai/code)
- intervals.icu 帳號

## 快速開始

### 1. Clone 專案

```bash
git clone https://github.com/KoryChen/cycling-coach.git
cd cycling-coach
```

### 2. 安裝依賴

```bash
pip install -r requirements.txt
```

### 3. 執行初始設定

在 Claude Code 中執行：

```
/rider-setup
```

指令會引導你完成：
- 憑證設定（自動建立 `.env`，填入 Athlete ID 與 API 金鑰）
- 建立個人訓練目標（`goals.md`）
- 同步初始訓練資料

完成後即可開始使用所有指令。

## 資料更新

`/rider-setup` 只執行一次初始同步。之後定期執行以保持資料最新：

在 Claude Code 中執行：
```
/fetch-activities
```

或直接在 terminal 執行：
```bash
python fetch.py        # 同步最近 90 天
python fetch.py --all  # 重新同步全部歷史
```

> `--all` 預設從 `fetch.py` 頂部的 `HISTORY_START` 日期開始，可依自己開始使用 intervals.icu 的年份調整。

## Claude Code 指令

在 Claude Code 中可直接使用以下斜線指令（需先同步資料）：

| 指令 | 說明 |
|---|---|
| `/rider-setup` | 首次安裝引導：憑證設定、建立目標、同步資料 |
| `/create-goal` | 更新 `goals.md` 中的目標、里程碑或個人資料 |
| `/fetch-activities` | 從 intervals.icu 同步訓練資料（互動式選擇範圍） |
| `/fitness` | 顯示體能快照：CTL、ATL、TSB 趨勢與目標進度 |
| `/plan [週數或月份]` | 規劃課表並建立至 intervals.icu（確認後才寫入） |
| `/review-ride [YYYY-MM]` | 選擇單次騎乘進行詳細 review，含 power curve 與 PR 比對 |
| `/weekly-review [參數]` | 分析整週或整月訓練，含目標進度評估與下週建議 |

`/weekly-review` 參數範例：`week`、`month`、`2026-06`、`2026-W27`

## 專案結構

```
cycling/
├── fetch.py              # intervals.icu 資料同步
├── requirements.txt
├── .env.example          # 環境變數範本（複製為 .env 並填入憑證）
│
├── coach/
│   ├── review_rules.md         # 單次騎乘評估規則
│   └── weekly_review_rules.md  # 週訓練評估規則
│
├── intervals/
│   ├── client.py         # intervals.icu API 客戶端
│   └── streams.py        # 活動 streams 分析（power curve、疲勞）
│
├── .claude/commands/        # Claude Code 斜線指令定義
│   ├── rider-setup.md       # 首次安裝引導
│   ├── create-goal.md       # 更新訓練目標
│   ├── fetch-activities.md  # 同步訓練資料
│   ├── fitness.md           # 體能狀態快照
│   ├── plan.md              # 課表規劃
│   ├── review-ride.md       # 單次騎乘 review
│   └── weekly-review.md     # 週訓練分析
│
├── goals.md              # 訓練目標（由 /rider-setup 產生，不納入版控）
└── data/                 # 訓練資料（由 fetch.py 產生，不納入版控）
    └── YYYY/MM/
        ├── YYYY-MM-DD_活動名稱.json
        └── wellness.json
```

## 依賴

- `requests` — intervals.icu API 呼叫
- `python-dotenv` — 環境變數管理
