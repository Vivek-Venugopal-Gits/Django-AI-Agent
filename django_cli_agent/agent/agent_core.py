# from agent.prompt import build_prompt
# from llm.model import LLM
# from rag.retriever import retrieve_context
# from agent.file_tools import (
#     read_file,
#     write_file,
#     append_file,
#     FileToolError,
#     set_workspace_root  # NEW: Import the setter function
# )
# import re


# class AgentCore:
#     """
#     Smart Django CLI Agent
#     - LLM generates code + explanation
#     - Code goes to file
#     - Full response prints to CLI
#     - Supports both CLI mode (workspace.py) and Web UI mode (dynamic path)
#     """

#     def __init__(self, workspace_root=None):
#         """
#         Initialize AgentCore with optional workspace root
        
#         Args:
#             workspace_root: Optional path to project directory
#                            - If None: Uses default from workspace.py (CLI mode)
#                            - If provided: Uses custom path (Web UI mode)
#         """
#         self.llm = LLM()
        
#         # Set workspace root dynamically
#         if workspace_root:
#             set_workspace_root(workspace_root)
#             print(f"[DEBUG] Workspace set to: {workspace_root}")

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
#                 # This is a general question about a concept
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
        
#         # If no markdown, extract raw code
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
            
#             # Skip explanation lines
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

        # STEP 2: Check if user mentions a source file to read from
        # Example: "register models from students/models.py into students/admin.py"
        source_file_content = None
        source_file_path = None
        
        if mode == "ACTION":
            # Look for source file patterns like "from <file>", "inside <file>"
            source_keywords = ['from', 'inside']
            tokens = user_input.split()
            
            for i, token in enumerate(tokens):
                if token.lower() in source_keywords and i + 1 < len(tokens):
                    potential_source = tokens[i + 1]
                    if potential_source.endswith((".py", ".html")) and potential_source != path:
                        source_file_path = potential_source
                        print(f"[DEBUG] Source file detected: {source_file_path}")
                        try:
                            source_file_content = read_file(source_file_path)
                            print(f"[DEBUG] Source file read successfully: {len(source_file_content)} chars")
                        except FileToolError as e:
                            print(f"[DEBUG] Could not read source file: {e}")
                        break

        # STEP 3: If ANSWER MODE with file path, read the file content
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

        # STEP 4: Retrieve RAG context
        try:
            context, sources = retrieve_context(user_input, k=4)
        except Exception:
            context, sources = None, []

        # STEP 5: Build prompt with file content if available
        prompt = build_prompt(
            user_input=user_input, 
            context=context,
            file_content=file_content or source_file_content,  # Use source file if no answer file
            file_path=path,
            source_file_path=source_file_path  # Pass source file info to prompt
        )
        
        # STEP 6: Generate LLM response
        raw = self.llm.generate(prompt).strip()

        # STEP 7: Handle ANSWER MODE (no file operations, just display)
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

        # STEP 8: Handle ACTION MODE (extract code and write to file)
        code = self._extract_code_only(raw)
        if not code:
            return "❌ No code detected in LLM output.\n\n" + raw

        if not path:
            return "❌ ACTION MODE requires a file path.\n\n" + raw

        # STEP 9: Remove duplicate imports if file exists
        try:
            existing = read_file(path)
            code = self._remove_duplicate_imports(existing, code)
        except Exception:
            pass  # file does not exist yet

        # STEP 10: Decide safe action (write new file or append to existing)
        try:
            read_file(path)
            action = "append_file"
        except Exception:
            action = "write_file"

        # STEP 11: Execute file action
        try:
            if action == "write_file":
                write_file(path, code)
                file_status = f"✅ File created: {path}"
            else:
                append_file(path, code)
                file_status = f"✅ Code appended to: {path}"

        except FileToolError as e:
            file_status = f"❌ [FILE ERROR] {e}"

        # STEP 12: Build CLI output
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
        
        Priority for ACTION MODE:
        1. Look for "into <file>" or "to <file>" (target file)
        2. Look for "in <file>" only if no target found (source file for reading)
        3. Fall back to any .py/.html file found
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
        
        # ACTION MODE: Extract target file path intelligently
        tokens = user_input.split()
        
        # Strategy 1: Look for "into <file>" or "to <file>" pattern (TARGET FILE)
        # Example: "register models into students/admin.py"
        target_keywords = ['into', 'to', 'inside']
        for i, token in enumerate(tokens):
            if token.lower() in target_keywords and i + 1 < len(tokens):
                next_token = tokens[i + 1]
                if next_token.endswith((".py", ".html")):
                    print(f"[DEBUG] Target file found after '{token}': {next_token}")
                    return next_token
        
        # Strategy 2: Look for "in <file>" pattern (might be source or target)
        # Only use this if no clear target was found above
        # Example: "create view in students/views.py"
        for i, token in enumerate(tokens):
            if token.lower() == 'in' and i + 1 < len(tokens):
                next_token = tokens[i + 1]
                if next_token.endswith((".py", ".html")):
                    # Check if this looks like a target (create/write/add context)
                    action_context = any(keyword in lower_input[:lower_input.find('in')] 
                                       for keyword in ['create', 'write', 'add', 'register', 'make'])
                    if action_context:
                        print(f"[DEBUG] Target file found after 'in': {next_token}")
                        return next_token
        
        # Strategy 3: Fall back to any .py or .html file (last resort)
        all_files = [token for token in tokens if token.endswith((".py", ".html"))]
        if all_files:
            # Prefer the LAST file mentioned (usually the target)
            target_file = all_files[-1]
            print(f"[DEBUG] Using last file mentioned: {target_file}")
            return target_file
        
        return None

    def _extract_code_only(self, text: str) -> str:
        """
        Extract code from LLM output - handles markdown and raw code
        Returns clean Python code without markdown backticks or explanations
        
        AGGRESSIVE EXTRACTION: Works even when LLM ignores format rules
        """
        # Strategy 1: Try markdown code blocks first (most common)
        markdown_pattern = r'```(?:python)?\s*\n(.*?)\n```'
        markdown_matches = re.findall(markdown_pattern, text, re.DOTALL)
        
        if markdown_matches:
            # Use the first code block found
            code = markdown_matches[0].strip()
            cleaned = self._clean_extracted_code(code)
            if cleaned:
                print(f"[DEBUG] Extracted code from markdown block: {len(cleaned)} chars")
                return cleaned
        
        # Strategy 2: Extract raw Python code (no markdown)
        lines = []
        recording = False
        found_code_start = False
        
        for line in text.splitlines():
            stripped = line.strip()
            
            # Detect start of actual Python code
            if not found_code_start:
                # Skip everything until we hit actual Python code
                if stripped.startswith(("from ", "import ", "class ", "def ", "@")):
                    found_code_start = True
                    recording = True
                else:
                    continue
            
            # Once recording, stop at explanation markers
            if recording:
                # Stop conditions
                stop_markers = [
                    "Explanation:", "Note:", "Summary:", "This will",
                    "This code", "The code", "In this case",
                    "The above", "By default", "You can now"
                ]
                
                if any(stripped.startswith(marker) for marker in stop_markers):
                    break
                
                # Also stop if we hit another "In ACTION/ANSWER MODE" text
                if stripped.startswith("In ") and "MODE" in stripped:
                    break
                
                lines.append(line)
        
        code = "\n".join(lines).strip()
        cleaned = self._clean_extracted_code(code)
        
        if cleaned:
            print(f"[DEBUG] Extracted raw code: {len(cleaned)} chars")
            return cleaned
        
        # Strategy 3: AGGRESSIVE - Look for any Python-like code blocks
        # This catches cases where LLM adds extra text before code
        print("[DEBUG] Using aggressive extraction (LLM didn't follow format)")
        
        all_lines = text.splitlines()
        best_code_block = ""
        current_block = []
        in_code = False
        
        for i, line in enumerate(all_lines):
            stripped = line.strip()
            
            # Start of code block
            if stripped.startswith(("from ", "import ", "class ", "def ", "@admin")):
                if not in_code:
                    in_code = True
                    current_block = [line]
                else:
                    current_block.append(line)
            
            # Continue code block
            elif in_code:
                # Check if still code (indentation, empty lines, or code-like syntax)
                if (line.startswith((" ", "\t")) or 
                    not stripped or 
                    stripped.startswith(("admin.", "models.", "return ", "if ", "for ", "with "))):
                    current_block.append(line)
                else:
                    # End of code block
                    in_code = False
                    block_code = "\n".join(current_block).strip()
                    
                    # Keep the longest/best code block found
                    if len(block_code) > len(best_code_block):
                        best_code_block = block_code
                    
                    current_block = []
        
        # Don't forget the last block
        if current_block:
            block_code = "\n".join(current_block).strip()
            if len(block_code) > len(best_code_block):
                best_code_block = block_code
        
        if best_code_block:
            cleaned = self._clean_extracted_code(best_code_block)
            if cleaned:
                print(f"[DEBUG] Aggressively extracted code: {len(cleaned)} chars")
                return cleaned
        
        print("[DEBUG] ❌ No code could be extracted")
        return ""

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