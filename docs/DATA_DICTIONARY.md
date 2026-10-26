# 欄位與檔案

`data/facts.json`是本版的事實投影主檔，`metadata/inventory.json`是凍結的來源盤點。JSONL、CSV與SQLite由主檔產生，不各自人工修改。CSV使用UTF-8 BOM，空欄代表缺值；巢狀欄位為JSON字串。

| 欄位 | 意義 |
|---|---|
| `observation_id` | 本專案穩定紀錄識別；一列不等於一件藏品 |
| `organization_id` | 本專案盤點識別，非官方統一館碼 |
| `organization_name` | 整理時的機關／館所名稱；名稱不作自動數值合併 |
| `data_year` | 原報敘述的資料年度，不由出版年推算 |
| `publication_year` | 已核出版年；未核則null |
| `metric_as_reported` | 原報作業名稱。推算列僅保留來源作業詞 |
| `metric_label`、`metric_class` | 本整理的顯示名稱與分類；不等於統一統計定義 |
| `quantity_raw` | 原數字字串，保留全形、逗號、近似及雙單位。推算值沒有原報單一數字，留null |
| `quantity_numeric` | 明確原字串經程式轉換，或明標的推算值；近似及雙單位合列不硬轉單一數字 |
| `quantity_qualifier` | 精確、近似、雙單位或推算等原數字性質 |
| `unit_as_reported` | 件、組件、號、案、條、片等原量詞，不能互換 |
| `unit_status` | 原報有量詞為reported；原表未標量詞為not_stated_in_source，不能自行填件 |
| `numeric_origin` | source_reported為原報值；controller_derived為程式推算 |
| `record_kind` | observation為原報觀測；derived_summary為推算；context_component只解釋混合合計 |
| `source_scope`、`subject_scope` | 年度、批次、計畫、館藏／受託等範圍。未逐件核權屬者照實標示 |
| `completion_status` | 原報是否明載完成或僅列年度執行；不把計畫目標當完成量 |
| `source_id` | 對應sources。識別由PDF SHA前16碼產生，完整SHA仍保留 |
| `pdf_page_1_based` | PDF檔從1開始的頁序號，與印刷頁不同 |
| `printed_page` | 原頁印刷頁碼；跨頁PDF可有兩個印刷頁 |
| `source_components`、`dual_unit_quantities` | 原報分項或同批雙單位，只作脈絡，不能再與總項相加 |
| `derivation` | 推算方法、原分項與公式；不證明唯一物件或跨年可比 |
| `verification_status` | 文字／原頁覆讀層級。不是人類定本或館方認證 |
| `aggregation_role`、`interpretation_note` | 原報分項、合計及解讀限制。只有關係足夠明確才標示包含 |
| 四個布林限制欄 | default_aggregation_allowed、cross_museum_comparable、unique_object_count_verified、year_on_year_ready本版均為false |

來源表的`original_file_sha256`、`original_file_bytes`指取得的官方PDF。`official_landing_url`為官方書目／內容頁，`official_file_url`為實際文件端點；例如鶯歌D14端點副檔名雖是.htm，實際回傳PDF。`metadata/build.json`的projection SHA則指本專案公開JSON，兩者不可混用。

`source_inventory`為71個組織×2020–2025的426格。`status`為找到報告、父機關報告候選、未定位或歷史範圍待核等來源狀態，不是修復量。`metadata/read_coverage.json`另列本版已有數值分項的組織年度；它也不宣稱完整涵蓋該年度所有作業。

`relations`記錄不相加、平行單位、疑似對應或原報合計脈絡。`relationship_verified=false`不能用來建立確定父子集合；來源列數、原報總數與分項不能一起相加。臺文館2025的31件與114條即使數字相加為145，也未建立它們與摘要145件的父子關係。

SQLite的`observations`保留常用欄位的數字／null，另有完整`record_json`。其他表保留每列`record_json`，供SQLite JSON函式或程式讀取。不要對整張表執行SUM當全國修復總量；可按館名、年份與原詞篩選後回原件引用。

所有原件與頁碼的實際轉錄核對，與離線格式一致性檢查是兩個不同工作。`scripts/build_exports.py --check`不會重新下載原件，不能被描述成原件內容再次驗證。
