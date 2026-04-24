from irc_parser import parse_irc_line


def test_parse_433_numeric_reply():
    parsed = parse_irc_line(":server 433 * Terminator :Nickname is already in use")

    assert parsed["command"] == "433"
