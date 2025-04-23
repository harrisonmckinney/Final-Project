# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import gradio as gr
import sys

# Import the Gradio interface from the separate file
from assistant import gradio_init as gradio_init_assistant, assistant as assistant_original
from assistant_with_dropdown import gradio_init as gradio_init_dropdown, assistant as assistant_dropdown

gradio_init_assistant()
gradio_init_dropdown()


# Create FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

interface=assistant_original()
interface2=assistant_dropdown()
# return client clientgradio_search_interface()

# Mount Gradio app
app = gr.mount_gradio_app(app, interface, path="/gradio")
app = gr.mount_gradio_app(app, interface2, path="/gradio2")

# FastAPI route
@app.get("/")
async def root():
    return {"message": "Welcome to the Article Analysis API"}

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)