# from agent.prompt import build_prompt
# from llm.model import LLM
# from rag.retriever import retrieve_context
# from agent.file_tools import (
#     read_file,
#     write_file,
#     append_file,
#     FileToolError
# )
# import re


# class AgentCore:
#     """
#     Smart Django CLI Agent
#     - LLM generates code + explanation
#     - Code goes to file
#     - Full response prints to CLI
#     """

#     def __init__(self):
#         self.llm = LLM()

#     def run(self, user_input: str) -> str:
#         # STEP 1: Detect mode and extract path FIRST
#         mode = self._detect_mode(user_input)
#         path = self._extract_path(user_input)
        
#         # DEBUG: Show detected mode
#         print(f"\n[DEBUG] Detected mode: {mode}")
#         print(f"[DEBUG] Extracted path: {path}")

#         # STEP 2: If ANSWER MODE with file path, read the file content
#         file_content = None
#         if mode == "ANSWER" and path:
#             try:
#                 from pathlib import Path
#                 full_path = Path("D:/Final_Project_Folder/django_cli_agent/agent_test_project") / path
#                 print(f"[DEBUG] Trying to read: {full_path}")
#                 print(f"[DEBUG] File exists: {full_path.exists()}")
                
#                 file_content = read_file(path)
#                 print(f"[DEBUG] File content read successfully: {len(file_content)} chars")
#             except FileToolError as e:
#                 print(f"[DEBUG] FileToolError: {e}")
#                 return f"❌ Cannot read file: {e}"
#             except Exception as e:
#                 print(f"[DEBUG] Unexpected error: {e}")
#                 return f"❌ Error reading file: {e}"

#         # STEP 3: Retrieve RAG context
#         try:
#             context, sources = retrieve_context(user_input, k=4)
#         except Exception:
#             context, sources = None, []

#         # STEP 4: Build prompt with file content if available
#         prompt = build_prompt(
#             user_input=user_input, 
#             context=context,
#             file_content=file_content,
#             file_path=path
#         )
        
#         # STEP 5: Generate LLM response
#         raw = self.llm.generate(prompt).strip()

#         # STEP 6: Handle ANSWER MODE (no file operations, just display)
#         if mode == "ANSWER":
#             cli_output = []
            
#             # If reading a file, show the actual code first
#             if file_content:
#                 cli_output.extend([
#                     f"📄 Code from {path}:",
#                     "=" * 60,
#                     file_content,
#                     "=" * 60,
#                     "",
#                     "📝 Explanation:",
#                     "=" * 60
#                 ])
            
#             cli_output.append(raw)
            
#             if sources:
#                 cli_output.extend(["", "=" * 60, "📚 Sources:", "=" * 60])
#                 cli_output.extend(f"  • {s}" for s in sources)
            
#             return "\n".join(cli_output)

#         # STEP 7: Handle ACTION MODE (extract code and write to file)
#         code = self._extract_code_only(raw)
#         if not code:
#             return "❌ No code detected in LLM output.\n\n" + raw

#         if not path:
#             return "❌ ACTION MODE requires a file path.\n\n" + raw

#         # STEP 8: Remove duplicate imports if file exists
#         try:
#             existing = read_file(path)
#             code = self._remove_duplicate_imports(existing, code)
#         except Exception:
#             pass  # file does not exist yet

#         # STEP 9: Decide safe action (write new file or append to existing)
#         try:
#             read_file(path)
#             action = "append_file"
#         except Exception:
#             action = "write_file"

#         # STEP 10: Execute file action
#         try:
#             if action == "write_file":
#                 write_file(path, code)
#                 file_status = f"✅ File created: {path}"
#             else:
#                 append_file(path, code)
#                 file_status = f"✅ Code appended to: {path}"

#         except FileToolError as e:
#             file_status = f"❌ [FILE ERROR] {e}"

#         # STEP 11: Build CLI output
#         cli_output = [file_status, "", "=" * 60, "📝 Full Response:", "=" * 60, raw]
        
#         if sources:
#             cli_output.extend(["", "=" * 60, "📚 Sources:", "=" * 60])
#             cli_output.extend(f"  • {s}" for s in sources)

