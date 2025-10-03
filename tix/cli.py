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
import subprocess
import platform
import os
import sys
from .utils import get_date
from .storage import storage
from .config import CONFIG
from .context import context_storage

from tix.storage.backup import create_backup, list_backups, restore_from_backup

console = Console()
storage = TaskStorage()
context_storage = ContextStorage()
archive_storage = ArchiveStorage()

def cli(ctx):
        """ TIX - Lightning-fast terminal task manager

        Quick start:
            tix add "My task" -p high    # Add a high priority task
            tix ls                        # List all active tasks
            tix done 1                    # Mark task #1 as done
            tix context list              # List all contexts
            tix --help                    # Show all commands
        """
        if ctx.invoked_subcommand is None:
                ctx.invoke(ls)


def backup():
    pass


def backup_create(filename, data_file):
    """Create a timestamped backup of your tasks file."""
    try:
        data_path = Path(data_file) if data_file else storage.storage_path
        bpath = create_backup(data_path, filename)
        console.print(f"[green] Backup created:[/green] {bpath}")
    except Exception as e:
        console.print(f"[red]Backup failed:[/red] {e}")
        raise click.Abort()


def backup_list(data_file):
    """List available backups for the active tasks file."""
    try:
        data_path = Path(data_file) if data_file else storage.storage_path
        backups = list_backups(data_path)
        if not backups:
            console.print("[dim]No backups found[/dim]")
            return
        for b in backups:
            console.print(str(b))
    except Exception as e:
        console.print(f"[red]Failed to list backups:[/red] {e}")
        raise click.Abort()


def backup_restore(backup_file, data_file, yes):
    """Restore tasks from a previous backup. Will ask confirmation by default."""
    try:
        data_path = Path(data_file) if data_file else storage.storage_path
        if not yes:
            if not click.confirm(f"About to restore backup '{backup_file}'. This will overwrite your current tasks file. Continue?"):
                console.print("[yellow]Restore cancelled[/yellow]")
                return
        restore_from_backup(backup_file, data_path, require_confirm=False)
        console.print("[green] Restore complete[/green]")
    except FileNotFoundError as e:
        console.print(f"[red]Restore failed:[/red] {e}")
        raise click.Abort()
    except RuntimeError as e:
        console.print(f"[yellow]{e}[/yellow]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Restore failed:[/red] {e}")
        raise click.Abort()


# -----------------------
# Top-level restore
# -----------------------
@cli.command("restore")
@click.argument("backup_file", required=True)
@click.option("--data-file", type=click.Path(), default=None, help="Path to tix data file (for testing/dev)")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation")
def restore(backup_file, data_file, yes):
    """
    Restore tasks from a previous backup (top-level command).
    Usage: tix restore <backup_file>
    """
    try:
        data_path = Path(data_file) if data_file else storage.storage_path
        if not yes:
            if not click.confirm(f"About to restore backup '{backup_file}'. This will overwrite your current tasks file. Continue?"):
                console.print("[yellow]Restore cancelled[/yellow]")
                return
        restore_from_backup(backup_file, data_path, require_confirm=False)
        console.print("[green]✔ Restore complete[/green]")
    except FileNotFoundError as e:
        console.print(f"[red]Restore failed:[/red] {e}")
        raise click.Abort()
    except RuntimeError as e:
        console.print(f"[yellow]{e}[/yellow]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Restore failed:[/red] {e}")
        raise click.Abort()


@cli.command()
@click.argument('task')
@click.option('--priority', '-p', default='medium',
              type=click.Choice(['low', 'medium', 'high']),
              help='Set task priority')
