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
[data-testid="stSidebar"] {
    background-color: #111827;
}

.stApp {
    background-color: #0e1117;
    color: white;
}

h1, h2, h3 {
    color: #f9fafb;
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
    st.title("Welcome back, Dastha 👋")

    df = get_data()

    if df.empty:
        avg_score = 0
        total_sessions = 0
        streak = 0
        level = "Lvl 1"
    else:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")

        avg_score = round(df["score"].mean(), 2)
        total_sessions = len(df)
        streak = len(df[df["timestamp"] > (pd.Timestamp.now() - pd.Timedelta(days=1))])
        level = "Lvl 1" if avg_score < 5 else "Lvl 2"

    # ---------- CARDS ----------
    col1, col2, col3, col4 = st.columns(4)

    def card(title, value):
        st.markdown(f"""
        <div style="
            background-color:#1f2937;
            padding:20px;
            border-radius:12px;
            text-align:center;
            box-shadow:0 4px 10px rgba(0,0,0,0.3);
        ">
            <p style="color:#9ca3af; font-size:14px;">{title}</p>
            <h2 style="color:white;">{value}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col1:
        card("Average Fluency", f"{avg_score}")

    with col2:
        card("Total Sessions", f"{total_sessions}")

    with col3:
        card("Current Streak", f"{streak} Days")

    with col4:
        card("Current Level", level)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---------- CHARTS ----------
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Fluency Trend")
        if not df.empty:
            st.line_chart(df.set_index("timestamp")["score"])
        else:
            st.info("No data yet. Start practicing!")

    with col2:
        st.markdown("### Skill Breakdown")
        if not df.empty:
            st.bar_chart(df["score"].value_counts())
        else:
            st.info("No data yet. Start practicing!")
