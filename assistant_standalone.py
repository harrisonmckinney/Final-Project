import os
import time
import gradio as gr
from openai import OpenAI, AzureOpenAI
from dotenv import load_dotenv
import pprint
import tempfile
import json
import traceback
import http.client
# Import from practical_ai_azure_keyvault
from practical_ai_azure_keyvault import initialize_app, AIConfig

client=None
assistantID=None

# Load environment variables
def gradio_init():
    global client,assistantID
    load_dotenv()

    # Check for API key
    if os.getenv("OPENAI_API_KEY"):
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    else:
        try:
            initialize_app("ClassWeatherApi")  # Match assistant.py Key Vault name
            config = AIConfig()
            endpoint = config.endpoint
            api_key = config.api_key
            api_version = config.api_version
            client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version=api_version
            )
        except Exception as e:
            raise ValueError(f"Failed to authenticate with Azure: {str(e)}")

    if os.getenv("OPENAI_ASSISTANT_ID"):
        assistantID=os.getenv("OPENAI_ASSISTANT_ID")
    else:
        raise ValueError("No valid Assistant ID found. Please set OPENAI_ASSISTANT_ID.")
    return 

# Tool: Generate_Workout_Plan
def Generate_Workout_Plan(days):
    """
    Generates a structured weekly workout plan tailored to the user's fitness goals, experience level, and preferred training style.
    days: Number of days in a week the user intends to work out in (string)
    """
    # Example implementation (replace with your logic as needed)
    try:
        days_int = int(days)
        plan = []
        for i in range(1, days_int + 1):
            plan.append(f"Day {i}: Full body workout with warm-up, main exercises, and cool-down.")
        return {
            "workout_plan": plan,
            "summary": f"Here is your {days}-day workout plan for the week. Remember to rest and hydrate!"
        }
    except Exception as e:
        return {"error": f"Invalid input for days: {days}. Error: {str(e)}"}

# Tool: Nutrition_Advice (tool function version)
def Nutrition_Advice_tool(calories):
    """
    Provides personalized nutrition advice based on the user's fitness goals.
    calories: Number of calories a day the user intends to eat (string)
    """
    try:
        calories_int = int(calories)
        advice = [
            f"Consume approximately {calories_int} calories per day.",
            "Focus on balanced meals with protein, complex carbs, and healthy fats.",
            "Stay hydrated and avoid processed sugars.",
            "Include vegetables and fruits in every meal."
        ]
        return {
            "nutrition_tips": advice,
            "summary": f"Nutrition advice for a {calories}-calorie daily intake."
        }
    except Exception as e:
        return {"error": f"Invalid input for calories: {calories}. Error: {str(e)}"}

def chat_with_assistant(message, history, assistantid, thread_id):
    try:
        if not thread_id:
            thread = client.beta.threads.create()
            thread_id = thread.id

        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )

        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread_id,
            assistant_id=assistantid
        )

        start_time = time.time()
        while run.status not in ["completed", "failed", "expired", "requires_action"]:
            if time.time() - start_time > 60:
                raise TimeoutError("Assistant response timed out. Please try again.")
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        # Tool call handling
        if run.status == "requires_action":
            tools_output = []
            for tool in run.required_action.submit_tool_outputs.tool_calls:
                if tool.function.name == "Generate_Workout_Plan":
                    args = json.loads(tool.function.arguments)
                    output = Generate_Workout_Plan(args["days"])
                    tools_output.append({"tool_call_id": tool.id, "output": json.dumps(output)})
                elif tool.function.name == "Nutrition_Advice":
                    args = json.loads(tool.function.arguments)
                    output = Nutrition_Advice_tool(args["calories"])
                    tools_output.append({"tool_call_id": tool.id, "output": json.dumps(output)})
            if tools_output:
                try:
                    run = client.beta.threads.runs.submit_tool_outputs_and_poll(
                        thread_id=thread_id,
                        run_id=run.id,
                        tool_outputs=tools_output
                    )
                except Exception as e:
                    print("failed to submit tool_outputs", e)
        if run.status != "completed":
            raise Exception(f"Run failed: {run.last_error}")

        messages = client.beta.threads.messages.list(thread_id=thread_id)
        assistant_messages = [msg for msg in messages if msg.role == "assistant"]
        if assistant_messages:
            latest_message = assistant_messages[0].content[0].text.value
            return latest_message, thread_id
        else:
            return "No response from the assistant. Please try again.", thread_id

    except Exception as e:
        tb = traceback.format_exc()
        return f"An error occurred: {str(e)} at line {tb.splitlines()[-2]}. Please try again or contact support if the issue persists.", thread_id

