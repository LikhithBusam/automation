#!/usr/bin/env python3
"""
Intelligent Development Assistant - AutoGen Edition
Multi-Agent AI System with AutoGen, Gemini, Groq & MCP Servers

Version: 2.0.0 (AutoGen)
Framework: Microsoft AutoGen
Models: Google Gemini 2.5 Flash & Groq
"""

import asyncio
import logging
import sys
import shlex
from pathlib import Path
from dotenv import load_dotenv

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Import AutoGen adapters
from src.autogen_adapters.conversation_manager import create_conversation_manager

# Import security
from src.security.input_validator import validate_parameters, validate_workflow_name, ValidationError
from src.security.log_sanitizer import install_log_filter

console = Console()

# Load environment variables with validation
env_loaded = load_dotenv()
if not env_loaded:
    # Warn if .env file not found (but don't fail - may use system env vars)
    import os
    if not os.path.exists('.env'):
        import warnings
        warnings.warn("No .env file found. Using system environment variables.")


BANNER = """
==================================================================

       INTELLIGENT DEVELOPMENT ASSISTANT
       Multi-Agent AI System with AutoGen, Gemini & Groq

       Version: 2.0.0 (AutoGen Edition)
       Agents: Code Analyzer | Security | Docs | Deploy | PM
       Models: Gemini 2.5 Flash | Groq Mixtral & Llama

==================================================================
"""


def setup_logging():
    """Setup logging configuration with proper error handling"""
    import tempfile
    
    # Create logs directory with fallback to temp directory
    log_dir = Path('logs')
    try:
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / 'autogen_dev_assistant.log'
    except (PermissionError, OSError) as e:
        # Fallback to temp directory if current directory is read-only
        temp_dir = Path(tempfile.gettempdir()) / 'automaton_logs'
        temp_dir.mkdir(exist_ok=True)
        log_file = temp_dir / 'autogen_dev_assistant.log'
        logging.warning(f"Could not create logs directory, using {temp_dir}: {e}")

    try:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    except Exception as e:
        # If file logging fails, at least enable console logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
        logging.warning(f"Could not setup file logging: {e}")

    # Install sensitive data filter to prevent API keys/secrets in logs
    # Enable redaction for better security
    install_log_filter(
        logger=None,  # Install on root logger
        redact_emails=True,  # Enable email redaction
        redact_ips=True  # Enable IP redaction
    )