@click.option('--tag', '-t', multiple=True, help='Add tags to task')
@click.option('--attach', '-f', multiple=True, help='Attach file(s)')
@click.option('--link', '-l', multiple=True, help='Attach URL(s)')
def add(task, priority, tag, attach, link):
    """Add a new task"""
    from tix.config import CONFIG

    if not task or not task.strip():
        console.print("[red]✗[/red] Task text cannot be empty")
        sys.exit(1)

    # merge default tags from config
    default_tags = CONFIG.get('defaults', {}).get('tags', [])
    tags = list(default_tags) + list(tag)
    tags = list(dict.fromkeys(tags))  # preserve order, unique

    new_task = storage.add_task(task, priority, tags)

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

    # Links
    if link:
        if not hasattr(new_task, "links"):
            new_task.links = []
        new_task.links.extend(link)

    storage.update_task(new_task)

    color = {'high': 'red', 'medium': 'yellow', 'low': 'green'}[priority]
    console.print(f"[green]✔[/green] Added task #{new_task.id}: [{color}]{task}[/{color}]")
    if tags:
        console.print(f"[dim]  Tags: {', '.join(tags)}[/dim]")
    if attach or link:
        console.print(f"[dim]  Attachments/Links added[/dim]")


@cli.command()
@click.option("--all", "-a", "show_all", is_flag=True, help="Show completed tasks too")
def ls(show_all):
    """List all tasks"""
    from tix.config import CONFIG

    tasks = storage.load_tasks() if show_all else storage.get_active_tasks()

    if not tasks:
        console.print("[dim]No tasks found. Use 'tix add' to create one![/dim]")
        return

    # Get display settings from config
    display_config = CONFIG.get('display', {})
    show_ids = display_config.get('show_ids', True)
    show_dates = display_config.get('show_dates', False)
    compact_mode = display_config.get('compact_mode', False)
    max_text_length = display_config.get('max_text_length', 0)

    # color settings
    priority_colors = CONFIG.get('colors', {}).get('priority', {})
    status_colors = CONFIG.get('colors', {}).get('status', {})
    tag_color = CONFIG.get('colors', {}).get('tags', 'cyan')

    title = "All Tasks" if show_all else "Tasks"
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

    count = dict()

    for task in sorted(tasks, key=lambda t: (getattr(t, "completed", False), getattr(t, "id", 0))):
        status = "✔" if getattr(task, "completed", False) else "○"
        priority_color = priority_colors.get(getattr(task, "priority", "medium"),
                                            {'high': 'red', 'medium': 'yellow', 'low': 'green'}[getattr(task, "priority", "medium")])
        tags_str = ", ".join(getattr(task, "tags", [])) if getattr(task, "tags", None) else ""

        attach_icon = " 📎" if getattr(task, "attachments", None) or getattr(task, "links", None) else ""

        # text truncation
        text_val = getattr(task, "text", getattr(task, "task", ""))
        if max_text_length and max_text_length > 0 and len(text_val) > max_text_length:
            text_val = text_val[: max_text_length - 3] + "..."

        task_style = "dim strike" if getattr(task, "completed", False) else ""
        row = []
        if show_ids:
            row.append(str(getattr(task, "id", "")))
        row.append(status)
        row.append(f"[{priority_color}]{getattr(task, 'priority', '')}[/{priority_color}]")
        if getattr(task, "completed", False):
            row.append(f"[{task_style}]{text_val}[/{task_style}]{attach_icon}")
        else:
            row.append(f"{text_val}{attach_icon}")
        if not compact_mode:
            row.append(tags_str)
        if show_dates:
            created = getattr(task, "created", getattr(task, "created_at", None))
            if created:
                try:
                    created_date = datetime.fromisoformat(created).strftime('%Y-%m-%d')
                    row.append(created_date)
                except:
                    row.append("")
            else:
                row.append("")
        table.add_row(*row)
        count[getattr(task, "completed", False)] = count.get(getattr(task, "completed", False), 0) + 1

    console.print(table)
    if not compact_mode:
        console.print("\n")
    console.print(f"[cyan]Total tasks:{sum(count.values())}")
    console.print(f"[cyan]Active tasks:{count.get(False, 0)}")
    console.print(f"[green]Completed tasks:{count.get(True, 0)}")

    if show_all:
        active = len([t for t in tasks if not getattr(t, "completed", False)])
        completed = len([t for t in tasks if getattr(t, "completed", False)])
        console.print(f"\n[dim]Total: {len(tasks)} | Active: {active} | Completed: {completed}[/dim]")


