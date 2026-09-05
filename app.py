import uuid

import streamlit as st
import anthropic
import json

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
case_map = {c["case_id"]: c for c in cases}
case_label = {
    c["case_id"]: f"{c['name']} — {c['case_id']} — {c['role']} ({c['department']})"
    for c in cases
}

# --- Participant session identity (non-identifying pairing code only) ---
# Generated once per browser session. Used ONLY so the analysis can pair a
# given participant's AI-Assisted and Manual responses on the same case
# together (a within-subjects / repeated-measures design). It is not a
# name, login, email address, or any other personally identifying value,
# and it is never shown to anyone but the participant themselves.
if "participant_session_id" not in st.session_state:
    st.session_state["participant_session_id"] = uuid.uuid4().hex[:10]

# --- Per-case progress tracking ---
# case_progress[case_id] = {"ai_done": bool, "manual_done": bool, "ai_output": str|None}
if "case_progress" not in st.session_state:
    st.session_state["case_progress"] = {
        c["case_id"]: {"ai_done": False, "manual_done": False, "ai_output": None}
        for c in cases
    }

with st.sidebar:
    st.title("⚙️ Settings")

    _secret_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    workspace_id = st.secrets.get("ANTHROPIC_WORKSPACE_ID", "")
    if _secret_key:
        # A shared key is configured on the server (e.g. deployed on Streamlit
        # Community Cloud) - use it directly and never show a key field to
        # the participant.
        api_key = _secret_key
    else:
        # No server-side secret configured (e.g. running locally on a laptop
        # without .streamlit/secrets.toml set up) - fall back to the original
        # manual entry field so local testing keeps working.
        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            help="Get yours at https://console.anthropic.com/",
        )

    st.divider()
    st.caption(
        f"Session pairing code: `{st.session_state['participant_session_id']}` "
        "— a random, non-identifying code used only to link your own "
        "responses across the steps and cases you complete. It is not "
        "your name, login, or any other personal information."
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
    "in AI-assisted appraisals. For each case you choose, you will first generate an AI-Assisted summary and "
    "rate it, then write your own Manual summary for the same case and self-rate it."
)

# --- Progress overview across all four cases ---
st.subheader("📊 Your progress")
progress_cols = st.columns(len(cases))
for col, c in zip(progress_cols, cases):
    prog = st.session_state["case_progress"][c["case_id"]]
    if prog["ai_done"] and prog["manual_done"]:
        status = "✅ Done"
    elif prog["ai_done"] or prog["manual_done"]:
        status = "🟡 In progress"
    else:
        status = "⬜ Not started"
    with col:
        st.markdown(f"**{c['case_id']}**  \n{c['name']}  \n{status}")

completed_cases = [
    cid for cid, p in st.session_state["case_progress"].items()
    if p["ai_done"] and p["manual_done"]
]
in_progress_cases = [
    cid for cid, p in st.session_state["case_progress"].items()
    if (p["ai_done"] or p["manual_done"]) and not (p["ai_done"] and p["manual_done"])
]

st.divider()

if len(completed_cases) == len(cases):
    st.success(
        "🎉 You have completed all four synthetic cases. Thank you very much for taking part! "
        "You do not need to do anything else — you may close this window."
    )
    st.stop()

if len(completed_cases) >= 1 and not in_progress_cases:
    st.info(
        f"You have completed {len(completed_cases)} of 4 case(s). You have met the minimum "
        "requirement to take part — you may stop here, or continue with another case below "
        "if you have the time and interest to do so."
    )

# Cases still available to select: anything not yet fully completed.
available_case_ids = [c["case_id"] for c in cases if c["case_id"] not in completed_cases]

# If a case is already in progress (AI done, manual not done), default to it
# rather than letting the participant wander to a fresh case mid-task.
default_case_id = in_progress_cases[0] if in_progress_cases else available_case_ids[0]
default_index = available_case_ids.index(default_case_id)

selected_case_id = st.selectbox(
    "Select a synthetic employee case to work on",
    available_case_ids,
    index=default_index,
    format_func=lambda cid: case_label[cid],
)
case = case_map[selected_case_id]
progress = st.session_state["case_progress"][selected_case_id]

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


