首次安裝引導：依序完成憑證設定、建立訓練目標、同步初始資料。

## 步驟

### 第一步：檢查 .env

確認 `.env` 是否存在且包含必要的環境變數（`INTERVALS_ATHLETE_ID`、`INTERVALS_API_KEY`）。

若不存在或缺少欄位，引導使用者取得憑證：

- **Athlete ID**：登入 intervals.icu，網址列顯示 `intervals.icu/athlete/i/XXXXXXXX`，取 `XXXXXXXX` 部分
- **API 金鑰**：intervals.icu → 右上角頭像 → Settings → 頁面底部 API → Copy API Key

詢問使用者輸入兩個值後，將 `.env.example` 複製為 `.env` 並寫入對應欄位。

### 第二步：建立 goals.md

確認 `goals.md` 是否存在。若已存在，詢問是否跳過或重新建立。

若不存在，逐步收集以下資訊（每次問 1–2 個問題，等回答後再繼續）：

**個人基本資料**
- 姓名、年齡、身高、體重（kg）
- 每週預期訓練時數

**體能現況**
- 目前 FTP（若不確定，說明可從 intervals.icu Power Curve 或 20 分鐘功率測驗 × 0.95 估算）
- 目前 CTL（可從 intervals.icu Fitness 頁面查看，若不知道填「不確定」）
- CP5 是否已測（可選）

**年度目標**
- 是否有目標賽事（名稱與日期）？若無，以體能建設為主
- FTP 目標（年底）
- CP5 目標（可選）

**里程碑**
- 是否有中間測驗節點或特殊時間段（出國、休賽期、比賽）？列出 2–4 個

整理後展示 `goals.md` 預覽，確認後寫入，格式如下：

```
# 訓練目標
<!--
  此檔案由 /rider-setup 產生，之後可透過 /create-goal 更新。
  以下欄位會被指令讀取，請確認填寫正確：
    - 體重（kg）         → /review-ride 計算 W/kg 時使用
    - 每週預期訓練時數   → /weekly-review 評估訓練量時使用
    - FTP 目前值（體能指標表格第一欄）→ /review-ride、/fitness 使用
    - 訓練負荷參考       → /weekly-review 評估 CTL 合理範圍時使用
-->

## 個人基本資料

- 姓名：XXX
- 年齡：XX 歲
- 身高：XXX cm
- 體重：XX kg          ← /review-ride 讀取此值計算 W/kg
- 每週預期訓練時數：XX–XX 小時   ← /weekly-review 評估訓練量基準

## 主要目標

- 賽事：XXX（或「無，以體能建設為主」）
- 截止日期：YYYY-MM-DD
- 期望表現：
  - FTP 達到 X.X W/kg（目標 XXX W）
  - CP5 達到 X.X W/kg（目標 XXX W）（若有）

## 體能指標

| 指標 | 目前 | 目標（年底） |
|---|---|---|
| FTP | XXX W（X.XX W/kg） | XXX W（X.X W/kg） |   ← 目前 FTP 由 /review-ride、/fitness 讀取
| CP5 | 未測（估計 ~XXX W） | XXX W（X.X W/kg） |
| CTL | XX（YYYY-MM-DD） | 無硬性目標 |

## 訓練負荷參考

- 每週 XX–XX 小時對應穩態 CTL 約 XX–XX   ← /weekly-review 評估 CTL 合理區間時參考
- 無需刻意衝高 CTL，優先提升訓練品質與強度

## 里程碑

- YYYY-MM：（里程碑描述）
- ...

## 備註

- （特殊事項，例如出國、受傷、賽季安排）
```

### 第三步：同步初始資料

詢問使用者想下載多久的歷史資料：
- 最近 90 天（預設，快速）
- 全部歷史（較慢）
- 自訂起始日期

依選擇執行對應指令：

```bash
python fetch.py
python fetch.py --all
python fetch.py --start YYYY-MM-DD
```

顯示下載進度，完成後確認資料已就緒。

### 第四步：完成提示

告知使用者 setup 已完成，可使用以下指令：

```
/fitness        — 查看目前體能狀態
/weekly-review  — 分析近期訓練
/review-ride    — review 單次騎乘
/plan           — 規劃並建立課表
```

用繁體中文回覆。
