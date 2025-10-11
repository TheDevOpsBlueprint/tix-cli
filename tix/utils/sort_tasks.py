from tix.models import Task

def sort_tasks(tasks: list[Task], sort_by: str = None, sort_order:str = None) -> list[Task]:
    try:    
        priority_order = {"low": 0, "medium": 1, "high": 2}
        if sort_by:
            sort_by_target = sort_by if sort_by != "created" else "created_at" # fix difference key on task model
            is_reverse = sort_order == 'desc'
            
            if sort_by == "priority":
                sorted_tasks = sorted(tasks, key=lambda t: priority_order.get(getattr(t, sort_by_target, ""), ""), reverse=is_reverse)
            else:
                sorted_tasks = sorted(tasks, key=lambda t: getattr(t, sort_by_target, ""), reverse=is_reverse)
        else:
            sorted_tasks = sorted(tasks, key=lambda t: (getattr(t, "completed", False) ,getattr(t, "id", 0)))
    except:
        sorted_tasks = sorted(tasks, key=lambda t: (getattr(t, "completed", False), getattr(t, "id", 0)))
    return sorted_tasks
