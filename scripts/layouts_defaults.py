# scripts/layouts_default.py

from scripts.layout_registry import LayoutConfig, register_layout

register_layout(
    LayoutConfig(
        name="a4",
        paper_option="a4paper",
        geometry_options="paperwidth=210mm,inner=27mm,outer=20mm,top=10mm,headsep=7mm,includehead,includefoot, footskip=18mm, ",
        meta_spacing=r"\addvspace{10pt}",
        block_spacing=r"\addvspace{12pt}",
        admin_spacing=r"\addvspace{\bigskipamount}",
        heading_size=r"\Large",
        array_stretch=1.2
    )
)

register_layout(
    LayoutConfig(
        name="a5",
        paper_option="a5paper",
        geometry_options="paperwidth=148mm,paperheight=210mm,inner=15mm,outer=10mm,top=7mm,headsep=5mm,includehead,includefoot, footskip=18mm,",
        meta_spacing=r"\addvspace{4pt}",
        block_spacing=r"\addvspace{6pt}",
        admin_spacing=r"\addvspace{\medskipamount}",
        heading_size=r"\large",
        array_stretch=1.1
    )
)
