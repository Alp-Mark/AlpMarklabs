"""
AlpMark Notion Sync
-------------------
Pulls phases, milestones, and tasks from your Notion workspace
and saves them to tasks.md in this workspace.

Usage:
    Set NOTION_TOKEN and NOTION_ROOT_PAGE_ID environment variables, then:
    .venv/bin/python notion_sync.py
"""

import os
from notion_client import Client
from datetime import datetime

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
ROOT_PAGE_ID = os.getenv("NOTION_ROOT_PAGE_ID", "36391c4ec32b804e9eaaf27c38c21614")

if not NOTION_TOKEN:
    raise ValueError("NOTION_TOKEN environment variable is not set")

notion = Client(auth=NOTION_TOKEN)


def get_plain_text(rich_text_array):
    """Extract plain text from Notion rich text array."""
    if not rich_text_array:
        return ""
    return "".join([t.get("plain_text", "") for t in rich_text_array])


def get_property_value(prop):
    """Extract value from a Notion property object."""
    if not prop:
        return ""
    ptype = prop.get("type", "")

    if ptype == "title":
        return get_plain_text(prop.get("title", []))
    elif ptype == "rich_text":
        return get_plain_text(prop.get("rich_text", []))
    elif ptype == "select":
        sel = prop.get("select")
        return sel.get("name", "") if sel else ""
    elif ptype == "multi_select":
        return ", ".join([s.get("name", "") for s in prop.get("multi_select", [])])
    elif ptype == "status":
        status = prop.get("status")
        return status.get("name", "") if status else ""
    elif ptype == "date":
        date = prop.get("date")
        if date:
            start = date.get("start", "")
            end = date.get("end", "")
            return f"{start} → {end}" if end else start
        return ""
    elif ptype == "checkbox":
        return "Yes" if prop.get("checkbox") else "No"
    elif ptype == "number":
        val = prop.get("number")
        return str(val) if val is not None else ""
    elif ptype == "url":
        return prop.get("url", "") or ""
    elif ptype == "email":
        return prop.get("email", "") or ""
    elif ptype == "people":
        people = prop.get("people", [])
        return ", ".join([p.get("name", "") for p in people])
    elif ptype == "relation":
        return f"{len(prop.get('relation', []))} linked"
    elif ptype == "formula":
        formula = prop.get("formula", {})
        ftype = formula.get("type", "")
        return str(formula.get(ftype, ""))
    elif ptype == "rollup":
        rollup = prop.get("rollup", {})
        rtype = rollup.get("type", "")
        if rtype == "number":
            return str(rollup.get("number", ""))
        elif rtype == "array":
            items = rollup.get("array", [])
            return str(len(items)) + " items"
        return ""
    return ""


def fetch_database(database_id, label="Database"):
    """Fetch all rows from a Notion database."""
    results = []
    cursor = None
    try:
        while True:
            kwargs = {"database_id": database_id}
            if cursor:
                kwargs["start_cursor"] = cursor
            response = notion.databases.query(**kwargs)
            results.extend(response.get("results", []))
            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")
        print(f"  Fetched {len(results)} rows from {label}")
    except Exception as e:
        print(f"  SKIPPED (no access): {label} — {e}")
        return None
    return results


def fetch_child_pages(block_id):
    """Recursively fetch child pages/databases under a block."""
    children = []
    cursor = None
    while True:
        kwargs = {"block_id": block_id}
        if cursor:
            kwargs["start_cursor"] = cursor
        response = notion.blocks.children.list(**kwargs)
        children.extend(response.get("results", []))
        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")
    return children