@cli.command()
@click.argument("task_id", type=int)
def done(task_id):
    """Mark a task as done"""
    from tix.config import CONFIG

    task = storage.get_task(task_id)
    if not task:
        console.print(f"[red]✗[/red] Task #{task_id} not found")
        return

    if getattr(task, "completed", False):
        console.print(f"[yellow]![/yellow] Task #{task_id} already completed")
        return

    # mark and persist
    if hasattr(task, "mark_done"):
        task.mark_done()
    else:
        task.completed = True
        task.completed_at = datetime.now().isoformat()
    storage.update_task(task)

    if CONFIG.get('notifications', {}).get('on_completion', True):
        console.print(f"[green]✔[/green] Completed: {getattr(task, 'text', getattr(task, 'task', ''))}")
    else:
        console.print(f"[green]✔[/green] Task #{task_id} completed")


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
        if not click.confirm(f"Are you sure you want to delete task #{task_id}: '{getattr(task, 'text', getattr(task, 'task', ''))}'?"):
            console.print("[yellow]⚠ Cancelled[/yellow]")
            return

    # Auto-backup
    try:
        bpath = create_backup(storage.storage_path)
        console.print(f"[dim]Backup created before delete:[/dim] {bpath}")
    except Exception as e:
        console.print(f"[red]Failed to create backup before delete:[/red] {e}")
        console.print("[red]Aborting delete.[/red]")
        return

    # delete
    if hasattr(storage, "delete_task"):
        ok = storage.delete_task(task_id)
        if ok:
            console.print(f"[red]✗[/red] Removed: {getattr(task, 'text', getattr(task, 'task', ''))}")
    elif hasattr(storage, "remove_task"):
        storage.remove_task(task_id)
        console.print(f"[red]✖ Task {task_id} removed[/red]")
    else:
        # fallback: write back without that task
        try:
            tasks = storage.load_tasks()
            remaining = [t for t in tasks if getattr(t, "id", None) != task_id]
            if hasattr(storage, "save_tasks"):
                storage.save_tasks(remaining)
            else:
                console.print(f"[red]✗[/red] Could not remove task {task_id} (no supported API).")
        except Exception as e:
            console.print(f"[red]✗[/red] Error removing task: {e}")


@cli.command()
@click.option("--completed/--active", default=True, help="Clear completed or active tasks")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def clear(completed, force):
    """Clear multiple tasks at once"""
    tasks = storage.load_tasks()
    if completed:
        to_clear = [t for t in tasks if getattr(t, "completed", False)]
        remaining = [t for t in tasks if not getattr(t, "completed", False)]
        task_type = "completed"
    else:
        to_clear = [t for t in tasks if not getattr(t, "completed", False)]
        remaining = [t for t in tasks if getattr(t, "completed", False)]
        task_type = "active"

    if not to_clear:
        console.print(f"[yellow]No {task_type} tasks to clear[/yellow]")
        return

    count = len(to_clear)
    if not force:
        console.print(f"[yellow]About to clear {count} {task_type} task(s):[/yellow]")
        for task in to_clear[:5]:
            console.print(f"  - {getattr(task, 'text', getattr(task, 'task', ''))}")
        if count > 5:
            console.print(f"  ... and {count - 5} more")
        if not click.confirm("Continue?"):
            console.print("[dim]Cancelled[/dim]")
            return

    # Backup before clear
    try:
        bpath = create_backup(storage.storage_path)
        console.print(f"[dim]Backup created before clear:[/dim] {bpath}")
    except Exception as e:
        console.print(f"[red]Failed to create backup before clear:[/red] {e}")
        console.print("[red]Aborting clear.[/red]")
        return

    if hasattr(storage, "save_tasks"):
        storage.save_tasks(remaining)
    elif hasattr(storage, "save"):
        storage.save(remaining)
    else:
        # fallback: try update
        for t in remaining:
            try:
                storage.update_task(t)
            except Exception:
                pass

    console.print(f"[green]✔[/green] Cleared {count} {task_type} task(s)")


