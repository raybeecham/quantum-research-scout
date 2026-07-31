const state = {
  data: null,
  status: "priority",
  query: "",
  trendDays: 30,
  watchType: "entities",
  compareFirst: "",
  compareSecond: "",
  opportunityFilter: "all",
  decisionFilter: "open",
  analystDecisions: {},
  relationshipMission: "",
  relationshipNode: "",
  contractorQuery: ""
};
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
const formatMoney = value => {
  const amount = Number(value || 0);
  if (!amount) return "Not reported";
  return new Intl.NumberFormat(undefined,{style:"currency",currency:"USD",notation:"compact",maximumFractionDigits:1}).format(amount);
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
const ANALYST_DECISION_STORAGE_KEY = "quantum-research-scout:analyst-decisions:v1";

function loadAnalystDecisions(){
  try {
    const value = JSON.parse(window.localStorage.getItem(ANALYST_DECISION_STORAGE_KEY) || "{}");
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  } catch {
    return {};
  }
}

function persistAnalystDecisions(){
  try { window.localStorage.setItem(ANALYST_DECISION_STORAGE_KEY, JSON.stringify(state.analystDecisions)); } catch { /* Browser-local storage may be unavailable. */ }
}

state.analystDecisions = loadAnalystDecisions();

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
  const missionPayload = state.data.federal_missions || { missions: [], discovery_candidates: [], summary: {} };
  const fundingPayload = state.data.federal_funding || { records: [], mission_portfolios: [], summary: {} };
  const procurementPayload = state.data.procurement_intelligence || { opportunities: [], summary: {} };
  const decisionPayload = state.data.bid_no_bid || { briefs: [], summary: {} };
  const pursuitPayload = state.data.pursuits || { pursuits: [], summary: {} };
  const claimPayload = state.data.claim_ledger || { claims: [], summary: {} };
  const changePayload = state.data.intelligence_changes || { summary: {} };
  const temporalPayload = state.data.temporal_intelligence || { summary: {}, priority_events: [], upcoming: [] };
  const forecastPayload = state.data.strategic_forecasts || { summary: {}, active_forecasts: [], resolved_forecasts: [] };
  const analystDecisionPayload = state.data.decision_center || { items: [], summary: {} };
  document.getElementById("repo-link").href = safeUrl(state.data.repository_url);
  document.getElementById("alerts-report-link").href = safeUrl(`${state.data.repository_url}/blob/main/reports/alerts.md`);
  document.getElementById("hero-report-link").href = safeUrl(state.data.reports?.latest_daily?.url || "#reports");
  document.getElementById("metric-actionable").textContent = themes.filter(x => x.status === "actionable").length;
  document.getElementById("metric-critical").textContent = themes.filter(x => x.importance === "critical").length;
  const healthy = sources.filter(x => x.status === "healthy").length;
  const alerts = state.data.alerts || { alerts: [], active_count: 0, new_count: 0 };
  document.getElementById("metric-alerts").textContent = alerts.new_count || 0;
  document.getElementById("metric-alerts-detail").textContent = `${alerts.active_count || 0} active overall`;
  document.getElementById("metric-patents").textContent = patentPayload.summary?.total || 0;
  document.getElementById("metric-patents-detail").textContent = `${patentPayload.summary?.last_30_days || 0} published in 30 days · ${patentPayload.summary?.curated_total || 0} notable`;
  document.getElementById("hero-patent-count").textContent = `${patentPayload.summary?.total || 0} tracked`;
  document.getElementById("hero-mission-count").textContent = `${missionPayload.summary?.active || 0} active`;
  document.getElementById("signal-updated").textContent = `Updated ${formatDate(state.data.signals.updated_at)}`;
  const verified = sources.filter(x => x.verification_status === "verified").length;
  const fresh = sources.filter(x => x.freshness === "fresh").length;
  const stale = sources.filter(x => x.freshness === "stale").length;
  document.getElementById("source-summary").textContent = `${healthy} healthy · ${verified} verified · ${fresh} fresh · ${stale} stale`;
  document.getElementById("footer-updated").textContent = `Dashboard built ${formatDate(state.data.generated_at)}`;
  renderReports(state.data.reports); renderAlerts(alerts, temporalPayload); renderDecisionCenter(analystDecisionPayload, changePayload); renderForecasts(forecastPayload); renderMissions(missionPayload, fundingPayload); renderFunding(fundingPayload); renderProcurementDocuments(procurementPayload); renderDecisionBriefs(decisionPayload); renderPursuits(pursuitPayload); renderEvidenceLedger(claimPayload, changePayload, temporalPayload); renderSignals(); renderPatents(patentPayload); renderWatch();
  renderTrend(); renderReadiness(); renderStandards(); renderComparison(); renderCoverage(); renderSources(sources);
  animateMetrics();
  setupReveal();
  revealHashSection();
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
  document.getElementById("trend-chart").innerHTML = `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient id="trend-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#a66bff" stop-opacity=".34"/><stop offset=".55" stop-color="#48e4ff" stop-opacity=".12"/><stop offset="1" stop-color="#48e4ff" stop-opacity="0"/></linearGradient><linearGradient id="trend-stroke" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#a66bff"/><stop offset=".5" stop-color="#7085ff"/><stop offset="1" stop-color="#48e4ff"/></linearGradient></defs>${grid}<path class="trend-area" d="${area}"/><path class="trend-line" d="${line}"/><text class="trend-label" x="${pad}" y="${height-5}">${series[0].label}</text><text class="trend-label" text-anchor="end" x="${width-pad}" y="${height-5}">${series[series.length-1].label}</text></svg>`;
  document.getElementById("trend-total").textContent = series.reduce((sum,item) => sum + item.count, 0);
  const peak = series.reduce((best,item) => item.count > best.count ? item : best, series[0]);
  document.getElementById("trend-peak").textContent = `${peak.count} · ${peak.label}`;
}

function renderAlerts(payload, temporalPayload={}){
  const highlights = buildBriefingHighlights(
    payload,
    state.data.intelligence_changes || {},
    state.data.decision_center || {},
    state.data.federal_missions || {},
    temporalPayload
  );
  const timeSensitive = highlights.filter(item => item.timeSensitive).length;
  document.getElementById("alert-summary").textContent = highlights.length
    ? `${highlights.length} prioritized${timeSensitive ? ` · ${timeSensitive} time-sensitive` : ""}`
    : "No material changes";
  document.getElementById("alerts-report-link").textContent = `View ${payload.active_count || 0} monitored conditions →`;
  document.getElementById("alert-list").innerHTML = highlights.length ? highlights.map(item => {
    const evidence = item.evidenceUrl
      ? `<a href="${escapeHtml(safeUrl(item.evidenceUrl))}" target="_blank" rel="noopener">Review evidence →</a>`
      : "";
    const destination = item.destinationUrl
      ? `<a href="${escapeHtml(safeUrl(item.destinationUrl))}">${escapeHtml(item.destinationLabel || "Open detail")} →</a>`
      : "";
    return `<article class="intelligence-brief-card ${escapeHtml(item.priority)} ${escapeHtml(item.category)}">
      <div class="intelligence-brief-head"><div><span class="intelligence-status">${escapeHtml(item.statusLabel)}</span><span class="intelligence-priority ${escapeHtml(item.priority)}">${escapeHtml(item.priority)}</span></div><span>${escapeHtml(item.meta)}</span></div>
      <h3>${escapeHtml(item.title)}</h3>
      <p class="intelligence-why">${escapeHtml(item.why)}</p>
      <div class="intelligence-next-action"><b>Next action</b><span>${escapeHtml(item.action)}</span></div>
      <footer>${evidence}${destination}</footer>
    </article>`;
  }).join("") : `<div class="empty-state intelligence-quiet-state"><strong>No material changes today</strong><span>The scout is monitoring for authoritative changes, urgent opportunities, amendments, and conflicts.</span></div>`;
}

function buildBriefingHighlights(alertPayload, changePayload, decisionPayload, missionPayload, temporalPayload={}){
  const changes = (temporalPayload.priority_events || []).length
    ? temporalChangeHighlights(temporalPayload)
    : meaningfulChangeHighlights(changePayload);
  const alerts = materialAlertHighlights(alertPayload);
  const decisions = decisionHighlights(decisionPayload, temporalPayload);
  const urgentAlerts = alerts.filter(item => item.timeSensitive);
  const priorityAlerts = alerts.filter(item => !item.timeSensitive);
  const selected = [];
  const lanes = [changes,urgentAlerts];
  if (!changes.length) lanes.push(priorityAlerts);
  lanes.push(decisions);
  lanes.forEach(lane => {
    if (selected.length >= 3) return;
    const candidate = lane.find(item => !isDuplicateHighlight(item, selected));
    if (candidate) selected.push(candidate);
  });
  [...changes,...alerts,...decisions]
    .sort((a,b) => b.score - a.score || a.title.localeCompare(b.title))
    .forEach(item => {
      if (selected.length < 3 && !isDuplicateHighlight(item, selected)) selected.push(item);
    });
  if (!selected.length) {
    const milestone = nextMissionMilestone(missionPayload);
    if (milestone) selected.push(milestone);
  }
  return selected.sort((a,b) => b.score - a.score || a.title.localeCompare(b.title)).slice(0,3);
}

