# GitHub Actions for STS (Sports Tournament Scheduling)

This repository includes several GitHub Actions workflows to automatically run and test the STS models.

## Available Workflows

### 1. Run All STS Models (`run-all-models.yml`)

**Triggers:**
- Push to main/master branch
- Pull requests to main/master
- Manual trigger via GitHub UI
- Weekly schedule (Sundays at 2 AM UTC)

**Features:**
- Runs all four STS models (CP, MIP, SAT, SMT)
- Tests across multiple Python versions (3.9, 3.10, 3.11, 3.12)
- Configurable parameters via manual trigger
- Uploads results as artifacts
- Generates execution summary

**Manual Trigger Options:**
- `team_numbers`: Comma-separated list (e.g., "2,4,6,8")
- `mode`: Running mode (generate, test, select)
- `timeout`: Timeout in seconds per model
- `verbose`: Enable verbose output
- `models`: Models to run ("all" or comma-separated: "CP,MIP,SAT,SMT")

### 2. Quick STS Test (`quick-test.yml`)

**Purpose:** Fast testing of individual models

**Features:**
- Manual trigger only
- Tests single model with limited team numbers
- 15-minute timeout for quick feedback
- Minimal dependency installation

**Manual Trigger Options:**
- `team_numbers`: Team numbers to test (default: "2,4")
- `model`: Single model to run (CP, MIP, SAT, SMT)
- `timeout`: Timeout in seconds (default: 120)

### 3. STS Integration Tests (`integration-tests.yml`)

**Triggers:**
- Push/PR that modifies source code, tests, or requirements
- Weekly comprehensive testing (Mondays at 6 AM UTC)
- Manual trigger with `[full-test]` in commit message

**Features:**
- Code linting and formatting checks
- Smoke tests on core models
- Comprehensive testing (triggered by schedule or `[full-test]`)
- Solution validation
- Detailed test reporting

## How to Use

### Running Tests Manually

1. **Quick Test:** Go to Actions → "Quick STS Test" → "Run workflow"
   - Choose a single model and small team numbers for fast feedback

2. **Full Test:** Go to Actions → "Run All STS Models" → "Run workflow"
   - Configure all parameters as needed
   - Results will be uploaded as artifacts

3. **Comprehensive Test:** Include `[full-test]` in your commit message
   - Triggers the most thorough testing including all models and validation

### Viewing Results

1. **GitHub Actions Tab:** Check the workflow run status and logs
2. **Artifacts:** Download result files from completed workflow runs
3. **Summary:** Each workflow generates a summary report visible in the Actions tab

### Interpreting Results

- ✅ **Success:** New result files were generated in the `res/` directory
- ⚠️ **Warning:** Workflow completed but no new results detected
- ❌ **Error:** Workflow failed - check logs for details

## File Structure After Runs

After successful runs, you'll find:
```
res/
├── CP/          # Constraint Programming results
├── MIP/         # Mixed Integer Programming results  
├── SAT/         # Boolean Satisfiability results
└── SMT/         # Satisfiability Modulo Theories results
```

## Dependencies

The workflows automatically install:
- Python dependencies from `requirements.txt`
- MiniZinc (for CP model)
- System build tools

## Troubleshooting

### Common Issues

1. **Timeout Errors:** Increase timeout values in manual triggers
2. **Missing Dependencies:** Check if `requirements.txt` is complete
3. **Model-Specific Failures:** Use Quick Test to isolate issues
4. **Permission Errors:** Ensure repository has Actions enabled

### Debugging

1. Enable verbose mode in manual triggers
2. Check individual model logs in workflow details
3. Download and examine result artifacts
4. Use Quick Test for isolated debugging

## Configuration

### Modifying Workflows

Edit the `.github/workflows/*.yml` files to:
- Change default parameters
- Modify trigger conditions  
- Add new Python versions
- Adjust timeout values

### Environment Variables

The workflows set:
- `PYTHONPATH`: Points to the workspace root
- `PATH`: Includes MiniZinc installation (for CP model)

## Performance Notes

- **Smoke Tests:** ~2-5 minutes per model
- **Quick Tests:** ~5-15 minutes total
- **Full Tests:** ~30-60 minutes depending on configuration
- **Comprehensive Tests:** ~60+ minutes with all models and validations

## Support

For issues with the GitHub Actions:
1. Check the workflow logs in the Actions tab
2. Verify the STS models work locally first
3. Ensure all required files are committed to the repository
