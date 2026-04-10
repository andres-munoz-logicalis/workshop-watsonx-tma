"""
CU-02 — Azure Cost Estimator API (v1: Azure Functions only)
v1 soporta SOLO azure_functions. Otros servicios devuelven status=unsupported_service.
"""

import os
import math
import logging
import requests
from typing import Optional, Any
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()
logging.basicConfig(level=logging.INFO)

API_PUBLIC_URL    = os.getenv("API_PUBLIC_URL", "http://localhost:8080")
AZURE_PRICES_URL  = "https://prices.azure.com/api/retail/prices"

# Constantes de Azure Functions Consumption Plan
FREE_EXECUTIONS  = 1_000_000   # gratis por mes
FREE_GB_SECONDS  = 400_000     # gratis por mes
MEMORY_BLOCK_MB  = 128         # Azure factura memoria en bloques de 128MB

UNCERTAINTY_BANDS = {
    "azure_functions": (0.70, 1.40),
}

OFFICIAL_CALCULATOR = {
    "azure_functions": "https://azure.microsoft.com/pricing/calculator/?service=functions",
}

DOCS_URL = {
    "azure_functions": "https://learn.microsoft.com/azure/azure-functions/",
}

SUPPORTED_SERVICES = {"azure_functions"}

DISCLAIMER = (
    "Esta es una estimación de orden de magnitud basada en los precios "
    "públicos de Azure Retail Prices API. No reemplaza una cotización formal. "
    "Storage, networking, Application Insights y otros servicios accesorios "
    "se facturan por separado y no están incluidos en este cálculo."
)

