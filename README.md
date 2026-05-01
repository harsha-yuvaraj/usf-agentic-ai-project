# Multi-Agent System for Statistical Data Analysis and Clinical Trials 

**By: Harshavardan Yuvaraj and Dylan Girrens**

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

#### E2B

To use the code execution tool:
1. Sign up for an [E2B API key](https://e2b.dev/sign-in).
2. Once you have your API key, add it to your `.env` file:
```
E2B_API_KEY=your-api-key
```

### Configure Model and Provider for Inference

The current __default__ model is:

```
openai/gpt-5-nano-2025-08-07
```

To __switch__ the model, update the `.env` file:

```
MODEL={provider}/{model}
```

The available providers are:

- openai
- anthropic
- ollama
- unsloth (locally hosted model served with llama.cpp via OpenAI-compatible API)


For example, to use an ollama model you would:

```
MODEL=ollama/qwen3:8b
```

#### Local Models Notes (ollama, unsloth):
Remember not all ollama models have tool capabilities!
Check the [Ollama Documentation](https://docs.ollama.com/) for details.

The unsloth provider is not an external API provider.
It is a routing label used by this project to connect to a locally hosted model served with llama.cpp via its OpenAI-compatible API.


### Start the development agent server

1. Install the packages
```bash
uv sync
```

2. Start the server
```bash 
uv run langgraph dev
```

## Firebase for File Storage
1. Install Node: [Link](https://nodejs.org/en/download)
2. Install Firebase CLI (recommend using NPM): [Link](https://firebase.google.com/docs/cli)
3. Log in: 
```
firebase login
```
4. Install dependencies (need to be in `services/functions`):
```
cd services/functions
```

5. Create a `.env` file.

```bash
cp .env.example .env
```
Open `.env` and add API keys as needed

```
npm install
```
6. Build project
```
npm run build
```

7. Start emulators (need to be `services`):
```
cd ..
```
```
firebase emulators:start
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

2. Create a `.env` file.

```bash
cp .env.example .env
```
Open `.env` and add API keys as needed

3. Install packages
```bash
flutter pub get
```

4. Run the Flutter app and target the Chrome device (web).
```bash
flutter run -d chrome
```
This launches the Flutter web app and connects to the local agent server.

## Sample Datasets

For testing purposes, we included AI-generated sample datasets located in the `agent/sample_data` directory. These can be used to test our system:
- `clinical_trial_results.csv`
- `tech_company_growth.csv`

## TableBench evaluation (instruct-only)

We evaluate the agent on the **TableBench** *direct-prompt* (`DP`) split using the workflow from the [official TableBench repository](https://github.com/TableBench/TableBench).

1. Download the dataset (from the **project root**, so files land in `./datasets/`):

```bash
uvx hf download Multilingual-Multimodal-NLP/TableBench TableBench_DP.jsonl --repo-type dataset --local-dir ./datasets
```

If that Hub path or filename changes, use the dataset linked from the TableBench README / paper.

2. Run our inference script (writes JSONL with `model_name` and `prediction`):

```bash
cd agent
uv sync
uv run tablebench-inference
```

Use `--input` / `--output` to override paths. Defaults: input `../datasets/TableBench_DP.jsonl`, output `../datasets/tablebench_inference_<model>.jsonl`.

3. Clone TableBench and install its dependencies:

```bash
git clone https://github.com/TableBench/TableBench.git
cd TableBench
uv pip install -r requirements.txt
```

4. Copy your inference JSONL into `TableBench/eval_examples/inference_results/` (same layout as their examples), then run their parse and evaluation scripts as described in [their README](https://github.com/TableBench/TableBench#-how-to-evaluate-on-tablebench): `parse_tablebench_instruction_response_script.py`, then `eval_tablebench_script.py`. Metrics appear under `eval_examples/evaluation_results/`.

## Acknowledgments & Code Sources

The following sources and tools were used in the development of this project:

*   **Core Architecture & Logic:** The core multi-agent logic, tool routing, and frontend-backend integration were primarily written by us.
*   **Backend Framework:** The agent orchestration relies on [LangGraph](https://langchain-ai.github.io/langgraph/). The base project structure was initially adapted from LangGraph starter templates but heavily modified for our specific biostatistical use case.
*   **Frontend UI:** The chat interface was built using the [flutter_ai_toolkit](https://pub.dev/packages/flutter_ai_toolkit) package.
*   **Code Execution:** Python and R code execution is handled securely using the [E2B Code Interpreter](https://e2b.dev/).
*   **AI Development Assistants:** We utilized Cursor AI IDE for debugging assistance and Gemini Code Assist (free version) for peer-reviewing our code during GitHub Pull Requests.

