# Shared Windows environment

All projects in this folder can use `.venv` (Python 3.14).

From PowerShell in `ai_course`, activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use the interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m jupyterlab
.\.venv\Scripts\python.exe -m pip install PACKAGE_NAME
```

In VS Code, select `.venv\Scripts\python.exe` as the Python interpreter
and notebook kernel. In JupyterLab, select `Python (ai_course)`.
Open `chess/chess.ipynb` and run its cells to start the game.
Pygame is supplied by `pygame-ce`, which imports as `pygame`.

To reinstall the shared dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

A1's supplied `environment.yml` describes a separate legacy Python 3.7
environment. This shared environment does not reproduce those legacy pins;
projects requiring a specific older Python version need a separate environment.
