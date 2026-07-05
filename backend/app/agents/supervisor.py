import time
import logging
from backend.app.agents.base import BaseAgent
from backend.app.agents.rag import RAGAgent
from backend.app.agents.sql_gen import SQLGenAgent
from backend.app.agents.sql_review import SQLReviewAgent
from backend.app.agents.execution import ExecutionAgent
from backend.app.agents.chart import ChartAgent
from backend.app.agents.response import ResponseAgent
from backend.app.services.observability import get_traces_by_session, clear_traces

logger = logging.getLogger("app.agents.supervisor")

SUPERVISOR_SYSTEM_PROMPT = """You are the Principal Supervisor Agent.
Your job is to orchestrate, organize, plan, and route tasks among specialized downstream agents (RAG, SQL Gen, SQL Review, Execution, Chart, Response).
"""

class SupervisorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Supervisor_Agent",
            system_prompt=SUPERVISOR_SYSTEM_PROMPT
        )
        # Instantiate sub-agents
        self.rag_agent = RAGAgent()
        self.sql_gen_agent = SQLGenAgent()
        self.sql_review_agent = SQLReviewAgent()
        self.execution_agent = ExecutionAgent()
        self.chart_agent = ChartAgent()
        self.response_agent = ResponseAgent()

    def process_query(self, user_question: str, session_id: str = "default_session") -> dict:
        """Run the complete agentic text-to-SQL analytics pipeline."""
        start_time = time.time()
        logger.info(f"Supervisor Agent starting execution for user query: '{user_question}'")
        
        # Clear trace cache for a fresh session trace if needed
        # clear_traces() 
        
        pipeline_status = "SUCCESS"
        error_msg = None
        sql_used = ""
        records = []
        chart_data = {"chart_type": "None", "fig_json": "{}", "image_base64": ""}
        summary = ""
        
        try:
            # 1. RAG context retrieval
            logger.info("Supervisor -> Invoking RAG Agent")
            context = self.rag_agent.retrieve_context(user_question, session_id=session_id)
            
            # 2. SQL generation
            logger.info("Supervisor -> Invoking SQL Gen Agent")
            sql_used = self.sql_gen_agent.generate_sql(user_question, context, session_id=session_id)
            
            # 3. SQL Review / validation
            logger.info("Supervisor -> Invoking SQL Review Agent")
            review = self.sql_review_agent.review_sql(sql_used, session_id=session_id)
            
            if review.get("status") == "REJECTED":
                errs = ", ".join(review.get("errors", ["Rejected by validation policy"]))
                raise Exception(f"SQL Validation Rejected: {errs}")
                
            # If review suggested corrected SQL, use it
            if review.get("corrected_sql"):
                logger.info("Supervisor -> Using corrected SQL suggested by review agent.")
                sql_used = review.get("corrected_sql")
                
            # 4. SQL Execution
            logger.info("Supervisor -> Invoking Execution Agent")
            exec_result = self.execution_agent.execute_query(sql_used, session_id=session_id)
            
            if not exec_result.get("success"):
                raise Exception(f"Execution Failed: {exec_result.get('error')}")
                
            records = exec_result.get("records", [])
            sql_used = exec_result.get("sql", sql_used)  # Might be corrected on execution retry
            
            # 5. Chart generation
            logger.info("Supervisor -> Invoking Chart Agent")
            chart_data = self.chart_agent.generate_chart(records, session_id=session_id)
            
            # 6. Response generation
            logger.info("Supervisor -> Invoking Response Agent")
            summary = self.response_agent.generate_final_response(user_question, sql_used, records, session_id=session_id)
            
        except Exception as e:
            logger.error(f"Supervisor Agent execution failed: {e}")
            pipeline_status = "ERROR"
            error_msg = str(e)
            summary = f"### System Error\nFailed to complete analytics process.\n\n**Reason:** {error_msg}"
            
        total_latency = (time.time() - start_time) * 1000
        
        # Gather all traces for this session to calculate summary metrics
        session_traces = get_traces_by_session(session_id)
        total_cost = sum(t.get("cost", 0.0) for t in session_traces)
        total_tokens = sum(t.get("tokens", 0) for t in session_traces)
        
        result_payload = {
            "success": pipeline_status == "SUCCESS",
            "error": error_msg,
            "sql": sql_used,
            "records": records,
            "chart": chart_data,
            "summary": summary,
            "metrics": {
                "latency_ms": round(total_latency, 2),
                "cost_usd": round(total_cost, 6),
                "tokens": total_tokens
            },
            "traces": session_traces
        }
        
        # Log trace for Supervisor itself
        self.record_supervisor_trace(user_question, result_payload, total_latency, pipeline_status, total_tokens, total_cost, session_id)
        
        return result_payload

    def record_supervisor_trace(self, question: str, output: dict, latency: float, status: str, tokens: int, cost: float, session_id: str):
        from backend.app.services.observability import record_agent_trace
        record_agent_trace(
            session_id=session_id,
            agent_name="Supervisor_Agent",
            step_name="process_query_complete",
            input_payload={"question": question},
            output_payload={
                "success": output["success"],
                "error": output["error"],
                "row_count": len(output["records"])
            },
            latency_ms=latency,
            status=status,
            tokens=tokens,
            cost=cost
        )

# Instantiate singleton
supervisor_agent = SupervisorAgent()
