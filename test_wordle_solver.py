import unittest

from wordle_solver import (
    ALL_GREEN,
    WordleModel,
    feedback_code,
    feedback_code_to_string,
    feedback_string_to_code,
)


class FeedbackTests(unittest.TestCase):
    def test_all_green(self):
        self.assertEqual(feedback_code("crane", "crane"), ALL_GREEN)
        self.assertEqual(feedback_string_to_code("22222"), ALL_GREEN)

    def test_round_trip_all_patterns(self):
        for code in range(243):
            feedback = feedback_code_to_string(code)
            self.assertEqual(feedback_string_to_code(feedback), code)

    def test_duplicate_letters_do_not_overcount_yellows(self):
        # The answer contains one 'e'. The second guessed 'e' must be gray.
        code = feedback_code("eerie", "cider")
        feedback = feedback_code_to_string(code)
        self.assertEqual(feedback.count("1") + feedback.count("2"), 3)


class HardModeTests(unittest.TestCase):
    def setUp(self):
        answers = ["cigar", "rebut", "sissy", "humph"]
        guesses = answers + ["cairn", "caper", "curry", "arise"]
        self.model = WordleModel(answers, guesses)

    def test_green_must_stay_fixed(self):
        history = [("cigar", "20000")]
        legal = {
            self.model.allowed_guesses[i]
            for i in self.model.hard_mode_guess_indices(history)
        }
        self.assertIn("cairn", legal)
        self.assertNotIn("arise", legal)

    def test_yellow_cannot_repeat_same_position(self):
        history = [("arise", "10000")]
        legal = {
            self.model.allowed_guesses[i]
            for i in self.model.hard_mode_guess_indices(history)
        }
        self.assertNotIn("arise", legal)


if __name__ == "__main__":
    unittest.main()
