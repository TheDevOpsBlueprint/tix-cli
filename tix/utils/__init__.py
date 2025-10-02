from datetime import datetime, timedelta
from rich.console import Console

console = Console()


def get_date(date: str):
    if not date:
        return None
    try:
        date = date.strip()
        due_date = None
        if date == "tomorrow":
            return (datetime.today() + timedelta(days=1)).strftime(r"%Y-%m-%d")
        if date == "next week":
            return (datetime.today() + timedelta(weeks=1)).strftime(r"%Y-%m-%d")
        due_date = datetime.strptime(date, r"%Y-%m-%d")
        if due_date < datetime.today():
            console.print("[red]Past dates not allowed")
            return None
        return due_date.strftime(r"%Y-%m-%d")
    except ValueError as ve:
        console.print(f"Error parsing due date:\n{ve}")
        return None
