"""
STAGE 6a: Document Renderer
Input: Stage 5 JSON
Output: Human-readable HTML (easy to print to PDF)
"""
from jinja2 import Template
import json
import os

HTML_TEMPLATE = """
<html>
<head><style>
    body { font-family: sans-serif; line-height: 1.6; margin: 40px; }
    .header { border-bottom: 2px solid #333; }
    .comp-box { border: 1px solid #ccc; padding: 10px; margin: 10px 0; }
</style></head>
<body>
    <div class="header">
        <h1>{{ course_code }}: {{ syllabus_data.metadata.course_title }}</h1>
        <p>Category: {{ syllabus_data.metadata.category }} | Credits: {{ syllabus_data.metadata.c }}</p>
    </div>
    <h2>Course Content</h2>
    {% for key, comp in syllabus_data.articulation.items() %}
    <div class="comp-box">
        <h3>Component: {{ key }} ({{ comp.contact_hours }} Hours)</h3>
        <ul>{% for item in comp.content_summary %}<li>{{ item }}</li>{% endfor %}</ul>
    </div>
    {% endfor %}
</body>
</html>
"""

def render_syllabus(json_path, output_dir="rendered_syllabi"):
    os.makedirs(output_dir, exist_ok=True)
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    template = Template(HTML_TEMPLATE)
    html_out = template.render(data)
    
    filename = os.path.basename(json_path).replace(".json", ".html")
    with open(os.path.join(output_dir, filename), 'w') as f:
        f.write(html_out)
    print(f"📄 Rendered: {filename}")