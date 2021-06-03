from dataclasses import dataclass
from enum import Enum
from typing import Callable, Protocol, Type, Union, runtime_checkable

from bot.bot import Bot, Event
from mypy_extensions import KwArg, VarArg


@dataclass
class MessageEnv:
    bot: Bot
    event: Event
    user_id: str


class BadArg(Exception):
    pass


class ImproperlyConfigured(Exception):
    pass


@runtime_checkable
class CustomParam(Protocol):
    '''
    Any custom param type of bot must implement this protocol.

    from_message and to_message methods
    must be mutually inverse transformations.

    verbose_classname may be cls.__name__ or any other verbose
    classname for help method.

    That is they must satisfy following rules:
    ```python
    arg: str
    CustomParam.from_arg(arg).to_arg() == arg

    param: CustomParam
    CustomParam.from_arg(param.to_arg()) == param
    ```

    Also from_arg must raise `BadArg` exception on validation error.
    '''
    @classmethod
    def verbose_classname(cls) -> str: ...

    @classmethod
    def from_arg(cls, arg: str) -> 'CustomParam': ...

    def to_arg(self) -> str: ...


ArgType = Union[str, int, float, bool, Enum, CustomParam]

ArgSigType = Union[
    Type[str], Type[int], Type[float], Type[bool],
    Type[Enum], Type[CustomParam],
]

CommandHandler = Callable[[MessageEnv, VarArg(ArgType), KwArg(ArgType)], str]

Handler = Callable[[Bot, Event], None]

Decorator = Callable[[Handler], Handler]
