import os
import logging
import time
from strands import Agent
from strands.models import BedrockModel
from backend.app.services.bedrock_service import CLAUDE_SONNET, CLAUDE_OPUS, NOVA_PRO, bedrock_service
from backend.app.services.observability import record_agent_trace

logger = logging.getLogger("app.agents.base")

class BaseAgent:
    def __init__(self, name: str, system_prompt: str, tools: list = None):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.mock_mode = os.getenv("MOCK_LLM", "false").lower() == "true"
        self.model_id = os.getenv("BEDROCK_MODEL_ID", CLAUDE_SONNET)
        from backend.app.services.bedrock_service import PRICING
        if self.model_id not in PRICING:
            self.model_id = CLAUDE_SONNET
            
        if self.mock_mode:
            logger.info(f"Agent '{self.name}' initialized in mock mode.")
            self.strands_agent = None
        else:
            try:
                # Initialize Strands BedrockModel
                region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
                bedrock_model = BedrockModel(
                    model_id=self.model_id,
                    temperature=0.1
                )
                # Set system prompt if supported by strands Agent constructor or via messages
                self.strands_agent = Agent(model=bedrock_model, tools=self.tools)
                logger.info(f"Agent '{self.name}' successfully initialized using Strands Agents SDK with model {self.model_id}.")
            except Exception as e:
                logger.warning(f"Failed to initialize Strands Agent '{self.name}': {e}. Falling back to Bedrock service wrapper / Mock.")
                self.strands_agent = None

    def execute(self, prompt: str, session_id: str = "default_session") -> str:
        """Execute the agent task, tracking latency, token usage, and cost."""
        start_time = time.time()
        logger.info(f"Executing agent '{self.name}' for session '{session_id}'...")
        
        try:
            if self.strands_agent:
                # Compile system prompt + prompt together if strands agent doesn't take system prompt directly in __init__
                full_prompt = f"{self.system_prompt}\n\nUser Request: {prompt}"
                response = self.strands_agent(full_prompt)
                # Strands agents return a string or response object
                result = str(response)
            else:
                # Fallback to direct bedrock service wrapper
                result = bedrock_service.generate_text(
                    prompt=prompt,
                    system_prompt=self.system_prompt,
                    model_id=self.model_id
                )
                
            latency_ms = (time.time() - start_time) * 1000
            
            # Simple token estimation for tracking logs
            estimated_tokens = (len(prompt) + len(self.system_prompt) + len(result)) // 4
            estimated_cost = (estimated_tokens / 1000.0) * 0.003  # default standard sonnet cost
            
            # Log trace
            record_agent_trace(
                session_id=session_id,
                agent_name=self.name,
                step_name="execute",
                input_payload={"prompt": prompt},
                output_payload={"result": result},
                latency_ms=latency_ms,
                status="SUCCESS",
                tokens=estimated_tokens,
                cost=estimated_cost
            )
            return result
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Error executing agent '{self.name}': {e}")
            record_agent_trace(
                session_id=session_id,
                agent_name=self.name,
                step_name="execute_error",
                input_payload={"prompt": prompt},
                output_payload={"error": str(e)},
                latency_ms=latency_ms,
                status="ERROR"
            )
            raise e