async def main():
    """Main entry point"""
    try:
        # Setup logging
        setup_logging()
        logger = logging.getLogger(__name__)

        # Display banner
        console.print(BANNER, style="bold cyan")
        console.print()

        # Initialize conversation manager
        console.print("[bold blue]Initializing AutoGen System...[/bold blue]")

        try:
            manager = await create_conversation_manager()
            console.print("[green][OK] AutoGen system initialized successfully[/green]")
            console.print()
        except Exception as e:
            console.print(f"[red][ERROR] Failed to initialize: {e}[/red]")
            logger.error(f"Initialization failed: {e}", exc_info=True)
            return 1

        # Show available workflows
        console.print("[bold]Available Workflows:[/bold]")
        workflows = manager.list_workflows()

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Workflow", style="cyan")
        table.add_column("Description")

        workflow_descriptions = {
            "code_analysis": "Comprehensive code review with security & quality checks",
            "security_audit": "Deep security vulnerability assessment",
            "documentation_generation": "Generate project documentation",
            "deployment": "Execute deployment to target environment",
            "research": "Research technologies and best practices",
            "quick_code_review": "Quick code review for small changes",
            "quick_documentation": "Quick documentation update",
        }

        for workflow in workflows:
            desc = workflow_descriptions.get(workflow, "N/A")
            table.add_row(workflow, desc)

        console.print(table)
        console.print()

        # Interactive mode
        console.print("[bold green]Interactive Mode[/bold green]")
        console.print("[dim]Commands: run, list, history, help, exit[/dim]")
        console.print()

        while True:
            try:
                # Get user input
                user_input = console.input("[bold cyan]>>> [/bold cyan]").strip()

                if not user_input:
                    continue

                # Parse command (using shlex to properly handle quoted strings)
                try:
                    parts = shlex.split(user_input)
                except ValueError as e:
                    # Report parsing error instead of silently falling back
                    console.print(f"[red]Invalid command syntax: {e}[/red]")
                    console.print("[dim]Use quotes for values with spaces, e.g., param=\"value with spaces\"[/dim]")
                    continue
                
                if not parts:
                    continue
                    
                command = parts[0].lower()

                if command in ["exit", "quit", "q"]:
                    console.print("[yellow]Goodbye![/yellow]")
                    break

                elif command == "help":
                    console.print(Panel("""
[bold]Available Commands:[/bold]

  [cyan]run <workflow> [params...][/cyan]
    Execute a workflow
    Example: run code_analysis code_path=./src

  [cyan]list[/cyan]
    List available workflows

  [cyan]history[/cyan]
    Show recent workflow executions

  [cyan]help[/cyan]
    Show this help message

  [cyan]exit[/cyan]
    Exit the application
                    """, title="Help"))

                elif command == "list":
                    console.print("\n[bold]Available Workflows:[/bold]")
                    for workflow in workflows:
                        console.print(f"  • {workflow}")
                    console.print()

                elif command == "history":
                    try:
                        history = manager.get_workflow_history(10)

                        if not history:
                            console.print("[dim]No execution history available[/dim]")
                        else:
                            hist_table = Table(show_header=True, header_style="bold magenta")
                            hist_table.add_column("Workflow")
                            hist_table.add_column("Status")
                            hist_table.add_column("Duration")

                            for entry in history:
                                # Validate entry structure
                                if not isinstance(entry, dict):
                                    continue
                                
                                workflow_name = entry.get("workflow_name", "unknown")
                                status = entry.get("status", "unknown")
                                duration_seconds = entry.get("duration_seconds", 0.0)
                                
                                status_icon = "[OK]" if status == "success" else "[FAIL]"
                                duration = f"{duration_seconds:.2f}s"
                                hist_table.add_row(
                                    workflow_name,
                                    f"{status_icon} {status}",
                                    duration
                                )

                            console.print(hist_table)
                    except Exception as e:
                        console.print(f"[red]Error retrieving history: {e}[/red]")
                        logger.error(f"History retrieval error: {e}", exc_info=True)

                elif command == "run":
                    if len(parts) < 2:
                        console.print("[red]Usage: run <workflow> [param=value ...][/red]")
                        continue

                    workflow_name = parts[1]

                    # Parse parameters
                    variables = {}
                    for arg in parts[2:]:
                        if "=" in arg:
                            key, value = arg.split("=", 1)
                            # Strip whitespace and validate key
                            key = key.strip()
                            if not key:
                                console.print(f"[red]Invalid parameter: empty key in '{arg}'[/red]")
                                continue
                            variables[key] = value.strip()

                    try:
                        # Validate workflow name
                        workflow_name = validate_workflow_name(workflow_name)

                        # Always validate parameters (even if empty)
                        variables = validate_parameters(variables)

                    except ValidationError as e:
                        console.print(f"[red]Validation error: {e}[/red]")
                        logger.warning(f"Input validation failed: {e}")
                        continue

                    console.print(f"\n[bold]Executing workflow:[/bold] {workflow_name}")
                    if variables:
                        console.print(f"[dim]Parameters: {variables}[/dim]")
                    console.print()

                    try:
                        # Execute workflow with timeout protection
                        import asyncio
                        try:
                            result = await asyncio.wait_for(
                                manager.execute_workflow(workflow_name, variables),
                                timeout=300.0  # 5 minute timeout
                            )
                        except asyncio.TimeoutError:
                            console.print(f"[red][ERROR] Workflow timed out after 5 minutes[/red]")
                            logger.error(f"Workflow '{workflow_name}' timed out")
                            continue

                        # Display result
                        if result.status == "success":
                            console.print(f"[green][OK] Workflow completed successfully[/green]")
                        elif result.status == "partial":
                            console.print(f"[yellow][WARN] Workflow completed with warnings[/yellow]")
                        else:
                            console.print(f"[red][ERROR] Workflow failed[/red]")

                        console.print(f"\n[bold]Summary:[/bold]")
                        console.print(result.summary)
                        console.print(f"\n[dim]Duration: {result.duration_seconds:.2f}s[/dim]")
                        console.print(f"[dim]Tasks: {result.tasks_completed} completed, {result.tasks_failed} failed[/dim]")

                        if result.error:
                            console.print(f"\n[red]Error: {result.error}[/red]")

                    except ValidationError as e:
                        console.print(f"[red]Validation error: {e}[/red]")
                        logger.warning(f"Input validation failed: {e}")
                    except asyncio.TimeoutError:
                        # Already handled above
                        pass
                    except Exception as e:
                        console.print(f"[red]Error executing workflow: {e}[/red]")
                        logger.error(f"Workflow execution error: {e}", exc_info=True)

                    console.print()

                else:
                    console.print(f"[yellow]Unknown command: {command}[/yellow]")
                    console.print("[dim]Type 'help' for available commands[/dim]")

            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit[/yellow]")
            except EOFError:
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                logger.error(f"Command error: {e}", exc_info=True)

        return 0

    except Exception as e:
        console.print(f"[bold red]Fatal error: {e}[/bold red]")
        logger = logging.getLogger(__name__)
        logger.exception("Fatal error")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
