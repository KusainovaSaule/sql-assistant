const vscode = acquireVsCodeApi();

let state = {
  mode: "analysis",
  staticResult: null,
  aiResult: null,
  optimizeResult: null,
  schemaInfo: null,
  historyResult: null,
  error: null,
};

function setMode(mode) {
  state.mode = mode;
  render();
}

function render() {
  const { mode, staticResult, aiResult, optimizeResult, schemaInfo, historyResult, error } = state;

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.mode === mode);
  });

  const errorEl = document.getElementById("error");
  if (errorEl) {
    if (error) {
      errorEl.style.display = "block";
      errorEl.textContent = error;
    } else {
      errorEl.style.display = "none";
    }
  }

  const analysisSection = document.getElementById("analysis-section");
  const optimizationSection = document.getElementById("optimization-section");
  const schemaSection = document.getElementById("schema-section");
  const historySection = document.getElementById("history-section");

  if (analysisSection) analysisSection.style.display = mode === "analysis" ? "block" : "none";
  if (optimizationSection) optimizationSection.style.display = mode === "optimization" ? "block" : "none";
  if (schemaSection) schemaSection.style.display = mode === "schema" ? "block" : "none";
  if (historySection) historySection.style.display = mode === "history" ? "block" : "none";

  if (mode === "analysis") {
    const staticSummary = document.getElementById("static-summary");
    const staticIssues = document.getElementById("static-issues");
    const staticRecs = document.getElementById("static-recommendations");

    if (staticSummary) {
      if (staticResult && staticResult.problems) {
        staticSummary.textContent = `Найдено проблем: ${staticResult.problems.length}`;
        if (staticIssues) {
          staticIssues.innerHTML = "";
          staticResult.problems.forEach((problem) => {
            const li = document.createElement("li");
            const severityColor = problem.severity === 'ERROR' ? '#ff6b6b' : '#ffa94d';
            li.innerHTML = `<strong>${problem.code}</strong>: ${problem.message} <span style="color: ${severityColor}">(${problem.severity})</span>`;
            if (problem.recommendation) {
              const small = document.createElement("small");
              small.textContent = `→ ${problem.recommendation}`;
              li.appendChild(small);
            }
            staticIssues.appendChild(li);
          });
        }
      } else {
        staticSummary.textContent = "✅ Статический анализ выполнен, проблем не найдено.";
        if (staticIssues) staticIssues.innerHTML = "";
      }
    }
    if (staticRecs) staticRecs.innerHTML = "";

    const aiSummary = document.getElementById("ai-summary");
    const aiIssues = document.getElementById("ai-issues");
    const aiRecs = document.getElementById("ai-recommendations");

    if (aiSummary) {
      if (aiResult) {
        aiSummary.textContent = aiResult.logic_description || "Описание логики отсутствует.";
        
        if (aiIssues) {
          aiIssues.innerHTML = "";
          (aiResult.problems || []).forEach((problem) => {
            const li = document.createElement("li");
            const severityColor = problem.severity === 'ERROR' ? '#ff6b6b' : '#ffa94d';
            li.innerHTML = `<strong>${problem.code || 'ISSUE'}</strong>: ${problem.message} <span style="color: ${severityColor}">(${problem.severity || 'WARNING'})</span>`;
            if (problem.recommendation) {
              const small = document.createElement("small");
              small.textContent = `→ ${problem.recommendation}`;
              li.appendChild(small);
            }
            aiIssues.appendChild(li);
          });
        }

        if (aiRecs) {
          aiRecs.innerHTML = "";
          (aiResult.recommendations || []).forEach((rec) => {
            const li = document.createElement("li");
            li.textContent = rec;
            aiRecs.appendChild(li);
          });
        }
      } else {
        aiSummary.textContent = "⏳ AI анализ не выполнен или данные не получены.";
        if (aiIssues) aiIssues.innerHTML = "";
        if (aiRecs) aiRecs.innerHTML = "";
      }
    }
  }

  if (mode === "optimization") {
    const optimizedSql = document.getElementById("optimized-sql");
    const explanation = document.getElementById("optimization-explanation");
    const effect = document.getElementById("optimization-effect");

    if (optimizeResult) {
      if (optimizedSql) optimizedSql.textContent = optimizeResult.optimized_sql || "Нет оптимизированного SQL.";
      if (explanation) explanation.textContent = optimizeResult.explanation || "Нет объяснения.";
      if (effect) effect.textContent = optimizeResult.expected_effect || "Нет описания эффекта.";
    } else {
      if (optimizedSql) optimizedSql.textContent = "⏳ Оптимизация не выполнена.";
      if (explanation) explanation.textContent = "";
      if (effect) effect.textContent = "";
    }
  }

  if (mode === "schema") {
    const dbType = document.getElementById("schema-dbtype");
    const tablesEl = document.getElementById("schema-tables");

    if (dbType) dbType.textContent = "DB Type: " + (schemaInfo?.dbType || "unknown");

    if (tablesEl) {
      tablesEl.innerHTML = "";
      if (schemaInfo?.tables && schemaInfo.tables.length > 0) {
        schemaInfo.tables.forEach((table) => {
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
            li.textContent = `${col.name} (${col.type})${flags.length ? " [" + flags.join(", ") + "]" : ""}`;
            ul.appendChild(li);
          });
          div.appendChild(ul);
          tablesEl.appendChild(div);
        });
      } else {
        tablesEl.innerHTML = "Нет данных о схеме.";
      }
    }
  }

  if (mode === "history") {
    const historyList = document.getElementById("history-list");
    if (historyList) {
      historyList.innerHTML = "";
      if (historyResult?.history && historyResult.history.length > 0) {
        historyResult.history.forEach((item) => {
          const div = document.createElement("div");
          div.className = "history-item";
          const timestamp = item.created_at ? new Date(item.created_at * 1000).toLocaleString() : 'неизвестно';
          div.innerHTML = `
            <div><strong>${item.operation || 'unknown'}</strong> at ${timestamp}</div>
            <div style="font-size: 12px; color: #888;">${item.sql ? item.sql.substring(0, 100) : ''}${item.sql && item.sql.length > 100 ? '...' : ''}</div>
          `;
          historyList.appendChild(div);
        });
      } else {
        historyList.innerHTML = "Нет истории.";
      }
    }
    renderHistoryPager(historyResult);
  }
}

