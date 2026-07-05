# AWS Deployment & Architecture Guide

This document describes the enterprise deployment patterns, security zones, and scalability designs of the Text-to-SQL Analytics Agent Platform.

---

## 1. Local Containerized Stack
When running locally via `docker compose up`, the architecture simulates real AWS capabilities:

```
[Business User] 
       │ (HTTP/8501)
       ▼
┌───────────────────────── Streamlit Container ─────────────────────────┐
│ renders UI, captures user prompt, displays charts, displays agent traces│
└──────────────────────────────────┬────────────────────────────────────┘
                                   │ (HTTP/8000)
                                   ▼
┌────────────────────────── FastAPI Container ──────────────────────────┐
│ Runs endpoints, executes supervisor, routes requests to sub-agents   │
└───────────────────────┬──────────┬──────────┬─────────────────────────┘
                        │          │          │
                        ▼          ▼          ▼
             ┌──────────┐┌─────────┐┌─────────┐
             │ Postgres ││ Langfuse││ Local   │
             │(pgvector)││ (Traces)││ Parquets│
             │ [5432]   ││ [3000]  ││(DuckDB) │
             └──────────┘└─────────┘└─────────┘
```

---

## 2. Production AWS Deployment Architecture
In a production-ready AWS environment, the architecture maps to AWS-native managed services:

```
                                [ Business User ]
                                        │ (HTTPS)
                                        ▼
                                 [ Route 53 DNS ]
                                        │
                                        ▼
                              [ Application Load Balancer ]
                                        │
                         ┌──────────────┴──────────────┐
                         ▼                             ▼
                [ stream.enterprise.com ]     [ api.enterprise.com ]
                ┌───────────────────────┐     ┌───────────────────────┐
                │   Streamlit Web App   │     │   FastAPI Agent App   │
                │     (ECS Fargate)     │     │     (ECS Fargate)     │
                └───────────────────────┘     └───────────┬───────────┘
                                                          │
                         ┌────────────────────────────────┼────────────────────────────────┐
                         ▼                                ▼                                ▼
               [ Amazon RDS Postgres ]             [ Amazon Athena ]                [ Amazon Bedrock ]
               │ pgvector glossary RAG │           │   Query engine  │                │ Sonnet, Nova,   │
               │   and user sessions   │           └──────────────┬──┘                │ Titan Embeddings│
               └───────────────────────┘                          │                   └─────────────────┘
                                                                  ▼
                                                          [ Amazon S3 Bucket ]
                                                          │ Raw Parquet files│
                                                          │ & Athena results │
                                                          └──────────────────┘
```

### Components
1. **Application Load Balancer (ALB)**: Routes public web requests to Fargate target groups. Enforces TLS termination.
2. **Cognito User Pool**: Manages authentication, MFA, and user token issuances. Linked directly to the FastAPI bearer token validation schemes.
3. **ECS Fargate**: Serves as the compute layer, running stateless Docker containers for the backend API and Streamlit.
4. **Amazon RDS PostgreSQL (with pgvector)**: Managed relational database storing glossary chunks, KPI definitions, and semantic vector indexes.
5. **Amazon Athena**: Serverless query engine mapping local schema queries to Parquet files stored in S3.
6. **Amazon Bedrock**: Serves foundational LLMs (Claude 3.5 Sonnet, Claude 3 Opus, Nova Pro) and embeddings (Titan Text Embeddings) over secure IAM endpoints.
7. **Secrets Manager**: Rotates database credentials and JWT security key parameters automatically.
8. **CloudWatch & X-Ray**: Exposes structured container logs, tracks CPU/memory usage, and visualizes network call latency.
