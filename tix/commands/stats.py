from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn
from datetime import datetime, timedelta
from collections import Counter

console = Console()


def show_stats(storage):
    """Display comprehensive task statistics including time tracking"""
    tasks = storage.load_tasks()

    if not tasks:
        console.print("[dim]No tasks to analyze. Add some tasks first![/dim]")
        return

    active = [t for t in tasks if not t.completed]
    completed = [t for t in tasks if t.completed]

    # Priority breakdown
    priority_counts = Counter(t.priority for t in active)

    # Tags analysis
    all_tags = []
    for task in tasks:
        all_tags.extend(task.tags)
    tag_counts = Counter(all_tags)

    # Time tracking stats
    tasks_with_estimates = [t for t in tasks if t.estimate]
    tasks_with_time = [t for t in tasks if t.time_spent > 0]
    total_estimated = sum(t.estimate for t in tasks_with_estimates)
    total_spent = sum(t.time_spent for t in tasks_with_time)
    
    running_timers = [t for t in tasks if t.is_timer_running()]

    # Time analysis
    today = datetime.now().date()
    today_completed = len([
        t for t in completed
        if t.completed_at and
           datetime.fromisoformat(t.completed_at).date() == today
    ])

    # Create stats panel
    stats_text = f"""[bold cyan]📊 Task Statistics[/bold cyan]

[bold]Overview:[/bold]
  • Total tasks: {len(tasks)}
  • Active: {len(active)} ({len(active) / max(len(tasks), 1) * 100:.0f}%)
  • Completed: {len(completed)} ({len(completed) / max(len(tasks), 1) * 100:.0f}%)

[bold]Priority Distribution (Active):[/bold]
  • 🔴 High: {priority_counts.get('high', 0)}
  • 🟡 Medium: {priority_counts.get('medium', 0)}
  • 🟢 Low: {priority_counts.get('low', 0)}

[bold]Time Tracking:[/bold]
  • Tasks with estimates: {len(tasks_with_estimates)}
  • Tasks with tracked time: {len(tasks_with_time)}"""

    if total_estimated > 0:
        stats_text += f"\n  • Total estimated: {format_time(total_estimated)}"
    if total_spent > 0:
        stats_text += f"\n  • Total time spent: {format_time(total_spent)}"
    if running_timers:
        stats_text += f"\n  • [green]Active timers: {len(running_timers)}[/green]"

    stats_text += f"""

[bold]Today's Progress:[/bold]
  • Completed today: {today_completed} task(s)

[bold]Top Tags:[/bold]"""

    if tag_counts:
        for tag, count in tag_counts.most_common(3):
            stats_text += f"\n  • {tag}: {count} task(s)"
    else:
        stats_text += "\n  • No tags used yet"

    panel = Panel(stats_text, expand=False, border_style="cyan")
    console.print(panel)

    # Progress bar
    if tasks:
        console.print("\n[bold]Completion Progress:[/bold]")
        with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        ) as progress:
            progress.add_task(
                "Overall",
                total=len(tasks),
                completed=len(completed)
            )
    
    # Show active timers
    if running_timers:
        console.print("\n[bold]Active Timers:[/bold]")
        for task in running_timers:
            duration = task.get_current_session_duration()
            console.print(f"  • Task #{task.id}: {task.text} - [cyan]{format_time(duration)}[/cyan]")


def format_time(minutes: int) -> str:
    """Format minutes into human readable format"""
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    mins = minutes % 60
    if mins == 0:
        return f"{hours}h"
    return f"{hours}h {mins}m"