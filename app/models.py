from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal

class Geography(BaseModel):
    country: str = "Italia"
    region: Optional[str] = None
    provinces: List[str] = Field(default_factory=list)

class Segment(BaseModel):
    type: Literal["PMI", "Enterprise", "Unknown"] = "Unknown"
    employees_min: Optional[int] = None
    employees_max: Optional[int] = None
    revenue_min_eur: Optional[int] = None
    revenue_max_eur: Optional[int] = None

class ApiKeys(BaseModel):
    serper_api_key: Optional[str] = None
    perplexity_api_key: Optional[str] = None
    newsapi_key: Optional[str] = None
    opencorporates_api_key: Optional[str] = None
    hunter_api_key: Optional[str] = None
    email_verify_provider: Optional[str] = None
    email_verify_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    web_provider: Optional[str] = None  # auto|serper|perplexity|newsapi

class Evidence(BaseModel):
    title: str
    url: str
    snippet: Optional[str] = None
    published_at: Optional[str] = None
    source: str = "web"

class CompanyCandidate(BaseModel):
    company_name: str
    website: str
    province: Optional[str] = None
    industry: Optional[str] = None
    growth_signals: List[str] = Field(default_factory=list)
    evidences: List[Evidence] = Field(default_factory=list)

class CompanyProfile(BaseModel):
    company_name: str
    website: str
    province: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    services_products: List[str] = Field(default_factory=list)
    target_customers: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    employees_est: Optional[int] = None
    revenue_est_eur: Optional[int] = None
    headquarters: Optional[str] = None
    recent_projects: List[str] = Field(default_factory=list)
    partners: List[str] = Field(default_factory=list)
    evidences: List[Evidence] = Field(default_factory=list)

class DecisionMaker(BaseModel):
    name: str
    role: str
    source_url: Optional[str] = None
    linkedin_url: Optional[str] = None

class VerifiedEmail(BaseModel):
    email: str
    status: Literal["valid", "invalid", "unknown"] = "unknown"
    confidence: Optional[float] = None
    source: str = "pattern"
    details: Dict[str, Any] = Field(default_factory=dict)

class LeadRecord(BaseModel):
    company: CompanyProfile
    decision_maker: Optional[DecisionMaker] = None
    verified_email: Optional[VerifiedEmail] = None
    contact_source: Optional[str] = None
    estimated_budget_eur: Optional[int] = None
    investment_window_months: Optional[List[int]] = None
    score: int = 0
    score_class: str = "cold"
    status: Literal["nuovo", "contattato", "follow-up"] = "nuovo"

class RunRequest(BaseModel):
    force_refresh_profile: bool = False
    enable_project_profile: bool = True
    api_keys: Optional[ApiKeys] = None
    reference_company_url: Optional[str] = None
    preset: Optional[str] = None  # e.g. "teleimpianti", "logistica"
    geography: Geography
    industry: str
    segment: Segment = Segment()
    investment_window_months: List[int] = Field(default_factory=lambda:[4,6])
    allowed_channels: List[str] = Field(default_factory=lambda:["email","linkedin"])
    limit: int = 30
    include_email_drafts: bool = False
    session_id: str = "run"

class DiscoverRequest(BaseModel):
    reference_company_url: Optional[str] = None
    geography: Geography
    industry: str
    segment: Segment = Segment()
    investment_window_months: List[int] = Field(default_factory=lambda:[4,6])
    allowed_channels: List[str] = Field(default_factory=lambda:["email","linkedin"])
    limit: int = 30
    session_id: str = "discover"

class EnrichRequest(BaseModel):
    candidates: List[CompanyCandidate]
    session_id: str = "enrich"

class IdentifyRequest(BaseModel):
    companies: List[CompanyProfile]
    session_id: str = "identify"

class VerifyRequest(BaseModel):
    leads: List[LeadRecord]
    session_id: str = "verify"

class ScoreRequest(BaseModel):
    leads: List[LeadRecord]
    reference_company_url: Optional[str] = None
    session_id: str = "score"

class ExportRequest(BaseModel):
    leads: List[LeadRecord]
    file_format: Literal["xlsx","csv"] = "xlsx"
    session_id: str = "export"

class RunResponse(BaseModel):
    run_id: str
    leads: List[LeadRecord]
    export: Optional[Dict[str, Any]] = None
    email_drafts: Optional[List[Dict[str, Any]]] = None

class LinkedInImportResponse(BaseModel):
    imported_rows: int
    leads: List[LeadRecord]

class ProjectProfile(BaseModel):
    reference_url: str
    services_offered: List[str] = []
    industries_served: List[str] = []
    technologies: List[str] = []
    value_props: List[str] = []
    proof_points: List[str] = []
    typical_deal_min_eur: Optional[int] = None
    typical_deal_max_eur: Optional[int] = None
    notes: Optional[str] = None
