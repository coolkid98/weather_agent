import streamlit as st
import asyncio
import os
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient

# 定义天气工具函数
async def get_weather(city: str) -> str:
    return f"{city}的天气是23度，晴天。"

# 设置页面配置
st.set_page_config(
    page_title="智能天气助手",
    page_icon="🌤️",
    layout="wide"
)

# 初始化Streamlit页面
st.title("🌤️ 智能天气助手")
st.markdown("### 让AI帮你查询任何城市的天气信息")

# 创建输入框
user_input = st.text_input(
    "请输入要查询的城市名称:",
    placeholder="例如：北京、上海、广州...",
    help="输入任何城市名称，AI助手将为您查询天气信息"
)

async def run_weather_agent(query: str):
    # 设置系统提示词
    system_message = """你是一个专业的天气助手。请以友好和自然的方式回答用户的天气查询。
    回答时请注意：
    1. 使用礼貌和亲切的语气
    2. 除了天气数据外，可以根据天气给出合适的建议
    3. 回答要简洁明了
    4. 全程使用中文回答
    
    当完成回答后，请说"结束"。
    """
    
    # 定义agent
    weather_agent = AssistantAgent(
        name="weather_agent",
        system_message=system_message,
        model_client=OpenAIChatCompletionClient(
            model="gpt-3.5-turbo",
            api_key=os.environ['OPENAI_API_KEY']
        ),
        tools=[get_weather],
    )

    # 定义终止条件
    termination = TextMentionTermination("结束")

    # 定义团队
    agent_team = RoundRobinGroupChat([weather_agent], termination_condition=termination)

    # 创建进度提示
    with st.spinner('正在查询天气信息...'):
        # 运行团队并获取消息流
        message_placeholder = st.empty()
        async for message in agent_team.run_stream(task=f"请查询{query}的天气情况"):
            message_placeholder.markdown(message)

# 添加查询按钮
if st.button("查询天气", type="primary"):
    if user_input:
        asyncio.run(run_weather_agent(user_input))
    else:
        st.warning("请先输入城市名称！")

# 添加页面底部信息
st.markdown("---")
st.markdown("##### 💡 提示：你可以询问任何城市的天气，AI助手会为你提供详细信息。")