#         return "\n".join(cli_output)

#     # ---------------- HELPERS ---------------- #

#     def _detect_mode(self, user_input: str) -> str:
#         """
#         Detect whether the user wants ACTION MODE or ANSWER MODE
        
#         ANSWER MODE triggers:
#         - 'read', 'explain', 'what is', 'how does', 'why'
#         - 'difference between', 'when to use'
#         - 'best practice', 'should I', 'help understand'
        
#         ACTION MODE triggers:
#         - 'create', 'write', 'generate', 'build', 'add'
#         - 'implement', 'make', 'develop', 'insert'
#         """
#         lower_input = user_input.lower()
        
#         # ANSWER MODE keywords (check these FIRST for read/explain)
#         # These are stronger signals than generic words
#         answer_keywords = [
#             'read the code', 'read code', 'explain the code', 'explain code',
#             'show me the code', 'what is', 'how does', 'why', 
#             'explain', 'describe', 'tell me about',
#             'difference', 'when to use', 'best practice',
#             'help understand', 'understand', 'clarify'
#         ]
        
#         for keyword in answer_keywords:
#             if keyword in lower_input:
#                 return "ANSWER"
        
#         # Check for "read" alone (without "write")
#         if 'read' in lower_input and 'write' not in lower_input:
#             return "ANSWER"
        
#         # ACTION MODE keywords (specific action verbs)
#         action_keywords = [
#             'create', 'write', 'generate', 'build', 'add',
#             'implement', 'make', 'develop', 'insert',
#             'update', 'modify', 'change', 'delete'
#         ]
        
#         for keyword in action_keywords:
#             if keyword in lower_input:
#                 return "ACTION"
        
#         # Default to ANSWER if no clear action verb
#         return "ANSWER"

#     def _extract_path(self, user_input: str) -> str | None:
#         """Extract file path from user input"""
#         for token in user_input.split():
#             if token.endswith((".py", ".html")):
#                 return token
#         return None

#     def _extract_code_only(self, text: str) -> str:
#         """
#         Extract code from LLM output - handles markdown and raw code
#         Returns clean Python code without markdown backticks or explanations
#         """
#         # First, try to extract from markdown code blocks
#         markdown_pattern = r'```(?:python)?\s*\n(.*?)\n```'
#         markdown_matches = re.findall(markdown_pattern, text, re.DOTALL)
        
#         if markdown_matches:
#             # Use the first code block found
#             code = markdown_matches[0].strip()
#             return self._clean_extracted_code(code)
        
#         # If no markdown, extract raw code (original method)
#         lines = []
#         recording = False
        
#         for line in text.splitlines():
#             stripped = line.strip()
            
#             # Start recording when we hit code-like lines
#             if stripped.startswith(("class ", "def ", "from ", "import ")):
#                 recording = True
            
#             # Stop recording if we hit explanation markers
#             if recording and (
#                 stripped.startswith(("Explanation:", "In order to", "Note:", "This"))
#                 or stripped.lower().startswith(("you can", "the above", "in this"))
#             ):
#                 break
            
#             if recording:
#                 lines.append(line)
        
#         code = "\n".join(lines).strip()
#         return self._clean_extracted_code(code)

#     def _clean_extracted_code(self, code: str) -> str:
#         """
#         Clean extracted code:
#         - Remove stray markdown backticks
#         - Remove invalid lines
#         - Fix indentation issues
#         """
#         lines = []
        
#         for line in code.splitlines():
#             stripped = line.strip()
            
#             # Skip markdown artifacts
#             if stripped in ['```', '```python', '```py']:
#                 continue
            
#             # Skip explanation lines that slipped through
#             if any(stripped.startswith(marker) for marker in [
#                 'Explanation:', 'Note:', 'In this', 'The above', 'This model'
#             ]):
#                 continue
            
#             # Keep valid Python lines
#             lines.append(line)
        
#         # Validate the code has a proper class or function definition
#         code_str = "\n".join(lines).strip()
        
