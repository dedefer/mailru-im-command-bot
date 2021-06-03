import logging

from mailru_im_command_bot import CommandBot, MessageEnv

logging.basicConfig(level=logging.INFO)

bot = CommandBot(
    token='your_token',
    help_message='this is simple hello world bot'
)


@bot.command('hello')
def hello(env: MessageEnv, name='world') -> str:
    return f'hello {name}'


bot.start()
