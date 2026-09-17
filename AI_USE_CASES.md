# Horizon Sync — AI Use Cases

> **Document Prepared By:** GitHub Copilot
> **Date:** 2026-07-17
> **Scope:** AI/ML integration opportunities across QReach, QSeal, Product Visibility & Micro ERP

---

## Overview

Horizon Sync's rich data ecosystem — spanning QR campaigns, consumer engagement, inventory, billing, and warehousing — presents multiple high-impact opportunities for AI integration. Below are five prioritized use cases mapped to the platform's core modules.

---

## 1. QReach — AI-Powered Campaign Optimization Engine

### Problem

Brand managers currently configure QReach campaigns (Scan2Win, Play2Win, Feedback2Win, Click2Win) manually — setting prize distributions, win probabilities, coupon values, and campaign durations based on intuition and trial-and-error.

### AI Solution

A **campaign optimization & recommendation engine** that learns from historical campaign performance to suggest optimal parameters.

### Key Capabilities

| Feature                             | Description                                                                                                                                                                                       |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Performance Prediction**          | Predict scan volume, coupon redemption rate, and lead generation for a draft campaign before launch, trained on past campaigns with similar product categories, geographies, and prize structures |
| **Prize Distribution Optimization** | Recommend win probabilities and coupon value tiers that maximize engagement while staying within budget constraints (constrained optimization)                                                    |
| **A/B Variant Suggestions**         | Auto-generate campaign variants with different prize/design parameters for split testing                                                                                                          |
| **Churn Prevention Alerts**         | Detect campaigns with declining scan velocity mid-flight and suggest interventions (e.g., boost prize pool, send reminder SMS)                                                                    |
| **Seasonal Adjustment**             | Factor in seasonal/holiday trends and day-of-week patterns to recommend ideal launch windows                                                                                                      |

### Data Sources

- `campaigns`, `campaign_analytics`, `lead_entries`, `coupon_redemptions`, `scan_events`
- Product metadata (category, price point, margin)
- Geographic/device distribution data from analytics dashboards

### Technical Approach

- Gradient-boosted trees (XGBoost/LightGBM) for structured prediction tasks
- Bayesian optimization for prize distribution tuning
- Deploy as a microservice or scheduled batch inference job within `core-service`

---

## 2. QReach — Intelligent Lead Scoring & Smart Segmentation

### Problem

QReach campaigns generate large lead databases. Currently, all leads are treated uniformly for SMS/WhatsApp retargeting, leading to wasted messaging credits and consumer fatigue.

### AI Solution

An **ML-driven lead scoring and segmentation engine** that ranks leads by engagement propensity and segments them for personalized outreach.

### Key Capabilities

| Feature                               | Description                                                                                                                                         |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Lead Quality Scoring**              | Score each lead (0–100) based on scan frequency, coupon redemption history, feedback sentiment, time since last engagement, and demographic signals |
| **Propensity-to-Convert Model**       | Predict likelihood of a lead redeeming a coupon, making a purchase, or referring others                                                             |
| **Smart Segmentation**                | Auto-cluster leads into cohorts (e.g., "High-Value Repeat Scanners", "One-Time Curious", "At-Risk of Churn") using unsupervised learning            |
| **Targeted Outreach Recommendations** | Suggest which segment to target with which campaign type (e.g., "Send `20% off` coupon to At-Risk segment via WhatsApp")                            |
| **Churn Prediction**                  | Flag leads whose engagement has dropped below a learned threshold, triggering re-engagement workflows                                               |

### Data Sources

- `leads`, `lead_notes`, `lead_tags`, `lead_activity_log`
- SMS/WhatsApp campaign delivery & response logs
- Coupon generation and redemption history
- Feedback2Win text responses

### Technical Approach

- Random forest / XGBoost for propensity scoring
- K-Means or DBSCAN for behavioral clustering
- Batch scoring pipeline (nightly) + real-time scoring API for new leads
- Store scores as columns on the `leads` table for fast filtering

---

## 3. Product Visibility — AI-Enhanced Semantic Product Search & Auto-Cataloging

### Problem

The ERP's product catalog grows large with diverse item names, descriptions, and attributes. Traditional keyword search (`search-service` using PostgreSQL full-text search) fails on typos, synonyms, and natural-language queries from warehouse staff and mobile app users.

