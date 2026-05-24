import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Adaptive Document Prep System",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Adaptive Document Preparation System")
st.markdown("Study smarter — the system adapts to your weak areas over time.")

# ─── Sidebar ───
st.sidebar.header("Session Settings")

sections = st.sidebar.multiselect(
    "Select sections to study:",
    options=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
    default=["1"]
)

num_questions = st.sidebar.slider(
    "Number of questions per section:",
    min_value=1,
    max_value=10,
    value=5
)

simulate = st.sidebar.checkbox("Simulate answers automatically", value=True)

# ─── Start Session Button ───
if st.sidebar.button("🚀 Start Study Session"):
    if not sections:
        st.error("Please select at least one section!")
    else:
        with st.spinner("Generating questions and running session..."):
            try:
                response = requests.post(f"{API_URL}/prep/start", json={
                    "section_ids": sections,
                    "num_questions": num_questions,
                    "simulate": simulate
                })
                result = response.json()

                if response.status_code == 200:
                    # ─── Score ───
                    st.success("Session completed!")
                    score = result["score"]
                    total = result["total_questions"]

                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Questions", total)
                    col2.metric("✅ Correct", score["correct"])
                    col3.metric("❌ Wrong", score["wrong"])

                    # ─── Questions Review ───
                    st.subheader("Questions Review")
                    for i, q in enumerate(result["questions"], 1):
                        with st.expander(f"Q{i}: {q['question_text']}"):
                            st.write(f"**A:** {q['option_a']}")
                            st.write(f"**B:** {q['option_b']}")
                            st.write(f"**C:** {q['option_c']}")
                            st.write(f"**D:** {q['option_d']}")
                            st.info(f"✅ Correct Answer: **{q['correct_answer']}**")
                            st.caption(f"💡 {q['explanation']}")

                    # ─── KB Snapshot ───
                    st.subheader("Knowledge Base Snapshot")
                    st.json(result["kb_snapshot"])

                else:
                    st.error(f"Error: {result.get('detail', 'Something went wrong')}")

            except Exception as e:
                st.error(f"Could not connect to API: {e}")
                st.info("Make sure the server is running at http://127.0.0.1:8000")

# ─── Weak Areas Section ───
st.divider()
st.subheader("🔍 Check Weak Areas")

weak_sections = st.multiselect(
    "Select sections to check weak areas:",
    options=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
    key="weak"
)

if st.button("Check Weak Areas"):
    if not weak_sections:
        st.error("Please select at least one section!")
    else:
        with st.spinner("Checking knowledge base..."):
            try:
                ids = ",".join(weak_sections)
                response = requests.get(f"{API_URL}/prep/weak-areas/{ids}")
                result = response.json()

                weak = result.get("weak_areas", [])
                if weak:
                    st.warning(f"Found {len(weak)} weak areas:")
                    for i, w in enumerate(weak, 1):
                        st.write(f"{i}. {w}")
                else:
                    st.success("No weak areas found! You're doing great! 🎉")

            except Exception as e:
                st.error(f"Could not connect to API: {e}")

# ─── Scenario B Section ───
st.divider()
st.subheader("🧪 Run Scenario B (Evaluation)")
st.caption("Runs 3 consecutive iterations: sections 5,8 → 6,8,9 → 8")

if st.button("▶️ Run Scenario B"):
    with st.spinner("Running all 3 iterations... this may take a minute..."):
        try:
            response = requests.post(f"{API_URL}/scenario-b", json={"num_questions": 5})
            result = response.json()

            if response.status_code == 200:
                st.success("Scenario B completed successfully!")
                for key, val in result["results"].items():
                    st.write(f"**{key}** — Sections: {val['section_ids']} | Score: {val['score']}")
            else:
                st.error(f"Error: {result.get('detail', 'Something went wrong')}")

        except Exception as e:
            st.error(f"Could not connect to API: {e}")