def render_questionnaire(key_prefix: str, subject_caption: str) -> dict:
    """
    Renders the combined Participant Questionnaire (quality rubric +
    perception measures + open-text reflections) and returns the values
    entered, keyed by field name. `key_prefix` must be unique per
    case_id + condition combination (e.g. "ai_EMP101" / "manual_EMP101")
    so widget keys never collide across cases within one session.
    """
    st.divider()
    st.subheader("📋 Participant Questionnaire")
    st.caption(subject_caption + " (1 = Strongly Disagree, 5 = Strongly Agree).")

    q_clarity = st.slider(
        "Clarity — The summary is easy to understand", 1, 5, 3, key=f"{key_prefix}_clarity"
    )
    q_specificity = st.slider(
        "Specificity — The summary references specific evidence", 1, 5, 3, key=f"{key_prefix}_specificity"
    )
    q_balance = st.slider(
        "Balance — Fairly represents strengths and development areas", 1, 5, 3, key=f"{key_prefix}_balance"
    )
    q_tone = st.slider(
        "Tone — The language is professional and appropriate", 1, 5, 3, key=f"{key_prefix}_tone"
    )
    q_accuracy = st.slider(
        "Accuracy — The summary is faithful to the case evidence, without unsupported claims",
        1, 5, 3, key=f"{key_prefix}_accuracy"
    )
    q_unsupported_claim = st.radio(
        "Unsupported claim flag — Does the summary introduce any factual claim not present in the synthetic case?",
        ["No", "Yes"],
        index=0,
        key=f"{key_prefix}_unsupported_claim_flag"
    )
    q_notes = st.text_area(
        "Notes on unsupported claims or major omissions (optional)",
        height=70,
        key=f"{key_prefix}_rubric_notes"
    )
    q_fairness = st.slider(
        "Fairness — The summary feels fair to the employee", 1, 5, 3, key=f"{key_prefix}_fairness"
    )
    q_trust = st.slider(
        "Trust — I would trust this to inform an appraisal decision", 1, 5, 3, key=f"{key_prefix}_trust"
    )
    q_usefulness = st.slider(
        "Usefulness — This step meaningfully supports me in appraisal writing",
        1, 5, 3, key=f"{key_prefix}_usefulness"
    )
    q_transparency = st.slider(
        "Transparency — It is clear to me how this summary was derived from the evidence",
        1, 5, 3, key=f"{key_prefix}_transparency"
    )
    q_open_fairness = st.text_area(
        "What made this summary feel fair or unfair?",
        height=70,
        key=f"{key_prefix}_open_fairness"
    )
    q_open_trust = st.text_area(
        "What would increase your trust in this process?",
        height=70,
        key=f"{key_prefix}_open_trust"
    )

    return {
        "clarity": q_clarity,
        "specificity": q_specificity,
        "balance": q_balance,
        "tone": q_tone,
        "accuracy": q_accuracy,
        "unsupported_claim_flag": q_unsupported_claim,
        "rubric_notes": q_notes,
        "fairness": q_fairness,
        "trust": q_trust,
        "usefulness": q_usefulness,
        "transparency": q_transparency,
        "open_fairness": q_open_fairness,
        "open_trust": q_open_trust,
    }


