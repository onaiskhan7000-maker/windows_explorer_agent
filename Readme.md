\# Windows File System Agent



A local AI agent that manages files and folders on Windows using natural language. Built with LangGraph and a local Ollama model, with a CLI loop and a FastAPI `/chat` endpoint.



\## Features

\- Read, write, move, copy, search, and list files

\- Create directories and open folders in Windows Explorer

\- Run PowerShell commands

\- Interactive CLI and REST API



\## ⚠️ Security Warning

This agent has broad access to the file system (`C:\\`) and can execute PowerShell commands. Run it only on machines you own, and never expose the API to a network without authentication. Consider restricting `WORKING\_DIR` to a safer folder before real use.



\## Requirements

\- Windows 10/11

\- Python 3.10+

\- \[Ollama](https://ollama.com) running locally

\- A pulled model, e.g.:

&#x20; ```bash

&#x20; ollama pull qwen3.5:9b

&#x20; ```



\## Installation

```bash

git clone https://github.com/<your-username>/<repo-name>.git

cd <repo-name>

python -m venv .venv

.venv\\Scripts\\activate

pip install -r requirements.txt

```



\## Usage



\*\*CLI mode\*\*

```bash

python main.py

```



\*\*API mode\*\*

```bash

uvicorn main:api --reload

```

Then:

```bash

curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\\"message\\": \\"List files on my Desktop\\"}"

```



Health check: `GET /health`



\## Project Structure

```

.

├── main.py           # Agent, tools, CLI, and API

├── requirements.txt  # Python dependencies

├── .gitignore

├── LICENSE

└── README.md

```



\## Notes

\- The model name is set in `main.py` (`ChatOllama(model="qwen3.5:9b")`). Change it to match your local model.

\- `WORKING\_DIR` defaults to `C:\\`. Change it to restrict access.



\## License

MIT. See \[LICENSE](LICENSE).

