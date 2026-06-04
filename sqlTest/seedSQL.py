import os
import importlib
import dotenv
import pandas as pd

dotenv.load_dotenv()

excelFile = "Access_Data_Sample.xlsx"

print("Parsing Excel workbook sheets into memory...")
sheets = pd.read_excel(excelFile, sheet_name=["RoleAccess", "Emp Master", "RoleMaster", "Job Master"])

roleAccessSheet = sheets["RoleAccess"]
empMasterSheet = sheets["Emp Master"]
roleMasterSheet = sheets["RoleMaster"]
jobMasterSheet = sheets["Job Master"]


mysql = importlib.import_module("mysql.connector")

MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": os.environ.get("password"), 
    "database": "sqltest"
}

def seed_mysql():
    conn = mysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    print("Connected to MySQL successfully. Starting dataframe streaming process...")

    try:
        print("-> Loading Employees Master records...")
        emp_df = empMasterSheet.dropna(subset=["PSNo", "MEMP_Name"])
        emp_data = [(str(row["PSNo"]).strip(), str(row["MEMP_Name"]).strip()) for _, row in emp_df.iterrows()]
        cursor.executemany("INSERT IGNORE INTO Employees (psno, name) VALUES (%s, %s);", emp_data)

        print("-> Loading Jobs Master records...")
        job_df = jobMasterSheet.dropna(subset=["Job_Code"])
        job_data = [
            (
                str(row["Job_Code"]).strip(), 
                str(row.get("Job_Description", "")).strip(), 
                str(row.get("Long_Job_Description", "")).strip()
            ) 
            for _, row in job_df.iterrows()
        ]
        cursor.executemany("INSERT IGNORE INTO Jobs (job_code, job_description, long_job_description) VALUES (%s, %s, %s);", job_data)

        print("-> Loading Production Documents matrix chunks...")
        if os.path.exists("documents.csv"):
            doc_df = pd.read_csv("documents.csv", dtype=str).dropna()
            doc_data = [(str(row.iloc[0]).strip(), str(row.iloc[1]).strip()) for _, row in doc_df.iterrows()]
            cursor.executemany("INSERT IGNORE INTO Documents (document_id, title) VALUES (%s, %s);", doc_data)
        else:
            print("⚠️ Skipping Documents master: 'documents.csv' not found in working path directory.")

        print("-> Mapping Employee clearance vectors...")
        role_access_df = roleAccessSheet.dropna(subset=["PSNo", "Role_Code", "Job_Code"])
        role_access_data = [
            (str(row["PSNo"]).strip(), str(row["Role_Code"]).strip(), str(row["Job_Code"]).strip()) 
            for _, row in role_access_df.iterrows()
        ]
        cursor.executemany("INSERT IGNORE INTO Employee_Jobs_Bridge (psno, role_code, job_code) VALUES (%s, %s, %s);", role_access_data)
        print("-> Mapping Directory Leaf indices...")
        if os.path.exists("job_document_mapping.csv"):
            mapping_df = pd.read_csv("job_document_mapping.csv", dtype=str).dropna()
            mapping_data = [(str(row.iloc[0]).strip(), str(row.iloc[1]).strip()) for _, row in mapping_df.iterrows()]
            cursor.executemany("INSERT IGNORE INTO Job_Documents_Bridge (job_code, document_id) VALUES (%s, %s);", mapping_data)
        else:
            print("error")

        conn.commit()
        print("seeded into MySQL")

    except Exception as e:
        conn.rollback()
        print(f"failure: {repr(e)}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    seed_mysql()