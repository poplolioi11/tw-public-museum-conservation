# 分層補充資料：期間、來源與使用界線

版本v0.22.0，2026-11-05。公立補查、私立藝術家／基金會館、私立大學館／典藏中心、私立大學其他博物館及名稱候選分五檔保存；它們不進原311列公立主觀測、原71組織×六年歷史索引或固定分階段比例。

本版涉及9個私立館／典藏中心（含既有朱銘）、3個既有公立候選與1個藝術中心名稱候選，不是全國館數或完整年度面板。每一識別碼都是專案查找碼，不冒充官方館所代碼。

|分層|機構工作列|帶量值紀錄|文字紀錄|資料|
|---|---:|---:|---:|---|
|公立既有候選補查|3|5|2|[JSON](../data/conservation_supplement/public_followup.json)／[CSV](../data/conservation_supplement/public_followup.csv)／[JSONL](../data/conservation_supplement/public_followup.jsonl)|
|私立藝術家／基金會館|5|1|4|[JSON](../data/conservation_supplement/private_artist_museums.json)／[CSV](../data/conservation_supplement/private_artist_museums.csv)／[JSONL](../data/conservation_supplement/private_artist_museums.jsonl)|
|私立大學館／典藏中心|3|15|6|[JSON](../data/conservation_supplement/private_university_museums.json)／[CSV](../data/conservation_supplement/private_university_museums.csv)／[JSONL](../data/conservation_supplement/private_university_museums.jsonl)|
|私立大學其他博物館|1|0|0|[JSON](../data/conservation_supplement/private_university_other_museums.json)／[CSV](../data/conservation_supplement/private_university_other_museums.csv)／[JSONL](../data/conservation_supplement/private_university_other_museums.jsonl)|
|名稱與範圍候選|1|0|0|[JSON](../data/conservation_supplement/art_center_scope_candidates.json)／[CSV](../data/conservation_supplement/art_center_scope_candidates.csv)／[JSONL](../data/conservation_supplement/art_center_scope_candidates.jsonl)|

21則帶量值、12則文字是紀錄數，不是修復合計。7則帶量值能定位作業年，14則作業年保持未知；有年份也不表示全年全量。原朱銘試辦4列維持於原獨立容器，未再計為新增。

## 14則期間補核

逐則回到既存原件及相鄰館務段落後，沒有一則足以由報告年改填單一作業年。補核改為明列期間型態、來源限定與可回查旁證。會議日、發布日、學年、紀念展敘事年與作業年分開；送裱、委託或計畫不升為完成。

- 5,312組件為累計清點：2024-05-01與07-03報告均見同量。[較早原頁](https://secretariat.pccu.edu.tw/var/file/10/1010/img/399/1815%26112-10.pdf#page=52)記4月22日當次清點，不能拿當次日期當整批累計起訖。
- 601組670件為同句雙量詞累計：[2025-04-09原頁](https://secretariat.pccu.edu.tw/var/file/10/1010/img/399/1826%26113-9.pdf#page=53)在3月5日當次盤點後已有同量記載；不是2025年度新增清點量，兩種量詞不相加。
- 每月894件另有同一[4月報告](https://secretariat.pccu.edu.tw/var/file/10/1010/img/399/1826%26113-9.pdf#page=53)具名三月份點檢旁證，但不證明7月原句的整段月份或全年每月都完成，不能乘12。

原數值來源與期間旁證各自保留source_id、URL、PDF序號／印刷頁與定位。旁證不取代原量值來源。其餘未載起訖的已完成、委託、送裱及修復，只保留報告快照和未知界線。

中美館25件修復的資料年為2025，報告出版在2026；另一筆200件整飭修復是混合作業，期間及與25件的包含關係未確定，不相加或做差。李梅樹三件協作個案的委託、執行與關聯機構分列，不由作品、展覽年或計畫清單推權屬與完工年。

## 替代官方來源與機構脈絡

亞洲大學校方網域的備用館站介紹正文已取得；學校單位組織入口仍連原主站，因此不宣稱正式遷站。一般志工展場服務職掌未直接給出典藏保存修護實績，本版不提升為修護人力或年度作業紀錄。新取得113、114學年度分層負責附件沒有定位美術館章，不能代替舊111學年度職掌。

屏東新館依[2026-03-27官方新聞](https://www.frs.gov.tw/view.php?id=14589&subtheme=&theme=news_frs)分開記典禮日與03-28對外開放；不借新館日期回填舊館或縣典藏中心的年度量，也不把全部舊年改成未適用。尚未取得正常原始bytes的來源維持待核，不製造SHA或採入量值。

東海校方正式名稱是藝術中心，美術館候選名稱未證明為正式別名或另一單位；另設候選頁，不計入公私立館數。基金會登錄也不自動證明現行開館。

## 網站、機讀與重建

- [公立補查頁](https://poplolioi11.github.io/tw-public-museum-conservation/supplement-public.html)、[私立分層頁](https://poplolioi11.github.io/tw-public-museum-conservation/supplement-private.html)、[名稱候選頁](https://poplolioi11.github.io/tw-public-museum-conservation/supplement-scope.html)各有初始HTML事實與來源；JavaScript只篩選已列內容。
- 館名／作業文字、資料層、量值／文字與作業年可篩選；未知作業年是獨立選項，報告年不代填。0列館仍顯示限定說明，不當零修護。
- 五個JSON容器各含機構、來源及紀錄；CSV／JSONL只匯出該層紀錄。空CSV保留完整欄名，null不轉0。新附表沒有併入既有SQLite觀測表。
- [schema](../schema/conservation-supplement.schema.json)、[驗證與匯出程式](../scripts/conservation_supplement.py)及[建置清單](../metadata/conservation_supplement_build.json)可重跑。公開程式只讀已核白名單輸入，不讀私人原件或判定台帳。
- period_kind是搜尋分類；period_label、period_basis及period_evidence保留實際來源界線。quantity_numeric只做精確原字串轉換，雙量詞保持元件與原句，沒有scalar總數。

## 權利、品質與公開範圍

公開只發必要事實、一般作業文字、來源中介資料與定位。官方／館方原PDF、完整HTML、頁圖、私人判定、個人／廠商名單、經費、精細庫位及安全配置不重散布。官網連結或SHA不使原件取得本專案授權。

本版為AI輔助指定來源讀核與本機程式檢查；人類固定核讀仍為博物館0／50、圖書館0／120，不宣稱人工雙校、專家或機構認證。非機率選樣與不同報告口徑不能用來比較公私立揭露率、全國總量或績效。後續只在新原件、清冊或官方釋義出現時重開具體缺口。
