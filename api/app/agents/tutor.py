from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from .. import store
from ..llm import get_llm


# 1. State: everything the agent knows, passed from node to node
class TutorState(TypedDict):
    user_id: str
    course: str
    messages: Annotated[list[AnyMessage], add_messages]
    context: str
    sources: list[dict]


# 2. Nodes: one step each; return only the fields that change
def retrieve(state: TutorState) -> dict:
    context, sources = store.material_context(state["user_id"], state["course"])
    return {"context": context, "sources": sources}


async def generate(state: TutorState) -> dict:
    prompt = list(state["messages"])
    if state["context"]:
        prompt.insert(0, SystemMessage(
            "Course materials uploaded by the student:\n" + state["context"]))
    answer = await get_llm().ainvoke(prompt)
    return {"messages": [answer]}


# 3. Graph: connect the nodes
def build_graph():
    graph = StateGraph(TutorState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


tutor_graph = build_graph()