# Finans Otomasyon

Streamlit finance automation dashboard for Finnhub market snapshots, stock and
commodity scoring, news sentiment, SQLite history, and scheduled daily updates.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Finnhub](https://img.shields.io/badge/Data-Finnhub-1B2536?style=for-the-badge)](https://finnhub.io)
[![SQLite](https://img.shields.io/badge/Storage-SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

## 30-Second Scan

| Area | What this project shows |
|---|---|
| Finance workflow | Daily stock and commodity snapshots with scoring, history, alerts, and dashboard review |
| Analytics | 6-factor equity scoring, 4-factor commodity ETF scoring, momentum checks, and VADER news sentiment |
| Automation | GitHub Actions workflow for 09:00 Turkey-time data refreshes |
| Data model | SQLite snapshot history for prices, scores, alerts, and trend review |
| Portfolio value | A recruiter-readable finance automation project combining APIs, scheduling, sentiment, and visualization |

> Educational analytics only. This project does not provide investment advice,
> trading signals, or financial recommendations.

## Features

- Default watchlist covering major US equities and commodity ETFs:
  `AAPL`, `MSFT`, `GOOGL`, `AMZN`, `NVDA`, `META`, `TSLA`, `GLD`, `SLV`, `USO`, `UNG`, `DBA`.
- Finnhub-powered quote, fundamentals, analyst recommendation, and news pulls.
- Equity scoring across valuation, profitability, growth, financial health, technicals, and analyst/news inputs.
- Commodity ETF scoring across technical trend, news, volatility, and long-term trend.
- VADER sentiment scoring and keyword grouping for earnings, M&A, regulation, macro, and other news themes.
- Streamlit dashboard with manual refresh, historical charts, score trends, and alert views.
- GitHub Actions workflow for unattended daily snapshot collection.

## Tech Stack

| Layer | Tools |
|---|---|
| App | Python 3.11, Streamlit |
| Data | Finnhub API, SQLite |
| Analytics | pandas, VADER, custom scoring modules |
| Charts | Plotly |
| Automation | GitHub Actions, optional Windows Task Scheduler |

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env
# Add FINNHUB_API_KEY=your_key_here to .env

python -m jobs.daily_snapshot
streamlit run streamlit_app.py
```

Open `http://localhost:8501` after Streamlit starts.

## Daily Automation

The repository includes a GitHub Actions workflow for daily data collection.

1. Add a repository secret named `FINNHUB_API_KEY`.
2. Confirm `.github/workflows/daily-snapshot.yml` is enabled.
3. The workflow runs at `06:00 UTC`, which is `09:00` in Turkey.
4. Use **Actions -> Daily Snapshot -> Run workflow** for a manual refresh.

## Data Sources

- Finnhub quote, fundamentals, recommendation, and company news endpoints.
- Local SQLite database under `data/` for historical snapshots.

## Validation

- Run `python -m jobs.daily_snapshot` to verify API connectivity and database writes.
- Run `streamlit run streamlit_app.py` to verify dashboard rendering.
- Confirm the dashboard clearly labels data availability and shows the non-advisory disclaimer.

## License

MIT License. See [LICENSE](LICENSE).
