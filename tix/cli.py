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
# from tix.storage.context_storage import ContextStorage
from tix.storage.history import HistoryManager
from tix.storage.backup import create_backup, list_backups, restore_from_backup
from tix.models import Task, STATUS_CHOICES
from rich.prompt import Prompt
from rich.markdown import Markdown
from datetime import datetime
from typing import List
# from .storage import storage
# from .config import CONFIG
# from .context import context_storage

console = Console()
storage = TaskStorage()

def parse_time_estimate(time_str: str) -> int:
    """Parse time string like '2h', '30m', '1h30m' into minutes"""
    time_str = time_str.lower().strip()
    total_minutes = 0
    
    if 'h' in time_str:
        parts = time_str.split('h')
        hours = int(parts[0])
        total_minutes += hours * 60
        if len(parts) > 1 and parts[1]:
            mins = parts[1].replace('m', '').strip()
            if mins:
                total_minutes += int(mins)
    elif 'm' in time_str:
        total_minutes = int(time_str.replace('m', ''))
    else:
        total_minutes = int(time_str)
    
    return total_minutes


def parse_due_date(date_str: str) -> str:
    """Parse due date string into ISO format.
    Supports: '2026-04-23', 'today', 'tomorrow', 'next-week', 'in-3-days'
    """
    from datetime import datetime, timedelta
    
    date_str = date_str.lower().strip()
    today = datetime.now().date()
    
    if date_str == 'today':
        return datetime.combine(today, datetime.min.time()).isoformat()
    elif date_str == 'tomorrow':
        return datetime.combine(today + timedelta(days=1), datetime.min.time()).isoformat()
    elif date_str == 'next-week' or date_str == 'nextweek':
        return datetime.combine(today + timedelta(days=7), datetime.min.time()).isoformat()
    elif date_str.startswith('in-') and date_str.endswith('-days'):
        try:
            days = int(date_str.split('-')[1])
            return datetime.combine(today + timedelta(days=days), datetime.min.time()).isoformat()
        except (ValueError, IndexError):
            pass
    else:
        # Try parsing as ISO date
        try:
            parsed = datetime.strptime(date_str, '%Y-%m-%d')
            return parsed.isoformat()
        except ValueError:
            pass
        try:
            parsed = datetime.fromisoformat(date_str)
            return parsed.isoformat()
        except ValueError:
            pass
    
    raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD, 'today', 'tomorrow', 'in-N-days'")


def parse_blocked_by(blocked_by_str: str) -> List[int]:
    """Parse blocked-by string like '1,2,3' into list of integers"""
    if not blocked_by_str:
        return []
    parts = blocked_by_str.split(',')
    result = []
    for p in parts:
        p = p.strip()
        if p:
            try:
                result.append(int(p))
            except ValueError:
                raise ValueError(f"Invalid task ID: {p}")
    return result


def format_time_helper(minutes: int) -> str:
    """Format minutes into human readable format"""
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    mins = minutes % 60
    if mins == 0:
        return f"{hours}h"
    return f"{hours}h {mins}m"

from typing import Optional, Dict, Any
import json


# context_storage = ContextStorage()
history = HistoryManager()

@click.group(invoke_without_command=True)
@click.version_option(version="0.8.0", prog_name="tix", message='%(prog)s, version %(version)s (Python ' + platform.python_version() + ')')
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
@click.option('--estimate', '-e', help='Time estimate (e.g., 2h, 30m, 1h30m)')
# Team collaboration options
@click.option('--owner', '-o', help='Assign owner to task')
@click.option('--reviewer', '-r', help='Assign reviewer to task')
@click.option('--status', '-s', default='todo',
              type=click.Choice(STATUS_CHOICES),
              help='Set task status')
@click.option('--due-at', '-d', 'due_at', help='Due date (YYYY-MM-DD, today, tomorrow, in-N-days)')
@click.option('--handoff-note', '-n', 'handoff_note', help='Add handoff note for task')
@click.option('--blocked-by', '-b', help='Tasks blocking this one (comma-separated IDs: 1,2,3)')
@click.option('--incident', '-i', is_flag=True, help='Mark as incident task')
def add(task, priority, tag, attach, link, estimate,
        owner, reviewer, status, due_at, handoff_note, blocked_by, incident):
    """Add a new task (with team collaboration support)"""
    from tix.config import CONFIG

    if not task or not task.strip():
        console.print("[red]✗[/red] Task text cannot be empty")
        sys.exit(1)

    # Parse time estimate
    estimate_minutes = None
    if estimate:
        try:
            estimate_minutes = parse_time_estimate(estimate)
        except ValueError:
            console.print("[red]✗[/red] Invalid time format. Use format like: 2h, 30m, 1h30m")
            return

    # Parse due date
    parsed_due_at = None
    if due_at:
        try:
            parsed_due_at = parse_due_date(due_at)
        except ValueError as e:
            console.print(f"[red]✗[/red] {str(e)}")
            return

    # Parse blocked-by
    parsed_blocked_by = []
    if blocked_by:
        try:
            parsed_blocked_by = parse_blocked_by(blocked_by)
        except ValueError as e:
            console.print(f"[red]✗[/red] {str(e)}")
            return

    # Use config defaults if not specified
    if priority is None:
        priority = CONFIG.get('defaults', {}).get('priority', 'medium')
    
    # Merge config default tags with provided tags
    default_tags = CONFIG.get('defaults', {}).get('tags', [])
    all_tags = list(set(list(tag) + default_tags))
    
    # Create task with all team collaboration fields
    new_task = storage.add_task(
        task, 
        priority, 
        all_tags, 
        estimate=estimate_minutes,
        owner=owner,
        reviewer=reviewer,
        status=status,
        due_at=parsed_due_at,
        handoff_note=handoff_note,
        blocked_by=parsed_blocked_by,
        incident=incident,
    )
    
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
    status_color = new_task.get_status_color()
    console.print(f"[green]✔[/green] Added task #{new_task.id}: [{color}]{task}[/{color}]")
    
    # Show notification if enabled
    if CONFIG.get('notifications', {}).get('on_creation', True):
        if all_tags:
            tag_color = CONFIG.get('colors', {}).get('tags', 'cyan')
            console.print(f"[dim]  Tags: [{tag_color}]{', '.join(all_tags)}[/{tag_color}][/dim]")
        if attach or link:
            console.print(f"[dim]  Attachments/Links added[/dim]")
        if estimate:
            console.print(f"[dim]  Estimated time: {new_task.format_time(estimate_minutes)}[/dim]")
        # Show team collaboration fields
        if owner:
            console.print(f"[dim]  Owner: {owner}[/dim]")
        if reviewer:
            console.print(f"[dim]  Reviewer: {reviewer}[/dim]")
        if status != 'todo':
            console.print(f"[dim]  Status: [{status_color}]{status}[/{status_color}][/dim]")
        if due_at:
            console.print(f"[dim]  Due: {new_task.get_due_date_display()}[/dim]")
        if handoff_note:
            console.print(f"[dim]  Handoff note: {handoff_note[:50]}{'...' if len(handoff_note) > 50 else ''}[/dim]")
        if parsed_blocked_by:
            console.print(f"[dim]  Blocked by: #{', #'.join(map(str, parsed_blocked_by))}[/dim]")
        if incident:
            console.print(f"[red]  ⚠ INCIDENT TASK[/red]")


