# Security & Cost Estimation Guide

This guide details the security defenses and pricing models for the Text-to-SQL Analytics Agent Platform.

---

## 1. Security Architecture & Controls

We implement security layers at all API endpoints to protect sensitive customer information and shield backend models from attack.

```
Incoming Request
  │
  ▼
[ Rate Limiter ]  ──> Exceeds 60 req/min ──> Block with HTTP 429
  │
  ▼
[ JWT & RBAC ] ──> Invalid Token or Unauthorized Role ──> Block with HTTP 401/403
  │
  ▼
[ PII Sanitization ] ──> Regex scrubbing (Emails, Phones, SSNs)
  │
  ▼
[ Prompt Injection Scan ] ──> System Instruction Override Check ──> Block with HTTP 400
  │
  ▼
[ SQL Validation & Review ] ──> Block DDL/DML, check schemas ──> Reject Query
  │
  ▼
Processed Safe Pipeline
```

### Key Security Implementations
- **Role-Based Access Control**:
  - `Viewer`: Can execute safe queries, browse metrics, view dashboards.
  - `Admin`: Full privileges, including `/ingest` configuration and metadata alterations.
- **SQL Sanitization**: Standard Presto parsing scans queries before execution. Any keyword like `DROP`, `DELETE`, `UPDATE`, `ALTER`, `CREATE` is rejected, preventing data loss or alteration.
- **Audit Logging**: Write transaction records mapping `timestamp`, `user`, `action`, `details`, and `status` to JSON stdout to establish full security compliance.

---

## 2. Amazon Bedrock Cost Estimation

The system tracks Bedrock consumption metrics to estimate operational budgets.

### Model Pricing (per 1,000,000 tokens)
- **Claude 3.5 Sonnet**: \$3.00 Input, \$15.00 Output.
- **Claude 3 Opus**: \$15.00 Input, \$75.00 Output.
- **Amazon Nova Pro**: \$0.80 Input, \$3.20 Output.
- **Amazon Titan Embeddings**: \$0.10 Input (Free Output).

### Execution Math Example
If a customer asks: *"Compare Q1 and Q2 sales metrics by region"*
1. **RAG Step**: Titan Embedding computes prompt vector (~15 tokens) = **\$0.0000015**
2. **SQL Generation Step**: (Claude 3.5 Sonnet) Input context with glossary/schema (~1,500 tokens), Output SQL (~150 tokens)
   - Input: 1,500 * (\$3.00 / 1,000,000) = \$0.00450
   - Output: 150 * (\$15.00 / 1,000,000) = \$0.00225
   - Subtotal: **\$0.00675**
3. **SQL Review Step**: (Claude 3.5 Sonnet) Input SQL (~250 tokens), Output JSON (~100 tokens)
   - Input: 250 * (\$3.00 / 1,000,000) = \$0.00075
   - Output: 100 * (\$15.00 / 1,000,000) = \$0.00150
   - Subtotal: **\$0.00225**
4. **Insights Summarization Step**: (Claude 3.5 Sonnet) Input SQL & query records (~1,000 tokens), Output report (~400 tokens)
   - Input: 1,000 * (\$3.00 / 1,000,000) = \$0.00300
   - Output: 400 * (\$15.00 / 1,000,000) = \$0.00600
   - Subtotal: **\$0.00900**

**Total Estimated Transaction Cost**: **\$0.0180015 USD**
The Streamlit sidebar compiles this cost metrics logic in real time!
