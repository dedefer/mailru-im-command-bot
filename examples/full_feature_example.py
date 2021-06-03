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