@cli.command()
@click.option("--all", "-a", "show_all", is_flag=True, help="Show completed tasks too")
@click.option("--owner", "-o", help="Filter by owner (use 'none' for unassigned)")
@click.option("--reviewer", "-r", help="Filter by reviewer (use 'none' for no reviewer)")
@click.option("--status", "-s", type=click.Choice(STATUS_CHOICES), help="Filter by task status")
@click.option("--blocked", "-b", is_flag=True, help="Show only blocked tasks")
@click.option("--incident", "-i", is_flag=True, help="Show only incident tasks")
@click.option("--overdue", is_flag=True, help="Show only overdue tasks")
@click.option("--due-soon", is_flag=True, help="Show only tasks due soon (today/tomorrow)")
@click.option("--no-handoff", is_flag=True, help="Show only tasks needing handoff notes")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed view with owner, status, due date")
@click.option("--priority", "-p", type=click.Choice(['low', 'medium', 'high']), help="Filter by priority")
@click.option("--tag", "-t", help="Filter by tag")
def ls(show_all, owner, reviewer, status, blocked, incident, overdue, 
       due_soon, no_handoff, detailed, priority, tag):
    """List tasks with team collaboration filters and display"""
    from tix.config import CONFIG

    # Load all tasks first
    tasks = storage.load_tasks()

    # Apply basic completion filter
    if not show_all:
        tasks = [t for t in tasks if not t.completed]

    # Apply owner filter
    if owner is not None:
        if owner.lower() == 'none':
            tasks = [t for t in tasks if not t.has_owner()]
        else:
            tasks = [t for t in tasks if t.owner and t.owner.lower() == owner.lower()]

    # Apply reviewer filter
    if reviewer is not None:
        if reviewer.lower() == 'none':
            tasks = [t for t in tasks if not t.has_reviewer()]
        else:
            tasks = [t for t in tasks if t.reviewer and t.reviewer.lower() == reviewer.lower()]

    # Apply status filter
    if status:
        tasks = [t for t in tasks if t.status == status]

    # Apply blocked filter
    if blocked:
        tasks = [t for t in tasks if t.is_blocked()]

    # Apply incident filter
    if incident:
        tasks = [t for t in tasks if t.is_incident_task()]

    # Apply overdue filter
    if overdue:
        tasks = [t for t in tasks if t.is_overdue()]

    # Apply due-soon filter
    if due_soon:
        tasks = [t for t in tasks if t.is_due_soon(days=2)]

    # Apply no-handoff filter
    if no_handoff:
        tasks = [t for t in tasks if t.needs_handoff()]

    # Apply priority filter
    if priority:
        tasks = [t for t in tasks if t.priority == priority]

    # Apply tag filter
    if tag:
        tasks = [t for t in tasks if tag in t.tags]

    if not tasks:
        console.print("[dim]No tasks found matching your criteria[/dim]")
        return

    # Get display settings from config
    display_config = CONFIG.get('display', {})
    show_ids = display_config.get('show_ids', True)
    show_dates = display_config.get('show_dates', False)
    compact_mode = display_config.get('compact_mode', False)
    max_text_length = display_config.get('max_text_length', 0)

    # color settings
    priority_colors = CONFIG.get('colors', {}).get('priority', {})
    tag_color = CONFIG.get('colors', {}).get('tags', 'cyan')

    title = "Tasks"
    if show_all:
        title = "All Tasks"
    
    # Build table
    table = Table(title=title)
    if show_ids:
        table.add_column("ID", style="cyan", width=4)
    table.add_column("✔", width=3)
    table.add_column("Pri", width=4)
    if detailed:
        table.add_column("Status", width=12)
        table.add_column("Owner", width=10)
        table.add_column("Due", width=16)
    table.add_column("Task")
    if not compact_mode:
        table.add_column("Tags", style=tag_color)
    if show_dates:
        table.add_column("Created", style="dim")

    count = dict()
    owner_counts = {}
    status_counts = {}

    # Sort tasks: incidents first, then by priority (high first), then by status (blocked first)
    def sort_key(t):
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        status_order = {'blocked': 0, 'in_progress': 1, 'review': 2, 'todo': 3, 'done': 4}
        return (
            not t.incident,
            priority_order.get(t.priority, 1),
            status_order.get(t.status, 3),
            t.is_overdue(),
            t.id
        )

    for task in sorted(tasks, key=sort_key):
        check_status = "✔" if task.completed else "○"
        priority_color = priority_colors.get(task.priority,
                                            {'high': 'red', 'medium': 'yellow', 'low': 'green'}[task.priority])
        tags_str = ", ".join(task.tags) if task.tags else ""

        # Icons for special tasks
        icons = []
        if task.incident:
            icons.append("🔴")
        if task.is_blocked():
            icons.append("🚫")
        if task.is_overdue():
            icons.append("⏰")
        if task.needs_handoff():
            icons.append("📋")
        icon_str = " " + " ".join(icons) if icons else ""

        # Attachment icon
        attach_icon = " 📎" if task.attachments or task.links else ""

        # text truncation
        text_val = task.text
        if max_text_length and max_text_length > 0 and len(text_val) > max_text_length:
            text_val = text_val[: max_text_length - 3] + "..."

        task_style = "dim strike" if task.completed else ""
        row = []
        if show_ids:
            row.append(str(task.id))
        row.append(check_status)
        row.append(f"[{priority_color}]{task.priority[:3]}[/{priority_color}]")
        
        if detailed:
            # Status with color
            status_color = task.get_status_color()
            status_display = task.status.replace('_', '-')
            row.append(f"[{status_color}]{status_display}[/{status_color}]")
            
            # Owner
            owner_display = task.owner or "-"
            row.append(owner_display if len(owner_display) <= 10 else owner_display[:10])
            
            # Due date
            row.append(task.get_due_date_display())
        
        # Task text
        if task.completed:
            row.append(f"[{task_style}]{text_val}[/{task_style}]{icon_str}{attach_icon}")
        else:
            row.append(f"{text_val}{icon_str}{attach_icon}")
        
        if not compact_mode:
            row.append(tags_str)
        
        if show_dates:
            created = task.created_at
            if created:
                try:
                    created_date = datetime.fromisoformat(created).strftime('%Y-%m-%d')
                    row.append(created_date)
                except:
                    row.append("")
            else:
                row.append("")
        
        table.add_row(*row)
        
        # Count for summary
        count[task.completed] = count.get(task.completed, 0) + 1
        
        # Owner counts
        if task.owner:
            owner_counts[task.owner] = owner_counts.get(task.owner, 0) + 1
        else:
            owner_counts['(unassigned)'] = owner_counts.get('(unassigned)', 0) + 1
        
        # Status counts
        status_counts[task.status] = status_counts.get(task.status, 0) + 1

    console.print(table)
    
    # Summary
    if not compact_mode:
        console.print("\n")
    
    console.print(f"[cyan]Total: {sum(count.values())}[/cyan]")
    console.print(f"[cyan]Active: {count.get(False, 0)}[/cyan]")
    console.print(f"[green]Completed: {count.get(True, 0)}[/green]")
    
    # Owner breakdown in detailed mode
    if detailed and owner_counts:
        console.print("\n[bold]By Owner:[/bold]")
        for owner_name, cnt in sorted(owner_counts.items(), key=lambda x: (-x[1], x[0])):
            console.print(f"  • {owner_name}: {cnt} task{'s' if cnt != 1 else ''}")
    
    # Status breakdown
    if status_counts:
        console.print("\n[bold]By Status:[/bold]")
        for status_name, cnt in sorted(status_counts.items()):
            console.print(f"  • {status_name}: {cnt}")


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
# Team collaboration edit options
@click.option('--owner', '-o', help='Set/change owner (use "none" to clear)')
@click.option('--reviewer', '-r', help='Set/change reviewer (use "none" to clear)')
@click.option('--status', '-s', type=click.Choice(STATUS_CHOICES), help='Set task status')
@click.option('--due-at', '-d', 'due_at', help='Set due date (YYYY-MM-DD, today, tomorrow; use "none" to clear)')
@click.option('--handoff-note', '-n', 'handoff_note', help='Set handoff note (use "none" to clear)')
@click.option('--blocked-by', '-b', help='Set blocking tasks (comma-separated IDs: 1,2,3; overwrites existing)')
@click.option('--add-blocker', 'add_blocker', multiple=True, type=int, help='Add a blocking task ID (incremental)')
@click.option('--remove-blocker', 'remove_blocker', multiple=True, type=int, help='Remove a blocking task ID (incremental)')
@click.option('--incident/--no-incident', default=None, help='Mark/unmark as incident task')
def edit(task_id, text, priority, add_tag, remove_tag, attach, link,
         owner, reviewer, status, due_at, handoff_note, blocked_by, add_blocker, remove_blocker, incident):
    """Edit a task (with team collaboration fields)"""
    task = storage.get_task(task_id)
    if not task:
        console.print(f"[red]✗[/red] Task #{task_id} not found")
        return

    changes = []
    
    # Basic fields
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

    # Attachments
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

    # Links
    if link:
        if not hasattr(task, "links"):
            task.links = []
        task.links.extend(link)
        changes.append(f"links added: {list(link)}")

    # Team collaboration fields
    if owner is not None:
        old_owner = task.owner or "(none)"
        if owner.lower() == 'none':
            task.owner = None
            changes.append(f"owner: {old_owner} → (cleared)")
        else:
            task.owner = owner
            changes.append(f"owner: {old_owner} → {owner}")
    
    if reviewer is not None:
        old_reviewer = task.reviewer or "(none)"
        if reviewer.lower() == 'none':
            task.reviewer = None
            changes.append(f"reviewer: {old_reviewer} → (cleared)")
        else:
            task.reviewer = reviewer
            changes.append(f"reviewer: {old_reviewer} → {reviewer}")
    
    if status is not None:
        old_status = task.status
        task.set_status(status)
        changes.append(f"status: {old_status} → {status}")
    
    if due_at is not None:
        old_due = task.due_at or "(none)"
        if due_at.lower() == 'none':
            task.due_at = None
            changes.append(f"due date: {old_due} → (cleared)")
        else:
            try:
                parsed = parse_due_date(due_at)
                task.due_at = parsed
                changes.append(f"due date: {old_due} → {due_at}")
            except ValueError as e:
                console.print(f"[red]✗[/red] {str(e)}")
                return
    
    if handoff_note is not None:
        old_note = task.handoff_note or "(none)"
        if handoff_note.lower() == 'none':
            task.handoff_note = None
            changes.append(f"handoff note: (cleared)")
        else:
            task.handoff_note = handoff_note
            changes.append(f"handoff note updated")
    
    # Blockers
    # First handle --blocked-by (overwrites existing)
    if blocked_by is not None:
        old_blockers = list(task.blocked_by)
        if blocked_by.lower() == 'none':
            task.blocked_by = []
            if old_blockers:
                changes.append(f"blocked-by: #{', #'.join(map(str, old_blockers))} → (cleared)")
        else:
            try:
                parsed = parse_blocked_by(blocked_by)
                old_blockers_str = ', #'.join(map(str, old_blockers)) if old_blockers else "(none)"
                new_blockers_str = ', #'.join(map(str, parsed)) if parsed else "(none)"
                task.set_blocked_by(parsed)
                changes.append(f"blocked-by: #{old_blockers_str} → #{new_blockers_str}")
            except ValueError as e:
                console.print(f"[red]✗[/red] {str(e)}")
                return
    
    # Then handle incremental --add-blocker and --remove-blocker
    for blocker_id in add_blocker:
        if blocker_id != task.id and blocker_id not in task.blocked_by:
            task.add_blocker(blocker_id)
            changes.append(f"+blocker: #{blocker_id}")
    
    for blocker_id in remove_blocker:
        if blocker_id in task.blocked_by:
            task.remove_blocker(blocker_id)
            changes.append(f"-blocker: #{blocker_id}")
    
    # Incident flag
    if incident is not None:
        old_incident = task.incident
        task.incident = incident
        changes.append(f"incident: {old_incident} → {incident}")

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
@click.option("--owner", "-o", help="Filter by owner (use 'none' for unassigned)")
@click.option("--reviewer", "-r", help="Filter by reviewer (use 'none' for no reviewer)")
@click.option("--status", "-s", type=click.Choice(STATUS_CHOICES), help="Filter by task status")
@click.option("--blocked", "-b", is_flag=True, help="Show only blocked tasks")
@click.option("--incident", "-i", is_flag=True, help="Show only incident tasks")
@click.option("--overdue", is_flag=True, help="Show only overdue tasks")
@click.option("--due-soon", is_flag=True, help="Show only tasks due soon")
@click.option("--no-handoff", is_flag=True, help="Show only tasks needing handoff notes")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed view")
@click.option("--saved", "-S", "saved_name", help="Apply a saved filter by name (uppercase -S)")
def filter_apply(priority: Optional[str], tag: Optional[str], completed: Optional[bool],
                 owner: Optional[str], reviewer: Optional[str], status: Optional[str],
                 blocked: bool, incident: bool, overdue: bool, due_soon: bool, 
                 no_handoff: bool, detailed: bool, saved_name: Optional[str]):
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
        owner = saved.get("owner")
        reviewer = saved.get("reviewer")
        status = saved.get("status")
        blocked = saved.get("blocked", False)
        incident = saved.get("incident", False)
        overdue = saved.get("overdue", False)
        due_soon = saved.get("due_soon", False)
        no_handoff = saved.get("no_handoff", False)

    # Now perform filtering
    tasks = storage.load_tasks() if hasattr(storage, "load_tasks") else []

    # completion filter: None = all, True = completed, False = active
    if completed is not None:
        tasks = [t for t in tasks if t.completed == completed]

    if priority:
        tasks = [t for t in tasks if t.priority == priority]

    if tag:
        tasks = [t for t in tasks if tag in t.tags]
    
    # Team collaboration filters
    if owner is not None:
        if owner.lower() == 'none':
            tasks = [t for t in tasks if not t.has_owner()]
        else:
            tasks = [t for t in tasks if t.owner and t.owner.lower() == owner.lower()]
    
    if reviewer is not None:
        if reviewer.lower() == 'none':
            tasks = [t for t in tasks if not t.has_reviewer()]
        else:
            tasks = [t for t in tasks if t.reviewer and t.reviewer.lower() == reviewer.lower()]
    
    if status:
        tasks = [t for t in tasks if t.status == status]
    
    if blocked:
        tasks = [t for t in tasks if t.is_blocked()]
    
    if incident:
        tasks = [t for t in tasks if t.is_incident_task()]
    
    if overdue:
        tasks = [t for t in tasks if t.is_overdue()]
    
    if due_soon:
        tasks = [t for t in tasks if t.is_due_soon(days=2)]
    
    if no_handoff:
        tasks = [t for t in tasks if t.needs_handoff()]

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
    if owner:
        filters_desc.append(f"owner={owner}")
    if reviewer:
        filters_desc.append(f"reviewer={reviewer}")
    if status:
        filters_desc.append(f"status={status}")
    if blocked:
        filters_desc.append("blocked")
    if incident:
        filters_desc.append("incident")
    if overdue:
        filters_desc.append("overdue")
    if due_soon:
        filters_desc.append("due-soon")
    if no_handoff:
        filters_desc.append("needs-handoff")
    
    filter_desc = " AND ".join(filters_desc) if filters_desc else "all"
    console.print(f"[bold]{len(tasks)} task(s) matching [{filter_desc}]:[/bold]\n")

    # Build table based on detailed mode
    if detailed:
        table = Table()
        table.add_column("ID", style="cyan", width=4)
        table.add_column("✔", width=3)
        table.add_column("Pri", width=4)
        table.add_column("Status", width=12)
        table.add_column("Owner", width=10)
        table.add_column("Due", width=16)
        table.add_column("Task")
        table.add_column("Tags", style="dim")

        for task in sorted(tasks, key=lambda t: (t.completed, t.id)):
            check_status = "✔" if task.completed else "○"
            priority_color = {"high": "red", "medium": "yellow", "low": "green"}.get(task.priority, "yellow")
            tags_str = ", ".join(task.tags) if task.tags else ""
            status_color = task.get_status_color()
            status_display = task.status.replace('_', '-')
            
            # Icons for special tasks
            icons = []
            if task.incident:
                icons.append("🔴")
            if task.is_blocked():
                icons.append("🚫")
            if task.is_overdue():
                icons.append("⏰")
            if task.needs_handoff():
                icons.append("📋")
            icon_str = " " + " ".join(icons) if icons else ""
            
            table.add_row(
                str(task.id),
                check_status,
                f"[{priority_color}]{task.priority[:3]}[/{priority_color}]",
                f"[{status_color}]{status_display}[/{status_color}]",
                task.owner or "-",
                task.get_due_date_display(),
                f"{task.text}{icon_str}",
                tags_str,
            )
    else:
        table = Table()
        table.add_column("ID", style="cyan", width=4)
        table.add_column("✔", width=3)
        table.add_column("Priority", width=8)
        table.add_column("Task")
        table.add_column("Tags", style="dim")

        for task in sorted(tasks, key=lambda t: (t.completed, t.id)):
            check_status = "✔" if task.completed else "○"
            priority_color = {"high": "red", "medium": "yellow", "low": "green"}.get(task.priority, "yellow")
            tags_str = ", ".join(task.tags) if task.tags else ""
            
            # Icons for special tasks
            icons = []
            if task.incident:
                icons.append("🔴")
            if task.is_blocked():
                icons.append("🚫")
            if task.is_overdue():
                icons.append("⏰")
            if task.needs_handoff():
                icons.append("📋")
            icon_str = " " + " ".join(icons) if icons else ""
            
            table.add_row(
                str(task.id),
                check_status,
                f"[{priority_color}]{task.priority}[/{priority_color}]",
                f"{task.text}{icon_str}",
                tags_str,
            )

    console.print(table)


