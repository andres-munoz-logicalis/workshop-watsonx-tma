python -m venv .venv
source .venv/bin/activate

pip install ibm-watsonx-orchestrate


orchestrate env add -n <ambiente> -u <service-instance-url>
orchestrate env activate <ambiente>

-- orchestrate env add -n <ambiente> -u <service-instance-url> --type ibm_iam --activate

orchestrate agents list

orchestrate agents export -n <agent_name> --kind native --output <file_name.yaml> --agent-only

orchestrate models list

azure-cu01 > watsonx/meta-llama/llama-3-3-70b-instruct
azure-cu02 > groq/openai/gpt-oss-120b
asesor-azure > watsonx/meta-llama/llama-3-3-70b-instruct

orchestrate agents import -f <file_name.yaml>