#         # Must contain at least one class or function definition
#         if not any(keyword in code_str for keyword in ['class ', 'def ']):
#             return ""
        
#         return code_str

#     def _remove_duplicate_imports(self, existing: str, new_code: str) -> str:
#         """
#         Removes imports from new_code that are already present in existing
#         Only removes exact matches and keeps the rest intact
#         """
#         existing_lines = existing.splitlines()
#         new_lines = new_code.splitlines()
#         filtered_lines = []

#         for line in new_lines:
#             stripped = line.strip()
            
#             # Skip empty lines at the start
#             if not stripped and not filtered_lines:
#                 continue
            
#             # Check if this line already exists
#             if stripped and stripped not in [l.strip() for l in existing_lines]:
#                 filtered_lines.append(line)
#             elif not stripped:
#                 # Keep blank lines within the code
#                 filtered_lines.append(line)

#         return "\n".join(filtered_lines).strip()

# from agent.prompt import build_prompt
# from llm.model import LLM
# from rag.retriever import retrieve_context
# from agent.file_tools import (
#     read_file,
#     write_file,
#     append_file,
#     FileToolError
# )
# import re


# class AgentCore:
#     """
#     Smart Django CLI Agent
#     - LLM generates code + explanation
#     - Code goes to file
#     - Full response prints to CLI
#     """

#     def __init__(self):
#         self.llm = LLM()

#     def run(self, user_input: str) -> str:
#         # STEP 1: Detect mode and extract path FIRST
#         mode = self._detect_mode(user_input)
#         path = self._extract_path(user_input, mode)
        
#         # DEBUG: Show detected mode
#         print(f"\n[DEBUG] Detected mode: {mode}")
#         print(f"[DEBUG] Extracted path: {path}")

#         # STEP 2: If ANSWER MODE with file path, read the file content
#         file_content = None
#         if mode == "ANSWER" and path:
#             try:
#                 from pathlib import Path
#                 full_path = Path("D:/Final_Project_Folder/django_cli_agent/agent_test_project") / path
#                 print(f"[DEBUG] Trying to read: {full_path}")
#                 print(f"[DEBUG] File exists: {full_path.exists()}")
                
#                 file_content = read_file(path)
#                 print(f"[DEBUG] File content read successfully: {len(file_content)} chars")
#             except FileToolError as e:
#                 print(f"[DEBUG] FileToolError: {e}")
#                 return f"❌ Cannot read file: {e}"
#             except Exception as e:
#                 print(f"[DEBUG] Unexpected error: {e}")
#                 return f"❌ Error reading file: {e}"

#         # STEP 3: Retrieve RAG context
#         try:
#             context, sources = retrieve_context(user_input, k=4)
#         except Exception:
#             context, sources = None, []

#         # STEP 4: Build prompt with file content if available
#         prompt = build_prompt(
#             user_input=user_input, 
#             context=context,
#             file_content=file_content,
#             file_path=path
#         )
        
#         # STEP 5: Generate LLM response
#         raw = self.llm.generate(prompt).strip()

#         # STEP 6: Handle ANSWER MODE (no file operations, just display)
#         if mode == "ANSWER":
#             cli_output = []
            
#             # If reading a file, show the actual code first
#             if file_content:
#                 cli_output.extend([
#                     f"📄 Code from {path}:",
#                     "=" * 60,
#                     file_content,
#                     "=" * 60,
#                     "",
#                     "📝 Explanation:",
#                     "=" * 60
#                 ])
            
#             cli_output.append(raw)
            
#             if sources:
#                 cli_output.extend(["", "=" * 60, "📚 Sources:", "=" * 60])
#                 cli_output.extend(f"  • {s}" for s in sources)
            
#             return "\n".join(cli_output)

#         # STEP 7: Handle ACTION MODE (extract code and write to file)
#         code = self._extract_code_only(raw)
#         if not code:
#             return "❌ No code detected in LLM output.\n\n" + raw

#         if not path:
#             return "❌ ACTION MODE requires a file path.\n\n" + raw

#         # STEP 8: Remove duplicate imports if file exists
#         try:
#             existing = read_file(path)
#             code = self._remove_duplicate_imports(existing, code)
#         except Exception:
#             pass  # file does not exist yet

