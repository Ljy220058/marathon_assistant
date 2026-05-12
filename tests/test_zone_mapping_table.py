from marathon_qa_assistant.ui.ui_config import build_zone_mapping_table


def test_build_zone_mapping_table_renders_all_nine_zones():
    hr_zones = {f"Z{i}": f"{100 + i} bpm" for i in range(1, 10)}
    pace_zones = {f"Z{i}": f"{i}:00/km" for i in range(1, 10)}

    table = build_zone_mapping_table(hr_zones, pace_zones)

    assert "**Z1**" in table
    assert "**Z9**" in table
    assert table.count("| **Z") == 9
    assert "101" in table
    assert "9:00/km" in table


def test_build_zone_mapping_table_falls_back_for_missing_values():
    table = build_zone_mapping_table({"Z1": "120 bpm"}, {"Z1": "6:00/km"})

    assert "| **Z1** | 120 | 6:00/km |" in table
    assert "| **Z9** | - | - |" in table
