"""
core/metrics.py — Prometheus metrics collection for Lazarus Protocol.

Provides:
- API request metrics
- Storage operation metrics
- Email sending metrics
- System metrics
- Business metrics
- Metrics server for Prometheus scraping
"""

import os
import time
import psutil
from functools import wraps
from typing import Callable, Optional
from datetime import datetime

try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Info, start_http_server,
        CollectorRegistry, generate_latest
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    print("Warning: prometheus_client not available. Metrics collection disabled.")


# Create a custom registry
if PROMETHEUS_AVAILABLE:
    registry = CollectorRegistry()
else:
    registry = None


# ---------------------------------------------------------------------------
# API Request Metrics
# ---------------------------------------------------------------------------

if PROMETHEUS_AVAILABLE:
    api_requests_total = Counter(
        'api_requests_total',
        'Total API requests',
        ['method', 'endpoint', 'status'],
        registry=registry
    )

    api_request_duration = Histogram(
        'api_request_duration_seconds',
        'API request duration',
        ['method', 'endpoint'],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
        registry=registry
    )
else:
    api_requests_total = None
    api_request_duration = None


# ---------------------------------------------------------------------------
# Storage Metrics
# ---------------------------------------------------------------------------

if PROMETHEUS_AVAILABLE:
    storage_uploads_total = Counter(
        'storage_uploads_total',
        'Total storage uploads',
        ['provider', 'status'],
        registry=registry
    )

    storage_upload_duration = Histogram(
        'storage_upload_duration_seconds',
        'Storage upload duration',
        ['provider'],
        buckets=(1, 5, 10, 30, 60, 120, 300, 600),
        registry=registry
    )

    storage_downloads_total = Counter(
        'storage_downloads_total',
        'Total storage downloads',
        ['provider', 'status'],
        registry=registry
    )

    storage_download_duration = Histogram(
        'storage_download_duration_seconds',
        'Storage download duration',
        ['provider'],
        buckets=(1, 5, 10, 30, 60, 120, 300, 600),
        registry=registry
    )
else:
    storage_uploads_total = None
    storage_upload_duration = None
    storage_downloads_total = None
    storage_download_duration = None


# ---------------------------------------------------------------------------
# Email Metrics
# ---------------------------------------------------------------------------

if PROMETHEUS_AVAILABLE:
    email_sends_total = Counter(
        'email_sends_total',
        'Total emails sent',
        ['type', 'status'],
        registry=registry
    )

    email_send_duration = Histogram(
        'email_send_duration_seconds',
        'Email send duration',
        ['type'],
        buckets=(1, 2, 5, 10, 30, 60),
        registry=registry
    )
else:
    email_sends_total = None
    email_send_duration = None


# ---------------------------------------------------------------------------
# System Metrics
# ---------------------------------------------------------------------------

if PROMETHEUS_AVAILABLE:
    memory_usage_bytes = Gauge(
        'memory_usage_bytes',
        'Memory usage in bytes',
        registry=registry
    )

    cpu_usage_percent = Gauge(
        'cpu_usage_percent',
        'CPU usage percentage',
        registry=registry
    )

    active_connections = Gauge(
        'active_connections',
        'Number of active connections',
        registry=registry
    )

    disk_usage_bytes = Gauge(
        'disk_usage_bytes',
        'Disk usage in bytes',
        ['mount_point'],
        registry=registry
    )
else:
    memory_usage_bytes = None
    cpu_usage_percent = None
    active_connections = None
    disk_usage_bytes = None


# ---------------------------------------------------------------------------
# Business Metrics
# ---------------------------------------------------------------------------

if PROMETHEUS_AVAILABLE:
    active_configurations = Gauge(
        'active_configurations',
        'Number of active configurations',
        registry=registry
    )

    pending_checkins = Gauge(
        'pending_checkins',
        'Number of pending check-ins',
        registry=registry
    )

    documents_stored = Gauge(
        'documents_stored',
        'Total number of documents stored',
        registry=registry
    )

    total_storage_bytes = Gauge(
        'total_storage_bytes',
        'Total storage used in bytes',
        registry=registry
    )
else:
    active_configurations = None
    pending_checkins = None
    documents_stored = None
    total_storage_bytes = None


# ---------------------------------------------------------------------------
# Application Info
# ---------------------------------------------------------------------------

if PROMETHEUS_AVAILABLE:
    app_info = Info(
        'application',
        'Application information',
        registry=registry
    )
else:
    app_info = None


# ---------------------------------------------------------------------------
# Metrics Recording Functions
# ---------------------------------------------------------------------------

def record_api_request(method: str, endpoint: str, status: int, duration: float):
    """Record API request metrics"""
    if not PROMETHEUS_AVAILABLE:
        return
    
    api_requests_total.labels(
        method=method,
        endpoint=endpoint,
        status=status
    ).inc()
    api_request_duration.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)


def record_storage_upload(provider: str, status: str, duration: float):
    """Record storage upload metrics"""
    if not PROMETHEUS_AVAILABLE:
        return
    
    storage_uploads_total.labels(
        provider=provider,
        status=status
    ).inc()
    storage_upload_duration.labels(
        provider=provider
    ).observe(duration)


def record_storage_download(provider: str, status: str, duration: float):
    """Record storage download metrics"""
    if not PROMETHEUS_AVAILABLE:
        return
    
    storage_downloads_total.labels(
        provider=provider,
        status=status
    ).inc()
    storage_download_duration.labels(
        provider=provider
    ).observe(duration)


def record_email_send(email_type: str, status: str, duration: float):
    """Record email send metrics"""
    if not PROMETHEUS_AVAILABLE:
        return
    
    email_sends_total.labels(
        type=email_type,
        status=status
    ).inc()
    email_send_duration.labels(
        type=email_type
    ).observe(duration)


def update_system_metrics():
    """Update system metrics"""
    if not PROMETHEUS_AVAILABLE:
        return
    
    try:
        process = psutil.Process(os.getpid())
        
        # Memory usage
        memory_usage_bytes.set(process.memory_info().rss)
        
        # CPU usage
        cpu_usage_percent.set(process.cpu_percent())
        
        # Disk usage
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_usage_bytes.labels(
                    mount_point=partition.mountpoint
                ).set(usage.used)
            except (PermissionError, OSError):
                continue
    except Exception as e:
        print(f"Error updating system metrics: {e}")


def update_business_metrics(
    active_configs: int = 0,
    pending: int = 0,
    docs: int = 0,
    storage_bytes: int = 0
):
    """Update business metrics"""
    if not PROMETHEUS_AVAILABLE:
        return
    
    active_configurations.set(active_configs)
    pending_checkins.set(pending)
    documents_stored.set(docs)
    total_storage_bytes.set(storage_bytes)


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------

def track_api_call(func: Callable) -> Callable:
    """Decorator to track API calls"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        method = kwargs.get('method', 'GET')
        endpoint = func.__name__
        
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start
            record_api_request(method, endpoint, 200, duration)
            return result
        except Exception as e:
            duration = time.time() - start
            record_api_request(method, endpoint, 500, duration)
            raise
    
    return wrapper


def track_sync_api_call(func: Callable) -> Callable:
    """Decorator to track synchronous API calls"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        method = kwargs.get('method', 'GET')
        endpoint = func.__name__
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start
            record_api_request(method, endpoint, 200, duration)
            return result
        except Exception as e:
            duration = time.time() - start
            record_api_request(method, endpoint, 500, duration)
            raise
    
    return wrapper


# ---------------------------------------------------------------------------
# Metrics Server
# ---------------------------------------------------------------------------

def start_metrics_server(port: int = 9090):
    """Start Prometheus metrics server"""
    if not PROMETHEUS_AVAILABLE:
        print("Warning: Prometheus client not available. Metrics server not started.")
        return
    
    try:
        start_http_server(port, registry=registry)
        print(f"Metrics server started on port {port}")
        
        # Set application info
        app_info.info({
            'version': os.environ.get('APP_VERSION', '1.0.0'),
            'environment': os.environ.get('ENVIRONMENT', 'development'),
            'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
            'start_time': datetime.now().isoformat()
        })
    except Exception as e:
        print(f"Error starting metrics server: {e}")


def get_metrics() -> Optional[str]:
    """Get metrics in Prometheus format"""
    if not PROMETHEUS_AVAILABLE:
        return None
    
    try:
        return generate_latest(registry).decode('utf-8')
    except Exception as e:
        print(f"Error generating metrics: {e}")
        return None


# ---------------------------------------------------------------------------
# Metrics Context Manager
# ---------------------------------------------------------------------------

class MetricsContext:
    """Context manager for tracking operation metrics"""
    
    def __init__(self, operation_type: str, labels: dict = None):
        """
        Initialize metrics context.
        
        Args:
            operation_type: Type of operation (e.g., 'api_request', 'storage_upload')
            labels: Additional labels for the metric
        """
        self.operation_type = operation_type
        self.labels = labels or {}
        self.start_time = None
        self.status = 'success'
    
    def __enter__(self):
        """Start timing operation"""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Record metrics on exit"""
        if self.start_time is None:
            return
        
        duration = time.time() - self.start_time
        
        if exc_type is not None:
            self.status = 'error'
        
        # Record based on operation type
        if self.operation_type == 'api_request':
            method = self.labels.get('method', 'GET')
            endpoint = self.labels.get('endpoint', 'unknown')
            status_code = self.labels.get('status_code', 500 if self.status == 'error' else 200)
            record_api_request(method, endpoint, status_code, duration)
        
        elif self.operation_type == 'storage_upload':
            provider = self.labels.get('provider', 'unknown')
            record_storage_upload(provider, self.status, duration)
        
        elif self.operation_type == 'storage_download':
            provider = self.labels.get('provider', 'unknown')
            record_storage_download(provider, self.status, duration)
        
        elif self.operation_type == 'email_send':
            email_type = self.labels.get('type', 'unknown')
            record_email_send(email_type, self.status, duration)
        
        return False  # Don't suppress exceptions


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------

def is_metrics_enabled() -> bool:
    """Check if metrics collection is enabled"""
    return PROMETHEUS_AVAILABLE


def get_registry():
    """Get the Prometheus registry"""
    return registry


if __name__ == "__main__":
    # Test metrics collection
    print("Testing metrics collection...")
    
    if PROMETHEUS_AVAILABLE:
        # Record some test metrics
        record_api_request('GET', '/status', 200, 0.05)
        record_api_request('POST', '/ping', 200, 0.1)
        record_storage_upload('local', 'success', 2.5)
        record_email_send('checkin', 'success', 1.2)
        
        # Update system metrics
        update_system_metrics()
        
        # Update business metrics
        update_business_metrics(
            active_configs=10,
            pending=5,
            docs=100,
            storage_bytes=1024 * 1024 * 100  # 100MB
        )
        
        # Get metrics
        metrics = get_metrics()
        if metrics:
            print("Metrics collected successfully:")
            print(metrics[:500])  # Print first 500 characters
        else:
            print("Failed to generate metrics")
    else:
        print("Prometheus client not available")
