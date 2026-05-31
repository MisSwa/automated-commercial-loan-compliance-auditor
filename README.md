Background - 
A major commercial bank receives unstructured underwriting packages from borrowers. Before a loan can move to manual underwriting, a compliance check must verify that all required documents are present, financial covenants match the bank's strict credit policy, and no red flags exist. Doing this manually creates a massive backlog.

Your Goal - 
Build a Streamlit prototype powered by LangGraph that takes an uploaded "Loan Package" text file, extracts key metadata, cross-references it against a credit policy using single-stage retrieval, and flags any violations.


Important to keep in mind -
compliance and data privacy is paramount
inputs are unstructured data
output should be clean structured compliance report
human in look to review the report before approving or rejecting. You should never make a decision. 
Provide a confidence score as part of the output.
Graceful failure is essential in all failure patterns possible. 