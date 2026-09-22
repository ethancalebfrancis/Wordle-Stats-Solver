from pathlib import Path
import html

import streamlit as st

from wordle_solver import WordleModel, feedback_string_to_code, load_words


BASE_DIR = Path(__file__).resolve().parent
ANSWERS_PATH = BASE_DIR / "possible_answers.txt"
GUESSES_PATH = BASE_DIR / "allowed_guesses.txt"

FEEDBACK_LABELS = {
    0: "⬛",
    1: "🟨",
    2: "🟩",
}

TILE_COLORS = {
    "0": "#787c7e",
    "1": "#c9b458",
    "2": "#6aaa64",
}


st.set_page_config(
    page_title="Wordle Stats Solver",
    page_icon="🟩",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .block-container {
        max-width: 760px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    .wordle-row {
        display: flex;
        gap: 0.35rem;
        margin: 0.35rem 0 0.75rem 0;
        flex-wrap: nowrap;
    }

    .wordle-tile {
        width: 3.1rem;
        height: 3.1rem;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 800;
        font-size: 1.45rem;
        border-radius: 0.2rem;
        text-transform: uppercase;
    }

    @media (max-width: 600px) {
        .block-container {
            padding-left: 0.8rem;
            padding-right: 0.8rem;
            padding-top: 0.75rem;
        }

        .wordle-tile {
            width: 2.65rem;
            height: 2.65rem;
            font-size: 1.2rem;
        }

        h1 {
            font-size: 1.8rem !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner="Building statistical model...")
def build_model() -> WordleModel:
    answers, guesses = load_words(str(ANSWERS_PATH), str(GUESSES_PATH))
    return WordleModel(answers, guesses, logger=None)


def reset_feedback():
    st.session_state.feedback_tiles = [0, 0, 0, 0, 0]


def reset_game(model: WordleModel):
    st.session_state.candidates = list(range(len(model.answers)))
    st.session_state.history = []
    st.session_state.solved = False
    st.session_state.game_id = st.session_state.get("game_id", 0) + 1
    reset_feedback()


def render_feedback_row(word: str, feedback: str):
    tiles = []
    for letter, result in zip(word.upper(), feedback):
        color = TILE_COLORS[result]
        tiles.append(
            f'<div class="wordle-tile" style="background:{color}">'
            f"{html.escape(letter)}</div>"
        )

    st.markdown(
        '<div class="wordle-row">' + "".join(tiles) + "</div>",
        unsafe_allow_html=True,
    )


st.title("Wordle Stats Solver")
st.caption("Statistical Wordle solving with expected-information ranking")

if not ANSWERS_PATH.exists() or not GUESSES_PATH.exists():
    st.error("The repository word lists are missing.")
    st.stop()

try:
    model = build_model()
except Exception as exc:
    st.error(f"Could not build the Wordle model: {exc}")
    st.stop()

if "candidates" not in st.session_state:
    reset_game(model)

if "feedback_tiles" not in st.session_state:
    reset_feedback()

with st.sidebar:
    st.header("Settings")

    hard_mode = st.toggle(
        "Wordle Hard Mode",
        value=False,
        help=(
            "Keeps every revealed green and yellow hint in future guesses. "
            "Unlike candidate-only mode, legal information-gathering guesses can still appear."
        ),
    )

    first_guess = st.text_input(
        "Preferred first guess",
        value="tarse",
        max_chars=5,
    ).strip().lower()

    st.caption(
        "Normal Mode ranks the entire allowed-guess list. "
        "Hard Mode ranks only guesses that obey revealed hints."
    )

    if st.button("New game", use_container_width=True):
        reset_game(model)
        st.rerun()

strategy = "hard" if hard_mode else "all"

ranked = model.rank_guesses_fast(
    st.session_state.candidates,
    strategy=strategy,
    top_k=10,
    history=st.session_state.history,
)

remaining = len(st.session_state.candidates)

metric1, metric2 = st.columns(2)
metric1.metric("Remaining", f"{remaining:,}")
metric2.metric("Guesses", len(st.session_state.history))

if remaining == 0:
    st.error("No answers match the feedback so far. Check the last row you entered.")
elif remaining == 1 and not st.session_state.solved:
    answer = model.answers[st.session_state.candidates[0]]
    st.info(f"Only one candidate remains: **{answer.upper()}**")

st.subheader("Your next guess")

default_suggestion = ranked[0][0] if ranked else ""
if not st.session_state.history and first_guess in model.guess_index:
    recommended = first_guess
else:
    recommended = default_suggestion

if "guess_input" not in st.session_state:
    st.session_state.guess_input = recommended

guess_key = (
    f"guess_input_{st.session_state.game_id}_"
    f"{len(st.session_state.history)}"
)

guess = st.text_input(
    "Guess",
    value=recommended,
    max_chars=5,
    key=guess_key,
    placeholder="Enter a 5-letter word",
).strip().lower()

guess_valid = (
    len(guess) == 5
    and guess.isalpha()
    and guess in model.guess_index
)

hard_mode_legal = True
if hard_mode and guess_valid:
    legal_indices = model.hard_mode_guess_indices(st.session_state.history)
    legal_words = {
        model.allowed_guesses[gi]
        for gi in legal_indices
    }
    hard_mode_legal = guess in legal_words

if guess and not guess_valid:
    st.warning("Enter a five-letter word from the allowed guess list.")
elif guess_valid and hard_mode and not hard_mode_legal:
    st.warning(
        "That guess does not reuse all revealed hints, so it is not legal "
        "in Hard Mode."
    )

st.write("Tap each tile to cycle **gray → yellow → green**.")

tile_columns = st.columns(5)
for i, col in enumerate(tile_columns):
    letter = guess[i].upper() if len(guess) == 5 else "?"
    state = st.session_state.feedback_tiles[i]

    with col:
        if st.button(
            f"{FEEDBACK_LABELS[state]} {letter}",
            key=f"feedback_tile_{i}",
            use_container_width=True,
        ):
            st.session_state.feedback_tiles[i] = (state + 1) % 3
            st.rerun()

feedback = "".join(str(value) for value in st.session_state.feedback_tiles)

if len(guess) == 5:
    render_feedback_row(guess, feedback)

apply_col, new_col = st.columns([2, 1])

with apply_col:
    apply_feedback = st.button(
        "Apply feedback",
        type="primary",
        use_container_width=True,
        disabled=(
            not guess_valid
            or not hard_mode_legal
            or st.session_state.solved
        ),
    )

with new_col:
    if st.button("Reset", use_container_width=True):
        reset_game(model)
        st.rerun()

if apply_feedback:
    fb_code = feedback_string_to_code(feedback)
    gi = model.guess_index[guess]

    st.session_state.history.append((guess, feedback))

    if feedback == "22222":
        st.session_state.solved = True
    else:
        st.session_state.candidates = model.filter_candidates_cached(
            st.session_state.candidates,
            gi,
            fb_code,
        )

    reset_feedback()
    st.rerun()

if st.session_state.solved:
    solved_word = st.session_state.history[-1][0].upper()
    st.success(
        f"Solved with **{solved_word}** in "
        f"**{len(st.session_state.history)} guesses**."
    )

st.divider()
st.subheader("Top suggestions")

if ranked and not st.session_state.solved:
    for index, (word, bits) in enumerate(ranked[:5], start=1):
        cols = st.columns([1, 3, 2])
        cols[0].markdown(f"**#{index}**")
        cols[1].markdown(f"**{word.upper()}**")
        cols[2].markdown(f"{bits:.3f} bits")

    with st.expander("Show top 10"):
        st.dataframe(
            {
                "Rank": list(range(1, len(ranked) + 1)),
                "Guess": [word.upper() for word, _ in ranked],
                "Expected information": [
                    round(bits, 3) for _, bits in ranked
                ],
            },
            hide_index=True,
            use_container_width=True,
        )
elif not st.session_state.solved:
    st.write("No suggestions are available.")

if st.session_state.history:
    st.subheader("Game board")
    for word, fb in st.session_state.history:
        render_feedback_row(word, fb)

if 1 < remaining <= 30 and not st.session_state.solved:
    with st.expander(f"Show {remaining} remaining answers"):
        st.write(
            ", ".join(
                model.answers[ai].upper()
                for ai in st.session_state.candidates
            )
        )

st.caption(
    f"{len(model.answers):,} possible answers • "
    f"{len(model.allowed_guesses):,} allowed guesses • "
    f"{'Hard' if hard_mode else 'Normal'} Mode"
)
