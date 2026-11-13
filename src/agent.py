"""회의실 안내 LangGraph 단일 Agent.

    python src/agent.py            # 시험 질문 실행
    python src/agent.py "질문"      # 원하는 질문으로 실행

그래프:  START -> agent --(도구 호출 있음)--> tools -> agent ... --(없음)--> END
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tools import TOOLS  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[2] / ".env")   # sds-ax-practice/.env (AWS 키)

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
REGION = "us-east-1"

SYSTEM = (
    "당신은 사내 회의실 안내 담당입니다. "
    "회의실 정보는 반드시 도구로 확인하고, 도구 결과에 있는 내용만 답하세요. "
    "예약 가능 여부는 아직 확인할 수 없으니, 물어보면 '예약 조회는 준비 중'이라고 안내하세요. "
    "답은 한국어로 짧고 정리해서 하세요."
)
TEST_QUESTION = "8명이 회의할 방을 찾아주고, 그중 제일 작은 방의 상세 정보도 알려줘"


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def build_graph():
    llm = ChatBedrockConverse(model=MODEL_ID, region_name=REGION, temperature=0).bind_tools(TOOLS)

    def agent(state: State) -> dict:
        return {"messages": [llm.invoke([SystemMessage(SYSTEM), *state["messages"]])]}

    g = StateGraph(State)
    g.add_node("agent", agent)
    g.add_node("tools", ToolNode(TOOLS))
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", tools_condition)   # 도구 호출이 있으면 tools, 없으면 END
    g.add_edge("tools", "agent")
    return g.compile()


def main() -> None:
    question = " ".join(sys.argv[1:]) or TEST_QUESTION
    print(f"[질문] {question}\n")
    result = build_graph().invoke({"messages": [HumanMessage(question)]}, {"recursion_limit": 10})
    for m in result["messages"][1:]:
        if getattr(m, "tool_calls", None):
            for c in m.tool_calls:
                print(f"  → 도구 호출: {c['name']}({c['args']})")
        elif m.type == "tool":
            print(f"  ← 결과: {m.content.splitlines()[0]} ...")
    print(f"\n[답변]\n{result['messages'][-1].content}")


if __name__ == "__main__":
    main()
