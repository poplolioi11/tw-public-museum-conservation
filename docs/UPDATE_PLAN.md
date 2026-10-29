# 後續整理與逐版更新

v0.14.0為2026-10-30的既有證據整理版。本輪完成既有觀測的30格關聯索引回填、275則指定段缺量註記分類、搜尋正規化及明確分母的涵蓋附表；沒有新增觀測、來源原件或原件閱讀。

## 本輪完成範圍

- 原299列紀錄、328來源及關係保留；查核由552增為582則，目前467個葉節點對應456館年格。30則新增索引只連89筆既有原報觀測，見[INDEX_BACKFILL30](INDEX_BACKFILL30.md)。
- 275則未定位量葉節點分布於269館年格；分類只讀既有公開查核註記，264則有註記支持、11則資訊不足，不改原查核狀態，見[ABSENCE](ABSENCE.md)。
- 涵蓋分開列426格歷史基線、456格已查核及541格聯集；85格not_assessed與未定位來源分開。保留全部目前葉節點及混合狀態，不取最高狀態，見[COVERAGE](COVERAGE.md)。
- 正規化附表提供搜尋別名及作業多標籤，原91個作業分類、34個完成用語及25個單位原值不動；null與未明列不當量詞，別名不代表數量可換算或跨館可比。見[作業](METRIC_CLASS_MAP.md)、[完成](COMPLETION_STATUS_MAP.md)、[單位](UNIT_MAP.md)對照。
- [研究筆記](RESEARCH_NOTE_DRAFT.md)說明資料、方法與限制，維持repo草稿層級，不宣稱投稿、DOI或人類雙校。

## 下一次更新的觸發條件

已有數值卻缺關聯索引時，先核既有觀測與來源的識別、年份、頁列及原範圍，避免重複閱讀被算成新證據。指定段未定位量、資訊不足與適用正文待核，須分別保留；只有出現具名館務正文、新附件、完成清冊、逐年表或原件換版等具體線索時，才依實際範圍延伸查核。沒有新線索時不反覆搜尋同文，也不把缺量推成全年未做或未公開。

後續註記若更正，保留版本與理由；新的原件閱讀另建有明確範圍的查核，不把本輪註記分類追溯稱為原件閱讀。所有新增作業詞或單位先審對照及原值清冊，再建搜尋附表；未知原值不自動歸入看似相近的類別。跨年、總子項、母子館及可能重疊批次仍不拆配或相加。

原定順序一至六的第一輪有界來源查找及後續補讀沿革，保留於[NPM](NPM.md)、[BATCH2](BATCH2.md)、[BATCH3](BATCH3.md)、[BATCH4](BATCH4.md)、[BATCH5](BATCH5.md)、[BATCH6](BATCH6.md)、[BODY_FOLLOWUP](BODY_FOLLOWUP.md)及[BODY_FOLLOWUP40](BODY_FOLLOWUP40.md)。這些歷史範圍不是全國或各館全年全量；原名錄的索引轉錄層級不因新增附表而改變。

## 本版整合驗收

發布前核對原觀測字典與來源不變、索引外鍵／年度／定位、引文與標籤依據、原值清冊、三種分母及混合狀態。資料附件與網站分別核版本與SHA；本機檢查不替代公開端點讀回。新附表清單與雜湊見[enrichment_build](../metadata/enrichment_build.json)，方法分見ABSENCE、COVERAGE及三份詞表。

## 網站交付與部署

本版以同一公開主檔產生靜態前端、完整篩選結果CSV、逐筆固定JSON、llms.txt機讀導航與資料manifest。互動查詢入口為 https://poplolioi11.github.io/tw-public-museum-conservation/ ；每版部署結果依公開網址讀回及版本雜湊核對。

建置方式借鏡圖書館網站參考commit `558c16b3db18675b6afbaeeb6568af7881d56060`：由公開主檔產生帶雜湊檔名的JSON與固定入口，靜態前端讀取manifest；完成資料一致性、篩選／完整CSV、來源定位與必要介面檢查後才部署。部署後還須從公開網址核對版本、資料JSON雜湊與逐筆入口；參考站的驗收不能替代本站驗收。

網站只協助查找來源、原報口徑與缺口，不生成跨館修復總量、成長評分或責任排名。原始文件與私有流程不加入網站。

## 重建與核對

資料匯出與離線一致性檢查需要Python 3.10以上，使用標準函式庫；網站行為驗收與部署另外執行，不由資料格式檢查代替。

```sh
python3 scripts/build_exports.py --check
python3 scripts/selfcheck.py
```

已經過人工操作或AI來源覆讀的新候選，以獨立檔案交給更新器；候選格式／數字／關係驗證失敗時不替換現有公開主檔與匯出檔。

```sh
python3 scripts/build_exports.py --candidate-facts /absolute/path/to/reviewed-facts.json
```

輸入不變時跳過寫入。同一官方URL的原件SHA若改變，預設停止；覆讀並記錄變更後才能使用`--accept-reviewed-source-change`。格式驗證在替換前完成；寫入期間一般I/O例外有還原處理，但此檔案更新器不是斷電後可自動恢復的資料庫交易。發行以不可變Git版本與下載檔另留存。

要另行重抓官方原件核對bytes，明確指定公開儲存庫外的快取路徑：

```sh
python3 scripts/check_original_sources.py --cache-dir /absolute/path/to/source-cache --download
```

原件不隨資料庫再發布；重抓失敗或官方換版都保持待核，不能當成零或自動改寫舊數字。此步只驗原件版本，不替代原頁內容覆讀。

## SQLite跨runtime核對（v0.5.1）

跨SQLite版本重建時，以相同schema、所有資料表的完整列資料及資料庫完整性檢查核對邏輯等價，不只比筆數或抽樣。不同SQLite版本可能產生不同binary layout；邏輯等價不表示檔案bytes或SHA相同。實際發行的SQLite檔仍必須與該版發行manifest的SHA一致；下載檔不符時保持待核，不能以邏輯等價跳過原檔雜湊檢查。重建檢查不因runtime差異覆寫已保留的發行檔bytes或manifest。

v0.5.0標籤保留。該次Linux CI因要求跨SQLite版本重建bytes完全一致而失敗，未建立GitHub Release，也未由該次CI部署。v0.5.1修正可攜性檢查，沿用同一205列內容；後續版本的公開部署與下載檔仍依各自讀回紀錄核對。
