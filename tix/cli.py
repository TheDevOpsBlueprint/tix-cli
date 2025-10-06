# tix/cli.py -- cleaned, drop-in replacement preserving backup/restore feature
import click
import subprocess
import platform
import os
import sys
from rich.console import Console
from rich.table import Table
from pathlib import Path
from tix.storage.json_storage import TaskStorage
from tix.storage.context_storage import ContextStorage
from tix.storage.history import HistoryManager
from tix.storage.backup import create_backup, list_backups, restore_from_backup
from tix.models import Task
from rich.prompt import Prompt
from rich.markdown import Markdown
from datetime import datetime
# from .storage import storage
from .config import CONFIG
from .storage import context_storage

console = Console()
storage = TaskStorage()

from typing import Optional, Dict, Any
import json


context_storage = ContextStorage()
history = HistoryManager()

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

# -----------------------
# Backup CLI group
# -----------------------
@cli.group(help="Backup and restore task data")
def backup():
    pass


@backup.command("create")
@click.argument("filename", required=False)
@click.option("--data-file", type=click.Path(), default=None, help="Path to tix data file (for testing/dev)")
def backup_create(filename, data_file):
    """Create a timestamped backup of your tasks file."""
    try:
        data_path = Path(data_file) if data_file else storage.storage_path
        bpath = create_backup(data_path, filename)
        console.print(f"[green]✔ Backup created:[/green] {bpath}")
    except Exception as e:
        console.print(f"[red]Backup failed:[/red] {e}")
        raise click.Abort()


@backup.command("list")
@click.option("--data-file", type=click.Path(), default=None, help="Path to tix data file (for testing/dev)")
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


@backup.command("restore")
@click.argument("backup_file", required=True)
@click.option("--data-file", type=click.Path(), default=None, help="Path to tix data file (for testing/dev)")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation")
def backup_restore(backup_file, data_file, yes):
    """Restore tasks from a previous backup. Will ask confirmation by default."""
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

    storage.update_task(new_task, record_history=False)

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
    old_priority = getattr(task, "priority", None)
    task.priority = priority
    storage.update_task(task)
    color = {"high": "red", "medium": "yellow", "low": "green"}[priority]
    console.print(f"[green]✔[/green] Changed priority: {old_priority} → [{color}]{priority}[/{color}]")

def apply(op):
    """Re-apply an operation (used for redo)"""
    if op["op"] == "add":
        tasks = storage.load_tasks()
        restored_task = Task.from_dict(op["after"])
        tasks.append(restored_task)
        storage.save_tasks(sorted(tasks, key=lambda t: t.id))
    elif op["op"] == "update":
        storage.update_task(Task.from_dict(op["after"]), record_history=False)
    elif op["op"] == "delete":
        storage.delete_task(op["before"]["id"], record_history=False)

def apply_inverse(op):
    """Apply the inverse of an operation (used for undo)"""
    if op["op"] == "add":
        deleted = storage.delete_task(op["after"]["id"], record_history=False)
    elif op["op"] == "update":
        storage.update_task(Task.from_dict(op["before"]), record_history=False)
    elif op["op"] == "delete":
        tasks = storage.load_tasks()
        restored_task = Task.from_dict(op["before"])
        tasks.append(restored_task)
        storage.save_tasks(sorted(tasks, key=lambda t: t.id))

@cli.command()
def undo():
    """Undo the last operation"""
    op = history.pop_undo()
    if not op:
        console.print("[yellow]No operations to undo[/yellow]")
        return

    apply_inverse(op)
    console.print(f"[green]✔ Undo complete[/green]")

@cli.command()
def redo():
    """Redo the last undone operation"""
    op = history.pop_redo()
    if not op:
        console.print("[yellow]No operations to redo[/yellow]")
        return

    apply(op)
    console.print(f"[green]✔ Redo complete[/green]")

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
        
@click.argument("name")
def context(name):
    """Switch or create context"""
    context_storage.set_active_context(name)
    console.print(f"[blue]Switched to context:[/blue] {name}")
