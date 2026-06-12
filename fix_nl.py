#!/usr/bin/env python3
filepath = 'templates/index.html'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Delete lines 1377-1388 (0-indexed: 1376-1387) and insert correct code
# Lines to delete: 1377,1378,1379,1380,1381,1382,1383,1384,1385,1386,1387,1388
del_start = 1376  # 0-indexed
del_end = 1388    # 0-indexed, exclusive

new_code = [
    "            if (msg.role === 'user') {\n",
    "                content += '\u3010\u7528\u6237\u3011\\n' + msg.content + '\\n\\n';\n",
    "            } else if (msg.role === 'assistant') {\n",
    "                content += '\u3010AI\u52a9\u624b\u3011\\n' + msg.content + '\\n\\n';\n",
    "            }\n",
]

lines[del_start:del_end] = new_code

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Done')