function renderHistoryPager(historyResult) {
  const pager = document.getElementById("history-pager");
  if (!pager) return;
  pager.innerHTML = "";
  if (!historyResult || !historyResult.history) return;

  const total = historyResult.total || 0;
  const limit = historyResult.limit || 30;
  const offset = historyResult.offset || 0;
  const count = historyResult.history.length;
  if (total <= limit && offset === 0) return;

  const from = total === 0 ? 0 : offset + 1;
  const to = offset + count;

  const prev = document.createElement("button");
  prev.textContent = "← Назад";
  prev.disabled = offset <= 0;
  prev.onclick = () =>
    vscode.postMessage({ command: "loadHistoryPage", offset: Math.max(0, offset - limit) });

  const info = document.createElement("span");
  info.className = "pager-info";
  info.textContent = `${from}–${to} из ${total}`;

  const next = document.createElement("button");
  next.textContent = "Вперёд →";
  next.disabled = to >= total;
  next.onclick = () =>
    vscode.postMessage({ command: "loadHistoryPage", offset: offset + limit });

  pager.appendChild(prev);
  pager.appendChild(info);
  pager.appendChild(next);
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
    const mode = tab.dataset.mode;
    setMode(mode);
    vscode.postMessage({ command: "runMode", mode });
  });
});

const applyBtn = document.getElementById("apply-optimized");
if (applyBtn) {
  applyBtn.addEventListener("click", () => {
    if (!state.optimizeResult?.optimized_sql) return;
    vscode.postMessage({
      command: "applyOptimizedQuery",
      text: state.optimizeResult.optimized_sql,
    });
  });
}

const copyBtn = document.getElementById("copy-optimized");
if (copyBtn) {
  copyBtn.addEventListener("click", async () => {
    if (!state.optimizeResult?.optimized_sql) return;
    try {
      await navigator.clipboard.writeText(state.optimizeResult.optimized_sql);
    } catch (e) {
      // может не работать
    }
  });
}

render();