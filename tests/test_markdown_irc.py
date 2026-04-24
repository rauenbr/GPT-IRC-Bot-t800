from markdown_irc import convert_markdown_to_irc


def test_empty_text_returns_same_value():
    assert convert_markdown_to_irc("") == ""


def test_bold_markdown_to_irc_bold():
    assert convert_markdown_to_irc("isso é **importante**") == "isso é \x02importante\x02"


def test_underline_markdown_to_irc_underline():
    assert convert_markdown_to_irc("isso é __grave__") == "isso é \x1Fgrave\x1F"


def test_inline_code_to_irc_monospace():
    assert convert_markdown_to_irc("use `pytest -vv`") == "use \x11pytest -vv\x11"


def test_link_to_text_and_url():
    assert convert_markdown_to_irc("[OpenAI](https://openai.com)") == "OpenAI (https://openai.com)"


def test_heading_marker_removed():
    assert convert_markdown_to_irc("## Título") == "Título"


def test_bullet_normalized():
    assert convert_markdown_to_irc("- item") == "• item"


def test_latex_fraction_simplified():
    assert convert_markdown_to_irc(r"\frac{a}{b}") == "(a)/(b)"


def test_latex_sqrt_simplified():
    assert convert_markdown_to_irc(r"\sqrt{x}") == "√(x)"


def test_latex_symbols_replaced():
    assert convert_markdown_to_irc(r"a \neq b e x \leq y") == "a ≠ b e x ≤ y"


def test_power_two_and_three():
    assert convert_markdown_to_irc("x^2 + y^3") == "x² + y³"


def test_code_block_removes_fence():
    text = "```python\nprint('oi')\n```"
    assert convert_markdown_to_irc(text) == "print('oi')"
