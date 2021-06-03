import enum
import inspect
import re
import unittest
from dataclasses import dataclass
from textwrap import dedent, indent
from typing import List, Tuple
from unittest.mock import Mock

from bot.bot import Bot, Event

from mailru_im_command_bot import CommandBot, MessageEnv
from mailru_im_command_bot.command_bot import (
    BadArg, Handler, ImproperlyConfigured,
)


class ExampleEnum(enum.Enum):
    case_one = 1
    case_two = 2


@dataclass
class F:
    arg: int

    @classmethod
    def verbose_classname(cls) -> str:
        return cls.__name__

    @classmethod
    def from_arg(cls, arg: str) -> 'F':
        try:
            return cls(int(arg))
        except ValueError:
            raise BadArg(f'can\'t cast {arg!r} to F')

    def to_arg(self) -> str:
        return str(self.arg)


def cmd(
    env: MessageEnv,
    int_arg: int,  # required
    float_arg: float = 1.0,  # optional
    str_arg: str = 'test_str',  # optional
    enum_arg: ExampleEnum = ExampleEnum.case_one,  # optional
    implicit_str_arg='test_str',  # optional
    bool_arg: bool = True,
    custom_arg: F = F(123),
) -> str:
    """your function help message"""
    ...
    return 'your result'


cmd_defaults = {
    name: p.default
    for name, p in inspect.signature(cmd).parameters.items()
    if p.default is not p.empty
}

cmd_help = indent(dedent('''\
    your function help message
    args:
      int_arg: int
      float_arg: float = 1.0
      str_arg: str = test_str
      enum_arg: case_one|case_two = case_one
      implicit_str_arg: str = test_str
      bool_arg: True|False = True
      custom_arg: F = 123'''), '  ')


