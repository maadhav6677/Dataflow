(function () {
  "use strict";

  const raw = window.CONTROL_TOWER_DATA;
  if (!raw) {
    document.body.innerHTML = '<p class="empty">Dashboard data is missing. Run <code>make dashboard</code>.</p>';
    return;
  }

  const objects = (schema, rows) => rows.map(row => Object.fromEntries(schema.map((name, i) => [name, row[i]])));
  const allLines = objects(raw.schema.lines, raw.lines);
  const allReceipts = objects(raw.schema.receipts, raw.receipts);
  const allWaste = objects(raw.schema.waste, raw.waste);
  const targets = raw.meta.targets;

  const $ = id => document.getElementById(id);
  const startInput = $("start-date");
  const endInput = $("end-date");
  const cityInput = $("city-filter");
  const categoryInput = $("category-filter");

  const unique = (rows, key) => [...new Set(rows.map(row => row[key]))].sort();
  unique(allLines, "city").forEach(value => cityInput.add(new Option(value, value)));
  unique(allLines, "category").forEach(value => categoryInput.add(new Option(value, value)));

  const formatNumber = value => new Intl.NumberFormat("en-IN").format(Math.round(value));
  const formatPct = value => Number.isFinite(value) ? `${value.toFixed(1)}%` : "—";
  const formatCurrency = value => {
    const amount = Math.abs(value);
    const sign = value < 0 ? "−" : "";
    if (amount >= 1e7) return `${sign}₹${(amount / 1e7).toFixed(2)} Cr`;
    if (amount >= 1e5) return `${sign}₹${(amount / 1e5).toFixed(2)} L`;
    if (amount >= 1e3) return `${sign}₹${(amount / 1e3).toFixed(1)} K`;
    return `${sign}₹${formatNumber(amount)}`;
  };
  const sum = (rows, key) => rows.reduce((total, row) => total + Number(row[key] || 0), 0);
  const ratio = (numerator, denominator) => denominator ? 100 * numerator / denominator : NaN;
  const safe = value => String(value).replace(/[&<>'"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));

  function selected(rows) {
    const city = cityInput.value;
    const category = categoryInput.value;
    return rows.filter(row => row.date >= startInput.value && row.date <= endInput.value
      && (city === "All" || row.city === city)
      && (category === "All" || row.category === category));
  }

  function metrics(lines, receipts, waste) {
    const orderedUnits = sum(lines, "ordered_qty");
    const fulfilledUnits = sum(lines, "fulfilled_qty");
    const orderedValue = sum(lines, "ordered_value");
    const revenue = sum(lines, "delivered_value");
    const grossProfit = sum(lines, "gross_profit");
    const acceptedUnits = receipts.reduce((total, row) => total + row.received_qty - row.rejected_qty, 0);
    return {
      lines: lines.length,
      orders: new Set(lines.map(row => row.order_id)).size,
      customers: new Set(lines.map(row => row.customer_id)).size,
      revenue,
      orderedValue,
      unfulfilled: orderedValue - revenue,
      otif: ratio(sum(lines, "line_otif"), lines.length),
      fill: ratio(fulfilledUnits, orderedUnits),
      margin: ratio(grossProfit, revenue),
      wasteRate: ratio(sum(waste, "waste_units"), acceptedUnits),
      wasteCost: sum(waste, "waste_cost")
    };
  }

  function setKpis(kpi) {
    $("kpi-revenue").textContent = formatCurrency(kpi.revenue);
    $("kpi-revenue-note").textContent = `${formatNumber(kpi.orders)} orders · ${formatNumber(kpi.customers)} buyers`;
    $("kpi-otif").textContent = formatPct(kpi.otif);
    $("kpi-otif-note").textContent = `${(kpi.otif - targets.line_otif).toFixed(1)} pp vs 95% target`;
    $("kpi-otif-note").className = kpi.otif >= targets.line_otif ? "good" : "bad";
    $("kpi-fill").textContent = formatPct(kpi.fill);
    $("kpi-fill-note").textContent = `${(kpi.fill - targets.fill_rate).toFixed(1)} pp vs 98% target`;
    $("kpi-fill-note").className = kpi.fill >= targets.fill_rate ? "good" : "warn";
    $("kpi-margin").textContent = formatPct(kpi.margin);
    $("kpi-margin-note").textContent = "On delivered value";
    $("kpi-unfulfilled").textContent = formatCurrency(kpi.unfulfilled);
    $("kpi-unfulfilled-note").textContent = `${formatPct(ratio(kpi.unfulfilled, kpi.orderedValue))} of ordered value`;
    $("kpi-waste").textContent = formatPct(kpi.wasteRate);
    $("kpi-waste-note").textContent = `${formatCurrency(kpi.wasteCost)} disposed cost`;
    $("kpi-waste-note").className = kpi.wasteRate <= targets.waste_rate ? "good" : "bad";
  }

  function weekStart(dateText) {
    const value = new Date(`${dateText}T00:00:00Z`);
    const day = value.getUTCDay() || 7;
    value.setUTCDate(value.getUTCDate() - day + 1);
    return value.toISOString().slice(0, 10);
  }

  function drawTrend(lines) {
    const groups = new Map();
    lines.forEach(row => {
      const key = weekStart(row.date);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(row);
    });
    const points = [...groups].sort(([a], [b]) => a.localeCompare(b)).map(([week, rows]) => ({
      week,
      otif: ratio(sum(rows, "line_otif"), rows.length),
      fill: ratio(sum(rows, "fulfilled_qty"), sum(rows, "ordered_qty"))
    }));
    const container = $("trend-chart");
    if (!points.length) { container.innerHTML = '<p class="empty">No data in this range.</p>'; return; }

    const width = 1000, height = 255, left = 42, right = 14, top = 14, bottom = 29;
    const minY = Math.max(60, Math.floor(Math.min(...points.flatMap(point => [point.otif, point.fill])) / 5) * 5 - 5);
    const maxY = 100;
    const x = i => left + (points.length === 1 ? 0 : i * (width - left - right) / (points.length - 1));
    const y = value => top + (maxY - value) * (height - top - bottom) / (maxY - minY);
    const path = key => points.map((point, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(point[key]).toFixed(1)}`).join(" ");
    const ticks = [minY, minY + (maxY - minY) / 2, maxY];
    const labelIndexes = [...new Set([0, Math.floor((points.length - 1) / 2), points.length - 1])];
    container.innerHTML = `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true">
      ${ticks.map(tick => `<line class="grid-line" x1="${left}" y1="${y(tick)}" x2="${width-right}" y2="${y(tick)}"></line><text x="2" y="${y(tick)+3}">${Math.round(tick)}%</text>`).join("")}
      <line class="target-line" x1="${left}" y1="${y(targets.line_otif)}" x2="${width-right}" y2="${y(targets.line_otif)}"></line>
      <path class="line-fill" d="${path("fill")}"></path><path class="line-otif" d="${path("otif")}"></path>
      ${labelIndexes.map(i => `<text x="${x(i)}" y="${height-5}" text-anchor="${i === 0 ? "start" : i === points.length-1 ? "end" : "middle"}">${new Date(points[i].week+"T00:00:00Z").toLocaleDateString("en-IN", {day:"2-digit",month:"short",timeZone:"UTC"})}</text>`).join("")}
    </svg>`;
  }

  function groupMetrics(lines, dimension) {
    const groups = new Map();
    lines.forEach(row => {
      if (!groups.has(row[dimension])) groups.set(row[dimension], []);
      groups.get(row[dimension]).push(row);
    });
    return [...groups].map(([name, rows]) => ({
      name,
      otif: ratio(sum(rows, "line_otif"), rows.length),
      fill: ratio(sum(rows, "fulfilled_qty"), sum(rows, "ordered_qty")),
      lines: rows.length
    })).sort((a, b) => a.otif - b.otif);
  }

  function drawPerformance(lines) {
    const dimension = cityInput.value === "All" ? "city" : "category";
    $("performance-title").textContent = dimension === "city" ? "Warehouse performance" : "Category performance";
    const values = groupMetrics(lines, dimension);
    $("performance-chart").innerHTML = values.length ? values.map(item => `
      <div class="bar-row"><div class="bar-row__head"><span>${safe(item.name)}</span><span class="${item.otif < 90 ? "bad" : item.otif < 95 ? "warn" : "good"}">${formatPct(item.otif)}</span></div>
      <div class="bar-track"><div class="bar-fill" style="width:${Math.max(2, item.otif)}%"></div></div><small>${formatPct(item.fill)} fill · ${formatNumber(item.lines)} lines</small></div>`).join("") : '<p class="empty">No data in this range.</p>';
  }

  function reasonGroups(lines) {
    const groups = new Map();
    lines.filter(row => !row.line_otif).forEach(row => {
      const current = groups.get(row.failure_reason) || {count: 0, value: 0};
      current.count += 1;
      current.value += row.ordered_value - row.delivered_value;
      groups.set(row.failure_reason, current);
    });
    return [...groups].map(([name, value]) => ({name, ...value})).sort((a, b) => b.count - a.count);
  }

  function drawReasons(lines) {
    const values = reasonGroups(lines);
    const max = values.length ? values[0].count : 1;
    $("reason-chart").innerHTML = values.length ? values.slice(0, 6).map(item => `
      <div class="bar-row"><div class="bar-row__head"><span>${safe(item.name)}</span><span>${formatNumber(item.count)}</span></div>
      <div class="bar-track"><div class="bar-fill" style="width:${100 * item.count / max}%"></div></div><small>${formatCurrency(item.value)} unfulfilled value</small></div>`).join("") : '<p class="empty">No service failures in this range.</p>';
  }

  function actionGroups(lines, receipts, waste) {
    const lineMap = new Map(), receiptMap = new Map(), wasteMap = new Map();
    lines.forEach(row => {
      const key = `${row.city}|${row.category}`;
      if (!lineMap.has(key)) lineMap.set(key, []);
      lineMap.get(key).push(row);
    });
    receipts.forEach(row => {
      const key = `${row.city}|${row.category}`;
      if (!receiptMap.has(key)) receiptMap.set(key, []);
      receiptMap.get(key).push(row);
    });
    waste.forEach(row => {
      const key = `${row.city}|${row.category}`;
      if (!wasteMap.has(key)) wasteMap.set(key, []);
      wasteMap.get(key).push(row);
    });
    return [...lineMap].map(([key, rows]) => {
      const [city, category] = key.split("|");
      const kpi = metrics(rows, receiptMap.get(key) || [], wasteMap.get(key) || []);
      const reasons = reasonGroups(rows);
      const topReason = reasons.length ? reasons[0].name : "None";
      const priority = kpi.unfulfilled + kpi.wasteCost + (100 - kpi.otif) * 250;
      return {city, category, ...kpi, topReason, priority};
    }).sort((a, b) => b.priority - a.priority);
  }

  function recommendation(item) {
    if (item.wasteRate > 1) return "Review FEFO rotation and category-level demand forecast";
    const lookup = {
      "Cold-chain exception": "Audit cold-chain handoffs and temperature exceptions",
      "Supplier delay": "Tighten supplier SLA; validate a backup source",
      "Quality rejection": "Increase inbound QC and review supplier CAPA",
      "Stockout": "Revisit safety stock and reorder-point assumptions",
      "Capacity constraint": "Rebalance picking and dispatch capacity",
      "Customer cancellation": "Review promise accuracy and cancellation cohort"
    };
    return lookup[item.topReason] || "Monitor weekly; no immediate intervention";
  }

  function setActions(actions) {
    $("action-body").innerHTML = actions.length ? actions.slice(0, 8).map((item, index) => `<tr>
      <td><span class="priority">${String(index + 1).padStart(2, "0")}</span></td><td><strong>${safe(item.city)}</strong><br><small>${safe(item.category)}</small></td>
      <td class="${item.otif < 90 ? "bad" : "warn"}">${formatPct(item.otif)}</td><td>${formatPct(item.fill)}</td><td>${formatCurrency(item.unfulfilled)}</td><td>${formatPct(item.wasteRate)}<br><small>${formatCurrency(item.wasteCost)}</small></td><td>${safe(recommendation(item))}</td>
    </tr>`).join("") : '<tr><td colspan="7" class="empty">No data in this range.</td></tr>';
  }

  function setSuppliers(receipts) {
    const groups = new Map();
    receipts.forEach(row => {
      if (!groups.has(row.supplier)) groups.set(row.supplier, []);
      groups.get(row.supplier).push(row);
    });
    const scores = [...groups].map(([supplier, rows]) => {
      const onTime = ratio(sum(rows, "on_time"), rows.length);
      const acceptance = ratio(rows.reduce((t, r) => t + r.received_qty - r.rejected_qty, 0), sum(rows, "ordered_qty"));
      const rejectedCost = rows.reduce((t, r) => t + r.rejected_qty * r.unit_cost, 0);
      return {supplier, category: rows[0].category, receipts: rows.length, onTime, acceptance, rejectedCost, score: .55 * onTime + .45 * acceptance};
    }).sort((a, b) => a.score - b.score);
    $("supplier-body").innerHTML = scores.length ? scores.slice(0, 7).map(item => {
      const status = item.score < 95 ? ["Review", "pill--red"] : item.score < 97.5 ? ["Watch", "pill--amber"] : ["Healthy", "pill--green"];
      return `<tr><td><strong>${safe(item.supplier)}</strong></td><td>${safe(item.category)}</td><td>${formatNumber(item.receipts)}</td><td>${formatPct(item.onTime)}</td><td>${formatPct(item.acceptance)}</td><td>${formatCurrency(item.rejectedCost)}</td><td><span class="pill ${status[1]}">${status[0]}</span></td></tr>`;
    }).join("") : '<tr><td colspan="7" class="empty">No receipts in this range.</td></tr>';
  }

  function setInsights(lines, actions) {
    const reasons = reasonGroups(lines);
    const worst = [...actions].sort((a, b) => a.otif - b.otif)[0];
    const biggestLoss = [...actions].sort((a, b) => b.unfulfilled - a.unfulfilled)[0];
    const topReason = reasons[0];
    const insights = worst ? [
      ["Largest service gap", `${worst.city} × ${worst.category} runs at ${formatPct(worst.otif)} line OTIF.`],
      ["Largest demand loss", `${biggestLoss.city} × ${biggestLoss.category} carries ${formatCurrency(biggestLoss.unfulfilled)} unfulfilled value.`],
      topReason
        ? ["Primary failure mode", `${topReason.name} affects ${formatNumber(topReason.count)} failed lines in this view.`]
        : ["Primary failure mode", "No failed order lines are recorded in this view."]
    ] : [];
    $("insight-list").innerHTML = insights.map(([title, copy]) => `<div class="insight"><b>${safe(title)}</b><span>${safe(copy)}</span></div>`).join("");
    const protectedValue = actions.slice(0, 5).reduce((total, item) => total + .3 * item.unfulfilled + .2 * item.wasteCost, 0);
    $("opportunity-value").textContent = formatCurrency(protectedValue);
  }

  function render() {
    if (startInput.value > endInput.value) endInput.value = startInput.value;
    const lines = selected(allLines), receipts = selected(allReceipts), waste = selected(allWaste);
    const kpi = metrics(lines, receipts, waste);
    const actions = actionGroups(lines, receipts, waste);
    const scopeCity = cityInput.value === "All" ? "All warehouses" : cityInput.value;
    const scopeCategory = categoryInput.value === "All" ? "All categories" : categoryInput.value;
    $("scope-label").textContent = `${scopeCity} · ${scopeCategory}`;
    setKpis(kpi);
    drawTrend(lines);
    drawPerformance(lines);
    drawReasons(lines);
    setActions(actions);
    setSuppliers(receipts);
    setInsights(lines, actions);
  }

  [startInput, endInput, cityInput, categoryInput].forEach(element => element.addEventListener("change", render));
  $("reset-filters").addEventListener("click", () => {
    startInput.value = raw.meta.period_start;
    endInput.value = raw.meta.period_end;
    cityInput.value = "All";
    categoryInput.value = "All";
    render();
  });
  $("footer-source").textContent = raw.meta.source;
  render();
})();
