import click
from rich.console import Console
from rich.table import Table
from pathlib import Path
from tix.storage.json_storage import TaskStorage
from tix.storage.context_storage import ContextStorage
from tix.storage.archive_storage import ArchiveStorage
from rich.prompt import Prompt
from rich.markdown import Markdown
from datetime import datetime

console = Console()
storage = TaskStorage()
context_storage = ContextStorage()
archive_storage = ArchiveStorage()

from .storage import storage
from .config import CONFIG
from .context import context_storage


console = Console()


@click.group()
def cli():
    """TIX - Lightning-fast Terminal Task Manager ⚡"""
    pass


@cli.command()
@click.argument("task")
@click.option("--priority", type=click.Choice(["low", "medium", "high"]))
@click.option("--tag", multiple=True, help="Add one or more tags")
@click.option("--date", help="Due date (YYYY-MM-DD)")
@click.option("--global", "is_global", is_flag=True, help="Make this a global task")
@click.option("--attach", multiple=True, help="File attachments")
@click.option("--link", multiple=True, help="Links to attach")
def add(task, priority, tag, date, is_global, attach, link):
    """Add a new task"""

    # Apply config defaults if not provided
    if priority is None:
        priority = CONFIG.get("defaults", {}).get("priority", "medium")

    # Merge config default tags with provided tags
    default_tags = CONFIG.get("defaults", {}).get("tags", [])
    all_tags = list(set(list(tag) + default_tags))

    # Add task
    new_task = storage.add_task(task, priority, all_tags, due=date, is_global=is_global)

    # Handle attachments and links
    if attach:
        storage.add_attachments(new_task.id, attach)
    if link:
        storage.add_links(new_task.id, link)

    storage.update_task(new_task)

    # Priority colors (configurable, fallback to defaults)
    priority_colors = CONFIG.get("colors", {}).get("priority", {})
    color = priority_colors.get(priority, {"high": "red", "medium": "yellow", "low": "green"}[priority])

    global_indicator = " [dim](global)[/dim]" if is_global else ""
    console.print(f"[green]✔[/green] Added task #{new_task.id}: [{color}]{task}[/{color}]{global_indicator}")

    if all_tags:
        tag_color = CONFIG.get("colors", {}).get("tags", "cyan")
        console.print(f"[dim]  Tags: [{tag_color}]{', '.join(all_tags)}[/{tag_color}][/dim]")
    if attach or link:
        console.print(f"[dim]  Attachments/Links added[/dim]")

    # Show current context if not default
    active_context = context_storage.get_active_context()
    if active_context != "default":
        console.print(f"[dim]  Context: {active_context}[/dim]")


@cli.command()
@click.option("--all", "show_all", is_flag=True, help="Show all tasks including completed")
def ls(show_all):
    """List tasks"""
    active_context = context_storage.get_active_context()
    title = "Tasks" if not show_all else "All Tasks"
    if active_context != "default":
        title += f" [dim]({active_context})[/dim]"

    # Display + color settings
    display_config = CONFIG.get("display", {})
    show_ids = display_config.get("show_ids", True)
    show_dates = display_config.get("show_dates", False)
    compact_mode = display_config.get("compact_mode", False)
    max_text_length = display_config.get("max_text_length", 0)

    priority_colors = CONFIG.get("colors", {}).get("priority", {})
    status_colors = CONFIG.get("colors", {}).get("status", {})
    tag_color = CONFIG.get("colors", {}).get("tags", "cyan")

    table = Table(title=title)
    if show_ids:
        table.add_column("ID", style="cyan", width=4)
    table.add_column("✔", width=3)
    table.add_column("Priority", width=8)
    table.add_column("Task")
    if not compact_mode:
        table.add_column("Tags", style=tag_color)
    if show_dates:
        table.add_column("Created", style="dim")
    table.add_column("Due Date")
    table.add_column("Scope", style="dim", width=6)

    tasks = storage.list_tasks(include_completed=show_all, context=active_context)

    if not tasks:
        console.print("[yellow]No tasks found.[/yellow]")
        return

    now = datetime.now().date()

    for t in tasks:
        status_symbol = "✔" if t.status == "done" else " "
        color = priority_colors.get(t.priority, {"high": "red", "medium": "yellow", "low": "green"}[t.priority])
        status_color = status_colors.get(t.status, "white")

        task_text = t.task
        if max_text_length and len(task_text) > max_text_length:
            task_text = task_text[: max_text_length - 3] + "..."

        row = []
        if show_ids:
            row.append(str(t.id))
        row.append(status_symbol)
        row.append(f"[{color}]{t.priority}[/{color}]")
        row.append(f"[{status_color}]{task_text}[/{status_color}]")
        if not compact_mode:
            row.append(", ".join(t.tags))
        if show_dates:
            row.append(t.created.strftime("%Y-%m-%d"))
        due_display = ""
        if t.due:
            try:
                due_date = datetime.strptime(t.due, "%Y-%m-%d").date()
                if due_date < now and t.status != "done":
                    due_display = f"[red]{t.due} (OVERDUE)[/red]"
                elif due_date == now:
                    due_display = f"[yellow]{t.due} (TODAY)[/yellow]"
                else:
                    due_display = t.due
            except ValueError:
                due_display = t.due
        row.append(due_display)
        row.append("Global" if t.is_global else "Local")

        table.add_row(*row)

    console.print(table)
    console.print(f"[dim]{len(tasks)} tasks listed[/dim]")


