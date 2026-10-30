# 臺灣公立館保存修護公開資料索引（持續整理）

將官方年報、年度成果與業務報告中的保存修護資料整理成可回查索引，保留原數字、作業詞、單位、期間、完成用語、來源版本與定位。私立館的公開來源試辦另列。

**v0.17.0｜2026-10-30**。[查詢網站](https://poplolioi11.github.io/tw-public-museum-conservation/)與[固定發行版本](https://github.com/poplolioi11/tw-public-museum-conservation/releases/tag/v0.17.0)各依實際版本與讀回確認。

## 從這裡開始

- **依館所找數字：** [館所索引](catalog/README.md)、[互動查詢](https://poplolioi11.github.io/tw-public-museum-conservation/)及[資料樣貌](catalog/SAMPLE.md)。
- **回查一筆：** 依[觀測JSONL](data/observations.jsonl)的observation_id查原值，再以source_id連[來源表](data/sources.csv)與官方原頁。見[查找與引用](docs/QUERYING.md)。
- **累計、計畫與跨年另看：** [公立脈絡頁](https://poplolioi11.github.io/tw-public-museum-conservation/context.html)／[6則JSON](data/public_context_notes.json)，不代填單年已施作量。
- **私立館另列：** [私立試辦頁](https://poplolioi11.github.io/tw-public-museum-conservation/private-art.html)／[獨立JSON](data/private_art_pilot.json)／[CSV](data/private_art_observations.csv)。這是館方公開來源，不是使用者私人紀錄；不混入公立分母。
- **判讀界線：** [關係附表](docs/RELATIONS.md)、[完成語覆核](docs/COMPLETION_REVIEW.md)、[缺量註記](docs/ABSENCE.md)、[覆蓋率分母](docs/COVERAGE.md)及[SQLite](data/museum-conservation.sqlite)。

## 本版整理範圍

|資料層|本版筆數|意義|
|---|---:|---|
|公立公開紀錄|311|308原報觀測、1推算、2既有脈絡；不是物件合計|
|公立來源版本|345|305 PDF、40 HTML；原件取得與正文核讀分層|
|公立查核含歷史／目前葉節點|626／500|同館年多來源保留，不取最高狀態|
|公立已查館年格|489|含期間外2015、2016兩格|
|指定段未定位量註記|282則／276格|281則說明支持、1則資訊不足；不是未公開機構數|
|原關係／原完成語覆核|86／14|原字典與判讀保持，沒有重做全批原件|
|私立試辦|1館、4列、6則查核|6個來源版本；完全另列|

本版依序核桃園與黃金的指定正文、師大校藏與館所角色，再做朱銘私立館試辦。桃園新增2021紙質4件、2023修護12件、2025水墨9件；黃金新增2020圖書文獻1件。4與9有直接完成語，12與1保留年度施作但未明載完成。各數值只代表原報指定口徑，不相加為館級年總量。桃園2024年報入口已定位，適用正文仍待核；沒有借其他年份替代。

師大未新增年度數值：未載起訖累計、長期平均及2020–2022跨年專案另存脈絡，美術館、美術系校藏與執行中心角色分開。計畫數16、優先對象6與完成年未確立的個案亦不列年度施作量。詳見[本階段來源與範圍](docs/EXPANSION_V017.md)。

原307列、330來源、608則查核及86則關係完整保留。本版新增4列、15個公立來源版本、18則公立查核、6則獨立脈絡；舊14筆完成語覆核沒有升格為分項明載完成。私立數字保留原報館內／借展或混合作業界線，不變成自藏、純修復或唯一物件總數。

## 分母與期間

原71組織×2020–2025歷史索引仍426格。全期間已查489格、與原索引聯集555格；2020–2025已查487格、同期間聯集553格。兩個歷史格另列，五個集合／年份子集重疊，不能相加。全聯集66格無館年查核索引，與已查找而未定位來源不同。師大另列公立擴充候選，不改原71組織；朱銘不進任何公立集合。

覆蓋率只描述本版有界來源查核，不是全國資料公開率、作業量成長或館所績效。工作批次不是官方館類，權管及島群只映射原證據，未知保留unknown。見[覆蓋率JSON](metadata/coverage.json)與[研究筆記草稿](docs/RESEARCH_NOTE_DRAFT.md)。

## 原值與引用

91個metric_class為歷史分類值；34個完成詞保留原義；25個單位欄相異值含null及「未明列」，不能稱25種量詞。[作業](docs/METRIC_CLASS_MAP.md)、[完成詞](docs/COMPLETION_STATUS_MAP.md)及[單位](docs/UNIT_MAP.md)別名只供搜尋，不換算、不拆年、不授予加總資格。未知不補零，分項、借展、跨年及可能重疊批次沒有證據便不相加。

引用請保留固定v0.17.0、公開投影SHA、逐筆官方來源及頁碼／段落。原件SHA、匯出manifest與網站manifest各自核對。[AI_USAGE](AI_USAGE.md)說明實際AI與本機Python範圍；不稱人類二校、館方或專家認證。研究筆記維持repo草稿，未投稿、取DOI或寄送。

公開只含必要事實與定位；PDF、完整HTML、整頁圖文及私人補充紀錄不重發布。原創程式與文件採MIT，第三方權利依來源。見[公開範圍](docs/PUBLICATION.md)、[授權](LICENSE.md)、[版本紀錄](CHANGELOG.md)及[更新計畫](docs/UPDATE_PLAN.md)。

整理者：曲宸宇（Chu, Chen-Yu；GitHub：[poplolioi11](https://github.com/poplolioi11)），[ORCID](https://orcid.org/0009-0003-9738-6914)。姓名與帳號為同一位整理者。
