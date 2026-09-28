import re
with open('static/index.html', 'r') as f:
    content = f.read()
scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
if len(scripts) > 1:
    with open('test_script.js', 'w') as out:
        out.write(scripts[1])
