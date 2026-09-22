from collections import Counter, defaultdict
from math import log2
from typing import List, Dict, Tuple, Optional
import random
import os
import csv
from datetime import datetime

try:
    from tqdm import tqdm
except Exception:
    def tqdm(x, **kwargs):
        return x


ALL_GREEN = 242  # 22222 packed as base-3


def feedback_code(guess: str, answer: str) -> int:
    """Return exact Wordle feedback packed as a base-3 integer.

    0 = gray, 1 = yellow, 2 = green.
    Duplicate letters are handled with the same two-pass approach as Wordle.
    """
    greens = [False] * 5
    ans_count = Counter(answer)

    for i, (g, a) in enumerate(zip(guess, answer)):
        if g == a:
            greens[i] = True
            ans_count[g] -= 1

    code = 0
    pow3 = 1
    for i, g in enumerate(guess):
        if greens[i]:
            trit = 2
        elif ans_count[g] > 0:
            trit = 1
            ans_count[g] -= 1
        else:
            trit = 0

        code += trit * pow3
        pow3 *= 3

    return code


def feedback_string_to_code(feedback: str) -> int:
    if len(feedback) != 5 or any(ch not in "012" for ch in feedback):
        raise ValueError("Feedback must contain exactly five digits using 0, 1, and 2.")

    code = 0
    pow3 = 1
    for ch in feedback:
        code += int(ch) * pow3
        pow3 *= 3
    return code


def feedback_code_to_string(code: int) -> str:
    digits = []
    for _ in range(5):
        digits.append(str(code % 3))
        code //= 3
    return "".join(digits)


def load_words(
    answers_path: str = "possible_answers.txt",
    guesses_path: Optional[str] = "allowed_guesses.txt",
) -> Tuple[List[str], List[str]]:
    with open(answers_path, "r", encoding="utf-8") as f:
        answers = [w.strip().lower() for w in f if w.strip()]
    answers = [w for w in answers if len(w) == 5 and w.isalpha()]

    if guesses_path:
        try:
            with open(guesses_path, "r", encoding="utf-8") as f:
                guesses = [w.strip().lower() for w in f if w.strip()]
            guesses = [w for w in guesses if len(w) == 5 and w.isalpha()]
        except FileNotFoundError:
            guesses = answers[:]
    else:
        guesses = answers[:]

    # Candidate answers should always be playable guesses.
    seen = set(guesses)
    for answer in answers:
        if answer not in seen:
            guesses.append(answer)
            seen.add(answer)

    return answers, guesses


class GameLogger:
    """Append completed Wordle results to a CSV file."""

    def __init__(self, path: str = "wordle_history.csv"):
        self.path = path
        self._ensure_header()

    def _ensure_header(self):
        need_header = not os.path.exists(self.path) or os.path.getsize(self.path) == 0
        if need_header:
            with open(self.path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "mode", "answer", "guesses_count", "guesses"])

    def log(self, mode: str, answer: str, guesses: list[str]):
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(timespec="seconds"),
                mode,
                answer,
                len(guesses),
                " | ".join(guesses),
            ])


