import re
with open('templates/dashboard/site_config/ads.html', 'r', encoding='utf-8') as f:
    content = f.read()

def repl(match):
    classes = match.group(1).split()
    new_classes = []
    for c in classes:
        # Don't prefix these special cases
        if c.startswith('!') or c.startswith('group') or c.startswith('peer') or '{' in c or '%' in c:
            new_classes.append(c)
        elif c in ['hidden', 'block', 'inline', 'inline-flex', 'inline-block', 'flex', 'grid', 'table', 'sr-only']:
            new_classes.append('!' + c)
        elif c.startswith('x-') or c.startswith('@'):
            new_classes.append(c)
        else:
            # Handle variants like hover:, focus:, sm:, md:, etc.
            if ':' in c:
                parts = c.split(':')
                # Add ! right after the last colon
                last = parts[-1]
                parts[-1] = '!' + last
                new_classes.append(':'.join(parts))
            else:
                new_classes.append('!' + c)
    return 'class="' + ' '.join(new_classes) + '"'

# Replace class attributes
content = re.sub(r'class=\s*"([^"]*)"', repl, content)

with open('templates/dashboard/site_config/ads.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('Replaced successfully')
