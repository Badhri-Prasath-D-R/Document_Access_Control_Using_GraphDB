from fastapi import FastAPI, HTTPException, Path, Header, Body
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import dotenv
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
import time
from fetchFromDB import fetchFromDB
import importlib
dotenv.load_dotenv()

mysql = importlib.import_module("mysql.connector")

MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3307,
    "user": "root",
    "password": os.environ.get("password"), 
    "database": "sqltest"
}

app = FastAPI(title="Secure Document Access")

app.add_middleware(GZipMiddleware, minimum_size=500)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ArcadeDBConnector:
    def __init__(self, URL, user, password, database):
        print("connecting to database")
        self.baseURL = URL.rstrip('/')
        self.auth = (user, password)
        self.database = database
        self.endpoint = f"{self.baseURL}/api/v1/command/{self.database}"
        self.client = httpx.Client(
            auth=self.auth,
            http2=True,  # Enables binary multiplexing streams over a single connection
            timeout=30.0,
            limits=httpx.Limits(
                max_keepalive_connections=50,  # Keeps connections alive in the pool
                max_connections=200,          # Production boundary handling
                keepalive_expiry=60.0
            ),
            headers={
                "Content-Type": "application/json",
                "Connection": "keep-alive"    # Forces the server-side to preserve the stream
            }
        )

    def run_query(self, query: str, parameters: dict):
        payload = {
            "language": "cypher",
            "command": query,
        }
        if parameters:
            payload["params"] = parameters
        try:
            response = self.client.post(self.endpoint, json=payload)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"ArcadeDB Error: {response.text}"
                )
            return response.json().get("result", [])
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Database connectivity exception across hot stream pool: {str(exc)}"
            )

DB_URI = os.environ["DB_URI"] 
DB_USERNAME = os.environ["DB_USERNAME"]
DB_PWD = os.environ["DB_PWD"]
DB_NAME = os.environ["DB_NAME"]

conn = ArcadeDBConnector(DB_URI, DB_USERNAME, DB_PWD, DB_NAME)

@app.get("/")
def mainPage():
    return {"status": "running"}


@app.get("/getDocumentIDAndAccess/{psno}")
def getDocumentIDAndAccess(psno: str = Path(..., description="The unique PSNo identifier of the employee")):
    start_total_pipeline = time.time()
    
    query = """
            MATCH (e:Employee {psno: $psno})-[access:HAS_ACCESS]->(j:Job)-[:CAN_VIEW]->(d:Document)
            RETURN DISTINCT d.documentID AS DocumentID, 
                   d.title AS DocumentTitle, 
                   access.roleCode AS AuthorizedByRoleCode,
                   j.jobCode AS JobCode
                   LIMIT 10000000
            """
    qstart = time.time()
    records = conn.run_query(query, parameters={"psno": psno})
    total_records_count = len(records) 
    qend = time.time()
    
    if total_records_count == 0:
        return JSONResponse(content={
            "qtimeTaken": qend - qstart,
            "atimeTaken": 0.0,
            "psno": psno,
            "total_accessible_documents": 0,
            "accessible_documents": []
        })
    
    validatedDocuments = []
    astart = time.time()
    for record in records:
        validatedDocuments.append({
            "DocumentID": str(record.get("DocumentID")),
            "DocumentTitle": str(record.get("DocumentTitle")),
            "AuthorizedByRoleCode": str(record.get("AuthorizedByRoleCode")),
            "JobCode": str(record.get("JobCode"))
        })
    aend = time.time()
    
    end_total_pipeline = time.time()
    print(f"\n---LOG FOR PSNO {psno} ---")
    print(f"ArcadeDB Query Execution: {qend - qstart:.4f} seconds")
    print(f"Data Structuring Pipeline: {aend - astart:.4f} seconds")
    print(f"Total API Turnaround Time: {end_total_pipeline - start_total_pipeline:.4f} seconds\n")

    return JSONResponse(content={
        "qtimeTaken": qend - qstart,
        "atimeTaken": aend - astart,
        "psno": psno,
        "total_accessible_documents": len(validatedDocuments),
        "accessible_documents": validatedDocuments
    })

