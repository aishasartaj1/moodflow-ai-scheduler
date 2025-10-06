# MoodFlow: Complete System Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Components](#architecture-components)
3. [Data Flow](#data-flow)
4. [User Interaction Flow](#user-interaction-flow)
5. [Technical Implementation](#technical-implementation)
6. [AWS Services Deep Dive](#aws-services-deep-dive)

---

## System Overview

MoodFlow is an emotion-aware AI task scheduler that uses conversational AI to detect user mood and generate optimized schedules based on psychological research. The system applies different scheduling strategies depending on emotional state (stressed, energized, anxious, focused, tired, sad, or happy).

**Core Innovation:** Retrieval-Augmented Generation (RAG) grounds scheduling decisions in evidence-based research rather than AI improvisation.

**Architecture Pattern:** Serverless microservices on AWS

---

## Architecture Components

### 1. Frontend: Streamlit Web Application

**File:** `app.py`

**Purpose:** User interface for conversational scheduling

**Key Features:**
- Date selector for planning specific days
- Start/end time configuration
- Chat interface for natural language interaction
- Schedule display with reasoning and wellness tips
- Schedule history viewer
- Quick date switching via "View Schedule" button

**Session State Management:**
```python
- session_id: Unique identifier for conversation continuity
- messages: Chat history
- current_schedule: Active schedule being displayed
- current_mood: Last detected emotional state
- unscheduled_tasks: Tasks that didn't fit in available time
- schedule_history: Last 10 schedule versions with timestamps
- current_schedule_date: Which date the displayed schedule is for
```

**User Input Processing:**
Streamlit formats messages with metadata:
```
"<user message>

[Planning for Wednesday, October 06, 2025 | Start: 9:00 AM | End by: 5:00 PM]"
```

This enhanced message is sent to the API, allowing Lambda to extract:
- Date being planned
- Available time window
- User's actual request

---

### 2. API Layer: Amazon API Gateway

**Configuration:**
- Type: REST API
- Endpoint: `/prod/chat`
- Method: POST
- CORS: Enabled for all origins (`*`)

**Request Format:**
```json
{
  "message": "I'm tired and need to finish documentation..."
}
```

**Query Parameters:**
- `session_id`: Used for potential future session tracking

**Response Format:**
```json
{
  "mood_detected": "tired",
  "conversation_state": "scheduling_new",
  "schedule": [
    {
      "time": "9:00-9:30 AM",
      "task": "Documentation - Part 1",
      "reasoning": "Short blocks accommodate tired state",
      "wellness_note": "Take breaks to rest your eyes"
    }
  ],
  "unscheduled_tasks": [],
  "reschedule_for_date": null,
  "response_message": "I've created a schedule..."
}
```

---

### 3. Orchestration Layer: AWS Lambda

**Function Name:** `moodflow-orchestrator`

**Runtime:** Python 3.x

**Timeout:** 30 seconds (Bedrock calls can take 10-15s)

**Memory:** 128 MB

**Key Responsibilities:**
1. Parse incoming user messages
2. Extract date, start time, end time
3. Query Bedrock Knowledge Base for relevant scheduling strategies
4. Construct structured prompts for Claude
5. Invoke Bedrock with guardrails
6. Parse JSON responses from Claude
7. Persist schedules to DynamoDB
8. Handle cross-date rescheduling

**Function Flow:**

```python
def lambda_handler(event, context):
    # 1. Extract message from API Gateway event
    user_message = json.loads(event['body'])['message']
    
    # 2. Parse date from message
    # "Planning for Wednesday, October 06, 2025" → "2025-10-06"
    date_str = extract_date(user_message)
    
    # 3. Parse times
    # "Start: 9:00 AM" → "9:00 AM"
    # "End by: 5:00 PM" → "5:00 PM"
    start_time, end_time = extract_times(user_message)
    
    # 4. Query Knowledge Base
    kb_results = query_knowledge_base(user_message)
    
    # 5. Invoke Bedrock
    response_text = invoke_bedrock(user_message, date_str, start_time, end_time, kb_results)
    
    # 6. Parse Claude's JSON response
    schedule_data = parse_response(response_text)
    
    # 7. Save to DynamoDB
    save_schedule_for_date(date_str, schedule_data['schedule'], 
                           schedule_data['unscheduled_tasks'], 
                           schedule_data['mood_detected'])
    
    # 8. Handle rescheduling to future dates
    if schedule_data.get('reschedule_for_date'):
        save_schedule_for_date(future_date, future_tasks, [], mood)
    
    # 9. Return to API Gateway
    return {
        'statusCode': 200,
        'body': json.dumps(schedule_data)
    }
```

---

### 4. Knowledge Storage: Amazon S3

**Bucket Purpose:** Store evidence-based scheduling knowledge

**Files:**

**1. mood-planning-strategies.txt**
```
Content: Strategies for 7 emotional states
- Task ordering patterns (easy→hard vs hard→easy)
- Time block durations (20 min to 180 min)
- Break frequencies (every 25 min to every 120 min)
- Break activities (grounding vs physical vs mental)
```

**2. task-completion-patterns.txt**
```
Content: Task-specific guidance by mood
- Documentation: effective when stressed if broken into chunks
- Code review: requires focused state, avoid when stressed
- Creative work: best when energized or happy
- Bug fixing: frustrating when stressed, good when focused
```

**3. wellness-guidelines.txt**
```
Content: Health-focused interventions
- Stress indicators and break requirements
- Anxiety management scheduling
- Burnout prevention patterns
- Fatigue management
- Mood-specific break recommendations
```

---

### 5. Vector Search: OpenSearch Serverless

**Purpose:** Enable semantic search over knowledge documents

**Process:**
1. Documents are chunked into smaller segments
2. Each chunk is converted to vector embedding
3. User query is converted to vector
4. Cosine similarity finds top 3 most relevant chunks

**Example:**
```
Query: "I'm stressed and need to finish documentation"

Retrieved chunks:
1. "STRESSED STATE PLANNING: 30-45 minute blocks..."
2. "Documentation: Works well when stressed if broken into sections..."
3. "STRESS INDICATORS: Mandatory breaks every 45-60 minutes..."
```

---

### 6. RAG Orchestration: Bedrock Knowledge Base

**Knowledge Base ID:** `YOUR_KNOWLEDGE_BASE_ID`

**Configuration:**
- Data source: S3 bucket
- Vector store: OpenSearch Serverless
- Embedding model: Amazon Titan Embeddings
- Chunk strategy: Default (300 tokens with 20% overlap)

**Query Process:**
```python
response = bedrock_agent.retrieve(
    knowledgeBaseId=KB_ID,
    retrievalQuery={'text': user_message},
    retrievalConfiguration={
        'vectorSearchConfiguration': {'numberOfResults': 3}
    }
)
```

**Returns:** Top 3 text chunks most relevant to the query

---

### 7. AI Brain: Amazon Bedrock (Claude 3.5 Sonnet v2)

**Model ID:** `us.anthropic.claude-3-5-sonnet-20241022-v2:0`

**Why Claude 3.5 Sonnet:**
- Superior reasoning for multi-step scheduling logic
- Excellent instruction following for complex prompts
- Natural conversation ability
- JSON output reliability
- Context window supports full scheduling context

**Prompt Structure:**

```python
system_prompt = f"""You are MoodFlow, an empathetic AI schedule planner.

Planning date: {date_str}
Start time: {start_time}
End time: {end_time}
Available hours: {available_hours}

EXISTING SCHEDULE FOR THIS DATE:
{existing_tasks}

PREVIOUSLY DETECTED MOOD: {previous_mood}

User's message: {user_message}

Planning knowledge from database:
{kb_results}

MOOD DETECTION RULES:
- If user explicitly mentions emotion, use that new mood
- If user does NOT mention emotion, use PREVIOUSLY DETECTED MOOD
- Maintain mood continuity across conversation turns

WORKFLOW LOGIC:
1. If existing schedule exists and user just selected date:
   - Show existing schedule
   - Ask if they want to edit or start fresh
   
2. If user confirms editing:
   - Apply requested changes
   - Keep unscheduled_tasks intact
   
3. If user provides NEW tasks:
   - Detect mood
   - Consult planning knowledge
   - Apply emotion-aware patterns
   - Schedule what fits
   - Move overflow to unscheduled_tasks
   
4. If user specifies date for unscheduled tasks:
   - Extract date
   - Return in reschedule_for_date object
   
5. If user says "drop X":
   - Remove from schedule

MANDATORY: Use planning knowledge to inform decisions. Explain WHY this helps their emotional state.

OUTPUT JSON:
{
  "mood_detected": "stressed|energized|anxious|focused|sad|tired|happy",
  "conversation_state": "awaiting_confirmation|editing|scheduling_new|asking_for_date",
  "schedule": [
    {"time": "9:00-11:00 AM", "task": "...", "reasoning": "...", "wellness_note": "..."}
  ],
  "unscheduled_tasks": [
    {"task": "...", "estimated_duration": "..."}
  ],
  "reschedule_for_date": {
    "date": "2025-10-08",
    "tasks": [...]
  },
  "response_message": "Conversational response"
}
"""
```

**Key Prompt Engineering Techniques:**

1. **Mood Persistence:** Instructs Claude to maintain mood across turns unless user explicitly changes it

2. **Retrieval Detection:** Distinguishes "show me my schedule" from "create a schedule"

3. **Date Extraction:** Can pull dates from natural language ("schedule for Oct 8")

4. **Knowledge Grounding:** Forces Claude to apply retrieved strategies, not improvise

5. **Structured Output:** Guarantees valid JSON for parsing

---

### 8. Safety Layer: Bedrock Guardrails

**Guardrail ID:** `YOUR_GUARDRAIL_ID`

**Version:** DRAFT

**Purpose:** Content filtering to ensure healthy recommendations

**Filters:**
- Blocks content encouraging overwork
- Prevents harmful productivity advice
- Ensures wellness-focused recommendations
- Maintains evidence-based guidance

**Implementation:**
```python
response = bedrock_runtime.invoke_model(
    modelId=MODEL_ID,
    guardrailIdentifier=GUARDRAIL_ID,
    guardrailVersion=GUARDRAIL_VERSION,
    body=json.dumps(body)
)
```

---

### 9. Data Persistence: DynamoDB

**Table 1: moodflow_schedules**

**Purpose:** Store schedules per user per date

**Schema:**
```
Partition Key: user_id (String) - "default_user" for hackathon
Sort Key: schedule_date (String) - "2025-10-06"

Attributes:
- schedule (List) - Array of task objects
- unscheduled_tasks (List) - Tasks that didn't fit
- mood (String) - Last detected mood for this date
- last_updated (String) - ISO timestamp
```

**Example Item:**
```json
{
  "user_id": "default_user",
  "schedule_date": "2025-10-06",
  "schedule": [
    {
      "time": "9:00-10:00 AM",
      "task": "Documentation",
      "reasoning": "Starting with writing when energy is fresh",
      "wellness_note": "Take breaks every 30 minutes"
    }
  ],
  "unscheduled_tasks": [],
  "mood": "tired",
  "last_updated": "2025-10-06T09:30:00Z"
}
```

**Table 2: moodflow_sessions**

**Purpose:** Track conversation context (currently minimal use)

**Schema:**
```
Partition Key: session_id (String)
Sort Key: timestamp (String)

Attributes:
- current_mood
- current_schedule
- last_update
```

---

## Data Flow

### Complete Request Flow (Step-by-Step)

**Scenario:** User says "I'm tired, need to write documentation for 2 hours"

**Step 1: User Input (Streamlit)**
```
User types: "I'm tired, need to write documentation for 2 hours"
Selected date: Oct 6, 2025
Start time: 9:00 AM
End time: 5:00 PM
```

**Step 2: Message Enhancement (Streamlit)**
```
Enhanced message:
"I'm tired, need to write documentation for 2 hours

[Planning for Wednesday, October 06, 2025 | Start: 9:00 AM | End by: 5:00 PM]"
```

**Step 3: HTTP POST (Streamlit → API Gateway)**
```http
POST YOUR_API_GATEWAY_URL

{
  "message": "I'm tired, need to write documentation for 2 hours\n\n[Planning for Wednesday, October 06, 2025 | Start: 9:00 AM | End by: 5:00 PM]"
}
```

**Step 4: Lambda Invocation (API Gateway → Lambda)**

Lambda receives the event and begins processing:

**Step 4a: Date Extraction**
```python
# Extract: "Wednesday, October 06, 2025" → "2025-10-06"
date_str = "2025-10-06"
```

**Step 4b: Time Extraction**
```python
start_time = "9:00 AM"
end_time = "5:00 PM"
available_hours = 8.0
```

**Step 4c: Knowledge Base Query (Lambda → Bedrock KB)**
```python
query = "I'm tired, need to write documentation for 2 hours"

# Bedrock KB searches OpenSearch
# Returns top 3 chunks:

kb_results = """
TIRED STATE PLANNING:
Primary strategy: Minimize cognitive load and prioritize recovery.
Task ordering: Low-effort tasks only, defer complex work to when rested
Time block duration: 20-30 minutes maximum for any focused work
Break frequency: 15-minute breaks every 30 minutes

Writing and Documentation:
When tired: Simple documentation updates acceptable. Avoid complex technical writing. Limit to 30 minutes.

TIREDNESS AND FATIGUE MANAGEMENT:
Fatigue signals: User reports being "tired"
Recommended interventions:
- Limit work blocks to 20-30 minutes maximum
- Defer all complex cognitive tasks to when well-rested
"""
```

**Step 4d: Check Existing Schedule (Lambda → DynamoDB)**
```python
# Query DynamoDB for existing schedule for 2025-10-06
existing_schedule = get_schedule_for_date("2025-10-06")

# Returns: None (no existing schedule)
has_existing = False
previous_mood = "unknown"
```

**Step 4e: Construct Bedrock Prompt**
```python
system_prompt = """
You are MoodFlow, an empathetic AI schedule planner.

Planning date: 2025-10-06
Start time: 9:00 AM
End time: 5:00 PM
Available hours: 8.0

EXISTING SCHEDULE FOR THIS DATE:
No existing schedule

PREVIOUSLY DETECTED MOOD: unknown

User's message: I'm tired, need to write documentation for 2 hours

Planning knowledge from database:
[... kb_results from Step 4c ...]

MOOD DETECTION RULES:
- If user explicitly mentions emotion, use that new mood
- User said "I'm tired" → detect mood as "tired"

WORKFLOW LOGIC:
3. User provides NEW tasks:
   - Detect mood: "tired"
   - Consult planning knowledge: 20-30 min blocks, frequent breaks
   - Parse tasks: "documentation for 2 hours"
   - Apply tired-state patterns
   - Schedule what fits in 8 hours
   
OUTPUT JSON:
{ ... }
"""
```

**Step 4f: Invoke Bedrock (Lambda → Bedrock Claude)**
```python
response = bedrock_runtime.invoke_model(
    modelId="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    guardrailIdentifier="YOUR_GUARDRAIL_ID",
    guardrailVersion="DRAFT",
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2500,
        "messages": [
            {"role": "user", "content": system_prompt}
        ]
    })
)
```

**Step 4g: Claude Processes (Bedrock)**

Claude's reasoning:
1. Detects mood: "tired" (explicit mention)
2. Retrieves strategy from knowledge: 20-30 min blocks, frequent breaks
3. User wants 2 hours documentation
4. Breaks into 4 × 30-minute blocks with 15-min breaks between
5. Total time: 2h work + 45min breaks = 2h45min
6. Fits easily in 8-hour day (9 AM - 5 PM)
7. Adds wellness notes about hydration, rest

Claude returns JSON:
```json
{
  "mood_detected": "tired",
  "conversation_state": "scheduling_new",
  "schedule": [
    {
      "time": "9:00-9:30 AM",
      "task": "Documentation - Part 1",
      "reasoning": "Breaking into short 30-minute blocks to accommodate tired state",
      "wellness_note": "Take frequent breaks. Stay hydrated."
    },
    {
      "time": "9:30-9:45 AM",
      "task": "Break",
      "reasoning": "Recovery period to maintain clarity",
      "wellness_note": "Step away from screen, rest your eyes"
    },
    {
      "time": "9:45-10:15 AM",
      "task": "Documentation - Part 2",
      "reasoning": "Continuing in manageable chunks",
      "wellness_note": "If feeling very tired, consider stopping"
    },
    {
      "time": "10:15-10:30 AM",
      "task": "Break",
      "reasoning": "Mandatory rest when fatigued",
      "wellness_note": "Light snack and water recommended"
    },
    {
      "time": "10:30-11:00 AM",
      "task": "Documentation - Part 3",
      "reasoning": "Third focused block",
      "wellness_note": "Monitor energy levels closely"
    },
    {
      "time": "11:00-11:15 AM",
      "task": "Break",
      "reasoning": "Recovery period",
      "wellness_note": "Brief walk if possible"
    },
    {
      "time": "11:15-11:45 AM",
      "task": "Documentation - Part 4",
      "reasoning": "Final documentation block completes 2 hours",
      "wellness_note": "You've completed your goal - rest afterward"
    }
  ],
  "unscheduled_tasks": [],
  "reschedule_for_date": null,
  "response_message": "I've scheduled your 2 hours of documentation work in four 30-minute blocks with recovery breaks between each. Since you're tired, I've kept the blocks short to prevent exhaustion. You'll complete the documentation by 11:45 AM, leaving plenty of time for rest or lighter tasks in the afternoon."
}
```

**Step 4h: Save to DynamoDB (Lambda → DynamoDB)**
```python
schedules_table.put_item(Item={
    'user_id': 'default_user',
    'schedule_date': '2025-10-06',
    'schedule': [...schedule array...],
    'unscheduled_tasks': [],
    'mood': 'tired',
    'last_updated': '2025-10-06T09:15:00Z'
})
```

**Step 5: Return to API Gateway (Lambda → API Gateway)**
```json
{
  "statusCode": 200,
  "headers": {
    "Access-Control-Allow-Origin": "*",
    "Content-Type": "application/json"
  },
  "body": "{\"mood_detected\": \"tired\", ...}"
}
```

**Step 6: Display in UI (API Gateway → Streamlit)**

Streamlit receives the response:
```python
data = response.json()

# Store in session state
st.session_state.current_schedule = data['schedule']
st.session_state.current_mood = 'tired'

# Add to history
st.session_state.schedule_history.append({
    'timestamp': datetime.now(),
    'date': selected_date,
    'schedule': data['schedule'],
    'mood': 'tired'
})

# Display
st.header("📅 Your Optimized Schedule for Wednesday, October 06, 2025")
st.dataframe(df)  # Shows the schedule table
st.info("Planning optimized for: 😴 Tired mood")
```

**User sees:**
- Chat message from assistant explaining the schedule
- Table showing 4 documentation blocks with breaks
- Mood indicator: 😴 Tired
- Wellness tips for each task

---

## User Interaction Flow

### Scenario 1: Creating First Schedule

```
User: "I'm stressed, need to finish project proposal (3h) and email responses (1h)"

System:
1. Detects mood: stressed
2. Retrieves stressed-state strategy: 30-45 min blocks, easy→hard→easy ordering
3. Calculates: 4 hours work needed
4. Applies pattern:
   - Email (1h) first - easy warmup
   - Project proposal (3h) - hardest task
   - Split proposal into 3×45min blocks with breaks
5. Generates schedule
6. Saves to DynamoDB

Response: "I've scheduled your tasks with your stress in mind. Starting with emails as a warmup, then tackling the proposal in three 45-minute blocks with breaks between."
```

### Scenario 2: Editing Existing Schedule

```
User: (next message) "Actually, can you swap the order? I want to do the proposal first"

System:
1. Retrieves existing schedule from DynamoDB
2. Detects: editing request
3. Maintains mood: still "stressed"
4. Reorders: Proposal first, emails last
5. Updates DynamoDB

Response: "I've moved the project proposal to the morning. You'll tackle it first while your energy is fresh, then handle emails later."
```

### Scenario 3: Cross-Date Scheduling

```
User: "These tasks won't fit. Can you schedule the demo recording for Oct 8 instead?"

System:
1. Detects: rescheduling request
2. Extracts date: "Oct 8" → "2025-10-08"
3. Removes "demo recording" from Oct 6 schedule
4. Creates/updates Oct 8 schedule with demo recording
5. Saves both dates to DynamoDB

Response: "I've moved the demo recording to October 8th. Your October 6th schedule is now lighter, and I've created a schedule for October 8th starting with the demo."
```

### Scenario 4: Viewing Different Dates

```
User: (clicks date picker, selects Oct 8, clicks "View Schedule" button)

System:
1. Streamlit sends: "show me schedule [Planning for October 08, 2025]"
2. Lambda detects: retrieval query (contains "show me")
3. Queries DynamoDB for 2025-10-08
4. Returns existing schedule
5. Does NOT invoke Bedrock (just retrieval)

Display: Shows Oct 8 schedule with demo recording
```

### Scenario 5: Mood Persistence

```
User: (on Oct 7, without mentioning mood) "I need to write documentation for 1 hour and attend a meeting at 2 PM"

System:
1. Checks DynamoDB for Oct 7: no existing schedule
2. Previous mood: "stressed" (from Oct 6)
3. Applies MOOD PERSISTENCE rule
4. Uses "stressed" mood for scheduling
5. Generates schedule with 30-45 min blocks

Response: "Since you're still feeling stressed, I've kept the work blocks short..."
```

---

## Technical Implementation Details

### Date Parsing Algorithm

```python
def extract_date(user_message):
    # Pattern: "Planning for Wednesday, October 06, 2025"
    pattern = r'Planning for [^,]+, ([A-Za-z]+) (\d{1,2}), (\d{4})'
    match = re.search(pattern, user_message)
    
    if match:
        month_name = match.group(1)  # "October"
        day = match.group(2).zfill(2)  # "06"
        year = match.group(3)  # "2025"
        
        # Convert month name to number
        month_num = datetime.strptime(month_name, '%B').strftime('%m')  # "10"
        
        return f"{year}-{month_num}-{day}"  # "2025-10-06"
    
    return datetime.now().strftime('%Y-%m-%d')  # Fallback
```

### Time Calculation

```python
def calculate_available_hours(start_time, end_time):
    # Parse "9:00 AM" and "5:00 PM"
    start_match = re.search(r'(\d{1,2}):(\d{2})\s+([AP]M)', start_time)
    end_match = re.search(r'(\d{1,2}):(\d{2})\s*([AP]M)?', end_time)
    
    start_hour = int(start_match.group(1))
    start_min = int(start_match.group(2))
    start_ampm = start_match.group(3)
    
    end_hour = int(end_match.group(1))
    end_min = int(end_match.group(2))
    end_ampm = end_match.group(3) or 'PM'
    
    # Convert to 24-hour
    if start_ampm == 'PM' and start_hour != 12:
        start_hour += 12
    elif start_ampm == 'AM' and start_hour == 12:
        start_hour = 0
    
    if end_ampm == 'PM' and end_hour != 12:
        end_hour += 12
    elif end_ampm == 'AM' and end_hour == 12:
        end_hour = 0
    
    # Calculate hours
    total_minutes = (end_hour * 60 + end_min) - (start_hour * 60 + start_min)
    return total_minutes / 60
```

### Retrieval Detection

```python
def is_retrieval_query(user_message):
    retrieval_phrases = [
        'show me', 'show my', 'what is my', 
        'display', 'view my', 'see my',
        'show', 'view', 'check my'
    ]
    
    return any(phrase in user_message.lower() for phrase in retrieval_phrases)
```

### JSON Parsing with Error Handling

```python
def parse_response(text):
    # Remove markdown code blocks
    text = text.replace('```json', '').replace('```', '').strip()
    
    try:
        # Find JSON boundaries
        start = text.index('{')
        end = text.rindex('}') + 1
        json_only = text[start:end]
        
        return json.loads(json_only)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"JSON parse error: {e}")
        print(f"Raw text: {text}")
        
        # Return minimal valid structure
        return {
            "mood_detected": "unknown",
            "schedule": [],
            "response_message": "Error parsing schedule. Please try again."
        }
```

---

## AWS Services Deep Dive

### Amazon Bedrock Configuration

**Model Access:**
Must request access to Claude 3.5 Sonnet v2 in AWS Console:
1. Bedrock → Model access
2. Request access to Anthropic models
3. Wait for approval (usually instant)

**Invocation Parameters:**
```python
{
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 2500,  # Enough for full schedule JSON
    "messages": [
        {"role": "user", "content": system_prompt}
    ]
}
```

**Why these settings:**
- `max_tokens: 2500`: Schedules can be large (10+ tasks with reasoning)
- Single-turn conversation: Each request is independent
- System instructions in user message: Bedrock API doesn't have separate system param

### Knowledge Base Setup

**Creation Steps:**
1. Create S3 bucket
2. Upload 3 .txt files
3. Create Knowledge Base in Bedrock console
4. Select S3 as data source
5. Choose embedding model (Titan Embeddings)
6. Create OpenSearch Serverless collection (automatic)
7. Sync data source (indexes documents)

**Chunking Strategy:**
- Default: 300 tokens per chunk
- 20% overlap between chunks
- Preserves context across chunk boundaries

**Retrieval Configuration:**
```python
retrievalConfiguration={
    'vectorSearchConfiguration': {
        'numberOfResults': 3  # Top 3 most relevant chunks
    }
}
```

### DynamoDB Table Design

**Why this schema:**
```
Partition key: user_id
Sort key: schedule_date
```

**Benefits:**
- Query all schedules for a user: `user_id = "default_user"`
- Get specific date: `user_id = "default_user" AND schedule_date = "2025-10-06"`
- Efficient single-item lookups
- Scalable to multi-user (change user_id from "default_user")

**Capacity Mode:** On-demand (pay per request)

**Why on-demand:**
- Unpredictable traffic during hackathon
- No need to provision capacity
- Cost-effective for low volume

### Lambda Optimization

**Cold Start Mitigation:**
- Keep function warm during demos (invoke every 5 minutes)
- Import only necessary libraries
- Reuse boto3 clients (defined outside handler)

**Timeout Strategy:**
- 30 seconds allows for:
  - Knowledge Base query: 2-3s
  - Bedrock invocation: 10-15s
  - DynamoDB operations: <1s
  - Buffer for retries

**Error Handling:**
```python
try:
    # Main logic
except Exception as e:
    print(f"Error: {str(e)}")
    traceback.print_exc()  # Full stack trace in CloudWatch
    return {
        'statusCode': 500,
        'body': json.dumps({'error': str(e)})
    }
```

---

## Key Design Decisions

### 1. Why RAG Instead of Fine-Tuning?

**Advantages of RAG:**
- Update knowledge without retraining (just update S3 files)
- Explainable: Can trace which knowledge influenced decisions
- Cost-effective: No fine-tuning compute needed
- Flexible: Easy to add new emotional states or strategies

**Trade-offs:**
- Retrieval latency (2-3s)
- Limited to knowledge in documents
- Requires good document structure

### 2. Why Serverless Architecture?

**Benefits:**
- Zero server management
- Auto-scaling (handles 1 or 1000 users)
- Pay only for usage
- Fast deployment

**Limitations:**
- Cold starts (mitigated with warm-up)
- Vendor lock-in to AWS
- Debugging requires CloudWatch

### 3. Why DynamoDB Over RDS?

**DynamoDB advantages:**
- Serverless (matches Lambda)
- Single-millisecond latency
- Simple schema (key-value)
- No connection pooling needed

**When RDS would be better:**
- Complex queries across dates
- Multi-user analytics
- Relational data (teams, organizations)

### 4. Why Streamlit Over React?

**Streamlit benefits:**
- Rapid prototyping (100 lines vs 500+)
- Python-native (matches Lambda)
- Built-in state management
- Good for demos/MVPs

**Production considerations:**
- React would be better for production (faster, more flexible)
- Streamlit is demo-focused

---

## Performance Characteristics

**Typical Response Times:**

```
User sends message
  ↓ 50-100ms (API Gateway)
Lambda cold start: 1-2s (warm: 10ms)
  ↓ 2-3s (Knowledge Base query)
  ↓ 10-15s (Bedrock invocation)
  ↓ 100ms (DynamoDB save)
  ↓ 50ms (Response to client)
─────────────────────────────
Total: 13-20s (cold), 12-18s (warm)
```

**Bottlenecks:**
1. Bedrock invocation (10-15s) - Cannot optimize, model processing time
2. Knowledge Base query (2-3s) - Could cache common queries
3. Lambda cold start (1-2s) - Keep warm with periodic invokes

**Scalability:**
- Bedrock: 100+ requests/second (AWS limit)
- DynamoDB: Unlimited (on-demand mode)
- Lambda: 1000 concurrent executions (default)
- API Gateway: 10,000 requests/second

---

## Error Handling & Resilience

### Common Errors and Solutions

**1. JSON Parse Error**
```
Cause: Claude returns markdown-wrapped JSON
Solution: Strip ```json and ``` before parsing
```

**2. Knowledge Base Empty Results**
```
Cause: Query too specific, no matching chunks
Solution: Use broader queries, always include default strategies
```

**3. Timeout**
```
Cause: Bedrock took >30s
Solution: Increase Lambda timeout, retry with exponential backoff
```

**4. DynamoDB Throttling**
```
Cause: Burst traffic exceeds on-demand limits
Solution: Implement exponential backoff, add caching layer
```

### Monitoring

**CloudWatch Logs:**
- Lambda execution logs
- Error stack traces
- Performance metrics

**CloudWatch Metrics:**
- Lambda duration
- Lambda errors
- API Gateway 4xx/5xx
- DynamoDB consumed capacity

---

## Security Considerations

**Current State (Hackathon):**
- API Gateway has no authentication
- Single user ("default_user")
- Credentials hardcoded in Lambda

**Production Requirements:**
- API Gateway: AWS IAM auth or API keys
- Lambda: Use AWS Secrets Manager for IDs
- DynamoDB: Enable encryption at rest
- Multi-tenancy: Real user_id from auth token
- HTTPS only (already enforced by API Gateway)

---

## Cost Analysis

**Estimated Costs (100 users, 10 requests/day each):**

```
Service                   Volume              Cost/Month
─────────────────────────────────────────────────────────
Bedrock (Claude)          30K requests        $3.00
Knowledge Base            30K queries         $1.50
OpenSearch Serverless     1 OCU              $24.00
Lambda                    30K invocations     $0.06
API Gateway              30K requests         $0.30
DynamoDB                 60K operations       $0.25
S3                       3 files (1KB)        $0.01
─────────────────────────────────────────────────────────
Total:                                        ~$29/month
```

**Cost drivers:**
- OpenSearch Serverless: Fixed $24/month minimum
- Bedrock: Pay per token (input + output)
- Everything else: Negligible at this scale

**Optimization:**
- Cache common queries (reduce Bedrock calls)
- Use Aurora Serverless instead of OpenSearch for smaller scale
- Batch DynamoDB writes

---

## Future Enhancements

### 1. Google Calendar MCP Integration

**Implementation:**
```python
# Lambda queries Google Calendar MCP server
calendar_events = mcp_client.get_events(date_str)

# Include in Bedrock prompt:
f"""
Existing calendar commitments:
{calendar_events}

Schedule around these existing events.
"""

# After schedule generation:
mcp_client.create_events(schedule)
```

**Benefits:**
- Automatic conflict detection
- Sync to user's actual calendar
- Pull real commitments into planning

### 2. Wearable Integration

**Data sources:**
- Heart rate variability (stress indicator)
- Sleep quality (fatigue indicator)
- Activity levels (energy indicator)

**Enhanced mood detection:**
```python
biometric_data = get_wearable_data(user_id)

# Override user-stated mood if biometrics show high stress
if biometric_data['hrv'] < threshold:
    actual_mood = "stressed"
```

### 3. Long-term Analytics

**Track patterns:**
- Best productivity times per mood
- Task completion rates by emotional state
- Mood trends over time

**Personalized strategies:**
- Learn individual patterns
- Adjust strategies per user
- Predict mood from schedule history

---

## Conclusion

MoodFlow demonstrates a production-ready serverless AI application on AWS, combining:
- **Conversational AI** (Bedrock Claude)
- **Retrieval-Augmented Generation** (Knowledge Base + OpenSearch)
- **Safety guardrails** (Bedrock Guardrails)
- **Scalable persistence** (DynamoDB)
- **Serverless orchestration** (Lambda + API Gateway)

The architecture is modular, scalable, and cost-effective, ready to expand from hackathon demo to production system with proper authentication, multi-tenancy, and monitoring.
