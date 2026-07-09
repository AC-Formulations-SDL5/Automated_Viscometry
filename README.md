# Automated Viscometry

This repository runs the automated viscometry platform (CNC + viscometer + ESP32 wash station) with a Flask web interface.

## Main Run Path

1. Launch automation:

```bash
python run_viscometry.py
```

2. Open web interface:

```text
http://localhost:5001
```

## Required Docs And Paths

Directory tree chart (main required docs/config paths):

```text
Automated_Viscometry/
|-- README.md
|-- pyproject.toml
|-- requirements.txt
|-- requirements_web.txt
|-- setup_requirements.yaml
|-- run_viscometry.py
|-- config/
|   `-- locations.yaml
|-- src/
|   `-- viscometry/
|       |-- run/
|       |   |-- controller.py
|       |   `-- settings.py
|       |-- web/
|       |   `-- app.py
|       `-- hardware/
|           |-- cnc.py
|           |-- pump.py
|           `-- viscometer/
|               `-- client.py
|-- templates/
|   `-- index.html
|-- static/
|-- data/
|   `-- calibration/
`-- results/
    `-- README.md
```

Main required docs quick index:

| File/Path | Purpose | Access Path |
|---|---|---|
| README.md | Top-level usage and structure | ./README.md |
| pyproject.toml | Package metadata and core dependencies | ./pyproject.toml |
| requirements.txt | Shared/base dependencies | ./requirements.txt |
| requirements_web.txt | Web-specific pinned dependencies | ./requirements_web.txt |
| setup_requirements.yaml | Setup manifest for automation + web modes | ./setup_requirements.yaml |
| config/locations.yaml | Hardware locations and platform configuration | ./config/locations.yaml |
| results/README.md | Output/result folder notes | ./results/README.md |

## Environment Setup

Use the YAML manifest for mode-specific setup:

```text
setup_requirements.yaml
```

Or standard install:

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```