# FastAPI app
app = FastAPI(
    title="CU-02 Azure Cost Estimator API",
    description=(
        "Backend del agente CU-02 (estimador de costos) de la malla de "
        "watsonx Orchestrate. Calcula costos mensuales estimados de servicios "
        "Azure consultando la Azure Retail Prices API en vivo. v1 soporta "
        "únicamente Azure Functions en plan Consumption."
    ),
    version="1.0.0",
    servers=[{"url": API_PUBLIC_URL}],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Schemas — response unificado
class EstimateRange(BaseModel):
    low: float = Field(description="Cota inferior del rango estimado")
    expected: float = Field(description="Valor central calculado")
    high: float = Field(description="Cota superior del rango estimado")
    currency: str = Field(default="USD")


class CostComponent(BaseModel):
    name: str = Field(description="Nombre del componente: executions, compute, etc.")
    expected_cost: float
    formula: str = Field(description="Fórmula legible para explicar el cálculo")
    source: str = Field(description="azure_retail_prices | free_tier | fixed")


class Assumption(BaseModel):
    field: str = Field(description="Nombre del input al que aplica")
    value: str = Field(description="Valor asumido como string")
    source: str = Field(description="deep_dive | derived | default | user_provided")
    note: Optional[str] = Field(default=None, description="Explicación corta")


class HandoffBack(BaseModel):
    from_agent: str = "cu-02-cost-estimator"
    status: str = Field(description="completed | skipped | error | unsupported_service")
    service: str
    estimated_monthly_usd: Optional[dict] = None
    assumptions_count: int = 0
    next_suggested_action: str = Field(
        description="open_azure_calculator | refine_inputs | done | escalate_to_human"
    )


class EstimateResponse(BaseModel):
    service: str
    pricing_model: str
    region: str
    estimated_monthly: EstimateRange
    breakdown: list[CostComponent]
    assumptions: list[Assumption]
    inputs_used: dict
    disclaimer: str
    official_calculator_url: str
    handoff_back: HandoffBack


# Schemas — request del endpoint tipado
class FunctionsEstimateRequest(BaseModel):
    region: str = Field(
        default="eastus",
        description="Región de Azure en formato armRegionName.",
        examples=["eastus", "westeurope", "brazilsouth"],
    )
    monthly_executions: int = Field(
        description="Número total de invocaciones por mes.",
        examples=[1_000_000, 5_000_000, 50_000_000],
        gt=0,
    )
    avg_duration_ms: int = Field(
        description="Duración promedio de cada ejecución en milisegundos.",
        examples=[200, 500, 1000],
        gt=0,
    )
    memory_mb: int = Field(
        default=128,
        description="Memoria asignada en MB. Azure factura en bloques de 128MB.",
        examples=[128, 256, 512, 1024],
        gt=0,
    )
    currency: str = Field(default="USD", examples=["USD", "EUR"])
    assumptions: list[Assumption] = Field(
        default_factory=list,
        description=(
            "Assumptions que el agente quiere propagar al response. Permite que "
            "NORMALIZE del agente registre cómo derivó cada input desde el deep dive."
        ),
    )


# Schemas — request del router from-handoff
class HandoffParams(BaseModel):
    service: str
    pricing_tier: Optional[str] = None


class HandoffSection(BaseModel):
    next_agent: str
    required_inputs: list[str] = []
    params: HandoffParams


class UserContext(BaseModel):
    tree_path: list[str] = []
    deep_dive_answers: dict[str, Any] = {}


class FromHandoffRequest(BaseModel):
    """Payload completo que CU-01 produce. Solo usamos los campos relevantes."""
    service: Optional[str] = None
    summary: Optional[str] = None
    user_context: UserContext = Field(default_factory=UserContext)
    handoff: HandoffSection

    class Config:
        extra = "ignore"  # ignoramos campos como why_factors, key_considerations, etc.


class FromHandoffResponse(BaseModel):
    status: str = Field(description="ready_for_estimate | unsupported_service")
    service: str
    message: str
    required_inputs: list[str] = []
    deep_dive_keys_present: list[str] = []
    supported_services: list[str] = []
    next_endpoint: Optional[str] = Field(
        default=None,
        description="Endpoint tipado al que el agente debe llamar después de NORMALIZE",
    )


# Helpers — Azure Retail Prices API
def _query_azure_prices(filter_query: str, currency: str) -> list:
    """Consulta la Azure Retail Prices API y devuelve los Items con precio > 0."""
    params = {
        "$filter": filter_query,
        "currencyCode": f"'{currency}'",
    }
    try:
        response = requests.get(AZURE_PRICES_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error consultando Azure Retail Prices API: {str(e)}",
        )

    return [i for i in data.get("Items", []) if i["retailPrice"] > 0]


def fetch_functions_price(
    meter_name_contains: str,
    region: str,
    currency: str,
) -> float:
    """Busca un precio específico de Azure Functions por meterName."""
    filters = [
        "serviceFamily eq 'Compute'",
        f"armRegionName eq '{region}'",
        f"contains(meterName, '{meter_name_contains}')",
        "contains(productName, 'Functions')",
        "priceType eq 'Consumption'",
    ]
    items = _query_azure_prices(" and ".join(filters), currency)

    if not items:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No se encontraron precios para meterName='{meter_name_contains}' "
                f"en región='{region}'. Revisá GET /debug/meters?region={region}."
            ),
        )

    item = items[0]
    logging.info(
        f"Functions meter: {item['meterName']} | {item['productName']} | "
        f"{item['retailPrice']} {currency}"
    )
    return item["retailPrice"]


def round_memory_to_block(memory_mb: int) -> int:
    """Azure factura memoria en bloques de 128MB, redondeando hacia arriba."""
    return math.ceil(memory_mb / MEMORY_BLOCK_MB) * MEMORY_BLOCK_MB


