# 資料樣貌

版本：0.13.0。以下挑選不同資料型態，示範如何閱讀；不是隨機抽樣或可相加的統計表。

|型態|館所｜資料年／期間|原報作業|原數字與量詞|如何閱讀|回查來源|
|---|---|---|---|---|---|
|原報精確數字|國立臺灣歷史博物館｜2020|完整修護|7 件|「完整修護」是作業分類，不能只憑名稱認定已完成。|[逐筆資料](records/NMTH-2020-full-treatment.json)／[官方PDF第79頁](https://file.moc.gov.tw/Download.ashx?u=LzAwMS9VcGxvYWQvT2xkRmlsZXMvQWRtaW5VcGxvYWRzL2ZpbGVzLzIwMjIxMi82Njg2MWI2MS1kYzlmLTRkZDMtOGE0YS01NDA0MzRkNzBlZDMucGRm&n=5ZyL56uL6Ie654Gj5q235Y%2by5Y2a54mp6aSoMjAyMOW5tOWgsS5wZGY%3d#page=79)|
|來源明列零|國立臺灣歷史博物館｜2023|緊急加固|0 件|只有來源明列且確認語義的零才記0；未查到的數字保留未知。|[逐筆資料](records/NMTH-2023-emergency-stabilization.json)／[官方PDF第82頁](https://file.moc.gov.tw/Download.ashx?u=LzAwMS9VcGxvYWQvNTI4L3JlbGZpbGUvMTM3NzYvMjIyNTAwLzRmODgwNjQ5LTk0ODMtNDY2MS1iZWY3LWMwODc0MDNkMzcwZS5wZGY%3d&n=5bm05aCxMjAyMy3pm7vlrZDniYgo5ZCr5bCB6Z2iKS5wZGY%3d#page=82)|
|原報近似量|客家文化發展中心｜2024|藏品之整飭建檔與登錄|300餘 件|保留「餘」等原字串，精確數值欄留空，不改成整數300。|[逐筆資料](records/thcdc-2024-arrangement-registration.json)／[官方PDF第11頁](https://thcdc.hakka.gov.tw/media/tefb15j2/113%E5%B9%B4%E5%BA%A6%E6%B1%BA%E7%AE%97.pdf?mediaDL=true#page=11)|
|原報雙單位|桃園市立大溪木藝生態博物館｜2025|本館藏品數位化暨整飭修護案完成量|463組（715件）|同一原句的兩種單位一起保留，不拆配成兩筆獨立工作量。|[逐筆資料](records/daxi-2025-combined-project.json)／[官方PDF第10頁](https://ws.tycg.gov.tw/001/Upload/86/relfile/13658/997426/a149063e-9704-41bb-b0f6-63d91faa41d2.pdf#page=10)|
|案數|高雄市立歷史博物館｜2024|完成修復案|5 案|同年件、案、項各有原報範圍，不互換、不相加。|[逐筆資料](records/KHM-2024-treatment-project-cases.json)／[官方PDF第44頁](https://cissearch.kcc.gov.tw/Upload/Attachment/Proposal/138582/9d920ab0-b661-4da4-98c3-2e9c33c88284.pdf#page=44)|
|文物件數|高雄市立歷史博物館｜2024|完成修復案|24 件|同年件、案、項各有原報範圍，不互換、不相加。|[逐筆資料](records/KHM-2024-treatment-objects-as-reported.json)／[官方PDF第44頁](https://cissearch.kcc.gov.tw/Upload/Attachment/Proposal/138582/9d920ab0-b661-4da4-98c3-2e9c33c88284.pdf#page=44)|
|工作項數|高雄市立歷史博物館｜2024|典藏文物修復及維護工作|22 項|同年件、案、項各有原報範圍，不互換、不相加。|[逐筆資料](records/KHM-2024-conservation-work-items.json)／[官方PDF第52頁](https://cissearch.kcc.gov.tw/Upload/Attachment/Proposal/138582/9d920ab0-b661-4da4-98c3-2e9c33c88284.pdf#page=52)|
|跨年期間|國立臺灣史前文化博物館｜2020-2022|考古學整飭|5,910 件|保留原報期間，不平均分配到各年度。|[逐筆資料](records/nmp-2020-2022-archaeology-arrangement.json)／[官方PDF第27頁](https://file.moc.gov.tw/Download.ashx?u=LzAwMS9VcGxvYWQvNDk3L3JlbGZpbGUvMTE1NjkvMTc0NDU0LzI0NWQ0YTQ1LWY5OGQtNDVmNy1iMTI2LWM2Y2M1ZmRkM2RkNi5wZGY%3d&n=MjAyMC0yMDIy5bm05aCxKOS4reaWhykucGRm#page=27)|
|程式推算|臺北市立美術館｜2023|館內自行修護|程式推算 30 件|另標計算依據，不能當作原報總數。|[逐筆資料](records/tfam-2023-internal-derived.json)／[官方PDF第61頁](https://www.tfam.museum/AnnualReport/2023/2023tfam_annualreport_ch.pdf#page=61)|
|官方網頁|臺北市立美術館｜2021|因應展示整理|2 件|依網頁的年度段落定位，不借用其他PDF的頁碼。|[逐筆資料](records/tfam-2021-display_arrangement-html.json)／[官方網頁](https://www.tfam.museum/Common/editor.aspx?id=39)|

每筆完整資料還保留完成狀態、對象範圍、來源版次與雜湊。近似量或雙單位的精確數值欄留空，是保留不確定性。

[依館所查找](README.md)｜[全部CSV資料](../data/observations.csv)｜[欄位說明](../docs/DATA_DICTIONARY.md)

