#!/usr/bin/env python3
"""
Generate 4 Word documents containing all source code under the src/ directory.
Each file's code is clearly separated with a heading showing the file path.

- Part 1: Table of Contents + first quarter of source files
- Part 2: Second quarter of source files
- Part 3: Third quarter of source files
- Part 4: Fourth quarter of source files
"""

import os
import sys
import math
from pathlib import Path

try:
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
except ImportError:
    print("ERROR: python-docx is not installed. Please run: pip3 install python-docx")
    sys.exit(1)

# File extensions to include as source code
SOURCE_EXTENSIONS = {
    '.py', '.cpp', '.hpp', '.h', '.c', '.cc', '.cxx',
    '.yaml', '.yml', '.json', '.xml', '.txt', '.md',
    '.launch', '.launch.py', '.msg', '.srv', '.action',
    '.xacro', '.sdf', '.rviz', '.lua', '.cfg', '.ini',
    '.toml', '.cmake', '.sh', '.urdf', '.world', '.pgm',
    '.mtl', '.obj', '.csv', '.gitkeep', '.gitignore',
    '.clang-format', '.dockerignore', '.editorconfig',
}

# Files to skip (binary or non-source)
SKIP_FILES = {
    '.gitkeep',
}

# Binary extensions to skip
BINARY_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico',
    '.pdf', '.zip', '.tar', '.gz', '.bz2', '.7z',
    '.so', '.a', '.o', '.dll', '.dylib', '.exe',
    '.pyc', '.pyo', '.class', '.jar',
    '.woff', '.woff2', '.ttf', '.otf', '.eot',
    '.mp3', '.mp4', '.avi', '.mov', '.wav',
    '.db', '.sqlite', '.sqlite3',
}

# Directories to skip entirely
SKIP_DIRS = {
    'build', 'devel', 'install', 'log', '.git',
    '__pycache__', '.catkin_tools', '.vscode',
}


def is_source_file(filepath: Path) -> bool:
    """Check if a file should be included as source code."""
    name = filepath.name
    if name in SKIP_FILES:
        return False

    ext = filepath.suffix.lower()
    if ext in BINARY_EXTENSIONS:
        return False

    # Include files with known source extensions
    if ext in SOURCE_EXTENSIONS:
        return True

    # Include common ROS2 files
    if name in {'CMakeLists.txt', 'package.xml', 'Dockerfile', 'Makefile'}:
        return True

    # Include files with no extension that are text-like
    if ext == '' and name not in SKIP_FILES:
        # Check if it's a text file by trying to read it
        try:
            with open(filepath, 'rb') as f:
                chunk = f.read(1024)
                # Check if it contains mostly printable ASCII/UTF-8
                try:
                    chunk.decode('utf-8')
                    return True
                except UnicodeDecodeError:
                    return False
        except Exception:
            return False

    return False


def read_file_content(filepath: Path) -> str:
    """Read file content as text, handling encoding issues."""
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'gbk', 'gb2312']
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, PermissionError):
            continue
        except Exception as e:
            print(f"  Warning: Could not read {filepath}: {e}")
            return ""
    return ""


def set_cell_shading(cell, color_hex):
    """Set background shading for a table cell."""
    shading_elm = OxmlElement('w:shd')
    shading_elm.set(qn('w:fill'), color_hex)
    shading_elm.set(qn('w:val'), 'clear')
    cell._tc.get_or_add_tcPr().append(shading_elm)


def add_code_block(doc, code_text, file_path):
    """Add a code block to the document with monospace font and background."""
    # Add a table with one cell to create a code block with background
    table = doc.add_table(rows=1, cols=1)
    table.style = 'Table Grid'
    cell = table.cell(0, 0)

    # Set cell shading to light gray
    set_cell_shading(cell, 'F2F2F2')

    # Clear default paragraph
    cell.paragraphs[0].clear()

    # Add code lines
    lines = code_text.split('\n')
    first = True
    for line in lines:
        if first:
            p = cell.paragraphs[0]
            first = False
        else:
            p = cell.add_paragraph()

        run = p.add_run(line if line else ' ')
        run.font.name = 'Courier New'
        run.font.size = Pt(8)
        # Set East Asian font as well
        r = run._element
        rPr = r.get_or_add_rPr()
        rFonts = rPr.find(qn('w:rFonts'))
        if rFonts is None:
            rFonts = OxmlElement('w:rFonts')
            rPr.append(rFonts)
        rFonts.set(qn('w:ascii'), 'Courier New')
        rFonts.set(qn('w:hAnsi'), 'Courier New')
        rFonts.set(qn('w:eastAsia'), 'Courier New')

        # Set paragraph spacing to minimal
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0

    # Add spacing after the code block
    doc.add_paragraph()


