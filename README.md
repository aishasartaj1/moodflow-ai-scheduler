# MoodFlow: Emotion-Aware AI Scheduler

Emotion-aware task scheduling powered by AWS Bedrock, RAG, and DynamoDB.

## Features
- Mood detection from natural language
- Research-based scheduling strategies for 7 emotional states
- Multi-day planning with intelligent task rescheduling
- Conversational interface with schedule editing
- Wellness tips integrated into every task

## AWS Services
- **Amazon Bedrock** (Claude 3.5 Sonnet v2) - Conversational AI and planning logic
- **Bedrock Knowledge Base + RAG** - Evidence-based scheduling strategies
- **Bedrock Guardrails** - Safe, contextual recommendations
- **DynamoDB** - Schedule and session persistence
- **Lambda + API Gateway** - Serverless orchestration
- **OpenSearch Serverless** - Vector search for knowledge retrieval

## Architecture

```
User (Streamlit) → API Gateway → Lambda → Bedrock (Claude + KB + Guardrails)
                                    ↓
                              DynamoDB (schedules)
```

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

**Note:** You'll need to configure your own API Gateway endpoint in `app.py`:
```python
API_ENDPOINT = "your-api-gateway-url-here"
```

## Demo Video

[Watch the demo](https://drive.google.com/file/d/1KQXlgH4PKxn2bZ5pa9G7NLqHzgBtIurH/view?usp=sharing)

## Documentation

See [MoodFlow.pdf](MoodFlow.pdf) for complete project documentation and architecture details.

## Hackathon

Built for **UCLA x AWS Gen AI Hackathon 2025** by Aisha, Saloni, Dhwani

---

**Note:** Lambda code and AWS credentials are not included in this repository for security reasons. The application requires proper AWS configuration with Bedrock, Knowledge Base, and DynamoDB access.
