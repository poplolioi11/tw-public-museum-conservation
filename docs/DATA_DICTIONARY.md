# 欄位與檔案

`data/facts.json`是本版的事實投影主檔，`metadata/inventory.json`是凍結的來源盤點。JSONL、CSV與SQLite由主檔產生，不各自人工修改。CSV使用UTF-8 BOM，空欄代表缺值；巢狀欄位為JSON字串。

| 欄位 | 意義 |
|---|---|
| `observation_id` | 本專案穩定紀錄識別；一列不等於一件藏品 |
| `organization_id` | 本專案盤點識別，非官方統一館碼 |
| `organization_name` | 整理時的機關／館所名稱；名稱不作自動數值合併 |
| `data_year` | 原報明示的單一資料年度；跨年合計為null，不由出版年推算 |
| `publication_year` | 已核出版年；未核則null |
| `metric_as_reported` | 原報作業名稱。推算列僅保留來源作業詞 |
| `metric_label`、`metric_class` | 本整理的顯示名稱與分類；不等於統一統計定義 |
| `quantity_raw` | 原數字字串，保留全形、逗號、明確中文數詞、近似及雙單位。推算值沒有原報單一數字，留null |
| `quantity_numeric` | 明確原字串經程式精確轉換（例如「兩」轉2），或明標的推算值；近似及雙單位合列維持null |
| `quantity_qualifier` | 精確、近似、雙單位或推算等原數字性質 |
| `unit_as_reported` | 件、組件、號、案、條、片等原量詞，不能互換 |
| `unit_status` | 原報有量詞為reported；原表未標量詞為not_stated_in_source，不能自行填件 |
| `numeric_origin` | source_reported為原報值；controller_derived為程式推算 |
| `record_kind` | observation為原報觀測；derived_summary為推算；context_component為脈絡列，例如混合合計分項或純數位作業；不納實體修復量 |
| `source_scope`、`subject_scope` | 年度、批次、計畫、館藏／受託等範圍。未逐件核權屬者照實標示 |
| `completion_status` | 原報是否明載完成或僅列年度執行；不把計畫目標當完成量 |
| `source_id` | 對應sources。識別由官方原件SHA前16碼產生，PDF或HTML均保留完整SHA |
| `pdf_page_1_based` | PDF檔從1開始的頁序號，與印刷頁不同；HTML必須為null |
| `printed_page` | 原頁印刷頁碼；跨頁PDF可有兩個印刷頁；HTML必須為null |
| `source_locator` | HTML觀測必填的非空短定位，指向明確年度段落；不以衍生渲染頁碼冒充原頁 |
| `source_components`、`dual_unit_quantities` | 原報分項或同批雙單位，只作脈絡，不能再與總項相加 |
| `derivation` | 推算方法、原分項與公式；不證明唯一物件或跨年可比 |
| `verification_status` | 文字／原頁覆讀層級。不是人類定本或館方認證 |
| `aggregation_role`、`interpretation_note` | 原報分項、合計及解讀限制。只有關係足夠明確才標示包含 |
| 四個布林限制欄 | default_aggregation_allowed、cross_museum_comparable、unique_object_count_verified、year_on_year_ready本版均為false |

來源表的`original_file_sha256`、`original_file_bytes`指取得的官方PDF或完整原始HTML bytes。`official_landing_url`為官方書目／內容頁，`official_file_url`為實際文件端點；例如鶯歌D14端點副檔名雖是.htm，實際回傳PDF。`metadata/build.json`的projection SHA則指本專案公開JSON，兩者不可混用。

`source_inventory`為71個組織×2020–2025的426格。`status`為找到報告、父機關報告候選、未定位或歷史範圍待核等來源狀態，不是修復量。`metadata/read_coverage.json`另列本版已有數值分項的組織年度；它也不宣稱完整涵蓋該年度所有作業。

`relations`記錄不相加、平行單位、疑似對應或原報合計脈絡。`relationship_verified=false`不能用來建立確定父子集合；來源列數、原報總數與分項不能一起相加。臺文館2025的31件與114條即使數字相加為145，也未建立它們與摘要145件的父子關係。

SQLite的`observations`保留常用欄位的數字／null，另有完整`record_json`。其他表保留每列`record_json`，供SQLite JSON函式或程式讀取。不要對整張表執行SUM當全國修復總量；可按館名、年份與原詞篩選後回原件引用。

所有原件與頁碼的實際轉錄核對，與離線格式一致性檢查是兩個不同工作。`scripts/build_exports.py --check`不會重新下載原件，不能被描述成原件內容再次驗證。

## 跨年期間與正文覆讀（v0.2.0起）

原報只給跨年共同數字時，`data_year=null`，`year_assignment_status=multi_year_not_allocated`；`reporting_period_raw`保留原期間，`data_year_start/end`只記來源明示的起訖年，不杜撰月日。這筆只存一次，不複製成各年的值，也不除以年數造成年平均。查找某年時請同時查看明示期間是否涵蓋該年。

