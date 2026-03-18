import streamlit as st
from google import genai
import pandas as pd
import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# ------------------ CONFIG ------------------
st.set_page_config(page_title="FluentMind Pro", layout="wide")

# ------------------ STYLE ------------------
st.markdown("""
<style>
.stApp {
    background-color: #0e1117;
    color: white;
}
h1, h2 {
    color: #00FFAA;
}
</style>
""", unsafe_allow_html=True)

# ------------------ GEMINI SETUP ------------------
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# ------------------ FIREBASE SETUP ------------------
# 🔥 Important: for deployment, file must exist in repo
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ------------------ FUNCTIONS ------------------

def analyze_text(text):
    prompt = (
        "You are an English communication expert.\n\n"
        "1. Correct grammar\n"
        "2. Improve sentence\n"
        "3. Give score out of 10\n"
        "4. Give short feedback\n\n"
        f"Sentence: {text}"
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Error: {e}"


def extract_score(result):
    try:
        for line in result.split("\n"):
            if "Score" in line:
                return int(''.join(filter(str.isdigit, line)))
    except:
        return 5
    return 5


def save_data(text, feedback, score):
    db.collection("progress").add({
        "text": text,
        "feedback": feedback,
        "score": score,
        "timestamp": datetime.datetime.now()
    })


def get_data():
    docs = db.collection("progress").stream()
    data = []
    for doc in docs:
        data.append(doc.to_dict())
    return pd.DataFrame(data)

# ------------------ SIDEBAR ------------------
st.sidebar.title("🧠 FluentMind")
menu = st.sidebar.radio("Navigation", ["🏠 Home", "💬 Practice", "📊 Dashboard"])

# ------------------ HOME ------------------
if menu == "🏠 Home":
    st.title("🚀 FluentMind AI Coach")
    st.write("Improve your English communication using AI-powered feedback.")

# ------------------ PRACTICE ------------------
elif menu == "💬 Practice":
    st.title("💬 Practice with AI")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_input = st.chat_input("Type your sentence...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.write(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                result = analyze_text(user_input)
            st.write(result)

        st.session_state.messages.append({"role": "assistant", "content": result})

        score = extract_score(result)
        save_data(user_input, result, score)

# ------------------ DASHBOARD ------------------
elif menu == "📊 Dashboard":
    st.title("📊 Progress Dashboard")

    df = get_data()

    if df.empty:
        st.warning("No data yet.")
    else:
        st.dataframe(df)

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")

        st.subheader("📈 Score Trend")
        st.line_chart(df.set_index("timestamp")["score"])

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Average Score", round(df["score"].mean(), 2))

        with col2:
            st.metric("Total Attempts", len(df))
