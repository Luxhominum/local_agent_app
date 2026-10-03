import json
import time
from typing import Dict, List, Any, Optional
import ollama

from tools.file_tools import (
    list_directory_contents,
    organize_folder,
    read_file_content,
    bulk_rename_files,
    create_or_write_file
)
from tools.web_tools import (
    scrape_webpage_content,
    search_web_quick
)
from tools.system_tools import (
    format_system_metrics_text,
    execute_powershell
)
from tools.data_tools import (
    read_pdf_text,
    inspect_csv_or_excel
)

# Registry of callable tools
TOOL_REGISTRY = {
    "list_directory_contents": list_directory_contents,
    "organize_folder": organize_folder,
    "read_file_content": read_file_content,
    "bulk_rename_files": bulk_rename_files,
    "create_or_write_file": create_or_write_file,
    "scrape_webpage_content": scrape_webpage_content,
    "search_web_quick": search_web_quick,
    "format_system_metrics_text": format_system_metrics_text,
    "execute_powershell": execute_powershell,
    "read_pdf_text": read_pdf_text,
    "inspect_csv_or_excel": inspect_csv_or_excel
}

AVAILABLE_TOOLS_SCHEMA = [
    list_directory_contents,
    organize_folder,
    read_file_content,
    bulk_rename_files,
    create_or_write_file,
    scrape_webpage_content,
    search_web_quick,
    format_system_metrics_text,
    execute_powershell,
    read_pdf_text,
    inspect_csv_or_excel
]

SYSTEM_PROMPT = """You are a helpful and reliable Local AI Automation Agent running on the user's computer.
You have direct access to local tools for file management, web research, document/data analysis, and PowerShell automation.

Guidelines:
1. Choose the most direct and safest tool to fulfill the user's request.
2. Once a tool returns the output or directory list, DO NOT call the tool again. Immediately synthesize and summarize the results in your final response to the user.
3. For organizing folders or renaming files, use dry_run=True first unless the user explicitly requested immediate execution.
4. Be concise, clear, and highlight exact paths, files changed, or metrics in your final response.
"""