`body_reviews`另記本批每個目標館所年度的有限覆讀範圍，與數值觀測分開。`target_data_year`是查找目標，不會使跨年報告的數字自動成為當年數字。`source_ids`連到有原件SHA的來源；僅入口或未取得正文不升級為原件已讀。`reviewed_pdf_pages_1_based`只表示列出的正文頁，書目／版權頁核對不等於年報全文覆讀。

| review_status | 解讀 |
|---|---|
| numeric_observations_verified | 所列來源及頁面有本版納入的數字；仍看各觀測的年度與期間 |
| body_read_no_eligible_quantity_located | 在已列章節／頁面未定位本題合格數量；不是全館零修護或未公開 |
| source_found_body_not_reviewed | 找到來源，但本文覆讀仍待完成 |
| source_not_located_in_this_search | 本輪限定搜尋未定位來源，保留缺值 |
| annual_scope_not_separable | 合刊或跨年資料不能拆到目標單年；若有合格跨年觀測則只存一次 |
| outside_selected_scope | 已列正文內容屬其他作業，本批未作修護數字收錄 |

`missing_quantity_is_zero`固定false。科學館的標本採集、入藏、初次製作、活體照養、研究／數位化與設施維修不能只因同頁出現「修復」便改作既有館藏完成修復量。公共來源中的無關人類遺骸個案也不在這批公開範圍。

v0.2.0的主檔schema_version為2.0：data_year允許跨年null，並新增body_reviews。資料版本(dataset_version)與結構版本分開；本版v0.5.1的主檔結構為4.0，舊版結構及內容保留於各tag。

## v0.3.0查詢欄位與補充來源

action_categories是來源作業用語的複選標籤；completion_category將明載完成、父項脈絡、截止時點、年度執行、進行中及未明載分開；subject_scope_category只依原報對象，不證明法律所有權。classification_rule_version記分類程式版本，詞表在schema/vocabulary.json。原始metric與completion_status不改。v0.3.0主檔結構版本為3.0；本版為4.0。

來源original_file_type可為PDF或HTML；HTML使用body_reviews.source_locators正文定位，PDF保留各來源頁映射。v0.3.0的82個採用來源版本不是82份年度修復統計；本版111份來源也不能作修復量。body_review_records計查核則數，body_review_target_year_cells計唯一館所年度；同年不同來源scope可有多則，extends_review_id指向補充前的查核，舊紀錄不覆蓋。

跨頁數值保留additional_pdf_pages_1_based，與首個pdf_page_1_based合讀；不將跨頁後半句當作另一份來源。

## v0.5.1結構4.0：HTML數值與精確數詞

HTML觀測使用`pdf_page_1_based=null`、`printed_page=null`及必填`source_locator`。來源`original_file_type=HTML`的SHA與bytes指完整取得的原始HTML，不是文字擷取檔、截圖或衍生列印PDF。HTML出版年未核仍為null；頁面更新日期不能冒充資料年或出版年。

查核紀錄中，PDF各來源實讀頁保留於`source_page_reviews`；HTML另用`source_locators`列表，每項為`{source_id, locator_type: "html_article_body", locator: "短定位"}`。它們記錄實讀範圍，不讓HTML數字掛回沒有明列量的年報頁。

`quantity_raw="兩"`、`quantity_numeric=2`屬原報值的精確單字數詞轉換，保留原單位「幅」，不是按作品名單計件或新增推算列。「近300」「300餘」及「463組（715件）」等近似／雙單位仍保留null，不能套用單字轉換規則猜數。

北美館2022的120件是保存維護措施量，不是120件藏品修復；年報8件與HTML9件分別保留原scope。來源正文已讀但沒有合格量的紀錄照實保留，不因另找到HTML數字而將原年報同源升級。

網站`site/manifest.json`記錄靜態資料JSON、詞表及固定逐筆入口的建置雜湊；其manifest結構版號與事實主檔結構4.0是不同層次。公開JSON投影SHA、網站檔案SHA與官方原件SHA各指不同bytes。

篩選CSV另帶來源表的五欄：`official_file_url`、`official_landing_url`、`original_file_type`、`original_file_sha256`、`original_file_bytes`；觀測本身的`source_locator`與原單位照常保留。網站根`llms.txt`僅作版本與入口導航，不是新的數值來源。

## SQLite邏輯內容與檔案版本

跨SQLite版本重建時，以相同schema、所有資料表的完整列資料及資料庫完整性檢查核對邏輯等價，不只比筆數或抽樣。不同SQLite版本可能產生不同binary layout；邏輯等價不表示檔案bytes或SHA相同。實際發行的SQLite檔仍必須與該版發行manifest的SHA一致；下載檔不符時保持待核，不能以邏輯等價跳過原檔雜湊檢查。重建檢查不因runtime差異覆寫已保留的發行檔bytes或manifest。