class WordleModel:
    def __init__(
        self,
        answers: List[str],
        allowed_guesses: List[str],
        logger: GameLogger | None = None,
    ):
        self.answers = answers
        self.allowed_guesses = allowed_guesses
        self.logger = logger

        self.answer_index: Dict[str, int] = {w: i for i, w in enumerate(self.answers)}
        self.guess_index: Dict[str, int] = {w: i for i, w in enumerate(self.allowed_guesses)}

        G, A = len(self.allowed_guesses), len(self.answers)

        # A feedback code is always 0..242, so one byte per guess/answer pair is enough.
        # This keeps the full 14k x 2k cache practical for a web deployment.
        self.pattern_table = [bytearray(A) for _ in range(G)]

        for gi, guess in enumerate(
            tqdm(self.allowed_guesses, desc="Building pattern table", unit="guess")
        ):
            row = self.pattern_table[gi]
            for ai, answer in enumerate(self.answers):
                row[ai] = feedback_code(guess, answer)

    def fb_cached(self, guess_idx: int, answer_idx: int) -> int:
        return self.pattern_table[guess_idx][answer_idx]

    def filter_candidates_cached(
        self,
        candidate_idxs: List[int],
        guess_idx: int,
        fb_code: int,
    ) -> List[int]:
        pt_row = self.pattern_table[guess_idx]
        return [ai for ai in candidate_idxs if pt_row[ai] == fb_code]

    def expected_information_cached(
        self,
        guess_idx: int,
        candidate_idxs: List[int],
    ) -> float:
        if not candidate_idxs:
            return 0.0

        pt_row = self.pattern_table[guess_idx]
        buckets: Dict[int, int] = defaultdict(int)

        for ai in candidate_idxs:
            buckets[pt_row[ai]] += 1

        total = len(candidate_idxs)
        exp_bits = 0.0

        for count in buckets.values():
            p = count / total
            exp_bits += -p * log2(p)

        return exp_bits

    def is_hard_mode_legal(
        self,
        word: str,
        history: List[Tuple[str, str]],
    ) -> bool:
        """Return whether a word obeys all revealed Wordle Hard Mode hints."""
        greens: Dict[int, str] = {}
        yellow_blocked: Dict[int, set[str]] = defaultdict(set)
        minimum_counts: Dict[str, int] = defaultdict(int)

        for guess, feedback in history:
            turn_counts: Dict[str, int] = defaultdict(int)

            for i, (letter, result) in enumerate(zip(guess, feedback)):
                if result == "2":
                    greens[i] = letter
                    turn_counts[letter] += 1
                elif result == "1":
                    yellow_blocked[i].add(letter)
                    turn_counts[letter] += 1

            for letter, count in turn_counts.items():
                minimum_counts[letter] = max(minimum_counts[letter], count)

        if any(word[pos] != letter for pos, letter in greens.items()):
            return False

        if any(word[pos] in blocked for pos, blocked in yellow_blocked.items()):
            return False

        counts = Counter(word)
        if any(counts[letter] < needed for letter, needed in minimum_counts.items()):
            return False

        return True

    def hard_mode_guess_indices(
        self,
        history: List[Tuple[str, str]],
    ) -> List[int]:
        """Return allowed-list guesses that obey every revealed Hard Mode hint."""
        return [
            gi
            for gi, word in enumerate(self.allowed_guesses)
            if self.is_hard_mode_legal(word, history)
        ]

    def guess_metrics(
        self,
        guess_word: str,
        candidate_idxs: List[int],
        custom_answers: Optional[List[str]] = None,
    ) -> Dict[str, float | int]:
        """Return entropy plus expected/worst-case remaining candidates."""
        custom_answers = custom_answers or []
        buckets: Dict[int, int] = defaultdict(int)
        gi = self.guess_index.get(guess_word)

        if gi is not None:
            row = self.pattern_table[gi]
            for ai in candidate_idxs:
                buckets[row[ai]] += 1
        else:
            for ai in candidate_idxs:
                buckets[feedback_code(guess_word, self.answers[ai])] += 1

        for answer in custom_answers:
            buckets[feedback_code(guess_word, answer)] += 1

        total = len(candidate_idxs) + len(custom_answers)
        if total == 0:
            return {
                "entropy": 0.0,
                "expected_remaining": 0.0,
                "worst_case": 0,
                "partitions": 0,
            }

        entropy = 0.0
        expected_remaining = 0.0
        for count in buckets.values():
            p = count / total
            entropy += -p * log2(p)
            expected_remaining += p * count

        return {
            "entropy": entropy,
            "expected_remaining": expected_remaining,
            "worst_case": max(buckets.values()),
            "partitions": len(buckets),
        }

    def rank_guesses_detailed(
        self,
        candidate_idxs: List[int],
        strategy: str = "all",
        top_k: int = 10,
        history: Optional[List[Tuple[str, str]]] = None,
        custom_answers: Optional[List[str]] = None,
    ) -> List[Dict[str, object]]:
        """Rank guesses and return richer metrics for the web UI."""
        if strategy not in {"all", "candidates", "hard"}:
            raise ValueError("strategy must be 'all', 'candidates', or 'hard'")

        history = history or []
        custom_answers = custom_answers or []
        candidate_words = {self.answers[ai] for ai in candidate_idxs}
        candidate_words.update(custom_answers)

        if strategy == "candidates":
            guess_words = list(candidate_words)
        elif strategy == "hard":
            guess_words = [
                word
                for word in self.allowed_guesses
                if self.is_hard_mode_legal(word, history)
            ]
            for word in custom_answers:
                if (
                    word not in self.guess_index
                    and self.is_hard_mode_legal(word, history)
                ):
                    guess_words.append(word)
        else:
            guess_words = list(self.allowed_guesses)
            for word in custom_answers:
                if word not in self.guess_index:
                    guess_words.append(word)

        scored: List[Dict[str, object]] = []
        iterable = (
            tqdm(guess_words, desc="Scoring guesses", unit="guess", leave=False)
            if len(guess_words) > 200
            else guess_words
        )

        for word in iterable:
            metrics = self.guess_metrics(
                word,
                candidate_idxs,
                custom_answers,
            )
            scored.append({
                "word": word,
                "entropy": metrics["entropy"],
                "expected_remaining": metrics["expected_remaining"],
                "worst_case": metrics["worst_case"],
                "partitions": metrics["partitions"],
                "is_candidate": word in candidate_words,
            })

        scored.sort(
            key=lambda item: (
                item["entropy"],
                item["is_candidate"],
                -item["expected_remaining"],
            ),
            reverse=True,
        )
        return scored[:top_k]

    def rank_guesses_fast(
        self,
        candidate_idxs: List[int],
        strategy: str = "adaptive",
        candidate_cutover: int = 25,
        top_k: int = 15,
        history: Optional[List[Tuple[str, str]]] = None,
    ) -> List[Tuple[str, float]]:
        if strategy not in {"all", "candidates", "adaptive", "hard"}:
            raise ValueError(
                "strategy must be 'all', 'candidates', 'adaptive', or 'hard'"
            )

        if not candidate_idxs:
            return []

        use_candidates_only = (
            strategy == "candidates"
            or (strategy == "adaptive" and len(candidate_idxs) <= candidate_cutover)
        )

        if strategy == "hard":
            guess_space = self.hard_mode_guess_indices(history or [])
        elif use_candidates_only:
            guess_space: List[int] = []
            for ai in candidate_idxs:
                word = self.answers[ai]
                gi = self.guess_index.get(word)
                if gi is not None:
                    guess_space.append(gi)

            if not guess_space:
                guess_space = list(range(len(self.allowed_guesses)))
        else:
            guess_space = list(range(len(self.allowed_guesses)))

        scored: List[Tuple[int, float]] = []
        iterable = (
            tqdm(guess_space, desc="Scoring guesses", unit="guess", leave=False)
            if len(guess_space) > 200
            else guess_space
        )

        for gi in iterable:
            scored.append(
                (gi, self.expected_information_cached(gi, candidate_idxs))
            )

        candidate_words = {self.answers[ai] for ai in candidate_idxs}
        scored.sort(
            key=lambda item: (
                item[1],
                self.allowed_guesses[item[0]] in candidate_words,
            ),
            reverse=True,
        )

        return [
            (self.allowed_guesses[gi], bits)
            for gi, bits in scored[:top_k]
        ]

    def simulate(
        self,
        first_guess: Optional[str] = None,
        hard_mode: bool = False,
        sample: Optional[int] = None,
        rng_seed: int = 0,
    ) -> Dict[str, object]:
        if sample is not None and sample > 0:
            rng = random.Random(rng_seed)
            answer_indices = rng.sample(
                range(len(self.answers)),
                k=min(sample, len(self.answers)),
            )
        else:
            answer_indices = list(range(len(self.answers)))

        results: List[int] = []
        worst_case_paths: List[Tuple[str, int]] = []

        for ai in tqdm(answer_indices, desc="Simulating Wordles", unit="game"):
            hidden_ai = ai
            candidate_idxs = list(range(len(self.answers)))
            guesses_used = 0
            seq: list[str] = []
            history: List[Tuple[str, str]] = []

            if first_guess:
                if first_guess not in self.guess_index:
                    raise ValueError(
                        f"first_guess '{first_guess}' not in allowed guesses"
                    )
                gi = self.guess_index[first_guess]
            else:
                ranked = self.rank_guesses_fast(
                    candidate_idxs,
                    strategy=("hard" if hard_mode else "all"),
                    top_k=1,
                    history=history,
                )
                gi = self.guess_index[ranked[0][0]]

            while True:
                guesses_used += 1
                guess_word = self.allowed_guesses[gi]
                seq.append(guess_word)

                fb_code = self.fb_cached(gi, hidden_ai)
                fb_string = feedback_code_to_string(fb_code)
                history.append((guess_word, fb_string))

                if fb_code == ALL_GREEN:
                    break

                candidate_idxs = self.filter_candidates_cached(
                    candidate_idxs,
                    gi,
                    fb_code,
                )

                ranked = self.rank_guesses_fast(
                    candidate_idxs,
                    strategy=("hard" if hard_mode else "all"),
                    top_k=1,
                    history=history,
                )
                gi = self.guess_index[ranked[0][0]]

            if self.logger is not None:
                mode = f"simulate{'-hard' if hard_mode else ''}"
                self.logger.log(
                    mode=mode,
                    answer=self.answers[hidden_ai],
                    guesses=seq,
                )

            results.append(guesses_used)
            worst_case_paths.append((self.answers[hidden_ai], guesses_used))

        avg = sum(results) / len(results)
        hist: Dict[int, int] = defaultdict(int)

        for result in results:
            hist[result] += 1

        worst_answer, worst_guesses = max(
            worst_case_paths,
            key=lambda x: x[1],
        )

        return {
            "count": len(answer_indices),
            "average_guesses": avg,
            "histogram": dict(sorted(hist.items())),
            "worst_case": {
                "answer": worst_answer,
                "guesses": worst_guesses,
            },
        }


def main():
    answers, guesses = load_words()
    logger = GameLogger("wordle_history.csv")
    model = WordleModel(answers, guesses, logger=logger)

    print(
        f"Model ready: {len(answers)} answers and "
        f"{len(guesses)} allowed guesses."
    )
    print("Run 'streamlit run app.py' to use the web interface.")


if __name__ == "__main__":
    main()