function temporalChangeHighlights(payload){
  const scoreByClass = {
    conflict_opened: 142,
    changed_since_prior_run: 132,
    superseded: 126,
    happened_today: 122,
    published_today: 118,
    recent_event: 108,
    recently_published: 104
  };
  const statusByClass = {
    conflict_opened: "CONFLICT OPENED",
    changed_since_prior_run: "CHANGED",
    superseded: "SUPERSEDED",
    happened_today: "HAPPENED TODAY",
    published_today: "PUBLISHED TODAY",
    recent_event: "RECENT EVENT",
    recently_published: "RECENT PUBLICATION"
  };
  return (payload.priority_events || []).map(item => {
    const temporal = item.temporal || {};
    const score = scoreByClass[temporal.classification];
    if (!score) return null;
    const subject = item.subject?.label || item.subject_label || item.evidence_title || "Tracked intelligence";
    const value = item.value ?? item.object?.label;
    const previous = item.previous_value ?? item.previous_object?.label;
    const delta = previous != null && value != null && normalizeBriefingText(previous) !== normalizeBriefingText(value)
      ? ` Previous: ${briefingValue(previous)}. Current: ${briefingValue(value)}.`
      : "";
    return {
      id: `temporal:${item.claim_id || subject}:${item.change_type || temporal.classification}`,
      category: "change",
      statusLabel: statusByClass[temporal.classification],
      priority: ["conflict_opened","changed_since_prior_run","superseded"].includes(temporal.classification) ? "critical" : "high",
      score: score + (item.authority === "authoritative" ? 5 : 0),
      title: smartBriefingTitle(subject),
      why: `${temporal.explanation || "Material evidence entered the comparison."}${delta}`,
      action: actionForPredicate(item.predicate),
      meta: briefingMeta(sourceName(item.evidence_url), temporal.primary_date || temporal.first_observed_at),
      evidenceUrl: item.evidence_url || "",
      destinationUrl: `${state.data.repository_url}/blob/main/reports/temporal-intelligence.md`,
      destinationLabel: "Open time trace",
      timeSensitive: ["conflict_opened","changed_since_prior_run"].includes(temporal.classification)
    };
  }).filter(Boolean).sort((a,b) => b.score - a.score || a.title.localeCompare(b.title));
}

function meaningfulChangeHighlights(payload){
  const criticalPredicates = new Set(["deadline","requirement","qualification_gate","opportunity_status","mission_status","legal_status"]);
  return ["changed","superseded"].flatMap(changeType => (payload[changeType] || []).map(event => {
    const before = event.previous_value ?? event.previous_object?.label ?? "";
    const after = event.value ?? event.object?.label ?? "";
    if (normalizeBriefingText(before) === normalizeBriefingText(after)) return null;
    const source = (event.sources || []).find(item => item?.url) || {};
    const predicate = String(event.predicate || "tracked fact").replaceAll("_"," ");
    const subject = event.subject?.label || event.subject_label || "Tracked intelligence";
    const priority = criticalPredicates.has(event.predicate) ? "critical" : "high";
    const authority = event.authority === "authoritative" ? "Authoritative" : "Analytical";
    return {
      id: `change:${event.claim_id || subject}:${event.predicate || changeType}`,
      category: "change",
      statusLabel: changeType === "superseded" ? "SUPERSEDED" : "CHANGED",
      priority,
      score: (priority === "critical" ? 116 : 96) + (event.authority === "authoritative" ? 8 : 0),
      title: `${titleCaseBriefing(predicate)} changed for ${smartBriefingTitle(subject)}`,
      why: `${authority} evidence now reports ${briefingValue(after)} instead of ${briefingValue(before)}.`,
      action: actionForPredicate(event.predicate),
      meta: briefingMeta(source.title || authority, payload.updated_at),
      evidenceUrl: source.url || "",
      destinationUrl: `${state.data.repository_url}/blob/main/reports/intelligence-changes.md`,
      destinationLabel: "View change trace",
      timeSensitive: priority === "critical"
    };
  })).filter(Boolean).sort((a,b) => b.score - a.score || a.title.localeCompare(b.title));
}

function materialAlertHighlights(payload){
  const rules = {
    procurement_amendment_impact: {label:"MATERIAL AMENDMENT",score:120,timeSensitive:true,action:"Revalidate requirements, risk, checklist items, and the bid decision against the amendment."},
    procurement_amendment: {label:"NEW AMENDMENT",score:108,timeSensitive:true,action:"Compare the new document with the prior solicitation and identify changed requirements or dates."},
    opportunity_closing: {label:"CLOSING NOW",score:136,timeSensitive:true,action:"Review eligibility and requirements now, then record a bid/no-bid decision."},
    opportunity_new: {label:"PRIORITY OPPORTUNITY",score:92,timeSensitive:false,action:"Assess mission fit, eligibility, technical requirements, and pursuit value."}
  };
  return (payload.alerts || []).map(alert => {
    const rule = alert.type?.startsWith("entity_")
      ? {label:"MATERIAL EVENT",score:88,timeSensitive:false,action:"Review the authoritative evidence and assess mission, technology, and competitor implications."}
      : rules[alert.type];
    if (!rule) return null;
    const summaryParts = String(alert.summary || "").split(" · ");
    const why = ["opportunity_closing","opportunity_new"].includes(alert.type)
      ? `${summaryParts.slice(0,-1).join(" · ") || alert.summary}.`
      : alert.summary || "A material intelligence condition requires review.";
    return {
      id: alert.id,
      category: alert.type?.startsWith("opportunity_") ? "opportunity" : "event",
      statusLabel: alert.is_new && rule.label !== "CLOSING NOW" ? `NEW · ${rule.label}` : rule.label,
      priority: alert.severity || "high",
      score: rule.score + (alert.is_new ? 5 : 0),
      title: smartBriefingTitle(stripAlertPrefix(alert.title)),
      why,
      action: summaryParts.length > 1 && ["opportunity_closing","opportunity_new"].includes(alert.type)
        ? summaryParts.at(-1)
        : rule.action,
      meta: briefingMeta(briefingAlertSource(alert), alert.evidence_date || alert.last_seen),
      evidenceUrl: alert.evidence_url || "",
      destinationUrl: `${state.data.repository_url}/blob/main/reports/${alert.link}`,
      destinationLabel: alert.type?.startsWith("opportunity_") ? "Open opportunity radar" : "Open event detail",
      timeSensitive: rule.timeSensitive
    };
  }).filter(Boolean).sort((a,b) => b.score - a.score || a.title.localeCompare(b.title));
}

function decisionHighlights(payload, temporalPayload={}){
  const labels = {
    amendment_revalidation: "REVALIDATION REQUIRED",
    authoritative_change: "GOVERNMENT EVIDENCE",
    claim_conflict: "UNRESOLVED CONFLICT"
  };
  return (payload.items || []).filter(item => !["reviewed","dismissed"].includes(state.analystDecisions[item.decision_id]?.disposition)).map(item => {
    const evidence = (item.evidence || []).find(source => source?.url) || {};
    const temporalEvent = (temporalPayload.priority_events || []).find(event => event.evidence_url && event.evidence_url === evidence.url);
    const temporal = temporalEvent?.temporal || {};
    const details = item.details || {};
    const priority = item.priority || "high";
    const historical = temporal.classification === "historical_discovery";
    const temporalBonus = ["happened_today","published_today"].includes(temporal.classification) ? 16
      : ["recent_event","recently_published"].includes(temporal.classification) ? 9
      : historical ? -32 : 0;
    return {
      id: item.decision_id,
      category: "decision",
      statusLabel: historical ? "HISTORICAL EVIDENCE FOUND" : labels[item.queue_type] || "ANALYST DECISION",
      priority,
      score: (priority === "critical" ? 118 : priority === "high" ? 98 : 78) + Math.min(12, Number(details.selection_score || 0) / 10) + decisionRecencyScore(details.record_date) + temporalBonus,
      title: decisionBriefingTitle(item),
      why: historical ? `${temporal.explanation} ${decisionBriefingWhy(item)}` : decisionBriefingWhy(item),
      action: decisionBriefingAction(item),
      meta: briefingMeta(details.awarding_agency || sourceName(evidence.url), details.record_date || item.observed_at),
      evidenceUrl: evidence.url || "",
      destinationUrl: "#decision-center",
      destinationLabel: "Open decision",
      timeSensitive: item.queue_type === "amendment_revalidation" || priority === "critical"
    };
  }).sort((a,b) => b.score - a.score || a.title.localeCompare(b.title));
}

function decisionRecencyScore(value){
  if (!value || !state.data.generated_at) return 0;
  const ageDays = (new Date(state.data.generated_at) - new Date(`${String(value).slice(0,10)}T00:00:00Z`)) / 86400000;
  if (!Number.isFinite(ageDays)) return 0;
  if (ageDays <= 180) return 10;
  if (ageDays <= 365) return 4;
  if (ageDays <= 730) return -8;
  return -18;
}

function decisionBriefingWhy(item){
  const details = item.details || {};
  const predicates = new Set(details.predicates || [details.predicate]);
  if (item.queue_type === "claim_conflict") return item.why || "Authoritative evidence remains in conflict and cannot safely support a decision yet.";
  if (item.queue_type === "amendment_revalidation") return item.why || "A material solicitation amendment changed a controlling pursuit assumption.";
  if (details.value === "awarded" || predicates.has("opportunity_status")) {
    return "Official government evidence records an award action; linked claims identify its status, agency, recipient, and reported amount where available.";
  }
  if (predicates.has("reported_recipient")) {
    return `Official award evidence identifies ${details.value || "a recipient"} as the reported recipient.`;
  }
  return item.why || "Authoritative government evidence crossed the strategic review threshold.";
}

