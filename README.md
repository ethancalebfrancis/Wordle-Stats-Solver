# Wordle Stats Solver

A statistical Wordle assistant written in Python. The solver models Wordle feedback exactly (including duplicate letters), filters the remaining answer set after each guess, and ranks future guesses using expected information (Shannon entropy).

The project now includes a Streamlit web interface so the solver can be used from a browser on desktop or mobile.

## Features

- Exact duplicate-safe Wordle scoring
- Base-3 encoding for the 243 possible feedback patterns
- Precomputed guess × answer feedback table for fast repeated scoring
- Entropy-based guess ranking
- Normal Mode ranks the full allowed-guess vocabulary, including information-gathering probe words
- Wordle-style Hard Mode keeps revealed green/yellow hints while still allowing legal probe words
- Clickable gray/yellow/green feedback tiles in the web interface
- Responsive mobile-friendly Streamlit layout
- Memory-efficient one-byte feedback cache for web deployment
- Interactive multi-game solver
- Simulation support in the Python engine
- Optional CSV game-history logging in the CLI engine
- Streamlit web interface

## Project structure

```text
Wordle-Stats-Solver/
├── app.py
├── wordle_solver.py
├── possible_answers.txt
├── allowed_guesses.txt
├── requirements.txt
├── .gitignore
└── README.md
```

The two word-list files are required at runtime. `possible_answers.txt` contains candidate solutions and `allowed_guesses.txt` contains the larger set of legal guesses.

## Run the web app locally

Create and activate a virtual environment, then install the dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows, activate with:

```powershell
.venv\Scripts\activate
```

Start Streamlit:

```bash
streamlit run app.py
```

Streamlit will print a local URL, normally `http://localhost:8501`.

## Solver modes

### Normal Mode

The solver scores every word in `allowed_guesses.txt`, so it can recommend information-gathering guesses that are not currently possible answers.

### Hard Mode

Hard Mode keeps revealed hints in future guesses: green letters stay fixed, yellow letters must move from their known-wrong positions, and revealed duplicate-letter minimums are retained. This is intentionally different from restricting guesses to only the remaining possible answers.

## Feedback format

Feedback is entered as five digits:

- `0` = gray
- `1` = yellow
- `2` = green

For example:

```text
02001
```

## How ranking works

For a possible guess, the solver determines which feedback pattern each remaining answer would produce. Those answers are grouped into feedback buckets. It then calculates the entropy of that distribution:

```text
H = -Σ p(x) log₂ p(x)
```

A higher value means the guess is expected to reveal more information about the hidden answer.

## Development

This repository supersedes the earlier project-only version of Wordle Stats Solver. Future development will focus on the web interface, performance, statistics/history, mobile usability, and solver strategy improvements.
