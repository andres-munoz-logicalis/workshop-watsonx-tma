# Build and push docker image

## Preparar enviroment
```bash
cp example.txt .env
```
- Reemplazar los valores en `.env`

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
#docker build --platform="linux/amd64" -t us.icr.io/workshop-registry/api-decision-tree:latest .
```
Push
```bash
docker push us.icr.io/<ibm-container-registry>/<aplication-name>:latest
#docker push us.icr.io/workshop-registry/api-decision-tree:latest
```
