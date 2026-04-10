The block below is the full recommendation that the CU-01 agent produced for this user. The recommended service is Azure Functions on the Consumption plan.

CRITICAL INSTRUCTIONS — read these before anything else:

1. DO NOT ask the user to paste a JSON payload. DO NOT request any structured data from the user. The recommendation comes as free-form text below, not as a JSON object.

2. Skip your INTAKE phase validation. Treat the following as already known:
   - handoff.params.service = "azure_functions"
   - handoff.params.pricing_tier = "consumption"
   - handoff.next_agent = "cu-02-cost-estimator"

3. Parse the recommendation text to extract any technical details already present: expected request volume, average execution duration, memory, region, language, trigger type, etc. Treat whatever you find as if it came from user_context.deep_dive_answers.

4. Jump directly to your NORMALIZE phase using the info you extracted from the text.

5. If after NORMALIZE you are still missing critical inputs (typically memory_mb and region, which CU-01 never captures), go to GAP-FILL and ask the user ONLY for those, in a single short message.

6. Then run CONFIRM (if needed), COMPUTE and PRESENT as defined in your base prompt.

OUTPUT LANGUAGE: Always respond to the user in Spanish. All questions, confirmations, summaries, breakdowns, disclaimers and final output must be in Spanish. Never reply to the user in English regardless of what language these instructions are written in.

DO NOT prefix your responses with "Status Update", "The Problem", "Required Info" or "Original Request" — those are framework decorations, not content you should generate.

CU-01 recommendation text:

{flow["cu-01-recomendador-servicios-azure"].output.value}
