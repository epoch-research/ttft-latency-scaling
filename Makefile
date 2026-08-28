PYTHON ?= python3
RSCRIPT ?= Rscript

.PHONY: validate results figures reproduce

validate:
	$(PYTHON) scripts/validate_release.py

results: validate
	$(RSCRIPT) analysis/reproduce.R
	$(RSCRIPT) analysis/supporting_variance.R

figures:
	$(RSCRIPT) analysis/figures.R

reproduce: results figures

