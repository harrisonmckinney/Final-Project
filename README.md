# Gradio OpenAI Assistant Template

This repository provides templates for creating chat interfaces with OpenAI Assistants using Gradio and FastAPI. It includes both standalone applications and components for integration with a FastAPI server.

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

### Authentication
This project supports two authentication methods:
- Azure OpenAI via device code authentication (recommended, requires valid university MS account with access to the keyvault)
- Environment variables configured via GitHub Secrets

### Setting Up Environment Variables in GitHub Codespaces
Configure your environment variables using GitHub Secrets:

1. **Using GitHub Secrets (recommended for all sensitive information)**:
   - Go to your GitHub repository
   - Navigate to Settings > Secrets and variables > Codespaces
   - Add these secrets:
     - `OPENAI_ASSISTANT_ID`: The ID of your assistant (required for single assistant mode)
   - These will be automatically loaded as environment variables in your Codespace

> **⚠️ SECURITY WARNING**: 
> - API keys should always be kept secret and never committed to version control
> - Assistant IDs are less sensitive but should still be managed carefully in production environments
> - This repository's `.gitignore` is configured to protect sensitive information

## Standalone Applications

### Single Assistant
The `assistant_standalone.py` script runs a standalone Gradio app for a single assistant. To use it, ensure the environment variable `OPENAI_ASSISTANT_ID` is set through GitHub Secrets.

Run the application:
```bash
python assistant_standalone.py
```

Access the app at [http://localhost:7860](http://localhost:7860).

### Multiple Assistants
The `assistant_with_dropdown_standalone.py` script runs a standalone Gradio app for multiple assistants. Store your assistant IDs in a CSV file named `assistants.csv` in the project directory with the format:
```csv
assistant_id,name
asst_xxxxx,my assistant
asst_xxxx2,my 2nd assistant
```

Run the application:
```bash
python assistant_with_dropdown_standalone.py
```

Access the app at [http://localhost:7860](http://localhost:7860).

## FastAPI Server Applications

### Single Assistant
The `assistant.py` script integrates a single assistant Gradio app with a FastAPI server. This also requires the `OPENAI_ASSISTANT_ID` environment variable to be set through GitHub Secrets.

### Multiple Assistants
The `assistant_with_dropdown.py` script integrates a multiple assistants Gradio app with a FastAPI server. This requires the `assistants.csv` file as described above.

To run both applications through the FastAPI server:
```bash
python app.py
```

Access the endpoints at:
- Single assistant: [http://localhost:8000/gradio](http://localhost:8000/gradio)
- Multiple assistants: [http://localhost:8000/gradio2](http://localhost:8000/gradio2)

## Security
This project uses device code authentication for Azure OpenAI. Students must have access to the keyvault and a valid university MS account.

## Downloading Chats
Chats can be downloaded by clicking the download button in the Gradio interface.

