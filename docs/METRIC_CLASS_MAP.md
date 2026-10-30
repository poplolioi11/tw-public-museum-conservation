# 作業分類搜尋別名

本表由 `scripts/normalization.py` 的 `build_outputs(facts, rules)` 產生。規則版 `1.0`；既有分類規則版 `1.2`。

已審核 `data/facts.json` 版本 `0.17.0`，觀測清冊 311 筆；輸入版本與逐列觀測 SHA-256 摘要見 `metadata/normalization_rules.json`。

僅供搜尋與發現；未新增觀測、改寫原始欄位、拆配數量、換算或授予加總資格。各列依 `observation_id` 連回 `data/facts.json` 的原證據與來源定位。

`metric_class_original` 是既有歷史分類欄，並非館方原文；館方用語另存 `metric_as_reported`。`metric_class_normalized` 逐列直接複製既有 `action_categories` 陣列，不能將 91 種原分類硬映為 91 個單一作業。相同原分類可能有不同標籤組合。

`action_class_v2` 是保留多標籤的搜尋投影；檢視／登錄與科學檢測共用搜尋值，細分類仍完整保留在 `metric_class_normalized` 與原觀測中。清潔、加固、裝裱、數位化、純數位修復及混合作業各自保留。

| 既有作業標籤 | action_class_v2 |
|---|---|
| `arrangement` | `arrangement_inventory` |
| `cleaning` | `cleaning` |
| `digital_restoration` | `digital_restoration` |
| `digitization` | `digitization` |
| `inspection_registration` | `inspection_examination` |
| `maintenance` | `preventive_maintenance` |
| `mixed_workflow` | `mixed_workflow` |
| `mounting` | `mounting` |
| `needs_review` | `needs_review` |
| `restoration_as_reported` | `reported_restoration` |
| `scientific_examination` | `inspection_examination` |
| `stabilization` | `stabilization` |

`needs_review` 留作詞彙，但本批候選若出現此值即拒絕。`initial_preparation` 僅列為 `proposed_unused`，指派觀測為 0；保存盒製作不判為文物初製。

原分類清冊共 91 值；以下按原值與逐列 canonical 標籤組合列示。