class AutomationAgent:
    def __init__(self, host: str = "http://127.0.0.1:11434"):
        self.client = ollama.Client(host=host)

    def get_available_models(self) -> List[str]:
        """Fetch list of pulled models from Ollama."""
        try:
            res = self.client.list()
            # res can be a dict or a ListResponse with .models
            models_list = res.models if hasattr(res, 'models') else res.get('models', [])
            names = []
            for m in models_list:
                name = getattr(m, 'model', None) or (m.get('name') if isinstance(m, dict) else str(m))
                if name:
                    names.append(name)
            return names if names else ["llama3.2:1b"]
        except Exception as e:
            print(f"Error fetching Ollama models: {e}")
            return ["llama3.2:1b"]

    def run_agent_loop(
        self,
        prompt: str,
        history: Optional[List[Dict[str, Any]]] = None,
        model: str = "llama3.2:1b",
        max_turns: int = 6
    ) -> Dict[str, Any]:
        """Runs the multi-turn agent loop with tool execution."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        if history:
            for h in history[-8:]: # keep recent context
                messages.append(h)
                
        messages.append({"role": "user", "content": prompt})
        
        steps = []
        requires_confirmation = False
        pending_action = None
        
        for turn in range(max_turns):
            try:
                response = self.client.chat(
                    model=model,
                    messages=messages,
                    tools=AVAILABLE_TOOLS_SCHEMA
                )
            except Exception as e:
                return {
                    "response": f"Failed to connect to model '{model}': {str(e)}. Make sure Ollama is running.",
                    "steps": steps,
                    "requires_confirmation": False
                }
                
            msg = response.message
            tool_calls = getattr(msg, "tool_calls", None) or (msg.get("tool_calls") if isinstance(msg, dict) else None)
            
            # Resilient fallback: parse tool calls from text content if native tool_calls is empty
            if not tool_calls:
                content = getattr(msg, "content", "") or (msg.get("content") if isinstance(msg, dict) else "")
                parsed_calls = []
                import re
                
                # Check for json code blocks or inline json containing tool names
                json_blocks = re.findall(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
                if not json_blocks and "{" in content and "}" in content:
                    # Try finding standalone json objects in content
                    match = re.search(r'(\{[\s\S]*\})', content)
                    if match:
                        json_blocks.append(match.group(1))
                        
                for block in json_blocks:
                    try:
                        data = json.loads(block.strip())
                        fn_name = data.get("name") or data.get("tool") or data.get("function")
                        if fn_name and fn_name in TOOL_REGISTRY:
                            fn_args = data.get("arguments") or data.get("parameters") or data.get("args") or {}
                            parsed_calls.append({"function": {"name": fn_name, "arguments": fn_args}})
                    except:
                        pass
                        
                if parsed_calls:
                    tool_calls = parsed_calls

            if not tool_calls:
                # No more tools called; final answer reached
                raw_content = getattr(msg, "content", "") or (msg.get("content") if isinstance(msg, dict) else "")
                
                # If content is just raw JSON tool markup and we have executed steps, use the last step output
                if steps and ("```json" in raw_content or (raw_content.strip().startswith("{") and raw_content.strip().endswith("}"))):
                    last_step = steps[-1]
                    raw_content = f"Executed **{last_step['tool']}** successfully:\n\n{last_step['output']}"
                    
                return {
                    "response": raw_content,
                    "steps": steps,
                    "requires_confirmation": requires_confirmation,
                    "pending_action": pending_action
                }
                
            # Append assistant message with tool calls
            messages.append(msg)
            
            # Limit tool calls per turn to top 2 to avoid runaway calls from small models
            tool_calls = tool_calls[:2]
            
            # Execute tool calls
            for tool_call in tool_calls:
                fn_name = tool_call.function.name if hasattr(tool_call, 'function') else tool_call['function']['name']
                fn_args = tool_call.function.arguments if hasattr(tool_call, 'function') else tool_call['function']['arguments']
                
                # Check for registry match
                fn = TOOL_REGISTRY.get(fn_name)
                start_t = time.time()
                
                if fn:
                    try:
                        import inspect
                        # Call function with kwargs
                        if isinstance(fn_args, str):
                            try:
                                fn_args = json.loads(fn_args)
                            except:
                                fn_args = {}
                        
                        if isinstance(fn_args, dict):
                            sig = inspect.signature(fn)
                            has_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
                            if not has_varkw:
                                valid_keys = set(sig.parameters.keys())
                                filtered_args = {k: v for k, v in fn_args.items() if k in valid_keys}
                            else:
                                filtered_args = fn_args
                            tool_result = fn(**filtered_args)
                        else:
                            tool_result = fn()
                    except Exception as err:
                        tool_result = f"Tool execution exception: {str(err)}"
                else:
                    tool_result = f"Unknown tool '{fn_name}'."
                    
                duration_ms = round((time.time() - start_t) * 1000, 1)
                
                # Safety interceptor
                if isinstance(tool_result, str) and tool_result.startswith("SAFETY_REQUIRED:"):
                    requires_confirmation = True
                    pending_action = {
                        "tool": fn_name,
                        "args": fn_args,
                        "warning": tool_result
                    }
                    
                steps.append({
                    "turn": turn + 1,
                    "tool": fn_name,
                    "args": fn_args,
                    "output": str(tool_result),
                    "duration_ms": duration_ms
                })
                
                # Feed tool result back to agent
                messages.append({
                    "role": "tool",
                    "name": fn_name,
                    "content": str(tool_result)
                })
                
                if requires_confirmation:
                    return {
                        "response": f"⚠️ **Approval Needed**: {tool_result}",
                        "steps": steps,
                        "requires_confirmation": True,
                        "pending_action": pending_action
                    }
            
            # Check if all tools executed in this turn were duplicates of previous turns
            if turn >= 1 and len(steps) >= 2:
                last_tool = steps[-1]["tool"]
                prev_tool = steps[-2]["tool"]
                if last_tool == prev_tool and steps[-1]["args"] == steps[-2]["args"]:
                    # Final synthesis call without tool schemas to force final answer
                    try:
                        final_res = self.client.chat(
                            model=model,
                            messages=messages + [{"role": "user", "content": "Now summarize the tool results and provide the final answer."}]
                        )
                        final_content = getattr(final_res.message, "content", "")
                        return {
                            "response": final_content if final_content else steps[-1]["output"],
                            "steps": steps,
                            "requires_confirmation": False
                        }
                    except:
                        return {
                            "response": f"Results from {last_tool}:\n\n{steps[-1]['output']}",
                            "steps": steps,
                            "requires_confirmation": False
                        }
                    
        return {
            "response": "Reached maximum tool execution steps.",
            "steps": steps,
            "requires_confirmation": False
        }
