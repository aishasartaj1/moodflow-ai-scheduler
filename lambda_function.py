import boto3
import json
import uuid
import re
from datetime import datetime

bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
bedrock_agent = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

# Tables
sessions_table = dynamodb.Table('moodflow_sessions')
schedules_table = dynamodb.Table('moodflow_schedules')

# Constants
KB_ID = '9EGYZF82ME'
GUARDRAIL_ID = 'b4gnfb96cc52'
GUARDRAIL_VERSION = 'DRAFT'
MODEL_ID = 'us.anthropic.claude-3-5-sonnet-20241022-v2:0'
USER_ID = 'default_user'

def get_schedule_for_date(date_str):
    """Retrieve existing schedule for a specific date"""
    try:
        response = schedules_table.get_item(
            Key={
                'user_id': USER_ID,
                'schedule_date': date_str
            }
        )
        return response.get('Item', None)
    except Exception as e:
        print(f"DynamoDB get error: {e}")
        return None

def save_schedule_for_date(date_str, schedule_data, unscheduled_tasks, mood):
    """Save schedule to DynamoDB"""
    try:
        schedules_table.put_item(Item={
            'user_id': USER_ID,
            'schedule_date': date_str,
            'schedule': schedule_data,
            'unscheduled_tasks': unscheduled_tasks,
            'mood': mood,
            'last_updated': datetime.utcnow().isoformat()
        })
    except Exception as e:
        print(f"DynamoDB save error: {e}")

def query_knowledge_base(query):
    """Query Bedrock Knowledge Base"""
    try:
        response = bedrock_agent.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={'text': query},
            retrievalConfiguration={
                'vectorSearchConfiguration': {'numberOfResults': 3}
            }
        )
        results = []
        for result in response['retrievalResults']:
            results.append(result['content']['text'])
        return '\n\n'.join(results)
    except Exception as e:
        print(f"KB Error: {e}")
        return ""

