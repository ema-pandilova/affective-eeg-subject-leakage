"""Execute the notebook in-process (no Jupyter kernel): deterministic, single process,
guaranteed venv310 deps. Captures stdout and inline figures, writes outputs back."""
import io, os, base64, contextlib, traceback, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nbformat
from nbformat.v4 import new_output
from pathlib import Path

here = Path(__file__).resolve().parent
os.chdir(here)                      # so ../../data and ../figures resolve as in Jupyter
path = here / "demo_leakage_collapse.ipynb"
nb = nbformat.read(str(path), as_version=4)
ns = {"__name__": "__main__"}
ok = True
for i, cell in enumerate(nb.cells):
    if cell.cell_type != "code":
        continue
    cell.outputs = []; cell.execution_count = i
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            exec(cell.source, ns)
    except Exception as e:
        tb = traceback.format_exc().splitlines()
        cell.outputs.append(new_output("error", ename=type(e).__name__, evalue=str(e), traceback=tb))
        print("CELL", i, "ERROR:", e); ok = False
        break
    txt = buf.getvalue()
    if txt:
        cell.outputs.append(new_output("stream", name="stdout", text=txt))
        print(txt, end="")
    for fn in plt.get_fignums():
        fig = plt.figure(fn); b = io.BytesIO()
        fig.savefig(b, format="png", dpi=110, bbox_inches="tight")
        cell.outputs.append(new_output("display_data",
            data={"image/png": base64.b64encode(b.getvalue()).decode(), "text/plain": "<Figure>"},
            metadata={}))
        plt.close(fig)
nbformat.write(nb, str(path))
print("=== notebook executed:", "OK" if ok else "FAILED", "===")
sys.exit(0 if ok else 1)
