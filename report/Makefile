# Makefile for LaTeX report compilation

# Main document
MAIN = main
TEX_FILE = $(MAIN).tex
PDF_FILE = $(MAIN).pdf

# LaTeX compiler
LATEX = pdflatex
BIBTEX = bibtex

# Compilation flags
LATEX_FLAGS = -interaction=nonstopmode -halt-on-error

# Default target
all: $(PDF_FILE)

# Compile PDF (with bibliography support)
$(PDF_FILE): $(TEX_FILE)
	$(LATEX) $(LATEX_FLAGS) $(TEX_FILE)
	$(LATEX) $(LATEX_FLAGS) $(TEX_FILE)
	$(LATEX) $(LATEX_FLAGS) $(TEX_FILE)

# Quick compile (single pass)
quick: $(TEX_FILE)
	$(LATEX) $(LATEX_FLAGS) $(TEX_FILE)

# Clean auxiliary files
clean:
	rm -f *.aux *.log *.out *.toc *.bbl *.blg *.fls *.fdb_latexmk *.synctex.gz

# Clean everything including PDF
cleanall: clean
	rm -f $(PDF_FILE)

# View PDF (platform dependent)
view: $(PDF_FILE)
ifeq ($(OS),Windows_NT)
	start $(PDF_FILE)
else
	xdg-open $(PDF_FILE)
endif

# Force rebuild
rebuild: cleanall all

# Help
help:
	@echo "Available targets:"
	@echo "  all      - Compile the complete report (default)"
	@echo "  quick    - Single-pass compilation"
	@echo "  clean    - Remove auxiliary files"
	@echo "  cleanall - Remove all generated files"
	@echo "  view     - Open the PDF"
	@echo "  rebuild  - Clean and rebuild"
	@echo "  help     - Show this help"

.PHONY: all quick clean cleanall view rebuild help