### AI Solution

A **semantic search and intelligent cataloging layer** that understands intent, not just keywords.

### Key Capabilities

| Feature                           | Description                                                                                                                                   |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| **Semantic / NLP Search**         | Enable queries like "blue medium t-shirt under 500" or "packaging material for fragile items" using embedding-based retrieval (vector search) |
| **Auto-Tagging & Categorization** | Automatically assign item groups, categories, and attributes (size, color, material) from product names and descriptions using NLP            |
| **Duplicate Detection**           | Identify near-duplicate items across the catalog (e.g., same product entered with slight name variations) using fuzzy matching + embeddings   |
| **Image-Based Product Lookup**    | Mobile app users can snap a photo of a product to search the catalog (CNN/CLIP embeddings → vector similarity)                                |
| **Smart Attribute Extraction**    | Parse free-text item descriptions to extract structured attributes (weight, dimensions, brand, SKU patterns)                                  |

### Data Sources

- `items`, `item_groups`, `item_attributes`, `brands`
- Mobile app image uploads (future)
- Barcode/GTIN data

### Technical Approach

- **Embedding model**: `text-embedding-3-small` (OpenAI) or open-source `all-MiniLM-L6-v2` for product descriptions
- **Vector store**: pgvector extension on PostgreSQL (no new infrastructure)
- **Image model**: CLIP or MobileNet for on-device inference
- Integrate into existing `search-service` as a semantic search fallback alongside FTS

---

## 4. Micro ERP — AI Demand Forecasting & Inventory Optimization

### Problem

Warehouse managers rely on manual stock level checks and gut-feel reordering. This leads to stockouts of fast-moving items and overstock of slow-moving ones, tying up working capital.

### AI Solution

A **demand forecasting and smart replenishment engine** that predicts future stock requirements and recommends purchase orders.

### Key Capabilities

| Feature                                       | Description                                                                                                                                                                    |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Demand Forecasting**                        | Predict daily/weekly demand per item per warehouse using historical stock movement, sales orders, and seasonal patterns (time-series models)                                   |
| **Smart Reorder Point Suggestions**           | Dynamically calculate reorder points and safety stock levels based on demand volatility, supplier lead times, and desired service levels — replacing static min/max thresholds |
| **Purchase Order Recommendations**            | Auto-generate draft POs with suggested quantities, considering: forecasted demand, current stock, pending POs, lead times, and bulk discount thresholds                        |
| **Slow-Moving / Dead Stock Detection**        | Flag items with declining velocity and recommend liquidation strategies (discount, transfer to high-demand warehouse, return to supplier)                                      |
| **Put-Away Optimization**                     | Recommend optimal bin assignments for inbound stock based on item velocity (fast-movers → front bins, slow-movers → back bins) — enhances WMS put-away rules                   |
| **Anomaly Detection in Stock Reconciliation** | Flag unusual discrepancies in stock reconciliation that may indicate theft, damage, or data entry errors                                                                       |

### Data Sources

- `stock_entries`, `stock_ledger`, `stock_levels`, `stock_reconciliation`
- `sales_orders`, `delivery_notes`, `purchase_orders`, `purchase_receipts`
- `items`, `warehouses`, `bins`, `suppliers`
- Historical trend data from analytics module

### Technical Approach

- **Forecasting**: Prophet (Meta) or LightGBM with lag features for time-series demand prediction
- **Reorder optimization**: Classic inventory theory (EOQ + safety stock) augmented with ML-predicted demand distributions
- **Anomaly detection**: Isolation Forest or statistical process control on reconciliation variances
- Scheduled batch job (daily) in `core-service` + dashboard widgets

---

## 5. QSeal / Platform-Wide — AI-Powered Fraud & Anomaly Detection

### Problem

QR campaigns are vulnerable to abuse (bulk scans, coupon farming, fake leads). Similarly, ERP transactions (invoices, payments, stock movements) can contain errors or fraudulent entries that go unnoticed.

### AI Solution

A **cross-module anomaly detection engine** that surfaces suspicious patterns across QReach campaigns and ERP transactions.

### Key Capabilities

