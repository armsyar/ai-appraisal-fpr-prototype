import streamlit as st
import anthropic
import json
import time

from prompt_template import APPRAISAL_SYSTEM_PROMPT, build_user_prompt
from storage import save_response

st.set_page_config(
    page_title="AI Appraisal Drafting Assistant",
    page_icon="📋",
    layout="wide"
)


@st.cache_data
def load_cases():
    with open("synthetic_cases.json") as f:
        return json.load(f)["cases"]


cases = load_cases()
case_map = {
    f"{c['name']} — {c['case_id']} — {c['role']} ({c['department']})": c
    for c in cases
}

with st.sidebar:
    st.title("⚙️ Settings")

    api_key = st.secrets.get("ANTHROPIC_API_KEY", "")

    st.divider()
    st.markdown("**Participant Profile** *(complete once per participant, before their first task)*")
    participant_id = st.text_input(
        "Anonymous participant code (e.g. P01)",
        key="participant_id",
        help="Assign this code at recruitment. Do not use a real name or employee ID.",
    )
    nationality = st.selectbox(
        "Nationality / primary work location",
        ["Singaporean", "Australian", "American", "British", "Malaysian", "Indian", "Other"],
        key="nationality",
    )
    years_experience = st.number_input(
        "Years of appraisal-writing experience",
        min_value=0, max_value=50, value=0, step=1,
        key="years_experience",
    )
    is_former_manager = st.radio(
        "Current or former line manager?",
        ["Current line manager", "Former line manager"],
        key="is_former_manager",
    )
    prior_ai_usage = st.radio(
        "Prior use of generative-AI tools (e.g. ChatGPT, Claude)?",
        ["No", "Yes"],
        key="prior_ai_usage",
    )

    st.divider()
    st.markdown("**Study Condition**")
    condition = st.radio(
        "Participant condition",
        ["AI-Assisted", "Manual"],
        index=0
    )
    st.caption("Set to Manual for the control condition. AI generation will be disabled.")

    task_order = st.radio(
        "Order of this task for this participant",
        ["1st", "2nd"],
        key="task_order",
        help="Counterbalancing check: was this the participant's first or second task in the session?",
    )

st.title("📋 AI Appraisal Drafting Assistant")
st.markdown(
    "Research prototype for drafting annual appraisal summaries from structured evidence. "
    "The AI output is an editable **draft**, not a final appraisal decision, and managers remain "
    "responsible for the final wording."
)

st.info(
    "This prototype uses synthetic employee cases only and avoids protected attributes. "
    "It is designed to study appraisal summary quality, evidence-faithfulness, fairness, and human oversight "
    "in AI-assisted appraisals."
)

selected_label = st.selectbox("Select Employee Case", list(case_map.keys()))
case = case_map[selected_label]

current_signature = f"{case['case_id']}_{condition}"

if st.session_state.get("current_signature") != current_signature:
    st.session_state["current_signature"] = current_signature
    for key in ["last_output", "last_elapsed", "last_case", "last_case_id", "manual_start"]:
        if key in st.session_state:
            del st.session_state[key]

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader(f"📂 Employee Data — {case['name']} ({case['case_id']})")

    with st.expander("🏷️ Profile", expanded=True):
        st.markdown(
            f"**Name:** {case['name']}  \n"
            f"**Role:** {case['role']}  \n"
            f"**Department:** {case['department']}  \n"
            f"**Tenure:** {case['tenure_years']} year(s)  \n"
            f"**Review Period:** {case['review_period']}  \n"
            f"**Performance Consistency:** {case['performance_consistency']}"
        )

    with st.expander("📊 Performance Scores (out of 5)", expanded=True):
        for metric, score in case["performance_scores"].items():
            label = metric.replace("_", " ").title()
            st.progress(score / 5, text=f"{label}: {score}/5")

    with st.expander("🎯 Goal Outcomes", expanded=True):
        for g in case["goals"]:
            icon = "✅" if g["status"] == "Completed" else (
                "⚠️" if g["status"] == "Partially Met" else "❌"
            )
            st.markdown(
                f"{icon} **{g['goal']}**  \n→ *{g['status']}* — {g['notes']}"
            )

    with st.expander("💬 Peer Feedback", expanded=False):
        for fb in case["peer_feedback"]:
            st.info(f'"{fb}"')

    with st.expander("📝 Manager Notes", expanded=False):
        st.warning(f'"{case["manager_notes"]}"')

