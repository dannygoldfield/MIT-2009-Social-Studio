"use strict";
const $ = (q, root = document) => root.querySelector(q);
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const stages = ["audio", "video", "text", "assembly"];
const names = {
  audio: "Audio",
  video: "Video",
  text: "Keyword",
  assembly: "Assembly",
};
let current = localStorage.getItem("studio-project"),
  stage = "audio",
  state,
  activeBatch,
  polling,
  lastJobSignature = "";
let pending = false;
let savedDrafts;
try {
  savedDrafts = JSON.parse(localStorage.getItem("studio-drafts") || "[]");
} catch {
  savedDrafts = [];
}
const drafts = new Map(savedDrafts);
function saveDrafts() {
  localStorage.setItem("studio-drafts", JSON.stringify([...drafts]));
}

async function api(path, body, method = "POST") {
  const options =
    body === undefined ? {} : { method, headers: { "X-Studio-Request": "1" } };
  if (body instanceof FormData) options.body = body;
  else if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch("/api" + path, options);
  const data = await response.json();
  if (!response.ok)
    throw new Error(
      data.error ||
        (typeof data.detail === "string"
          ? data.detail
          : data.detail?.map((x) => x.msg).join(" · ")) ||
        "Something went wrong. Please try again.",
    );
  return data;
}
function notice(message) {
  const node = $("#notice");
  node.textContent = message;
  node.hidden = false;
  clearTimeout(node.timer);
  node.timer = setTimeout(() => (node.hidden = true), 6500);
}
async function act(fn) {
  if (pending) return;
  pending = true;
  try {
    await fn();
  } catch (error) {
    notice(error.message);
  } finally {
    pending = false;
  }
}
function mediaUrl(c, kind = "preview") {
  return `/api/candidates/${c.id}/file/${kind}${c.stage === "audio" && kind === "preview" ? "?playback=1" : ""}`;
}
function currentDraft() {
  if (!drafts.has(current))
    drafts.set(current, { keyword: "", audio: {}, photos: null });
  return drafts.get(current);
}
async function refreshProjects() {
  const projects = await api("/projects");
  $("#projects").innerHTML = projects
    .map(
      (p) =>
        `<button data-project="${p.id}" class="${p.id === current ? "active" : ""}">${esc(p.name)}<small>${esc(p.author)} · ${p.aspect === "vertical" ? "9:16" : "16:9"}</small></button>`,
    )
    .join("");
  return projects;
}
function autoStage() {
  return stages.find((s) => !state.selections[s]) || "assembly";
}
async function openProject(id) {
  current = id;
  localStorage.setItem("studio-project", id);
  state = await api("/projects/" + id);
  stage = autoStage();
  activeBatch = null;
  lastJobSignature = "";
  await refreshProjects();
  render();
  startPolling();
}
async function refresh() {
  state = await api("/projects/" + current);
  render();
}
function openCreate() {
  const dialog = $("#create-dialog");
  dialog.showModal();
  $("#create-form [name=author]").value =
    localStorage.getItem("studio-author") || "";
  $("#create-form [name=name]").focus();
}
function welcome() {
  state = null;
  $("#main").innerHTML =
    `<div class="welcome"><span class="eyebrow">MIT 2.009 · HUMAN CHOICES, REAL STORIES</span><h1>Start with something yours.<br>See where it can go.</h1><p class="intro">A sound. A few photographs. One word. Compare three possibilities at a time, shape a 15-second story, and explain why it carries your name.</p><div class="welcome-steps">${stages.map((s, i) => `<div><small>0${i + 1}</small>${names[s]}</div>`).join("")}</div><div class="actions"><button data-action="new">Start a project →</button><button class="secondary" data-action="demo">Try the sample project</button></div><p class="muted welcome-note">This first version makes real media with local melody preparation and image animation. AI providers are a future extension. Your projects and choices stay on this computer.</p></div>`;
}
function selectedCandidate(s) {
  return state.candidates.find((c) => c.id === state.selections[s]);
}
function render() {
  if (!state) return welcome();
  const p = state.project;
  const locked = stages
    .slice(0, stages.indexOf(stage))
    .some((s) => !state.selections[s]);
  $("#main").innerHTML =
    `<span class="eyebrow">${esc(p.name)}</span><div class="project-meta">Made by ${esc(p.author)} · ${p.aspect === "vertical" ? "9:16 Vertical" : "16:9 Horizontal"} · 15 seconds</div><nav class="stages" aria-label="Workflow">${stages.map((s, i) => `<button data-stage="${s}" class="${s === stage ? "active" : ""} ${state.selections[s] ? "done" : ""}"><span class="step-number">${state.selections[s] ? "✓" : i + 1}</span>${names[s]}</button>`).join("")}</nav>${stageHeading()}${jobPanel()}${locked ? '<div class="empty">Select a candidate at each earlier stage to continue.</div>' : inputPanel() + comparison() + advancePanel()}${state.approvals.length ? approvalHistory() : ""}`;
  // Keep checkbox changes local until a generation request snapshots them.
}
function stageHeading() {
  const text = {
    audio: [
      "Your melody. A world of possibilities.",
      "Hum, sing, or play a phrase. Start with what comes naturally—we’ll build from your musical idea.",
    ],
    video: [
      "Give your story a different shape.",
      "Choose 1–10 photographs. Three bold treatments respond to the rhythm of your selected audio.",
    ],
    text: [
      "One word. Make it move.",
      "Three transparent treatments take their timing and placement from your selected video.",
    ],
    assembly: [
      "Same ingredients. Different stories.",
      "Compare three editorial decisions. Choose one, explain why, and approve the exact final file.",
    ],
  }[stage];
  return `<h1>${text[0]}</h1><p class="intro">${text[1]}</p>`;
}
function jobPanel() {
  const jobs = state.jobs.filter(
    (j) => state.batches.find((b) => b.id === j.batch_id)?.stage === stage,
  );
  const job = jobs.at(-1);
  if (!job || job.status === "done") return "";
  const done = state.candidates.filter(
    (c) => c.batch_id === job.batch_id && c.status === "ready",
  ).length;
  const count = stage === "audio" ? 4 : 3;
  return `<div class="job ${job.status === "failed" ? "failed" : ""}" aria-live="polite"><strong>${esc(job.progress)}</strong>${job.status === "failed" ? `<p class="error">${esc(job.error)}</p><button class="secondary" data-retry="${job.id}">Retry missing candidates</button>` : `<p class="muted">${done} of ${count} ready. You can leave this page; keep the studio running.</p><progress max="${count}" value="${done}"></progress>`}</div>`;
}
function assetSelect(role, label) {
  const items = state.assets.filter((a) => a.role === role);
  const draft = currentDraft();
  const selected = draft.audio[role] || items.at(-1)?.id || "";
  draft.audio[role] = selected;
  return `<label>${label}<select data-audio-role="${role}" ${!items.length ? "disabled" : ""}>${items.map((a) => `<option value="${a.id}" ${a.id === selected ? "selected" : ""}>${esc(a.name)}</option>`).join("")}</select><input type="file" data-upload="${role}" accept="audio/*" aria-label="Upload ${label.toLowerCase()}"></label>`;
}
function inputPanel() {
  const busy = state.jobs.some((j) => ["queued", "running"].includes(j.status));
  const disabled = busy ? "disabled" : "";
  if (stage === "audio") {
    const chosen =
      state.assets.find((a) => a.id === currentDraft().audio.reference) ||
      state.assets.filter((a) => a.role === "reference").at(-1);
    const guide = chosen?.analysis.melody_guide;
    return `<div class="input-panel">${assetSelect("reference", "Your musical phrase")}${chosen ? `<div class="reference-audio"><span class="eyebrow">Your starting idea</span><audio controls preload="metadata" src="/api/assets/${chosen.id}/file?playback=1"></audio><p class="muted">${esc(chosen.name)} · Playback skips the opening wait. Your full original stays saved.</p></div>` : ""}<button data-action="melody" ${disabled || (!chosen ? "disabled" : "")}>${guide ? "Check my melody again" : "Find my melody"}</button><span class="muted">One phrase is all you need. No extra sounds to choose.</span></div>${guide ? `<div class="melody-check"><span class="eyebrow">Melody check</span><p>A simple instrument plays the notes we heard. This is a guide for the ensemble, not the finished arrangement.</p><audio controls preload="metadata" src="${esc(guide.url)}?playback=1"></audio></div>` : ""}`;

  }
  if (stage === "video") {
    const photos = state.assets.filter((a) => a.role === "photo");
    const d = currentDraft();
    if (d.photos === null) d.photos = photos.slice(-10).map((a) => a.id);
    return `<div class="input-panel"><label>Add photographs<input type="file" data-upload="photo" multiple accept="image/jpeg,image/png,image/webp,image/tiff"></label><div class="photos">${photos.map((a) => `<label class="photo"><input type="checkbox" data-photo="${a.id}" ${d.photos.includes(a.id) ? "checked" : ""}><img src="/api/assets/${a.id}/file" alt="${esc(a.name)}"><span>${esc(a.name)}</span></label>`).join("")}</div><button data-action="generate" ${disabled}>Generate 3</button><span class="muted">Use 1–10 checked photos · Select the best fit before asking for more.</span></div>`;
  }
  if (stage === "text") {
    return `<div class="input-panel"><label>Keyword<input id="keyword" maxlength="32" value="${esc(currentDraft().keyword)}" placeholder="CONNECT" autocomplete="off"></label><button data-action="generate" ${disabled}>Generate 3</button><span class="muted">Exactly one word · Transparent animation</span></div>`;
  }
  return `<div class="ingredients">${stages
    .slice(0, 3)
    .map(
      (s) =>
        `<div class="ingredient"><small>${names[s]} · Your selection</small>${esc(selectedCandidate(s)?.settings.style.name)}</div>`,
    )
    .join(
      "",
    )}</div><div class="actions"><button data-action="generate" ${disabled}>Assemble 3 final mixes</button><span class="muted">Your selections stay authoritative.</span></div>`;
}
function waveform(c) {
  return `<div class="sound-art" style="--accent:${esc(c.settings.style.color)}" aria-hidden="true">${Array.from({ length: 33 }, (_, i) => `<span style="--height:${12 + Math.round(62 * Math.abs(Math.sin(i * 1.31 + c.slot) * Math.cos(i * 0.24)))}px"></span>`).join("")}</div>`;
}
function card(c) {
  const ready = c.status === "ready",
    selected = state.selections[stage] === c.id;
  return `<article class="candidate ${selected ? "selected" : ""}" data-candidate="${c.id}"><div class="candidate-top"><div class="option-label"><span>${c.kind === "original" ? "PRESERVATION + ENHANCEMENT" : "OPTION " + c.slot}</span><span class="winner">${c.winner_at ? "★ Saved winner" : ""}</span></div><h3>${esc(c.settings.style.name)}</h3><p>${esc(c.settings.style.description)}</p></div><div class="candidate-body">${ready ? (stage === "audio" ? waveform(c) + `<audio controls preload="metadata" src="${mediaUrl(c)}"></audio>` : `<video controls playsinline preload="none" poster="${mediaUrl(c, "poster")}" src="${mediaUrl(c)}"></video>`) : `<div class="sound-art muted">${c.status === "failed" ? "Needs a retry" : c.status === "running" ? "Rendering…" : "Waiting…"}</div>`}${c.error ? `<p class="error">${esc(c.error)}</p>` : ""}<div class="stars" role="group" aria-label="Rate ${esc(c.settings.style.name)}">${[1, 2, 3, 4, 5].map((n) => `<button data-rate="${c.id}" data-stars="${n}" aria-label="${n} star${n === 1 ? "" : "s"} for ${esc(c.settings.style.name)}" aria-pressed="${c.rating === n}" class="${n <= c.rating ? "filled" : ""}" ${ready ? "" : "disabled"}>★</button>`).join("")}</div>${c.stale ? '<p class="muted">Made for earlier selections. Regenerate to use with your current choices.</p>' : ""}<button class="select-button" data-select="${c.id}" ${!ready || c.stale || !c.rating ? "disabled" : ""}>${selected ? "✓ Selected" : !c.rating ? "Rate, then select" : "Select this one"}</button><details class="provenance"><summary>How it was made</summary><p class="muted">${esc(c.settings.provider)} · ${esc(c.settings.renderer_version)} · ${c.analysis.elapsed_seconds?.toFixed(1) || "—"}s to render</p><pre>${esc(JSON.stringify({ settings: c.settings, sources: c.sources, earlier_choices: c.context, analysis: c.analysis }, null, 2))}</pre>${ready ? `<a href="${mediaUrl(c, "output")}" download>Download draft ${stage === "text" ? "alpha MOV" : "file"}</a>` : ""}</details></div></article>`;
}
function comparison() {
  if (stage === "audio") {
    const briefs = [
      ["#1f78bb", "Bass-heavy dance", "Your phrase becomes the hook: deep bass, a tight drum groove, and a lead that opens into a bigger arrangement."],
      ["#924c9e", "Chamber trio", "Piano, violin, and cello listen and respond—sharing your melody with warmth, space, and expressive phrasing."],
      ["#ee3a80", "Jazz trio", "Piano, upright bass, and drums find the swing in your phrase, then playfully develop it together."],
    ];
    const older = state.candidates.filter(c => c.stage === "audio");
    return `<section class="ensemble-preview"><div class="batch-heading"><span class="eyebrow">Three ensembles. Your musical idea.</span></div><p class="muted">Next: convincing instrumental performances built around your phrase. We’re testing orchestration quality before offering these as finished choices.</p><div class="candidate-grid">${briefs.map(([color, name, description]) => `<article class="ensemble-brief" style="--ensemble-color:${color}"><span class="tag">In development</span><h3>${name}</h3><p>${description}</p></article>`).join("")}</div></section>${older.length ? `<details class="history"><summary>Earlier sound experiments</summary><p class="muted">These came from the retired voice-effects prototype and may contain recognizable words. They are saved as history, not examples of the new ensemble direction.</p><div class="candidate-grid">${older.map(c => `<article class="ensemble-brief"><h3>${esc(c.settings.style.name)}</h3>${c.status === "ready" ? `<audio controls preload="none" src="${mediaUrl(c)}"></audio>` : `<p>${esc(c.status)}</p>`}</article>`).join("")}</div></details>` : ""}`;
  }
  const batches = state.batches.filter((b) => b.stage === stage);
  if (!batches.length)
    return '<div class="empty">Your three possibilities will appear here.</div>';
  const batch = batches.find((b) => b.id === activeBatch) || batches.at(-1);
  const candidates = state.candidates.filter((c) => c.batch_id === batch.id);
  const original = candidates.find((c) => c.kind === "original");
  return `<div class="batch-heading"><span class="eyebrow">BATCH ${batches.indexOf(batch) + 1} · COMPARE & CHOOSE</span><p class="muted">5 stars saves a winner. It never approves a file.</p></div><div class="candidate-grid">${candidates
    .filter((c) => c.kind !== "original")
    .map(card)
    .join(
      "",
    )}</div>${original ? `<section class="original"><div><span class="tag">A DIFFERENT POSSIBILITY</span><h2>Original Mix</h2><p>Your contribution stays in the foreground. Your original recording, supported by a bed and sound effects.</p><p class="muted">Preserved timing, pitch, and order within the 15-second excerpt. This is not a fourth interpretation.</p></div>${card(original)}</section>` : ""}<details class="history"><summary>Earlier batches & saved winners (${batches.length} batches · ${state.candidates.filter((c) => c.stage === stage && c.winner_at).length} winners)</summary><div class="history-buttons">${batches.map((b, i) => `<button class="secondary" data-batch="${b.id}">Batch ${i + 1}${state.candidates.some((c) => c.batch_id === b.id && c.winner_at) ? " · ★" : ""}</button>`).join("")}</div><p class="muted">A winner remains saved even if you later change its rating. New generation is an explicit choice.</p></details>`;
}
function advancePanel() {
  if (stage === "audio") return "";
  const c = selectedCandidate(stage);
  if (!c) return "";
  if (stage !== "assembly")
    return `<div class="advance"><p><strong>${esc(c.settings.style.name)}</strong> is your selected ${names[stage].toLowerCase()}.</p><button data-stage="${stages[stages.indexOf(stage) + 1]}">Continue to ${names[stages[stages.indexOf(stage) + 1]]} →</button></div>`;
  const already = state.approvals.find((a) => a.candidate_id === c.id);
  if (already)
    return `<div class="advance"><p>This version was approved with your explanation. You can export it below.</p></div>`;
  return `<section class="approval"><span class="eyebrow">YOUR NAME. YOUR DECISION.</span><h2>Why this one?</h2><p class="muted">You chose <strong>${esc(c.settings.style.name)}</strong>. Explain the choice that makes this your work.</p><label>Your explanation<textarea id="explanation" maxlength="1000" placeholder="I chose this because…">${esc(currentDraft().explanation || "")}</textarea></label><label class="checkbox"><input type="checkbox" id="confirm-approval">I have reviewed this final mix and approve this exact version as ${esc(state.project.author)}.</label><button data-approve="${c.id}">Approve this version</button><p class="muted">Approval records the file, sources, candidates considered, decisions, your explanation, and the date.</p></section>`;
}
function approvalHistory() {
  return `<section class="approval"><span class="eyebrow">APPROVED OUTPUTS</span>${state.approvals.map((a) => `<div class="record"><strong>Approved by ${esc(state.project.author)}</strong><p>${esc(a.explanation)}</p><p class="muted">${new Date(a.created_at).toLocaleString()}</p><div class="actions"><button data-export="${a.id}">Export approved media + provenance</button><button class="text-button" data-provenance="${a.id}">View approval record</button></div></div>`).join("")}</section>`;
}
async function generate() {
  const d = currentDraft();
  const body = { stage, asset_ids: [] };
  if (stage === "audio")
    body.asset_ids = [d.audio.reference].filter(Boolean);
  if (stage === "video") body.asset_ids = d.photos || [];
  if (stage === "text") body.keyword = d.keyword;
  await api("/projects/" + current + "/generate", body);
  activeBatch = null;
  await refresh();
}
function startPolling() {
  clearInterval(polling);
  lastJobSignature = JSON.stringify(
    state.jobs.map((j) => [j.id, j.status, j.progress]),
  );
  polling = setInterval(async () => {
    if (!current || pending) return;
    try {
      const next = await api("/projects/" + current);
      const signature = JSON.stringify(
        next.jobs.map((j) => [j.id, j.status, j.progress]),
      );
      const working = next.jobs.some((j) =>
        ["queued", "running"].includes(j.status),
      );
      if (signature !== lastJobSignature) {
        const oldWasWorking = state.jobs.some((j) =>
          ["queued", "running"].includes(j.status),
        );
        state = next;
        lastJobSignature = signature;
        if (working) {
          const panel = $(".job");
          if (panel && panel.contains(document.activeElement) === false)
            panel.outerHTML = jobPanel();
          else if (!panel) render();
        } else if (oldWasWorking || signature) render();
      }
    } catch (error) {
      notice("Connection lost. Your saved choices remain on disk.");
    }
  }, 1600);
}
// A comparison should have only one sound or video playing at a time.
document.addEventListener(
  "play",
  (event) => {
    document.querySelectorAll("audio,video").forEach((m) => {
      if (m !== event.target) m.pause();
    });
  },
  true,
);
document.addEventListener("input", (event) => {
  if (event.target.id === "keyword")
    currentDraft().keyword = event.target.value;
  if (event.target.id === "explanation")
    currentDraft().explanation = event.target.value;
  if (current) saveDrafts();
});
document.addEventListener("change", (event) => {
  const node = event.target;
  if (node.dataset.audioRole !== undefined)
    currentDraft().audio[node.dataset.audioRole] = node.value;
  if (node.dataset.photo) {
    const d = currentDraft();
    d.photos = node.checked
      ? [...new Set([...d.photos, node.dataset.photo])]
      : d.photos.filter((id) => id !== node.dataset.photo);
  }
  if (current) saveDrafts();
  if (node.dataset.upload)
    act(async () => {
      notice("Adding your source material…");
      for (const file of node.files) {
        const form = new FormData();
        form.append("role", node.dataset.upload);
        form.append("file", file);
        const a = await api("/projects/" + current + "/assets", form);
        if (a.role === "photo") {
          const d = currentDraft();
          d.photos = [...new Set([...(d.photos || []), a.id])].slice(-10);
        } else currentDraft().audio[a.role] = a.id;
      }
      saveDrafts();
      await refresh();
      notice("Source material saved.");
    });
});
document.addEventListener("click", (event) => {
  const node = event.target.closest("button");
  if (!node) return;
  if (node.dataset.stage) {
    stage = node.dataset.stage;
    activeBatch = null;
    render();
    return;
  }
  if (node.dataset.batch) {
    activeBatch = node.dataset.batch;
    render();
    return;
  }
  if (node.dataset.action === "new" || node.id === "new-project") {
    openCreate();
    return;
  }
  if (node.id === "cancel-create") {
    $("#create-dialog").close();
    return;
  }
  act(async () => {
    if (node.dataset.project) await openProject(node.dataset.project);
    if (node.dataset.action === "generate") await generate();
    if (node.dataset.action === "melody") {
      node.disabled = true;
      node.textContent = "Listening for your melody…";
      try {
        await api("/assets/" + currentDraft().audio.reference + "/melody", {});
      } finally {
        await refresh();
      }
    }
    if (node.dataset.action === "demo") {
      const p = await api("/demo", {});
      await openProject(p.id);
    }
    if (node.dataset.rate) {
      await api("/candidates/" + node.dataset.rate + "/rating", {
        stars: Number(node.dataset.stars),
      });
      await refresh();
    }
    if (node.dataset.select) {
      await api("/candidates/" + node.dataset.select + "/select", {});
      await refresh();
    }
    if (node.dataset.retry) {
      await api("/jobs/" + node.dataset.retry + "/retry", {});
      await refresh();
    }
    if (node.dataset.approve) {
      if (!$("#confirm-approval").checked)
        throw new Error(
          "Review the final mix and confirm your approval first.",
        );
      await api("/projects/" + current + "/approvals", {
        candidate_id: node.dataset.approve,
        explanation: $("#explanation").value,
        confirmed: true,
      });
      await refresh();
      notice("Your explanation and approval are saved.");
    }
    if (node.dataset.export) {
      const result = await api(
        "/approvals/" + node.dataset.export + "/export",
        {},
      );
      const link = document.createElement("a");
      link.href = result.url;
      link.download = "2.009-approved-media.zip";
      link.click();
      notice("Approved media and provenance are ready to download.");
    }
    if (node.dataset.provenance) {
      const a = await api("/approvals/" + node.dataset.provenance);
      const blob = new Blob([JSON.stringify(a.snapshot, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "approval-record.json";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
  });
});
$("#create-form").addEventListener("submit", (event) => {
  event.preventDefault();
  act(async () => {
    const form = new FormData(event.target);
    const body = Object.fromEntries(form);
    const p = await api("/projects", body);
    localStorage.setItem("studio-author", body.author);
    $("#create-dialog").close();
    await openProject(p.id);
  });
});
(async () => {
  try {
    const projects = await refreshProjects();
    if (current && projects.some((p) => p.id === current))
      await openProject(current);
    else welcome();
  } catch (error) {
    notice(error.message);
    welcome();
  }
})();
