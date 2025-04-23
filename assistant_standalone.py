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
# Import from practical_ai_azure_keyvault
from practical_ai_azure_keyvault import initialize_app, AIConfig

load_dotenv()

client=None
assistantID=None

# Load environment variables
def gradio_init():
    global client,assistantID
    print("Loading environment variables...")
    load_dotenv()

    # Check for API key
    if os.getenv("OPENAI_API_KEY"):
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    else:
        # Use device code authentication with Azure Key Vault
        try:
            # Initialize with your Key Vault name - this will trigger device code authentication
            initialize_app("keyvaultname")  # Replace with your actual key vault name
            
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

        # Start timing for timeout check
        start_time = time.time()

        # Loop to poll the run status until it reaches a terminal state or requires action
        while run.status not in ["completed", "failed", "expired"]:
            # Check if the operation has taken too long (60-second timeout)
            if time.time() - start_time > 60:
                raise TimeoutError("Assistant response timed out. Please try again.")
            # Pause for 1 second to avoid overwhelming the API with requests
            time.sleep(1)
            # Refresh the run object to get the latest status
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

            # If tools are defined in the assistant, the following section can be uncommented to handle them
            # This block is commented with single-line comments; use Ctrl+/ to toggle in most IDEs
            # Check if the run requires action (e.g., tool execution)
            # if run.status == "requires_action":
            #     # Initialize a list to store tool outputs for submission
            #     tools_output = []
            #     # Iterate over each tool call requested by the assistant
            #     for tool in run.required_action.submit_tool_outputs.tool_calls:
            #         # Check if the tool function is 'tool_name' (replace with actual tool name, e.g., 'get_weather')
            #         if tool.function.name == "tool_name":
            #             # Parse the JSON string of arguments into a Python dictionary
            #             function_args = json.loads(tool.function.arguments)
            #             # Call the actual function with the parsed arguments
            #             # Replace 'function1' with your real function; it should return a JSON-serializable object
            #             results = function1(function_args)
            #             # Append the tool output with the tool call ID and JSON-serialized result
            #             tools_output.append({"tool_call_id": tool.id, "output": json.dumps(results)})
            #         # Example for a second tool; add more elifs for additional tools
            #         elif tool.function.name == "tool_name":  # Replace with a different tool name, e.g., 'get_time'
            #             # Parse the JSON string of arguments into a Python dictionary
            #             function_args = json.loads(tool.function.arguments)
            #             # Call the actual function, accessing a specific parameter (e.g., 'parameter')
            #             # Replace 'function2' with your real function; it should return a JSON-serializable object
            #             results = function2(function_args["parameter"])
            #             # Append the tool output with the tool call ID and JSON-serialized result
            #             tools_output.append({"tool_call_id": tool.id, "output": json.dumps(results)})
            #     # If there are any tool outputs, submit them to the assistant
            #     if tools_output:
            #         try:
            #             # Submit tool outputs and poll for completion in one step
            #             run = client.beta.threads.runs.submit_tool_outputs_and_poll(
            #                 thread_id=thread_id,
            #                 run_id=run.id,
            #                 tool_outputs=tools_output
            #             )
            #         except Exception as e:
            #             # Print error if submission fails (could be logged instead in production)
            #             print(f"Failed to submit tool outputs: {e}")
            #             raise  # Re-raise to handle in the outer try-except

        # Check if the run completed successfully; if not, raise an error
        # This works whether tools are used or not
        if run.status != "completed":
            raise Exception(f"Run failed: {run.last_error}")

        # Retrieve all messages from the thread
        messages = client.beta.threads.messages.list(thread_id=thread_id)

        # Filter for assistant messages and get the latest one
        assistant_messages = [msg for msg in messages if msg.role == "assistant"]
        if assistant_messages:
            # Extract the text content from the latest assistant message
            latest_message = assistant_messages[0].content[0].text.value
            return latest_message, thread_id
        else:
            # Return a fallback message if no assistant response is found
            return "No response from the assistant. Please try again.", thread_id

    # Exception handling block (assuming this is inside a try-except)
    except Exception as e:
        # Capture the full traceback for debugging
        tb = traceback.format_exc()
        error_lines = tb.splitlines()
        
        # Extract key error details
        error_msg = str(e)
        error_location = ""
        
        # Find the line in the traceback where the error occurred
        for line in error_lines:
            if "File" in line and "line" in line:
                error_location = line.strip()
                break
        
        # Format a detailed error message for the user
        formatted_error = (
            f"Error Details:\n"
            f"- Message: {error_msg}\n"
            f"- Location: {error_location}\n"
            f"Please try again or contact support if the issue persists."
        )
        
        # Return the error message along with the thread ID
        return formatted_error, thread_id

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

    // Periodically check for the chatbot element and scroll
    // setInterval(attemptScroll, 2000);

    console.log('Auto-scroll setup complete');
    })();
    </script>
    """

    with gr.Blocks(css="#chatbot { height:600px; overflow-y:scroll; }", head=head) as app:
        # ... rest of your code
        gr.Markdown("# Chat with OpenAI Assistant")
        
        
        chatbot = gr.Chatbot(elem_id="chatbot", placeholder="say 'Hello' to start chatting with the assistant...")
        msg = gr.Textbox()
        clear = gr.Button("Clear")
        
        download_button = gr.Button("Download Chat History")
        download_output = gr.File(label="Chat History")
        assistant_id=gr.State(value=assistantID)
        thread_id = gr.State()

        msg.submit(gradio_interface, 
                    inputs=[msg, chatbot, assistant_id, thread_id], 
                    outputs=[chatbot, thread_id, msg])
        clear.click(lambda: (None, None,""), None, [chatbot, thread_id], queue=False)
        download_button.click(download_history, inputs=[chatbot], outputs=[download_output])
        
    return app

if __name__ == "__main__":
    gradio_init()
    app = assistant()
    app.queue()
    app.launch()