@cli.command()
@click.argument("task_id", type=int)
def done(task_id):
    """Mark a task as done"""
    task = storage.get_task(task_id)
    if not task:
        console.print(f"[red]Task {task_id} not found[/red]")
        return
    storage.mark_done(task_id)
    console.print(f"[green]✔ Task {task_id} marked as done[/green]")


@cli.command()
@click.argument("task_id", type=int)
def rm(task_id):
    """Remove a task"""
    task = storage.get_task(task_id)
    if not task:
        console.print(f"[red]Task {task_id} not found[/red]")
        return
    storage.remove_task(task_id)
    console.print(f"[red]✖ Task {task_id} removed[/red]")


@cli.command()
@click.argument("name")
def context(name):
    """Switch or create context"""
    context_storage.set_active_context(name)
    console.print(f"[blue]Switched to context:[/blue] {name}")


@cli.command()
def contexts():
    """List all contexts"""
    contexts = context_storage.list_contexts()
    active = context_storage.get_active_context()
    for c in contexts:
        if c == active:
            console.print(f"[cyan]> {c} (active)[/cyan]")
        else:
            console.print("[red]Error updating due date. Try again with proper format")
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
@click.option('--format', '-f', type=click.Choice(['text', 'json','markdown']), default='text', help='Output format')
@click.option('--output', '-o', type=click.Path(), help='Output to file')
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
    elif format == 'markdown':
        report_lines = [
            "# TIX Task Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Summary",
            "",
            f"- **Total Tasks:** {len(tasks)}",
            f"- **Active:** {len(active)}",
            f"- **Completed:** {len(completed)}",
            ""
        ]
        priority_order = ['high', 'medium', 'low']
        active_by_priority = {p: [] for p in priority_order}
        for task in active:
            active_by_priority[task.priority].append(task)

        report_lines.extend([
            "## Active Tasks",
            "",
        ])
        for priority in priority_order:
            tasks_in_priority = active_by_priority[priority]
            if tasks_in_priority:
                priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
                report_lines.append(f"### {priority_emoji[priority]} {priority.capitalize()} Priority")
                report_lines.append("")
                
                for task in tasks_in_priority:
                    tags = f" `{', '.join(task.tags)}`" if task.tags else ""
                    report_lines.append(f"- [ ] **#{task.id}** {task.text}{tags}")
                
                report_lines.append("")
        if completed:
            report_lines.extend([
                "## Completed Tasks",
                "",
                "| ID | Task | Priority | Tags | Completed At |",
                "|---|---|---|---|---|"
            ])
            for task in completed:
                tags = ", ".join([f"`{tag}`" for tag in task.tags]) if task.tags else "-"
                completed_date = datetime.fromisoformat(task.completed_at).strftime('%Y-%m-%d %H:%M') if task.completed_at else "-"
                priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
                report_lines.append(
                    f"| #{task.id} | ~~{task.text}~~ | {priority_emoji[task.priority]} {task.priority} | {tags} | {completed_date} |"
                )
            report_lines.append("")
        report_text = "\n".join(report_lines)
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


# Import and register context commands
from tix.commands.context import context
cli.add_command(context)

@cli.command()
@click.argument("task_id", type=int)
def archive(task_id):
    """Archive (soft-delete) a task"""
    task = storage.get_task(task_id)
    if not task:
        console.print(f"[red]✗[/red] Task #{task_id} not found")
        return
    ArchiveStorage().add_task(task)
    storage.delete_task(task_id)
    console.print(f"[yellow]→[/yellow] Archived: {task.text}")

@cli.command()
def archived():
    """List archived tasks"""
    tasks = ArchiveStorage().load_tasks()
    if not tasks:
        console.print("[dim]No archived tasks found.[/dim]")
        return
    table = Table(title="Archived Tasks")
    table.add_column("ID", style="cyan", width=4)
    table.add_column("Task")
    table.add_column("Priority", width=8)
    table.add_column("Tags", style="dim")
    for task in tasks:
        tags_str = ", ".join(task.tags) if task.tags else ""
        table.add_row(str(task.id), task.text, task.priority, tags_str)
    console.print(table)

@cli.command()
@click.argument("task_id", type=int)
def unarchive(task_id):
    """Restore an archived task"""
    archive = ArchiveStorage()
    task = archive.get_task(task_id)
    if not task:
        console.print(f"[red]✗[/red] Archived task #{task_id} not found")
        return
    storage.add_task(task.text, task.priority, task.tags, due=task.due, is_global=task.is_global)
    archive.remove_task(task_id)
    console.print(f"[green]✔[/green] Restored: {task.text}")


if __name__ == '__main__':
    cli()
    console.print(f"  {c}")

