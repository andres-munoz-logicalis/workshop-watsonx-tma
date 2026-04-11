ibmcloud login --sso
ibmcloud target -g workshop-rg
ibmcloud cr login
docker build --platform="linux/amd64" -t us.icr.io/elastic-workshop-registry/pythonapp:latest .
docker push us.icr.io/elastic-workshop-registry/pythonapp:latest
ibmcloud ce project select -n 
ibmcloud ce application get -n
ibmcloud ce application events -n
ibmcloud ce application logs -f -n