@click.argument("from_id", type=int)
@click.argument("to_id", type=int)
def move(from_id, to_id):
    """Move/renumber a task to a different ID"""
    if from_id == to_id:
        console.print("[yellow]Source and destination IDs are the same[/yellow]")
        return
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
@click.option("--priority", "-p", type=click.Choice(["low", "medium", "high"]), help="Filter by priority")
@click.option("--completed", "-c", is_flag=True, help="Search in completed tasks")
def search(query, tag, priority, completed):
    """Search tasks by text"""
    tasks = storage.load_tasks()
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
    for t in results:
        status = "✔" if getattr(t, "completed", False) else "○"
        priority_color = {"high": "red", "medium": "yellow", "low": "green"}.get(getattr(t, "priority", "medium"), "yellow")
        tags_str = ", ".join(getattr(t, "tags", [])) if getattr(t, "tags", None) else ""
        ttext = getattr(t, "text", getattr(t, "task", ""))
        highlighted = ttext.replace(query, f"[bold yellow]{query}[/bold yellow]") if query.lower() in ttext.lower() else ttext
        table.add_row(str(getattr(t, "id", "")), status, f"[{priority_color}]{getattr(t, 'priority', '')}[/{priority_color}]", highlighted, tags_str)
    console.print(table)


# ---- Saved filters: replace the old `filter` command with this group ----
from typing import Optional, Dict, Any
import json

FILTERS_PATH = Path.home() / ".tix" / "filters.json"
FILTERS_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_saved_filters() -> Dict[str, Dict[str, Any]]:
    """Return mapping name -> filter-params"""
    if not FILTERS_PATH.exists():
        return {}
    try:
        with FILTERS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            return {}
    except Exception:
        return {}


def _save_saved_filters(filters: Dict[str, Dict[str, Any]]) -> bool:
    try:
        with FILTERS_PATH.open("w", encoding="utf-8") as f:
            json.dump(filters, f, indent=2, sort_keys=True)
        return True
    except Exception:
        return False


@cli.group()
def filter():
    """Manage and apply saved filters"""
    pass


@filter.command("apply")
@click.option("--priority", "-p", type=click.Choice(["low", "medium", "high"]), help="Filter by priority")
@click.option("--tag", "-t", help="Filter by tag")
@click.option("--completed/--active", "-c/-a", default=None, help="Filter by completion status")
@click.option("--saved", "-s", "saved_name", help="Apply a saved filter by name")
def filter_apply(priority: Optional[str], tag: Optional[str], completed: Optional[bool], saved_name: Optional[str]):
    """
    Apply a filter (immediately). Use --saved <name> to apply saved filters.
    If --saved is provided, any inline options are ignored (saved filter takes precedence).
    """
    # If saved filter requested, load and override CLI params
    if saved_name:
        saved = _load_saved_filters().get(saved_name)
        if not saved:
            console.print(f"[red]✗[/red] Saved filter '{saved_name}' not found")
            return
        priority = saved.get("priority")
        tag = saved.get("tag")
        completed = saved.get("completed")

    # Now perform filtering (same UX as previous 'filter' command)
    tasks = storage.load_tasks() if hasattr(storage, "load_tasks") else []

    # completion filter: None = all, True = completed, False = active
    if completed is not None:
        tasks = [t for t in tasks if getattr(t, "completed", False) == completed]

    if priority:
        tasks = [t for t in tasks if getattr(t, "priority", None) == priority]

    if tag:
        tasks = [t for t in tasks if tag in getattr(t, "tags", [])]

    if not tasks:
        console.print("[dim]No matching tasks[/dim]")
        return

    # Build filter description
    filters_desc = []
    if priority:
        filters_desc.append(f"priority={priority}")
    if tag:
        filters_desc.append(f"tag='{tag}'")
    if completed is not None:
        filters_desc.append("completed" if completed else "active")
    filter_desc = " AND ".join(filters_desc) if filters_desc else "all"
    console.print(f"[bold]{len(tasks)} task(s) matching [{filter_desc}]:[/bold]\n")

    table = Table()
    table.add_column("ID", style="cyan", width=4)
    table.add_column("✔", width=3)
    table.add_column("Priority", width=8)
    table.add_column("Task")
    table.add_column("Tags", style="dim")

    for task in sorted(tasks, key=lambda t: (getattr(t, "completed", False), getattr(t, "id", 0))):
        status = "✔" if getattr(task, "completed", False) else "○"
        priority_color = {"high": "red", "medium": "yellow", "low": "green"}.get(getattr(task, "priority", "medium"), "yellow")
        tags_str = ", ".join(getattr(task, "tags", [])) if getattr(task, "tags", None) else ""
        table.add_row(
            str(getattr(task, "id", "")),
            status,
            f"[{priority_color}]{getattr(task, 'priority', '')}[/{priority_color}]",
            getattr(task, "text", getattr(task, "task", "")),
            tags_str,
        )

    console.print(table)