def create_document(title_text, subtitle_text):
    """Create a new document with title."""
    doc = Document()

    # Set default font
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)

    # Title
    title = doc.add_heading(title_text, level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Subtitle
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = sub.add_run(subtitle_text)
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    doc.add_paragraph()
    return doc


def add_file_section(doc, fpath, file_index, total_files):
    """Add a single file's code section to the document."""
    content = read_file_content(fpath)
    if not content:
        print(f"    (empty or unreadable, skipping)")
        return False

    # Add file path as heading
    heading_text = f"File {file_index}: {fpath}"
    doc.add_heading(heading_text, level=1)

    # Add file metadata
    meta = doc.add_paragraph()
    meta_run = meta.add_run(f"Path: {fpath}\nSize: {len(content)} bytes\nLines: {content.count(chr(10)) + 1}")
    meta_run.font.size = Pt(9)
    meta_run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

    # Add code block
    add_code_block(doc, content, str(fpath))
    return True


def main():
    src_dir = Path('src')
    if not src_dir.exists():
        print(f"ERROR: Directory '{src_dir}' does not exist.")
        sys.exit(1)

    # Collect all source files
    source_files = []
    for root, dirs, files in os.walk(src_dir):
        # Filter out skip directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for fname in sorted(files):
            fpath = Path(root) / fname
            if is_source_file(fpath):
                source_files.append(fpath)

    source_files.sort(key=lambda p: str(p))

    total_files = len(source_files)
    print(f"Found {total_files} source files to include.")

    # Split into 4 parts
    part_size = math.ceil(total_files / 4)
    parts = []
    for i in range(4):
        start = i * part_size
        end = min((i + 1) * part_size, total_files)
        if start < total_files:
            parts.append(source_files[start:end])

    print(f"Split into {len(parts)} parts:")
    for i, part in enumerate(parts):
        print(f"  Part {i+1}: {len(part)} files (files {i*part_size+1} to {i*part_size+len(part)})")

    # Generate Part 1 (with Table of Contents)
    print("\nGenerating Part 1 (with Table of Contents)...")
    doc1 = create_document(
        'Robot Source Code Documentation - Part 1',
        f'Source code from the src/ directory\nFiles 1 to {len(parts[0])} of {total_files} total'
    )

    # Table of contents for ALL files
    toc_heading = doc1.add_heading('Table of Contents (All Files)', level=1)
    for i, fpath in enumerate(source_files, 1):
        p = doc1.add_paragraph()
        run = p.add_run(f'{i}. {fpath}')
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

    doc1.add_page_break()

    # Add files for part 1
    for idx, fpath in enumerate(parts[0], 1):
        file_num = idx  # File numbers restart per part
        print(f"  [{idx}/{len(parts[0])}] Processing: {fpath}")
        add_file_section(doc1, fpath, file_num, total_files)

    doc1.save('src_source_code_part1.docx')
    print(f"Saved: src_source_code_part1.docx")

    # Generate Parts 2, 3, 4 (no table of contents)
    for part_idx in range(1, len(parts)):
        part_num = part_idx + 1
        print(f"\nGenerating Part {part_num}...")
        start_file = part_idx * part_size + 1
        end_file = part_idx * part_size + len(parts[part_idx])

        doc = create_document(
            f'Robot Source Code Documentation - Part {part_num}',
            f'Source code from the src/ directory\nFiles {start_file} to {end_file} of {total_files} total'
        )

        for idx, fpath in enumerate(parts[part_idx], 1):
            file_num = start_file + idx - 1  # Use global file number
            print(f"  [{idx}/{len(parts[part_idx])}] Processing: {fpath}")
            add_file_section(doc, fpath, file_num, total_files)

        output_name = f'src_source_code_part{part_num}.docx'
        doc.save(output_name)
        print(f"Saved: {output_name}")

    print(f"\nAll documents generated successfully!")
    print(f"Total files: {total_files}")
    for i, part in enumerate(parts):
        print(f"  Part {i+1}: {len(part)} files")


if __name__ == '__main__':
    main()