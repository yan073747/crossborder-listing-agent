import csv
import io
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.database import clear_runs, init_db, list_runs, save_listing_run
from app.excel_export import build_listing_runs_xlsx
from app.schemas import ListingRequest, ListingResponse, RefineRequest
from env_loader import load_env_file
from listing_agent import generate_listing, refine_listing


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    load_env_file()
    init_db()
    yield


app = FastAPI(
    title="Cross-Border Listing Optimization Agent",
    description="Generate, score, compare, and export cross-border e-commerce Listing copy.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "listing-agent", "stack": "FastAPI"}


@app.post("/api/listings/generate", response_model=ListingResponse)
def create_listing(request: ListingRequest) -> ListingResponse:
    request_payload = request.model_dump()
    response_payload = generate_listing(request_payload)
    saved_payload = save_listing_run(request_payload, response_payload)
    return ListingResponse.model_validate(saved_payload)


@app.post("/api/listings/refine", response_model=ListingResponse)
def refine_existing_listing(request: RefineRequest) -> ListingResponse:
    request_payload = request.model_dump()
    response_payload = refine_listing(request_payload)
    saved_payload = save_listing_run(request_payload, response_payload)
    return ListingResponse.model_validate(saved_payload)


@app.get("/api/listings")
def get_listings() -> list[dict]:
    return list_runs()


@app.delete("/api/listings")
def delete_listings() -> dict[str, int]:
    return clear_runs()


@app.get("/api/listings/export.csv")
def export_listings_csv() -> StreamingResponse:
    rows = list_runs()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "product_name", "market", "language", "recommended_version", "score", "title"])
    for row in rows:
        versions = row["response"]["versions"]
        best = max(versions, key=lambda item: item["score"])
        writer.writerow(
            [
                row["id"],
                row["product_name"],
                row["target_market"],
                row["target_language"],
                best["version"],
                best["score"],
                best["title"],
            ]
        )
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=listing-runs.csv"},
    )


@app.get("/api/listings/export.xlsx")
def export_listings_xlsx() -> StreamingResponse:
    workbook = build_listing_runs_xlsx(list_runs())
    return StreamingResponse(
        iter([workbook]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=listing-runs.xlsx"},
    )