#         # STEP 9: Decide safe action (write new file or append to existing)
#         try:
#             read_file(path)
#             action = "append_file"
#         except Exception:
#             action = "write_file"

#         # STEP 10: Execute file action
#         try:
#             if action == "write_file":
#                 write_file(path, code)
#                 file_status = f"✅ File created: {path}"
#             else:
#                 append_file(path, code)
#                 file_status = f"✅ Code appended to: {path}"

#         except FileToolError as e:
#             file_status = f"❌ [FILE ERROR] {e}"

#         # STEP 11: Build CLI output
#         cli_output = [file_status, "", "=" * 60, "📝 Full Response:", "=" * 60, raw]
        
#         if sources:
#             cli_output.extend(["", "=" * 60, "📚 Sources:", "=" * 60])
#             cli_output.extend(f"  • {s}" for s in sources)

#         return "\n".join(cli_output)

#     # ---------------- HELPERS ---------------- #

#     def _detect_mode(self, user_input: str) -> str:
#         """
#         Detect whether the user wants ACTION MODE or ANSWER MODE
        
#         ANSWER MODE triggers:
#         - 'read', 'explain', 'what is', 'how does', 'why'
#         - 'difference between', 'when to use'
#         - 'best practice', 'should I', 'help understand'
        
#         ACTION MODE triggers:
#         - 'create', 'write', 'generate', 'build', 'add'
#         - 'implement', 'make', 'develop', 'insert'
#         """
#         lower_input = user_input.lower()
        
#         # ANSWER MODE keywords (check these FIRST for read/explain)
#         # These are stronger signals than generic words
#         answer_keywords = [
#             'read the code', 'read code', 'explain the code', 'explain code',
#             'show me the code', 'what is', 'how does', 'why', 
#             'explain', 'describe', 'tell me about',
#             'difference', 'when to use', 'best practice',
#             'help understand', 'understand', 'clarify'
#         ]
        
#         for keyword in answer_keywords:
#             if keyword in lower_input:
#                 return "ANSWER"
        
#         # Check for "read" alone (without "write")
#         if 'read' in lower_input and 'write' not in lower_input:
#             return "ANSWER"
        
#         # ACTION MODE keywords (specific action verbs)
#         action_keywords = [
#             'create', 'write', 'generate', 'build', 'add',
#             'implement', 'make', 'develop', 'insert',
#             'update', 'modify', 'change', 'delete'
#         ]
        
#         for keyword in action_keywords:
#             if keyword in lower_input:
#                 return "ACTION"
        
#         # Default to ANSWER if no clear action verb
#         return "ANSWER"

#     def _extract_path(self, user_input: str, mode: str) -> str | None:
#         """
#         Extract file path from user input
        
#         Only extract paths when context indicates an actual file operation:
#         - ACTION MODE: Always try to extract path (user wants to write code)
#         - ANSWER MODE: Only extract if explicit file reading keywords present
#         """
#         lower_input = user_input.lower()
        
#         # In ANSWER MODE, only extract path if explicitly reading a specific file
#         if mode == "ANSWER":
#             # Check for explicit file reading indicators
#             file_read_indicators = [
#                 'read the code in',
#                 'read code in', 
#                 'read the file',
#                 'read file',
#                 'show me the code in',
#                 'show code in',
#                 'explain the code in',
#                 'explain code in',
#                 'what does the code in',
#                 'open',
#                 'display the file'
#             ]
            
#             has_file_read_indicator = any(indicator in lower_input for indicator in file_read_indicators)
            
#             if not has_file_read_indicator:
#                 # This is a general question about a concept (e.g., "What is models.py for?")
#                 # Don't extract path
#                 return None
        
#         # Extract path from tokens
#         for token in user_input.split():
#             if token.endswith((".py", ".html")):
#                 return token
        
#         return None

