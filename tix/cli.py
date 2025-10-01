import click
from rich.console import Console
from rich.table import Table
from pathlib import Path
from tix.storage.json_storage import TaskStorage
from tix.storage.template_storage import TemplateStorage
from tix.storage.context_storage import ContextStorage
from datetime import datetime
import subprocess
import platform
import os
import sys
from importlib import import_module


# Initialize console and storages
console = Console()
storage = TaskStorage()
template_storage = TemplateStorage()
context_storage = ContextStorage()



@click.group(invoke_without_command=True)
@click.version_option(version="0.8.0", prog_name="tix")
@click.pass_context
def cli(ctx):
    """⚡ TIX - Lightning-fast terminal task manager

    Quick start:
      tix add "My task" -p high    # Add a high priority task
      tix ls                        # List all active tasks
      tix done 1                    # Mark task #1 as done
      tix context list              # List all contexts
      tix --help                    # Show all commands
    """
    if ctx.invoked_subcommand is None:
        ctx.invoke(ls)


@cli.command()
@click.argument('task')
@click.option('--priority', '-p', default='medium',
              type=click.Choice(['low', 'medium', 'high']),
              help='Set task priority')
@click.option('--tag', '-t', multiple=True, help='Add tags to task')
@click.option('--attach', '-f', multiple=True, help='Attach file(s)')
@click.option('--link', '-l', multiple=True, help='Attach URL(s)')
@click.option('--global', 'is_global', is_flag=True, help='Make task visible in all contexts')
def add(task, priority, tag, attach, link, is_global):
    """Add a new task"""
    if not task or not task.strip():
        console.print("[red]✗[/red] Task text cannot be empty")
        sys.exit(1)

    new_task = storage.add_task(task, priority, list(tag), is_global=is_global)
    
    # Handle attachments
    if attach:
        attachment_dir = Path.home() / ".tix" / "attachments" / str(new_task.id)
        attachment_dir.mkdir(parents=True, exist_ok=True)
        for file_path in attach:
            try:
                src = Path(file_path).expanduser().resolve()  
                if not src.exists():
                    console.print(f"[red]✗[/red] File not found: {file_path}")
                    continue
                dest = attachment_dir / src.name
                dest.write_bytes(src.read_bytes())
                new_task.attachments.append(str(dest))
            except Exception as e:
                console.print(f"[red]✗[/red] Failed to attach {file_path}: {e}")

    # Handle links
    if link:
        new_task.links.extend(link)

    storage.update_task(new_task)

    color = {'high': 'red', 'medium': 'yellow', 'low': 'green'}[priority]
    
    global_indicator = " [dim](global)[/dim]" if is_global else ""
    console.print(f"[green]✔[/green] Added task #{new_task.id}: [{color}]{task}[/{color}]{global_indicator}")
    if tag:
        console.print(f"[dim]  Tags: {', '.join(tag)}[/dim]")
    if attach or link:
        console.print(f"[dim]  Attachments/Links added[/dim]")
    
    # Show current context if not default
    active_context = context_storage.get_active_context()
    if active_context != "default":
        console.print(f"[dim]  Context: {active_context}[/dim]")


@cli.command()
@click.option("--all", "-a", is_flag=True, help="Show completed tasks too")
def ls(all):
    """List all tasks"""
    tasks = storage.load_tasks() if all else storage.get_active_tasks()

    if not tasks:
        console.print("[dim]No tasks found. Use 'tix add' to create one![/dim]")
        return

    active_context = context_storage.get_active_context()
    title = "Tasks" if not all else "All Tasks"
    if active_context != "default":
        title += f" [dim]({active_context})[/dim]"

    table = Table(title=title)
    table.add_column("ID", style="cyan", width=4)
    table.add_column("✔", width=3)
    table.add_column("Priority", width=8)
    table.add_column("Task")
    table.add_column("Tags", style="dim")
    table.add_column("Scope", style="dim", width=6)
    
    count = dict()

    for task in sorted(tasks, key=lambda t: (t.completed, t.id)):
        status = "✔" if task.completed else "○"
        priority_color = {"high": "red", "medium": "yellow", "low": "green"}[task.priority]
        tags_str = ", ".join(task.tags) if task.tags else ""
        scope = "global" if task.is_global else "local"

        # Show paperclip if task has attachments or links
        attach_icon = " 📎" if task.attachments or task.links else ""

        task_style = "dim strike" if task.completed else ""
        table.add_row(
            str(task.id),
            status,
            f"[{priority_color}]{task.priority}[/{priority_color}]",
            f"[{task_style}]{task.text}[/{task_style}]{attach_icon}" if task.completed else f"{task.text}{attach_icon}",
            tags_str,
            scope
        )
        count[task.completed] = count.get(task.completed, 0) + 1

    console.print(table)
    console.print("\n")
    console.print(f"[cyan]Total tasks:{sum(count.values())}")
    console.print(f"[red]Active tasks:{count.get(False,0)}")
    console.print(f"[green]Completed tasks:{count.get(True,0)}")

    # Show summary
    if all:
        active = len([t for t in tasks if not t.completed])
        completed = len([t for t in tasks if t.completed])
        global_count = len([t for t in tasks if t.is_global])
        local_count = len(tasks) - global_count
        console.print(f"\n[dim]Total: {len(tasks)} ({local_count} local, {global_count} global) | Active: {active} | Completed: {completed}[/dim]")


