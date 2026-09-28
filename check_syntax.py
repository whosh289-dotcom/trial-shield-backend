import re

with open('static/index.html', 'r') as f:
    content = f.read()

script_content = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if script_content:
    js = script_content.group(1)
    print("Backtick count:", js.count('`'))
    print("Single quote count:", js.count("'"))
