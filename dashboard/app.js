const state = { data: null, status: "priority", query: "", trendDays: 30, watchType: "entities", compareFirst: "", compareSecond: "" };
const icons = { rising: "↗", stable: "→", declining: "↘" };
const definitions = {
  rising: "Latest seven-day evidence is at least 50% higher than the prior seven days.",
  stable: "Evidence did not move enough to meet the rising or declining threshold.",
  declining: "Latest seven-day evidence is at least one-third lower than the prior period.",
  critical: "At least one supporting item scored 100 or higher.",
  high: "At least one supporting item scored between 50 and 99.",
  medium: "Highest supporting item scored below 50.",
  actionable: "A high- or critical-importance signal with rising momentum.",
  watching: "Relevant, but not currently actionable or stale.",
  stale: "No supporting evidence appeared for more than 14 days."
};

const escapeHtml = value => String(value ?? "").replace(/[&<>'"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
const safeUrl = value => { try { const url = new URL(String(value), window.location.href); return ["http:","https:"].includes(url.protocol) ? url.href : "#"; } catch { return "#"; } };
const formatDate = value => value ? new Intl.DateTimeFormat(undefined,{dateStyle:"medium",timeStyle:"short"}).format(new Date(value)) : "Unknown";
const formatShortDate = value => {
  if(!value) return "—";
  const text = String(value);
  const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(text);
  return new Intl.DateTimeFormat(undefined,{dateStyle:"medium",...(dateOnly ? {timeZone:"UTC"} : {})}).format(new Date(dateOnly ? `${text}T00:00:00Z` : text));
};
const friendlyReportName = (name, type) => {
  const value = String(name || "");
  const daily = value.match(/^(\d{4}-\d{2}-\d{2})-digest$/);
  if (type === "DAILY" && daily) return formatShortDate(daily[1]);
  const weekly = value.match(/^(\d{4}-\d{2}-\d{2})_to_(\d{4}-\d{2}-\d{2})-weekly$/);
  if (type === "WEEKLY" && weekly) {
    const start = new Date(`${weekly[1]}T00:00:00Z`);
    const end = new Date(`${weekly[2]}T00:00:00Z`);
    const sameMonth = start.getUTCFullYear() === end.getUTCFullYear() && start.getUTCMonth() === end.getUTCMonth();
    if (sameMonth) {
      const month = new Intl.DateTimeFormat(undefined,{month:"long",timeZone:"UTC"}).format(start);
      return `${month} ${start.getUTCDate()}–${end.getUTCDate()}, ${end.getUTCFullYear()}`;
    }
    return `${formatShortDate(weekly[1])} – ${formatShortDate(weekly[2])}`;
  }
  const monthly = value.match(/^(\d{4})-(\d{2})-monthly$/);
  if (type === "MONTHLY" && monthly) {
    return new Intl.DateTimeFormat(undefined,{month:"long",year:"numeric",timeZone:"UTC"}).format(new Date(`${monthly[1]}-${monthly[2]}-01T00:00:00Z`));
  }
  return value.replaceAll("_", " ").replace(/-(digest|weekly|monthly)$/i, "");
};
const profileUrl = (name, kind="entities") => `entity.html?name=${encodeURIComponent(name)}&kind=${encodeURIComponent(kind)}`;

fetch("data/dashboard.json?v=__ASSET_VERSION__").then(response => {
  if (!response.ok) throw new Error(`Dashboard data failed: ${response.status}`);
  return response.json();
}).then(data => { state.data = data; render(); }).catch(error => {
  document.getElementById("signal-grid").innerHTML = `<p>Unable to load dashboard data: ${escapeHtml(error.message)}</p>`;
});

function render(){
  const themes = state.data.signals?.themes || [];
  const sources = state.data.source_health?.sources || [];
  const patentPayload = state.data.patents || { patents: [], summary: {} };
  document.getElementById("repo-link").href = safeUrl(state.data.repository_url);
  document.getElementById("alerts-report-link").href = safeUrl(`${state.data.repository_url}/blob/main/reports/alerts.md`);
  document.getElementById("hero-report-link").href = safeUrl(state.data.reports?.latest_daily?.url || "#reports");
  document.getElementById("metric-actionable").textContent = themes.filter(x => x.status === "actionable").length;
  document.getElementById("metric-critical").textContent = themes.filter(x => x.importance === "critical").length;
  const healthy = sources.filter(x => x.status === "healthy").length;
  const alerts = state.data.alerts || { alerts: [], active_count: 0, new_count: 0 };
  document.getElementById("metric-alerts").textContent = alerts.new_count || 0;
  document.getElementById("metric-alerts-detail").textContent = `${alerts.active_count || 0} active overall`;
  document.getElementById("metric-patents").textContent = patentPayload.summary?.last_30_days || 0;
  document.getElementById("metric-patents-detail").textContent = `${patentPayload.summary?.total || 0} tracked publication${patentPayload.summary?.total === 1 ? "" : "s"}`;
  document.getElementById("signal-updated").textContent = `Updated ${formatDate(state.data.signals.updated_at)}`;
  const verified = sources.filter(x => x.verification_status === "verified").length;
  const fresh = sources.filter(x => x.freshness === "fresh").length;
  const stale = sources.filter(x => x.freshness === "stale").length;
  document.getElementById("source-summary").textContent = `${healthy} healthy · ${verified} verified · ${fresh} fresh · ${stale} stale`;
  document.getElementById("footer-updated").textContent = `Dashboard built ${formatDate(state.data.generated_at)}`;
  renderReports(state.data.reports); renderAlerts(alerts); renderSignals(); renderPatents(patentPayload); renderWatch();
  renderTrend(); renderReadiness(); renderStandards(); renderComparison(); renderCoverage(); renderSources(sources);
}

function renderTrend(){
  const raw = state.data.signals.overall_trend || [];
  if (!raw.length) { document.getElementById("trend-chart").innerHTML = "<p>No historical evidence is available yet.</p>"; return; }
  const points = raw.map(item => ({ date: new Date(`${item.date}T00:00:00Z`), label: item.date, count: item.count }));
  const latest = points[points.length - 1].date;
  const cutoff = state.trendDays === "all" ? points[0].date : new Date(latest.getTime() - (Number(state.trendDays) - 1) * 86400000);
  const filtered = points.filter(item => item.date >= cutoff);
  const byDay = new Map(filtered.map(item => [item.label, item.count]));
  const series = [];
  for (let day = new Date(cutoff); day <= latest; day = new Date(day.getTime() + 86400000)) {
    const label = day.toISOString().slice(0,10); series.push({ label, count: byDay.get(label) || 0 });
  }
  const max = Math.max(...series.map(item => item.count), 1), width = 1000, height = 220, pad = 28;
  const x = index => pad + index * ((width - pad * 2) / Math.max(series.length - 1, 1));
  const y = count => height - pad - count / max * (height - pad * 2);
  const line = series.map((item,index) => `${index ? "L" : "M"}${x(index).toFixed(1)},${y(item.count).toFixed(1)}`).join(" ");
  const area = `${line} L${x(series.length-1)},${height-pad} L${x(0)},${height-pad} Z`;
  const grid = [0,.25,.5,.75,1].map(ratio => `<line class="trend-grid" x1="${pad}" y1="${y(max*ratio)}" x2="${width-pad}" y2="${y(max*ratio)}"/>`).join("");
  document.getElementById("trend-chart").innerHTML = `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient id="trend-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#49d8d0" stop-opacity=".3"/><stop offset="1" stop-color="#49d8d0" stop-opacity="0"/></linearGradient></defs>${grid}<path class="trend-area" d="${area}"/><path class="trend-line" d="${line}"/><text class="trend-label" x="${pad}" y="${height-5}">${series[0].label}</text><text class="trend-label" text-anchor="end" x="${width-pad}" y="${height-5}">${series[series.length-1].label}</text></svg>`;
  document.getElementById("trend-total").textContent = series.reduce((sum,item) => sum + item.count, 0);
  const peak = series.reduce((best,item) => item.count > best.count ? item : best, series[0]);
  document.getElementById("trend-peak").textContent = `${peak.count} · ${peak.label}`;
}

function renderAlerts(payload){
  const alerts = payload.alerts || [];
  document.getElementById("alert-summary").textContent = `${payload.active_count || 0} active · ${payload.new_count || 0} new`;
  document.getElementById("alert-list").innerHTML = alerts.length ? alerts.slice(0, 3).map(item =>
    `<article class="alert-item ${escapeHtml(item.severity)}"><span class="badge ${escapeHtml(item.severity)}">${escapeHtml(item.severity)}</span><div><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.summary)}</p></div><div>${item.is_new ? '<span class="new-tag">NEW</span> ' : ''}${item.evidence_url ? `<a href="${escapeHtml(safeUrl(item.evidence_url))}" target="_blank" rel="noopener">Evidence →</a> ` : ''}<a href="${escapeHtml(safeUrl(state.data.repository_url + '/blob/main/reports/' + item.link))}">Profile →</a></div></article>`
  ).join("") : "<p>No active alerts.</p>";
}

function renderSignals(){
  const query = state.query.toLowerCase();
  const themes = state.data.signals.themes.filter(item => {
    const statusMatch = state.status === "all"
      || (state.status === "priority" && (item.status === "actionable" || item.importance === "critical"))
      || item.status === state.status;
    const haystack = [item.name, ...(item.organizations || []), ...(item.evidence || []).map(x => x.title)].join(" ").toLowerCase();
    return statusMatch && haystack.includes(query);
  });
  const visibleThemes = state.status === "all" ? themes : themes.slice(0, 6);
  document.getElementById("signal-grid").innerHTML = visibleThemes.length ? visibleThemes.map(signalCard).join("") : "<p>No signals match the current filters.</p>";
  document.querySelectorAll(".evidence-toggle").forEach(button => button.addEventListener("click", () => {
    const list = document.getElementById(button.dataset.target); list.classList.toggle("open");
    button.textContent = list.classList.contains("open") ? "Hide evidence" : "View evidence";
  }));
}

function renderPatents(payload){
  const patents = payload.patents || [];
  const summary = payload.summary || {};
  document.getElementById("patent-summary").textContent = `${summary.last_30_days || 0} published in 30 days · ${summary.unique_assignees || 0} named assignees`;
  document.getElementById("patent-report-link").href = safeUrl(`${state.data.repository_url}/blob/main/reports/patents.md`);
  document.getElementById("patent-grid").innerHTML = patents.length ? patents.slice(0, 6).map(item => {
    const number = item.publication_number || "Publication number unavailable";
    const topics = (item.matched_keywords || []).slice(0, 3);
    return `<article class="patent-card"><div class="patent-meta"><span>${escapeHtml(number)}</span><time>${escapeHtml(formatShortDate(item.publication_date))}</time></div><h3><a href="${escapeHtml(safeUrl(item.url))}" target="_blank" rel="noopener">${escapeHtml(item.title)}</a></h3><p class="patent-assignee">${escapeHtml(item.assignee || "Assignee not listed")}</p><p>${escapeHtml(item.summary || "No abstract snippet is available.")}</p><div class="patent-footer"><div class="profile-themes">${topics.map(topic => `<span>${escapeHtml(topic)}</span>`).join("")}</div><strong>${item.score || 0}</strong></div></article>`;
  }).join("") : '<div class="empty-state">No relevant patent publications have been collected yet. Collection activates when the USPTO_ODP_API_KEY repository secret is configured.</div>';
}

function renderWatch(){
  const payload = state.data.entity_watch || { entities: [], technologies: [] };
  const items = payload[state.watchType] || [];
  const unseen = payload[`unseen_${state.watchType}`] || [];
  const watchCard = item => {
    const evidence = item.evidence?.[0];
    return `<article class="watch-card"><span class="watch-type">${escapeHtml(item.type || state.watchType)}</span><h3><a class="profile-link" href="${escapeHtml(profileUrl(item.name, state.watchType))}">${escapeHtml(item.name)}</a></h3><div class="badges"><span class="badge ${escapeHtml(item.momentum)}">${escapeHtml(item.momentum)}</span><span class="badge ${escapeHtml(item.priority)}">${escapeHtml(item.priority)}</span><span class="badge">${escapeHtml(item.status)}</span></div><div class="watch-stats"><div><span>Evidence</span><strong>${item.evidence_count}</strong></div><div><span>Recent</span><strong>${item.recent_count}</strong></div><div><span>Prior</span><strong>${item.prior_count}</strong></div></div><p class="themes">${escapeHtml((item.themes || []).slice(0,3).join(" · "))}</p><div class="watch-actions"><a class="watch-link" href="${escapeHtml(profileUrl(item.name, state.watchType))}">View profile →</a>${evidence ? `<a class="watch-link muted-link" href="${escapeHtml(safeUrl(evidence.url))}" target="_blank" rel="noopener">Latest evidence ↗</a>` : ""}</div></article>`;
  };
  const matched = items.length ? items.slice(0, 6).map(watchCard).join("") : "<p>No configured watch items have matched evidence yet.</p>";
  const more = items.length > 6 ? `<details class="watch-more"><summary>Show ${items.length - 6} more matched items</summary><div class="watch-more-grid">${items.slice(6).map(watchCard).join("")}</div></details>` : "";
  const awaiting = unseen.length ? `<details class="watch-unseen"><summary>${unseen.length} configured ${state.watchType === "entities" ? "organizations" : "technologies"} awaiting evidence</summary><div>${unseen.map(item => `<a href="${escapeHtml(profileUrl(item.name, state.watchType))}"><strong>${escapeHtml(item.name)}</strong> · ${escapeHtml(item.type)} · ${escapeHtml(item.priority)}</a>`).join("")}</div></details>` : "";
  document.getElementById("watch-grid").innerHTML = matched + more + awaiting;
}

function renderReadiness(){
  const payload = state.data.readiness || { organizations: [], summary: {} };
  const organizations = payload.organizations || [];
  const assessed = payload.summary?.assessed || 0;
  document.getElementById("readiness-summary").textContent = `${assessed} of ${organizations.length} organizations assessed from public evidence`;
  document.getElementById("readiness-table").innerHTML = organizations.map(item =>
    `<tr><td><a class="profile-link" href="${escapeHtml(profileUrl(item.name))}">${escapeHtml(item.name)}</a></td><td><span class="readiness-stage ${escapeHtml(item.stage)}">${escapeHtml(item.stage_label)}</span></td><td>${escapeHtml(item.confidence)}</td><td>${item.evidence_count || 0}${item.historical_evidence_count ? ` <small>(${item.historical_evidence_count} historical)</small>` : ""}</td><td>${item.source_count || 0}</td><td>${escapeHtml(formatShortDate(item.latest_evidence_at))}</td></tr>`
  ).join("") || '<tr><td colspan="6">No readiness evidence is available yet.</td></tr>';
}

function renderStandards(){
  const payload = state.data.standards || { milestones: [], summary: {} };
  const summary = payload.summary || {};
  const next = payload.next_milestone;
  const nextText = next ? `${next.title} · ${next.days_remaining} day${next.days_remaining === 1 ? "" : "s"}` : "No upcoming milestone";
  document.getElementById("standards-summary").textContent = `${summary.completed || 0} completed · ${summary.due_soon || 0} due soon · next: ${nextText}`;
  const order = { overdue: 0, due_soon: 1, upcoming: 2, estimated: 3, completed: 4 };
  const milestones = [...(payload.milestones || [])].sort((a,b) => (order[a.timing] - order[b.timing]) || String(a.target_date).localeCompare(String(b.target_date)));
  document.getElementById("standards-timeline").innerHTML = milestones.map(item => {
    const countdown = item.timing === "completed" ? "Completed" : item.timing === "estimated" ? "Planning estimate" : item.days_remaining < 0 ? `${Math.abs(item.days_remaining)} days overdue` : item.days_remaining === 0 ? "Due today" : `${item.days_remaining} days remaining`;
    return `<article class="milestone-card ${escapeHtml(item.timing)}"><div class="milestone-date"><strong>${escapeHtml(item.date_label)}</strong><span>${escapeHtml(countdown)}</span></div><div><div class="badges"><span class="badge">${escapeHtml(item.authority)}</span><span class="milestone-status ${escapeHtml(item.timing)}">${escapeHtml(item.timing.replace("_"," "))}</span></div><h3><a href="${escapeHtml(safeUrl(item.source_url))}" target="_blank" rel="noopener">${escapeHtml(item.title)}</a></h3><p>${escapeHtml(item.summary)}</p><div class="profile-themes">${(item.technologies || []).map(value => `<span>${escapeHtml(value)}</span>`).join("")}</div></div></article>`;
  }).join("") || '<div class="empty-state">No standards milestones are configured.</div>';
}

function renderCoverage(){
  const coverage = state.data.entity_watch?.coverage || [];
  const gaps = coverage.filter(item => item.status !== "covered").length;
  document.getElementById("coverage-summary").textContent = `${gaps} coverage gap${gaps === 1 ? "" : "s"} · ${coverage.length} configured organizations`;
  document.getElementById("coverage-table").innerHTML = coverage.map(item => {
    const sourceNames = (item.active_sources || []).map(source => source.name).join(", ") || (item.disabled_sources || []).map(source => `${source.name} (disabled)`).join(", ") || "None";
    return `<tr><td><a class="profile-link" href="${escapeHtml(profileUrl(item.name))}">${escapeHtml(item.name)}</a></td><td><span class="badge ${escapeHtml(item.priority)}">${escapeHtml(item.priority)}</span></td><td><span class="coverage-status ${escapeHtml(item.status)}"><i></i>${escapeHtml(item.status)}</span></td><td>${escapeHtml(sourceNames)}</td><td>${item.evidence_count || 0}</td></tr>`;
  }).join("");
}

function renderComparison(){
  const watch = state.data.entity_watch || {};
  const entities = [...(watch.entities || []), ...(watch.unseen_entities || [])].sort((a,b) => (b.evidence_count || 0) - (a.evidence_count || 0) || a.name.localeCompare(b.name));
  if (!entities.length) { document.getElementById("compare-results").innerHTML = '<div class="empty-state">No organizations are configured for comparison.</div>'; return; }
  if (!state.compareFirst || !entities.some(item => item.name === state.compareFirst)) state.compareFirst = entities[0].name;
  if (!state.compareSecond || state.compareSecond === state.compareFirst || !entities.some(item => item.name === state.compareSecond)) state.compareSecond = (entities.find(item => item.name !== state.compareFirst) || entities[0]).name;
  const options = selected => entities.map(item => `<option value="${escapeHtml(item.name)}" ${item.name === selected ? "selected" : ""}>${escapeHtml(item.name)}</option>`).join("");
  document.getElementById("compare-first").innerHTML = options(state.compareFirst);
  document.getElementById("compare-second").innerHTML = options(state.compareSecond);
  const coverage = new Map((watch.coverage || []).map(item => [item.name,item]));
  const health = new Map((state.data.source_health?.sources || []).map(item => [item.name,item]));
  const alerts = state.data.alerts?.alerts || [];
  const readiness = new Map((state.data.readiness?.organizations || []).map(item => [item.name,item]));
  const selected = [state.compareFirst,state.compareSecond].map(name => entities.find(item => item.name === name));
  const maxEvidence = Math.max(...selected.map(item => item.evidence_count || 0),1);
  document.getElementById("compare-results").innerHTML = selected.map(item => {
    const itemCoverage = coverage.get(item.name);
    const sourceHealth = (itemCoverage?.active_sources || []).map(source => health.get(source.name)).filter(Boolean);
    const verification = sourceHealth.some(source => source.verification_status === "verified") ? "verified" : sourceHealth.some(source => source.verification_status === "failing") ? "failing" : "unverified";
    const freshness = sourceHealth.some(source => source.freshness === "fresh") ? "fresh" : sourceHealth.some(source => source.freshness === "stale") ? "stale" : "unknown";
    const activeAlerts = alerts.filter(alert => alert.entity?.toLowerCase() === item.name.toLowerCase()).length;
    const itemReadiness = readiness.get(item.name);
    const width = Math.max(4,Math.round((item.evidence_count || 0) / maxEvidence * 100));
    return `<article class="compare-card"><div class="compare-head"><div><span>${escapeHtml(item.type || "organization")}</span><h3><a class="profile-link" href="${escapeHtml(profileUrl(item.name))}">${escapeHtml(item.name)}</a></h3></div><div class="badges"><span class="badge ${escapeHtml(item.priority)}">${escapeHtml(item.priority)}</span><span class="badge ${escapeHtml(item.momentum || "stable")}">${escapeHtml(item.momentum || "unseen")}</span></div></div><div class="compare-evidence"><span>Evidence volume</span><strong>${item.evidence_count || 0}</strong><div class="bar"><i style="width:${width}%"></i></div></div><dl class="compare-stats"><div><dt>Recent / prior</dt><dd>${item.recent_count || 0} / ${item.prior_count || 0}</dd></div><div><dt>Latest seen</dt><dd>${escapeHtml(item.latest_seen || "Not seen")}</dd></div><div><dt>PQC readiness</dt><dd><span class="readiness-stage ${escapeHtml(itemReadiness?.stage || "not_assessed")}">${escapeHtml(itemReadiness?.stage_label || "Not assessed")}</span></dd></div><div><dt>Active alerts</dt><dd>${activeAlerts}</dd></div><div><dt>Coverage</dt><dd>${escapeHtml(itemCoverage?.status || "N/A")}</dd></div><div><dt>Validation</dt><dd><span class="freshness ${escapeHtml(verification)}">${escapeHtml(verification)}</span></dd></div><div><dt>Freshness</dt><dd><span class="freshness ${escapeHtml(freshness)}">${escapeHtml(freshness)}</span></dd></div></dl><div class="profile-themes">${(item.themes || []).slice(0,5).map(theme => `<span>${escapeHtml(theme)}</span>`).join("") || '<span>No matched themes</span>'}</div><a class="watch-link" href="${escapeHtml(profileUrl(item.name))}">Open full profile →</a></article>`;
  }).join("");
}

function signalCard(item, index){
  const max = Math.max(item.recent_count || 0, item.prior_count || 0, 1);
  const width = Math.max(8, Math.round((item.recent_count || 0) / max * 100));
  const evidence = (item.evidence || []).map(x => `<li><a href="${escapeHtml(safeUrl(x.url))}" target="_blank" rel="noopener">${escapeHtml(x.title)}</a> · ${escapeHtml(x.date)}</li>`).join("");
  const evidenceId = `evidence-${index}`;
  return `<article class="signal-card"><div class="signal-head"><h3>${escapeHtml(item.name)}</h3><span>${icons[item.momentum] || "•"}</span></div>
    <div class="badges"><span class="badge ${escapeHtml(item.momentum)}" tabindex="0" title="${escapeHtml(definitions[item.momentum])}">${escapeHtml(item.momentum)}</span><span class="badge ${escapeHtml(item.importance)}" tabindex="0" title="${escapeHtml(definitions[item.importance])}">${escapeHtml(item.importance)}</span><span class="badge ${escapeHtml(item.status)}" tabindex="0" title="${escapeHtml(definitions[item.status])}">${escapeHtml(item.status)}</span><span class="badge" tabindex="0" title="Confidence reflects evidence volume and source diversity.">${escapeHtml(item.confidence)} confidence</span></div>
    <div class="momentum"><div class="momentum-label"><span>Recent ${item.recent_count || 0}</span><span>Prior ${item.prior_count || 0}</span></div><div class="bar"><span style="width:${width}%"></span></div></div>
    <p class="organizations"><strong>Leading sources:</strong> ${escapeHtml((item.organizations || []).join(", "))}</p><p class="follow-up"><strong>Follow-up:</strong> ${escapeHtml(item.follow_up)}</p>
    <button class="evidence-toggle" data-target="${evidenceId}">View evidence</button><ul id="${evidenceId}" class="evidence">${evidence}</ul></article>`;
}

function renderSources(sources){
  const order = { failing: 0, degraded: 1, healthy: 2 };
  document.getElementById("source-table").innerHTML = [...sources].sort((a,b) => (order[a.status]-order[b.status]) || a.name.localeCompare(b.name)).map(item =>
    `<tr><td>${escapeHtml(item.name)}</td><td>${escapeHtml(item.type)}</td><td>${item.success_rate ?? "—"}${item.success_rate == null ? "" : "%"}</td><td>${item.warning_days || 0}</td><td>${escapeHtml(formatShortDate(item.last_checked_at))}</td><td>${escapeHtml(formatShortDate(item.last_item_at))}</td><td><span class="freshness ${escapeHtml(item.freshness || "unverified")}">${escapeHtml(item.freshness || "unverified")}</span></td><td><span class="health"><i class="dot ${escapeHtml(item.status)}"></i>${escapeHtml(item.status)} · ${escapeHtml(item.verification_status || "unverified")}</span></td></tr>`).join("");
}

function renderReports(reports){
  const cards = [["DAILY",reports.latest_daily],["WEEKLY",reports.latest_weekly],["MONTHLY",reports.latest_monthly]].filter(([,item]) => item);
  document.getElementById("report-cards").innerHTML = cards.map(([type,item]) => `<a class="report-card" href="${escapeHtml(safeUrl(item.url))}"><span>${type}</span><h3>${escapeHtml(friendlyReportName(item.name, type))}</h3></a>`).join("");
}

document.getElementById("signal-search").addEventListener("input", event => { state.query = event.target.value; if(state.data) renderSignals(); });
document.getElementById("status-filters").addEventListener("click", event => { if(!event.target.dataset.status) return; state.status = event.target.dataset.status; document.querySelectorAll("#status-filters button").forEach(x => x.classList.toggle("active", x === event.target)); if(state.data) renderSignals(); });
document.getElementById("trend-ranges").addEventListener("click", event => { if(!event.target.dataset.days) return; state.trendDays = event.target.dataset.days === "all" ? "all" : Number(event.target.dataset.days); document.querySelectorAll("#trend-ranges button").forEach(x => x.classList.toggle("active", x === event.target)); if(state.data) renderTrend(); });
document.getElementById("watch-tabs").addEventListener("click", event => { if(!event.target.dataset.watch) return; state.watchType = event.target.dataset.watch; document.querySelectorAll("#watch-tabs button").forEach(x => x.classList.toggle("active", x === event.target)); if(state.data) renderWatch(); });
document.getElementById("compare-first").addEventListener("change", event => { state.compareFirst = event.target.value; if(state.data) renderComparison(); });
document.getElementById("compare-second").addEventListener("change", event => { state.compareSecond = event.target.value; if(state.data) renderComparison(); });

const navToggle = document.querySelector(".nav-toggle");
const navLinks = document.getElementById("primary-links");
const closeNav = () => { navLinks?.classList.remove("open"); navToggle?.setAttribute("aria-expanded", "false"); };
navToggle?.addEventListener("click", () => { const open = navLinks.classList.toggle("open"); navToggle.setAttribute("aria-expanded", String(open)); });
navLinks?.addEventListener("click", event => { if(event.target.closest("a")) closeNav(); });
document.addEventListener("keydown", event => { if(event.key === "Escape") closeNav(); });

const revealHashSection = () => {
  if (!window.location.hash) return;
  const target = document.querySelector(window.location.hash);
  for (let parent = target?.closest("details"); parent; parent = parent.parentElement?.closest("details")) parent.open = true;
};
window.addEventListener("hashchange", revealHashSection);
revealHashSection();
