# Django AI Agent

> An AI-powered Django development assistant that understands Django documentation, answers development questions, and generates or modifies Django code directly inside a project workspace.

The **Django AI Agent** is an AI coding assistant designed specifically for Django development. It combines a local Large Language Model with **Retrieval-Augmented Generation (RAG)** and **hybrid search** to provide context-aware answers and generate Django-specific code.

The agent can operate through an interactive **CLI** and also includes a **Django-based web interface** where users can create projects and interact with the agent through a chat interface.

---

##  Features

*  **AI-powered Django coding assistant**
*  Natural-language interaction through an interactive CLI
*  Django-based web interface
*  **RAG-powered Django documentation retrieval**
*  Hybrid search using:

  * **ChromaDB** for semantic similarity search
  * **BM25** for keyword/exact-term matching
*  Local LLM support through **Ollama**
*  Django-aware code generation
*  Reads existing project files to understand context
*  Creates new files and appends generated code to existing files
*  Smart merging of `urlpatterns` in `urls.py`
*  Removes duplicate imports and cleans generated code
*  Workspace path protection to prevent file access outside the configured workspace
*  User authentication in the web interface
*  Project management and project-specific chat history
*  Utilities for verifying the RAG and vector database setup

---

##  Architecture

The project follows an AI-agent pipeline built around four major components:

```text
                    ┌─────────────────────┐
                    │     User Request    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Agent Controller   │
                    │    AgentCore         │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
       ┌────────────┐   ┌──────────────┐  ┌──────────────┐
       │ File Tools │   │ Hybrid RAG   │  │ Prompt Engine│
       └────────────┘   └──────┬───────┘  └──────┬───────┘
                               │                 │
                       ┌───────┴────────┐        │
                       │                │        │
                       ▼                ▼        │
                 ┌──────────┐      ┌────────┐    │
                 │ ChromaDB │      │  BM25  │    │
                 │ Semantic │      │Keyword │    │
                 │ Search   │      │ Search │    │
                 └────┬─────┘      └───┬────┘    │
                      │                 │         │
                      └────────┬────────┘         │
                               ▼                  │
                       ┌──────────────┐           │
                       │ Django Docs  │           │
                       │   Context    │           │
                       └──────┬───────┘           │
                              │                   │
                              └─────────┬─────────┘
                                        ▼
                                ┌──────────────┐
                                │ Local LLM    │
                                │ CodeLlama 7B │
                                │   Ollama     │
                                └──────┬───────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │ Generated Code / │
                              │ Explanation      │
                              └────────┬────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │ Project Files / │
                              │ CLI Response    │
                              └─────────────────┘
```

---

##  Retrieval-Augmented Generation

The agent uses Django documentation as its knowledge source.

The RAG pipeline consists of:

```text
Django Documentation
        │
        ▼
Document Loader
        │
        ▼
Text Chunking
        │
        ▼
Embeddings
        │
        ▼
ChromaDB
        │
        ├───────────────┐
        │               │
        ▼               ▼
 Semantic Search     BM25 Search
        │               │
        └───────┬───────┘
                ▼
         Hybrid Retrieval
                │
                ▼
         Relevant Context
                │
                ▼
             LLM
```

Documents are split using `RecursiveCharacterTextSplitter` with a chunk size of **800 characters** and an overlap of **100 characters**.

For semantic retrieval, the project uses the `all-MiniLM-L6-v2` Sentence Transformer model to generate embeddings.

The vector store uses a persistent ChromaDB collection named:

```text
django_docs
```

with cosine similarity.

### Hybrid Search

The retrieval system combines:

**Semantic search**

> Useful for understanding concepts and finding documents with similar meaning.

**BM25 keyword search**

> Useful for exact Django terminology such as `ForeignKey`, `CharField`, `models.py`, `views.py`, and `urls.py`.

The hybrid retriever explicitly combines BM25 keyword search with embedding-based semantic search.

The BM25 index is generated from the existing ChromaDB documents and stored as:

```text
data/bm25_index.pkl
```

The project then loads both indexes at startup for retrieval.

---

##  AI Model

The current LLM implementation communicates with **Ollama** through its local generation API.

The default model configured in the project is:

```text
codellama:7b
```

and the API endpoint is:

```text
http://localhost:11434/api/generate
```

The implementation uses a low temperature of `0.1` by default to encourage more deterministic code generation.

### Start Ollama

Make sure Ollama is installed and the configured model is available locally.

For example:

```bash
ollama pull codellama:7b
```

Then ensure Ollama is running before starting the agent.

---

##  AgentCore

`AgentCore` is the central component responsible for coordinating the agent workflow.

It:

1. Detects whether the request is an **ANSWER** or **ACTION** request.
2. Identifies the target file when code modification is required.
3. Reads relevant project files.
4. Retrieves Django documentation context.
5. Builds an augmented prompt.
6. Sends the prompt to the LLM.
7. Extracts and cleans generated code.
8. Writes, appends, or updates project files.
9. Returns the generated response and retrieval sources.

The agent also has Django-specific rules for files such as:

```text
models.py
views.py
urls.py
forms.py
admin.py
serializers.py
signals.py
```

For example, `models.py` generation is constrained to Django model classes, while `urls.py` generation is constrained to URL patterns.

---

##  Code Generation & File Operations

The agent can work directly with files inside the configured workspace.

Supported operations include:

```text
read
write
append
update
delete
```

The file tool also resolves paths relative to the configured workspace and blocks attempts to access files outside that workspace.

### Example

A user can ask:

```text
Create a Student model in models.py
```

The agent can generate the Django model and write it into the appropriate project file.

Another example:

```text
Create URLs for the views in views.py and add them to urls.py
```

The agent can inspect the source `views.py`, identify the available view functions, and generate URL patterns specifically for those views.

### Smart `urls.py` Merging

When an existing `urls.py` already contains `urlpatterns`, the agent attempts to merge newly generated paths into the existing list instead of replacing the entire file.

Duplicate paths are avoided during the merge.

---

##  Generated Code Cleanup

LLM-generated code can occasionally contain formatting problems or explanatory text.

The agent includes preprocessing logic to:

* Remove unnecessary mode labels
* Remove generated explanation text from code
* Clean malformed prefixes
* Normalize collapsed code
* Expand collapsed Python statements
* Merge multiple code blocks
* Deduplicate imports
* Fix common indentation issues

The code extraction pipeline collects code from multiple Markdown blocks and raw code sections before producing the final code block.

---

##  Web Interface

Alongside the CLI, the project contains a Django web application.

The web application provides:

* User signup
* User login/logout
* Dashboard
* Project creation
* Project listing
* Project-specific chat
* Chat history
* Project chat deletion

The dashboard allows users to create a project by providing a project name and workspace/root path, after which the user is redirected to the project chat.

The interface is designed around the concept of:

```text
Create Project
      ↓
Set Workspace
      ↓
Chat with AI Agent
      ↓
Generate / Modify Django Code
      ↓
Review Project Files
```

---

##  Project Structure

```text
django_cli_agent/
│
├── agent/
│   ├── agent_core.py
│   ├── cli.py
│   ├── file_tools.py
│   ├── prompt.py
│   └── workspace.py
│
├── llm/
│   └── model.py
│
├── rag/
│   ├── embeddings.py
│   ├── initialise_rag.py
│   ├── loader.py
│   ├── retriever.py
│   ├── setup.py
│   ├── splitter.py
│   └── vector_store.py
│
├── data/
│   ├── django_docs/
│   ├── vector_db/
│   └── bm25_index.pkl
│
├── agent_test_project/
│   ├── manage.py
│   ├── agent_test_project/
│   └── students/
│
├── build_bm25_index.py
├── verify_vector_db.py
├── main.py
├── config.py
└── setup.py
```

The project also contains a separate Django web application under `web_ui_project`, containing `accounts`, `dashboard`, and `chat` components.

---

##  Installation

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd django_cli_agent
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:

**Windows**

```bash
venv\Scripts\activate
```

**Linux / macOS**

```bash
source venv/bin/activate
```

### 3. Install dependencies

Install the project's required Python packages.

```bash
pip install -r requirements.txt
```

> If a `requirements.txt` file is not included in your repository yet, generate one from the development environment with:
>
> ```bash
> pip freeze > requirements.txt
> ```

---

## 📚 Initialize the RAG System

Place the Django documentation files inside:

```text
data/django_docs/
```

The vector database is created under:

```text
data/vector_db/
```

The project uses a persistent ChromaDB database and creates the `django_docs` collection when building the vector store.

Run the RAG initialization script:

```bash
python rag/initialise_rag.py
```

The project includes a verification workflow that tests retrieval with a Django-related query and reports the retrieved context and sources.

---

##  Build the BM25 Index

After initializing ChromaDB, build the keyword-search index:

```bash
python build_bm25_index.py
```

This process:

1. Loads documents from ChromaDB.
2. Tokenizes the documents.
3. Builds a BM25 index.
4. Saves the index to `data/bm25_index.pkl`.
5. Runs a test query to verify the index.

After this step, the agent can use both semantic and keyword retrieval.

---

##  Verify the Vector Database

Run:

```bash
python verify_vector_db.py
```

The verification script checks:

* Whether the vector database exists
* ChromaDB connectivity
* Available collections
* Document counts
* Sample metadata
* Semantic retrieval

---

##  Running the CLI Agent

Start the CLI application with:

```bash
python main.py
```

The CLI starts an interactive chat session:

```text
 Django CLI AI Agent
Press Ctrl+C or Ctrl+D to exit

Ask:
```

The CLI continuously accepts user requests and sends them to the agent.

### Example Queries

```text
Ask: How do Django models work?
```

```text
Ask: Explain the code in models.py
```

```text
Ask: Create a Student model in models.py
```

