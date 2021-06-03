# mailru_im_command_bot
[![PyPI](https://img.shields.io/pypi/v/mailru-im-command-bot?style=for-the-badge)](https://pypi.org/project/mailru-im-command-bot)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/mailru-im-command-bot?style=for-the-badge)
![tests](https://img.shields.io/github/workflow/status/dedefer/mailru-im-command-bot/lint%20and%20test/main?label=tests&style=for-the-badge)
![coverage](https://img.shields.io/codecov/c/github/dedefer/mailru-im-command-bot?color=green&style=for-the-badge)

mailru_im_command_bot is convenient library for generic myteam/icq bots.
In fact it is a wrapper for mailru-im-bot.

It uses type annotations for help method and transforming arguments.

It is fully tested and production-ready)

[Pypi link](https://pypi.org/project/mailru-im-command-bot)

## Usage

You can create your bot with following code:

```python
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
```

Bot will response you:

```text
you: /hello
bot: hello world

you: /hello danila
bot: hello danila
```

Help message will be:

```text
this is simple hello world bot

list of commands:
/hello
  args:
    name: str = world
```

## Advanced Usage

Bot can automatically parse int, float, bool, any enum.Enum
and also any type that implements mailru_im_command_bot.CustomParam protocol:

```python
import enum
import logging
from logging import getLogger

from mailru_im_command_bot import BadArg, CommandBot, MessageEnv

logging.basicConfig(level=logging.INFO)


class Email(str):
    @classmethod
    def verbose_classname(cls) -> str:
        return cls.__name__

    @classmethod
    def from_arg(cls, arg: str) -> 'Email':
        if '@' not in arg:
            raise BadArg(f'{arg} is invalid email')
        return cls(arg)

    def to_arg(self) -> str:
        return str(self)


class ExampleEnum(enum.Enum):
    case_one = 1
    case_two = 2


bot = CommandBot(
    token='tour_token',
    name='your_bot_name',
    version='1.0.0',
    logger=getLogger(__name__),
    alert_to=['your_id'],
    help_message='your bot description',
)


@bot.command('example_command')
def example_command(
    env: MessageEnv,
    int_arg: int,  # required
    float_arg: float = 1.0,  # optional
    str_arg: str = 'test_str',  # optional
    enum_arg: ExampleEnum = ExampleEnum.case_one,  # optional
    bool_arg: bool = True,  # optional
    email_arg: Email = Email('ddf1998@gmail.com'),  # optional
) -> str:
    """your function help message"""
    ...
    return 'response'


bot.start()
```

You can also wrap existing bot:

```python
from bot import Bot
from mailru_im_command_bot import CommandBot
from logging import getLogger

base_bot = Bot(
    token='your_token_here',
    name='your_bot_name',
    version='your_bot_version',
)

bot = CommandBot(
    from_bot=base_bot,
    logger=getLogger(__name__),
    alert_to=['danila.fomin@corp.mail.ru'],
    help_message='your bot description',
)

```

Bot accepts messages like this:

```text
/example_command 1
# you get int_arg = 1 and other arguments defaults

/example_command 1 0
# you get int_arg = 1, float_arg = 0.0 and other arguments defaults

...etc
```

It also can accept key-value arguments:

```text
/example_command int_arg=1
/example_command 1 enum_arg=case_two
/example_command int_arg=1 enum_arg=case_two
```

Your help message will be like this:

```text
your bot description

list of commands:
/example_command
  your function help message
  args:
    int_arg: int
    float_arg: float = 1.0
    str_arg: str = test_str
    enum_arg: case_one|case_two = case_one
    bool_arg: True|False = True
    email_arg: Email = ddf1998@gmail.com
```

Bot automatically writes access log with provided logger.

```text
[ACCESS] [user_id]@[chat_id] /example_command elapsed=0.100s
```

If an exception occurred bot will write the error into log, send `'some exception occurred'` to user and report error to users in `alert_to` list.
