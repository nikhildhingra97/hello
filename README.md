# Supply Chain Control Tower Blueprint & Prototype

This repository combines a blueprint for building an inventory-focused control tower with a runnable FastAPI prototype that demonstrates key concepts such as unified visibility, risk detection, and inbound order tracking.

## 1. Vision and Objectives
- **Unified Visibility**: Deliver a single source of truth for on-hand, in-transit, and planned inventory across plants, warehouses, suppliers, and retail channels.
- **Early Warning Signals**: Surface exceptions (stock-outs, capacity constraints, order delays) before they impact service levels.
- **Decision Automation**: Enable guided responses (e.g., rebalancing inventory, expediting shipments, adjusting production plans) based on configurable business rules.
- **Scalable Governance**: Provide role-based access, audit trails, and data quality monitoring to maintain trust in the control tower outputs.

## 2. Core Capabilities
1. **Data Ingestion & Harmonization**
   - Connect to ERP, WMS, TMS, OMS, MES, supplier portals, and external data (weather, macro trends).
   - Standardize units of measure, product hierarchy, location hierarchy, and time dimensions.
   - Implement data quality rules (completeness, timeliness, accuracy) with automated alerts.
2. **Inventory Visibility Layer**
   - Model inventory states: on-hand, reserved, available-to-promise, in-transit, work-in-progress, safety stock, projected inventory.
   - Support near real-time updates for fast-moving SKUs.
3. **Exception Management**
   - Define service-level KPIs (fill rate, OTIF, days of supply).
   - Configure thresholds and business rules to flag shortages, overstocks, delayed POs, capacity risks.
   - Provide collaboration workflows (assign, comment, resolve) integrated with email/Teams/Slack.
4. **Predictive & Prescriptive Analytics**
   - Demand forecasting using statistical and ML approaches.
   - Inventory optimization (multi-echelon, reorder point, safety stock calculations).
   - Scenario simulation and what-if analysis (e.g., supplier disruption, demand surge).
5. **User Experience**
   - Persona-based dashboards (executives, planners, logistics, procurement).
   - Customizable alerts (email, SMS, push notifications).
   - Guided decision playbooks outlining recommended actions.
6. **Integration & Automation**
   - APIs and webhooks to integrate with ERP for automated execution (e.g., create transfer orders).
   - RPA/automation for systems without native integration.

## 3. Reference Architecture
```
+---------------------------------------------------------------+
|                       Experience Layer                        |
|  - Executive dashboard  - Planner workbench  - Mobile alerts  |
+-----------------------------+---------------------------------+
                              |
+-----------------------------v---------------------------------+
|                     Analytics & Intelligence                  |
|  - KPI computation  - Forecasting models  - Optimization      |
+-----------------------------+---------------------------------+
                              |
+-----------------------------v---------------------------------+
|                  Data & Application Services                  |
|  - Inventory API  - Exception engine  - Workflow services     |
+-----------------------------+---------------------------------+
                              |
+-----------------------------v---------------------------------+
|                    Data Management Platform                   |
|  - Data lake / warehouse  - Streaming ingestion  - MDM        |
+-----------------------------+---------------------------------+
                              |
+-----------------------------v---------------------------------+
|              Source Systems & External Feeds                  |
|  ERP | WMS | TMS | OMS | MES | Supplier EDI | Market data     |
+---------------------------------------------------------------+
```

### Technology Considerations
- **Data Platform**: Cloud data warehouse (Snowflake/BigQuery/Redshift) + data lake (S3/ADLS) + streaming (Kafka/Kinesis/PubSub).
- **Integration**: ETL/ELT (dbt, Fivetran), iPaaS (MuleSoft, Boomi), API gateway.
- **Analytics**: Python/R notebooks, ML pipelines (SageMaker, Vertex AI, Databricks), optimization solvers.
- **Visualization**: Power BI, Tableau, Looker, or custom React/Angular dashboards.
- **Workflow & Alerts**: ServiceNow/Jira integration, Slack/Teams bots, rule engine.
- **Security**: IAM, SSO, data encryption, audit logging, GDPR/CCPA compliance.