# Nutrition Advice API function (copied from assistant.py)
def Nutrition_Advice(location):
    conn = http.client.HTTPSConnection("ai-workout-planner-exercise-fitness-nutrition-guide.p.rapidapi.com")
    payload = json.dumps({
        "goal": "Lose weight",
        "dietary_restrictions": ["Vegetarian"],
        "current_weight": 80,
        "target_weight": 70,
        "daily_activity_level": "Moderate",
        "lang": "en"
    })
    headers = {
        'x-rapidapi-key': os.getenv("RAPIDAPI_KEY"),
        'x-rapidapi-host': "ai-workout-planner-exercise-fitness-nutrition-guide.p.rapidapi.com",
        'Content-Type': "application/json"
    }
    conn.request("POST", "/nutritionAdvice?noqueue=1", payload, headers)
    res = conn.getresponse()
    data = res.read()
    try:
        response = json.loads(data.decode("utf-8"))
        return response["result"]
    except Exception as e:
        return {"error": str(e)}

# Updated Gradio interface to include Nutrition Advice
def gradio_interface_with_nutrition(message, history, assistant_id, thread_id, location):
    if message.lower() == "nutrition advice":
        nutrition_data = Nutrition_Advice(location)
        response = pprint.pformat(nutrition_data)
    else:
        response, new_thread_id = chat_with_assistant(message, history, assistant_id, thread_id)
        thread_id = new_thread_id

    print("Debug - Returning from gradio_interface_with_nutrition:")
    print("Response:", response)
    print("History:")
    pprint.pprint(history)
    print("New Thread ID:", thread_id)
    history.append([message, response])
    return history, thread_id, ""

def download_history(history):
    history_text = "\n".join([f"Human: {h}\nAI: {a}" for h, a in history])
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
        temp_file.write(history_text)
        temp_file_path = temp_file.name
    return temp_file_path

def clear_conversation():
    return None, None

def assistant():
    head = """
    <script>
    (function() {
    // ...existing code...
    })();
    </script>
    """
    with gr.Blocks(css="#chatbot { height:600px; overflow-y:scroll; }", head=head) as app:
        gr.Markdown("# Chat with OpenAI Assistant")
        chatbot = gr.Chatbot(elem_id="chatbot", placeholder="say 'Hello' to start chatting with the assistant...")
        msg = gr.Textbox()
        location = gr.Textbox(label="Location (e.g., San Francisco, CA)", placeholder="Enter your location")
        clear = gr.Button("Clear")
        download_button = gr.Button("Download Chat History")
        download_output = gr.File(label="Chat History")
        assistant_id = gr.State(value=assistantID)
        thread_id = gr.State()
        msg.submit(gradio_interface_with_nutrition, 
                    inputs=[msg, chatbot, assistant_id, thread_id, location], 
                    outputs=[chatbot, thread_id, msg])
        clear.click(lambda: (None, None, ""), None, [chatbot, thread_id], queue=False)
        download_button.click(download_history, inputs=[chatbot], outputs=[download_output])
    return app

if __name__ == "__main__":
    gradio_init()
    app = assistant()
    app.queue()
    app.launch()