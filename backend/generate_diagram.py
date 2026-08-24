from app.agent.graph import build_graph

graph = build_graph()
diagram = graph.get_graph().draw_mermaid()

with open("langgraph_diagram.md", "w") as f:
    f.write("```mermaid\n")
    f.write(diagram)
    f.write("\n```\n")
