"""
Script to compile .po translation files to .mo files.
This is a workaround for systems without GNU gettext tools installed.
"""
import os
import struct
import array

def generate_mo_file(po_file_path, mo_file_path):
    """
    Compile a .po file to .mo file format with proper UTF-8 encoding.
    This is a simple implementation for basic translation needs.
    """
    import codecs

    # Read the .po file with explicit UTF-8 encoding
    messages = {}
    current_msgid = None
    current_msgstr = None
    in_msgid = False
    in_msgstr = False

    with codecs.open(po_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # Handle msgid
            if line.startswith('msgid '):
                if current_msgid is not None and current_msgstr is not None:
                    messages[current_msgid] = current_msgstr
                current_msgid = line[7:-1]  # Remove 'msgid "' and '"'
                in_msgid = True
                in_msgstr = False
                current_msgstr = None

            # Handle msgstr
            elif line.startswith('msgstr '):
                current_msgstr = line[8:-1]  # Remove 'msgstr "' and '"'
                in_msgid = False
                in_msgstr = True

            # Handle continuation lines
            elif line.startswith('"') and line.endswith('"'):
                text = line[1:-1]
                if in_msgid:
                    current_msgid += text
                elif in_msgstr:
                    current_msgstr += text

        # Add the last message
        if current_msgid is not None and current_msgstr is not None:
            messages[current_msgid] = current_msgstr

    # IMPORTANT: Add a proper header entry for UTF-8 encoding
    header = (
        'Project-Id-Version: ProGestock 1.0\\n'
        'Report-Msgid-Bugs-To: \\n'
        'POT-Creation-Date: 2025-11-08 12:00+0000\\n'
        'PO-Revision-Date: 2025-11-08 12:00+0000\\n'
        'Last-Translator: ProGestock Team\\n'
        'Language-Team: \\n'
        'MIME-Version: 1.0\\n'
        'Content-Type: text/plain; charset=UTF-8\\n'
        'Content-Transfer-Encoding: 8bit\\n'
    )

    # Add header as empty string key
    messages_with_header = {'': header}
    messages_with_header.update(messages)

    # Build .mo file format
    # MO file format: https://www.gnu.org/software/gettext/manual/html_node/MO-Files.html
    keys = sorted(messages_with_header.keys())
    offsets = []
    ids = b''
    strs = b''

    for key in keys:
        # Encode with UTF-8
        msg_id = key.encode('utf-8')
        msg_str = messages_with_header[key].encode('utf-8')
        offsets.append((len(ids), len(msg_id), len(strs), len(msg_str)))
        ids += msg_id + b'\x00'
        strs += msg_str + b'\x00'

    # Generate the header
    keystart = 7 * 4 + 16 * len(keys)
    valuestart = keystart + len(ids)

    # Magic number (little-endian)
    output = struct.pack('<Iiiiiii',
                        0x950412de,          # Magic number
                        0,                   # File format revision
                        len(keys),           # Number of entries
                        7 * 4,               # Start of key index
                        7 * 4 + 8 * len(keys),  # Start of value index
                        0, 0)                # Size and offset of hash table

    # Generate key index and value index (little-endian)
    for o1, l1, o2, l2 in offsets:
        output += struct.pack('<ii', l1, o1 + keystart)
    for o1, l1, o2, l2 in offsets:
        output += struct.pack('<ii', l2, o2 + valuestart)

    # Add the actual translations
    output += ids + strs

    # Write the .mo file
    with open(mo_file_path, 'wb') as f:
        f.write(output)

    print(f"[OK] Compiled {po_file_path} -> {mo_file_path}")
    print(f"     Total translations: {len(keys)} (including header)")


if __name__ == '__main__':
    import sys

    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Compile English translations
    en_po = os.path.join(base_dir, 'locale', 'en', 'LC_MESSAGES', 'django.po')
    en_mo = os.path.join(base_dir, 'locale', 'en', 'LC_MESSAGES', 'django.mo')

    # Compile French translations
    fr_po = os.path.join(base_dir, 'locale', 'fr', 'LC_MESSAGES', 'django.po')
    fr_mo = os.path.join(base_dir, 'locale', 'fr', 'LC_MESSAGES', 'django.mo')

    print("\nCompiling translation files...\n")

    if os.path.exists(en_po):
        generate_mo_file(en_po, en_mo)
    else:
        print(f"[ERROR] English .po file not found: {en_po}")

    if os.path.exists(fr_po):
        generate_mo_file(fr_po, fr_mo)
    else:
        print(f"[ERROR] French .po file not found: {fr_po}")

    print("\nTranslation compilation complete!\n")
