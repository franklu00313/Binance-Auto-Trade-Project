import os
from dotenv import load_dotenv

# load env variable
load_dotenv(override=True)
gcp_project_id = os.getenv("GCP_PROJECT_ID")
gcp_repo_name = os.getenv("GCP_REPO_NAME")
gcp_github_version = os.getenv("GCP_GITHUB_VERSION")

def create_http_function(func_name, version, memory='256MB'):
    script = f'''gcloud functions deploy {func_name} --trigger-http \
        --region="asia-east1"\
        --entry-point="{func_name}"\
        --memory="{memory}"\
        --runtime="python39"\
        --timeout="50"\
        --env-vars-file .env.yaml\
        --service-account="{gcp_project_id}@appspot.gserviceaccount.com"\
        --source="https://source.developers.google.com/projects/{gcp_project_id}/repos/{gcp_repo_name}/revisions/{version}/paths/"\
    '''
    print("--------------------")
    print("gcloud script")
    print(f'gcloud config set project {gcp_project_id}')
    os.system(f'gcloud config set project {gcp_project_id}')
    print(script)
    os.system(script)

# Deploy all the function in main.py
if __name__ == "__main__":
    create_http_function('rebalance_weight', version=gcp_github_version)
    create_http_function('send_daily_report', version=gcp_github_version)