# Cálculo principal de Azure Functions
def compute_functions_estimate(
    params: FunctionsEstimateRequest,
) -> EstimateResponse:
    """
    Calcula la estimación completa de Azure Functions Consumption Plan.

    Modelo de pricing:
      - 1M ejecuciones gratis/mes, luego $0.20/M (precio en eastus, varía por región)
      - 400k GB-segundos gratis/mes, luego $0.000016/GB-s
      - Memoria facturada en bloques de 128MB
    """
    # 1) Consultar precios en vivo
    price_per_10_executions = fetch_functions_price(
        "Total Executions", params.region, params.currency
    )
    price_per_gb_second = fetch_functions_price(
        "Execution Time", params.region, params.currency
    )

    # La API devuelve precio por 10 ejecuciones → convertir a por millón
    price_per_million_executions = price_per_10_executions * 100_000

    # 2) Calcular GB-segundos consumidos
    memory_mb_billed  = round_memory_to_block(params.memory_mb)
    memory_gb_billed  = memory_mb_billed / 1024
    duration_seconds  = params.avg_duration_ms / 1000
    total_gb_seconds  = params.monthly_executions * memory_gb_billed * duration_seconds

    # 3) Aplicar free tier
    billable_executions = max(0, params.monthly_executions - FREE_EXECUTIONS)
    billable_gb_seconds = max(0.0, total_gb_seconds - FREE_GB_SECONDS)
    free_tier_covers_all = (
        params.monthly_executions <= FREE_EXECUTIONS
        and total_gb_seconds <= FREE_GB_SECONDS
    )

    # 4) Calcular costos
    executions_cost = (billable_executions / 1_000_000) * price_per_million_executions
    compute_cost    = billable_gb_seconds * price_per_gb_second
    expected_cost   = executions_cost + compute_cost

    # 5) Aplicar banda de incertidumbre
    low_mult, high_mult = UNCERTAINTY_BANDS["azure_functions"]
    estimated_monthly = EstimateRange(
        low=round(expected_cost * low_mult, 2),
        expected=round(expected_cost, 2),
        high=round(expected_cost * high_mult, 2),
        currency=params.currency,
    )

    # 6) Armar breakdown
    breakdown = []
    if free_tier_covers_all:
        breakdown.append(CostComponent(
            name="free_tier",
            expected_cost=0.0,
            formula=(
                f"{params.monthly_executions:,} ejecuciones y "
                f"{total_gb_seconds:,.0f} GB-s caen dentro del free tier "
                f"({FREE_EXECUTIONS:,} ejecuciones + {FREE_GB_SECONDS:,} GB-s)"
            ),
            source="free_tier",
        ))
    else:
        breakdown.append(CostComponent(
            name="executions",
            expected_cost=round(executions_cost, 4),
            formula=(
                f"max(0, {params.monthly_executions:,} - {FREE_EXECUTIONS:,}) "
                f"/ 1M × ${price_per_million_executions:.4f} = "
                f"${executions_cost:.4f}"
            ),
            source="azure_retail_prices",
        ))
        breakdown.append(CostComponent(
            name="compute_gb_seconds",
            expected_cost=round(compute_cost, 4),
            formula=(
                f"max(0, {total_gb_seconds:,.0f} - {FREE_GB_SECONDS:,}) "
                f"GB-s × ${price_per_gb_second} = ${compute_cost:.4f}"
            ),
            source="azure_retail_prices",
        ))

    # 7) Armar handoff_back
    handoff_back = HandoffBack(
        status="completed",
        service="azure_functions",
        estimated_monthly_usd={
            "low": estimated_monthly.low,
            "expected": estimated_monthly.expected,
            "high": estimated_monthly.high,
        },
        assumptions_count=len(params.assumptions),
        next_suggested_action="open_azure_calculator" if expected_cost > 50 else "done",
    )

    return EstimateResponse(
        service="azure_functions",
        pricing_model="consumption",
        region=params.region,
        estimated_monthly=estimated_monthly,
        breakdown=breakdown,
        assumptions=params.assumptions,
        inputs_used={
            "monthly_executions": params.monthly_executions,
            "avg_duration_ms": params.avg_duration_ms,
            "memory_mb": params.memory_mb,
            "memory_mb_billed": memory_mb_billed,
            "total_gb_seconds": round(total_gb_seconds, 2),
            "billable_executions": billable_executions,
            "billable_gb_seconds": round(billable_gb_seconds, 2),
            "price_per_million_executions": round(price_per_million_executions, 6),
            "price_per_gb_second": price_per_gb_second,
            "free_tier_covers_all": free_tier_covers_all,
        },
        disclaimer=DISCLAIMER,
        official_calculator_url=OFFICIAL_CALCULATOR["azure_functions"],
        handoff_back=handoff_back,
    )


