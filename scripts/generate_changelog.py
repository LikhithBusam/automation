#!/usr/bin/env python3
"""
Automated Changelog Generator

Generates changelog from git commits following conventional commits specification.
"""

import re
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Conventional commit types
COMMIT_TYPES = {
    "feat": {"title": "Features", "emoji": "✨"},
    "fix": {"title": "Bug Fixes", "emoji": "🐛"},
    "docs": {"title": "Documentation", "emoji": "📚"},
    "style": {"title": "Code Style", "emoji": "💅"},
    "refactor": {"title": "Code Refactoring", "emoji": "♻️"},
    "perf": {"title": "Performance Improvements", "emoji": "⚡"},
    "test": {"title": "Tests", "emoji": "✅"},
    "build": {"title": "Build System", "emoji": "🏗️"},
    "ci": {"title": "CI/CD", "emoji": "👷"},
    "chore": {"title": "Chores", "emoji": "🔧"},
    "revert": {"title": "Reverts", "emoji": "⏪"},
    "security": {"title": "Security", "emoji": "🔒"},
}

# Breaking change indicator
BREAKING_CHANGE = "💥 BREAKING CHANGES"


class ChangelogGenerator:
    """Generates changelog from git commits"""

    def __init__(self, repo_path: str = "."):
        """
        Initialize changelog generator

        Args:
            repo_path: Path to git repository
        """
        self.repo_path = Path(repo_path)

    def get_latest_tag(self) -> str:
        """Get the latest git tag"""
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            # No tags exist
            return ""

    def get_commits_since_tag(self, tag: str = "") -> List[str]:
        """
        Get commits since a specific tag

        Args:
            tag: Git tag to compare from (empty for all commits)

        Returns:
            List of commit messages
        """
        if tag:
            commit_range = f"{tag}..HEAD"
        else:
            commit_range = "HEAD"

        try:
            result = subprocess.run(
                ["git", "log", commit_range, "--pretty=format:%H|||%s|||%b|||%an|||%ae"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return [line for line in result.stdout.split("\n") if line]
        except subprocess.CalledProcessError as e:
            print(f"Error getting commits: {e}")
            return []

    def parse_commit(self, commit_line: str) -> Dict:
        """
        Parse a commit line into structured data

        Args:
            commit_line: Commit line from git log

        Returns:
            Dictionary with commit information
        """
        try:
            hash_id, subject, body, author, email = commit_line.split("|||")
        except ValueError:
            return None

        # Parse conventional commit format: type(scope): message
        # Examples: feat(api): add new endpoint
        #          fix: resolve bug in parser
        match = re.match(r"^(\w+)(?:\(([^)]+)\))?: (.+)$", subject)

        if match:
            commit_type, scope, message = match.groups()
        else:
            # Not a conventional commit, categorize as "chore"
            commit_type = "chore"
            scope = None
            message = subject

        # Check for breaking changes
        is_breaking = "BREAKING CHANGE:" in body or "!" in subject

        return {
            "hash": hash_id[:8],
            "type": commit_type.lower(),
            "scope": scope,
            "message": message,
            "body": body,
            "author": author,
            "email": email,
            "breaking": is_breaking,
        }

    def group_commits_by_type(self, commits: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group commits by type

        Args:
            commits: List of parsed commits

        Returns:
            Dictionary mapping commit type to list of commits
        """
        grouped = defaultdict(list)

        for commit in commits:
            if commit:
                commit_type = commit.get("type", "chore")
                grouped[commit_type].append(commit)

        return grouped

    def format_commit_line(self, commit: Dict) -> str:
        """
        Format a single commit line

        Args:
            commit: Commit dictionary

        Returns:
            Formatted commit line
        """
        scope = f"**{commit['scope']}**: " if commit["scope"] else ""
        breaking = "⚠️ " if commit["breaking"] else ""

        return f"- {breaking}{scope}{commit['message']} ([{commit['hash']}](../../commit/{commit['hash']}))"

    def generate_changelog_section(
        self, version: str, commits: List[Dict], date: str = None
    ) -> str:
        """
        Generate changelog section for a version

        Args:
            version: Version number
            commits: List of commits
            date: Release date (defaults to today)

        Returns:
            Formatted changelog section
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        grouped_commits = self.group_commits_by_type(commits)

        # Start changelog section
        lines = [
            f"## [{version}] - {date}",
            "",
        ]

        # Add breaking changes first if any
        breaking_changes = [c for c in commits if c and c.get("breaking")]
        if breaking_changes:
            lines.append(f"### {BREAKING_CHANGE}")
            lines.append("")
            for commit in breaking_changes:
                lines.append(self.format_commit_line(commit))
            lines.append("")

        # Add commits by type
        for commit_type in sorted(grouped_commits.keys()):
            if commit_type not in COMMIT_TYPES:
                continue

            type_info = COMMIT_TYPES[commit_type]
            type_commits = grouped_commits[commit_type]

            if type_commits:
                lines.append(f"### {type_info['emoji']} {type_info['title']}")
                lines.append("")
                for commit in type_commits:
                    lines.append(self.format_commit_line(commit))
                lines.append("")

        # Add contributors
        contributors = set(c["author"] for c in commits if c)
        if contributors:
            lines.append("### 👥 Contributors")
            lines.append("")
            for contributor in sorted(contributors):
                lines.append(f"- @{contributor}")
            lines.append("")

        return "\n".join(lines)

    def generate_changelog(
        self, version: str = None, output_file: str = "CHANGELOG.md"
    ) -> str:
        """
        Generate complete changelog

        Args:
            version: Version number (defaults to latest tag or 'Unreleased')
            output_file: Output file path

        Returns:
            Generated changelog content
        """
        # Get version info
        if version is None:
            latest_tag = self.get_latest_tag()
            version = latest_tag if latest_tag else "Unreleased"

        # Get commits
        latest_tag = self.get_latest_tag()
        commit_lines = self.get_commits_since_tag(latest_tag)

        # Parse commits
        commits = [self.parse_commit(line) for line in commit_lines]
        commits = [c for c in commits if c]  # Filter None

        if not commits:
            print(f"No commits found since {latest_tag or 'beginning'}")
            return ""

        # Generate changelog header
        changelog = [
            "# Changelog",
            "",
            "All notable changes to this project will be documented in this file.",
            "",
            "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),",
            "and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).",
            "",
        ]

        # Add new version section
        changelog_section = self.generate_changelog_section(version, commits)
        changelog.append(changelog_section)

        # Read existing changelog if it exists
        output_path = self.repo_path / output_file
        if output_path.exists():
            with open(output_path, "r") as f:
                existing_content = f.read()

            # Find where to insert new content (after header)
            lines = existing_content.split("\n")
            header_end = 0
            for i, line in enumerate(lines):
                if line.startswith("## ["):
                    header_end = i
                    break

            if header_end > 0:
                # Preserve header and prepend new section
                changelog = lines[:header_end] + [changelog_section] + lines[header_end:]
            else:
                # No existing sections, append
                changelog.extend(lines)

        # Write changelog
        content = "\n".join(changelog) if isinstance(changelog, list) else changelog
        with open(output_path, "w") as f:
            f.write(content)

        print(f"✅ Changelog generated: {output_path}")
        print(f"📝 Version: {version}")
        print(f"📊 Commits: {len(commits)}")

        return content

    def generate_release_notes(self, version: str) -> str:
        """
        Generate release notes for GitHub/GitLab releases

        Args:
            version: Version number

        Returns:
            Formatted release notes
        """
        latest_tag = self.get_latest_tag()
        commit_lines = self.get_commits_since_tag(latest_tag)
        commits = [self.parse_commit(line) for line in commit_lines]
        commits = [c for c in commits if c]

        grouped_commits = self.group_commits_by_type(commits)

        # Generate release notes
        notes = [f"# Release {version}", ""]

        # Highlights
        features = grouped_commits.get("feat", [])
        if features:
            notes.append("## 🎉 Highlights")
            notes.append("")
            for commit in features[:3]:  # Top 3 features
                notes.append(f"- {commit['message']}")
            notes.append("")

        # Breaking changes
        breaking_changes = [c for c in commits if c.get("breaking")]
        if breaking_changes:
            notes.append(f"## {BREAKING_CHANGE}")
            notes.append("")
            for commit in breaking_changes:
                notes.append(f"- {commit['message']}")
            notes.append("")

        # What's Changed
        notes.append("## 📝 What's Changed")
        notes.append("")
        for commit_type in ["feat", "fix", "perf", "security"]:
            if commit_type in grouped_commits:
                type_info = COMMIT_TYPES[commit_type]
                notes.append(f"### {type_info['emoji']} {type_info['title']}")
                notes.append("")
                for commit in grouped_commits[commit_type]:
                    notes.append(self.format_commit_line(commit))
                notes.append("")

        # Full Changelog
        notes.append("## 📋 Full Changelog")
        notes.append("")
        if latest_tag:
            notes.append(
                f"**Full Changelog**: https://github.com/yourusername/automaton/compare/{latest_tag}...{version}"
            )
        else:
            notes.append(
                f"**Full Changelog**: https://github.com/yourusername/automaton/commits/{version}"
            )

        return "\n".join(notes)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Generate changelog from git commits")
    parser.add_argument(
        "--version",
        "-v",
        help="Version number (defaults to latest tag or 'Unreleased')",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="CHANGELOG.md",
        help="Output file path (default: CHANGELOG.md)",
    )
    parser.add_argument(
        "--release-notes",
        "-r",
        action="store_true",
        help="Generate release notes instead of changelog",
    )
    parser.add_argument(
        "--repo-path",
        "-p",
        default=".",
        help="Path to git repository (default: current directory)",
    )

    args = parser.parse_args()

    generator = ChangelogGenerator(repo_path=args.repo_path)

    if args.release_notes:
        if not args.version:
            print("Error: --version is required for release notes")
            return 1

        notes = generator.generate_release_notes(args.version)
        output_file = args.output.replace("CHANGELOG.md", "RELEASE_NOTES.md")
        with open(output_file, "w") as f:
            f.write(notes)
        print(f"✅ Release notes generated: {output_file}")
    else:
        generator.generate_changelog(version=args.version, output_file=args.output)

    return 0


if __name__ == "__main__":
    exit(main())
