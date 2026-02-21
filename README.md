# Agentic AI Project

## Clone this repository:
```bash
git clone git@github.com:harsha-yuvaraj/usf-agentic-ai-project.git
cd usf-agentic-ai-project
```

## Langgraph Agent

### Prerequisites 
We use `uv` for Python environment + dependency management. Install uv [here](https://docs.astral.sh/uv/getting-started/installation/).


### Create Environment Variables

1. Navigate to the `agent` directory:
```bash
cd agent
```

2. Create a `.env` file.

```bash
cp .env.example .env
```
Open `.env` and add API keys as needed


#### Anthropic

To use Anthropic's chat models:

1. Sign up for an [Anthropic API key](https://console.anthropic.com/) if you haven't already.
2. Once you have your API key, add it to your `.env` file:

```env
ANTHROPIC_API_KEY=your-api-key
```
#### OpenAI

To use OpenAI's chat models:

1. Sign up for an [OpenAI API key](https://platform.openai.com/signup).
2. Once you have your API key, add it to your `.env` file:
```env
OPENAI_API_KEY=your-api-key
```

#### Tavily Search

To use the search tool:
1. Sign up for an [Tavily API key](https://app.tavily.com/sign-in).
2. Once you have your API key, add it to your `.env` file:
```
TAVILY_API_KEY=your-api-key
```

### Configure the Default Model

Default `model`:

```yaml
gpt-5-nano-2025-08-07
```

To change default model, update the `.env` file:

```
MODEL={provider}/{model}
```

The available providers are:
```
openai, anthropic, ollama
```

For example, to use an ollama model you would:

```
MODEL=ollama/qwen3:8b
```

Remember not all ollama models have tool capabilities!

### Start the development agent server

1. Install the packages
```bash
uv sync
```

2. Start the server
```bash 
uv run langgraph dev
```


## Frontend (Flutter Web)

### 1. Install Flutter 
Install flutter by following the instructions [here](https://docs.flutter.dev/install)

Verify installation:
```bash
flutter doctor
```

### 2. Run the Web App
1. Navigate to the `app` directory:
```bash
cd app
```

2. Install packages
```bash
flutter pub get
```

3. Run the Flutter app and target the Chrome device (web).
```bash
flutter run -d chrome
```
This launches the Flutter web app and connects to the local agent server.

