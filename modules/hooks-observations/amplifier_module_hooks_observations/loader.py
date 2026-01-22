"""Observer loading from bundle paths.

This module handles loading observer definitions from markdown files with YAML frontmatter,
similar to how agents are loaded in Amplifier.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ContextFile:
    """A resolved context file from an @-mention."""

    path: str
    content: str
    source_mention: str


@dataclass
class LoadedObserver:
    """A fully loaded observer definition with resolved @-mentions."""

    name: str
    description: str
    model: str
    timeout: int
    tools: list[str]
    instruction: str  # Markdown body (raw, @-mentions not yet resolved)
    context_files: list[ContextFile] = field(default_factory=list)

    def get_full_instruction(self) -> str:
        """Get instruction with resolved context files appended."""
        if not self.context_files:
            return self.instruction

        context_parts = []
        for cf in self.context_files:
            context_parts.append(f'<context_file path="{cf.path}">\n{cf.content}\n</context_file>')

        context_block = "\n\n".join(context_parts)
        return f"{self.instruction}\n\n---\n\n{context_block}"


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from markdown text.

    Args:
        text: Markdown text with optional YAML frontmatter

    Returns:
        Tuple of (frontmatter_dict, body_text)
    """
    import re

    import yaml

    pattern = r"^---\s*\n(.*?)\n---\s*\n?"
    match = re.match(pattern, text, re.DOTALL)

    if not match:
        return {}, text

    yaml_content = match.group(1)
    body = text[match.end() :]

    try:
        frontmatter = yaml.safe_load(yaml_content) or {}
    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse frontmatter YAML: {e}")
        frontmatter = {}

    return frontmatter, body


def parse_mentions(text: str) -> list[str]:
    """Extract @-mentions from text, excluding code blocks.

    Args:
        text: Text to parse for @-mentions

    Returns:
        List of mention strings (e.g., ["@bundle:path/file.md", "@local/file.md"])
    """
    import re

    # Remove code blocks first
    code_block_pattern = r"```[\s\S]*?```|`[^`]+`"
    text_without_code = re.sub(code_block_pattern, "", text)

    # Find @-mentions (word chars, colons, slashes, dots, hyphens)
    mention_pattern = r"@[\w:/.@-]+"
    mentions = re.findall(mention_pattern, text_without_code)

    return mentions


async def resolve_mentions(
    text: str,
    sources: dict[str, str],
    base_path: Path,
) -> list[ContextFile]:
    """Resolve @-mentions in text to their content.

    Args:
        text: Text containing @-mentions
        sources: Mapping of bundle names to their base paths
        base_path: Base path for relative file resolution

    Returns:
        List of resolved ContextFile objects
    """
    mentions = parse_mentions(text)
    context_files = []
    seen_paths: set[str] = set()

    for mention in mentions:
        # Strip the @ prefix
        ref = mention[1:]

        try:
            path = resolve_mention_path(ref, sources, base_path)
            if path and str(path) not in seen_paths and path.exists():
                seen_paths.add(str(path))
                content = path.read_text(encoding="utf-8")
                context_files.append(
                    ContextFile(
                        path=str(path),
                        content=content,
                        source_mention=mention,
                    )
                )
        except Exception as e:
            logger.debug(f"Could not resolve mention {mention}: {e}")

    return context_files


def resolve_mention_path(
    ref: str,
    sources: dict[str, str],
    base_path: Path,
) -> Path | None:
    """Resolve a mention reference to a file path.

    Patterns:
    - "bundle-name:path/file.md" → sources[bundle-name]/path/file.md
    - "path/file.md" → base_path/path/file.md

    Args:
        ref: Reference string (without @ prefix)
        sources: Mapping of bundle names to their base paths
        base_path: Base path for relative references

    Returns:
        Resolved Path or None if not resolvable
    """
    if ":" in ref:
        # Bundle reference: "bundle-name:path/file.md"
        parts = ref.split(":", 1)
        if len(parts) == 2:
            bundle_name, path_str = parts
            bundle_base = sources.get(bundle_name)
            if bundle_base:
                return Path(bundle_base) / path_str
            # Fallback: treat as relative path
            logger.debug(f"Bundle '{bundle_name}' not found in sources, treating as relative")

    # Relative reference
    path = base_path / ref
    if path.exists():
        return path

    # Try with .md extension
    path_md = base_path / f"{ref}.md"
    if path_md.exists():
        return path_md

    return None


def resolve_observer_path(
    observer_ref: str,
    sources: dict[str, str],
    base_path: Path,
) -> Path:
    """Resolve observer reference to file path.

    Patterns:
    - "bundle-name:observers/name" → sources[bundle-name]/observers/name.md
    - "observers/name" → base_path/observers/name.md

    Args:
        observer_ref: Observer reference string
        sources: Mapping of bundle names to their base paths
        base_path: Base path for relative references

    Returns:
        Resolved Path to observer file

    Raises:
        FileNotFoundError: If observer file cannot be found
    """
    if ":" in observer_ref:
        # Bundle reference
        parts = observer_ref.split(":", 1)
        if len(parts) == 2:
            bundle_name, obs_path = parts
            bundle_base = sources.get(bundle_name)
            if bundle_base:
                # Try exact path first
                path = Path(bundle_base) / obs_path
                if path.exists():
                    return path
                # Try with .md extension
                path_md = Path(bundle_base) / f"{obs_path}.md"
                if path_md.exists():
                    return path_md
                raise FileNotFoundError(
                    f"Observer not found: {observer_ref} (tried {path} and {path_md})"
                )
            raise FileNotFoundError(
                f"Bundle '{bundle_name}' not found in sources. "
                f"Available sources: {list(sources.keys())}"
            )

    # Relative reference
    path = base_path / observer_ref
    if path.exists():
        return path

    path_md = base_path / f"{observer_ref}.md"
    if path_md.exists():
        return path_md

    raise FileNotFoundError(f"Observer not found: {observer_ref} (tried {path} and {path_md})")


async def load_observer(
    observer_ref: str,
    sources: dict[str, str],
    base_path: Path,
) -> LoadedObserver:
    """Load an observer from a bundle reference.

    Args:
        observer_ref: "bundle:observers/name" or "observers/name" (relative)
        sources: Mapping of bundle names to their base paths
        base_path: Base path for relative references

    Returns:
        LoadedObserver with resolved @-mentions

    Raises:
        FileNotFoundError: If observer file cannot be found
        ValueError: If observer file is malformed
    """
    # 1. Resolve observer path
    path = resolve_observer_path(observer_ref, sources, base_path)
    logger.debug(f"Loading observer from: {path}")

    # 2. Parse markdown + frontmatter
    content = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)

    # 3. Extract observer config from frontmatter
    obs_config = frontmatter.get("observer", {})
    if not obs_config:
        raise ValueError(f"Observer file missing 'observer:' section: {path}")

    tools = frontmatter.get("tools", [])

    # 4. Resolve @-mentions in the body
    context_files = await resolve_mentions(body, sources, path.parent)

    # 5. Build LoadedObserver
    return LoadedObserver(
        name=obs_config.get("name", path.stem),
        description=obs_config.get("description", ""),
        model=obs_config.get("model", "claude-3-5-haiku-latest"),
        timeout=obs_config.get("timeout", 30),
        tools=tools,
        instruction=body.strip(),
        context_files=context_files,
    )
