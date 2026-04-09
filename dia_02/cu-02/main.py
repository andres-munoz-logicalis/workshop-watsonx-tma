"""
CU-02 — API de cotización de servicios Azure
Consulta la Azure Retail Prices API y calcula costos mensuales estimados.
Soporta múltiples servicios: Functions, Virtual Machines
"""

import os
import logging
import math
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

load_dotenv()
logging.basicConfig(level=logging.INFO)

API_PUBLIC_URL    = os.getenv("API_PUBLIC_URL", "http://localhost:8081")
AZURE_PRICES_URL  = "https://prices.azure.com/api/retail/prices"
HOURS_PER_MONTH   = 730  # horas en un mes promedio (365 días / 12 × 24)

app = FastAPI(
    title="CU-02 Azure Pricing API",
    description="Calcula costos mensuales estimados de servicios Azure usando la Azure Retail Prices API.",
    version="1.0.0",
    servers=[{"url": API_PUBLIC_URL}],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Modelos

class FunctionParams(BaseModel):
    region: str = Field(
        default="eastus",
        description="Región de Azure en formato armRegionName. Ej: eastus, westeurope, brazilsouth",
        examples=["eastus", "westeurope", "brazilsouth"],
    )
    monthly_executions: int = Field(
        description="Número de invocaciones por mes",
        examples=[1_000_000, 5_000_000, 50_000_000],
        gt=0,
    )
    avg_duration_ms: int = Field(
        description="Duración promedio de cada ejecución en milisegundos",
        examples=[200, 500, 1000],
        gt=0,
    )
    memory_mb: int = Field(
        description="Memoria asignada a la función en MB. Azure factura en bloques de 128MB.",
        examples=[128, 256, 512, 1024],
        gt=0,
    )
    currency: str = Field(
        default="USD",
        description="Código de moneda ISO 4217",
        examples=["USD", "EUR", "ARS"],
    )


class FunctionPriceBreakdown(BaseModel):
    executions_cost: float
    compute_cost: float
    total_cost: float
    currency: str
    free_tier_applied: bool
    details: dict


class VMParams(BaseModel):
    sku_name: str = Field(
        description=(
            "SKU de la VM en formato armSkuName. Ej: Standard_D2s_v3, Standard_B2ms, Standard_E4s_v5. "
            "Usá GET /skus/vms?region=eastus&search=D2 para buscar SKUs disponibles."
        ),
        examples=["Standard_D2s_v3", "Standard_B2ms", "Standard_E4s_v5"],
    )
    region: str = Field(
        default="eastus",
        description="Región de Azure en formato armRegionName.",
        examples=["eastus", "westeurope", "brazilsouth"],
    )
    os_type: str = Field(
        default="linux",
        description="Sistema operativo. 'linux' o 'windows'. Afecta el precio.",
        examples=["linux", "windows"],
    )
    hours_per_month: int = Field(
        default=HOURS_PER_MONTH,
        description=f"Horas de uso por mes. Default {HOURS_PER_MONTH} (mes completo). Usá menos para VMs que no corren 24/7.",
        examples=[730, 160, 480],
        gt=0,
        le=744,
    )
    currency: str = Field(
        default="USD",
        description="Código de moneda ISO 4217",
        examples=["USD", "EUR", "ARS"],
    )


class VMPriceBreakdown(BaseModel):
    compute_cost: float
    total_cost: float
    currency: str
    details: dict


# Helpers genéricos

def _query_azure_prices(filter_query: str, currency: str) -> list:
    """Ejecuta un query contra la Azure Retail Prices API y devuelve los Items con precio > 0."""
    params = {
        "$filter": filter_query,
        "currencyCode": f"'{currency}'",
    }
    try:
        response = requests.get(AZURE_PRICES_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error consultando Azure Pricing API: {str(e)}")

    return [i for i in data.get("Items", []) if i["retailPrice"] > 0]


def fetch_azure_price(
    meter_name_contains: str,
    region: str,
    currency: str,
    product_name_contains: str = "",
    service_family: str = "Compute",
    price_type: str = "Consumption",
) -> float:
    """
    Función genérica para consultar precios por meterName + productName.
    Usada principalmente por Azure Functions.
    """
    filters = [
        f"serviceFamily eq '{service_family}'",
        f"armRegionName eq '{region}'",
        f"contains(meterName, '{meter_name_contains}')",
        f"priceType eq '{price_type}'",
    ]
    if product_name_contains:
        filters.append(f"contains(productName, '{product_name_contains}')")

    items = _query_azure_prices(" and ".join(filters), currency)

    if not items:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No se encontraron precios para meterName contains='{meter_name_contains}' "
                f"productName contains='{product_name_contains}' en región='{region}'. "
                f"Usá GET /debug/meters?region={region}&product_name={product_name_contains} "
                f"para ver los meters disponibles."
            ),
        )

    logging.info(f"Meter: {items[0]['meterName']} | {items[0]['productName']} | {items[0]['retailPrice']} {currency}")
    return items[0]["retailPrice"]


