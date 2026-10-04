# DineIQ Analytics — Restaurant AI & Artificial Intelligence Analytics Platform

**DineIQ Analytics** is an open-source **Restaurant AI**, **Artificial Intelligence**, **Machine Learning**, and **Data Science** project for restaurant decision intelligence. It combines **Apache Spark, PySpark, Spark SQL, MLlib, scikit-learn, Flask, Pandas, Parquet, forecasting, customer analytics, menu intelligence, wastage analysis, pricing intelligence, promotion analysis, recommendations, and What-If simulation** in one end-to-end restaurant analytics application.

Built by **Team Vision AI** for **TechWiz 7 — Data Science Intelligence Arena**, DineIQ is designed to help restaurants turn large operational datasets into explainable business decisions.

> **Keywords:** Restaurant AI, Artificial Intelligence for Restaurants, Restaurant Analytics, Restaurant Data Science, Machine Learning for Restaurants, AI Restaurant Management, Restaurant Business Intelligence, Menu Analytics, Demand Forecasting, Customer Segmentation, Wastage Reduction, Pricing Intelligence, Promotion Analytics, Apache Spark, PySpark, Spark SQL, MLlib, scikit-learn.

**All supplied business data is synthetic. Currency is PKR. Contribution is not accounting profit.**

## What DineIQ solves

Restaurants generate large amounts of operational data but often struggle to answer practical questions such as:

- Which dishes are profitable, high-volume, low-performing, or hidden opportunities?
- Which menu items create high wastage or inventory risk?
- Which customers are high-value, loyal, inactive, or at churn risk?
- Which products are commonly purchased together?
- What demand should be expected in the next days or weeks?
- Which promotions increase sales but reduce contribution?
- Which prices, discounts, branches, or menu decisions should be tested before rollout?
- Do independent Python and Spark pipelines reach consistent analytical conclusions?

DineIQ brings these questions into a single **restaurant artificial intelligence and analytics workspace**.

## Core Restaurant AI features

- **Executive Dashboard** — revenue, order demand, branch performance, contribution, wastage and anomaly views.
- **Menu Intelligence** — menu profitability, volume drivers, low performers and hidden opportunities.
- **Customer Intelligence** — RFM analysis, customer segmentation and churn-risk signals.
- **Market-Basket Analysis** — product combinations using support, confidence and lift.
- **Demand Forecasting** — future demand planning using historical features and seasonality.
- **Waste & Inventory Intelligence** — wastage patterns and operational risk signals.
- **Promotion & Pricing Intelligence** — promotion economics, price sensitivity and contribution effects.
- **Recommendations** — actionable restaurant decision support based on analytical outputs.
- **What-If Studio** — scenario simulation for price, discount, demand, preparation and wastage changes.
- **Anomaly Detection** — unusual sales, rating and operational behavior.
- **Live Prediction** — Python prediction, Spark prediction and **Run Both Models**.
- **Dual-Pipeline Model Comparison** — independently generated Python and Spark results.
- **Processing Center** — Python → Spark → Compare → Generate.
- **Evidence & Reporting** — PDF, JSON and CSV analytical outputs.
- **Role-Based Access & Audit Trail** — administrator, analyst, restaurant manager and regional manager workflows.

## AI / Data Science architecture

DineIQ uses two independent analytical paths so results can be compared rather than relying on one implementation:

1. **Python Data Science Pipeline** — Pandas, NumPy and scikit-learn.
2. **Apache Spark Pipeline** — PySpark, Spark SQL and Spark MLlib.
3. **Comparison Layer** — evaluates consistency across unseen analytical cases.
4. **Reporting Layer** — generates judge-facing and business-facing evidence.
5. **Flask Application** — exposes dashboards, workflows, predictions and downloadable results.

This design makes the project useful as a portfolio example for **restaurant AI, big data analytics, machine learning, artificial intelligence, data engineering and business intelligence**.

## Technology stack

| Area | Technology |
|---|---|
| Web application | Flask, HTML, CSS, JavaScript |
| Python analytics | Pandas, NumPy, scikit-learn |
| Big Data | Apache Spark, PySpark |
| Big Data querying | Spark SQL |
| Machine Learning | Spark MLlib, scikit-learn |
| Storage | CSV, JSON, Parquet |
| Reporting | ReportLab / generated PDF, JSON, CSV |
| Testing | pytest |
| Runtime | Python, Java/OpenJDK |

