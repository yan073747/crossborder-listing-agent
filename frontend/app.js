const demoVersion = "20260716-static-demo";
const stateKey = `crossborder-listing-demo-${demoVersion}`;

const form = document.querySelector("#listingForm");
const csvInput = document.querySelector("#csvInput");
const statusText = document.querySelector("#statusText");
const statusTitle = document.querySelector("#statusTitle");
const resultPanel = document.querySelector("#resultPanel");
const competitorRows = document.querySelector("#competitorRows");
const payloadPreview = document.querySelector("#payloadPreview");
const targetLanguage = document.querySelector("#target_language");
const historyList = document.querySelector("#historyList");
const clearHistoryButton = document.querySelector("#clearHistoryButton");
const loadSampleButton = document.querySelector("#loadSampleButton");
const exportCsvButton = document.querySelector("#exportCsvButton");
const exportExcelButton = document.querySelector("#exportExcelButton");
const marketStat = document.querySelector("#marketStat");
const competitorStat = document.querySelector("#competitorStat");
const historyStat = document.querySelector("#historyStat");

const sampleProduct = {
  name: "Portable Electric Blender",
  category: "personal blender",
  target_market: "United States",
  target_language: "Chinese",
  material: "BPA-free plastic",
  size: "380ml",
  price_range: "$19-$29",
  brand_tone: "modern, reliable, fitness-friendly",
  selling_points: "USB rechargeable, easy to clean, compact bottle design, leak-resistant lid",
  use_cases: "smoothies, travel, office, gym bag"
};

const sampleCompetitors = [
  {
    title: "Portable Blender for Shakes and Smoothies, 14oz USB Rechargeable",
    bullet_points: ["six stainless blades", "easy rinse cup", "travel bottle design"],
    keywords: ["portable blender", "smoothie maker", "USB blender"],
    price: "$24.99",
    rating: 4.5,
    review_summary: "Customers like portability and fast cleanup but mention limited capacity."
  },
  {
    title: "Mini Personal Blender with Travel Lid for Office and Gym",
    bullet_points: ["one-button blend", "compact cup", "BPA-free material"],
    keywords: ["mini blender", "personal blender", "protein shake mixer"],
    price: "$21.99",
    rating: 4.3,
    review_summary: "Positive feedback on size and convenience; some users want stronger power."
  },
  {
    title: "Cordless Smoothie Blender, Rechargeable Juicer Cup for Travel",
    bullet_points: ["cordless charging", "leak-proof lid", "fruit juice on the go"],
    keywords: ["cordless blender", "juicer cup", "travel smoothie blender"],
    price: "$27.99",
    rating: 4.4,
    review_summary: "Buyers mention strong portability and clean design, with mixed notes on ice crushing."
  }
];

let competitors = structuredClone(sampleCompetitors);
let history = loadHistory();
let currentResult = history[0]?.response || null;
let activeHistoryId = history[0]?.id || null;

const languageDefaults = {
  Chinese: {
    target_market: "United States",
    name: "Portable Electric Blender",
    category: "个人便携榨汁杯",
    material: "食品级 BPA-free 塑料",
    size: "380ml",
    price_range: "$19-$29",
    brand_tone: "实用、可靠、有品质感",
    selling_points: "USB 充电，容易清洗，便携杯身设计，防漏杯盖",
    use_cases: "早餐奶昔，办公室，旅行，健身包"
  },
  English: sampleProduct,
  Japanese: {
    target_market: "Japan",
    name: "Portable Electric Blender",
    category: "携帯型パーソナルブレンダー",
    material: "BPA フリー食品グレード樹脂",
    size: "380ml",
    price_range: "JPY 2,900-4,500",
    brand_tone: "実用的で信頼感のある",
    selling_points: "USB 充電，洗いやすい，持ち運びやすいボトル設計，漏れにくいフタ",
    use_cases: "朝食スムージー，オフィス，旅行，ジムバッグ"
  },
  German: {
    target_market: "Germany",
    name: "Portable Electric Blender",
    category: "tragbarer Personal Blender",
    material: "BPA-freier lebensmittelechter Kunststoff",
    size: "380ml",
    price_range: "19-29 EUR",
    brand_tone: "praktisch, zuverlassig und modern",
    selling_points: "USB-aufladbar, leicht zu reinigen, kompaktes Flaschendesign, auslaufsicherer Deckel",
    use_cases: "Smoothies, Reisen, Buro, Sporttasche"
  },
  Spanish: {
    target_market: "Spain",
    name: "Portable Electric Blender",
    category: "licuadora personal portatil",
    material: "plastico alimentario libre de BPA",
    size: "380ml",
    price_range: "19-29 EUR",
    brand_tone: "practica, confiable y moderna",
    selling_points: "recargable por USB, facil de limpiar, diseno compacto, tapa antifugas",
    use_cases: "batidos, viajes, oficina, bolsa de gimnasio"
  }
};

