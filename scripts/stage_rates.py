#!/usr/bin/env python3
"""Recompute the fixed v0.18.0 review-cell snapshot using public Git history only."""
import argparse
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import subprocess

PINS = {
    "v0.18.0": "0231eb69cddf2cf49047d46810547afaf1280702",
    "v0.5.1": "daf89020c1e8c2cbde1b41b76f113e72bb55b7de",
    "v0.6.0": "91d2ad74af525d9d2482b180130b27a201b172b7",
}
NUMERIC = "numeric_observations_verified"
NO_QUANTITY = "body_read_no_eligible_quantity_located"
POPULATION = "reviewed_2020_2025_cohort"
LABELS = {
    "v0.5.1_observation_organization_ids_15": "v0.5.1 observations 中的15個館所ID",
    "workflow_batch2_to_6": "BATCH2–6工作集合",
    "taoyuan_and_gold_followup_ids": "桃園市立美術館／新北市立黃金博物館",
    "npm": "國立故宮博物院",
    "ntnu_attached_art_museum": "國立臺灣師範大學美術館",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def percent(numerator, denominator):
    if not denominator:
        return None
    value = Decimal(numerator) * 100 / Decimal(denominator)
    return str(value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def has_numeric(cell):
    return NUMERIC in cell["review_statuses"]


def summarize(rows):
    numerator = sum(map(has_numeric, rows))
    return {
        "denominator_reviewed_organization_year_cells": len(rows),
        "numerator_any_numeric_cells": numerator,
        "percent_any_numeric": percent(numerator, len(rows)),
        "organizations": len({row["organization_id"] for row in rows}),
        "state_counts": dict(sorted(Counter(row["coverage_state"] for row in rows).items())),
        "cell_ids": sorted(row["coverage_cell_id"] for row in rows),
    }


def generate(repo):
    manifest = []

    def git(*parts):
        return subprocess.check_output(["git", "-C", str(repo), *parts])

    for tag, commit in PINS.items():
        require(git("rev-parse", f"{tag}^{{commit}}").decode().strip() == commit,
                f"Pinned public tag changed or is unavailable: {tag}")

    def read_json(path, tag="v0.18.0"):
        commit = PINS[tag]
        raw = git("show", f"{commit}:{path}")
        manifest.append({"tag": tag, "commit": commit, "path": path,
                         "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        return json.loads(raw)

    coverage = read_json("metadata/coverage.json")
    annotations = read_json("data/absence_annotations.json")
    vocabulary = read_json("metadata/absence_vocabulary.json")
    dimensions = read_json("metadata/organization_dimensions.json")
    early_facts = read_json("data/facts.json", "v0.5.1")
    npm_followup = read_json("data/facts.json", "v0.6.0")
    cells = [cell for cell in coverage["cells"] if POPULATION in cell["populations"]]
    require(len({cell["coverage_cell_id"] for cell in cells}) == len(cells), "Duplicate cells")
    require(all(2020 <= cell["target_data_year"] <= 2025 and cell["review_ids"] for cell in cells),
            "Unexpected year or unreviewed cell")
    total = summarize(cells)
    require((len(cells), sum(map(has_numeric, cells))) == (487, 104), "Unexpected fixed cohort")
    require(total["state_counts"]["numeric_only"] == 103, "Numeric-only is not any-numeric")
    population = next(row for row in coverage["populations"] if row["population_id"] == POPULATION)
    require(population["denominator_cells"] == len(cells) and
            population["cells_with_any_verified_observation_review"] == sum(map(has_numeric, cells)),
            "Coverage summary mismatch")
    require(total["state_counts"] == {key: value for key, value in population["state_counts"].items() if value},
            "Coverage states mismatch")

    early_ids = {row["organization_id"] for row in early_facts["observations"]}
    require(len(early_ids) == 15, "Early subset must use observations, not body_reviews")
    predicates = {
        "v0.5.1_observation_organization_ids_15": lambda row: row["organization_id"] in early_ids,
        "workflow_batch2_to_6": lambda row: row["working_category_membership_set"] in
            {f"BATCH{number}" for number in range(2, 7)},
        "taoyuan_and_gold_followup_ids": lambda row: row["organization_id"] in {"SUP-002", "BASE-039"},
        "npm": lambda row: row["organization_id"] == "BASE-023",
        "ntnu_attached_art_museum": lambda row: row["organization_id"] == "EXP-001",
    }
    require(all(sum(predicate(row) for predicate in predicates.values()) == 1 for row in cells),
            "The five post-hoc subsets must be disjoint and complete")
    phases = {key: summarize([row for row in cells if predicate(row)]) for key, predicate in predicates.items()}
    require([(row["denominator_reviewed_organization_year_cells"], row["numerator_any_numeric_cells"])
             for row in phases.values()] == [(85, 69), (378, 25), (12, 4), (6, 6), (6, 0)],
            "Unexpected fixed stage counts")

    def group_by(key):
        groups = {value: summarize([row for row in cells if row[key] == value])
                  for value in sorted({row[key] for row in cells})}
        require(sum(row["denominator_reviewed_organization_year_cells"] for row in groups.values()) == len(cells)
                and sum(row["numerator_any_numeric_cells"] for row in groups.values()) == sum(map(has_numeric, cells)),
                f"Incomplete dimension: {key}")
        require("unknown" in groups, f"Unknown must remain explicit: {key}")
        return groups

    require(not any(row["organization_id"] == "BASE-023" for key in ("observations", "body_reviews")
                    for row in early_facts[key]), "Unexpected v0.5.1 NPM history")
    require(all(any(row["organization_id"] == "BASE-023" for row in npm_followup[key])
                for key in ("observations", "body_reviews")), "Unexpected v0.6.0 NPM history")
    annotation_cells = {f"{row['organization_id']}::{row['target_data_year']}" for row in annotations}
    n_cells = {row["coverage_cell_id"] for row in cells if NO_QUANTITY in row["review_statuses"]}
    statuses = dict(sorted(Counter(row["classification_status"] for row in annotations).items()))
    require(len(annotations) == 283 and len(annotation_cells) == 277 and annotation_cells == n_cells,
            "Annotation records and distinct N cells differ from the pinned snapshot")
    require(statuses == {"insufficient_detail": 1, "supported_by_review_note": 282},
            "Unexpected annotation support counts")
    require(all(row["not_institutional_nonpublication"] for row in annotations),
            "Annotations must not imply institutional nonpublication")
    return {
        "snapshot_schema_version": "1.0",
        "source_tag": "v0.18.0", "source_commit": PINS["v0.18.0"],
        "source_dataset_version": coverage["dataset_version"], "source_as_of": coverage["as_of"],
        "source_manifest": manifest,
        "population_rule": f"coverage.cells populations contains {POPULATION}; organization_id x target_data_year",
        "numeric_rule": "One cell counts once when review_statuses contains numeric_observations_verified; mixed states retained; no quantities added.",
        "total": total, "phase_subsets_evaluated_at_v018": phases,
        "phase_partition_complete_and_disjoint": True,
        "early_15_definition": "Distinct organization_id in v0.5.1 facts.observations; not all body_review organizations.",
        "early_15_organization_ids": sorted(early_ids),
        "batch_details": {f"BATCH{number}": summarize([row for row in cells if
                          row["working_category_membership_set"] == f"BATCH{number}"])
                          for number in range(2, 7)},
        "admin_groups": group_by("admin_group"), "island_groups": group_by("island_group"),
        "dimensions_scope": dimensions["classification_scope"],
        "mixed_cells": [{"cell_id": row["coverage_cell_id"], "review_statuses": row["review_statuses"],
                         "counts_as_any_numeric": has_numeric(row)} for row in cells
                        if row["coverage_state"] == "mixed_current_states"],
        "npm_history_check": {"absent_from_v051_observations_and_body_reviews": True,
                              "present_in_v060_observations_and_body_reviews": True,
                              "limit": "Only the two pinned tags were compared; no exhaustive history search."},
        "absence_annotations": {"records": len(annotations), "distinct_organization_year_cells": len(annotation_cells),
                                "classification_status_counts": statuses, "evidence_basis": vocabulary["evidence_basis"],
                                "criteria_version": vocabulary["criteria_version"],
                                "all_not_institutional_nonpublication": True},
        "limits": [
            "Historical fixed public-package snapshot; no new official-source or human re-reading.",
            "Post-hoc workflow subsets, not a sampling design or representative museum population.",
            "Organization-year cells are not counts of museums, objects, annual operations, or national disclosure rates.",
            "Administrative and island groups are separate recorded mappings; unknown is retained.",
            "No quantity or missing review does not mean no work, zero, no source, or institutional nonpublication.",
            "Annotation support is from existing public review notes, not new independent source verification.",
        ],
        "reproduction": {"command": "python3 scripts/stage_rates.py --check",
                         "requires": "Python 3 standard library, Git, and the three pinned public history tags; unavailable tags fail closed."},
    }


def render_note(result):
    def line(label, row):
        return (f"| {label} | {row['numerator_any_numeric_cells']} | "
                f"{row['denominator_reviewed_organization_year_cells']} | {row['percent_any_numeric']}% |")

    lines = ["# v0.18.0分階段工作集合的館年格比例", "",
             f"固定公開基線：`v0.18.0`／`{PINS['v0.18.0']}`，資料截至{result['source_as_of']}。", "",
             "這是歷史版本快照，五組以既有工作歷程事後辨識，全部採v0.18.0的館年格狀態；不是各階段當時的成功率、新增量或前後成效比較。", "",
             "分母是2020–2025已有有界查核的organization_id × 目標年格；分子是review_statuses含numeric_observations_verified的格，每格計一次，不加總修護數量。館年格不是館數。", "",
             "| 可重建工作集合（皆採v0.18.0狀態） | 含已核數值格 | 已查核館年格 | 比例 |",
             "|---|---:|---:|---:|", line("全部", result["total"])]
    lines += [line(LABELS[key], row) for key, row in result["phase_subsets_evaluated_at_v018"].items()]
    lines += ["", "五組完整且互斥地分割487格，分子合計104。早期15館只取v0.5.1的facts.observations中互異organization_id；不混入只出現於body_reviews的館。故宮在比較的v0.5.1觀測及查核均無紀錄，v0.6.0兩者已有紀錄；這只核對兩個既有標籤。", "",
              "工作批次不是官方館類或抽樣設計。早期15館由已有觀測的ID界定，本來就帶有選入差異；BATCH2–6的6.613757%只能描述這378個已查核館年格，不能代表一般館所或全國公開率。", "",
              "numeric_only有103格；故宮2025混合狀態格仍含numeric標記，因此any numeric為104格。桃園2024的N與P混合格沒有numeric標記，不計分子。", "",
              "## 行政與島群映射", "",
              "| 分開的維度 | 含已核數值格 | 已查核館年格 | 比例 |", "|---|---:|---:|---:|"]
    for key, label in (("admin_groups", "行政映射"), ("island_groups", "島群映射")):
        lines += [line(f"{label}：{group}", row) for group, row in result[key].items()]
    lines += ["", "中央／地方與島群是兩個維度，不能把離島當作與中央、地方互斥的第三類。unknown各自保留。行政分類是既有權管文字映射，島群是名錄／權管行政區，不代表全部分館或藏品位置。", "",
              "## 缺量註記與證據限制", "",
              "283則N註記對應277個含N的館年格；282則由既有公開review note文字支持分類，1則資訊不足。這不是本輪獨立覆讀官方原件或人類抽樣核讀。未定位適用數量、未定位來源或缺少查核紀錄，均不能推論未做、零或機構未公開。", "",
              "本次重算只讀公開Git固定位元組，沒有新查來源、修改觀測或新增人類覆核結果。", "",
              "## 重跑", "",
              "需有Python 3、Git及三個既有公開標籤的歷史；只下載發行ZIP而未取得Git歷史時不能重跑。缺標籤或與固定commit不符即停止。", "",
              "```sh", "python3 scripts/stage_rates.py", "python3 scripts/stage_rates.py --check", "```", "",
              "第一式只更新本說明及[分階段結果](../metadata/stage_rates_v018.json)；第二式重新計算並逐位元組核對這兩份產物，不寫檔。可用--repo指定另一份含相同公開歷史的checkout。輸入SHA-256、commit、格ID與各批次明細均留在結果檔；不依賴私人資料或其他評估資料夾。"]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true", help="Recompute and compare without writing")
    args = parser.parse_args()
    repo = args.repo.resolve()
    result = generate(repo)
    outputs = {repo / "metadata/stage_rates_v018.json": json.dumps(result, ensure_ascii=False, indent=2) + "\n",
               repo / "docs/STAGE_RATES_V018.md": render_note(result)}
    for path, content in outputs.items():
        if args.check:
            require(path.is_file() and path.read_bytes() == content.encode("utf-8"),
                    f"Generated output differs: {path.name}")
        else:
            path.write_text(content, encoding="utf-8")
    print(json.dumps({"source_commit": PINS["v0.18.0"], "reviewed_cells": 487,
                      "any_numeric_cells": 104, "phase_partition_verified": True,
                      "outputs": [str(path.relative_to(repo)) for path in outputs],
                      "check": args.check}, ensure_ascii=False))


if __name__ == "__main__":
    main()