#     def _extract_code_only(self, text: str) -> str:
#         """
#         Extract code from LLM output - handles markdown and raw code
#         Returns clean Python code without markdown backticks or explanations
#         """
#         # First, try to extract from markdown code blocks
#         markdown_pattern = r'```(?:python)?\s*\n(.*?)\n```'
#         markdown_matches = re.findall(markdown_pattern, text, re.DOTALL)
        
#         if markdown_matches:
#             # Use the first code block found
#             code = markdown_matches[0].strip()
#             return self._clean_extracted_code(code)
        
#         # If no markdown, extract raw code (original method)
#         lines = []
#         recording = False
        
#         for line in text.splitlines():
#             stripped = line.strip()
            
#             # Start recording when we hit code-like lines
#             if stripped.startswith(("class ", "def ", "from ", "import ")):
#                 recording = True
            
#             # Stop recording if we hit explanation markers
#             if recording and (
#                 stripped.startswith(("Explanation:", "In order to", "Note:", "This"))
#                 or stripped.lower().startswith(("you can", "the above", "in this"))
#             ):
#                 break
            
#             if recording:
#                 lines.append(line)
        
#         code = "\n".join(lines).strip()
#         return self._clean_extracted_code(code)

#     def _clean_extracted_code(self, code: str) -> str:
#         """
#         Clean extracted code:
#         - Remove stray markdown backticks
#         - Remove invalid lines
#         - Fix indentation issues
#         """
#         lines = []
        
#         for line in code.splitlines():
#             stripped = line.strip()
            
#             # Skip markdown artifacts
#             if stripped in ['```', '```python', '```py']:
#                 continue
            
#             # Skip explanation lines that slipped through
#             if any(stripped.startswith(marker) for marker in [
#                 'Explanation:', 'Note:', 'In this', 'The above', 'This model'
#             ]):
#                 continue
            
#             # Keep valid Python lines
#             lines.append(line)
        
#         # Validate the code has a proper class or function definition
#         code_str = "\n".join(lines).strip()
        
#         # Must contain at least one class or function definition
#         if not any(keyword in code_str for keyword in ['class ', 'def ']):
#             return ""
        
#         return code_str

#     def _remove_duplicate_imports(self, existing: str, new_code: str) -> str:
#         """
#         Removes imports from new_code that are already present in existing
#         Only removes exact matches and keeps the rest intact
#         """
#         existing_lines = existing.splitlines()
#         new_lines = new_code.splitlines()
#         filtered_lines = []

#         for line in new_lines:
#             stripped = line.strip()
            
#             # Skip empty lines at the start
#             if not stripped and not filtered_lines:
#                 continue
            
#             # Check if this line already exists
#             if stripped and stripped not in [l.strip() for l in existing_lines]:
#                 filtered_lines.append(line)
#             elif not stripped:
#                 # Keep blank lines within the code
#                 filtered_lines.append(line)

#         return "\n".join(filtered_lines).strip()

from agent.prompt import build_prompt
from llm.model import LLM
from rag.retriever import retrieve_context
from agent.file_tools import (
    read_file,
    write_file,
    append_file,
    FileToolError,
    set_workspace_root  # NEW: Import the setter function
)
import re


