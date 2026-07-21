const params = new URLSearchParams(window.location.search);
const requestedName = params.get("name") || "";
const requestedKind = params.get("kind") === "technologies" ? "technologies" : "entities";
const escapeHtml = value => String(value ?? "").replace(/[&<>'"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
const safeUrl = value => { try { const url = new URL(String(value), window.location.href); return ["http:","https:"].includes(url.protocol) ? url.href : "#"; } catch { return "#"; } };
const displayDate = value => value ? new Intl.DateTimeFormat(undefined,{dateStyle:"medium"}).format(new Date(`${String(value).slice(0,10)}T00:00:00Z`)) : "Not seen";
const formatDateTime = value => value ? new Intl.DateTimeFormat(undefined,{dateStyle:"medium",timeStyle:"short"}).format(new Date(value)) : "Unknown";

fetch("data/dashboard.json?v=__ASSET_VERSION__").then(response => {
  if (!response.ok) throw new Error(`Dashboard data failed: ${response.status}`);
  return response.json();
}).then(renderProfile).catch(error => showError(`Unable to load this profile: ${error.message}`));

function renderProfile(data){
  const watch = data.entity_watch || {};
  const profiles = [...(watch[requestedKind] || []), ...(watch[`unseen_${requestedKind}`] || [])];
  const profile = profiles.find(item => item.name?.localeCompare(requestedName, undefined, {sensitivity:"accent"}) === 0);
  if (!profile) { showError(requestedName ? `No watchlist profile was found for “${requestedName}”.` : "No profile was selected."); return; }
  const coverage = requestedKind === "entities" ? (watch.coverage || []).find(item => item.name === profile.name) : null;
  const alerts = (data.alerts?.alerts || []).filter(item => item.entity?.toLocaleLowerCase() === profile.name.toLocaleLowerCase());
  const evidence = [...(profile.evidence || [])].sort((a,b) => String(b.date).localeCompare(String(a.date)) || (b.score || 0) - (a.score || 0));

  document.title = `${profile.name} · Quantum Research Scout`;
  document.getElementById("repo-link").href = safeUrl(data.repository_url);
  document.getElementById("profile-kind").textContent = requestedKind === "entities" ? "Organization" : "Technology";
  document.getElementById("profile-eyebrow").textContent = `${profile.type || (requestedKind === "entities" ? "organization" : "technology")} · intelligence profile`.toUpperCase();
  document.getElementById("profile-name").textContent = profile.name;
  document.getElementById("profile-badges").innerHTML = [profile.momentum, profile.priority, profile.status].filter(Boolean).map(value => `<span class="badge ${escapeHtml(value)}">${escapeHtml(value)}</span>`).join("");
  document.getElementById("profile-evidence").textContent = profile.evidence_count || 0;
  document.getElementById("profile-latest").textContent = displayDate(profile.latest_seen);
  document.getElementById("profile-momentum").textContent = `${profile.recent_count || 0} / ${profile.prior_count || 0}`;
  document.getElementById("profile-coverage").textContent = coverage?.status || (requestedKind === "technologies" ? "N/A" : "Gap");
  document.getElementById("profile-updated").textContent = `Watch data updated ${formatDateTime(watch.updated_at)}`;
  document.getElementById("footer-updated").textContent = `Dashboard built ${formatDateTime(data.generated_at)} · ${data.build_id || "current build"}`;
  renderChart(evidence);
  renderTimeline(evidence, data.repository_url);
  renderThemes(profile.themes || []);
  renderSources(coverage);
  renderAlerts(alerts);
}

function renderChart(evidence){
  const target = document.getElementById("profile-chart");
  if (!evidence.length) { target.innerHTML = '<div class="empty-state">No matching evidence has been collected yet. The profile will populate automatically when a source produces a match.</div>'; return; }
  const counts = new Map();
  evidence.forEach(item => { if(item.date) counts.set(item.date, (counts.get(item.date) || 0) + 1); });
  const days = [...counts.keys()].sort();
  const start = new Date(`${days[0]}T00:00:00Z`), end = new Date(`${days[days.length-1]}T00:00:00Z`);
  const series = [];
  for(let day = start; day <= end; day = new Date(day.getTime() + 86400000)){ const label = day.toISOString().slice(0,10); series.push({label,count:counts.get(label) || 0}); }
  const max = Math.max(...series.map(item => item.count), 1), width = 1000, height = 190, pad = 26;
  const x = index => pad + index * ((width - pad * 2) / Math.max(series.length - 1, 1));
  const y = count => height - pad - count / max * (height - pad * 2);
  const line = series.map((item,index) => `${index ? "L" : "M"}${x(index).toFixed(1)},${y(item.count).toFixed(1)}`).join(" ");
  const area = `${line} L${x(series.length-1)},${height-pad} L${x(0)},${height-pad} Z`;
  target.innerHTML = `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient id="profile-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#49d8d0" stop-opacity=".3"/><stop offset="1" stop-color="#49d8d0" stop-opacity="0"/></linearGradient></defs><path fill="url(#profile-fill)" d="${area}"/><path class="trend-line" d="${line}"/><text class="trend-label" x="${pad}" y="${height-5}">${days[0]}</text><text class="trend-label" text-anchor="end" x="${width-pad}" y="${height-5}">${days[days.length-1]}</text></svg>`;
}

function renderTimeline(evidence, repoUrl){
  const target = document.getElementById("profile-timeline");
  target.innerHTML = evidence.length ? evidence.map(item => {
    const report = item.report ? `<a href="${escapeHtml(safeUrl(`${repoUrl}/blob/main/reports/${item.report}`))}">Daily report</a>` : "";
    return `<article class="timeline-item"><a href="${escapeHtml(safeUrl(item.url))}" target="_blank" rel="noopener">${escapeHtml(item.title)}</a><p>${escapeHtml(displayDate(item.date))} · ${escapeHtml(item.source || "Unknown source")} · score ${item.score || 0}${report ? ` · ${report}` : ""}</p><div class="profile-themes">${(item.themes || []).map(theme => `<span>${escapeHtml(theme)}</span>`).join("")}</div></article>`;
  }).join("") : '<div class="empty-state">No evidence has matched this watchlist entry yet.</div>';
}

function renderThemes(themes){
  document.getElementById("profile-themes").innerHTML = themes.length ? themes.map(theme => `<span>${escapeHtml(theme)}</span>`).join("") : '<span class="empty-state">Awaiting a matched theme</span>';
}

function renderSources(coverage){
  const sources = [...(coverage?.active_sources || []), ...(coverage?.disabled_sources || [])];
  document.getElementById("profile-sources").innerHTML = sources.length ? sources.map(source => `<div class="profile-source"><strong>${escapeHtml(source.name)}</strong><small>${escapeHtml(source.type)} · ${source.enabled ? "active" : "disabled"}</small></div>`).join("") : '<div class="empty-state">No official source is configured for this profile.</div>';
}

function renderAlerts(alerts){
  document.getElementById("profile-alerts").innerHTML = alerts.length ? alerts.map(item => `<article class="profile-alert ${escapeHtml(item.severity)}"><h4>${escapeHtml(item.title)}</h4><p>${escapeHtml(item.summary)}</p>${item.evidence_url ? `<a class="watch-link" href="${escapeHtml(safeUrl(item.evidence_url))}" target="_blank" rel="noopener">Evidence →</a>` : ""}</article>`).join("") : '<div class="empty-state">No active alerts are tied directly to this profile.</div>';
}

function showError(message){
  document.getElementById("profile-name").textContent = "Profile unavailable";
  document.getElementById("profile-content").innerHTML = `<section class="section"><div class="empty-state">${escapeHtml(message)} <a class="watch-link" href="index.html#watch">Return to the watchlist.</a></div></section>`;
}

const navToggle = document.querySelector(".nav-toggle");
const navLinks = document.getElementById("primary-links");
const closeNav = () => { navLinks?.classList.remove("open"); navToggle?.setAttribute("aria-expanded", "false"); };
navToggle?.addEventListener("click", () => { const open = navLinks.classList.toggle("open"); navToggle.setAttribute("aria-expanded", String(open)); });
navLinks?.addEventListener("click", event => { if(event.target.closest("a")) closeNav(); });
document.addEventListener("keydown", event => { if(event.key === "Escape") closeNav(); });
