const vscode = acquireVsCodeApi();

let state = {
  mode: "analysis",
  staticResult: null,
  aiResult: null,
  optimizeResult: null,
  schemaInfo: null,
  error: null,
};

function setMode(mode) {
  state.mode = mode;
  render();
}

function render() {
  const { mode, staticResult, aiResult, optimizeResult, schemaInfo, error } = state;

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.mode === mode);
  });

  const errorEl = document.getElementById("error");
  if (error) {
    errorEl.style.display = "block";
    errorEl.textContent = error;
  } else {
    errorEl.style.display = "none";
  }

  const analysisSection = document.getElementById("analysis-section");
  const optimizationSection = document.getElementById("optimization-section");
  const schemaSection = document.getElementById("schema-section");

  analysisSection.style.display = mode === "analysis" ? "block" : "none";
  optimizationSection.style.display = mode === "optimization" ? "block" : "none";
  schemaSection.style.display = mode === "schema" ? "block" : "none";

  if (mode === "analysis") {
    const staticSummary = document.getElementById("static-summary");
    const staticIssues = document.getElementById("static-issues");
    const staticRecs = document.getElementById("static-recommendations");

    staticSummary.textContent = staticResult?.summary || "No static summary.";
    staticIssues.innerHTML = "";
    (staticResult?.issues || []).forEach((issue) => {
      const li = document.createElement("li");
      li.textContent = issue;
      staticIssues.appendChild(li);
    });
    staticRecs.innerHTML = "";
    (staticResult?.recommendations || []).forEach((rec) => {
      const li = document.createElement("li");
      li.textContent = rec;
      staticRecs.appendChild(li);
    });

    const aiSummary = document.getElementById("ai-summary");
    const aiIssues = document.getElementById("ai-issues");
    const aiRecs = document.getElementById("ai-recommendations");
    const aiExplanation = document.getElementById("ai-explanation");

    aiSummary.textContent = aiResult?.summary || "No AI summary.";
    aiIssues.innerHTML = "";
    (aiResult?.issues || []).forEach((issue) => {
      const li = document.createElement("li");
      li.textContent = issue;
      aiIssues.appendChild(li);
    });
    aiRecs.innerHTML = "";
    (aiResult?.recommendations || []).forEach((rec) => {
      const li = document.createElement("li");
      li.textContent = rec;
      aiRecs.appendChild(li);
    });
    aiExplanation.textContent =
      aiResult?.llm_explanation || "No AI explanation.";
  }

  if (mode === "optimization") {
    document.getElementById("optimized-sql").textContent =
      optimizeResult?.optimized_sql || "No optimized SQL.";
    document.getElementById("optimization-explanation").textContent =
      optimizeResult?.explanation || "No explanation.";
    document.getElementById("optimization-effect").textContent =
      optimizeResult?.expected_effect || "No effect description.";
  }

  if (mode === "schema") {
    document.getElementById("schema-dbtype").textContent =
      "DB Type: " + (schemaInfo?.dbType || "unknown");

    const tablesEl = document.getElementById("schema-tables");
    tablesEl.innerHTML = "";
    (schemaInfo?.tables || []).forEach((table) => {
      const div = document.createElement("div");
      div.style.marginBottom = "8px";

      const title = document.createElement("div");
      title.textContent = `Table: ${table.name}`;
      div.appendChild(title);

      const ul = document.createElement("ul");
      (table.columns || []).forEach((col) => {
        const li = document.createElement("li");
        const flags = [];
        if (col.isPrimaryKey) flags.push("PK");
        if (col.isIndexed) flags.push("IDX");
        li.textContent = `${col.name} (${col.type})${
          flags.length ? " [" + flags.join(", ") + "]" : ""
        }`;
        ul.appendChild(li);
      });
      div.appendChild(ul);

      tablesEl.appendChild(div);
    });
  }
}

window.addEventListener("message", (event) => {
  const message = event.data;
  if (message.command === "updateState") {
    state = { ...state, ...message.state };
    render();
  }
});

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    setMode(tab.dataset.mode);
  });
});

document.getElementById("apply-optimized").addEventListener("click", () => {
  if (!state.optimizeResult?.optimized_sql) return;
  vscode.postMessage({
    command: "applyOptimizedQuery",
    text: state.optimizeResult.optimized_sql,
  });
});

document.getElementById("copy-optimized").addEventListener("click", async () => {
  if (!state.optimizeResult?.optimized_sql) return;
  try {
    await navigator.clipboard.writeText(state.optimizeResult.optimized_sql);
  } catch (e) {
    // может не работать в WebView, но пробуем
  }
});

render();
