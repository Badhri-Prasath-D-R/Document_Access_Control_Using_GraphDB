import pandas as pd
import time
import random
from main import conn
from concurrent.futures import ThreadPoolExecutor

excelFile = "Access_Data_Sample.xlsx"

sheets = pd.read_excel(excelFile, sheet_name=["RoleAccess","Emp Master","RoleMaster","Job Master","Document Access"])

accessSheet = sheets["RoleAccess"]

def createRelBtwPSnoAndJobCode(rowTuple):
    index, row = rowTuple
    jobCode = str(row["Job_Code"]).strip()
    psNumber = str(row["PSNo"]).strip()
    roleCode = str(row["Role_Code"]).strip()
    if not jobCode or not psNumber or not roleCode:
        return
    if index%500 == 0:
        print(f"row ind reached is ---------> {index}")
    print(f"{psNumber}-[:{roleCode}]->{jobCode}")
    query = """
            MATCH (e:Employee {psno: $psno})
            MATCH (j:Job {jobCode: $jobCode})
            MERGE (e)-[r:HAS_ACCESS {roleCode: $roleCode}]->(j)
            """
    params = {
        "psno": psNumber,
        "jobCode": jobCode,
        "roleCode": roleCode
    }
    maxRetries = 6
    backoffDelay = 0.05
    for attempt in range(maxRetries):
        try:
            conn.run_query(query,parameters = params)
            return
        except Exception as e:
            if "ConcurrentModificationException" in str(e) and attempt < maxRetries - 1:
                sleep_time = (backoffDelay * (2 ** attempt)) + random.uniform(0, 0.05)
                time.sleep(sleep_time)
                continue
            else:
                print(f"Failed to link row {index} ({psNumber} -> {jobCode}): {e}")
                break

def runParallelAccessIngestion():
    startTime = time.time()
    print(f"spawning threadpool")
    rows = list(accessSheet.iterrows())
    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(createRelBtwPSnoAndJobCode,rows))  
    endTime = time.time()
    print(f"time taken: {endTime-startTime}")

runParallelAccessIngestion()


