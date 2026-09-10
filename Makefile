PYTHON ?= python3
RSCRIPT ?= Rscript

.PHONY: validate results figures reproduce astra astra-results astra-figures

validate:
	$(PYTHON) scripts/validate_release.py

results: validate
	$(RSCRIPT) analysis/reproduce.R
	$(RSCRIPT) analysis/supporting_variance.R

figures:
	$(RSCRIPT) analysis/figures.R

astra-results: validate
	$(RSCRIPT) analysis/astra_api.R

astra-figures:
	$(RSCRIPT) analysis/figures.R --astra-api

astra: astra-results
	$(RSCRIPT) analysis/figures.R --astra-api

reproduce: results figures astra
