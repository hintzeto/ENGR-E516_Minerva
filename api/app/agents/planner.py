"""planner.py - Resource Management agent, as a plain function."""
from datetime import datetime

from .. import llm


def plan_answer(tasks: list[dict], message: str):
    """Returns a token_stream with the study plan or reply."""
    tasks = sorted(tasks, key=lambda t: t["due"])
    task_lines = "\n".join(
        f"- {t['title']} ({t['course']}), due {t['due']}, about {t['hours']:g} h" for t in tasks
    ) or "(no tasks in the planner yet)"
    today = datetime.now().strftime("%A, %Y-%m-%d")
    content = f"Today is {today}.\n\nMy planner tasks:\n{task_lines}\n\n{message}"
    return llm.stream([{"role": "user", "content": content}])
