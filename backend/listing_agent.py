from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from env_loader import load_env_file


ScoreBreakdown = dict[str, int]


SCORE_KEYS = [
    "title_completeness",
    "keyword_coverage",
    "benefit_clarity",
    "localization_quality",
    "ad_conversion_potential",
]


def generate_listing(payload: dict[str, Any]) -> dict[str, Any]:
    load_env_file()
    config = _llm_config()
    api_key = config["api_key"]
    if api_key:
        try:
            response = _generate_with_chat_completions(payload, config)
            response["generation_source"] = "llm"
            response["generation_provider"] = config["provider"]
            return _normalize_response(payload, response)
        except Exception as exc:
            fallback = _generate_with_rules(payload)
            fallback["generation_source"] = "fallback"
            fallback["generation_provider"] = config["provider"]
            fallback["competitor_insights"].insert(
                0,
                _text(
                    payload,
                    f"大模型调用失败，已自动切换到本地规则生成。错误：{exc}",
                    f"LLM call failed; local fallback was used. Error: {exc}",
                ),
            )
            return fallback

    fallback = _generate_with_rules(payload)
    fallback["generation_source"] = "fallback"
    fallback["generation_provider"] = config["provider"]
    fallback["competitor_insights"].insert(
        0,
        _text(
            payload,
            "未检测到 LLM_API_KEY，本次使用本地规则生成；配置 Key 后会自动启用大模型生成。",
            "LLM_API_KEY is not configured, so local fallback generation was used.",
        ),
    )
    return fallback


def refine_listing(payload: dict[str, Any]) -> dict[str, Any]:
    direction = payload.get("direction", "seo")
    base_payload = {
        "product": payload["product"],
        "competitors": payload.get("competitors", []),
        "previous_response": payload.get("previous_response", {}),
        "refine_direction": direction,
    }
    load_env_file()
    config = _llm_config()
    if config["api_key"]:
        try:
            response = _generate_with_chat_completions(base_payload, config, prompt_kind="refine")
            response["generation_source"] = "llm"
            response["generation_provider"] = config["provider"]
            normalized = _normalize_response(payload, response)
            normalized["competitor_insights"].insert(0, _refine_message(payload, direction, True))
            return normalized
        except Exception as exc:
            fallback = _generate_refinement_with_rules(payload, direction)
            fallback["generation_source"] = "fallback"
            fallback["generation_provider"] = config["provider"]
            fallback["competitor_insights"].insert(
                0,
                _text(
                    payload,
                    f"大模型二次优化失败，已使用本地规则完成{_direction_label(direction)}。错误：{exc}",
                    f"LLM refinement failed; local fallback completed {direction} refinement. Error: {exc}",
                ),
            )
            return fallback

    fallback = _generate_refinement_with_rules(payload, direction)
    fallback["generation_source"] = "fallback"
    fallback["generation_provider"] = config["provider"]
    fallback["competitor_insights"].insert(0, _refine_message(payload, direction, False))
    return fallback


def _generate_refinement_with_rules(payload: dict[str, Any], direction: str) -> dict[str, Any]:
    response = _generate_with_rules(payload)
    for version in response["versions"]:
        version["title"] = _refine_title(version["title"], payload, direction)
        version["bullet_points"] = [_refine_bullet(bullet, direction, payload) for bullet in version["bullet_points"]]
        version["ad_copy"] = _refine_ad_copy(version["ad_copy"], direction, payload)
        version["seo_keywords"] = _refine_keywords(version["seo_keywords"], direction, payload)
        version["optimization_reasons"].insert(0, _refine_reason(payload, direction))
        version["score_breakdown"] = _score_breakdown(
            version["title"],
            version["bullet_points"],
            version["seo_keywords"],
            version["ad_copy"],
            payload,
            "seo" if direction == "seo" else "conversion",
        )
        if direction == "seo":
            version["score_breakdown"]["keyword_coverage"] = min(100, version["score_breakdown"]["keyword_coverage"] + 8)
        elif direction == "conversion":
            version["score_breakdown"]["ad_conversion_potential"] = min(100, version["score_breakdown"]["ad_conversion_potential"] + 8)
        elif direction == "concise":
            version["score_breakdown"]["benefit_clarity"] = min(100, version["score_breakdown"]["benefit_clarity"] + 6)
        elif direction == "localization":
            version["score_breakdown"]["localization_quality"] = min(100, version["score_breakdown"]["localization_quality"] + 8)
        version["score"] = _average_score(version["score_breakdown"])
    response["recommendation"] = _text(
        payload,
        f"已完成{_direction_label(direction)}二次优化。建议将优化后的版本与上一版历史记录对比，观察标题关键词、卖点表达和广告转化潜力变化。",
        f"{direction.title()} refinement completed. Compare this run with the previous history record.",
    )
    return response


