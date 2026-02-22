def _get_action_rules(file_path: str | None) -> str:
    """
    Return only the rules relevant to the target file type.
    Reduces prompt size significantly vs. sending all rules every time.
    """
    if not file_path:
        return (
            "GENERAL CODE RULES:\n"
            "- Start your response with actual code (from/import/class/def/@ statements)\n"
            "- Output ONLY valid Django code\n"
            "- Do NOT duplicate imports\n"
            "- Use Django best practices and PEP 8\n\n"
        )

    path_lower = file_path.lower()

    if "models.py" in path_lower:
        return (
            "MODEL RULES:\n"
            "- Always inherit from models.Model\n"
            "- Use appropriate field types (CharField, IntegerField, etc.)\n"
            "- Add max_length to CharField (required)\n"
            "- Use blank=True for optional fields, null=True for database NULL\n"
            "- Do NOT add Meta class unless explicitly requested\n"
            "- Use related_name for ForeignKey and ManyToMany relationships\n"
            "- Use on_delete parameter for ForeignKey (CASCADE, PROTECT, SET_NULL)\n"
            "- Use auto_now_add for created timestamps, auto_now for updated\n"
            "- Implement __str__ method only if requested\n\n"
        )

    if "views.py" in path_lower:
        return (
            "VIEW RULES:\n"
            "- Use class-based views when appropriate (ListView, DetailView, etc.)\n"
            "- Use function-based views for simple operations\n"
            "- Always handle HTTP methods correctly (GET, POST, PUT, DELETE)\n"
            "- Use get_object_or_404 for object retrieval\n"
            "- Return proper HttpResponse or JsonResponse\n"
            "- Use decorators appropriately (@login_required, @require_http_methods)\n"
            "- Handle form validation in POST requests\n\n"
        )

    if "urls.py" in path_lower:
        return (
            "URL RULES:\n"
            "- Use path() for modern Django (not url())\n"
            "- Always name URL patterns with name parameter\n"
            "- Use angle brackets for path converters (<int:pk>, <str:slug>)\n"
            "- Group related URLs with include()\n"
            "- Use app_name for namespacing when needed\n\n"
        )

    if "admin.py" in path_lower:
        return (
            "ADMIN RULES:\n"
            "- Register models with @admin.register decorator or admin.site.register\n"
            "- Inherit from admin.ModelAdmin\n"
            "- Use list_display for list view columns\n"
            "- Use list_filter for filterable fields\n"
            "- Use search_fields for searchable fields\n"
            "- When registering multiple models, import all models first\n"
            "- Use relative imports (.models) for same-directory imports\n\n"
        )

    if "forms.py" in path_lower:
        return (
            "FORM RULES:\n"
            "- Inherit from forms.Form or forms.ModelForm\n"
            "- Use ModelForm for model-based forms\n"
            "- Define fields explicitly in forms.Form\n"
            "- Use Meta.fields or Meta.exclude in ModelForm\n"
            "- Implement clean_<field> methods for field validation\n"
            "- Implement clean() for cross-field validation\n\n"
        )

    if "serializers.py" in path_lower:
        return (
            "SERIALIZER RULES (DRF):\n"
            "- Inherit from serializers.ModelSerializer or serializers.Serializer\n"
            "- Use Meta.fields = '__all__' or list specific fields\n"
            "- Use read_only_fields for non-editable fields\n"
            "- Implement validate_<field> for field validation\n"
            "- Implement validate() for object-level validation\n\n"
        )

    if ".html" in path_lower:
        return (
            "TEMPLATE RULES:\n"
            "- Use Django template syntax {{ }}, {% %}\n"
            "- Use {% load static %} for static files\n"
            "- Use {% url %} tag for URL reversing\n"
            "- Extend base templates with {% extends %}\n"
            "- Define blocks with {% block %}\n"
            "- Use CSRF protection ({% csrf_token %} in forms)\n\n"
        )

    # Fallback for unknown file types
    return (
        "GENERAL CODE RULES:\n"
        "- Start your response with actual code (from/import/class/def/@ statements)\n"
        "- Output ONLY valid Django code\n"
        "- Do NOT duplicate imports\n"
        "- Use Django best practices and PEP 8\n\n"
    )


def build_prompt(
    user_input: str,
    context: str | None = None,
    file_content: str | None = None,
    file_path: str | None = None,
    source_file_path: str | None = None
) -> str:

    # Core system instruction — kept concise and universal
    system_instruction = (
        "You are a Django AI Agent with two modes:\n\n"

        "ANSWER MODE → explanation only, no code generation.\n"
        "Use when: user says explain, read, describe, what is, how does, why.\n\n"

        "ACTION MODE → code FIRST, then a brief explanation.\n"
        "Use when: user says create, write, generate, build, add, implement, register.\n\n"

        "═══ ACTION MODE FORMAT (STRICT) ═══\n"
        "- Your FIRST character MUST be one of: f i c d @  (from/import/class/def/@)\n"
        "- NO preamble, NO 'In ACTION MODE', NO markdown ``` blocks\n"
        "- NO # file/path.py comments at the top\n"
        "- After the code: one blank line, then 'Explanation:'\n\n"

        "✅ CORRECT:\n"
        "from django.db import models\n\n"
        "class School(models.Model):\n"
        "    school_name = models.CharField(max_length=200)\n\n"
        "Explanation: Creates a School model...\n\n"

        "❌ WRONG (starts with explanation):\n"
        "To create a School model, you need to...\n\n"

        "❌ WRONG (uses markdown):\n"
        "```python\nclass School...\n```\n\n"

        "MULTI-FILE: When source file content is provided, read it, then generate\n"
        "code for the TARGET file only.\n\n"
    )

    # Add file-type-specific rules (much smaller than sending all rules)
    action_rules = _get_action_rules(file_path)

    prompt_parts = [system_instruction, action_rules]

    # Add source file content (multi-file operations)
    if source_file_path and file_content:
        prompt_parts.append(f"--- SOURCE FILE: {source_file_path} ---")
        prompt_parts.append(file_content)
        prompt_parts.append("--- END SOURCE FILE ---\n")
        if file_path:
            prompt_parts.append(f"TARGET FILE: {file_path}\n")

    # Add file content (ANSWER MODE file reading)
    elif file_content and file_path:
        prompt_parts.append(f"--- FILE: {file_path} ---")
        prompt_parts.append(file_content)
        prompt_parts.append("--- END FILE ---\n")

    # Add RAG context — limit to 1500 chars to avoid bloating prompt
    if context:
        truncated_context = context[:1500] + "..." if len(context) > 1500 else context
        prompt_parts.append("--- DJANGO DOCS CONTEXT ---")
        prompt_parts.append(truncated_context)
        prompt_parts.append("--- END CONTEXT ---\n")

    prompt_parts.append(f"User Request: {user_input}")

    return "\n".join(prompt_parts)