@cli.command()
@click.argument("task_id", type=int)
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
        old = getattr(task, "text", getattr(task, "task", ""))
        task.text = text
        changes.append(f"text: '{old}' → '{text}'")
    if priority:
        old = getattr(task, "priority", None)
        task.priority = priority
        changes.append(f"priority: {old} → {priority}")
    for tag in add_tag:
        if tag not in getattr(task, "tags", []):
            if not hasattr(task, "tags"):
                task.tags = []
            task.tags.append(tag)
            changes.append(f"+tag: '{tag}'")
    for tag in remove_tag:
        if tag in getattr(task, "tags", []):
            task.tags.remove(tag)
            changes.append(f"-tag: '{tag}'")
    if due:
        new_date = get_date(due)
        if new_date:
            old_date = getattr(task, "due", None)
            task.due = new_date
            changes.append(f"due date: {old_date} → {new_date}")
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
            console.print("[red]Error processing due date[/red]")

    if attach:
        attachment_dir = Path.home() / ".tix" / "attachments" / str(task.id)
        attachment_dir.mkdir(parents=True, exist_ok=True)
        for file_path in attach:
            try:
                src = Path(file_path).expanduser().resolve()
                if not src.exists():
                    console.print(f"[red]✗[/red] File not found: {file_path}")
                    continue
                dest = attachment_dir / src.name
                dest.write_bytes(src.read_bytes())
                if not hasattr(task, "attachments"):
                    task.attachments = []
                task.attachments.append(str(dest))
            except Exception as e:
                console.print(f"[red]✗[/red] Failed to attach {file_path}: {e}")
        changes.append(f"attachments added: {[Path(f).name for f in attach]}")

    if link:
        if not hasattr(task, "links"):
            task.links = []
        task.links.extend(link)
        changes.append(f"links added: {list(link)}")

    if changes:
        storage.update_task(task)
        console.print(f"[green]✔[/green] Updated task #{task_id}:")
        for change in changes:
            console.print(f"  • {change}")
        from tix.config import CONFIG
        if CONFIG.get('notifications', {}).get('on_update', True):
            console.print(f"[green]✔[/green] Updated task #{task_id}:")
            for c in changes:
                console.print(f"  • {c}")
        else:
            console.print(f"[green]✔[/green] Task #{task_id} updated")
    else:
        console.print("[yellow]No changes made[/yellow]")


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
    for tid in task_ids:
        task = storage.get_task(tid)
        if not task:
            not_found.append(tid)
        elif getattr(task, "completed", False):
            already_done.append(tid)
        else:
            if hasattr(task, "mark_done"):
                task.mark_done()
            else:
                task.completed = True
                task.completed_at = datetime.now().isoformat()
            storage.update_task(task)
            completed.append((tid, getattr(task, "text", getattr(task, "task", ""))))
    if completed:
        console.print("[green]✔ Completed:[/green]")
        for tid, text in completed:
            console.print(f"  #{tid}: {text}")
    if already_done:
        console.print(f"[yellow]Already done: {', '.join(map(str, already_done))}[/yellow]")
    if not_found:
        console.print(f"[red]Not found: {', '.join(map(str, not_found))}[/red]")


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
    old_priority = getattr(task, "priority", None)
    task.priority = priority
    storage.update_task(task)
    color = {"high": "red", "medium": "yellow", "low": "green"}[priority]
    console.print(f"[green]✔[/green] Changed priority: {old_priority} → [{color}]{priority}[/{color}]")


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
    src = storage.get_task(from_id)
    if not src:
        console.print(f"[red]✗[/red] Task #{from_id} not found")
        return
    if storage.get_task(to_id):
        console.print(f"[red]✗[/red] Task #{to_id} already exists")
        return
    tasks = storage.load_tasks()
    tasks = [t for t in tasks if getattr(t, "id", None) != from_id]
    src.id = to_id
    tasks.append(src)
    if hasattr(storage, "save_tasks"):
        storage.save_tasks(sorted(tasks, key=lambda t: t.id))
    else:
        for t in tasks:
            storage.update_task(t)
    console.print(f"[green]✔[/green] Moved task from #{from_id} to #{to_id}")


