from pathlib import Path
import html

import streamlit as st

from wordle_solver import (
    WordleModel,
    feedback_code,
    feedback_string_to_code,
    load_words,
)


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
        max-width: 820px;
        padding-top: 1.25rem;
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

    .mode-note {
        opacity: 0.8;
        font-size: 0.9rem;
    }

    @media (max-width: 600px) {
        .block-container {
            padding-left: 0.8rem;
            padding-right: 0.8rem;
            padding-top: 0.7rem;
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


MODEL_CACHE_VERSION = "2026-09-22-v2"


@st.cache_resource(show_spinner="Building statistical model...")
def build_model(model_cache_version: str) -> WordleModel:
    """Build the solver model.

    model_cache_version is deliberately part of the cache key so changes to
    WordleModel can invalidate an older Streamlit resource instance.
    """
    answers, guesses = load_words(str(ANSWERS_PATH), str(GUESSES_PATH))
    return WordleModel(answers, guesses, logger=None)


@st.cache_data(show_spinner=False)
def get_ranked_guesses(
    _model: WordleModel,
    candidate_idxs: tuple[int, ...],
    strategy: str,
    history: tuple[tuple[str, str], ...],
    custom_candidates: tuple[str, ...],
    top_k: int = 10,
):
    return _model.rank_guesses_detailed(
        list(candidate_idxs),
        strategy=strategy,
        top_k=top_k,
        history=list(history),
        custom_answers=list(custom_candidates),
    )


def reset_feedback():
    st.session_state.feedback_tiles = [0, 0, 0, 0, 0]


def cycle_feedback(index: int):
    st.session_state.feedback_tiles[index] = (
        st.session_state.feedback_tiles[index] + 1
    ) % 3


def reset_game(model: WordleModel):
    if "custom_answers" not in st.session_state:
        st.session_state.custom_answers = []

    st.session_state.candidates = list(range(len(model.answers)))
    st.session_state.custom_candidates = list(st.session_state.custom_answers)
    st.session_state.history = []
    st.session_state.turn_stats = []
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


def custom_word_matches_history(word: str) -> bool:
    for prior_guess, prior_feedback in st.session_state.history:
        if feedback_code(prior_guess, word) != feedback_string_to_code(prior_feedback):
            return False
    return True


def add_custom_answer(model: WordleModel, word: str):
    word = word.strip().lower()

    if len(word) != 5 or not word.isalpha():
        st.session_state.custom_answer_message = (
            "error",
            "A possible answer must contain exactly five letters.",
        )
        return

    if word in model.answer_index:
        st.session_state.custom_answer_message = (
            "info",
            f"{word.upper()} is already in the built-in possible-answer list.",
        )
        return

    if word in st.session_state.custom_answers:
        st.session_state.custom_answer_message = (
            "info",
            f"{word.upper()} is already in your custom answer list.",
        )
        return

    st.session_state.custom_answers.append(word)

    if custom_word_matches_history(word):
        st.session_state.custom_candidates.append(word)
        message = (
            f"Added {word.upper()} to this session and to the current candidate pool."
        )
    else:
        message = (
            f"Added {word.upper()} to this session, but it does not match the "
            "feedback already entered in this game."
        )

    st.session_state.custom_answer_message = ("success", message)


def filter_base_candidates(
    model: WordleModel,
    candidate_idxs: list[int],
    guess: str,
    fb_code: int,
) -> list[int]:
    gi = model.guess_index.get(guess)
    if gi is not None:
        return model.filter_candidates_cached(candidate_idxs, gi, fb_code)

    return [
        ai
        for ai in candidate_idxs
        if feedback_code(guess, model.answers[ai]) == fb_code
    ]


st.title("Wordle Stats Solver")
st.caption("Statistical Wordle solving with expected-information ranking")

if not ANSWERS_PATH.exists() or not GUESSES_PATH.exists():
    st.error("The repository word lists are missing.")
    st.stop()

try:
    model = build_model(MODEL_CACHE_VERSION)

    # Streamlit can preserve a cached resource across code updates in imported
    # modules. If the cached object predates a new solver method, rebuild it.
    if not hasattr(model, "rank_guesses_detailed"):
        build_model.clear()
        model = build_model(MODEL_CACHE_VERSION)
except Exception as exc:
    st.error(f"Could not build the Wordle model: {exc}")
    st.stop()

if "custom_answers" not in st.session_state:
    st.session_state.custom_answers = []

if "candidates" not in st.session_state:
    reset_game(model)

if "feedback_tiles" not in st.session_state:
    reset_feedback()

with st.sidebar:
    st.header("Settings")

    mode = st.selectbox(
        "Solver mode",
        ["Normal", "Hard", "Candidate Only"],
        index=0,
        help=(
            "Normal scores every allowed guess. Hard keeps revealed hints. "
            "Candidate Only only recommends words that can still be the answer."
        ),
    )

    first_guess = st.text_input(
        "Preferred first guess",
        value="tarse",
        max_chars=5,
    ).strip().lower()

    if mode == "Normal":
        st.caption("Best information-gathering guess from the full allowed list.")
    elif mode == "Hard":
        st.caption("Only guesses that reuse all revealed green/yellow hints.")
    else:
        st.caption("Only words that are still possible answers.")

    st.divider()
    st.subheader("Custom possible answers")
    st.caption(
        "Adds a missing word for your browser session. Public users cannot "
        "rewrite the GitHub repository."
    )

    custom_word = st.text_input(
        "Add a 5-letter answer",
        key="custom_answer_input",
        max_chars=5,
        placeholder="e.g. newwd",
    ).strip().lower()

    if st.button("Add possible answer", use_container_width=True):
        add_custom_answer(model, custom_word)
        st.rerun()

    message = st.session_state.pop("custom_answer_message", None)
    if message:
        kind, text = message
        if kind == "error":
            st.error(text)
        elif kind == "success":
            st.success(text)
        else:
            st.info(text)

    if st.session_state.custom_answers:
        st.write(
            "**Session additions:** "
            + ", ".join(w.upper() for w in st.session_state.custom_answers)
        )
        st.download_button(
            "Download additions",
            data="\n".join(st.session_state.custom_answers) + "\n",
            file_name="custom_possible_answers.txt",
            mime="text/plain",
            use_container_width=True,
        )

    st.divider()
    if st.button("New game", use_container_width=True):
        reset_game(model)
        st.rerun()

strategy = {
    "Normal": "all",
    "Hard": "hard",
    "Candidate Only": "candidates",
}[mode]

ranked = get_ranked_guesses(
    model,
    tuple(st.session_state.candidates),
    strategy,
    tuple(st.session_state.history),
    tuple(st.session_state.custom_candidates),
    10,
)

remaining = (
    len(st.session_state.candidates)
    + len(st.session_state.custom_candidates)
)

metric1, metric2, metric3 = st.columns(3)
metric1.metric("Remaining", f"{remaining:,}")
metric2.metric("Guesses", len(st.session_state.history))
metric3.metric("Mode", mode)

if remaining == 0:
    st.error("No answers match the feedback so far. Check the last row you entered.")
elif remaining == 1 and not st.session_state.solved:
    if st.session_state.custom_candidates:
        answer = st.session_state.custom_candidates[0]
    else:
        answer = model.answers[st.session_state.candidates[0]]
    st.info(f"Only one candidate remains: **{answer.upper()}**")

solver_tab, analysis_tab = st.tabs(["Solver", "Analysis"])

with solver_tab:
    st.subheader("Your next guess")

    default_suggestion = ranked[0]["word"] if ranked else ""
    if (
        not st.session_state.history
        and (
            first_guess in model.guess_index
            or first_guess in st.session_state.custom_answers
        )
    ):
        recommended = first_guess
    else:
        recommended = default_suggestion

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
        and (
            guess in model.guess_index
            or guess in st.session_state.custom_answers
        )
    )

    hard_mode_legal = True
    if mode == "Hard" and guess_valid:
        hard_mode_legal = model.is_hard_mode_legal(
            guess,
            st.session_state.history,
        )

    candidate_only_legal = True
    if mode == "Candidate Only" and guess_valid:
        candidate_words = {
            model.answers[ai]
            for ai in st.session_state.candidates
        }
        candidate_words.update(st.session_state.custom_candidates)
        candidate_only_legal = guess in candidate_words

    if guess and not guess_valid:
        st.warning(
            "That word is not in the allowed guess list or your custom possible answers."
        )
    elif guess_valid and mode == "Hard" and not hard_mode_legal:
        st.warning("That guess does not reuse all revealed hints.")
    elif guess_valid and mode == "Candidate Only" and not candidate_only_legal:
        st.warning("Candidate Only mode requires a remaining possible answer.")

    if ranked:
        top = ranked[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Top entropy", f"{top['entropy']:.3f} bits")
        c2.metric("Expected left", f"{top['expected_remaining']:.1f}")
        c3.metric("Worst case", int(top["worst_case"]))

    st.write("Tap each tile to cycle **gray → yellow → green**.")

    @st.fragment
    def feedback_controls(
        current_guess: str,
        valid_guess: bool,
        hard_legal: bool,
        candidate_legal: bool,
    ):
        tile_columns = st.columns(5)

        for i, col in enumerate(tile_columns):
            letter = (
                current_guess[i].upper()
                if len(current_guess) == 5
                else "?"
            )
            state = st.session_state.feedback_tiles[i]

            with col:
                st.button(
                    f"{FEEDBACK_LABELS[state]} {letter}",
                    key=(
                        f"feedback_tile_{st.session_state.game_id}_"
                        f"{len(st.session_state.history)}_{i}"
                    ),
                    use_container_width=True,
                    on_click=cycle_feedback,
                    args=(i,),
                )

        feedback = "".join(
            str(value)
            for value in st.session_state.feedback_tiles
        )

        if len(current_guess) == 5:
            render_feedback_row(current_guess, feedback)

        apply_col, clear_col = st.columns([2, 1])

        with apply_col:
            apply_feedback = st.button(
                "Apply feedback",
                type="primary",
                use_container_width=True,
                disabled=(
                    not valid_guess
                    or not hard_legal
                    or not candidate_legal
                    or st.session_state.solved
                ),
                key=(
                    f"apply_feedback_{st.session_state.game_id}_"
                    f"{len(st.session_state.history)}"
                ),
            )

        with clear_col:
            st.button(
                "Clear colors",
                use_container_width=True,
                on_click=reset_feedback,
                key=(
                    f"clear_feedback_{st.session_state.game_id}_"
                    f"{len(st.session_state.history)}"
                ),
            )

        if apply_feedback:
            before_count = (
                len(st.session_state.candidates)
                + len(st.session_state.custom_candidates)
            )

            fb_code = feedback_string_to_code(feedback)
            st.session_state.history.append((current_guess, feedback))

            if feedback == "22222":
                st.session_state.solved = True
                after_count = 1
            else:
                st.session_state.candidates = filter_base_candidates(
                    model,
                    st.session_state.candidates,
                    current_guess,
                    fb_code,
                )
                st.session_state.custom_candidates = [
                    answer
                    for answer in st.session_state.custom_candidates
                    if feedback_code(current_guess, answer) == fb_code
                ]
                after_count = (
                    len(st.session_state.candidates)
                    + len(st.session_state.custom_candidates)
                )

            st.session_state.turn_stats.append({
                "turn": len(st.session_state.history),
                "guess": current_guess.upper(),
                "before": before_count,
                "after": after_count,
                "removed": max(0, before_count - after_count),
            })

            reset_feedback()
            st.rerun()

    feedback_controls(
        guess,
        guess_valid,
        hard_mode_legal,
        candidate_only_legal,
    )

    reset_col, spacer_col = st.columns([1, 2])
    with reset_col:
        if st.button("Reset game", use_container_width=True):
            reset_game(model)
            st.rerun()

    if st.session_state.solved:
        solved_word = st.session_state.history[-1][0].upper()
        st.success(
            f"Solved with **{solved_word}** in "
            f"**{len(st.session_state.history)} guesses**."
        )

    if st.session_state.history:
        st.subheader("Game board")
        for word, fb in st.session_state.history:
            render_feedback_row(word, fb)

with analysis_tab:
    st.subheader("Recommendation analysis")

    if ranked and not st.session_state.solved:
        st.dataframe(
            {
                "Rank": list(range(1, len(ranked) + 1)),
                "Guess": [item["word"].upper() for item in ranked],
                "Entropy": [
                    round(float(item["entropy"]), 3)
                    for item in ranked
                ],
                "Expected left": [
                    round(float(item["expected_remaining"]), 1)
                    for item in ranked
                ],
                "Worst case": [
                    int(item["worst_case"])
                    for item in ranked
                ],
                "Partitions": [
                    int(item["partitions"])
                    for item in ranked
                ],
                "Possible answer": [
                    "Yes" if item["is_candidate"] else "No"
                    for item in ranked
                ],
            },
            hide_index=True,
            use_container_width=True,
        )
    elif not st.session_state.solved:
        st.write("No recommendations are available.")

    if st.session_state.turn_stats:
        st.subheader("Candidate reduction by turn")
        st.dataframe(
            st.session_state.turn_stats,
            hide_index=True,
            use_container_width=True,
        )

    if not st.session_state.solved and remaining <= 50:
        st.subheader("Remaining possible answers")
        remaining_words = [
            model.answers[ai].upper()
            for ai in st.session_state.candidates
        ]
        remaining_words.extend(
            word.upper()
            for word in st.session_state.custom_candidates
        )

        if remaining_words:
            st.write(", ".join(sorted(remaining_words)))
        else:
            st.write("None")

st.caption(
    f"{len(model.answers):,} built-in answers • "
    f"{len(model.allowed_guesses):,} allowed guesses • "
    f"{len(st.session_state.custom_answers)} session additions"
)
