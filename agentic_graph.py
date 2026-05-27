from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool

from config import Config
from core.retriever import HybridRetriever

# 延迟初始化检索器（避免 import 时创建数据库连接）
_retriever = None


def _get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever


# 定义唯一工具：知识检索
@tool
def knowledge_search(query: str) -> str:
    """在企业知识库中搜索相关内容。当需要基于内部文档、手册回答问题时使用此工具。"""
    chunks, _ = _get_retriever().hybrid_search(query, top_k=3)
    if not chunks:
        return "未找到相关信息。"
    return "\n\n".join(chunks)


tools = [knowledge_search]

# 创建 LLM 实例
llm = ChatOllama(model=Config.LLM_MODEL, temperature=0, base_url=Config.OLLAMA_BASE_URL)

# 自定义中文 ReAct 提示词模板
template = """你是一个智能助手，可以调用以下工具来回答问题：

{tools}

使用以下格式，每一步必须严格遵守：
Question: 用户的问题
Thought: 你需要思考下一步该做什么
Action: 要调用的工具名称，必须是 [{tool_names}] 中的一个
Action Input: 工具需要的输入（单个字符串）
Observation: 工具返回的结果
... (可以重复 Thought/Action/Action Input/Observation 多次)
Thought: 我现在有足够的信息来回答用户了
Final Answer: 对用户的最终回答

开始！

Question: {input}
Thought: {agent_scratchpad}
"""

prompt = PromptTemplate.from_template(template)

# 创建 Agent 执行器
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True, max_iterations=10, max_execution_time=120)


def run_agent(question: str, history=None) -> str:
    """运行智能体，返回最终答案"""
    if history:
        context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history[-4:]])
        input_text = f"对话历史：\n{context}\n\n最新问题：{question}"
    else:
        input_text = question
    response = agent_executor.invoke({"input": input_text})
    return response["output"]
