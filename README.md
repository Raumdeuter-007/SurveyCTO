# surveycto-converter

Pipeline to convert Word document surveys into SurveyCTO-compatible Excel sheets.

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Pandoc](https://pandoc.org/installing.html) — install via `winget install JohnMacFarlane.Pandoc`, then restart terminal

## Setup

```bash
uv sync
uv pip install -e .
```

## Running Tests

```bash
uv run pytest
```

## Debugging the Splitter

1. Create a `.env` file at the project root:

```
DEBUG_PATH="D:\\path\\to\\your\\document.docx"
```

> Note: escape backslashes with `\\` and apostrophes with `\'`
> Note: You need to use the DELIMITER in file in order for this to work properly.

2. Run:

```bash
uv run --env-file .env python tests/debug_splitter.py
```

Output will be printed to stdout and logged to `app.log`.

## Project Structure

```
surveycto-converter/
├── src/
│   ├── pipeline/
│   │   ├── splitter.py       # Stage 1: docx → modules
│   │   ├── parser.py         # Stage 2: module → LLM → structured questions
│   │   └── compiler.py       # Stage 3: structured questions → xlsx
│   ├── models/
│   │   └── survey.py
│   ├── config/
│   │   └── settings.py
│   └── utils/
│       └── logger.py
├── prompts/
│   └── parse_module.txt
├── tests/
│   ├── test_splitter.py
│   └── debug_splitter.py
├── pyproject.toml
└── .env
```
