// 커리어인연 화면 동작
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const STEMS = "갑을병정무기경신임계", STEM_HJ = "甲乙丙丁戊己庚辛壬癸";
const BRANCHES = "자축인묘진사오미신유술해", BRANCH_HJ = "子丑寅卯辰巳午未申酉戌亥";
const ELEM_HJ = { 목: "木", 화: "火", 토: "土", 금: "金", 수: "水" };
const ELEM_COLOR = { 목: "var(--wood)", 화: "var(--fire)", 토: "var(--earth)", 금: "var(--metal)", 수: "var(--water)" };
const HOURS = ["자시 23:30~01:29", "축시 01:30~03:29", "인시 03:30~05:29", "묘시 05:30~07:29", "진시 07:30~09:29", "사시 09:30~11:29",
  "오시 11:30~13:29", "미시 13:30~15:29", "신시 15:30~17:29", "유시 17:30~19:29", "술시 19:30~21:29", "해시 21:30~23:29"];

const state = { review: null, saju: null, ranked: null, applied: new Set(), shown: 8 };

// ─── 시연용 프로필 (가상 인물) ───
const SAMPLES = {
  linkedin: `김하늘 · Backend Engineer @ 넥스트소프트
서울, 대한민국 · 1촌 312명

[소개]
사용자가 체감하는 속도를 줄이는 백엔드를 만듭니다. Python과 AWS 기반 API 개발 4년차.

[경력]
넥스트소프트 · 백엔드 개발자 (2022.03 ~ 현재, 3년 8개월)
- FastAPI로 주문/결제 API 개발 및 운영
- PostgreSQL 쿼리 튜닝으로 응답 속도 개선
- Docker, AWS ECS로 배포 자동화
- 사내 LLM 챗봇 PoC (LangChain, Bedrock) 참여

코드웨이브 · 인턴 (2021.07 ~ 2021.12)
- Django 관리자 페이지 유지보수

[기술]
Python, FastAPI, Django, PostgreSQL, Docker, AWS, LangChain, Git

[자격증]
AWS Solutions Architect – Associate`,
  remember: `김하늘
넥스트소프트 | 개발팀 | 선임 (백엔드)
경력 4년 · 서울

경력 사항
· 넥스트소프트 백엔드 개발 (2022.03~재직중)
  주문 API 개발, 배포 자동화 담당
· 코드웨이브 인턴 (2021.07~2021.12)

보유 스킬: Python, FastAPI, AWS, Docker, PostgreSQL, LangChain
관심 직무: 백엔드, AI 서비스 개발`,
};

// ─── 공통 ───
function toast(msg, err = false) {
  const t = $("#toast");
  t.textContent = msg; t.className = "toast show" + (err ? " err" : "");
  clearTimeout(toast._t); toast._t = setTimeout(() => (t.className = "toast"), 2800);
}
function loading(on, text = "분석 중...") { $("#loading").hidden = !on; $("#loadingText").textContent = text; }
async function api(path, body, method) {
  const res = await fetch(path, body ? { method: method || "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : { method: method || "GET" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `오류 ${res.status}`);
  return data;
}
function go(name) {
  $$(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${name}`));
  $$(".step").forEach((s) => s.classList.toggle("active", s.dataset.go === name));
  if (name === "apps") renderApps();
  if (name === "jobs") loadJobs();
  if (name === "recruiter") renderRecruiter();
  if (name === "overview") renderOverview();
  if (name === "resume") { renderRuSide(); renderRuResult(); }
  if (name === "liscan") { renderLsAcct(); if (!$("#lsFeedPane").hidden) loadFeed(); if (!$("#lsCoPane").hidden) loadCompanies(); }
  window.scrollTo({ top: 0, behavior: "smooth" });
}
function unlock(...names) { names.forEach((n) => { const b = $(`.step[data-go="${n}"]`); b.disabled = false; }); }
function markDone(name) { $(`.step[data-go="${name}"]`).classList.add("done"); }

document.addEventListener("click", (e) => {
  const g = e.target.closest("[data-go]");
  if (g && !g.disabled) go(g.dataset.go);
});

// ─── 1. 프로필 입력 ───
const hourSel = $("#hour");
HOURS.forEach((h, i) => {
  const o = document.createElement("option");
  o.value = i * 2; // 각 시진의 대표 시각 (자시=0시, 축시=2시 ...)
  o.textContent = h;
  hourSel.append(o);
});
hourSel.value = "8"; // 진시 기본값 (예시)
// 학교 자동완성 목록 (추천인이 등록된 학교)
fetch("/api/network", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
  .then((r) => r.json()).then((d) => {
    $("#schoolList").innerHTML = (d.schools || []).map((s) => `<option value="${esc(s)}">`).join("");
    $("#hometown").innerHTML += (d.regions || []).map((s) => `<option>${esc(s)}</option>`).join("");
  })
  .catch(() => {});

$("#profileText").addEventListener("input", (e) => ($("#charCount").textContent = e.target.value.length));

// 입력 확인 목록: 무엇이 채워졌고 무엇이 남았는지 버튼 옆에서 바로 보여 줌
function updateReady() {
  const len = $("#profileText").value.trim().length;
  const items = [
    { ok: len >= 30, need: true, t: len >= 30 ? `레주메 ${len}자` : `레주메 ${len}/30자`, go: "#profileText" },
    { ok: !!$("#birth").value, need: true, t: "생년월일", go: "#birth" },
    { ok: $("#hour").value !== "", need: false, t: "태어난 시간", go: "#hour" },
    { ok: !!($("#school").value || $("#hometown").value || $("#pastCompanies").value), need: false, t: "학교·지역·이전 회사", go: "#school" },
  ];
  const done = items.filter((i) => i.need && i.ok).length;
  $("#ready").innerHTML = `<li class="ready-sum ${done === 2 ? "ok" : ""}">${done === 2 ? "분석 준비 완료" : `필수 ${done}/2`}</li>` +
    items.map((i) => `<li class="${i.ok ? "ok" : i.need ? "need" : "opt"}"><button type="button" data-focus="${i.go}">${i.ok ? "✓" : i.need ? "!" : "+"} ${i.t}${i.need || i.ok ? "" : " (선택)"}</button></li>`).join("");
  $("#analyzeBtn").classList.toggle("dim", done < 2);
}
["#profileText", "#birth", "#hour", "#school", "#hometown", "#pastCompanies"].forEach((id) => ["input", "change"].forEach((ev) => $(id).addEventListener(ev, updateReady)));
document.addEventListener("click", (e) => {
  const f = e.target.closest("[data-focus]");
  if (!f) return;
  const el = $(f.dataset.focus);
  el.scrollIntoView({ behavior: "smooth", block: "center" }); setTimeout(() => el.focus(), 300);
});
updateReady();
$$("[data-import]").forEach((b) => b.addEventListener("click", () => {
  const ta = $("#profileText");
  ta.value = SAMPLES[b.dataset.import];
  ta.dispatchEvent(new Event("input"));
  if (!$("#school").value) $("#school").value = "서울대학교";              // 예시 인물의 학교·전 직장
  if (!$("#pastCompanies").value) $("#pastCompanies").value = "넥스트소프트, 삼성SDS";
  if (!$("#hometown").value) $("#hometown").value = "부산";
  updateReady();
  toast(`${b.dataset.import === "linkedin" ? "링크드인" : "리멤버"} 예시 프로필을 불러왔어요 (시연용)`);
}));

function bindSeg(id, cb) {
  $$(`#${id} button`).forEach((b) => b.addEventListener("click", () => {
    $$(`#${id} button`).forEach((x) => x.classList.toggle("on", x === b));
    cb && cb(b.dataset.v);
  }));
}
let calendar = "solar";
bindSeg("calendar", (v) => { calendar = v; $("#leapWrap").hidden = v !== "lunar"; });

$("#analyzeBtn").addEventListener("click", async () => {
  const text = $("#profileText").value.trim();
  if (text.length < 30) return toast("프로필 내용을 30자 이상 넣어 주세요.", true);
  if (!$("#birth").value) return toast("생년월일을 입력해 주세요.", true);
  const hour = $("#hour").value === "" ? null : Number($("#hour").value);
  loading(true, "AI가 이력서를 읽고 사주를 풀고 있어요...");
  try {
    const needSum = !(state.skipSummary && state.summary); state.skipSummary = false;
    const [review, saju, net, summary] = await Promise.all([
      api("/api/resume/review", { text }),
      api("/api/saju", { birth: $("#birth").value, hour, calendar, leap: $("#leap").checked }),
      api("/api/network", netInput()),
      needSum ? api("/api/resume/summary", { text, prev_text: state.appliedText && state.appliedText !== text ? state.appliedText : null }).catch(() => null) : Promise.resolve(state.summary),
    ]);
    state.summary = summary; state.appliedText = text;
    state.review = review; state.saju = saju; state.net = net.by_company || {}; state.ranked = null; state.ov = null; state.ovHtml = null;
    renderReview(); renderSaju();
    markDone("profile"); unlock("review", "saju", "overview");
    saveResumeIfConsented(review);   // 동의했을 때만 암호화 보관
    go("review");
  } catch (err) {
    toast(err.message, true);
  } finally { loading(false); }
});

// ─── 2. 첨삭 ───
function renderReview() {
  setTimeout(renderReviewFocus, 0);
  const r = state.review;
  $("#reviewBody").innerHTML = `
    ${r.ai_error ? `<div class="ai-warn">⚠ ${esc(r.ai_error)}. 잠시 뒤 다시 분석하면 AI 첨삭을 받을 수 있어요.</div>` : ""}
    <div class="review-top">
      <div class="card score-card">
        <div class="ring-chart" style="--p:${r.score}"><div><div><b>${r.score}</b><small>/ 100</small></div></div></div>
        <div class="score-label">이력서 완성도</div>
      </div>
      <div class="card">
        <p class="summary">${esc(r.summary)}</p>
        <div class="meta-row">
          <div class="meta">총 경력<b>${r.years}년</b></div>
          <div class="meta">직급 레벨<b>${esc(r.level)}</b></div>
          <div class="meta">보유 기술<b>${r.skills.length}개</b></div>
        </div>
        <div class="skills">${r.skills.map((s) => `<span class="skill">${esc(s)}</span>`).join("")}</div>
      </div>
    </div>
    <div class="grid-2" style="grid-template-columns:1fr 1fr">
      <div class="card"><h3>강점</h3><ul class="list good">${r.strengths.map((s) => `<li>${esc(s)}</li>`).join("")}</ul></div>
      <div class="card"><h3>보완하면 좋은 점</h3><ul class="list bad">${r.weaknesses.map((s) => `<li>${esc(s)}</li>`).join("")}</ul></div>
    </div>
    <div class="card" style="margin-top:20px">
      <h3>이렇게 고쳐 써 보세요</h3>
      ${r.rewrites.map((w) => `<div class="rewrite"><div class="before">${esc(w.before)}</div><div class="arrow">→</div><div class="after">${esc(w.after)}</div></div>`).join("")}
    </div>
    <div class="rv-focus"><div class="rv-sum-head"><h3>인터뷰 전략 — 최근 업무를 이렇게 강조하세요 <small>회사별 전략은 회사 대시보드 "인터뷰 전략" 탭</small></h3></div><div id="rvFocus"></div></div>
    ${state.summary ? `<div class="rv-sum">
      <div class="rv-sum-head"><h3>레주메 분석 요약 <small>채용 담당자에게는 이 요약이 전달돼요 (원문 X)</small></h3>
        <button class="btn-ghost sm" data-go="resume">↻ 레주메 업데이트</button></div>
      ${summaryHtml(state.summary, { gaps: true })}</div>` : ""}`;
}

// ─── 3. 사주 ───
function charBox(ch, isStem) {
  const idx = (isStem ? STEMS : BRANCHES).indexOf(ch);
  const hj = (isStem ? STEM_HJ : BRANCH_HJ)[idx];
  return { hj, idx };
}
// ═══ 회사 인연도 대시보드 (전체 화면) ═══
// 총점 = ① 한국 사업확대 20 + ② 주가 성장성 20 + ③ 커리어 30 + ④ 사주 인연 20 + ⑤ 미래사업·인지도 10
function netInput() {
  return { school: $("#school").value.trim(), hometown: $("#hometown").value,
    past_companies: $("#pastCompanies").value.split(/[,，、]/).map((x) => x.trim()).filter(Boolean) };
}
const SEC = [
  { key: "korea", no: "①", name: "한국 사업확대", color: "var(--s-korea)" },
  { key: "stock", no: "②", name: "주가 성장성", color: "var(--s-stock)" },
  { key: "career", no: "③", name: "커리어 매칭", color: "var(--s-career)" },
  { key: "saju", no: "④", name: "사주 인연·물", color: "var(--s-saju)" },
  { key: "future", no: "⑤", name: "미래사업·인지도", color: "var(--s-future)" },
];
const TABS = [
  ["overview", "종합 인연도"], ["score", "점수 계산"], ["keywords", "키워드 매칭"], ["tendency", "커리어 성향·연간 방향"], ["posting", "구인 내용"],
  ["finance", "회사 재무 분석"], ["applicant", "내 커리어 분석"], ["interview", "인터뷰 전략"],
];
const chg = (v) => (v == null ? "-" : `<span class="${v > 0 ? "up" : v < 0 ? "down" : ""}">${v > 0 ? "▲" : v < 0 ? "▼" : ""} ${Math.abs(v)}%</span>`);
const fitColor = (t) => (t >= 75 ? "var(--aff)" : t >= 60 ? "var(--gold)" : t >= 45 ? "var(--comp)" : "var(--metal)");
const partsList = (p) => `<div class="pt-list">${Object.entries(p).map(([k, v]) => `<span>${esc(k)} <b>${v}</b></span>`).join("")}</div>`;
const card = (title, body, extra = "") => `<section class="dcard ${extra}"><h5>${title}</h5>${body}</section>`;
const toneDot = (t) => `<i class="dot ${t}"></i>`;
const dashProfile = () => {
  const r = state.review || {};
  return { ...myProfile(), summary: r.summary, strengths: r.strengths || [], weaknesses: r.weaknesses || [] };
};

// ── 작은 SVG 차트 ──
function radarSvg(vals, labels, colors) {          // vals: 0~1
  const n = vals.length, R = 88, cx = 170, cy = 122;
  const pt = (i, r) => { const a = -Math.PI / 2 + (2 * Math.PI * i) / n; return [cx + r * Math.cos(a), cy + r * Math.sin(a)]; };
  const ring = (k) => Array.from({ length: n }, (_, i) => pt(i, R * k).join(",")).join(" ");
  const poly = vals.map((v, i) => pt(i, R * Math.max(v, 0.04)).join(",")).join(" ");
  return `<svg viewBox="0 0 340 250" class="radar" role="img" aria-label="회사 인연도 레이더">
    ${[0.25, 0.5, 0.75, 1].map((k) => `<polygon points="${ring(k)}" class="rg"/>`).join("")}
    ${vals.map((_, i) => `<line x1="${cx}" y1="${cy}" x2="${pt(i, R)[0]}" y2="${pt(i, R)[1]}" class="rg"/>`).join("")}
    <polygon points="${poly}" class="rv"/>
    ${vals.map((v, i) => { const [x, y] = pt(i, R * Math.max(v, 0.04)); return `<circle cx="${x}" cy="${y}" r="4" fill="${colors[i]}"/>`; }).join("")}
    ${labels.map((l, i) => { const [x, y] = pt(i, R + 18); return `<text x="${x}" y="${y}" text-anchor="middle" dominant-baseline="middle">${esc(l)}</text>`; }).join("")}
  </svg>`;
}
function barsSvg(items, { h = 150, unit = "", color = "var(--ok)", fmt = (v) => v } = {}) {   // items: [{label, v, cls}]
  const max = Math.max(...items.map((x) => x.v), 1), w = 56, gap = 18, W = items.length * (w + gap) + gap;
  return `<svg viewBox="0 0 ${W} ${h + 40}" class="bars" role="img">
    ${items.map((x, i) => { const bh = (h - 20) * (x.v / max), X = gap + i * (w + gap), Y = h - bh;
      return `<rect x="${X}" y="${Y}" width="${w}" height="${bh}" rx="5" class="${x.cls || ""}" style="fill:${x.color || color}"/>
        <text x="${X + w / 2}" y="${Y - 6}" text-anchor="middle" class="bv">${fmt(x.v)}${unit}</text>
        <text x="${X + w / 2}" y="${h + 18}" text-anchor="middle" class="bl">${esc(x.label)}</text>`; }).join("")}
    <line x1="0" y1="${h}" x2="${W}" y2="${h}" class="axis"/>
  </svg>`;
}
const hbar = (label, v, max, color, right = "") => `
  <div class="hbar"><span>${esc(label)}</span><i><u style="width:${(100 * v) / Math.max(max, 1)}%;background:${color}"></u></i><b>${right || v}</b></div>`;

// ── 열기 / 닫기 ──
function ensureModal() {
  let m = $("#dashModal");
  if (m) return m;
  m = document.createElement("div");
  m.id = "dashModal"; m.className = "dash-overlay"; m.hidden = true;
  m.innerHTML = `<div class="dash" role="dialog" aria-modal="true" aria-label="회사 인연도 대시보드"><div class="dash-inner"></div></div>`;
  document.body.append(m);
  m.addEventListener("click", (e) => { if (e.target === m || e.target.closest(".dash-close")) closeDash(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !m.hidden) closeDash(); });
  return m;
}
function closeDash() { $("#dashModal").hidden = true; document.body.classList.remove("no-scroll"); }

async function openDashboard(jobId) {
  if (!state.saju) return toast("먼저 프로필·사주 분석을 해 주세요.", true);
  const m = ensureModal(), inner = $(".dash-inner", m);
  m.hidden = false; document.body.classList.add("no-scroll");
  inner.innerHTML = `<div class="dash-loading"><span class="spin"></span>회사 인연도 대시보드를 만들고 있어요...</div>`;
  try {
    const d = await api("/api/company-analysis", { job_id: jobId, saju: state.saju, profile: dashProfile(), ...netInput() });
    inner.innerHTML = dashHtml(d);
    $$(".dtab", inner).forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));
    loadInterview(d); loadScore(d); loadKeywords(d);
  } catch (err) { inner.innerHTML = `<div class="dash-loading">${esc(err.message)} <button class="dash-close btn-ghost">닫기</button></div>`; }
}
function showTab(t) {
  $$("#dashModal .dtab").forEach((b) => b.classList.toggle("on", b.dataset.tab === t));
  $$("#dashModal .dpane").forEach((p) => (p.hidden = p.dataset.tab !== t));
  $("#dashModal .dash-body").scrollTop = 0;
}
async function loadInterview(d) {
  const pane = $('#dashModal .dpane[data-tab="interview"]');
  pane.innerHTML = interviewHtml(d.interview, true);
  // 레주메 최근 업무 키워드는 코드 계산이라 바로 보여 줌 (AI는 그다음)
  api("/api/recent-focus", { profile: dashProfile(), job_id: d.job.id }).then((f) => {
    d.interview.recent_focus = f; const box = $(".rf-host", pane); if (box) box.outerHTML = recentFocusHtml(f, d.job);
  }).catch(() => {});
  try {
    const ai = await api("/api/interview-strategy", { job_id: d.job.id, saju: state.saju, profile: dashProfile() });
    if (pane.isConnected) pane.innerHTML = interviewHtml(ai, false);
  } catch { if (pane.isConnected) pane.innerHTML = interviewHtml(d.interview, false); }
}

// ── 전체 틀 ──
function dashHtml(d) {
  const j = d.job, p = d.posting;
  const initials = j.company.split(/\s+/).map((w) => w[0]).join("").slice(0, 2);
  const head = `
    <header class="dash-head">
      <div class="dh-co"><span class="logo">${esc(initials)}</span>
        <div><small>회사 인연도 대시보드 · ${esc(j.company_type)}</small><h3>${esc(j.company)}</h3>
          <div class="dh-meta"><span>${esc(j.title)}</span><span>${esc(j.level)}</span><span>${esc(j.location)}</span><span>${esc(j.salary)}</span>
            <span class="dday ${p.dday <= 14 ? "soon" : ""}">마감 ${p.dday >= 0 ? `D-${p.dday}` : "종료"}</span></div></div></div>
      <div class="dh-score">
        <div class="ca-total" style="--p:${d.total};--c:${fitColor(d.total)}"><b>${d.total}</b><small>/100</small></div>
        <div><small>회사 인연도</small><em class="ca-grade" style="background:${fitColor(d.total)}">${esc(d.grade)}</em>
          <div class="dh-note">매칭률과 별개 · 참고용</div></div>
      </div>
      <button class="dash-close" aria-label="닫기">✕</button>
    </header>
    <div class="kpi-row">${SEC.map((s) => { const x = d[s.key];
      return `<div class="kpi" style="--c:${s.color}"><div class="k-top"><span class="no">${s.no}</span>${s.name}</div>
        <div class="k-val"><b>${x.score}</b><small>/ ${x.max}</small></div>
        <div class="k-bar"><u style="width:${(100 * x.score) / x.max}%"></u></div><div class="k-grade">${esc(x.grade)}</div></div>`; }).join("")}</div>
    <nav class="dtabs">${TABS.map(([k, n], i) => `<button class="dtab ${i ? "" : "on"}" data-tab="${k}">${n}</button>`).join("")}</nav>`;
  const panes = { overview: overviewHtml(d), tendency: tendencyHtml(d), posting: postingHtml(d), finance: financeHtml(d),
    applicant: applicantHtml(d), interview: "", score: "", keywords: "" };
  return head + `<div class="dash-body">${TABS.map(([k], i) => `<div class="dpane" data-tab="${k}" ${i ? "hidden" : ""}>${panes[k]}</div>`).join("")}
    <footer class="dash-foot">계산은 프로그램, 해석·인터뷰 전략은 AI · 회사 재무·주가·뉴스·인물은 가상 예시 데이터 · 합격을 보장하지 않는 참고 리포트예요.</footer></div>`;
}

