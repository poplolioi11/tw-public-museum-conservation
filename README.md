# 臺灣公立館保存修護公開資料索引（持續整理）

將官方年報、年度成果與業務報告中的保存修護資料整理成可回查索引，保留原數字、作業詞、單位、期間、完成用語、來源版本與定位。

**v0.16.0｜2026-10-30**。[公開查詢網站](https://poplolioi11.github.io/tw-public-museum-conservation/)及[發行版本](https://github.com/poplolioi11/tw-public-museum-conservation/releases)各依顯示版本與實際讀回結果確認；本文件不代替部署回執。

## 從這裡開始

- **哪館有數字？** 從[館所索引](catalog/README.md)或[互動查詢](https://poplolioi11.github.io/tw-public-museum-conservation/)依館名、資料年及作業找資料。[資料樣貌](catalog/SAMPLE.md)示範原口徑；有數值與另一來源指定段未定位量可同時出現在一個館年。
- **怎麼查一筆？** 在[觀測JSONL](data/observations.jsonl)查固定`observation_id`。先讀原數字、原單位、期間、完成語及對象範圍，再以`source_id`對照[來源表](data/sources.csv)，回官方原頁或HTML段落。詳見[查找與引用](docs/QUERYING.md)。
- **哪些資料不能相加？** 看[關係與證據附表說明](docs/RELATIONS.md)及[關係CSV](data/relation_projection.csv)／[JSONL](data/relation_projection.jsonl)。總分項、重述、平行量詞與重疊未核分開，原註記與角色參照保留。
- **完成語有什麼依據？** 本版[14筆覆核JSON](data/completion_reviews.json)／[CSV](data/completion_reviews.csv)／[JSONL](data/completion_reviews.jsonl)連回原紀錄與原頁。父句完成脈絡不等於每個分項都明載完成。
- **下載其他附表。** [缺量註記CSV](data/absence_annotations.csv)、[搜尋別名CSV](data/normalized_observations.csv)、[館年狀態CSV](data/coverage_cells.csv)、[分組摘要CSV](data/coverage_groups.csv)及[SQLite](data/museum-conservation.sqlite)保留固定識別與證據連結。

## 本版資料與變更

|層級|本版筆數|代表什麼|
|---|---:|---|
|公開紀錄|307|304筆原報觀測、1筆程式推算、2筆脈絡；不是物件合計|
|來源版本|330|294 PDF、36 HTML；取得版本與核讀範圍分開記錄|
|來源查核紀錄，含歷史|608|原606則保留，新增2則歷史索引|
|目前查核／館年格|482／471|同館年多來源全部保留；含2015、2016兩個歷史格|
|原關係與證據投影|86|38種原名稱對應15類、4種註記層級；不新增關係認證|
|完成語覆核|14|重看9份既存PDF的10個指定原頁；沒有新增數值|
|指定段未定位量的分類|275則／269格|274則說明支持、1則資訊不足；不是未公開機構數|

本版依序補高美館2015、2016兩格索引，連回6筆既有原報觀測；整理86則關係附表；再覆核14筆依上下文判讀完成的紀錄。原307列、330來源、606則歷史查核及86則原關係完整保留。歷史索引補登沒有新增原件閱讀，也沒有把既有數值算成館方新公布。本版另修正沿用舊值的摘要計數；原觀測未新增或改動。

14筆覆核均支持原有的父項或段落完成脈絡，仍保留`completion_from_context`。這是14筆既有觀測的完成語證據，不是14件新增完成物件；不升為分項明載完成，不推逐件名冊、權屬或跨年去重。文字可讀頁與實看圖頁分列，掃描頁只據原圖判讀；不稱全頁所有欄位、全冊或全年已核。

## 分母與期間先分清

原71組織×2020–2025的歷史索引仍為426格。含所有年份的已查核集合為471格，與原索引的全聯集為543格；其中2020–2025已查核子集仍為469格、同期間聯集仍為541格。2015、2016兩格歷史子集另列，不能混進六年分母。

[覆蓋率JSON](metadata/coverage.json)列出五個有重疊關係的集合／年份子集，不能相加。全聯集中72格無館年查核索引，與已查找而未定位來源不同。同格的全部目前狀態與混合證據保留，工作批次、權管及島群只是索引分組，不是全國估計、官方館類或館所績效。見[分母說明](docs/COVERAGE.md)及[研究筆記草稿](docs/RESEARCH_NOTE_DRAFT.md)。

## 原口徑與附表的界線

原作業分類、完成詞與單位不改寫：91個作業分類原值不等於91種獨立工序；34個完成詞不壓成同一完成定義；25個單位欄值含`null`與「未明列」，不能稱25種量詞。搜尋別名見[作業](docs/METRIC_CLASS_MAP.md)、[完成詞](docs/COMPLETION_STATUS_MAP.md)及[單位](docs/UNIT_MAP.md)對照。

關係附表逐列保留原字典、順序及角色。原`relationship_verified`有3列true、30列false、53列未列；這些是整理者原註記的旗標，沒有因本版分類而重新核實官方關係。false不是已證明沒有關係，未列也不代表可加總。來源續頁、構成脈絡與量詞提醒，不自動當物件包含關係。

存量、新入藏、初製、展示、課程、館舍維護與外部服務不直接代填既有館藏修護量。總子項、不同報告、母子館、跨年與可能重疊批次，沒有包含與去重證據便不相加。未知不補零，近似量及雙單位不猜確數，件、組件、案、冊等不換算。

## 完整資料、來源與引用

- [事實JSON](data/facts.json)、[觀測CSV](data/observations.csv)、[欄位字典](docs/DATA_DICTIONARY.md)、[來源與原件SHA](data/sources.csv)、[目前查核識別](metadata/read_coverage.json)。
- [關係規則](metadata/relation_projection_rules.json)／[結構](schema/relation_projection.schema.json)、[完成語覆核規則](metadata/completion_review_rules.json)／[結構](schema/completion_review.schema.json)。
- [既有盤點](metadata/inventory.json)、[附表建置資訊](metadata/enrichment_build.json)、[網站manifest](site/manifest.json)、[機讀導航](llms.txt)、[版本紀錄](CHANGELOG.md)與[更新計畫](docs/UPDATE_PLAN.md)。

逐筆固定紀錄對有本版完成語覆核者提供`completion_review_reference`，可連至獨立覆核表；原觀測完成詞不被覆核表自動取代。網站有界資料頁用關係分類與完成語表協助查讀，實際部署仍以公開manifest和資料讀回核對。

引用請保留專案名稱、實際發行版本、日期、公開投影SHA，以及逐筆官方來源與頁碼／段落。固定版使用v0.16.0標籤；網站先核對manifest。資料由Codex協作整理、本機Python實算，AI參與及閱讀層級見[AI_USAGE](AI_USAGE.md)，不稱人類逐格雙校、專家或館方認證。

公開只含必要事實與定位；官方PDF、完整HTML、整頁文字及圖片不重發布，私人補充紀錄不進公開版。原創程式及文件採MIT，第三方權利仍依來源，見[公開範圍](docs/PUBLICATION.md)與[授權](LICENSE.md)。[研究筆記](docs/RESEARCH_NOTE_DRAFT.md)保持repo草稿，未宣稱投稿、DOI或正式審查。

## 整理者

曲宸宇（Chu, Chen-Yu；GitHub：[poplolioi11](https://github.com/poplolioi11)），[ORCID 0009-0003-9738-6914](https://orcid.org/0009-0003-9738-6914)。姓名與帳號為同一位整理者，角色為資料整理、選題與AI協作。