def invoke_bedrock(user_message, date_str, start_time, end_time, kb_results):
    """Invoke Bedrock with context"""
    # Check if schedule exists for this date
    existing_schedule = get_schedule_for_date(date_str)
    
    has_existing = existing_schedule is not None
    existing_tasks = existing_schedule.get('schedule', []) if has_existing else []
    unscheduled = existing_schedule.get('unscheduled_tasks', []) if has_existing else []
    previous_mood = existing_schedule.get('mood', 'unknown') if has_existing else 'unknown'
    
    # Detect if this is a retrieval query
    is_retrieval = any(phrase in user_message.lower() for phrase in [
        'show me', 'show my', 'what is my', 'display', 'view my', 'see my',
        'show', 'view', 'display my', 'what\'s my', 'check my'
    ])
    
    # Check if user is asking about a different date
    date_in_message = re.search(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})', user_message.lower())
    
    if date_in_message and is_retrieval:
        month_str = date_in_message.group(1)
        day = date_in_message.group(2).zfill(2)
        year = date_str.split('-')[0]
        
        # Map month name to number
        month_map = {
            'jan': '01', 'january': '01',
            'feb': '02', 'february': '02',
            'mar': '03', 'march': '03',
            'apr': '04', 'april': '04',
            'may': '05',
            'jun': '06', 'june': '06',
            'jul': '07', 'july': '07',
            'aug': '08', 'august': '08',
            'sep': '09', 'september': '09',
            'oct': '10', 'october': '10',
            'nov': '11', 'november': '11',
            'dec': '12', 'december': '12'
        }
        
        month = month_map.get(month_str, '10')
        date_str = f"{year}-{month}-{day}"
        
        # Re-fetch schedule for the correct date
        existing_schedule = get_schedule_for_date(date_str)
        has_existing = existing_schedule is not None
        existing_tasks = existing_schedule.get('schedule', []) if has_existing else []
        unscheduled = existing_schedule.get('unscheduled_tasks', []) if has_existing else []
    
    # Parse times to calculate available hours
    start_match = re.search(r'(\d{1,2}):(\d{2})\s+([AP]M)', start_time)
    end_match = re.search(r'(\d{1,2}):(\d{2})\s*([AP]M)?', end_time)
    
    available_hours = 8.0  # default fallback
    if start_match and end_match:
        start_hour = int(start_match.group(1))
        start_min = int(start_match.group(2))
        start_ampm = start_match.group(3)
        
        end_hour = int(end_match.group(1))
        end_min = int(end_match.group(2))
        end_ampm = end_match.group(3) if end_match.group(3) else 'PM'
        
        # Convert to 24h format
        if start_ampm == 'PM' and start_hour != 12:
            start_hour += 12
        elif start_ampm == 'AM' and start_hour == 12:
            start_hour = 0
        
        if end_ampm == 'PM' and end_hour != 12:
            end_hour += 12
        elif end_ampm == 'AM' and end_hour == 12:
            end_hour = 0
            
        available_hours = (end_hour * 60 + end_min - start_hour * 60 - start_min) / 60
    else:
        print(f"Warning: Could not parse times. Start: {start_time}, End: {end_time}")
    
    system_prompt = f"""You are MoodFlow, an empathetic AI schedule planner.

Planning date: {date_str}
Start time: {start_time}
End time: {end_time}
Available hours: {available_hours:.1f}

EXISTING SCHEDULE FOR THIS DATE:
{json.dumps(existing_tasks) if has_existing else "No existing schedule"}

PREVIOUSLY DETECTED MOOD: {previous_mood}

PREVIOUSLY UNSCHEDULED TASKS:
{json.dumps(unscheduled) if unscheduled else "None"}

User's message: {user_message}

Planning knowledge from database:
{kb_results}

SPECIAL INSTRUCTION - RETRIEVAL QUERY:
{"User is asking to VIEW an existing schedule, not create a new one. Return ONLY the existing schedule without modifications. If no schedule exists for this date, return empty schedule array with message 'No schedule found for this date.' DO NOT attempt to create a new schedule." if is_retrieval else ""}

MOOD DETECTION RULES:
- If the user explicitly mentions their emotional state (e.g., "I'm tired", "feeling stressed", "I'm energized"), detect and use that new mood
- If the user does NOT mention their emotional state in this message, use the PREVIOUSLY DETECTED MOOD: {previous_mood}
- Only change mood when user explicitly expresses a different emotion
- Maintain mood continuity across conversation turns

CRITICAL SCHEDULING CONSTRAINTS:
1. The FIRST task in the schedule MUST start at or immediately after {start_time}
2. ALL tasks must fall between {start_time} and {end_time}
3. Schedule FORWARDS from start time, not backwards from end time or interruptions
4. If user mentions appointments/meetings (like "class at X"), incorporate them as BLOCKS within the schedule, not endpoints
5. Use ALL available time between start and end - do not leave large gaps at the beginning

WORKFLOW LOGIC:
1. If existing schedule exists and user just selected this date:
   - Show the existing schedule
   - Ask: "You have existing tasks for this day. Would you like to edit this schedule or start fresh?"
   - Set conversation_state to "awaiting_confirmation"
   
2. If user confirms editing (says yes/edit/continue):
   - Apply their requested changes (add/remove/reorder tasks)
   - Keep unscheduled_tasks intact unless they schedule them
   
3. If user provides NEW tasks:
   - Detect their mood from the message
   - Consult the planning knowledge from database to determine optimal scheduling for this mood
   - Parse tasks with durations
   - Apply emotion-aware patterns: task ordering, time blocks, break frequency based on knowledge base
   - Calculate if they fit in available time
   - Move overflow to unscheduled_tasks array
   - Ask: "These tasks don't fit today: [list]. Which date would you like to schedule them for?"
   
4. If user specifies a date for unscheduled tasks (e.g., "Oct 08"):
   - Extract the date
   - Return those tasks in reschedule_for_date object
   - Clear them from unscheduled_tasks
   
5. If user says "drop X" or "remove X":
   - Remove that task from schedule
   - Do NOT add to unscheduled

MANDATORY: Your scheduling decisions MUST be informed by the planning knowledge provided. Explain the reasoning in terms of benefits to the user, not which strategy you applied. Focus on WHY this schedule helps them given their emotional state.

OUTPUT JSON:
{{
  "mood_detected": "stressed|energized|anxious|focused|sad|tired|happy",
  "conversation_state": "awaiting_confirmation|editing|scheduling_new|asking_for_date",
  "schedule": [
    {{"time": "9:00-11:00 AM", "task": "Task name", "reasoning": "Natural explanation of why this time/order helps the user", "wellness_note": "Actionable tip"}}
  ],
  "unscheduled_tasks": [
    {{"task": "Task name", "estimated_duration": "2 hours"}}
  ],
  "reschedule_for_date": {{
    "date": "2025-10-08",
    "tasks": [{{"task": "Demo", "time": "9:00-11:00 AM"}}]
  }},
  "response_message": "Conversational response based on conversation_state"
}}"""

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2500,
        "messages": [{"role": "user", "content": system_prompt}]
    }
    
    response = bedrock_runtime.invoke_model(
        modelId=MODEL_ID,
        guardrailIdentifier=GUARDRAIL_ID,
        guardrailVersion=GUARDRAIL_VERSION,
        body=json.dumps(body)
    )
    
    response_body = json.loads(response['body'].read())
    return response_body['content'][0]['text']

