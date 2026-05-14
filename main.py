import streamlit as st
from openai import OpenAI
import json
import requests

st.set_page_config(page_title="German Driving Theory Practice", page_icon="🚗", layout="centered")
st.title("🚗 German Driving Theory – MCQ Practice (AI-Powered)")

# --- OpenRouter Client ---
@st.cache_resource
def get_client():
    if "OPENROUTER_API_KEY" not in st.secrets:
        st.error(
            "Missing OPENROUTER_API_KEY in Streamlit secrets. "
            "Set it in Streamlit Cloud under App Settings > Secrets."
        )
        st.stop()
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=st.secrets["OPENROUTER_API_KEY"],
    )

# --- Search Wikimedia Commons for an image ---
def search_wikimedia_image(keywords: str):
    search_url = "https://commons.wikimedia.org/w/api.php"
    headers = {
        "User-Agent": "GermanDrivingTheoryPractice/1.0 (https://github.com/learnbydoingkav-max)",
    }
    if not keywords:
        return None

    base_keywords = keywords.strip()
    if "germany" not in base_keywords.lower():
        base_keywords += " Germany"

    search_variants = [
        base_keywords,
        base_keywords + " filetype:svg",
        base_keywords + " filetype:jpg",
        base_keywords + " filetype:png",
        base_keywords + " filetype:webp",
    ]
    valid_mimes = {
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/gif",
        "image/svg+xml",
        "image/webp",
        "image/bmp",
        "image/tiff",
    }

    try:
        for query in search_variants:
            params = {
                "action": "query",
                "format": "json",
                "formatversion": 2,
                "generator": "search",
                "gsrsearch": query,
                "gsrnamespace": 6,
                "gsrlimit": 20,
                "prop": "imageinfo",
                "iiprop": "url|mime",
            }
            response = requests.get(search_url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            try:
                data = response.json()
            except ValueError:
                st.warning(f"Wikimedia search returned invalid JSON: {response.text[:200]}")
                continue

            pages = data.get("query", {}).get("pages", [])
            for page in pages:
                for imageinfo in page.get("imageinfo", []) or []:
                    mime = imageinfo.get("mime", "")
                    if mime in valid_mimes:
                        return imageinfo.get("url")
        return None
    except requests.RequestException as e:
        st.warning(f"Failed to search Wikimedia: {e}")
        return None

# --- Generate a situation-based question with image keywords ---
@st.cache_data(ttl=3600)
def generate_question(topic: str, q_index: int):
    client = get_client()
    prompt = f"""Generate a situation-based multiple-choice question about German driving regulations on the topic: "{topic}".

The question should describe a real driving scenario a learner driver in Germany might face.

Provide image_keywords as a string of search terms (e.g., "stop sign traffic light") that can be used to find a relevant image on Wikimedia Commons.

Return ONLY valid JSON in this exact format:
{{
  "question": "You are driving and see this sign. What must you do?",
  "image_keywords": "stop sign Germany",
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
        q = json.loads(raw)
    except json.JSONDecodeError:
        st.error(f"Failed to decode JSON from AI response: {raw}")
        st.stop()
    
    # Search for image using keywords
    keywords = q.get("image_keywords", "")
    if keywords:
        image_url = search_wikimedia_image(keywords)
        q["image_url"] = image_url
    else:
        q["image_url"] = None
    
    return q

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
    answer_keys = [""] + list(q["options"].keys())
    choice = st.radio(
        "Select your answer:",
        answer_keys,
        format_func=lambda l: "Select an answer" if l == "" else f"{l}. {q['options'][l]}",
        key=f"radio_{qid}",
        disabled=is_revealed,
        label_visibility="collapsed",
    )
    selected_answer = None if choice == "" else choice
    st.session_state.answers[qid] = selected_answer

# --- Navigation Buttons ---
with st.container(border=True, height=80):
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("⬅ Previous", use_container_width=True, disabled=(idx == 0)):
            st.session_state.current_q = max(0, idx - 1)
            st.rerun()
    with col2:
        if st.button("✅ Submit", use_container_width=True, disabled=is_revealed):
            if st.session_state.answers.get(qid) is None:
                st.warning("Please select an answer before submitting.")
            else:
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
