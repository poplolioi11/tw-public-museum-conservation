# 臺灣公立館保存修護公開資料索引（持續整理）

將官方年報、年度成果與業務報告中的保存修護資料整理成可回查索引，保留原數字、作業詞、單位、期間、完成用語、來源版本與定位。

**v0.15.0｜2026-10-30**。[公開查詢網站](https://poplolioi11.github.io/tw-public-museum-conservation/)及[已發行版本](https://github.com/poplolioi11/tw-public-museum-conservation/releases)的狀態，以各自顯示版本與實際讀回結果為準。

## 從這裡開始

- **哪館有數字？** 先開[館所索引](catalog/README.md)或[互動查詢](https://poplolioi11.github.io/tw-public-museum-conservation/)，依館名、資料年及作業查找。[資料樣貌](catalog/SAMPLE.md)提供原口徑範例。有數值查核與另一來源的指定段未定位量，可以同時出現在同一館年。
- **怎麼查一筆？** 在[觀測JSONL](data/observations.jsonl)搜尋固定`observation_id`，例如`ntm-2022-puppet-project-completed`。先讀`quantity_raw`、`unit_as_reported`、期間、完成狀態及範圍，再以`source_id`對照[來源表](data/sources.csv)，回官方原件的PDF頁序／印頁或HTML段落。逐筆查法見[查詢說明](docs/QUERYING.md)。
- **下載新增附表。** [指定段缺量註記CSV](data/absence_annotations.csv)／[JSONL](data/absence_annotations.jsonl)、[搜尋正規化CSV](data/normalized_observations.csv)／[JSONL](data/normalized_observations.jsonl)、[館年狀態CSV](data/coverage_cells.csv)／[JSONL](data/coverage_cells.jsonl)、[分組摘要CSV](data/coverage_groups.csv)／[JSONL](data/coverage_groups.jsonl)。附表以固定ID連回原紀錄，沒有改寫原值或增加可相加性。

## 本版資料與變更

| 層級 | 本版筆數 | 代表什麼 |
|---|---:|---|
| 公開紀錄 | 307 | 304筆原報觀測、1筆程式推算、2筆脈絡；不是物件合計 |
| 官方原件版本 | 330 | 294 PDF、36 HTML；取得版本與核讀範圍分開記錄 |
| 來源查核紀錄，含歷史 | 606 | 原582則保留；新增8則索引、5則缺年首查、11則延伸補讀 |
| 目前查核葉節點／館年格 | 480／469 | 同館同年可能有多則目前查核，全部保留 |
| 指定段未定位量的分類 | 275則／269格 | 274則有註記支持、1則資訊不足；不是未公開機構數 |

本版補回8格查核索引，連回17筆既有原報觀測，這部分沒有重新讀原件；另首查5格既有館所缺年，其中4格取得適用分項、1格未定位適用館級來源。新增8筆原報列及2個來源版次；原299列、328來源、582則查核及83則關係的完整內容保留。案、件、項、冊與組件不換算、不相加；5筆跨年紀錄仍只存一次。[本輪成果與限定](docs/EXISTING_FOLLOWUP.md)列明每一項的證據範圍。

原11則資訊不足註記經指定業務子段補讀後，10則可以說明缺量原因、1則仍保留資訊不足。新增延伸查核均記本版日期，不回填為舊版已讀。275則目前N查核仍分布269格；其餘註記沿用既有公開說明。引文、內容標籤及未採原因可複選，不解釋機構未做或未公開的動機，不當互斥比例。[缺量註記方法](docs/ABSENCE.md)與[分類詞表](metadata/absence_vocabulary.json)保留證據及界線。

涵蓋摘要分開提供原歷史基線426格、本版有界查核469格，以及兩者聯集541格。聯集中72格為`not_assessed`（無館年查核索引），與本輪查找未定位來源不同。同格的所有目前狀態均保留；不挑最高狀態取代混合證據。工作批次、權管與島群的分組只描述索引集合，不是全國估計、官方館類或館所績效。見[分母及涵蓋方法](docs/COVERAGE.md)、[涵蓋JSON](metadata/coverage.json)及[研究筆記草稿](docs/RESEARCH_NOTE_DRAFT.md)。

## 搜尋分類與原口徑

新增正規化附表提供搜尋用別名及作業多標籤，原`metric_class`、`completion_status`、`unit_as_reported`及觀測內容不變。91個作業分類原值不等於91種獨立作業；34個完成用語原值不壓成同一完成定義；25個單位原值包含`null`與「未明列」，不能稱為25種量詞。

- [作業分類對照](docs/METRIC_CLASS_MAP.md)：複合作業保留多標籤，不拆配數量或改稱純修復。
- [完成用語對照](docs/COMPLETION_STATUS_MAP.md)：年度執行、完成、進行中與目標分開，未明載完成不等於未完成。
- [單位對照](docs/UNIT_MAP.md)：字面別名只改善搜尋；件、組、組件、案、冊等不互換，同為件也須核對對象。

典藏存量、新入藏、初製、展示、課程、館舍維護及外部服務不直接代填既有館藏修護量。總項與子項、不同報告、母子館、跨年或可能重疊批次，沒有包含與去重證據便不相加。未知、`null`、原刊留白與未定位不補零；近似量及雙單位不猜確數。

## 完整資料、來源與版本

- [事實主檔JSON](data/facts.json)、[觀測CSV](data/observations.csv)、[SQLite](data/museum-conservation.sqlite)、[欄位字典](docs/DATA_DICTIONARY.md)及[觀測結構](schema/observation.schema.json)。
- [來源清單與原件雜湊](data/sources.csv)、[既有來源盤點](metadata/inventory.json)、[正文分項範圍](metadata/read_coverage.json)。原名錄仍保留索引轉錄層級，不因本版附表而升格為原PDF已核。
- [附表建置資訊](metadata/enrichment_build.json)、[正規化規則](metadata/normalization_rules.json)、[網站manifest](site/manifest.json)與[版本建置資訊](metadata/build.json)。官方原件SHA、資料投影SHA與網站建置SHA分開核對。
- [機讀導航llms.txt](https://poplolioi11.github.io/tw-public-museum-conservation/llms.txt)、[更新計畫](docs/UPDATE_PLAN.md)、[版本紀錄](CHANGELOG.md)。機讀導航不是事實主檔或原始證據。

網站的完整篩選CSV涵蓋當下條件的全部結果；完整資料CSV則是整版紀錄。下載列數都不是修復物件總量。原報資料年、出版年及跨年期間分開；HTML的PDF頁碼為`null`，以段落定位回查，渲染PDF不冒充官方原件PDF。

## 查核、權利與引用

本索引可用於尋找官方來源、檢查口徑及辨識缺口。公立、公設民營、設置機關、權管與營運關係分開，行政或場址關係不等於每件藏品所有權；不主張涵蓋全國全部館所。

公開內容為必要事實及短定位，官方PDF、完整HTML、整頁文字與圖片不重新發布。原創程式與文件採MIT，第三方來源權利仍依原來源處理，見[授權](LICENSE.md)、[公開範圍](docs/PUBLICATION.md)及[既有成果與查核界線](docs/PRIOR_ART.md)。

資料由Codex協作整理與本機Python實算驗證，AI參與及核對層級見[AI使用說明](AI_USAGE.md)。不宣稱人類逐格雙校、專家審定、館方認證或跨館可比性認證。原件版本、資料附件及網站各自讀回，不能互相代替。

引用請保留專案名稱、實際發行版本、日期、公開投影SHA，以及觀測對應的官方來源與頁碼／段落。固定版本引用使用v0.15.0標籤與發行頁；網站則先核對manifest的版本與雜湊。本儲存庫的[研究筆記](docs/RESEARCH_NOTE_DRAFT.md)是方法草稿，沒有宣稱投稿、DOI或正式審查。

## 整理者

曲宸宇（Chu, Chen-Yu；GitHub：[poplolioi11](https://github.com/poplolioi11)），[ORCID 0009-0003-9738-6914](https://orcid.org/0009-0003-9738-6914)。本名、中英文姓名與帳號指同一位整理者；角色為資料整理、選題與AI協作。