| metric_class 原值 | 原 action_categories（完整陣列） | 觀測列數 | observation_id |
|---|---|---:|---|
| `archival_arrangement_as_reported` | `["arrangement"]` | 3 | `IOE-2022-museum-arrangement-as-reported`, `IOE-2024-museum-arrangement-as-reported`, `IOE-2025-museum-arrangement-as-reported` |
| `arrangement` | `["arrangement"]` | 1 | `tfam-2021-display_arrangement-html` |
| `arrangement_and_inspection` | `["arrangement", "inspection_registration"]` | 1 | `pilot-ntcart-2025-inspection` |
| `collection_arrangement` | `["arrangement", "inspection_registration"]` | 4 | `nmp-2022-donated-stone`, `nmp-2022-reclassification`, `nmp-2023-donated-pottery`, `nmp-2023-reclassification` |
| `collection_arrangement` | `["arrangement"]` | 41 | `nmp-2020-2022-archaeology-arrangement`, `nmp-2020-2022-ethnology-arrangement`, `nmp-2020-2022-natural-history-arrangement`, `nmp-2020-archaeology-arrangement`, `nmp-2020-display-archaeology`, `nmp-2020-display-ethnology`, `nmp-2020-display-natural-history`, `nmp-2020-display-research`, `nmp-2020-ethnology-entrusted`, `nmp-2020-ethnology-own`, `nmp-2020-ethnology-total`, `nmp-2021-donated-archaeology`, `nmp-2021-entrusted-arrangement`, `nmp-2021-ethnology-display`, `nmp-2022-entrusted`, `nmp-2022-hualien-loan`, `nmp-2022-south-arrangement`, `nmp-2023-entrusted`, `nmp-2023-pottery-bags`, `nmp-2023-pottery-shards`, `nmp-2023-research-bags`, `nmp-2023-south-arrangement`, `nmp-2024-bone-antler-arrangement`, `nmp-2024-ethnology-arrangement`, `nmp-2024-research-bags`, `nmp-2025-ethnology-arrangement`, `nmp-2025-transferred-arrangement`, `NMMST-2020-specimens-arrangement`, `NMMST-2020-humanities-arrangement`, `NMMST-2021-specimens-arrangement`, `NMMST-2021-humanities-arrangement`, `NMMST-2022-specimens-arrangement`, `NMMST-2022-humanities-arrangement`, `NMMST-2023-specimens-arrangement`, `NMMST-2023-humanities-arrangement`, `NMMST-2024-specimens-arrangement`, `NMMST-2024-humanities-arrangement`, `NMMST-2025-specimens-arrangement`, `NMMST-2025-humanities-arrangement`, `LYM-2021-arrangement-partial-year`, `LYM-2021-2022-arrangement-project` |
| `collection_arrangement` | `["maintenance"]` | 1 | `nmp-2023-entrusted-fumigation` |
| `combined_arrangement_cataloguing` | `["arrangement", "mixed_workflow"]` | 1 | `thcdc-2025-arrangement-cataloguing` |
| `combined_arrangement_cataloguing_registration` | `["arrangement", "inspection_registration", "mixed_workflow"]` | 1 | `thcdc-2024-arrangement-registration` |
| `combined_arrangement_cleaning` | `["arrangement", "cleaning", "mixed_workflow"]` | 1 | `IOE-2023-museum-arrangement-as-reported` |
| `combined_arrangement_cleaning_storage` | `["arrangement", "cleaning", "mixed_workflow"]` | 1 | `nmp-2021-displayed-ethnology` |
| `combined_arrangement_digitisation` | `["arrangement", "digitization", "mixed_workflow"]` | 1 | `nmp-2024-donated-specimens` |
| `combined_arrangement_restoration_preservation_reproduction` | `["maintenance", "mixed_workflow", "restoration_as_reported"]` | 1 | `thcdc-2025-cannon-combined-treatment` |
| `combined_cleaning_and_maintenance` | `["cleaning", "maintenance", "mixed_workflow"]` | 1 | `LYM-2020-cleaning-maintenance` |
| `combined_collection_preservation_treatment_project_cases` | `["maintenance", "mixed_workflow", "restoration_as_reported"]` | 1 | `NCKU-2022-commissioned-conservation-cases` |
| `combined_digitization_arrangement_restoration_project` | `["arrangement", "digitization", "mixed_workflow", "restoration_as_reported"]` | 2 | `pilot-daxi-2024-combined`, `daxi-2025-combined-project` |
| `combined_display_support_stabilization_and_maintenance` | `["maintenance", "mixed_workflow", "stabilization"]` | 1 | `LYM-2020-display-support-maintenance` |
| `combined_historygallery_restoration_mounting_storage_measures` | `["arrangement", "mixed_workflow", "restoration_as_reported"]` | 1 | `NTU-2022-historygallery-postcards3` |
| `combined_inspection_cleaning_photography_registration_condition_assessment` | `["arrangement", "cleaning", "inspection_registration", "maintenance", "mixed_workflow"]` | 1 | `daxi-2021-combined-arrangement` |
| `combined_inventory_arrangement` | `["arrangement", "mixed_workflow"]` | 1 | `DRAMA-2023-2024-inventory-arrangement` |
| `combined_maintenance_restoration` | `["maintenance", "mixed_workflow", "restoration_as_reported"]` | 8 | `tfam-2022-routine_restoration-html`, `KHM-2024-conservation-work-items`, `KHM-2025-conservation-work-items`, `KHM-2025-treatment-objects-as-reported`, `KHM-2025-treatment-project-cases`, `KHM-2023-treatment-project-cases`, `KHM-2023-treatment-objects-as-reported`, `KHM-2023-conservation-work-items` |
| `combined_mount_form_and_storage_box_preservation` | `["maintenance", "mixed_workflow"]` | 1 | `yilan-2023-compound-maintenance26` |
| `commissioned_restoration` | `["restoration_as_reported"]` | 1 | `tfam-2023-commissioned_restoration` |
| `conservation_and_restoration_total` | `["maintenance", "mixed_workflow", "restoration_as_reported"]` | 1 | `tfam-2025-conservation_and_restoration_total` |
| `conservation_historical_register_unspecified_treatment` | `["restoration_as_reported"]` | 6 | `KMFA-2015-register-01`, `KMFA-2016-register-02`, `KMFA-2016-register-03`, `KMFA-2016-register-04`, `KMFA-2016-register-05`, `KMFA-2016-register-06` |
| `conservation_restoration` | `["restoration_as_reported"]` | 1 | `pilot-ntcart-2025-professional` |
| `digital_restoration` | `["digital_restoration"]` | 1 | `nmp-2022-digital-restoration` |
| `digital_restoration_film_table_quantity_unit_not_stated` | `["digital_restoration"]` | 1 | `KFA-2022-digital-restoration-reported-quantity` |
| `document_arrangement_not_restoration` | `["arrangement"]` | 1 | `TNAM-2024-document-arrangement` |
| `inspection_and_registration` | `["inspection_registration"]` | 1 | `tfam-2025-inspection_and_registration` |
| `inspection_or_cleaning` | `["cleaning", "inspection_registration"]` | 1 | `tfam-2024-inspection_or_cleaning` |
| `internal_conservation_category_subtotal` | `["restoration_as_reported"]` | 1 | `tfam-2023-internal-derived` |
| `maintenance` | `["maintenance"]` | 1 | `tfam-2022-preservation_measures` |
| `mixed_arrangement_restoration` | `["arrangement", "mixed_workflow", "restoration_as_reported"]` | 3 | `nmp-2024-south-total`, `KHM-2022-paper-treatment-objects`, `KHM-2022-paper-treatment-project-cases` |
| `mixed_selection_maintenance` | `["arrangement", "maintenance", "mixed_workflow"]` | 1 | `nmp-2021-display-selection-maintenance` |
| `mounting` | `["mounting"]` | 2 | `pilot-ntcart-2025-mounting`, `tfam-2020-calligraphy_remounting` |
| `museum_reported_inspection` | `["inspection_registration"]` | 12 | `NPM-2020-annual-inspection`, `NPM-2021-annual-inspection`, `NPM-2022-annual-inspection`, `NPM-2023-annual-inspection`, `NPM-2024-annual-inspection`, `NPM-2021-vdr2025-inspection`, `NPM-2022-vdr2025-inspection`, `NPM-2023-vdr2025-inspection`, `NPM-2024-vdr2025-inspection`, `NPM-2025-finalaccounts-inspection`, `NTCRI-2023-finalaccounts-condition-inspection`, `NTCRI-2023-finalaccounts-condition-form` |
| `museum_reported_restoration` | `["restoration_as_reported"]` | 6 | `yilan-2025-oil-restoration8`, `NTUA-2022-meeting1102-conserved-posters`, `gold-2020-library-document-treatment`, `taoyuan-2021-paper-completed`, `taoyuan-2023-repair-reported`, `taoyuan-2025-ink-completed` |
| `museum_reported_treatment` | `["arrangement", "maintenance"]` | 1 | `nmh-2025-35` |
| `museum_reported_treatment` | `["arrangement"]` | 8 | `ntmofa-2020-7`, `ntmofa-2021-8`, `ntmofa-2022-10`, `ntmofa-2022-9`, `ntmofa-2023-11`, `ntmofa-2023-12`, `ntmofa-2024-13`, `ntmofa-2024-14` |
| `museum_reported_treatment` | `["cleaning", "restoration_as_reported"]` | 7 | `nmh-2021-26`, `nmh-2021-27`, `nmh-2022-28`, `nmh-2022-29`, `nmh-2023-30`, `nmh-2023-31`, `nmh-2024-33` |
| `museum_reported_treatment` | `["cleaning"]` | 1 | `nmh-2020-16` |
| `museum_reported_treatment` | `["restoration_as_reported"]` | 67 | `nmh-2020-15`, `nmh-2021-17`, `nmh-2021-18`, `nmh-2021-19`, `nmh-2022-20`, `nmh-2022-21`, `nmh-2022-22`, `nmh-2023-23`, `nmh-2023-24`, `nmh-2023-25`, `nmh-2024-32`, `nmh-2025-34`, `ntmofa-2020-1`, `ntmofa-2021-2`, `ntmofa-2022-3`, `ntmofa-2023-4`, `ntmofa-2024-5`, `ntmofa-2025-6`, `sshm-2021-ceramic-repair`, `KHM-2024-treatment-objects-as-reported`, `KHM-2024-treatment-project-cases`, `KMFA-2024-existing-collection-restoration`, `KMFA-2025-existing-collection-restoration`, `NPM-2020-annual-books`, `NPM-2020-annual-paintings`, `NPM-2020-annual-objects`, `NPM-2020-annual-textiles`, `NPM-2021-annual-books`, `NPM-2021-annual-paintings`, `NPM-2021-annual-objects`, `NPM-2021-annual-textiles`, `NPM-2022-annual-books`, `NPM-2022-annual-paintings`, `NPM-2022-annual-objects`, `NPM-2022-annual-textiles`, `NPM-2023-annual-books`, `NPM-2023-annual-paintings`, `NPM-2023-annual-objects`, `NPM-2023-annual-textiles`, `NPM-2024-annual-books`, `NPM-2024-annual-paintings`, `NPM-2024-annual-objects`, `NPM-2024-annual-textiles`, `NPM-2021-vdr2025-books`, `NPM-2021-vdr2025-paintings`, `NPM-2021-vdr2025-objects`, `NPM-2021-vdr2025-textiles`, `NPM-2022-vdr2025-books`, `NPM-2022-vdr2025-paintings`, `NPM-2022-vdr2025-objects`, `NPM-2022-vdr2025-textiles`, `NPM-2023-vdr2025-books`, `NPM-2023-vdr2025-paintings`, `NPM-2023-vdr2025-objects`, `NPM-2023-vdr2025-textiles`, `NPM-2024-vdr2025-books`, `NPM-2024-vdr2025-paintings`, `NPM-2024-vdr2025-objects`, `NPM-2024-vdr2025-textiles`, `NPM-2025-finalaccounts-books`, `NPM-2025-finalaccounts-paintings`, `NPM-2025-finalaccounts-objects`, `NPM-2025-finalaccounts-textiles`, `yilan-2022-conservation15`, `TNAM-2020-refugee-project-scope`, `KHM-2021-treatment-items-as-reported`, `KHM-2022-yongxingle-script-treatment-volumes` |
| `museum_reported_treatment_component` | `["restoration_as_reported"]` | 1 | `KMFA-2023-oil-painting-restoration` |
| `physical_restoration` | `["restoration_as_reported"]` | 3 | `nmp-2023-plank-boats`, `nmp-2024-pottery-restoration`, `nmp-2025-artwork-restoration` |
| `preventive_collection_maintenance` | `["maintenance"]` | 1 | `yilan-2023-stability-maintenance133` |
| `preventive_conservation_as_reported` | `["maintenance"]` | 10 | `NPM-2020-annual-preventive-north`, `NPM-2020-annual-preventive-south`, `NPM-2021-annual-preventive-north`, `NPM-2021-annual-preventive-south`, `NPM-2022-annual-preventive-north`, `NPM-2022-annual-preventive-south`, `NPM-2023-annual-preventive-north`, `NPM-2023-annual-preventive-south`, `NPM-2024-annual-preventive-north`, `NPM-2024-annual-preventive-south` |
| `preventive_conservation_operations` | `["maintenance"]` | 7 | `sshm-2021-fumigation-reported`, `north4-sshm-2022-fumigation`, `sshm-2023-fumigation-reported`, `sshm-2024-collection-fumigation`, `sshm-2024-loan-fumigation`, `sshm-2025-collection-fumigation`, `sshm-2025-loan-fumigation` |
| `preventive_packaging_as_reported` | `["maintenance"]` | 1 | `DRAMA-2022-acid-free-packaging` |
| `preventive_pest_treatment` | `["maintenance"]` | 1 | `LYM-2020-inbound-exhibit-freezing` |
| `project_book_conservation` | `["restoration_as_reported"]` | 1 | `tfam-2024-project_book_conservation` |
| `project_paper_conservation` | `["restoration_as_reported"]` | 1 | `tfam-2024-project_paper_conservation` |
| `project_restoration` | `["restoration_as_reported"]` | 1 | `tfam-2025-project_restoration` |
| `restoration_as_reported` | `["maintenance", "restoration_as_reported"]` | 1 | `LYM-2025-gazetteer-conservation` |
| `restoration_as_reported` | `["restoration_as_reported"]` | 7 | `yingge-2020-source-reported-annual-repair`, `tfam-2020-oil_project_phase2`, `tfam-2020-oil_project_two_completed`, `tfam-2021-outsourced_restoration-html`, `tfam-2022-display_treatment`, `tfam-2022-exhibition_collection_restoration`, `tfam-2022-new_collection_exhibition_treatment` |
| `restoration_as_reported_including_cleaning` | `["restoration_as_reported"]` | 1 | `yingge-2021-reported-annual-repair` |
| `restoration_as_reported_with_scientific_examination_context` | `["restoration_as_reported"]` | 1 | `tfam-2020-oil_painting_restoration_annual` |
| `restoration_summary` | `["restoration_as_reported"]` | 1 | `tfam-2024-restoration_summary` |
| `routine_conservation` | `["maintenance", "restoration_as_reported"]` | 1 | `tfam-2025-routine_conservation` |
| `scientific_examination` | `["scientific_examination"]` | 2 | `nmp-2025-xrf-archaeology`, `nmp-2025-xrf-ethnology` |
| `treatment_batch` | `["restoration_as_reported"]` | 1 | `north4-daxi-2024-repair-batch` |
| `保存維護` | `["maintenance"]` | 5 | `NMTL-2020-maintenance`, `NMTL-2021-maintenance`, `NMTL-2022-maintenance`, `NMTL-2023-maintenance`, `NMTL-2025-maintenance` |
| `修護及保存維護混合` | `["maintenance", "restoration_as_reported"]` | 2 | `TNAM-2022-completed`, `TNAM-2022-under-treatment` |
| `原報年度修護與維護混合業務量` | `["maintenance", "mixed_workflow", "restoration_as_reported"]` | 3 | `ntm-reread-2023-accounts-reported-completed`, `ntm-reread-2024-accounts-reported-completed`, `ntm-reread-2025-accounts-reported-completed` |
| `原報摘要合計_混合單位疑義` | `["restoration_as_reported"]` | 1 | `NMTL-2025-reported-summary-total` |
| `原報標籤衝突_不得作修復量` | `["restoration_as_reported"]` | 1 | `NMTL-2024-summary-family-label` |
| `原報混合修護維護及檢測表` | `["mixed_workflow", "restoration_as_reported"]` | 1 | `ntm-2022-mixed-table-total` |
| `原報混合修護維護表` | `["mixed_workflow", "restoration_as_reported"]` | 2 | `ntm-2020-mixed-table-total`, `ntm-2021-mixed-table-total` |
| `原報混合合計_不可作修復總數` | `["mixed_workflow", "restoration_as_reported"]` | 1 | `TNAM-2024-reported-composite-total` |
| `原報混合年度合計` | `["restoration_as_reported"]` | 1 | `TNAM-2023-reported-total` |
| `原報藏品修護年度合計（含不同處置）` | `["maintenance", "mixed_workflow", "restoration_as_reported", "stabilization"]` | 4 | `NMTH-2020-conservation-reported-total`, `NMTH-2022-conservation-reported-total`, `NMTH-2023-conservation-reported-total`, `NMTH-2024-conservation-reported-total` |
| `基礎修復_含多種處理` | `["cleaning", "restoration_as_reported"]` | 4 | `NMTL-2020-basic-repair`, `NMTL-2021-basic-repair`, `NMTL-2022-basic-repair`, `NMTL-2023-basic-repair` |
| `完整修護（原表分類）` | `["restoration_as_reported"]` | 4 | `NMTH-2020-full-treatment`, `NMTH-2022-full-treatment`, `NMTH-2023-full-treatment`, `NMTH-2024-full-treatment` |
| `展覽修護` | `["restoration_as_reported"]` | 1 | `TNAM-2025-exhibition-treatment` |
| `展覽修護專案` | `["restoration_as_reported"]` | 1 | `TNAM-2024-exhibition-project` |
| `展覽館外作品緊急維護` | `["maintenance"]` | 1 | `TNAM-2023-exhibition-emergency` |
| `底片修護` | `["restoration_as_reported"]` | 1 | `NMTL-2025-film-treatment` |
| `底片修護及數位化混合` | `["digitization", "mixed_workflow", "restoration_as_reported"]` | 1 | `NMTL-2024-film-treatment` |
| `損傷修護_含清潔與加固等` | `["restoration_as_reported"]` | 1 | `ntm-2020-damage-treatment` |
| `損傷修護_含除塵除蟲害除標記` | `["restoration_as_reported"]` | 1 | `ntm-2021-damage-treatment` |
| `整飭資料筆數_非修復` | `["arrangement"]` | 2 | `NMTL-2024-collection-arrangement`, `NMTL-2025-collection-arrangement` |
| `文物修護` | `["restoration_as_reported"]` | 1 | `NMTL-2025-collection-treatment` |
| `文獻整飭_非純修復` | `["arrangement"]` | 1 | `NMTL-2024-family-arrangement` |
| `日常維護（原表分類）` | `["maintenance"]` | 4 | `NMTH-2020-routine-maintenance`, `NMTH-2022-routine-maintenance`, `NMTH-2023-routine-maintenance`, `NMTH-2024-routine-maintenance` |
| `書畫修護_含重新裝潢` | `["mounting", "restoration_as_reported"]` | 2 | `NMTL-2020-calligraphy-treatment`, `NMTL-2022-calligraphy-treatment` |
| `書畫修護_館內外混合` | `["restoration_as_reported"]` | 1 | `NMTL-2023-mixed-calligraphy` |
| `清潔修護與檢登數位化混合計畫` | `["cleaning", "digitization", "inspection_registration", "mixed_workflow", "restoration_as_reported"]` | 3 | `NMTH-2021-film-pieces`, `NMTH-2021-film-reels`, `NMTH-2021-film-titles` |
| `特定計畫完成修護_含檢視影像科學分析` | `["restoration_as_reported"]` | 1 | `ntm-2022-puppet-project-completed` |
| `緊急加固（原表分類）` | `["stabilization"]` | 4 | `NMTH-2020-emergency-stabilization`, `NMTH-2022-emergency-stabilization`, `NMTH-2023-emergency-stabilization`, `NMTH-2024-emergency-stabilization` |
| `館內修護` | `["restoration_as_reported"]` | 1 | `TNAM-2024-internal-treatment` |
| `館內與展覽混合修護` | `["restoration_as_reported"]` | 1 | `TNAM-2021-internal-exhibition-completed` |
| `館內藏品維護` | `["maintenance"]` | 1 | `TNAM-2023-collection-maintenance` |
| `館外受託修護` | `["restoration_as_reported"]` | 4 | `TNAM-2021-external-service`, `TNAM-2023-external-service`, `TNAM-2024-external-service`, `TNAM-2025-external-service` |
| `館外書畫修護` | `["restoration_as_reported"]` | 1 | `NMTL-2024-family-calligraphy` |
| `館外館群修護` | `["restoration_as_reported"]` | 1 | `NMTL-2023-family-museum-treatment` |
| `館藏修復與維護` | `["maintenance", "restoration_as_reported"]` | 1 | `NMTL-2022-collection-treatment` |
| `館藏修護` | `["restoration_as_reported"]` | 4 | `NMTL-2020-collection-treatment`, `NMTL-2023-collection-treatment`, `NMTL-2024-collection-treatment`, `NMTL-2024-fire-damaged-manuscripts` |
| `館藏修護_含重新裝潢` | `["mounting", "restoration_as_reported"]` | 1 | `NMTL-2021-collection-treatment` |
| `館藏動產修護` | `["restoration_as_reported"]` | 1 | `NMTH-2025-wall-panels-completed` |