@cli.command()
@click.argument("task_id", type=int)
def done(task_id):
    """Mark a task as done"""
    task = storage.get_task(task_id)
    if not task:
        console.print(f"[red]✗[/red] Task #{task_id} not found")
        return

    if task.completed:
        console.print(f"[yellow]![/yellow] Task #{task_id} already completed")
        return

    task.mark_done()
    storage.update_task(task)
    console.print(f"[green]✔[/green] Completed: {task.text}")


@cli.command()
@click.argument("task_id", type=int)
@click.option("--confirm", "-y", is_flag=True, help="Skip confirmation")
def rm(task_id, confirm):
    """Remove a task"""
    task = storage.get_task(task_id)
    if not task:
        console.print(f"[red]✗[/red] Task #{task_id} not found")
        return

    if not confirm:
        if not click.confirm(f"Are you sure you want to delete task #{task_id}: '{task.text}'?"):
            console.print("[yellow]⚠ Cancelled[/yellow]")
            return

    if storage.delete_task(task_id):
        console.print(f"[red]✗[/red] Removed: {task.text}")


@cli.command()
@click.option("--completed/--active", default=True, help="Clear completed or active tasks")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def clear(completed, force):
    """Clear multiple tasks at once"""
    tasks = storage.load_tasks()

    if completed:
        to_clear = [t for t in tasks if t.completed]
        remaining = [t for t in tasks if not t.completed]
        task_type = "completed"
    else:
        to_clear = [t for t in tasks if not t.completed]
        remaining = [t for t in tasks if t.completed]
        task_type = "active"

    if not to_clear:
        console.print(f"[yellow]No {task_type} tasks to clear[/yellow]")
        return

    count = len(to_clear)

    if not force:
        console.print(f"[yellow]About to clear {count} {task_type} task(s):[/yellow]")
        for task in to_clear[:5]:  # Show first 5
            console.print(f"  - {task.text}")
        if count > 5:
            console.print(f"  ... and {count - 5} more")

        if not click.confirm("Continue?"):
            console.print("[dim]Cancelled[/dim]")
            return

    storage.save_tasks(remaining)
    console.print(f"[green]✔[/green] Cleared {count} {task_type} task(s)")


@cli.command()
@click.argument("task_id", type=int)
def undo(task_id):
    """Mark a completed task as active again"""
    task = storage.get_task(task_id)
    if not task:
        console.print(f"[red]✗[/red] Task #{task_id} not found")
        return

    if not task.completed:
        console.print(f"[yellow]![/yellow] Task #{task_id} is not completed")
        return

    task.completed = False
    task.completed_at = None
    storage.update_task(task)
    console.print(f"[green]✔[/green] Reactivated: {task.text}")


@cli.command(name="done-all")
@click.argument("task_ids", nargs=-1, type=int, required=True)
def done_all(task_ids):
    """Mark multiple tasks as done"""
    completed = []
    not_found = []
    already_done = []

    for task_id in task_ids:
        task = storage.get_task(task_id)
        if not task:
            not_found.append(task_id)
        elif task.completed:
            already_done.append(task_id)
        else:
            task.mark_done()
            storage.update_task(task)
            completed.append((task_id, task.text))

    # Report results
    if completed:
        console.print("[green]✔ Completed:[/green]")
        for tid, text in completed:
            console.print(f"  #{tid}: {text}")

    if already_done:
        console.print(f"[yellow]Already done: {', '.join(map(str, already_done))}[/yellow]")

    if not_found:
        console.print(f"[red]Not found: {', '.join(map(str, not_found))}[/red]")


