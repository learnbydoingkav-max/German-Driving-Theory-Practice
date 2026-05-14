import streamlit as st
from openai import OpenAI
import json

st.set_page_config(page_title="German Driving Theory Practice", page_icon="🚗", layout="centered")
st.title("🚗 German Driving Theory – MCQ Practice (AI-Powered)")

# --- OpenRouter Client ---
@st.cache_resource
def get_client():
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=st.secrets["OPENROUTER_API_KEY"],
    )

# --- Generate a situation-based question with a real image URL ---
@st.cache_data(ttl=3600)
def generate_question(topic: str, q_index: int):
    client = get_client()
    prompt = f"""Generate a situation-based multiple-choice question about German driving regulations on the topic: "{topic}".

The question should describe a real driving scenario a learner driver in Germany might face.

For the image_url field, provide a real, publicly accessible image URL from Wikimedia Commons 
(https://upload.wikimedia.org/wikipedia/commons/...) that shows a relevant German traffic sign or road situation.
Only use URLs you are confident exist. If unsure, set image_url to null.

Return ONLY valid JSON in this exact format:
{{
  "question": "You are driving and see this sign. What must you do?",
  "image_url": "https://upload.wikimedia.org/wikipedia/commons/...",
  "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
  "correct": "A",
  "explanation": "..."
}}"""
    completion = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        stream=False,
    )
    raw = completion.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        st.error(f"Failed to decode JSON from AI response: {raw}")
        st.stop()

# --- Session State ---
st.session_state.setdefault("current_q", 0)
st.session_state.setdefault("answers", {})
st.session_state.setdefault("revealed", {})

# --- Topics ---
TOPICS = [
    "traffic signs",
    "right of way rules",
    "speed limits",
    "motorway (Autobahn) rules",
    "parking regulations",
]

idx = st.session_state.current_q
topic = TOPICS[idx % len(TOPICS)]

# --- Load question ---
with st.spinner("Loading question..."):
    try:
        q = generate_question(topic, idx)
    except Exception as e:
        st.error(f"Failed to generate question: {e}")
        st.stop()

qid = f"q_{idx}"
is_revealed = st.session_state.revealed.get(qid, False)

# --- Question Box ---
with st.container(border=True):
    st.markdown(f"**Q{idx + 1} | Topic: {topic.title()}**")

    # Display situation image if provided
    image_url = q.get("image_url")
    if image_url:
        try:
            st.image(image_url, caption="Situation", width=300)
        except Exception:
            st.caption("_(Image could not be loaded)_")

    st.markdown(q["question"])

# --- Options Box ---
with st.container(border=True, height=220):
    choice = st.radio(
        "Select your answer:",
        list(q["options"].keys()),
        format_func=lambda l: f"{l}. {q['options'][l]}",
        key=f"radio_{qid}",
        disabled=is_revealed,
        label_visibility="collapsed",
    )
    st.session_state.answers[qid] = choice

# --- Navigation Buttons ---
with st.container(border=True, height=80):
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("⬅ Previous", use_container_width=True, disabled=(idx == 0)):
            st.session_state.current_q = max(0, idx - 1)
            st.rerun()
    with col2:
        if st.button("✅ Submit", use_container_width=True, disabled=is_revealed):
            st.session_state.revealed[qid] = True
            st.rerun()
    with col3:
        if st.button("Next ➡", use_container_width=True):
            st.session_state.current_q = idx + 1
            st.rerun()

# --- Answer/Explanation Box ---
with st.container(border=True, height=130):
    if is_revealed:
        user_ans = st.session_state.answers.get(qid)
        if user_ans == q["correct"]:
            st.success(f"✅ Correct! Answer: {q['correct']}")
        else:
            st.error(f"❌ Incorrect. Correct: {q['correct']} | Your answer: {user_ans or '—'}")
        st.info(q.get("explanation", ""))
    else:
        st.caption("Submit your answer to see the explanation.")