# Endpoints — utilidad y meta
@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "version": "1.0.0", "supported_services": list(SUPPORTED_SERVICES)}


@app.get(
    "/regions",
    tags=["meta"],
    summary="list_azure_regions",
    description="Lista de regiones de Azure soportadas en formato armRegionName.",
)
def list_regions():
    return {
        "regions": [
            {"armRegionName": "eastus",         "location": "East US"},
            {"armRegionName": "eastus2",        "location": "East US 2"},
            {"armRegionName": "westus",         "location": "West US"},
            {"armRegionName": "westus2",        "location": "West US 2"},
            {"armRegionName": "westeurope",     "location": "West Europe"},
            {"armRegionName": "northeurope",    "location": "North Europe"},
            {"armRegionName": "southcentralus", "location": "South Central US"},
            {"armRegionName": "brazilsouth",    "location": "Brazil South"},
            {"armRegionName": "australiaeast",  "location": "Australia East"},
            {"armRegionName": "southeastasia",  "location": "Southeast Asia"},
        ]
    }


@app.get(
    "/debug/meters",
    tags=["meta"],
    summary="debug_azure_meters",
    description=(
        "List of meters avaiblables in Azure Retail API filtered by region and product"
    ),
)
def debug_meters(region: str = "eastus", product_name: str = "Functions"):
    items = _query_azure_prices(
        f"serviceFamily eq 'Compute' "
        f"and armRegionName eq '{region}' "
        f"and contains(productName, '{product_name}') "
        f"and priceType eq 'Consumption'",
        "USD",
    )
    return {
        "region": region,
        "product_name_filter": product_name,
        "count": len(items),
        "meters": [
            {
                "meterName": i["meterName"],
                "productName": i["productName"],
                "retailPrice": i["retailPrice"],
                "unitOfMeasure": i["unitOfMeasure"],
                "skuName": i.get("skuName", ""),
                "armSkuName": i.get("armSkuName", ""),
            }
            for i in items
        ],
    }


# Endpoints — pricing didáctico
@app.get(
    "/pricing/azure_functions",
    tags=["pricing"],
    summary="get_azure_functions_pricing_info",
    description=(
        "Devuelve los coeficientes vivos de Azure Functions Consumption Plan, "
        "los inputs requeridos para cotizar, la banda de incertidumbre aplicada "
        "y el link a la calculadora oficial. El agente llama a este endpoint "
        "SOLO cuando el usuario pregunta '¿cómo se calcula?' o '¿de dónde "
        "sale ese número?'. No es parte del flujo normal de cotización."
    ),
)
def get_functions_pricing_info(region: str = "eastus", currency: str = "USD"):
    try:
        price_per_10_executions = fetch_functions_price("Total Executions", region, currency)
        price_per_gb_second = fetch_functions_price("Execution Time", region, currency)
    except HTTPException:
        # Si la API de Azure falla, devolvemos solo metadata sin coeficientes vivos
        price_per_10_executions = None
        price_per_gb_second = None

    return {
        "service": "azure_functions",
        "pricing_model": "consumption",
        "region": region,
        "currency": currency,
        "required_inputs": [
            {
                "name": "monthly_executions",
                "type": "integer",
                "unit": "executions/month",
                "description": "Número total de invocaciones por mes.",
                "derivable_from": ["latencia_arranque", "escala_automatica"],
            },
            {
                "name": "avg_duration_ms",
                "type": "integer",
                "unit": "milliseconds",
                "description": "Duración promedio de cada ejecución.",
                "derivable_from": ["latencia_arranque"],
            },
            {
                "name": "memory_mb",
                "type": "integer",
                "unit": "MB",
                "description": "Memoria asignada. Azure factura en bloques de 128MB.",
                "derivable_from": [],
                "default": 128,
            },
            {
                "name": "region",
                "type": "string",
                "unit": "armRegionName",
                "description": "Región de Azure.",
                "derivable_from": [],
                "default": "eastus",
            },
        ],
        "coefficients": {
            "price_per_million_executions": (
                round(price_per_10_executions * 100_000, 6)
                if price_per_10_executions else None
            ),
            "price_per_gb_second": price_per_gb_second,
            "free_executions_per_month": FREE_EXECUTIONS,
            "free_gb_seconds_per_month": FREE_GB_SECONDS,
            "memory_block_mb": MEMORY_BLOCK_MB,
        },
        "uncertainty_band": {
            "low_multiplier": UNCERTAINTY_BANDS["azure_functions"][0],
            "high_multiplier": UNCERTAINTY_BANDS["azure_functions"][1],
            "rationale": (
                "Banda amplia (±30-40%) porque el tráfico esperado es el input "
                "más ambiguo en respuestas conversacionales del deep dive."
            ),
        },
        "official_calculator_url": OFFICIAL_CALCULATOR["azure_functions"],
        "docs_url": DOCS_URL["azure_functions"],
    }


