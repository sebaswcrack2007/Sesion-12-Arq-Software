# ingesta_flask.py
# Servicio Flask con extracción W3C Trace Context e inyección en comentario SQL (Paso 1.5)
import logging
import json
from flask import Flask, request
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.propagate import extract, inject

# 1. Configurar OpenTelemetry
provider = TracerProvider(resource=Resource.create({
    "service.name": "ingesta-service",
    "service.namespace": "metromio"
}))
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("ingesta-service")

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")

@app.post("/telemetria")
def recibir():
    # 2. Extraer el contexto W3C (traceparent y tracestate) de las cabeceras HTTP entrantes
    ctx = extract({k.lower(): v for k, v in request.headers.items()})
    
    with tracer.start_as_current_span("ingesta.procesar", context=ctx, kind=trace.SpanKind.SERVER) as span:
        trace_id = format(span.get_span_context().trace_id, "032x")
        datos = request.get_json()
        span.set_attribute("bus.id", datos["bus_id"])
        
        # 3. Crear span hijo para la operación de base de datos e inyectar contexto en SQL
        with tracer.start_as_current_span("timescaledb.insert", kind=trace.SpanKind.CLIENT) as db_span:
            carrier = {}
            inject(carrier)  # Genera el traceparent hijo para TimescaleDB
            
            sql = (
                f"/*traceparent='{carrier['traceparent']}'*/ "
                "INSERT INTO telemetria (bus_id, lat, lon) VALUES (%s, %s, %s)"
            )
            db_span.set_attribute("db.statement", sql)
            # En producción: cur.execute(sql, (datos["bus_id"], datos["lat"], datos["lon"]))
            print(f"\n[SQL EJECUTADO] -> {sql}\n")

        # 4. Log estructurado correlacionado con el mismo trace_id
        log_evento = json.dumps({
            "level": "INFO",
            "service": "ingesta-service",
            "msg": "Telemetria guardada en TimescaleDB",
            "bus_id": datos["bus_id"],
            "trace_id": trace_id
        })
        app.logger.info(log_evento)
        
        return {"status": "ok", "trace_id": trace_id, "sql_generado": sql}, 201

if __name__ == "__main__":
    # Ejecuta una prueba automática interna usando el cliente de pruebas de Flask
    with app.test_client() as client:
        headers_gateway = {
            "traceparent": "00-9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c-30c3d4e5f6030303-01",
            "tracestate": "metromio=bus457"
        }
        payload = {"bus_id": "MIO-T31-0457", "lat": 3.4516, "lon": -76.5320}
        resp = client.post("/telemetria", json=payload, headers=headers_gateway)
        print("[RESPUESTA HTTP 201] ->", resp.get_json())