// ── 탭 1: 종합 인연도 ──
function overviewHtml(d) {
  const vals = SEC.map((s) => d[s.key].score / d[s.key].max);
  const best = SEC.reduce((a, s, i) => (vals[i] > vals[a] ? i : a), 0), low = SEC.reduce((a, s, i) => (vals[i] < vals[a] ? i : a), 0);
  const w = d.saju.water, n = d.network;
  const summary = `
    <ul class="insights">
      <li>${toneDot("good")}<b>가장 강한 연결</b><span>${SEC[best].no} ${SEC[best].name} — ${d[SEC[best].key].score}/${d[SEC[best].key].max}점</span></li>
      <li>${toneDot("bad")}<b>보완할 부분</b><span>${SEC[low].no} ${SEC[low].name} — ${d[SEC[low].key].score}/${d[SEC[low].key].max}점</span></li>
      <li>${toneDot(w.tone)}<b>물(水)</b><span>${esc(w.verdict)}</span></li>
      <li>${toneDot(n.recommenders ? "good" : "soso")}<b>사내 추천</b><span>${n.recommenders ? `추천서 가능 ${n.recommenders}명 (학연·지연·전 직장)` : "연결된 추천인 없음"}</span></li>
      <li>${toneDot("soso")}<b>다음 행동</b><span>${esc((d.tendency.plan[0] || {}).action || "-")}</span></li>
    </ul>`;
  const k = d.korea, g = d.stock, cr = d.career, f = d.future;
  const tag = (l) => `<span class="lk ${l.startsWith("학연") ? "school" : l.startsWith("지연") ? "region" : "work"}">${esc(l)}</span>`;
  const sec = (s, body) => `<section class="ca-sec" style="--c:${s.color}"><h4><span class="no">${s.no}</span>${s.name}<span class="grade">${esc(d[s.key].grade)}</span><b class="sc">${d[s.key].score}<small>/${d[s.key].max}</small></b></h4>${body}</section>`;
  return `
    <div class="g2">
      ${card("점수 구성", `<div class="radar-wrap">${radarSvg(vals, SEC.map((s) => `${s.no} ${s.name}`), SEC.map((s) => s.color))}</div>
        <div class="ca-stack">${SEC.map((s) => `<div style="flex:${d[s.key].max};--c:${s.color}"><u style="width:${(100 * d[s.key].score) / d[s.key].max}%"></u></div>`).join("")}</div>
        <div class="stack-cap">배점 20 · 20 · 30 · 20 · 10 = 100</div>`)}
      ${card("핵심 요약", summary)}
    </div>
    <div class="ca-secs">
      ${sec(SEC[0], `<div class="partners"><small>한국 확대 계획</small><span class="exp-${esc(k.expand)}">${esc(k.expand || "-")}</span><em>${esc(k.plan || "")}</em></div>
        <div class="partners"><small>함께 사업하는 한국 기업</small>${k.partners.length ? k.partners.map((p) => `<span>${esc(p)}</span>`).join("") : "<em>없음</em>"}${k.korea_invest ? `<span class="inv">한국 투자 확대</span>` : ""}</div>
        ${k.items.length ? `<ol class="news">${k.items.map((x) => `<li><time>${esc(x.date)}</time><div><span class="kind">${esc(x.kind)}</span> <b>${esc(x.title)}</b><div class="meaning ${x.my_skills.length ? "hit" : ""}">→ ${esc(x.meaning)}</div></div></li>`).join("")}</ol>` : `<p class="muted">최근 한국 사업 뉴스가 없어요.</p>`}
        ${partsList(k.parts)}`)}
      ${sec(SEC[1], g.info ? `<div class="kpis"><div><small>주가</small><b>${g.info.listed ? esc(g.info.price) : "비상장"}</b><em>${g.info.listed ? `전일 ${chg(g.info.chg)}` : "투자 유치"}</em></div>
        <div><small>52주</small><b>${chg(g.info.w52)}</b><em>1년 변동</em></div><div><small>성장 전망</small><b class="up">연 ${g.info.growth}%</b><em>3년</em></div></div>
        <ul class="plain">${g.notes.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>${partsList(g.parts)}` : `<p class="muted">회사 정보 미등록</p>`)}
      ${sec(SEC[2], `<div>${cr.career.matched.map((x) => `<span class="skill">${esc(x)}</span>`).join("")}${cr.career.missing.map((x) => `<span class="skill miss">${esc(x)}</span>`).join("")}</div>
        <div class="mini-bars"><div><span>기술·경력</span><i><u style="width:${cr.career.score}%;background:var(--comp)"></u></i><b>${cr.career.score}</b></div>
        <div><span>연봉·직급</span><i><u style="width:${cr.pay.score}%;background:var(--pay)"></u></i><b>${cr.pay.score}</b></div></div>
        <div class="muted">(기술·경력 60% + 연봉·직급 40%) ${cr.base}점 × 0.3</div>`)}
      ${sec(SEC[3], `<div class="water-in ${w.tone}"><div class="drop">${w.in ? "💧" : "◌"}</div><div><b>${esc(w.verdict)}</b>
        <div>회사 날짜(${esc(d.saju.deadline_gz)}) 물: ${w.where.length ? w.where.map(esc).join(" · ") : "없음"}</div>
        <div>내 물 ${w.mine}개 · 나에게 <b>${esc(w.role)}</b> (${esc(w.role_meaning)})</div></div></div>
        <ul class="story">${d.saju.story.map((s) => `<li class="st ${s.tone}"><b>${esc(s.title)}</b><span>${esc(s.text)}</span></li>`).join("")}</ul>`)}
      ${sec(SEC[4], `<div class="future"><span class="sector">${esc(f.sector)}</span><span>글로벌 직원 ${Number(f.emp || 0).toLocaleString()}명</span></div>${partsList(f.parts)}`)}
      <section class="ca-sec ref" style="--c:var(--aff)"><h4><span class="no">+</span>참고: 사내 인맥 (학연·지연·전 직장)<span class="grade">${esc(n.grade)}</span><b class="sc ref-sc">점수 미포함</b></h4>
        ${n.people.length ? n.people.map((p) => `<div class="person"><span class="p-ava">${esc(p.name[0])}</span>
          <div><b>${esc(p.name)}</b> <small>${esc(p.role)} · 재직 ${p.years_here}년</small>${p.can_recommend ? `<span class="rec-ok">✓ 추천서 가능</span>` : ""}
          <div class="p-links">${p.links.map(tag).join("")}</div></div>
          <button class="chip-btn ghost ref-req" data-ref="${p.id}" data-job="${d.job.id}">추천 요청</button></div>`).join("")
          : `<p class="muted">이 회사에는 나와 학연·지연·전 직장으로 이어진 추천인이 아직 없어요.</p>`}
        <div class="muted">스스로 등록·공개 동의한 재직자만 (가상 인물, 이름 일부 가림)</div></section>
    </div>`;
}

// ── 탭 2: 커리어 성향 · 연간 방향성 ──
function tendencyHtml(d) {
  const t = d.tendency, el = state.saju.day_master_elem;
  const KIND = { go: ["지원 집중", "var(--aff)"], net: ["인맥·추천", "var(--gold)"], prep: ["역량 보완", "var(--comp)"] };
  const qs = [0, 1, 2, 3].map((q) => t.plan.slice(q * 3, q * 3 + 3)).filter((x) => x.length);
  return `
    <div class="g2">
      ${card("커리어 성향", `<div class="tend"><span class="elem-badge" style="background:${ELEM_COLOR[el]}">${ELEM_HJ[el]}</span>
        <div><b>${esc(t.type)}</b><p>${esc(t.desc)}</p></div></div>
        ${t.work_style ? `<p class="ai-txt"><span class="src-tag">AI 풀이</span>${esc(t.work_style)}</p>` : ""}
        <div class="field-bars">${Object.entries(t.fields).map(([k, v]) => hbar(k, v, Math.max(...Object.values(t.fields)), "var(--comp)", `${v}개`)).join("")}</div>`)}
      ${card("올해 방향성", `<div class="direction">${esc(t.direction)}</div>
        <div class="best-months"><small>지원하기 좋은 달 (이직운 계산)</small>${t.best.map((b) => `<span>${esc(b.ym)} <b>${b.score}</b></span>`).join("") || "-"}</div>
        <div class="legend-row">${Object.values(KIND).map(([n, c]) => `<span><i style="background:${c}"></i>${n}</span>`).join("")}</div>`)}
    </div>
    ${card("12개월 로드맵 — 이직운 점수와 할 일", `${barsSvg(t.plan.map((p) => ({ label: p.ym.slice(2).replace("-", "."), v: p.score, color: KIND[p.kind][1] })), { h: 140 })}
      <div class="quarters">${qs.map((q, i) => `<div class="qtr"><h6>${i + 1}분기 <small>${esc(q[0].ym)} ~ ${esc(q[q.length - 1].ym)}</small></h6>
        ${q.map((p) => `<div class="qrow"><span class="qk" style="background:${KIND[p.kind][1]}">${KIND[p.kind][0]}</span><b>${esc(p.ym)}</b><span>${esc(p.action)}</span></div>`).join("")}</div>`).join("")}</div>`, "wide")}`;
}

// ── 탭 3: 구인 내용 ──
function postingHtml(d) {
  const p = d.posting, have = new Set(d.career.career.matched);
  const rows = [["회사", `${p.company} (${p.hq} 본사)`], ["포지션", p.title], ["직급", p.level], ["경력", p.years], ["연봉", p.salary],
    ["영어", p.english], ["근무지", p.location], ["마감", `${p.deadline} (${p.dday >= 0 ? "D-" + p.dday : "마감"})`], ["출처", p.source]];
  const list = (arr) => `<ul class="checks">${arr.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>`;
  return `
    <div class="g2">
      ${card("포지션 개요", `<table class="spec">${rows.map(([k, v]) => `<tr><th>${k}</th><td>${esc(v)}</td></tr>`).join("")}</table>`)}
      <div class="stack-col">
        ${card("주요 업무", list(p.duties))}
        ${card("자격 요건", list(p.requirements))}
        ${card("우대 사항", list(p.preferred))}
      </div>
    </div>
    <div class="g2">
      ${card("요구 기술 vs 내 기술", `<div class="req-skills">${p.skills.map((s) => `<span class="${have.has(s) ? "have" : "need"}">${have.has(s) ? "✓" : "＋"} ${esc(s)}</span>`).join("")}</div>
        <div class="muted">✓ 보유 ${have.size}개 · ＋ 준비 필요 ${p.skills.length - have.size}개</div>`)}
      ${card("채용 담당자", `<div class="recruiter"><span class="p-ava">${esc(p.recruiter.name[0])}</span><div><b>${esc(p.recruiter.name)}</b><small>${esc(p.recruiter.role)}</small></div></div>
        <p class="muted">연결 요청은 매칭 공고 화면의 "담당자에게 연결 요청"으로 보내요. 담당자에게는 사주 정보가 전달되지 않아요.</p>`)}
    </div>`;
}

// ── 탭 4: 회사 재무 분석 ──
function financeHtml(d) {
  const f = d.finance;
  if (!f) return card("회사 재무 분석", `<p class="muted">구인자가 회사 정보를 아직 등록하지 않았어요.</p>`, "wide");
  const c = f.info;
  return `
    <div class="kpi-tiles">
      <div><small>연 매출 (글로벌)</small><b>$${c.revenue}억</b><em>전년 대비 ${chg(c.yoy)}</em></div>
      <div><small>영업이익</small><b>$${f.op_profit}억</b><em>이익률 ${chg(c.margin)}</em></div>
      <div><small>현재 주가</small><b>${c.listed ? esc(c.price) : "비상장"}</b><em>${c.listed ? `${esc(c.listed)} · 전일 ${chg(c.chg)}` : "투자 유치 단계"}</em></div>
      <div><small>52주 주가 변동</small><b>${chg(c.w52)}</b><em>최근 1년</em></div>
      <div><small>사원 수</small><b>${c.emp.toLocaleString()}명</b><em>한국 ${c.emp_kr}명</em></div>
      <div><small>1인당 매출</small><b>${f.per_emp}억 원</b><em>생산성</em></div>
    </div>
    <div class="g2">
      ${card(`매출 전망 — 연 ${c.growth}% 성장 가정 (억 달러)`, barsSvg(f.projection.map((x, i) => ({ label: String(x.year), v: x.rev, color: i ? "var(--ok)" : "var(--navy-700, #2a3755)" })), { h: 150 })
        + `<div class="muted">2026년 실적 기준, 3년 성장률 전망을 그대로 적용한 추정치</div>`)}
      ${card("재무 진단", `<ul class="diag">${f.checks.map((x) => `<li>${toneDot(x.tone)}<div><b>${esc(x.k)}</b><span class="v">${esc(x.v)}</span><p>${esc(x.t)}</p></div></li>`).join("")}</ul>`)}
    </div>
    <div class="muted">${esc(f.note)} · 실제 서비스는 공시·시세 API로 갱신</div>`;
}

// ── 탭 5: 내 커리어 분석 ──
function applicantHtml(d) {
  const a = d.applicant, LV = ["주니어", "미들", "시니어", "리드"];
  const maxJobs = Math.max(...a.skills.map((s) => s.jobs), 1);
  return `
    <div class="g2">
      ${card("커리어 위치", `<div class="lv-path">${LV.map((l) => `<div class="lv ${l === a.level ? "now" : ""} ${l === a.next_level && l !== a.level ? "next" : ""}"><i></i><span>${l}</span></div>`).join("")}</div>
        <div class="big-stats"><div><b>${a.years}</b><small>년 경력</small></div><div><b>${a.skills.length}</b><small>보유 기술</small></div>
          <div><b>${a.reach}<em>/${a.total_jobs}</em></b><small>기술 절반 이상 맞는 공고</small></div></div>
        ${a.summary ? `<p class="ai-txt"><span class="src-tag">AI 요약</span>${esc(a.summary)}</p>` : ""}`)}
      ${card("분야 구성", `<div class="field-bars">${Object.entries(a.fields).map(([k, v]) => hbar(k, v, Math.max(...Object.values(a.fields)), "var(--pay)", `${v}개`)).join("")}</div>
        <div class="gaps"><small>시장 수요는 많은데 나에게 없는 기술</small>${a.market_gaps.map((g) => `<span>＋ ${esc(g)}</span>`).join("")}</div>`)}
    </div>
    <div class="g2">
      ${card("내 기술의 시장 수요 (공고 20개 중 요구 수)", a.skills.map((s) => hbar(s.skill, s.jobs, maxJobs, "var(--comp)", `${s.jobs}곳`)).join("") || `<p class="muted">기술 정보가 없어요.</p>`)}
      ${card("강점 · 보완점 (AI 첨삭)", `<div class="sw"><div><h6 class="good">강점</h6><ul class="checks">${a.strengths.map((x) => `<li>${esc(x)}</li>`).join("") || "<li>-</li>"}</ul></div>
        <div><h6 class="bad">보완점</h6><ul class="checks warn">${a.weaknesses.map((x) => `<li>${esc(x)}</li>`).join("") || "<li>-</li>"}</ul></div></div>`)}
    </div>`;
}

// ── 탭 6: 인터뷰 전략 ──
function interviewHtml(v, loading) {
  return `
    <div class="iv-head"><span class="src-tag ${v.source?.startsWith("AI") ? "ai" : ""}">${esc(v.source || "")}</span>
      ${loading ? `<span class="iv-load"><span class="spin"></span>AI 코치가 이 회사 맞춤 전략을 쓰고 있어요 (20~40초)...</span>` : ""}
      ${v.ai_error ? `<span class="iv-err">${esc(v.ai_error)}</span>` : ""}</div>
    ${v.recent_focus ? recentFocusHtml(v.recent_focus, v.job) : `<div class="rf-host"></div>`}
    ${card("핵심 메시지 — 면접에서 꼭 전달할 3가지", `<ol class="keymsg">${v.key_messages.map((x) => `<li>${esc(x)}</li>`).join("")}</ol>`, "wide")}
    ${card("예상 질문과 답변 방향", `<div class="qa">${v.questions.map((x, i) => `<div class="qa-item"><span class="qn">Q${i + 1}</span><div><b>${esc(x.q)}</b><p>${esc(x.tip)}</p></div></div>`).join("")}</div>`, "wide")}
    <div class="g3">
      ${card("약점 대응", `<ul class="checks warn">${v.weakness_plan.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>`)}
      ${card("면접관에게 할 역질문", `<ul class="checks">${v.ask_them.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>`)}
      ${card("영어 · 시기", `<p>${esc(v.english)}</p>${v.timing ? `<p class="timing">${esc(v.timing)}</p>` : ""}`)}
    </div>`;
}

// 대시보드 열기 · 추천 요청 (사주 화면·매칭 화면 공통)
document.addEventListener("click", async (e) => {
  const open = e.target.closest(".fate-open, .ca-open");
  if (open) return openDashboard(Number(open.dataset.job));
  const rq = e.target.closest(".ref-req");
  if (rq) {
    try {
      await api("/api/referral", { referrer_id: Number(rq.dataset.ref), job_id: Number(rq.dataset.job) });
      rq.textContent = "추천 요청됨 ✓"; rq.disabled = true; toast("추천인에게 추천 요청을 보냈어요 (사주 정보는 보내지 않아요).");
    } catch (err) { toast(err.message, true); }
  }
});

function renderSaju() {
  const s = state.saju;
  const order = ["시주", "일주", "월주", "년주"]; // 전통 표기: 오른쪽에서 왼쪽 (시 일 월 년)
  const byName = Object.fromEntries(s.pillars.map((p) => [p.name, p]));
  const pillarsHtml = order.map((n) => {
    const p = byName[n];
    if (!p) return `<div class="pillar empty"><div class="pillar-name">${n}</div><div class="gz"><div class="ch" style="background:#ddd">?</div><div class="ch" style="background:#ddd">?</div></div><div class="pillar-ko">시간 모름</div></div>`;
    const st = charBox(p.gz[0], true), br = charBox(p.gz[1], false);
    return `<div class="pillar ${n === "일주" ? "day" : ""}">
      <div class="pillar-name">${n}</div>
      <div class="gz">
        <div class="ch el-${p.stem_elem}">${st.hj}<small>${p.gz[0]} · ${p.stem_elem}</small></div>
        <div class="ch el-${p.branch_elem}">${br.hj}<small>${p.gz[1]} · ${p.branch_elem}</small></div>
      </div>
      <div class="pillar-ko">${p.gz}${n.slice(0, 1)}</div>
      ${n === "일주" ? `<span class="day-badge">나 (일간)</span>` : ""}
    </div>`;
  }).join("");

  const max = Math.max(...Object.values(s.elements), 1);
  const elems = Object.entries(s.elements).map(([e, c]) => `
    <div class="elem-row"><div class="lbl">${e}<span>${ELEM_HJ[e]}</span></div>
      <div class="bar"><div style="width:0;background:${ELEM_COLOR[e]}" data-w="${(c / max) * 100}"></div></div><b>${c}</b></div>`).join("");

  const rd = s.reading;
  const readingHtml = rd ? `
    <div class="paper"><h3><i>性</i>타고난 성향</h3><p>${esc(rd.personality)}</p></div>
    <div class="paper"><h3><i>業</i>어울리는 일</h3><p>${esc(rd.work_style)}</p></div>
    <div class="paper"><h3><i>運</i>${s.this_year.year}년 ${esc(s.this_year.gz)}년 커리어 운세</h3><p>${esc(rd.this_year)}</p>
      <div class="months">${rd.best_months.map((m) => `<span class="month">${esc(m)}</span>`).join("")}</div></div>`
    : `<div class="paper"><p>${esc(s.reading_error || "풀이를 불러오지 못했어요.")}</p></div>`;

  // 물(水) 분석 + 지금 지원하면 이직운 (계산값은 서버, 풀이는 AI)
  const w = s.water, mv = s.move;
  const lvl = mv.score >= 70 ? "hi" : mv.score >= 50 ? "mid" : "lo";
  const bestSet = new Set(mv.best.map((b) => b.ym));
  const keyHtml = `
    <div class="key-grid">
      <div class="paper water-card">
        <h3><i>水</i>물(水) 분석</h3>
        <div class="water-head">
          <div class="water-drop ${w.count ? "" : "none"}"><span>${w.count}<small>개</small></span></div>
          <div><b class="water-status">물 ${esc(w.status)}</b>
            <div class="water-where">${w.where.length ? w.where.map(esc).join(" · ") : "사주 여덟 글자 중 물 기운이 없어요"}</div>
            <div class="water-role">나에게 물은 <b>${esc(w.role)}</b> — ${esc(w.role_meaning)}</div></div>
        </div>
        ${rd ? `<p>${esc(rd.water)}</p>` : ""}
      </div>
      <div class="paper move-card">
        <h3><i>移</i>지금 지원하면 이직이 될까?</h3>
        <div class="move-head">
          <div class="move-score ${lvl}">${mv.score}<small>점</small></div>
          <div><b class="move-verdict ${lvl}">${esc(mv.verdict)}</b>
            <div class="water-where">${mv.date} 지원 기준 · ${esc(mv.year_gz)}년 ${esc(mv.month_gz)}월</div></div>
        </div>
        <ul class="move-notes">${mv.notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ul>
        ${rd ? `<p>${esc(rd.move_now)}</p>` : ""}
        <div class="move-months">${mv.months.map((m) => `
          <div class="mm ${bestSet.has(m.ym) ? "best" : ""}" title="${esc(m.gz)} · ${m.score}점">
            <div class="mm-bar"><div style="height:${m.score}%"></div></div><span>${+m.ym.slice(5)}월</span></div>`).join("")}</div>
        <div class="elem-note">금색 막대 = 앞으로 12개월 중 이직운이 가장 좋은 달 · 명리 해석은 참고용이며 합격을 보장하지 않아요</div>
      </div>
    </div>`;

  // 이직 인연 랭킹: 지금 올라온 모든 공고 회사와의 사주 인연 %
  const fr = s.fate_ranking || [];
  const frColor = (p) => (p >= 70 ? "hi" : p >= 50 ? "mid" : "lo");
  const fateHtml = fr.length ? `
    <div class="paper fate-card ref-box">
      <span class="ref-tag">참고사항</span>
      <h3><i>緣</i>이직 인연 랭킹 <small>지금 채용 중인 외국계 IT ${fr.length}곳과 나의 사주 인연</small></h3>
      <ol class="fate-list">${fr.map((f, i) => `
        <li class="fate ${i < 3 ? "top" : ""} ${i >= 10 ? "more" : ""}" ${i >= 10 ? "hidden" : ""}>
          <span class="fate-rank">${f.rank}</span>
          <div class="fate-co"><b>${esc(f.company)}</b> <small>${esc(f.hq)} 본사</small><div class="fate-title">${esc(f.title)}</div></div>
          <div class="fate-bar"><div class="${frColor(f.percent)}" style="width:${f.percent}%"></div></div>
          <b class="fate-pct ${frColor(f.percent)}">${f.percent}%</b>
          <div class="fate-why">마감 ${f.deadline} <span class="dl-gz">${esc(f.deadline_gz)}일</span> · ${f.notes.map(esc).join(" · ")}
            ${(state.net?.[f.company] || []).length ? `<span class="net-badge">인맥 ${state.net[f.company].length}명</span>` : ""}
            <button class="fate-open" data-job="${f.job_id}">회사 인연도 대시보드 ↗</button></div>
        </li>`).join("")}</ol>
      ${fr.length > 10 ? `<button class="btn-ghost more" id="fateMore">나머지 ${fr.length - 10}곳 더 보기</button>` : ""}
      <div class="elem-note">이직 인연 % = 나의 사주와 공고 마감일 사주의 궁합 (일주 중심 + 천간합·월주·년주·월지 보조, 5~99%) · 커리어·연봉과 별개, 매칭률 ③과 같은 값 · 참고용</div>
    </div>` : "";

  $("#sajuBody").innerHTML = `
    <div class="pillars">${pillarsHtml}</div>
    ${keyHtml}
    <div class="saju-grid">
      <div class="stack">
        <div class="paper"><h3><i>五</i>오행 분포</h3>${elems}
          <div class="elem-note">일간 <b>${s.day_master}(${s.day_master_elem})</b> · 가장 강한 기운 <b>${s.strongest}</b> · 보완할 기운 <b>${s.weakest}</b><br>
          <span style="color:var(--ink-3);font-size:12px">양력 ${s.solar_date} 기준 계산</span></div></div>
        ${rd ? `<div class="paper"><h3><i>合</i>잘 맞는 회사 유형</h3><div class="ctypes">${rd.company_types.map((c) => `<div class="ctype">${esc(c)}</div>`).join("")}</div></div>` : ""}
      </div>
      <div class="stack">${readingHtml}</div>
    </div>
    ${rd ? `<div class="advice">${esc(rd.advice)}</div>` : ""}
    ${fateHtml}`;
  requestAnimationFrame(() => $$("#sajuBody .bar > div").forEach((b) => (b.style.width = b.dataset.w + "%")));
  $("#fateMore")?.addEventListener("click", (e) => { $$(".fate.more").forEach((li) => (li.hidden = false)); e.target.remove(); });
}

$("#matchBtn").addEventListener("click", async () => {
  if (state.ranked) return go("match");
  loading(true, "역량과 인연을 계산해 공고를 고르고 있어요...");
  try {
    const r = state.review;
    state.ranked = await api("/api/recommend", { profile: myProfile(), saju: state.saju });
    state.shown = 8;
    renderMatch(); markDone("review"); markDone("saju"); unlock("match"); go("match");
  } catch (err) { toast(err.message, true); } finally { loading(false); }
});

function myProfile() {
  const r = state.review;
  return { summary: r.summary, skills: r.skills, years: r.years, level: r.level,
    desired_level: $("#wantLevel").value || r.level, desired_family: $("#wantFamily").value || r.job_family || "", expected_salary: Number($("#expSalary").value) || null,
    linkedin_url: $("#linkedinUrl").value.trim() || null, resume_text: $("#profileText").value, resume_summary: state.summary || null };
}
["#expSalary", "#wantLevel", "#wantFamily", "#school", "#hometown", "#pastCompanies"].forEach((id) => $(id).addEventListener("change", () => { state.ranked = null; state.ov = null; })); // 조건이 바뀌면 다시 계산

// ─── 4. 매칭 ───
// 마감까지 남은 날 (D-day)
function dday(dl) {
  const t = new Date(); t.setHours(0, 0, 0, 0);
  const n = Math.round((new Date(dl + "T00:00:00") - t) / 86400000);
  return { n, label: n < 0 ? "마감" : n === 0 ? "D-day" : `D-${n}`, cls: n < 0 ? "over" : n <= 7 ? "soon" : "" };
}
const MSORT = { rec: ["추천순", null], fit: ["회사 인연도", (r) => -r.company_fit], kw: ["키워드 매칭", (r) => -(r.keyword_match ?? 0)],
  dl: ["마감 임박", (r) => r.job.deadline], pay: ["연봉 높은 순", (r) => -(r.job.salary_max ?? 0)] };
state.mf = { sort: "rec", lvl: false, remote: false, todo: false, family: null };   // family: null = 아직 안 정함(희망 직종으로 시작)
const myFamily = () => $("#wantFamily").value || state.review?.job_family || "";

function matchFiltered() {
  const want = $("#wantLevel").value || state.review?.level;
  let list = state.ranked.map((r, i) => ({ ...r, _rank: i + 1 }));
  if (state.mf.family == null) state.mf.family = $("#wantFamily").value || "";   // 직접 고른 희망 직종이 있으면 그 직종부터
  if (state.mf.family) list = list.filter((r) => r.job.family === state.mf.family);
  if (state.mf.lvl) list = list.filter((r) => r.job.level === want);
  if (state.mf.remote) list = list.filter((r) => /원격|재택|remote/i.test(r.job.location));
  if (state.mf.todo) list = list.filter((r) => !state.applied.has(r.job.id));
  const key = MSORT[state.mf.sort][1];
  if (key) list.sort((a, b) => (key(a) < key(b) ? -1 : key(a) > key(b) ? 1 : a._rank - b._rank));
  return list;
}

function renderMatch() {
  const all = state.ranked, f = state.mf;
  const list = matchFiltered(), shown = list.slice(0, state.shown);
  const hi = all.filter((r) => r.pass_rate >= 70).length;
  const soon = all.filter((r) => { const d = dday(r.job.deadline).n; return d >= 0 && d <= 14; }).length;
  const want = $("#wantLevel").value || state.review?.level;
  $("#matchBody").innerHTML = `
  <div class="m-sum">
    <div><b>${all.length}</b><span>매칭된 공고</span></div>
    <div><b class="ok">${hi}</b><span>합격 가능성 70% 이상</span></div>
    <div><b class="warn">${soon}</b><span>2주 안에 마감</span></div>
    <div><b>${state.applied.size}</b><span>연결 요청한 공고</span></div>
  </div>
  ${familyChips(all.map((r) => r.job), f.family, "mfam")}
  <div class="m-bar">
    <div class="m-sort" role="group" aria-label="정렬">${Object.entries(MSORT).map(([k, [t]]) => `<button data-msort="${k}" class="${f.sort === k ? "on" : ""}">${t}</button>`).join("")}</div>
    <div class="m-filt">
      <button data-mf="lvl" class="${f.lvl ? "on" : ""}">${f.lvl ? "✓ " : ""}내 희망 직급(${esc(want || "-")})만</button>
      <button data-mf="remote" class="${f.remote ? "on" : ""}">${f.remote ? "✓ " : ""}원격 근무</button>
      <button data-mf="todo" class="${f.todo ? "on" : ""}">${f.todo ? "✓ " : ""}아직 요청 안 한 공고</button>
    </div>
  </div>
  <div class="m-count">${f.family ? `<b>${esc(f.family)}</b> ` : ""}${list.length}개 공고 · ${MSORT[f.sort][0]}${f.family || f.lvl || f.remote || f.todo ? ` <button class="m-reset" data-mreset>필터 지우기</button>` : ""}</div>
  ${list.length ? "" : `<div class="empty"><b>조건에 맞는 공고가 없어요</b>필터를 지우면 전체 공고를 볼 수 있어요.</div>`}
  <div class="match-list">${shown.map((r) => {
    const j = r.job, c = r.career, p = r.pay, a = r.affinity;
    const applied = state.applied.has(j.id), d = dday(j.deadline);
    const color = r.pass_rate >= 70 ? "var(--ok)" : r.pass_rate >= 50 ? "var(--comp)" : "var(--aff)";
    return `<article class="match ${r._rank <= 3 ? "top" : ""}">
      <div class="rank"><small>추천</small>${r._rank}</div>
      <div class="m-main">
        <div class="co">${famBadge(j)} ${esc(j.company)} <span class="badge-type">${esc(j.company_type)}</span> <span class="dday ${d.cls}">${d.label}</span> ${srcBadge(j)}</div>
        <div class="title">${esc(j.title)}</div>
        <div class="facts"><span class="lvl">${j.level}</span><span>경력 ${j.years_min}~${j.years_max}년</span><span>${esc(j.location)}</span><span>${esc(j.salary)}</span><span>영어 ${esc(j.english)}</span><span>마감 ${j.deadline}</span></div>
        <div class="skills">${c.matched.map((s) => `<span class="skill">${esc(s)}</span>`).join("")}${c.missing.map((s) => `<span class="skill miss">${esc(s)} 부족</span>`).join("")}</div>
        <div class="split"><div class="a" style="width:${c.score * 0.34}%"></div><div class="p" style="width:${p.score * 0.33}%"></div><div class="b" style="width:${a.score * 0.33}%"></div></div>
        <div class="split-legend"><span class="c-comp">① 커리어 ${c.score}</span><span class="c-pay">② 연봉·직급 ${p.score}</span><span class="c-aff">③ 인연 ${a.score}</span><span>매칭률 <b>${r.total}%</b></span></div>
        <div class="ca-host"><span class="fit-badge" style="--c:${fitColor(r.company_fit)}">회사 인연도 <b>${r.company_fit}</b>점</span><span class="fit-badge kw-badge">키워드 매칭 <b>${r.keyword_match ?? "-"}</b>%</span><button class="ca-open" data-job="${j.id}">회사 인연도 대시보드 ↗</button></div>
        <details class="m-more">
          <summary>점수 근거${r.comment ? " · AI 코치 조언" : ""} · 채용 담당자 보기</summary>
          <div class="recruiter-line">채용 담당 <b>${esc(j.recruiter.name)}</b> · ${esc(j.recruiter.role)} ${srcBadge(j)}</div>
          <div class="why">
            <div class="why-box"><b class="c-comp">① 커리어</b><ul>${c.notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ul></div>
            <div class="why-box pay"><b class="c-pay">② 연봉·직급</b><ul>${p.notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ul></div>
            <div class="why-box aff"><b class="c-aff">③ 인연 · 마감일 <span class="dl-gz">${a.deadline_gz}일</span></b><ul>${a.notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ul></div>
          </div>
          ${r.comment ? `<div class="ai-comment"><b>AI 코치</b><span>${esc(r.comment)}</span></div>` : ""}
        </details>
      </div>
      <div class="rate">
        <div class="gauge" style="--p:${r.pass_rate};--c:${color}"><b>${r.pass_rate}%</b></div>
        <div class="rate-label">합격 가능성 <span class="est">AI 추정치</span></div>
        <button class="btn-apply" data-apply="${j.id}" ${applied ? "disabled" : ""}>${applied ? "✓ 연결 요청됨" : "담당자에게 연결 요청"}</button>
      </div>
    </article>`;
  }).join("")}</div>
  ${state.shown < list.length ? `<button class="btn-ghost more" id="moreBtn">공고 더 보기 (${list.length - state.shown}개)</button>` : ""}`;
  $("#moreBtn")?.addEventListener("click", () => { state.shown = list.length; renderMatch(); });
}
document.addEventListener("click", (e) => {
  const s = e.target.closest("[data-msort]"), m = e.target.closest("[data-mf]"), x = e.target.closest("[data-mreset]");
  if (!s && !m && !x) return;
  if (s) state.mf.sort = s.dataset.msort;
  if (m) state.mf[m.dataset.mf] = !state.mf[m.dataset.mf];
  if (x) Object.assign(state.mf, { lvl: false, remote: false, todo: false, family: "" });
  renderMatch();
});

document.addEventListener("click", async (e) => {
  const b = e.target.closest("[data-apply]");
  if (!b) return;
  const id = Number(b.dataset.apply);
  const r = state.ranked?.find((x) => x.job.id === id);
  try {
    await api("/api/apply", { job_id: id, total: r?.total ?? null, pass_rate: r?.pass_rate ?? null,
      candidate: myProfile(), career_score: r?.career.score ?? null, pay_score: r?.pay.score ?? null });
    state.applied.add(id);
    $("#appCount").textContent = `${state.applied.size}건`;
    b.disabled = true; b.textContent = "✓ 연결 요청됨";
    toast(`${r?.job.recruiter.name ?? "채용 담당자"}님에게 연결 요청을 보냈어요.`);
  } catch (err) { toast(err.message, true); }
});

// ─── 5. 지원 내역 ───
async function renderApps() {
  const apps = await api("/api/applications");
  $("#appCount").textContent = `${apps.length}건`;
  $("#appsBody").innerHTML = apps.length ? `
    <table class="table"><thead><tr><th>회사</th><th>포지션</th><th>채용 담당</th><th>매칭률</th><th>합격 가능성 (추정)</th><th>요청 일시</th><th>상태</th></tr></thead>
    <tbody>${apps.map((a) => `<tr><td><b>${esc(a.job.company)}</b></td><td>${esc(a.job.title)}</td><td>${esc(a.job.recruiter.name)}</td>
      <td>${a.total != null ? a.total + "%" : "-"}</td><td>${a.pass_rate != null ? a.pass_rate + "%" : "-"}</td><td>${a.applied_at}</td><td><span class="status">${esc(a.status)}</span></td></tr>`).join("")}</tbody></table>`
    : `<div class="empty"><b>아직 연결 요청이 없어요</b>매칭 공고에서 채용 담당자에게 연결을 요청해 보세요.</div>`;
}

// ─── 전체 공고 ───
let level = "", jobFam = null;
bindSeg("levelFilter", (v) => { level = v; loadJobs(); });
let qTimer;
$("#q").addEventListener("input", () => { clearTimeout(qTimer); qTimer = setTimeout(loadJobs, 200); });
async function loadJobs() {
  if (jobFam == null) jobFam = $("#wantFamily").value || "";
  const [jobs, all] = await Promise.all([api(`/api/jobs?q=${encodeURIComponent($("#q").value)}&level=${encodeURIComponent(level)}&family=${encodeURIComponent(jobFam)}`), api("/api/jobs")]);
  $("#jobFamilies").innerHTML = familyChips(all, jobFam, "jfam");
  $("#jobsBody").innerHTML = jobs.length ? jobs.map((j) => `
    <div class="job">
      <div class="co">${famBadge(j)} ${esc(j.company)} <span class="badge-type">${esc(j.company_type)}</span></div>
      <div class="title">${esc(j.title)}</div>
      <div class="facts"><span class="lvl">${j.level}</span><span>경력 ${j.years_min}~${j.years_max}년</span><span>${esc(j.location)}</span></div>
      <div class="job-src">${srcBadge(j)}</div>
      <div class="skills">${j.skills.map((s) => `<span class="skill muted">${esc(s)}</span>`).join("")}</div>
      <div class="row"><span>${esc(j.salary)}</span><span>마감 ${j.deadline}</span></div>
    </div>`).join("") : `<div class="empty" style="grid-column:1/-1"><b>검색 결과가 없어요</b>다른 키워드로 찾아보세요.</div>`;
}

// ─── 구인자(채용 담당자) ───
const STATUSES = ["연결 요청됨", "검토중", "인터뷰 제안", "보류"];
document.addEventListener("change", async (e) => {
  const sel = e.target.closest("[data-status]");
  if (!sel) return;
  try {
    await api(`/api/recruiter/requests/${sel.dataset.status}/status`, { status: sel.value });
    toast(`상태를 '${sel.value}'(으)로 바꿨어요.`);
  } catch (err) { toast(err.message, true); }
});

// ─── 내 링크드인 연결 (Sign in with LinkedIn) ───
async function refreshLinkedIn() {
  const me = await api("/api/linkedin/me").catch(() => null);
  state.linkedin = me;
  const box = $("#liStatus"), btn = $("#liConnect");
  if (me?.connected) {
    const u = me.user;
    box.innerHTML = `<div class="li-card">${u.picture ? `<img src="${esc(u.picture)}" alt="">` : `<span class="li-ava">in</span>`}
      <div><b>${esc(u.name)}</b> <span class="li-ok">✓ 링크드인 본인 확인</span><small>${esc(u.email || "")} · ${esc(u.connected_at)}</small></div>
      <button class="btn-ghost li-out" id="liOut">연결 해제</button></div>`;
    btn.innerHTML = "<span>in</span> 연결됨"; btn.disabled = true;
    $("#liOut").addEventListener("click", async () => { await api("/api/linkedin/logout", {}); refreshLinkedIn(); toast("링크드인 연결을 해제했어요."); });
  } else {
    box.innerHTML = me && !me.configured
      ? `<div class="li-card warn">링크드인 앱 키가 아직 설정되지 않았어요. <small>..\.env 에 LINKEDIN_CLIENT_ID · LINKEDIN_CLIENT_SECRET 을 넣고 서버를 다시 켜면 연결돼요.</small></div>` : "";
    btn.innerHTML = "<span>in</span> 내 링크드인 연결"; btn.disabled = false;
  }
}
$("#liConnect").addEventListener("click", () => {
  if (state.linkedin && !state.linkedin.configured) return toast("링크드인 앱 키를 먼저 설정해 주세요 (안내 참고).", true);
  location.href = "/auth/linkedin/login";
});
(() => {
  const q = new URLSearchParams(location.search), r = q.get("linkedin");
  if (r === "ok") toast("링크드인에 연결됐어요. 이제 경력 내용을 붙여넣어 주세요.");
  if (r === "error") toast(`링크드인 연결 실패: ${q.get("msg") || "알 수 없음"}`, true);
  if (r === "not_configured") toast("링크드인 앱 키가 설정되지 않았어요.", true);
  if (r) history.replaceState(null, "", "/");
  refreshLinkedIn();
})();

// ═══ ★ 커리어 인연 종합 대시보드 ═══
// 색은 항목(①~⑤)을 따라감 — 어느 화면에서나 같은 항목은 같은 색 (팔레트는 색약 검증 통과: 주황·청록·파랑·노랑·보라)
const OV_KEYS = ["korea", "stock", "career", "saju", "future"];
const OV_NAME = { korea: "① 한국 사업확대", stock: "② 주가 성장성", career: "③ 커리어 매칭", saju: "④ 사주 인연", future: "⑤ 미래사업·인지도" };
const OV_GROUPS = [
  ["전체", () => true],
  ["AI·데이터", (s) => s === "AI·데이터"],
  ["클라우드·반도체·로봇", (s) => ["클라우드", "반도체", "로봇"].includes(s)],
  ["핀테크·보안·모빌리티", (s) => ["핀테크", "보안", "모빌리티"].includes(s)],
  ["기타", (s) => !["AI·데이터", "클라우드", "반도체", "로봇", "핀테크", "보안", "모빌리티"].includes(s)],
];
const OV_SORTS = [["total", "회사 인연도순"], ["match", "매칭률순"], ["dday", "마감 임박순"]];
state.ov = null; state.ovGroup = 0; state.ovSort = "total"; state.ovTableSort = ["total", -1]; state.ovFamily = null;

// 공용 툴팁 (값은 표에도 있으므로 툴팁은 보조)
function tip(html, e) {
  let t = $("#ovTip");
  if (!t) { t = document.createElement("div"); t.id = "ovTip"; t.className = "ov-tip"; t.setAttribute("role", "status"); document.body.append(t); }
  if (!html) { t.hidden = true; return; }
  t.innerHTML = html; t.hidden = false;
  const r = t.getBoundingClientRect(), x = Math.min(e.clientX + 14, innerWidth - r.width - 8), y = e.clientY + 16 + r.height > innerHeight ? e.clientY - r.height - 12 : e.clientY + 16;
  t.style.left = x + "px"; t.style.top = y + "px";
}
const partsTip = (c) => `<b>${esc(c.company)}</b><span class="tt-sub">${esc(c.sector)} · ${esc(c.title)}</span>
  ${OV_KEYS.map((k) => `<div class="tt-row"><i class="sw s-${k}"></i>${OV_NAME[k]}<b>${c.parts[k]}<small>/${state.ov.max[k]}</small></b></div>`).join("")}
  <div class="tt-row tt-total">회사 인연도<b>${c.total}<small>/100</small></b></div><div class="tt-row">매칭률<b>${c.match}%</b></div>`;

async function renderOverview(force) {
  const body = $("#ovBody");
  if (!state.saju || !state.review) { body.innerHTML = `<div class="empty">1단계에서 프로필·사주 분석을 먼저 해 주세요.</div>`; return; }
  if (!state.ov || force) {
    body.innerHTML = state.ovHtml ? state.ovHtml : `<div class="dash-loading"><span class="spin"></span>20개 회사의 인연도를 계산하고 있어요...</div>`;
    body.style.opacity = state.ovHtml ? 0.5 : 1;     // 다시 계산할 때는 이전 화면을 흐리게 유지 (깜빡임 없음)
    try { state.ov = await api("/api/overview", { saju: state.saju, profile: dashProfile(), ...netInput() }); }
    catch (err) { body.innerHTML = `<div class="empty">${esc(err.message)}</div>`; return; }
    body.style.opacity = 1;
  }
  const d = state.ov, grp = OV_GROUPS[state.ovGroup][1];
  if (state.ovFamily == null) state.ovFamily = $("#wantFamily").value || "";
  const all = d.companies, list = all.filter((c) => grp(c.sector) && (!state.ovFamily || c.family === state.ovFamily));
  const sorted = [...list].sort((a, b) => state.ovSort === "dday" ? a.dday - b.dday : b[state.ovSort] - a[state.ovSort] || a.dday - b.dday);
  $("#ovAsof").innerHTML = `<small>기준일</small><b>${new Date().toISOString().slice(0, 10)}</b><small>회사 ${all.length}곳 · 가상 예시 데이터</small>`;

  body.innerHTML = `
    ${familyChips(all, state.ovFamily, "ofam")}
    <div class="ov-filters" role="toolbar" aria-label="대시보드 필터">
      <div class="ov-seg" aria-label="분야">${OV_GROUPS.map(([n], i) => `<button class="${i === state.ovGroup ? "on" : ""}" data-ovg="${i}">${n}<small>${all.filter((c) => OV_GROUPS[i][1](c.sector)).length}</small></button>`).join("")}</div>
      <div class="ov-seg" aria-label="정렬">${OV_SORTS.map(([k, n]) => `<button class="${k === state.ovSort ? "on" : ""}" data-ovs="${k}">${n}</button>`).join("")}</div>
    </div>
    ${list.length ? `
    ${kpiHtml(d, list)}
    <div class="ov-grid ov-main">
      ${ovCard("회사별 회사 인연도", "막대 = 5개 항목 점수의 합 (100점 만점) · 줄을 누르면 회사 대시보드", rankingHtml(d, sorted), "ov-rank", legendHtml())}
      <div class="ov-col">
        ${ovCard("커리어 적합 × 회사 매력", "가로 = ③ 커리어 매칭(30) · 세로 = ①+②+⑤ 회사 매력(50)", scatterHtml(d, list), "ov-scatter")}
        ${ovCard("앞으로 12개월 이직운", "사주 세운·월운으로 계산 · 진한 막대 = 가장 좋은 달 3개", monthsHtml(d))}
      </div>
    </div>
    <div class="ov-grid ov-two">
      ${ovCard("마감 임박 공고", "마감 순 · 회사 인연도와 함께", deadlinesHtml(list))}
      ${ovCard("분야별 평균 회사 인연도", "같은 분야 회사들의 평균 (전체 회사 기준)", sectorsHtml(d))}
    </div>
    ${ovCard("전체 표", "제목을 누르면 정렬 · 모든 값은 이 표에서 확인할 수 있어요", tableHtml(d, list), "ov-table-card")}
    ` : `<div class="empty">이 분야에는 지금 채용 중인 회사가 없어요.</div>`}
    <p class="ov-foot">회사 인연도는 매칭률(커리어 34 · 연봉·직급 33 · 사주 33)과 별개의 참고 점수예요 · 학연·지연·인맥은 점수에 넣지 않아요 · 회사 재무·주가·뉴스·인물은 가상 예시이며 합격을 보장하지 않아요.</p>`;
  state.ovHtml = body.innerHTML;
  bindOverview(d, list);
}

function ovCard(title, sub, inner, cls = "", extra = "") {
  return `<section class="ov-card ${cls}"><header><div><h3>${title}</h3><p>${sub}</p></div>${extra}</header>${inner}</section>`;
}
const legendHtml = () => `<div class="ov-legend" aria-label="범례">${OV_KEYS.map((k) => `<span><i class="sw s-${k}"></i>${OV_NAME[k]}</span>`).join("")}</div>`;

// ── KPI ──
function kpiHtml(d, list) {
  const top = [...list].sort((a, b) => b.total - a.total)[0];
  const avg = Math.round(list.reduce((s, c) => s + c.total, 0) / list.length);
  const strong = list.filter((c) => c.total >= 60).length;
  const refs = list.reduce((s, c) => s + c.referrers, 0), refCos = list.filter((c) => c.referrers).length;
  const mv = d.me.move, w = d.me.water;
  const mvTone = mv.score >= 70 ? "good" : mv.score >= 50 ? "soso" : "bad";
  return `<div class="ov-kpis">
    <button class="ov-hero" data-dash="${top.job_id}" aria-label="${esc(top.company)} 회사 대시보드 열기">
      <small>가장 인연 깊은 회사</small>
      <div class="hero-row"><b class="hero-num">${top.total}</b><span class="hero-of">/100</span>
        <div class="hero-co"><strong>${esc(top.company)}</strong><span>${esc(top.title)} · ${esc(top.sector)}</span><em class="pill">${esc(top.grade)}</em></div></div>
      <div class="seg-bar" aria-hidden="true">${OV_KEYS.map((k) => `<i class="s-${k}" style="flex:${top.parts[k] || 0.001}"></i>`).join("")}<i class="rest" style="flex:${100 - top.total}"></i></div>
      <span class="hero-go">회사 대시보드 열기 ↗</span>
    </button>
    <div class="ov-kpi"><small>평균 회사 인연도</small><b>${avg}<span>/100</span></b><em>${list.length}곳 기준</em></div>
    <div class="ov-kpi"><small>인연 강함 이상</small><b>${strong}<span>곳</span></b><em>60점 이상 · 전체 ${list.length}곳 중</em></div>
    <div class="ov-kpi"><small>지금 이직운</small><b>${mv.score ?? "-"}<span>/100</span></b><em><i class="ovst ${mvTone}" aria-hidden="true"></i>${esc(mv.verdict || "")}</em></div>
    <div class="ov-kpi"><small>내 사주의 물(水)</small><b>${w.count ?? "-"}<span>개</span></b><em>${esc(w.status || "")} · 나에게 ${esc(w.role || "")}</em></div>
    <div class="ov-kpi"><small>추천 가능 인맥</small><b>${refs}<span>명</span></b><em>${refCos}개 회사 · 학연·지연·전 직장</em></div>
  </div>`;
}

// ── 순위 (누적 가로 막대) ──
function rankingHtml(d, rows) {
  return `<ol class="rk">${rows.map((c, i) => `
    <li class="rk-row" data-dash="${c.job_id}" data-tip="${c.job_id}" tabindex="0" aria-label="${esc(c.company)} 회사 인연도 ${c.total}점, 매칭률 ${c.match}%">
      <span class="rk-n ${i < 3 && state.ovSort === "total" ? "top" : ""}">${i + 1}</span>
      <span class="rk-co"><b>${esc(c.company)}</b><small>${esc(c.sector)} · D-${c.dday}</small></span>
      <span class="rk-bar">${OV_KEYS.map((k) => `<i class="s-${k}" style="width:${c.parts[k]}%"></i>`).join("")}<b class="rk-val">${c.total}</b></span>
      <span class="rk-m"><b>${c.match}%</b><small>매칭률</small></span>
    </li>`).join("")}</ol>`;
}

// ── 사분면 산점도 ──
function scatterHtml(d, list) {
  const W = 440, H = 330, L = 44, R = 16, T = 18, B = 42, pw = W - L - R, ph = H - T - B;
  const x = (v) => L + (pw * v) / 30, y = (v) => T + ph - (ph * v) / 50;
  const attract = (c) => c.parts.korea + c.parts.stock + c.parts.future;
  const topList = [...list].sort((a, b) => b.total - a.total).slice(0, 3);
  const top3 = new Set(topList.map((c) => c.job_id)), rankOf = Object.fromEntries(topList.map((c, i) => [c.job_id, i + 1]));
  const xt = [0, 10, 20, 30], yt = [0, 10, 20, 30, 40, 50];
  const q = (tx, ty, t, anchor) => `<text x="${tx}" y="${ty}" class="q-lab" text-anchor="${anchor}">${t}</text>`;
  const pts = [...list].sort((a, b) => top3.has(a.job_id) - top3.has(b.job_id));
  return `<svg viewBox="0 0 ${W} ${H}" class="ovsc" role="img" aria-label="커리어 매칭과 회사 매력 산점도">
    <rect x="${x(18)}" y="${y(50)}" width="${x(30) - x(18)}" height="${y(30) - y(50)}" class="q-hot"/>
    ${yt.map((v) => `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" class="grid"/><text x="${L - 8}" y="${y(v) + 4}" text-anchor="end" class="tick">${v}</text>`).join("")}
    ${xt.map((v) => `<text x="${x(v)}" y="${H - B + 18}" text-anchor="middle" class="tick">${v}</text>`).join("")}
    <line x1="${x(18)}" x2="${x(18)}" y1="${T}" y2="${T + ph}" class="q-line"/><line x1="${L}" x2="${W - R}" y1="${y(30)}" y2="${y(30)}" class="q-line"/>
    ${q(W - R - 6, T + 14, "바로 지원", "end")}${q(L + 6, T + 14, "성장 기업 · 역량 보완", "start")}
    ${q(W - R - 6, T + ph - 8, "안정 지원", "end")}${q(L + 6, T + ph - 8, "보류", "start")}
    <text x="${L + pw / 2}" y="${H - 6}" text-anchor="middle" class="ax-t">③ 커리어 매칭 (30점)</text>
    <text transform="translate(12 ${T + ph / 2}) rotate(-90)" text-anchor="middle" class="ax-t">회사 매력 ①+②+⑤ (50점)</text>
    ${pts.map((c) => { const cx = x(c.parts.career), cy = y(attract(c)), hot = top3.has(c.job_id);
      return `<g class="pt ${hot ? "hot" : ""}" data-tip="${c.job_id}" data-dash="${c.job_id}" tabindex="0" aria-label="${esc(c.company)}: 커리어 ${c.parts.career}, 회사 매력 ${attract(c)}">
        <circle cx="${cx}" cy="${cy}" r="14" class="hit"/><circle cx="${cx}" cy="${cy}" r="${hot ? 6 : 5}" class="dot"/>
        ${hot ? `<circle cx="${cx}" cy="${cy}" r="8" class="dot hotdot"/><text x="${cx}" y="${cy + 3.5}" text-anchor="middle" class="pt-n">${rankOf[c.job_id]}</text>` : ""}</g>`; }).join("")}
  </svg>
  <div class="ovsc-key">${topList.map((c, i) => `<span data-dash="${c.job_id}"><i>${i + 1}</i>${esc(c.company)}</span>`).join("")}<em>점에 마우스를 올리면 회사·점수</em></div>`;
}

// ── 12개월 이직운 (세로 막대, 기준선 50·70) ──
function monthsHtml(d) {
  const ms = d.me.move.months || [], best = new Set((d.me.move.best || []).map((b) => b.ym));
  const W = 360, H = 210, L = 28, R = 54, T = 14, B = 30, pw = W - L - R, ph = H - T - B, bw = Math.min(18, pw / ms.length - 6);
  const y = (v) => T + ph - (ph * v) / 100;
  return `<svg viewBox="0 0 ${W} ${H}" class="mo" role="img" aria-label="12개월 이직운">
    ${[0, 50, 70, 100].map((v) => `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" class="${v === 50 || v === 70 ? "thr" : "grid"}"/>
      <text x="${L - 6}" y="${y(v) + 4}" text-anchor="end" class="tick">${v}</text>`).join("")}
    <text x="${W - R + 6}" y="${y(70) + 4}" class="thr-lab">지원 적기</text><text x="${W - R + 6}" y="${y(50) + 4}" class="thr-lab">도전 가능</text>
    ${ms.map((m, i) => { const cx = L + (pw * (i + 0.5)) / ms.length, h = y(0) - y(m.score), b = best.has(m.ym);
      return `<g class="mo-b" data-mtip="${esc(m.ym)} · ${esc(m.gz)}|${m.score}">
        <rect x="${cx - 12}" y="${T}" width="24" height="${ph}" class="hit"/>
        <path d="M${cx - bw / 2},${y(0)} V${y(m.score) + 4} q0,-4 4,-4 h${bw - 8} q4,0 4,4 V${y(0)} Z" class="${b ? "best" : "norm"}"/>
        ${b ? `<text x="${cx}" y="${y(m.score) - 5}" text-anchor="middle" class="val">${m.score}</text>` : ""}
        <text x="${cx}" y="${H - 12}" text-anchor="middle" class="tick ${b ? "b" : ""}">${+m.ym.slice(5)}</text></g>`; }).join("")}
    <text x="${W - R + 6}" y="${H - 12}" class="tick">월</text>
  </svg>
  <div class="mo-best">${(d.me.move.best || []).map((b) => `<span>${esc(b.ym)} <b>${b.score}</b></span>`).join("")}</div>`;
}

// ── 마감 임박 ──
function deadlinesHtml(list) {
  const up = [...list].filter((c) => c.dday >= 0).sort((a, b) => a.dday - b.dday).slice(0, 6);
  return `<ul class="dl">${up.map((c) => `
    <li data-dash="${c.job_id}" tabindex="0"><span class="dd ${c.dday <= 14 ? "soon" : ""}">D-${c.dday}</span>
      <span class="dl-co"><b>${esc(c.company)}</b><small>${esc(c.title)}</small></span>
      <span class="dl-bar"><i style="width:${c.total}%"></i></span><b class="dl-v">${c.total}</b></li>`).join("")}</ul>`;
}

// ── 분야별 평균 ──
function sectorsHtml(d) {
  return `<ul class="sec">${d.sectors.map((s) => `
    <li><span>${esc(s.sector)}<small>${s.n}곳</small></span><span class="sec-bar"><i style="width:${s.avg}%"></i></span><b>${s.avg}</b></li>`).join("")}</ul>`;
}

// ── 표 (접근성용 전체 값) ──
function tableHtml(d, list) {
  const [k, dir] = state.ovTableSort;
  const val = (c, key) => (key in c.parts ? c.parts[key] : c[key]);
  const rows = [...list].sort((a, b) => (typeof val(a, k) === "string" ? val(a, k).localeCompare(val(b, k)) : val(a, k) - val(b, k)) * dir);
  const th = (key, label, num = true) => `<th class="${num ? "num" : ""}" data-tsort="${key}" aria-sort="${k === key ? (dir < 0 ? "descending" : "ascending") : "none"}">${label}${k === key ? (dir < 0 ? " ↓" : " ↑") : ""}</th>`;
  return `<div class="ov-table-wrap"><table class="ov-table">
    <thead><tr>${th("company", "회사", false)}${th("sector", "분야", false)}${th("total", "회사 인연도")}
      ${OV_KEYS.map((key) => th(key, `<i class="sw s-${key}"></i>${OV_NAME[key].slice(2)}`)).join("")}
      ${th("match", "매칭률")}${th("keyword", "키워드")}${th("affinity", "이직 인연")}${th("referrers", "추천인")}${th("dday", "마감")}<th></th></tr></thead>
    <tbody>${rows.map((c) => `<tr>
      <td><b>${esc(c.company)}</b><small>${esc(c.title)}</small></td><td class="nw">${esc(c.sector)}</td>
      <td class="num"><b>${c.total}</b><span class="mini-seg">${OV_KEYS.map((key) => `<i class="s-${key}" style="flex:${c.parts[key] || 0.001}"></i>`).join("")}<i class="rest" style="flex:${100 - c.total}"></i></span></td>
      ${OV_KEYS.map((key) => `<td class="num">${c.parts[key]}<small>/${d.max[key]}</small></td>`).join("")}
      <td class="num">${c.match}%</td><td class="num">${c.keyword}%</td><td class="num">${c.affinity}%</td><td class="num">${c.referrers || "-"}</td><td class="num nw">D-${c.dday}</td>
      <td><button class="tbl-go" data-dash="${c.job_id}">대시보드 ↗</button></td></tr>`).join("")}</tbody></table></div>`;
}

function bindOverview(d, list) {
  const byId = Object.fromEntries(d.companies.map((c) => [c.job_id, c]));
  const root = $("#ovBody");
  root.onclick = (e) => {
    const g = e.target.closest("[data-ovg]"), s = e.target.closest("[data-ovs]"), t = e.target.closest("[data-tsort]"), o = e.target.closest("[data-dash]");
    if (g) { state.ovGroup = +g.dataset.ovg; return renderOverview(); }
    if (s) { state.ovSort = s.dataset.ovs; return renderOverview(); }
    if (t) { const key = t.dataset.tsort; state.ovTableSort = [key, state.ovTableSort[0] === key ? -state.ovTableSort[1] : (["company", "sector", "dday"].includes(key) ? 1 : -1)]; return renderOverview(); }
    if (o) { tip(null); openDashboard(+o.dataset.dash); }
  };
  root.onkeydown = (e) => { const o = e.target.closest("[data-dash]"); if (o && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); openDashboard(+o.dataset.dash); } };
  root.onmousemove = (e) => {
    const p = e.target.closest("[data-tip]"), m = e.target.closest("[data-mtip]");
    if (p) return tip(partsTip(byId[p.dataset.tip]), e);
    if (m) { const [lab, v] = m.dataset.mtip.split("|"); return tip(`<b>${esc(lab)}</b><div class="tt-row">이직운<b>${v}<small>/100</small></b></div>`, e); }
    tip(null);
  };
  root.onmouseleave = () => tip(null);
  root.onfocusin = (e) => { const p = e.target.closest("[data-tip]"); if (p) { const r = p.getBoundingClientRect(); tip(partsTip(byId[p.dataset.tip]), { clientX: r.right, clientY: r.top }); } };
  root.onfocusout = () => tip(null);
}

// ═══ 회사 대시보드 "점수 계산" 탭 — 추천 점수가 어떻게 만들어졌는지 ═══
async function loadScore(d) {
  const pane = $('#dashModal .dpane[data-tab="score"]');
  pane.innerHTML = `<div class="dash-loading"><span class="spin"></span>점수 계산 과정을 불러오고 있어요...</div>`;
  try {
    const b = await api("/api/score-breakdown", { job_id: d.job.id, saju: state.saju, profile: dashProfile() });
    if (pane.isConnected) pane.innerHTML = scoreHtml(b);
  } catch (err) { if (pane.isConnected) pane.innerHTML = `<p class="muted">${esc(err.message)}</p>`; }
}

// 폭포 차트: 0에서 시작해 ①~⑤를 차례로 쌓아 총점에 도달. 옅은 부분 = 받지 못한 점수
function waterfallSvg(items, total) {
  const W = 1060, H = 300, L = 34, R = 10, T = 26, B = 52, pw = W - L - R, ph = H - T - B, n = items.length + 1;
  const slot = pw / n, bw = Math.min(56, slot * 0.56), y = (v) => T + ph - (ph * v) / 100;
  let cum = 0;
  const cols = items.map((it, i) => {
    const x = L + slot * i + (slot - bw) / 2, y0 = y(cum), y1 = y(cum + it.score), y2 = y(cum + it.max), cx = x + bw / 2;
    const g = `<g class="wf-col">
      <rect x="${x}" y="${y2}" width="${bw}" height="${Math.max(0, y1 - y2)}" class="wf-miss"/>
      <rect x="${x}" y="${y1}" width="${bw}" height="${Math.max(0, y0 - y1 - 2)}" rx="3" style="fill:var(--s-${it.key})"/>
      ${true ? `<line x1="${x + bw}" x2="${x + slot}" y1="${y1}" y2="${y1}" class="wf-link"/>` : ""}
      <text x="${cx}" y="${y2 - 6}" text-anchor="middle" class="wf-v">+${it.score}</text>
      <text x="${cx}" y="${H - B + 18}" text-anchor="middle" class="wf-l">${esc(it.name.split(" ")[0])} ${esc(it.short)}</text>
      <text x="${cx}" y="${H - B + 34}" text-anchor="middle" class="wf-s">${it.score} / ${it.max}</text></g>`;
    cum += it.score;
    return g;
  }).join("");
  const tx = L + slot * items.length + (slot - bw) / 2;
  return `<svg viewBox="0 0 ${W} ${H}" class="wf" role="img" aria-label="회사 인연도 계산 폭포 차트: ${items.map((i) => `${i.name} ${i.score}점`).join(", ")}, 합계 ${total}점">
    ${[0, 25, 50, 75, 100].map((v) => `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" class="wf-grid"/><text x="${L - 6}" y="${y(v) + 4}" text-anchor="end" class="wf-t">${v}</text>`).join("")}
    ${cols}
    <rect x="${tx}" y="${y(total)}" width="${bw}" height="${y(0) - y(total)}" rx="3" class="wf-total"/>
    <text x="${tx + bw / 2}" y="${y(total) - 8}" text-anchor="middle" class="wf-tv">${total}</text>
    <text x="${tx + bw / 2}" y="${H - B + 18}" text-anchor="middle" class="wf-l b">회사 인연도</text>
    <text x="${tx + bw / 2}" y="${H - B + 34}" text-anchor="middle" class="wf-s">/ 100</text>
  </svg>`;
}

function scoreHtml(b) {
  const SHORT = { korea: "한국 사업", stock: "주가 성장", career: "커리어", saju: "사주 인연", future: "미래사업" };
  const items = b.fit.items.map((i) => ({ ...i, short: SHORT[i.key] }));
  const lost = items.reduce((s, i) => s + i.max - i.score, 0);
  const meter = (pts, mx, color) => `<span class="sm-meter"><i style="width:${Math.max(0, (100 * pts) / mx)}%;background:${color}"></i></span>`;

  // A. 회사 인연도 폭포
  const A = `
    <section class="dcard sc-hero">
      <div class="sc-hero-top">
        <div><h5>회사 인연도 계산 흐름</h5><p class="muted">0점에서 시작해 ①~⑤ 점수를 차례로 더해요. 옅은 부분은 받지 못한 점수예요.</p></div>
        <div class="sc-eq"><span>${items.map((i) => `<b>${i.score}</b>`).join("<em>+</em>")}</span><em>=</em><strong>${b.fit.total}</strong><small>/100</small></div>
      </div>
      ${waterfallSvg(items, b.fit.total)}
      <div class="sc-legend"><span><i class="sw wf-miss-sw"></i>받지 못한 점수 ${lost}점</span>${items.map((i) => `<span><i class="sw s-${i.key}"></i>${esc(i.name)}</span>`).join("")}</div>
    </section>`;

  // B. 항목별 계산 카드
  const card = (i) => {
    const color = `var(--s-${i.key})`;
    const rows = i.lines ? `<table class="calc">${i.lines.map((l) => `<tr><th>${esc(l.label)}</th><td class="cv">${esc(l.value)}</td>
        <td class="cm">${meter(l.pts, l.max, color)}</td><td class="cp"><b>${l.pts}</b><small>/${l.max}</small></td></tr>`).join("")}</table>` : "";
    const basePts = i.saju_lines ? i.raw - i.saju_lines.reduce((t, l) => t + (l.pts || 0), 0) : 0;
    const sj = i.saju_lines ? `<ul class="sj-lines">${i.saju_lines.map((l) => { const v = l.pts != null ? l.pts : basePts;
      return `<li><span>${esc(l.label)}${l.pts == null ? ` <small class="base">일주 궁합 기본점</small>` : ""}</span><b class="${v >= 0 ? "pos" : "neg"}">${v > 0 ? "+" : ""}${v}</b></li>`; }).join("")}
      <li class="sj-sum"><span>원점수 합계</span><b>${i.raw}</b></li></ul>` : "";
    return `<section class="dcard calc-card" style="--c:${color}">
      <header><span class="cc-sw"></span><h6>${esc(i.name)}</h6><b class="cc-score">${i.score}<small> / ${i.max}</small></b></header>
      ${meter(i.score, i.max, color).replace("sm-meter", "sm-meter big")}
      ${rows}${sj}
      ${i.calc ? `<div class="calc-line">${esc(i.calc)}</div>` : ""}
      <p class="calc-rule">규칙: ${esc(i.rule)}</p>
    </section>`;
  };
  const B = `<div class="calc-grid">${items.map(card).join("")}</div>`;

  // C. 매칭률 (추천 순위) · 합격 가능성
  const m = b.match, MC = { career: "var(--s-career)", pay: "var(--s-pay)", affinity: "var(--s-saju)" };
  const sum = m.items.reduce((s, x) => s + x.contrib, 0);
  const C = `
    <section class="dcard match-calc">
      <h5>매칭률 계산 — 매칭 공고 추천 순위의 기준</h5>
      <div class="mc-rows">${m.items.map((x) => `
        <div class="mc-row"><span class="mc-name"><i class="sw" style="background:${MC[x.key]}"></i>${esc(x.name)}</span>
          <span class="mc-raw">${meter(x.raw, 100, MC[x.key])}<b>${x.raw}</b><small>/100</small></span>
          <span class="mc-op">× ${x.w}</span><span class="mc-op">=</span><b class="mc-c">${x.contrib.toFixed(1)}</b></div>`).join("")}
      </div>
      <div class="mc-stack" aria-hidden="true">${m.items.map((x) => `<i style="flex:${x.contrib};background:${MC[x.key]}"></i>`).join("")}<i class="rest" style="flex:${100 - sum}"></i></div>
      <div class="mc-sum"><span>합계 ${sum.toFixed(1)} → 반올림</span><strong>매칭률 ${m.total}%</strong></div>
      <div class="mc-pass"><span>합격 가능성 = 5 + ${m.total} × 0.9</span><strong>${m.pass_rate}%</strong><em>AI 추정치 · 실제 통계 아님</em></div>
    </section>`;

  // D. 점수 올리기 시뮬레이션
  const gmax = Math.max(1, ...b.whatif.map((w) => Math.max(w.fit_gain, w.match_gain)));
  const D = `
    <section class="dcard whatif">
      <h5>점수 올리기 시뮬레이션 — 내가 준비하면 바뀌는 점수</h5>
      ${b.whatif.length ? `<table class="wi">
        <thead><tr><th>준비할 것</th><th class="num">회사 인연도</th><th></th><th class="num">매칭률</th><th></th><th class="num">합격 가능성</th></tr></thead>
        <tbody>${b.whatif.map((w) => `<tr><td><b>${esc(w.action)}</b><small>${esc(w.why)}</small></td>
          <td class="num"><b>+${w.fit_gain}</b><small>→ ${w.fit}</small></td><td class="wbar">${meter(w.fit_gain, gmax, "var(--emph)")}</td>
          <td class="num"><b>+${w.match_gain}</b><small>→ ${w.match}%</small></td><td class="wbar">${meter(w.match_gain, gmax, "var(--emph)")}</td>
          <td class="num"><b>+${w.pass_gain}</b><small>→ ${w.pass}%</small></td></tr>`).join("")}</tbody></table>`
        : `<p class="muted">요구 기술·연봉·직급이 이미 모두 맞아요. 남은 점수는 회사·사주 항목이라 준비로 바뀌지 않아요.</p>`}
      <p class="muted">사주 인연·회사(한국 사업·주가·미래사업) 항목은 내가 바꿀 수 없어서, 기술·기대 연봉·희망 직급을 바꿨을 때만 다시 계산했어요.</p>
    </section>`;

  return A + `<div class="g2 sc-mid">${C}${D}</div>` + `<h4 class="calc-title">항목별 계산 풀이</h4>` + B;
}

// ═══ 회사 대시보드 "키워드 매칭" 탭 — 구인 요건 핵심 키워드 × 내 레주메 ═══
const KW_ST = { "있음": ["ok", "✓"], "관련 경험": ["mid", "△"], "없음": ["no", "✕"] };
async function loadKeywords(d) {
  const pane = $('#dashModal .dpane[data-tab="keywords"]');
  pane.innerHTML = `<div class="dash-loading"><span class="spin"></span>구인 요건을 분석하고 레주메와 맞춰 보고 있어요...</div>`;
  try {
    const k = await api("/api/keywords", { job_id: d.job.id, profile: dashProfile() });
    if (pane.isConnected) pane.innerHTML = keywordsHtml(k, d);
  } catch (err) { if (pane.isConnected) pane.innerHTML = `<p class="muted">${esc(err.message)}</p>`; }
}

function keywordsHtml(k, d) {
  const st = (s) => `<span class="kw-st ${KW_ST[s][0]}"><i aria-hidden="true">${KW_ST[s][1]}</i>${s}</span>`;
  const maxImp = Math.max(...k.rows.map((r) => r.imp));
  // 1) 요약
  const sum = `
    <div class="kw-top">
      <div class="kw-hero">
        <small>레주메 키워드 매칭률</small>
        <div class="kw-hero-row"><b>${k.rate}</b><span>%</span></div>
        <span class="kw-meter" aria-hidden="true"><i style="width:${k.rate}%"></i></span>
        <em>중요도를 반영한 점수 · 있음 1 · 관련 경험 0.5 · 없음 0</em>
      </div>
      <div class="kw-stat"><small>필수 기술 충족</small><b>${k.must_ok}<span>/ ${k.must_total}</span></b><em>공고 앞쪽 3개 기술</em></div>
      <div class="kw-stat"><small>${st("있음")}</small><b>${k.counts["있음"]}<span>개</span></b><em>레주메에 그대로 있음</em></div>
      <div class="kw-stat"><small>${st("관련 경험")}</small><b>${k.counts["관련 경험"]}<span>개</span></b><em>비슷한 경험으로 연결 가능</em></div>
      <div class="kw-stat"><small>${st("없음")}</small><b>${k.counts["없음"]}<span>개</span></b><em>보완 필요</em></div>
    </div>
    ${k.has_resume ? "" : `<div class="ai-warn">레주메(프로필) 글이 없어 첨삭에서 뽑은 기술만으로 비교했어요. 1단계에 프로필을 붙여넣으면 더 정확해요.</div>`}`;
  // 2) 키워드 한눈에 (크기 = 중요도, 테두리 = 매칭 상태) — 정확한 값은 아래 표
  const cloud = `
    <section class="dcard">
      <h5>구인 요건 핵심 키워드 — 크기는 중요도, 표시는 내 레주메 매칭</h5>
      <div class="kw-cloud">${k.rows.map((r) => `<span class="kw-chip ${KW_ST[r.status][0]}" style="--s:${(0.78 + 0.5 * (r.imp / maxImp)).toFixed(2)}" title="중요도 ${r.imp} · ${r.status}">
        <i aria-hidden="true">${KW_ST[r.status][1]}</i>${esc(r.kw)}<small>${r.imp}</small></span>`).join("")}</div>
      <div class="kw-legend">${Object.keys(KW_ST).map((s) => st(s)).join("")}<span class="muted">숫자 = 중요도(0~100)</span></div>
    </section>`;
  // 3) 상세 표
  const table = `
    <section class="dcard">
      <h5>요건 키워드별 매칭 상세 (중요도 순)</h5>
      <table class="kw-table">
        <thead><tr><th>키워드</th><th>구분</th><th class="num">중요도</th><th></th><th>내 레주메</th><th>근거 (레주메 문장)</th></tr></thead>
        <tbody>${k.rows.map((r) => `<tr>
          <td><b>${esc(r.kw)}</b></td><td><span class="kw-type">${esc(r.type)}</span></td>
          <td class="num">${r.imp}</td><td class="kw-bar"><span class="sm-meter"><i style="width:${r.imp}%;background:var(--emph)"></i></span></td>
          <td>${st(r.status)}</td><td class="kw-ev">${r.evidence ? `“${esc(r.evidence)}”` : `<span class="muted">레주메에서 찾지 못함</span>`}</td></tr>`).join("")}</tbody>
      </table>
      <p class="muted">중요도: 필수 기술 100·92·84(직무명에 있으면 +8) · 경력·직급 85 · 직무 업무 75 · 우대 기술 70부터 · 영어 유창 80/비즈니스 65/업무 가능 50</p>
    </section>`;
  // 4) 보완 우선순위 · 레주메 강점
  const gaps = k.rows.filter((r) => r.status !== "있음").sort((a, b) => b.imp - a.imp);
  const gapCard = `
      <section class="dcard">
        <h5>보완 우선순위 — 중요도 높은 것부터</h5>
        ${gaps.length ? `<ol class="kw-gaps">${gaps.map((r) => `<li><span class="kw-rank">${r.imp}</span><div><b>${esc(r.kw)}</b> ${st(r.status)}
          <p>${r.status === "관련 경험" ? `레주메의 비슷한 경험을 <b>${esc(r.kw)}</b>라는 말로 다시 써 주세요. (예: “${esc(r.evidence || "")}”에 ${esc(r.kw)} 언급 추가)`
            : r.type === "언어·협업" ? "영어로 진행한 회의·문서·발표 경험이나 어학 점수를 레주메에 적어 주세요."
            : r.type === "경력·직급" ? "연차가 부족해요. 맡았던 범위·성과를 숫자로 적어 경력의 깊이를 보여 주세요."
            : r.type === "직무 업무" ? `${esc(r.kw)} 경험을 레주메에 구체적으로(무엇을·어떻게·결과) 적어 주세요.` : `${esc(r.kw)} 미니 프로젝트를 만들어 깃허브 링크와 함께 레주메에 추가하면 좋아요.`}</p></div></li>`).join("")}</ol>`
          : `<p class="muted">요건 키워드를 모두 갖췄어요.</p>`}
      </section>`;
  const extraCard = `
      <section class="dcard">
        <h5>요건에는 없지만 내 레주메의 강점 키워드</h5>
        <div class="req-skills">${k.extra.map((s) => `<span class="have">＋ ${esc(s)}</span>`).join("") || `<span class="muted">-</span>`}</div>
        <p class="muted" style="margin-top:10px">면접에서 “추가로 기여할 수 있는 부분”으로 말하기 좋은 키워드예요.</p>
      </section>`;
  return sum + `<div class="g2 kw-mid"><div class="stack-col">${cloud}${extraCard}</div>${gapCard}</div>` + table;
}

// ═══ 구인자 화면: 받은 연결 요청 · 공고 등록(실시간 미리보기) · 등록한 공고 ═══
state.rTab = "requests"; state.rMeta = null; state.rSkills = []; state.rNews = [{}];
const R_SAMPLE = {
  company: "Nimbusway AI", hq: "미국", title: "GenAI Backend Engineer", level: "미들", years_min: 3, years_max: 6,
  salary_min: 8000, salary_max: 10500, english: "비즈니스", location: "서울 강남", deadline: "", recruiter_name: "한지수",
  sector: "AI·데이터", listed: "NASDAQ", price: "$64.20", chg: 1.4, w52: 38, revenue: 12.5, emp: 5200, emp_kr: 90,
  growth: 30, yoy: 34, margin: 12, expand: "높음", plan: "서울 GenAI 센터 신설, 한국 엔지니어 40명 채용",
  skills: ["Python", "FastAPI", "LangGraph", "AWS", "Kubernetes"],
  news: [{ title: "Nimbusway, 한빛카드와 AI 상담 서비스 공동 개발", partner: "한빛카드", kind: "공동 개발", date: "2026-11-02", kw: "LangGraph, Python" },
         { title: "Nimbusway 서울 GenAI 센터 설립", partner: "", kind: "한국 투자", date: "2026-10-20", kw: "" }],
};

async function renderRecruiter() {
  if (!state.rMeta) state.rMeta = await api("/api/recruiter/meta").catch(() => null);
  const [reqs, mine, db] = await Promise.all([api("/api/recruiter/requests"), api("/api/recruiter/jobs"), api("/api/admin/db").catch(() => null)]);
  const tab = (k, n, c) => `<button class="rt ${state.rTab === k ? "on" : ""}" data-rtab="${k}">${n}${c != null ? `<small>${c}</small>` : ""}</button>`;
  $("#recruiterBody").innerHTML = `
    <div class="r-bar">
      <nav class="rtabs">${tab("requests", "받은 연결 요청", reqs.length)}${tab("post", "공고 등록")}${tab("mine", "등록한 공고", mine.length)}</nav>
      ${db ? `<span class="db-chip" title="저장소 상태"><i class="${db.backend === "postgresql" ? "pg" : "lite"}"></i>${db.backend === "postgresql" ? "PostgreSQL 운영 DB" : "SQLite 파일 DB"} · 공고 ${db.counts.job || 0} · 요청 ${db.counts.application || 0} · 추천 ${db.counts.referral || 0}</span>` : ""}
    </div>
    <div id="rPane"></div>`;
  $$(".rt").forEach((b) => b.addEventListener("click", () => { state.rTab = b.dataset.rtab; renderRecruiter(); }));
  const pane = $("#rPane");
  if (state.rTab === "requests") pane.innerHTML = requestsHtml(reqs);
  if (state.rTab === "mine") pane.innerHTML = mineHtml(mine);
  if (state.rTab === "post") { pane.innerHTML = postFormHtml(); bindPostForm(); }
}

function requestsHtml(reqs) {
  return reqs.length ? `
    <table class="table"><thead><tr><th>포지션</th><th>후보자 요약</th><th>경력 · 직급</th><th>기대 연봉</th><th>커리어</th><th>연봉·직급</th><th>상태</th></tr></thead>
    <tbody>${reqs.map((q) => { const c = q.candidate; return `<tr>
      <td><b>${esc(q.job.company)}</b><br><small>${esc(q.job.title)}</small></td>
      <td>${q.verified ? `<b>${esc(q.verified.name)}</b> <span class="li-ok">✓ 링크드인 확인</span><br><small>${esc(q.verified.email || "")}</small><br>` : ""}${esc(c.summary || "")}<br><small>${(c.skills || []).map(esc).join(", ")}</small>${c.linkedin_url ? `<br><a href="${esc(c.linkedin_url)}" target="_blank" rel="noopener">링크드인 프로필</a>` : ""}</td>
      <td>${c.years ?? "-"}년 · ${esc(c.level || "-")} → 희망 ${esc(c.desired_level || "-")}</td>
      <td>${c.expected_salary ? c.expected_salary.toLocaleString() + "만" : "-"}</td>
      <td class="c-comp"><b>${q.career_score ?? "-"}</b></td><td class="c-pay"><b>${q.pay_score ?? "-"}</b></td>
      <td><select data-status="${q.id}">${STATUSES.map((s) => `<option ${s === q.status ? "selected" : ""}>${s}</option>`).join("")}</select></td>
    </tr>${c.resume_summary ? `<tr class="rs-row"><td colspan="7"><details ${reqs.length <= 3 ? "open" : ""}><summary>📄 AI 레주메 분석 요약 — ${esc(c.resume_summary.headline || "")}</summary>${summaryHtml(c.resume_summary, { eyebrow: "지원자 레주메 · AI 분석 요약", compact: true })}</details></td></tr>` : ""}`; }).join("")}</tbody></table>
    <p class="muted">구인자에게는 커리어·연봉/직급 점수, 프로필, <b>AI 레주메 요약</b>(한 줄 소개·경력 타임라인·성과·기술)만 보여요. 생년월일·사주·인연 점수·레주메 원문은 전달되지 않아요. 상태를 바꾸면 DB에 저장돼요.</p>`
    : `<div class="empty"><b>아직 받은 연결 요청이 없어요</b>구직자가 매칭 공고에서 연결을 요청하면 여기에 나타나요.</div>`;
}

function mineHtml(mine) {
  if (!mine.length) return `<div class="empty"><b>직접 등록한 공고가 없어요</b>"공고 등록" 탭에서 첫 공고를 올려 보세요. 등록하면 바로 구직자 랭킹·대시보드에 반영돼요.</div>`;
  const dd = (d) => Math.round((new Date(d) - new Date(new Date().toISOString().slice(0, 10))) / 864e5);
  return `<div class="mine-grid">${mine.map((j) => `
    <article class="mine-card">
      <header><span class="logo">${esc(j.company.split(/\s+/).map((w) => w[0]).join("").slice(0, 2))}</span>
        <div><small>${famBadge(j)} ${esc(j.sector || "기타")} · ${esc(j.hq)} 본사 · ${srcBadge(j)}</small><b>${esc(j.company)}</b><span>${esc(j.title)}</span></div>
        <em class="dday ${dd(j.deadline) <= 14 ? "soon" : ""}">D-${dd(j.deadline)}</em></header>
      <div class="mine-facts"><span>${esc(j.level)}</span><span>경력 ${j.years_min}~${j.years_max}년</span><span>${esc(j.salary)}</span><span>영어 ${esc(j.english)}</span></div>
      <div class="req-skills">${j.skills.map((s, i) => `<span class="${i < 3 ? "have" : ""}">${i < 3 ? "필수" : "우대"} · ${esc(s)}</span>`).join("")}</div>
      <footer><span>받은 연결 요청 <b>${j.requests}</b>건 · 한국 사업 소식 ${(j.news || []).length}건</span>
        <button class="btn-ghost sm" data-rdash="${j.id}">구직자 화면에서 보기 ↗</button><button class="btn-ghost sm danger" data-rdel="${j.id}">삭제</button></footer>
    </article>`).join("")}</div>`;
}

// ── 공고 등록 폼 ──
function postFormHtml() {
  const m = state.rMeta || { levels: [], english: [], expand: [], sectors: [], news_kinds: [], skills: [] };
  const seg = (name, opts, val) => `<div class="pf-seg" data-seg="${name}">${opts.map((o) => `<button type="button" class="${o === val ? "on" : ""}" data-v="${esc(o)}">${esc(o)}</button>`).join("")}</div><input type="hidden" name="${name}" value="${esc(val)}">`;
  const f = (label, name, type = "text", ph = "", extra = "", cls = "") => `<label class="pf ${cls}"><span>${label}</span><input name="${name}" type="${type}" placeholder="${esc(ph)}" ${extra}></label>`;
  return `
  <form class="post-wrap" id="postForm" autocomplete="off" novalidate>
    <div class="post-form">
      <section class="li-imp" id="liImp">
        <header><span class="li-logo">⇣</span><div><h4>구직 사이트 공고 가져오기</h4>
          <p>링크드인·원티드·리멤버 등에 올린 우리 회사 공고를 <b>복사해 붙여넣으면</b> AI가 아래 칸을 채우고, <b>출처</b>를 구직자에게 보여 줘요.</p></div></header>
        <div class="site-row" id="siteRow" role="group" aria-label="공고 출처">${(m.sites || []).map((x) => `<button type="button" class="${x.key === state.rSite ? "on" : ""}" data-site="${x.key}">${esc(x.name)}</button>`).join("")}</div>
        <ol class="li-steps"><li><b id="siteName1">링크드인</b>에서 공고를 열어요</li><li>공고 글 전체를 드래그해 복사 <kbd>Ctrl</kbd>+<kbd>C</kbd></li><li>아래에 붙여넣기 <kbd>Ctrl</kbd>+<kbd>V</kbd></li></ol>
        <label class="pf" id="liUrlWrap"><span><b id="siteName2">링크드인</b> 공고 주소 <small>(선택 · 구직자에게 "원문 ↗" 링크로 보여요)</small></span>
          <input id="liUrl" placeholder="https://www.linkedin.com/jobs/view/1234567890"></label>
        <label class="pf"><span>공고 글 *</span><textarea id="liText" rows="6" placeholder="About the job&#10;We are looking for a Senior Backend Engineer...&#10;Requirements: 5+ years of Python..."></textarea></label>
        <div class="li-act"><small class="muted">서버는 그 사이트에 접속하지 않아요 (붙여넣은 글만 정리) · 연봉·마감일은 공고에 있을 때만 채워요</small>
          <button type="button" class="btn-primary sm" id="liParse">AI로 자동 채우기 <span>→</span></button></div>
        <div id="liResult"></div>
      </section>
      <input type="hidden" name="source_url" value=""><input type="hidden" name="source_site" value="direct">
      <div class="pf-actions"><p class="muted">*표시는 꼭 입력해요. 회사 정보는 회사 인연도(① 한국 사업확대 · ② 주가 성장성 · ⑤ 미래사업)에 바로 쓰여요.</p>
        <button type="button" class="btn-ghost sm" id="pfSample">예시로 채우기</button></div>
      <section class="pf-card"><h4><span>1</span>포지션</h4>
        <div class="pf-grid">${f("회사명 *", "company", "text", "예) Nimbusway AI")}${f("본사 국가 *", "hq", "text", "예) 미국")}
          ${f("포지션 *", "title", "text", "예) GenAI Backend Engineer", "", "wide")}
          <label class="pf wide"><span>직종 * <small>구직자 화면의 직종 필터에 쓰여요</small></span>${seg("family", (m.families || []).map((f) => f.name), "")}</label>
          <label class="pf wide"><span>직급 *</span>${seg("level", m.levels, "미들")}</label>
          ${f("경력 최소(년) *", "years_min", "number", "3", 'min="0" max="30"')}${f("경력 최대(년) *", "years_max", "number", "6", 'min="0" max="40"')}
          ${f("근무지 *", "location", "text", "예) 서울 강남 / 원격 근무")}${f("마감일 *", "deadline", "date")}
          ${f("채용 담당자 이름 *", "recruiter_name", "text", "예) 한지수")}</div></section>
      <section class="pf-card"><h4><span>2</span>조건 · 요구 기술</h4>
        <div class="pf-grid">${f("연봉 최소(만원) *", "salary_min", "number", "8000", 'step="100"')}${f("연봉 최대(만원) *", "salary_max", "number", "10500", 'step="100"')}
          <label class="pf wide"><span>영어 수준 *</span>${seg("english", m.english, "업무 가능")}</label>
          <div class="pf wide"><span>요구 기술 * <small>입력 후 Enter · 앞의 3개가 <b>필수 기술</b>(키워드 중요도 100·92·84), 나머지는 우대</small></span>
            <div class="skill-box" id="skillBox"><div id="skillChips"></div><input id="skillIn" placeholder="예) Python" list="skillList"></div>
            <datalist id="skillList">${m.skills.map((s) => `<option value="${esc(s)}">`).join("")}</datalist>
            <div class="skill-sugg">${m.skills.slice(0, 18).map((s) => `<button type="button" data-addskill="${esc(s)}">＋ ${esc(s)}</button>`).join("")}</div></div></div></section>
      <section class="pf-card"><h4><span>3</span>회사 정보 <small>회사 인연도 ② 주가 성장성 · ⑤ 미래사업</small></h4>
        <div class="pf-grid three">
          <label class="pf"><span>미래사업 분야</span><select name="sector">${m.sectors.map((s) => `<option>${esc(s)}</option>`).join("")}</select></label>
          ${f("상장 시장 <small>(비상장이면 빈칸)</small>", "listed", "text", "예) NASDAQ")}${f("현재 주가", "price", "text", "예) $64.20")}
          ${f("전일 대비(%)", "chg", "number", "1.4", 'step="0.1"')}${f("52주 주가 변동(%)", "w52", "number", "38")}${f("연매출(억 달러)", "revenue", "number", "12.5", 'step="0.1"')}
          ${f("전년 대비 매출(%)", "yoy", "number", "34")}${f("영업이익률(%)", "margin", "number", "12")}${f("향후 3년 성장률(%/년)", "growth", "number", "30")}
          ${f("글로벌 직원 수", "emp", "number", "5200")}${f("한국 법인 인원", "emp_kr", "number", "90")}</div></section>
      <section class="pf-card"><h4><span>4</span>한국 사업 <small>회사 인연도 ① 한국 사업확대</small></h4>
        <div class="pf-grid"><label class="pf wide"><span>한국 확대 가능성</span>${seg("expand", m.expand, "보통")}</label>
          ${f("확대 계획·근거", "plan", "text", "예) 서울 GenAI 센터 신설, 한국 엔지니어 40명 채용", "", "wide")}</div>
        <div class="news-rows" id="newsRows"></div>
        <button type="button" class="btn-ghost sm" id="addNews">＋ 한국 사업 소식 추가</button>
        <p class="muted">한국 기업과의 제휴·공동 개발·계약·투자 소식. 파트너 1곳당 3점(최대 2곳), 한국 투자 소식 4점. 사실인 내용만 적어 주세요.</p></section>
    </div>
    <aside class="post-preview" id="postPreview"></aside>
  </form>`;
}

function newsRowsHtml() {
  const kinds = (state.rMeta || {}).news_kinds || [];
  return state.rNews.map((n, i) => `
    <div class="news-row" data-ni="${i}">
      <input type="date" data-nf="date" value="${esc(n.date || "")}" aria-label="날짜">
      <select data-nf="kind" aria-label="유형">${kinds.map((k) => `<option ${k === n.kind ? "selected" : ""}>${esc(k)}</option>`).join("")}</select>
      <input data-nf="partner" class="p" placeholder="한국 파트너 기업 (한국 투자 소식이면 빈칸)" value="${esc(n.partner || "")}">
      <input data-nf="title" class="t" placeholder="소식 제목 (예: ○○, △△와 AI 상담 공동 개발)" value="${esc(n.title || "")}">
      <input data-nf="kw" class="k" placeholder="관련 기술 (쉼표로 구분)" value="${esc(n.kw || "")}">
      <button type="button" class="nr-del" data-delnews="${i}" aria-label="삭제">✕</button>
    </div>`).join("");
}

function readPostForm() {
  const fm = $("#postForm"), v = (n) => fm.elements[n].value.trim(), num = (n) => (fm.elements[n].value === "" ? null : Number(fm.elements[n].value));
  return {
    company: v("company"), hq: v("hq"), title: v("title"), level: v("level"), years_min: num("years_min") ?? 0, years_max: num("years_max") ?? 0,
    skills: state.rSkills, salary_min: num("salary_min") ?? 0, salary_max: num("salary_max") ?? 0, english: v("english"),
    location: v("location"), deadline: v("deadline"), recruiter_name: v("recruiter_name"),
    sector: v("sector"), listed: v("listed"), price: v("price"), chg: num("chg"), w52: num("w52"), revenue: num("revenue") ?? 0,
    emp: num("emp") ?? 0, emp_kr: num("emp_kr") ?? 0, growth: num("growth") ?? 0, yoy: num("yoy") ?? 0, margin: num("margin") ?? 0,
    expand: v("expand"), plan: v("plan"), source_url: v("source_url"), source_site: v("source_site") || "direct", family: v("family"),
    news: state.rNews.filter((n) => (n.title || "").trim()).map((n) => ({ ...n, kw: String(n.kw || "").split(",").map((x) => x.trim()).filter(Boolean) })),
  };
}

function renderSkillChips() {
  $("#skillChips").innerHTML = state.rSkills.map((s, i) => `<span class="sk ${i < 3 ? "must" : ""}"><em>${i < 3 ? "필수" : "우대"}</em>${esc(s)}<button type="button" data-delskill="${i}" aria-label="${esc(s)} 빼기">✕</button></span>`).join("");
}

let _pvTimer;
function schedulePreview() { clearTimeout(_pvTimer); _pvTimer = setTimeout(updatePreview, 350); }
async function updatePreview() {
  const box = $("#postPreview"); if (!box) return;
  const d = readPostForm();
  const dday = d.deadline ? Math.round((new Date(d.deadline) - new Date(new Date().toISOString().slice(0, 10))) / 864e5) : null;
  let score = null, err = null;
  try { score = await api("/api/recruiter/preview", d); } catch (e) { err = e.message; }
  const meter = (x, mx, k) => `<div class="pv-row"><span><i class="sw s-${k}"></i>${OV_NAME[k]}</span><span class="sm-meter"><i style="width:${(100 * x) / mx}%;background:var(--s-${k})"></i></span><b>${x}<small>/${mx}</small></b></div>`;
  box.innerHTML = `
    <div class="pv-sticky">
      <p class="pv-label">구직자에게 보이는 모습 (미리보기)</p>
      <article class="pv-card">
        <header><span class="logo">${esc((d.company || "?").split(/\s+/).map((w) => w[0]).join("").slice(0, 2))}</span>
          <div><small>${d.family ? `${famBadge(d)} ` : ""}외국계 · ${esc(d.hq || "본사 국가")} 본사 · ${esc(d.sector)} ${srcBadge({ source_site: d.source_site, source_site_name: siteName(d.source_site), source_url: d.source_url })}</small><b>${esc(d.company || "회사명")}</b><span>${esc(d.title || "포지션")}</span></div>
          ${dday != null ? `<em class="dday ${dday <= 14 ? "soon" : ""}">D-${dday}</em>` : ""}</header>
        <div class="mine-facts"><span>${esc(d.level)}</span><span>경력 ${d.years_min}~${d.years_max}년</span><span>${d.salary_min ? `${d.salary_min.toLocaleString()}~${d.salary_max.toLocaleString()}만` : "연봉"}</span><span>영어 ${esc(d.english)}</span><span>${esc(d.location || "근무지")}</span></div>
        <div class="req-skills">${d.skills.map((s, i) => `<span class="${i < 3 ? "have" : ""}">${esc(s)}</span>`).join("") || `<span class="muted">요구 기술을 넣어 주세요</span>`}</div>
      </article>
      <section class="pv-score">
        <header><span>회사 쪽 점수 <small>구직자와 무관한 50점</small></span><b>${score ? score.company_side : "-"}<small>/50</small></b></header>
        ${score ? meter(score.korea.score, 20, "korea") + meter(score.stock.score, 20, "stock") + meter(score.future.score, 10, "future")
          + `<p class="muted">③ 커리어 매칭(30) · ④ 사주 인연(20)은 구직자마다 달라져요. 총 회사 인연도 = 회사 쪽 50 + 구직자 쪽 50</p>`
          : `<div class="pv-err"><b>아직 등록할 수 없어요</b><ul>${String(err || "").split(" · ").map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>`}
      </section>
      <button type="submit" class="btn-primary pv-submit" ${score ? "" : "disabled"}>공고 등록하기 <span>→</span></button>
      <p class="muted">등록하면 DB에 저장되고, 바로 구직자의 매칭 공고·종합 대시보드·회사 대시보드에 나타나요.</p>
    </div>`;
}

function bindPostForm() {
  const fm = $("#postForm");
  renderSkillChips(); $("#newsRows").innerHTML = newsRowsHtml();
  fm.addEventListener("input", (e) => {
    const row = e.target.closest("[data-ni]");
    if (row) state.rNews[+row.dataset.ni][e.target.dataset.nf] = e.target.value;
    e.target.closest(".pf")?.classList.remove("li-need");
    if (e.target.id !== "skillIn") schedulePreview();
  });
  fm.addEventListener("change", (e) => { const row = e.target.closest("[data-ni]"); if (row) state.rNews[+row.dataset.ni][e.target.dataset.nf] = e.target.value; schedulePreview(); });
  fm.addEventListener("click", (e) => {
    const sb = e.target.closest("[data-seg] button");
    if (sb) { const g = sb.parentElement; $$("button", g).forEach((x) => x.classList.toggle("on", x === sb)); fm.elements[g.dataset.seg].value = sb.dataset.v; g.closest(".pf")?.classList.remove("li-need"); schedulePreview(); return; }
    const add = e.target.closest("[data-addskill]"); if (add) { addSkill(add.dataset.addskill); return; }
    const del = e.target.closest("[data-delskill]"); if (del) { state.rSkills.splice(+del.dataset.delskill, 1); renderSkillChips(); schedulePreview(); return; }
    const dn = e.target.closest("[data-delnews]"); if (dn) { state.rNews.splice(+dn.dataset.delnews, 1); if (!state.rNews.length) state.rNews.push({}); $("#newsRows").innerHTML = newsRowsHtml(); schedulePreview(); return; }
    if (e.target.id === "addNews") { if (state.rNews.length < 5) { state.rNews.push({ kind: "제휴" }); $("#newsRows").innerHTML = newsRowsHtml(); } return; }
    if (e.target.id === "pfSample") fillSample();
    if (e.target.closest("#skillBox")) $("#skillIn").focus();
  });
  $("#skillIn").addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === ",") { e.preventDefault(); addSkill(e.target.value); e.target.value = ""; }
    if (e.key === "Backspace" && !e.target.value && state.rSkills.length) { state.rSkills.pop(); renderSkillChips(); schedulePreview(); }
  });
  fm.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const job = await api("/api/recruiter/jobs", readPostForm());
      toast(`'${job.company} · ${job.title}' 공고를 등록했어요. 구직자 화면에 바로 반영돼요.`);
      state.ranked = null; state.ov = null; state.ovHtml = null; state.rSkills = []; state.rNews = [{}]; state.rTab = "mine"; state.liDraft = null; state.rSite = "linkedin";
      renderRecruiter();
    } catch (err) { toast(err.message, true); }
  });
  updatePreview();
}
function addSkill(s) {
  s = String(s || "").trim().replace(/,$/, "");
  if (!s || state.rSkills.some((x) => x.toLowerCase() === s.toLowerCase())) return;
  if (state.rSkills.length >= 8) return toast("요구 기술은 8개까지예요.", true);
  state.rSkills.push(s); renderSkillChips(); schedulePreview();
}
function fillSample() {
  const fm = $("#postForm"), d = { ...R_SAMPLE };
  d.deadline = new Date(Date.now() + 30 * 864e5).toISOString().slice(0, 10);
  Object.entries(d).forEach(([k, v]) => { if (fm.elements[k] && !Array.isArray(v)) fm.elements[k].value = v; });
  ["level", "english", "expand"].forEach((k) => $$(`[data-seg="${k}"] button`).forEach((b) => b.classList.toggle("on", b.dataset.v === d[k])));
  state.rSkills = [...d.skills]; state.rNews = d.news.map((n) => ({ ...n }));
  renderSkillChips(); $("#newsRows").innerHTML = newsRowsHtml(); updatePreview();
  toast("예시 회사로 채웠어요 (가상 회사).");
}

// 등록한 공고: 삭제 · 구직자 화면에서 보기
document.addEventListener("click", async (e) => {
  const del = e.target.closest("[data-rdel]");
  if (del) {
    if (!confirm("이 공고를 삭제할까요? DB에서도 지워져요.")) return;
    try { await api(`/api/recruiter/jobs/${del.dataset.rdel}`, null, "DELETE"); state.ranked = null; state.ov = null; state.ovHtml = null; toast("공고를 삭제했어요."); renderRecruiter(); }
    catch (err) { toast(err.message, true); }
  }
  const dsh = e.target.closest("[data-rdash]");
  if (dsh) openDashboard(+dsh.dataset.rdash);
});

// ═══ 구직자 레주메 장기 보관 (동의 · 암호화 · 1년 · 언제든 삭제) ═══
async function refreshResumeBox() {
  const box = $("#rsStatus"); if (!box) return;
  const r = await api("/api/resumes/me").catch(() => null);
  state.savedResume = r && r.saved ? r : null;
  if (!r) { box.innerHTML = ""; return; }
  if (r.error) { box.innerHTML = `<p class="rs-err">${esc(r.error)}</p>`; return; }
  box.innerHTML = r.saved ? `
    <div class="rs-saved"><span class="rs-ic">🔒</span>
      <div><b>보관된 레주메 v${r.version}</b><small>${esc(r.updated_at)} 저장 · ${r.chars.toLocaleString()}자 · 기술 ${r.skills}개 · 이전 버전 ${r.history}개 · <b>${esc(r.expires_at)}</b>까지 보관 · ${r.owner_type === "linkedin" ? "링크드인 계정 기준(다른 기기에서도 불러오기)" : "이 브라우저 기준"}</small></div>
      <button type="button" class="btn-ghost sm" id="rsLoad">불러오기</button><button type="button" class="btn-ghost sm danger" id="rsDel">삭제</button></div>`
    : `<p class="rs-none">아직 보관한 레주메가 없어요. 위에 체크하고 "분석하기"를 누르면 첨삭 결과와 함께 보관돼요.${r.owner_type === "cookie" ? " 링크드인을 연결하면 다른 기기에서도 불러올 수 있어요." : ""}</p>`;
  if (r.saved) $("#rsConsent").checked = true;
  if (typeof renderRuSide === "function") renderRuSide();
}
function applySavedResume() {
  const d = state.savedResume?.data; if (!d) return;
  $("#profileText").value = d.resume_text || ""; $("#profileText").dispatchEvent(new Event("input"));
  if (d.linkedin_url) $("#linkedinUrl").value = d.linkedin_url;
  if (d.expected_salary) $("#expSalary").value = d.expected_salary;
  if (d.desired_level != null) $("#wantLevel").value = d.desired_level;
  if (d.desired_family != null) $("#wantFamily").value = d.desired_family;
  $("#school").value = d.school || ""; $("#hometown").value = d.hometown || "";
  $("#pastCompanies").value = (d.past_companies || []).join(", ");
  updateReady();
  toast(`보관한 레주메 v${state.savedResume.version}을(를) 불러왔어요.`);
}
async function saveResumeIfConsented(review) {
  if (!$("#rsConsent")?.checked) return;
  try {
    const n = netInput();
    const r = await api("/api/resumes/me", { consent: true, resume_text: $("#profileText").value, linkedin_url: $("#linkedinUrl").value.trim() || null,
      expected_salary: Number($("#expSalary").value) || null, desired_level: $("#wantLevel").value || null, desired_family: $("#wantFamily").value || null,
      school: n.school, hometown: n.hometown, past_companies: n.past_companies,
      review: review && { summary: review.summary, score: review.score, skills: review.skills, years: review.years, level: review.level, strengths: review.strengths, weaknesses: review.weaknesses }, resume_summary: state.summary || null });
    toast(`레주메를 암호화해서 보관했어요 (v${r.version}, ${r.expires_at}까지).`);
    refreshResumeBox();
  } catch (err) { toast(`레주메 보관 실패: ${err.message}`, true); }
}
document.addEventListener("click", async (e) => {
  if (e.target.id === "rsLoad") applySavedResume();
  if (e.target.id === "rsDel") {
    if (!confirm("보관한 레주메(이전 버전 포함)를 삭제할까요? 되돌릴 수 없어요.")) return;
    await api("/api/resumes/me", null, "DELETE"); $("#rsConsent").checked = false; toast("보관한 레주메를 삭제했어요."); refreshResumeBox();
  }
});
refreshResumeBox();

// ═══ 레주메 파일 올리기 · AI 분석 요약 · 업데이트 ═══
async function readResumeFile(file) {
  const fd = new FormData(); fd.append("file", file);
  const res = await fetch("/api/resume/extract", { method: "POST", body: fd });
  const d = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(d.detail || `오류 ${res.status}`);
  return d;
}
async function useFile(file, target) {
  if (!file) return;
  loading(true, `${file.name} 읽는 중...`);
  try {
    const d = await readResumeFile(file);
    const note = `${d.type}${d.pages ? ` ${d.pages}쪽` : ""} · ${d.chars.toLocaleString()}자${d.truncated ? " (2만 자까지만)" : ""}`;
    if (target === "profile") {
      $("#profileText").value = d.text; $("#profileText").dispatchEvent(new Event("input")); updateReady();
      state.ranked = null; state.ov = null;
      const filledUrl = !!(d.linkedin_url && !$("#linkedinUrl").value.trim());
      if (filledUrl) { $("#linkedinUrl").value = d.linkedin_url; checkLiUrl(); }
      toast(d.linkedin_pdf ? `링크드인 프로필 PDF를 읽었어요 · ${note}${filledUrl ? " · 프로필 주소도 채웠어요" : ""}. 내용을 확인해 주세요.`
                           : `${d.filename}에서 글자를 읽었어요 · ${note}. 내용을 확인해 주세요.`);
    } else {
      $("#ruText").value = d.text; $("#ruText").dispatchEvent(new Event("input"));
      $("#ruFile").innerHTML = `📄 <b>${esc(d.filename)}</b> · ${esc(note)}`;
      toast("파일을 읽었어요. 내용을 확인하고 'AI 분석·요약'을 눌러 주세요.");
    }
  } catch (err) { toast(err.message, true); } finally { loading(false); $("#fileInput").value = ""; }
}
$("#fileInput").addEventListener("change", (e) => useFile(e.target.files[0], state.pickTarget));
document.addEventListener("click", (e) => {
  const p = e.target.closest("[data-pick]");
  if (p) { state.pickTarget = p.dataset.pick; $("#fileInput").click(); }
});
$("#ruDrop").addEventListener("click", (e) => { e.preventDefault(); state.pickTarget = "resume"; $("#fileInput").click(); });
$("#ruDrop").addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); $("#ruDrop").click(); } });
// 끌어다 놓기: 레주메 업데이트 칸 · 프로필 입력칸
[["#ruDrop", "resume"], ["#profileText", "profile"], ["#ruText", "resume"]].forEach(([sel, target]) => {
  const el = $(sel);
  el.addEventListener("dragover", (e) => { e.preventDefault(); el.classList.add("over"); });
  el.addEventListener("dragleave", () => el.classList.remove("over"));
  el.addEventListener("drop", (e) => { e.preventDefault(); el.classList.remove("over"); if (e.dataTransfer.files[0]) useFile(e.dataTransfer.files[0], target); });
});
$("#ruText").addEventListener("input", (e) => ($("#ruCount").textContent = e.target.value.length.toLocaleString()));
$("#ruFromProfile").addEventListener("click", () => {
  const t = $("#profileText").value.trim();
  if (!t) return toast("프로필에 레주메가 아직 없어요.", true);
  $("#ruText").value = t; $("#ruText").dispatchEvent(new Event("input")); $("#ruFile").textContent = "";
});

// 비교 대상(이전 버전): 보관된 레주메 → 없으면 마지막으로 분석한 프로필 레주메
function ruPrev() {
  const saved = state.savedResume?.data?.resume_text;
  if (saved) return { text: saved, label: `보관된 v${state.savedResume.version}` };
  const cur = state.appliedText || "";
  return cur ? { text: cur, label: "지금 프로필" } : null;
}
function renderRuSide() {
  const prev = ruPrev();
  $("#ruCmp").innerHTML = prev ? `비교 대상 <b>${esc(prev.label)}</b>` : `<span class="muted">첫 레주메 · 비교할 이전 버전 없음</span>`;
  const r = state.savedResume;
  const items = r ? [{ v: r.version, at: r.updated_at, chars: r.chars, cur: true }, ...(r.history_list || []).map((h, i) => ({ v: h.version, at: h.saved_at, chars: h.chars, idx: i }))] : [];
  $("#ruVersions").innerHTML = items.length ? `
    <ol class="ver-list">${items.map((h) => `<li class="${h.cur ? "cur" : ""}"><b>v${h.v}</b><span>${esc(h.at || "")}<small>${(h.chars || 0).toLocaleString()}자</small></span>
      ${h.cur ? `<em>현재</em>` : `<button type="button" class="btn-ghost sm" data-ver="${h.idx}">불러오기</button>`}</li>`).join("")}</ol>
    <p class="muted">🔒 암호화 보관 · ${esc(r.expires_at)}까지 · 이전 버전은 최근 5개</p>`
    : `<div class="ver-empty"><b>보관된 버전이 없어요</b><span>업데이트할 때 "새 버전으로 보관"을 체크하면 v1, v2 … 로 쌓이고 이전 버전과 비교할 수 있어요.</span></div>`;
  $("#ruNav").textContent = r ? `보관 v${r.version} · 파일 올리기` : "파일 올리기 · AI 분석 요약";
}
document.addEventListener("click", (e) => {
  const b = e.target.closest("[data-ver]");
  if (!b) return;
  const h = state.savedResume?.history_list?.[+b.dataset.ver];
  if (!h) return;
  $("#ruText").value = h.resume_text || ""; $("#ruText").dispatchEvent(new Event("input"));
  $("#ruFile").innerHTML = `↺ 이전 버전 <b>v${h.version}</b> (${esc(h.saved_at)})`;
  toast(`v${h.version}을(를) 불러왔어요. 분석하거나 그대로 업데이트할 수 있어요.`);
});

$("#ruAnalyze").addEventListener("click", async () => {
  const text = $("#ruText").value.trim();
  if (text.length < 30) return toast("레주메 내용을 30자 이상 넣어 주세요.", true);
  const prev = ruPrev();
  loading(true, "AI가 레주메를 읽고 요약하고 있어요...");
  try {
    const s = await api("/api/resume/summary", { text, prev_text: prev?.text || null });
    state.ruDraft = { text, summary: s, prevLabel: prev?.label };
    renderRuResult();
    $("#ruResult").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) { toast(err.message, true); } finally { loading(false); }
});

function summaryHtml(s, opt = {}) {
  const kpi = (v, t) => `<div><b>${v}</b><span>${t}</span></div>`;
  const KIND = { 추가: "add", 보완: "mod", 삭제: "del" };
  const nSkills = (s.skill_groups || []).reduce((a, g) => a + (g.items || []).length, 0);
  return `
  <div class="rsum ${opt.compact ? "compact" : ""}">
    <div class="rsum-head">
      <div><p class="eyebrow">${opt.eyebrow || "AI 레주메 분석 요약"}</p><h3>${esc(s.headline)}</h3>
        ${s.ai === false ? `<p class="rs-err">${esc(s.ai_error || "AI 요약을 쓸 수 없어 간이 추출했어요.")}</p>` : ""}</div>
      <div class="rsum-kpi">${kpi(`${s.years ?? "-"}<small>년</small>`, "총 경력")}${kpi(esc(s.level || "-"), "직급 수준")}${kpi(nSkills, "보유 기술")}${kpi((s.careers || []).length, "경력 회사")}</div>
    </div>
    ${(s.summary || []).length ? `<ul class="rsum-lines">${s.summary.map((l) => `<li>${esc(l)}</li>`).join("")}</ul>` : ""}
    ${opt.changes && ((s.changes || []).length || s.diff) ? `
      <div class="rsum-chg"><h4>이전 버전(${esc(opt.prevLabel || "")})과 달라진 점 ${s.diff ? `<small>${s.diff.before.toLocaleString()}자 → ${s.diff.after.toLocaleString()}자 (${s.diff.after - s.diff.before >= 0 ? "+" : ""}${(s.diff.after - s.diff.before).toLocaleString()})</small>` : ""}</h4>
        ${(s.changes || []).length ? `<ul>${s.changes.map((c) => `<li class="${KIND[c.kind] || "mod"}"><i>${esc(c.kind)}</i>${esc(c.text)}</li>`).join("")}</ul>` : `<p class="muted">내용상 큰 변화는 없어요.</p>`}</div>` : ""}
    <div class="rsum-grid">
      <section><h4>경력 타임라인</h4>${(s.careers || []).length ? `<ol class="tl">${s.careers.map((c) => `
        <li><span class="tl-dot"></span><div><b>${esc(c.company)}</b>${c.role ? ` <span>${esc(c.role)}</span>` : ""}${c.period ? `<small>${esc(c.period)}</small>` : ""}
          ${(c.highlights || []).length ? `<ul>${c.highlights.map((h) => `<li>${esc(h)}</li>`).join("")}</ul>` : ""}</div></li>`).join("")}</ol>` : `<p class="muted">레주메에서 경력 기간을 찾지 못했어요.</p>`}</section>
      <section>
        <h4>주요 성과</h4>${(s.achievements || []).length ? `<ul class="ach">${s.achievements.map((a) => `<li>${esc(a)}</li>`).join("")}</ul>` : `<p class="muted">-</p>`}
        <h4>기술</h4><div class="sg">${(s.skill_groups || []).map((g) => `<div><small>${esc(g.group)}</small><p>${(g.items || []).map((x) => `<span class="skill">${esc(x)}</span>`).join("")}</p></div>`).join("")}</div>
        ${(s.certificates || []).length || (s.languages || []).length ? `<h4>자격증 · 외국어</h4><p class="rsum-meta">${[...(s.certificates || []), ...(s.languages || [])].map(esc).join(" · ")}</p>` : ""}
        ${(s.fit_roles || []).length ? `<h4>잘 맞는 외국계 직무</h4><div class="roles">${s.fit_roles.map((r) => `<span>${esc(r)}</span>`).join("")}</div>` : ""}
      </section>
    </div>
    ${opt.gaps && (s.gaps || []).length ? `<div class="rsum-gap"><h4>채용 담당자가 물어볼 만한 점 <small>나에게만 보여요 · 면접 전에 준비</small></h4><ul>${s.gaps.map((g) => `<li>${esc(g)}</li>`).join("")}</ul></div>` : ""}
  </div>`;
}

function renderRuResult() {
  const d = state.ruDraft;
  if (!d) {
    $("#ruResult").innerHTML = state.summary ? `<h2 class="ru-h">지금 적용된 레주메 요약</h2>${summaryHtml(state.summary, { gaps: true })}` : "";
    return;
  }
  const consent = $("#rsConsent").checked;
  $("#ruResult").innerHTML = `
    <h2 class="ru-h">② 분석 결과 확인 <small>${esc(d.summary.as_of || "")}</small></h2>
    ${summaryHtml(d.summary, { changes: true, gaps: true, prevLabel: d.prevLabel })}
    <div class="ru-share"><b>채용 담당자에게 보이는 것</b>
      <span>연결 요청할 때 <b>한 줄 소개 · 핵심 요약 · 경력 타임라인 · 주요 성과 · 기술 · 자격증/외국어 · 잘 맞는 직무</b>만 전달돼요. 레주메 원문 · 달라진 점 · 물어볼 만한 점 · 생년월일 · 사주는 전달되지 않아요.</span></div>
    <div class="cta-row sticky-cta ru-bar">
      <label class="ru-consent"><input type="checkbox" id="ruConsent" ${consent ? "checked" : ""}><span><b>암호화해서 새 버전으로 보관</b><small>1년 보관 · 이전 버전 5개 · 언제든 삭제</small></span></label>
      <div class="cta-right"><button class="btn-ghost" id="ruCancel">취소</button><button class="btn-primary" id="ruApply">이 레주메로 업데이트 <span>→</span></button></div>
    </div>`;
  $("#ruConsent").addEventListener("change", (e) => ($("#rsConsent").checked = e.target.checked));
  $("#ruCancel").addEventListener("click", () => { state.ruDraft = null; renderRuResult(); });
  $("#ruApply").addEventListener("click", applyRuDraft);
}

async function applyRuDraft() {
  const d = state.ruDraft; if (!d) return;
  $("#profileText").value = d.text; $("#profileText").dispatchEvent(new Event("input")); updateReady();
  state.summary = d.summary; state.appliedText = d.text;
  state.ranked = null; state.ov = null; state.ovHtml = null;
  if ($("#ruConsent").checked) { $("#rsConsent").checked = true; await saveResumeIfConsented(state.review); await refreshResumeBox(); }
  state.ruDraft = null; renderRuResult(); renderRuSide();
  if (state.review) {   // 이미 분석했으면 새 레주메로 첨삭·매칭을 다시 계산
    toast("새 레주메로 업데이트했어요. 첨삭·매칭을 다시 계산할게요.");
    state.skipSummary = true;   // 요약은 방금 만들었으니 다시 만들지 않음
    $("#analyzeBtn").click();
  } else {
    toast("프로필에 새 레주메를 넣었어요. 'AI 분석 시작'을 눌러 주세요.");
    go("profile");
  }
}


// ═══ 링크드인 공고 가져오기: 붙여넣은 글 → AI가 등록 칸 채우기 ═══
// 링크드인은 공고를 가져가는 공개 API가 없고 자동 수집은 약관 위반 → 구인자가 복사한 글만 사용
const LI_FIELD = { 회사명: "company", "본사 국가": "hq", 포지션: "title", 직급: "level", 경력: "years_min", "연봉(원화)": "salary_min",
  "영어 수준": "english", 근무지: "location", 마감일: "deadline", "담당자 이름": "recruiter_name", "경력 최대": "years_max", "연봉 최대": "salary_max" };
document.addEventListener("click", async (e) => {
  if (e.target.closest("#liParse")) {
    const text = $("#liText").value.trim(), url = $("#liUrl").value.trim();
    if (text.length < 80) return toast(`${siteName(state.rSite)} 공고 글을 통째로 복사해 붙여넣어 주세요 (80자 이상).`, true);
    loading(true, `AI가 ${siteName(state.rSite)} 공고를 읽고 등록 칸을 채우고 있어요...`);
    try {
      const r = await api("/api/recruiter/import-posting", { site: state.rSite || "linkedin", url, text });
      applyLiDraft(r);
    } catch (err) { toast(err.message, true); } finally { loading(false); }
  }
  const g = e.target.closest("[data-lifocus]");
  if (g) { const el = $("#postForm").elements[g.dataset.lifocus]; const tgt = el && el.type === "hidden" ? $(`[data-seg="${g.dataset.lifocus}"]`) : el;
    if (tgt) { tgt.scrollIntoView({ behavior: "smooth", block: "center" }); if (tgt.focus) setTimeout(() => tgt.focus(), 300); } }
});
function applyLiDraft(r) {
  const fm = $("#postForm"), d = r.draft;
  const set = (k, v) => { if (fm.elements[k] && v != null && v !== "") fm.elements[k].value = v; };
  ["company", "hq", "title", "location", "deadline", "recruiter_name", "sector"].forEach((k) => set(k, d[k]));
  set("years_min", d.years_min); set("years_max", d.years_max);
  set("salary_min", d.salary_min); set("salary_max", d.salary_max);
  ["level", "english"].forEach((k) => { if (d[k]) { fm.elements[k].value = d[k]; $$(`[data-seg="${k}"] button`).forEach((b) => b.classList.toggle("on", b.dataset.v === d[k])); } });
  fm.elements.source_url.value = r.source_url || "";
  fm.elements.source_site.value = r.site || "direct";
  if (d.job_family) { fm.elements.family.value = d.job_family; $$(`[data-seg="family"] button`).forEach((b) => b.classList.toggle("on", b.dataset.v === d.job_family)); }
  if (d.skills.length) { state.rSkills = d.skills.slice(0, 8); renderSkillChips(); }
  $$(".pf.li-need").forEach((x) => x.classList.remove("li-need"));
  r.missing.forEach((m) => { const k = LI_FIELD[m]; const el = k && fm.elements[k]; const lab = el && (el.closest(".pf") || $(`[data-seg="${k}"]`)?.closest(".pf")); if (lab) lab.classList.add("li-need"); });
  const filled = Object.values(d).filter((v) => v != null && v !== "" && !(Array.isArray(v) && !v.length) && v !== "기타").length - (d.summary?.length ? 1 : 0) - (d.salary_text ? 1 : 0) - (d.employment ? 1 : 0);
  $("#liResult").innerHTML = `
    <div class="li-res ${r.duplicate ? "dup" : ""}">
      ${r.duplicate ? `<p class="li-dup">⚠ 이 링크드인 공고는 이미 등록돼 있어요. 등록하면 중복으로 거절돼요.</p>` : ""}
      ${r.ai ? "" : `<p class="rs-err">AI를 지금 쓸 수 없어(${esc(r.ai_error || "")}) 공고 글에서 <b>적혀 있는 값만</b> 코드로 읽었어요. 칸을 한 번씩 확인해 주세요.</p>`}
      <div class="li-res-head"><b>✓ ${filled}개 칸을 채웠어요 · 직종 <em class="fam">${esc(d.job_family || "-")}</em></b>${srcBadge({ source_site: r.site, source_site_name: r.site_name, source_url: r.source_url })}</div>
      ${(d.summary || []).length ? `<ul class="li-sum">${d.summary.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}
      ${d.salary_text && !d.salary_min ? `<p class="muted">공고의 급여 표기: <b>${esc(d.salary_text)}</b> → 원화(만원)로 직접 넣어 주세요.</p>` : ""}
      ${r.missing.length ? `<div class="li-miss"><span>직접 확인할 칸</span>${r.missing.map((m) => `<button type="button" data-lifocus="${LI_FIELD[m] || ""}">${esc(m)}</button>`).join("")}</div>` : ""}
      <p class="muted">${esc(r.company_info_note)}</p>
    </div>`;
  updatePreview();
  toast(`${r.site_name} 공고로 ${filled}개 칸을 채웠어요. 빨간 칸을 확인해 주세요.`);
}


// ═══ 직종 · 출처 공통 표시 ═══
const FAM_ICON = { 개발: "</>", "데이터·AI": "◆", "인프라·클라우드": "☁", 세일즈: "₩", 프리세일즈: "▶", 딜리버리: "▣", "고객 성공": "♥" };
const FAMILIES = ["개발", "데이터·AI", "인프라·클라우드", "세일즈", "프리세일즈", "딜리버리", "고객 성공"];
const famBadge = (j) => (j.family ? `<span class="fam f-${FAMILIES.indexOf(j.family)}" title="직종">${FAM_ICON[j.family] || ""} ${esc(j.family)}</span>` : "");
const SITE_NAMES = { linkedin: "링크드인", wanted: "원티드", remember: "리멤버", jumpit: "점핏", saramin: "사람인", jobkorea: "잡코리아", rocketpunch: "로켓펀치", careers: "회사 채용 페이지", direct: "직접 작성", sample: "예시 공고(가상)" };
const siteName = (k) => SITE_NAMES[k] || "직접 작성";
function srcBadge(j) {
  const key = j.source_site || "direct", name = j.source_site_name || siteName(key);
  const inner = `<i class="src-dot s-${esc(key)}"></i>출처 · ${esc(name)}`;
  return j.source_url
    ? `<a class="src-badge" href="${esc(j.source_url)}" target="_blank" rel="noopener" title="${esc(name)} 원문 공고 열기">${inner} ↗</a>`
    : `<span class="src-badge" title="공고 출처">${inner}</span>`;
}
// 직종 칩 (지금 목록의 직종별 개수, 0개 직종은 흐리게)
function familyChips(list, cur, key) {
  const cnt = (f) => list.filter((x) => (x.family || "개발") === f).length;
  return `<div class="fam-chips" role="group" aria-label="직종">
    <button class="${!cur ? "on" : ""}" data-${key}="">전체 직종 <small>${list.length}</small></button>
    ${FAMILIES.map((f) => `<button class="${cur === f ? "on" : ""} ${cnt(f) ? "" : "zero"}" data-${key}="${esc(f)}" ${cnt(f) ? "" : "disabled"}>${FAM_ICON[f]} ${esc(f)} <small>${cnt(f)}</small></button>`).join("")}
    ${$("#wantFamily").value && cur !== $("#wantFamily").value ? `<span class="fam-hint">내 희망 직종: <b>${esc($("#wantFamily").value)}</b></span>` : ""}
  </div>`;
}
document.addEventListener("click", (e) => {
  const m = e.target.closest("[data-mfam]"), j = e.target.closest("[data-jfam]"), o = e.target.closest("[data-ofam]"), st = e.target.closest("[data-site]");
  if (m) { state.mf.family = m.dataset.mfam; state.shown = 8; renderMatch(); }
  if (j) { jobFam = j.dataset.jfam; loadJobs(); }
  if (o) { state.ovFamily = o.dataset.ofam; renderOverview(); }
  if (st) {
    state.rSite = st.dataset.site;
    $$("#siteRow button").forEach((b) => b.classList.toggle("on", b === st));
    const meta = (state.rMeta?.sites || []).find((x) => x.key === state.rSite) || {};
    $("#siteName1").textContent = meta.key === "direct" ? "워드·메일 등" : meta.name; $("#siteName2").textContent = meta.name;
    $("#liUrlWrap").hidden = meta.needs_url === false; $("#liUrl").placeholder = meta.example || ""; $("#liUrl").value = "";
  }
});
state.rSite = "linkedin";
// 희망 직종 선택지 (지금 공고 수와 설명)
fetch("/api/families").then((r) => r.json()).then((fs) => {
  $("#wantFamily").innerHTML = `<option value="">이력서 기준 (AI 판단)</option>` + fs.map((f) => `<option value="${esc(f.name)}" title="${esc(f.desc)}">${esc(f.name)} · 공고 ${f.count}</option>`).join("");
  if (state.savedResume?.data?.desired_family) $("#wantFamily").value = state.savedResume.data.desired_family;
}).catch(() => {});
$("#wantFamily").addEventListener("change", () => { state.mf.family = null; jobFam = null; state.ovFamily = null; });

// ═══ 인터뷰 전략: 레주메 최근 업무 강조 키워드 (키워드 + 2줄 설명) ═══
function recentFocusHtml(f, job) {
  if (!f) return "";
  const TAGC = { "필수 기술": "must", "우대 기술": "nice", "관련 경험": "rel", "최근 업무": "recent" };
  return `<section class="dcard wide rf">
    <h5>최근 업무 강조 키워드 <small>레주메에서 가장 최근 경력${f.recent ? ` — <b>${esc(f.recent.company)}</b> · ${esc(f.recent.period)}` : ""}${job ? ` · ${esc(job.title || "")} 기준` : ""}</small></h5>
    ${f.items.length ? `
      <div class="rf-keys">${f.items.map((x, i) => `<span class="rf-key ${TAGC[x.tag] || ""}"><b>${i + 1}</b>${esc(x.keyword)}</span>`).join("")}</div>
      <ol class="rf-list">${f.items.map((x) => `
        <li><div class="rf-k"><span class="rf-tag ${TAGC[x.tag] || ""}">${esc(x.tag)}</span><b>${esc(x.keyword)}</b>${x.has_number ? `<em>숫자 성과</em>` : ""}</div>
          <p class="rf-ev"><span>레주메 근거</span>${esc(x.evidence)}</p>
          <p class="rf-pitch"><span>이렇게 강조</span>${esc(x.pitch)}</p></li>`).join("")}</ol>
      <p class="muted">${esc(f.note)}</p>` : `<p class="muted">${esc(f.note)}</p>`}
  </section>`;
}
async function renderReviewFocus() {
  const host = $("#rvFocus"); if (!host) return;
  try { host.innerHTML = recentFocusHtml(await api("/api/recent-focus", { profile: myProfile() }), null); } catch { host.innerHTML = ""; }
}


// ═══ 링크드인 공고 분석 (구직자 특별 섹션) ═══
// 붙여넣은 공고 → 직종 · 직급(일반·주니어·시니어·리더) · 예상 연봉 · 인터뷰 핵심 키워드 (+ 내 레주메 비교)
state.lsHist = [];
const LS_SAMPLE = `Enterprise Account Executive - Korea
Nimbus Cloud · Seoul, South Korea · 3 days ago · Over 100 applicants
On-site  Full-time  Mid-Senior level

About the job
Nimbus Cloud (US-based) is hiring an Enterprise Account Executive to own new logo acquisition across financial services in Korea.

Responsibilities
- Achieve and exceed quarterly quota through prospecting and closing complex deals
- Build and manage a healthy pipeline in Salesforce with accurate forecasting
- Negotiate multi-year enterprise contracts with C-level stakeholders
- Work with Solutions Engineers on demos and PoCs

Requirements
- 8+ years of B2B enterprise software sales experience
- Proven track record of quota attainment
- Fluent English and Korean`;
async function renderLsAcct() {
  const box = $("#lsAcct"); if (!box) return;
  const me = await api("/api/linkedin/me").catch(() => null);
  box.innerHTML = me && me.connected
    ? `<span class="ls-dot ok"></span><div><b>${esc(me.user?.name || "내 링크드인")}</b><small>링크드인 계정 연결됨 · ${esc(me.user?.email || "")}</small></div>`
    : $("#linkedinUrl").value.trim().match(LI_PROFILE)
    ? `<span class="ls-dot ok"></span><div><b>내 링크드인 프로필</b><small><a href="${esc($("#linkedinUrl").value.trim())}" target="_blank" rel="noopener">${esc($("#linkedinUrl").value.trim().replace("https://www.", ""))} ↗</a> · 로그인 연결은 앱 키 설정 후</small></div>`
    : `<span class="ls-dot"></span><div><b>내 링크드인 연결 안 됨</b><small>${me && me.configured === false ? "앱 키 설정 후 1단계에서 직접 로그인" : "1단계 프로필에서 \"내 링크드인 연결\""}</small></div>`;
  renderLsHist();
}
function renderLsHist() {
  $("#lsHist").innerHTML = state.lsHist.length ? `<span>이번에 분석한 공고</span>${state.lsHist.map((h, i) =>
    `<button type="button" data-lsh="${i}" class="${i === state.lsCur ? "on" : ""}">${famBadge({ family: h.family.family })} ${esc(h.posting.company || "회사")} · ${esc(h.posting.title || "")}</button>`).join("")}` : "";
}
$("#lsSample").addEventListener("click", () => { $("#lsText").value = LS_SAMPLE; $("#lsUrl").value = "https://www.linkedin.com/jobs/view/4012345678"; toast("예시 공고(가상 회사)를 넣었어요."); });
$("#lsGo").addEventListener("click", async () => {
  const text = $("#lsText").value.trim();
  if (text.length < 80) return toast("링크드인 공고 글을 통째로 복사해 붙여넣어 주세요 (80자 이상).", true);
  loading(true, "링크드인 공고를 분석하고 있어요 (직종·직급·연봉·인터뷰)...");
  try {
    const prof = state.review ? myProfile() : { resume_text: $("#profileText").value, expected_salary: Number($("#expSalary").value) || null };
    const r = await api("/api/linkedin/analyze", { url: $("#lsUrl").value.trim(), text, profile: prof });
    state.lsHist.unshift(r); state.lsHist = state.lsHist.slice(0, 6); state.lsCur = 0;
    renderLsResult(r); renderLsHist();
    $("#lsResult").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) { toast(err.message, true); } finally { loading(false); }
});
document.addEventListener("click", (e) => {
  const h = e.target.closest("[data-lsh]");
  if (h) { state.lsCur = +h.dataset.lsh; renderLsResult(state.lsHist[state.lsCur]); renderLsHist(); }
});
const won = (v) => (v == null ? "-" : `${Number(v).toLocaleString()}`);
function renderLsResult(r) {
  const p = r.posting, f = r.family, t = r.tier, sal = r.salary, me = r.me;
  const tiers = ["일반", "주니어", "시니어", "리더"];
  const want = Number($("#expSalary").value) || null;
  const scaleMax = Math.max(sal.max * 1.25, (want || 0) * 1.1, 1000);
  const pct = (v) => Math.max(0, Math.min(100, (100 * v) / scaleMax));
  $("#lsResult").innerHTML = `
  <article class="ls-res">
    <header class="ls-head">
      <span class="ls-logo">${esc((p.company || "?").split(/\s+/).map((w) => w[0]).join("").slice(0, 2))}</span>
      <div><small>${esc(p.company || "회사명 없음")}${p.location ? ` · ${esc(p.location)}` : ""}${p.employment ? ` · ${esc(p.employment)}` : ""}</small>
        <h2>${esc(p.title || "포지션")}</h2>
        <div class="ls-meta">${p.years_min != null ? `<span>경력 ${p.years_min}${p.years_max ? `~${p.years_max}` : "+"}년</span>` : ""}${p.english ? `<span>영어 ${esc(p.english)}</span>` : ""}${p.deadline ? `<span>마감 ${esc(p.deadline)}</span>` : ""}
          ${srcBadge({ source_site: "linkedin", source_site_name: "링크드인", source_url: r.source_url })}</div></div>
      ${r.ai ? `<span class="src-tag ai">AI + 코드 분석</span>` : `<span class="src-tag">코드 분석 (AI 미사용)</span>`}
    </header>
    ${(p.summary || []).length ? `<ul class="ls-sum">${p.summary.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}

    <div class="ls-tiles">
      <section class="ls-tile">
        <p class="ls-k">① 직종</p>
        <div class="ls-big">${famBadge({ family: f.family })}</div>
        <p class="ls-why">찾은 키워드</p>
        <div class="ls-chips">${f.evidence.map((w) => `<span>${esc(w)}</span>`).join("") || `<span class="muted">직종 키워드가 거의 없어 기본값</span>`}</div>
        <div class="ls-bars">${f.scores.slice(0, 3).map((x) => `<div><span>${esc(x.family)}</span><i><b style="width:${x.pct}%"></b></i><em>${x.pct}%</em></div>`).join("")}</div>
      </section>
      <section class="ls-tile">
        <p class="ls-k">② 직급</p>
        <div class="ls-ladder">${tiers.map((x) => `<div class="${x === t.tier ? "on" : ""}"><b>${x}</b></div>`).join("")}</div>
        <p class="ls-big-t">${esc(t.tier)} <small>${esc(t.desc)}</small></p>
        <p class="ls-why">근거 · ${esc(t.why)}</p>
        <p class="muted">서비스 매칭 직급으로는 <b>${esc(t.service_level)}</b></p>
      </section>
      <section class="ls-tile">
        <p class="ls-k">③ 예상 연봉 <small>만원 · 연봉</small></p>
        <p class="ls-money">${won(sal.min)} <span>~</span> ${won(sal.max)}</p>
        <div class="ls-range"><i style="left:${pct(sal.min)}%;width:${pct(sal.max) - pct(sal.min)}%"></i>${want ? `<em style="left:${pct(want)}%" title="내 기대 연봉"></em>` : ""}</div>
        ${want ? `<p class="ls-want">내 기대 연봉 <b>${won(want)}</b> → ${esc(me?.salary_fit || (want < sal.min ? "범위보다 낮음 (협상 여지)" : want > sal.max ? "범위보다 높음" : "범위 안"))}</p>` : ""}
        <p class="ls-why">${sal.kind === "posted" ? "✓ " : "≈ "}${esc(sal.basis)}</p>
        ${sal.note ? `<p class="muted">${esc(sal.note)}</p>` : ""}${sal.extra ? `<p class="ls-tip">${esc(sal.extra)}</p>` : ""}
        ${sal.posted_text && sal.kind !== "posted" ? `<p class="muted">공고 급여 표기: ${esc(sal.posted_text)}</p>` : ""}
      </section>
    </div>

    <section class="ls-iv">
      <header><p class="ls-k">④ 인터뷰에서 가장 중요한 것</p><h3>${esc(f.family)} 면접 핵심 키워드</h3>
        <p class="muted">공고에 나온 역량을 먼저 · 각 키워드는 <b>왜 중요한지</b>와 <b>어떻게 준비할지</b> 2줄로</p></header>
      <div class="ls-ivkeys">${r.interview.map((x, i) => `<span class="${x.in_posting ? "hit" : ""}"><b>${i + 1}</b>${esc(x.keyword)}</span>`).join("")}</div>
      <ol class="ls-ivlist">${r.interview.map((x, i) => `
        <li><div class="ls-ivk"><b>${i + 1}</b><strong>${esc(x.keyword)}</strong><span class="ls-tag ${x.kind === "필수 기술" ? "must" : ""}">${esc(x.kind)}</span>
          ${x.in_posting ? `<em>공고에 나옴${x.evidence ? ` · “${esc(x.evidence)}”` : ""}</em>` : ""}</div>
          <p><span>왜 중요</span>${esc(x.why)}</p><p class="prep"><span>이렇게 준비</span>${esc(x.prep)}</p></li>`).join("")}</ol>
    </section>

    ${me ? `<section class="ls-me">
      <header><p class="ls-k">⑤ 내 레주메와 비교</p></header>
      <div class="ls-me-grid">
        <div class="ls-rate"><b>${me.rate}<small>%</small></b><span>키워드 매칭률</span><small>필수 기술 ${me.must_ok}/${me.must_total}</small></div>
        <div class="ls-kwset">
          <p><span class="st ok">있음</span>${me.have.map((k) => `<em>${esc(k)}</em>`).join("") || "-"}</p>
          <p><span class="st part">관련 경험</span>${me.partial.map((k) => `<em>${esc(k)}</em>`).join("") || "-"}</p>
          <p><span class="st no">부족</span>${me.missing.map((k) => `<em>${esc(k)}</em>`).join("") || "없음"}</p>
        </div>
      </div>
      ${me.focus.length ? recentFocusHtml({ recent: me.recent, items: me.focus, note: "이 공고 면접에서 내 최근 업무를 이렇게 연결하세요." }, { title: p.title }) : ""}
    </section>` : `<p class="muted ls-nome">1단계에 레주메를 넣으면 이 공고와 내 레주메의 키워드 매칭률·강조할 최근 업무도 함께 보여 드려요.</p>`}
  </article>`;
}


// ═══ 내 링크드인 프로필 주소: 모양 확인 · 열기 링크 (주소만 저장·전달, 내용은 가져오지 않음) ═══
const LI_PROFILE = /^(?:https?:\/\/)?(?:[a-z]{2,3}\.|www\.)?linkedin\.com\/in\/([A-Za-z0-9\-_%]{3,100})\/?(?:[?#].*)?$/i;
function checkLiUrl() {
  const v = $("#linkedinUrl").value.trim(), box = $("#liUrlState"), m = v.match(LI_PROFILE);
  if (!v) { box.innerHTML = ""; $("#liMyProfile").href = "https://www.linkedin.com/in/"; return; }
  if (!m) { box.innerHTML = `<span class="bad">링크드인 프로필 주소 모양이 아니에요 — 예) https://www.linkedin.com/in/내아이디</span>`; return; }
  const url = `https://www.linkedin.com/in/${m[1]}/`;
  if (v !== url) $("#linkedinUrl").value = url;
  $("#liMyProfile").href = url;
  box.innerHTML = `<span class="ok">✓ 링크드인 프로필 <b>${esc(m[1])}</b></span><a href="${esc(url)}" target="_blank" rel="noopener">프로필 열기 ↗</a><small>연결 요청할 때만 채용 담당자에게 전달돼요</small>`;
}
$("#linkedinUrl").addEventListener("change", checkLiUrl);
$("#linkedinUrl").addEventListener("blur", checkLiUrl);


// ═══ 내 링크드인 공고 가져오기 (데이터 내보내기 ZIP/CSV · 채용 알림 메일) → 나와 맞는 회사 순위 ═══
state.lsFile = null; state.lsImp = null; state.lsImpFam = "";
function lsTab(t) {
  $$("[data-lstab]").forEach((b) => b.classList.toggle("on", b.dataset.lstab === t));
  $("#lsImportPane").hidden = t !== "import"; $("#lsOnePane").hidden = t !== "one"; $("#lsFeedPane").hidden = t !== "feed"; $("#lsCoPane").hidden = t !== "co";
  if (t === "feed") loadFeed();
  if (t === "co") loadCompanies();
}
document.addEventListener("click", (e) => {
  const b = e.target.closest("[data-lstab]"); if (b) lsTab(b.dataset.lstab);
  const d = e.target.closest("[data-lsdeep]");
  if (d) {   // 자세히 분석: 원문 주소를 넣고, 공고 글을 붙여넣게 안내
    const j = state.lsImp.jobs.find((x) => x.job_id === d.dataset.lsdeep);
    lsTab("one"); $("#lsUrl").value = j.url || ""; $("#lsText").value = "";
    $("#lsText").placeholder = `"${j.title}" 공고를 링크드인에서 열고(위 주소) 공고 글 전체를 복사해 여기에 붙여넣으세요`;
    window.open(j.url, "_blank", "noopener"); $("#lsText").focus();
    toast("링크드인에서 공고를 열었어요. 공고 글을 복사해 붙여넣으면 자세히 분석해요.");
  }
  const f = e.target.closest("[data-ifam]"); if (f) { state.lsImpFam = f.dataset.ifam; renderLsImp(); }
});
$("#lsDrop").addEventListener("click", (e) => { e.preventDefault(); $("#lsFile").click(); });
$("#lsFile").addEventListener("change", (e) => { state.lsFile = e.target.files[0] || null; $("#lsDropFile").innerHTML = state.lsFile ? `📦 <b>${esc(state.lsFile.name)}</b> · ${(state.lsFile.size / 1024).toFixed(0)}KB` : ""; });
["dragover", "dragleave", "drop"].forEach((ev) => $("#lsDrop").addEventListener(ev, (e) => {
  e.preventDefault(); $("#lsDrop").classList.toggle("over", ev === "dragover");
  if (ev === "drop" && e.dataTransfer.files[0]) { state.lsFile = e.dataTransfer.files[0]; $("#lsDropFile").innerHTML = `📦 <b>${esc(state.lsFile.name)}</b>`; }
}));
$("#lsImpSample").addEventListener("click", () => {
  state.lsFile = null; $("#lsDropFile").textContent = "";
  $("#lsMail").value = `Your job alert for "backend engineer" in Seoul — 4 new jobs (예시·가상 회사)

Senior Backend Engineer (Python)
Quillstone · Seoul, South Korea
View job: https://www.linkedin.com/comm/jobs/view/4011111111/

LLM Application Engineer
Elyra AI Korea · Seoul, South Korea
View job: https://www.linkedin.com/comm/jobs/view/4044444444/

Solutions Engineer (Presales)
Kestrelbyte Cloud · Seoul, South Korea
View job: https://www.linkedin.com/comm/jobs/view/4066666666/

Enterprise Account Executive
Nimbus Cloud · Seoul, South Korea
View job: https://www.linkedin.com/comm/jobs/view/4022222222/

Technical Delivery Manager
Orbitworks · Pangyo, South Korea
View job: https://www.linkedin.com/comm/jobs/view/4033333333/`;
  toast("예시 채용 알림 메일(가상 회사)을 넣었어요. '가져와서 분석하기'를 눌러 보세요.");
});
$("#lsImpGo").addEventListener("click", async () => {
  if (!state.lsFile && !$("#lsMail").value.trim()) return toast("파일을 올리거나 채용 알림 메일 내용을 붙여넣어 주세요.", true);
  const r0 = state.review || {};
  const prof = { desired_family: $("#wantFamily").value || r0.job_family || "", skills: r0.skills || [], years: r0.years ?? null,
    level: r0.level || "", desired_level: $("#wantLevel").value || r0.level || "" };
  const fd = new FormData();
  if (state.lsFile) fd.append("file", state.lsFile); else fd.append("text", $("#lsMail").value);
  fd.append("profile", JSON.stringify(prof));
  loading(true, "링크드인 공고를 가져와 나와 맞는 회사를 분석하고 있어요...");
  try {
    const res = await fetch("/api/linkedin/import", { method: "POST", body: fd });
    const d = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(d.detail || `오류 ${res.status}`);
    if (d.single) {   // 공고 1개짜리 PDF → ② 자세히 분석으로 바로
      lsTab("one"); $("#lsText").value = d.text; $("#lsUrl").value = d.url || "";
      toast("공고 1개짜리 PDF라 '자세히 분석'으로 바로 분석할게요.");
      setTimeout(() => $("#lsGo").click(), 0); return;   // 가져오기의 로딩 표시가 끝난 뒤 분석 시작
    }
    state.lsImp = d; state.lsImpFam = ""; renderLsImp();
    $("#lsImpResult").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) { toast(err.message, true); } finally { loading(false); }
});
const KIND = { saved: ["저장", "s"], applied: ["지원함", "a"], alert: ["알림", "n"] };
function renderLsImp() {
  const d = state.lsImp; if (!d) return;
  const sm = d.summary, list = d.jobs.filter((j) => !state.lsImpFam || j.family === state.lsImpFam);
  const top = d.jobs[0];
  $("#lsImpResult").innerHTML = `
  <section class="li-rank">
    <header class="li-rank-head"><div><p class="ls-k">나와 맞는 회사 분석</p><h2>내 링크드인 공고 ${d.count}개 · <span>${esc(d.source)}</span></h2>
      <p class="muted">${sm.my_family ? `내 직종 <b>${esc(sm.my_family)}</b> · ` : "1단계에서 희망 직종을 고르면 더 정확해요 · "}내 직급 <b>${esc(sm.my_tier)}</b> 기준</p></div></header>
    <div class="li-kpis">
      <div class="hero"><small>가장 잘 맞는 회사</small><b>${esc(top.company || "-")}</b><span>${esc(top.title)}</span><em>${top.fit.score}<small>/100</small></em></div>
      <div><small>가져온 공고</small><b>${d.count}</b><span>저장 ${sm.kinds.saved} · 지원 ${sm.kinds.applied} · 알림 ${sm.kinds.alert}</span></div>
      <div><small>내 직종과 같은 공고</small><b>${sm.same_family}</b><span>${esc(sm.my_family || "직종 미정")}</span></div>
      <div><small>적합도 70점 이상</small><b>${sm.good}</b><span>먼저 지원해 볼 곳</span></div>
    </div>
    ${familyChips(d.jobs, state.lsImpFam, "ifam")}
    <ol class="li-list">${list.map((j) => `
      <li class="${j.rank <= 3 ? "top" : ""}">
        <span class="li-rk">${j.rank}</span>
        <div class="li-main">
          <div class="li-co">${famBadge({ family: j.family })} <b>${esc(j.company || "회사 정보 없음")}</b>${j.location ? `<small>${esc(j.location)}</small>` : ""}
            <span class="li-kind k-${KIND[j.kind][1]}">${KIND[j.kind][0]}</span>${j.date ? `<small>${esc(j.date)}</small>` : ""}</div>
          <div class="li-title">${esc(j.title)}</div>
          <div class="li-facts"><span>직급 <b>${esc(j.tier)}</b></span><span>예상 연봉 <b>${won(j.salary.min)}~${won(j.salary.max)}</b>만 <small>${j.salary.kind === "peer" ? `같은 직종·직급 ${j.salary.n}개 기준` : "기준표(가정치)"}</small></span></div>
          <div class="li-iv"><span>인터뷰 핵심</span>${j.interview.map((x) => `<em title="${esc(x.prep)}">${esc(x.keyword)}</em>`).join("")}</div>
          <div class="li-why">${j.fit.reasons.map((x) => `<span>${esc(x)}</span>`).join("")}</div>
        </div>
        <div class="li-side">
          <div class="li-score"><b>${j.fit.score}</b><small>/100 적합도</small></div>
          <div class="li-bar" title="직종 ${j.fit.parts.family}/40 · 직급 ${j.fit.parts.tier}/30 · 기술 ${j.fit.parts.keyword}/30">
            <i class="f" style="width:${j.fit.parts.family}%"></i><i class="t" style="width:${j.fit.parts.tier}%"></i><i class="k" style="width:${j.fit.parts.keyword}%"></i></div>
          <div class="li-btns">${j.url ? `<a class="src-badge" href="${esc(j.url)}" target="_blank" rel="noopener"><i class="src-dot s-linkedin"></i>링크드인 원문 ↗</a>` : ""}
            ${j.job_id ? `<button class="btn-ghost sm" data-lsdeep="${esc(j.job_id)}">자세히 분석</button>` : ""}
            ${j.service_job_id ? `<button class="ca-open" data-job="${j.service_job_id}">회사 인연도 ↗</button>` : ""}</div>
        </div>
      </li>`).join("")}</ol>
    <p class="li-legend"><i class="f"></i>직종 40 <i class="t"></i>직급 30 <i class="k"></i>직무명 속 내 기술 30 — ${esc(d.formula)}</p>
    <button class="btn-primary co-go" data-lstab="co">★ 이 공고들을 회사별로 분석하기 <span>→</span></button>
    <p class="muted">직무명·회사만으로 계산한 1차 순위예요. 마음에 드는 공고는 <b>자세히 분석</b>으로 공고 글까지 보면 직급·연봉·인터뷰 키워드가 더 정확해져요.</p>
  </section>`;
}


// ═══ ⓪ 오늘의 새 공고 — 하루 한 번 배치(에이전트 스캔 · 회사 공개 채용 API)로 쌓인 공고 ═══
state.feedFam = ""; state.feedNewOnly = false;
function feedProfile() {
  const r0 = state.review || {};
  return { desired_family: $("#wantFamily").value || r0.job_family || "", skills: r0.skills || [], years: r0.years ?? null,
    level: r0.level || "", desired_level: $("#wantLevel").value || r0.level || "" };
}
async function loadFeed() {
  const pane = $("#lsFeedPane");
  pane.innerHTML = `<div class="dash-loading"><span class="spin"></span>배치로 쌓인 공고를 불러오고 있어요...</div>`;
  try {
    const [st, f] = await Promise.all([api("/api/batch/status"), api("/api/feed", { profile: feedProfile(), days: 14 })]);
    state.feed = f; state.feedSt = st; renderFeed();
  } catch (err) { pane.innerHTML = `<div class="empty">${esc(err.message)}</div>`; }
}
function feedSetupHtml(st) {
  return `<details class="fd-setup" ${st.total ? "" : "open"}><summary>배치 연동 방법 — 매일 정해진 시각에 공고가 자동으로 쌓이게</summary>
    <div class="fd-setup-grid">
      <section><h5><span>1</span>링크드인: 내 에이전트가 읽은 결과 보내기</h5>
        <p>사용자가 직접 돌리는 브라우저 에이전트(예: Claude <b>linkedin-job-scan</b> 스킬 · 본인 로그인 · 읽기만)가 매일 정해진 시각에 검색 결과를 읽고 이 서비스로 보내요. <b>이 서비스 서버는 링크드인에 접속하지 않아요.</b></p>
        <pre>POST /api/batch/linkedin-scan
X-Batch-Token: (상위 폴더 .env 의 BATCH_TOKEN)
{"run_at": "2026-11-12 09:00",
 "items": [{"title": "Partner Manager, Korea",
   "company": "회사", "work_type": "Hybrid",
   "posted": "2 days ago", "tags": ["Easy Apply"],
   "alumni": 3, "url": "https://www.linkedin.com/jobs/view/…"}]}</pre>
        <p class="fd-st ${st.token_set ? "ok" : "no"}">${st.token_set ? "✓ BATCH_TOKEN 설정됨 — 받을 준비 완료" : "BATCH_TOKEN 미설정 — 상위 폴더 .env 에 넣고 서버 재시작"}</p></section>
      <section><h5><span>2</span>회사 공개 채용 페이지 (Greenhouse · Lever · Ashby)</h5>
        <p>외국계 회사가 채용 페이지용으로 공개한 API를 서버가 매일 직접 가져와요(로그인·키 필요 없음). 한국 근무 공고만 남겨요.</p>
        <pre>data/ats_sources.json
[{"ats": "greenhouse", "slug": "회사아이디", "company": "회사 이름"},
 {"ats": "lever", "slug": "…", "company": "…"}]</pre>
        <p class="fd-st ${st.ats_config ? "ok" : "no"}">${st.ats_config ? "✓ 회사 목록 있음" : "회사 목록 없음 — 지원할 회사를 정해 주세요"}</p></section>
      <section><h5><span>3</span>매일 실행 시각</h5>
        <p>Windows 작업 스케줄러에 매일 등록하거나, 상위 폴더 .env 에 <code>BATCH_TIME=07:00</code>을 넣으면 서버가 켜져 있는 동안 그 시각에 실행해요.</p>
        <pre>python -m app.batch ats
python -m app.batch linkedin-file 결과.json</pre>
        <p class="fd-st ${st.batch_time ? "ok" : "no"}">${st.batch_time ? `✓ 매일 ${esc(st.batch_time)}` : "BATCH_TIME 미설정 (작업 스케줄러 사용 가능)"}</p></section>
    </div></details>`;
}
function renderFeed() {
  const f = state.feed, st = state.feedSt, pane = $("#lsFeedPane");
  const list = f.jobs.filter((j) => (!state.feedFam || j.family === state.feedFam) && (!state.feedNewOnly || j.is_new));
  const lr = f.last_run;
  pane.innerHTML = `
    <section class="li-rank fd">
      <header class="li-rank-head fd-head"><div><p class="ls-k">매일 배치 · 오늘의 새 공고</p>
        <h2>${lr ? `마지막 배치 <span>${esc(lr.run_at)} · ${esc(lr.source)} · 새 ${lr.new} / 전체 ${lr.total}</span>` : "아직 배치 기록이 없어요"}</h2>
        <p class="muted">최근 14일 동안 본 공고 ${f.jobs.length}개 · 출처 ${f.sources.map(esc).join(" · ") || "-"}</p></div>
        <button class="btn-ghost sm" id="fdReload">새로고침</button></header>
      ${f.jobs.length ? `
      <div class="li-kpis">
        <div class="hero"><small>오늘 가장 잘 맞는 공고</small><b>${esc(f.jobs[0].company || "-")}</b><span>${esc(f.jobs[0].title)}</span><em>${f.jobs[0].fit.score}<small>/100</small></em></div>
        <div><small>오늘 새로 나온 공고</small><b class="fd-new">${f.new}</b><span>지난 배치에 없던 공고</span></div>
        <div><small>쌓인 공고 (14일)</small><b>${f.jobs.length}</b><span>중복 없이</span></div>
        <div><small>적합도 70점 이상</small><b>${f.jobs.filter((j) => j.fit.score >= 70).length}</b><span>먼저 볼 곳</span></div>
      </div>
      <div class="fd-filters">${familyChips(f.jobs, state.feedFam, "ffam")}
        <button class="fd-newonly ${state.feedNewOnly ? "on" : ""}" id="fdNewOnly">${state.feedNewOnly ? "✓ " : ""}새 공고만</button></div>
      <ol class="li-list">${list.map((j) => `
        <li class="${j.rank <= 3 ? "top" : ""}">
          <span class="li-rk">${j.rank}</span>
          <div class="li-main">
            <div class="li-co">${j.is_new ? `<span class="fd-badge">NEW</span>` : ""}${famBadge({ family: j.family })} <b>${esc(j.company || "-")}</b>${j.location ? `<small>${esc(j.location)}</small>` : ""}
              ${j.work_type ? `<span class="li-kind k-s">${esc(j.work_type)}</span>` : ""}${j.posted ? `<small>${esc(j.posted)}</small>` : ""}</div>
            <div class="li-title">${esc(j.title)}</div>
            <div class="li-facts"><span>직급 <b>${esc(j.tier)}</b></span><span>예상 연봉 <b>${won(j.salary.min)}~${won(j.salary.max)}</b>만</span>
              ${(j.tags || []).map((t) => `<span class="fd-tag">${esc(t)}</span>`).join("")}${j.alumni ? `<span class="fd-tag alumni">동문 ${j.alumni}명</span>` : ""}
              <span class="fd-src">${esc(j.source_name)} · 처음 본 날 ${esc(j.first_seen)}${j.runs > 1 ? ` · ${j.runs}번 봄` : ""}</span></div>
            <div class="li-iv"><span>인터뷰 핵심</span>${j.interview.map((x) => `<em title="${esc(x.prep)}">${esc(x.keyword)}</em>`).join("")}</div>
            <div class="li-why">${j.fit.reasons.map((x) => `<span>${esc(x)}</span>`).join("")}</div>
          </div>
          <div class="li-side">
            <div class="li-score"><b>${j.fit.score}</b><small>/100 적합도</small></div>
            <div class="li-bar"><i class="f" style="width:${j.fit.parts.family}%"></i><i class="t" style="width:${j.fit.parts.tier}%"></i><i class="k" style="width:${j.fit.parts.keyword}%"></i></div>
            <div class="li-btns">${j.url ? `<a class="src-badge" href="${esc(j.url)}" target="_blank" rel="noopener"><i class="src-dot ${j.source === "linkedin-scan" ? "s-linkedin" : "s-careers"}"></i>원문 ↗</a>` : ""}
              ${j.source === "linkedin-scan" && j.job_id ? `<button class="btn-ghost sm" data-fdeep="${esc(j.job_id)}">자세히 분석</button>` : ""}
              ${j.service_job_id ? `<button class="ca-open" data-job="${j.service_job_id}">회사 인연도 ↗</button>` : ""}</div>
          </div>
        </li>`).join("") || `<div class="empty"><b>조건에 맞는 공고가 없어요</b>필터를 바꿔 보세요.</div>`}</ol>
      <p class="li-legend"><i class="f"></i>직종 40 <i class="t"></i>직급 30 <i class="k"></i>직무명 속 내 기술 30 — 참고 적합도 (매칭률·회사 인연도와 별개)</p>`
      : `<div class="empty"><b>배치로 들어온 공고가 아직 없어요</b>아래 '배치 연동 방법'대로 연결하면 매일 정해진 시각에 쌓여요.</div>`}
      ${feedSetupHtml(st)}
    </section>`;
  $("#fdReload")?.addEventListener("click", loadFeed);
  $("#fdNewOnly")?.addEventListener("click", () => { state.feedNewOnly = !state.feedNewOnly; renderFeed(); });
}
document.addEventListener("click", (e) => {
  const f = e.target.closest("[data-ffam]"); if (f) { state.feedFam = f.dataset.ffam; renderFeed(); }
  const d = e.target.closest("[data-fdeep]");
  if (d) {
    const j = state.feed.jobs.find((x) => x.job_id === d.dataset.fdeep);
    lsTab("one"); $("#lsUrl").value = j.url || ""; $("#lsText").value = "";
    $("#lsText").placeholder = `"${j.title}" 공고를 링크드인에서 열고 공고 글 전체를 복사해 여기에 붙여넣으세요`;
    window.open(j.url, "_blank", "noopener"); $("#lsText").focus();
  }
});


// ═══ ★ 구인 회사 분석 — 링크드인 공고(매일 배치 + 가져온 공고)를 회사별로 ═══
const TONE = { up: "▲", info: "●", warn: "!" };
async function loadCompanies() {
  const pane = $("#lsCoPane");
  pane.innerHTML = `<div class="dash-loading"><span class="spin"></span>링크드인 공고를 회사별로 분석하고 있어요...</div>`;
  try {
    const d = await api("/api/companies", { profile: feedProfile(), saju: state.saju || null, days: 14, imported: state.lsImp?.jobs || [] });
    state.cos = d; renderCompanies();
  } catch (err) { pane.innerHTML = `<div class="empty">${esc(err.message)}</div>`; }
}
function renderCompanies() {
  const d = state.cos, pane = $("#lsCoPane");
  if (!d.companies.length) {
    pane.innerHTML = `<section class="li-rank"><div class="empty"><b>분석할 링크드인 공고가 아직 없어요</b>
      <span>⓪ 오늘의 새 공고(매일 배치)로 쌓이거나 ① 내 링크드인 공고 가져오기(데이터 내보내기 ZIP · 채용 알림 메일)로 올리면 회사별로 분석해 드려요.</span>
      <div class="co-empty-btns"><button class="btn-primary" data-lstab="import">① 내 링크드인 공고 가져오기 →</button><button class="btn-ghost" data-lstab="feed">⓪ 매일 배치 연동 방법</button></div></div></section>`;
    return;
  }
  const top = d.companies[0], sm = feedProfile();
  const famColor = (f) => (FAMILIES.includes(f) ? `var(--fc-${FAMILIES.indexOf(f)})` : "#b8c0cc");   // 기타 = 회색
  pane.innerHTML = `
  <section class="li-rank co">
    <header class="li-rank-head fd-head"><div><p class="ls-k">★ 구인 회사 분석</p><h2>링크드인 공고 ${d.jobs}개 · 회사 ${d.count}곳</h2>
      <p class="muted">${sm.desired_family ? `내 직종 <b>${esc(sm.desired_family)}</b> 기준 · ` : "1단계에서 희망 직종을 고르면 더 정확해요 · "}매일 배치 피드 + 가져온 공고</p></div>
      <button class="btn-ghost sm" id="coReload">새로고침</button></header>
    <div class="li-kpis">
      <div class="hero"><small>나와 가장 잘 맞는 회사</small><b>${esc(top.company)}</b><span>공고 ${top.count}개 · 최고 ${esc(top.best.title)}</span><em>${top.score}<small>/100</small></em></div>
      <div><small>분석한 회사</small><b>${d.count}</b><span>공고 ${d.jobs}개</span></div>
      <div><small>내 직종을 뽑는 회사</small><b>${d.companies.filter((c) => c.my_family_count).length}</b><span>${esc(sm.desired_family || "직종 미정")}</span></div>
      <div><small>새 공고가 있는 회사</small><b class="fd-new">${d.companies.filter((c) => c.new).length}</b><span>지금 지원하면 빠른 지원자</span></div>
    </div>
    <ol class="co-list">${d.companies.map((c) => `
      <li class="${c.rank <= 3 ? "top" : ""}">
        <header class="co-h">
          <span class="li-rk">${c.rank}</span>
          <span class="co-logo">${esc(c.company.split(/\s+/).map((w) => w[0]).join("").slice(0, 2))}</span>
          <div class="co-name"><b>${esc(c.company)}</b><small>${c.locations.map(esc).join(" · ") || "근무지 정보 없음"}${c.work_types.length ? ` · ${c.work_types.map(esc).join("/")}` : ""} · 출처 ${c.sources.map(esc).join(", ")}</small></div>
          <div class="co-score"><b>${c.score}</b><small>/100 회사 적합도</small>
            <div class="li-bar" title="최고 공고 ${c.parts.best}/60 · 내 직종 비중 ${c.parts.mine}/20 · 채용 활발도 ${c.parts.activity}/20"><i class="f" style="width:${c.parts.best}%"></i><i class="t" style="width:${c.parts.mine}%"></i><i class="k" style="width:${c.parts.activity}%"></i></div></div>
        </header>
        <div class="co-body">
          <section><h6>무엇을 얼마나 뽑나</h6>
            <p class="co-big"><b>${c.count}</b>개 공고${c.new ? ` · <span class="fd-badge">NEW ${c.new}</span>` : ""}</p>
            <div class="co-stack">${c.families.map((f) => `<i style="flex:${f.n};background:${famColor(f.family)}" title="${esc(f.family)} ${f.n}"></i>`).join("")}</div>
            <div class="co-fams">${c.families.map((f) => `${famBadge({ family: f.family })}<small>${f.n}</small>`).join(" ")}</div>
            <p class="co-tiers">직급 ${c.tiers.map((t) => `<b>${esc(t.tier)}</b> ${t.n}`).join(" · ")}</p>
            <p class="co-sal">예상 연봉 <b>${won(c.salary.min)}~${won(c.salary.max)}</b>만</p></section>
          <section><h6>채용 신호 <small>공고에서 읽은 추정</small></h6>
            <ul class="co-sig">${c.signals.map((x) => `<li class="${x.tone}"><i>${TONE[x.tone]}</i>${esc(x.text)}</li>`).join("") || `<li class="info"><i>●</i>공고가 1개라 신호가 아직 약해요</li>`}</ul></section>
          <section><h6>나와의 연결</h6>
            <p class="co-best">가장 잘 맞는 공고<br><b>${esc(c.best.title)}</b> <em>${c.best.score}점</em></p>
            <p class="co-mine">내 직종 공고 <b>${c.my_family_count}</b> / ${c.count}</p>
            <div class="li-iv"><span>인터뷰 공통 키워드</span>${c.interview.map((k) => `<em>${esc(k)}</em>`).join("")}</div>
            ${c.service_company ? `<div class="co-svc"><span>서비스 분석 가능</span>${c.company_fit != null ? `회사 인연도 <b>${c.company_fit}</b>점 · ` : ""}재무·한국 사업·사주·인맥
              <button class="ca-open" data-job="${c.service_job_id}">회사 인연도 대시보드 ↗</button></div>` : `<p class="muted co-nosvc">재무·한국 사업 정보는 아직 없어요 — 공고 1개를 <b>자세히 분석</b>하면 회사 소개도 읽어요</p>`}
          </section>
        </div>
        <details class="co-posts"><summary>이 회사 공고 ${c.count}개 보기</summary>
          <ul>${c.postings.map((p) => `<li>${p.is_new ? `<span class="fd-badge">NEW</span>` : ""}${famBadge({ family: p.family })}<b>${esc(p.title)}</b><small>${esc(p.tier)}${p.work_type ? ` · ${esc(p.work_type)}` : ""}${p.posted ? ` · ${esc(p.posted)}` : ""}</small>
            <em>${p.fit}점</em>${p.url ? `<a href="${esc(p.url)}" target="_blank" rel="noopener">원문 ↗</a>` : ""}</li>`).join("")}</ul></details>
      </li>`).join("")}</ol>
    <p class="li-legend"><i class="f"></i>최고 공고 적합도 60 <i class="t"></i>내 직종 비중 20 <i class="k"></i>채용 활발도 20 — ${esc(d.formula)}</p>
  </section>`;
  $("#coReload")?.addEventListener("click", loadCompanies);
}


// ② 공고 1개 자세히 분석: 공고 파일(PDF·Word·txt) 올리기 → 글·공고 주소 채우기
$("#lsOneFileBtn").addEventListener("click", () => $("#lsOneFile").click());
$("#lsOneFile").addEventListener("change", async (e) => {
  const file = e.target.files[0]; if (!file) return;
  loading(true, `${file.name} 읽는 중...`);
  try {
    const d = await readResumeFile(file);
    $("#lsText").value = d.text;
    if (d.job_urls && d.job_urls.length && !$("#lsUrl").value.trim()) $("#lsUrl").value = d.job_urls[0];
    $("#lsOneFileName").innerHTML = `📄 <b>${esc(d.filename)}</b> · ${d.type}${d.pages ? ` ${d.pages}쪽` : ""} · ${d.chars.toLocaleString()}자${d.job_urls?.length ? " · 공고 주소 찾음" : ""}`;
    toast("공고 파일을 읽었어요. '공고 분석하기'를 누르세요.");
  } catch (err) { toast(err.message, true); } finally { loading(false); e.target.value = ""; }
});