form.addEventListener("submit", (event) => {
  event.preventDefault();
  generateListing("initial");
});

csvInput.addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const text = await file.text();
  competitors = parseCompetitorCsv(text);
  setStatus(`已导入 ${competitors.length} 条竞品数据。`, "数据已更新");
  renderCompetitors();
  updatePayloadPreview();
});

targetLanguage.addEventListener("change", () => {
  applyLanguageDefaults(targetLanguage.value);
  setStatus(`已切换输出语言：${targetLanguage.selectedOptions[0].textContent}`, "语言已切换");
});

document.querySelectorAll("input, select, textarea").forEach((element) => {
  element.addEventListener("input", updatePayloadPreview);
  element.addEventListener("change", updatePayloadPreview);
});

loadSampleButton.addEventListener("click", () => {
  competitors = structuredClone(sampleCompetitors);
  applyLanguageDefaults(targetLanguage.value || "Chinese");
  renderCompetitors();
  updatePayloadPreview();
  setStatus("已恢复安全样例数据。", "样例已载入");
});

clearHistoryButton.addEventListener("click", () => {
  history = [];
  currentResult = null;
  activeHistoryId = null;
  saveHistory();
  renderHistory();
  renderStats();
  resultPanel.innerHTML = `
    <div class="empty-state">
      <p class="section-kicker">03 / Generation Result</p>
      <h2>历史已清空</h2>
      <p>重新生成一次 Listing 后，新的记录会显示在这里。</p>
    </div>
  `;
  setStatus("历史记录已清空。", "已清空");
});

exportCsvButton.addEventListener("click", exportHistoryCsv);
exportExcelButton.addEventListener("click", exportHistoryExcel);

renderCompetitors();
applyLanguageDefaults("Chinese");
renderHistory();
renderStats();
if (currentResult) renderResult(currentResult);

function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(stateKey) || "[]");
  } catch {
    return [];
  }
}

function saveHistory() {
  localStorage.setItem(stateKey, JSON.stringify(history));
}

function setStatus(message, title = "演示就绪") {
  statusText.textContent = message;
  statusTitle.textContent = title;
}

