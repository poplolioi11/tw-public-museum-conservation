# 私立美術館公開來源獨立層

本層保存已選私立美術館的公開保存修護資料；「私立」指館所屬性，不是使用者的私人收藏或私人台帳。不採財務、人員、廠商與企業委託資料。公立原始清單、71館分母及426館年格維持分開，不能把本層列數或原報數量加入公立或全國合計。

主容器為 `data/private_art_pilot.json`，採 `schema/private_art_pilot.schema.json`。根欄位為 `schema_version`、`dataset_version`、`scope`、`public_baseline_eligible`、`institutions`、`sources`、`observations`、`body_reviews`、`scope_notes`，以及可省略的 `relations`。目前 `schema_version` 為 `1.0`、`scope` 固定 `private_art_museum_pilot`、`public_baseline_eligible` 固定 `false`，關係只允許空陣列。版本須與呼叫者提供的版本一致。

館所ID使用 `PRIV-` 加三位數；觀測、覆核及範圍註記只能引用容器內的館所。初始朱銘美術館館所ID為 `PRIV-001`，`ownership_type` 為「私立藝術家基金會館」，`automatic_numeric_aggregation_allowed` 必須為 `false`。館所欄位僅允許機構ID、名稱、所有權類型、官方網址與此加總旗標。來源沿用既有 `facts.sources` 欄位白名單；觀測與正文覆核以本機參照重用既有兩份 schema，不修改它們。

`scope_notes` 每則含 `note_id`、`organization_id`、`source_ids`、`observation_ids`、`note`、`annual_quantity_eligible:false`。可保存館內外、權屬、期段、分項與合計的範圍矛盾或未採原因；註記不會把兩種說法自動選成一種，不核實包含關係，也不把跨年數分配到單年。

`scripts/private_art_pilot.py` 提供 `generate(root:Path, version:str)->dict`，回傳 `outputs`、`tables`、`summary`。它不自行寫檔、不讀私人原件、不連網、不連SQLite，也不改 `facts.json`、`metadata/coverage.json` 或公開母表。呼叫者完成整階段審查後，再統一保存及發布回傳內容；輸入不存在會報錯，不會悄悄建立空資料。

輸出為 `data/private_art_observations.{csv,jsonl}`、`data/private_art_sources.{csv,jsonl}`、`data/private_art_body_reviews.{csv,jsonl}`、`data/private_art_scope_notes.{csv,jsonl}`，以及 `metadata/private_art_pilot_build.json`。表名固定相同的 `private_art_` 前綴，每列增加 `dataset_scope` 與完整原列的 `record_json`。原始容器由呼叫者另行保存；模組不修改原詞、原數字、完成狀態或其查詢分類。陣列按各表ID排序；同一輸入重跑的輸出位元組一致，沒有寫入當前時間或本機路徑。

驗證包含欄位白名單、ID唯一與本層引用閉合、來源SHA-256與 `src-` 加前16碼的對應、公開HTTP/HTTPS網址，以及私人路徑與憑證跡象拒絕。PDF來源必須提供正整數 `original_file_pdf_pages` 以驗頁界；HTML來源不能偽造PDF頁，觀測須有 `source_locator`，已讀正文覆核須有逐來源定位。覆核引用的觀測須同館同年；未分配年度的跨年觀測，目標年須落在保留的起訖內。讀圖與文字讀取頁只能是該來源已覆核頁的子集，且觀測所引頁須在覆核頁內。來源不得跨私館重用。

數字轉換沿用 `build_exports.source_number`；帶限定詞與複合量詞的未解析值保持空值，不當零。查詢分類沿用既有 `facets`，並檢查完成分類沒有偏離原先保留的完成狀態。程式推算須保留分項、各分項原值與同單位證據；不執行跨館加總。來源雜湊為來源研究階段保存的證據，本匯出器沒有重新讀取原PDF/HTML位元組，因此建置記錄明示未重驗原始位元組；通過此模組也不代表獨立人工二校或全年全來源讀畢。
