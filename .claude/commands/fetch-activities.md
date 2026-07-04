從 intervals.icu 下載訓練資料並儲存為本地 JSON。

## 步驟

### 第一步：詢問同步範圍

列出選項讓使用者選擇：

```
請選擇同步範圍：

  1. 今天
  2. 最近 90 天（預設）
  3. 全部歷史（從 HISTORY_START 開始）
  4. 自訂起始日期（到今天）
  5. 自訂日期區間（指定起訖）

請輸入選項編號：
```

### 第二步：若選 4，詢問起始日期

```
請輸入起始日期（格式 YYYY-MM-DD）：
```

### 第三步：若選 5，依序詢問起訖日期

```
請輸入起始日期（格式 YYYY-MM-DD）：
請輸入結束日期（格式 YYYY-MM-DD）：
```

### 第四步：執行對應指令

依選擇執行（選項 1 的 TODAY 替換為今天的實際日期）：

| 選項 | 指令 |
|---|---|
| 1 | `python3 fetch.py --start TODAY --end TODAY` |
| 2 | `python3 fetch.py` |
| 3 | `python3 fetch.py --all` |
| 4 | `python3 fetch.py --start YYYY-MM-DD` |
| 5 | `python3 fetch.py --start YYYY-MM-DD --end YYYY-MM-DD` |

顯示執行輸出，讓使用者看到下載進度。

### 第五步：完成提示

下載完成後告知使用者資料已更新，可執行以下指令查看：

```
/fitness        — 查看最新體能狀態
/weekly-review  — 分析近期訓練
/review-ride    — review 單次騎乘
```

用繁體中文回覆。
