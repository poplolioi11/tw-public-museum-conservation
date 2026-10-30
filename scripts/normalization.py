#!/usr/bin/env python3
"""Conservative search aliases for existing observations; no quantity outputs.

The source facts and classify_facets remain authoritative.  Inventories lock the
reviewed raw-value/observation membership; they do not reclassify observations.
All public output is deterministic and uses the Python standard library.
"""
import argparse
import hashlib
import json
from pathlib import Path

try:
    from . import classify_facets
except ImportError:
    import classify_facets

RULE_VERSION = "1.0"
CLASSIFICATION_RULE_VERSION = "1.2"
OBSERVATION_DIGEST_ALGORITHM = "sha256-canonical-json-utf8-ordered-observations-v1"
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
RAW_FIELDS = ("metric_class", "completion_status", "unit_as_reported")
FALSE_FLAGS = ("default_aggregation_allowed", "cross_museum_comparable",
               "unique_object_count_verified", "year_on_year_ready")
ACTION_PROJECTION = {
    "restoration_as_reported": "reported_restoration",
    "maintenance": "preventive_maintenance",
    "arrangement": "arrangement_inventory",
    "inspection_registration": "inspection_examination",
    "scientific_examination": "inspection_examination",
    "digitization": "digitization",
    "digital_restoration": "digital_restoration",
    "cleaning": "cleaning",
    "stabilization": "stabilization",
    "mounting": "mounting",
    "mixed_workflow": "mixed_workflow",
    "needs_review": "needs_review",
}
UNIT_STATUSES = ("lexical_alias_only", "retained_as_reported",
                 "compound_not_convertible", "not_stated", "not_explicitly_stated")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _raw_key(value):
    return (value is not None, "" if value is None else value)


def _rows(facts):
    rows = facts["observations"] if isinstance(facts, dict) else facts
    _require(isinstance(rows, list), "observations must be an array")
    return rows


def _inventory(rows, field):
    values = {}
    for row in rows:
        values.setdefault(row[field], []).append(row["observation_id"])
    return {raw: sorted(ids) for raw, ids in values.items()}