@filter.command("save")
@click.argument("name")
@click.option("--priority", "-p", type=click.Choice(["low", "medium", "high"]), help="Filter by priority")
@click.option("--tag", "-t", help="Filter by tag")
@click.option("--completed/--active", "-c/-a", default=None, help="Filter by completion status")
@click.option("--owner", "-o", help="Filter by owner (use 'none' for unassigned)")
@click.option("--reviewer", "-r", help="Filter by reviewer (use 'none' for no reviewer)")
@click.option("--status", "-s", type=click.Choice(STATUS_CHOICES), help="Filter by task status")
@click.option("--blocked", "-b", is_flag=True, help="Filter by blocked")
@click.option("--incident", "-i", is_flag=True, help="Filter by incident")
@click.option("--overdue", is_flag=True, help="Filter by overdue")
@click.option("--due-soon", is_flag=True, help="Filter by due-soon")
@click.option("--no-handoff", is_flag=True, help="Filter by no-handoff")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing saved filter of same name")
def filter_save(name: str, priority: Optional[str], tag: Optional[str], completed: Optional[bool],
                owner: Optional[str], reviewer: Optional[str], status: Optional[str],
                blocked: bool, incident: bool, overdue: bool, due_soon: bool, 
                no_handoff: bool, force: bool):
    """
    Save a filter under <name>. Later you can apply it with `tix filter apply --saved <name>`.
    Example: tix filter save oncall -o alice --incident
    """
    filters = _load_saved_filters()
    if name in filters and not force:
        console.print(f"[red]✗[/red] A saved filter named '{name}' already exists. Use --force to overwrite.")
        return

    storage_obj = {
        "priority": priority,
        "tag": tag,
        "owner": owner,
        "reviewer": reviewer,
        "status": status,
        "blocked": blocked if blocked else None,
        "incident": incident if incident else None,
        "overdue": overdue if overdue else None,
        "due_soon": due_soon if due_soon else None,
        "no_handoff": no_handoff if no_handoff else None,
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
        if "owner" in storage_obj:
            parts.append(f"-o {storage_obj['owner']}")
        if "reviewer" in storage_obj:
            parts.append(f"-r {storage_obj['reviewer']}")
        if "status" in storage_obj:
            parts.append(f"-s {storage_obj['status']}")
        if storage_obj.get("blocked"):
            parts.append("-b")
        if storage_obj.get("incident"):
            parts.append("-i")
        if storage_obj.get("overdue"):
            parts.append("--overdue")
        if storage_obj.get("due_soon"):
            parts.append("--due-soon")
        if storage_obj.get("no_handoff"):
            parts.append("--no-handoff")
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
        if "owner" in obj:
            parts.append(f"owner={obj['owner']}")
        if "reviewer" in obj:
            parts.append(f"reviewer={obj['reviewer']}")
        if "status" in obj:
            parts.append(f"status={obj['status']}")
        if obj.get("blocked"):
            parts.append("blocked")
        if obj.get("incident"):
            parts.append("incident")
        if obj.get("overdue"):
            parts.append("overdue")
        if obj.get("due_soon"):
            parts.append("due-soon")
        if obj.get("no_handoff"):
            parts.append("needs-handoff")
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

@cli.command()
@click.argument('task_id', type=int)
def start(task_id):
    """Start time tracking for a task"""
    task = storage.get_task(task_id)
    if not task:
        console.print(f"[red]✗[/red] Task #{task_id} not found")
        return
    
    if task.completed:
        console.print(f"[yellow]![/yellow] Cannot start timer on completed task")
        return
    
    for t in storage.load_tasks():
        if t.is_timer_running() and t.id != task_id:
            console.print(f"[yellow]![/yellow] Task #{t.id} timer is already running")
            console.print(f"[dim]Stop it first with: tix stop {t.id}[/dim]")
            return
    
    if task.is_timer_running():
        duration = task.get_current_session_duration()
        console.print(f"[yellow]![/yellow] Timer already running for {task.format_time(duration)}")
        return
    
    try:
        task.start_timer()
        storage.update_task(task)
        console.print(f"[green]⏱[/green] Started timer for task #{task_id}: {task.text}")
        if task.estimate:
            console.print(f"[dim]  Estimated: {task.format_time(task.estimate)}[/dim]")
    except ValueError as e:
        console.print(f"[red]✗[/red] {str(e)}")


@cli.command()
@click.argument('task_id', type=int)
def stop(task_id):
    """Stop time tracking for a task"""
    task = storage.get_task(task_id)
    if not task:
        console.print(f"[red]✗[/red] Task #{task_id} not found")
        return
    
    if not task.is_timer_running():
        console.print(f"[yellow]![/yellow] No timer running for task #{task_id}")
        return
    
    try:
        duration = task.stop_timer()
        storage.update_task(task)
        
        console.print(f"[green]⏹[/green] Stopped timer for task #{task_id}")
        console.print(f"[cyan]  Session duration: {task.format_time(duration)}[/cyan]")
        console.print(f"[dim]  Total time spent: {task.format_time(task.time_spent)}[/dim]")
        
        if task.estimate:
            remaining = task.get_time_remaining()
            if remaining > 0:
                console.print(f"[dim]  Remaining: {task.format_time(remaining)}[/dim]")
            elif remaining < 0:
                console.print(f"[yellow]  Over estimate by: {task.format_time(abs(remaining))}[/yellow]")
            else:
                console.print("[green]  Completed within estimate![/green]")
    except ValueError as e:
        console.print(f"[red]✗[/red] {str(e)}")


@cli.command()
@click.argument('task_id', type=int, required=False)
def status(task_id):
    """Show timer status for a task or all tasks"""
    if task_id:
        task = storage.get_task(task_id)
        if not task:
            console.print(f"[red]✗[/red] Task #{task_id} not found")
            return
        
        if task.is_timer_running():
            duration = task.get_current_session_duration()
            console.print(f"[green]⏱[/green] Timer running for task #{task_id}: {task.text}")
            console.print(f"[cyan]  Current session: {task.format_time(duration)}[/cyan]")
            console.print(f"[dim]  Total time: {task.format_time(task.time_spent + duration)}[/dim]")
        else:
            console.print(f"[dim]No timer running for task #{task_id}[/dim]")
            if task.time_spent > 0:
                console.print(f"[dim]Total time spent: {task.format_time(task.time_spent)}[/dim]")
    else:
        tasks = storage.load_tasks()
        running_tasks = [t for t in tasks if t.is_timer_running()]
        
        if running_tasks:
            for task in running_tasks:
                duration = task.get_current_session_duration()
                console.print(f"[green]⏱[/green] Task #{task.id}: {task.text}")
                console.print(f"[cyan]  Running for: {task.format_time(duration)}[/cyan]")
        else:
            console.print("[dim]No active timers[/dim]")


@cli.command()
@click.option('--period', '-p', type=click.Choice(['week', 'month', 'all']), 
              default='week', help='Time period for report')
def timereport(period):
    """Generate time tracking report"""
    from datetime import timedelta
    
    tasks = storage.load_tasks()
    now = datetime.now()
    
    if period == 'week':
        start_date = now - timedelta(days=7)
        title = "Weekly Time Report"
    elif period == 'month':
        start_date = now - timedelta(days=30)
        title = "Monthly Time Report"
    else:
        start_date = None
        title = "All Time Report"
    
    relevant_tasks = []
    for task in tasks:
        if task.time_spent > 0:
            if start_date:
                task_logs = [log for log in task.time_logs 
                           if datetime.fromisoformat(log['ended_at']) >= start_date]
                if task_logs:
                    relevant_tasks.append((task, sum(log['duration'] for log in task_logs)))
            else:
                relevant_tasks.append((task, task.time_spent))
    
    if not relevant_tasks:
        console.print(f"[dim]No time tracked in the {period}[/dim]")
        return
    
    console.print(f"\n[bold cyan]{title}[/bold cyan]\n")
    
    table = Table()
    table.add_column("ID", style="cyan", width=4)
    table.add_column("Task")
    table.add_column("Estimated", style="dim", width=10)
    table.add_column("Spent", style="yellow", width=10)
    table.add_column("Remaining", width=10)
    table.add_column("Status", width=8)
    
    total_estimated = 0
    total_spent = 0
    
    for task, time_in_period in relevant_tasks:
        estimate_str = task.format_time(task.estimate) if task.estimate else "-"
        spent_str = task.format_time(time_in_period)
        
        if task.estimate:
            total_estimated += task.estimate
            remaining = task.get_time_remaining()
            if remaining > 0:
                remaining_str = task.format_time(remaining)
                status = "✓" if task.completed else "→"
                status_color = "green" if task.completed else "blue"
            elif remaining < 0:
                remaining_str = f"+{task.format_time(abs(remaining))}"
                status = "⚠"
                status_color = "yellow"
            else:
                remaining_str = "0m"
                status = "✓"
                status_color = "green"
        else:
            remaining_str = "-"
            status = "✓" if task.completed else "→"
            status_color = "green" if task.completed else "blue"
        
        total_spent += time_in_period
        
        table.add_row(
            str(task.id),
            task.text[:40] + "..." if len(task.text) > 40 else task.text,
            estimate_str,
            spent_str,
            remaining_str,
            f"[{status_color}]{status}[/{status_color}]"
        )
    
    console.print(table)
    
    console.print(f"\n[bold]Summary:[/bold]")
    if total_estimated > 0:
        console.print(f"  Total estimated: {format_time_helper(total_estimated)}")
    console.print(f"  Total spent: {format_time_helper(total_spent)}")
    if total_estimated > 0:
        efficiency = (total_estimated / max(total_spent, 1)) * 100
        console.print(f"  Efficiency: {efficiency:.1f}%")


def _format_task_for_list(task: Task, show_owner: bool = True) -> str:
    """Format a task for display in handoff view"""
    icons = []
    if task.incident:
        icons.append("🔴")
    if task.is_blocked():
        icons.append("🚫")
    if task.is_overdue():
        icons.append("⏰")
    icon_str = " " + " ".join(icons) if icons else ""
    
    owner_str = f" [owner: {task.owner}]" if show_owner and task.owner else ""
    return f"#{task.id}: {task.text}{icon_str}{owner_str}"


@cli.command()
@click.option("--format", "-f", type=click.Choice(['console', 'markdown']), default='console', help='Output format')
@click.option("--output", "-o", type=click.Path(), help='Output to file (for markdown format)')
def handoff(format, output):
    """Handoff view - show tasks needing attention for shift交接
    
    Shows:
    - Tasks due today that must be handed off
    - Unassigned high-priority tasks
    - Blocked tasks without handoff notes
    - Cross-person tasks missing reviewers
    - Overdue incomplete tasks
    """
    from datetime import datetime, timedelta
    from collections import defaultdict
    
    tasks = storage.load_tasks()
    today = datetime.now().date()
    
    # Category 1: Tasks due today that need handoff (active, due today, with owner)
    due_today = []
    # Category 2: Unassigned high priority tasks
    unassigned_high = []
    # Category 3: Blocked tasks without handoff notes
    blocked_no_note = []
    # Category 4: Tasks needing review (status=review but no reviewer)
    needs_reviewer = []
    # Category 5: Overdue incomplete tasks
    overdue_incomplete = []
    
    for task in tasks:
        if task.completed:
            continue
        
        # Category 1: Due today with owner
        if task.due_at:
            try:
                due_date = datetime.fromisoformat(task.due_at).date()
                if due_date == today and task.owner:
                    due_today.append(task)
            except (ValueError, TypeError):
                pass
        
        # Category 2: Unassigned high priority
        if not task.has_owner() and task.priority == 'high':
            unassigned_high.append(task)
        
        # Category 3: Blocked without handoff note
        if task.is_blocked() and not task.handoff_note:
            blocked_no_note.append(task)
        
        # Category 4: In review status but no reviewer
        if task.status == 'review' and not task.has_reviewer():
            needs_reviewer.append(task)
        
        # Category 5: Overdue and incomplete
        if task.is_overdue():
            overdue_incomplete.append(task)
    
    # Generate output based on format
    if format == 'markdown':
        lines = ["# 📋 Handoff Report", "", f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]
        
        # Due today
        if due_today:
            lines.append("## 🔴 Tasks Due Today (Need Handoff)")
            lines.append("")
            for task in due_today:
                lines.append(f"- [ ] **#{task.id}** {task.text}")
                if task.owner:
                    lines.append(f"  - Owner: {task.owner}")
                if task.handoff_note:
                    lines.append(f"  - Handoff Note: {task.handoff_note}")
                lines.append("")
        else:
            lines.append("## ✅ Tasks Due Today")
            lines.append("")
            lines.append("No tasks due today.")
            lines.append("")
        
        # Unassigned high priority
        if unassigned_high:
            lines.append("## ⚠️ Unassigned High-Priority Tasks")
            lines.append("")
            for task in unassigned_high:
                lines.append(f"- [ ] **#{task.id}** {task.text}")
                if task.due_at:
                    lines.append(f"  - Due: {task.get_due_date_display()}")
                lines.append("")
        else:
            lines.append("## ✅ Unassigned High-Priority Tasks")
            lines.append("")
            lines.append("All high-priority tasks are assigned.")
            lines.append("")
        
        # Blocked without note
        if blocked_no_note:
            lines.append("## 🚫 Blocked Tasks Without Handoff Notes")
            lines.append("")
            for task in blocked_no_note:
                lines.append(f"- [ ] **#{task.id}** {task.text}")
                if task.owner:
                    lines.append(f"  - Owner: {task.owner}")
                lines.append(f"  - Blocked by: #{', #'.join(map(str, task.blocked_by))}")
                lines.append("")
        else:
            lines.append("## ✅ Blocked Tasks")
            lines.append("")
            lines.append("All blocked tasks have handoff notes.")
            lines.append("")
        
        # Needs reviewer
        if needs_reviewer:
            lines.append("## 👀 Tasks Needing Reviewer")
            lines.append("")
            for task in needs_reviewer:
                lines.append(f"- [ ] **#{task.id}** {task.text}")
                if task.owner:
                    lines.append(f"  - Owner: {task.owner}")
                lines.append("")
        else:
            lines.append("## ✅ Tasks Needing Reviewer")
            lines.append("")
            lines.append("All tasks in review have assigned reviewers.")
            lines.append("")
        
        # Overdue
        if overdue_incomplete:
            lines.append("## ⏰ Overdue Incomplete Tasks")
            lines.append("")
            for task in overdue_incomplete:
                lines.append(f"- [ ] **#{task.id}** {task.text}")
                if task.owner:
                    lines.append(f"  - Owner: {task.owner}")
                lines.append(f"  - Due: {task.get_due_date_display()}")
                lines.append("")
        else:
            lines.append("## ✅ Overdue Tasks")
            lines.append("")
            lines.append("No overdue incomplete tasks.")
            lines.append("")
        
        # Summary
        lines.append("## 📊 Summary")
        lines.append("")
        lines.append(f"- Tasks due today: {len(due_today)}")
        lines.append(f"- Unassigned high-priority: {len(unassigned_high)}")
        lines.append(f"- Blocked without notes: {len(blocked_no_note)}")
        lines.append(f"- Needs reviewer: {len(needs_reviewer)}")
        lines.append(f"- Overdue incomplete: {len(overdue_incomplete)}")
        lines.append("")
        
        report_text = "\n".join(lines)
        
        if output:
            Path(output).write_text(report_text, encoding='utf-8')
            console.print(f"[green]✔[/green] Handoff report saved to {output}")
        else:
            console.print(Markdown(report_text))
    
    else:
        # Console format
        from rich.panel import Panel
        
        total_issues = len(due_today) + len(unassigned_high) + len(blocked_no_note) + len(needs_reviewer) + len(overdue_incomplete)
        
        console.print("")
        console.print(Panel(
            f"[bold cyan]📋 Handoff View[/bold cyan]\n\n"
            f"[dim]Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}[/dim]\n"
            f"[yellow]⚠ Items needing attention: {total_issues}[/yellow]",
            expand=False,
            border_style="cyan"
        ))
        
        # Due today
        console.print("")
        if due_today:
            console.print("[bold red]🔴 Tasks Due Today (Need Handoff):[/bold red]")
            for task in due_today:
                console.print(f"  {_format_task_for_list(task)}")
                if task.handoff_note:
                    console.print(f"    [dim]📋 Handoff: {task.handoff_note}[/dim]")
        else:
            console.print("[bold green]✅ Tasks Due Today:[/bold green] [dim]None[/dim]")
        
        # Unassigned high priority
        console.print("")
        if unassigned_high:
            console.print("[bold yellow]⚠️ Unassigned High-Priority Tasks:[/bold yellow]")
            for task in unassigned_high:
                console.print(f"  {_format_task_for_list(task, show_owner=False)}")
        else:
            console.print("[bold green]✅ Unassigned High-Priority:[/bold green] [dim]All assigned[/dim]")
        
        # Blocked without note
        console.print("")
        if blocked_no_note:
            console.print("[bold red]🚫 Blocked Tasks Without Handoff Notes:[/bold red]")
            for task in blocked_no_note:
                console.print(f"  {_format_task_for_list(task)}")
                console.print(f"    [dim]Blocked by: #{', #'.join(map(str, task.blocked_by))}[/dim]")
        else:
            console.print("[bold green]✅ Blocked Tasks:[/bold green] [dim]All have handoff notes[/dim]")
        
        # Needs reviewer
        console.print("")
        if needs_reviewer:
            console.print("[bold yellow]👀 Tasks Needing Reviewer:[/bold yellow]")
            for task in needs_reviewer:
                console.print(f"  {_format_task_for_list(task)}")
        else:
            console.print("[bold green]✅ Tasks Needing Reviewer:[/bold green] [dim]All have reviewers[/dim]")
        
        # Overdue
        console.print("")
        if overdue_incomplete:
            console.print("[bold red]⏰ Overdue Incomplete Tasks:[/bold red]")
            for task in overdue_incomplete:
                console.print(f"  {_format_task_for_list(task)}")
                console.print(f"    [dim]Due: {task.get_due_date_display()}[/dim]")
        else:
            console.print("[bold green]✅ Overdue Tasks:[/bold green] [dim]None[/dim]")
        
        # Summary
        console.print("")
        console.print("[bold]📊 Summary:[/bold]")
        console.print(f"  • Tasks due today: {len(due_today)}")
        console.print(f"  • Unassigned high-priority: {len(unassigned_high)}")
        console.print(f"  • Blocked without notes: {len(blocked_no_note)}")
        console.print(f"  • Needs reviewer: {len(needs_reviewer)}")
        console.print(f"  • Overdue incomplete: {len(overdue_incomplete)}")


@cli.command("daily")
@click.option("--format", "-f", type=click.Choice(['console', 'markdown']), default='console', help='Output format')
@click.option("--output", "-o", type=click.Path(), help='Output to file (for markdown format)')
@click.option("--owner", help='Filter by specific owner')
def daily_report(format, output, owner):
    """Daily report - summary of tasks by owner
    
    Shows for each owner:
    - New tasks added today
    - Tasks completed today
    - Overdue tasks
    - Tasks needing handoff
    - Incident tasks
    """
    from datetime import datetime, timedelta
    from collections import defaultdict
    
    tasks = storage.load_tasks()
    today = datetime.now().date()
    
    # Group tasks by owner
    tasks_by_owner = defaultdict(list)
    unassigned = []
    
    for task in tasks:
        if task.owner:
            tasks_by_owner[task.owner].append(task)
        else:
            unassigned.append(task)
    
    # If filtering by specific owner
    if owner:
        if owner.lower() == 'none':
            tasks_by_owner = {'(unassigned)': unassigned}
        else:
            filtered = {k: v for k, v in tasks_by_owner.items() if k.lower() == owner.lower()}
            if not filtered:
                console.print(f"[yellow]No tasks found for owner: {owner}[/yellow]")
                return
            tasks_by_owner = filtered
    
    # Calculate statistics for each owner
    owner_stats = {}
    
    for owner_name, owner_tasks in tasks_by_owner.items():
        stats = {
            'total': len(owner_tasks),
            'active': len([t for t in owner_tasks if not t.completed]),
            'completed': len([t for t in owner_tasks if t.completed]),
            'added_today': [],
            'completed_today': [],
            'overdue': [],
            'needs_handoff': [],
            'incidents': [],
        }
        
        for task in owner_tasks:
            # Added today
            try:
                created_date = datetime.fromisoformat(task.created_at).date()
                if created_date == today:
                    stats['added_today'].append(task)
            except (ValueError, TypeError):
                pass
            
            # Completed today
            if task.completed and task.completed_at:
                try:
                    completed_date = datetime.fromisoformat(task.completed_at).date()
                    if completed_date == today:
                        stats['completed_today'].append(task)
                except (ValueError, TypeError):
                    pass
            
            # Overdue
            if task.is_overdue():
                stats['overdue'].append(task)
            
            # Needs handoff
            if task.needs_handoff():
                stats['needs_handoff'].append(task)
            
            # Incident
            if task.is_incident_task() and not task.completed:
                stats['incidents'].append(task)
        
        owner_stats[owner_name] = stats
    
    # Add unassigned stats if not filtered
    if not owner and unassigned:
        unassigned_stats = {
            'total': len(unassigned),
            'active': len([t for t in unassigned if not t.completed]),
            'completed': len([t for t in unassigned if t.completed]),
            'added_today': [],
            'completed_today': [],
            'overdue': [],
            'needs_handoff': [],
            'incidents': [],
        }
        
        for task in unassigned:
            try:
                created_date = datetime.fromisoformat(task.created_at).date()
                if created_date == today:
                    unassigned_stats['added_today'].append(task)
            except (ValueError, TypeError):
                pass
            
            if task.is_overdue():
                unassigned_stats['overdue'].append(task)
            
            if task.needs_handoff():
                unassigned_stats['needs_handoff'].append(task)
            
            if task.is_incident_task() and not task.completed:
                unassigned_stats['incidents'].append(task)
        
        owner_stats['(unassigned)'] = unassigned_stats
    
    # Generate output
    if format == 'markdown':
        lines = ["# 📊 Daily Task Report", "", f"**Date:** {today.strftime('%Y-%m-%d')}", ""]
        
        # Overall summary
        total_active = sum(s['active'] for s in owner_stats.values())
        total_completed = sum(s['completed'] for s in owner_stats.values())
        total_added = sum(len(s['added_today']) for s in owner_stats.values())
        total_completed_today = sum(len(s['completed_today']) for s in owner_stats.values())
        total_overdue = sum(len(s['overdue']) for s in owner_stats.values())
        total_incidents = sum(len(s['incidents']) for s in owner_stats.values())
        
        lines.append("## 📈 Overall Summary")
        lines.append("")
        lines.append(f"- **Total Active Tasks:** {total_active}")
        lines.append(f"- **Total Completed:** {total_completed}")
        lines.append(f"- **Added Today:** {total_added}")
        lines.append(f"- **Completed Today:** {total_completed_today}")
        lines.append(f"- **Overdue:** {total_overdue}")
        lines.append(f"- **Active Incidents:** {total_incidents}")
        lines.append("")
        
        # By owner
        lines.append("## 👥 By Owner")
        lines.append("")
        
        for owner_name, stats in sorted(owner_stats.items()):
            lines.append(f"### {owner_name}")
            lines.append("")
            lines.append(f"- **Active:** {stats['active']} | **Completed:** {stats['completed']}")
            lines.append(f"- **Added Today:** {len(stats['added_today'])}")
            lines.append(f"- **Completed Today:** {len(stats['completed_today'])}")
            lines.append(f"- **Overdue:** {len(stats['overdue'])}")
            lines.append(f"- **Needs Handoff:** {len(stats['needs_handoff'])}")
            lines.append(f"- **Active Incidents:** {len(stats['incidents'])}")
            lines.append("")
            
            # Added today
            if stats['added_today']:
                lines.append("**Added Today:**")
                for task in stats['added_today']:
                    lines.append(f"- [ ] #{task.id} {task.text}")
                lines.append("")
            
            # Completed today
            if stats['completed_today']:
                lines.append("**Completed Today:**")
                for task in stats['completed_today']:
                    lines.append(f"- [x] #{task.id} {task.text}")
                lines.append("")
            
            # Overdue
            if stats['overdue']:
                lines.append("**Overdue:**")
                for task in stats['overdue']:
                    lines.append(f"- [ ] #{task.id} {task.text} (Due: {task.get_due_date_display()})")
                lines.append("")
            
            # Incidents
            if stats['incidents']:
                lines.append("**Active Incidents:**")
                for task in stats['incidents']:
                    lines.append(f"- [ ] 🔴 #{task.id} {task.text}")
                lines.append("")
        
        report_text = "\n".join(lines)
        
        if output:
            Path(output).write_text(report_text, encoding='utf-8')
            console.print(f"[green]✔[/green] Daily report saved to {output}")
        else:
            console.print(Markdown(report_text))
    
    else:
        # Console format
        from rich.panel import Panel
        
        total_active = sum(s['active'] for s in owner_stats.values())
        total_completed = sum(s['completed'] for s in owner_stats.values())
        total_added = sum(len(s['added_today']) for s in owner_stats.values())
        total_completed_today = sum(len(s['completed_today']) for s in owner_stats.values())
        total_overdue = sum(len(s['overdue']) for s in owner_stats.values())
        total_incidents = sum(len(s['incidents']) for s in owner_stats.values())
        
        console.print("")
        console.print(Panel(
            f"[bold cyan]📊 Daily Task Report[/bold cyan]\n\n"
            f"[dim]Date: {today.strftime('%Y-%m-%d')}[/dim]\n\n"
            f"[green]Completed Today: {total_completed_today}[/green] | "
            f"[cyan]Added Today: {total_added}[/cyan] | "
            f"[yellow]Overdue: {total_overdue}[/yellow] | "
            f"[red]Incidents: {total_incidents}[/red]",
            expand=False,
            border_style="cyan"
        ))
        
        # By owner
        for owner_name, stats in sorted(owner_stats.items()):
            console.print("")
            console.print(f"[bold]👤 {owner_name}[/bold]")
            console.print(f"  Active: {stats['active']} | Completed: {stats['completed']}")
            
            if stats['added_today']:
                console.print(f"  [cyan]📥 Added Today ({len(stats['added_today'])}):[/cyan]")
                for task in stats['added_today']:
                    console.print(f"    • #{task.id}: {task.text}")
            
            if stats['completed_today']:
                console.print(f"  [green]✅ Completed Today ({len(stats['completed_today'])}):[/green]")
                for task in stats['completed_today']:
                    console.print(f"    • #{task.id}: {task.text}")
            
            if stats['overdue']:
                console.print(f"  [red]⏰ Overdue ({len(stats['overdue'])}):[/red]")
                for task in stats['overdue']:
                    console.print(f"    • #{task.id}: {task.text}")
            
            if stats['needs_handoff']:
                console.print(f"  [yellow]📋 Needs Handoff ({len(stats['needs_handoff'])}):[/yellow]")
                for task in stats['needs_handoff']:
                    console.print(f"    • #{task.id}: {task.text}")
            
            if stats['incidents']:
                console.print(f"  [red]🔴 Active Incidents ({len(stats['incidents'])}):[/red]")
                for task in stats['incidents']:
                    console.print(f"    • #{task.id}: {task.text}")


if __name__ == '__main__':
    cli()