def fetch_vm_price(sku_name: str, region: str, os_type: str, currency: str) -> dict:
    """
    Busca el precio de una VM por armSkuName exacto.
    Para Windows filtra los productos que contienen 'Windows'.
    Para Linux excluye los que contienen 'Windows' (sin licencia).
    Excluye precios Spot y DevTest.
    """
    filter_query = (
        f"serviceName eq 'Virtual Machines' "
        f"and armRegionName eq '{region}' "
        f"and armSkuName eq '{sku_name}' "
        f"and priceType eq 'Consumption'"
    )

    items = _query_azure_prices(filter_query, currency)

    if not items:
        raise HTTPException(
            status_code=404,
            detail=(
                f"SKU '{sku_name}' no encontrado en región '{region}'. "
                f"Usá GET /skus/vms?region={region}&search=<término> para buscar SKUs disponibles."
            ),
        )

    # Filtrar Spot, Low Priority y DevTest — solo pay-as-you-go regular
    items = [
        i for i in items
        if "Spot" not in i["meterName"]
        and "Low Priority" not in i["meterName"]
        and i["type"] not in ("DevTestConsumption", "Reservation")
    ]

    if not items:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No se encontraron precios pay-as-you-go regulares para '{sku_name}' en '{region}'. "
                f"Este SKU puede estar descontinuado o solo disponible como Low Priority/Spot. "
                f"Probá con una versión más nueva, por ejemplo reemplazando '_v3' por '_v5'."
            ),
        )

    # Separar Linux vs Windows por productName
    if os_type.lower() == "windows":
        os_items = [i for i in items if "Windows" in i.get("productName", "")]
    else:
        os_items = [i for i in items if "Windows" not in i.get("productName", "")]

    if not os_items:
        # Fallback: si no hay match exacto de OS, usar el primero disponible
        os_items = items
        logging.warning(f"No se encontró precio específico para OS '{os_type}' en {sku_name}. Usando primer resultado.")

    item = os_items[0]
    logging.info(f"VM: {item['armSkuName']} | {item['productName']} | ${item['retailPrice']}/h {currency}")
    return {
        "price_per_hour": item["retailPrice"],
        "sku_name": item["armSkuName"],
        "meter_name": item["meterName"],
        "product_name": item["productName"],
    }


def round_memory_to_block(memory_mb: int) -> int:
    """Azure factura memoria en bloques de 128MB, redondeando hacia arriba."""
    return math.ceil(memory_mb / 128) * 128


