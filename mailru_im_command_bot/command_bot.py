from enum import Enum
from inspect import Parameter, signature
from logging import Logger, getLogger
from textwrap import dedent, indent
from time import time
from traceback import format_exc
from typing import Callable, Dict, Iterable, List, Optional, Tuple, Union

from bot.bot import Bot, Event
from bot.handler import CommandHandler as StdCommandHandler
from bot.handler import HelpCommandHandler, StartCommandHandler

from .types import (
    ArgSigType, ArgType, BadArg, CommandHandler, CustomParam,
    Decorator, Handler, ImproperlyConfigured, MessageEnv,
)


class CommandBot:
    def __init__(
        self, *args,
        help_message: str = '',
        alert_to: Optional[List[str]] = None,
        logger: Optional[Logger] = None,
        from_bot: Optional[Bot] = None,
        decorators: Optional[List[Decorator]] = None,
        **kwargs,
    ):
        '''
        you can use any bot.Bot's *args **kwargs
        :help_message - is help message header
        :alert_to - list of chats to send exceptions
        :logger - provided logger (by default `getLogger()`)
        :from_bot - existing bot.Bot instance
        :decorators - list of your decorators `Callable[[Handler], Handler]`
            where `Handler = Callable[[bot.Bot, bot.Event], None]`

        Example:
        ```python
        bot = CommandBot(
            token='your_token_here',
            name='your_bot_name',
            version='your_bot_version',
            logger=getLogger(__name__),
            alert_to=['danila.fomin@corp.mail.ru'],
            help_message='your bot description',
        )
        ```
        '''
        self.bot = from_bot or Bot(*args, **kwargs)
        self.paths: List[Tuple[str, CommandHandler]] = []
        self.alert_to = alert_to or []
        self.help_message = help_message
        self.decorators = decorators or []
        self.logger = logger or getLogger()

    def command(self, path: str):
        '''
        registers new command in CommandBot
        for example:
        ```python
        class ExampleEnum(enum.Enum):
            case_one = 1
            case_two = 2

        @bot.command('cmd')
        def cmd(
            env: MessageEnv,
            int_arg: int,  # required
            float_arg: float = 1.0,  # optional
            str_arg: str = 'test_str',  # optional
            enum_arg: ExampleEnum = ExampleEnum.case_one,  # optional
            implicit_str_arg = 'implicit_str',  # optional
            bool_arg: bool = True,  # optional
        ) -> str:
            """your function help message"""
            ...
            return 'your result'
        ```
        '''
        def decorator(func: CommandHandler) -> CommandHandler:
            self._check_args(func)
            self.paths.append((path, func))
            self.bot.dispatcher.add_handler(StdCommandHandler(
                command=path, callback=self._decorate(path, func),
            ))

            return func

        return decorator

    def register_help(self):
        help_cb = self._access_log_decorator(self._help_cb)
        self.bot.dispatcher.add_handler(
            HelpCommandHandler(callback=help_cb),
        )

        self.bot.dispatcher.add_handler(
            StartCommandHandler(callback=help_cb)
        )

    def start(self):
        self.register_help()
        self.bot.start_polling()

    @classmethod
    def _format_param(cls, param: Parameter) -> str:
        types_to_str = {
            int: 'int',
            float: 'float',
            str: 'str',
            bool: 'True|False',
        }

        if param.annotation in types_to_str:
            param_str = f'{param.name}: {types_to_str[param.annotation]}'
            if param.default is not param.empty:
                param_str += f' = {param.default}'
            return param_str

        if issubclass(param.annotation, CustomParam):
            param_str = f'{param.name}: {param.annotation.verbose_classname()}'
            if param.default is not param.empty:
                param_str += f' = {param.default.to_arg()}'
            return param_str

        if issubclass(param.annotation, Enum):
            vars = '|'.join(e.name for e in param.annotation)  # type: ignore
            param_str = f'{param.name}: {vars}'
            if param.default is not param.empty:
                param_str += f' = {param.default.name}'
            return param_str

        param_str = f'{param.name}: str'
        if param.default is not param.empty:
            param_str += f' = {param.default}'

        return param_str

    @classmethod
    def _format_function_help(cls, path: str, func: CommandHandler) -> str:
        doc = [f'/{path}']

        desc = dedent(func.__doc__ or '').strip()
        if desc:
            doc.append(indent(desc, '  '))

        sig = "\n".join(
            indent(cls._format_param(p), '  ')
            for p in cls._parameters(func)
        )
        if sig:
            doc.append(indent(f'args:\n{sig}', '  '))

        return '\n'.join(doc)

    @classmethod
    def _parameters(cls, func: CommandHandler) -> List[Parameter]:
        return list(signature(func).parameters.values())[1:]

    @classmethod
    def _format_help_message(
        cls, help_message: str, funcs: Iterable[Tuple[str, CommandHandler]],
    ) -> str:
        message = '\n\n'.join(
            cls._format_function_help(path, cb)
            for path, cb in funcs
        )

        message = f'list of commands:\n{message}'
        if help_message:
            message = f'{help_message}\n\n{message}'

        return message

    def _help_cb(self, bot, event):
        bot.send_text(
            chat_id=event.from_chat,
            text=self._format_help_message(self.help_message, self.paths),
        )

    @classmethod
    def _format_error_message(
        cls, user: str, message: Union[str, Callable[[], str]],
    ) -> str:
        if callable(message):
            message = message()

        return f'ERROR: user={user}\n\n{message}'

    def _send_error_message(
        self,
        user: str = '__unknown__',
        message: Union[str, Callable[[], str]] = format_exc,
    ):
        for alert_chat_id in self.alert_to:
            try:
                self.bot.send_text(
                    chat_id=alert_chat_id,
                    text=self._format_error_message(user, message),
                )
            except Exception as e:
                self.logger.exception(f'an error while reporting error: {e}')

    @classmethod
    def _access_log(
        cls,
        log: Callable[[str], None],
        log_error: Callable[[str, Exception], None],
        user_and_chat: str, message: str,
        handler: Callable[[], None],
    ):
        start_t = time()
        path = '{not a path}'

        splitted = message.split()
        if len(splitted) > 0 and splitted[0].startswith('/'):
            path, *_ = splitted

        access_msg = f'[ACCESS] {user_and_chat} {path}'
        try:
            log(access_msg)
            handler()
        except Exception as e:
            log_error(user_and_chat, e)
        finally:
            log(f'{access_msg} elapsed={time() - start_t:.3f}s')

    def _log_exception(self, user_and_chat: str, e: Exception):
        self.logger.error(e, exc_info=True)
        self._send_error_message(user_and_chat)

    def _access_log_decorator(self, func: Handler) -> Handler:
        def decorated(bot: Bot, event: Event):
            self._access_log(
                self.logger.info, self._log_exception,
                f'[{self._get_user(event)}]@[{event.from_chat}]',
                event.text, lambda: func(bot, event),
            )

        return decorated

    @classmethod
    def _check_args(cls, func: CommandHandler):
        for p in cls._parameters(func):
            ann = p.annotation
            if ann is not p.empty:
                if not issubclass(
                    ann, (str, int, float, bool, Enum, CustomParam),
                ):
                    raise ImproperlyConfigured(
                        f'improperly configured: param type {p} '
                        f'is not supported. must be {ArgType}'
                    )
            else:
                ann = str

            if (
                p.default is not p.empty and
                not isinstance(p.default, ann)
            ):
                raise ImproperlyConfigured(
                    'improperly configured: '
                    f'param default {p} is not instance of {ann}'
                )

    @classmethod
    def _cast_arg(
        cls, param: Parameter, arg: str
    ) -> ArgType:
        ann: ArgSigType = param.annotation

        if issubclass(ann, CustomParam):
            return ann.from_arg(arg)

        if issubclass(ann, Enum):
            try:
                return ann[arg]
            except KeyError:
                raise BadArg(f'{arg!r} is bad param for {ann}')

        if issubclass(ann, bool):
            arg = arg.lower()
            if arg == 'true':
                return True
            elif arg == 'false':
                return False
            else:
                raise BadArg(f'can\t cast param {arg!r} to {ann}')

        if issubclass(ann, (float, int)):
            try:
                return ann(arg)
            except ValueError:
                raise BadArg(f'can\'t cast param {arg!r} to {ann}')

        return arg

    @classmethod
    def _gen_kwargs(
        cls, params: List[Parameter], msg_args: List[str],
    ) -> Dict[str, ArgType]:
        splited_args = [arg.split('=', 1) for arg in msg_args]
        # not allow commands like /cmd 1 2 c=3 4
        single_or_pair = list(map(len, splited_args))
        if sorted(single_or_pair) != single_or_pair:
            raise BadArg(
                'you can\'t use positional arguments after key-value arguments'
            )

        default_kwargs = {
            p.name: p.default
            for p in params
            if p.default is not p.empty
        }

        params_by_name = {
            p.name: p
            for p in params
        }

        try:
            kwarg_kwargs = {
                kv[0]: cls._cast_arg(params_by_name[kv[0]], kv[1])
                for kv in splited_args
                if len(kv) == 2
            }
        except KeyError as e:
            raise BadArg(f'no argument with name {e}')

        try:
            positional_args = msg_args[:single_or_pair.index(2)]
        except ValueError:
            positional_args = msg_args

        positional_kwargs = {
            p.name: cls._cast_arg(p, pos_arg)
            for p, pos_arg in zip(params, positional_args)
        }

        kwargs = {
            **default_kwargs,
            **positional_kwargs,
            **kwarg_kwargs,
        }

        for param in params:
            if param.name not in kwargs:
                raise BadArg(f'no value for arg {param.name!r}')

        return kwargs

    @classmethod
    def _gen_kwargs_from_msg(
        cls, func: CommandHandler, msg: str,
    ) -> Dict[str, ArgType]:
        msg_args = [a for a in msg.split() if a][1:]
        return cls._gen_kwargs(cls._parameters(func), msg_args)

    @classmethod
    def _command_args(
        cls,
        send: Callable[[str], None],
        path: str, handler: CommandHandler,
        env: MessageEnv, message: str,
    ):
        try:
            kwargs = cls._gen_kwargs_from_msg(handler, message)
        except BadArg as e:
            send(f'{e}\n{cls._format_function_help(path, handler)}')
            return

        try:
            send(handler(env, **kwargs))
        except Exception:
            send('some error occurred')
            raise

    def _command_args_decorator(
        self, path: str, func: CommandHandler,
    ) -> Handler:
        def decorated(bot: Bot, event: Event):
            self._command_args(
                lambda msg: bot.send_text(event.from_chat, msg), path, func,
                MessageEnv(bot, event, self._get_user(event)), event.text,
            )

        return decorated

    def _decorate(self, path: str, func: CommandHandler) -> Handler:
        decorated = self._command_args_decorator(path, func)

        for decorator in self.decorators:
            decorated = decorator(decorated)

        decorated = self._access_log_decorator(decorated)

        return decorated

    @classmethod
    def _get_user(cls, event: Event):
        return event.message_author['userId']
