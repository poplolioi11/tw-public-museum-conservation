# 查找與引用

先從[館所索引](../catalog/README.md)選館，再看資料年／跨年期間、原報作業、單位、完成狀態與對象範圍。每筆可回到固定JSON及官方來源。[互動查詢入口](https://poplolioi11.github.io/tw-public-museum-conservation/)的版本由資料manifest辨識，部署與發行結果以公開網址讀回紀錄核對。

## 網頁、CSV與固定JSON

本版網站提供館所、年度、作業、單位、完成狀態等篩選。CSV匯出包含當下篩選條件的全部結果，不限畫面分頁；[完整CSV](../data/observations.csv)則提供整版資料。匯出列數與搜尋結果數都是紀錄數，不是唯一藏品數或修復完成合計。

每列保留固定JSON入口。網站使用`records/{observation_id}.json`；儲存庫中的[固定紀錄目錄](../catalog/README.md)保留`catalog/records/{observation_id}.json`。不可變版本引用可使用：

`https://raw.githubusercontent.com/poplolioi11/tw-public-museum-conservation/v0.15.0/catalog/records/{observation_id}.json`

main可查目前版，固定tag供重現；引用時核對發行版本與檔案雜湊。網站[資料manifest](../site/manifest.json)指向帶SHA檔名的完整資料／詞表JSON與固定入口範本。[官方來源清單](../data/sources.csv)另列原件網址、類型與SHA；投影JSON雜湊不能冒充原件雜湊。

## 機讀入口與CSV來源欄位

網站根目錄的[llms.txt](https://poplolioi11.github.io/tw-public-museum-conservation/llms.txt)是給AI與程式的文字導航，指出版本、manifest、固定JSON、官方來源定位及不相加等使用限制。實際數字仍以事實主檔與逐筆官方證據為準，不以導航摘要取代原件。

篩選CSV保留觀測欄位，並帶有五個來源欄位：`official_file_url`、`official_landing_url`、`original_file_type`、`original_file_sha256`、`original_file_bytes`。HTML的`source_locator`另保留在觀測欄，PDF頁碼留null；原件bytes與SHA不冒充公開投影bytes或SHA。

## 三個查詢欄位

| 欄位 | 用途與界線 |
|---|---|
| action_categories | 原報提及的修護、維護、整飭、檢視、數位等複選標籤；不把數量拆配到各類 |
| completion_category | 分開明載完成、父項／段落脈絡、截止時點、年度執行、進行中及未明載；原completion_status另保留 |
| subject_scope_category | 原報本館、託管、館外受託或混合待核；不是法律權屬調查 |

值與中文標籤見[詞表](../schema/vocabulary.json)。分類規則1.2由本機程式產生，保留舊版標籤含義；不得只改一張匯出表而讓各格式分歧。

## 年度、來源與缺值

- 單年看data_year；跨年為null，須看reporting_period_raw與明示起訖年，不能每年複製同一量。
- 「兩」保留quantity_raw，由本機程式精確轉2；原單位「幅」不改件。近300、300餘與雙單位合列的quantity_numeric仍為null。
- PDF看頁序及印刷頁；HTML兩種頁碼為null，以觀測的source_locator及查核的source_locators回到明確年度段落。
- body_reviews記來源查核。未定位合格量不是零；extends_review_id表示補充範圍，不抹去原查核的有限結論。
- 原報合計、子項、不同作業或可能重疊批次不能一起相加。例如[臺史博2020完整修護分項](../catalog/records/NMTH-2020-full-treatment.json)與[年度合計](../catalog/records/NMTH-2020-conservation-reported-total.json)不相加；「完整修護」也不自動代表明載完成。

## 使用界線

v0.15.0共有307列，其中304原報觀測、1推算、2脈絡；不是全國修復物件總量。保留observation_id、資料年或期間、quantity_raw、原單位、原詞及官方來源定位再引用。網站不提供跨館總量或責任績效排行。

## v0.15.0的補充查找表

[缺量註記](../data/absence_annotations.jsonl)以review_id連回275則目前指定段無量查核；標籤與引文是目前公開查核說明的分類（本版11則新增指定子段補讀延伸），不代替官方原件。1則資訊不足保留，不推未公開原因。275則、269個含N格與268個僅N格的粒度不同。

[搜尋別名](../data/normalized_observations.jsonl)以observation_id連回原列；不帶數量、不改完成狀態或可比資格。[作業對照表](METRIC_CLASS_MAP.md)、[完成詞表](COMPLETION_STATUS_MAP.md)及[單位表](UNIT_MAP.md)說明映射與null的保留方式。

[覆蓋率JSON](../metadata/coverage.json)提供原歷史索引、本版有界查核及聯集三個集合；[逐格表](../data/coverage_cells.csv)保留所有目前來源狀態，[分組表](../data/coverage_groups.csv)附各自分母。先選population_id，再選分組維度；同一格會出現在不同集合及不同切面，不可把整張分組表加成一個總數。工作批次不是官方館類，unknown保持獨立分母。這些表只計查核格，不能據以加總修護量。

SQLite的四個同名補充表保存row_number與完整record_json；複選標籤以JSON陣列保留。網站[有界資料整理頁](https://poplolioi11.github.io/tw-public-museum-conservation/enrichment.html)提供相同公開資料、圖與文字表格，manifest列各端點SHA及bytes。

[JSON](../data/facts.json)、[JSONL](../data/observations.jsonl)、[CSV](../data/observations.csv)、[SQLite](../data/museum-conservation.sqlite)及網站由同一公開主檔產生。先看[資料樣貌](../catalog/SAMPLE.md)可比較不同計量方式；例子不構成可相加數列。

SQLite下載檔以發行manifest核SHA；跨SQLite版本重建則核schema、全表rows與完整性。兩者是不同檢查，邏輯等價不代表原檔SHA相同。
