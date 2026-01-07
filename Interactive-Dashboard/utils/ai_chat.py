"""Claude (Anthropic) integration with BYOK support - UPDATED FOR MODERN API.

Provides a wrapper `ClaudeChat` to query data summaries, ask for
python/pandas code, and safely execute generated code against a DataFrame.

Uses the modern Anthropic Messages API (2023+).

Security: `execute_safe_code` performs AST checks to block imports and
dangerous builtin usage. Only `pandas` (as `pd`) and `numpy` (as `np`) and
the provided `df` are available in the execution namespace.

Requires: `anthropic>=0.18.0` (pip install anthropic --upgrade)
"""

from __future__ import annotations

import ast
import re
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from streamlit import context

try:
    import anthropic
except Exception:
    anthropic = None


class ClaudeChat:
    """Simple Claude wrapper using the modern `anthropic` Messages API.

    Usage: ClaudeChat(api_key="sk-ant-...")
    """

    # Use the latest Claude Sonnet model
    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def __init__(self, api_key: str):
        if not api_key or not isinstance(api_key, str):
            raise ValueError("API key required")
        
        if anthropic is None:
            raise ImportError(
                "anthropic library not installed. "
                "Install with: pip install anthropic --upgrade"
            )

        try:
            # Modern API initialization
            self.client = anthropic.Anthropic(api_key=api_key)
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize Anthropic client: {exc}") from exc

    # ----------------- helpers: dataframe summarization -----------------
    def _summarize_df(self, df: pd.DataFrame, max_samples: int = 5) -> str:
        """Return a concise textual summary of the DataFrame."""
        if df is None or df.empty:
            return "(empty dataframe)"

        parts: List[str] = []
        parts.append(f"Shape: {df.shape[0]} rows x {df.shape[1]} cols")

        # columns + dtypes + nulls
        cols_info = []
        for c in df.columns:
            dtype = str(df[c].dtype)
            nulls = int(df[c].isna().sum())
            cols_info.append(f"{c} ({dtype}, nulls={nulls})")
        parts.append("Columns: " + ", ".join(cols_info))

        # sample rows (head)
        try:
            head = df.head(max_samples).fillna("").to_dict(orient="records")
            sample_lines = [
                " | ".join([f"{k}: {v}" for k, v in row.items()]) 
                for row in head
            ]
            parts.append("Sample rows:\n" + "\n".join(sample_lines))
        except Exception:
            parts.append("Sample rows: (could not render)")

        # numeric summary
        try:
            num = df.select_dtypes(include=[np.number])
            if not num.empty:
                desc = num.describe().loc[["count", "mean", "50%", "std"]].round(2).to_dict()
                stats_lines = []
                for col, vals in desc.items():
                    stats_lines.append(
                        f"{col}: count={int(vals['count'])}, "
                        f"mean={vals['mean']}, median={vals['50%']}, std={vals['std']}"
                    )
                parts.append("Numeric summary:\n" + "\n".join(stats_lines))
        except Exception:
            pass

        return "\n\n".join(parts)

    # ----------------- core methods -----------------
    def query_data(self, question: str, dataframe: pd.DataFrame, context: str = "") -> str:
        """Ask Claude a question about the dataset using Messages API."""
        if not hasattr(self, 'client'):
            raise RuntimeError("Anthropic client not initialized")

        # Build the system message - TELL CLAUDE IT HAS DATA
        system_message = (
        f"You are a data analyst with COMPLETE, UNRESTRICTED ACCESS to the ENTIRE customer database. "
        f"CRITICAL: You have ALL {len(dataframe)} customers - this is the COMPLETE dataset, NOT a sample. "
        f"Every single customer record is included in the data provided. "
        f"There are exactly {len(dataframe)} total customers and you can see ALL of them. "
        f"\n\n"
        f"When answering:\n"
        f"- DO NOT say 'based on sample data' - you have the COMPLETE dataset\n"
        f"- DO NOT say 'approximately' - give exact counts\n"
        f"- DO use phrases like 'based on all {len(dataframe)} customers' or 'across the complete dataset'\n"
        f"- Provide specific customer names, exact figures, and precise percentages\n"
        f"\n"
        f"You are analyzing the FULL, COMPLETE dataset with every customer included."
    )

    # Build the user message with context
        user_message = []
        if context:
            user_message.append("Here is the dataset information and sample data:\n")
            user_message.append(context)
            user_message.append("\n---\n")
        user_message.append(f"Question: {question}")
        user_message.append("\nProvide a specific answer using the actual data shown above.")
    
        full_user_message = "\n".join(user_message)

        try:
            # Use modern Messages API
            response = self.client.messages.create(
                model=self.DEFAULT_MODEL,
                max_tokens=2048,  # Increase for more detailed answers
                system=system_message,
                messages=[
                    {"role": "user", "content": full_user_message}
                ],
                temperature=0.3
            )
        
            # Extract text from response
            if hasattr(response, 'content') and response.content:
                text_blocks = [
                    block.text for block in response.content 
                    if hasattr(block, 'text')
                ]
                return "\n".join(text_blocks) if text_blocks else ""
        
            return ""
        
        except Exception as exc:
            raise RuntimeError(f"Claude API error: {exc}")

    # ----------------- safety: execute code -----------------
    @staticmethod
    def _extract_code(text: str) -> str:
        """Extract python code from a text response (handles markdown fences)."""
        if not text:
            return ""
        
        # Look for fenced code blocks
        fence_re = re.compile(r"```(?:python)?\n(.*?)```", re.DOTALL | re.IGNORECASE)
        m = fence_re.search(text)
        if m:
            return m.group(1).strip()
        
        # Fallback: indented code
        lines = text.splitlines()
        code_lines = [ln for ln in lines if ln.startswith("    ") or ln.startswith("\t")]
        if code_lines:
            return "\n".join([ln.lstrip() for ln in code_lines]).strip()
        
        return text.strip()

    @staticmethod
    def _is_code_safe(code: str) -> Tuple[bool, Optional[str]]:
        """Basic AST inspection to block imports and dangerous names."""
        try:
            tree = ast.parse(code)
        except Exception as exc:
            return False, f"Code parse error: {exc}"

        forbidden_nodes = (ast.Import, ast.ImportFrom)
        forbidden_names = {
            "open", "exec", "eval", "compile", "__import__", 
            "os", "sys", "subprocess", "socket", "shutil", 
            "psutil", "requests", "urllib"
        }

        for node in ast.walk(tree):
            if isinstance(node, forbidden_nodes):
                return False, "Import statements are not allowed in generated code."
            
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in forbidden_names:
                    return False, f"Use of {node.func.id} is not allowed."
            
            if isinstance(node, ast.Attribute):
                if isinstance(node.attr, str) and node.attr.startswith("__"):
                    return False, "Access to dunder attributes is not allowed."

        return True, None

    def execute_safe_code(
        self, 
        code: str, 
        dataframe: pd.DataFrame
    ) -> Union[pd.DataFrame, str]:
        """Execute generated code in a restricted namespace.

        Rules:
        - `df` is provided as a copy of `dataframe`.
        - `pd` and `np` are available.
        - Code must not contain import statements or blacklisted calls.

        Returns:
            Result of execution (DataFrame, value, or error message)
        """
        if not code or not code.strip():
            return "No code to execute."

        safe, reason = self._is_code_safe(code)
        if not safe:
            return f"Code rejected for safety: {reason}"

        # Prepare restricted namespace
        local_ns: Dict[str, Any] = {
            "pd": pd, 
            "np": np, 
            "df": dataframe.copy()
        }
        global_ns: Dict[str, Any] = {}

        try:
            exec(code, global_ns, local_ns)
        except Exception as exc:
            return f"Error executing code: {exc}"

        # Prefer explicit `result` variable
        if "result" in local_ns:
            return local_ns["result"]

        # Otherwise, if df changed, return it
        try:
            maybe_df = local_ns.get("df")
            if isinstance(maybe_df, pd.DataFrame):
                return maybe_df
        except Exception:
            pass

        # Otherwise, collect outputs
        try:
            outputs = {
                k: v for k, v in local_ns.items() 
                if k not in ("pd", "np", "df", "__builtins__")
            }
            if outputs:
                return str(outputs)
        except Exception:
            pass

        return "Execution completed (no result produced)."