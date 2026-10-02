# DineIQ Analytics
**MenuMatrix Dining Intelligence — Data Science Intelligence Arena**

A runnable restaurant intelligence application with Flask, Pandas, Apache Spark, Spark SQL, MLlib and independently trained scikit-learn models. It includes generated relational data, quality quarantine, Parquet storage, forecasting, menu classification, customer segmentation, market-basket analysis, waste risk, pricing, campaigns, anomalies, recommendations and scenarios.

**All supplied business data is synthetic. Currency is PKR. Contribution is not accounting profit.**

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

## Core application features
- Premium Executive Dashboard with revenue, order-demand and branch-performance visualizations.
- Quick Lookup for immediate location/menu/date-range results.
- Guided Data Entry and ZIP ingestion with validation.
- Menu Intelligence, Customers & RFM, Basket Analysis, Demand Forecast, Waste & Inventory.
- Promotions & Pricing, Recommendations, anomaly detection and What-If Studio.
- Independent Python and Spark pipelines.
- Live Prediction: Python, Spark, and Run Both Models.
- Model Comparison and Data & Model Evidence.
- Processing Center: Python → Spark → Compare → Generate.
- PDF/JSON/CSV analytical outputs.
- Role-based access, audit trail, CSRF protection and login password show/hide control.

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

## Repository scope
This GitHub repository contains the source code, setup scripts, tests, configuration, sample data, technical documentation and judge-facing project material that are practical to keep in Git.

Large generated artifacts such as the 1M+ row raw dataset, processed Parquet outputs, Spark model directories, the final 9:13 MP4 and the complete submission ZIP are intentionally not duplicated into normal Git history. They are generated or supplied separately in the final submission package.

## Team Vision AI
- **Syed Sajjad Hussain** — Team Lead, project coordination, product direction, system planning, final integration, UI review, documentation supervision, quality review and submission readiness.
- **Ali Khan** — Demo support, presentation support, voiceover coordination, visual communication and submission asset preparation.
- **Abdul Hameed** — Big Data processing support, Spark workflow assistance, data-quality review and technical validation support.
- **Hamdan Ahmed** — ML verification review, testing support and final-stage validation assistance.

**Mentor / Faculty:** Sir Kamran Hyder

## Final evidence
The final project was manually verified on Windows with working Python prediction, Spark prediction, Run Both Models, and all four Processing Center stages. Existing comparison evidence records **1,120 unseen cases** with **94.46% diagnostic agreement** at the configured 2% comparison tolerance. This diagnostic agreement is not an accuracy guarantee.

## Competition
**TechWiz 7 — Data Science Intelligence Arena**

Team: **Vision AI**
