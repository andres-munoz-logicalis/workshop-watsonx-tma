# Test local
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main_cu02:app --reload --port 8081
```

# Build and push docker image
## En la terminal
```bash
ibmcloud login --sso
ibmcloud target -g <RG> #workshop-rg
ibmcloud cr login
```

## Build & Push
Build
```bash
docker build --platform="linux/amd64" -t us.icr.io/<ibm-container-registry>/<aplication-name>:latest .
#docker build --platform="linux/amd64" -t us.icr.io/workshop-registry/api-azure-pricing:latest .
```
Push
```bash
docker push us.icr.io/<ibm-container-registry>/<aplication-name>:latest
#docker push us.icr.io/workshop-registry/api-azure-pricing:latest
```