| Feature                       | Description                                                                                                                                                                                          |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **QR Scan Fraud Detection**   | Detect suspicious patterns: rapid-fire scans from single IP/device, impossible geographic jumps (scans from two cities minutes apart), scans outside campaign active hours, bot-like timing patterns |
| **Coupon Abuse Detection**    | Flag: single user redeeming excessive coupons, coupon codes being shared/leaked (redeemed by many users), redemption velocity spikes                                                                 |
| **Fake Lead Detection**       | Identify leads with synthetic-looking data: disposable email domains, invalid/voip phone patterns, names matching known fake patterns, feedback responses that are copy-paste or gibberish           |
| **ERP Transaction Anomalies** | Flag: duplicate invoice patterns, unusually large payments, stock adjustments at odd hours, delivery notes without corresponding pick lists, purchase receipts with zero quantity                    |
| **Real-Time Risk Scoring**    | Assign a risk score to every scan, lead entry, coupon redemption, and financial transaction; high scores trigger alerts or auto-blocks                                                               |

### Data Sources

- QReach: `scan_events`, `lead_entries`, `coupon_redemptions`, `otp_verifications`, Matomo tracking events
- Micro ERP: `invoices`, `payments`, `journal_entries`, `stock_entries`, `delivery_notes`, `purchase_receipts`
- Identity: `users`, `organizations`, audit logs

### Technical Approach

- **Rule-based + ML hybrid**: Simple heuristics (rate limits, geo-velocity) as first pass; ML models for subtle patterns
- **Isolation Forest / Autoencoder** for unsupervised anomaly detection on transaction embeddings
- **Real-time scoring**: Consume Redis Streams events → score → push alerts to dashboard/notification service
- **Feedback loop**: Allow manual flag/review to improve model precision over time

---

## Implementation Roadmap (Suggested)

```
Phase 1 (Quick Wins — 4–8 weeks)
├── Lead Scoring & Segmentation (#2) — high ROI, well-structured data, batch processing
└── Fraud Detection — QR scan rules (#5 QReach portion) — immediate abuse prevention

Phase 2 (Core Intelligence — 8–16 weeks)
├── Semantic Product Search (#3) — requires pgvector, embedding pipeline
└── Demand Forecasting (#4) — requires sufficient historical data

Phase 3 (Advanced — 16–24 weeks)
├── Campaign Optimization Engine (#1) — needs Phase 1 & 2 data maturity
├── ERP Transaction Anomaly Detection (#5 ERP portion)
└── Image-Based Product Lookup (#3 extension)

```

---

## Infrastructure Considerations

| Concern           | Recommendation                                                                                                                                                      |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Model Serving** | Start with batch inference (scheduled Celery/APScheduler jobs in `core-service`); graduate to a dedicated `ai-service` FastAPI microservice for real-time endpoints |
| **Vector Store**  | Enable `pgvector` extension on existing PostgreSQL — no new infrastructure needed for semantic search                                                               |
| **ML Pipeline**   | Use `scikit-learn` + `xgboost` for classical ML; `sentence-transformers` for embeddings; `Prophet` for forecasting — all Python-native, fits the FastAPI stack      |
| **GPU Needs**     | None for classical ML; optional for CLIP image embeddings (use on-device/CPU inference as fallback)                                                                 |
| **Feature Store** | Start simple — materialize features as columns on existing tables; graduate to Redis-backed feature store for real-time scoring                                     |
| **Monitoring**    | Track model drift (prediction distributions over time), precision/recall on flagged anomalies, and business KPIs (campaign ROI lift, stockout reduction %)          |
| **Data Privacy**  | All models run on tenant-isolated data (`organization_id` scoped); embeddings and scores stay within the database; no external API calls for core inference         |

---

## Success Metrics

| Use Case              | Key Metric                        | Target         |
| --------------------- | --------------------------------- | -------------- |
| Campaign Optimization | Avg. coupon redemption rate lift  | +15%           |
| Lead Scoring          | SMS campaign conversion rate      | +25%           |
| Semantic Search       | Search-to-find time reduction     | -40%           |
| Demand Forecasting    | Stockout incidents reduction      | -50%           |
| Fraud Detection       | Fraudulent lead/coupon catch rate | >90% precision |

---

_End of document._
