const apiBase = "http://127.0.0.1:8010";

let competitors = [
  {
    title: "便携式榨汁杯 适合奶昔和果汁",
    bullet_points: ["可充电强劲电机", "旅行场景清洗方便"],
    keywords: ["便携式榨汁杯", "奶昔机", "USB 充电"],
    price: "¥169",
    rating: 4.5,
    review_summary: "用户喜欢便携性和容易清洗。"
  }
];

const form = document.querySelector("#listingForm");
const csvInput = document.querySelector("#csvInput");
const statusText = document.querySelector("#statusText");
const resultPanel = document.querySelector("#resultPanel");
const competitorRows = document.querySelector("#competitorRows");
const payloadPreview = document.querySelector("#payloadPreview");
const globalLanguage = document.querySelector("#global_language");
const targetLanguage = document.querySelector("#target_language");
const historyList = document.querySelector("#historyList");
const refreshHistoryButton = document.querySelector("#refreshHistoryButton");
const clearHistoryButton = document.querySelector("#clearHistoryButton");

let activeHistoryId = null;
let currentResult = null;

const defaultValuesByLanguage = {
  Chinese: {
    name: "便携式电动榨汁杯",
    category: "个人榨汁机",
    material: "食品级 BPA-free 塑料",
    size: "380ml",
    price_range: "¥129-¥199",
    brand_tone: "实用、可靠、有品质感",
    selling_points: "USB 充电，容易清洗，便携杯身设计",
    use_cases: "早餐奶昔，办公室，旅行"
  },
  English: {
    name: "Portable Electric Blender",
    category: "personal blender",
    material: "BPA-free plastic",
    size: "380ml",
    price_range: "$19-$29",
    brand_tone: "modern and reliable",
    selling_points: "USB rechargeable, easy to clean, compact bottle design",
    use_cases: "smoothies, travel, office"
  },
  Japanese: {
    name: "ポータブル電動ブレンダー",
    category: "個人用ブレンダー",
    material: "BPA フリー樹脂",
    size: "380ml",
    price_range: "¥2,900-¥4,500",
    brand_tone: "実用的で信頼感がある",
    selling_points: "USB 充電，洗いやすい，持ち運びやすいボトル設計",
    use_cases: "朝食スムージー，オフィス，旅行"
  },
  German: {
    name: "Tragbarer elektrischer Mixer",
    category: "Personal Blender",
    material: "BPA-freier Kunststoff",
    size: "380ml",
    price_range: "19-29 EUR",
    brand_tone: "praktisch und zuverlässig",
    selling_points: "USB-aufladbar, leicht zu reinigen, kompaktes Flaschendesign",
    use_cases: "Smoothies, Reisen, Büro"
  },
  Spanish: {
    name: "Licuadora electrica portatil",
    category: "licuadora personal",
    material: "plastico libre de BPA",
    size: "380ml",
    price_range: "19-29 EUR",
    brand_tone: "practica y confiable",
    selling_points: "recargable por USB, facil de limpiar, diseno compacto",
    use_cases: "batidos, viajes, oficina"
  }
};

form.addEventListener("submit", (event) => {
  event.preventDefault();
  generateListing();
});

csvInput.addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const text = await file.text();
  competitors = parseCompetitorCsv(text);
  renderCompetitors();
  updatePayloadPreview();
  statusText.textContent = `已导入 ${competitors.length} 条竞品数据。`;
});

globalLanguage.addEventListener("change", () => {
  targetLanguage.value = globalLanguage.value;
  applyLanguageDefaults(globalLanguage.value);
  updatePayloadPreview();
  statusText.textContent = `已切换生成语言：${globalLanguage.selectedOptions[0].textContent}`;
});

targetLanguage.addEventListener("change", () => {
  globalLanguage.value = targetLanguage.value;
  updatePayloadPreview();
});

refreshHistoryButton.addEventListener("click", loadHistory);
clearHistoryButton.addEventListener("click", clearHistory);

document.querySelectorAll("input, select, textarea").forEach((element) => {
  element.addEventListener("input", updatePayloadPreview);
  element.addEventListener("change", updatePayloadPreview);
});

renderCompetitors();
applyLanguageDefaults("Chinese");
updatePayloadPreview();
loadHistory();

function applyLanguageDefaults(language) {
  const values = defaultValuesByLanguage[language] || defaultValuesByLanguage.Chinese;
  for (const [id, value] of Object.entries(values)) {
    const field = document.querySelector(`#${id}`);
    if (field) field.value = value;
  }
}

