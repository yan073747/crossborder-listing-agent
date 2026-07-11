from listing_agent import generate_listing


def test_generate_listing_returns_two_scored_versions(monkeypatch) -> None:
    monkeypatch.setenv("SKIP_DOTENV", "1")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    payload = {
        "product": {
            "name": "Portable Electric Blender",
            "category": "personal blender",
            "target_market": "United States",
            "target_language": "English",
            "selling_points": ["USB rechargeable", "easy to clean", "compact bottle design"],
            "material": "BPA-free plastic",
            "size": "380ml",
            "use_cases": ["smoothies", "travel", "office"],
            "price_range": "$19-$29",
            "brand_tone": "modern and reliable",
        },
        "competitors": [
            {
                "title": "Portable Blender for Shakes and Smoothies",
                "bullet_points": ["Rechargeable blender with strong motor", "Easy cleaning cup for travel"],
                "keywords": ["portable blender", "smoothie maker", "USB rechargeable"],
                "price": "$24.99",
                "rating": 4.5,
                "review_summary": "Customers like the portability and easy cleaning.",
            }
        ],
    }

    response = generate_listing(payload)

    assert response["market"] == "United States"
    assert len(response["versions"]) == 2
    assert response["versions"][0]["score"] >= 80
    assert response["generation_source"] == "fallback"
    assert response["generation_provider"] == "deepseek"
    assert response["versions"][0]["score_breakdown"]["keyword_coverage"] >= 80
    assert "portable blender" in [keyword.lower() for keyword in response["versions"][0]["seo_keywords"]]


def test_generate_listing_defaults_to_chinese_copy_when_language_is_chinese(monkeypatch) -> None:
    monkeypatch.setenv("SKIP_DOTENV", "1")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    payload = {
        "product": {
            "name": "便携式电动榨汁杯",
            "category": "个人榨汁机",
            "target_market": "United States",
            "target_language": "Chinese",
            "selling_points": ["USB 充电", "容易清洗", "便携杯身设计"],
            "material": "食品级 BPA-free 塑料",
            "size": "380ml",
            "use_cases": ["早餐奶昔", "办公室", "旅行"],
            "price_range": "¥129-¥199",
            "brand_tone": "实用、可靠、有品质感",
        },
        "competitors": [
            {
                "title": "便携式榨汁杯 适合奶昔和果汁",
                "bullet_points": ["可充电强劲电机", "旅行场景清洗方便"],
                "keywords": ["便携式榨汁杯", "奶昔机", "USB 充电"],
                "price": "¥169",
                "rating": 4.5,
                "review_summary": "用户喜欢便携性和容易清洗。",
            }
        ],
    }

    response = generate_listing(payload)

    assert response["language"] == "Chinese"
    assert response["generation_source"] == "fallback"
    assert any(insight.startswith("已读取") for insight in response["competitor_insights"])
    assert "面向美国市场" in response["versions"][0]["title"]
    assert "推荐" in response["recommendation"]
    assert set(response["versions"][0]["score_breakdown"]) == {
        "title_completeness",
        "keyword_coverage",
        "benefit_clarity",
        "localization_quality",
        "ad_conversion_potential",
    }
