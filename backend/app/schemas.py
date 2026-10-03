from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Job = Literal["admin.", "blue-collar", "entrepreneur", "housemaid", "management", "retired",
              "self-employed", "services", "student", "technician", "unemployed", "unknown"]
Marital = Literal["divorced", "married", "single"]
Education = Literal["primary", "secondary", "tertiary", "unknown"]
YesNo = Literal["yes", "no"]
Contact = Literal["cellular", "telephone", "unknown"]
Month = Literal["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
POutcome = Literal["failure", "other", "success", "unknown"]


class ClientRecord(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "age": 35, "job": "management", "marital": "married", "education": "tertiary",
        "default": "no", "balance": 1500, "housing": "yes", "loan": "no",
        "contact": "cellular", "day": 15, "month": "may", "campaign": 2,
        "pdays": -1, "previous": 0, "poutcome": "unknown",
    }})

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
    prediction: Literal["yes", "no"]
    probability: float
    threshold: float
    likelihood: Literal["low", "medium", "high"]


class BatchRowError(BaseModel):
    row: int
    error: str


class BatchResponse(BaseModel):
    total: int
    predicted_yes: int
    predicted_no: int
    failed: int
    results: list[dict]
    errors: list[BatchRowError]
