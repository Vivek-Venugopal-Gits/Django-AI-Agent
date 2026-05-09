from agent.prompt import build_prompt
from llm.model import LLM
from rag.retriever import retrieve_context
from agent.file_tools import (
    read_file,
    write_file,
    append_file,
    FileToolError,
    set_workspace_root
)
import re
import os


class AgentCore:
    """
    Smart Django CLI Agent
    - LLM generates code + explanation
    - Code goes to file
    - Full response prints to CLI
    - Supports both CLI mode (workspace.py) and Web UI mode (dynamic path)
    """

    FILE_TYPE_HINTS = {
        "urls.py": (
            "TARGET FILE TYPE: urls.py\n"
            "You MUST produce a valid Django `urlpatterns` list using `path()` or `re_path()`.\n"
            "Always include FULL imports at the top:\n"
            "    from django.urls import path\n"
            "    from . import views\n"
            "Do NOT generate model classes, view functions, or form code.\n"
            "Output ONLY the urlpatterns Python code block with all imports at the top."
        ),
        "models.py": (
            "TARGET FILE TYPE: models.py\n"
            "You MUST produce Django model classes that inherit from `models.Model`.\n"
            "Always include `from django.db import models` at the top.\n"
            "Do NOT generate url patterns, view functions, or form code.\n"
            "Output ONLY the model class(es) with all imports at the top."
        ),
        "views.py": (
            "TARGET FILE TYPE: views.py\n"
            "You MUST produce Django view functions or class-based views.\n"
            "Always include FULL imports at the top:\n"
            "    from django.shortcuts import render, redirect\n"
            "Do NOT generate model classes, url patterns, or form code.\n"
            "Output ONLY the view function(s) or class(es) with all imports at the top."
        ),
        "forms.py": (
            "TARGET FILE TYPE: forms.py\n"
            "You MUST produce Django Form or ModelForm classes.\n"
            "Always include FULL imports at the top:\n"
            "    from django import forms\n"
            "    from .models import <ModelName>\n"
            "Do NOT generate model classes, url patterns, or view functions.\n"
            "Output ONLY the form class(es) with all imports at the top."
        ),
        "admin.py": (
            "TARGET FILE TYPE: admin.py\n"
            "You MUST register models using `admin.site.register()` or `@admin.register()`.\n"
            "Always include FULL imports at the top:\n"
            "    from django.contrib import admin\n"
            "    from .models import <ModelName>\n"
            "Do NOT generate model classes, url patterns, or view functions.\n"
            "Output ONLY the admin registration code with all imports at the top."
        ),
        "serializers.py": (
            "TARGET FILE TYPE: serializers.py\n"
            "You MUST produce DRF serializer classes using `serializers.ModelSerializer`.\n"
            "Always include FULL imports at the top.\n"
            "Output ONLY the serializer class(es) with all imports."
        ),
        "signals.py": (
            "TARGET FILE TYPE: signals.py\n"
            "You MUST produce Django signal handlers using the `@receiver` decorator.\n"
            "Always include FULL imports at the top.\n"
            "Output ONLY the signal handler code with all imports."
        ),
    }
    VALID_MARKERS = ['class ', 'def ', 'urlpatterns', 'import ', 'from ', 'admin.site.register']
    # Matches lines that are pure LLM garbage abbreviations like "f i c d @" or "f ic d @"
    # Strategy: strip the garbage PREFIX but keep any trailing real code on the same line
    # GARBAGE_PREFIX_PATTERN = re.compile(
    #     r'^(?:[a-z@]{1,2}\s+){2,}',
    #     re.IGNORECASE
    # )
    GARBAGE_PREFIX_PATTERN = re.compile(
        r'^(?:[a-z@]{1,2}\s+){2,}(?=[a-z@])',  # only strip if next char is also lowercase/symbol
        re.IGNORECASE
    )

    STOP_MARKERS = [
        "Explanation:", "Note:", "Summary:", "This will", "This code",
        "The code", "In this case", "The above", "By default", "You can now",
        "The user has", "This will allow"
    ]

    CODE_START_PREFIXES = (
        "from ", "import ", "class ", "def ", "@",
        "urlpatterns", "app_name", "admin.site",
    )

    def _get_file_type_hint(self, path: str | None) -> str | None:
        if not path:
            return None
        filename = path.replace("\\", "/").split("/")[-1].lower()
        return self.FILE_TYPE_HINTS.get(filename)

    def _extract_model_names_from_source(self, source_content: str) -> list[str]:
        return re.findall(r'^class\s+(\w+)\s*\(models\.Model\)', source_content, re.MULTILINE)

    def _extract_view_names_from_source(self, source_content: str) -> list[str]:
        """Extract all view function names from a views.py file."""
        return re.findall(r'^def\s+(\w+)\s*\(request', source_content, re.MULTILINE)


    def _build_urls_hint_from_views(self, view_names: list[str]) -> str:
        """
        Build an explicit urls.py generation hint from actual view names.
        This overrides the generic FILE_TYPE_HINTS['urls.py'] when a source views.py
        is available, so the LLM generates paths for real views only.
        """
        # Home view gets path('') — all others get path('name/')
        path_lines = []
        for name in view_names:
            url = '' if name == 'home' else f'{name}/'
            path_lines.append(f'    path("{url}", views.{name}, name="{name}"),')
        paths_str = '\n'.join(path_lines)

        return (
            "TARGET FILE TYPE: urls.py\n"
            f"The source views.py contains EXACTLY these view functions: {view_names}\n"
            "You MUST generate url patterns for ONLY these views — do NOT invent or add any others.\n"
            "Use ONLY the view names listed above.\n"
            "Always include:\n"
            "    from django.urls import path\n"
            "    from . import views\n"
            f"Generate this exact urlpatterns list:\n"
            f"urlpatterns = [\n{paths_str}\n]"
        )

    def _clean_garbage_line(self, line: str) -> str:
        """
        Strip garbage abbreviation prefix from a line but keep any real code after it.
        e.g. "f i c d @ admin.site.register(Student)" -> "admin.site.register(Student)"
        e.g. "from django.contrib import admin"        -> unchanged
        """
        stripped = self.GARBAGE_PREFIX_PATTERN.sub('', line).strip()
        # If stripping left nothing or just punctuation, return empty
        if not stripped or stripped in ('@', '#'):
            return ''
        return stripped

    def __init__(self, workspace_root: str | None = None):
        if workspace_root:
            workspace_root = workspace_root.strip().rstrip('>"\'')  # strip FIRST
            workspace_root = os.path.abspath(workspace_root)
            if not os.path.exists(workspace_root):
                raise ValueError(f"Invalid workspace root: {workspace_root!r}")
            set_workspace_root(workspace_root)
        self.workspace_root = workspace_root
        self.llm = LLM()

    def _fix_indentation(self, code: str) -> str:
        lines = code.splitlines()
        result = []
        # Stack tracks (indent_level_of_header, body_indent_string)
        indent_stack: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                result.append("")
                continue

            is_block_header = bool(
                re.match(r'^(class |def |async def )\w', stripped)
                and stripped.endswith(":")
            )

            if is_block_header:
                leading = len(line) - len(line.lstrip())
                # Pop stack entries deeper than current level
                while indent_stack and len(indent_stack[-1]) >= leading + 4:
                    indent_stack.pop()
                result.append(line)
                indent_stack.append(" " * (leading + 4))
                continue

            if indent_stack:
                leading = len(line) - len(line.lstrip())
                if leading == 0:
                    line = indent_stack[-1] + stripped
            
            result.append(line)

        return "\n".join(result)

    def run(self, user_input: str) -> str:
        # STEP 1: Detect mode and extract path
        mode = self._detect_mode(user_input)
        path = self._extract_path(user_input, mode)

        print(f"\n[DEBUG] Detected mode: {mode}")
        print(f"[DEBUG] Extracted path: {path}")

        # STEP 2: Source file detection — only for "from X ... to/into Y" pattern
        source_file_content = None
        source_file_path = None

        if mode == "ACTION":
            tokens = user_input.split()
            lower_tokens = [t.lower() for t in tokens]
            has_target_keyword = any(t in lower_tokens for t in ['to', 'into', 'inside'])

            if has_target_keyword:
                for i, token in enumerate(tokens):
                    if token.lower() == 'from' and i + 1 < len(tokens):
                        potential_source = tokens[i + 1]
                        if potential_source.endswith((".py", ".html")) and potential_source != path:
                            source_file_path = potential_source
                            print(f"[DEBUG] Source file detected: {source_file_path}")
                            try:
                                source_file_content = read_file(source_file_path)
                                print(f"[DEBUG] Source file read: {len(source_file_content)} chars")
                            except FileToolError as e:
                                print(f"[DEBUG] Could not read source file: {e}")
                            break

        # STEP 3: ANSWER MODE — read target file content
        file_content = None
        if mode == "ANSWER" and path:
            try:
                file_content = read_file(path)
            except FileToolError as e:
                return f"❌ Cannot read file: {e}"
            except Exception as e:
                return f"❌ Error reading file: {e}"

        # STEP 4: RAG context
        try:
            context, sources = retrieve_context(user_input, k=3)
        except Exception:
            context, sources = None, []

        # STEP 5: Build augmented prompt with file-type hint
        file_type_hint = self._get_file_type_hint(path)
        augmented_input = user_input

        if file_type_hint and mode == "ACTION":
            target_filename = path.replace("\\", "/").split("/")[-1].lower() if path else ""

            if target_filename == "urls.py" and source_file_content:
                # urls.py + source views.py: extract real view names and build explicit hint
                view_names = self._extract_view_names_from_source(source_file_content)
                if view_names:
                    print(f"[DEBUG] Views found in source: {view_names}")
                    file_type_hint = self._build_urls_hint_from_views(view_names)
                else:
                    print("[DEBUG] No view functions found in source file")

            elif target_filename == "admin.py" and source_file_content:
                # admin.py: inject actual model names so LLM knows what to register
                model_names = self._extract_model_names_from_source(source_file_content)
                if model_names:
                    names_str = ", ".join(model_names)
                    file_type_hint += (
                        f"\n\nModels to register (from source file): {names_str}\n"
                        f"Use: from .models import {names_str}\n"
                        f"Then: admin.site.register({model_names[0]}) for each model."
                    )

            augmented_input = f"{file_type_hint}\n\nUser request: {user_input}"

        prompt = build_prompt(
            user_input=augmented_input,
            context=context,
            file_content=file_content or source_file_content,
            file_path=path,
            source_file_path=source_file_path
        )

        # STEP 6: Generate LLM response
        raw = self.llm.generate(prompt).strip()

        # STEP 7: ANSWER MODE output
        if mode == "ANSWER":
            cli_output = []
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

        # STEP 8: ACTION MODE — extract and write code
        code = self._extract_code_only(raw)
        if not code:
            return "❌ No code detected in LLM output.\n\n" + raw

        if not path:
            return "❌ ACTION MODE requires a file path.\n\n" + raw

        # STEP 9: File exists? Use smart merge for urls.py, else dedup-and-append
        existing_content = None
        merged_content = None
        try:
            existing_content = read_file(path)
            is_urls_file = path.replace("\\", "/").endswith("urls.py")

            if is_urls_file and "urlpatterns" in existing_content and "urlpatterns" in code:
                # Smart merge: insert new paths into existing urlpatterns list
                merged_content = self._merge_urlpatterns(existing_content, code)
                action = "update_file" if merged_content else "append_file"
            else:
                code = self._remove_duplicate_imports(existing_content, code)
                action = "append_file"
        except Exception:
            action = "write_file"

        # STEP 10: Execute file action
        try:
            if action == "write_file":
                write_file(path, code)
                file_status = f"✅ File created: {path}"
            elif action == "update_file" and merged_content:
                from agent.file_tools import update_file
                update_file(path, merged_content)
                file_status = f"✅ URL paths merged into: {path}"
            else:
                append_file(path, code)
                file_status = f"✅ Code appended to: {path}"
        except FileToolError as e:
            file_status = f"❌ [FILE ERROR] {e}"

        # STEP 11: CLI output
        cli_output = [file_status, "", "=" * 60, "📝 Full Response:", "=" * 60, raw]
        if sources:
            cli_output.extend(["", "=" * 60, "📚 Sources:", "=" * 60])
            cli_output.extend(f"  • {s}" for s in sources)
        return "\n".join(cli_output)

    # ---------------- HELPERS ---------------- #

    def _merge_urlpatterns(self, existing: str, new_code: str):
        """
        Merge new path() entries into the existing urlpatterns list in-place.
        Returns merged file string, or None if merging is not possible.
        """
        existing_block = re.search(r'urlpatterns\s*=\s*\[(.*?)\]', existing, re.DOTALL)
        new_block = re.search(r'urlpatterns\s*=\s*\[(.*?)\]', new_code, re.DOTALL)

        if not existing_block or not new_block:
            return None

        def extract_path_lines(block_content):
            lines = []
            for line in block_content.splitlines():
                s = line.strip().rstrip(',')
                if s.startswith(('path(', 're_path(')):
                    lines.append('    ' + s)
            return lines

        existing_paths = extract_path_lines(existing_block.group(1))
        new_paths = extract_path_lines(new_block.group(1))

        existing_set = {l.strip() for l in existing_paths}
        to_add = [l for l in new_paths if l.strip() not in existing_set]

        if not to_add:
            print("[DEBUG] No new url paths to add — all already exist")
            return existing

        all_paths = existing_paths + to_add
        paths_str = ",\n".join(all_paths) + ","

        merged = re.sub(
            r'urlpatterns\s*=\s*\[.*?\]',
            f'urlpatterns = [\n{paths_str}\n]',
            existing,
            flags=re.DOTALL
        )

        existing_imports = {
            l.strip() for l in existing.splitlines()
            if l.strip().startswith(('from ', 'import '))
        }
        new_imports = [
            l for l in new_code.splitlines()
            if l.strip().startswith(('from ', 'import '))
            and l.strip() not in existing_imports
        ]
        if new_imports:
            merged = "\n".join(new_imports) + "\n" + merged

        print(f"[DEBUG] urlpatterns merged: added {len(to_add)} new path(s)")
        return merged


    def _detect_mode(self, user_input: str) -> str:
        lower_input = user_input.lower()

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

        if 'read' in lower_input and 'write' not in lower_input:
            return "ANSWER"

        action_keywords = [
            'create', 'write', 'generate', 'build', 'add',
            'implement', 'make', 'develop', 'insert',
            'update', 'modify', 'change', 'delete', 'register'
        ]
        for keyword in action_keywords:
            if keyword in lower_input:
                return "ACTION"

        return "ANSWER"

    def _extract_path(self, user_input: str, mode: str) -> str | None:
        lower_input = user_input.lower()

        if mode == "ANSWER":
            file_read_indicators = [
                'read the code in', 'read code in', 'read the file', 'read file',
                'show me the code in', 'show code in', 'explain the code in',
                'explain code in', 'what does the code in', 'open', 'display the file'
            ]
            if not any(indicator in lower_input for indicator in file_read_indicators):
                return None

        tokens = user_input.split()

        # Strategy 1: "into/to/inside <file>"
        for i, token in enumerate(tokens):
            if token.lower() in ('into', 'to', 'inside') and i + 1 < len(tokens):
                next_token = tokens[i + 1]
                if next_token.endswith((".py", ".html")):
                    print(f"[DEBUG] Target file found after '{token}': {next_token}")
                    return next_token

        # Strategy 2: "in <file>" with action context
        for i, token in enumerate(tokens):
            if token.lower() == 'in' and i + 1 < len(tokens):
                next_token = tokens[i + 1]
                if next_token.endswith((".py", ".html")):
                    action_context = any(
                        keyword in lower_input[:lower_input.find('in')]
                        for keyword in ['create', 'write', 'add', 'register', 'make']
                    )
                    if action_context:
                        print(f"[DEBUG] Target file found after 'in': {next_token}")
                        return next_token

        # Strategy 3: last .py/.html file mentioned
        all_files = [t for t in tokens if t.endswith((".py", ".html"))]
        if all_files:
            print(f"[DEBUG] Using last file mentioned: {all_files[-1]}")
            return all_files[-1]

        return None

    def _normalize_collapsed_code(self, text: str) -> str:
        """
        Fix LLM output where multiple statements are collapsed onto one line.
        e.g. "class Foo:     x = 1     y = 2" → proper multi-line with indent
        """
        # Split on 4+ spaces that appear to separate statements
        # Only activate when we detect a class/def header mid-text
        if not re.search(r'(class |def )\w.*:\s{2,}\w', text):
            return text  # Nothing collapsed, skip

        # Insert real newlines before known statement starters that follow spaces
        text = re.sub(
            r'(?<=:)\s{2,}(?=(from |import |class |def |    \w|\w+\s*=))',
            '\n',
            text
        )
        # Insert newline+indent before field assignments after a class header
        text = re.sub(
            r'(?<=[^\n])\s{4,}(\w+\s*=\s*models\.)',
            r'\n    \1',
            text
        )
        return text

    def _expand_collapsed_lines(self, text: str) -> str:
        """
        Fix LLM output where multiple Python statements are collapsed onto one line.
        Uses a state machine to correctly handle nested blocks like class Meta:.
        """
        # Step 1: Insert newlines before top-level keywords after 2+ spaces
        # Handles: "from X  class Foo" → "from X\nclass Foo"
        text = re.sub(
            r'(?<=\S)  +(?=(from |import |class |def |async def |@))',
            '\n',
            text
        )

        # Step 2: Per-line expansion — if a line contains a block header followed
        # by collapsed body content, expand it using a depth-aware state machine
        expanded_lines = []
        for line in text.splitlines():
            if not re.search(r'(?:class |def )\w[^:]*:\s{2,}\S', line):
                # No collapsed block on this line — keep as-is
                expanded_lines.append(line)
                continue

            # This line has a collapsed block — expand it
            base_indent = len(line) - len(line.lstrip())
            expanded_lines.extend(
                self._expand_single_collapsed_line(line.strip(), base_indent)
            )

        return "\n".join(expanded_lines)


    def _expand_single_collapsed_line(self, text: str, base_indent: int) -> list[str]:
        """
        Expand a single collapsed line like:
        "class Foo:     class Meta:         model = X         fields = Y"
        into properly indented lines using a token state machine.

        Returns a list of correctly indented lines.
        """
        # Split on 2+ spaces — these are the statement separators
        # but we must NOT split inside string literals
        tokens = self._split_on_spaces(text)
        
        result_lines: list[str] = []
        indent_level = base_indent  # current indent in spaces
        pending: list[str] = []     # tokens accumulating into current statement

        def flush(next_indent: int | None = None):
            """Emit the accumulated tokens as one line, then set new indent."""
            nonlocal indent_level
            if pending:
                result_lines.append(" " * indent_level + " ".join(pending))
                pending.clear()
            if next_indent is not None:
                indent_level = next_indent

        i = 0
        while i < len(tokens):
            token = tokens[i]
            if not token.strip():
                i += 1
                continue

            # Check if this token starts a new statement
            is_new_statement = (
                i > 0 and
                re.match(
                    r'^(from|import|class|def|async|@|\w+\s*=)',
                    token.strip()
                )
            )

            if is_new_statement:
                # Flush previous statement first
                # Determine if previous statement was a block header
                prev = " ".join(pending).strip()
                if prev.endswith(":") and re.match(r'^(class |def |async def )', prev):
                    flush(next_indent=indent_level + 4)
                else:
                    flush(next_indent=indent_level)

            pending.append(token.strip())
            i += 1

        # Flush final statement
        flush()
        return result_lines


    def _split_on_spaces(self, text: str) -> list[str]:
        """
        Split text on runs of 2+ spaces, but not inside string literals.
        Returns list of non-empty tokens.
        """
        tokens = []
        current = []
        in_string = None  # None, '"', or "'"
        i = 0

        while i < len(text):
            ch = text[i]

            if in_string:
                current.append(ch)
                if ch == in_string and (i == 0 or text[i-1] != '\\'):
                    in_string = None
                i += 1
                continue

            if ch in ('"', "'"):
                in_string = ch
                current.append(ch)
                i += 1
                continue

            # Check for 2+ space separator
            if ch == ' ' and i + 1 < len(text) and text[i+1] == ' ':
                # Consume all spaces
                token = "".join(current).strip()
                if token:
                    tokens.append(token)
                current = []
                while i < len(text) and text[i] == ' ':
                    i += 1
                continue

            current.append(ch)
            i += 1

        token = "".join(current).strip()
        if token:
            tokens.append(token)

        return tokens

    def _preprocess_llm_output(self, text: str) -> str:
        """
        Clean raw LLM output before code extraction:
        1. Strip "In ACTION/ANSWER MODE:" labels
        2. Strip garbage abbreviation PREFIXES (keep trailing real code on same line)
        3. Strip explanation prose that follows the code
        """
        text = self._normalize_collapsed_code(text)
        text = self._expand_collapsed_lines(text)
        # Step 1: remove mode labels
        text = re.sub(
            r'In\s+(?:ACTION|ANSWER)\s+MODE\s*:\s*',
            '\n',
            text,
            flags=re.IGNORECASE
        )

        # Step 2: clean garbage prefixes line by line (keep trailing code)
        cleaned_lines = []
        for line in text.splitlines():
            result = self._clean_garbage_line(line)
            if result != line.strip():
                print(f"[DEBUG] Cleaned garbage: {repr(line.strip())} -> {repr(result)}")
            cleaned_lines.append(result)

        return "\n".join(cleaned_lines)

    def _extract_code_only(self, text: str) -> str:
        """
        Extract ALL code pieces from LLM output and merge them into one clean block.

        Key insight: the LLM often splits imports and code across different parts
        of its response (e.g. register() call in raw text, imports in a markdown block).
        We collect EVERYTHING and merge: imports first, then the rest.
        """
        text = self._preprocess_llm_output(text)

        # Collect all code pieces from every source
        all_pieces: list[str] = []

        # Source A: all markdown code blocks (not just the first one)
        markdown_pattern = r'```(?:python)?\s*\n(.*?)\n```'
        for block in re.findall(markdown_pattern, text, re.DOTALL):
            block = block.strip()
            if block:
                all_pieces.append(block)
                print(f"[DEBUG] Found markdown block: {len(block)} chars")

        # Source B: raw code outside markdown blocks
        text_no_markdown = re.sub(markdown_pattern, '\n', text, flags=re.DOTALL)
        raw_lines = []
        found_start = False
        for line in text_no_markdown.splitlines():
            stripped = line.strip()
            if not found_start:
                if stripped.startswith(self.CODE_START_PREFIXES):
                    found_start = True
                else:
                    continue
            if any(stripped.startswith(m) for m in self.STOP_MARKERS):
                break
            raw_lines.append(line)

        raw_code = "\n".join(raw_lines).strip()
        if raw_code:
            all_pieces.append(raw_code)
            print(f"[DEBUG] Found raw code: {len(raw_code)} chars")

        if not all_pieces:
            print("[DEBUG] ❌ No code pieces found")
            return ""

        # Merge all pieces: deduplicated imports first, then all other code
        import_lines: list[str] = []
        other_lines: list[str] = []
        seen_imports: set[str] = set()
        seen_other: set[str] = set()

        for piece in all_pieces:
            for line in piece.splitlines():
                s = line.strip()
                if not s:
                    continue
                # Skip markdown fences that slipped through
                if s in ('```', '```python', '```py'):
                    continue
                if s.startswith(("from ", "import ")):
                    if s not in seen_imports:
                        seen_imports.add(s)
                        import_lines.append(line)
                else:
                    if s not in seen_other:
                        seen_other.add(s)
                        other_lines.append(line)

        merged = "\n".join(import_lines + [""] + other_lines).strip() if import_lines else "\n".join(other_lines).strip()
        cleaned = self._clean_extracted_code(merged)
    
        if cleaned:
            cleaned = self._fix_indentation(cleaned)   # ← add this line
            print(f"[DEBUG] Final merged code: {len(cleaned)} chars")
            return cleaned

        print("[DEBUG] ❌ No valid code after merge")
        return ""

    def _clean_extracted_code(self, code: str) -> str:
        """Validate extracted code contains real Python content."""
        lines = []
        for line in code.splitlines():
            stripped = line.strip()
            if stripped in ('```', '```python', '```py'):
                continue
            if any(stripped.startswith(m) for m in [
                'Explanation:', 'Note:', 'In this', 'The above', 'This model',
                'The user has', 'This will allow'
            ]):
                break  # Stop at explanation prose
            lines.append(line)

        code_str = "\n".join(lines).strip()

        VALID_MARKERS = ['class ', 'def ', 'urlpatterns', 'import ', 'admin.site.register']
        if not any(keyword in code_str for keyword in VALID_MARKERS):
            return ""

        return code_str

    def _remove_duplicate_imports(self, existing: str, new_code: str) -> str:
        """Remove imports from new_code already present in existing file."""
        existing_line_set = {l.strip() for l in existing.splitlines()}
        filtered_lines = []

        for line in new_code.splitlines():
            stripped = line.strip()
            if not stripped and not filtered_lines:
                continue
            if not stripped or stripped not in existing_line_set:
                filtered_lines.append(line)

        return "\n".join(filtered_lines).strip()
    
    def _fix_indentation(self, code: str) -> str:
        lines = code.splitlines()
        result = []
        # Stack tracks (indent_level_of_header, body_indent_string)
        indent_stack: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                result.append("")
                continue

            is_block_header = bool(
                re.match(r'^(class |def |async def )\w', stripped)
                and stripped.endswith(":")
            )

            if is_block_header:
                leading = len(line) - len(line.lstrip())
                # Pop stack entries deeper than current level
                while indent_stack and len(indent_stack[-1]) >= leading + 4:
                    indent_stack.pop()
                result.append(line)
                indent_stack.append(" " * (leading + 4))
                continue

            if indent_stack:
                leading = len(line) - len(line.lstrip())
                if leading == 0:
                    line = indent_stack[-1] + stripped
            
            result.append(line)

        return "\n".join(result)