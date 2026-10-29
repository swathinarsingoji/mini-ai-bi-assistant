
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from database import initialize_database, run_query
from ai_assistant import interpret_question


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Mini AI Business Intelligence Assistant",
    description="Ask questions about sales data using natural language.",
    version="1.0.0",
    lifespan=lifespan,
)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


@app.get("/")
def home():
    return {
        "message": "Mini AI BI Assistant API is running",
        "docs": "/docs",
    }


@app.get("/api/health")
def health():
    return {"status": "healthy"}


@app.post("/api/ask")
def ask_question(request: QuestionRequest):
    try:
        # Identify the question and its parameters.
        intent, params = interpret_question(request.question)

        # Execute the corresponding predefined database query.
        rows = run_query(intent, params)

        value = None
        answer = ""

        if intent == "total_revenue":
            value = round(float(rows[0]["revenue"] or 0), 2)
            answer = f"Total revenue is {value:,.2f}."

        elif intent == "top_product":
            if not rows:
                raise ValueError("No valid product sales were found.")

            value = round(float(rows[0]["revenue"] or 0), 2)
            answer = (
                f"{rows[0]['product']} generated the highest revenue: "
                f"{value:,.2f}."
            )

        elif intent == "top_region":
            if not rows:
                raise ValueError("No valid regional sales were found.")

            value = round(float(rows[0]["revenue"] or 0), 2)
            answer = (
                f"{rows[0]['region']} generated the highest sales: "
                f"{value:,.2f}."
            )

        elif intent == "monthly_trend":
            answer = "Here is the monthly revenue trend."

        elif intent == "month_comparison":
            month1 = params.get("month1")
            month2 = params.get("month2")

            if not month1 or not month2:
                raise ValueError(
                    "Please specify two months to compare."
                )

            revenue_by_month = {
                row["month"]: float(row["revenue"] or 0)
                for row in rows
            }

            revenue1 = revenue_by_month.get(month1, 0)
            revenue2 = revenue_by_month.get(month2, 0)
            difference = round(revenue2 - revenue1, 2)

            if revenue1 == 0:
                percentage = None
                percent_text = (
                    "Percentage change is undefined because "
                    "the first month's revenue is zero."
                )
            else:
                percentage = round(
                    (difference / revenue1) * 100, 2
                )
                percent_text = (
                    f"Percentage change: {percentage:.2f}%."
                )

            value = difference
            answer = (
                f"Revenue changed from {month1} ({revenue1:,.2f}) "
                f"to {month2} ({revenue2:,.2f}). "
                f"Difference: {difference:,.2f}. {percent_text}"
            )

            rows = [
                {"month": month1, "revenue": revenue1},
                {"month": month2, "revenue": revenue2},
            ]

        else:
            raise ValueError(
                "Unsupported question type. Ask about total revenue, "
                "top product, monthly trend, top region, or month comparison."
            )

        return {
            "success": True,
            "question": request.question,
            "intent": intent,
            "answer": answer,
            "value": value,
            "unit": "Currency units (the dataset does not specify currency)",
            "supporting_data": rows,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail=(
                "An internal error occurred while processing the question. "
                "Check the backend terminal for details."
            ),
        )
