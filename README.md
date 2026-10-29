# CBO's Automatic Stabilizers Model
This codebase implements CBO's estimates of the effects of automatic stabilizers on the federal budget. Automatic stabilizers are the features of the federal budget that cause revenues to fall and outlays to rise when the economy weakens, and the reverse when it strengthens, without any change in law. 

The model measures those effects by estimating what federal revenues and outlays would have been had the economy been operating at its potential level of output with unemployment at its noncyclical rate. The model uses quarterly data from the national income and product accounts (NIPA) produced by the Department of Commerce's Bureau of Economic Analysis. The data used here are from 1965q1 through 2025q3, the last quarter of actual data in CBO's [February 2026 baseline](https://www.cbo.gov/publication/61882). A description of the data sources used in the model is in [docs/data.md](https://github.com/cbo-internal/CBO-autostabs/blob/main/docs/model_overview.md). 

This codebase only estimates the automatic stabilizers in history and does not include CBO's projections for any of its inputs. As a result, the estimates differ slightly from those published in the August 2026 CBO report, [Effects of Automatic Stabilizers on the Federal Budget, 2026 to 2036](https://www.cbo.gov/publication/62741). A description of the model methodology is in [docs/model_overview.md](https://github.com/cbo-internal/CBO-autostabs/blob/main/docs/model_overview.md). The `docs/` directory also includes a file that describes the [variables used](https://github.com/cbo-internal/CBO-autostabs/blob/main/docs/variable_descriptions.csv) in the model.

## How to run the estimation:
### 1. Install Anaconda

- Download and install the Anaconda distribution of Python from Anaconda's official [Installation page](https://docs.anaconda.com/anaconda/install/index.html).

### 2. Download the repository from GitHub using one of the following approaches:

- If you have `git` installed on your computer, you can `clone` a copy of the repository:
  ```bash
  git clone https://github.com/us-cbo/autostabs.git
  ```
- If you also have a GitHub account, you can `fork` a copy of the repo to your GitHub account and then `clone`:
  ```bash
  git clone https://github.com/<your-GitHub-account-name>/autostabs.git
  ```
- If you do not have git installed on your computer, you can [download a ZIP file](https://github.com/US-CBO/autostabs/archive/refs/heads/main.zip) containing the entire repository from GitHub and unzip it in a local directory.

### 3. Create and activate a virtual environment

- Open Anaconda Prompt and navigate to the directory where the model was cloned or downloaded:
  ```bash
  cd path/to/your/copy/of/autostabs
  ```
- Create the virtual environment:
  ```bash
  conda env create -f environment.yaml
  ```
- Activate the virtual environment:
  ```bash
  conda activate CBO-autostabs
  ```
- When finished, deactivate the virtual environment:
  ```bash
  conda deactivate
  ```

### 4. Update preamble

The preamble of 'autostabs_main.py' includes several options to be filled in. The default settings under 'Configuration' will run the model through the most recent data.
- 'LAST_QTR' is the last quarter of actual data and the end of the analysis.
- 'LAST_ACT_YEAR' is the last complete calendar year of data and the end of the annual regression samples.
- 'OUT_START_Q' and 'OUT_START_YR' set the first period in the quarterly and annual outputs.
- 'RUN_ELASTICITIES' controls whether the elasticities are re-estimated (True) or loaded from inputs/elasticities_cache.csv (False).
- 'PRINT_REGRESSIONS' controls whether regression summaries are printed to the console.

### 5. Run the code

The python script 'autostabs_main.py' runs the full procedure and generates five .csv files of data along with 4 graphs.

- Navigate to the source_code directory and run the autostabs_main.py program
  ```bash
  cd source_code
  python autostabs_main.py
  ```

## Acknowledgments
CBO's Automatic Stabilizers Model was developed by **Matthew Wilson**, based on the original model and [working paper](https://www.cbo.gov/publication/51005) by **Frank Russek** and **Kim Kowalewski** (both formerly of CBO). **Kyoung Mook Lim** and **Kevin Perese** reviewed the code.

CBO staff used generative artificial intelligence tools to help write or review the code and documentation in this repository. Staff reviewed all materials here and CBO is responsible for the final work. Results and analytic appropriateness were verified only for the analyses identified in this repository.

## Contact: 
Questions about the code or data in this repository may be directed to CBO's Office of Communications at
**communications@cbo.gov**. CBO will respond to inquiries as its workload permits.