## Verified Windows runtime

The final Windows path was verified with **Python 3.11**, **Java/OpenJDK 17**, **PySpark 3.5.3**, `pandas 2.2.3`, plus the Windows Hadoop helper (`winutils.exe` + `hadoop.dll`). Python 3.11 is intentional for this verified PySpark 3.5.3 runtime; changing the interpreter version should be followed by a complete Spark and regression test pass.

### First-time setup

1. Double-click `SETUP_DINEIQ.bat`.
2. Then double-click `START_DINEIQ.bat`.
3. Open `http://127.0.0.1:5000`.
4. Use `STOP_DINEIQ.bat` to stop the local server.

Manual launch after setup:

```powershell
$env:PYSPARK_PYTHON = (Resolve-Path ".\.venv-spark\Scripts\python.exe").Path
$env:PYSPARK_DRIVER_PYTHON = $env:PYSPARK_PYTHON
$env:HADOOP_HOME = (Resolve-Path ".\runtime\hadoop").Path
$env:PATH = "$env:HADOOP_HOME\bin;$env:PATH"
$env:SPARK_LOCAL_IP = "127.0.0.1"
.\.venv-spark\Scripts\python.exe -m src.app
```

## Demo accounts

| Username | Role | Local demo password |
|---|---|---|
| admin | Administrator | DineIQ-Demo-2026! |
| analyst | Analyst | DineIQ-Demo-2026! |
| manager | Restaurant manager | DineIQ-Demo-2026! |
| regional | Regional manager | DineIQ-Demo-2026! |

## Rebuild the analytical outputs

```bash
python -m python_pipeline.run --horizon 30
python -m spark_jobs.pipeline
python -m src.compare
python -m src.generate_report
python -m src.database
python -m pytest -q tests --junitxml=reports/test_results.xml
```

## Model comparison evidence

The project includes independently generated Python and Spark results. Existing comparison evidence records **1,120 unseen cases** with **94.46% diagnostic agreement** at the configured 2% comparison tolerance. This diagnostic agreement is a pipeline-consistency measure, not an accuracy guarantee.

## Repository scope

This repository contains the source code, setup scripts, tests, configuration, technical documentation and judge-facing project material that are practical to keep in Git.

Large generated artifacts such as the 1M+ row raw dataset, processed Parquet outputs, Spark model directories, the full final MP4 and the complete submission ZIP are handled separately when they are not practical for ordinary Git history.

## Demo video

The final judge-facing video is named:

`DineIQ_Team_Vision_AI_Final_Demo_9m13_SMALL_SUBTITLES.mp4`

The repository includes a `Demo_Video/` location reserved for the final demo asset and related instructions.

## Team Vision AI

- **Syed Sajjad Hussain** — Team Lead, project coordination, product direction, system planning, final integration, UI review, documentation supervision, quality review and submission readiness.
- **Ali Khan** — Demo support, presentation support, voiceover coordination, visual communication and submission asset preparation.
- **Abdul Hameed** — Big Data processing support, Spark workflow assistance, data-quality review and technical validation support.
- **Hamdan Ahmed** — ML verification review, testing support and final-stage validation assistance.

**Mentor / Faculty:** Sir Kamran Hyder

## Project lead / AI portfolio

**Syed Sajjad Hussain** works on AI automation, AI agents, data science and machine-learning projects. DineIQ demonstrates practical skills in **restaurant artificial intelligence, big data, Apache Spark, Python analytics, machine learning, full-stack integration, testing and AI-powered business intelligence**.

See [`PORTFOLIO.md`](PORTFOLIO.md) for a search-friendly professional summary and project keywords.

## Competition

**TechWiz 7 — Data Science Intelligence Arena**  
Team: **Vision AI**

## Search discovery terms

DineIQ is relevant to people searching for:

**restaurant AI**, **AI for restaurants**, **artificial intelligence restaurant analytics**, **restaurant machine learning**, **restaurant data science**, **restaurant business intelligence**, **menu engineering AI**, **restaurant demand forecasting**, **food wastage analytics**, **customer segmentation restaurant**, **restaurant pricing analytics**, **promotion analytics**, **Apache Spark restaurant analytics**, **PySpark restaurant project**, **MLlib project**, **Python restaurant analytics**, and **AI restaurant management software**.
