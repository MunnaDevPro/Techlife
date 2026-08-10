import re

def prefix_classes(content):
    def replace_class(match):
        classes = match.group(1).split()
        prefixed = []
        for c in classes:
            c = c.strip()
            if not c or c.startswith('!') or c.startswith('{') or c.startswith('group') or c.startswith('peer') or (':' in c and c.split(':')[-1].startswith('!')):
                prefixed.append(c)
            elif ':' in c:
                parts = c.split(':')
                prefixed.append(':'.join(parts[:-1]) + ':!' + parts[-1])
            else:
                prefixed.append(f'!{c}')
        return 'class="' + ' '.join(prefixed) + '"'
    return re.sub(r'class="([^"]+)"', replace_class, content)

files = ['templates/dashboard/site_config/footer.html', 'templates/dashboard/site_config/maintenance.html']
for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    content = prefix_classes(content)
    content = content.replace('!blue-', '!indigo-')
    content = content.replace('!cursor-pointer', 'cursor-pointer') # avoid double
    content = content.replace('cursor-pointer', '!cursor-pointer') # standardise
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
print('Done!')