class AgentCore:
    """
    Smart Django CLI Agent
    - LLM generates code + explanation
    - Code goes to file
    - Full response prints to CLI
    - Supports both CLI mode (workspace.py) and Web UI mode (dynamic path)
    """

    def __init__(self, workspace_root=None):
        """
        Initialize AgentCore with optional workspace root
        
        Args:
            workspace_root: Optional path to project directory
                           - If None: Uses default from workspace.py (CLI mode)
                           - If provided: Uses custom path (Web UI mode)
        """
        self.llm = LLM()
        
        # Set workspace root dynamically
        if workspace_root:
            set_workspace_root(workspace_root)
            print(f"[DEBUG] Workspace set to: {workspace_root}")

    def run(self, user_input: str) -> str:
        # STEP 1: Detect mode and extract path FIRST
        mode = self._detect_mode(user_input)
        path = self._extract_path(user_input, mode)
        
        # DEBUG: Show detected mode
        print(f"\n[DEBUG] Detected mode: {mode}")
        print(f"[DEBUG] Extracted path: {path}")

        # STEP 2: If ANSWER MODE with file path, read the file content
        file_content = None
        if mode == "ANSWER" and path:
            try:
                file_content = read_file(path)
                print(f"[DEBUG] File content read successfully: {len(file_content)} chars")
            except FileToolError as e:
                print(f"[DEBUG] FileToolError: {e}")
                return f"❌ Cannot read file: {e}"
            except Exception as e:
                print(f"[DEBUG] Unexpected error: {e}")
                return f"❌ Error reading file: {e}"

        # STEP 3: Retrieve RAG context
        try:
            context, sources = retrieve_context(user_input, k=4)
        except Exception:
            context, sources = None, []

        # STEP 4: Build prompt with file content if available
        prompt = build_prompt(
            user_input=user_input, 
            context=context,
            file_content=file_content,
            file_path=path
        )
        
        # STEP 5: Generate LLM response
        raw = self.llm.generate(prompt).strip()

        # STEP 6: Handle ANSWER MODE (no file operations, just display)
        if mode == "ANSWER":
            cli_output = []
            
            # If reading a file, show the actual code first
            if file_content:
                cli_output.extend([
                    f"📄 Code from {path}:",
                    "=" * 60,
                    file_content,
                    "=" * 60,
                    "",
                    "📝 Explanation:",
                    "=" * 60
                ])
            
            cli_output.append(raw)
            
            if sources:
                cli_output.extend(["", "=" * 60, "📚 Sources:", "=" * 60])
                cli_output.extend(f"  • {s}" for s in sources)
            
            return "\n".join(cli_output)

        # STEP 7: Handle ACTION MODE (extract code and write to file)
        code = self._extract_code_only(raw)
        if not code:
            return "❌ No code detected in LLM output.\n\n" + raw

        if not path:
            return "❌ ACTION MODE requires a file path.\n\n" + raw

        # STEP 8: Remove duplicate imports if file exists
        try:
            existing = read_file(path)
            code = self._remove_duplicate_imports(existing, code)
        except Exception:
            pass  # file does not exist yet

        # STEP 9: Decide safe action (write new file or append to existing)
        try:
            read_file(path)
            action = "append_file"
        except Exception:
            action = "write_file"

        # STEP 10: Execute file action
        try:
            if action == "write_file":
                write_file(path, code)
                file_status = f"✅ File created: {path}"
            else:
                append_file(path, code)
                file_status = f"✅ Code appended to: {path}"

        except FileToolError as e:
            file_status = f"❌ [FILE ERROR] {e}"

        # STEP 11: Build CLI output
        cli_output = [file_status, "", "=" * 60, "📝 Full Response:", "=" * 60, raw]
        
        if sources:
            cli_output.extend(["", "=" * 60, "📚 Sources:", "=" * 60])
            cli_output.extend(f"  • {s}" for s in sources)

        return "\n".join(cli_output)

    # ---------------- HELPERS ---------------- #

    def _detect_mode(self, user_input: str) -> str:
        """
        Detect whether the user wants ACTION MODE or ANSWER MODE
        
        ANSWER MODE triggers:
        - 'read', 'explain', 'what is', 'how does', 'why'
        - 'difference between', 'when to use'
        - 'best practice', 'should I', 'help understand'
        
        ACTION MODE triggers:
        - 'create', 'write', 'generate', 'build', 'add'
        - 'implement', 'make', 'develop', 'insert'
        """
        lower_input = user_input.lower()
        
        # ANSWER MODE keywords (check these FIRST for read/explain)
        answer_keywords = [
            'read the code', 'read code', 'explain the code', 'explain code',
            'show me the code', 'what is', 'how does', 'why', 
            'explain', 'describe', 'tell me about',
            'difference', 'when to use', 'best practice',
            'help understand', 'understand', 'clarify'
        ]
        
        for keyword in answer_keywords:
            if keyword in lower_input:
                return "ANSWER"
        
        # Check for "read" alone (without "write")
        if 'read' in lower_input and 'write' not in lower_input:
            return "ANSWER"
        
        # ACTION MODE keywords (specific action verbs)
        action_keywords = [
            'create', 'write', 'generate', 'build', 'add',
            'implement', 'make', 'develop', 'insert',
            'update', 'modify', 'change', 'delete'
        ]
        
        for keyword in action_keywords:
            if keyword in lower_input:
                return "ACTION"
        
        # Default to ANSWER if no clear action verb
        return "ANSWER"

    def _extract_path(self, user_input: str, mode: str) -> str | None:
        """
        Extract file path from user input
        
        Only extract paths when context indicates an actual file operation:
        - ACTION MODE: Always try to extract path (user wants to write code)
        - ANSWER MODE: Only extract if explicit file reading keywords present
        """
        lower_input = user_input.lower()
        
        # In ANSWER MODE, only extract path if explicitly reading a specific file
        if mode == "ANSWER":
            # Check for explicit file reading indicators
            file_read_indicators = [
                'read the code in',
                'read code in', 
                'read the file',
                'read file',
                'show me the code in',
                'show code in',
                'explain the code in',
                'explain code in',
                'what does the code in',
                'open',
                'display the file'
            ]
            
            has_file_read_indicator = any(indicator in lower_input for indicator in file_read_indicators)
            
            if not has_file_read_indicator:
                # This is a general question about a concept
                return None
        
        # Extract path from tokens
        for token in user_input.split():
            if token.endswith((".py", ".html")):
                return token
        
        return None

    def _extract_code_only(self, text: str) -> str:
        """
        Extract code from LLM output - handles markdown and raw code
        Returns clean Python code without markdown backticks or explanations
        """
        # First, try to extract from markdown code blocks
        markdown_pattern = r'```(?:python)?\s*\n(.*?)\n```'
        markdown_matches = re.findall(markdown_pattern, text, re.DOTALL)
        
        if markdown_matches:
            # Use the first code block found
            code = markdown_matches[0].strip()
            return self._clean_extracted_code(code)
        
        # If no markdown, extract raw code
        lines = []
        recording = False
        
        for line in text.splitlines():
            stripped = line.strip()
            
            # Start recording when we hit code-like lines
            if stripped.startswith(("class ", "def ", "from ", "import ")):
                recording = True
            
            # Stop recording if we hit explanation markers
            if recording and (
                stripped.startswith(("Explanation:", "In order to", "Note:", "This"))
                or stripped.lower().startswith(("you can", "the above", "in this"))
            ):
                break
            
            if recording:
                lines.append(line)
        
        code = "\n".join(lines).strip()
        return self._clean_extracted_code(code)

    def _clean_extracted_code(self, code: str) -> str:
        """
        Clean extracted code:
        - Remove stray markdown backticks
        - Remove invalid lines
        - Fix indentation issues
        """
        lines = []
        
        for line in code.splitlines():
            stripped = line.strip()
            
            # Skip markdown artifacts
            if stripped in ['```', '```python', '```py']:
                continue
            
            # Skip explanation lines
            if any(stripped.startswith(marker) for marker in [
                'Explanation:', 'Note:', 'In this', 'The above', 'This model'
            ]):
                continue
            
            # Keep valid Python lines
            lines.append(line)
        
        # Validate the code has a proper class or function definition
        code_str = "\n".join(lines).strip()
        
        # Must contain at least one class or function definition
        if not any(keyword in code_str for keyword in ['class ', 'def ']):
            return ""
        
        return code_str

    def _remove_duplicate_imports(self, existing: str, new_code: str) -> str:
        """
        Removes imports from new_code that are already present in existing
        Only removes exact matches and keeps the rest intact
        """
        existing_lines = existing.splitlines()
        new_lines = new_code.splitlines()
        filtered_lines = []

        for line in new_lines:
            stripped = line.strip()
            
            # Skip empty lines at the start
            if not stripped and not filtered_lines:
                continue
            
            # Check if this line already exists
            if stripped and stripped not in [l.strip() for l in existing_lines]:
                filtered_lines.append(line)
            elif not stripped:
                # Keep blank lines within the code
                filtered_lines.append(line)

        return "\n".join(filtered_lines).strip()