def _llm_config() -> dict[str, str]:
    provider = os.getenv("LLM_PROVIDER", "deepseek").strip() or "deepseek"
    defaults = {
        "deepseek": {
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-v4-flash",
        }
    }
    provider_defaults = defaults.get(provider.lower(), {})
    return {
        "provider": provider,
        "api_key": os.getenv("LLM_API_KEY", "").strip(),
        "base_url": os.getenv("LLM_BASE_URL", provider_defaults.get("base_url", "")).strip().rstrip("/"),
        "model": os.getenv("LLM_MODEL", provider_defaults.get("model", "")).strip(),
    }


def _generate_with_chat_completions(payload: dict[str, Any], config: dict[str, str], prompt_kind: str = "generate") -> dict[str, Any]:
    if not config["base_url"]:
        raise RuntimeError("LLM_BASE_URL is required when LLM_API_KEY is configured")
    if not config["model"]:
        raise RuntimeError("LLM_MODEL is required when LLM_API_KEY is configured")

    request_body = {
        "model": config["model"],
        "messages": [
            {
                "role": "system",
                "content": "You are a cross-border e-commerce Listing optimization agent. Return only valid JSON.",
            },
            {"role": "user", "content": _build_llm_prompt(payload) if prompt_kind == "generate" else _build_refine_prompt(payload)},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.4,
    }
    request = urllib.request.Request(
        f"{config['base_url']}/chat/completions",
        data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{config['provider']} HTTP {exc.code}: {detail[:300]}") from exc

    text = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not text:
        raise RuntimeError(f"{config['provider']} response did not include message content")

    return json.loads(text)


def _build_refine_prompt(payload: dict[str, Any]) -> str:
    language = payload.get("product", {}).get("target_language", "Chinese")
    direction = payload.get("refine_direction", "seo")
    direction_guidance = {
        "seo": "Prioritize keyword coverage, search intent, long-tail terms, and title discoverability.",
        "conversion": "Prioritize purchase motivation, benefit clarity, ad click-through, and trust signals.",
        "concise": "Make title and bullets shorter, clearer, and easier to scan while preserving key facts.",
        "localization": "Improve local language, market fit, cultural expression, and customer concerns.",
    }
    return f"""
You are refining an existing cross-border e-commerce Listing.
Return only valid JSON. Do not wrap it in Markdown.

Output language: {language}
Refinement direction: {direction}
Direction guidance: {direction_guidance.get(direction, direction_guidance["seo"])}

Keep the same JSON schema as the generation task:
- market, language, competitor_insights, versions, recommendation
- each version has version, title, bullet_points, seo_keywords, ad_copy, score, score_breakdown, optimization_reasons

The new result must be meaningfully different from previous_response and should explain what changed.

Input:
{json.dumps(payload, ensure_ascii=False, indent=2)}
""".strip()


def _build_llm_prompt(payload: dict[str, Any]) -> str:
    language = payload.get("product", {}).get("target_language", "Chinese")
    return f"""
You are a cross-border e-commerce Listing optimization agent.
Return only valid JSON. Do not wrap it in Markdown.

Output language: {language}

Business task:
- Analyze product and competitor data.
- Generate two A/B Listing versions.
- Each version must include title, five bullet points, SEO keywords, ad copy, total score, score breakdown, and optimization reasons.
- Make the copy practical for e-commerce operators, not generic creative writing.

JSON schema:
{{
  "market": "string",
  "language": "string",
  "competitor_insights": ["string"],
  "versions": [
    {{
      "version": "A",
      "title": "string",
      "bullet_points": ["string", "string", "string", "string", "string"],
      "seo_keywords": ["string"],
      "ad_copy": "string",
      "score": 0,
      "score_breakdown": {{
        "title_completeness": 0,
        "keyword_coverage": 0,
        "benefit_clarity": 0,
        "localization_quality": 0,
        "ad_conversion_potential": 0
      }},
      "optimization_reasons": ["string"]
    }}
  ],
  "recommendation": "string"
}}

Scoring rule:
- Each score_breakdown value is 0-100.
- score is the rounded average of the five dimensions.

Input:
{json.dumps(payload, ensure_ascii=False, indent=2)}
""".strip()


def _direction_label(direction: str) -> str:
    return {
        "seo": "SEO 强化",
        "conversion": "转化强化",
        "concise": "简洁化",
        "localization": "本地化强化",
    }.get(direction, direction)


def _refine_message(payload: dict[str, Any], direction: str, used_llm: bool) -> str:
    if used_llm:
        return _text(payload, f"已使用大模型完成{_direction_label(direction)}二次优化。", f"LLM completed {direction} refinement.")
    return _text(payload, f"未检测到 LLM_API_KEY，已使用本地规则完成{_direction_label(direction)}二次优化。", f"Local fallback completed {direction} refinement.")


def _refine_reason(payload: dict[str, Any], direction: str) -> str:
    return _text(
        payload,
        f"本轮按“{_direction_label(direction)}”方向重写，便于和上一版历史记录对比。",
        f"This run was rewritten for {direction} refinement and can be compared with the previous history record.",
    )


def _refine_title(title: str, payload: dict[str, Any], direction: str) -> str:
    product = payload["product"]
    keywords = _build_keywords(payload)[:4]
    if _is_chinese(payload):
        if direction == "seo":
            return f"{title}｜搜索词：{'、'.join(keywords)}"[:190]
        if direction == "conversion":
            return f"{title}｜突出省时、放心、适合日常使用"[:190]
        if direction == "concise":
            return f"{product.get('name', '')}，{_first(product.get('selling_points', []), '')}，适合{_first(product.get('use_cases', []), '')}"[:120]
        if direction == "localization":
            return f"{title}｜更贴近{_market_label(product.get('target_market', ''))}消费者搜索习惯"[:190]
    else:
        if direction == "seo":
            return f"{title} | Search terms: {', '.join(keywords)}"[:190]
        if direction == "conversion":
            return f"{title} | Built for easier daily use and confident purchase"[:190]
        if direction == "concise":
            return f"{product.get('name', '')}, {_first(product.get('selling_points', []), '')}, for {_first(product.get('use_cases', []), '')}"[:120]
        if direction == "localization":
            return f"{title} | Tuned for {product.get('target_market', '')} shoppers"[:190]
    return title


def _refine_bullet(bullet: str, direction: str, payload: dict[str, Any]) -> str:
    if _is_chinese(payload):
        prefixes = {
            "seo": "【关键词强化】",
            "conversion": "【转化强化】",
            "concise": "【简洁表达】",
            "localization": "【本地化表达】",
        }
        if direction == "concise":
            return f"{prefixes[direction]}{bullet.split('：')[0]}：一句话说明核心购买理由。"
        return f"{prefixes.get(direction, '')}{bullet}"
    prefixes = {
        "seo": "[SEO] ",
        "conversion": "[Conversion] ",
        "concise": "[Concise] ",
        "localization": "[Localized] ",
    }
    if direction == "concise":
        return f"{prefixes[direction]}{bullet.split(':')[0]}: clear purchase benefit."
    return f"{prefixes.get(direction, '')}{bullet}"


def _refine_ad_copy(ad_copy: str, direction: str, payload: dict[str, Any]) -> str:
    if _is_chinese(payload):
        suffixes = {
            "seo": "覆盖更多高意图搜索场景，适合投放前的关键词测试。",
            "conversion": "强调立即购买理由，适合详情页和广告落地页。",
            "concise": "保留核心利益点，减少冗余表达。",
            "localization": "表达更贴近目标市场消费者的真实使用顾虑。",
        }
        return f"{ad_copy} {suffixes.get(direction, '')}".strip()
    suffixes = {
        "seo": "Built for high-intent keyword testing.",
        "conversion": "Designed to increase purchase confidence.",
        "concise": "Keeps the core benefit clear and scannable.",
        "localization": "Tuned to shopper concerns in the target market.",
    }
    return f"{ad_copy} {suffixes.get(direction, '')}".strip()


def _refine_keywords(keywords: list[str], direction: str, payload: dict[str, Any]) -> list[str]:
    additions = {
        "seo": ["高转化关键词", "长尾搜索词"] if _is_chinese(payload) else ["high intent keyword", "long tail search"],
        "conversion": ["购买理由", "转化卖点"] if _is_chinese(payload) else ["purchase reason", "conversion benefit"],
        "concise": ["核心卖点"] if _is_chinese(payload) else ["core benefit"],
        "localization": ["本地化表达", "目标市场"] if _is_chinese(payload) else ["localized copy", "target market"],
    }
    return _clean_words([*keywords, *additions.get(direction, [])])[:14]


def _generate_with_rules(payload: dict[str, Any]) -> dict[str, Any]:
    version_a = _make_version(payload, "A", "conversion")
    version_b = _make_version(payload, "B", "seo")
    if _is_chinese(payload):
        recommendation = "推荐：版本 A 更适合商品详情页转化，版本 B 更适合提升搜索覆盖。建议先用版本 A 上线，再用版本 B 做关键词测试。"
        if version_b["score"] > version_a["score"]:
            recommendation = "推荐版本 B，因为它的 SEO 关键词覆盖更强，更适合搜索流量场景。"
        elif version_a["score"] > version_b["score"]:
            recommendation = "推荐版本 A，因为它在卖点表达和转化清晰度之间更平衡。"
    else:
        recommendation = (
            "Use Version A for product detail pages when conversion is the priority. "
            "Use Version B when search ranking and keyword coverage are more important."
        )
        if version_b["score"] > version_a["score"]:
            recommendation = "Version B is recommended because it has stronger SEO coverage."
        elif version_a["score"] > version_b["score"]:
            recommendation = "Version A is recommended because it balances benefits and conversion clarity."

    product = payload["product"]
    return {
        "id": None,
        "market": product.get("target_market", "United States"),
        "language": product.get("target_language", "Chinese"),
        "competitor_insights": _build_insights(payload),
        "versions": [version_a, version_b],
        "recommendation": recommendation,
    }


def _make_version(payload: dict[str, Any], version: str, angle: str) -> dict[str, Any]:
    product = payload["product"]
    keywords = _build_keywords(payload)
    primary_point = _first(product.get("selling_points", []), "daily use")
    use_case = _first(product.get("use_cases", []), "home, office, and travel")
    chinese = _is_chinese(payload)
    material_value = product.get("material", "")
    size_value = product.get("size", "")
    market = product.get("target_market", "United States")
    market_text = _market_label(market) if chinese else market
    category = product.get("category", "product")
    name = product.get("name", "Product")

    if chinese:
        material = f"，材质：{material_value}" if material_value else ""
        size = f"，规格：{size_value}" if size_value else ""
        if angle == "conversion":
            title = f"{name}，适合{use_case}，主打{primary_point}，{category}{material}{size}，面向{market_text}市场"
            ad_copy = (
                f"用 {name} 提升{use_case}场景下的使用效率。突出{primary_point}、便携设计和清洗便利性，"
                f"适合面向{market_text}消费者的商品详情页和广告素材。"
            )
        else:
            tone = product.get("brand_tone", "实用可靠")
            title = f"{name} {category}，{primary_point}，{tone}选择{material}{size}，适合{use_case}"
            ad_copy = (
                f"围绕{category}的高意图搜索需求，强调{primary_point}和{use_case}场景，"
                f"帮助运营人员快速准备更贴近用户需求的广告文案。"
            )
        bullets = _build_bullets_chinese(product, market_text)
        reasons = [
            "标题同时覆盖商品类型、核心卖点、使用场景和目标市场。",
            "五点描述把原始功能改写成面向用户的利益点。",
            "SEO 关键词结合商品属性和竞品高频搜索词。",
            "A/B 两个版本分别服务转化表达和搜索覆盖，便于运营对比选择。",
        ]
    else:
        material = f" with {material_value}" if material_value else ""
        size = f", {size_value}" if size_value else ""
        if angle == "conversion":
            title = f"{name} for {use_case}, {primary_point}, {category}{material}{size}, Designed for {market}"
            ad_copy = (
                f"Upgrade your {use_case} routine with {name}. Clear benefits, practical design, "
                f"and ready-to-use convenience for shoppers in {market}."
            )
        else:
            tone = product.get("brand_tone", "practical and trustworthy").title()
            title = f"{name} {category}, {primary_point}, {tone} Choice{material}{size} for {use_case}"
            ad_copy = (
                f"Discover a smarter {category} for {use_case}. Built around {primary_point} "
                f"and positioned for high-intent search traffic."
            )
        bullets = _build_bullets_english(product, market)
        reasons = [
            "Title combines product type, primary benefit, use case, and target market.",
            "Bullet points convert raw features into customer-facing benefits.",
            "SEO keywords reuse product attributes and competitor search terms.",
            "A/B version angle supports comparison between conversion copy and search-focused copy.",
        ]

    score_breakdown = _score_breakdown(title, bullets, keywords, ad_copy, payload, angle)
    return {
        "version": version,
        "title": title[:190],
        "bullet_points": bullets,
        "seo_keywords": keywords,
        "ad_copy": ad_copy,
        "score": _average_score(score_breakdown),
        "score_breakdown": score_breakdown,
        "optimization_reasons": reasons,
    }


def _score_breakdown(
    title: str,
    bullets: list[str],
    keywords: list[str],
    ad_copy: str,
    payload: dict[str, Any],
    angle: str,
) -> ScoreBreakdown:
    competitor_terms = _competitor_keywords(payload)
    selling_points = payload.get("product", {}).get("selling_points", [])
    chinese = _is_chinese(payload)
    market = payload.get("product", {}).get("target_market", "")
    market_text = _market_label(market) if chinese else market

    title_score = 60
    if payload.get("product", {}).get("name", "") in title:
        title_score += 10
    if payload.get("product", {}).get("category", "") in title:
        title_score += 10
    if market_text and market_text in title:
        title_score += 10
    if 24 <= len(title) <= 190:
        title_score += 10

    keyword_score = 55 + min(len(keywords), 10) * 3
    keyword_overlap = sum(1 for term in competitor_terms if term in keywords)
    keyword_score += min(keyword_overlap, 5) * 3

    benefit_hits = sum(1 for point in selling_points if any(point in bullet for bullet in bullets))
    benefit_score = 60 + min(benefit_hits, 5) * 6
    if len(bullets) >= 5:
        benefit_score += 10

    localization_score = 70
    if chinese and any("：把商品功能" in bullet for bullet in bullets):
        localization_score += 15
    if not chinese and all("customer benefit" in bullet for bullet in bullets):
        localization_score += 15
    if market_text:
        localization_score += 5

    conversion_score = 70
    if angle == "conversion":
        conversion_score += 10
    if ad_copy:
        conversion_score += 10
    if any(word in ad_copy.lower() for word in ["upgrade", "discover"]) or any(word in ad_copy for word in ["提升", "帮助"]):
        conversion_score += 5

    return {
        "title_completeness": min(title_score, 100),
        "keyword_coverage": min(keyword_score, 100),
        "benefit_clarity": min(benefit_score, 100),
        "localization_quality": min(localization_score, 100),
        "ad_conversion_potential": min(conversion_score, 100),
    }


def _normalize_response(payload: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    product = payload["product"]
    response.setdefault("id", None)
    response.setdefault("market", product.get("target_market", "United States"))
    response.setdefault("language", product.get("target_language", "Chinese"))
    response.setdefault("generation_provider", _llm_config()["provider"])
    response.setdefault("competitor_insights", _build_insights(payload))
    response.setdefault("recommendation", "")
    response["versions"] = [_normalize_version(payload, item) for item in response.get("versions", [])[:2]]
    if len(response["versions"]) < 2:
        fallback_versions = _generate_with_rules(payload)["versions"]
        response["versions"].extend(fallback_versions[len(response["versions"]) : 2])
    return response


def _normalize_version(payload: dict[str, Any], version: dict[str, Any]) -> dict[str, Any]:
    version.setdefault("version", "A")
    version.setdefault("title", "")
    version.setdefault("bullet_points", [])
    version["bullet_points"] = list(version["bullet_points"])[:5]
    while len(version["bullet_points"]) < 5:
        version["bullet_points"].append(_text(payload, "补充一个清晰的用户利益点。", "Add one clear customer benefit."))
    version.setdefault("seo_keywords", [])
    version.setdefault("ad_copy", "")
    version.setdefault("optimization_reasons", [])
    breakdown = version.get("score_breakdown")
    if not isinstance(breakdown, dict):
        breakdown = _score_breakdown(
            version["title"],
            version["bullet_points"],
            version["seo_keywords"],
            version["ad_copy"],
            payload,
            "conversion" if version.get("version") == "A" else "seo",
        )
    version["score_breakdown"] = {key: int(max(0, min(100, breakdown.get(key, 0)))) for key in SCORE_KEYS}
    version["score"] = _average_score(version["score_breakdown"])
    return version


def _build_insights(payload: dict[str, Any]) -> list[str]:
    competitors = payload.get("competitors", [])
    insights: list[str] = []
    if competitors:
        insights.append(
            _text(
                payload,
                f"已读取 {len(competitors)} 条竞品数据，可作为标题定位、卖点表达和关键词覆盖的参考。",
                f"Found {len(competitors)} competitor records for positioning reference.",
            )
        )
    ratings = [item.get("rating") for item in competitors if isinstance(item.get("rating"), (int, float))]
    if ratings:
        avg_rating = sum(ratings) / len(ratings)
        insights.append(
            _text(
                payload,
                f"竞品平均评分为 {avg_rating:.1f}，文案需要突出可靠性、品质感和降低购买顾虑。",
                f"Average competitor rating is {avg_rating:.1f}, so copy should emphasize trust and quality proof.",
            )
        )
    competitor_terms = _competitor_keywords(payload)
    if competitor_terms:
        insights.append(
            _text(
                payload,
                f"可复用搜索词：{', '.join(competitor_terms[:6])}。",
                f"Reusable search terms detected: {', '.join(competitor_terms[:6])}.",
            )
        )
    if not insights:
        insights.append(
            _text(
                payload,
                "未提供竞品数据，本次生成将重点围绕商品卖点和使用场景展开。",
                "No competitor data provided; generation focuses on product selling points.",
            )
        )
    return insights


def _build_keywords(payload: dict[str, Any]) -> list[str]:
    product = payload["product"]
    return _clean_words(
        [
            product.get("name", ""),
            product.get("category", ""),
            product.get("material", ""),
            *product.get("selling_points", []),
            *product.get("use_cases", []),
            *_competitor_keywords(payload),
        ]
    )[:14]


def _build_bullets_chinese(product: dict[str, Any], market_text: str) -> list[str]:
    selling_points = list(product.get("selling_points", []))[:5]
    while len(selling_points) < 5:
        selling_points.append("日常使用更方便")
    return [
        f"{point}：把商品功能转化为{market_text}消费者更容易理解的购买理由。"
        for point in selling_points[:5]
    ]


def _build_bullets_english(product: dict[str, Any], market: str) -> list[str]:
    selling_points = list(product.get("selling_points", []))[:5]
    while len(selling_points) < 5:
        selling_points.append("Designed for convenient everyday use")
    return [
        f"{point}: communicates a direct customer benefit for {market} shoppers."
        for point in selling_points[:5]
    ]


def _competitor_keywords(payload: dict[str, Any]) -> list[str]:
    keywords: list[str] = []
    for competitor in payload.get("competitors", []):
        keywords.extend(competitor.get("keywords", []))
        for bullet in competitor.get("bullet_points", []):
            keywords.extend([word.strip(",.").lower() for word in str(bullet).split() if len(word) > 5])
    return _clean_words(keywords)[:12]


def _clean_words(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = str(value).strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(str(value).strip())
    return result


def _is_chinese(payload: dict[str, Any]) -> bool:
    return payload.get("product", {}).get("target_language", "").lower() in {"chinese", "中文", "zh", "zh-cn"}


def _market_label(market: str) -> str:
    labels = {
        "United States": "美国",
        "Japan": "日本",
        "Germany": "德国",
        "Spain": "西班牙",
    }
    return labels.get(market, market)


def _first(values: list[str], fallback: str) -> str:
    return values[0] if values else fallback


def _average_score(score_breakdown: ScoreBreakdown) -> int:
    return round(sum(score_breakdown.values()) / len(SCORE_KEYS))


def _text(payload: dict[str, Any], chinese: str, english: str) -> str:
    return chinese if _is_chinese(payload) else english