function applyLanguageDefaults(language) {
  const values = languageDefaults[language] || languageDefaults.Chinese;
  for (const [id, value] of Object.entries(values)) {
    const field = document.querySelector(`#${id}`);
    if (field) field.value = value;
  }
  targetLanguage.value = language;
  renderStats();
  updatePayloadPreview();
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

function generateListing(direction = "initial") {
  const payload = buildPayload();
  const response = createListingResponse(payload, direction);
  const record = {
    id: Date.now(),
    created_at: new Date().toISOString(),
    product_name: payload.product.name,
    target_market: payload.product.target_market,
    target_language: payload.product.target_language,
    response
  };

  history = [record, ...history].slice(0, 12);
  currentResult = response;
  activeHistoryId = record.id;
  saveHistory();
  renderResult(response);
  renderHistory();
  renderStats();
  setStatus(`已生成 ${response.versions.length} 个 Listing 版本，并保存到浏览器本地历史。`, "生成完成");
}

function createListingResponse(payload, direction) {
  const product = payload.product;
  const competitorSignals = analyzeCompetitors(payload.competitors);
  const language = product.target_language;
  const versionA = buildVersion("A", product, competitorSignals, direction, language);
  const versionB = buildVersion("B", product, competitorSignals, direction, language);
  const versions = [versionA, versionB].map(scoreVersion);
  const best = [...versions].sort((a, b) => b.score - a.score)[0];

  return {
    generation_source: "local_static_demo",
    generation_provider: "rule-based mock",
    competitor_insights: [
      `竞品高频关键词集中在：${competitorSignals.keywords.slice(0, 6).join("、")}。`,
      `价格带主要落在 ${competitorSignals.priceRange}，当前商品 ${product.price_range} 适合强调性价比和便携场景。`,
      `评论信号显示用户最关注 ${competitorSignals.reviewThemes.join("、")}，Listing 需要把这些利益点前置。`
    ],
    versions,
    recommendation: `建议优先上线版本 ${best.version}：它在关键词覆盖、本地化表达和广告转化潜力上更平衡，适合先作为主 Listing，再用另一个版本做广告素材或 A/B 测试。`,
    direction
  };
}

function analyzeCompetitors(items) {
  const keywordCounts = new Map();
  const ratings = [];
  const prices = [];
  const reviewText = [];

  items.forEach((item) => {
    item.keywords.forEach((keyword) => {
      const key = keyword.trim();
      if (key) keywordCounts.set(key, (keywordCounts.get(key) || 0) + 1);
    });
    if (Number.isFinite(Number(item.rating))) ratings.push(Number(item.rating));
    const numericPrice = Number(String(item.price).replace(/[^\d.]/g, ""));
    if (numericPrice) prices.push(numericPrice);
    if (item.review_summary) reviewText.push(item.review_summary.toLowerCase());
  });

  const keywords = [...keywordCounts.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([keyword]) => keyword);

  const minPrice = prices.length ? Math.min(...prices) : 19;
  const maxPrice = prices.length ? Math.max(...prices) : 29;
  const themes = [
    reviewText.join(" ").includes("clean") || reviewText.join(" ").includes("清洗") ? "易清洁" : "便携性",
    reviewText.join(" ").includes("power") || reviewText.join(" ").includes("ice") ? "动力表现" : "日常使用",
    reviewText.join(" ").includes("travel") || reviewText.join(" ").includes("office") ? "通勤/旅行场景" : "健康饮品场景"
  ];

  return {
    keywords,
    priceRange: `$${minPrice.toFixed(0)}-$${maxPrice.toFixed(0)}`,
    averageRating: ratings.length ? ratings.reduce((sum, item) => sum + item, 0) / ratings.length : 4.4,
    reviewThemes: [...new Set(themes)]
  };
}

function buildVersion(version, product, signals, direction, language) {
  const points = product.selling_points;
  const useCases = product.use_cases;
  const keywords = [...new Set([...signals.keywords, product.category, ...useCases])].slice(0, 8);
  const tone = direction === "conversion" ? "high-intent" : direction === "seo" ? "keyword-rich" : product.brand_tone;

  if (version === "A") {
    return localizeVersion(
      {
        version,
        title: `${product.name} for ${useCases.slice(0, 2).join(" and ")} - ${product.size} ${product.category}`,
        bullet_points: [
          `Built for ${useCases.join(", ")} with a compact ${product.size} bottle design.`,
          `${points[0] || "USB rechargeable"} so shoppers can use it at home, office, gym or travel.`,
          `${points[1] || "Easy to clean"} design reduces daily maintenance friction.`,
          `${product.material} material supports a safer everyday drink routine.`,
          `Positioned at ${product.price_range} with clear value against similar competitors.`
        ],
        seo_keywords: keywords,
        ad_copy: `Blend fresh drinks anywhere. A compact ${product.category} for busy mornings, workouts and travel.`,
        optimization_reasons: [
          "标题前置品类词和核心场景，适合自然搜索。",
          "卖点围绕便携、清洁、材质和价格带展开。",
          `语气保持 ${tone}，便于运营团队直接复用。`
        ]
      },
      language
    );
  }

  return localizeVersion(
    {
      version,
      title: `${product.size} Portable Blender, USB Rechargeable Smoothie Cup for Travel, Office and Gym`,
      bullet_points: [
        `Create smoothies, shakes and fresh juice in daily ${useCases.slice(0, 3).join(", ")} scenes.`,
        `USB rechargeable body supports flexible use without a kitchen setup.`,
        `Compact cup shape and leak-resistant lid make it easier to carry in a work bag.`,
        `Easy-rinse structure helps users clean quickly after fruit, protein or juice blends.`,
        `Modern look and ${product.material} build match a reliable wellness product positioning.`
      ],
      seo_keywords: keywords,
      ad_copy: `No bulky blender. No messy cleanup. Just fresh smoothies wherever the day starts.`,
      optimization_reasons: [
        "版本 B 更偏转化表达，直接放大无负担、易携带、易清洁。",
        "广告文案更适合短视频或站内广告素材。",
        "标题覆盖 portable blender、USB rechargeable、smoothie cup 等高意图词。"
      ]
    },
    language
  );
}

function localizeVersion(version, language) {
  if (language === "Chinese") {
    return {
      ...version,
      title: version.version === "A"
        ? "便携式电动榨汁杯 380ml - 适合早餐奶昔、办公室和旅行"
        : "USB 充电便携榨汁杯，防漏随行杯设计，适合健身、通勤和旅行",
      bullet_points: version.bullet_points.map((_, index) => [
        "380ml 便携杯身设计，适合早餐奶昔、办公室饮品、旅行和健身包随身携带。",
        "USB 充电模式减少厨房设备限制，日常通勤和户外场景也能快速制作饮品。",
        "易清洗结构降低使用后的维护成本，适合高频使用的健康生活人群。",
        "食品级 BPA-free 材质，强化安全感和家庭日常使用信任。",
        "对比同类竞品价格带，强调便携、清洁和性价比，适合主图卖点和广告文案复用。"
      ][index]),
      ad_copy: version.version === "A"
        ? "把新鲜奶昔带到办公室、健身房和旅途中。小巧杯身，随时开榨。"
        : "不用笨重料理机，也不用复杂清洗。每天一杯新鲜果昔，从随身杯开始。"
    };
  }

  if (language === "Japanese") {
    return {
      ...version,
      title: "USB充電式ポータブルブレンダー 380ml - オフィス、旅行、ジム向け",
      ad_copy: "忙しい朝でも、外出先でも、手軽にスムージーを楽しめる携帯型ブレンダー。"
    };
  }

  if (language === "German") {
    return {
      ...version,
      title: "Tragbarer USB Mixer 380ml - Smoothie Cup fur Reisen, Buro und Fitness",
      ad_copy: "Frische Smoothies ohne sperrige Kuchema Maschine - kompakt, aufladbar und schnell gereinigt."
    };
  }

  if (language === "Spanish") {
    return {
      ...version,
      title: "Licuadora Portatil USB 380ml - vaso para batidos, viajes, oficina y gimnasio",
      ad_copy: "Prepara batidos frescos sin una licuadora grande: compacta, recargable y facil de limpiar."
    };
  }

  return version;
}

function scoreVersion(version) {
  const titleCompleteness = Math.min(96, 78 + Math.round(version.title.length / 7));
  const keywordCoverage = Math.min(98, 70 + version.seo_keywords.length * 3);
  const benefitClarity = version.bullet_points.filter((item) => /easy|clean|便携|清洗|travel|office|gym|安全|value/i.test(item)).length * 13 + 25;
  const localizationQuality = /[一-龥]|Japanese|German|Spanish|USB|portable/i.test(version.title) ? 88 : 82;
  const adConversion = version.ad_copy.length > 60 ? 91 : 84;
  const scoreBreakdown = {
    title_completeness: clamp(titleCompleteness, 0, 100),
    keyword_coverage: clamp(keywordCoverage, 0, 100),
    benefit_clarity: clamp(benefitClarity, 0, 100),
    localization_quality: clamp(localizationQuality, 0, 100),
    ad_conversion_potential: clamp(adConversion, 0, 100)
  };
  const score = Math.round(Object.values(scoreBreakdown).reduce((sum, item) => sum + item, 0) / 5);
  return { ...version, score, score_breakdown: scoreBreakdown };
}

function renderResult(data) {
  currentResult = data;
  const bestVersion = [...data.versions].sort((a, b) => b.score - a.score)[0];
  resultPanel.innerHTML = `
    <div class="result-head">
      <div>
        <p class="section-kicker">03 / Generation Result</p>
        <h2>Listing 生成结果</h2>
      </div>
      <span class="source-pill">本地规则演示 / 无需 API Key</span>
    </div>
    <div class="insights">
      <strong>推荐版本 ${escapeHtml(bestVersion.version)} · ${bestVersion.score} 分</strong>
      ${data.competitor_insights.map((item) => `<p>${escapeHtml(item)}</p>`).join("")}
    </div>
    <div class="refine-actions">
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
    button.addEventListener("click", () => generateListing(button.dataset.refine));
  });
}

function renderVersion(version) {
  return `
    <article class="version-card">
      <div class="version-header">
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
      <p class="ad-copy">${escapeHtml(version.ad_copy)}</p>
      <details>
        <summary>查看优化理由</summary>
        <ul>${version.optimization_reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}</ul>
      </details>
    </article>
  `;
}

function renderScoreBreakdown(scoreBreakdown) {
  const labels = {
    title_completeness: "标题完整度",
    keyword_coverage: "关键词覆盖",
    benefit_clarity: "卖点清晰度",
    localization_quality: "本地化质量",
    ad_conversion_potential: "广告转化潜力"
  };
  return `
    <div class="score-grid">
      ${Object.entries(labels)
        .map(([key, label]) => {
          const score = Number(scoreBreakdown[key] || 0);
          return `
            <div class="score-item">
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
  renderStats();
}

function renderHistory() {
  if (!history.length) {
    historyList.innerHTML = '<p class="empty-history">暂无历史记录。生成一次 Listing 后会显示在这里。</p>';
    return;
  }
  historyList.innerHTML = history
    .map((record) => {
      const best = [...record.response.versions].sort((a, b) => b.score - a.score)[0];
      return `
        <button class="history-item ${record.id === activeHistoryId ? "active" : ""}" type="button" data-history-id="${record.id}">
          <span>${escapeHtml(record.product_name)}</span>
          <small>${escapeHtml(record.target_market)} · ${escapeHtml(record.target_language)} · 推荐 ${escapeHtml(best.version)} / ${best.score} 分</small>
          <small>${formatDate(record.created_at)}</small>
        </button>
      `;
    })
    .join("");
  historyList.querySelectorAll("[data-history-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const id = Number(button.dataset.historyId);
      const record = history.find((item) => item.id === id);
      if (!record) return;
      activeHistoryId = id;
      currentResult = record.response;
      renderResult(record.response);
      renderHistory();
      setStatus(`已加载历史记录：${record.product_name}`, "历史复盘");
      resultPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
}

function renderStats() {
  marketStat.textContent = valueOf("target_market") || "United States";
  competitorStat.textContent = String(competitors.length);
  historyStat.textContent = String(history.length);
}

function updatePayloadPreview() {
  payloadPreview.textContent = JSON.stringify(buildPayload(), null, 2);
  renderStats();
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

function splitSemicolonList(value) {
  return value
    .split(/[;；]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function exportHistoryCsv() {
  const rows = [
    ["id", "created_at", "product_name", "market", "language", "recommended_version", "score", "title", "ad_copy"]
  ];
  history.forEach((record) => {
    const best = [...record.response.versions].sort((a, b) => b.score - a.score)[0];
    rows.push([
      record.id,
      record.created_at,
      record.product_name,
      record.target_market,
      record.target_language,
      best.version,
      best.score,
      best.title,
      best.ad_copy
    ]);
  });
  downloadFile("listing-history.csv", rows.map((row) => row.map(csvCell).join(",")).join("\n"), "text/csv;charset=utf-8");
}

function exportHistoryExcel() {
  const rows = history.map((record) => {
    const best = [...record.response.versions].sort((a, b) => b.score - a.score)[0];
    return `<tr><td>${record.id}</td><td>${escapeHtml(record.created_at)}</td><td>${escapeHtml(record.product_name)}</td><td>${escapeHtml(record.target_market)}</td><td>${escapeHtml(best.version)}</td><td>${best.score}</td><td>${escapeHtml(best.title)}</td></tr>`;
  });
  const html = `<html><meta charset="utf-8"><body><table><thead><tr><th>ID</th><th>Created</th><th>Product</th><th>Market</th><th>Version</th><th>Score</th><th>Title</th></tr></thead><tbody>${rows.join("")}</tbody></table></body></html>`;
  downloadFile("listing-history.xls", html, "application/vnd.ms-excel;charset=utf-8");
}

function downloadFile(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function csvCell(value) {
  return `"${String(value ?? "").replaceAll('"', '""')}"`;
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value || "-";
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
