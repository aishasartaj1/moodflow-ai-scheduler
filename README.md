# MoodFlow: Emotion-Aware AI Scheduler

Emotion-aware task scheduling powered by AWS Bedrock, RAG, and DynamoDB.

## Features
- Mood detection from natural language
- Research-based scheduling strategies
- Multi-day planning
- Conversational interface

## AWS Services
- Amazon Bedrock (Claude 3.5 Sonnet v2)
- Bedrock Knowledge Base + RAG
- Bedrock Guardrails
- DynamoDB
- Lambda + API Gateway
- OpenSearch Serverless

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