def parse_response(text):
    """Extract JSON from Claude's response"""
    text = text.replace('```json', '').replace('```', '').strip()
    
    try:
        start = text.index('{')
        end = text.rindex('}') + 1
        json_only = text[start:end]
        return json.loads(json_only)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"JSON parse error: {e}")
        print(f"Raw text: {text}")
        return {
            "mood_detected": "unknown",
            "schedule": [],
            "response_message": "Error parsing schedule. Please try again."
        }

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        user_message = body['message']
        
        # Extract date: "Planning for Sunday, October 05, 2025"
        date_match = re.search(r'Planning for [^,]+, ([A-Za-z]+) (\d{1,2}), (\d{4})', user_message)
        
        if date_match:
            month_name = date_match.group(1)
            day = date_match.group(2).zfill(2)
            year = date_match.group(3)
            
            month_num = datetime.strptime(month_name, '%B').strftime('%m')
            date_str = f"{year}-{month_num}-{day}"
        else:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        # Extract times
        start_time_match = re.search(r'Start:\s+([^|]+)', user_message)
        end_time_match = re.search(r'End by:\s+([^\]]+)', user_message)
        
        start_time = start_time_match.group(1).strip() if start_time_match else "9:00 AM"
        end_time = end_time_match.group(1).strip() if end_time_match else "5:00 PM"
        
        # Query Knowledge Base
        kb_results = query_knowledge_base(user_message)
        
        # Call Bedrock
        response_text = invoke_bedrock(user_message, date_str, start_time, end_time, kb_results)
        
        # Parse response
        schedule_data = parse_response(response_text)
        
        # Save to DynamoDB
        save_schedule_for_date(
            date_str,
            schedule_data.get('schedule', []),
            schedule_data.get('unscheduled_tasks', []),
            schedule_data.get('mood_detected', 'unknown')
        )
        
        # Handle rescheduled tasks
        if 'reschedule_for_date' in schedule_data and schedule_data['reschedule_for_date']:
            reschedule_info = schedule_data['reschedule_for_date']
            future_date = reschedule_info.get('date')
            future_tasks = reschedule_info.get('tasks', [])
            
            if future_date and future_tasks:
                save_schedule_for_date(
                    future_date,
                    future_tasks,
                    [],
                    schedule_data.get('mood_detected', 'unknown')
                )
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps(schedule_data)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }