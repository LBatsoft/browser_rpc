"""
Prometheus 监控指标定义
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from prometheus_client.openmetrics.exposition import CONTENT_TYPE_LATEST
import time

# Gateway 指标
gateway_requests_total = Counter(
    'gateway_requests_total',
    'Total number of gateway requests',
    ['method', 'endpoint', 'status']
)

gateway_request_duration_seconds = Histogram(
    'gateway_request_duration_seconds',
    'Gateway request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

gateway_retry_total = Counter(
    'gateway_retry_total',
    'Total number of retries in gateway',
    ['operation', 'reason']
)

gateway_active_sessions = Gauge(
    'gateway_active_sessions',
    'Number of active sessions through gateway'
)

gateway_node_selection_total = Counter(
    'gateway_node_selection_total',
    'Total number of node selections',
    ['node_id', 'status']
)

# Worker 指标
worker_requests_total = Counter(
    'worker_requests_total',
    'Total number of worker requests',
    ['method', 'endpoint', 'status']
)

worker_request_duration_seconds = Histogram(
    'worker_request_duration_seconds',
    'Worker request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

worker_active_sessions = Gauge(
    'worker_active_sessions',
    'Number of active sessions on worker',
    ['node_id']
)

worker_session_operations_total = Counter(
    'worker_session_operations_total',
    'Total number of session operations',
    ['operation', 'status']
)

# 节点注册指标
node_registry_nodes = Gauge(
    'node_registry_nodes',
    'Number of registered nodes',
    ['status']  # 'active' or 'total'
)

node_registry_heartbeat_total = Counter(
    'node_registry_heartbeat_total',
    'Total number of heartbeats',
    ['node_id']
)

# CDP 操作指标
cdp_operations_total = Counter(
    'cdp_operations_total',
    'Total number of CDP operations',
    ['operation', 'status']
)

cdp_operation_duration_seconds = Histogram(
    'cdp_operation_duration_seconds',
    'CDP operation duration in seconds',
    ['operation'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)


def get_metrics():
    """获取 Prometheus 格式的指标数据"""
    return generate_latest(REGISTRY)


def get_metrics_content_type():
    """获取指标内容的 Content-Type"""
    return CONTENT_TYPE_LATEST


# 注意: RequestMetrics 类目前未使用，保留用于未来可能的代码重构
# 如果决定不使用，可以删除此类
class RequestMetrics:
    """
    请求指标记录器（上下文管理器）
    
    用于简化指标记录的上下文管理器，目前未在代码中使用。
    可以考虑在重构时使用此类来减少代码重复。
    """
    
    def __init__(self, counter, histogram, method: str, endpoint: str):
        self.counter = counter
        self.histogram = histogram
        self.method = method
        self.endpoint = endpoint
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        # 记录持续时间
        self.histogram.labels(method=self.method, endpoint=self.endpoint).observe(duration)
        
        # 确定状态码
        if exc_type is None:
            status = 'success'
        elif isinstance(exc_val, Exception):
            status = 'error'
        else:
            status = 'unknown'
        
        # 记录计数器
        self.counter.labels(method=self.method, endpoint=self.endpoint, status=status).inc()
        
        return False  # 不抑制异常