def observation_digest(facts):
    """Fingerprint reviewed observations, including original quantities and order.

    Dataset summaries and source/body review metadata can be refreshed separately;
    changing any observation still requires an explicit reviewed-manifest update.
    """
    encoded = json.dumps(_rows(facts), ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _unit_target(raw):
    """A literal search alias is never a conversion or a counting definition."""
    if raw is None:
        return None, "not_stated"
    if raw == "未明列（原表僅標「數量」）":
        return None, "not_explicitly_stated"
    if raw in ("件", "件數", "件作品"):
        return "item_word", "lexical_alias_only"
    if raw in ("組（件）", "組、件"):
        return raw, "compound_not_convertible"
    return raw, "retained_as_reported"


def validate_rules(facts, rules):
    """Reject unknown raw values, drifted inventories, or noncanonical facets.

    Returns an audit summary on success and raises ValueError on failure.  A new
    source value needs an explicit inventory review before normalization can run.
    The stored canonical facets are checked against their one existing classifier;
    the normalizer never repairs or overwrites a discrepancy.
    """
    rows = _rows(facts)
    _require(set(rules) == {
        'normalization_rule_version', 'classification_rule_version', 'reviewed_observation_count',
        'reviewed_input_manifest',
        'canonical_aliases', 'canonical_authority', 'action_class_v2_projection',
        'action_projection_basis', 'proposed_unused_actions', 'unit_mapping_basis',
        'review_gate', 'limits', 'inventories'}, 'unknown or missing rule field')
    _require(set(rules['inventories']) == set(RAW_FIELDS), 'unknown inventory field')
    _require(rules["normalization_rule_version"] == RULE_VERSION,
             "unsupported normalization rule version")
    _require(rules["classification_rule_version"] == CLASSIFICATION_RULE_VERSION
             == classify_facets.RULE_VERSION, "classification rule version mismatch")
    _require(type(rules["reviewed_observation_count"]) is int and
             rules["reviewed_observation_count"] > 0 and
             len(rows) == rules["reviewed_observation_count"],
             "reviewed observation count changed")
    manifest = rules["reviewed_input_manifest"]
    _require(isinstance(manifest, dict) and set(manifest) == {
        "source", "dataset_version", "reviewed_observation_count", "observations_sha256",
    }, "unknown or missing reviewed input manifest field")
    _require(manifest["source"] == "data/facts.json", "reviewed input source changed")
    _require(isinstance(manifest["dataset_version"], str) and manifest["dataset_version"],
             "missing reviewed dataset version")
    _require(type(manifest["reviewed_observation_count"]) is int and
             manifest["reviewed_observation_count"] == rules["reviewed_observation_count"],
             "reviewed manifest observation count changed")
    digest = manifest["observations_sha256"]
    _require(isinstance(digest, str) and len(digest) == 64 and
             all(char in "0123456789abcdef" for char in digest),
             "invalid reviewed observations_sha256")
    if isinstance(facts, dict):
        _require(facts.get("dataset_version") == manifest["dataset_version"],
                 "reviewed dataset version changed")
    ids = [row["observation_id"] for row in rows]
    _require(len(set(ids)) == len(ids), "duplicate observation_id")
    _require(rules["canonical_aliases"] == {
        "metric_class_normalized": "action_categories",
        "completion_status_normalized": "completion_category",
    }, "canonical alias definitions changed")
    _require(rules["action_class_v2_projection"] == ACTION_PROJECTION,
             "action projection changed without a rule-version review")
    _require(set(ACTION_PROJECTION) == set(classify_facets.ACTION_LABELS),
             "canonical action vocabulary changed")
    _require(rules["proposed_unused_actions"] == [{
        "action_class": "initial_preparation", "status": "proposed_unused",
        "assigned_observation_ids": [],
        "rationale": "本清冊未將任何觀測判為初製；保存盒製作不等於文物初製。",
    }], "unused initial_preparation must not be assigned")
    counts = {}
    for field in RAW_FIELDS:
        entries = rules["inventories"][field]
        actual = _inventory(rows, field)
        _require(isinstance(entries, list) and len(entries) == len(actual),
                 field + " inventory count changed")
        indexed = {}
        for entry in entries:
            fields = {'mapping_id', 'raw_value', 'observation_ids'}
            if field == 'unit_as_reported':
                fields |= {'normalized_value', 'mapping_status', 'unit_alias_is_conversion'}
            _require(set(entry) == fields, 'unknown or missing mapping field')
            raw = entry["raw_value"]
            _require(raw not in indexed, field + " duplicate inventory value")
            _require(entry["observation_ids"] == sorted(set(entry["observation_ids"])),
                     field + " inventory ids must be unique and sorted")
            indexed[raw] = entry["observation_ids"]
            if field == "unit_as_reported":
                target, status = _unit_target(raw)
                _require(entry["normalized_value"] == target and
                         entry["mapping_status"] == status,
                         "unit rule changed without a rule-version review")
                _require(entry["unit_alias_is_conversion"] is False,
                         "unit alias cannot be a conversion")
        _require(indexed == actual, field + " unknown or changed inventory membership")
        counts[field] = len(actual)
    _require(observation_digest(facts) == manifest["observations_sha256"],
             "unreviewed observation content or order changed")
    for row in rows:
        label = row["observation_id"]
        expected = classify_facets.facets(row)
        for field in ("action_categories", "completion_category",
                      "classification_rule_version"):
            _require(row[field] == expected[field], label + " canonical facet drift: " + field)
        actions = row["action_categories"]
        _require(actions and len(actions) == len(set(actions)), label + " duplicate/empty actions")
        _require(set(actions) <= set(ACTION_PROJECTION), label + " unknown action")
        _require("needs_review" not in actions and row["completion_category"] != "needs_review",
                 label + " needs controller review before normalization")
        _require(row["completion_category"] in classify_facets.COMPLETION_LABELS,
                 label + " unknown completion category")
        for field in FALSE_FLAGS:
            _require(row[field] is False, label + " nonfalse comparison/aggregation flag")
    return {"observations": len(rows), "inventories": counts,
            "normalization_rule_version": RULE_VERSION,
            "classification_rule_version": CLASSIFICATION_RULE_VERSION,
            "unknown_rows": 0}


def normalize(facts, rules):
    """Return one quantity-free sidecar row per unchanged input observation."""
    validate_rules(facts, rules)
    unit_rules = {entry["raw_value"]: entry
                  for entry in rules["inventories"]["unit_as_reported"]}
    result = []
    for row in _rows(facts):
        unit = unit_rules[row["unit_as_reported"]]
        record = {
            "observation_id": row["observation_id"],
            "metric_class_original": row["metric_class"],
            "metric_class_normalized": list(row["action_categories"]),
            "completion_status_original": row["completion_status"],
            "completion_status_normalized": row["completion_category"],
            "unit_as_reported": row["unit_as_reported"],
            "unit_normalized": unit["normalized_value"],
            "unit_mapping_status": unit["mapping_status"],
            "unit_alias_is_conversion": False,
            "action_class_v2": sorted({rules["action_class_v2_projection"][action]
                                       for action in row["action_categories"]}),
            "normalization_rule_version": RULE_VERSION,
            "classification_rule_version": row["classification_rule_version"],
        }
        record.update({field: False for field in FALSE_FLAGS})
        _require(not any(key.startswith("quantity") for key in record),
                 "normalization cannot carry quantities")
        _require("initial_preparation" not in record["action_class_v2"],
                 "initial_preparation is proposed but unused")
        result.append(record)
    _require([r["observation_id"] for r in result] ==
             [r["observation_id"] for r in _rows(facts)], "sidecar membership/order drift")
    return result


def _cell(value):
    if value is None:
        return "`null`"
    return "`" + str(value).replace("|", "&#124;").replace("\n", "<br>").replace("`", "&#96;") + "`"


def _ids(rows):
    return ", ".join(_cell(row["observation_id"]) for row in rows)


def _groups(rows, field, canonical):
    groups = {}
    for row in rows:
        value = row[canonical]
        key = tuple(value) if isinstance(value, list) else value
        groups.setdefault((row[field], key), []).append(row)
    return sorted(groups.items(), key=lambda item: (_raw_key(item[0][0]), str(item[0][1])))


def build_outputs(facts, rules):
    """Return {package-relative path: UTF-8 bytes} for the three audited maps.

    One original metric value can occupy several rows when its existing canonical
    facet arrays differ.  These tables are derived reports, never mapping inputs.
    """
    sidecar = normalize(facts, rules)
    rows = _rows(facts)
    intro = ("本表由 `scripts/normalization.py` 的 `build_outputs(facts, rules)` 產生。"
             "規則版 `1.0`；既有分類規則版 `1.2`。\n\n"
             f"已審核 `data/facts.json` 版本 `{rules['reviewed_input_manifest']['dataset_version']}`，"
             f"觀測清冊 {rules['reviewed_observation_count']} 筆；"
             "輸入版本與逐列觀測 SHA-256 摘要見 `metadata/normalization_rules.json`。\n\n"
             "僅供搜尋與發現；未新增觀測、改寫原始欄位、拆配數量、換算或授予加總資格。"
             "各列依 `observation_id` 連回 `data/facts.json` 的原證據與來源定位。\n\n")
    metric = ["# 作業分類搜尋別名\n\n", intro,
              "`metric_class_original` 是既有歷史分類欄，並非館方原文；館方用語另存 `metric_as_reported`。"
              "`metric_class_normalized` 逐列直接複製既有 `action_categories` 陣列，"
              f"不能將 {len(rules['inventories']['metric_class'])} 種原分類硬映為 "
              f"{len(rules['inventories']['metric_class'])} 個單一作業。相同原分類可能有不同標籤組合。\n\n",
              "`action_class_v2` 是保留多標籤的搜尋投影；檢視／登錄與科學檢測共用搜尋值，"
              "細分類仍完整保留在 `metric_class_normalized` 與原觀測中。"
              "清潔、加固、裝裱、數位化、純數位修復及混合作業各自保留。\n\n",
              "| 既有作業標籤 | action_class_v2 |\n|---|---|\n"]
    for action, projected in rules["action_class_v2_projection"].items():
        metric.append(f"| {_cell(action)} | {_cell(projected)} |\n")
    metric.extend(["\n`needs_review` 留作詞彙，但本批候選若出現此值即拒絕。"
                   "`initial_preparation` 僅列為 `proposed_unused`，指派觀測為 0；"
                   "保存盒製作不判為文物初製。\n\n",
                   f"原分類清冊共 {len(rules['inventories']['metric_class'])} 值；以下按原值與逐列 canonical 標籤組合列示。\n\n",
                   "| metric_class 原值 | 原 action_categories（完整陣列） | 觀測列數 | observation_id |\n|---|---|---:|---|\n"])
    for (raw, actions), members in _groups(rows, "metric_class", "action_categories"):
        metric.append(f"| {_cell(raw)} | {_cell(json.dumps(actions, ensure_ascii=False))} | {len(members)} | {_ids(members)} |\n")
    completion = ["# 完成狀態搜尋別名\n\n", intro,
                  "`completion_status_normalized` 逐列直接複製既有 `completion_category`；"
                  "唯一完成文字映射來源是 `scripts/classify_facets.py` 的 `COMPLETION_MAP`，"
                  "不另維護第二份完成文字對照。未明載完成不等於未完成；"
                  "「完整修護」不推定完成，年度執行、父項脈絡、截點完成、活動已施作與進行中均分開。\n\n",
                  f"原值清冊共 {len(rules['inventories']['completion_status'])} 值。"
                  "未知新值或 `needs_review` 候選必須停止並覆核。\n\n",
                  "| completion_status 原值 | 既有 completion_category | 觀測列數 | observation_id |\n|---|---|---:|---|\n"]
    for (raw, category), members in _groups(rows, "completion_status", "completion_category"):
        completion.append(f"| {_cell(raw)} | {_cell(category)} | {len(members)} | {_ids(members)} |\n")
    units = ["# 量詞字面搜尋別名\n\n", intro,
             "只有 `件`、`件數`、`件作品` 使用 `item_word` 搜尋別名；"
             "它不定義計數對象、唯一物件或可比工作量。其餘明列量詞保留原詞。"
             "原值 `null` 及原文未明列量詞的 `unit_normalized` 保持 `null`，"
             "由 `unit_mapping_status` 區別原因，不能補成件數。\n\n",
             "`組件` 視為原詞，不拆字；`組（件）` 與 `組、件` 原樣保留且不換算。"
             "同批平行量詞不拆列相加。`unit_alias_is_conversion` 與四項加總／可比旗標固定為 `false`。\n\n",
             f"原值清冊共 {len(rules['inventories']['unit_as_reported'])} 值（含 `null`）。\n\n",
             "| unit_as_reported 原值 | unit_normalized | unit_mapping_status | 觀測列數 | observation_id |\n|---|---|---|---:|---|\n"]
    for entry in rules["inventories"]["unit_as_reported"]:
        members = [row for row in rows if row["unit_as_reported"] == entry["raw_value"]]
        units.append(f"| {_cell(entry['raw_value'])} | {_cell(entry['normalized_value'])} | {_cell(entry['mapping_status'])} | {len(members)} | {_ids(members)} |\n")
    _require(len(sidecar) == len(rows), "sidecar count mismatch")
    return {"docs/METRIC_CLASS_MAP.md": "".join(metric).encode("utf-8"),
            "docs/COMPLETION_STATUS_MAP.md": "".join(completion).encode("utf-8"),
            "docs/UNIT_MAP.md": "".join(units).encode("utf-8")}


def validate_boundaries(facts, rules):
    """Finite regression checks for reviewed semantic failure paths."""
    records = {r["observation_id"]: r for r in normalize(facts, rules)}
    original = {r["observation_id"]: r for r in _rows(facts)}
    checked = []

    def check(condition, message):
        _require(condition, message)
        checked.append(message)

    digital_ids = ("nmp-2022-digital-restoration",
                   "KFA-2022-digital-restoration-reported-quantity")
    for oid in digital_ids:
        check(records[oid]["action_class_v2"] == ["digital_restoration"],
                 oid + " pure digital restoration must stay separate")
    for oid in ("ntm-2021-mixed-table-total", "ntm-2022-mixed-table-total",
                "KFA-2022-digital-restoration-reported-quantity"):
        check(records[oid]["unit_normalized"] is None, oid + " missing unit was invented")
    for oid in ("daxi-2025-combined-project", "NTCRI-2023-finalaccounts-condition-inspection"):
        check(records[oid]["unit_normalized"] == original[oid]["unit_as_reported"] and
                 records[oid]["unit_mapping_status"] == "compound_not_convertible",
                 oid + " compound unit was converted")
    check(records["TNAM-2024-reported-composite-total"]["unit_normalized"] == "組件",
             "組件 must remain one literal unit")
    check(records["NMTH-2024-conservation-reported-total"]["completion_status_normalized"]
             == "annual_execution_not_explicit", "完整修護 cannot imply completed")
    check(records["TNAM-2022-completed"]["completion_status_normalized"] == "explicit_completed",
          "explicit completion was changed")
    check(records["TNAM-2022-under-treatment"]["completion_status_normalized"] == "in_progress",
          "under-treatment row was changed to completed")
    check(records["sshm-2021-fumigation-reported"]["unit_normalized"] == "次"
             and records["sshm-2021-fumigation-reported"]["completion_status_normalized"] == "performed_activity",
             "activity was changed to object count or completion")
    check("initial_preparation" not in records["yilan-2023-compound-maintenance26"]["action_class_v2"],
             "storage-box preparation cannot imply initial preparation")
    check(any(len(row["action_class_v2"]) > 1 for row in records.values()),
             "multilabel action projection collapsed")
    return {"boundary_checks": len(checked), "passed": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facts", type=Path, default=PACKAGE_ROOT / "data/facts.json")
    parser.add_argument("--rules", type=Path, default=PACKAGE_ROOT / "metadata/normalization_rules.json")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="verify the three generated tables")
    mode.add_argument("--write", action="store_true", help="regenerate the three tables only")
    args = parser.parse_args()
    facts = json.loads(args.facts.read_text(encoding="utf-8"))
    rules = json.loads(args.rules.read_text(encoding="utf-8"))
    summary = validate_rules(facts, rules)
    summary.update(validate_boundaries(facts, rules))
    outputs = build_outputs(facts, rules)
    for relative, content in outputs.items():
        target = PACKAGE_ROOT / relative
        if args.write:
            target.write_bytes(content)
        if args.check:
            _require(target.exists() and target.read_bytes() == content,
                     "generated map differs: " + relative)
    encoded = b"".join((json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
                       for row in normalize(facts, rules))
    summary["sidecar_sha256"] = hashlib.sha256(encoded).hexdigest()
    summary["generated_maps"] = sorted(outputs)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
