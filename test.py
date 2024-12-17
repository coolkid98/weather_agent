import aiohttp
import asyncio
import os
import json

async def test_api():
    API_KEY = os.environ['WEATHER_API_KEY']
    API_HOST = "https://devapi.qweather.com"
    city = "上海"
    
    print(f"使用的API KEY: {API_KEY}")  # 打印API KEY（注意安全）
    
    async with aiohttp.ClientSession() as session:
        # 测试城市查询API
        geo_url = f"{API_HOST}/v2/city/lookup"
        params = {
            "location": city,
            "key": API_KEY,
            "range": "cn"
        }
        
        print(f"完整请求URL: {geo_url}?{'&'.join([f'{k}={v}' for k,v in params.items()])}")
        
        async with session.get(geo_url, params=params) as response:
            print(f"响应状态码: {response.status}")
            print(f"响应头: {dict(response.headers)}")
            data = await response.text()
            print(f"响应内容: {data}")

if __name__ == "__main__":
    asyncio.run(test_api())