"""Request/response models for the API.

Pydantic validates every incoming request against these classes, so invalid
input (wrong category, out-of-range number, missing field) is rejected with a
clear 422 error before it ever reaches the model.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Allowed values for each categorical field (exactly the categories in the dataset).
Job = Literal["admin.", "blue-collar", "entrepreneur", "housemaid", "management", "retired",
              "self-employed", "services", "student", "technician", "unemployed", "unknown"]
Marital = Literal["divorced", "married", "single"]
Education = Literal["primary", "secondary", "tertiary", "unknown"]
YesNo = Literal["yes", "no"]
Contact = Literal["cellular", "telephone", "unknown"]
Month = Literal["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
POutcome = Literal["failure", "other", "success", "unknown"]


class ClientRecord(BaseModel):
    """One client's details: the 15 inputs the model needs."""

    # Example payload shown in the interactive API docs at /docs.
    model_config = ConfigDict(json_schema_extra={"example": {
        "age": 35, "job": "management", "marital": "married", "education": "tertiary",
        "default": "no", "balance": 1500, "housing": "yes", "loan": "no",
        "contact": "cellular", "day": 15, "month": "may", "campaign": 2,
        "pdays": -1, "previous": 0, "poutcome": "unknown",
    }})

    # ge / le = "greater or equal" / "less or equal" range checks.
    age: int = Field(ge=18, le=100)
    job: Job
    marital: Marital
    education: Education
    default: YesNo
    balance: int = Field(ge=-100_000, le=1_000_000, description="Average yearly balance (EUR)")
    housing: YesNo
    loan: YesNo
    contact: Contact
    day: int = Field(ge=1, le=31, description="Last contact day of month")
    month: Month
    campaign: int = Field(ge=1, le=100, description="Contacts during this campaign")
    pdays: int = Field(ge=-1, le=1000, description="Days since previous campaign contact (-1 = never)")
    previous: int = Field(ge=0, le=300, description="Contacts before this campaign")
    poutcome: POutcome


class Prediction(BaseModel):
    """Result of scoring one client."""

    prediction: Literal["yes", "no"]          # final decision using the tuned threshold
    probability: float                        # model score between 0 and 1
    threshold: float                          # threshold the score was compared against
    likelihood: Literal["low", "medium", "high"]  # lead priority band


class BatchRowError(BaseModel):
    """A CSV row that failed validation (row numbers start at 1, excluding the header)."""

    row: int
    error: str


class BatchResponse(BaseModel):
    """Result of scoring an uploaded CSV file."""

    total: int              # rows in the file
    predicted_yes: int
    predicted_no: int
    failed: int             # rows rejected by validation
    results: list[dict]     # each valid row's inputs plus its prediction fields
    errors: list[BatchRowError]