## 4. Data Model Highlights
- **Product Dimension**: SKU, brand, category, pack size, unit conversions.
- **Location Dimension**: Plant, warehouse, store, region, customer.
- **Time Dimension**: Calendar, fiscal periods, lead times.
- **Inventory Fact Tables**:
  - `fact_inventory_snapshot`
  - `fact_inventory_projection`
  - `fact_orders` (purchase, sales, transfer)
  - `fact_shipments`
- **Reference Tables**: Safety stock policies, reorder parameters, service-level targets.

## 5. Implementation Roadmap
1. **Discovery & Alignment (Weeks 1-4)**
   - Stakeholder interviews, persona mapping, KPI alignment.
   - Data source inventory, integration feasibility assessment.
2. **Foundational Data Layer (Weeks 5-12)**
   - Build ingestion pipelines, data lake/warehouse schemas, MDM setup.
   - Establish data quality framework and monitoring.
3. **MVP Control Tower (Weeks 13-20)**
   - Implement core inventory visibility dashboards and exception alerts for priority SKUs.
   - Stand up workflow for planners with manual action logging.
4. **Advanced Analytics (Weeks 21-32)**
   - Deploy demand forecasting models, inventory optimization, scenario analysis.
   - Integrate with execution systems for semi-automated actions.
5. **Scale & Continuous Improvement (Weeks 33+)**
   - Expand to additional geographies, product lines, and suppliers.
   - Implement A/B testing on alert thresholds and decision playbooks.
   - Monitor adoption, gather feedback, refine UI/UX.

## 6. Governance & Operating Model
- **Control Tower Team**: Product owner, data engineers, analytics leads, planners, IT support.
- **Cadence**: Daily stand-ups, weekly KPI reviews, monthly steering committee.
- **Runbook**: Incident management procedures, data quality triage, release management.
- **Change Management**: Training programs, communication plan, success metrics.

## 7. KPIs & Success Metrics
- Inventory accuracy (%), days of supply, service level (OTIF), forecast accuracy, expedited freight cost, working capital turns, planner productivity.

## 8. Next Steps
- Validate requirements with stakeholders.
- Prioritize data sources and integration sequencing.
- Build a proof of concept using historical data.
- Define infrastructure budget and vendor selection criteria.

---

## 9. FastAPI Prototype
The `/app` package contains a lightweight, in-memory implementation of a control tower API:

- `models.py` defines domain entities (inventory items, demand signals, replenishment orders) and a snapshot schema.
- `data_store.py` manages in-memory persistence and aggregated metrics.
- `services.py` applies business logic to compute SKU health, shortfalls, and inbound visibility.
- `sample_data.py` loads representative sample data used by the API and tests.
- `api.py` exposes REST endpoints via FastAPI for snapshots, SKU health, and inbound orders.
- `main.py` runs the application with Uvicorn.

### Getting Started
1. **Install dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Run the API**
   ```bash
   uvicorn app.api:app --reload
   ```
3. **Explore endpoints**
   - `GET /snapshot` – aggregated inventory totals and top risk SKUs.
   - `GET /sku-health` – per-location health metrics (shortfall, coverage days, safety stock).
   - `GET /inbound` – inbound purchase orders with shortfall coverage indicator.
   - Interactive docs available at `http://localhost:8000/docs` when the server is running.

### Running Tests
```bash
pytest
```

### Single-File (Colab-Friendly) Script
If you prefer to work inside Google Colab or want a consolidated script, use `control_tower_colab.py`. The file contains the domain models, in-memory data store, business services, sample data, and FastAPI endpoints in one place.

```bash
# Print demo analytics directly in the notebook / terminal
python control_tower_colab.py

# Or start the FastAPI server from the single file
python control_tower_colab.py --serve --host 0.0.0.0 --port 8000
```

The `--serve` option mirrors the multi-module API, while running without arguments prints the snapshot, SKU health, and inbound visibility tables to stdout—handy for quick validation in notebook environments.

The prototype is intentionally simple—extend the service layer, replace the in-memory data store with database integrations, and wire the API to a front-end dashboard or alerting system to evolve it into a production-ready control tower.
