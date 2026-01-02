"""
Agent Prompt Optimization
Reduce token usage through prompt compression and optimization
"""

import logging
from typing import Any, Dict, List, Optional
import re

logger = logging.getLogger(__name__)


class PromptOptimizer:
    """
    Optimize agent prompts to reduce token usage.
    Implements compression, summarization, and token-efficient formatting.
    """
    
    def __init__(self):
        """Initialize prompt optimizer"""
        self.logger = logging.getLogger("prompt.optimizer")
    
    def optimize_prompt(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        preserve_instructions: bool = True
    ) -> str:
        """
        Optimize prompt by removing redundancy and compressing.
        
        Args:
            prompt: Original prompt
            max_tokens: Optional maximum token limit
            preserve_instructions: Preserve important instructions
        
        Returns:
            Optimized prompt
        """
        optimized = prompt
        
        # Remove extra whitespace
        optimized = re.sub(r'\s+', ' ', optimized)
        optimized = optimized.strip()
        
        # Remove redundant phrases
        redundant_patterns = [
            r'\bplease\s+',  # Remove "please"
            r'\bkindly\s+',  # Remove "kindly"
            r'\bI would like to\s+',  # Remove verbose phrases
            r'\bI want to\s+',
            r'\bI need to\s+',
        ]
        
        for pattern in redundant_patterns:
            optimized = re.sub(pattern, '', optimized, flags=re.IGNORECASE)
        
        # Compress repeated words
        optimized = re.sub(r'\b(\w+)(\s+\1\b)+', r'\1', optimized, flags=re.IGNORECASE)
        
        # Remove unnecessary punctuation
        optimized = re.sub(r'[.]{2,}', '.', optimized)
        optimized = re.sub(r'[!]{2,}', '!', optimized)
        
        # If token limit specified, truncate intelligently
        if max_tokens:
            # Rough estimate: 4 characters per token
            max_chars = max_tokens * 4
            if len(optimized) > max_chars:
                optimized = self._truncate_intelligently(optimized, max_chars, preserve_instructions)
        
        return optimized
    
    def _truncate_intelligently(
        self,
        text: str,
        max_chars: int,
        preserve_instructions: bool
    ) -> str:
        """Truncate text while preserving important parts"""
        if len(text) <= max_chars:
            return text
        
        # Split into sentences
        sentences = re.split(r'[.!?]\s+', text)
        
        if preserve_instructions:
            # Keep first sentence (usually instructions)
            result = sentences[0] + '. '
            remaining = max_chars - len(result)
            
            # Add sentences until limit
            for sentence in sentences[1:]:
                if len(sentence) + 2 <= remaining:
                    result += sentence + '. '
                    remaining -= len(sentence) + 2
                else:
                    break
        else:
            # Just truncate
            result = text[:max_chars]
            if not result.endswith(('.', '!', '?')):
                result += '...'
        
        return result
    
    def summarize_context(
        self,
        context: str,
        max_length: int = 500
    ) -> str:
        """
        Summarize context while preserving key information.
        
        Args:
            context: Context to summarize
            max_length: Maximum length
        
        Returns:
            Summarized context
        """
        if len(context) <= max_length:
            return context
        
        # Extract key sentences (first, last, and longest)
        sentences = re.split(r'[.!?]\s+', context)
        
        if len(sentences) <= 3:
            return context[:max_length] + '...'
        
        # Get first sentence
        summary = sentences[0] + '. '
        
        # Get longest sentence (likely most informative)
        middle = sentences[1:-1]
        if middle:
            longest = max(middle, key=len)
            if len(summary) + len(longest) < max_length:
                summary += longest + '. '
        
        # Get last sentence
        if len(summary) + len(sentences[-1]) < max_length:
            summary += sentences[-1]
        
        if len(summary) > max_length:
            summary = summary[:max_length] + '...'
        
        return summary
    
    def compress_history(
        self,
        history: List[Dict[str, str]],
        max_items: int = 10
    ) -> List[Dict[str, str]]:
        """
        Compress conversation history.
        
        Args:
            history: Conversation history
            max_items: Maximum items to keep
        
        Returns:
            Compressed history
        """
        if len(history) <= max_items:
            return history
        
        # Keep first and last items
        keep_indices = set([0, len(history) - 1])
        
        # Keep items with highest importance (longer messages)
        remaining = max_items - 2
        if remaining > 0:
            # Sort by length and keep top N
            sorted_indices = sorted(
                range(1, len(history) - 1),
                key=lambda i: len(history[i].get('content', '')),
                reverse=True
            )
            keep_indices.update(sorted_indices[:remaining])
        
        # Return kept items in order
        return [history[i] for i in sorted(keep_indices)]
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Args:
            text: Text to estimate
        
        Returns:
            Estimated token count
        """
        # Rough estimate: 4 characters per token
        # More accurate would use tiktoken or similar
        return len(text) // 4
    
    def optimize_for_model(
        self,
        prompt: str,
        model_name: str
    ) -> str:
        """
        Optimize prompt for specific model.
        
        Args:
            prompt: Prompt to optimize
            model_name: Model name (e.g., "gpt-4", "claude-3")
        
        Returns:
            Model-optimized prompt
        """
        optimized = prompt
        
        # Model-specific optimizations
        if "gpt" in model_name.lower():
            # GPT models work well with structured prompts
            optimized = self._structure_for_gpt(optimized)
        elif "claude" in model_name.lower():
            # Claude prefers conversational style
            optimized = self._optimize_for_claude(optimized)
        
        return optimized
    
    def _structure_for_gpt(self, prompt: str) -> str:
        """Structure prompt for GPT models"""
        # Add clear sections
        if not prompt.startswith("#"):
            prompt = f"# Task\n\n{prompt}"
        return prompt
    
    def _optimize_for_claude(self, prompt: str) -> str:
        """Optimize prompt for Claude models"""
        # Claude prefers natural language
        return prompt


# Global prompt optimizer instance
_prompt_optimizer: Optional[PromptOptimizer] = None


def get_prompt_optimizer() -> PromptOptimizer:
    """Get global prompt optimizer"""
    global _prompt_optimizer
    if _prompt_optimizer is None:
        _prompt_optimizer = PromptOptimizer()
    return _prompt_optimizer

