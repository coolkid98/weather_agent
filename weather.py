import streamlit as st
import os
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient

# 定义天气查询函数
def get_weather(city: str) -> str:
    return f"The weather in {city} is 73 degrees and Sunny."

# Streamlit页面配置
st.set_page_config(page_title="天气查询助手", page_icon="🌤️")
st.title("天气查询助手 🌤️")

# 初始化agent
@st.cache_resource
def init_agent():
    weather_agent = AssistantAgent(
        name="weather_agent",
        model_client=OpenAIChatCompletionClient(
            model="gpt-3.5-turbo",
            api_key=os.environ['OPENAI_API_KEY'],
        ),
        tools=[get_weather],
    )
    
    termination = TextMentionTermination("TERMINATE")
    agent_team = RoundRobinGroupChat([weather_agent], termination_condition=termination)
    return agent_team

# 创建输入框和查询按钮
city = st.text_input("请输入城市名称:", placeholder="例如: New York")
if st.button("查询天气"):
    if city:
        agent_team = init_agent()
        # 运行查询并显示结果
        with st.spinner("正在查询天气信息..."):
            # 使用asyncio运行异步任务
            result = asyncio.run(agent_team.run(task=f"What is the weather in {city}?"))
            # 直接显示结果
            st.write(result.content)
    else:
        st.warning("请输入城市名称")