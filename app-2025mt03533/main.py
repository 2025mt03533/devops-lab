import os
import socket

import psutil
from flask import Flask, jsonify

# Values are injected as environment variables (defaults for local runs)
APP_VERSION = os.getenv('APP_VERSION', '1.0')
APP_TITLE = os.getenv('APP_TITLE', 'Devops for Cloud Assignment')
POD_NAME = os.getenv('POD_NAME', socket.gethostname())

app = Flask(__name__)
request_counter = None


def setup_metrics():
    """Enable OTLP metrics only when a collector endpoint is configured."""
    global request_counter
    if not os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT'):
        return
    from opentelemetry import metrics
    from opentelemetry.metrics import Observation
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter

    resource = Resource.create({
        'service.name': 'flask-app',
        'service.instance.id': POD_NAME,
    })
    # Endpoint is read from OTEL_EXPORTER_OTLP_ENDPOINT (/v1/metrics is appended)
    reader = PeriodicExportingMetricReader(OTLPMetricExporter(), export_interval_millis=10000)
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))
    meter = metrics.get_meter('flask-app')

    proc = psutil.Process()
    proc.cpu_percent(None)  # prime the counter
    attrs = {'pod': POD_NAME}

    def cpu_cb(options):
        yield Observation(proc.cpu_percent(None), attrs)

    def mem_cb(options):
        yield Observation(proc.memory_info().rss, attrs)

    request_counter = meter.create_counter(
        'get_info_requests', description='Requests received by /get_info')
    meter.create_observable_gauge(
        'app_cpu_usage_percent', callbacks=[cpu_cb], description='Process CPU percent')
    meter.create_observable_gauge(
        'app_memory_usage_bytes', callbacks=[mem_cb], description='Process RSS memory')


setup_metrics()


@app.route('/get_info')
def get_info():
    if request_counter is not None:
        request_counter.add(1, {'pod': POD_NAME, 'endpoint': '/get_info'})
    return jsonify({'APP_VERSION': APP_VERSION, 'APP_TITLE': APP_TITLE})


if __name__ == '__main__':
    print(f'Starting {APP_TITLE} v{APP_VERSION} on pod {POD_NAME}', flush=True)
    app.run(host='0.0.0.0', port=8000)
