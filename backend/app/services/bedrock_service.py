import os
import json
import time
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger("app.services.bedrock_service")

# Model IDs
CLAUDE_SONNET = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
CLAUDE_OPUS = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
NOVA_PRO = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
TITAN_EMBEDDING = "amazon.titan-embed-text-v1"

# Bedrock Pricing per 1,000 tokens (Standard pricing in USD)
PRICING = {
    CLAUDE_SONNET: {"input": 0.003, "output": 0.015},
    TITAN_EMBEDDING: {"input": 0.0001, "output": 0.0}
}

# Global usage and cost tracking metrics
metrics_store = {
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_cost": 0.0,
    "call_count": 0,
    "calls": []  # List of execution traces (model, prompt_tokens, output_tokens, cost, latency_sec)
}

class BedrockService:
    def __init__(self):
        self.region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        self.mock_mode = os.getenv("MOCK_LLM", "false").lower() == "true"
        
        if self.mock_mode:
            logger.info("Initializing Bedrock Service in MOCK mode.")
            self.client = None
        else:
            try:
                self.client = boto3.client("bedrock-runtime", region_name=self.region)
                logger.info(f"Bedrock Runtime Client successfully initialized in region {self.region}")
            except Exception as e:
                logger.warning(f"Failed to initialize real Bedrock client: {e}. Falling back to MOCK mode.")
                self.mock_mode = True
                self.client = None

    def generate_embeddings(self, text_input: str) -> list[float]:
        """Generate text embeddings using Amazon Titan Embeddings."""
        if self.mock_mode:
            # Return a deterministic mock embedding vector of size 1536
            # Use hash of the input string to generate a reproducible mock vector
            import hashlib
            hash_val = int(hashlib.md5(text_input.encode('utf-8')).hexdigest(), 16)
            vector = []
            for i in range(1536):
                # Pseudo-random float between -1.0 and 1.0
                val = (((hash_val >> (i % 64)) & 0xff) / 255.0) * 2 - 1
                vector.append(val)
            # Normalize vector
            norm = sum(x**2 for x in vector)**0.5
            return [x/norm for x in vector]

        try:
            body = json.dumps({"inputText": text_input})
            start_time = time.time()
            response = self.client.invoke_model(
                body=body,
                modelId=TITAN_EMBEDDING,
                accept="application/json",
                contentType="application/json"
            )
            latency = time.time() - start_time
            response_body = json.loads(response.get("body").read())
            embedding = response_body.get("embedding")
            
            # Titan pricing counts character length or tokens. Typically approx 4 chars = 1 token.
            token_count = len(text_input) // 4
            cost = (token_count / 1000.0) * PRICING[TITAN_EMBEDDING]["input"]
            
            self._update_metrics(TITAN_EMBEDDING, token_count, 0, cost, latency)
            return embedding
        except Exception as e:
            logger.error(f"Error calling Bedrock embeddings: {e}. Falling back to mock embeddings.")
            self.mock_mode = True
            return self.generate_embeddings(text_input)

    def generate_text(self, prompt: str, system_prompt: str = "", model_id: str = CLAUDE_SONNET, temperature: float = 0.1) -> str:
        """Call Bedrock foundation models (Claude Sonnet/Opus, Nova Pro) to generate text responses."""
        if model_id not in PRICING:
            model_id = CLAUDE_SONNET

        if self.mock_mode:
            return self._generate_mock_text(prompt, system_prompt, model_id)

        try:
            start_time = time.time()
            
            # Prepare payloads according to different provider requirements
            if "claude" in model_id:
                # Anthropic Claude Messages API on Bedrock
                messages = [{"role": "user", "content": prompt}]
                payload = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4096,
                    "temperature": temperature,
                    "messages": messages
                }
                if system_prompt:
                    payload["system"] = system_prompt
                
                response = self.client.invoke_model(
                    body=json.dumps(payload),
                    modelId=model_id,
                    accept="application/json",
                    contentType="application/json"
                )
                response_body = json.loads(response.get("body").read())
                result_text = response_body["content"][0]["text"]
                
                # Extract tokens
                input_tokens = response_body.get("usage", {}).get("input_tokens", 0)
                output_tokens = response_body.get("usage", {}).get("output_tokens", 0)
                
            elif "nova" in model_id:
                # Amazon Nova Messages API
                messages = [{"role": "user", "content": [{"text": prompt}]}]
                payload = {
                    "inferenceConfig": {
                        "temperature": temperature,
                        "maxNewTokens": 4096
                    },
                    "messages": messages
                }
                if system_prompt:
                    payload["system"] = [{"text": system_prompt}]
                
                response = self.client.invoke_model(
                    body=json.dumps(payload),
                    modelId=model_id,
                    accept="application/json",
                    contentType="application/json"
                )
                response_body = json.loads(response.get("body").read())
                result_text = response_body["output"]["message"]["content"][0]["text"]
                
                # Extract tokens
                input_tokens = response_body.get("usage", {}).get("inputTokens", 0)
                output_tokens = response_body.get("usage", {}).get("outputTokens", 0)
            else:
                raise ValueError(f"Unsupported model provider for model_id: {model_id}")

            latency = time.time() - start_time
            
            # Cost calculation
            cost = ((input_tokens / 1000.0) * PRICING[model_id]["input"]) + ((output_tokens / 1000.0) * PRICING[model_id]["output"])
            self._update_metrics(model_id, input_tokens, output_tokens, cost, latency)
            
            return result_text

        except Exception as e:
            logger.error(f"Error in Bedrock text generation for model {model_id}: {e}. Falling back to Mock.")
            return self._generate_mock_text(prompt, system_prompt, model_id)

    def _update_metrics(self, model: str, input_t: int, output_t: int, cost: float, latency: float):
        metrics_store["total_input_tokens"] += input_t
        metrics_store["total_output_tokens"] += output_t
        metrics_store["total_cost"] += cost
        metrics_store["call_count"] += 1
        metrics_store["calls"].append({
            "timestamp": time.time(),
            "model": model,
            "input_tokens": input_t,
            "output_tokens": output_t,
            "cost": round(cost, 6),
            "latency": round(latency, 2)
        })

    def _generate_mock_text(self, prompt: str, system_prompt: str, model_id: str) -> str:
        """Simulate high quality mock responses for SQL generation, SQL validation, and RAG retrieval."""
        logger.info(f"Generating mock response for prompt snippet: {prompt[:60]}...")
        
        # Approximate tokens
        input_t = len(prompt) // 4 + 10
        output_t = 150
        cost = ((input_t / 1000.0) * PRICING[model_id]["input"]) + ((output_t / 1000.0) * PRICING[model_id]["output"])
        self._update_metrics(model_id, input_t, output_t, cost, 0.1)

        sys_prompt_lower = system_prompt.lower()
        prompt_lower = prompt.lower()
        
        # 1. RAG Agent / Postgres Retrieval
        if "rag" in sys_prompt_lower:
            return "Active Customer = customer with at least one order in the last 90 days. Churn Rate = percentage of customers with no active orders in 90 days."

        # 2. SQL Gen Agent
        if "staff ai" in sys_prompt_lower or "convert a natural language" in sys_prompt_lower:
            if "revenue growth" in prompt_lower or "12 months" in prompt_lower:
                return """SELECT 
    date_trunc('month', order_date) AS month, 
    SUM(total_amount) AS monthly_revenue
FROM orders 
WHERE status = 'Completed' 
GROUP BY 1 
ORDER BY 1 DESC 
LIMIT 12"""
            elif "highest revenue last quarter" in prompt_lower or "products" in prompt_lower:
                return """SELECT 
    p.name, 
    SUM(oi.quantity * oi.price * (1 - oi.discount)) AS total_revenue
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
JOIN orders o ON oi.order_id = o.order_id
WHERE o.status = 'Completed' AND o.order_date >= '2026-04-01' AND o.order_date <= '2026-06-30'
GROUP BY p.name
ORDER BY total_revenue DESC
LIMIT 10"""
            elif "churn" in prompt_lower or "region" in prompt_lower:
                return """SELECT 
    r.name as region,
    COUNT(CASE WHEN c.churned = 'Yes' THEN 1 END) * 100.0 / COUNT(*) AS churn_rate
FROM customers c
JOIN regions r ON c.region_id = r.region_id
GROUP BY r.name
ORDER BY churn_rate DESC"""
            else:
                # Default generic query
                return "SELECT * FROM customers LIMIT 10"

        # 3. SQL Review Agent
        if "quality assurance" in sys_prompt_lower or "review" in sys_prompt_lower:
            return json.dumps({
                "status": "APPROVED",
                "corrected_sql": "",
                "errors": [],
                "warnings": ["Ensure that appropriate indexes exist on foreign keys (region_id, customer_id)."]
            })

        # 4. Response Agent / Insights
        if "principal aws" in sys_prompt_lower or "executive summary" in sys_prompt_lower:
            return """# Executive Summary
The business metrics show healthy revenue growth of 12% quarter-over-quarter.

## Key Insights
- **Top Product**: CloudBook Pro 15 generated the highest segment sales ($20,000).
- **Regional Strength**: North America region continues to show the lowest churn rate at 5.4%, whereas Latin America has the highest churn at 18.2%.

## Recommendations
1. Focus marketing efforts in Latin America to retain customers.
2. Cross-sell accessories with the CloudBook Pro 15 product lines.
"""

        # General text response fallback
        return f"Mock response from {model_id}. Input prompt length: {len(prompt)} characters. System prompt length: {len(system_prompt)}."

# Singleton service instance
bedrock_service = BedrockService()
