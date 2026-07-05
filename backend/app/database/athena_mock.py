import os
import time
import logging
import boto3
import pandas as pd
import duckdb

logger = logging.getLogger("app.database.athena_mock")

class AthenaClient:
    def __init__(self):
        self.is_local = os.getenv("LOCAL_DEV", "true").lower() == "true"
        self.database = os.getenv("ATHENA_DATABASE", "analytics_db")
        self.s3_output = os.getenv("ATHENA_S3_OUTPUT", "s3://my-athena-query-results-bucket/uncategorized/")
        self.region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        
        if self.is_local:
            logger.info("Initializing Athena Client in LOCAL MOCK mode (using DuckDB).")
            self.duck_conn = duckdb.connect()
            self._mount_local_parquet_views()
        else:
            logger.info(f"Initializing Athena Client in AWS native mode (Region: {self.region}, Database: {self.database}).")
            self.athena_client = boto3.client("athena", region_name=self.region)
            self.s3_client = boto3.client("s3", region_name=self.region)

    def _mount_local_parquet_views(self):
        """Map local Parquet paths to virtual DuckDB tables, simulating Athena database schemas."""
        # Find absolute path of project root
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        sample_data_dir = os.path.join(base_dir, "data", "sample_data")
        
        tables = ["customers", "products", "orders", "order_items", "sales_summary", "regions"]
        
        for table in tables:
            parquet_pattern = os.path.join(sample_data_dir, table, "*.parquet")
            # Replace backslashes with forward slashes for DuckDB on Windows
            parquet_pattern = parquet_pattern.replace("\\", "/")
            try:
                # Mount tables as views
                self.duck_conn.execute(f"CREATE OR REPLACE VIEW {table} AS SELECT * FROM read_parquet('{parquet_pattern}')")
                logger.info(f"Mounted DuckDB view for table '{table}' from {parquet_pattern}")
            except Exception as e:
                logger.error(f"Failed to mount DuckDB view for {table}: {e}")

    def execute_query(self, sql_query: str) -> pd.DataFrame:
        """Run SQL query against either Athena (AWS) or DuckDB (local)."""
        # Ensure query is clean
        query_stripped = sql_query.strip()
        if query_stripped.endswith(";"):
            # Sometime Athena dislikes trailing semicolons
            query_stripped = query_stripped[:-1]

        if self.is_local:
            logger.info(f"Executing SQL query on DuckDB: {query_stripped}")
            try:
                df = self.duck_conn.execute(query_stripped).fetchdf()
                return df
            except Exception as e:
                logger.error(f"DuckDB execution error: {e}")
                raise e
        else:
            logger.info(f"Executing SQL query on Amazon Athena: {query_stripped}")
            try:
                response = self.athena_client.start_query_execution(
                    QueryString=query_stripped,
                    QueryExecutionContext={"Database": self.database},
                    ResultConfiguration={"OutputLocation": self.s3_output}
                )
                query_execution_id = response["QueryExecutionId"]
                
                # Poll query execution status
                while True:
                    status_resp = self.athena_client.get_query_execution(QueryExecutionId=query_execution_id)
                    state = status_resp["QueryExecution"]["Status"]["State"]
                    
                    if state in ["SUCCEEDED"]:
                        logger.info(f"Athena query {query_execution_id} completed successfully.")
                        break
                    elif state in ["FAILED", "CANCELLED"]:
                        reason = status_resp["QueryExecution"]["Status"].get("StateChangeReason", "Unknown reason")
                        logger.error(f"Athena query {query_execution_id} failed: {reason}")
                        raise Exception(f"Athena Query Failed: {reason}")
                        
                    time.sleep(1)
                
                # Fetch results from S3 and load into pandas
                # Athena saves query results as a CSV in S3: s3_output/query_execution_id.csv
                # Parse bucket name and key
                s3_path = f"{self.s3_output.rstrip('/')}/{query_execution_id}.csv"
                bucket_name = s3_path.split("/")[2]
                key_name = "/".join(s3_path.split("/")[3:])
                
                s3_resp = self.s3_client.get_object(Bucket=bucket_name, Key=key_name)
                df = pd.read_csv(s3_resp["Body"])
                return df
                
            except Exception as e:
                logger.error(f"Athena execution error: {e}")
                raise e

# Instantiate singleton client
athena_client = AthenaClient()
