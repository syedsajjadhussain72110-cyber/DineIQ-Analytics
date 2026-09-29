# Building DineIQ Analytics with independently verified data pipelines

> Final build note (29 Sep 2026): the final Windows-tested runtime uses Python 3.11, Java 17 and PySpark 3.5.3. Python, Spark, Run Both Models, and all four Processing Center stages were verified on Windows. The preserved evidence set also records 78 automated tests and 12 browser QA checks from the prior verified run. Team name: Vision AI.

## Business problem and purpose

Restaurant businesses need to understand the economic consequences of the meals they sell. High revenue can hide expensive preparation, heavy discounting, weak repeat purchases or unsold food. A popular dish may therefore deserve urgent review, while an overlooked item may offer a useful opportunity. DineIQ Analytics combines these perspectives in a web application that presents numerical evidence alongside recommendations.

The project implements the MenuMatrix Dining Intelligence theme in the supplied Data Science Intelligence Arena SRS. It is intended for restaurant managers, analysts, regional managers and administrators. Its purpose is analytical. Live payments, delivery-platform integration and point-of-sale operation remain outside the specified scope. The project processes supplied records rather than claiming to operate a restaurant's entire commercial infrastructure.

## Scope, assumptions and constraints

The implementation includes a reproducible synthetic dataset, related tables, quality validation, independent Spark and Python processing, model training, result comparison, dashboards, exports, source maintenance and simulations. It serves one restaurant organization. All authenticated roles may inspect its analytics, while role permissions control administrative and processing actions. It does not implement tenant isolation or branch-level row restrictions.

The dataset uses PKR amounts, integer identifiers, ISO dates, fractional discounts and portions as inventory units. Recipe unit costs are fixed within the generated period. Net revenue accounts for line discounts. Contribution subtracts preparation cost, and recorded waste cost appears separately. These measures exclude wages, rent, utilities, tax and other overhead, so the application does not label them accounting profit. Synthetic customer aliases contain no personal contact details.

## Relational dataset generation

The default generator creates 1,050,000 original order-line records and 262,500 original orders. It includes 50,000 customers, 150 menu items, ten categories, twenty restaurants, multiple campaigns, historical price changes and four hundred days of activity. It creates more than the minimum required ratings and wastage records. A manifest records actual intended table counts and the seed, while physical file-count tests check the saved data itself.

Dimensions precede facts. Orders refer to customers and restaurants. Order lines refer to orders and menu items. Ratings, inventory, waste and prices connect through the appropriate identifiers. Ordering channel is a validated field on each order. The generator supplies difficult business cases rather than simply creating uniform random numbers: expensive popular items, quiet high-margin items, high waste, promotion dependence, seasonal demand, location interactions, changing prices and late menu introductions.

Customer cohorts include customers who stop ordering during the later months and customers who join late. Item combinations introduce genuine co-occurrence for basket analysis. Peak-hour and weekend weights affect ordering behavior. All these relationships remain synthetic, so their realism is limited by the generator's assumptions. Reproducibility is valuable for testing but cannot substitute for an external restaurant dataset.

## Deliberate defects and data quality

The raw data intentionally contains duplicate primary keys, missing customers, invalid location and item references, malformed dates, negative quantities, negative prices, excessive discounts, invalid ratings, inconsistent units and impossible waste. Cancellations also appear in the source. A correct pipeline must identify these records and explain how it treats them rather than silently calculating with them.

Both implementations validate required columns and parse types. They exclude cancelled or unknown order statuses before processing dependent transactions. Foreign-key checks use retained parent tables. Invalid records are quarantined instead of inventing customers or items. Pandas writes rejected rows with reason strings, while Spark independently records raw, clean and rejected counts and writes rejected identifiers. Identical duplicates remain visible in counts even when a rejected-key anti-join cannot distinguish the retained instance from its duplicate.

## Integration and feature engineering

The fact table joins order headers, lines, menu items, categories, customers and restaurants. Revenue equals quantity multiplied by selling price and one minus the discount. Preparation cost equals quantity multiplied by the recipe unit cost. Contribution is their difference. Ratings, inventory, wastage and price histories are aggregated before joining to item-level summaries so that one-to-many relationships do not multiply transaction revenue.

Features include units sold, unique orders, contribution percentage, repeat-purchase rate, average rating, rating trend, waste percentage, promotion dependence, weekend ratio and recent sales trend. Customer features include recency, frequency, monetary value, average order value, visit frequency, preferred category, preferred channel and ordering time. Retaining these intermediate features lets an evaluator inspect why a classification or recommendation occurred.

## Spark architecture and storage

Apache Spark demonstrates both inferred CSV schemas and explicit ingestion schemas. The explicit path validates types, relationships and business ranges independently from Pandas. Spark SQL performs relational integration and analytical summaries. Operational item tables are aggregated before integration. The large processed transaction table is written as Parquet with month partitions, which supports selective time-based access and illustrates efficient analytical storage.

