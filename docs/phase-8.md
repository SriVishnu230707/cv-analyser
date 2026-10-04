# Phase 8: broader local matching coverage

Phase 8 expands the next enhancement identified in the README: broader rule coverage. It also makes supported technology names and aliases discoverable before uploading a resume.

## User workflow

Open **Explore supported skills and aliases** above the upload form. Search a technology or alias such as `sklearn`, `Kafka`, or `dotnet`. Results show the canonical skill and accepted wording; an empty search shows the whole catalog. Dictionary loading errors offer a retry button.

The existing upload, text review, category confirmation, comparison, evidence review, improvement suggestions, and PDF/JSON download workflow stays in place. New technologies participate in the same scoring policy. Unknown names still require review and genuine alias mapping; related tools are not treated as equivalent.

## Coverage

Dictionary version **1.1.0** contains **71 canonical skills**, adding 20:

Svelte, SvelteKit, NestJS, .NET, ASP.NET Core, SQLAlchemy, Celery, RabbitMQ, Apache Kafka, Elasticsearch, OpenSearch, Ansible, Jenkins, Prometheus, Grafana, Apache Spark, Apache Airflow, scikit-learn, Hugging Face Transformers, and Power BI.

Examples of aliases: `sklearn` → scikit-learn, `kafka` → Apache Kafka, `dotnet` → .NET, `pyspark` → Apache Spark, and `powerbi` → Power BI. Svelte/SvelteKit, SQL/SQLAlchemy, and .NET/ASP.NET Core remain separate skills. Overlapping names select the longest supported phrase.

Responsibility rules version **1.1.1** includes four new task families, bringing the total to ten:

| Job requirement | Eligible example |
|---|---|
| Monitor service health using Prometheus | Monitored service health using Prometheus. |
| Optimize SQL queries | Optimized SQL queries. |
| Automate CI/CD pipelines using Jenkins | Automated CI/CD pipelines using Jenkins. |
| Build data pipelines using Apache Airflow | Built data pipelines using Apache Airflow. |

Actions, objects, and required technology wording must occur within the same eligible clause under Projects or Experience. Negated/learning evidence, tool listings alone, and multi-task or unsupported wording receive no automatic responsibility credit. Possible positive evidence still needs user confirmation. The report and both export formats carry the new taxonomy and rule versions.

Task targets are distinct: logs, metrics, and service health are not interchangeable, nor are build/deployment/CI/CD pipelines or data/ETL pipelines. See the [follow-up bug fixes](bug-fixes.md) for runtime dictionary validation and matching regressions.

## Validation

All **113 backend tests**, **4 frontend request tests**, and the production build passed. New regressions cover every catalog alias and its offsets, near matches, distinct overlapping skills, learning gates, positive and negative task examples, explicit confirmation, and JSON export. Earlier unknown-skill regressions now use SolidJS because Svelte is supported.

Browser verification covered alias search, empty results, a simulated failed dictionary request followed by successful retry, mobile/desktop layouts, and the complete extraction/review/comparison flow with the new skills and tasks. No uncaught browser errors were reported.

The existing 18 development fixtures produced 63 true-positive automatic skill matches, zero false positives, and zero false negatives. This is a small synthetic development regression check, not a new held-out or real-world accuracy claim. Reserved cases were not used to tune these additions. The evaluation script now reports its actual rule version.

## Run

Use the same setup as Phase 4, API port 8001, and frontend port 5173. No new packages, cloud models, credentials, or downloads are required.

```powershell
python -m pytest backend/tests -q
cd frontend
npm test
npm run build
```

The scoring weights and v1.1 report schema remain unchanged. More supported job skills can now enter the reviewed denominator, so a new comparison may differ from a prior report. Previously downloaded reports remain snapshots. Semantic proposals and broader factual rewriting remain future enhancements.