@cli.command()
@click.argument("query")
@click.option("--tag", "-t", help="Filter by tag")
@click.option(
    "--priority", "-p", type=click.Choice(["low", "medium", "high"]), help="Filter by priority"
)
@click.option("--priority", "-p", type=click.Choice(["low", "medium", "high"]), help="Filter by priority")
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

    if not completed:
        tasks = [t for t in tasks if not getattr(t, "completed", False)]
    q = query.lower()
    results = [t for t in tasks if q in getattr(t, "text", getattr(t, "task", "")).lower()]
    if tag:
        results = [t for t in results if tag in getattr(t, "tags", [])]
    if priority:
        results = [t for t in results if getattr(t, "priority", None) == priority]
    if not results:
        console.print(f"[dim]No tasks matching '{query}'[/dim]")
        return
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

    for t in results:
        status = "✔" if getattr(t, "completed", False) else "○"
        priority_color = {"high": "red", "medium": "yellow", "low": "green"}.get(getattr(t, "priority", "medium"), "yellow")
        tags_str = ", ".join(getattr(t, "tags", [])) if getattr(t, "tags", None) else ""
        ttext = getattr(t, "text", getattr(t, "task", ""))
        highlighted = ttext.replace(query, f"[bold yellow]{query}[/bold yellow]") if query.lower() in ttext.lower() else ttext
        table.add_row(str(getattr(t, "id", "")), status, f"[{priority_color}]{getattr(t, 'priority', '')}[/{priority_color}]", highlighted, tags_str)
    console.print(table)


