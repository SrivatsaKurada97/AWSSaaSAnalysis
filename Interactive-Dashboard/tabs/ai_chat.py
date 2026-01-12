import streamlit as st
from typing import Any, Dict, List, Optional
from datetime import datetime
import io
import re

from utils.ai_chat import ClaudeChat
import pandas as pd


def _init_state():
    """Initialize session state variables."""
    if "claude_api_key" not in st.session_state:
        st.session_state["claude_api_key"] = ""
    if "ai_chat_history" not in st.session_state:
        st.session_state["ai_chat_history"] = []
    if "ai_show_code" not in st.session_state:
        st.session_state["ai_show_code"] = False


def render_ai_chat(df: Optional[pd.DataFrame]):
    """Render the AI Chat tab using Claude (Anthropic).

    Parameters:
        df: DataFrame to analyze (may be None)
    """
    _init_state()

    st.subheader("💬 AI Chat — Ask Claude About Your Data")

    # Sidebar: Chat management
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 💬 Chat Controls")
        
        # Clear history button
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state["ai_chat_history"] = []
            st.success("Chat history cleared!")
        
        # Export chat button
        if st.session_state.get("ai_chat_history"):
            md = _export_chat_markdown(st.session_state["ai_chat_history"])
            st.download_button(
                label="📥 Export Chat",
                data=md.encode("utf-8"),
                file_name=f"claude_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown",
                use_container_width=True
            )

    # SECTION 1: API Key Configuration
    with st.expander("🔑 API Key Configuration", expanded=not st.session_state.get("claude_api_key")):
        st.markdown("""
        **Get your Claude API key:**
        1. Visit [console.anthropic.com](https://console.anthropic.com/)
        2. Create an account or sign in
        3. Generate an API key
        4. Paste it below and click Save
        """)
        
        key_input = st.text_input(
            "Claude API Key",
            value=st.session_state.get("claude_api_key", ""),
            type="password",
            help="Your API key starts with 'sk-ant-'"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Key", use_container_width=True):
                st.session_state["claude_api_key"] = key_input.strip()
                if key_input.strip():
                    st.success("✅ API Key saved!")
                else:
                    st.warning("⚠️ API Key cleared")
        
        with col2:
            if st.session_state.get("claude_api_key"):
                st.success("✅ Key Configured")
            else:
                st.error("❌ No API Key")

    api_key = st.session_state.get("claude_api_key", "")

    # Validation helper
    def _is_api_key_valid(k: str) -> bool:
        return bool(k and k.startswith("sk-ant-") and len(k) > 20)

    # Show API key status
    if not api_key:
        st.warning("⚠️ **Please configure your Claude API key above to start chatting.**")
    elif not _is_api_key_valid(api_key):
        st.error("❌ **Invalid API key format.** Claude API keys start with 'sk-ant-'")

    # DEBUGGING: Show what data we're actually passing to Claude
    if st.checkbox("🔍 Show DataFrame Info", value=False):
        if df is not None and not df.empty:
            st.write("**DataFrame Shape:**", df.shape)
            st.write("**Columns:**", df.columns.tolist())
            st.write("**First 5 Rows:**")
            st.dataframe(df.head(5))
        
        # Show data types
        st.write("**Data Types:**")
        st.write(df.dtypes)
    else:
        st.warning("No dataframe provided to AI Chat tab")


    # SECTION 2: Quick Start Templates
    st.markdown("""
                <style>
                /* Fix prompt buttons - force single line */
                div[data-testid="stButton"] button {
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
            }
            div[data-testid="stButton"] button p {
            white-space: nowrap !important;
            }
            </style>
            """, unsafe_allow_html=True)

    # Shorten your prompts
    sample_prompts = [
            "Revenue by CLV tier",
    "Platinum vs Gold customers",
    "Top 10 customers",
    "Best product segment",
    "High engagement %",
    "At-risk customers"
    ]

    # SECTION 3: Chat History Display
    history = st.session_state.get("ai_chat_history", [])
    
    if history:
        for i, msg in enumerate(history):
            role = msg.get("role", "assistant")
            content = msg.get("content", "")
            ts = msg.get("ts")
            
            if role == "user":
                with st.chat_message("user"):
                    st.markdown(content)
                    if ts:
                        st.caption(f"🕒 {_format_timestamp(ts)}")
            else:
                with st.chat_message("assistant", avatar="🤖"):
                    _render_formatted_response(content, msg.get("code"))
                    if ts:
                        st.caption(f"🕒 {_format_timestamp(ts)}")
                    
                    # Follow-up suggestions
                    if msg.get("followups"):
                        st.markdown("**💭 Follow-up questions:**")
                        cols = st.columns(len(msg["followups"]))
                        for j, followup in enumerate(msg["followups"]):
                            if cols[j].button(f"↪️ {followup}", key=f"followup_{i}_{j}"):
                                _process_message(followup, df, api_key)

        st.markdown("---")

    # SECTION 4: Chat Input Area
    st.markdown("### 💬 Ask your questions to the data")
    
    # Code generation toggle
    show_code = st.checkbox(
        "🐍 Show generated Python code",
        value=st.session_state.get("ai_show_code", False),
        help="When enabled, Claude will generate executable Python code for your questions"
    )
    st.session_state["ai_show_code"] = show_code

    # Chat input using st.chat_input (modern approach)
    user_input = st.chat_input(
        "Ask a question about your data...",
        key="chat_input"
    )

    # Process message when user submits
    if user_input:
        _process_message(user_input, df, api_key)


def _process_message(user_input: str, df: pd.DataFrame, api_key: str):
    """Process a chat message and get Claude's response.
    
    This function handles the entire message flow without forcing page reloads.
    """
    # Validate API key
    if not api_key or not api_key.startswith("sk-ant-"):
        st.error("❌ Please configure a valid Claude API key first.")
        return

    # Add user message to history
    st.session_state["ai_chat_history"].append({
        "role": "user",
        "content": user_input,
        "ts": datetime.utcnow().isoformat()
    })

    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(user_input)

    # Get Claude's response
    with st.chat_message("assistant", avatar="🤖"):
        with st.status("🤔 Claude is thinking...", expanded=True) as status:
            try:
                # Initialize client
                status.write("Initializing Claude...")
                client = ClaudeChat(api_key=api_key)
                
                # Build context
                status.write("Building data context...")
                dataset_ctx = _build_dataset_context(df)
                
                # Query Claude
                status.write("Getting response from Claude...")
                answer = client.query_data(user_input, df, context=dataset_ctx)
                
                # Generate code if requested
                code_text = None
                if st.session_state.get("ai_show_code"):
                    status.write("Generating Python code...")
                    try:
                        code_text = client.generate_python_code(user_input, df)
                    except Exception as code_exc:
                        st.warning(f"⚠️ Could not generate code: {code_exc}")
                
                status.update(label="✅ Response ready!", state="complete")
                
            except Exception as exc:
                status.update(label="❌ Error", state="error")
                answer = f"**Error:** {str(exc)}\n\nPlease check your API key and try again."
                st.error(answer)
                
                # Add error to history
                st.session_state["ai_chat_history"].append({
                    "role": "assistant",
                    "content": answer,
                    "ts": datetime.utcnow().isoformat()
                })
                return

        # Display response
        _render_formatted_response(answer, code_text)
        
        # Extract and display follow-ups
        followups = _extract_followups(answer)
        if followups:
            st.markdown("**💭 Follow-up questions:**")
            cols = st.columns(len(followups))
            for idx, followup in enumerate(followups):
                cols[idx].button(f"↪️ {followup}", key=f"new_followup_{idx}")

        # Add assistant message to history
        assistant_msg = {
            "role": "assistant",
            "content": answer,
            "ts": datetime.utcnow().isoformat(),
            "followups": followups
        }
        if code_text:
            assistant_msg["code"] = code_text
        
        st.session_state["ai_chat_history"].append(assistant_msg)

        # Show code execution option if code was generated
        if code_text:
            st.markdown("### 🐍 Generated Python Code")
            st.code(code_text, language="python")
            
            if st.button("▶️ Execute Code", key="execute_code"):
                with st.spinner("Executing code..."):
                    try:
                        result = client.execute_safe_code(code_text, df if df is not None else pd.DataFrame())
                        
                        st.success("✅ Code executed successfully!")
                        
                        if isinstance(result, pd.DataFrame):
                            st.dataframe(result, use_container_width=True)
                        elif isinstance(result, (int, float)):
                            st.metric("Result", result)
                        else:
                            st.write(result)
                    except Exception as exc:
                        st.error(f"❌ Error executing code: {exc}")


# ---------------- Helper Utilities ----------------

def _build_dataset_context(df: Optional[pd.DataFrame]) -> str:
    """Build a comprehensive dataset summary with actual sample data for Claude."""
    if df is None or df.empty:
        return "Dataset: No data available. Please load data first."
    
    parts = []
    
    # Header
    parts.append("=" * 60)
    parts.append("DATASET INFORMATION")
    parts.append("=" * 60)
    parts.append("")
    
    # Basic stats
    parts.append(f"📊 **Overview:**")
    parts.append(f"   Total Records: {df.shape[0]:,}")
    parts.append(f"   Total Columns: {df.shape[1]}")
    parts.append("")
    
    # Column information
    parts.append(f"📋 **Column Names:**")
    parts.append(f"   {', '.join(df.columns.tolist())}")
    parts.append("")
    
    # Key metrics
    parts.append(f"📈 **Key Metrics:**")
    
    # CLV Tier distribution
    clv_col = next((c for c in df.columns if 'clv' in c.lower() or 'tier' in c.lower()), None)
    if clv_col and clv_col in df.columns:
        tier_counts = df[clv_col].value_counts().to_dict()
        parts.append(f"   CLV Tier Distribution:")
        for tier, count in sorted(tier_counts.items()):
            pct = (count / len(df)) * 100
            parts.append(f"      - {tier}: {count} customers ({pct:.1f}%)")
    
    # Engagement distribution
    eng_col = next((c for c in df.columns if 'engag' in c.lower()), None)
    if eng_col and eng_col in df.columns:
        eng_counts = df[eng_col].value_counts().to_dict()
        parts.append(f"   Engagement Distribution:")
        for level, count in sorted(eng_counts.items()):
            pct = (count / len(df)) * 100
            parts.append(f"      - {level}: {count} customers ({pct:.1f}%)")
    
    # Revenue statistics
    rev_col = next((c for c in df.columns if any(k in c.lower() for k in ['revenue', 'sales', 'total_event', 'user_table'])), None)
    if rev_col and rev_col in df.columns:
        try:
            rev_data = pd.to_numeric(df[rev_col], errors='coerce').dropna()
            if not rev_data.empty:
                total = rev_data.sum()
                avg = rev_data.mean()
                median = rev_data.median()
                max_val = rev_data.max()
                min_val = rev_data.min()
                
                parts.append(f"   Revenue Statistics ({rev_col}):")
                parts.append(f"      - Total: ${total:,.2f}")
                parts.append(f"      - Average: ${avg:,.2f}")
                parts.append(f"      - Median: ${median:,.2f}")
                parts.append(f"      - Range: ${min_val:,.2f} to ${max_val:,.2f}")
        except Exception as e:
            parts.append(f"   Revenue Statistics: Error - {e}")
    
    parts.append("")
    
    # Sample data - SIMPLIFIED AND ROBUST VERSION
    parts.append("=" * 60)
    parts.append(f"COMPLETE CUSTOMER DATABASE - ALL {len(df)} ROWS")
    parts.append("=" * 60)
    parts.append("")
    
    try:
        # Get first 10 rows
        sample_df = df.copy()
        
        # Find customer and revenue columns
        cust_col = next((c for c in sample_df.columns if 'customer' in c.lower() and 'id' not in c.lower()), None)
        custid_col = next((c for c in sample_df.columns if 'customerid' in c.lower() or 'customer_id' in c.lower()), None)
        
        # Select key columns to show
        cols_to_show = []
        
        # Add customer identifier
        if custid_col:
            cols_to_show.append(custid_col)
        if cust_col and cust_col not in cols_to_show:
            cols_to_show.append(cust_col)
        
        # Add CLV tier if exists
        if clv_col and clv_col in sample_df.columns:
            cols_to_show.append(clv_col)
        
        # Add engagement if exists
        if eng_col and eng_col in sample_df.columns:
            cols_to_show.append(eng_col)
        
        # Add revenue column
        if rev_col and rev_col in sample_df.columns:
            cols_to_show.append(rev_col)
        
        # Add segment if exists
        seg_col = next((c for c in sample_df.columns if 'segment' in c.lower()), None)
        if seg_col and seg_col in sample_df.columns:
            cols_to_show.append(seg_col)
        
        # Add product count if exists
        prod_col = next((c for c in sample_df.columns if 'product' in c.lower() and 'count' in c.lower()), None)
        if prod_col and prod_col in sample_df.columns:
            cols_to_show.append(prod_col)
        
        # Remove duplicates while preserving order
        cols_to_show = list(dict.fromkeys(cols_to_show))
        
        # Make sure all columns exist
        cols_to_show = [c for c in cols_to_show if c in sample_df.columns]
        
        # If we don't have enough columns, add more
        if len(cols_to_show) < 8:
            remaining_cols = [c for c in sample_df.columns if c not in cols_to_show]
            cols_to_show.extend(remaining_cols[:8 - len(cols_to_show)])
        
        # Create subset
        if cols_to_show:
            subset = sample_df[cols_to_show]
        else:
            # Fallback: just use first 8 columns
            subset = sample_df.iloc[:, :8]
        
        # Convert to string representation (more reliable than CSV)
        parts.append("Columns: " + " | ".join(subset.columns))
        parts.append("-" * 60)
        
        for idx, row in subset.iterrows():
            row_parts = []
            for col in subset.columns:
                val = row[col]
                # Format value nicely
                if pd.isna(val):
                    formatted = "N/A"
                elif isinstance(val, int):
                    formatted = f"{val:,}"
                elif isinstance(val, float):
                    formatted = f"{val:,.2f}"
                else:
                    formatted = str(val)[:30]  # Limit string length
                row_parts.append(formatted)
            
            parts.append(" | ".join(row_parts))
        
        parts.append("")
        parts.append(f"✅ COMPLETE DATASET: All {len(df):,} customers included above")
        
    except Exception as e:
        # Better error reporting
        import traceback
        parts.append(f"❌ Error generating sample data:")
        parts.append(f"   Error type: {type(e).__name__}")
        parts.append(f"   Error message: {str(e)}")
        parts.append(f"   Traceback: {traceback.format_exc()}")
        parts.append("")
        parts.append("Available columns in dataframe:")
        parts.append(f"   {', '.join(df.columns.tolist())}")
    
    parts.append("")
    parts.append("=" * 60)
    parts.append("END OF DATASET INFORMATION")
    parts.append("=" * 60)
    
    return "\n".join(parts)



def _extract_followups(text: str) -> List[str]:
    """Extract follow-up question suggestions from Claude's response."""
    if not text:
        return []
    
    # Look for "follow-up" sections
    lines = text.splitlines()
    followups = []
    
    in_followup_section = False
    for line in lines:
        line_lower = line.lower()
        
        if any(keyword in line_lower for keyword in ['follow', 'you might', 'you could also']):
            in_followup_section = True
            continue
        
        if in_followup_section:
            # Extract bulleted items
            match = re.match(r"^[-*•]\s*(.+)", line.strip())
            if match:
                followups.append(match.group(1).strip())
            elif line.strip() and not line.startswith('#'):
                # End of section
                break
    
    return followups[:3]  # Return max 3 suggestions


def _render_formatted_response(text: str, code: Optional[str] = None):
    """Render Claude's response with nice formatting."""
    if not text:
        return
    
    # Check for code blocks in the text
    code_block_re = re.compile(r"```.*?```", re.DOTALL)
    code_blocks = code_block_re.findall(text)
    safe_text = code_block_re.sub("", text)
    
    # Render main text
    st.markdown(safe_text)
    
    # Render extracted code blocks
    for i, cb in enumerate(code_blocks):
        # Remove backticks and language identifier
        clean_code = cb.strip('`').strip()
        if clean_code.startswith('python\n'):
            clean_code = clean_code[7:]
        st.code(clean_code, language="python")
    
    # Render separately provided code
    if code:
        st.markdown("**📋 Generated Code:**")
        st.code(code, language="python")


def _format_timestamp(ts: str) -> str:
    """Format ISO timestamp to readable string."""
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return dt.strftime("%I:%M %p")
    except Exception:
        return ts


def _export_chat_markdown(history: List[Dict[str, Any]]) -> str:
    """Export chat history as markdown."""
    lines = [
        f"# Claude Chat Export",
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "---",
        ""
    ]
    
    for msg in history:
        ts = msg.get('ts', '')
        role = msg.get('role', 'assistant')
        content = msg.get('content', '')
        
        lines.append(f"## {role.title()} — {_format_timestamp(ts)}")
        lines.append("")
        lines.append(content)
        lines.append("")
        
        if msg.get('code'):
            lines.append("```python")
            lines.append(msg['code'])
            lines.append("```")
            lines.append("")
        
        lines.append("---")
        lines.append("")
    
    return "\n".join(lines)