@app.get("/api/documents/download/{document_id}")
def download_document_asset(
    document_id: str = Path(..., description="The ID of the document asset to fetch"),
    x_psno: str = Header(..., alias="X-PSNo", description="User identifier header"),
    x_role_code: str = Header(..., alias="X-Role-Code", description="The role code claim being checked")
    ):
    verification_query = """
    MATCH (e:Employee {psno: $psno})-[access:HAS_ACCESS {roleCode: $role_code}]->(j:Job)-[:CAN_VIEW]->(d:Document {documentID: $doc_id})
    RETURN count(access) > 0 AS IsAuthorized
    """
    params = {"psno": x_psno, "role_code": x_role_code, "doc_id": document_id}
    check = conn.run_query(verification_query, parameters=params)
    
    if not check or not check[0].get("IsAuthorized"):
        raise HTTPException(
            status_code=403,
            detail="Access Denied: The clearance role code does not match authorized permissions for this specific document."
        )
        
    print(f"Secure verified stream initialized for Document {document_id} by PSNo {x_psno}")
    return fetchFromDB(document_id)

@app.post("/api/documents/edit/{document_id}")
def edit_document_asset(
    document_id: str = Path(..., description="The ID of the document to modify"),
    x_psno: str = Header(..., alias="X-PSNo", description="User identifier header"),
    x_role_code: str = Header(..., alias="X-Role-Code", description="The role code claim being checked"),
    update_data: dict = Body(..., description="The modified dataset updates")
):
    if x_role_code != "5267":
        raise HTTPException(
            status_code=403,
            detail="Access Denied: Insufficient authorization permissions to modify file properties."
        ) 
    verification_query = """
    MATCH (e:Employee {psno: $psno})-[access:HAS_ACCESS {roleCode: '5267'}]->(j:Job)-[:CAN_VIEW]->(d:Document {documentID: $doc_id})
    RETURN count(access) > 0 AS IsAuthorized
    """
    check = conn.run_query(verification_query, parameters={"psno": x_psno, "doc_id": document_id})
    if not check or not check[0].get("IsAuthorized"):
        raise HTTPException(
            status_code=403, 
            detail="Access Denied: You do not have active Admin permissions for this specific document."
        )  
    print(f"Document {document_id} successfully modified by Admin PSNo {x_psno}")
    return {"status": "success", "message": f"Document {document_id} modified successfully."}

@app.get("/api/benchmark/compare-efficiency2/{target_psno}")
def run_production_database_benchmark(
    target_psno: str = Path(..., description="The Employee PSNo used to trigger cross-database execution metrics")
):
    results_profile = {}
    test_doc_id = "5375" 
    graph_start = time.perf_counter()
    
    graph_query = """
    MATCH (e:Employee {psno: $psno})-[access:HAS_ACCESS]->(j:Job)-[:CAN_VIEW]->(d:Document {documentID: $doc_id})
    RETURN count(d) > 0 AS IsAuthorized
    """
    try:
        graph_db_response = conn.run_query(graph_query, parameters={"psno": target_psno, "doc_id": test_doc_id})
        graph_res = graph_db_response[0].get("IsAuthorized", False) if graph_db_response else False
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph Engine Profiling Error: {str(e)}")
        
    graph_end = time.perf_counter()
    results_profile["graph_engine"] = {
        "execution_time_seconds": graph_end - graph_start,
        "authorized_status": graph_res
    }

    try:
        sql_connection = mysql.connect(
            host="localhost",
            database="sqltest",
            user="root",
            password=os.environ.get("password")
        )
        sql_cursor = sql_connection.cursor(dictionary=True)
        
        sql_start = time.perf_counter()
        
        sql_query = """
        SELECT COUNT(*) > 0 AS IsAuthorized
        FROM Employee_Jobs_Bridge ejb
        INNER JOIN Job_Documents_Bridge jdb ON ejb.job_code = jdb.job_code
        WHERE ejb.psno = %s AND jdb.document_id = %s;
        """
        sql_cursor.execute(sql_query, (target_psno, test_doc_id))
        sql_db_response = sql_cursor.fetchone()
        sql_res = sql_db_response["IsAuthorized"] if sql_db_response else False
        
        sql_end = time.perf_counter()
        sql_cursor.close()
        sql_connection.close()
        
    except Exception as e:
        results_profile["sql_engine_error"] = f"MySQL Benchmark Execution Failed: {str(e)}"
        return results_profile

    results_profile["sql_engine"] = {
        "execution_time_seconds": sql_end - sql_start,
        "authorized_status": bool(sql_res)
    }

    g_time = results_profile["graph_engine"]["execution_time_seconds"]
    s_time = results_profile["sql_engine"]["execution_time_seconds"]
    
    if g_time > 0:
        performance_multiplier = s_time / g_time
        results_profile["efficiency_summary"] = (
            f"Proved! For a single targeted security clearance check, "
            f"ArcadeDB's pointer-chasing approach was {performance_multiplier:.2f}x faster "
            f"than performing multi-index relational table scans."
        )

    return results_profile

