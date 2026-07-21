const state = { data: null, status: "all", query: "", trendDays: 30, watchType: "entities" };
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
const profileUrl = (name, kind="entities") => `entity.html?name=${encodeURIComponent(name)}&kind=${encodeURIComponent(kind)}`;

fetch("data/dashboard.json?v=__ASSET_VERSION__").then(response => {
  if (!response.ok) throw new Error(`Dashboard data failed: ${response.status}`);
  return response.json();
}).then(data => { state.data = data; render(); }).catch(error => {
  document.getElementById("signal-grid").innerHTML = `<p>Unable to load dashboard data: ${escapeHtml(error.message)}</p>`;
});

function render(){
  const themes = state.data.signals.themes || [];
  const sources = state.data.source_health.sources || [];
  document.getElementById("repo-link").href = safeUrl(state.data.repository_url);
  document.getElementById("metric-actionable").textContent = themes.filter(x => x.status === "actionable").length;
  document.getElementById("metric-rising").textContent = themes.filter(x => x.momentum === "rising").length;
  document.getElementById("metric-critical").textContent = themes.filter(x => x.importance === "critical").length;
  const healthy = sources.filter(x => x.status === "healthy").length;
  document.getElementById("metric-health").textContent = sources.length ? `${Math.round(healthy / sources.length * 100)}%` : "—";
  const alerts = state.data.alerts || { alerts: [], active_count: 0, new_count: 0 };
  document.getElementById("metric-alerts").textContent = alerts.active_count || 0;
  document.getElementById("metric-alerts-detail").textContent = `${alerts.new_count || 0} new condition${alerts.new_count === 1 ? "" : "s"}`;
  const coverage = state.data.entity_watch?.coverage || [];
  const covered = coverage.filter(item => item.status === "covered").length;
  document.getElementById("metric-coverage").textContent = coverage.length ? `${Math.round(covered / coverage.length * 100)}%` : "—";
  document.getElementById("metric-coverage-detail").textContent = `${covered} of ${coverage.length} organizations`;
  document.getElementById("signal-updated").textContent = `Updated ${formatDate(state.data.signals.updated_at)}`;
  document.getElementById("source-summary").textContent = `${healthy} of ${sources.length} active sources healthy`;
  document.getElementById("footer-updated").textContent = `Dashboard built ${formatDate(state.data.generated_at)}`;
  renderTrend(); renderAlerts(alerts); renderSignals(); renderWatch(); renderCoverage(); renderSources(sources); renderReports(state.data.reports);
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
  document.getElementById("alert-list").innerHTML = alerts.length ? alerts.slice(0, 16).map(item =>
    `<article class="alert-item ${escapeHtml(item.severity)}"><span class="badge ${escapeHtml(item.severity)}">${escapeHtml(item.severity)}</span><div><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.summary)}</p></div><div>${item.is_new ? '<span class="new-tag">NEW</span> ' : ''}${item.evidence_url ? `<a href="${escapeHtml(safeUrl(item.evidence_url))}" target="_blank" rel="noopener">Evidence →</a> ` : ''}<a href="${escapeHtml(safeUrl(state.data.repository_url + '/blob/main/reports/' + item.link))}">Profile →</a></div></article>`
  ).join("") : "<p>No active alerts.</p>";
}

function renderSignals(){
  const query = state.query.toLowerCase();
  const themes = state.data.signals.themes.filter(item => {
    const statusMatch = state.status === "all" || item.status === state.status;
    const haystack = [item.name, ...(item.organizations || []), ...(item.evidence || []).map(x => x.title)].join(" ").toLowerCase();
    return statusMatch && haystack.includes(query);
  });
  document.getElementById("signal-grid").innerHTML = themes.length ? themes.map(signalCard).join("") : "<p>No signals match the current filters.</p>";
  document.querySelectorAll(".evidence-toggle").forEach(button => button.addEventListener("click", () => {
    const list = document.getElementById(button.dataset.target); list.classList.toggle("open");
    button.textContent = list.classList.contains("open") ? "Hide evidence" : "View evidence";
  }));
}