The Spark master can be configured for a larger environment. The generator accepts a larger row count, including a five-million-line experiment. This is an architectural extension point rather than a measured performance claim. The supplied evidence describes the dataset actually executed. The Python path currently uses in-memory Pandas and needs enough memory; larger independent Python processing should use chunked associative aggregates rather than borrowing Spark-created features.

## Independent analytical pipelines

Spark and Python read the same canonical raw records but independently construct demand features. Spark uses daily aggregation, a complete calendar and window functions. Python uses grouping, reindexing, shifting and rolling calculations. Sharing a schema contract is acceptable; sharing generated predictions or feeding Spark-derived demand features into Python would undermine verification and is deliberately avoided.

The comparison stage first aligns entity and date keys and verifies that both pipelines agree on actual demand. A discrepancy at this level indicates an ingestion or feature-contract problem. A difference between predictions can instead arise from legitimate model choices, regularization and learned parameters. The project retains these differences instead of overwriting one result to create artificial agreement.

## Menu profitability and performance classes

Menu performance uses multiple observed dimensions. Demand and margin thresholds derive from quantiles of the current dataset. Configuration controls acceptable waste and minimum ratings. Profit Drivers combine demand with sound economics and customer response. Volume Drivers have meaningful demand with weaker relative profitability. Hidden Opportunities have attractive indicators but lower volume. Low Performers have an unfavorable combination of demand, economics, quality or waste.

High sales alone cannot rescue a loss-making item. Excess waste prevents a popular dish from automatically becoming a Profit Driver. A quiet item with favorable margins and ratings can become a Hidden Opportunity. Newly introduced or unsold items retain an insufficient-history status rather than disappearing from the report. Location-specific calculations reveal that a single dish may have different outcomes across branches. These are transparent business classifications, not supervised labels with invented accuracy.

## Customer segmentation and RFM

Recency measures days since the last observed order relative to the latest dataset date. Frequency counts distinct orders, not order lines. Monetary value sums net revenue. The implementation also calculates promotion sensitivity, visit frequency, order value and preferences. Transformed and standardized behavioral features feed K-means clustering, and the resulting cluster identifier remains available for inspection.

Readable behavioral segments use explicit rules, including High-Value Loyal Customers, Frequent Customers, Promotion-Driven Customers, At-Risk Customers, New Customers and Occasional Customers. Churn signals combine stale activity with declines in recent order frequency and value. They support a targeted experiment or manager review. They do not prove that a customer will never return or establish the causal benefit of a retention offer.

## Market baskets and combinations

Basket analysis begins with the unique set of menu items within each order. Counting the same item twice in an order would inflate support, so the algorithm removes those repetitions before counting single items and pairs. It computes support, directional confidence and lift. A minimum support threshold filters combinations based on very few observations.

Bundle and cross-sell suggestions include their supporting statistics. A large lift does not automatically imply commercial value, especially for a rare combination. Managers should also consider preparation cost, capacity and discount economics. The application presents combinations as tests worth investigating rather than guaranteed revenue improvements. Unit tests verify the metrics on small baskets with manually checkable answers.

## Demand models and temporal evaluation

The shared comparison task predicts location-level daily demand. Each implementation creates a full date calendar and fills absent daily totals with zero. Features include lag-one demand, lag-seven demand, prior-only seven-day and twenty-eight-day means, and calendar seasonality. Chronological splits place training before validation and validation before testing, preventing random-split leakage across time.

Python trains Ridge, Random Forest and Gradient Boosting. Spark trains Linear Regression, Random Forest and Gradient-Boosted Trees. Each selects its model using validation RMSE. Test MAE, RMSE and R-squared remain visible for every candidate, including unfavorable scores. A seasonal baseline provides a meaningful comparison. A negative R-squared value must not be hidden or confused with a software failure; it can indicate weak generalization.

The held-out test evaluates rolling one-day-ahead predictions. Earlier observed days can enter subsequent predictions because they would be known in that setting. Recursive future forecasts instead use prior predicted values when observations are not yet available. Separate forecasts cover items, categories and restaurants over a configurable horizon. Their bands are labeled heuristic and are not claims of calibrated statistical coverage.

## Result consistency and inference

The supplied time split yields 1,120 equivalent unseen location-day cases. The comparison report contains actual demand, both predictions, numerical and relative differences, per-model absolute errors, match status and explanatory notes. Relative agreement uses a declared configurable threshold. The default two-percent setting is a strict diagnostic criterion that makes small numerical differences visible. Agreement is not prediction accuracy.

Both saved model families support live inference. A feature vector is validated before the native saved Spark MLlib predictor and the independent Python estimator evaluate it. The initial request loads the Spark JVM and models. Warm requests reuse those models and have a separate benchmark. Regression models do not naturally produce classification probabilities, so confidence percentages are not fabricated.