# Endpoints generales

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get(
    "/regions",
    summary="regions_avaiblables",
    description="List of Azure regions",
)
def list_regions():
    return {
        "regions": [
            {"armRegionName": "eastus",         "location": "East US"},
            {"armRegionName": "eastus2",        "location": "East US 2"},
            {"armRegionName": "westus",         "location": "West US"},
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
    summary="check_meters_available",
    description="List meters filtered by region and product name. Helpfull for identify meter names.",
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


@app.get(
    "/skus/vms",
    summary="Buscar SKUs de Virtual Machines disponibles",
    description=(
        "Busca SKUs de VMs disponibles en una región. "
        "Usá el campo 'armSkuName' como valor para el parámetro 'sku_name' en /quote/vms."
    ),
)
def search_vm_skus(
    region: str = Query(default="eastus", description="Región de Azure"),
    search: str = Query(default="D2s", description="Término de búsqueda en el nombre del SKU. Ej: D2s, B2ms, E4"),
    os_type: str = Query(default="linux", description="'linux' o 'windows'"),
):
    filter_query = (
        f"serviceName eq 'Virtual Machines' "
        f"and armRegionName eq '{region}' "
        f"and contains(armSkuName, '{search}') "
        f"and priceType eq 'Consumption'"
    )
    all_items = _query_azure_prices(filter_query, "USD")

    # Filtrar Spot, Low Priority y DevTest — solo queremos pay-as-you-go regular
    items = [
        i for i in all_items
        if "Spot" not in i["meterName"]
        and "Low Priority" not in i["meterName"]
        and i["type"] not in ("DevTestConsumption", "Reservation")
    ]

    # Filtrar por OS
    if os_type.lower() == "windows":
        items = [i for i in items if "Windows" in i.get("productName", "")]
    else:
        items = [i for i in items if "Windows" not in i.get("productName", "")]

    # Deduplicar por armSkuName
    seen = set()
    unique = []
    for i in items:
        if i["armSkuName"] not in seen:
            seen.add(i["armSkuName"])
            unique.append(i)

    return {
        "region": region,
        "os_type": os_type,
        "search": search,
        "count": len(unique),
        "skus": [
            {
                "armSkuName": i["armSkuName"],
                "meterName": i["meterName"],
                "productName": i["productName"],
                "price_per_hour": i["retailPrice"],
                "currency": "USD",
            }
            for i in unique
        ],
    }


# /quote/functions

@app.post(
    "/quote/functions",
    summary="quote_azure_functions_consumption_plan",
    description=(
        "Calculate the estimated monthly cost of Azure Functions in the Consumption plan."
        "The first 1 million executions and the first 400,000 GB-seconds are free per month."
    ),
    response_model=FunctionPriceBreakdown,
)
def quote_functions(params: FunctionParams):

    price_per_million_executions = fetch_azure_price(
        "Standard Total Executions", params.region, params.currency,
        product_name_contains="Functions",
    )
    price_per_gb_second = fetch_azure_price(
        "Standard Execution Time", params.region, params.currency,
        product_name_contains="Functions",
    )

    memory_gb        = round_memory_to_block(params.memory_mb) / 1024
    duration_seconds = params.avg_duration_ms / 1000
    total_gb_seconds = params.monthly_executions * memory_gb * duration_seconds

    FREE_EXECUTIONS = 1_000_000
    FREE_GB_SECONDS = 400_000

    billable_executions = max(0, params.monthly_executions - FREE_EXECUTIONS)
    billable_gb_seconds = max(0, total_gb_seconds - FREE_GB_SECONDS)
    free_tier_applied   = (params.monthly_executions <= FREE_EXECUTIONS) or (total_gb_seconds <= FREE_GB_SECONDS)

    # La API devuelve precio por 10 ejecuciones → convertir a por millón
    price_per_million = price_per_million_executions * 100_000
    executions_cost   = (billable_executions / 1_000_000) * price_per_million
    compute_cost      = billable_gb_seconds * price_per_gb_second
    total_cost        = executions_cost + compute_cost

    return FunctionPriceBreakdown(
        executions_cost=round(executions_cost, 4),
        compute_cost=round(compute_cost, 4),
        total_cost=round(total_cost, 4),
        currency=params.currency,
        free_tier_applied=free_tier_applied,
        details={
            "region": params.region,
            "monthly_executions": params.monthly_executions,
            "billable_executions": billable_executions,
            "avg_duration_ms": params.avg_duration_ms,
            "memory_mb_billed": round_memory_to_block(params.memory_mb),
            "total_gb_seconds": round(total_gb_seconds, 2),
            "billable_gb_seconds": round(billable_gb_seconds, 2),
            "price_per_million_executions": round(price_per_million, 6),
            "price_per_gb_second": price_per_gb_second,
            "free_tier": {
                "free_executions": FREE_EXECUTIONS,
                "free_gb_seconds": FREE_GB_SECONDS,
            },
        },
    )


# /quote/vms

@app.post(
    "/quote/vms",
    summary="quote_azure_virtual_machine_payg",
    description=(
        "Calculate the estimated monthly cost of a VM in Azure using the pay-as-you-go pricing"
        "The price is hourly × hours of usage. No free tier."
        "Use GET /skus/vms?region=eastus&search=D2s to find the correct armSkuName."
    ),
    response_model=VMPriceBreakdown,
)
def quote_vms(params: VMParams):

    vm_price = fetch_vm_price(
        sku_name=params.sku_name,
        region=params.region,
        os_type=params.os_type,
        currency=params.currency,
    )

    compute_cost = vm_price["price_per_hour"] * params.hours_per_month
    total_cost   = compute_cost  # En el futuro: + storage_cost + network_cost

    return VMPriceBreakdown(
        compute_cost=round(compute_cost, 4),
        total_cost=round(total_cost, 4),
        currency=params.currency,
        details={
            "sku_name": vm_price["sku_name"],
            "meter_name": vm_price["meter_name"],
            "product_name": vm_price["product_name"],
            "region": params.region,
            "os_type": params.os_type,
            "price_per_hour": vm_price["price_per_hour"],
            "hours_per_month": params.hours_per_month,
            "note": (
                "Costo estimado solo de cómputo (CPU+RAM). "
                "Storage, networking y licencias se facturan por separado."
            ),
        },
    )
