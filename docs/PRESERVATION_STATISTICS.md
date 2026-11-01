# 官方環境作業統計附表

v0.20.0。覆核國立故宮博物院6份既存官方PDF、17則候選所在的7個指定頁面，另回查同報業務概況1頁。採用14則環境作業原口徑事實；2則暫緩、1則關聯既有主表紀錄而不新增。這是限定來源的附表，不是全國調查、修復件數、保存品質或達標率。

[網站表格](https://poplolioi11.github.io/tw-public-museum-conservation/preservation.html)／[JSON](../data/preservation_statistics.json)／[CSV](../data/preservation_statistics.csv)／[JSONL](../data/preservation_statistics.jsonl)／[來源與輸出範圍](../metadata/preservation_statistics.json)。CSV與JSONL另接官方標題、URL及原件SHA，JSON容器以source_id連主檔來源表。附表沒有併入主表、SQLite觀測或公立涵蓋率。

## 原列事實與期間

|報告年|原作業|原數字與單位|期間依據|原頁|
|---|---|---|---|---|
|2020|文物陳列櫃內微環境調控|50 櫃次/箱次|原列／表題有年度；未補月日|[PDF36／印68](https://www.npm.gov.tw/NewFileAtt.ashx?lang=1&id=10023582#page=36)|
|2020|文物照明量測|825 件次|原列／表題有年度；未補月日|[PDF36／印68](https://www.npm.gov.tw/NewFileAtt.ashx?lang=1&id=10023582#page=36)|
|2021|文物陳列櫃內微環境調控|61 櫃次 / 箱次|僅年報脈絡，觀測年未知|[PDF54／印106](https://www.npm.gov.tw/NewFileAtt.ashx?lang=1&id=10054624#page=54)|
|2022|文物展存環境溫溼度監測|231 室 / 櫃次|原列／表題有年度；未補月日|[PDF121／印121](https://www.npm.gov.tw/NewFileAtt.ashx?lang=1&id=10055548#page=121)|
|2022|文物陳列櫃內微環境調控|110 櫃 / 箱次|原列／表題有年度；未補月日|[PDF121／印121](https://www.npm.gov.tw/NewFileAtt.ashx?lang=1&id=10055548#page=121)|
|2022|文物照明量測|127 室 / 展次|原列／表題有年度；未補月日|[PDF121／印121](https://www.npm.gov.tw/NewFileAtt.ashx?lang=1&id=10055548#page=121)|
|2023|文物展存環境溫溼度監測|62 室 / 櫃次|原列／表題有年度；未補月日|[PDF159／印157](https://www.npm.gov.tw/NewFileAtt.ashx?lang=1&id=10056492#page=159)|
|2023|文物陳列櫃內微環境調控|65 櫃 / 箱次|原列／表題有年度；未補月日|[PDF159／印157](https://www.npm.gov.tw/NewFileAtt.ashx?lang=1&id=10056492#page=159)|
|2023|文物照明量測|658 室 / 展次 / 量測點|原列／表題有年度；未補月日|[PDF159／印157](https://www.npm.gov.tw/NewFileAtt.ashx?lang=1&id=10056492#page=159)|
|2024|文物展存環境溫溼度監測|37 室 / 櫃次|原列／表題有年度；未補月日|[PDF143／印141](https://www.npm.gov.tw/NewFileAtt.ashx?lang=1&id=10058806#page=143)|
|2024|文物陳列櫃內微環境調控|63 櫃 / 箱次|原列／表題有年度；未補月日|[PDF143／印141](https://www.npm.gov.tw/NewFileAtt.ashx?lang=1&id=10058806#page=143)|
|2024|文物照明量測|190 室 / 展次 / 量測點|原列／表題有年度；未補月日|[PDF143／印141](https://www.npm.gov.tw/NewFileAtt.ashx?lang=1&id=10058806#page=143)|
|2025|溫濕度監測協調、系統維護及微環境調控|2,029 件次|截至2025年底，起算點未知|[PDF35／印32](https://www.npm.gov.tw/NewFileAtt.ashx?lang=1&id=10059091#page=35)|
|2025|展存環境用材釋酸性檢測|324 件次|截至2025年底，起算點未知|[PDF35／印32](https://www.npm.gov.tw/NewFileAtt.ashx?lang=1&id=10059091#page=35)|

2021微環境一列只有年報頁尾及業務統計脈絡，`report_year=2021`，但`period_year/start/end`保持null。2025兩列只有「截至114年底止」，只記截止2025-12-31，`period_year/start`保持null；不稱年度新增或已證明跨年累計。其餘11列有原列或表題年度，未補推精確月日。

原單位包含櫃次／箱次、櫃／箱次、室／展次／量測點等，保留字序及原詞，不拆項、不換算、不作變化率。2025溫濕度監測協調、系統維護與微環境調控為合列，不分配成三個數值。這些作業計數不代表不重複空間、櫃箱或文物，也不能證明作業難度、投入工時、修復完成或環境品質。

## 未新增的三項

- 2020年報環境監測列寫「建置完成後」，未能限定觀測起訖；本版暫緩，不借報告年改成單年量。
- 2021年報照明列原印「次室 / 展次」，未見釋義；本版暫緩，不自行判定錯字或改成「室 / 展次」。
- 2025單位決算PDF36／印33的狀況檢視，與已收`NPM-2025-finalaccounts-inspection`（PDF8／印5）同為3,109，但正文原寫「檢視」「筆」、業務概況寫「檢示」「件」，期間措辭也不同。只記來源關聯，不重複新增，不互改原詞、原單位或推定不重複物件數。

## 可重跑與公開邊界

`data/preservation_statistics.json`為獨立白名單輸入；`scripts/preservation_statistics.py`產生CSV、JSONL與來源清單，並接入一般匯出流程。驗證原值／數值一致、唯一來源格、官方PDF來源與頁界、期間未知不推年度、嚴格欄位與不可加總旗標。`selfcheck.py`逐格還原CSV／JSONL型別，另在暫存副本驗證錯誤輸入不更動既有匯出。

原311列只在高美館兩筆補來源列鍵，其數字、單位、作業、完成語、期間與範圍保持。主表311列、來源351版、歷史查核636則、已查2020–2025共487格及有數值104格均不因附表改變。分階段研究比例仍固定引用v0.18.0。

公開只保留官方客觀作業事實、必要短定位及來源版本。經費、採購、廠商、人名、詳細庫位／防護配置、私人台帳與逐筆控制鍵不進附表；原件全文及頁圖不重發布。實際來源讀核為AI輔助，人工抽樣仍未開始，不稱人工雙校或機關認證。
