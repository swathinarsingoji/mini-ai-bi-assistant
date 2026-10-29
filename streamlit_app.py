
import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000/api/ask"

st.set_page_config(
    page_title="AI Business Intelligence Assistant",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Mini AI Business Intelligence Assistant")
st.write(
    "Ask questions about your sales data and get "
    "answers supported by database queries."
)

st.divider()

st.subheader("Ask a business question")

examples = [
    "What is the total revenue?",
    "Which product generated the highest revenue?",
    "Show monthly revenue trends.",
    "Which region has the highest sales?",
    "Compare revenue between January and February 2026."
]

with st.expander("Example questions"):
    for example in examples:
        st.write(f"• {example}")

question = st.text_input(
    "Enter your question",
    placeholder="Example: What is the total revenue?"
)

if st.button("Get Answer", type="primary"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        try:
            with st.spinner("Analyzing your sales data..."):
                response = requests.post(
                    API_URL,
                    json={"question": question},
                    timeout=30
                )

            if response.ok:
                data = response.json()

                st.subheader("Answer")
                st.success(
                    data.get("answer", "No answer was returned.")
                )

                if data.get("intent"):
                    st.caption(
                        f"Detected question type: {data['intent']}"
                    )

                if data.get("units"):
                    st.caption(f"Units: {data['units']}")

                st.subheader("Supporting data")

                supporting_data = data.get(
                    "supporting_data",
                    data.get("data")
                )

                if isinstance(supporting_data, list) and supporting_data:
                    st.dataframe(
                        supporting_data,
                        use_container_width=True
                    )
                elif isinstance(supporting_data, dict) and supporting_data:
                    st.json(supporting_data)
                elif supporting_data is not None:
                    st.write(supporting_data)
                else:
                    st.info(
                        "No separate supporting data was returned."
                    )
            else:
                try:
                    detail = response.json().get(
                        "detail", response.text
                    )
                except ValueError:
                    detail = response.text

                st.error(f"API error ({response.status_code}): {detail}")

        except requests.exceptions.ConnectionError:
            st.error(
                "Cannot connect to the backend. "
                "Make sure FastAPI is running at http://127.0.0.1:8000."
            )
        except requests.exceptions.Timeout:
            st.error("The request timed out. Please try again.")
        except Exception as error:
            st.error(f"Unexpected error: {error}")

st.divider()
st.caption("Mini AI Business Intelligence Assistant | Sales Analytics")