function decisionBriefingAction(item){
  const details = item.details || {};
  const predicates = new Set(details.predicates || [details.predicate]);
  if (item.queue_type === "claim_conflict" || item.queue_type === "amendment_revalidation") return item.recommended_action || "Review the evidence and record a disposition.";
  if (details.value === "awarded" || predicates.has("opportunity_status") || predicates.has("reported_recipient")) {
    return "Review the recipient, value, scope, and mission linkage for competitor, partner, or procurement implications.";
  }
  return item.recommended_action || "Classify the signal and connect it to any affected mission or pursuit.";
}

function decisionBriefingTitle(item){
  const title = smartBriefingTitle(item.title || "Analyst decision");
  const agencyParts = String(item.details?.awarding_agency || "").split(" · ");
  const program = agencyParts.length > 1 ? agencyParts.at(-1).trim() : "";
  if (title.length > 85 && program) return `${program} award activity`;
  return title.length > 155 ? `${title.slice(0,152).trim()}…` : title;
}

function nextMissionMilestone(payload){
  const milestones = (payload.missions || []).map(mission => ({mission,milestone:mission.next_milestone})).filter(item => item.milestone?.target_date).sort((a,b) => String(a.milestone.target_date).localeCompare(String(b.milestone.target_date)));
  if (!milestones.length) return null;
  const {mission,milestone} = milestones[0];
  return {
    id: `milestone:${mission.id}:${milestone.target_date}`,
    category: "milestone",
    statusLabel: "NEXT MILESTONE",
    priority: "medium",
    score: 50,
    title: smartBriefingTitle(milestone.title || mission.name),
    why: `${mission.name} has a published milestone scheduled for ${formatShortDate(milestone.target_date)}.`,
    action: "Monitor the official mission source for execution evidence or a schedule change.",
    meta: briefingMeta((mission.lead_agencies || []).join(", ") || "Federal mission", milestone.target_date),
    evidenceUrl: mission.official_url || "",
    destinationUrl: "#missions",
    destinationLabel: "Open mission tracker",
    timeSensitive: false
  };
}

function isDuplicateHighlight(candidate, selected){
  if (selected.some(item => item.id === candidate.id || (item.evidenceUrl && item.evidenceUrl === candidate.evidenceUrl))) return true;
  const candidateTokens = briefingTitleTokens(candidate.title);
  return selected.some(item => {
    const tokens = briefingTitleTokens(item.title);
    const overlap = candidateTokens.filter(token => tokens.includes(token)).length;
    return overlap >= 2 && overlap / Math.max(1, Math.min(candidateTokens.length,tokens.length)) >= .6;
  });
}

function briefingTitleTokens(value){
  const ignored = new Set(["the","and","for","with","from","this","that","new","federal","government","program","project","research","award","opportunity"]);
  return [...new Set(normalizeBriefingText(value).split(" ").filter(token => token.length > 2 && !ignored.has(token)))];
}

function normalizeBriefingText(value){ return String(value ?? "").toLowerCase().replace(/[^a-z0-9]+/g," ").trim(); }
function stripAlertPrefix(value){ return String(value || "").replace(/^(Federal opportunity closing soon|New high-priority federal opportunity|Procurement amendment impact|New procurement amendment|[^:]+ event):\s*/i,""); }
function titleCaseBriefing(value){ return String(value || "").replace(/\b\w/g,letter => letter.toUpperCase()); }
function briefingValue(value){ const text = String(value ?? "not specified"); return text.length > 90 ? `${text.slice(0,87)}…` : text; }
function actionForPredicate(predicate){
  return ({deadline:"Rebaseline the response calendar and confirm the controlling deadline.",requirement:"Update the compliance matrix and revalidate technical fit.",qualification_gate:"Re-run the qualification gate and confirm the pursuit decision.",opportunity_status:"Confirm the new status and update the pursuit workflow.",mission_status:"Reassess mission timing, dependencies, and linked opportunities.",legal_status:"Review the legal-status evidence before relying on this asset."})[predicate] || "Review the before-and-after evidence and update any affected decision.";
}
function briefingMeta(source, date){ return [source || "Public evidence", briefingDate(date)].filter(Boolean).join(" · "); }
function briefingDate(value){
  if (!value) return "";
  try { return formatShortDate(value); } catch { return String(value).slice(0,10); }
}
function sourceName(url){
  try {
    const host = new URL(url).hostname.replace(/^www\./,"");
    return ({"sam.gov":"SAM.gov","grants.gov":"Grants.gov","usaspending.gov":"USAspending"})[host] || host;
  } catch { return "Public evidence"; }
}
function briefingAlertSource(alert){
  const entity = String(alert.entity || "").trim();
  const codeParts = entity.split("-");
  if (codeParts.length === 2 && codeParts[0] === codeParts[1]) return codeParts[0];
  if (/^[A-Z0-9]+-[A-Z0-9]+$/.test(entity)) return sourceName(alert.evidence_url);
  return entity || sourceName(alert.evidence_url);
}
function smartBriefingTitle(value){
  const text = String(value || "").trim();
  const letters = text.replace(/[^a-zA-Z]/g,"");
  if (!letters || letters !== letters.toUpperCase()) return text;
  const acronyms = new Set(["AI","ARLIS","BAA","CAREER","DHS","DOD","DOE","NSF","PQC","QBI","RFI","SATC","UMD"]);
  return text.toLowerCase().replace(/\b[a-z][a-z0-9.-]*\b/g,word => acronyms.has(word.toUpperCase()) ? word.toUpperCase() : word[0].toUpperCase() + word.slice(1));
}