@cli.command()
@click.argument('task_id', type=int)
@click.option('--text', '-t', help='New task text')
@click.option('--priority', '-p', type=click.Choice(['low', 'medium', 'high']), help='New priority')
@click.option('--add-tag', multiple=True, help='Add tags')
@click.option('--remove-tag', multiple=True, help='Remove tags')
@click.option('--attach', '-f', multiple=True, help='Attach file(s)')
@click.option('--link', '-l', multiple=True, help='Attach URL(s)')
def edit(task_id, text, priority, add_tag, remove_tag, attach, link):
    """Edit a task"""
    task = storage.get_task(task_id)
    if not task:
        console.print(f"[red]✗[/red] Task #{task_id} not found")
        return

    changes = []

    if text:
        old_text = task.text
        task.text = text
        changes.append(f"text: '{old_text}' → '{text}'")

    if priority:
        old_priority = task.priority
        task.priority = priority
        changes.append(f"priority: {old_priority} → {priority}")

    for tag in add_tag:
        if tag not in task.tags:
            task.tags.append(tag)
            changes.append(f"+tag: '{tag}'")

    for tag in remove_tag:
        if tag in task.tags:
            task.tags.remove(tag)
            changes.append(f"-tag: '{tag}'")

    # Handle attachments
    if attach:
        attachment_dir = Path.home() / ".tix/attachments" / str(task.id)
        attachment_dir.mkdir(parents=True, exist_ok=True)
        for file_path in attach:
            src = Path(file_path)
            dest = attachment_dir / src.name
            dest.write_bytes(src.read_bytes())
            task.attachments.append(str(dest))
        changes.append(f"attachments added: {[Path(f).name for f in attach]}")

    # Handle links
    if link:
        task.links.extend(link)
        changes.append(f"links added: {list(link)}")

    if changes:
        storage.update_task(task)
        console.print(f"[green]✔[/green] Updated task #{task_id}:")
        for change in changes:
            console.print(f"  • {change}")
    else:
        console.print("[yellow]No changes made[/yellow]")


@cli.command()
@click.argument("task_id", type=int)
@click.argument("priority", type=click.Choice(["low", "medium", "high"]))
def priority(task_id, priority):
    """Quick priority change"""
    task = storage.get_task(task_id)
    if not task:
        console.print(f"[red]✗[/red] Task #{task_id} not found")
        return

    old_priority = task.priority
    task.priority = priority
    storage.update_task(task)

    color = {"high": "red", "medium": "yellow", "low": "green"}[priority]
    console.print(
        f"[green]✔[/green] Changed priority: {old_priority} → [{color}]{priority}[/{color}]"
    )


@cli.command()
@click.argument("from_id", type=int)
@click.argument("to_id", type=int)
def move(from_id, to_id):
    """Move/renumber a task to a different ID"""
    if from_id == to_id:
        console.print("[yellow]Source and destination IDs are the same[/yellow]")
        return

    source_task = storage.get_task(from_id)
    if not source_task:
        console.print(f"[red]✗[/red] Task #{from_id} not found")
        return

    # Check if destination ID exists
    dest_task = storage.get_task(to_id)
    if dest_task:
        console.print(f"[red]✗[/red] Task #{to_id} already exists")
        console.print("[dim]Tip: Remove the destination task first or use a different ID[/dim]")
        return

    # Create new task with new ID
    tasks = storage.load_tasks()
    tasks = [t for t in tasks if t.id != from_id]  # Remove old task

    # Create task with new ID
    source_task.id = to_id
    tasks.append(source_task)

    # Save all tasks
    storage.save_tasks(sorted(tasks, key=lambda t: t.id))
    console.print(f"[green]✔[/green] Moved task from #{from_id} to #{to_id}")


@cli.command()
@click.argument("query")
@click.option("--tag", "-t", help="Filter by tag")
@click.option(
    "--priority", "-p", type=click.Choice(["low", "medium", "high"]), help="Filter by priority"
)
@click.option("--completed", "-c", is_flag=True, help="Search in completed tasks")
def search(query, tag, priority, completed):
    """Search tasks by text"""
    tasks = storage.load_tasks()

    # Filter by completion status
    if not completed:
        tasks = [t for t in tasks if not t.completed]

    # Filter by query text (case-insensitive)
    query_lower = query.lower()
    results = [t for t in tasks if query_lower in t.text.lower()]

    # Filter by tag if specified
    if tag:
        results = [t for t in results if tag in t.tags]

    # Filter by priority if specified
    if priority:
        results = [t for t in results if t.priority == priority]

    if not results:
        console.print(f"[dim]No tasks matching '{query}'[/dim]")
        return

    console.print(f"[bold]Found {len(results)} task(s) matching '{query}':[/bold]\n")

    table = Table()
    table.add_column("ID", style="cyan", width=4)
    table.add_column("✔", width=3)
    table.add_column("Priority", width=8)
    table.add_column("Task")
    table.add_column("Tags", style="dim")

    for task in results:
        status = "✔" if task.completed else "○"
        priority_color = {"high": "red", "medium": "yellow", "low": "green"}[task.priority]
        tags_str = ", ".join(task.tags) if task.tags else ""

        # Highlight matching text
        highlighted_text = (
            task.text.replace(query, f"[bold yellow]{query}[/bold yellow]")
            if query.lower() in task.text.lower()
            else task.text
        )

        table.add_row(
            str(task.id),
            status,
            f"[{priority_color}]{task.priority}[/{priority_color}]",
            highlighted_text,
            tags_str,
        )

    console.print(table)


