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
    implicit_str_arg='test_str',  # optional
    bool_arg: bool = True,
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
            implicit_str_arg: str = test_str
            bool_arg: True|False = True''')

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
            implicit_str_arg: str = test_str
            bool_arg: True|False = True

        /cmd_alias
          your function help message
          args:
            int_arg: int
            float_arg: float = 1.0
            str_arg: str = test_str
            enum_arg: case_one|case_two = case_one
            implicit_str_arg: str = test_str
            bool_arg: True|False = True''')

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
            'implicit_str_arg': 'some',
            'enum_arg': ExampleEnum.case_two,
            'bool_arg': False,
        }

        self.assertEqual(
            CommandBot._get_kwargs_from_msg(
                cmd, '/cmd 1  0   some case_two some False',
            ),
            expected,
        )

        self.assertEqual(
            CommandBot._get_kwargs_from_msg(
                cmd,
                '/cmd int_arg=1  float_arg=0   str_arg=some '
                'enum_arg=case_two implicit_str_arg=some bool_arg=False',
            ),
            expected,
        )

        self.assertEqual(
            CommandBot._get_kwargs_from_msg(
                cmd,
                '/cmd '
                'enum_arg=case_two implicit_str_arg=some bool_arg=False '
                'int_arg=1  float_arg=0   str_arg=some ',
            ),
            expected,
        )

    def test_parse_args_defaults(self):
        expected = {
            'int_arg': 1,
            'float_arg': 1.0,
            'str_arg': 'test_str',
            'implicit_str_arg': 'test_str',
            'enum_arg': ExampleEnum.case_one,
            'bool_arg': True,
        }

        self.assertEqual(
            CommandBot._get_kwargs_from_msg(cmd, '/cmd 1'),
            expected,
        )

        self.assertEqual(
            CommandBot._get_kwargs_from_msg(cmd, '/cmd int_arg=1'),
            expected,
        )

    def test_parse_args_partial_defaults(self):
        expected = {
            'int_arg': 1,
            'float_arg': 0.0,
            'str_arg': 'test_str',
            'implicit_str_arg': 'test_str',
            'enum_arg': ExampleEnum.case_one,
            'bool_arg': True,
        }

        self.assertEqual(
            CommandBot._get_kwargs_from_msg(cmd, '/cmd 1 0'),
            expected,
        )

        self.assertEqual(
            CommandBot._get_kwargs_from_msg(cmd, '/cmd int_arg=1 float_arg=0'),
            expected,
        )

        self.assertEqual(
            CommandBot._get_kwargs_from_msg(cmd, '/cmd float_arg=0 int_arg=1'),
            expected,
        )

        self.assertEqual(
            CommandBot._get_kwargs_from_msg(cmd, '/cmd 1 bool_arg=False'),
            {
                'int_arg': 1,
                'float_arg': 1.0,
                'str_arg': 'test_str',
                'implicit_str_arg': 'test_str',
                'enum_arg': ExampleEnum.case_one,
                'bool_arg': False,
            },
        )

    def test_parse_args_bad_type(self):
        with self.assertRaisesRegex(BadArg, 'float'):
            CommandBot._get_kwargs_from_msg(cmd, '/cmd 1  asd   some case_two')

        with self.assertRaisesRegex(BadArg, 'int'):
            CommandBot._get_kwargs_from_msg(cmd, '/cmd qwe  1   some case_two')

        with self.assertRaisesRegex(BadArg, 'bool'):
            CommandBot._get_kwargs_from_msg(
                cmd, '/cmd 1 1 some case_two some not_bool',
            )

        with self.assertRaisesRegex(BadArg, 'ExampleEnum'):
            CommandBot._get_kwargs_from_msg(cmd, '/cmd 1  1   some case  ')

        with self.assertRaisesRegex(BadArg, 'no value for arg'):
            CommandBot._get_kwargs_from_msg(cmd, '/cmd')

        with self.assertRaisesRegex(
            BadArg, 'positional arguments after key-value arguments'
        ):
            CommandBot._get_kwargs_from_msg(cmd, '/cmd int_arg=1 1')

        with self.assertRaisesRegex(BadArg, 'no value for arg'):
            CommandBot._get_kwargs_from_msg(cmd, '/cmd bool_arg=true')

        with self.assertRaisesRegex(BadArg, 'argument with name'):
            CommandBot._get_kwargs_from_msg(cmd, '/cmd not_existing_arg=true')

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
