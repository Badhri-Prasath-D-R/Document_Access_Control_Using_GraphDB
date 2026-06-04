import pandas as pd
from main import conn
from concurrent.futures import ThreadPoolExecutor
import time
import random

df = pd.read_csv("job_document_mapping.csv")

def createRelBtwJobCodeAndDocument(rowTuple):
    index, row = rowTuple
    jobCode = str(row["Job_Code"]).strip()
    documentID = str(row["DocumentID"]).strip()
    if not documentID or not jobCode:
        return
    if index%100 == 0:
        print(f"row ind reached is = {index}")
    print(f"{jobCode} -> {documentID}")
    query = """
            MATCH (j:Job {jobCode: $jobCode})
            MATCH (d:Document {documentID: $docId})
            MERGE (j)-[r:CAN_VIEW]->(d)
            """
    params = {
        "jobCode": jobCode,
        "docId": documentID
    }
    maxRetries = 5
    backoffDelay = 0.05
    for attempt in range(maxRetries):
        try:
            conn.run_query(query,parameters=params)
            return
        except Exception as e:
            if "ConcurrentModificationException" in str(e) and attempt < maxRetries - 1:
                sleep_time = (backoffDelay * (2 ** attempt)) + random.uniform(0, 0.05)
                time.sleep(sleep_time)
                continue
            else:
                print(f"failed to link row {index} : {e}")
                break
            
def runParallelLinking():
    startTime = time.time()
    print(f"creating threads")
    rows = list(df.iterrows())
    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(createRelBtwJobCodeAndDocument,rows))
    endTime = time.time()
    print("threads are done")
    print(f"time taken {endTime-startTime}")

runParallelLinking()