import os

class Config:
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOCAL_DEV: bool = os.getenv("LOCAL_DEV", "true").lower() == "true"
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
    
    # Athena Configuration
    ATHENA_DATABASE: str = os.getenv("ATHENA_DATABASE", "analytics_db")
    ATHENA_S3_OUTPUT: str = os.getenv("ATHENA_S3_OUTPUT", "s3://my-athena-query-results-bucket/uncategorized/")
    AWS_DEFAULT_REGION: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    
    # LLM Settings
    BEDROCK_MODEL_ID: str = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
    MOCK_LLM: bool = os.getenv("MOCK_LLM", "false").lower() == "true"
    
    # Security Configuration
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super-secret-enterprise-key-do-not-share-12345")
    REQUIRE_AUTH: bool = os.getenv("REQUIRE_AUTH", "false").lower() == "true"
    RATE_LIMIT_MAX: int = int(os.getenv("RATE_LIMIT_MAX", "60"))
    
    # Langfuse Observability
    LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

settings = Config()
