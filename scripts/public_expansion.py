"""Additional public candidates and non-annual source context, outside the frozen baseline."""
import hashlib,json,re

def roster_rows(inventory):
    return (inventory['baseline_71_organizations'] + inventory['supplemental_14_organization_candidates']
            + inventory['additional_13_public_facility_candidates']
            + inventory.get('expanded_public_organization_candidates', []))

def validate_context(root, facts, inventory, shape):
    path=root/'data/public_context_notes.json'
    if not path.exists():
        assert not inventory.get('expanded_public_organization_candidates'), 'public_context_file_missing'
        return []
    rows=json.loads(path.read_text());schema=json.loads((root/'schema/public_context_note.schema.json').read_text())
    orgs={r.get('source_inventory_id',r.get('source_facility_inventory_id')) for r in roster_rows(inventory)}
    sources={s['source_id']:s for s in facts['sources']}
    assert len({r['note_id'] for r in rows})==len(rows), 'context_duplicate_id'
    for r in rows:
        shape(r,schema,r['note_id'])
        assert r['organization_id'] in orgs and r['source_id'] in sources, 'context_scope_reference'
        assert r['source_locator'].strip() and r['statement_as_reported'].strip()
        assert len(r['statement_as_reported'])<=180, 'context_quote_too_long'
        if sources[r['source_id']]['original_file_type']=='HTML':
            assert r['pdf_page_1_based'] is None and r['printed_page'] is None
        else:
            assert isinstance(r['pdf_page_1_based'],int) and r['pdf_page_1_based']>0
        text=json.dumps(r,ensure_ascii=False)
        assert not re.search(r'/Users/|file://|drive\.google\.com|localhost|127\.0\.0\.1',text), 'context_private_path'
    return rows
