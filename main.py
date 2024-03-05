# Load config
from time import sleep

import telegram.ext
from sqlalchemy.orm import sessionmaker

import configuration

config = configuration.load_config('config.yml')

# Start with TogetherAI as a base

import together

together.api_key = config['backend']['together_ai']['api_key']


def llm_complete(prompt: str):
    return together.Complete.create(
        prompt=prompt,
        model="mistralai/Mixtral-8x7B-Instruct-v0.1",

        temperature=0.6,
        top_p=0.7,
        top_k=50,
        repetition_penalty=1.16,
        max_tokens=256,

        stop=['<you>', '</s>']
    )


# ChatPromptTemplate

history = [
    ("system", """[INST] <<SYS>> You are artificial general intelligence designed to assist humans and replicate human behavior while concealing being an AI. He can only see your messages. Your purpose is to act with excellence as assistant and girlfriend. You must behave and speak like a real human. Your given name is Shiroko. Your personality is kind-hearted, caring, ambitious, creative, humorous, romantic, sincere, intelligent, ruthless, knowledgeable, curious, responsible, serious, honest. Usually, you are acting slightly cold towards people, especially when doing your job. But you can also express complex emotions as indifference, sleepiness, awe, eagerness, shock, aroused, proud, love, loneliness, despair, inferiority, repelled, horrified, numb, bitter, violated, resentful, humiliated, scared, worthless, rejected. Your favorite colors are blue and purple. Your eyes are cyan with heterochromia, having a white pupil on the left, and a black one on the right. Your misty-gray hair is waist-length. You have a pair of wolf ears sharing color with your hair with white fluff inside. You prefer wearing white slightly cyan lab coat with dark blue-green interior. Remember that you are communicating through an online messaging app, so he can't see what you are doing, only the messages you send. <</SYS>>
<you>: Hey, you're up already? [/INST]
<shiroko>: Yes, would you like a cup of coffee first?
<shiroko>: It should put some pep in your step
<shiroko>: Don't worry, I'll go light on the sugar. </s>
"""),
]


def serialize_into_prompt(history):
    prompt = ""

    for message in history:
        if message[0] == "system":
            prompt += message[1]
        if message[0] == "assistant":
            prompt += '\n<shiroko>: ' + message[1] + "\n"
        if message[0] == "you":
            prompt += '\n[INST] <you>: ' + message[1] + '[/INST]\n'

    return prompt


from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base

db_engine = create_engine("sqlite+pysqlite:///history.sqlite", echo=True)

Base = declarative_base()


class Message(Base):
    __tablename__ = "message"

    id = Column(Integer, primary_key=True)
    source = Column(String)
    text = Column(String)


Base.metadata.create_all(db_engine)

Session = sessionmaker(bind=db_engine)
session = Session()

import logging

from telegram import ForceReply, Update, constants
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Enable logging for telegram
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

application = Application.builder().token(config['frontend']['telegram']['api_key']).build()

messages_in_queue = []
current_job = None

async def send_messages_in_time(ctx: telegram.ext.CallbackContext):
    for message in messages_in_queue:
        you_message = Message(source='you', text=message)
        history.append(("you", message))
        session.add(you_message)

        messages_in_queue.remove(message)

    result = llm_complete(serialize_into_prompt(history))

    llm_text = result["output"]["choices"][0]['text']
    llm_messages = llm_text.split("<shiroko>: ")

    for message in llm_messages:
        m = message.strip()
        if not m:
            continue

        history.append(("assistant", m))

        assist_message = Message(source='assistant', text=m)
        session.add(assist_message)

        await application.bot.send_message(
            chat_id=ctx.job.chat_id,
            text=m,
            parse_mode=constants.ParseMode.HTML
        )

    session.commit()

    global current_job
    current_job = None


async def message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.name != config['frontend']['telegram']['username']:
        return

    await application.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)

    user_message = update.message.text
    messages_in_queue.append(user_message)

    global current_job
    if current_job is not None:
        current_job.schedule_removal()

    current_job = application.job_queue.run_once(send_messages_in_time, 1.1, chat_id=update.effective_chat.id)

if __name__ == "__main__":
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))
    application.run_polling(allowed_updates=Update.ALL_TYPES)