with col2:
    st.subheader("✍️ Appraisal Summary Output")

    if condition == "Manual":
        st.info(
            "**Manual Condition** — Please write your appraisal summary following the **exact same four-section structure** used by the AI. "
            "This ensures both conditions produce comparable outputs."
        )

        if "manual_start" not in st.session_state:
            st.session_state["manual_start"] = time.time()

        st.markdown(
            f"""## Annual Performance Appraisal Summary
**Name:** {case['name']} | **Role:** {case['role']} | **Department:** {case['department']} | **Review Period:** {case['review_period']}"""
        )

        st.markdown("### 1. Overall Performance Summary")
        overall = st.text_area(
            "Write 1–2 paragraphs summarising the year, including performance consistency and high-level interpretation of the scores and goal outcomes.",
            height=130,
            placeholder="e.g. This has been a strong year of performance...",
            key="manual_overall",
        )

        st.markdown("### 2. Key Strengths")
        strengths = st.text_area(
            "Use bullet points only (3–5 bullets). Each strength must be clearly linked to documented evidence (goals, scores, peer feedback, or manager notes).",
            height=150,
            placeholder="- **Technical competency:** Highest-rated competency (4.5), supported by peer feedback...\n- **Delivery and goal ownership:** ...",
            key="manual_strengths",
        )

        st.markdown("### 3. Development Areas")
        development = st.text_area(
            "Use bullet points only (2–4 bullets). Each development area must be linked to specific evidence. If evidence is missing or unclear, say so rather than guessing.",
            height=130,
            placeholder="- **Stakeholder communication:** Manager notes specifically flag...\n- **Cross-team engagement:** Peer feedback notes...",
            key="manual_development",
        )

        st.markdown("### 4. Suggested Next-Step Focus")
        next_steps = st.text_area(
            "Write 1–2 paragraphs proposing practical next steps or focus areas for the coming period, clearly connected to the evidence and development areas above.",
            height=130,
            placeholder="Given the documented gap in stakeholder communication, a practical focus for the coming period could include...",
            key="manual_next_steps",
        )

        st.caption(
            "*This draft is intended for manager review and editing and does not constitute a final appraisal decision.*"
        )

        st.divider()
        st.subheader("📋 Rubric Rating Form (Manual)")
        st.caption(
            "Read the case first, then rate the summary you wrote using the rubric below "
            "(1 = weakest, 5 = strongest)."
        )

        st.caption(
                    "**Unsupported claim flag:** Mark **Yes** if the summary introduces at least one factual claim not traceable to the synthetic case."
                )

        q_clarity = st.slider(
            "Clarity — Easy to understand, well-structured, and coherent", 1, 5, 3, key="manual_clarity"
        )
        q_specificity = st.slider(
            "Specificity — Uses concrete case evidence rather than vague statements", 1, 5, 3, key="manual_specificity"
        )
        q_balance = st.slider(
            "Balance — Represents strengths and development areas fairly relative to the evidence", 1, 5, 3, key="manual_balance"
        )
        q_tone = st.slider(
            "Tone — Professional, respectful, and appropriate for HR appraisal use", 1, 5, 3, key="manual_tone"
        )
        q_accuracy = st.slider(
            "Accuracy — Faithful to the case evidence without unsupported claims", 1, 5, 3, key="manual_accuracy"
        )
        q_unsupported_claim = st.radio(
            "Unsupported claim flag — Does the summary introduce any factual claim not present in the synthetic case?",
            ["No", "Yes"],
            index=0,
            key="manual_unsupported_claim_flag"
        )
        q_notes = st.text_area(
            "Notes on unsupported claims or major omissions (optional)",
            height=90,
            key="manual_rubric_notes"
        )

        st.divider()
        st.subheader("🤝 Perception Questionnaire")
        st.caption(
            "Now think about the process of producing this summary, not just the text itself. "
            "Rate each statement from 1 (strongly disagree) to 5 (strongly agree)."
        )
        q_fairness = st.slider(
            "Fairness — This process produced a fair representation of the employee's performance", 1, 5, 3, key="manual_fairness"
        )
        q_trust = st.slider(
            "Trust — I trust the accuracy and judgement reflected in this summary", 1, 5, 3, key="manual_trust"
        )
        q_usefulness = st.slider(
            "Usefulness — This process was useful for producing an appraisal summary", 1, 5, 3, key="manual_usefulness"
        )
        q_transparency = st.slider(
            "Transparency — It was clear to me how this summary was derived from the underlying evidence", 1, 5, 3, key="manual_transparency"
        )
        q_retained_control = st.slider(
            "Retained control — I felt I retained control over the final content of this summary", 1, 5, 3, key="manual_retained_control"
        )

        if st.button("✅ Submit Manual Summary", use_container_width=True):
            elapsed = time.time() - st.session_state["manual_start"]

            summary_text = f"""## Annual Performance Appraisal Summary
**Name:** {case['name']} | **Role:** {case['role']} | **Department:** {case['department']} | **Review Period:** {case['review_period']}

### 1. Overall Performance Summary
{(overall or '').strip()}

### 2. Key Strengths
{(strengths or '').strip()}

### 3. Development Areas
{(development or '').strip()}

### 4. Suggested Next-Step Focus
{(next_steps or '').strip()}

*This draft is intended for manager review and editing and does not constitute a final appraisal decision.*"""

            ratings = {
                "participant_id": participant_id,
                "nationality": nationality,
                "years_experience": years_experience,
                "is_former_manager": is_former_manager,
                "prior_ai_usage": prior_ai_usage,
                "order": task_order,
                "case_id": case["case_id"],
                "employee_name": case["name"],
                "condition": "Manual",
                "time_seconds": round(elapsed, 2),
                "summary_text": summary_text,
                "clarity": q_clarity,
                "specificity": q_specificity,
                "balance": q_balance,
                "tone": q_tone,
                "accuracy": q_accuracy,
                "unsupported_claim_flag": q_unsupported_claim,
                "fairness": q_fairness,
                "trust": q_trust,
                "usefulness": q_usefulness,
                "transparency": q_transparency,
                "retained_control": q_retained_control,
                "rubric_notes": q_notes,
            }

            save_response(ratings)

            st.success(f"✅ Submitted! Time taken: **{elapsed/60:.1f} minutes**")
            del st.session_state["manual_start"]

    else:
        if not api_key:
            st.error(
                "AI-Assisted condition is temporarily unavailable (no API key configured on the server). "
                "Please let the researcher know, or switch to Manual condition."
            )
        else:
            if st.button("🤖 Generate AI Summary", type="primary", use_container_width=True):
                with st.spinner("Generating appraisal summary..."):
                    start = time.time()
                    try:
                        client = anthropic.Anthropic(api_key=api_key)
                        message = client.messages.create(
                            model="claude-sonnet-4-6",
                            max_tokens=1024,
                            system=APPRAISAL_SYSTEM_PROMPT,
                            messages=[
                                {"role": "user", "content": build_user_prompt(case)}
                            ],
                        )
                        st.session_state["last_output"] = message.content[0].text
                        st.session_state["last_elapsed"] = time.time() - start
                        st.session_state["last_case"] = case["name"]
                        st.session_state["last_case_id"] = case["case_id"]
                    except Exception as e:
                        st.error(f"API error: {e}")

            if "last_output" in st.session_state:
                st.success(
                    f"Generated in {st.session_state['last_elapsed']:.1f}s "
                    f"for {st.session_state['last_case']}"
                )

                output = st.session_state["last_output"]

                st.markdown("#### AI-generated draft for manager review")
                st.markdown(
                    "> This text is a draft based on the structured case evidence. "
                    "> Please review and edit before using it in any appraisal document."
                )

                st.markdown(output)

                st.caption(
                    "Note: This prototype is designed to avoid obvious biased wording, "
                    "but human reviewers must still check the draft for fairness and appropriateness."
                )

                st.divider()
                st.subheader("📋 Rubric Rating Form")
                st.caption(
                    "Rate the AI-generated summary using the same rubric used for manual summaries "
                    "(1 = weakest, 5 = strongest)."
                )

                st.caption(
                    "**Unsupported claim flag:** Mark **Yes** if the summary introduces at least one factual claim not traceable to the synthetic case."
                )

                q_clarity = st.slider(
                    "Clarity — Easy to understand, well-structured, and coherent", 1, 5, 3, key="ai_clarity"
                )
                q_specificity = st.slider(
                    "Specificity — Uses concrete case evidence rather than vague statements", 1, 5, 3, key="ai_specificity"
                )
                q_balance = st.slider(
                    "Balance — Represents strengths and development areas fairly relative to the evidence", 1, 5, 3, key="ai_balance"
                )
                q_tone = st.slider(
                    "Tone — Professional, respectful, and appropriate for HR appraisal use", 1, 5, 3, key="ai_tone"
                )
                q_accuracy = st.slider(
                    "Accuracy — Faithful to the case evidence without unsupported claims", 1, 5, 3, key="ai_accuracy"
                )
                q_unsupported_claim = st.radio(
                    "Unsupported claim flag — Does the summary introduce any factual claim not present in the synthetic case?",
                    ["No", "Yes"],
                    index=0,
                    key="ai_unsupported_claim_flag"
                )
                q_notes = st.text_area(
                    "Notes on unsupported claims or major omissions (optional)",
                    height=90,
                    key="ai_rubric_notes"
                )

                st.divider()
                st.subheader("🤝 Perception Questionnaire")
                st.caption(
                    "Now think about the process of producing this summary, not just the text itself. "
                    "Rate each statement from 1 (strongly disagree) to 5 (strongly agree)."
                )
                q_fairness = st.slider(
                    "Fairness — This process produced a fair representation of the employee's performance", 1, 5, 3, key="ai_fairness"
                )
                q_trust = st.slider(
                    "Trust — I trust the accuracy and judgement reflected in this summary", 1, 5, 3, key="ai_trust"
                )
                q_usefulness = st.slider(
                    "Usefulness — This process was useful for producing an appraisal summary", 1, 5, 3, key="ai_usefulness"
                )
                q_transparency = st.slider(
                    "Transparency — It was clear to me how this summary was derived from the underlying evidence", 1, 5, 3, key="ai_transparency"
                )
                q_retained_control = st.slider(
                    "Retained control — I felt I retained control over the final content of this summary", 1, 5, 3, key="ai_retained_control"
                )

                if st.button("📨 Submit Ratings", use_container_width=True):
                    ratings = {
                        "participant_id": participant_id,
                        "nationality": nationality,
                        "years_experience": years_experience,
                        "is_former_manager": is_former_manager,
                        "prior_ai_usage": prior_ai_usage,
                        "order": task_order,
                        "case_id": st.session_state["last_case_id"],
                        "employee_name": st.session_state["last_case"],
                        "condition": "AI-Assisted",
                        "time_seconds": round(st.session_state["last_elapsed"], 2),
                        "summary_text": st.session_state["last_output"],
                        "clarity": q_clarity,
                        "specificity": q_specificity,
                        "balance": q_balance,
                        "tone": q_tone,
                        "accuracy": q_accuracy,
                        "unsupported_claim_flag": q_unsupported_claim,
                        "fairness": q_fairness,
                        "trust": q_trust,
                        "usefulness": q_usefulness,
                        "transparency": q_transparency,
                        "retained_control": q_retained_control,
                        "rubric_notes": q_notes,
                    }

                    save_response(ratings)

                    st.success("✅ Ratings saved! Thank you.")

st.divider()
st.caption(
    "MSc CS with AI — Amsyar Ramlee (21087677) | University of Hertfordshire | Research Prototype"
)