const SAMPLE_ARCHIVE_PATH = "../fixtures/bqa-demo-archive.json";

const sampleArchive = {
  manifest: {
    archive_type: "bqa-demo",
    name: "bqa_synthetic_archive_v1.0.0",
    version: "1.0.0",
    created_at: "2026-06-29T00:00:00Z",
    synthetic: true,
    privacy: "synthetic-only",
    description: "Synthetic BQA archive for local browser demo flows."
  },
  sessions: [
    {
      id: "session-demo-001",
      title: "Synthetic checkout regression triage",
      source: "synthetic",
      summary: "Agent identified missing validation around checkout event normalization.",
      artifacts: ["agent-data-ingestion", "workflow-regression-loop", "spec-checkout-normalization"]
    },
    {
      id: "session-demo-002",
      title: "Synthetic release readiness review",
      source: "synthetic",
      summary: "Agent converted release notes into QA checks and handoff notes.",
      artifacts: ["agent-release-qa", "workflow-release-gate", "knowledge-release-readiness"]
    }
  ],
  agents: [
    {
      id: "agent-data-ingestion",
      name: "DataIngestionAgent",
      role: "Ingestion",
      domain: "Data",
      version: "1.0.0",
      status: "OK",
      description: "Discovers input files, validates schemas, and normalizes synthetic source records."
    },
    {
      id: "agent-release-qa",
      name: "ReleaseQAAssistant",
      role: "QA",
      domain: "Release",
      version: "1.0.0",
      status: "OK",
      description: "Builds release verification checklists from synthetic release notes."
    },
    {
      id: "agent-drift-guard",
      name: "DriftGuard",
      role: "Safety",
      domain: "Governance",
      version: "1.0.0",
      status: "OK",
      description: "Compares current work against acceptance criteria and warns on scope drift."
    }
  ],
  workflows: [
    {
      id: "workflow-regression-loop",
      name: "Regression Triage Loop",
      steps: ["Load synthetic session", "Extract expected checks", "Generate QA task", "Verify result"],
      owner: "ReleaseQAAssistant",
      status: "Ready"
    },
    {
      id: "workflow-release-gate",
      name: "Release Gate Review",
      steps: ["Review change summary", "Map affected checks", "Collect evidence", "Prepare approval note"],
      owner: "DriftGuard",
      status: "Ready"
    }
  ],
  specs: [
    {
      id: "spec-checkout-normalization",
      title: "Checkout Normalization Spec",
      type: "QA Spec",
      status: "Ready",
      acceptance: ["Input schema is explicit", "Output records are normalized", "Missing fields are reported"]
    },
    {
      id: "spec-demo-upload",
      title: "Demo Upload Flow Spec",
      type: "Product Spec",
      status: "Ready",
      acceptance: ["Archive is parsed locally", "Artifacts are displayed", "Result can be downloaded"]
    }
  ],
  knowledge: [
    {
      id: "knowledge-release-readiness",
      title: "Release Readiness Pattern",
      category: "Pattern",
      content: "Convert change notes into checks, evidence links, and explicit approval criteria."
    },
    {
      id: "knowledge-synthetic-data",
      title: "Synthetic Data Rule",
      category: "Safety",
      content: "Demo fixtures use invented identifiers, fake sessions, and public-safe examples only."
    }
  ],
  recommendations: [
    {
      id: "recommendation-add-smoke",
      title: "Add install smoke coverage",
      priority: "High",
      body: "Run the installer in a temporary repository before long autopilot runs."
    },
    {
      id: "recommendation-demo-script",
      title: "Prepare demo script",
      priority: "Medium",
      body: "Use the synthetic archive to show upload, validation, artifact review, and result download."
    }
  ]
};

const requiredSections = ["manifest", "sessions", "agents", "workflows", "specs", "knowledge", "recommendations"];
const sectionLabels = {
  agents: "Generated agents discovered in the archive.",
  workflows: "Runnable workflow outlines and handoffs.",
  specs: "Specs and acceptance criteria generated from sessions.",
  knowledge: "Reusable knowledge extracted from synthetic work.",
  recommendations: "Next actions generated from archive review."
};

let currentArchive = sampleArchive;
let activeSection = "agents";
let selectedId = "";

const elements = {
  input: document.querySelector("#archive-input"),
  loadSample: document.querySelector("#load-sample"),
  clearSession: document.querySelector("#clear-session"),
  download: document.querySelector("#download-result"),
  validationDot: document.querySelector("#validation-dot"),
  validationTitle: document.querySelector("#validation-title"),
  validationMessage: document.querySelector("#validation-message"),
  validationList: document.querySelector("#validation-list"),
  tabs: [...document.querySelectorAll(".tab")],
  sectionTitle: document.querySelector("#section-title"),
  sectionSubtitle: document.querySelector("#section-subtitle"),
  search: document.querySelector("#artifact-search"),
  list: document.querySelector("#artifact-list"),
  detail: document.querySelector("#artifact-detail"),
  counts: document.querySelector("#summary-counts"),
  details: document.querySelector("#archive-details")
};

function validateArchive(archive) {
  return requiredSections.map((section) => {
    const value = archive ? archive[section] : undefined;
    const valid = section === "manifest"
      ? value && typeof value === "object" && !Array.isArray(value)
      : Array.isArray(value);
    const count = Array.isArray(value) ? value.length : valid ? 1 : 0;
    return { section, valid: Boolean(valid), count };
  });
}