@cli.command()
@click.option(
    "--priority", "-p", type=click.Choice(["low", "medium", "high"]), help="Filter by priority"
)
@click.option("--tag", "-t", help="Filter by tag")
@click.option("--completed/--active", "-c/-a", default=None, help="Filter by completion status")
def filter(priority, tag, completed):
    """Filter tasks by criteria"""
    tasks = storage.load_tasks()

    # Apply filters
    if priority:
        tasks = [t for t in tasks if t.priority == priority]

    if tag:
        tasks = [t for t in tasks if tag in t.tags]

    if completed is not None:
        tasks = [t for t in tasks if t.completed == completed]

    if not tasks:
        console.print("[dim]No matching tasks[/dim]")
        return

    # Build filter description
    filters = []
    if priority:
        filters.append(f"priority={priority}")
    if tag:
        filters.append(f"tag='{tag}'")
    if completed is not None:
        filters.append("completed" if completed else "active")

    filter_desc = " AND ".join(filters) if filters else "all"
    console.print(f"[bold]{len(tasks)} task(s) matching [{filter_desc}]:[/bold]\n")

    table = Table()
    table.add_column("ID", style="cyan", width=4)
    table.add_column("✔", width=3)
    table.add_column("Priority", width=8)
    table.add_column("Task")
    table.add_column("Tags", style="dim")

    for task in sorted(tasks, key=lambda t: (t.completed, t.id)):
        status = "✔" if task.completed else "○"
        priority_color = {"high": "red", "medium": "yellow", "low": "green"}[task.priority]
        tags_str = ", ".join(task.tags) if task.tags else ""
        table.add_row(
            str(task.id),
            status,
            f"[{priority_color}]{task.priority}[/{priority_color}]",
            task.text,
            tags_str,
        )

    console.print(table)


@cli.command()
@click.option("--no-tags", is_flag=True, help="Show tasks without tags")
def tags(no_tags):
    """List all unique tags or tasks without tags"""
    tasks = storage.load_tasks()

    if no_tags:
        # Show tasks without tags
        untagged = [t for t in tasks if not t.tags]
        if not untagged:
            console.print("[dim]All tasks have tags[/dim]")
            return

        console.print(f"[bold]{len(untagged)} task(s) without tags:[/bold]\n")
        for task in untagged:
            status = "✔" if task.completed else "○"
            console.print(f"{status} #{task.id}: {task.text}")
    else:
        # Show all unique tags with counts
        tag_counts = {}
        for task in tasks:
            for tag in task.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        if not tag_counts:
            console.print("[dim]No tags found[/dim]")
            return

        console.print("[bold]Tags in use:[/bold]\n")
        for tag, count in sorted(tag_counts.items(), key=lambda x: (-x[1], x[0])):
            console.print(f"  • {tag} ({count} task{'s' if count != 1 else ''})")


@cli.command()
@click.option("--detailed", "-d", is_flag=True, help="Show detailed breakdown")
def stats(detailed):
    """Show task statistics"""
    from tix.commands.stats import show_stats

    show_stats(storage)

    if detailed:
        # Additional detailed stats
        tasks = storage.load_tasks()
        if tasks:
            console.print("\n[bold]Detailed Breakdown:[/bold]\n")

            # Tasks by day
            from collections import defaultdict

            by_day = defaultdict(list)

            for task in tasks:
                if task.completed and task.completed_at:
                    day = datetime.fromisoformat(task.completed_at).date()
                    by_day[day].append(task)

            if by_day:
                console.print("[bold]Recent Completions:[/bold]")
                for day in sorted(by_day.keys(), reverse=True)[:5]:
                    count = len(by_day[day])
                    console.print(f"  • {day}: {count} task(s)")


