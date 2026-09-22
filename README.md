# Wordle Stats Solver

A statistical Wordle assistant written in Python. The solver models Wordle feedback exactly (including duplicate letters), filters the remaining answer set after each guess, and ranks future guesses using expected information (Shannon entropy).

The project includes a Streamlit web interface so the solver can be used from a browser on desktop or mobile.

## Features

- Exact duplicate-safe Wordle scoring
- Base-3 encoding for the 243 possible feedback patterns
- Precomputed guess × answer feedback table for fast repeated scoring
- Entropy-based guess ranking
- Detailed recommendation metrics: expected remaining answers, worst-case split, and partition count
- Normal Mode ranks the full allowed-guess vocabulary, including information-gathering probe words
- Wordle-style Hard Mode keeps revealed green/yellow hints while still allowing legal probe words
- Clickable gray/yellow/green feedback tiles in the web interface
- Responsive mobile-friendly Streamlit layout
- Solver and Analysis tabs for gameplay and deeper statistics
- Session-level custom possible answers for newly introduced or missing words
- Candidate Only mode for solution-only recommendations
- Memory-efficient one-byte feedback cache for web deployment
- Interactive multi-game solver
- Simulation support in the Python engine
- Optional CSV game-history logging in the CLI engine
- Automated solver tests with GitHub Actions

## Project structure

```text
Wordle-Stats-Solver/
├── app.py
├── wordle_solver.py
├── possible_answers.txt
├── allowed_guesses.txt
├── requirements.txt
├── test_wordle_solver.py
├── .streamlit/
│   └── config.toml
├── .github/
│   └── workflows/
│       └── tests.yml
├── .gitignore
└── README.md
```

The two word-list files are required at runtime. `possible_answers.txt` contains candidate solutions and `allowed_guesses.txt` contains the larger set of legal guesses.

# Local setup and deployment

## Windows

### 1. Install prerequisites

Install:

- Python 3.11 or newer
- Git

Verify both are available in PowerShell:

```powershell
python --version
git --version
```

If `python` is not recognized, try:

```powershell
py --version
```

### 2. Clone the repository

```powershell
git clone https://github.com/ethancalebfrancis/Wordle-Stats-Solver.git
cd Wordle-Stats-Solver
```

### 3. Create a virtual environment

```powershell
python -m venv .venv
```

If your system uses the Python launcher instead:

```powershell
py -m venv .venv
```

### 4. Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script, run this once in the current PowerShell window:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate again:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 5. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 6. Run the app

```powershell
streamlit run app.py
```

Your browser should open automatically. If it does not, go to:

```text
http://localhost:8501
```

### 7. Stop the app

Return to PowerShell and press:

```text
Ctrl + C
```

---

## macOS

### 1. Install prerequisites

You need:

- Python 3.11 or newer
- Git

Git is often already available on macOS. Verify both in Terminal:

```bash
python3 --version
git --version
```

If Git is not installed, macOS may prompt you to install the Command Line Tools. You can also install them with:

```bash
xcode-select --install
```

### 2. Clone the repository

```bash
git clone https://github.com/ethancalebfrancis/Wordle-Stats-Solver.git
cd Wordle-Stats-Solver
```

### 3. Create a virtual environment

```bash
python3 -m venv .venv
```

### 4. Activate the virtual environment

```bash
source .venv/bin/activate
```

After activation, your Terminal prompt should usually show `(.venv)`.

### 5. Install dependencies

```bash
python3 -m pip install --upgrade pip
pip install -r requirements.txt
```

### 6. Run the app

```bash
streamlit run app.py
```

Your browser should open automatically. If it does not, go to:

```text
http://localhost:8501
```

### 7. Stop the app

Return to Terminal and press:

```text
Control + C
```

## Running it again later

You do not need to reinstall everything each time.

### Windows

```powershell
cd path\to\Wordle-Stats-Solver
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```

### macOS

```bash
cd /path/to/Wordle-Stats-Solver
source .venv/bin/activate
streamlit run app.py
```

# Deploy to Streamlit Community Cloud

Deploying to Streamlit Community Cloud gives the project a public web URL that can be opened from Windows, macOS, Android, iPhone, or any modern browser.

1. Make sure the latest version of this repository has been pushed to GitHub.
2. Go to Streamlit Community Cloud and sign in with GitHub.
3. Choose **Create app**.
4. Select the repository:
   `ethancalebfrancis/Wordle-Stats-Solver`
5. Select the `main` branch.
6. Set the main file path to:
   `app.py`
7. Deploy the app.

Streamlit will install the packages in `requirements.txt` and start the application automatically.

No API keys or secrets are currently required for this project.

# Custom possible answers

The sidebar includes **Add possible answer** for five-letter words that are missing from the built-in answer list.

Custom answers are intentionally stored only in the current browser session. This keeps a public Streamlit deployment from modifying the GitHub repository or changing the canonical word list for every user.

If a custom answer matches feedback already entered in the current game, it joins the current candidate pool immediately. Otherwise, it is saved for the session and will be available in the next game.

The app also provides a **Download additions** button so session additions can be reviewed and later committed to the repository if desired.

# Solver modes

## Normal Mode

The solver scores every word in `allowed_guesses.txt`, so it can recommend information-gathering guesses that are not currently possible answers.

## Hard Mode

Hard Mode keeps revealed hints in future guesses: green letters stay fixed, yellow letters must move from their known-wrong positions, and revealed duplicate-letter minimums are retained.

## Candidate Only

Candidate Only mode restricts recommendations to words that are still possible solutions. This is useful when you prefer to solve directly instead of playing an information-gathering probe word.

# Feedback

The web interface uses clickable Wordle-style feedback tiles:

- Gray = letter is not present
- Yellow = letter is present in another position
- Green = letter is in the correct position

Tap a tile repeatedly to cycle:

```text
Gray → Yellow → Green → Gray
```

Internally, the solver represents these states as:

- `0` = gray
- `1` = yellow
- `2` = green

# How ranking works

For a possible guess, the solver determines which feedback pattern each remaining answer would produce. Those answers are grouped into feedback buckets. It then calculates the entropy of that distribution:

```text
H = -Σ p(x) log₂ p(x)
```

A higher value means the guess is expected to reveal more information about the hidden answer.

# Tests

Run the solver regression tests locally with:

### Windows

```powershell
python -m unittest -v test_wordle_solver.py
```

### macOS

```bash
python3 -m unittest -v test_wordle_solver.py
```

The same tests also run automatically through GitHub Actions after pushes to `main` and on pull requests.

# Development

This repository supersedes the earlier project-only version of Wordle Stats Solver. Future development will focus on the web interface, performance, statistics/history, mobile usability, and solver strategy improvements.