```text
Ask: Add a list_students view to views.py
```

```text
Ask: Create URLs for the views in views.py and add them to urls.py
```

---

##  Running the Web Application

The project also contains a Django web application under:

```text
web_ui_project/
```

Run the Django development server:

```bash
cd web_ui_project
python manage.py runserver
```

Then open the local development server in your browser.

The web application provides authentication, a dashboard, project creation, project listing, and project-specific chat functionality.

---

##  Workspace Security

The agent operates relative to a configured workspace root.

The workspace can be dynamically changed using:

```python
set_workspace_root("/path/to/project")
```

The file tools resolve requested paths against this workspace and reject paths that attempt to escape it.

The default CLI workspace is configured in:

```text
agent/workspace.py
```

```python
WORKSPACE_ROOT = Path(
    r"..."
).resolve()
```

Update this path to point to the Django project you want the agent to work with.

---

##  Technology Stack

| Technology                   | Purpose                               |
| ---------------------------- | ------------------------------------- |
| **Python**                   | Core application and agent logic      |
| **Django**                   | Web interface and project environment |
| **Typer**                    | CLI interface                         |
| **Rich**                     | Terminal output formatting            |
| **Ollama**                   | Local LLM serving                     |
| **Code Llama 7B**            | Code-generation model                 |
| **ChromaDB**                 | Vector database                       |
| **Sentence Transformers**    | Text embeddings                       |
| **BM25**                     | Keyword-based retrieval               |
| **LangChain Text Splitters** | Document chunking                     |
| **SQLite**                   | Web application database              |

---

##  Request Flow

A typical coding request follows this flow:

```text
User
 │
 │ Natural-language request
 ▼
CLI / Web UI
 │
 ▼
AgentCore
 │
 ├── Detect request type
 │
 ├── Identify target file
 │
 ├── Read existing source files
 │
 ├── Retrieve Django documentation
 │
 ├── Build augmented prompt
 │
 ▼
LLM
 │
 ▼
Generated response
 │
 ├── Explanation
 │
 └── Django code
 │
 ▼
Code extraction & cleanup
 │
 ▼
File operation
 │
 ├── Create
 ├── Append
 ├── Update
 └── Merge
 │
 ▼
Django project
```

---

##  Example Use Cases

### Learn Django

```text
Explain how Django ForeignKey works.
```

### Understand Existing Code

```text
Explain the code in models.py.
```

### Generate Django Models

```text
Create a Student model with name, email and age in models.py.
```

### Generate Views

```text
Create a view that returns all students.
```

### Generate URLs

```text
Create URLs for the views in views.py and add them to urls.py.
```

### Modify Existing Code

```text
Add a new endpoint to views.py.
```

The agent can use existing project files as source context when performing these operations.

---

##  Development Utilities

### Verify Vector Database

```bash
python verify_vector_db.py
```

### Initialize RAG

```bash
python rag/initialise_rag.py
```

### Build BM25 Index

```bash
python build_bm25_index.py
```

### Start CLI

```bash
python main.py
```

### Start Web Application

```bash
cd web_ui_project
python manage.py runserver
```

---

##  Current Limitations

This project is currently focused specifically on Django-oriented development workflows.

Some areas that can be improved include:

* More robust code validation before writing generated code
* Better automated testing of generated code
* More sophisticated file-diff and approval workflows
* More configurable LLM providers
* Improved project/workspace configuration
* More comprehensive Django documentation coverage
* Additional Django file-type rules
* Production deployment configuration
* More extensive authentication and authorization controls for the web interface

---

##  Future Improvements

Potential future development includes:

* 🧠 Multi-model support
* 🔌 Support for additional LLM providers
* 🧪 Automatic generated-code testing
* 🔍 Static code analysis before file modification
* 📊 Agent execution history
* ↩️ Code change rollback
* 📝 Git-aware modifications
* 🌳 Project-wide dependency/context analysis
* ⚡ Streaming LLM responses
* 🧩 Plugin/tool architecture
* 🐳 Docker deployment
* ☁️ Cloud deployment
* 🔐 More granular workspace permissions

---

##  Project Goal

The goal of this project is to explore how **LLMs, RAG, semantic search, keyword retrieval, and tool-based agents** can be combined to create a practical AI-assisted software development environment.

Rather than functioning only as a conversational chatbot, the agent is designed to interact with an actual Django project by:

```text
Understanding
     ↓
Retrieving Context
     ↓
Generating Code
     ↓
Modifying Project Files
     ↓
Returning Results
```

This makes the project an exploration of **AI coding agents and agentic software development workflows**, with Django as the primary development domain.

---

##  License

Add your preferred license here, for example:

```text
MIT License
```

---

##  Author

**Vivek Venugopal**

Built as a project exploring:

* Artificial Intelligence
* Large Language Models
* Retrieval-Augmented Generation
* Hybrid Search
* AI Coding Agents
* Django
* Python
* Software Engineering