with col2:
    if not progress["ai_done"]:
        # --- Step 1 of 2: AI-Assisted ---
        st.subheader("✍️ Step 1 of 2 — AI-Assisted Summary")
        st.info(
            "First, generate an AI-Assisted appraisal summary for this case, then rate it below. "
            "You will write your own Manual summary for the same case in Step 2, straight after this."
        )

        if not api_key:
            st.error(
                "AI-Assisted step is temporarily unavailable (no API key configured on the server). "
                "Please let the researcher know."
            )
        elif not workspace_id:
            st.error(
                "AI-Assisted step is temporarily unavailable because the researcher server configuration "
                "is incomplete. Please let the researcher know."
            )
        else:
            if st.button("🤖 Generate AI Summary", type="primary", use_container_width=True):
                with st.spinner("Generating appraisal summary..."):
                    try:
                        client = anthropic.Anthropic(
                            api_key=api_key,
                            default_headers={
                                "anthropic-workspace-id": workspace_id
                            },
                        )

                        message = client.messages.create(
                            model="claude-sonnet-4-6",
                            max_tokens=1024,
                            system=APPRAISAL_SYSTEM_PROMPT,
                            messages=[
                                {"role": "user", "content": build_user_prompt(case)}
                            ],
                        )
                        progress["ai_output"] = message.content[0].text
                    except Exception:
                        st.error("AI generation is temporarily unavailable. Please inform the researcher.")

            if progress["ai_output"]:
                st.success(f"Generated draft for {case['name']}")

                st.markdown("#### AI-generated draft for manager review")
                st.markdown(
                    "> This text is a draft based on the structured case evidence. "
                    "> Please review it before rating it below."
                )
                st.markdown(progress["ai_output"])

                st.caption(
                    "Note: This prototype is designed to avoid obvious biased wording, "
                    "but human reviewers must still check the draft for fairness and appropriateness."
                )

                answers = render_questionnaire(
                    f"ai_{selected_case_id}",
                    "Rate the AI-generated draft you just reviewed"
                )

                if st.button("📨 Submit AI-Assisted Ratings", use_container_width=True):
                    ratings = {
                        "participant_session_id": st.session_state["participant_session_id"],
                        "case_id": case["case_id"],
                        "employee_name": case["name"],
                        "condition": "AI-Assisted",
                        "summary_text": progress["ai_output"],
                        **answers,
                    }
                    save_response(ratings)
                    progress["ai_done"] = True
                    st.success("✅ Ratings saved! Moving on to Step 2 — Manual summary for this case.")
                    st.rerun()

    elif not progress["manual_done"]:
        # --- Step 2 of 2: Manual ---
        st.subheader("✍️ Step 2 of 2 — Manual Summary")
        st.info(
            "Now write your own appraisal summary for this **same case** by hand, following the "
            "**exact same four-section structure** used in Step 1. This ensures both steps produce "
            "comparable outputs. The AI draft is not shown again here, so please write from your own "
            "judgement of the evidence on the left."
        )

        st.markdown(
            f"""## Annual Performance Appraisal Summary
**Name:** {case['name']} | **Role:** {case['role']} | **Department:** {case['department']} | **Review Period:** {case['review_period']}"""
        )

        st.markdown("### 1. Overall Performance Summary")
        overall = st.text_area(
            "Write 1–2 paragraphs summarising the year, including performance consistency and high-level interpretation of the scores and goal outcomes.",
            height=130,
            placeholder="e.g. This has been a strong year of performance...",
            key=f"manual_overall_{selected_case_id}",
        )

        st.markdown("### 2. Key Strengths")
        strengths = st.text_area(
            "Use bullet points only (3–5 bullets). Each strength must be clearly linked to documented evidence (goals, scores, peer feedback, or manager notes).",
            height=150,
            placeholder="- **Technical competency:** Highest-rated competency (4.5), supported by peer feedback...\n- **Delivery and goal ownership:** ...",
            key=f"manual_strengths_{selected_case_id}",
        )

        st.markdown("### 3. Development Areas")
        development = st.text_area(
            "Use bullet points only (2–4 bullets). Each development area must be linked to specific evidence. If evidence is missing or unclear, say so rather than guessing.",
            height=130,
            placeholder="- **Stakeholder communication:** Manager notes specifically flag...\n- **Cross-team engagement:** Peer feedback notes...",
            key=f"manual_development_{selected_case_id}",
        )

        st.markdown("### 4. Suggested Next-Step Focus")
        next_steps = st.text_area(
            "Write 1–2 paragraphs proposing practical next steps or focus areas for the coming period, clearly connected to the evidence and development areas above.",
            height=130,
            placeholder="Given the documented gap in stakeholder communication, a practical focus for the coming period could include...",
            key=f"manual_next_steps_{selected_case_id}",
        )

        st.caption(
            "*This draft is intended for manager review and editing and does not constitute a final appraisal decision.*"
        )

        answers = render_questionnaire(
            f"manual_{selected_case_id}",
            "Rate the summary you just wrote"
        )

        if st.button("✅ Submit Manual Summary and Ratings", use_container_width=True):
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
                "participant_session_id": st.session_state["participant_session_id"],
                "case_id": case["case_id"],
                "employee_name": case["name"],
                "condition": "Manual",
                "summary_text": summary_text,
                **answers,
            }
            save_response(ratings)
            progress["manual_done"] = True
            st.success("✅ Submitted! Thank you for completing this case.")
            st.rerun()

    else:
        st.success(
            f"You have already completed both steps for {case['name']} ({case['case_id']}). "
            "Select a different case above if you would like to continue, or stop here if you have "
            "reached your minimum of one completed case."
        )

st.divider()
st.caption(
    "MSc CS with AI — Amsyar Ramlee (21087677) | University of Hertfordshire | Research Prototype"
)
