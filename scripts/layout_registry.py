# scripts/layout_registry.py

from dataclasses import dataclass

@dataclass(frozen=True)
class LayoutConfig:
    name: str
    paper_option: str
    geometry_options: str
    meta_spacing: str
    block_spacing: str
    admin_spacing: str
    heading_size: str
    array_stretch: float


_LAYOUTS = {}

def register_layout(layout: LayoutConfig):
    if layout.name in _LAYOUTS:
        raise ValueError(f"Layout '{layout.name}' already registered.")
    _LAYS = _LAYOUTS  # local alias
    _LAYS[layout.name] = layout


def get_layout(name: str) -> LayoutConfig:
    if name not in _LAYOUTS:
        raise ValueError(f"Unknown layout: {name}")
    return _LAYOUTS[name]


def available_layouts():
    return list(_LAYOUTS.keys())