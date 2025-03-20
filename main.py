from dotenv import load_dotenv
import os
from rich.console import Console
from rich.markdown import Markdown
from src.llama_api import get_llama_response

console = Console()
load_dotenv(dotenv_path='../')

def main():
    console.print(Markdown(r"""**Добро пожаловать в вопрос-ответную систему ВШЭ!**\
Спрашивайте обо всем, что вас интересует. Если захотите прервать диалог, введите `stop`"""))
    conversation_history = []
    
    while True:
        user_input = input("\nВОПРОС: >> ")

        # Поменять заглушку, когда будет интерфейс
        if user_input.lower() == 'stop':
            console.print(Markdown(r"**До свидания!**"))
            break
        
        conversation_history.append({"role": "user", "content": user_input})
        response = get_llama_response(conversation_history)
        
        conversation_history.append({"role": "assistant", "content": response})
        console.print(Markdown(f"""\\
ОТВЕТ: << {response}"""))

if __name__ == "__main__":
    # Загрузка API-ключа из .env
    API_KEY = os.getenv('GROQ_API_KEY')
    os.environ['GROQ_API_KEY'] = API_KEY
    
    # Диалог
    main()