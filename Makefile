.PHONY: test demo seal archive check lint clean

PY = python
TEST_DIR = tests

test:
$(PY) -m py_compile supela/core/normative_eaas.py supela/core/k3_catalog.py
$(PY) -m pytest $(TEST_DIR) -v

demo:
$(PY) demo_eaas_lifecycle.py

seal:
$(PY) supela/tools/supela_cli.py seal $(MODULE) --git-commit

archive:
$(PY) tools/archive_supela_db.py

check:
$(PY) tools/check_supela.py

lint:
$(PY) -m py_compile supela/core/normative_eaas.py supela/core/k3_catalog.py supela/tools/supela_cli.py tools/check_supela.py tools/archive_supela_db.py

clean:
-rm -rf __pycache__ supela/__pycache__ supela/core/__pycache__ tests/__pycache__ .pytest_cache archives 2>nul || true
-del /Q /S *.pyc 2>nul || true
