from pathlib import Path

from icons import GLYPHS
from modules import ALL_MODULES, cs2_opt
from modules.backup import normalize_effects


def noop(*args, **kwargs):
    return None


def test_all_module_actions_follow_contract():
    required = {"name", "desc", "run", "icon", "risk", "irreversible", "effects"}

    for module in [*ALL_MODULES, cs2_opt]:
        category = module.get_category(noop, noop, noop)
        assert isinstance(category, dict), module.__name__
        assert "title" in category
        assert isinstance(category.get("actions"), list)
        for action in category["actions"]:
            assert required <= action.keys(), (module.__name__, action)
            assert action["risk"] in {"red", "yellow", "blue"}
            assert action["icon"] in GLYPHS, (module.__name__, action["icon"])
            assert callable(action["run"])
            normalize_effects(action["effects"])


def test_legacy_category_key_is_absent_from_modules():
    modules_dir = Path(__file__).parents[1] / "modules"
    legacy_name = "tracked" + "_keys"
    matches = [path for path in modules_dir.glob("*.py") if legacy_name in path.read_text(encoding="utf-8")]
    assert matches == []