## Waste intelligence and risk

Wastage records contain item, location, date, quantity, unit cost and reason. Inventory records provide opening stock, replenishment, planned preparation and consumption. Quality checks reject impossible relationships and inconsistent units. Reports expose discarded quantities and costs, while menu features compare waste with preparation quantities.

A Random Forest classifier estimates high-waste risk using planned preparation and previous observed demand and waste. It uses chronological training, validation and testing periods and records accuracy, macro precision, recall, F1 and a confusion matrix. Its high synthetic-data score reflects patterns in the generator and requires real-world validation. Missing item-location days are not falsely represented as observed operations; the task predicts the next observed operating case.

## Price, promotion and rating diagnostics

Price sensitivity estimates an observational relationship between log price and demand while including trend, seasonality, weekend behavior and discount terms. It requires enough history and price variation. The resulting coefficient supports sensitivity categories, but correlated business changes can still confound the result. It must not be interpreted as the outcome of a randomized pricing experiment.

Campaign reports compare volume, revenue, contribution, customer acquisition, average order value, waste and post-promotion repeat behavior with a prior equal-length window. Rules flag margin compression, weak retention, increased waste, or volume rising while contribution falls. A decline in profitable items during a campaign can flag possible displacement; it does not prove cannibalization. Ratings are analyzed alongside menu economics and location behavior, with temporal concentration and abrupt changes flagged for investigation.

## Anomalies and evidence-backed actions

Sales anomalies use prior location revenue patterns and an Isolation Forest over order value, quantity and discount. Rating rules inspect sudden shifts, repeated identical values and bursts in review count. These are investigation signals, not accusations of fraud or manipulation. Quality-rejected duplicates remain separate from unusual but valid business events.

Every recommendation includes evidence and priority. Loss-making items receive critical attention even when their volume is attractive. High-waste items lead to preparation review. Hidden Opportunities can support promotion tests. Basket statistics support combination suggestions. Customer segments support targeting ideas, and forecast demand supports inventory planning. The action remains understandable without an external generative-AI decision service.

## What-if analysis and interface

What-if inputs include price change, campaign discount, promotion exposure, demand change, preparation change, optional waste assumptions and item removal. The engine estimates demand, revenue, waste, contribution and contribution after waste. It states assumptions about elasticity, constant unit cost and unconstrained capacity. Outputs are prominently marked estimates and should not be treated as guaranteed forecasts.

The dashboard separates executive, menu, customer, forecast, waste, branch, basket, campaign, recommendation and verification tasks. Report filters are appropriate to their columns. A separate explorer recomputes transaction totals for date and entity selections. CSV exports preserve selected report filters. Responsive styles support narrow screens, and actual browser checks test navigation, scenarios and filtered results rather than relying only on static screenshots.

## Security, persistence and operations

Passwords use a salted password hash. Signed sessions use HttpOnly and SameSite cookies. State-changing requests require CSRF tokens, and registration cannot grant an elevated role. SQLite queries use parameters. Exports neutralize formula-like text that could otherwise become an active spreadsheet formula. Uploaded archives are limited in size and reject path traversal and missing canonical tables.

SQLite stores users, named jobs, configuration, result snapshots, recommendations and audit records. The source remains canonical CSV, which is appropriate for an analytical submission but is not a transactional POS database. Background jobs allow only fixed commands. The built-in runner expects one process and a running server. A production deployment needs a durable queue, HTTPS, new credentials, persistent storage and monitoring.

## Testing, limitations and completion obligations

Tests cover authentication, CSRF, roles, registration escalation, invalid archives, scenario bounds, filtered totals, pagination and exports. Analytical tests verify basket identities, difficult menu cases, time-feature behavior, chronological ordering, independent outputs, physical dataset counts, Spark/Python cleaning equivalence and Parquet revenue reconciliation. Saved logs and machine-readable reports distinguish executed results from untested assumptions.

A local implementation does not demonstrate ninety-nine-percent hosted uptime, five-million-row throughput or production penetration resistance. These require separate environments and measurement. Team members must independently review and understand the code, declare AI assistance, publish a public repository, make genuine commits over the required competition days and publish the technical blog. The package must not invent reviewer names, contribution history, public URLs or external evaluation results.

## Future improvements

Useful extensions include historical ingredient costs, calibrated forecast intervals, causal campaign experiments, capacity-aware simulations, durable orchestration, row-level branch permissions and a chunked independent Python feature store. Real restaurant datasets would test whether synthetic relationships generalize. The priority is to preserve clear evidence and independent verification as the system grows, rather than adding attractive screens that cannot explain their calculations.

Publication status: ready for team publication on Medium. Add the real Medium URL after publishing.
