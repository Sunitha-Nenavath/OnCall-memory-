"""
Synthetic Incident Data Generator for OnCallMemory.
Generates 30 realistic production incidents over the last 6 months
with recurring failure patterns for a fictional e-commerce platform.
Also creates 3 demo alerts for semantic recall validation.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

# Deterministic seed for reproducible data generation
random.seed(42)

DATA_DIR = Path(__file__).resolve().parent

SERVICES = [
    "checkout-api",
    "payments-gateway",
    "inventory-service",
    "search-service",
    "auth-service",
    "postgres-primary",
    "redis-cache",
    "kafka-orders",
]

ENGINEERS = [
    "Sarah Chen (Senior SRE)",
    "Alex Rivera (DevOps Lead)",
    "Priya Sharma (Backend Engineer)",
    "Marcus Vance (Infrastructure Eng)",
    "Elena Rostova (On-Call Primary)",
    "David Kim (Systems Architect)",
]

RUNBOOKS = [
    "https://runbooks.internal/db/postgres-connection-exhaustion",
    "https://runbooks.internal/k8s/oom-pod-restarts",
    "https://runbooks.internal/cache/redis-eviction-triage",
    "https://runbooks.internal/kafka/consumer-lag-recovery",
    "https://runbooks.internal/sec/tls-cert-rotation",
    "https://runbooks.internal/api/latency-degradation-triage",
]

# Standard incident scenarios (including recurring patterns)
SCENARIOS = [
    {
        "service": "checkout-api",
        "pattern": "connection_pool",
        "severity": "SEV1",
        "title": "PostgreSQL Connection Pool Exhaustion on Checkout Service",
        "alert_text": (
            "ALERT [SEV1] checkout-api latency p99 > 8500ms. "
            "Error rate 42% on POST /v2/checkout/submit. "
            "Log snippet: 'sqlalchemy.exc.TimeoutError: QueuePool limit of size 20 overflow 10 reached, connection timed out after 30.00 seconds'. "
            "Metric postgresql_stat_activity_count{db='orders_db', state='active'} = 100/100 connections maxed out."
        ),
        "root_cause": (
            "Unclosed DB transaction leak introduced in release v2.14.0 during Friday deploy. "
            "The updated checkout pipeline failed to release SQLAlchemy connections back to Hikari/QueuePool on payment processing timeouts."
        ),
        "fix_steps": [
            "Rolled back checkout-api container image to tag v2.13.9.",
            "Ran pg_terminate_backend() for idle-in-transaction connections on postgres-primary.",
            "Increased HikariCP maxConnections from 30 to 60 as emergency buffer.",
            "Patched checkout pipeline DB session context manager with explicit try...finally db.close()."
        ],
        "runbook_used": "https://runbooks.internal/db/postgres-connection-exhaustion",
        "time_range": (15, 60),
        "postmortem_note": "Ensure connection pool metrics have automated alerts set at 80% capacity. Strictly enforce connection context manager linter."
    },
    {
        "service": "payments-gateway",
        "pattern": "oom_leak",
        "severity": "SEV1",
        "title": "Payments Gateway Kubernetes Pod OOMKilled Loop",
        "alert_text": (
            "ALERT [SEV1] KubePodCrashLooping - payments-gateway-5f8d9b7c-x9z2q restarting repeatedly. "
            "Pod exit status: 137 (OOMKilled). "
            "Container memory utilization reached limit of 2Gi (2048MiB). "
            "JVM garbage collection log: 'java.lang.OutOfMemoryError: Java heap space' during stripe webhook payload serialization."
        ),
        "root_cause": (
            "Unbounded buffer allocation in payload logging interceptor when parsing large webhook payloads. "
            "Jackson JSON parser retained full byte arrays in memory per concurrent request without batch flushing."
        ),
        "fix_steps": [
            "Increased Kubernetes memory limit to 4Gi for deployment/payments-gateway as immediate mitigation.",
            "Disabled verbose raw payload payload-dump logging interceptor via feature flag PAYMENTS_LOG_VERBOSE=false.",
            "Deployed patch v1.8.4 implementing streaming JSON parsing with fixed 64KB buffer."
        ],
        "runbook_used": "https://runbooks.internal/k8s/oom-pod-restarts",
        "time_range": (20, 45),
        "postmortem_note": "Never enable full request payload in-memory buffering in production log interceptors."
    },
    {
        "service": "redis-cache",
        "pattern": "redis_eviction",
        "severity": "SEV2",
        "title": "Redis Cache Eviction Storm and Key Thrashing",
        "alert_text": (
            "ALERT [SEV2] Redis cache hit ratio dropped from 94% to 12%. "
            "redis_used_memory_rss_bytes = 15.8GB / maxmemory 16GB. "
            "Eviction rate spikes to 45,000 keys/sec (allkeys-lru). "
            "Downstream inventory-service experience 15x DB query surge causing DB CPU 98%."
        ),
        "root_cause": (
            "Campaign marketing flash sale stored 2M uncompressed user recommendation keys without TTL expiration. "
            "The memory pressure triggered aggressive LRU evictions of critical inventory session keys."
        ),
        "fix_steps": [
            "Flushed recommendation namespace keys via redis-cli SCAN 0 MATCH rec:* COUNT 5000 DEL.",
            "Updated Redis maxmemory policy to volatile-lru.",
            "Enforced default TTL of 1 hour for all product recommendation keys."
        ],
        "runbook_used": "https://runbooks.internal/cache/redis-eviction-triage",
        "time_range": (15, 40),
        "postmortem_note": "Require mandatory TTL policy check in pull requests touching cache set functions."
    },
    {
        "service": "kafka-orders",
        "pattern": "consumer_lag",
        "severity": "SEV2",
        "title": "Kafka Consumer Lag Spike in Order Fulfillment Pipeline",
        "alert_text": (
            "ALERT [SEV2] Kafka consumer group 'fulfillment-workers' lag exceeded 180,000 messages on topic 'orders.events.v1'. "
            "Order processing latency increased to 45 minutes. "
            "Partition 3 and 7 stuck processing due to lock contention."
        ),
        "root_cause": (
            "Third-party shipping carrier API rate limit HTTP 429 triggered exponential sleep retries inside synchronous event loop on worker threads."
        ),
        "fix_steps": [
            "Scaled consumer replica count from 4 to 12 pods.",
            "Implemented dead-letter queue (DLQ) pattern for orders facing carrier 429 rate limits.",
            "Added circuit breaker for carrier API with 5-second fallback timeout."
        ],
        "runbook_used": "https://runbooks.internal/kafka/consumer-lag-recovery",
        "time_range": (30, 90),
        "postmortem_note": "Isolate external API integrations into async dead-letter retry workers."
    },
    {
        "service": "auth-service",
        "pattern": "tls_cert",
        "severity": "SEV1",
        "title": "Expired Internal mTLS Certificate Breakdown",
        "alert_text": (
            "ALERT [SEV1] auth-service SSL handshake failures. "
            "Error: 'javax.net.ssl.SSLHandshakeException: PKIX path validation failed: certificate has expired'. "
            "All inter-service gRPC requests returning UNAUTHENTICATED."
        ),
        "root_cause": (
            "Cert-manager cron job failed to renew internal wildcard tls-secret 'auth-internal-cert' due to IAM permission revocation."
        ),
        "fix_steps": [
            "Manually issued emergency cert via Vault CLI.",
            "Updated Kubernetes secret 'auth-tls-certs' and triggered rolling restart of auth-service pods.",
            "Restored cert-manager IAM role bindings."
        ],
        "runbook_used": "https://runbooks.internal/sec/tls-cert-rotation",
        "time_range": (10, 30),
        "postmortem_note": "Add Prometheus alert for certificate expiration 14 days in advance."
    },
    {
        "service": "search-service",
        "pattern": "slow_query",
        "severity": "SEV3",
        "title": "Elasticsearch High CPU & Garbage Collection Pauses",
        "alert_text": (
            "ALERT [SEV3] search-service p95 latency increased to 3200ms. "
            "Elasticsearch node es-cluster-node-2 JVM GC pause time = 4.2s. "
            "Search queries with wildcard regex filter '*' overwhelming threadpool search queue."
        ),
        "root_cause": (
            "Unindexed wildcard query parameters allowed from frontend search autocomplete input without string length validation."
        ),
        "fix_steps": [
            "Enabled query cache and set max_analyzed_offset guardrail in Elasticsearch index settings.",
            "Deployed API gateway rule enforcing minimum 3 characters for autocomplete queries."
        ],
        "runbook_used": "https://runbooks.internal/api/latency-degradation-triage",
        "time_range": (15, 35),
        "postmortem_note": "Sanitize and truncate search prefix inputs at the API gateway layer."
    }
]


def generate_incidents(count=30):
    """Generates 30 realistic incident records with timestamps spread across 180 days."""
    incidents = []
    now = datetime.utcnow()
    
    # We explicitly seed 30 incidents ensuring recurring patterns on Fridays and connection pool issues
    for i in range(1, count + 1):
        # Pick base scenario
        scenario = list(SCENARIOS)[(i - 1) % len(SCENARIOS)]
        
        # Calculate timestamp (spread over 180 days back)
        days_ago = int((count - i) * (180 / count)) + random.randint(0, 3)
        incident_date = now - timedelta(days=days_ago)
        
        # Ensure some recurring Friday deploys for connection pool / config issues
        if scenario["pattern"] == "connection_pool" and i % 2 == 0:
            # Shift to nearest Friday
            days_until_friday = (4 - incident_date.weekday()) % 7
            incident_date = incident_date + timedelta(days=days_until_friday)
            post_deploy_tag = " [Friday Deploy Post-Mortem]"
        else:
            post_deploy_tag = ""

        time_to_resolve = random.randint(*scenario["time_range"])
        engineer = ENGINEERS[(i - 1) % len(ENGINEERS)]
        
        incident_id = f"INC-{1000 + i}"
        
        incident = {
            "id": incident_id,
            "timestamp": incident_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "service": scenario["service"],
            "severity": scenario["severity"],
            "alert_text": f"{scenario['alert_text']} (Ref: {incident_id})",
            "root_cause": f"{scenario['root_cause']}{post_deploy_tag}",
            "fix_steps": scenario["fix_steps"],
            "runbook_used": scenario["runbook_used"],
            "engineer_name": engineer,
            "time_to_resolve_minutes": time_to_resolve,
            "postmortem_note": scenario["postmortem_note"],
            "was_fix_effective": True
        }
        incidents.append(incident)
        
    return incidents


def generate_demo_alerts():
    """Generates 3 distinct demo alerts for semantic recall evaluation."""
    return [
        {
            "id": "DEMO-01",
            "title": "Checkout DB Connection Timeout & Latency Surge",
            "service": "checkout-api",
            "severity": "SEV1",
            "description": "Demo 1: High latency on Checkout API matching past connection pool exhaustion.",
            "alert_text": (
                "ALERT [SEV1] checkout-api latency spike! p99 response time reached 9200ms on checkout submission endpoint. "
                "Application logs show multiple thread starvation warnings: "
                "'HikariPool-1 - Connection is not available, request timed out after 30000ms'. "
                "PostgreSQL active connection count has hit max_connections limit of 100 on DB server postgres-primary."
            )
        },
        {
            "id": "DEMO-02",
            "title": "Payment Pod CrashLoop & Out of Memory Errors",
            "service": "payments-gateway",
            "severity": "SEV1",
            "description": "Demo 2: Pods restarting due to OOMKilled memory leak matching past Jackson parser issue.",
            "alert_text": (
                "ALERT [SEV1] Kubernetes cluster node alert: payments-gateway container terminated unexpectedly. "
                "kubectl get pods shows status 'CrashLoopBackOff', restart count 8. "
                "System event log: OOMKilled signal 9 invoked, process memory consumed 2.05 GiB exceeding cgroup quota. "
                "Application stack trace points to heap memory exhaustion in JSON payload parsing."
            )
        },
        {
            "id": "DEMO-03",
            "title": "Corrupted GeoIP Database File Causing International Routing Exceptions",
            "service": "auth-service",
            "severity": "SEV2",
            "description": "Demo 3: Brand new incident type with no past memory history (tests honest behavior).",
            "alert_text": (
                "ALERT [SEV2] auth-service returning HTTP 500 on international login requests. "
                "Log error trace: 'com.maxmind.geoip2.exception.AddressNotFoundException / InvalidDatabaseException: "
                "The MaxMind GeoIP2 database file /var/data/GeoIP2-City.mmdb is corrupted or unreadable at offset 0x0041F'. "
                "No previous occurrences found in system history."
            )
        }
    ]


def main():
    """Generates incidents.json and demo_alerts.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    incidents = generate_incidents(count=30)
    incidents_path = DATA_DIR / "incidents.json"
    with open(incidents_path, "w", encoding="utf-8") as f:
        json.dump(incidents, f, indent=2)
    print(f"Generated {len(incidents)} synthetic incidents at {incidents_path}")

    demo_alerts = generate_demo_alerts()
    demo_path = DATA_DIR / "demo_alerts.json"
    with open(demo_path, "w", encoding="utf-8") as f:
        json.dump(demo_alerts, f, indent=2)
    print(f"Generated {len(demo_alerts)} demo alerts at {demo_path}")


if __name__ == "__main__":
    main()
