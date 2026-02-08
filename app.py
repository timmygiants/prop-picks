import streamlit as st
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import pandas as pd
import re
import hashlib
from zoneinfo import ZoneInfo

# Page config
st.set_page_config(
    page_title="Super Bowl LX Prop Picks",
    page_icon="🏈",
    layout="wide"
)

# Data files
DATA_FILE = "picks.json"
RESULTS_FILE = "results.json"
COUNTS_FILE = "counts.json"
QUESTIONS_FILE = "Super Bowl LX Picks.xlsx"
QUESTIONS_TXT_FILE = "questions.txt"
QUESTION_CONFIG_FILE = "question_config.json"

# Initialize session state
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "questions" not in st.session_state:
    st.session_state.questions = None

def load_question_config() -> Dict:
    """Load question configuration from JSON file"""
    if os.path.exists(QUESTION_CONFIG_FILE):
        with open(QUESTION_CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def parse_questions_txt() -> List[Dict]:
    """Parse questions from questions.txt file (Google Forms export format)"""
    if not os.path.exists(QUESTIONS_TXT_FILE):
        return []
    
    questions = []
    exclude_questions = [
        'Email',
        'Name',
        'Would you like to opt-in for $20 SUPER BOWL POOL',
        'Yes, I like charity and sent $20',
        'Did you Venmo $20',
        'For auditing purposes, what is your Venmo handle',
        'If you win, what is your charity of choice'
    ]
    
    with open(QUESTIONS_TXT_FILE, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines()]
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Skip header/metadata lines
        if not line or line.startswith('Screen reader') or line.startswith('Super Bowl LX') or line.startswith('$20 Entry') or line.startswith('This form') or line.startswith('Banner') or line == '.':
            i += 1
            continue
        
        # Check if this looks like a question (not an answer option)
        # Questions typically don't start with common answer patterns
        if line and not line.startswith('*') and line not in ['Over', 'Under', 'Yes', 'No', 'Heads', 'Tails', 'Even', 'Odd', 'Up', 'Down']:
            question_text = line
            required = False
            options = []
            
            # Check if next line is * (required indicator)
            if i + 1 < len(lines) and lines[i + 1] == '*':
                required = True
                i += 2  # Skip question and *
            else:
                i += 1  # Skip just the question
            
            # Skip if this is an excluded question
            if any(exc.lower() in question_text.lower() for exc in exclude_questions):
                # Skip to next question (until we hit a line that looks like a question)
                while i < len(lines) and (lines[i] in ['Over', 'Under', 'Yes', 'No', 'Heads', 'Tails', 'Even', 'Odd', 'Up', 'Down'] or lines[i].startswith('*') or not lines[i]):
                    i += 1
                continue
            
            # Collect answer options until we hit next question or empty line
            while i < len(lines):
                if not lines[i]:  # Empty line means end of options
                    i += 1
                    break
                
                # Check if this looks like a new question (has question mark or starts with question words or specific patterns)
                looks_like_question = (
                    '?' in lines[i] or
                    lines[i].startswith(('Who ', 'What ', 'Which ', 'Will ', 'How ', 'When ', 'Where ', 'Why ', 'At ')) or
                    lines[i].startswith(('Seattle ', 'Total ', 'National ', 'First ', 'More ', 'Number ', 'Color ', 'Bad ', 'A commercial', 'From kick-off', 'TIE BREAKER', 'Would you', 'Did you', 'For auditing', 'If you win')) or
                    ':' in lines[i] and ('Over/Under' in lines[i] or 'Passing' in lines[i] or 'Rushing' in lines[i] or 'Receptions' in lines[i] or 'Receiving' in lines[i] or 'Jersey' in lines[i] or 'Tackles' in lines[i])
                )
                
                # If it looks like a question and we already have options, this is a new question
                if looks_like_question and len(options) > 0:
                    break
                
                # If it's a common answer option, collect it
                if lines[i] in ['Over', 'Under', 'Yes', 'No', 'Heads', 'Tails', 'Even', 'Odd', 'Up', 'Down', 'Run', 'Pass/Sack', 'Fumble', 'Interception', 'Turnover on Downs']:
                    if lines[i] != '*':
                        options.append(lines[i])
                    i += 1
                    continue
                
                # If it doesn't look like a question, it's an option
                if not looks_like_question:
                    if lines[i] != '*':
                        options.append(lines[i])
                    i += 1
                else:
                    # It looks like a question but we don't have options yet - might be the first question
                    # or might be an option that happens to look like a question
                    # If we're collecting options, treat it as an option unless it has a question mark or starts with specific patterns
                    if len(options) == 0 and ('?' in lines[i] or lines[i].startswith(('TIE BREAKER', 'Would you', 'Did you', 'For auditing', 'If you win'))):
                        # This is actually a new question
                        break
                    else:
                        # Treat as option
                        if lines[i] != '*':
                            options.append(lines[i])
                        i += 1
            
            # Determine question type based on options
            if not options:
                # No options = text or number input
                if 'TIE BREAKER' in question_text.upper() or 'Total Points Scored' in question_text:
                    q_type = 'number'
                    q_options = []
                else:
                    q_type = 'text'
                    q_options = []
            elif len(options) == 2 and set(options) == {'Over', 'Under'}:
                # Over/Under question
                # Extract threshold from question text
                match = re.search(r'over/under\s+([\d.]+)', question_text.lower())
                threshold = float(match.group(1)) if match else 0
                q_type = 'over_under'
                q_options = [threshold]
            elif len(options) == 2 and set(options) == {'Yes', 'No'}:
                q_type = 'yes_no'
                q_options = []
            elif len(options) > 0:
                q_type = 'select'
                q_options = options
            else:
                q_type = 'text'
                q_options = []
            
            questions.append({
                'key': question_text,
                'text': question_text,
                'type': q_type,
                'options': q_options,
                'required': required
            })
        else:
            i += 1
    
    return questions

def load_questions() -> List[Dict]:
    """Load questions from questions.txt file (preferred) or Excel file"""
    if st.session_state.questions is not None:
        return st.session_state.questions
    
    try:
        # Try to load from questions.txt first
        questions = parse_questions_txt()
        
        if questions:
            st.session_state.questions = questions
            return questions
        
        # Fall back to Excel file if questions.txt doesn't exist or is empty
        df = pd.read_excel(QUESTIONS_FILE)
        config = load_question_config()
        
        # Exclude metadata columns
        exclude_cols = [
            'Timestamp', 
            'Email Address', 
            'Name',
            'Would you like to opt-in for $20 SUPER BOWL POOL - Half of winnings go to charity of winner\'s choice and other half in their pocker.  Send a $20 Venmo to @john-deely-67',
            'Did you Venmo $20 to @john-deely-67',
            'For auditing purposes, what is your Venmo handle? (Please include @ in the handle or just Venmo me)',
            'If you win, what is your charity of choice? (Please don\'t say "idk" like Aaron Black)'
        ]
        
        questions = []
        for col in df.columns:
            if col not in exclude_cols:
                # Check if question is in config file first
                if col in config:
                    q_config = config[col]
                    q_type = q_config.get('type', 'text')
                    if q_type == 'over_under':
                        options = [q_config.get('threshold', 0)]
                    else:
                        options = q_config.get('options', [])
                else:
                    # Fall back to automatic detection
                    q_type, options = determine_question_type(col)
                
                questions.append({
                    'key': col,
                    'text': col,
                    'type': q_type,
                    'options': options,
                    'required': 'TIE BREAKER' not in col.upper()  # Tie breaker is optional
                })
        
        st.session_state.questions = questions
        return questions
    except Exception as e:
        st.error(f"Error loading questions: {str(e)}")
        return []

def determine_question_type(question_text: str) -> Tuple[str, List]:
    """Determine question type and options based on question text"""
    q_lower = question_text.lower()
    
    # Game spread question (first question about which team covers)
    # Check for game spread question - must have both teams and a vs/@ indicator
    if ('seahawks' in q_lower and 'patriots' in q_lower and 
        ('vs' in q_lower or '@' in question_text)):
        return 'select', ['Seahawks -4.5', 'Patriots +4.5']
    
    # Over/Under questions
    if 'over/under' in q_lower:
        # Extract the number
        match = re.search(r'over/under\s+([\d.]+)', q_lower)
        if match:
            threshold = float(match.group(1))
            return 'over_under', [threshold]
        return 'over_under', [0]
    
    # Yes/No questions
    if q_lower.startswith('will ') or 'will ' in q_lower:
        return 'yes_no', []
    
    # Heads or Tails
    if 'heads or tails' in q_lower or 'heads/tails' in q_lower:
        return 'select', ['Heads', 'Tails']
    
    # Even or Odd
    if 'even or odd' in q_lower:
        return 'select', ['Even', 'Odd']
    
    # Up or Down
    if 'up or down' in q_lower:
        return 'select', ['Up', 'Down']
    
    # Multiple choice with "or"
    if ' or ' in question_text and not 'over/under' in q_lower:
        # Try to extract options
        parts = question_text.split(' or ')
        if len(parts) == 2:
            # Clean up the options
            opt1 = parts[0].split(':')[-1].strip() if ':' in parts[0] else parts[0].strip()
            opt2 = parts[1].split('?')[0].strip() if '?' in parts[1] else parts[1].strip()
            # Remove common prefixes
            opt1 = re.sub(r'^(which|who|what|more|first)\s+', '', opt1, flags=re.IGNORECASE).strip()
            opt2 = re.sub(r'^(which|who|what|more|first)\s+', '', opt2, flags=re.IGNORECASE).strip()
            if opt1 and opt2:
                return 'select', [opt1, opt2]
    
    # Gatorade color
    if 'gatorade' in q_lower and 'color' in q_lower:
        return 'select', ['Orange', 'Yellow', 'Green', 'Blue', 'Purple', 'Red', 'Clear/Water', 'None']
    
    # First play type
    if 'first play' in q_lower and ('run' in q_lower or 'pass' in q_lower):
        return 'select', ['Run', 'Pass/Sack']
    
    # Turnover type
    if 'first turnover' in q_lower:
        return 'select', ['Fumble', 'Interception', 'Turnover on Downs', 'None']
    
    # Car commercial type
    if 'car commercial' in q_lower:
        return 'select', ['Gas', 'Electric', 'Hybrid']
    
    # Pharmaceutical commercial
    if 'pharmaceutical' in q_lower:
        return 'select', ['Weight Loss/Diabetes', 'Other']
    
    # Coach selection (for National Anthem)
    if 'coach' in q_lower and 'national anthem' in q_lower:
        return 'select', ['Seattle Seahawks Coach', 'New England Patriots Coach']
    
    # Coin toss winner
    if 'who wins coin toss' in q_lower:
        return 'select', ['Seattle Seahawks', 'New England Patriots']
    
    # Default to text input
    return 'text', []

def load_picks() -> List[Dict]:
    """Load picks from JSON file"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return []

def get_pick_by_email(email: str) -> Optional[Dict]:
    """Get existing pick by email address"""
    picks = load_picks()
    for pick in picks:
        if pick.get('email', '').lower() == email.lower():
            return pick
    return None

def save_picks(picks: List[Dict]):
    """Save picks to JSON file"""
    with open(DATA_FILE, 'w') as f:
        json.dump(picks, f, indent=2)

def export_picks_to_excel(picks: List[Dict], filename: str = "picks_export.xlsx"):
    """Export all picks to Excel file with name and email"""
    if not picks:
        return None
    
    # Create a list of dictionaries for the DataFrame
    export_data = []
    for pick in picks:
        row = {
            'Name': pick.get('name', ''),
            'Email': pick.get('email', ''),
            'Playing for Money': pick.get('playing_for_money', ''),
            'Submitted At': pick.get('submitted_at', '')
        }
        
        # Add all question answers
        for key, value in pick.items():
            if key not in ['name', 'email', 'playing_for_money', 'submitted_at']:
                row[key] = value if value is not None else ''
        
        export_data.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(export_data)
    
    # Export to Excel
    df.to_excel(filename, index=False, engine='openpyxl')
    return filename

def get_est_time():
    """Get current time in EST"""
    try:
        est = ZoneInfo("America/New_York")
    except:
        # Fallback for systems without zoneinfo
        from datetime import timedelta
        est_offset = timedelta(hours=-5)  # EST is UTC-5
        est = timezone(est_offset)
    return datetime.now(est), est

def can_view_picks() -> bool:
    """Check if current time is after 6:30pm EST on Sunday 2/8/2026"""
    now, est = get_est_time()
    
    # Target: 6:30pm EST on Sunday, February 8, 2026
    target = datetime(2026, 2, 8, 18, 30, 0, tzinfo=est)
    
    return now >= target

def can_submit_picks() -> bool:
    """Check if submissions are still open (before 6:30pm EST on Sunday 2/8/2026)"""
    now, est = get_est_time()
    
    # Lock at 6:30pm EST on Sunday, February 8, 2026
    lock_time = datetime(2026, 2, 8, 18, 30, 0, tzinfo=est)
    
    return now < lock_time

def load_results() -> Dict:
    """Load actual results from JSON file"""
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_results(results: Dict):
    """Save actual results to JSON file"""
    with open(RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=2)

def load_counts() -> Dict:
    """Load current counts from JSON file"""
    if os.path.exists(COUNTS_FILE):
        with open(COUNTS_FILE, 'r') as f:
            return json.load(f)
    return {
        'dog_commercials': 0,
        'covid_mask_commercials': 0,
        'halftime_songs': 0,
        'mahomes_kelce_mentions': 0
    }

def save_counts(counts: Dict):
    """Save current counts to JSON file"""
    with open(COUNTS_FILE, 'w') as f:
        json.dump(counts, f, indent=2)

def calculate_score(picks: Dict, results: Dict, questions: List[Dict]) -> int:
    """Calculate score based on picks vs results"""
    if not results:
        return 0
    
    score = 0
    base_points = 1  # Default points per question
    
    for question in questions:
        q_key = question['key']
        q_type = question['type']
        
        if q_key not in picks or q_key not in results:
            continue
        
        pick_value = picks[q_key]
        result_value = results[q_key]
        
        if pick_value is None or result_value is None:
            continue
        
        # Handle different question types
        if q_type == 'over_under':
            # For over/under, check if pick matches result (Over/Under)
            if pick_value == result_value:
                score += base_points
        elif q_type == 'yes_no':
            # Yes/No questions
            if str(pick_value).lower() == str(result_value).lower():
                score += base_points
        elif q_type == 'select':
            # Multiple choice
            if str(pick_value).strip().lower() == str(result_value).strip().lower():
                score += base_points
        elif q_type == 'text':
            # Text input - exact match (case insensitive)
            if str(pick_value).strip().lower() == str(result_value).strip().lower():
                score += base_points
        elif q_type == 'number':
            # Number input - exact match
            try:
                if float(pick_value) == float(result_value):
                    score += base_points
            except:
                pass
    
    return score

def create_safe_key(text: str, prefix: str = "", index: int = None) -> str:
    """Create a safe, unique key from text"""
    # Create a hash of the text for uniqueness
    text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
    # Sanitize the text for use in key
    safe_text = re.sub(r'[^a-zA-Z0-9]', '_', text[:30])
    # Include index if provided for extra uniqueness
    if index is not None:
        key = f"{prefix}_{index}_{safe_text}_{text_hash}" if prefix else f"{index}_{safe_text}_{text_hash}"
    else:
        key = f"{prefix}_{safe_text}_{text_hash}" if prefix else f"{safe_text}_{text_hash}"
    return key

def render_question_input(question: Dict, key_prefix: str = "", index: int = None, default_value: any = None):
    """Render appropriate input widget for a question"""
    q_key = question['key']
    q_text = question['text']
    q_type = question['type']
    q_options = question['options']
    q_required = question.get('required', True)
    
    full_key = create_safe_key(q_key, key_prefix, index)
    
    if q_type == 'over_under':
        threshold = q_options[0] if q_options else 0
        default_idx = 0
        if default_value:
            default_idx = 1 if default_value == "Over" else (2 if default_value == "Under" else 0)
        return st.selectbox(
            f"{q_text} *" if q_required else q_text,
            ["", "Over", "Under"],
            index=default_idx,
            key=full_key
        )
    elif q_type == 'yes_no':
        default_idx = 0
        if default_value:
            default_idx = 1 if default_value == "Yes" else (2 if default_value == "No" else 0)
        return st.selectbox(
            f"{q_text} *" if q_required else q_text,
            ["", "Yes", "No"],
            index=default_idx,
            key=full_key
        )
    elif q_type == 'select':
        options = [""] + q_options
        default_idx = 0
        if default_value and default_value in options:
            default_idx = options.index(default_value)
        return st.selectbox(
            f"{q_text} *" if q_required else q_text,
            options,
            index=default_idx,
            key=full_key
        )
    elif q_type == 'number':
        default_val = float(default_value) if default_value else 0.0
        return st.number_input(
            f"{q_text} *" if q_required else q_text,
            min_value=0.0,
            value=default_val,
            step=0.1,
            key=full_key
        )
    else:  # text
        default_text = str(default_value) if default_value else ""
        return st.text_input(
            f"{q_text} *" if q_required else q_text,
            value=default_text,
            key=full_key,
            placeholder="Enter your answer"
        )

def main():
    st.title("🏈 Super Bowl LX Prop Picks")
    st.markdown("---")
    
    # Load questions
    questions = load_questions()
    
    if not questions:
        st.error("Could not load questions from Excel file. Please ensure 'Super Bowl LX Picks.xlsx' is in the same directory.")
        return
    
    # Sidebar for admin (results entry)
    with st.sidebar:
        st.header("⚙️ Admin")
        admin_password = st.text_input("Admin Password", type="password", key="admin_password")
        admin_authenticated = (admin_password == "Pr0pP!cks")
        
        if admin_authenticated:
            st.subheader("Admin Tools")
            
            # Export picks to Excel
            picks = load_picks()
            if picks:
                if st.button("📥 Export All Picks to Excel"):
                    filename = export_picks_to_excel(picks, "picks_export.xlsx")
                    if filename and os.path.exists(filename):
                        with open(filename, 'rb') as f:
                            st.download_button(
                                label="Download Excel File",
                                data=f.read(),
                                file_name=filename,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        st.success(f"Exported {len(picks)} picks to Excel!")
            
            # Live Counting Interface
            if st.checkbox("📊 Live Counting Tools"):
                st.subheader("Real-Time Counters")
                st.markdown("Use these counters during the game to track counting questions.")
                
                counts = load_counts()
                
                # Dog Commercials Counter
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.markdown(f"### 🐕 Dog Commercials")
                    st.markdown(f"**Current Count: {counts['dog_commercials']}**")
                with col2:
                    if st.button("➕", key="dog_inc", use_container_width=True):
                        counts['dog_commercials'] += 1
                        save_counts(counts)
                        st.rerun()
                with col3:
                    if st.button("➖", key="dog_dec", use_container_width=True):
                        counts['dog_commercials'] = max(0, counts['dog_commercials'] - 1)
                        save_counts(counts)
                        st.rerun()
                
                # COVID Mask Commercials Counter
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.markdown(f"### 😷 COVID Mask Commercials")
                    st.markdown(f"**Current Count: {counts['covid_mask_commercials']}**")
                with col2:
                    if st.button("➕", key="covid_inc", use_container_width=True):
                        counts['covid_mask_commercials'] += 1
                        save_counts(counts)
                        st.rerun()
                with col3:
                    if st.button("➖", key="covid_dec", use_container_width=True):
                        counts['covid_mask_commercials'] = max(0, counts['covid_mask_commercials'] - 1)
                        save_counts(counts)
                        st.rerun()
                
                # Halftime Songs Counter
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.markdown(f"### 🎵 Halftime Songs")
                    st.markdown(f"**Current Count: {counts['halftime_songs']}**")
                with col2:
                    if st.button("➕", key="songs_inc", use_container_width=True):
                        counts['halftime_songs'] += 1
                        save_counts(counts)
                        st.rerun()
                with col3:
                    if st.button("➖", key="songs_dec", use_container_width=True):
                        counts['halftime_songs'] = max(0, counts['halftime_songs'] - 1)
                        save_counts(counts)
                        st.rerun()
                
                # Mahomes/Kelce Mentions Counter
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.markdown(f"### 🏈 Mahomes & Kelce Mentions")
                    st.markdown(f"**Current Count: {counts['mahomes_kelce_mentions']}**")
                with col2:
                    if st.button("➕", key="mentions_inc", use_container_width=True):
                        counts['mahomes_kelce_mentions'] += 1
                        save_counts(counts)
                        st.rerun()
                with col3:
                    if st.button("➖", key="mentions_dec", use_container_width=True):
                        counts['mahomes_kelce_mentions'] = max(0, counts['mahomes_kelce_mentions'] - 1)
                        save_counts(counts)
                        st.rerun()
                
                st.markdown("---")
                
                # Button to apply counts to results
                if st.button("✅ Apply Counts to Results", type="primary"):
                    results = load_results()
                    counts = load_counts()
                    
                    # Map counts to question keys
                    question_mapping = {
                        'dog_commercials': 'Number of commercials with dogs: Over/Under 7.5 (from kick-off to end of regulation - does not include animated dogs or costumes)',
                        'covid_mask_commercials': 'How many commercials will have some one wearing a COVID mask? Over/Under 1.5 (from kick-off to end of regulation)',
                        'halftime_songs': 'Total Songs during Halftime Show: Over/Under 10.5',
                        'mahomes_kelce_mentions': 'Total Number of Mentions of Patrick Mahomes AND Travis Kelce: Over/Under 1.5'
                    }
                    
                    thresholds = {
                        'dog_commercials': 7.5,
                        'covid_mask_commercials': 1.5,
                        'halftime_songs': 10.5,
                        'mahomes_kelce_mentions': 1.5
                    }
                    
                    for count_key, question_key in question_mapping.items():
                        count = counts[count_key]
                        threshold = thresholds[count_key]
                        result = "Over" if count > threshold else "Under"
                        results[question_key] = result
                    
                    save_results(results)
                    st.success(f"✅ Applied counts to results! (Dog: {counts['dog_commercials']}, COVID: {counts['covid_mask_commercials']}, Songs: {counts['halftime_songs']}, Mentions: {counts['mahomes_kelce_mentions']})")
                    st.rerun()
                
                if st.button("🔄 Reset All Counters"):
                    counts = {
                        'dog_commercials': 0,
                        'covid_mask_commercials': 0,
                        'halftime_songs': 0,
                        'mahomes_kelce_mentions': 0
                    }
                    save_counts(counts)
                    st.success("All counters reset!")
                    st.rerun()
            
            if st.checkbox("Enter Results (Admin Only)"):
                st.subheader("Enter Actual Results")
                results = load_results()
                
                result_inputs = {}
                for idx, question in enumerate(questions):
                    q_key = question['key']
                    q_text = question['text']
                    q_type = question['type']
                    q_options = question['options']
                    
                    current_value = results.get(q_key, "")
                    safe_key = create_safe_key(q_key, "result", idx)
                    
                    if q_type == 'over_under':
                        threshold = q_options[0] if q_options else 0
                        result_inputs[q_key] = st.selectbox(
                            q_text,
                            ["", "Over", "Under"],
                            index=0 if not current_value else (1 if current_value == "Over" else 2),
                            key=safe_key
                        )
                    elif q_type == 'yes_no':
                        result_inputs[q_key] = st.selectbox(
                            q_text,
                            ["", "Yes", "No"],
                            index=0 if not current_value else (1 if current_value == "Yes" else 2),
                            key=safe_key
                        )
                    elif q_type == 'select':
                        options = [""] + q_options
                        try:
                            idx = options.index(current_value) if current_value else 0
                        except:
                            idx = 0
                        result_inputs[q_key] = st.selectbox(
                            q_text,
                            options,
                            index=idx,
                            key=safe_key
                        )
                    elif q_type == 'number':
                        result_inputs[q_key] = st.number_input(
                            q_text,
                            min_value=0.0,
                            value=float(current_value) if current_value else 0.0,
                            step=0.1,
                            key=safe_key
                        )
                    else:  # text
                        result_inputs[q_key] = st.text_input(
                            q_text,
                            value=current_value if current_value else "",
                            key=safe_key
                        )
                
                if st.button("Save Results"):
                    # Clean up empty values
                    cleaned_results = {k: v if v != "" else None for k, v in result_inputs.items()}
                    cleaned_results['updated_at'] = datetime.now().isoformat()
                    save_results(cleaned_results)
                    st.success("Results saved!")
                    st.rerun()
        else:
            if admin_password:
                st.error("Incorrect password")
    
    # Main tabs - conditionally show "All Picks" tab
    if can_view_picks():
        tab1, tab2, tab3 = st.tabs(["📝 Submit Picks", "📊 Leaderboard", "📋 All Picks"])
    else:
        tab1, tab2 = st.tabs(["📝 Submit Picks", "📊 Leaderboard"])
        tab3 = None
    
    with tab1:
        st.header("Submit Your Prop Picks")
        
        # Instructions
        st.info("""
        **$20 Entry** - Half of winnings to Charity of Winner's choice and other half in their pocket. 
        Must submit picks by 02/08 before National Anthem start. 
        If you want to change your picks, we will accept latest entries. 
        Please Venmo **tim-roberts-16**
        
        *Note: You're welcome to play for fun, but we encourage you to join the pool to help support charity!*
        """)
        
        # Check if submissions are locked
        if not can_submit_picks():
            st.error("🔒 **Submissions are now closed!** Picks were locked at 6:30pm EST on Sunday, February 8th, 2026.")
            st.info("You can still view the leaderboard and all picks below.")
        
        with st.form("picks_form"):
            col1, col2 = st.columns(2)
            
            # Check for existing picks - use session state to track
            if 'check_email' not in st.session_state:
                st.session_state.check_email = ""
            
            with col1:
                name = st.text_input("Your Name *", placeholder="Enter your name", key="form_name")
            with col2:
                email = st.text_input("Email *", placeholder="your.email@example.com", key="form_email")
            
            # Load existing picks when email is entered
            existing_pick = None
            if email and email.lower() != st.session_state.check_email.lower():
                existing_pick = get_pick_by_email(email)
                if existing_pick:
                    st.session_state.check_email = email.lower()
                    st.info(f"📝 Found existing picks for this email. You can edit them below. Changes will be saved when you submit.")
                    # Pre-fill name
                    if existing_pick.get('name'):
                        # Update the name field via session state
                        st.session_state.form_name = existing_pick.get('name', '')
                else:
                    st.session_state.check_email = email.lower()
            elif email:
                # Re-check if email matches what we checked before
                existing_pick = get_pick_by_email(email)
            
            # If we have existing pick, use its name
            if existing_pick and existing_pick.get('name') and not name:
                name = existing_pick.get('name', '')
            
            # Playing for money question
            playing_for_money_default = ""
            if existing_pick and existing_pick.get('playing_for_money'):
                playing_for_money_default = existing_pick.get('playing_for_money')
            
            playing_for_money = st.selectbox(
                "Are you playing for money? *",
                ["", "Yes, I'm in the $20 pool", "No, just playing for fun"],
                index=1 if playing_for_money_default == "Yes, I'm in the $20 pool" else (2 if playing_for_money_default == "No, just playing for fun" else 0),
                help="Select whether you're participating in the $20 charity pool or just playing for fun",
                key="form_playing_for_money"
            )
            
            st.markdown("### Prop Questions")
            st.markdown("Please answer all questions. Questions marked with * are required.")
            
            # Group questions into sections for better organization
            # Use sets to track which questions have been added to avoid duplicates
            added_questions = set()
            game_questions = []
            commercial_questions = []
            halftime_questions = []
            anthem_questions = []
            other_questions = []
            
            # Categorize questions, ensuring no duplicates
            for q in questions:
                q_key = q['key']
                if q_key in added_questions:
                    continue
                
                q_lower = q['text'].lower()
                if any(word in q_lower for word in ['game', 'points', 'coin', 'play', 'touchdown', 'turnover', 'penalty', 'field goal', 'conversion', 'pass', 'run', 'tackle', 'reception', 'rushing', 'passing', 'jersey']):
                    game_questions.append(q)
                    added_questions.add(q_key)
                elif 'commercial' in q_lower:
                    commercial_questions.append(q)
                    added_questions.add(q_key)
                elif any(word in q_lower for word in ['halftime', 'kendrick', 'lamar', 'song']):
                    halftime_questions.append(q)
                    added_questions.add(q_key)
                elif 'anthem' in q_lower:
                    anthem_questions.append(q)
                    added_questions.add(q_key)
                else:
                    other_questions.append(q)
                    added_questions.add(q_key)
            
            pick_inputs = {}
            question_index = 0
            
            if game_questions:
                st.markdown("#### 🏈 Game Props")
                for question in game_questions:
                    default_val = existing_pick.get(question['key']) if existing_pick else None
                    pick_inputs[question['key']] = render_question_input(question, "pick", question_index, default_val)
                    question_index += 1
            
            if anthem_questions:
                st.markdown("#### 🎤 National Anthem Props")
                for question in anthem_questions:
                    default_val = existing_pick.get(question['key']) if existing_pick else None
                    pick_inputs[question['key']] = render_question_input(question, "pick", question_index, default_val)
                    question_index += 1
            
            if commercial_questions:
                st.markdown("#### 📺 Commercial Props")
                for question in commercial_questions:
                    default_val = existing_pick.get(question['key']) if existing_pick else None
                    pick_inputs[question['key']] = render_question_input(question, "pick", question_index, default_val)
                    question_index += 1
            
            if halftime_questions:
                st.markdown("#### 🎵 Halftime Show Props")
                for question in halftime_questions:
                    default_val = existing_pick.get(question['key']) if existing_pick else None
                    pick_inputs[question['key']] = render_question_input(question, "pick", question_index, default_val)
                    question_index += 1
            
            if other_questions:
                st.markdown("#### 📋 Other Props")
                for question in other_questions:
                    default_val = existing_pick.get(question['key']) if existing_pick else None
                    pick_inputs[question['key']] = render_question_input(question, "pick", question_index, default_val)
                    question_index += 1
            
            submitted = st.form_submit_button("Submit Picks", type="primary")
            
            if submitted:
                if not name or not email:
                    st.error("Please fill in your name and email!")
                elif not playing_for_money:
                    st.error("Please indicate if you're playing for money or just for fun!")
                else:
                    # Check required fields
                    required_missing = []
                    for question in questions:
                        if question.get('required', True):
                            q_key = question['key']
                            if not pick_inputs.get(q_key) or pick_inputs[q_key] == "":
                                required_missing.append(question['text'])
                    
                    if required_missing:
                        st.error(f"Please fill in all required fields: {', '.join(required_missing[:3])}{'...' if len(required_missing) > 3 else ''}")
                    else:
                        picks = load_picks()
                        
                        # Clean up empty values
                        cleaned_picks = {k: v if v != "" else None for k, v in pick_inputs.items()}
                        
                        # Check if email already exists - if so, update existing entry
                        existing_index = None
                        for idx, p in enumerate(picks):
                            if p['email'].lower() == email.lower():
                                existing_index = idx
                                break
                        
                        updated_pick = {
                            'name': name,
                            'email': email.lower(),
                            'playing_for_money': playing_for_money if playing_for_money else None,
                            **cleaned_picks,
                            'submitted_at': datetime.now().isoformat()
                        }
                        
                        if existing_index is not None:
                            # Update existing entry
                            picks[existing_index] = updated_pick
                            save_picks(picks)
                            st.session_state.submitted = True
                            st.success(f"✅ Picks updated successfully, {name}! Your previous submission has been replaced.")
                            st.balloons()
                        else:
                            # New submission
                            picks.append(updated_pick)
                            save_picks(picks)
                            st.session_state.submitted = True
                            st.success(f"✅ Picks submitted successfully, {name}!")
                            st.balloons()
    
    with tab2:
        st.header("🏆 Leaderboard")
        
        picks = load_picks()
        results = load_results()
        
        if not picks:
            st.info("No picks submitted yet. Be the first to submit!")
        else:
            # Calculate scores
            leaderboard_data = []
            for pick in picks:
                score = calculate_score(pick, results, questions)
                leaderboard_data.append({
                    'Name': pick['name'],
                    'Score': score,
                    'Email': pick.get('email', 'N/A')
                })
            
            # Sort by score (descending)
            leaderboard_data.sort(key=lambda x: x['Score'], reverse=True)
            
            # Display leaderboard
            df = pd.DataFrame(leaderboard_data)
            
            if results:
                st.success("✅ Results have been entered! Scores are now live.")
            else:
                st.info("⏳ Waiting for results to be entered. Scores will update automatically.")
            
            # Add rank column
            df.insert(0, 'Rank', range(1, len(df) + 1))
            
            # Display without email for privacy
            display_df = df[['Rank', 'Name', 'Score']].copy()
            
            st.dataframe(
                display_df.style.apply(
                    lambda x: ['background-color: #FFD700' if x.name < 1 else 
                              'background-color: #C0C0C0' if x.name < 2 else
                              'background-color: #CD7F32' if x.name < 3 else '' 
                              for _ in x], axis=1
                ),
                use_container_width=True,
                hide_index=True
            )
            
            # Show top 3 with emojis
            if len(df) > 0:
                st.markdown("### 🏅 Top 3")
                for idx, row in df.head(3).iterrows():
                    medal = "🥇" if row['Rank'] == 1 else "🥈" if row['Rank'] == 2 else "🥉"
                    st.markdown(f"{medal} **{row['Name']}** - {row['Score']} points")
    
    if tab3:
        with tab3:
            st.header("All Submitted Picks")
            
            picks = load_picks()
            results = load_results()
            
            if not picks:
                st.info("No picks submitted yet.")
            else:
                for i, pick in enumerate(picks, 1):
                    with st.expander(f"{pick['name']} - Submitted {pick['submitted_at'][:10]}"):
                        # Display picks in organized sections
                        pick_items = {k: v for k, v in pick.items() if k not in ['name', 'email', 'submitted_at', 'playing_for_money']}
                        
                        # Show playing for money status
                        if pick.get('playing_for_money'):
                            st.write(f"**Playing for Money:** {pick['playing_for_money']}")
                            st.markdown("---")
                        
                        cols = st.columns(2)
                        col_idx = 0
                        for q_key, q_value in pick_items.items():
                            if q_value is not None:
                                question = next((q for q in questions if q['key'] == q_key), None)
                                if question:
                                    with cols[col_idx % 2]:
                                        st.write(f"**{question['text']}**")
                                        st.write(f"{q_value}")
                                    col_idx += 1
                        
                        if results:
                            score = calculate_score(pick, results, questions)
                            st.metric("Current Score", f"{score} points")

if __name__ == "__main__":
    main()