function renderWatch(){
  const payload = state.data.entity_watch || { entities: [], technologies: [] };
  const items = payload[state.watchType] || [];
  const unseen = payload[`unseen_${state.watchType}`] || [];
  const matched = items.length ? items.map(item => {
    const evidence = item.evidence?.[0];
    return `<article class="watch-card"><span class="watch-type">${escapeHtml(item.type || state.watchType)}</span><h3><a class="profile-link" href="${escapeHtml(profileUrl(item.name, state.watchType))}">${escapeHtml(item.name)}</a></h3><div class="badges"><span class="badge ${escapeHtml(item.momentum)}">${escapeHtml(item.momentum)}</span><span class="badge ${escapeHtml(item.priority)}">${escapeHtml(item.priority)}</span><span class="badge">${escapeHtml(item.status)}</span></div><div class="watch-stats"><div><span>Evidence</span><strong>${item.evidence_count}</strong></div><div><span>Recent</span><strong>${item.recent_count}</strong></div><div><span>Prior</span><strong>${item.prior_count}</strong></div></div><p class="themes">${escapeHtml((item.themes || []).slice(0,3).join(" · "))}</p><div class="watch-actions"><a class="watch-link" href="${escapeHtml(profileUrl(item.name, state.watchType))}">View profile →</a>${evidence ? `<a class="watch-link muted-link" href="${escapeHtml(safeUrl(evidence.url))}" target="_blank" rel="noopener">Latest evidence ↗</a>` : ""}</div></article>`;
  }).join("") : "<p>No configured watch items have matched evidence yet.</p>";
  const awaiting = unseen.length ? `<details class="watch-unseen"><summary>${unseen.length} configured ${state.watchType === "entities" ? "organizations" : "technologies"} awaiting evidence</summary><div>${unseen.map(item => `<a href="${escapeHtml(profileUrl(item.name, state.watchType))}"><strong>${escapeHtml(item.name)}</strong> · ${escapeHtml(item.type)} · ${escapeHtml(item.priority)}</a>`).join("")}</div></details>` : "";
  document.getElementById("watch-grid").innerHTML = matched + awaiting;
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
    `<tr><td>${escapeHtml(item.name)}</td><td>${escapeHtml(item.type)}</td><td>${item.success_rate}%</td><td>${item.warning_days}</td><td><span class="health"><i class="dot ${escapeHtml(item.status)}"></i>${escapeHtml(item.status)}</span></td></tr>`).join("");
}

function renderReports(reports){
  const cards = [["DAILY",reports.latest_daily],["WEEKLY",reports.latest_weekly],["MONTHLY",reports.latest_monthly]].filter(([,item]) => item);
  document.getElementById("report-cards").innerHTML = cards.map(([type,item]) => `<a class="report-card" href="${escapeHtml(safeUrl(item.url))}"><span>${type}</span><h3>${escapeHtml(item.name)}</h3></a>`).join("");
}

document.getElementById("signal-search").addEventListener("input", event => { state.query = event.target.value; if(state.data) renderSignals(); });
document.getElementById("status-filters").addEventListener("click", event => { if(!event.target.dataset.status) return; state.status = event.target.dataset.status; document.querySelectorAll("#status-filters button").forEach(x => x.classList.toggle("active", x === event.target)); if(state.data) renderSignals(); });
document.getElementById("trend-ranges").addEventListener("click", event => { if(!event.target.dataset.days) return; state.trendDays = event.target.dataset.days === "all" ? "all" : Number(event.target.dataset.days); document.querySelectorAll("#trend-ranges button").forEach(x => x.classList.toggle("active", x === event.target)); if(state.data) renderTrend(); });
document.getElementById("watch-tabs").addEventListener("click", event => { if(!event.target.dataset.watch) return; state.watchType = event.target.dataset.watch; document.querySelectorAll("#watch-tabs button").forEach(x => x.classList.toggle("active", x === event.target)); if(state.data) renderWatch(); });

const navToggle = document.querySelector(".nav-toggle");
const navLinks = document.getElementById("primary-links");
const closeNav = () => { navLinks?.classList.remove("open"); navToggle?.setAttribute("aria-expanded", "false"); };
navToggle?.addEventListener("click", () => { const open = navLinks.classList.toggle("open"); navToggle.setAttribute("aria-expanded", String(open)); });
navLinks?.addEventListener("click", event => { if(event.target.closest("a")) closeNav(); });
document.addEventListener("keydown", event => { if(event.key === "Escape") closeNav(); });
