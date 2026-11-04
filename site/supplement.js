'use strict';
(() => {
  const form = document.getElementById('supplement-filter-form');
  if (!form) return;
  const controls = {
    search: document.getElementById('supplement-search'),
    layer: document.getElementById('supplement-layer'),
    organization: document.getElementById('supplement-organization'),
    kind: document.getElementById('supplement-kind'),
    year: document.getElementById('supplement-year')
  };
  const rows = [...document.querySelectorAll('[data-supplement-record]')];
  const institutions = [...document.querySelectorAll('[data-supplement-institution]')];
  const sections = [...document.querySelectorAll('[data-supplement-layer]')];
  const normalize = value => value.normalize('NFKC').toLocaleLowerCase('zh-Hant-TW');
  const haystacks = new Map([...rows, ...institutions].map(node => [node, normalize(node.textContent)]));
  function matches(node, includeRecordFields = true) {
    if (controls.layer.value && node.dataset.layer !== controls.layer.value) return false;
    if (controls.organization.value && node.dataset.organization !== controls.organization.value) return false;
    const terms = normalize(controls.search.value).trim().split(/\s+/u).filter(Boolean);
    if (terms.some(term => !haystacks.get(node).includes(term))) return false;
    if (includeRecordFields && controls.kind.value && node.dataset.kind !== controls.kind.value) return false;
    if (includeRecordFields && controls.year.value && node.dataset.year !== controls.year.value) return false;
    return true;
  }
  function apply() {
    let visible = 0;
    for (const row of rows) {
      row.hidden = !matches(row);
      if (!row.hidden) visible += 1;
    }
    for (const institution of institutions) institution.hidden = !matches(institution, false);
    for (const section of sections) {
      section.hidden = Boolean(controls.layer.value && section.dataset.supplementLayer !== controls.layer.value);
      const table = section.querySelector('.table-wrap');
      if (table) table.hidden = ![...table.querySelectorAll('[data-supplement-record]')].some(row => !row.hidden);
    }
    document.getElementById('supplement-result-count').textContent =
      `顯示 ${visible}／${rows.length} 則紀錄；列數不是物件量。館所清單依分層與館名文字顯示，作業年與類型只篩紀錄。`;
    document.getElementById('supplement-empty').hidden = visible > 0;
  }
  form.addEventListener('submit', event => event.preventDefault());
  for (const [key, control] of Object.entries(controls)) control.addEventListener(key === 'search' ? 'input' : 'change', apply);
  form.addEventListener('reset', () => {
    for (const control of Object.values(controls)) control.value = '';
    apply();
  });
  apply();
})();
