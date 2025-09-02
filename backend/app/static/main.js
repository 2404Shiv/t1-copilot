const $ = (sel) => document.querySelector(sel);

async function fetchHealth() {
  const res = await fetch('/health');
  return await res.json();
}
async function fetchBreaks() {
  const res = await fetch('/breaks?limit=5000');
  return await res.json();
}

function fmt(n) {
  return new Intl.NumberFormat('en-US', {maximumFractionDigits:2}).format(n);
}
function rowClass(sev) {
  const s = (sev || '').toLowerCase();
  if (s === 'high') return 'high';
  if (s === 'medium') return 'medium';
  return 'low';
}

function kpiSummary(items) {
  const k = { total: 0, nar: 0, byType: {} };
  for (const b of items) {
    k.total++;
    k.nar += (b.notional_usd || 0);
    k.byType[b.break_type] = (k.byType[b.break_type] || 0) + 1;
  }
  const parts = [
    `NAR: $${fmt(k.nar)}`,
    `Total breaks: ${fmt(k.total)}`,
    `Missing: ${fmt(k.byType.MissingConfirm||0)}`,
    `Late: ${fmt(k.byType.LateConfirm||0)}`,
    `Qty: ${fmt(k.byType.QuantityMismatch||0)}`,
    `Price: ${fmt(k.byType.PriceMismatch||0)}`,
    `Settle: ${fmt(k.byType.SettleDateMismatch||0)}`,
    `Account: ${fmt(k.byType.AccountMismatch||0)}`
  ];
  $('#kpis').innerText = parts.join('  ·  ');
}

function renderBreaks(items) {
  const tbody = $('#breaks tbody');
  tbody.innerHTML = '';
  for (const b of items) {
    const tr = document.createElement('tr');
    tr.className = rowClass(b.severity);
    tr.innerHTML = `
      <td>${new Date(b.created_at).toLocaleTimeString()}</td>
      <td>${b.trade_id}</td>
      <td>${b.break_type}</td>
      <td>${b.severity}</td>
      <td>${b.detail}</td>
      <td>${fmt(b.notional_usd)}</td>
      <td>${fmt(b.detected_ms)}</td>
    `;
    tbody.appendChild(tr);
  }
}

function toCSV(items) {
  const headers = ["created_at","trade_id","break_type","severity","detail","notional_usd","detected_ms"];
  const rows = [headers.join(",")];
  for (const b of items) {
    const r = [
      b.created_at,
      b.trade_id,
      b.break_type,
      b.severity,
      `"${String(b.detail||"").replace(/"/g,'""')}"`,
      b.notional_usd ?? "",
      b.detected_ms ?? ""
    ];
    rows.push(r.join(","));
  }
  return rows.join("\n");
}

async function refreshAll() {
  const h = await fetchHealth();
  $('#stats').innerText = `processed: ${h.processed} · breaks: ${h.breaks} · avg detect: ${fmt(h.avg_detect_ms)} ms`;

  let items = await fetchBreaks();
  if ($('#hideMissing').checked) {
    items = items.filter(b => b.break_type !== 'MissingConfirm');
  }
  kpiSummary(items);
  renderBreaks(items);
}

let timer = null;
function setupControls() {
  $('#refresh').addEventListener('click', refreshAll);
  $('#hideMissing').addEventListener('change', refreshAll);
  $('#autoRefresh').addEventListener('change', () => {
    if ($('#autoRefresh').checked) {
      timer = setInterval(refreshAll, 5000);
    } else {
      if (timer) clearInterval(timer);
      timer = null;
    }
  });
  $('#export').addEventListener('click', async () => {
    let items = await fetchBreaks();
    if ($('#hideMissing').checked) items = items.filter(b => b.break_type !== 'MissingConfirm');
    const blob = new Blob([toCSV(items)], {type: 'text/csv;charset=utf-8;'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `t1-copilot-breaks-${Date.now()}.csv`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });
}

async function boot() {
  await refreshAll();
  setupControls();

  // Live push
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onmessage = async (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      if (msg.type === 'break') {
        await refreshAll();
      }
    } catch (e) {}
  };
  ws.onopen = () => ws.send('ping');
  setInterval(() => { try { ws.send('ping'); } catch (e) {} }, 15000);

  // auto refresh on by default
  $('#autoRefresh').dispatchEvent(new Event('change'));
}
boot();