# traza_metromio.py
# Simula los 4 saltos de MetroMIO-IoT con OpenTelemetry
import time
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.propagate import inject, extract

# Configuración del proveedor de trazas y exportador a consola
provider = TracerProvider(resource=Resource.create({"service.name": "metromio-ingesta"}))
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("metromio.lab")

def consultar_timescaledb(headers_entrantes: dict):
    # 1) EXTRAER contexto que viene desde el servicio de ingesta
    ctx = extract(headers_entrantes)
    with tracer.start_as_current_span("salto4.timescaledb.insert", context=ctx) as span:
        span.set_attribute("db.system", "postgresql")
        span.set_attribute("db.operation", "INSERT")
        time.sleep(0.003)  # 3 ms

def servicio_ingesta(headers_entrantes: dict):
    # EXTRAER contexto del traceparent que llega del API Gateway
    ctx = extract(headers_entrantes)
    with tracer.start_as_current_span("salto3.ingesta-service", context=ctx):
        time.sleep(0.045)  # 45 ms
        
        # 2) INYECTAR el contexto actual para la llamada descendente hacia la BD
        headers_salida = {}
        inject(headers_salida)
        print(">> traceparent hacia la BD:", headers_salida["traceparent"])
        consultar_timescaledb(headers_salida)

# Inicio de la traza (Root Span en el Bus)
with tracer.start_as_current_span("root.bus-telemetria") as root:
    root.set_attribute("bus.id", "MIO-T31-0457")
    
    with tracer.start_as_current_span("salto1.edge-mqtt-k3s"):
        time.sleep(0.012)  # 12 ms
        
    with tracer.start_as_current_span("salto2.api-gateway-mtls"):
        time.sleep(0.008)  # 8 ms
        
        # Inyectar contexto en los encabezados antes de llamar a ingesta
        h = {}
        inject(h)
        print(">> traceparent hacia ingesta:", h["traceparent"])
        servicio_ingesta(h)