class Tests(unittest.TestCase):
    maxDiff = None

    def test_func_help(self):
        expected = f'/cmd\n{cmd_help}'

        help_msg = CommandBot._format_function_help('cmd', cmd)

        self.assertEqual(help_msg, expected)

    def test_help(self):
        expected = dedent(f'''\
        my help msg

        list of commands:
        /cmd\n{indent(cmd_help, '        ')}

        /cmd_alias\n{indent(cmd_help, '        ')}''')

        help_msg = CommandBot._format_help_message('my help msg', [
            ('cmd', cmd),
            ('cmd_alias', cmd),
        ])

        self.assertEqual(help_msg, expected)

    def test_parse_args(self):
        expected = {
            'int_arg': 1,
            'float_arg': 0.0,
            'str_arg': 'some',
            'implicit_str_arg': 'some',
            'enum_arg': ExampleEnum.case_two,
            'bool_arg': False,
            'custom_arg': F(321),
        }

        self.assertEqual(
            CommandBot._gen_kwargs_from_msg(
                cmd, '/cmd 1  0   some case_two some False 321',
            ),
            expected,
        )

        self.assertEqual(
            CommandBot._gen_kwargs_from_msg(
                cmd,
                '/cmd int_arg=1  float_arg=0   str_arg=some '
                'enum_arg=case_two implicit_str_arg=some bool_arg=False '
                'custom_arg=321',
            ),
            expected,
        )

        self.assertEqual(
            CommandBot._gen_kwargs_from_msg(
                cmd,
                '/cmd '
                'enum_arg=case_two implicit_str_arg=some bool_arg=False '
                'custom_arg=321 int_arg=1  float_arg=0   str_arg=some ',
            ),
            expected,
        )

    def test_parse_args_defaults(self):
        self.assertEqual(
            CommandBot._gen_kwargs_from_msg(cmd, '/cmd 1'),
            {**cmd_defaults, 'int_arg': 1},
        )

        self.assertEqual(
            CommandBot._gen_kwargs_from_msg(cmd, '/cmd int_arg=1'),
            {**cmd_defaults, 'int_arg': 1},
        )

    def test_parse_args_partial_defaults(self):
        self.assertEqual(
            CommandBot._gen_kwargs_from_msg(cmd, '/cmd 1 0'),
            {**cmd_defaults, 'int_arg': 1, 'float_arg': 0.0},
        )

        self.assertEqual(
            CommandBot._gen_kwargs_from_msg(cmd, '/cmd int_arg=1 float_arg=0'),
            {**cmd_defaults, 'int_arg': 1, 'float_arg': 0.0},
        )

        self.assertEqual(
            CommandBot._gen_kwargs_from_msg(cmd, '/cmd float_arg=0 int_arg=1'),
            {**cmd_defaults, 'int_arg': 1, 'float_arg': 0.0},
        )

        self.assertEqual(
            CommandBot._gen_kwargs_from_msg(cmd, '/cmd 1 bool_arg=False'),
            {**cmd_defaults, 'int_arg': 1, 'bool_arg': False},
        )

    def test_parse_args_bad_type(self):
        with self.assertRaisesRegex(BadArg, 'float'):
            CommandBot._gen_kwargs_from_msg(cmd, '/cmd 1  asd   some case_two')

        with self.assertRaisesRegex(BadArg, 'int'):
            CommandBot._gen_kwargs_from_msg(cmd, '/cmd qwe  1   some case_two')

        with self.assertRaisesRegex(BadArg, 'bool'):
            CommandBot._gen_kwargs_from_msg(
                cmd, '/cmd 1 1 some case_two some not_bool',
            )

        with self.assertRaisesRegex(BadArg, 'ExampleEnum'):
            CommandBot._gen_kwargs_from_msg(cmd, '/cmd 1  1   some case  ')

        with self.assertRaisesRegex(BadArg, 'F'):
            CommandBot._gen_kwargs_from_msg(
                cmd, '/cmd 1  1   some case_two some false asd'
            )

        with self.assertRaisesRegex(BadArg, 'no value for arg'):
            CommandBot._gen_kwargs_from_msg(cmd, '/cmd')

        with self.assertRaisesRegex(
            BadArg, 'positional arguments after key-value arguments'
        ):
            CommandBot._gen_kwargs_from_msg(cmd, '/cmd int_arg=1 1')

        with self.assertRaisesRegex(BadArg, 'no value for arg'):
            CommandBot._gen_kwargs_from_msg(cmd, '/cmd bool_arg=true')

        with self.assertRaisesRegex(BadArg, 'argument with name'):
            CommandBot._gen_kwargs_from_msg(cmd, '/cmd not_existing_arg=true')

    def test_check_args(self):
        CommandBot._check_args(cmd)

    def test_bot_create(self):
        bot = CommandBot(token='test')
        bot.command('cmd')(cmd)
        bot.register_help()

    def test_bot_bad_default(self):
        def bad_cmd(env: MessageEnv, a: int = '1'):  # type: ignore
            pass

        with self.assertRaises(ImproperlyConfigured):
            bot = CommandBot(token='test')
            bot.command('cmd')(bad_cmd)

        def bad_cmd_custom(env: MessageEnv, a: F = '1'):  # type: ignore
            pass

        with self.assertRaises(ImproperlyConfigured):
            bot = CommandBot(token='test')
            bot.command('cmd')(bad_cmd_custom)

    def test_bot_bad_bad_param_type(self):
        def bad_cmd(env: MessageEnv, a: Exception):
            pass

        with self.assertRaises(ImproperlyConfigured):
            bot = CommandBot(token='test')
            bot.command('cmd')(bad_cmd)

    def test_bot_decorator(self):
        def decorator(handler: Handler) -> Handler:
            def decorated(b: Bot, e: Event):
                print("decorated func")
                handler(b, e)

            return decorated

        bot = CommandBot(token='test', decorators=[decorator])
        bot.command('cmd')(cmd)

    def test_format_error_message(self):
        self.assertEqual(
            CommandBot._format_error_message('user', 'error'),
            'ERROR: user=user\n\nerror',
        )

        self.assertEqual(
            CommandBot._format_error_message('user', lambda: 'error'),
            'ERROR: user=user\n\nerror',
        )

    def gen_log_mock(self) -> Tuple[Mock, List[str]]:
        log_mock, log = Mock(), []
        log_mock.side_effect = lambda msg: log.append(msg)
        return log_mock, log

    def test_access_log(self):
        def access_regex(user: str, cmd: str) -> re.Pattern:
            return re.compile(
                r'\[ACCESS\] {} {} elapsed=\d+\.\d{{3}}s'
                .format(re.escape(user), re.escape(cmd)),
            )

        log_mock, log = self.gen_log_mock()
        log_error_mock = Mock()
        CommandBot._access_log(
            log_mock, log_error_mock,
            '[user]@[chat]', '/cmd',
            lambda: None,
        )
        self.assertEqual(log_mock.call_count, 2)
        self.assertEqual(log[0], '[ACCESS] [user]@[chat] /cmd')
        self.assertRegex(log[1], access_regex('[user]@[chat]', '/cmd'))
        log_error_mock.assert_not_called()

        log_mock, log = self.gen_log_mock()
        log_error_mock = Mock()
        CommandBot._access_log(
            log_mock, log_error_mock,
            '[user]@[chat]', 'hello',
            lambda: None,
        )
        self.assertEqual(log_mock.call_count, 2)
        self.assertEqual(log[0], '[ACCESS] [user]@[chat] {not a path}')
        self.assertRegex(log[1], access_regex('[user]@[chat]', '{not a path}'))
        log_error_mock.assert_not_called()

        log_mock, log = self.gen_log_mock()
        log_error_mock = Mock()
        exc = Exception()

        def raise_exc():
            raise exc
        CommandBot._access_log(
            log_mock, log_error_mock,
            '[user]@[chat]', '/cmd',
            raise_exc,
        )
        self.assertEqual(log[0], '[ACCESS] [user]@[chat] /cmd')
        self.assertRegex(log[1], access_regex('[user]@[chat]', '/cmd'))
        log_error_mock.assert_called_once_with('[user]@[chat]', exc)

    def test_command_args(self):
        send_mock = Mock()
        CommandBot._command_args(
            send_mock, '/cmd', lambda e: 'response message',
            MessageEnv(None, None, 'user'), '/cmd',  # type: ignore
        )
        send_mock.assert_called_once_with('response message')

        send_mock = Mock()

        def test_cmd(env: MessageEnv, i: int) -> str:
            return ''
        CommandBot._command_args(
            send_mock, '/cmd', test_cmd,
            MessageEnv(None, None, 'user'), '/cmd',  # type: ignore
        )
        send_mock.assert_called_once()

        send_mock = Mock()

        def test_raise(env: MessageEnv) -> str:
            raise Exception('exception')
        with self.assertRaisesRegex(Exception, 'exception'):
            CommandBot._command_args(
                send_mock, '/cmd', test_raise,
                MessageEnv(None, None, 'user'), '/cmd',  # type: ignore
            )
        send_mock.assert_called_once_with('some error occurred')


if __name__ == '__main__':
    unittest.main()
