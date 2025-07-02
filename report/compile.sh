#!/bin/bash

# Shell script to compile the CDMO report on Unix-like systems

echo "CDMO Report Compilation Script"
echo "=============================="

# Check if pdflatex is available
if ! command -v pdflatex &> /dev/null; then
    echo "ERROR: pdflatex not found in PATH"
    echo "Please install a LaTeX distribution (TeX Live) and ensure pdflatex is in your PATH"
    exit 1
fi

echo "Found pdflatex, proceeding with compilation..."
echo

# Function to run pdflatex with error checking
run_latex() {
    local pass=$1
    echo "[$pass/3] Compilation pass $pass..."
    if ! pdflatex -interaction=nonstopmode -halt-on-error main.tex > /dev/null; then
        echo "ERROR: Compilation pass $pass failed"
        echo "Check main.log for details"
        exit 1
    fi
}

# Three compilation passes
run_latex 1
run_latex 2
run_latex 3

echo
echo "=============================="
echo "Compilation completed successfully!"
echo "Generated: main.pdf"

# Check if PDF was created and show size
if [ -f main.pdf ]; then
    echo "PDF file size: $(du -h main.pdf | cut -f1)"
    echo
    
    # Ask if user wants to open the PDF
    read -p "Open the PDF now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if command -v xdg-open &> /dev/null; then
            xdg-open main.pdf
        elif command -v open &> /dev/null; then
            open main.pdf
        else
            echo "Please open main.pdf manually"
        fi
    fi
else
    echo "WARNING: main.pdf was not generated"
    echo "Check the compilation log for errors"
fi

echo
echo "To clean auxiliary files, run: make clean"
echo "To rebuild from scratch, run: make rebuild"
