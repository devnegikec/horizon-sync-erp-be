# Railway Kafka Messaging System Guide

> Scope: `horizon-sync-erp-be` services deployed on Railway
> Date: 2026-08-14

This guide covers standing up a **Kafka** message bus for the Railway-deployed backend and wiring it into the existing FastAPI services. Kafka is **not currently used** in the codebase — this is a greenfield integration.

---

## 1. Why Kafka alongside Redis

| Concern | Redis (current) | Kafka (proposed) |
|---|---|---|
| Model | pub/sub + short stream | durable, replayable log |
| Retention | ephemeral (stream trimmed to 5000) | configurable, persists |
| Ordering | per-channel | per-partition (strong) |
| Consumers | live only | replay from any offset, consumer groups |
| Use | 3-D real-time UI events, search sync | audit, billing, inventory events, cross-service integration |

Keep Redis for **real-time UI** (3-D view, search live sync). Add Kafka for **durable, ordered, replayable** events (invoices, payments, stock movements, ASN).

---

## 2. Options (pick one)

| Option | Provider | Effort | When |
|---|---|---|---|
| **A. Managed Kafka** | Confluent Cloud / Upstash Kafka / Aiven / AWS MSK | low | recommended for prod |
| **B. Self-hosted (KRaft)** | Your own services in Railway | medium | dev/test, full control |

> **Recommendation:** Option A for production (Confluent Cloud free tier or Upstash Kafka). Option B only for local parity / cost control.

---

## 3. Option A — Managed Kafka (Confluent Cloud example)

1. Create a cluster at https://confluent.cloud → **Basic/Standard**.
2. Create an **API key + secret** (SASL/PLAIN).
3. Create topics you need (or use auto-create in dev).

### 3.1 Environment variables

```bash
KAFKA_BOOTSTRAP_SERVERS=pkc-xxxx.us-west2.gcp.confluent.cloud:9092
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=PLAIN
KAFKA_SASL_USERNAME=<api-key>
KAFKA_SASL_PASSWORD=<api-secret>
```

---

## 4. Option B — Self-hosted Kafka (KRaft) in Railway

Kafka 3.3+ can run **without Zookeeper** using KRaft. Run a single broker for dev, or 3 brokers for prod-like resilience.

### 4.1 Dockerfile service (`infra/kafka`)

`infra/kafka/Dockerfile`:
```dockerfile
FROM apache/kafka:3.7.0
```

`infra/kafka/server.properties` (single-node KRaft):
```properties
process.roles=broker,controller
node.id=1
controller.quorum.voters=1@kafka:9093
listeners=PLAINTEXT://:9092,CONTROLLER://:9093
advertised.listeners=PLAINTEXT://kafka.railway.internal:9092
controller.listener.names=CONTROLLER
log.dirs=/var/lib/kafka/data
num.partitions=3
offsets.topic.replication.factor=1
```

### 4.2 `railway.toml` entry

```toml
[services.kafka]
source = "infra/kafka"
startCommand = "bash -c 'kafka-storage.sh format -t <cluster-id> -c /etc/kafka/server.properties && kafka-server-start.sh /etc/kafka/server.properties'"
```

> Generate a `<cluster-id>` once: `kafka-storage.sh random-uuid`.
> Attach a Railway **Volume** to `/var/lib/kafka/data` for persistence across redeploys.

---

## 5. Python integration

The backend is **FastAPI (async)** — use **`aiokafka`** for async producers/consumers, or `confluent-kafka` for max throughput.

### 5.1 Add dependency

`core-service/requirements.txt`:
```
aiokafka==0.11.0
```

### 5.2 Settings (`core-service/app/config.py`)

```python
kafka_bootstrap_servers: str = "localhost:9092"
kafka_security_protocol: str = "PLAINTEXT"   # SASL_SSL for Confluent
kafka_sasl_mechanism: str = "PLAIN"
kafka_sasl_username: str = ""
kafka_sasl_password: str = ""
```

### 5.3 Async producer (`app/events/kafka_publisher.py`)

```python
from aiokafka import AIOKafkaProducer
from app.config import settings

class KafkaEventPublisher:
    def __init__(self):
        self._producer = None

    async def start(self):
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            security_protocol=settings.kafka_security_protocol,
            sasl_mechanism=settings.kafka_sasl_mechanism,
            sasl_plain_username=settings.kafka_sasl_username,
            sasl_plain_password=settings.kafka_sasl_password,
            value_serializer=lambda v: json.dumps(v).encode(),
        )
        await self._producer.start()

    async def publish(self, topic: str, key: str, value: dict):
        await self._producer.send_and_wait(topic, key=key.encode(), value=value)

    async def stop(self):
        if self._producer:
            await self._producer.stop()
```

### 5.4 Async consumer (example)

```python
from aiokafka import AIOKafkaConsumer

async def consume():
    consumer = AIOKafkaConsumer(
        "warehouse.events",
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="core-service",
        value_deserializer=lambda b: json.loads(b.decode()),
    )
    await consumer.start()
    try:
        async for msg in consumer:
            await handle(msg.value)
    finally:
        await consumer.stop()
```

---

## 6. Topic design for this codebase

| Topic | Producer | Consumers | Purpose |
|---|---|---|---|
| `warehouse.events` | core-service (stock change, put-away, dispatch) | search-service, analytics | inventory + capacity events |
| `billing.events` | core-service (invoice/payment) | identity-service, analytics | financial events |
| `asn.events` | core-service | ai-service, notifications | inbound pre-alerts |

Conventions:
- One topic per **domain**, not per service.
- Partition by `organization_id` (key) so an org's events stay ordered.
- Keep events **immutable** and versioned (`{"event": "stock.changed", "v": 1, ...}`).

---

## 7. Wiring into the existing event layer

The current publisher is `app/events/publisher.py` (Redis). Add Kafka as a **side-channel** — publish to both, or make the transport pluggable:

```python
# publish to Redis (live UI) AND Kafka (durable log)
await redis_publisher.publish(event)
await kafka_publisher.publish(topic, key=str(org_id), value=event)
```

Do **not** remove Redis pub/sub — the 3-D view and search live sync depend on it.

---

## 8. Railway environment variables (summary)

Set on `core-service` (and any consumer service):

```bash
KAFKA_BOOTSTRAP_SERVERS=pkc-xxxx.us-west2.gcp.confluent.cloud:9092
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=PLAIN
KAFKA_SASL_USERNAME=<api-key>
KAFKA_SASL_PASSWORD=<api-secret>
```

---

## 9. Caveats

- **Managed Kafka is easiest** — self-hosted KRaft in Railway needs a Volume and careful advertised-listener config (`<service>.railway.internal`).
- **Replication factor:** self-hosted single broker = `replication.factor=1` (no HA). Use 3 brokers for resilience.
- **No public port for Kafka** — keep it private-network only; expose only the API gateway.
- **Startup ordering:** start the producer lazily and retry — Kafka may not be ready when your service boots.