async function generateListing() {
  statusText.textContent = "正在生成 Listing...";
  try {
    const payload = buildPayload();
    const response = await fetch(`${apiBase}/api/listings/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || error.error || `HTTP ${response.status}`);
    }
    const data = await response.json();
    statusText.textContent = `生成成功，已保存历史记录 #${data.id}`;
    activeHistoryId = data.id;
    renderResult(data);
    loadHistory();
  } catch (error) {
    statusText.textContent = error.message || "生成失败，请检查后端服务是否启动。";
  }
}

function buildPayload() {
  return {
    product: {
      name: valueOf("name"),
      category: valueOf("category"),
      target_market: valueOf("target_market"),
      target_language: valueOf("target_language"),
      selling_points: splitList(valueOf("selling_points")),
      material: valueOf("material"),
      size: valueOf("size"),
      use_cases: splitList(valueOf("use_cases")),
      price_range: valueOf("price_range"),
      brand_tone: valueOf("brand_tone")
    },
    competitors
  };
}

function valueOf(id) {
  return document.querySelector(`#${id}`).value.trim();
}

function splitList(value) {
  return value
    .split(/[,，\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function updatePayloadPreview() {
  payloadPreview.textContent = JSON.stringify(buildPayload(), null, 2);
}

async function loadHistory() {
  try {
    const response = await fetch(`${apiBase}/api/listings`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const records = await response.json();
    renderHistory(records);
  } catch (error) {
    historyList.innerHTML = `<p class="historyEmpty">历史记录加载失败：${escapeHtml(error.message || "请检查后端服务")}</p>`;
  }
}

async function clearHistory() {
  const confirmed = window.confirm("确定清空所有历史生成记录吗？这个操作只会清理本地 SQLite 历史，不会影响代码。");
  if (!confirmed) return;
  try {
    const response = await fetch(`${apiBase}/api/listings`, { method: "DELETE" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const result = await response.json();
    activeHistoryId = null;
    resultPanel.innerHTML = `
      <div class="emptyState">
        <h2>历史记录已清空</h2>
        <p>重新生成一次 Listing 后，新的记录会显示在下方。</p>
      </div>
    `;
    statusText.textContent = `已清空 ${result.deleted} 条历史记录。`;
    loadHistory();
  } catch (error) {
    statusText.textContent = error.message || "清空历史失败，请检查后端服务。";
  }
}

function renderHistory(records) {
  if (!records.length) {
    historyList.innerHTML = `<p class="historyEmpty">暂无历史记录，生成一次 Listing 后会显示在这里。</p>`;
    return;
  }
  historyList.innerHTML = records.map(renderHistoryItem).join("");
  historyList.querySelectorAll("[data-history-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const id = Number(button.dataset.historyId);
      const record = records.find((item) => item.id === id);
      if (!record) return;
      activeHistoryId = id;
      renderResult(record.response);
      renderHistory(records);
      statusText.textContent = `已加载历史记录 #${id}，可在右侧复盘。`;
      resultPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
}

function renderHistoryItem(record) {
  const response = record.response || {};
  const versions = response.versions || [];
  const bestVersion = versions.length ? [...versions].sort((a, b) => b.score - a.score)[0] : null;
  const sourceText = response.generation_source === "llm"
    ? `大模型：${response.generation_provider || "deepseek"}`
    : "本地回退";
  const activeClass = record.id === activeHistoryId ? " active" : "";
  return `
    <button type="button" class="historyItem${activeClass}" data-history-id="${record.id}">
      <span class="historyTitle">${escapeHtml(record.product_name || "未命名商品")}</span>
      <span class="historyMeta">
        ${escapeHtml(record.target_market || "-")} · ${escapeHtml(record.target_language || "-")} · ${escapeHtml(sourceText)}
      </span>
      <span class="historyMeta">
        推荐版本 ${escapeHtml(bestVersion?.version || "-")} · 最高分 ${escapeHtml(bestVersion?.score ?? "-")} · ${formatDate(record.created_at)}
      </span>
    </button>
  `;
}

function parseCompetitorCsv(text) {
  const rows = parseCsvRows(text).filter((row) => row.some(Boolean));
  if (rows.length < 2) return [];
  const headers = rows[0].map((header) => header.trim());
  return rows.slice(1).map((row) => {
    const record = Object.fromEntries(headers.map((header, index) => [header, row[index] || ""]));
    return {
      title: record.title || "",
      bullet_points: splitSemicolonList(record.bullet_points || ""),
      keywords: splitSemicolonList(record.keywords || ""),
      price: record.price || "",
      rating: record.rating ? Number(record.rating) : null,
      review_summary: record.review_summary || ""
    };
  });
}

function splitSemicolonList(value) {
  return value
    .split(/[;；]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseCsvRows(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let inQuotes = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];
    if (char === '"' && inQuotes && next === '"') {
      cell += '"';
      index += 1;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === "," && !inQuotes) {
      row.push(cell.trim());
      cell = "";
    } else if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && next === "\n") index += 1;
      row.push(cell.trim());
      rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }

  row.push(cell.trim());
  rows.push(row);
  return rows;
}

function renderCompetitors() {
  competitorRows.innerHTML = competitors
    .map(
      (competitor) => `
        <tr>
          <td>${escapeHtml(competitor.title)}</td>
          <td>${escapeHtml(competitor.keywords.join(", "))}</td>
          <td>${escapeHtml(competitor.price)}</td>
          <td>${escapeHtml(competitor.rating ?? "-")}</td>
        </tr>
      `
    )
    .join("");
}

function renderResult(data) {
  currentResult = data;
  const bestVersion = [...data.versions].sort((a, b) => b.score - a.score)[0];
  const provider = data.generation_provider || "deepseek";
  const sourceText = data.generation_source === "llm" ? `大模型生成：${provider}` : "本地规则回退";
  resultPanel.innerHTML = `
    <div class="insights">
      <div>
        <h2>竞品分析</h2>
        <p class="bestVersion">推荐版本：${escapeHtml(bestVersion.version)} · ${sourceText}</p>
      </div>
      ${data.competitor_insights.map((item) => `<p>${escapeHtml(item)}</p>`).join("")}
    </div>
    <div class="refineActions">
      <button type="button" data-refine="seo">更偏 SEO</button>
      <button type="button" data-refine="conversion">更偏转化</button>
      <button type="button" data-refine="concise">更简洁</button>
      <button type="button" data-refine="localization">更本地化</button>
    </div>
    <div class="versions">
      ${data.versions.map(renderVersion).join("")}
    </div>
    <div class="recommendation">${escapeHtml(data.recommendation)}</div>
  `;
  resultPanel.querySelectorAll("[data-refine]").forEach((button) => {
    button.addEventListener("click", () => refineCurrentResult(button.dataset.refine));
  });
}

async function refineCurrentResult(direction) {
  if (!currentResult) {
    statusText.textContent = "请先生成或加载一条历史记录，再进行二次优化。";
    return;
  }
  statusText.textContent = `正在进行二次优化：${directionLabel(direction)}...`;
  try {
    const payload = {
      ...buildPayload(),
      direction,
      previous_response: currentResult
    };
    const response = await fetch(`${apiBase}/api/listings/refine`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || error.error || `HTTP ${response.status}`);
    }
    const data = await response.json();
    activeHistoryId = data.id;
    renderResult(data);
    loadHistory();
    statusText.textContent = `二次优化完成，已保存历史记录 #${data.id}`;
  } catch (error) {
    statusText.textContent = error.message || "二次优化失败，请检查后端服务。";
  }
}

function renderVersion(version) {
  return `
    <article class="versionCard">
      <div class="versionHeader">
        <h3>版本 ${escapeHtml(version.version)}</h3>
        <strong>${version.score}</strong>
      </div>
      <h4>${escapeHtml(version.title)}</h4>
      <ul>
        ${version.bullet_points.map((bullet) => `<li>${escapeHtml(bullet)}</li>`).join("")}
      </ul>
      <div class="keywords">
        ${version.seo_keywords.map((keyword) => `<span>${escapeHtml(keyword)}</span>`).join("")}
      </div>
      ${renderScoreBreakdown(version.score_breakdown)}
      <p class="adCopy">${escapeHtml(version.ad_copy)}</p>
      <details class="reasons">
        <summary>查看优化理由</summary>
        <ul>
          ${version.optimization_reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}
        </ul>
      </details>
    </article>
  `;
}

function renderScoreBreakdown(scoreBreakdown = {}) {
  const labels = {
    title_completeness: "标题完整度",
    keyword_coverage: "关键词覆盖",
    benefit_clarity: "卖点清晰度",
    localization_quality: "本地化质量",
    ad_conversion_potential: "广告转化潜力"
  };
  return `
    <div class="scoreGrid">
      ${Object.entries(labels)
        .map(([key, label]) => {
          const score = Number(scoreBreakdown[key] ?? 0);
          return `
            <div class="scoreItem">
              <span>${label}</span>
              <strong>${score}</strong>
              <meter min="0" max="100" value="${score}"></meter>
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

function directionLabel(direction) {
  const labels = {
    seo: "更偏 SEO",
    conversion: "更偏转化",
    concise: "更简洁",
    localization: "更本地化"
  };
  return labels[direction] || direction;
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value.replace(" ", "T"));
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
