import yaml

def yaml_frontmatter(data: dict) -> str:
    """
    Generates a YAML frontmatter block.
    """
    return "---\n" + yaml.dump(data, default_flow_style=False) + "---\n"

def escape_markdown(text: str) -> str:
    """
    Escapes basic markdown characters.
    """
    # Simply escaping pipe for table safety
    if not text: return ""
    return str(text).replace("|", "\\|")