# Endpoint — cálculo tipado de Azure Functions
@app.post(
    "/estimate/functions",
    tags=["estimate"],
    summary="estimate_azure_functions_monthly_cost",
    description=(
        "Calcula el costo mensual estimado de Azure Functions en plan Consumption. "
        "Requiere inputs YA TIPADOS — el agente debe normalizar las respuestas del "
        "deep dive antes de llamar a este endpoint. Devuelve un rango (low/expected/"
        "high), breakdown detallado, assumptions, y handoff_back para el orquestador. "
        "Incluye free tier de 1M ejecuciones + 400k GB-s por mes."
    ),
    response_model=EstimateResponse,
)
def estimate_functions(params: FunctionsEstimateRequest) -> EstimateResponse:
    return compute_functions_estimate(params)


# Endpoint — router de handoff
@app.post(
    "/estimate/from-handoff",
    tags=["estimate"],
    summary="route_handoff_from_cu01",
    description=(
        "Puerta única para el orquestador. Recibe el payload completo de CU-01, "
        "valida que el servicio esté soportado y devuelve metadata para que el "
        "agente CU-02 pueda continuar con NORMALIZE. NO ejecuta el cálculo: "
        "después de llamar a este endpoint, el agente normaliza las respuestas "
        "del deep dive y llama a /estimate/functions con inputs tipados. "
        "Si el servicio no está soportado, devuelve status=unsupported_service "
        "con HTTP 200 (no es un error, es información para el agente)."
    ),
    response_model=FromHandoffResponse,
)
def route_handoff(payload: FromHandoffRequest) -> FromHandoffResponse:
    service = payload.handoff.params.service
    deep_dive_keys = list(payload.user_context.deep_dive_answers.keys())

    if service not in SUPPORTED_SERVICES:
        return FromHandoffResponse(
            status="unsupported_service",
            service=service,
            message=(
                f"En esta versión del estimador solo está soportado Azure Functions. "
                f"El servicio '{service}' va a estar disponible en próximas versiones. "
                f"Por ahora, te recomiendo usar la calculadora oficial de Azure: "
                f"https://azure.microsoft.com/pricing/calculator/"
            ),
            supported_services=list(SUPPORTED_SERVICES),
            deep_dive_keys_present=deep_dive_keys,
        )

    return FromHandoffResponse(
        status="ready_for_estimate",
        service=service,
        message=(
            "Servicio soportado. Procedé con NORMALIZE de las respuestas del "
            "deep dive y luego llamá a POST /estimate/functions con los inputs "
            "tipados."
        ),
        required_inputs=payload.handoff.required_inputs,
        deep_dive_keys_present=deep_dive_keys,
        supported_services=list(SUPPORTED_SERVICES),
        next_endpoint="/estimate/functions",
    )
