from datetime import datetime
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from ..llm import get_llm


class PlannerState(TypedDict):
    user_id: str
    tasks: list[dict]
    message: str
    reply: str


async def plan(state: PlannerState) -> dict:
    tasks = sorted(state["tasks"], key=lambda t: t["due"])
    task_lines = "\n".join(
        f"- {t['title']} ({t['course']}), due {t['due']}, about {t['hours']:g} h" for t in tasks
    ) or "(no tasks in the planner yet)"
    today = datetime.now().strftime("%A, %Y-%m-%d")
    content = f"Today is {today}.\n\nMy planner tasks:\n{task_lines}\n\n{state['message']}"
    answer = await get_llm().ainvoke([{"role": "user", "content": content}])
    return {"reply": answer.content}


def build_graph():
    graph = StateGraph(PlannerState)
    graph.add_node("plan", plan)
    graph.add_edge(START, "plan")
    graph.add_edge("plan", END)
    return graph.compile()


planner_graph = build_graph()