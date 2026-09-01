from WinBoostGUI import plural


def test_plural_russian_action_forms():
    forms = ("действие", "действия", "действий")
    expected = {
        1: "действие",
        2: "действия",
        4: "действия",
        5: "действий",
        11: "действий",
        14: "действий",
        21: "действие",
        22: "действия",
        25: "действий",
        101: "действие",
        111: "действий",
    }

    assert {number: plural(number, *forms) for number in expected} == expected