function renderForecasts(payload){
  const active = payload.active_forecasts || [];
  const summary = payload.summary || {};
  const calibration = payload.calibration || {};
  document.getElementById("forecast-summary").textContent =
    `${summary.active || 0} active · ${summary.due_within_30_days || 0} due ≤30d · ${summary.calibration_label || "Awaiting outcomes"}`;
  document.getElementById("forecast-report-link").href =
    safeUrl(`${state.data.repository_url}/blob/main/reports/strategic-forecasts.md`);
  const leading = active[0];
  document.getElementById("forecast-preview").innerHTML = leading
    ? `<span>${Math.round(Number(leading.probability || 0) * 100)}%</span><p><b>${escapeHtml(leading.subject || "Strategic forecast")}</b> · ${escapeHtml(forecastTypeLabel(leading.forecast_type))}</p><small>by ${escapeHtml(formatShortDate(leading.horizon_end))}</small>`
    : `<p><b>No active forecast</b> · New hypotheses appear when official evidence crosses the configured threshold.</p>`;
  document.getElementById("forecast-calibration").innerHTML = [
    ["Active hypotheses",summary.active || 0],
    ["Resolved",summary.resolved || 0],
    ["Accuracy",summary.accuracy_rate == null ? "Awaiting outcomes" : `${Math.round(Number(summary.accuracy_rate) * 100)}%`],
    ["Mean Brier",summary.mean_brier_score == null ? "Not scored" : Number(summary.mean_brier_score).toFixed(3)]
  ].map(([label,value]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("");
  document.getElementById("forecast-grid").innerHTML = active.length ? active.slice(0,4).map(item => {
    const probability = Math.round(Number(item.probability || 0) * 100);
    const dossier = item.dossier || {};
    const horizon = item.horizon_end ? formatShortDate(item.horizon_end) : "No horizon";
    const triggers = item.triggers || [];
    const observed = triggers.filter(trigger => trigger.status === "observed").length;
    const evidence = (item.evidence || []).map(source =>
      `<a href="${escapeHtml(safeUrl(source.url))}" target="_blank" rel="noopener"><strong>${escapeHtml(source.title || "Official evidence")}</strong><span>${escapeHtml(source.role || source.authority || "evidence")} · ${escapeHtml(briefingDate(source.date) || "date not reported")}</span></a>`
    ).join("");
    const factors = (item.probability_factors || []).map(factor =>
      `<span>${escapeHtml(factor.factor)} ${Number(factor.points || 0) >= 0 ? "+" : ""}${Math.round(Number(factor.points || 0) * 100)}pts</span>`
    ).join("");
    return `<article class="forecast-card ${escapeHtml(item.impact || "high")}">
      <div class="forecast-head"><div class="forecast-probability"><strong>${probability}%</strong><span>likelihood</span></div><div><span>${escapeHtml(String(item.forecast_type || "forecast").replaceAll("_"," "))}</span><small>Horizon ${escapeHtml(horizon)}</small></div></div>
      <h3>${escapeHtml(item.question || "Strategic forecast")}</h3>
      <p>${escapeHtml(item.rationale || "Evidence-backed analytical hypothesis.")}</p>
      <div class="forecast-trigger-status"><span>${observed} / ${triggers.length} triggers observed</span><b>${escapeHtml(item.status || "active")}</b></div>
      <details><summary>Evidence, indicators, and mission dossier</summary>
        <div class="forecast-detail">
          <section><h4>Probability trace</h4><div class="forecast-factors">${factors}</div></section>
          <section><h4>Confirming indicators</h4><ul>${(item.confirming_indicators || []).slice(0,3).map(value => `<li>${escapeHtml(value)}</li>`).join("")}</ul></section>
          <section><h4>Disconfirming indicators</h4><ul>${(item.disconfirming_indicators || []).slice(0,3).map(value => `<li>${escapeHtml(value)}</li>`).join("")}</ul></section>
          <section><h4>Mission dossier</h4><dl><div><dt>Funding activity</dt><dd>${escapeHtml(formatMoney((dossier.known_award_value || 0) + (dossier.announced_funding_value || 0)))}</dd></div><div><dt>Records / open</dt><dd>${dossier.record_count || 0} / ${dossier.open_opportunities || 0}</dd></div><div><dt>Awards</dt><dd>${dossier.award_count || 0}</dd></div><div><dt>Related patents</dt><dd>${dossier.related_patent_count || 0} analytical</dd></div></dl></section>
          <section class="forecast-evidence"><h4>Authoritative evidence</h4>${evidence || "<span>No linked evidence is available.</span>"}</section>
        </div>
      </details>
    </article>`;
  }).join("") : '<div class="empty-state">No evidence-qualified strategic forecasts are active. The registry will open hypotheses when official mission activity crosses the configured threshold.</div>';
}

function forecastTypeLabel(value){
  const labels = {
    mission_opportunity_release: "additional mission-linked opportunity",
    mission_milestone_confirmation: "mission milestone confirmation"
  };
  return labels[value] || String(value || "strategic forecast").replaceAll("_"," ");
}

function renderMissions(payload, fundingPayload){
  const missions = payload.missions || [];
  const summary = payload.summary || {};
  const candidates = payload.discovery_candidates || [];
  const fundingByMission = new Map((fundingPayload.mission_portfolios || []).map(item => [item.mission_id,item]));
  document.getElementById("mission-summary").textContent = `${summary.active || 0} active · ${summary.upcoming_milestones || 0} milestones · ${fundingPayload.summary?.missions_with_activity || 0} with funding activity`;
  document.getElementById("mission-report-link").href = safeUrl(`${state.data.repository_url}/blob/main/reports/federal-missions.md`);
  document.getElementById("mission-grid").innerHTML = missions.length ? missions.slice(0, 6).map(item => {
    const next = item.next_milestone;
    const parent = item.parent_mission ? `<span>Part of ${escapeHtml(item.parent_mission)}</span>` : "";
    const update = item.updates?.[0];
    const funding = fundingByMission.get(item.id);
    const fundingFact = funding?.record_count ? `<div><dt>Funding activity</dt><dd>${funding.record_count} record${funding.record_count === 1 ? "" : "s"} · ${funding.open_opportunities || 0} open · ${escapeHtml(formatMoney(funding.known_award_value || funding.announced_funding_value))}</dd></div>` : "";
    return `<article class="mission-card">
      <div class="mission-head"><span>${escapeHtml(item.kind)}</span><div class="badges"><span class="badge ${escapeHtml(item.priority)}">${escapeHtml(item.priority)}</span><span class="badge ${escapeHtml(item.status)}">${escapeHtml(item.status)}</span></div></div>
      <h3><a href="${escapeHtml(safeUrl(item.official_url))}" target="_blank" rel="noopener">${escapeHtml(item.name)}</a></h3>
      <p>${escapeHtml(item.objective)}</p>
      <dl class="mission-facts">
        <div><dt>Lead</dt><dd>${escapeHtml((item.lead_agencies || []).join(", ") || "Not listed")}</dd></div>
        <div><dt>Next milestone</dt><dd>${next ? `${escapeHtml(formatShortDate(next.target_date))} · ${escapeHtml(next.title)}` : "No dated milestone published"}</dd></div>
        ${fundingFact}
      </dl>
      <div class="profile-themes">${(item.domains || []).slice(0, 4).map(value => `<span>${escapeHtml(value)}</span>`).join("")}${parent}</div>
      ${update ? `<a class="mission-update" href="${escapeHtml(safeUrl(update.url || item.official_url))}" target="_blank" rel="noopener">Latest: ${escapeHtml(update.title)} →</a>` : ""}
    </article>`;
  }).join("") : '<div class="empty-state">No federal missions are configured.</div>';

  const candidateDetails = document.getElementById("mission-candidates");
  candidateDetails.hidden = !candidates.length;
  candidateDetails.querySelector("summary").textContent = `${candidates.length} possible new mission${candidates.length === 1 ? "" : "s"} awaiting review`;
  document.getElementById("mission-candidate-list").innerHTML = candidates.map(item =>
    `<a href="${escapeHtml(safeUrl(item.url))}" target="_blank" rel="noopener"><strong>${escapeHtml(item.title)}</strong><span>${escapeHtml(formatShortDate(item.date))} · ${escapeHtml(item.source || "official source")}</span></a>`
  ).join("");
}

function renderFunding(payload){
  const summary = payload.summary || {};
  const records = payload.records || [];
  const portfolios = (payload.mission_portfolios || []).filter(item => item.record_count);
  document.getElementById("funding-summary").textContent = `${summary.linked_records || 0} mission-linked · ${summary.open_opportunities || 0} open`;
  document.getElementById("funding-report-link").href = safeUrl(`${state.data.repository_url}/blob/main/reports/federal-funding.md`);
  document.getElementById("funding-metrics").innerHTML = [
    ["Known award value",formatMoney(summary.known_award_value)],
    ["Open opportunities",summary.open_opportunities || 0],
    ["Missions with activity",`${summary.missions_with_activity || 0} / ${summary.tracked_missions || 0}`],
    ["Recipients & contractors",summary.unique_recipients_and_contractors || 0]
  ].map(([label,value]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("");
  renderOpportunityRadar(payload);
  renderRelationshipExplorer(payload);
  renderContractors(payload);
  const order = {open:0,forecasted:1,awarded:2,announced:3,closed:4};
  const visible = [...records].sort((a,b) => (order[a.status] ?? 9) - (order[b.status] ?? 9) || (b.strategic_significance_score || 0) - (a.strategic_significance_score || 0)).slice(0,6);
  document.getElementById("funding-grid").innerHTML = visible.length ? visible.map(item => {
    const missions = (item.mission_links || []).map(link => link.mission_name);
    const organization = item.recipient || item.awardee || item.awarding_agency || item.funding_agency || "Organization not listed";
    return `<article class="funding-card">
      <div class="funding-head"><span class="funding-type">${escapeHtml(String(item.record_type || "record").replaceAll("_"," "))}</span><span class="funding-status ${escapeHtml(item.status || "open")}">${escapeHtml(item.status || "open")}</span></div>
      <h3><a href="${escapeHtml(safeUrl(item.url))}" target="_blank" rel="noopener">${escapeHtml(item.title)}</a></h3>
      <p>${escapeHtml(organization)}</p>
      <dl><div><dt>Value</dt><dd>${escapeHtml(formatMoney(item.amount))}</dd></div><div><dt>Close / date</dt><dd>${escapeHtml(formatShortDate(item.close_date || item.date))}</dd></div></dl>
      <div class="funding-links">${missions.length ? missions.map(name => `<span>${escapeHtml(name)}</span>`).join("") : "<span>Not mission-linked</span>"}</div>
      <footer><span>${item.related_patent_count || 0} patent match${item.related_patent_count === 1 ? "" : "es"}</span><b>${item.strategic_significance_score || 0} · ${escapeHtml(item.significance_label || "monitor")}</b></footer>
    </article>`;
  }).join("") : '<div class="empty-state">No funding or procurement records have been collected yet. USAspending and Grants.gov run without credentials; SAM.gov additionally requires SAM_GOV_API_KEY.</div>';
  document.getElementById("funding-portfolios").innerHTML = portfolios.slice(0,6).map(item => `<span><strong>${escapeHtml(item.mission_name)}</strong>${item.record_count} records · ${item.open_opportunities} open · ${item.related_patent_count || 0} analytical patent matches</span>`).join("");
}

function renderOpportunityRadar(payload){
  const summary = payload.summary || {};
  const opportunities = payload.opportunity_radar || [];
  document.getElementById("opportunity-summary").textContent =
    `${opportunities.length} ranked · ${summary.closing_within_30_days || 0} closing ≤30 days · ${summary.new_since_yesterday || 0} new`;
  const visible = opportunities.filter(item => {
    if (state.opportunityFilter === "closing") return ["closing_soon","closing_this_month"].includes(item.deadline_status);
    if (state.opportunityFilter === "new") return item.new_since_yesterday;
    if (state.opportunityFilter === "mission") return (item.mission_links || []).length;
    return true;
  }).slice(0,8);
  document.getElementById("opportunity-radar").innerHTML = visible.length ? visible.map(item => {
    const missions = (item.mission_links || []).map(link => link.mission_name);
    const domains = item.technology_domains || [];
    const deadline = item.days_to_close == null
      ? "Deadline not reported"
      : item.days_to_close === 0
        ? "Closes today"
        : item.days_to_close > 0
          ? `${item.days_to_close} days remaining`
          : "Closed";
    const agency = item.awarding_agency || item.funding_agency || "Agency not listed";
    return `<article class="opportunity-card ${escapeHtml(item.deadline_status || "")}">
      <div class="opportunity-rank"><span>#${item.radar_rank || "—"}</span><strong>${item.opportunity_score || 0}</strong><small>${escapeHtml(item.opportunity_label || "monitor")}</small></div>
      <div class="opportunity-body">
        <div class="opportunity-meta"><span>${escapeHtml(String(item.record_type || "opportunity").replaceAll("_"," "))}</span><span class="deadline-pill ${escapeHtml(item.deadline_status || "")}">${escapeHtml(deadline)}</span>${item.new_since_yesterday ? '<span class="new-tag">NEW</span>' : ""}</div>
        <h3><a href="${escapeHtml(safeUrl(item.url))}" target="_blank" rel="noopener">${escapeHtml(item.title)}</a></h3>
        <p>${escapeHtml(agency)} · ${escapeHtml(formatMoney(item.amount))}</p>
        <div class="opportunity-tags">${missions.map(name => `<span class="mission-tag">${escapeHtml(name)}</span>`).join("")}${domains.map(name => `<span>${escapeHtml(name)}</span>`).join("")}</div>
        <div class="opportunity-action"><b>Recommended action</b><span>${escapeHtml(item.recommended_action || "Review fit and requirements.")}</span></div>
      </div>
    </article>`;
  }).join("") : '<div class="empty-state">No open opportunities match this view.</div>';
}

function renderDecisionCenter(payload, changePayload = {}){
  const remoteItems = payload.items || [];
  const remoteIds = new Set(remoteItems.map(item => item.decision_id));
  const retainedItems = Object.values(state.analystDecisions)
    .filter(record => ["deferred","escalated"].includes(record?.disposition) && record.item && !remoteIds.has(record.decision_id))
    .map(record => ({...record.item, retained_locally:true}));
  const itemsById = new Map([...remoteItems,...retainedItems].map(item => [item.decision_id,item]));
  const items = [...itemsById.values()];
  const isHandled = item => ["reviewed","dismissed"].includes(state.analystDecisions[item.decision_id]?.disposition);
  const filtered = items.filter(item => {
    if (state.decisionFilter === "handled") return isHandled(item);
    if (state.decisionFilter === "open") return !isHandled(item);
    return item.queue_type === state.decisionFilter;
  });
  const openItems = items.filter(item => !isHandled(item));
  const critical = openItems.filter(item => item.priority === "critical").length;
  document.getElementById("analyst-decision-summary").textContent =
    `${openItems.length} open · ${critical} critical · ${Object.keys(state.analystDecisions).length} local actions`;
  const queueLabels = {
    amendment_revalidation: "Amendment",
    authoritative_change: "Government",
    claim_conflict: "Conflict"
  };
  const list = document.getElementById("analyst-decision-list");
  if (!filtered.length) {
    const message = state.decisionFilter === "handled"
      ? "No reviewed or dismissed decisions are stored in this browser."
      : state.decisionFilter === "open"
        ? "No open analyst decisions. The queue will repopulate when material evidence changes."
        : "No decisions currently match this queue.";
    if (state.decisionFilter === "open") {
      const cleared = recentlyClearedChanges(changePayload);
      const comparison = changePayload.comparison_started_at
        ? `Since ${formatDate(changePayload.comparison_started_at)}`
        : "Since the prior successful run";
      const clearedList = cleared.items.map(item =>
        `<a href="${escapeHtml(safeUrl(item.url))}" target="_blank" rel="noopener"><span>${escapeHtml(item.label)}</span><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.detail)}</small></a>`
      ).join("");
      const recent = cleared.total
        ? `<section class="recently-cleared"><div class="recently-cleared-head"><div><span>RECENTLY CLEARED</span><strong>${cleared.total} claim${cleared.total === 1 ? "" : "s"} removed from the action queue</strong></div><small>${escapeHtml(comparison)}</small></div><p>Resolved, superseded, and retracted corrections remain auditable but do not appear as open decisions.</p><div class="recently-cleared-list">${clearedList}</div><a class="section-link" href="${escapeHtml(safeUrl(`${state.data.repository_url}/blob/main/reports/intelligence-changes.md`))}" target="_blank" rel="noopener">Review all cleared changes →</a></section>`
        : `<section class="queue-rules"><span>WHAT WILL APPEAR HERE</span><div><b>Material amendments</b><b>Authoritative government changes</b><b>Unresolved claim conflicts</b></div></section>`;
      list.innerHTML = `<div class="decision-center-empty"><div class="queue-clear-status"><i aria-hidden="true">✓</i><div><strong>Nothing needs analyst action right now</strong><span>${escapeHtml(message)}</span></div></div>${recent}</div>`;
    } else {
      list.innerHTML = `<div class="empty-state decision-center-empty"><strong>Queue clear</strong><span>${escapeHtml(message)}</span></div>`;
    }
    return;
  }
  list.innerHTML = filtered.map(item => {
    const record = state.analystDecisions[item.decision_id] || {};
    const disposition = record.disposition || "open";
    const handled = isHandled(item);
    const evidence = (item.evidence || []).slice(0,4).map(source =>
      `<a href="${escapeHtml(safeUrl(source.url))}" target="_blank" rel="noopener">${escapeHtml(source.title || "Open evidence")} →</a>`
    ).join("");
    const detailEntries = decisionDetailEntries(item.details || {});
    return `<article class="analyst-decision-card ${escapeHtml(item.priority || "medium")} ${handled ? "handled" : ""}">
      <div class="analyst-decision-head"><div><span class="decision-priority ${escapeHtml(item.priority || "medium")}">${escapeHtml(item.priority || "medium")}</span><span class="decision-queue">${escapeHtml(queueLabels[item.queue_type] || item.queue_type || "Decision")}</span></div>${disposition !== "open" ? `<span class="decision-disposition">${escapeHtml(disposition)}</span>` : ""}</div>
      <h3>${escapeHtml(item.title || "Analyst decision")}</h3>
      <p class="analyst-decision-context">${escapeHtml(item.context || "Evidence review")}${item.retained_locally ? " · retained locally" : ""}</p>
      <p class="analyst-decision-why">${escapeHtml(item.why || "New evidence requires review.")}</p>
      <div class="analyst-decision-action"><b>Recommended action</b>${escapeHtml(item.recommended_action || "Review the supporting evidence.")}</div>
      <details class="analyst-decision-detail"><summary>Evidence and decision trace</summary><div class="decision-detail-grid">${detailEntries}${item.observed_at ? `<p><b>Observed:</b> ${escapeHtml(formatDate(item.observed_at))}</p>` : ""}</div><div class="decision-evidence">${evidence || "<span>No direct evidence link is available.</span>"}</div></details>
      <div class="analyst-decision-actions" data-decision-id="${escapeHtml(item.decision_id)}">
        ${decisionActionButton("reviewed","Mark reviewed",disposition)}
        ${decisionActionButton("escalated","Escalate",disposition)}
        ${decisionActionButton("deferred","Defer",disposition)}
        ${decisionActionButton("dismissed","Dismiss",disposition)}
      </div>
    </article>`;
  }).join("");
}

function recentlyClearedChanges(payload){
  const summary = payload.summary || {};
  const groups = [
    ["resolved", "Retracted or resolved"],
    ["superseded", "Superseded"],
    ["conflict_resolved", "Conflict resolved"]
  ];
  const grouped = new Map();
  let total = 0;
  groups.forEach(([key,label]) => (payload[key] || []).forEach(item => {
    total += 1;
    const source = (item.sources || [])[0] || {};
    const title = source.title || item.subject?.label || "Evidence correction";
    const url = source.url || "#decision-center";
    const groupKey = `${key}|${url}|${title}`;
    const existing = grouped.get(groupKey) || {label,title,url,predicates:[],count:0};
    existing.count += 1;
    if (item.predicate) existing.predicates.push(String(item.predicate).replaceAll("_"," "));
    grouped.set(groupKey,existing);
  }));
  const items = [...grouped.values()].slice(0,3).map(item => ({
    ...item,
    detail: `${item.count} claim${item.count === 1 ? "" : "s"}${item.predicates.length ? ` · ${[...new Set(item.predicates)].slice(0,2).join(" · ")}` : ""}`
  }));
  const reportedTotal = Number(summary.resolved || 0) + Number(summary.superseded || 0) + Number(summary.conflicts_resolved || 0);
  return {total:Math.max(total,reportedTotal),items};
}

function decisionActionButton(action, label, disposition){
  return `<button type="button" data-decision-action="${action}" class="${disposition === action ? "selected" : ""}" aria-pressed="${disposition === action}">${label}</button>`;
}

function decisionDetailEntries(details){
  const order = ["previous_value","value","affected_areas","decision_effects","checklist_actions","values","predicate","predicates","record_date","awarding_agency","claim_ids","claim_id","impact_id"];
  return order.filter(key => details[key] != null && details[key] !== "" && (!Array.isArray(details[key]) || details[key].length)).map(key => {
    const label = key.replaceAll("_"," ").replace(/\b\w/g, value => value.toUpperCase());
    const raw = details[key];
    const value = Array.isArray(raw) ? raw.join(" · ") : typeof raw === "object" ? JSON.stringify(raw) : String(raw);
    return `<p><b>${escapeHtml(label)}:</b> ${escapeHtml(value)}</p>`;
  }).join("");
}

function renderDecisionBriefs(payload){
  const briefs = payload.briefs || [];
  const summary = payload.summary || {};
  document.getElementById("decision-summary").textContent =
    `${summary.priority_qualification || 0} priority · ${summary.qualify || 0} qualify`;
  document.getElementById("decision-report-link").href =
    safeUrl(`${state.data.repository_url}/blob/main/reports/bid-no-bid.md`);
  document.getElementById("decision-grid").innerHTML = briefs.length ? briefs.slice(0,6).map(item => `
    <article class="decision-card ${escapeHtml(String(item.provisional_gate || "hold").replaceAll(" ","-"))}">
      <div class="decision-head"><span>${escapeHtml(item.provisional_gate || "hold")}</span><strong>${item.public_evidence_score ?? item.decision_score ?? 0}</strong></div>
      <h3><a href="${escapeHtml(safeUrl(item.url))}" target="_blank" rel="noopener">${escapeHtml(item.title)}</a></h3>
      <p>${escapeHtml(item.agency || "Agency not listed")} · ${escapeHtml(formatShortDate(item.deadline))}</p>
      ${item.decision_freshness?.status === "revalidation_required" ? '<div class="document-flags"><span class="amendment">Decision revalidation required</span></div>' : ""}
      <div class="evidence-meter"><i style="width:${Math.max(0,Math.min(100,Number(item.evidence_completeness || 0)))}%"></i></div>
      <small>${item.evidence_completeness || 0}% evidence completeness</small>
      <ul>${(item.required_actions || []).slice(0,3).map(value => `<li>${escapeHtml(value)}</li>`).join("")}</ul>
      ${item.decision_trace ? `<details class="decision-trace"><summary>Explain this score</summary>${(item.decision_trace.components || []).map(component => `<p><b>${Number(component.points || 0) >= 0 ? "+" : ""}${Number(component.points || 0)}</b>${escapeHtml(String(component.code || "component").replaceAll("_"," "))}<span>${escapeHtml((component.basis || []).join("; "))}</span></p>`).join("")}<small>Trace ${escapeHtml(item.decision_trace.trace_hash || "unavailable")}</small></details>` : ""}
    </article>
  `).join("") : '<div class="empty-state">No provisional decision briefs are available yet.</div>';
}

function renderPursuits(payload){
  const pursuits = payload.pursuits || [];
  const summary = payload.summary || {};
  document.getElementById("pursuit-summary").textContent =
    `${summary.active || 0} active · ${summary.managed || 0} managed · ${summary.decisions_revalidation_required || 0} to revalidate`;
  document.getElementById("pursuit-report-link").href =
    safeUrl(`${state.data.repository_url}/blob/main/reports/pursuits.md`);
  document.getElementById("pursuit-board").innerHTML = pursuits.length ? pursuits.slice(0,12).map(item => {
    const next = item.next_milestone?.name || (item.managed ? "No next milestone recorded" : "Assign owner and qualify");
    const total = Number(item.checklist_total || 0);
    const complete = Number(item.checklist_complete || 0);
    const deadline = item.deadline ? formatShortDate(item.deadline) : "No deadline";
    return `<article class="pursuit-card ${escapeHtml(item.stage || "watch")}">
      <div class="pursuit-head"><span>${escapeHtml(item.stage || "watch")}</span>${item.managed ? '<b class="managed-tag">MANAGED</b>' : '<b class="candidate-tag">CANDIDATE</b>'}</div>
      <h3><a href="${escapeHtml(safeUrl(item.url))}" target="_blank" rel="noopener">${escapeHtml(item.title || "Untitled opportunity")}</a></h3>
      <p>${escapeHtml(item.agency || "Agency not listed")} · ${escapeHtml(deadline)}</p>
      ${item.decision_revalidation_required ? `<div class="document-flags"><span class="amendment">Revalidate decision · ${item.impacted_checklist_items || 0} checklist impact${item.impacted_checklist_items === 1 ? "" : "s"}</span></div>` : ""}
      <dl><div><dt>Owner</dt><dd>${escapeHtml(item.owner || "Unassigned")}</dd></div><div><dt>Public score</dt><dd>${item.public_evidence_score ?? item.decision_score ?? 0}</dd></div></dl>
      <div class="pursuit-next"><b>Next</b><span>${escapeHtml(next)}</span></div>
      ${total ? `<div class="evidence-meter"><i style="width:${Math.max(0,Math.min(100,Number(item.checklist_percent || 0)))}%"></i></div><small>${complete} of ${total} checklist items complete</small>` : ""}
    </article>`;
  }).join("") : '<div class="empty-state">No pursuits or qualification candidates are available yet.</div>';
}

function renderProcurementDocuments(payload){
  const opportunities = payload.opportunities || [];
  const summary = payload.summary || {};
  document.getElementById("document-summary").textContent =
    `${summary.documents_extracted || 0} extracted · ${summary.material_amendment_impacts || 0} material impacts`;
  document.getElementById("document-report-link").href =
    safeUrl(`${state.data.repository_url}/blob/main/reports/procurement-intelligence.md`);
  document.getElementById("document-grid").innerHTML = opportunities.length ? opportunities.slice(0,6).map(item => {
    const activeDocuments = (item.documents || []).filter(doc => doc.active !== false);
    const extracted = activeDocuments.filter(doc => doc.extraction_status === "extracted").length;
    const impact = item.latest_amendment_impact || {};
    const firstChange = (impact.changes || [])[0];
    return `<article class="document-card">
      <div class="document-head"><span>${extracted} / ${activeDocuments.length} extracted</span><strong>${item.document_completeness_score || 0}</strong></div>
      <h3><a href="${escapeHtml(safeUrl(item.url))}" target="_blank" rel="noopener">${escapeHtml(item.title)}</a></h3>
      <p>${escapeHtml(item.agency || "Agency not listed")}</p>
      <div class="document-flags">${impact.material_change_count ? `<span class="amendment">${escapeHtml(impact.highest_materiality || "material")} · ${impact.material_change_count} impact${impact.material_change_count === 1 ? "" : "s"}</span>` : item.new_amendment ? '<span class="amendment">New amendment · comparison needed</span>' : ""}${item.changed_document ? "<span>Changed file</span>" : ""}</div>
      ${firstChange ? `<p class="impact-summary">${escapeHtml(firstChange.summary || "Material amendment change observed")}</p>` : ""}
      <ul>${(item.requirements || []).slice(0,3).map(value => `<li>${escapeHtml(value)}</li>`).join("") || "<li>No requirement excerpt extracted.</li>"}</ul>
    </article>`;
  }).join("") : '<div class="empty-state">No linked procurement documents have been analyzed yet.</div>';
}

function renderEvidenceLedger(claimPayload, changePayload, temporalPayload={}){
  const claimSummary = claimPayload.summary || {};
  const changeSummary = changePayload.summary || {};
  const temporalSummary = temporalPayload.summary || {};
  document.getElementById("evidence-ledger-summary").textContent =
    `${claimSummary.active_claims || 0} claims · ${changeSummary.material_changes || 0} changes · ${temporalSummary.historical_discoveries || 0} historical discoveries`;
  document.getElementById("claim-ledger-report-link").href =
    safeUrl(`${state.data.repository_url}/blob/main/reports/claim-ledger.md`);
  document.getElementById("changes-report-link").href =
    safeUrl(`${state.data.repository_url}/blob/main/reports/intelligence-changes.md`);
  document.getElementById("temporal-report-link").href =
    safeUrl(`${state.data.repository_url}/blob/main/reports/temporal-intelligence.md`);
  const rawChanges = [
    ...(changePayload.conflict_opened || changePayload.conflicts || []).map(item => ({...item, change_type:"conflict"})),
    ...(changePayload.conflict_resolved || []).map(item => ({...item, change_type:"resolved"})),
    ...(changePayload.superseded || []),
    ...(changePayload.changed || []),
    ...(changePayload.added || []),
    ...(changePayload.resolved || [])
  ];
  const changes = (temporalPayload.priority_events || []).length
    ? temporalPayload.priority_events.slice(0,8)
    : rawChanges.slice(0,8);
  document.getElementById("change-feed").innerHTML = changePayload.baseline_initialized
    ? '<div class="empty-state">Baseline initialized. Material changes will appear after the next successful comparison.</div>'
    : changes.length ? changes.map(item => {
        const subject = item.subject?.label || item.subject_label || "Tracked claim";
        const value = item.value ?? item.values ?? item.object?.label ?? "See evidence";
        const temporal = item.temporal || {};
        return `<article class="change-card ${escapeHtml(item.change_type || "changed")}"><div class="change-card-head"><strong>${escapeHtml(subject)}</strong>${temporal.label ? `<em>${escapeHtml(temporal.label)}</em>` : ""}</div><span>${escapeHtml(String(item.predicate || "claim").replaceAll("_"," "))}</span><small>${escapeHtml(Array.isArray(value) ? value.join(" ↔ ") : String(value))}</small>${temporal.explanation ? `<p>${escapeHtml(temporal.explanation)}</p>` : ""}</article>`;
      }).join("")
    : '<div class="empty-state">No material claim changes since the prior baseline.</div>';
  const claims = (claimPayload.claims || []).filter(item =>
    item.status === "conflicted"
    || item.predicate === "qualification_gate"
    || ["authoritative","analyst"].includes(item.authority)
  ).slice(0,8);
  document.getElementById("evidence-claim-grid").innerHTML = claims.length ? claims.map(item => {
    const value = item.value ?? item.object?.label ?? "Relationship assertion";
    const source = (item.sources || [])[0];
    return `<article class="evidence-claim"><div class="evidence-claim-head"><strong>${escapeHtml(item.subject?.label || "Tracked subject")}</strong><span class="authority-tag ${escapeHtml(item.authority || "unknown")}">${escapeHtml(item.authority || "unknown")}</span></div><span>${escapeHtml(String(item.predicate || "claim").replaceAll("_"," "))}: ${escapeHtml(String(value))}</span><small>${escapeHtml(item.basis || item.derivation?.rule || "Direct-source assertion")} · ${escapeHtml(item.claim_id || "")}</small>${source?.url ? `<a href="${escapeHtml(safeUrl(source.url))}" target="_blank" rel="noopener">Open evidence →</a>` : ""}</article>`;
  }).join("") : '<div class="empty-state">No traceable claims are available yet.</div>';
}

function renderRelationshipExplorer(payload){
  const graph = payload.relationship_explorer || { summary: {}, nodes: [], edges: [] };
  const nodes = graph.nodes || [];
  const edges = graph.edges || [];
  const byId = new Map(nodes.map(node => [node.node_id,node]));
  const missions = nodes.filter(node => node.node_type === "mission");
  const missionSelect = document.getElementById("relationship-mission");
  if (!state.relationshipMission || !byId.has(state.relationshipMission)) {
    state.relationshipMission = missions.find(node => (node.record_count || 0) > 0)?.node_id || missions[0]?.node_id || "";
  }
  missionSelect.innerHTML = missions.map(node =>
    `<option value="${escapeHtml(node.node_id)}"${node.node_id === state.relationshipMission ? " selected" : ""}>${escapeHtml(node.label)}</option>`
  ).join("");
  document.getElementById("relationship-summary").textContent =
    `${graph.summary?.nodes || 0} nodes · ${graph.summary?.edges || 0} evidence links`;
  const firstHop = edges.filter(edge => edge.source_node === state.relationshipMission);
  const executionIds = firstHop
    .map(edge => edge.target_node)
    .filter(nodeId => byId.get(nodeId)?.node_type !== "patent");
  const directPatentIds = firstHop
    .map(edge => edge.target_node)
    .filter(nodeId => byId.get(nodeId)?.node_type === "patent");
  const secondHop = edges.filter(edge => executionIds.includes(edge.source_node));
  const contractorIds = secondHop
    .map(edge => edge.target_node)
    .filter(nodeId => byId.get(nodeId)?.node_type === "recipient_or_contractor");
  const thirdHop = edges.filter(edge => contractorIds.includes(edge.source_node));
  const patentIds = [...new Set([
    ...directPatentIds,
    ...thirdHop.map(edge => edge.target_node).filter(nodeId => byId.get(nodeId)?.node_type === "patent")
  ])];
  const selectedMission = byId.get(state.relationshipMission);
  if (!state.relationshipNode || !byId.has(state.relationshipNode)) state.relationshipNode = state.relationshipMission;
  const nodeButton = (node, compact=false) => `<button class="relationship-node ${escapeHtml(node.node_type)}${node.node_id === state.relationshipNode ? " active" : ""}" data-node="${escapeHtml(node.node_id)}">
    <span>${escapeHtml(String(node.node_type).replaceAll("_"," "))}</span>
    <strong>${escapeHtml(node.label || node.identifier)}</strong>
    ${compact ? "" : `<small>${node.amount ? escapeHtml(formatMoney(node.amount)) : node.status ? escapeHtml(node.status) : node.assignee ? escapeHtml(node.assignee) : ""}</small>`}
  </button>`;
  const activityNodes = [...new Set(executionIds)].map(id => byId.get(id)).filter(Boolean).slice(0,8);
  const contractorNodes = [...new Set(contractorIds)].map(id => byId.get(id)).filter(Boolean).slice(0,6);
  const patentNodes = patentIds.map(id => byId.get(id)).filter(Boolean).slice(0,8);
  document.getElementById("relationship-graph").innerHTML = selectedMission ? `
    <div class="relationship-lane mission-lane"><h4>Mission</h4>${nodeButton(selectedMission)}<small>${firstHop.length} direct links</small></div>
    <div class="relationship-arrow" aria-hidden="true">→</div>
    <div class="relationship-lane"><h4>Execution</h4>${activityNodes.length ? activityNodes.map(node => nodeButton(node)).join("") : "<p>No linked execution records.</p>"}</div>
    <div class="relationship-arrow" aria-hidden="true">→</div>
    <div class="relationship-lane connected-lane"><h4>Contractors & patents</h4>${contractorNodes.map(node => nodeButton(node,true)).join("")}${patentNodes.map(node => nodeButton(node,true)).join("") || "<p>No downstream nodes.</p>"}</div>
  ` : '<div class="empty-state">No mission relationships are available.</div>';
  renderRelationshipDetail(graph, byId.get(state.relationshipNode));
  document.querySelectorAll(".relationship-node").forEach(button => button.addEventListener("click", () => {
    state.relationshipNode = button.dataset.node;
    renderRelationshipExplorer(payload);
  }));
}

function renderRelationshipDetail(graph, node){
  const detail = document.getElementById("relationship-detail");
  if (!node) { detail.innerHTML = ""; return; }
  const connections = (graph.edges || []).filter(edge => edge.source_node === node.node_id || edge.target_node === node.node_id);
  const confidence = connections.reduce((counts, edge) => {
    const key = edge.confidence || "unlabeled"; counts[key] = (counts[key] || 0) + 1; return counts;
  }, {});
  detail.innerHTML = `<div><span class="module-kicker">SELECTED ${escapeHtml(String(node.node_type).replaceAll("_"," "))}</span><h4>${escapeHtml(node.label || node.identifier)}</h4><p>${connections.length} connected evidence link${connections.length === 1 ? "" : "s"} · ${Object.entries(confidence).map(([key,value]) => `${value} ${key}`).join(" · ") || "no confidence label"}</p></div>
    <div class="relationship-evidence">${connections.slice(0,5).map(edge => {
      const source = (edge.claim_sources || [])[0];
      return `<span class="${escapeHtml(edge.claim_confidence || edge.confidence || "low")}"><b>${escapeHtml(edge.claim_authority || edge.confidence || "unlabeled")}</b>${escapeHtml(edge.claim_basis || edge.basis || "Relationship evidence")}${source?.url ? `<a href="${escapeHtml(safeUrl(source.url))}" target="_blank" rel="noopener">evidence</a>` : ""}</span>`;
    }).join("")}</div>
    ${node.url ? `<a href="${escapeHtml(safeUrl(node.url))}" target="_blank" rel="noopener">Open source →</a>` : ""}`;
}

function renderContractors(payload){
  const profiles = payload.contractor_profiles || [];
  const query = state.contractorQuery.trim().toLowerCase();
  const visible = profiles.filter(item => [
    item.name,
    ...(item.aliases || []),
    item.uei || "",
    item.entity_enrichment?.legal_business_name || "",
    item.entity_enrichment?.cage_code || "",
    ...(item.agencies || []),
    ...(item.mission_ids || []),
    ...(item.technology_specialties || [])
  ].join(" ").toLowerCase().includes(query)).slice(0,12);
  document.getElementById("contractor-summary").textContent = `${profiles.length} prioritized profiles`;
  document.getElementById("contractor-grid").innerHTML = visible.length ? visible.map(item => {
    const patents = item.related_patents || [];
    const peers = item.network_peers || [];
    const smallBusiness = item.small_business_evidence?.observed
      ? item.small_business_evidence.classifications.join(", ")
      : "Not established";
    const entity = item.entity_enrichment || {};
    const registration = entity.resolution_status === "resolved"
      ? `<a class="entity-badge resolved" href="${escapeHtml(safeUrl(entity.source_url))}" target="_blank" rel="noopener">SAM.GOV VERIFIED</a>`
      : `<span class="entity-badge pending">${escapeHtml(String(entity.resolution_status || "pending").replaceAll("_"," "))}</span>`;
    return `<article class="contractor-card">
      <div class="contractor-head"><div><span>${escapeHtml(item.contractor_label || "observed")}</span><strong>${item.contractor_score || 0}</strong></div><span class="momentum ${escapeHtml(String(item.award_momentum || "stable").replaceAll(" ","-"))}">${escapeHtml(item.award_momentum || "stable")}</span></div>
      <h3>${escapeHtml(item.name)}</h3>
      <p>${escapeHtml(item.incumbency || "observed recipient")} · ${registration}</p>
      <dl><div><dt>Known awards</dt><dd>${escapeHtml(formatMoney(item.known_award_value))}</dd></div><div><dt>Recent 12 months</dt><dd>${item.recent_award_count || 0} · ${escapeHtml(formatMoney(item.recent_award_value))}</dd></div><div><dt>Missions</dt><dd>${(item.mission_ids || []).length}</dd></div><div><dt>Patent matches</dt><dd>${item.related_patent_count || 0}</dd></div></dl>
      <div class="contractor-tags">${(item.technology_specialties || []).slice(0,4).map(value => `<span>${escapeHtml(value)}</span>`).join("")}</div>
      <details class="contractor-profile-detail">
        <summary>Open intelligence profile</summary>
        <div class="contractor-profile-body">
          <section><h4>Identity evidence</h4><p><b>${escapeHtml(entity.legal_business_name || item.name)}</b><span>${escapeHtml(entity.resolution_basis || item.resolution_basis || "Collected name evidence")}</span></p><p>${entity.uei ? `UEI ${escapeHtml(entity.uei)}` : "UEI not resolved"}${entity.cage_code ? ` · CAGE ${escapeHtml(entity.cage_code)}` : ""}</p><p>${escapeHtml((entity.sba_business_types || entity.business_types || []).slice(0,4).join(", ") || smallBusiness)}</p><h4>Corporate hierarchy</h4><p>${escapeHtml(entity.ultimate_parent?.name || entity.immediate_parent?.name || "No parent listed")}</p><h4>Agencies</h4><p>${escapeHtml((item.agencies || []).join(", ") || "Not listed")}</p></section>
          <section><h4>Recent awards</h4>${(item.top_awards || []).slice(0,3).map(award => `<a href="${escapeHtml(safeUrl(award.url))}" target="_blank" rel="noopener"><b>${escapeHtml(formatMoney(award.amount))}</b>${escapeHtml(award.title || "Award")}</a>`).join("") || "<p>No award detail available.</p>"}</section>
          <section><h4>Related patents</h4>${patents.slice(0,3).map(patent => `<a href="${escapeHtml(safeUrl(patent.url))}" target="_blank" rel="noopener">${escapeHtml(patent.title || patent.patent_id)}</a>`).join("") || "<p>No assignee matches.</p>"}</section>
          <section><h4>Peers & potential competitors</h4>${peers.slice(0,3).map(peer => `<p><b>${escapeHtml(peer.name)}</b><span>${escapeHtml(peer.relationship_type)}</span></p>`).join("") || "<p>Not enough shared evidence.</p>"}</section>
        </div>
      </details>
    </article>`;
  }).join("") : '<div class="empty-state">No contractor profiles match this search.</div>';
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
  document.getElementById("patent-summary").textContent = `${summary.families || 0} families · ${summary.applications || 0} applications · ${summary.grants || 0} grants · ranked by significance`;
  document.getElementById("patent-report-link").href = safeUrl(`${state.data.repository_url}/blob/main/reports/patents.md`);
  document.getElementById("patent-grid").innerHTML = patents.length ? patents.slice(0, 6).map(item => {
    const number =
      item.publication_number ||
      item.patent_number ||
      item.application_number ||
      "Patent identifier unavailable";
    const topics = (item.strategic_domains?.length ? item.strategic_domains : item.matched_keywords || []).slice(0, 3);
    const priority = item.significance_label || item.priority || "monitor";
    const trackingLabel = item.tracking_type === "curated" ? "notable" : "automated";
    const assessment = item.assessment ? `<p class="patent-assessment"><strong>Assessment:</strong> ${escapeHtml(item.assessment)}</p>` : "";
    const stage = `${item.document_type || "unknown"} · ${item.legal_status_normalized || "status unknown"}`;
    const intelligence = `${item.family_size || 1} family member${item.family_size === 1 ? "" : "s"} · ${item.citation_count || 0} citations`;
    return `<article class="patent-card"><div class="patent-meta"><span><b class="patent-track">${escapeHtml(trackingLabel)}</b>${escapeHtml(number)}</span><time>${escapeHtml(formatShortDate(item.publication_date))}</time></div><h3><a href="${escapeHtml(safeUrl(item.url))}" target="_blank" rel="noopener">${escapeHtml(item.title)}</a></h3><p class="patent-assignee">${escapeHtml(item.assignee || "Assignee not listed")}</p><div class="patent-intelligence"><span>${escapeHtml(stage)}</span><span>${escapeHtml(intelligence)}</span></div><p>${escapeHtml(item.summary || "No abstract snippet is available.")}</p>${assessment}<div class="patent-footer"><div class="profile-themes">${topics.map(topic => `<span>${escapeHtml(topic)}</span>`).join("")}</div><span class="patent-priority ${escapeHtml(priority)}">${item.strategic_significance_score || 0} · ${escapeHtml(priority)}</span></div></article>`;
  }).join("") : '<div class="empty-state">No patents are configured. Add notable records to the curated portfolio; automated discovery additionally requires USPTO_ODP_API_KEY.</div>';
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

function animateMetrics(){
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  document.querySelectorAll("#briefing.metrics strong").forEach(element => {
    const target = Number(element.textContent);
    if (!Number.isFinite(target) || target <= 0) return;
    const duration = 650;
    const start = performance.now();
    const tick = now => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      element.textContent = Math.round(target * eased);
      if (progress < 1) requestAnimationFrame(tick);
    };
    element.textContent = "0";
    requestAnimationFrame(tick);
  });
}

function setupReveal(){
  if (document.documentElement.dataset.revealSetup || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  document.documentElement.dataset.revealSetup = "true";
  const targets = document.querySelectorAll(
    "#briefing.metrics article,.briefing-panel,.signal-card,.mission-card,.funding-card,.opportunity-card,.contractor-card,.patent-card,.watch-card,.guide-grid article,.milestone-card"
  );
  if (!("IntersectionObserver" in window)) return;
  document.documentElement.classList.add("reveal-ready");
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add("is-visible");
      observer.unobserve(entry.target);
    });
  }, { rootMargin: "0px 0px -35px", threshold: .08 });
  targets.forEach((element,index) => {
    element.classList.add("reveal-item");
    element.style.transitionDelay = `${Math.min(index % 4, 3) * 55}ms`;
    observer.observe(element);
  });
}

document.getElementById("signal-search").addEventListener("input", event => { state.query = event.target.value; if(state.data) renderSignals(); });
document.getElementById("status-filters").addEventListener("click", event => { if(!event.target.dataset.status) return; state.status = event.target.dataset.status; document.querySelectorAll("#status-filters button").forEach(x => x.classList.toggle("active", x === event.target)); if(state.data) renderSignals(); });
document.getElementById("trend-ranges").addEventListener("click", event => { if(!event.target.dataset.days) return; state.trendDays = event.target.dataset.days === "all" ? "all" : Number(event.target.dataset.days); document.querySelectorAll("#trend-ranges button").forEach(x => x.classList.toggle("active", x === event.target)); if(state.data) renderTrend(); });
document.getElementById("watch-tabs").addEventListener("click", event => { if(!event.target.dataset.watch) return; state.watchType = event.target.dataset.watch; document.querySelectorAll("#watch-tabs button").forEach(x => x.classList.toggle("active", x === event.target)); if(state.data) renderWatch(); });
document.getElementById("compare-first").addEventListener("change", event => { state.compareFirst = event.target.value; if(state.data) renderComparison(); });
document.getElementById("compare-second").addEventListener("change", event => { state.compareSecond = event.target.value; if(state.data) renderComparison(); });
document.getElementById("opportunity-filters").addEventListener("click", event => {
  if (!event.target.dataset.opportunity) return;
  state.opportunityFilter = event.target.dataset.opportunity;
  document.querySelectorAll("#opportunity-filters button").forEach(button => button.classList.toggle("active", button === event.target));
  if (state.data) renderOpportunityRadar(state.data.federal_funding || {});
});
document.getElementById("analyst-decision-filters").addEventListener("click", event => {
  const button = event.target.closest("[data-decision-filter]");
  if (!button) return;
  state.decisionFilter = button.dataset.decisionFilter;
  document.querySelectorAll("#analyst-decision-filters button").forEach(item => item.classList.toggle("active", item === button));
  if (state.data) renderDecisionCenter(state.data.decision_center || {});
});
document.getElementById("analyst-decision-list").addEventListener("click", event => {
  const button = event.target.closest("[data-decision-action]");
  const actionGroup = button?.closest("[data-decision-id]");
  if (!button || !actionGroup || !state.data) return;
  const decisionId = actionGroup.dataset.decisionId;
  const action = button.dataset.decisionAction;
  const current = state.analystDecisions[decisionId];
  if (current?.disposition === action) {
    delete state.analystDecisions[decisionId];
  } else {
    const remoteItem = (state.data.decision_center?.items || []).find(item => item.decision_id === decisionId);
    const snapshot = remoteItem || current?.item;
    state.analystDecisions[decisionId] = {
      decision_id: decisionId,
      disposition: action,
      updated_at: new Date().toISOString(),
      item: snapshot
    };
  }
  persistAnalystDecisions();
  renderDecisionCenter(state.data.decision_center || {});
});
document.getElementById("export-analyst-decisions").addEventListener("click", () => {
  const records = Object.values(state.analystDecisions).sort((a,b) => String(a.decision_id).localeCompare(String(b.decision_id)));
  const content = JSON.stringify({version:1,exported_at:new Date().toISOString(),decisions:records},null,2);
  const url = URL.createObjectURL(new Blob([content],{type:"application/json"}));
  const link = document.createElement("a");
  link.href = url;
  link.download = `quantum-scout-analyst-decisions-${new Date().toISOString().slice(0,10)}.json`;
  link.click();
  URL.revokeObjectURL(url);
});
document.getElementById("clear-analyst-decisions").addEventListener("click", () => {
  if (!Object.keys(state.analystDecisions).length || !window.confirm("Clear all analyst decisions stored in this browser?")) return;
  state.analystDecisions = {};
  try { window.localStorage.removeItem(ANALYST_DECISION_STORAGE_KEY); } catch { /* Browser-local storage may be unavailable. */ }
  if (state.data) renderDecisionCenter(state.data.decision_center || {});
});
document.getElementById("relationship-mission").addEventListener("change", event => {
  state.relationshipMission = event.target.value;
  state.relationshipNode = event.target.value;
  if (state.data) renderRelationshipExplorer(state.data.federal_funding || {});
});
document.getElementById("contractor-search").addEventListener("input", event => {
  state.contractorQuery = event.target.value;
  if (state.data) renderContractors(state.data.federal_funding || {});
});

const navToggle = document.querySelector(".nav-toggle");
const navLinks = document.getElementById("primary-links");
const closeNav = () => { navLinks?.classList.remove("open"); navToggle?.setAttribute("aria-expanded", "false"); };
navToggle?.addEventListener("click", () => { const open = navLinks.classList.toggle("open"); navToggle.setAttribute("aria-expanded", String(open)); });
navLinks?.addEventListener("click", event => { if(event.target.closest("a")) closeNav(); });
document.addEventListener("keydown", event => { if(event.key === "Escape") closeNav(); });

const landingHero = document.querySelector(".hero:not(.profile-hero)");
if (landingHero && window.matchMedia("(pointer: fine)").matches && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  landingHero.addEventListener("pointermove", event => {
    const bounds = landingHero.getBoundingClientRect();
    landingHero.style.setProperty("--pointer-x", `${((event.clientX - bounds.left) / bounds.width * 100).toFixed(1)}%`);
    landingHero.style.setProperty("--pointer-y", `${((event.clientY - bounds.top) / bounds.height * 100).toFixed(1)}%`);
  });
  landingHero.addEventListener("pointerleave", () => {
    landingHero.style.setProperty("--pointer-x", "74%");
    landingHero.style.setProperty("--pointer-y", "38%");
  });
}

const revealHashSection = () => {
  if (!window.location.hash) return;
  const target = document.querySelector(window.location.hash);
  for (let parent = target?.closest("details"); parent; parent = parent.parentElement?.closest("details")) parent.open = true;
  if (target) {
    const scrollToTarget = () => target.scrollIntoView({block:"start"});
    requestAnimationFrame(() => requestAnimationFrame(scrollToTarget));
    setTimeout(scrollToTarget, 120);
  }
};
window.addEventListener("hashchange", revealHashSection);
revealHashSection();
