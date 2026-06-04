import pandas as pd
import random

job_master = pd.read_excel('Access_Data_Sample.xlsx', sheet_name='Job Master')
docs = pd.read_csv('documents.csv')

doc_ids = docs['DocumentID'].tolist()
job_codes = job_master['Job_Code'].tolist()

mapping = []
for job_code in job_codes:
    assigned_docs = random.sample(doc_ids, k=random.randint(1, 10))
    for doc_id in assigned_docs:
        mapping.append({'Job_Code': job_code, 'DocumentID': doc_id})

mapping_df = pd.DataFrame(mapping)
mapping_df.to_csv('job_document_mapping.csv', index=False)