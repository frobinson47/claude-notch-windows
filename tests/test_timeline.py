"""Tests for TimelineStrip widget."""

import pytest
from state_manager import ActiveTool, NotchConfig


def _make_tool(tool_name, config):
    """Create an ActiveTool from config lookup."""
    info = config.get_tool_info(tool_name)
    return ActiveTool(
        tool_name=tool_name,
        display_name=info['display_name'],
        category=info['category'],
        color=info['color'],
        pattern=info['pattern'],
        attention=info['attention'],
    )


class TestTimelineStrip:

    def test_empty_tools_hidden(self, notch_config, qapp):
        from overlay_window import TimelineStrip
        strip = TimelineStrip()
        strip.set_tools([], notch_config)
        assert not strip.isVisible()
        assert strip._segments == []

    def test_single_tool_one_segment(self, notch_config, qapp):
        from overlay_window import TimelineStrip
        strip = TimelineStrip()
        tools = [_make_tool('Read', notch_config)]
        strip.set_tools(tools, notch_config)
        assert strip.isVisible()
        assert len(strip._segments) == 1
        assert strip._segments[0][1] == 1  # weight

    def test_coalesce_consecutive_same_category(self, notch_config, qapp):
        from overlay_window import TimelineStrip
        strip = TimelineStrip()
        # Read and Glob are both 'observe' category; Write is 'create'
        tools = [_make_tool('Read', notch_config),
                 _make_tool('Glob', notch_config),
                 _make_tool('Write', notch_config)]
        strip.set_tools(tools, notch_config)
        assert len(strip._segments) == 2
        assert strip._segments[0][1] == 2  # Read+Glob coalesced
        assert strip._segments[1][1] == 1  # Write alone

    def test_different_categories_no_coalesce(self, notch_config, qapp):
        from overlay_window import TimelineStrip
        strip = TimelineStrip()
        # Read(observe), Write(create), Read(observe) — no adjacent duplicates
        tools = [_make_tool('Read', notch_config),
                 _make_tool('Write', notch_config),
                 _make_tool('Read', notch_config)]
        strip.set_tools(tools, notch_config)
        assert len(strip._segments) == 3

    def test_max_ten_tools(self, notch_config, qapp):
        from overlay_window import TimelineStrip
        strip = TimelineStrip()
        names = ['Read', 'Write', 'Bash', 'Glob', 'Grep',
                 'Edit', 'Read', 'Write', 'Bash', 'Glob']
        tools = [_make_tool(n, notch_config) for n in names]
        strip.set_tools(tools, notch_config)
        assert strip.isVisible()
        assert sum(w for _, w in strip._segments) == 10

    def test_segment_colors_match_config(self, notch_config, qapp):
        from overlay_window import TimelineStrip
        from PySide6.QtGui import QColor
        strip = TimelineStrip()
        tools = [_make_tool('Read', notch_config)]
        strip.set_tools(tools, notch_config)
        expected_rgb = notch_config.get_color_rgb(tools[0].color)
        seg_color = strip._segments[0][0]
        assert (seg_color.red(), seg_color.green(), seg_color.blue()) == expected_rgb
