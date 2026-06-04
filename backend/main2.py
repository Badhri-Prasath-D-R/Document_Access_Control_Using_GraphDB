from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
import mysql.connector
import httpx
import os
import dotenv
import time

# Load local environment settings
dotenv.load_dotenv()

MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3307,
    "user": "root",
    "password": os.environ.get("password"), 
    "database": "sqltest"
}

app = FastAPI(title="Secure Document Access - ArcadeDB Native High-Performance Speed")

app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GRAPH_HOST = "localhost"
GRAPH_PORT = 2480
GRAPH_USER = os.environ.get("DB_USERNAME")
GRAPH_PWD = os.environ.get("DB_PWD")
GRAPH_DB_NAME = os.environ["DB_NAME"]

native_client = httpx.AsyncClient(
    auth=(GRAPH_USER, GRAPH_PWD),
    limits=httpx.Limits(max_keepalive_connections=500, max_connections=1000),
    timeout=5.0
)

async def run_native_graph_query(command: str):
    url = f"http://{GRAPH_HOST}:{GRAPH_PORT}/api/v1/command/{GRAPH_DB_NAME}"
    payload = {"language": "sql", "command": command}
    
    try:
        response = await native_client.post(url, json=payload)
        if response.status_code == 200:
            return response.json().get("result", [])
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Native Graph Engine network error: {str(exc)}")


@app.get("/")
def main_page():
    return {"status": "running", "protocol": "ArcadeDB Native High-Speed JSON"}


@app.get("/getDocumentIDAndAccess/{psno}")
async def get_document_id_and_access(psno: str = Path(..., description="The unique PSNo identifier of the employee")):
    start_total_pipeline = time.perf_counter()
    native_query = f"""
    SELECT documentID, title, jobCode 
    FROM (
        SELECT expand(out('HAS_ACCESS').out('CAN_VIEW')) 
        FROM Employee WHERE psno = '{psno}'
    )
    """
    
    qstart = time.perf_counter()
    records = await run_native_graph_query(native_query) 
    qend = time.perf_counter()
    
    if not records:
        return JSONResponse(content={
            "qtimeTaken": qend - qstart,
            "atimeTaken": 0.0,
            "psno": psno,
            "total_accessible_documents": 0,
            "accessible_documents": []
        })
    
    astart = time.perf_counter()
    validated_documents = [
        {
            "DocumentID": str(record.get("documentID")),
            "DocumentTitle": str(record.get("title")),
            "AuthorizedByRoleCode": "AUTHORIZED",
            "JobCode": "NATIVE_WALK"
        } for record in records
    ]
    aend = time.perf_counter()
    
    end_total_pipeline = time.perf_counter()
    print(f"\n--- [NATIVE GRAPH PROTOCOL] LOG FOR PSNO {psno} ---")
    print(f"ArcadeDB Native Execution: {qend - qstart:.6f} seconds")
    print(f"Data Structuring Pipeline: {aend - astart:.6f} seconds")
    print(f"Total API Turnaround Time: {end_total_pipeline - start_total_pipeline:.6f} seconds\n")

    return JSONResponse(content={
        "qtimeTaken": qend - qstart,
        "atimeTaken": aend - astart,
        "psno": psno,
        "total_accessible_documents": len(validated_documents),
        "accessible_documents": validated_documents
    })


@app.get("/api/benchmark/compare-efficiency/{target_psno}")
async def run_production_database_benchmark(
    target_psno: str = Path(..., description="The Employee PSNo used to trigger cross-database execution metrics")
):
    results_profile = {}
    test_doc_id = "5375" 
    ITERATIONS = 100
    native_query = f"""
    SELECT count(*) AS path_count 
    FROM (
        SELECT expand(out('HAS_ACCESS').out('CAN_VIEW')) 
        FROM Employee WHERE psno = '{target_psno}'
    ) WHERE documentID = '{test_doc_id}'
    """
    
    try:
        await run_native_graph_query(native_query)
        
        graph_start = time.perf_counter()
        for _ in range(ITERATIONS):
            graph_db_response = await run_native_graph_query(native_query)
        graph_end = time.perf_counter()
        
        graph_avg_time = (graph_end - graph_start) / ITERATIONS
        
        raw_count = graph_db_response[0].get("path_count", 0) if graph_db_response else 0
        graph_res = raw_count > 0
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Native Graph Engine Profiling Error: {str(e)}")
        
    results_profile["graph_engine"] = {
        "total_time_for_100_runs": graph_end - graph_start,
        "execution_time_seconds": graph_avg_time,
        "authorized_status": bool(graph_res)
    }

    try:
        sql_connection = mysql.connector.connect(**MYSQL_CONFIG)
        sql_cursor = sql_connection.cursor(dictionary=True)
        
        sql_query = """
        SELECT COUNT(*) > 0 AS IsAuthorized
        FROM Employee_Jobs_Bridge ejb
        INNER JOIN Job_Documents_Bridge jdb ON ejb.job_code = jdb.job_code
        WHERE ejb.psno = %s AND jdb.document_id = %s;
        """
        
        sql_start = time.perf_counter()
        for _ in range(ITERATIONS):
            sql_cursor.execute(sql_query, (target_psno, test_doc_id))
            sql_db_response = sql_cursor.fetchone()
        sql_end = time.perf_counter()
        
        sql_avg_time = (sql_end - sql_start) / ITERATIONS
        sql_res = sql_db_response["IsAuthorized"] if sql_db_response else False
        
        sql_cursor.close()
        sql_connection.close()
        
    except Exception as e:
        results_profile["sql_engine_error"] = f"MySQL Benchmark Execution Failed: {str(e)}"
        return results_profile

    results_profile["sql_engine"] = {
        "total_time_for_100_runs": sql_end - sql_start,
        "execution_time_seconds": sql_avg_time,
        "authorized_status": bool(sql_res)
    }
    g_time = results_profile["graph_engine"]["execution_time_seconds"]
    s_time = results_profile["sql_engine"]["execution_time_seconds"]
    
    if g_time > 0:
        performance_multiplier = s_time / g_time
        if performance_multiplier > 1:
            results_profile["efficiency_summary"] = (
                f"Proved! Bypassing compatibility plugins, ArcadeDB graph native pointer walks "
                f"were {performance_multiplier:.2f}x faster than scanning MySQL relational indexes."
            )
        else:
            results_profile["efficiency_summary"] = (
                f"Verification complete. MySQL native index execution was "
                f"{1/performance_multiplier:.2f}x faster than walking small native graph pathways."
            )

    return results_profile


@app.on_event("shutdown")
async def shutdown_event():
    await native_client.aclose()