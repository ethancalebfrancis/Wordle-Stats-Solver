from pathlib import Path
import streamlit as st

from wordle_solver import WordleModel, feedback_string_to_code, load_words


BASE_DIR = Path(__file__).resolve().parent
ANSWERS_PATH = BASE_DIR / "possible_answers.txt"
GUESSES_PATH = BASE_DIR / "allowed_guesses.txt"


st.set_page_config(
    page_title="Wordle Stats Solver",
    page_icon="🟩",
    layout="centered",
)


@st.cache_resource(show_spinner="Building statistical model...")
def build_model() -> WordleModel:
    answers, guesses = load_words(str(ANSWERS_PATH), str(GUESSES_PATH))
    return WordleModel(answers, guesses, logger=None)


def reset_game(model: WordleModel):
    st.session_state.candidates = list(range(len(model.answers)))
    st.session_state.history = []
    st.session_state.active_guess = None
    st.session_state.feedback = ""


st.title("Wordle Stats Solver")
st.caption("Entropy-based Wordle analysis and guess recommendations")

if not ANSWERS_PATH.exists():
    st.error(
        "possible_answers.txt is missing. Add the answer list to the repository "
        "before running the app."
    )
    st.stop()

try:
    model = build_model()
except Exception as exc:
    st.error(f"Could not build the Wordle model: {exc}")
    st.stop()

if "candidates" not in st.session_state:
    reset_game(model)

with st.sidebar:
    st.header("Solver settings")

    hard_mode = st.toggle(
        "Hard Mode",
        value=False,
        help=(
            "Hard Mode restricts recommendations to remaining candidate answers. "
            "Normal mode can use the full allowed-guesses list as information probes."
        ),
    )

    candidate_cutover = st.number_input(
        "Normal-mode candidate cutoff",
        min_value=1,
        max_value=200,
        value=25,
        step=1,
        disabled=hard_mode,
        help=(
            "In Normal mode, the solver switches from the full guess list to "
            "candidate-only guesses when this many answers remain."
        ),
    )

    first_guess = st.text_input(
        "Preferred first guess",
        value="tarse",
        max_chars=5,
    ).strip().lower()

    if st.button("New game", use_container_width=True):
        reset_game(model)
        st.rerun()

strategy = "candidates" if hard_mode else "adaptive"

ranked = model.rank_guesses_fast(
    st.session_state.candidates,
    strategy=strategy,
    candidate_cutover=int(candidate_cutover),
    top_k=10,
)

remaining = len(st.session_state.candidates)

metric1, metric2 = st.columns(2)
metric1.metric("Remaining answers", remaining)
metric2.metric("Guesses played", len(st.session_state.history))

if remaining == 0:
    st.error("No candidates remain. Check the feedback from your previous guesses.")
elif remaining == 1:
    answer = model.answers[st.session_state.candidates[0]]
    st.success(f"Only remaining answer: **{answer.upper()}**")

st.subheader("Next guess")

default_suggestion = ranked[0][0] if ranked else ""

if not st.session_state.history and first_guess:
    recommended = first_guess
else:
    recommended = default_suggestion

guess = st.text_input(
    "Guess",
    value=st.session_state.active_guess or recommended,
    max_chars=5,
    key="guess_input",
).strip().lower()

if guess and guess not in model.guess_index:
    st.warning("That word is not in the allowed guess list.")

st.subheader("Enter Wordle feedback")
st.write("Use **0 = gray**, **1 = yellow**, **2 = green**.")

feedback = st.text_input(
    "Feedback",
    value="",
    max_chars=5,
    placeholder="Example: 02001",
    key="feedback_input",
).strip()

if st.button("Apply feedback", type="primary", use_container_width=True):
    if guess not in model.guess_index:
        st.error("Enter a valid allowed guess.")
    elif len(feedback) != 5 or any(ch not in "012" for ch in feedback):
        st.error("Feedback must be exactly five digits using 0, 1, and 2.")
    else:
        fb_code = feedback_string_to_code(feedback)
        gi = model.guess_index[guess]

        st.session_state.candidates = model.filter_candidates_cached(
            st.session_state.candidates,
            gi,
            fb_code,
        )
        st.session_state.history.append((guess, feedback))
        st.session_state.active_guess = None

        # Clear widget values before rerunning.
        st.session_state.guess_input = ""
        st.session_state.feedback_input = ""
        st.rerun()

st.divider()
st.subheader("Top statistical suggestions")

if ranked:
    st.dataframe(
        {
            "Rank": list(range(1, len(ranked) + 1)),
            "Guess": [word.upper() for word, _ in ranked],
            "Expected information (bits)": [
                round(bits, 3) for _, bits in ranked
            ],
        },
        hide_index=True,
        use_container_width=True,
    )
else:
    st.write("No suggestions available.")

if st.session_state.history:
    st.subheader("Guess history")
    for turn, (word, fb) in enumerate(st.session_state.history, start=1):
        st.write(f"**{turn}. {word.upper()}** — {fb}")

if 1 < remaining <= 30:
    with st.expander(f"Show {remaining} remaining candidate answers"):
        st.write(
            ", ".join(
                model.answers[ai].upper()
                for ai in st.session_state.candidates
            )
        )

st.caption(
    f"Loaded {len(model.answers):,} possible answers and "
    f"{len(model.allowed_guesses):,} allowed guesses."
)
