# 原關係與證據註記的機讀附表

版本v0.16.0；逐列保留86則原關係／證據註記，不合併、不去重、不改原值。

這是既有公開註記的分類與參照附表，不是新的官方原件核讀、物件去重或關係認證。分類只能協助查找，不能授予相加、換算、跨年配分或獨特物件推定資格。

## 如何解讀

- source_relation_ordinal_1_based是原relations陣列的1起算位置；source_relation_sha256核對該原字典的canonical JSON。原字典完整保留在original_relation。
- reference_roles保留每一原參照欄及其順序；observation_ids只供參照聯集，不是物件集合。source_ids來自被參照觀測與原明列來源，不是已新讀來源清單。
- relationship_verified_original僅照錄原布林值，未列時為null；false只表示原註記沒有核實該關係，不是已證明沒有關係。true也不是本版重新驗證。
- not_additive_together_original只照錄原值；未列時null不代表可相加。所有投影列仍固定不授予加總、量詞換算或獨特物件推定資格。
- 續頁定位、來源構成脈絡與計量提醒，不自動當成兩筆物件之間的包含關係。原分類名稱含includes、same、completed等字樣，不能替代原件證據或補出未列的verified旗標。

## 分類計數（註記列，不是館年或文物量）

|分類|註記列數|
|---|---:|
|跨期階段或可能重疊不拆配|6|
|同年不同官方來源並存|21|
|檢視與表單關聯不推物件映射|1|
|不同標籤可能對應而未核實|1|
|不同指標作業或計數對象範圍|6|
|混合作業不拆配數量|1|
|批次或作業重疊尚未核明|19|
|原報平行量詞或多層計量|13|
|同段處置與完成範圍|1|
|原報總項與分項提醒|11|
|同來源作業重述只留原觀測|2|
|單一跨期紀錄不重複作年度量|1|
|來源證據續頁定位|1|
|來源構成僅作脈絡|1|
|對象分列不推方向或所有權|1|

## 原關係核實旗標

|原旗標狀態|列數|
|---|---:|
|原列true|3|
|原列false|30|
|原未列，保留null|53|

原資料見[data/facts.json](../data/facts.json)的relations；完整投影見[data/relation_projection.json](../data/relation_projection.json)，分類規則見[relation_projection_rules.json](../metadata/relation_projection_rules.json)。

