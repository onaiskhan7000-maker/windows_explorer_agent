##Pips required to run this code:
##pip install langgraph langchain-ollama langchain-community langchain-core

import os
import json
import subprocess
from typing import Annotated, TypedDict

# LangGraph Core
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

# LangChain Local Ollama & Tools
from langchain_ollama import ChatOllama
from langchain_community.agent_toolkits import FileManagementToolkit
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage


from fastapi import FastAPI,HTTPException
from pydantic import BaseModel


# ==========================================
# 1. SYSTEM-WIDE FILESYSTEM TOOLKIT
# ==========================================
WORKING_DIR = os.path.abspath("C:\\")
USER_PROFILE = os.path.expanduser("~")

file_toolkit = FileManagementToolkit(
    root_dir=WORKING_DIR,
    selected_tools=[
        "read_file",
        "write_file",
        "list_directory",
        "file_search",
        "move_file",
        "copy_file"
    ]
)
file_tools = file_toolkit.get_tools()


# ==========================================
# 2. CUSTOM DIRECTORY & GUI TOOLS
# ==========================================
@tool
def create_directory(folder_path: str) -> str:
    """Creates a new folder or directory at the specified path (including parent folders)."""
    try:
        target_path = os.path.abspath(folder_path) if os.path.isabs(folder_path) else os.path.abspath(os.path.join(WORKING_DIR, folder_path))
        os.makedirs(target_path, exist_ok=True)
        return f"Successfully created directory: '{target_path}'"
    except Exception as e:
        return f"Failed to create directory: {str(e)}"

@tool
def open_in_windows_explorer(folder_path: str) -> str:
    """Opens a specified directory in the Windows File Explorer GUI."""
    try:
        target_path = os.path.abspath(folder_path) if os.path.isabs(folder_path) else os.path.abspath(os.path.join(WORKING_DIR, folder_path))
        if not os.path.exists(target_path):
            return f"Error: Path '{target_path}' does not exist."
        subprocess.run(f'explorer "{target_path}"', shell=True, check=True)
        return f"Successfully opened '{target_path}' in Windows File Explorer."
    except Exception as e:
        return f"Failed to open Windows File Explorer: {str(e)}"


@tool
def run_powershell_command(command: str) -> str:
    """Executes a PowerShell command or script and returns the standard output or error."""
    try:
        # Run command via PowerShell core/desktop
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True,
            timeout=30  # Safety timeout
        )
        
        if result.returncode == 0:
            return f"Output:\n{result.stdout}"
        else:
            return f"Error (Code {result.returncode}):\n{result.stderr}"
            
    except Exception as e:
        return f"Failed to execute PowerShell command: {str(e)}"

all_tools = file_tools + [create_directory, open_in_windows_explorer,run_powershell_command]


# ==========================================
# 3. AGENT STATE & LOCAL MODEL SETUP
# ==========================================
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


llm = ChatOllama(
    model="qwen3.5:9b",
    temperature=0,
    num_ctx=8192
)
llm_with_tools = llm.bind_tools(all_tools)


def agent_node(state: AgentState):
    """Primary reasoning node with JSON tool call parser fix."""
    system_prompt = SystemMessage(
        content=f"You are a Windows File System assistant with full tools access. "
                f"User Profile Directory: '{USER_PROFILE}'. "
                f"Desktop Directory: '{os.path.join(USER_PROFILE, 'Desktop')}'. "
                f"Downloads Directory: '{os.path.join(USER_PROFILE, 'Downloads')}'. "
                f"Always invoke function calls when actions are requested."
    )
    
    # Filter out initial SystemMessage duplicates
    filtered_msgs = [m for m in state["messages"] if not isinstance(m, SystemMessage)]
    messages = [system_prompt] + filtered_msgs
    
    response = llm_with_tools.invoke(messages)
    
    # Fallback Fix: If LLM outputted raw JSON tool call into content instead of tool_calls parameter
    if response.content and not response.tool_calls:
        try:
            content_str = response.content.strip()
            if content_str.startswith("{") and "name" in content_str and "arguments" in content_str:
                parsed_call = json.loads(content_str)
                response = AIMessage(
                    content="",
                    tool_calls=[{
                        "name": parsed_call["name"],
                        "args": parsed_call["arguments"],
                        "id": "fallback_call_id"
                    }]
                )
        except Exception:
            pass

    return {"messages": [response]}


# ==========================================
# 4. BUILD LANGGRAPH WORKFLOW
# ==========================================
builder = StateGraph(AgentState)

builder.add_node("agent", agent_node)
builder.add_node("tools", ToolNode(all_tools))

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition)
builder.add_edge("tools", "agent")

memory = MemorySaver()
app = builder.compile(checkpointer=memory)


# ==========================================
# 5. EXECUTION LOOP
# ==========================================
if __name__ == "__main__":
    print(f"📁 Local Windows File Explorer Agent Online (Ollama qwen2.5-coder:7b)!")
    print(f"User Profile Directory: {USER_PROFILE}")
    print("Type 'exit' to quit.\n")

    config = {"configurable": {"thread_id": "system_explorer_session"}}

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        for chunk in app.stream(
            {"messages": [HumanMessage(content=user_input)]},
            config=config,
            stream_mode="updates"
        ):
            for node_name, node_update in chunk.items():
                if node_name == "agent":
                    message = node_update["messages"][-1]
                    if message.content and not message.tool_calls:
                        print(f"\nAgent: {message.content}\n")
                elif node_name == "tools":
                    for tool_msg in node_update["messages"]:
                        print(f"\n🛠️ [Executed Tool Result]: {tool_msg.content}\n")





class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


api = FastAPI()


@api.get("/health")
def health():
    return {"status": "ok"}


@api.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    try:
        result = app.invoke(
            {"messages": [HumanMessage(content=body.message)]},
            config={"configurable": {"thread_id": "system_explorer_session"}},
        )
        reply = result["messages"][-1].content
        return ChatResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))