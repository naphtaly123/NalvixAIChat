# from groq import Groq
# import requests
# from core.config import get_settings

# settings = get_settings()

# class LLMService:
#     def __init__(self):
#         self.groq_client = Groq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None
    
#     def chat(self, prompt: str) -> str:
#         if settings.USE_DEEPSEEK_CHAT:
#             return self._chat_deepseek(prompt)
#         return self._chat_groq(prompt)
    
#     def _chat_groq(self, prompt: str) -> str:
#         if not self.groq_client:
#             raise ValueError("GROQ_API_KEY not set")
            
#         response = self.groq_client.chat.completions.create(
#             model="llama-3.1-8b-instant",
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0.7
#         )
#         return response.choices[0].message.content
    
#     def _chat_deepseek(self, prompt: str) -> str:
#         response = requests.post(
#             "https://api.deepseek.com/chat/completions",
#             headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"},
#             json={
#                 "model": "deepseek-chat",
#                 "messages": [{"role": "user", "content": prompt}],
#                 "stream": False
#             }
#         )
#         return response.json()["choices"][0]["message"]["content"]

# # Singleton
# _llm_service = None

# def get_llm_service():
#     global _llm_service
#     if _llm_service is None:
#         _llm_service = LLMService()
#     return _llm_service


# app/services/rag/llm.py (Updated to use settings)
from typing import Dict, List

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from core.config import settings
import logging

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        # Use Groq as primary LLM
        self.llm = ChatGroq(
            model=settings.GROQ_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            api_key=settings.GROQ_API_KEY,
            max_retries=2,
            max_tokens=settings.MAX_TOKENS
        )
        
        # Optionally support DeepSeek fallback
        self.use_deepseek = settings.USE_DEEPSEEK_CHAT
        if self.use_deepseek and settings.DEEPSEEK_API_KEY:
            # Initialize DeepSeek if configured
            pass
    
    async def generate_with_context(self, query: str, context: str) -> str:
        """Generate response with context using Groq"""
        try:
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="""You are a helpful AI assistant. Use the provided context to answer the user's question.
                If the answer is not in the context, say so politely. Be concise and accurate.""",),
                HumanMessage(content=f"""Context: {context}
                
                Question: {query}
                
                Answer: """)
            ])
            
            chain = prompt | self.llm
            response = await chain.ainvoke({})
            
            return response.content
        
        except Exception as e:
            logger.error(f"LLM generation error: {str(e)}")
            raise
    
    async def generate_response(self, messages: List[Dict]) -> str:
        """Generate response from conversation history"""
        try:
            formatted_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    formatted_messages.append(SystemMessage(content=msg["content"]))
                elif msg["role"] == "user":
                    formatted_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    formatted_messages.append(HumanMessage(content=f"Assistant: {msg['content']}"))
            
            response = await self.llm.ainvoke(formatted_messages)
            return response.content
        
        except Exception as e:
            logger.error(f"LLM generation error: {str(e)}")
            raise