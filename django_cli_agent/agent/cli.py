# import typer
# from rich import print
# import sys

# from agent.agent_core import AgentCore

# app = typer.Typer()


# @app.command()
# def chat():
#     """
#     Start an interactive chat session with the Django AI Agent.
#     """

#     print("[bold green]🤖 Django CLI AI Agent[/bold green]")
#     print("[dim]Press Ctrl+C or Ctrl+D to exit[/dim]\n")

#     agent = AgentCore()

#     try:
#         while True:
#             user_input = typer.prompt("Ask")

#             response = agent.run(user_input)

#             print("\n[cyan]Agent:[/cyan]")
#             print(response)
#             print("-" * 60)

#     except (KeyboardInterrupt, EOFError):
#         # Ctrl+C or Ctrl+D
#         print("\n[bold red]Session ended. Goodbye 👋[/bold red]")
#         sys.exit(0)


# if __name__ == "__main__":
#     app()

import typer
from rich import print
import sys

from agent.agent_core import AgentCore

app = typer.Typer()


@app.command()
def chat():
    """
    Start an interactive chat session with the Django AI Agent.
    Uses default workspace from agent/workspace.py
    """

    print("[bold green]🤖 Django CLI AI Agent[/bold green]")
    print("[dim]Press Ctrl+C or Ctrl+D to exit[/dim]\n")

    # Initialize agent without workspace parameter (uses default from workspace.py)
    agent = AgentCore()

    try:
        while True:
            user_input = typer.prompt("Ask")

            response = agent.run(user_input)

            print("\n[cyan]Agent:[/cyan]")
            print(response)
            print("-" * 60)

    except (KeyboardInterrupt, EOFError):
        # Ctrl+C or Ctrl+D
        print("\n[bold red]Session ended. Goodbye 👋[/bold red]")
        sys.exit(0)


if __name__ == "__main__":
    app()