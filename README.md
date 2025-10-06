# 🧠 MoodFlow: Emotion-Aware AI Scheduler

**Smart, emotion-aware task scheduling powered by AWS Bedrock, RAG, and DynamoDB.**  
MoodFlow brings emotional intelligence to productivity — aligning your daily plans with your current mood and cognitive state.

---

## 🚀 Features

- 💬 **Mood Detection** — Understands emotional tone from natural language input.  
- 🧩 **Evidence-Based Scheduling** — Uses research-backed strategies for seven emotional states.  
- 🗓️ **Dynamic Multi-Day Planning** — Intelligently reschedules and prioritizes tasks.  
- 🤖 **Conversational Interface** — Edit or adjust your plan via natural dialogue.  
- 🌱 **Wellness Integration** — Suggests breaks, mindfulness tips, and burnout-prevention actions.

---

## ☁️ AWS Services Used

| Service | Role |
|----------|------|
| **Amazon Bedrock (Claude 3.5 Sonnet v2)** | Conversational AI and planning logic |
| **Bedrock Knowledge Base + RAG** | Retrieval of research-backed scheduling strategies |
| **Bedrock Guardrails** | Contextual and safe recommendation filtering |
| **Amazon S3** | Storage for knowledge base documents |
| **Amazon OpenSearch Serverless** | Vector embeddings and semantic search |
| **Amazon DynamoDB** | Session and schedule persistence |
| **AWS Lambda + API Gateway** | Serverless orchestration layer |

---

## 🧭 Architecture Overview

```plaintext
┌─────────────┐
│  Streamlit  │
│     UI      │
└──────┬──────┘
       │ HTTPS
       ▼
┌─────────────────┐
│  API Gateway    │
└──────┬──────────┘
       │ Invoke
       ▼
┌──────────────────────────────────────┐
│           Lambda Function            │
│  • Parse user message                │
│  • Query Knowledge Base              │
│  • Invoke Bedrock with context       │
│  • Save schedules                    │
└───┬────────┬──────────┬──────────┬───┘
    │        │          │          │
    ▼        ▼          ▼          ▼
┌────────┐ ┌─────────┐ ┌────────┐ ┌──────────┐
│   S3   │→│Knowledge│ │Bedrock │ │ DynamoDB │
│ Bucket │ │  Base   │ │Claude  │ │          │
│        │ │    +    │ │   +    │ │schedules │
│3 docs  │ │OpenSearch│Guardrails│ │sessions  │
└────────┘ └─────────┘ └────────┘ └──────────┘
```

---

## 📚 Knowledge Base Documents

The **RAG (Retrieval-Augmented Generation)** system grounds scheduling logic in behavioral science documents stored in **S3** and indexed using **OpenSearch Serverless**.

| Document | Description |
|-----------|-------------|
| **`mood-planning-strategies.txt`** | Defines task ordering, duration, and break frequency for seven moods — *stressed, energized, anxious, focused, tired, sad, happy*. |
| **`task-completion-patterns.txt`** | Captures how task performance varies across moods (e.g., debugging when energized, writing when calm). |
| **`wellness-guidelines.txt`** | Outlines burnout prevention, mood recovery, and wellness recommendations. |

When a user mentions their mood, the **Lambda function** queries OpenSearch for the top 3 most semantically relevant strategy chunks. **Claude** then synthesizes a personalized schedule grounded in those insights.

---

## 🧑‍💻 Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

**Configuration:**  
Update your API endpoint in `app.py` before running:

```python
API_ENDPOINT = "your-api-gateway-url-here"
```

---

## 🎥 Demo Video

📺 [Watch the Demo](https://drive.google.com/file/d/12ZSG9apXDj1MmSIsy1X6eimYRkP0Udoy/view?usp=sharing)

---

## 📄 Documentation

For full technical details and system diagrams, see:  
📘 [MoodFlow.pdf](MoodFlow.pdf)

---

## 🔮 Future Improvements

- **🗓️ Google Calendar Integration (MCP Server)** — Auto-sync schedules, detect conflicts, and import existing events.  
- **⌚ Wearable Device Integration** — Incorporate biometric data (heart rate, sleep quality) for enhanced mood inference.  
- **📈 Productivity Pattern Analysis** — Track mood–performance correlations over time.  
- **👥 Team Scheduling** — Extend emotion-aware planning to group or team contexts.  
- **📱 Mobile Application** — Build native iOS/Android versions for mobile schedule updates.

---

## 🏆 Hackathon

Built for **UCLA Bruin AI × AWS Gen AI Hackathon 2025**  
👩‍💻 

---

> ⚠️ **Note:** Lambda source code and AWS credentials are intentionally excluded for security reasons.  
> The application requires proper AWS setup with Bedrock, Knowledge Base, and DynamoDB access.
