"""
Mini plataforma de monitoreo de infraestructura - IT Tech Service Specialist prep project.

Qué hace:
- Expone un endpoint "/" que muestra qué instancia EC2 respondió (para demostrar
  visualmente que el Application Load Balancer está repartiendo tráfico entre
  varias instancias del Auto Scaling Group).
- Expone "/health" para que el Target Group del ALB haga el health check.
- Expone "/report" que simula el análisis de TPY que hacías en Lenovo: lee un CSV
  de resultados de prueba, calcula el % de éxito y las principales fallas con
  Pandas, y sube el reporte como JSON a un bucket de S3 usando un rol de IAM
  (sin credenciales hardcodeadas -> boto3 las toma del rol de la instancia).

Variables de entorno esperadas:
  S3_BUCKET   -> nombre del bucket donde se sube el reporte (opcional; si no
                 está definida, /report solo calcula localmente y no sube nada)
  AWS_REGION  -> región (opcional, default us-east-1)
"""

import os
import json
import socket
from datetime import datetime, timezone
import pandas as pd
import requests
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

S3_BUCKET = os.environ.get("S3_BUCKET")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "sample_test_logs.csv")

EC2_METADATA_TOKEN_URL = "http://169.254.169.254/latest/api/token"
EC2_METADATA_URL = "http://169.254.169.254/latest/meta-data/"


def get_ec2_metadata():
    """Intenta leer instance-id y AZ del servicio de metadata de EC2 (IMDSv2).
    Si no corre en EC2 (ej. pruebas locales), regresa valores de fallback."""
    try:
        token = requests.put(
            EC2_METADATA_TOKEN_URL,
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
            timeout=0.3,
        ).text
        headers = {"X-aws-ec2-metadata-token": token}
        instance_id = requests.get(EC2_METADATA_URL + "instance-id", headers=headers, timeout=0.3).text
        az = requests.get(EC2_METADATA_URL + "placement/availability-zone", headers=headers, timeout=0.3).text
        return instance_id, az
    except Exception:
        return f"local-{socket.gethostname()}", "local-dev"

def report_metrics():
    df = pd.read_csv(DATA_PATH)
    df_fallas_por_zona = df[["estacion","ubicacion"]]
    total = len(df)
    passed = int((df["resultado"] == "PASS").sum())
    failed = total - passed
    pass_rate = round(passed / total * 100, 1) if total else 0

    return df, df_fallas_por_zona, total, passed, failed, pass_rate



@app.route("/")
def index():
    instance_id, az = get_ec2_metadata()
    html = """
    <html>
    <head><title>Infra Monitor</title></head>
    <body style="font-family: sans-serif; padding: 40px;">
      <h1>Servidor  Activo</h1>
      <p><b>Instance ID:</b> {{ instance_id }}</p>
      <p><b>Availability Zone:</b> {{ az }}</p>
      <p><b>Hora del servidor (UTC):</b> {{ now }}</p>
      <p>Refresca varias veces la página del Load Balancer: si el ASG tiene
      más de una instancia, deberías ver cambiar el Instance ID.</p>
      <p><a href="/report">Ver reporte de fallas (simulación TPY)</a></p>
    </body>
    </html>
    """
    return render_template_string(html, instance_id=instance_id, az=az, now=datetime.now(timezone.utc).isoformat())


@app.route("/health")
def health():
    return jsonify(status="ok"), 200


@app.route("/report")
def report():
    df, df_fallas_por_zona, total, passed, failed, pass_rate = report_metrics()

    top_failures = (
        df[df["resultado"] == "FAIL"]["causa_falla"]
        .value_counts()
        .head(5)
        .to_dict()
    )

    summary = {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "total_pruebas": total,
        "pass": passed,
        "fail": failed,
        "pass_rate_pct": pass_rate,
        "top_causas_falla": top_failures,
    }

    html = """
    <html>
    <head><title>Resumen de Fallas</title></head>
    <body style="font-family: sans-serif; padding: 40px;">
        <h1>Resumen de Fallas</h1>
        <p><b>Total de unidades probadas:</b> {{ total }}, <b>Total de unidades pasadas:</b> {{ passed }}, <b>Total de unidades fallidas:</b> {{ failed }}</p>
        <p><b>Porcentaje de éxito:</b> {{ pass_rate }}%</p>
        <h2>Top 5 causas de falla</h2>
        <ul>
        {% for causa, count in top_failures.items() %}
            <li>{{ causa }}: {{ count }} fallas</li>
        {% endfor %}
        </ul>
        <p><a href="/">Regresar a pagina principal</a></p>
    </body>
    """
    
    return render_template_string(html, total=total, passed=passed, failed=failed, pass_rate=pass_rate, top_failures=top_failures)

    uploaded = False
    if S3_BUCKET:
        try:
            import boto3

            s3 = boto3.client("s3", region_name=AWS_REGION)
            key = f"reportes/tpy_report_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.json"
            s3.put_object(Bucket=S3_BUCKET, Key=key, Body=json.dumps(summary, indent=2))
            summary["s3_key"] = key
            uploaded = True
        except Exception as e:
            summary["s3_error"] = str(e)

    summary["subido_a_s3"] = uploaded
    return jsonify(summary)



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
