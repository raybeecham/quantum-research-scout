const state = { data: null, status: "all", query: "" };
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

fetch("data/dashboard.json").then(response => {
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
  document.getElementById("signal-updated").textContent = `Updated ${formatDate(state.data.signals.updated_at)}`;
  document.getElementById("source-summary").textContent = `${healthy} of ${sources.length} active sources healthy`;
  document.getElementById("footer-updated").textContent = `Dashboard built ${formatDate(state.data.generated_at)}`;
  renderAlerts(alerts); renderSignals(); renderSources(sources); renderReports(state.data.reports);
}

function renderAlerts(payload){
  const alerts = payload.alerts || [];
  document.getElementById("alert-summary").textContent = `${payload.active_count || 0} active · ${payload.new_count || 0} new`;
  document.getElementById("alert-list").innerHTML = alerts.length ? alerts.slice(0, 12).map(item =>
    `<article class="alert-item ${escapeHtml(item.severity)}"><span class="badge ${escapeHtml(item.severity)}">${escapeHtml(item.severity)}</span><div><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.summary)}</p></div><div>${item.is_new ? '<span class="new-tag">NEW</span> ' : ''}<a href="${escapeHtml(safeUrl(state.data.repository_url + '/blob/main/reports/' + item.link))}">Open →</a></div></article>`
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
