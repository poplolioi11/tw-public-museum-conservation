# 臺灣公立館保存修護公開資料索引（持續整理）

將官方年報、年度成果與業務報告中的保存修護資料整理成可回查索引，保留原數字、作業詞、單位、期間、完成用語、來源版本與定位。私立館的公開來源試辦另列。

**v0.18.0｜2026-11-01**。[查詢網站](https://poplolioi11.github.io/tw-public-museum-conservation/)與[固定發行版本](https://github.com/poplolioi11/tw-public-museum-conservation/releases)各依實際版本與讀回結果引用。

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
|公立來源版本|351|311 PDF、40 HTML；原件取得與正文核讀分層|
|公立查核含歷史／目前葉節點|636／501|同館年多來源保留，不取最高狀態|
|公立已查館年格|489|含期間外2015、2016兩格|
|指定段未定位量註記|283則／277格|282則說明支持、1則資訊不足；不是未公開機構數|
|原關係／原完成語覆核|86／14|原字典與判讀保持，沒有重做全批原件|
|私立試辦|1館、4列、6則查核|6個來源版本；完全另列|

本版續補既有館所來源，新增6個公立來源版本與10則查核，沒有新增數值觀測。311列原紀錄逐欄保持；6則公立脈絡、86則關係、14筆完成語覆核及私立試辦內容保持。前版四館擴充與私立試辦詳節保留於[EXPANSION_V017](docs/EXPANSION_V017.md)及[版本紀錄](CHANGELOG.md)。

桃園2024新增113年9月工作報告「典藏品年度修復計畫」的限定N，只表示該子段未明載適用完成數量或年月。作品名稱不自行計數，紀錄片發表日不當修復完成日。2024年報附件網址另已定位，原件及適用正文仍待取得，獨立P持續保留。

新竹新增5份完整官方PDF與8則既有館年P延伸。已核的指定段落仍是館群／父機構合列、展覽服務或非動產內容，未確立可獨立歸館的保存處理量；原件取得與部分頁段已看不表示館級保存全文已讀。跨年施政報告保留原期段，不借作2025全年。師大與政大續查本輪沒有可採增量。詳見[本版來源續補](docs/SOURCE_FOLLOWUP_V018.md)。

## 分母與期間

原71組織×2020–2025歷史索引仍426格。全期間已查489格、與原索引聯集555格；2020–2025已查487格、同期間聯集553格。兩個歷史格另列，五個集合／年份子集重疊，不能相加。全聯集66格無館年查核索引，與已查找而未定位來源不同。師大另列公立擴充候選，不改原71組織；朱銘不進任何公立集合。

覆蓋率只描述本版有界來源查核，不是全國資料公開率、作業量成長或館所績效。工作批次不是官方館類，權管及島群只映射原證據，未知保留unknown。見[覆蓋率JSON](metadata/coverage.json)與[研究筆記草稿](docs/RESEARCH_NOTE_DRAFT.md)。

## 原值與引用

91個metric_class為歷史分類值；34個完成詞保留原義；25個單位欄相異值含null及「未明列」，不能稱25種量詞。[作業](docs/METRIC_CLASS_MAP.md)、[完成詞](docs/COMPLETION_STATUS_MAP.md)及[單位](docs/UNIT_MAP.md)別名只供搜尋，不換算、不拆年、不授予加總資格。未知不補零，分項、借展、跨年及可能重疊批次沒有證據便不相加。

引用請保留固定v0.18.0、公開投影SHA、逐筆官方來源及頁碼／段落。原件SHA、匯出manifest與網站manifest各自核對。[AI_USAGE](AI_USAGE.md)說明實際AI與本機Python範圍；不稱人類二校、館方或專家認證。研究筆記維持repo草稿，未投稿、取DOI或寄送。

公開只含必要事實與定位；PDF、完整HTML、整頁圖文及私人補充紀錄不重發布。原創程式與文件採MIT，第三方權利依來源。見[公開範圍](docs/PUBLICATION.md)、[授權](LICENSE.md)、[版本紀錄](CHANGELOG.md)及[更新計畫](docs/UPDATE_PLAN.md)。

整理者：曲宸宇（Chu, Chen-Yu；GitHub：[poplolioi11](https://github.com/poplolioi11)），[ORCID](https://orcid.org/0009-0003-9738-6914)。姓名與帳號為同一位整理者。
