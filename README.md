# FDM – Bank Marketing Term Deposit Predictor

End-to-end data mining system built on the [UCI Bank Marketing dataset](https://archive.ics.uci.edu/dataset/222/bank+marketing)
(Moro, Rita & Cortez, 2014, CC BY 4.0). It predicts whether a client contacted by a Portuguese bank's
telemarketing campaign will subscribe to a term deposit (`y`).

```
data (UCI zip) ─► ml/ cleaning ─► EDA ─► model training & selection ─► artifacts/
                                                                         │
                     React dashboard (frontend/) ◄── REST API (backend/, FastAPI)
```

## Project structure

| Path | Purpose |
| --- | --- |
| `ml/download_data.py` | Downloads the UCI archive and extracts `bank-full.csv` (45,211 rows, 16 inputs) |
| `ml/preprocess.py` | Data cleaning, writes `data/processed/bank_clean.csv` and `artifacts/cleaning_report.json` |
| `ml/eda.py` | Exploratory analysis aggregates, writes `artifacts/insights.json` |
| `ml/transformers.py` | Feature engineering and outlier-capping transformers used inside the model pipeline |
| `ml/train.py` | Trains, tunes and compares 6 models, saves the best pipeline and metrics |
| `ml/run_pipeline.py` | Runs everything above in order |
| `backend/` | FastAPI service that serves predictions, metrics and insights, plus pytest tests |
| `frontend/` | React + TypeScript dashboard (TanStack Start, Tailwind, shadcn/ui, Recharts; built with Lovable) |

## Data cleaning

1. Normalise text: trim and lower-case column names and categorical values.
2. Missing values: the dataset has no NaNs, but any that appear are median-imputed (numeric) or set to
   `unknown` (categorical). Existing `unknown` placeholders (contact 13k, poutcome 37k, education 1.9k, job 288)
   are kept as their own category because they carry signal.
3. Remove exact duplicates.
4. Validate domain rules (age 18–100, day 1–31, valid month, campaign ≥ 1, pdays = -1 or ≥ 0, yes/no binaries).
5. Drop `duration`: it is only known after the call ends and leaks the target, as the dataset authors note.
6. Encode the target as 0/1.

These steps run inside the saved scikit-learn pipeline, so training and the API apply them identically:

- Feature engineering: a previously-contacted flag, days since the previous contact, signed log balance,
  total contacts, and age group.
- Outliers are winsorised at the 1st/99th percentiles, learned on training data only.
- Numeric features are standardised and categorical features one-hot encoded.

## Modelling

The data is split 80/20 with stratification. Each model is tuned with 3-fold stratified cross-validation, scored
by ROC-AUC. The classes are imbalanced (11.7% subscribe), so models use balanced class weights.

| Model | CV ROC-AUC | Test ROC-AUC | Test F1 @0.5 |
| --- | --- | --- | --- |
| **Gradient Boosting (HistGB)** | **0.795** | **0.806** | 0.459 |
| Random Forest | 0.787 | 0.797 | 0.457 |
| Logistic Regression | 0.769 | 0.776 | 0.383 |
| Decision Tree | 0.762 | 0.773 | 0.428 |
| K-Nearest Neighbours | 0.750 | 0.767 | 0.208 |
| Gaussian Naive Bayes | 0.742 | 0.752 | 0.403 |

The model with the best CV ROC-AUC is selected. Its decision threshold is tuned for F1 on out-of-fold training
predictions (0.62), which gives a test F1 of 0.487, precision of 0.45 and recall of 0.53. The winning model is then
refit on all data and saved to `artifacts/model.joblib`. Permutation importance ranks month, contact type, previous
outcome, day and age as the strongest drivers.

## Running it

Prerequisites: Python 3.11+ and Node 18+.

```powershell
# 1. Python environment
python -m venv .venv
.\.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# 2. Download data, clean, EDA, train (about 1–2 minutes)
python -m ml.run_pipeline

# 3. Backend API on http://127.0.0.1:8000 (interactive docs at /docs)
cd backend
uvicorn app.main:app --port 8000

# 4. Frontend on http://localhost:5173 (new terminal)
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to the backend, so both must be running.

Run the backend tests with `cd backend && pytest`.

## API

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/health` | Service status and loaded model |
| GET | `/api/metadata` | Input schema (allowed categories, ranges, defaults), threshold, cleaning steps |
| GET | `/api/metrics` | All model results, ROC curves, confusion matrix, feature importance |
| GET | `/api/insights` | EDA aggregates and the cleaning report |
| POST | `/api/predict` | Score one client (JSON body with the 15 input fields) |
| POST | `/api/predict/batch` | Score a CSV upload (comma or semicolon separated; extra columns are ignored) |

Example request:

```json
POST /api/predict
{"age": 35, "job": "management", "marital": "married", "education": "tertiary", "default": "no",
 "balance": 1500, "housing": "yes", "loan": "no", "contact": "cellular", "day": 15, "month": "may",
 "campaign": 2, "pdays": -1, "previous": 0, "poutcome": "unknown"}
→ {"prediction": "no", "probability": 0.4659, "threshold": 0.62, "likelihood": "medium"}
```

Training uses class weighting, so `probability` is a ranking score rather than a calibrated probability.

## Dashboard

- **Predict client**: form built from the API metadata. Shows the score, the yes/no decision and the lead priority.
- **Batch scoring**: upload a CSV (the original `bank-full.csv` works), review the ranked results and export them.
- **Model performance**: model comparison table, score bar chart, ROC curves, confusion matrix and feature importance.
- **Data insights**: class balance, cleaning steps, subscription rate by attribute, age distribution, effect of
  campaign calls, and correlations.
