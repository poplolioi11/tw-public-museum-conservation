# 查找與引用

先從[館所索引](../catalog/README.md)選館，再看年份／跨年期間與原報作業。每列連到一個JSON，內含原數字、原量詞、分類、限制、官方來源與頁碼。這是可直接讀取的資料索引；互動網頁篩選尚在後續規劃。

例如臺史博2020的[完整修護分項](../catalog/records/NMTH-2020-full-treatment.json)與[原報年度合計](../catalog/records/NMTH-2020-conservation-reported-total.json)是不同層級，不能一起相加。作業名稱「完整修護」也不自動代表原文明載完成。

## 三個查詢欄位

| 欄位 | 用途與界線 |
|---|---|
| action_categories | 查詢原報提及的修護、維護、整飭、檢視、數位等類型；可複選，不將數量拆配到各類 |
| completion_category | 分開明載完成、父項／段落脈絡、截止時點、年度執行、進行中及未明載；原completion_status另保留 |
| subject_scope_category | 原報本館、託管、館外受託或混合待核；不是法律權屬調查 |

所有值與中文標籤見[詞表](../schema/vocabulary.json)。分類規則在`scripts/classify_facets.py`，由本機程式產生並核對，不能直接改一張匯出表而讓各格式分歧。

## 年度、近似及缺值

- 單年資料看data_year；跨年data_year為null，須同時看reporting_period_raw與明示起訖年，不能每年複製同一數字。
- 「近300」「300餘」看quantity_raw，quantity_numeric為null；不使用300代替確數。
- body_reviews是來源查核，未定位合格數量不是零。海生2020原年報缺口與後續決算業務覆讀分開保留；extends_review_id指補充範圍，不能抹去原查核。
- HTML正文以source_locators定位；只有PDF才有頁序，不把HTML雜湊冒充PDF版本。

## 供AI與其他工具引用

固定版本的逐筆入口為：

`https://raw.githubusercontent.com/poplolioi11/tw-public-museum-conservation/v0.4.0/catalog/records/{observation_id}.json`

保留observation_id、資料年或跨年期間、quantity_raw與原單位，再引用其中官方來源及PDF頁碼。main路徑供查當前版，tag路徑供重現固定版。不要把逐筆入口數、分類列數或所有數字相加解釋成全國修復量。

本版CSV／JSONL／SQLite仍提供完整資料。館所索引與逐筆檔由同一主檔產生，避免出現第二套人工維護的數字。


先看[資料樣貌](../catalog/SAMPLE.md)可比較不同計量方式；這些例子不構成可相加的數列。分類規則1.1擴充同型年度表及完成文字映射，保留舊版既有標籤含義。
