import pandas as pd
from main import conn
from concurrent.futures import ThreadPoolExecutor

excelFile = "Access_Data_Sample.xlsx"

sheets = pd.read_excel(excelFile, sheet_name=["RoleAccess","Emp Master","RoleMaster","Job Master","Document Access"])

roleAccessSheet = sheets["RoleAccess"]
empMasterSheet = sheets["Emp Master"]
roleMasterSheet = sheets["RoleMaster"]
jobMasterSheet = sheets["Job Master"]
documentSheet = sheets["Document Access"]

def createEMPNodes():
    print("Creating Emplyee Nodes with PSNo and name")
    for ind,row in empMasterSheet.iterrows():
        psno = str(row["PSNo"]).strip()
        empname = str(row["MEMP_Name"]).strip()
        query = f"""
                MERGE (e:Employee {{psno: '{psno}'}})
                ON CREATE SET e.name = '{empname}'
                ON MATCH SET e.name = '{empname}'
                RETURN e
                """
        try:
            conn.run_query(query)
        except Exception as e:
            print(f"failed to create employee nodes")
    print("employee node creation function complete")

def createJobNodesLinear():
    print("🚀 Starting linear job node ingestion...")
    
    for ind, row in jobMasterSheet.iterrows():
        job_code = str(row["Job_Code"]).strip()
        short_desc = str(row["Job_Description"]).strip().replace("'", "\\'")
        long_desc = str(row["Long_Job_Description"]).strip().replace("'", "\\'")
        
        if not job_code or job_code == "nan":
            continue
            
        if ind % 1000 == 0:
            print(f"Processing index: {ind}")
            
        query = f"""
        MERGE (j:Job {{jobCode: '{job_code}'}})
        ON CREATE SET j.shortJobDescription = '{short_desc}', j.longJobDescription = '{long_desc}'
        ON MATCH SET j.shortJobDescription = '{short_desc}', j.longJobDescription = '{long_desc}'
        """
        
        try:
            conn.run_query(query)
        except Exception as e:
            print(f"❌ Failed at index {ind} for JobCode {job_code}: {e}")
            
    print("🎉 Job node creation function complete!")