def rows_to_markdown_table(rows):
    """Convert Notion database rows to a markdown table."""
    if not rows:
        return "_No entries found._\n"

    # Collect all property names from rows (preserving order from first row)
    all_keys = []
    for row in rows:
        for k in row.get("properties", {}).keys():
            if k not in all_keys:
                all_keys.append(k)

    if not all_keys:
        return "_No properties found._\n"

    # Build rows
    table_rows = []
    for row in rows:
        props = row.get("properties", {})
        values = []
        for key in all_keys:
            val = get_property_value(props.get(key, {}))
            # Escape pipe characters for markdown tables
            val = val.replace("|", "\\|").replace("\n", " ")
            values.append(val)
        table_rows.append(values)

    # Build markdown table
    header = "| " + " | ".join(all_keys) + " |"
    separator = "| " + " | ".join(["---"] * len(all_keys)) + " |"
    body = "\n".join(["| " + " | ".join(row) + " |" for row in table_rows])

    return f"{header}\n{separator}\n{body}\n"


def build_markdown(root_id):
    """Walk the root page and build a full markdown document."""
    lines = []
    lines.append("# AlpMark - Notion Workspace Sync")
    lines.append(f"_Last synced: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n")
    lines.append("---\n")

    print("Fetching root page children...")
    children = fetch_child_pages(root_id)

    for block in children:
        btype = block.get("type", "")
        bid = block.get("id", "")

        if btype == "child_database":
            db_title = block.get("child_database", {}).get("title", "Unnamed Database")
            print(f"  Found database: {db_title}")
            lines.append(f"## {db_title}\n")
            rows = fetch_database(bid, label=db_title)
            if rows is None:
                lines.append("_⚠ No access — share this database with the AlpMark VSCode MCP integration in Notion._\n")
            else:
                lines.append(rows_to_markdown_table(rows))

        elif btype == "child_page":
            page_title = block.get("child_page", {}).get("title", "Unnamed Page")
            print(f"  Found page: {page_title}")
            lines.append(f"## {page_title}\n")

            # Check if there are nested databases inside this page
            sub_children = fetch_child_pages(bid)
            for sub_block in sub_children:
                sbtype = sub_block.get("type", "")
                sbid = sub_block.get("id", "")

                if sbtype == "child_database":
                    db_title = sub_block.get("child_database", {}).get("title", "Unnamed Database")
                    print(f"    Found nested database: {db_title}")
                    lines.append(f"### {db_title}\n")
                    rows = fetch_database(sbid, label=db_title)
                    if rows is None:
                        lines.append("_⚠ No access — share this database with the AlpMark VSCode MCP integration in Notion._\n")
                    else:
                        lines.append(rows_to_markdown_table(rows))

                elif sbtype == "child_page":
                    sub_page_title = sub_block.get("child_page", {}).get("title", "Unnamed Page")
                    lines.append(f"### {sub_page_title}\n")

        elif btype in ("heading_1", "heading_2", "heading_3"):
            text = get_plain_text(block.get(btype, {}).get("rich_text", []))
            level = {"heading_1": "#", "heading_2": "##", "heading_3": "###"}[btype]
            lines.append(f"{level} {text}\n")

        elif btype == "paragraph":
            text = get_plain_text(block.get("paragraph", {}).get("rich_text", []))
            if text:
                lines.append(f"{text}\n")

        elif btype == "bulleted_list_item":
            text = get_plain_text(block.get("bulleted_list_item", {}).get("rich_text", []))
            lines.append(f"- {text}")

        elif btype == "numbered_list_item":
            text = get_plain_text(block.get("numbered_list_item", {}).get("rich_text", []))
            lines.append(f"1. {text}")

        elif btype == "to_do":
            checked = block.get("to_do", {}).get("checked", False)
            text = get_plain_text(block.get("to_do", {}).get("rich_text", []))
            checkbox = "[x]" if checked else "[ ]"
            lines.append(f"- {checkbox} {text}")

        elif btype == "divider":
            lines.append("---\n")

    return "\n".join(lines)


def main():
    print("AlpMark Notion Sync")
    print("=" * 40)
    print(f"Root Page ID: {ROOT_PAGE_ID}")
    print()

    try:
        markdown_content = build_markdown(ROOT_PAGE_ID)

        output_path = "tasks.md"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        print()
        print("=" * 40)
        print(f"Saved to: {output_path}")
        print("Done!")

    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
