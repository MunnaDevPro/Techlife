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
    
    # Use negative lookbehind to ensure we don't match :class="..."
    return re.sub(r'(?<!:)class="([^"]+)"', replace_class, content)

def fix_alpine_class_bindings(content):
    def replace_alpine_class(match):
        # We need to add ! to literal class names inside :class bindings
        # e.g., 'bg-blue-500' -> '!bg-blue-500'
        # This is tricky because it's JS syntax. We'll just replace known utility prefixes
        # For simplicity, let's just do a basic replace for this specific project.
        inner = match.group(1)
        # Find single quoted strings and prefix the tailwind classes inside them
        def replace_quotes(m2):
            classes = m2.group(1).split()
            prefixed = []
            for c in classes:
                if not c or c.startswith('!'):
                    prefixed.append(c)
                elif ':' in c:
                    parts = c.split(':')
                    prefixed.append(':'.join(parts[:-1]) + ':!' + parts[-1])
                else:
                    prefixed.append(f'!{c}')
            return "'" + ' '.join(prefixed) + "'"
        
        fixed_inner = re.sub(r"'([^']+)'", replace_quotes, inner)
        return ':class="' + fixed_inner + '"'
        
    return re.sub(r':class="([^"]+)"', replace_alpine_class, content)

files = ['templates/dashboard/site_config/footer.html', 'templates/dashboard/site_config/maintenance.html']
for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Prefix regular class attributes
    content = prefix_classes(content)
    # Prefix classes inside Alpine :class bindings
    content = fix_alpine_class_bindings(content)
    
    # Standardize blue to indigo
    content = content.replace('!blue-', '!indigo-')
    content = content.replace('!cursor-pointer', 'cursor-pointer') # avoid double
    content = content.replace('cursor-pointer', '!cursor-pointer') # standardise
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
print('Done!')
