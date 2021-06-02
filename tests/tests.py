import enum
import unittest
from textwrap import dedent

from mailru_im_command_bot import CommandBot, MessageEnv
from mailru_im_command_bot.command_bot import BadArg


class ExampleEnum(enum.Enum):
    case_one = 1
    case_two = 2


def cmd(
    env: MessageEnv,
    int_arg: int,  # required
    float_arg: float = 1.0,  # optional
    str_arg: str = 'test_str',  # optional
    enum_arg: ExampleEnum = ExampleEnum.case_one,  # optional
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
            enum_arg: case_one|case_two = case_one''')

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

        /cmd_alias
          your function help message
          args:
            int_arg: int
            float_arg: float = 1.0
            str_arg: str = test_str
            enum_arg: case_one|case_two = case_one''')

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
            'enum_arg': ExampleEnum.case_two,
        }

        kwargs = CommandBot._get_kwargs_from_msg(
            cmd, '/cmd 1  0   some case_two  ',
        )

        self.assertEqual(kwargs, expected)

    def test_parse_args_defaults(self):
        expected = {
            'int_arg': 1,
            'float_arg': 1.0,
            'str_arg': 'test_str',
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


if __name__ == '__main__':
    unittest.main()
