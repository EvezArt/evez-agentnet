"""Sentry instrumentation wrapper for EVEZ AGI pipeline.
DSN target: steven-crawford-maggard.sentry.io
"""
import os, functools, time
import sentry_sdk
from sentry_sdk.tracing import Transaction

def init_sentry():
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN", ""),
        environment=os.getenv("ENVIRONMENT", "production"),
        release=os.getenv("VERCEL_GIT_COMMIT_SHA", "local"),
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        send_default_pii=False,
    )

def trace_pipeline(name: str):
    """Decorator: wraps any pipeline function in a Sentry transaction."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            with sentry_sdk.start_transaction(op="pipeline", name=name) as tx:
                t0 = time.perf_counter()
                try:
                    result = fn(*args, **kwargs)
                    tx.set_status("ok")
                    return result
                except Exception as e:
                    tx.set_status("internal_error")
                    sentry_sdk.capture_exception(e)
                    raise
                finally:
                    tx.set_measurement("latency_ms", (time.perf_counter()-t0)*1000, "millisecond")
        return wrapper
    return decorator

def capture_pipeline_result(run_id: str, model: str, latency_ms: float, ok: bool):
    sentry_sdk.set_tag("run_id", run_id[:12])
    sentry_sdk.set_tag("model", model)
    sentry_sdk.set_measurement("latency_ms", latency_ms, "millisecond")
    level = "info" if ok else "error"
    sentry_sdk.capture_message(f"EVEZ-AGI run {run_id[:12]} [{model}] {latency_ms:.0f}ms", level=level)
