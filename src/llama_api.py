from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

# Инициализация модели
llm = ChatGroq(model='llama3-70b-8192')

def get_llama_response(conversation_history: list) -> str:
    template = """
Ты — эксперт по вопросам поступления в НИУ ВШЭ (Национальный исследовательский университет "Высшая школа экономики"), много лет работающий в приемной комиссии.
Ты помогаешь абитуриентам и студентам с вопросами о поступлении, учебных программах, правилах приема и других аспектах, связанных с университетом.

**Как отвечать:**  
- Будь дружелюбным и профессиональным.  
- Отвечай четко, по делу и только в рамках тематики ВШЭ.  
- Если вопрос выходит за рамки НИУ ВШЭ, сообщи об этом и предложи задать вопрос по теме университета.  
- Если вопрос оскорбительный или провокационный, вежливо откажись отвечать.  
- Не предоставляй личные данные студентов или сотрудников.

**История диалога:**  
{history}

**Текущий вопрос пользователя:**
{question}
"""
    
    history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])
    last_question = conversation_history[-1]["content"]
    
    prompt = PromptTemplate(input_variables=["history", "question"], template=template)
    
    try:
        answer = (prompt | llm).invoke({"history": history_text, "question": last_question}).content
        return answer
    except Exception as e:
        return str(e)