@cli.command()
@click.option("--priority", "-p", type=click.Choice(["low", "medium", "high"]), help="Filter by priority")
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
    table.add_column("✓", width=3)
    table.add_column("Priority", width=8)
    table.add_column("Task")
    table.add_column("Tags", style="dim")

    for task in sorted(tasks, key=lambda t: (t.completed, t.id)):
        status = "✓" if task.completed else "○"
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
    if no_tags:
        untagged = [t for t in tasks if not getattr(t, "tags", [])]
        if not untagged:
            console.print("[dim]All tasks have tags[/dim]")
            return
        console.print(f"[bold]{len(untagged)} task(s) without tags:[/bold]\n")
        for t in untagged:
            status = "✔" if getattr(t, "completed", False) else "○"
            console.print(f"{status} #{getattr(t,'id','')}: {getattr(t,'text',getattr(t,'task',''))}")
    else:
        tag_counts = {}
        for t in tasks:
            for tg in getattr(t, "tags", []):
                tag_counts[tg] = tag_counts.get(tg, 0) + 1
        if not tag_counts:
            console.print("[dim]No tags found[/dim]")
            return
        console.print("[bold]Tags in use:[/bold]\n")
        for tg, cnt in sorted(tag_counts.items(), key=lambda x: (-x[1], x[0])):
            console.print(f"  • {tg} ({cnt} task{'s' if cnt != 1 else ''})")


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
    show_stats(storage)
    if detailed:
        tasks = storage.load_tasks()
        if tasks:
            console.print("\n[bold]Detailed Breakdown:[/bold]\n")
            from collections import defaultdict
            by_day = defaultdict(list)
            for t in tasks:
                if getattr(t, "completed", False) and getattr(t, "completed_at", None):
                    try:
                        day = datetime.fromisoformat(getattr(t, "completed_at")).date()
                    except Exception:
                        continue
                    by_day[day].append(t)
            if by_day:
                console.print("[bold]Recent Completions:[/bold]")
                for day in sorted(by_day.keys(), reverse=True)[:5]:
                    console.print(f"  • {day}: {len(by_day[day])} task(s)")


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

    if not tasks:
        console.print("[dim]No tasks to report[/dim]")
        return
    active = [t for t in tasks if not getattr(t, "completed", False)]
    completed = [t for t in tasks if getattr(t, "completed", False)]
    if format == "json":
        import json
        report_data = {'generated': datetime.now().isoformat(),
                       'summary': {'total': len(tasks), 'active': len(active), 'completed': len(completed)},
                       'tasks': [t.to_dict() for t in tasks]}
        report_text = json.dumps(report_data, indent=2)
    elif format == 'markdown':
        lines = ["# TIX Task Report", "", f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}", "", "## Summary", "", f"- **Total Tasks:** {len(tasks)}", f"- **Active:** {len(active)}", f"- **Completed:** {len(completed)}", ""]
        for t in active:
            tags = f" `{', '.join(getattr(t,'tags',[]))}`" if getattr(t,'tags',None) else ""
            lines.append(f"- [ ] **#{getattr(t,'id','')}** {getattr(t,'text',getattr(t,'task',''))}{tags}")
        if completed:
            lines.append("")
            lines.append("## Completed Tasks")
            lines.append("")
            lines.append("| ID | Task | Priority | Tags | Completed At |")
            lines.append("|---|---|---|---|---|")
            for t in completed:
                tags = ", ".join([f"`{x}`" for x in getattr(t,'tags',[])]) if getattr(t,'tags',None) else "-"
                comp = getattr(t,'completed_at', "-")
                lines.append(f"| #{getattr(t,'id','')} | ~~{getattr(t,'text',getattr(t,'task',''))}~~ | {getattr(t,'priority','')} | {tags} | {comp} |")
        report_text = "\n".join(lines)
    else:
        lines = ["TIX TASK REPORT", "="*40, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", "", f"Total Tasks: {len(tasks)}", f"Active: {len(active)}", f"Completed: {len(completed)}", "", "ACTIVE TASKS:", "-"*20]
        for t in active:
            tags = f" [{', '.join(getattr(t,'tags',[]))}]" if getattr(t,'tags',None) else ""
            lines.append(f"#{getattr(t,'id','')} [{getattr(t,'priority','')}] {getattr(t,'text',getattr(t,'task',''))}{tags}")
        lines.append("")
        lines.append("COMPLETED TASKS:")
        lines.append("-"*20)
        for t in completed:
            tags = f" [{', '.join(getattr(t,'tags',[]))}]" if getattr(t,'tags',None) else ""
            lines.append(f"#{getattr(t,'id','')} ✔ {getattr(t,'text',getattr(t,'task',''))}{tags}")
        report_text = "\n".join(lines)
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
    if not getattr(task, "attachments", None) and not getattr(task, "links", None):
        console.print(f"[yellow]![/yellow] Task {task_id} has no attachments or links")
        return

    def safe_open(path_or_url, is_link=False):
        system = platform.system()
        try:
            if system == "Linux":
                if "microsoft" in platform.release().lower():
                    subprocess.Popen(["explorer.exe", str(path_or_url)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    subprocess.Popen(["xdg-open", str(path_or_url)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif system == "Darwin":
                subprocess.Popen(["open", str(path_or_url)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif system == "Windows":
                subprocess.Popen(["explorer.exe", str(path_or_url)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            console.print(f"[green]✔[/green] Opened {'link' if is_link else 'file'}: {path_or_url}")
        except Exception as e:
            console.print(f"[yellow]![/yellow] Could not open {'link' if is_link else 'file'}: {path_or_url} ({e})")

    for file_path in getattr(task, "attachments", []):
        p = Path(file_path)
        if not p.exists():
            console.print(f"[red]✗[/red] File not found: {file_path}")
            continue
        safe_open(p)
    for url in getattr(task, "links", []):
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


@cli.group()
def config():
    """Manage TIX configuration settings"""
    pass


@config.command('init')
def config_init():
    """Initialize configuration file with defaults"""
    from tix.config import create_default_config_if_not_exists, get_config_path

    if create_default_config_if_not_exists():
        console.print(f"[green]✔[/green] Created default config at {get_config_path()}")
    else:
        console.print(f"[yellow]![/yellow] Config file already exists at {get_config_path()}")


@config.command('show')
@click.option('--key', '-k', help='Show specific config key (e.g., defaults.priority)')
def config_show(key):
    """Show current configuration"""
    from tix.config import load_config, get_config_value, get_config_path
    import yaml

    if key:
        value = get_config_value(key)
        if value is None:
            console.print(f"[red]✗[/red] Config key '{key}' not found")
        else:
            console.print(f"[cyan]{key}:[/cyan] {value}")
    else:
        config = load_config()
        console.print(f"[bold]Configuration from {get_config_path()}:[/bold]\n")
        console.print(yaml.dump(config, default_flow_style=False, sort_keys=False))


@config.command('set')
@click.argument('key')
@click.argument('value')
def config_set(key, value):
    """Set a configuration value (e.g., tix config set defaults.priority high)"""
    from tix.config import set_config_value

    # Try to parse value as YAML to support different types
    import yaml
    try:
        parsed_value = yaml.safe_load(value)
    except yaml.YAMLError:
        parsed_value = value

    if set_config_value(key, parsed_value):
        console.print(f"[green]✔[/green] Set {key} = {parsed_value}")
    else:
        console.print(f"[red]✗[/red] Failed to set configuration")


@config.command('get')
@click.argument('key')
def config_get(key):
    """Get a configuration value"""
    from tix.config import get_config_value

    value = get_config_value(key)
    if value is None:
        console.print(f"[red]✗[/red] Config key '{key}' not found")
    else:
        console.print(f"{value}")


@config.command('reset')
@click.option('--confirm', '-y', is_flag=True, help='Skip confirmation')
def config_reset(confirm):
    """Reset configuration to defaults"""
    from tix.config import DEFAULT_CONFIG, save_config, get_config_path

    if not confirm:
        if not click.confirm("Are you sure you want to reset configuration to defaults?"):
            console.print("[yellow]⚠ Cancelled[/yellow]")
            return

    if save_config(DEFAULT_CONFIG):
        console.print(f"[green]✔[/green] Reset configuration to defaults at {get_config_path()}")
    else:
        console.print(f"[red]✗[/red] Failed to reset configuration")


@config.command('path')
def config_path():
    """Show path to configuration file"""
    from tix.config import get_config_path
    console.print(get_config_path())


@config.command('edit')
def config_edit():
    """Open configuration file in default editor"""
    from tix.config import get_config_path, create_default_config_if_not_exists

    create_default_config_if_not_exists()
    config_path = get_config_path()

    editor = os.environ.get('EDITOR', 'nano')
    try:
        subprocess.run([editor, config_path])
        console.print(f"[green]✔[/green] Configuration edited")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to open editor: {e}")
        console.print(f"[dim]Try: export EDITOR=vim or export EDITOR=nano[/dim]")

@cli.command()
@click.argument("task_id", type=int)
def archive(task_id):
    """Archive (soft-delete) a task"""
    task = storage.get_task(task_id)
    if not task:
        console.print(f"[red]✗[/red] Task #{task_id} not found")
        return
    # Check if already archived
    if ArchiveStorage().get_task(task_id):
        console.print(f"[yellow]![/yellow] Task #{task_id} is already archived.")
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
    # Check for ID conflict
    if storage.get_task(task_id):
        console.print(f"[red]✗[/red] Cannot unarchive: Task ID #{task_id} already exists in active tasks.")
        return
    # Restore the original task object
    storage.save_task(task)  # Assumes save_task preserves ID and metadata
    archive.remove_task(task_id)
    console.print(f"[green]✔[/green] Restored: {task.text}")


if __name__ == '__main__':
    cli()