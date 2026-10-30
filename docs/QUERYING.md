# 查找與引用

先從[館所索引](../catalog/README.md)選館，再看資料年／跨年期間、原報作業、單位、完成語及對象範圍。[互動網站](https://poplolioi11.github.io/tw-public-museum-conservation/)依manifest辨識版本；發行與部署各由實際讀回確認。

## 網頁、CSV與固定紀錄

網站依館所、年度、作業、單位及完成狀態篩選。篩選CSV涵蓋條件下的全部結果，不限畫面分頁；[完整觀測CSV](../data/observations.csv)提供整版紀錄。列數不是唯一藏品數或完成合計。

每筆有`records/{observation_id}.json`網站入口，儲存庫固定版可使用：

`https://raw.githubusercontent.com/poplolioi11/tw-public-museum-conservation/v0.16.0/catalog/records/{observation_id}.json`

main供目前版查找，固定tag供引用與重現；核對實際版本、檔案雜湊及官方來源。[資料manifest](../site/manifest.json)指向完整資料及下載，[來源清單](../data/sources.csv)提供原件網址、類型、bytes與SHA；資料投影SHA不能代替原件SHA。

## 先讀原口徑

|欄位|用途與界線|
|---|---|
|action_categories|作業複選標籤；不把數量拆配到各類|
|completion_category|分開明載完成、父項／段落脈絡、截止時點、年度執行及未明載；原completion_status另保留|
|subject_scope_category|原報本館、託管、館外受託或混合待核；不作法律權屬推定|

[詞表](../schema/vocabulary.json)與[完成用語說明](COMPLETION_STATUS_MAP.md)可查分類界線。「完整修護」是作業詞，不自動代表已完成。quantity_raw、原單位、原範圍及官方定位應一起引用；近似量、雙單位的精確數值仍可為null。

單年看data_year，跨年看reporting_period_raw，不每年複製同一量。PDF看頁序／印頁，HTML用source_locator，頁碼為null；同年不同來源都保留，不選一筆蓋過其他證據。未知或未定位不補零。

## 關係與證據附表

[關係JSON](../data/relation_projection.json)／[JSONL](../data/relation_projection.jsonl)／[CSV](../data/relation_projection.csv)逐列連回原86則relations，保留原字典、角色參照、原位置及SHA。38種原名稱歸為15類、4種註記層級，只協助查找，不是新核官方關係。

先分辨這列是總分項提醒、作業重述、平行量詞、重疊未核，或只是來源續頁／構成脈絡。原relationship_verified的true、false或未列各照錄；未列為null，false不是已證明沒有關係。即使原未列not_additive_together，也不能據此相加。詳見[RELATIONS](RELATIONS.md)與[規則](../metadata/relation_projection_rules.json)。

## 14筆完成語覆核

有覆核的固定紀錄提供`completion_review_reference`，可連至[完成語JSON](../data/completion_reviews.json)／[JSONL](../data/completion_reviews.jsonl)／[CSV](../data/completion_reviews.csv)。以observation_id找對應列，依序讀原完成詞、completion_phrase_raw、completion_phrase_scope、review_scope、原件SHA／頁碼及remaining_uncertainty。

本版14筆皆為`parent_context_supported`：指定父項或段落可支持原有完成脈絡，仍保留`completion_from_context`，沒有改成分項明載完成。這些是既有紀錄的證據附表，不是14件新增完成物件；不要將父句完成語轉移到其他對象、作業或全部年度量。

覆核使用9份既存PDF、10個指定原頁；文字可讀頁與實看圖頁分列，掃描頁依原圖判讀。不是全頁所有欄位或全冊核讀。欄位與判讀界線見[覆核規則](../metadata/completion_review_rules.json)及[結構](../schema/completion_review.schema.json)。

## 館年分母與其他附表

[覆蓋率JSON](../metadata/coverage.json)含五個集合／年份子集。先選population_id再選分組，不能把不同集合或切面的列數相加。

|集合／子集|館年格數|
|---|---:|
|原71組織×2020–2025歷史索引|426|
|全部年份已有查核|471|
|原索引與全部查核的聯集|543|
|已查核中的2020–2025子集|469|
|已查核中的期間外歷史子集|2|

高美館2015、2016兩格只補回6筆既有觀測的索引；與2020–2025分母分開。同期間聯集仍為541格。這些是有重疊的索引集合，不是全國母體，也不代表館方新增公布或保存活動增加。工作批次不是官方館類，權管與島群保留不明。

[缺量註記](../data/absence_annotations.jsonl)連回275則目前指定段無量查核，其中274支持、1不足；269個含N格與268個僅N格是不同粒度，標籤不推機構未公開原因。[搜尋別名](../data/normalized_observations.jsonl)連回307筆原列，不改完成詞、量詞或可比資格。

[逐格表](../data/coverage_cells.csv)保留目前全部來源狀態，[分組表](../data/coverage_groups.csv)附各自分母。SQLite另存relation_projection、completion_reviews及原有附表，保留完整record_json；JSON陣列不拆成可相加計量。網站[有界資料頁](https://poplolioi11.github.io/tw-public-museum-conservation/enrichment.html)提供關係分類與完成語表的查讀入口，實際內容以部署版本及讀回結果為準。

## 引用與使用界線

v0.16.0仍為307列：304原報觀測、1推算、2脈絡。保留原詞、原量詞、期間、對象、完成語與官方定位，不做跨館總量或排名。根目錄[llms.txt](../llms.txt)只是AI導航，不能代替事實主檔或原始證據。

下載SQLite以發行manifest核SHA；跨runtime重建以相同schema、全表rows與完整性核對，邏輯相同不代表原檔SHA相同。官方原件、完整頁圖及私人補充不重發布，詳見[公開範圍](PUBLICATION.md)。