@filter.command("save")
@click.argument("name")
@click.option("--priority", "-p", type=click.Choice(["low", "medium", "high"]), help="Filter by priority")
@click.option("--tag", "-t", help="Filter by tag")
@click.option("--completed/--active", "-c/-a", default=None, help="Filter by completion status")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing saved filter of same name")
def filter_save(name: str, priority: Optional[str], tag: Optional[str], completed: Optional[bool], force: bool):
    """
    Save a filter under <name>. Later you can apply it with `tix filter apply --saved <name>`.
    Example: tix filter save work -t work -p high
    """
    filters = _load_saved_filters()
    if name in filters and not force:
        console.print(f"[red]✗[/red] A saved filter named '{name}' already exists. Use --force to overwrite.")
        return

    storage_obj = {
        "priority": priority,
        "tag": tag,
        # store completed as True/False/null
        "completed": None if completed is None else (True if completed else False),
        "saved_at": datetime.now().isoformat()
    }

    # Remove empty keys
    storage_obj = {k: v for k, v in storage_obj.items() if v is not None}
    filters[name] = storage_obj
    if _save_saved_filters(filters):
        console.print(f"[green]✔[/green] Saved filter '{name}'")
        # quick usage hint
        parts = []
        if "priority" in storage_obj:
            parts.append(f"-p {storage_obj['priority']}")
        if "tag" in storage_obj:
            parts.append(f"-t {storage_obj['tag']}")
        if "completed" in storage_obj:
            parts.append("--completed" if storage_obj["completed"] else "--active")
        if parts:
            console.print(f"[dim]Use: tix filter apply --saved {name}  (equivalent: tix filter apply {' '.join(parts)})[/dim]")
    else:
        console.print(f"[red]✗[/red] Failed to save filter '{name}'")


@filter.command("list")
def filter_list():
    """List saved filters"""
    filters = _load_saved_filters()
    if not filters:
        console.print("[dim]No saved filters[/dim]")
        return

    table = Table(title="Saved Filters")
    table.add_column("Name", style="cyan")
    table.add_column("Filter", style="dim")
    table.add_column("Saved At", style="green", width=22)

    for name, obj in sorted(filters.items(), key=lambda x: x[0]):
        parts = []
        if "priority" in obj:
            parts.append(f"priority={obj['priority']}")
        if "tag" in obj:
            parts.append(f"tag='{obj['tag']}'")
        if "completed" in obj:
            parts.append("completed" if obj["completed"] else "active")
        filter_desc = " AND ".join(parts) if parts else "all"
        saved_at = obj.get("saved_at", "-")
        table.add_row(name, filter_desc, saved_at)

    console.print(table)
# ---- end saved filters ----



@cli.command()
@click.option("--no-tags", is_flag=True, help="Show tasks without tags")
def tags(no_tags):
    """List all unique tags or tasks without tags"""
    tasks = storage.load_tasks()
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


if __name__ == '__main__':
    cli()