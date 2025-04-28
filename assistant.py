import os
import csv
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
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    else:
        # Use device code authentication with Azure Key Vault
        try:
            # Initialize with your Key Vault name - this will trigger device code authentication
            initialize_app("ClassWeatherApi")  # Replace with your actual key vault name
            
            # Access the configuration
            config = AIConfig()
            
            # Extract only the required parameters explicitly
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

# Function to interact with the selected assistant
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

        # Wait for the run to complete with a timeout
        start_time = time.time()
        while run.status not in ["completed", "failed", "expired", "requires_action"]:
            if time.time() - start_time > 60:  # 60 seconds timeout
                raise TimeoutError("Assistant response timed out. Please try again.")
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        # if there tools then uncomment below code
        # if run.status=="requires_action":
        #     tools_output=[]
        #     for tool in run.required_action.submit_tool_outputs.tool_calls:
        #         if tool.function.name=="tool_name": #change to the tool name the LLM will call
        #             tools_output.append({"tool_call_id":tool.id,"output":tool_funtion1(json.loads(tool.function.arguments)["parameter"])}) #change tool_funtion(parameter) to the function that will return the output of the tool
        #         elif tool.function.name=="tool_name": #change to the tool name the LLM will call
        #             tools_output.append({"tool_call_id":tool.id,"output":tool_funtion2(json.loads(tool.function.arguments)["parameter"])}) #change tool_funtion(parameter) to the function that will return the output of the tool
        #     if tools_output:
        #         try:
        #             client.beta.threads.runs.submit_tool_outputs_and_poll(thread_id=thread_id,run_id=run.id,tools_outputs=tools_output)
        #         except Exception as e:
        #             print("failed to submit tool_outputs",e)
        if run.status != "completed": #change this line to an elif if there are tools
            raise Exception(f"Run failed: {run.last_error}")
        
        # Retrieve messages
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        
        # Get the latest assistant message
        assistant_messages = [msg for msg in messages if msg.role == "assistant"]
        if (assistant_messages):
            latest_message = assistant_messages[0].content[0].text.value
            return latest_message, thread_id
        else:
            return "No response from the assistant. Please try again.", thread_id

    except Exception as e:
        tb = traceback.format_exc()
        return f"An error occurred: {str(e)} at line {tb.splitlines()[-2]}. Please try again or contact support if the issue persists.", thread_id


def gradio_interface(message, history, assistant_id, thread_id):

    response, new_thread_id = chat_with_assistant(message, history, assistant_id, thread_id)

    # Debug print statement
    print("Debug - Returning from gradio_interface:")
    print("Response:", response)
    print("History:")
    pprint.pprint(history)
    print("New Thread ID:", new_thread_id)
    history.append([message, response])
    return history, new_thread_id, ""

# Function to call the Nutrition Advice API
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
        'x-rapidapi-key': os.getenv("RAPIDAPI_KEY"),  # Use environment variable for API key
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

# Update the Gradio interface to include Nutrition Advice
def gradio_interface_with_nutrition(message, history, assistant_id, thread_id, location):
    if message.lower() == "nutrition advice":
        nutrition_data = Nutrition_Advice(location)
        response = pprint.pformat(nutrition_data)
    else:
        response, new_thread_id = chat_with_assistant(message, history, assistant_id, thread_id)
        thread_id = new_thread_id

    # Debug print statement
    print("Debug - Returning from gradio_interface_with_nutrition:")
    print("Response:", response)
    print("History:")
    pprint.pprint(history)
    print("New Thread ID:", thread_id)
    history.append([message, response])
    return history, thread_id, ""

# Function to download chat history

def download_history(history):
  history_text = "\n".join([f"Human: {h}\nAI: {a}" for h, a in history])
  
  # Create a temporary file with a short, fixed name
  with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
      temp_file.write(history_text)
      temp_file_path = temp_file.name
  
  return temp_file_path

# Function to clear conversation and thread
def clear_conversation():
  return None, None

def assistant():
    head = """
    <script>
    (function() {
    console.log('Auto-scroll script loaded');

    function findScrollableMessageContainer() {
        console.log('Searching for scrollable message container...');
        const chatbotContainer = document.querySelector('#chatbot');
        if (chatbotContainer) {
            const bubbleWrap = chatbotContainer.querySelector('.bubble-wrap');
            if (bubbleWrap) {
                console.log('Found scrollable element:', bubbleWrap);
                return bubbleWrap;
            }
        }
        console.log('Scrollable message container not found');
        return null;
    }

    function scrollToBottom(element) {
        element.scrollTop = element.scrollHeight;
        console.log('Scrolled to bottom');
    }

    function attemptScroll() {
        const scrollableElement = findScrollableMessageContainer();
        if (scrollableElement) {
            scrollToBottom(scrollableElement);
        } else {
            console.log('No scrollable element found');
        }
    }

    function setupObserver() {
        const chatbotContainer = document.querySelector('#chatbot');
        if (chatbotContainer) {
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                        setTimeout(attemptScroll, 100);
                    }
                });
            });
            observer.observe(chatbotContainer, { childList: true, subtree: true });
            console.log('MutationObserver set up');
        } else {
            console.log('Chatbot container not found for MutationObserver, retrying in 1 second');
            setTimeout(setupObserver, 1000);  // Retry after 1 second
        }
    }

    function initializeAutoScroll() {
        console.log('Initializing auto-scroll...');
        setupObserver();
        attemptScroll();
    }

    // Set up the observer when the DOM is fully loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeAutoScroll);
    } else {
        initializeAutoScroll();
    }

    // Also attempt to scroll on window load and resize
    window.addEventListener('load', attemptScroll);
    window.addEventListener('resize', attemptScroll);

    console.log('Auto-scroll setup complete');
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

# app.queue()
# app.launch()