@cli.command()
@click.option(
    "--format", "-f", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.option("--output", "-o", type=click.Path(), help="Output to file")
def report(format, output):
    """Generate a task report"""
    tasks = storage.load_tasks()

    if not tasks:
        console.print("[dim]No tasks to report[/dim]")
        return

    active = [t for t in tasks if not t.completed]
    completed = [t for t in tasks if t.completed]

    if format == "json":
        import json

        report_data = {
            'generated': datetime.now().isoformat(),
            'context': context_storage.get_active_context(),
            'summary': {
                'total': len(tasks),
                'active': len(active),
                'completed': len(completed)
            },
            'tasks': [t.to_dict() for t in tasks]
        }
        report_text = json.dumps(report_data, indent=2)
    else:
        # Text format
        active_context = context_storage.get_active_context()
        report_lines = [
            "TIX TASK REPORT",
            "=" * 40,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Context: {active_context}",
            "",
            f"Total Tasks: {len(tasks)}",
            f"Active: {len(active)}",
            f"Completed: {len(completed)}",
            "",
            "ACTIVE TASKS:",
            "-" * 20,
        ]

        for task in active:
            tags = f" [{', '.join(task.tags)}]" if task.tags else ""
            global_marker = " (global)" if task.is_global else ""
            report_lines.append(f"#{task.id} [{task.priority}] {task.text}{tags}{global_marker}")

        report_lines.extend(["", "COMPLETED TASKS:", "-" * 20])

        for task in completed:
            tags = f" [{', '.join(task.tags)}]" if task.tags else ""
            global_marker = " (global)" if task.is_global else ""
            report_lines.append(f"#{task.id} ✔ {task.text}{tags}{global_marker}")

        report_text = "\n".join(report_lines)

    if output:
        Path(output).write_text(report_text)
        console.print(f"[green]✔[/green] Report saved to {output}")
    else:
        console.print(report_text)


@cli.command()
@click.argument('task_id', type=int)
def open(task_id):
    """Open all attachments and links for a task"""
    task = storage.get_task(task_id)
    if not task:
        console.print(f"[red]✗[/red] Task #{task_id} not found")
        return

    if not task.attachments and not task.links:
        console.print(f"[yellow]![/yellow] Task {task_id} has no attachments or links")
        return
    
    # Helper to open files cross-platform
    def safe_open(path_or_url, is_link=False):
        """Cross-platform safe opener for files and links (non-blocking)."""
        system = platform.system()

        try:
            if system == "Linux":
                if "microsoft" in platform.release().lower():
                    subprocess.Popen(["explorer.exe", str(path_or_url)],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    subprocess.Popen(["xdg-open", str(path_or_url)],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            elif system == "Darwin":  # macOS
                subprocess.Popen(["open", str(path_or_url)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            elif system == "Windows":
                subprocess.Popen(["explorer.exe", str(path_or_url)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            console.print(f"[green]✔[/green] Opened {'link' if is_link else 'file'}: {path_or_url}")

        except Exception as e:
            console.print(f"[yellow]![/yellow] Could not open {'link' if is_link else 'file'}: {path_or_url} ({e})")

    # Open attachments
    for file_path in task.attachments:
        path = Path(file_path)
        if not path.exists():
            console.print(f"[red]✗[/red] File not found: {file_path}")
            continue
        safe_open(path)   

    # Open links
    for url in task.links:
        safe_open(url, is_link=True)  


@cli.command()
@click.option('--all', '-a', 'show_all', is_flag=True, help='Show completed tasks too')
def interactive(show_all):
    """launch interactive terminal ui"""
    try:
        from tix.tui.app import Tix
    except Exception as e:
        console.print(f"[red]failed to load tui: {e}[/red]")
        sys.exit(1)
    app = Tix(show_all=show_all)
    app.run()


@click.group()
def template():
    """Manage task templates"""
    pass


@template.command("save")
@click.argument("task_id", type=int)
@click.argument("name")
def save_template(task_id, name):
    """Save a task as a template"""
    task = storage.get_task(task_id)   
    if not task:
        console.print(f"[red]✗[/red] Task {task_id} not found")
        return

    template_storage.save_template(task, name)
    console.print(f"[green]✔[/green] Saved task {task_id} as template '{name}'")


@template.command("list")
def list_templates():
    """List all saved templates"""
    templates = template_storage.list_templates()
    if not templates:
        console.print("[dim]No templates saved yet[/dim]")
        return

    console.print("[bold]Templates:[/bold]")
    for t in templates:
        console.print(f"  • {t}")


# Register group with main CLI
cli.add_command(template)

# Import and register context commands
from tix.commands.context import context
cli.add_command(context)


if __name__ == '__main__':
    cli()
