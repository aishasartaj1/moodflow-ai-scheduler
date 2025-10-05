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

## Demo
(https://drive.google.com/file/d/1KQXlgH4PKxn2bZ5pa9G7NLqHzgBtIurH/view?usp=sharing)
Hackathon
Built for UCLA x AWS Gen AI Hackathon 2025
**Upload files**

**On GitHub:**
- Click "Add file" → "Upload files"
- Drag: `app.py`, `requirements.txt`, `README.md`, `.gitignore`, `MoodFlow.pdf`
- **DO NOT upload:** Lambda code (has API keys), any credentials

**Or via command line:**
```bash
git clone https://github.com/YOUR_USERNAME/moodflow-ai-scheduler.git
cd moodflow-ai-scheduler
cp /path/to/app.py .
cp /path/to/requirements.txt .
git add .
git commit -m "Initial commit"
git push
