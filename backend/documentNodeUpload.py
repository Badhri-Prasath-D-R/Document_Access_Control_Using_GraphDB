import pandas as pd
from main import conn
from concurrent.futures import ThreadPoolExecutor
import time
import random

df = pd.read_csv("documents.csv")

def uploadSingleDocument(rowTuple):
    index, row = rowTuple
    documentID = str(row["DocumentID"]).strip()
    documentName = str(row["DocumentName"]).strip().replace("'","\\'")
    if not documentID or documentID == "nan":
        return
    if index % 100 == 0:
        print(f"row ind: {index}")
    print(documentID, documentName)
    query = """
            MERGE (d:Document {documentID: $id}) SET d.title = $title
            """
    params = {
        "id": documentID,
        "title": documentName
    }

    max_retries = 5
    backoff_delay = 0.05

    for attempt in range(max_retries):
        try:
            conn.run_query(query, parameters=params)
            return 
        except Exception as e:
            if "ConcurrentModificationException" in str(e) and attempt < max_retries - 1:
                sleep_time = (backoff_delay * (2 ** attempt)) + random.uniform(0, 0.05)
                time.sleep(sleep_time)
                continue
            else:
                print(f"❌ Failed permanently inserting row {index} after {attempt+1} attempts: {e}")
                break

def runParallelIngestion():
    print(f"starting parallel ingestion")
    rowsToProcess = list(df.iterrows())
    startTime = time.time()
    with ThreadPoolExecutor(max_workers=8) as executor:
        executor.map(uploadSingleDocument,rowsToProcess)
    print("complete")
    endtime = time.time()
    print((endtime-startTime)/3600)
runParallelIngestion()