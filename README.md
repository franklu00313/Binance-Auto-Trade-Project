# Environment Setup
## Virtual Environment
```bash
conda create --name test python=3.9
conda activate test
conda install -n test ipykernel --update-deps --force-reinstall
conda install -c conda-forge ta-lib
pip install -r local_requirements.txt
```
## Complete .env / .env.yaml
+ Remember to fill in `your personal key & token` !

## Run preprocess.ipynb
+ Generate `./data/dataset.csv` for model training.
+ Generate `./result/lightgbm_model.pkl` for model prediction (later uploaded to Cloud Storage).
+ Generate `./result/lgbm_importance.png` for feature importance.

# Google Cloud Platform (GCP)

## Local cloud function Testing (test.ipynb)
```bash
functions-framework --target send_daily_report --debug
```
## Deploy Auto Trade Cloud System

1. Build a Project on Google Cloud Platform

2. Upload Weight(./result/lightgbm_model.pkl) to Cloud storage
    + bucket name = `model-weight`
    + file name = `lightgbm_model.pkl`

3. Deploy cloud function (using `deploy.py`)
    + install google cloud cli
    + change the version number in `.env` and run it
    + copy .env to .env.yaml (change `=` to `:`)
      + remember to turn number to string

4. Set up Cloud Scheduler


# VS Code Settings

## Add Type Hints (optional)
+ remember to uninstall "Python for VSCode" extension (deprecated)
  ```json
  // add in .vscode/settings.json
  {
    "python.analysis.inlayHints.functionReturnTypes": true,
    "python.analysis.inlayHints.variableTypes": false,
  }
  ```

## Check IP Address
+ Binance will block ip from US.
  ```bash
  curl ipinfo.io
  ```