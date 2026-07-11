from pydantic import BaseModel, Field


class ProductInput(BaseModel):
    name: str = Field(..., min_length=2)
    category: str = Field(..., min_length=2)
    target_market: str = "United States"
    target_language: str = "Chinese"
    selling_points: list[str] = Field(default_factory=list)
    material: str = ""
    size: str = ""
    use_cases: list[str] = Field(default_factory=list)
    price_range: str = ""
    brand_tone: str = "practical and trustworthy"


class CompetitorInput(BaseModel):
    title: str = ""
    bullet_points: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    price: str = ""
    rating: float | None = None
    review_summary: str = ""


class ListingRequest(BaseModel):
    product: ProductInput
    competitors: list[CompetitorInput] = Field(default_factory=list)


class RefineRequest(ListingRequest):
    direction: str = Field(..., pattern="^(seo|conversion|concise|localization)$")
    previous_response: dict = Field(default_factory=dict)


class ListingVersion(BaseModel):
    version: str
    title: str
    bullet_points: list[str]
    seo_keywords: list[str]
    ad_copy: str
    score: int
    score_breakdown: dict[str, int] = Field(default_factory=dict)
    optimization_reasons: list[str]


class ListingResponse(BaseModel):
    id: int | None = None
    market: str
    language: str
    generation_source: str = "fallback"
    generation_provider: str = "deepseek"
    competitor_insights: list[str]
    versions: list[ListingVersion]
    recommendation: str
