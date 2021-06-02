import enum
import unittest
from textwrap import dedent

from bot.bot import Bot, Event

from mailru_im_command_bot import CommandBot, MessageEnv
from mailru_im_command_bot.command_bot import (
    BadArg, Handler, ImproperlyConfigured,
)


class ExampleEnum(enum.Enum):
    case_one = 1
    case_two = 2


def cmd(
    env: MessageEnv,
    int_arg: int,  # required
    float_arg: float = 1.0,  # optional
    str_arg: str = 'test_str',  # optional
    enum_arg: ExampleEnum = ExampleEnum.case_one,  # optional
    str_arg2='test_str',  # optional
) -> str:
    """your function help message"""
    ...
    return 'your result'


class Tests(unittest.TestCase):
    def test_func_help(self):
        expected = dedent('''\
        /cmd
          your function help message
          args:
            int_arg: int
            float_arg: float = 1.0
            str_arg: str = test_str
            enum_arg: case_one|case_two = case_one
            str_arg2: str = test_str''')

        help_msg = CommandBot._gen_function_help('cmd', cmd)

        self.assertEqual(help_msg, expected)

    def test_help(self):
        expected = dedent('''\
        my help msg

        list of commands:
        /cmd
          your function help message
          args:
            int_arg: int
            float_arg: float = 1.0
            str_arg: str = test_str
            enum_arg: case_one|case_two = case_one
            str_arg2: str = test_str

        /cmd_alias
          your function help message
          args:
            int_arg: int
            float_arg: float = 1.0
            str_arg: str = test_str
            enum_arg: case_one|case_two = case_one
            str_arg2: str = test_str''')

        help_msg = CommandBot._gen_help('my help msg', [
            ('cmd', cmd),
            ('cmd_alias', cmd),
        ])

        self.assertEqual(help_msg, expected)

    def test_parse_args(self):
        expected = {
            'int_arg': 1,
            'float_arg': 0.0,
            'str_arg': 'some',
            'str_arg2': 'some',
            'enum_arg': ExampleEnum.case_two,
        }

        kwargs = CommandBot._get_kwargs_from_msg(
            cmd, '/cmd 1  0   some case_two some ',
        )

        self.assertEqual(kwargs, expected)

    def test_parse_args_defaults(self):
        expected = {
            'int_arg': 1,
            'float_arg': 1.0,
            'str_arg': 'test_str',
            'str_arg2': 'test_str',
            'enum_arg': ExampleEnum.case_one,
        }

        kwargs = CommandBot._get_kwargs_from_msg(
            cmd, '/cmd 1',
        )

        self.assertEqual(kwargs, expected)

    def test_parse_args_partial_defaults(self):
        expected = {
            'int_arg': 1,
            'float_arg': 0.0,
            'str_arg': 'test_str',
            'str_arg2': 'test_str',
            'enum_arg': ExampleEnum.case_one,
        }

        kwargs = CommandBot._get_kwargs_from_msg(
            cmd, '/cmd 1 0',
        )

        self.assertEqual(kwargs, expected)

    def test_parse_args_bad_type(self):
        with self.assertRaisesRegex(BadArg, 'float'):
            CommandBot._get_kwargs_from_msg(
                cmd, '/cmd 1  asd   some case_two  ',
            )

        with self.assertRaisesRegex(BadArg, 'int'):
            CommandBot._get_kwargs_from_msg(
                cmd, '/cmd qwe  1   some case_two  ',
            )

        with self.assertRaisesRegex(BadArg, 'ExampleEnum'):
            CommandBot._get_kwargs_from_msg(
                cmd, '/cmd 1  1   some case  ',
            )

        with self.assertRaisesRegex(BadArg, 'wrong argument number'):
            CommandBot._get_kwargs_from_msg(
                cmd, '/cmd',
            )

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


if __name__ == '__main__':
    unittest.main()