function archiveIsValid(archive) {
  return validateArchive(archive).every((item) => item.valid);
}

function setArchive(archive) {
  currentArchive = archive;
  selectedId = "";
  render();
}

function renderValidation() {
  const checks = validateArchive(currentArchive);
  const valid = checks.every((item) => item.valid);
  elements.validationDot.classList.toggle("invalid", !valid);
  elements.validationTitle.textContent = valid ? "Archive validated" : "Archive needs attention";
  elements.validationMessage.textContent = valid
    ? "All required sections are present and ready."
    : "Required sections are missing or malformed.";
  elements.validationList.innerHTML = checks.map((item) => `
    <li>
      <span>${item.section}</span>
      <strong>${item.valid ? item.count : "Missing"}</strong>
    </li>
  `).join("");
}

function renderSummary() {
  const counts = ["agents", "workflows", "specs", "knowledge", "recommendations"];
  elements.counts.innerHTML = counts.map((section) => `
    <div>
      <dt>${capitalize(section)}</dt>
      <dd>${Array.isArray(currentArchive[section]) ? currentArchive[section].length : 0}</dd>
    </div>
  `).join("");

  const manifest = currentArchive.manifest || {};
  elements.details.innerHTML = [
    ["Name", manifest.name || "Unknown"],
    ["Version", manifest.version || "Unknown"],
    ["Privacy", manifest.privacy || "Unknown"],
    ["Source", SAMPLE_ARCHIVE_PATH]
  ].map(([label, value]) => `
    <div>
      <dt>${label}</dt>
      <dd>${value}</dd>
    </div>
  `).join("");
}

function renderArtifacts() {
  const artifacts = Array.isArray(currentArchive[activeSection]) ? currentArchive[activeSection] : [];
  const query = elements.search.value.trim().toLowerCase();
  const filtered = artifacts.filter((artifact) => JSON.stringify(artifact).toLowerCase().includes(query));
  const selected = filtered.find((artifact) => artifact.id === selectedId) || filtered[0];
  selectedId = selected ? selected.id : "";

  elements.sectionTitle.textContent = capitalize(activeSection);
  elements.sectionSubtitle.textContent = sectionLabels[activeSection];
  elements.list.innerHTML = filtered.map((artifact) => {
    const title = artifact.name || artifact.title || artifact.id;
    const meta = artifact.role || artifact.type || artifact.category || artifact.priority || artifact.owner || "Artifact";
    const status = artifact.status || artifact.priority || "Ready";
    return `
      <button class="artifact-row ${artifact.id === selectedId ? "active" : ""}" type="button" data-id="${artifact.id}">
        <span>
          <strong>${title}</strong>
          <span>${meta}</span>
        </span>
        <span class="pill">${status}</span>
      </button>
    `;
  }).join("");

  renderDetail(selected);
}

function renderDetail(artifact) {
  if (!artifact) {
    elements.detail.innerHTML = "<h3>No artifacts found</h3><p>Try another tab or search term.</p>";
    return;
  }

  const title = artifact.name || artifact.title || artifact.id;
  const body = artifact.description || artifact.body || artifact.content || "Synthetic archive artifact.";
  const fields = Object.entries(artifact)
    .filter(([key]) => !["id", "name", "title", "description", "body", "content"].includes(key))
    .map(([key, value]) => `
      <div>
        <dt>${formatKey(key)}</dt>
        <dd>${Array.isArray(value) ? value.join(", ") : value}</dd>
      </div>
    `).join("");

  elements.detail.innerHTML = `
    <h3>${title}</h3>
    <p>${body}</p>
    <dl>${fields}</dl>
  `;
}

function downloadResult() {
  const result = {
    generated_at: new Date().toISOString(),
    source: currentArchive.manifest ? currentArchive.manifest.name : "uploaded-archive",
    valid: archiveIsValid(currentArchive),
    counts: Object.fromEntries(
      ["sessions", "agents", "workflows", "specs", "knowledge", "recommendations"].map((section) => [
        section,
        Array.isArray(currentArchive[section]) ? currentArchive[section].length : 0
      ])
    ),
    recommendations: currentArchive.recommendations || []
  };
  const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "bqa-demo-result.json";
  link.click();
  URL.revokeObjectURL(url);
}

function handleUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.addEventListener("load", () => {
    try {
      setArchive(JSON.parse(reader.result));
    } catch (error) {
      elements.validationDot.classList.add("invalid");
      elements.validationTitle.textContent = "Archive needs attention";
      elements.validationMessage.textContent = `Could not parse JSON: ${error.message}`;
    }
  });
  reader.readAsText(file);
}

function render() {
  renderValidation();
  renderSummary();
  renderArtifacts();
}

function capitalize(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatKey(value) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

elements.input.addEventListener("change", handleUpload);
elements.loadSample.addEventListener("click", () => setArchive(sampleArchive));
elements.clearSession.addEventListener("click", () => setArchive({}));
elements.download.addEventListener("click", downloadResult);
elements.search.addEventListener("input", renderArtifacts);
elements.tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    activeSection = tab.dataset.section;
    selectedId = "";
    elements.tabs.forEach((item) => item.classList.toggle("active", item === tab));
    renderArtifacts();
  });
});
elements.list.addEventListener("click", (event) => {
  const row = event.target.closest(".artifact-row");
  if (!row) return;
  selectedId = row.dataset.id;
  renderArtifacts();
});

render();
