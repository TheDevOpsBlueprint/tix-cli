import click
from rich.console import Console
from rich.table import Table
from pathlib import Path
from tix.storage.context_storage import ContextStorage
from tix.storage.json_storage import TaskStorage

console = Console()
context_storage = ContextStorage()


@click.group()
def context():
    """Manage contexts/workspaces for organizing tasks"""
    pass


@context.command(name='create')
@click.argument('name')
@click.option('--description', '-d', help='Description for the context')
def create_context(name, description):
    """Create a new context"""
    # Validate context name
    if not name.replace('_', '').replace('-', '').isalnum():
        console.print("[red]✗[/red] Context name can only contain letters, numbers, hyphens, and underscores")
        return
    
    try:
        new_context = context_storage.add_context(name, description)
        console.print(f"[green]✔[/green] Created context: [cyan]{name}[/cyan]")
        if description:
            console.print(f"[dim]  {description}[/dim]")
        console.print(f"\n[dim]Switch to this context with: tix context switch {name}[/dim]")
    except ValueError as e:
        console.print(f"[red]✗[/red] {str(e)}")


@context.command(name='switch')
@click.argument('name')
def switch_context(name):
    """Switch to a different context"""
    try:
        current = context_storage.get_active_context()
        if current == name:
            console.print(f"[yellow]![/yellow] Already in context: [cyan]{name}[/cyan]")
            return
        
        context_storage.set_active_context(name)
        console.print(f"[green]✔[/green] Switched to context: [cyan]{name}[/cyan]")
        
        # Show task count in new context
        try:
            storage = TaskStorage(context=name)
            tasks = storage.load_tasks()
            active = [t for t in tasks if not t.completed]
            global_count = len([t for t in tasks if t.is_global])
            local_count = len(tasks) - global_count
            
            console.print(f"[dim]  {len(active)} active task(s) ({local_count} local, {global_count} global)[/dim]")
        except:
            pass
    except ValueError as e:
        console.print(f"[red]✗[/red] {str(e)}")


@context.command(name='list')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed information')
def list_contexts(verbose):
    """List all contexts with task counts"""
    contexts = context_storage.load_contexts()
    active_context = context_storage.get_active_context()
    
    if not contexts:
        console.print("[dim]No contexts found[/dim]")
        return
    
    table = Table(title="Contexts")
    table.add_column("", width=2)
    table.add_column("Name", style="cyan")
    table.add_column("Tasks", justify="right")
    table.add_column("Active", justify="right")
    table.add_column("Completed", justify="right")
    if verbose:
        table.add_column("Created", style="dim")
        table.add_column("Description", style="dim")
    
    for ctx in sorted(contexts, key=lambda c: c.name):
        # Get task counts for this context
        try:
            storage = TaskStorage(context=ctx.name)
            all_tasks = storage._read_data()["tasks"]  # Get raw tasks without global merging
            tasks = [t for t in all_tasks]
            active = len([t for t in tasks if not t.get('completed', False)])
            completed = len([t for t in tasks if t.get('completed', False)])
            total = len(tasks)
        except:
            total = active = completed = 0
        
        # Mark active context
        marker = "→" if ctx.name == active_context else ""
        
        row = [
            marker,
            ctx.name,
            str(total),
            str(active),
            str(completed)
        ]
        
        if verbose:
            from datetime import datetime
            created = datetime.fromisoformat(ctx.created_at).strftime("%Y-%m-%d")
            row.append(created)
            row.append(ctx.description or "")
        
        table.add_row(*row)
    
    console.print(table)
    console.print(f"\n[dim]Active context: [cyan]{active_context}[/cyan][/dim]")
    console.print(f"[dim]Switch contexts with: tix context switch <name>[/dim]")


@context.command(name='delete')
@click.argument('name')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation')
def delete_context(name, force):
    """Delete a context and all its tasks"""
    if name == "default":
        console.print("[red]✗[/red] Cannot delete the default context")
        return
    
    ctx = context_storage.get_context(name)
    if not ctx:
        console.print(f"[red]✗[/red] Context '{name}' not found")
        return
    
    # Get task count
    try:
        storage = TaskStorage(context=name)
        task_count = len(storage._read_data()["tasks"])
    except:
        task_count = 0
    
    if not force:
        console.print(f"[yellow]⚠ About to delete context '[cyan]{name}[/cyan]' with {task_count} task(s)[/yellow]")
        if not click.confirm("Are you sure?"):
            console.print("[dim]Cancelled[/dim]")
            return
    
    try:
        context_storage.delete_context(name)
        
        # Delete the context's task file
        context_file = Path.home() / ".tix" / "contexts" / f"{name}.json"
        if context_file.exists():
            context_file.unlink()
        
        console.print(f"[green]✔[/green] Deleted context: [cyan]{name}[/cyan]")
        
        # Show active context if it changed
        active = context_storage.get_active_context()
        if active != name:
            console.print(f"[dim]Active context: [cyan]{active}[/cyan][/dim]")
    except ValueError as e:
        console.print(f"[red]✗[/red] {str(e)}")


@context.command(name='rename')
@click.argument('old_name')
@click.argument('new_name')
def rename_context(old_name, new_name):
    """Rename a context"""
    if old_name == "default":
        console.print("[red]✗[/red] Cannot rename the default context")
        return
    
    # Validate new name
    if not new_name.replace('_', '').replace('-', '').isalnum():
        console.print("[red]✗[/red] Context name can only contain letters, numbers, hyphens, and underscores")
        return
    
    if context_storage.context_exists(new_name):
        console.print(f"[red]✗[/red] Context '{new_name}' already exists")
        return
    
    ctx = context_storage.get_context(old_name)
    if not ctx:
        console.print(f"[red]✗[/red] Context '{old_name}' not found")
        return
    
    # Update context
    contexts = context_storage.load_contexts()
    for c in contexts:
        if c.name == old_name:
            c.name = new_name
            break
    context_storage.save_contexts(contexts)
    
    # Rename the task file
    old_file = Path.home() / ".tix" / "contexts" / f"{old_name}.json"
    new_file = Path.home() / ".tix" / "contexts" / f"{new_name}.json"
    if old_file.exists():
        old_file.rename(new_file)
    
    # Update active context if needed
    if context_storage.get_active_context() == old_name:
        context_storage.set_active_context(new_name)
    
    console.print(f"[green]✔[/green] Renamed context: [cyan]{old_name}[/cyan] → [cyan]{new_name}[/cyan]")


@context.command(name='current')
def show_current():
    """Show the current active context"""
    active = context_storage.get_active_context()
    ctx = context_storage.get_context(active)
    
    console.print(f"[bold]Current context:[/bold] [cyan]{active}[/cyan]")
    
    if ctx and ctx.description:
        console.print(f"[dim]{ctx.description}[/dim]")
    
    # Show task counts
    try:
        storage = TaskStorage(context=active)
        tasks = storage.load_tasks()
        active_tasks = [t for t in tasks if not t.completed]
        global_count = len([t for t in tasks if t.is_global])
        local_count = len(tasks) - global_count
        
        console.print(f"\n[bold]Tasks:[/bold]")
        console.print(f"  • Total: {len(tasks)} ({local_count} local, {global_count} global)")
        console.print(f"  • Active: {len(active_tasks)}")
        console.print(f"  • Completed: {len(tasks) - len(active_tasks)}")
    except:
        pass
