import streamlit as st
import json
import os
from datetime import date
from html import escape
from openai import OpenAI

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="Reflect",
    page_icon="◐",
    layout="centered",
)

DATA_FILE = "reflect_data.json"


# =========================================================
# PREMIUM DARK UI
# =========================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=Playfair+Display:wght@500;600&display=swap');

    html, body, [data-testid="stAppViewContainer"],
    [data-testid="stHeader"] {
        background: #101010 !important;
    }

    [data-testid="stAppViewContainer"] {
        color: #f3f1eb !important;
    }

    .block-container {
        max-width: 820px;
        padding-top: 60px;
        padding-bottom: 80px;
    }

    .reflect-title {
        font-family: 'Playfair Display', serif;
        font-size: 68px;
        line-height: 1;
        letter-spacing: -2.5px;
        color: #f3f1eb;
        margin-bottom: 12px;
    }

    .reflect-subtitle {
        font-family: 'DM Sans', sans-serif;
        color: #888888;
        font-size: 15px;
        margin-bottom: 48px;
    }

    .date-text {
        color: #666666;
        font-family: 'DM Sans', sans-serif;
        font-size: 11px;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 10px;
    }

    .section-title {
        font-family: 'Playfair Display', serif;
        font-size: 31px;
        color: #f3f1eb;
        margin-bottom: 5px;
    }

    .section-caption {
        color: #777777;
        font-family: 'DM Sans', sans-serif;
        font-size: 14px;
        margin-bottom: 25px;
    }

    /* Text inputs */
    textarea,
    input {
        background: #171717 !important;
        color: #f3f1eb !important;
        border: 1px solid #2d2d2d !important;
        border-radius: 12px !important;
    }

    textarea:focus,
    input:focus {
        border-color: #555555 !important;
        box-shadow: none !important;
    }

    textarea::placeholder,
    input::placeholder {
        color: #5f5f5f !important;
    }

    label {
        color: #bdb9b0 !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 13px !important;
    }

    /* Buttons */
    .stButton > button {
        background: #eee9df !important;
        color: #111111 !important;
        border: none !important;
        border-radius: 10px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600 !important;
        padding: 10px 22px !important;
    }

    .stButton > button:hover {
        background: #ffffff !important;
        color: #000000 !important;
    }

    /* Tabs */
    button[data-baseweb="tab"] {
        color: #666666 !important;
        font-family: 'DM Sans', sans-serif !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #f3f1eb !important;
    }

    /* Slider */
    [data-testid="stSlider"] {
        padding-bottom: 10px;
    }

    /* Dividers */
    hr {
        border-color: #292929 !important;
        margin: 38px 0 !important;
    }

    /* AI card */
    .ai-box {
        background: #181818;
        border: 1px solid #303030;
        border-radius: 18px;
        padding: 28px;
        margin-top: 25px;
    }

    .ai-title {
        font-family: 'Playfair Display', serif;
        font-size: 25px;
        color: #f3f1eb;
        margin-bottom: 18px;
    }

    .ai-text {
        color: #c6c2b9;
        font-family: 'DM Sans', sans-serif;
        font-size: 15px;
        line-height: 1.8;
    }

    /* History */
    [data-testid="stExpander"] {
        background: #171717 !important;
        border: 1px solid #2d2d2d !important;
        border-radius: 14px !important;
    }

    /* Success / error messages */
    [data-testid="stAlert"] {
        border-radius: 10px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# DATA FUNCTIONS
# =========================================================

def empty_day():
    return {
        "morning": {
            "energy": 7,
            "priorities": "",
            "intention": "",
        },
        "evening": {
            "accomplished": "",
            "unfinished": "",
            "distractions": "",
            "learning": "",
            "energy": 6,
        },
        "ai_reflection": "",
    }


def load_data():
    if not os.path.exists(DATA_FILE):
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            loaded = json.load(file)

        return loaded if isinstance(loaded, dict) else {}

    except (json.JSONDecodeError, OSError):
        return {}


def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=2,
                ensure_ascii=False
            )
        return True

    except OSError as error:
        st.error(f"Could not save journal: {error}")
        return False


# =========================================================
# LOAD TODAY
# =========================================================

data = load_data()
today = str(date.today())

if today not in data or not isinstance(data[today], dict):
    data[today] = empty_day()

else:
    # Protect against incomplete older data
    default = empty_day()

    data[today].setdefault("morning", default["morning"].copy())
    data[today].setdefault("evening", default["evening"].copy())
    data[today].setdefault("ai_reflection", "")

    for key, value in default["morning"].items():
        data[today]["morning"].setdefault(key, value)

    for key, value in default["evening"].items():
        data[today]["evening"].setdefault(key, value)


# =========================================================
# OPENAI
# =========================================================

api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key) if api_key else None


def generate_reflection(entry):

    if client is None:
        return (
            "OpenAI API key not detected. "
            "Make sure OPENAI_API_KEY is set in the same PowerShell "
            "window used to launch Streamlit."
        )

    prompt = f"""
You are the reflection engine inside a personal journaling app called Reflect.

Review this person's day.

MORNING
{entry.get("morning", {})}

EVENING
{entry.get("evening", {})}

Give a concise, honest reflection.

Use exactly these five sections:

WHAT WENT WELL
2-3 observations.

WHAT GOT IN THE WAY
2-3 observations.

PATTERN
One meaningful pattern from the day.

TOMORROW
One practical focus.

QUESTION
One thoughtful question for the user.

Rules:
- Use their actual journal information.
- Do not invent facts.
- Do not sound like a therapist.
- Do not give generic motivational quotes.
- Be direct and specific.
- Keep the entire response under 300 words.
"""

    try:
        response = client.responses.create(
            model="gpt-5-mini",
            input=prompt,
        )

        result = getattr(response, "output_text", None)

        if result:
            return result.strip()

        return "The AI returned an empty reflection."

    except Exception as error:
        return f"AI reflection could not be generated: {error}"


# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="reflect-title">Reflect.</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="reflect-subtitle">'
    'A few minutes of honesty can change the way you see a day.'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    f'<div class="date-text">{escape(today)}</div>',
    unsafe_allow_html=True,
)


# =========================================================
# TABS
# =========================================================

today_tab, history_tab = st.tabs(["Today", "History"])


# =========================================================
# TODAY
# =========================================================

with today_tab:

    # -----------------------------------------------------
    # MORNING
    # -----------------------------------------------------

    st.markdown(
        '<div class="section-title">Morning</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-caption">Start with intention.</div>',
        unsafe_allow_html=True,
    )

    morning = data[today]["morning"]

    energy = st.slider(
        "Energy",
        min_value=1,
        max_value=10,
        value=int(morning.get("energy", 7)),
        key="morning_energy",
    )

    priorities = st.text_area(
        "Three priorities",
        value=str(morning.get("priorities", "")),
        placeholder="What actually matters today?",
        height=100,
        key="morning_priorities",
    )

    intention = st.text_area(
        "Intention",
        value=str(morning.get("intention", "")),
        placeholder="How do you want to show up today?",
        height=90,
        key="morning_intention",
    )

    if st.button("Save morning", key="save_morning"):

        data[today]["morning"] = {
            "energy": energy,
            "priorities": priorities.strip(),
            "intention": intention.strip(),
        }

        if save_data(data):
            st.success("Morning saved.")


    st.markdown("<hr>", unsafe_allow_html=True)


    # -----------------------------------------------------
    # EVENING
    # -----------------------------------------------------

    st.markdown(
        '<div class="section-title">Evening</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-caption">'
        'Look back without judging yourself.'
        '</div>',
        unsafe_allow_html=True,
    )

    evening = data[today]["evening"]

    accomplished = st.text_area(
        "What did you accomplish?",
        value=str(evening.get("accomplished", "")),
        placeholder="What moved forward today?",
        height=100,
        key="evening_accomplished",
    )

    unfinished = st.text_area(
        "What remained unfinished?",
        value=str(evening.get("unfinished", "")),
        placeholder="What didn't get done?",
        height=100,
        key="evening_unfinished",
    )

    distractions = st.text_area(
        "What distracted you?",
        value=str(evening.get("distractions", "")),
        placeholder="Where did your attention go?",
        height=90,
        key="evening_distractions",
    )

    learning = st.text_area(
        "What did you learn?",
        value=str(evening.get("learning", "")),
        placeholder="Something about work, yourself, people, anything.",
        height=90,
        key="evening_learning",
    )

    evening_energy = st.slider(
        "Energy now",
        min_value=1,
        max_value=10,
        value=int(evening.get("energy", 6)),
        key="evening_energy",
    )

    if st.button("Reflect on today", key="reflect_today"):

        # Save journal first
        data[today]["evening"] = {
            "accomplished": accomplished.strip(),
            "unfinished": unfinished.strip(),
            "distractions": distractions.strip(),
            "learning": learning.strip(),
            "energy": evening_energy,
        }

        if save_data(data):

            with st.spinner("Looking for patterns..."):
                reflection = generate_reflection(data[today])

            data[today]["ai_reflection"] = reflection
            save_data(data)

            st.rerun()


    # -----------------------------------------------------
    # AI REFLECTION
    # -----------------------------------------------------

    reflection = data[today].get("ai_reflection", "")

    if reflection:

        safe_reflection = escape(str(reflection)).replace(
            "\n",
            "<br>"
        )

        st.markdown(
            '<div class="ai-box">'
            '<div class="ai-title">Your reflection</div>'
            f'<div class="ai-text">{safe_reflection}</div>'
            '</div>',
            unsafe_allow_html=True,
        )


# =========================================================
# HISTORY
# =========================================================

with history_tab:

    st.markdown(
        '<div class="section-title">History</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-caption">'
        'Your days, as you actually lived them.'
        '</div>',
        unsafe_allow_html=True,
    )

    dates = sorted(data.keys(), reverse=True)

    if not dates:

        st.write("Nothing here yet.")

    else:

        for journal_date in dates:

            entry = data[journal_date]

            with st.expander(journal_date):

                morning_entry = entry.get("morning", {})
                evening_entry = entry.get("evening", {})
                ai_entry = entry.get("ai_reflection", "")

                st.markdown("**Morning**")

                st.write(
                    f"Energy: {morning_entry.get('energy', '-')}/10"
                )

                if morning_entry.get("priorities"):
                    st.markdown("**Priorities**")
                    st.write(morning_entry["priorities"])

                if morning_entry.get("intention"):
                    st.markdown("**Intention**")
                    st.write(morning_entry["intention"])

                st.markdown("---")

                st.markdown("**Evening**")

                if evening_entry.get("accomplished"):
                    st.markdown("**Accomplished**")
                    st.write(evening_entry["accomplished"])

                if evening_entry.get("unfinished"):
                    st.markdown("**Unfinished**")
                    st.write(evening_entry["unfinished"])

                if evening_entry.get("distractions"):
                    st.markdown("**Distractions**")
                    st.write(evening_entry["distractions"])

                if evening_entry.get("learning"):
                    st.markdown("**Learning**")
                    st.write(evening_entry["learning"])

                if evening_entry:
                    st.write(
                        f"Evening energy: "
                        f"{evening_entry.get('energy', '-')}/10"
                    )

                if ai_entry:
                    st.markdown("---")
                    st.markdown("**AI Reflection**")
                    st.write(ai_entry)