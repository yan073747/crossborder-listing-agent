from fastapi.testclient import TestClient
import zipfile
from io import BytesIO

from app.database import init_db
from app.main import app


def make_client(monkeypatch, tmp_path) -> TestClient:
    monkeypatch.setenv("LISTING_AGENT_DB_PATH", str(tmp_path / "test_listing_agent.db"))
    monkeypatch.setenv("SKIP_DOTENV", "1")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    init_db()
    return TestClient(app)


def test_health_endpoint_reports_fastapi_stack() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["stack"] == "FastAPI"


def test_generate_endpoint_returns_ab_versions(monkeypatch, tmp_path) -> None:
    client = make_client(monkeypatch, tmp_path)
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

    response = client.post("/api/listings/generate", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    assert data["generation_source"] == "fallback"
    assert data["generation_provider"] == "deepseek"
    assert [version["version"] for version in data["versions"]] == ["A", "B"]
    assert "score_breakdown" in data["versions"][0]


def test_listings_endpoint_returns_saved_runs(monkeypatch, tmp_path) -> None:
    client = make_client(monkeypatch, tmp_path)
    payload = {
        "product": {
            "name": "History Test Blender",
            "category": "personal blender",
            "target_market": "United States",
            "target_language": "English",
            "selling_points": ["USB rechargeable", "easy to clean"],
            "material": "BPA-free plastic",
            "size": "380ml",
            "use_cases": ["office"],
            "price_range": "$19-$29",
            "brand_tone": "reliable",
        },
        "competitors": [],
    }

    create_response = client.post("/api/listings/generate", json=payload)
    assert create_response.status_code == 200
    created_id = create_response.json()["id"]

    list_response = client.get("/api/listings")

    assert list_response.status_code == 200
    records = list_response.json()
    record = next(item for item in records if item["id"] == created_id)
    assert record["product_name"] == "History Test Blender"
    assert record["response"]["versions"][0]["score_breakdown"]


def test_delete_listings_clears_saved_runs(monkeypatch, tmp_path) -> None:
    client = make_client(monkeypatch, tmp_path)
    payload = {
        "product": {
            "name": "Delete Test Blender",
            "category": "personal blender",
            "target_market": "United States",
            "target_language": "English",
        },
        "competitors": [],
    }
    assert client.post("/api/listings/generate", json=payload).status_code == 200

    delete_response = client.delete("/api/listings")

    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] == 1
    assert client.get("/api/listings").json() == []


def test_refine_endpoint_saves_second_run(monkeypatch, tmp_path) -> None:
    client = make_client(monkeypatch, tmp_path)
    payload = {
        "product": {
            "name": "Refine Test Blender",
            "category": "personal blender",
            "target_market": "United States",
            "target_language": "English",
            "selling_points": ["USB rechargeable", "easy to clean"],
            "material": "BPA-free plastic",
            "size": "380ml",
            "use_cases": ["office"],
            "price_range": "$19-$29",
            "brand_tone": "reliable",
        },
        "competitors": [],
    }
    first = client.post("/api/listings/generate", json=payload).json()

    refine_response = client.post(
        "/api/listings/refine",
        json={
            **payload,
            "direction": "seo",
            "previous_response": first,
        },
    )

    assert refine_response.status_code == 200
    refined = refine_response.json()
    assert refined["id"] != first["id"]
    assert refined["generation_source"] == "fallback"
    assert refined["versions"][0]["score_breakdown"]["keyword_coverage"] >= first["versions"][0]["score_breakdown"]["keyword_coverage"]
    assert "SEO" in " ".join(refined["versions"][0]["optimization_reasons"]) or "seo" in refined["recommendation"].lower()


def test_xlsx_export_returns_excel_workbook(monkeypatch, tmp_path) -> None:
    client = make_client(monkeypatch, tmp_path)
    payload = {
        "product": {
            "name": "Excel Test Blender",
            "category": "personal blender",
            "target_market": "United States",
            "target_language": "English",
            "selling_points": ["USB rechargeable"],
        },
        "competitors": [],
    }
    assert client.post("/api/listings/generate", json=payload).status_code == 200

    response = client.get("/api/listings/export.xlsx")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    with zipfile.ZipFile(BytesIO(response.content)) as workbook:
        names = set(workbook.namelist())
        assert "xl/workbook.xml" in names
        assert "xl/worksheets/sheet1.xml" in names
        sheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
        assert "Excel Test Blender" in sheet
        assert "Keyword Coverage" in sheet
