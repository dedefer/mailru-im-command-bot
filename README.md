# mailru_im_command_bot

mailru_im_command_bot is convenient library for generic myteam/icq bots.
In fact it is wrapper for mailru-im-bot.

It uses type annotations for help method and transforming arguments.

It is fully tested and production-ready)

[Pypi link](https://pypi.org/project/mailru-im-command-bot)

## Usage

You can create your bot with following code:

```python
from mailru_im_command_bot import CommandBot, MessageEnv
from logging import getLogger
import enum


class ExampleEnum(enum.Enum):
    case_one = 1
    case_two = 2


bot = CommandBot(
    # you can provide any bot.Bot kwargs
    token='your_token_here',
    name='your_bot_name',
    version='your_bot_version',
    logger=getLogger(__name__),
    alert_to=['danila.fomin@corp.mail.ru'],
    help_message='your bot description',
)

@bot.command('example_command')
def example_command(
    env: MessageEnv,
    int_arg: int,  # required
    float_arg: float = 1.0,  # optional
    str_arg: str = 'test_str',  # optional
    enum_arg: ExampleEnum = ExampleEnum.case_one,  # optional
) -> str:
    """your function help message"""
    ...
    return 'your result'

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

As argument type you can use str, float, int and any enum.Enum. Library automatically validates and casts strings to your types.

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
```

Bot automatically writes access log with provided logger.

```text
[ACCESS] [user_id]@[chat_id] /example_command elapsed=0.1s
```

If an exception occured bot will write the error into log, send `'some error occured'` to user and report error to users in `alert_to` list.