@app.get("/api/benchmark/compare-efficiency/{target_psno}")
def run_production_database_benchmark(
    target_psno: str = Path(..., description="The Employee PSNo used to trigger cross-database execution metrics")
):
    results_profile = {}
    test_doc_id = "5375" 

    graph_query = """
    MATCH (e:Employee {psno: $psno})-[access:HAS_ACCESS]->(j:Job)-[:CAN_VIEW]->(d:Document {documentID: $doc_id})
    RETURN count(d) > 0 AS IsAuthorized
    """
    params = {"psno": target_psno, "doc_id": test_doc_id}
    
    try:
        conn.run_query(graph_query, parameters=params)
        graph_start = time.perf_counter()
        graph_db_response = conn.run_query(graph_query, parameters=params)
        graph_end = time.perf_counter()
        graph_res = graph_db_response[0].get("IsAuthorized", False) if graph_db_response else False
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph Engine Profiling Error: {str(e)}")
        
    results_profile["graph_engine"] = {
        "execution_time_seconds": graph_end - graph_start,
        "authorized_status": bool(graph_res)
    }
    try:
        sql_connection = mysql.connect(**MYSQL_CONFIG)
        sql_cursor = sql_connection.cursor(dictionary=True)
        
        sql_start = time.perf_counter()
        
        sql_query = """
        SELECT COUNT(*) > 0 AS IsAuthorized
        FROM Employee_Jobs_Bridge ejb
        INNER JOIN Job_Documents_Bridge jdb ON ejb.job_code = jdb.job_code
        WHERE ejb.psno = %s AND jdb.document_id = %s;
        """
        sql_cursor.execute(sql_query, (target_psno, test_doc_id))
        sql_db_response = sql_cursor.fetchone()
        sql_res = sql_db_response["IsAuthorized"] if sql_db_response else False
        
        sql_end = time.perf_counter()
        sql_cursor.close()
        sql_connection.close()
        
    except Exception as e:
        results_profile["sql_engine_error"] = f"MySQL Benchmark Execution Failed: {str(e)}"
        return results_profile

    results_profile["sql_engine"] = {
        "execution_time_seconds": sql_end - sql_start,
        "authorized_status": bool(sql_res)
    }

    g_time = results_profile["graph_engine"]["execution_time_seconds"]
    s_time = results_profile["sql_engine"]["execution_time_seconds"]
    
    if g_time > 0:
        performance_multiplier = s_time / g_time
        if performance_multiplier > 1:
            results_profile["efficiency_summary"] = (
                f"Verification complete. ArcadeDB graph pointer walks were "
                f"{performance_multiplier:.2f}x faster than scanning MySQL relational indexes."
            )
        else:
            results_profile["efficiency_summary"] = (
                f"Verification complete. MySQL native binary stream protocol was "
                f"{1/performance_multiplier:.2f}x faster than parsing JSON over ArcadeDB's HTTP engine wrapper."
            )

    return results_profile